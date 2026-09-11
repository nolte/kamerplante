"""Tenant-scoped notification API endpoints (REQ-030).

All endpoints are mounted under /api/v1/t/{tenant_slug}/notifications/.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.v1.auth.router import limiter
from app.api.v1.notifications.schemas import (
    ChannelStatusResponse,
    NotificationListResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
    NotificationResponse,
    PwaSubscribeRequest,
    PwaSubscribeResponse,
    PwaUnsubscribeRequest,
    PwaUnsubscribeResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    UnreadCountResponse,
    VapidPublicKeyResponse,
)
from app.common.auth import get_current_tenant
from app.common.dependencies import get_care_reminder_service, get_notification_service
from app.common.enums import ReminderType
from app.common.exceptions import NotFoundError
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.config.settings import settings
from app.domain.models.notification import NotificationPreferences
from app.domain.models.tenant_context import TenantContext
from app.domain.services.care_reminder_service import CareReminderService
from app.domain.services.notification_service import NotificationService

#: Actionable ``action_id`` values that confirm the source care reminder (§4.2).
_CARE_CONFIRM_ACTIONS: frozenset[str] = frozenset({"confirm", "confirm_watering", "done"})

router = APIRouter(prefix="/notifications", tags=["notifications"], responses=NOT_FOUND_RESPONSE)


def _notification_response(n) -> NotificationResponse:
    """Convert domain Notification to API response."""
    return NotificationResponse(
        key=n.key or "",
        tenant_key=n.tenant_key,
        user_key=n.user_key,
        notification_type=n.notification_type,
        title=n.title,
        body=n.body,
        urgency=n.urgency,
        data=n.data,
        actions=[{"action_id": a.action_id, "title": a.title, "uri": a.uri} for a in n.actions],
        image_url=n.image_url,
        group_key=n.group_key,
        channels_sent=n.channels_sent,
        channels_failed=n.channels_failed,
        status=n.status,
        read_at=n.read_at,
        acted_at=n.acted_at,
        escalation_level=n.escalation_level,
        parent_notification_key=n.parent_notification_key,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


# ── List notifications ───────────────────────────────────────────────


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    pagination: PaginationParams = Depends(get_pagination),
    unread_only: bool = Query(False, description="If true, return only unread notifications."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """List notifications for the current user within this tenant."""
    items = service.list_notifications(
        user_key=ctx.user_key,
        tenant_key=ctx.tenant_key,
        limit=pagination.limit,
        offset=pagination.offset,
        unread_only=unread_only,
    )
    unread_count = service.count_unread(
        user_key=ctx.user_key,
        tenant_key=ctx.tenant_key,
    )
    return NotificationListResponse(
        items=[_notification_response(n) for n in items],
        total=len(items),
        unread_count=unread_count,
    )


# ── Unread count ─────────────────────────────────────────────────────


@router.get("/count", response_model=UnreadCountResponse)
def count_unread(
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    """Count unread notifications for the current user."""
    count = service.count_unread(
        user_key=ctx.user_key,
        tenant_key=ctx.tenant_key,
    )
    return UnreadCountResponse(unread_count=count)


# ── Mark as read ─────────────────────────────────────────────────────


@router.post(
    "/{notification_key}/read",
    response_model=NotificationResponse,
)
def mark_read(
    notification_key: Annotated[str, Path(description="Document key of the notification.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a notification as read."""
    result = service.mark_read(notification_key, ctx.tenant_key, user_key=ctx.user_key)
    if result is None:
        raise NotFoundError(
            entity="Notification",
            key=notification_key,
        )
    return _notification_response(result)


# ── Mark as acted ────────────────────────────────────────────────────


@router.post(
    "/{notification_key}/act",
    response_model=NotificationResponse,
)
def mark_acted(
    notification_key: Annotated[str, Path(description="Document key of the notification.")],
    action_id: str = Query(..., min_length=1, description="Identifier of the actionable button that was tapped."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
    care_service: CareReminderService = Depends(get_care_reminder_service),
) -> NotificationResponse:
    """Perform an actionable-button callback (REQ-030 §4.2, Issue #742).

    A one-tap ``Done`` on an actionable care notification both confirms the source
    reminder (creating a ``CareConfirmation`` and closing the pending care task) and
    marks the notification acted+read — in a single step. Ownership is verified
    fail-closed first; a foreign/missing notification yields 404 without disclosing
    which. Non-care notifications simply stamp acted+read.
    """
    notif = service.get_notification(notification_key, ctx.tenant_key, user_key=ctx.user_key)
    if notif is None:
        raise NotFoundError(entity="Notification", key=notification_key)

    # §4.2 — confirm the source care reminder for an actionable care notification.
    if notif.notification_type.startswith("care.") and action_id in _CARE_CONFIRM_ACTIONS:
        plant_key = notif.data.get("plant_key")
        raw_reminder_type = notif.data.get("reminder_type")
        if plant_key and raw_reminder_type:
            try:
                reminder_type = ReminderType(raw_reminder_type)
            except ValueError:
                reminder_type = None
            if reminder_type is not None:
                care_service.confirm_reminder(
                    plant_key,
                    reminder_type,
                    tenant_key=ctx.tenant_key,
                    user_key=ctx.user_key,
                )

    # Stamp read + acted so the notification drops out of the unread badge.
    service.mark_read(notification_key, ctx.tenant_key, user_key=ctx.user_key)
    result = service.mark_acted(notification_key, ctx.tenant_key, action_id, user_key=ctx.user_key)
    if result is None:
        raise NotFoundError(entity="Notification", key=notification_key)
    return _notification_response(result)


# ── Preferences ──────────────────────────────────────────────────────


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_preferences(
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """Get notification preferences for the current user."""
    prefs = service.get_preferences(ctx.user_key)
    return NotificationPreferencesResponse(
        key=prefs.key,
        user_key=prefs.user_key or ctx.user_key,
        channels=prefs.channels,
        quiet_hours=prefs.quiet_hours,
        batching=prefs.batching,
        escalation=prefs.escalation,
        type_overrides=prefs.type_overrides,
        daily_summary=prefs.daily_summary,
        created_at=prefs.created_at,
        updated_at=prefs.updated_at,
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_preferences(
    body: NotificationPreferencesRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferencesResponse:
    """Update notification preferences for the current user."""
    prefs = NotificationPreferences(
        user_key=ctx.user_key,
        channels=body.channels,
        quiet_hours=body.quiet_hours,
        batching=body.batching,
        escalation=body.escalation,
        type_overrides=body.type_overrides,
        daily_summary=body.daily_summary,
    )
    updated = service.update_preferences(ctx.user_key, prefs)
    return NotificationPreferencesResponse(
        key=updated.key,
        user_key=updated.user_key,
        channels=updated.channels,
        quiet_hours=updated.quiet_hours,
        batching=updated.batching,
        escalation=updated.escalation,
        type_overrides=updated.type_overrides,
        daily_summary=updated.daily_summary,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


# ── Channel status ──────────────────────────────────────────────────


@router.get(
    "/channels/status",
    response_model=list[ChannelStatusResponse],
)
async def channel_status(
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> list[ChannelStatusResponse]:
    """Health status of all registered notification channels."""
    statuses = await service.get_channel_status()
    return [
        ChannelStatusResponse(
            channel_key=s["channel_key"],
            healthy=s["healthy"],
            supports_actions=s["supports_actions"],
            supports_batching=s["supports_batching"],
        )
        for s in statuses
    ]


# ── Test notification ───────────────────────────────────────────────


@router.post("/test", response_model=TestNotificationResponse)
@limiter.limit(settings.rate_limit_notification_test)
async def send_test_notification(
    request: Request,
    body: TestNotificationRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> TestNotificationResponse:
    """Send a test notification through the caller's own configured channel.

    Rate limited per client address (``settings.rate_limit_notification_test``).
    The previous version of this docstring promised "5 requests per hour per
    user" and no limiter existed in this module at all — an unbacked claim found
    by the #1353 write-route sweep, and the reason the route is allowlisted there
    rather than gated: the notification goes to the caller's own channel with a
    fixed body, so a domain role is the wrong axis, but the volume still needs a
    bound.

    ``request`` is unused by the body and required by the decorator: slowapi
    inspects the signature and raises ``No "request" or "websocket" argument`` at
    decoration time, so deleting it as dead breaks the import rather than quietly
    disarming the limit.
    """
    result = await service.send_test(
        user_key=ctx.user_key,
        tenant_key=ctx.tenant_key,
        channel_key=body.channel_key,
    )
    return TestNotificationResponse(
        status=result.get("status", "error"),
        channel_key=body.channel_key,
        success=result.get("success", False),
        error=result.get("error"),
    )


# ── Web Push (PWA) ───────────────────────────────────────────────────


@router.get("/pwa/vapid-public-key", response_model=VapidPublicKeyResponse)
def get_vapid_public_key(
    ctx: TenantContext = Depends(get_current_tenant),
) -> VapidPublicKeyResponse:
    """Return the VAPID public key for client-side Web Push subscription."""
    return VapidPublicKeyResponse(vapid_public_key=settings.vapid_public_key)


@router.post("/pwa/subscribe", response_model=PwaSubscribeResponse)
def subscribe_pwa(
    body: PwaSubscribeRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> PwaSubscribeResponse:
    """Register a Web Push subscription for the current user."""
    endpoint = service.subscribe_pwa(
        user_key=ctx.user_key,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
        user_agent=body.user_agent,
    )
    return PwaSubscribeResponse(endpoint=endpoint)


@router.post("/pwa/unsubscribe", response_model=PwaUnsubscribeResponse)
def unsubscribe_pwa(
    body: PwaUnsubscribeRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: NotificationService = Depends(get_notification_service),
) -> PwaUnsubscribeResponse:
    """Remove a Web Push subscription for the current user."""
    removed = service.unsubscribe_pwa(user_key=ctx.user_key, endpoint=body.endpoint)
    return PwaUnsubscribeResponse(removed=removed)

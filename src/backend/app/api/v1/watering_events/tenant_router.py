from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.mapping import to_response
from app.api.v1.watering_events.schemas import (
    VolumeSuggestionResponse,
    WateringConfirmRequest,
    WateringConfirmResponse,
    WateringEventCreate,
    WateringEventResponse,
    WateringEventWithWarnings,
    WateringQuickConfirmRequest,
    WateringStatsResponse,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import get_watering_service
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action
from app.domain.models.tenant_context import TenantContext
from app.domain.models.watering_event import WateringEvent
from app.domain.services.watering_service import WateringService

router = APIRouter(tags=["watering-events"], responses=NOT_FOUND_RESPONSE)


def _event_response(e: WateringEvent) -> WateringEventResponse:
    return to_response(e, WateringEventResponse)


@router.post("/watering-events", response_model=WateringEventWithWarnings, status_code=201)
def create_event(
    body: WateringEventCreate,
    ctx: TenantContext = Depends(require_permission("watering-event", Action.CREATE)),
    service: WateringService = Depends(get_watering_service),
):
    """Record a watering event and return it with any warnings."""
    event = WateringEvent(**body.model_dump(), tenant_key=ctx.tenant_key)
    result = service.create_event(event)
    return WateringEventWithWarnings(event=_event_response(result["event"]), warnings=result["warnings"])


@router.get("/watering-events", response_model=list[WateringEventResponse])
def list_events(
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """List the tenant's watering events (paginated)."""
    items, _total = service.list_events(pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    return [_event_response(e) for e in items]


@router.get("/watering-events/{key}", response_model=WateringEventResponse)
def get_event(
    key: Annotated[str, Path(description="Document key of the watering event.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """Return a single watering event by key."""
    return _event_response(service.get_event(key, tenant_key=ctx.tenant_key))


@router.get("/plant-instances/{plant_key}/watering-events", response_model=list[WateringEventResponse])
def get_plant_events(
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """List a plant instance's watering events (paginated).

    A ``plant_key`` belonging to another tenant yields an empty list — the
    tenant scope is enforced in the repository query, not by an anchor check
    here (#927).
    """
    events = service.get_by_plant(plant_key, pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    return [_event_response(e) for e in events]


@router.get("/locations/{location_key}/watering-events", response_model=list[WateringEventResponse])
def get_location_events(
    location_key: Annotated[str, Path(description="Document key of the location.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """List a location's watering events (paginated).

    A ``location_key`` belonging to another tenant yields an empty list (#927).
    """
    events = service.get_by_location(location_key, pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    return [_event_response(e) for e in events]


@router.get("/locations/{location_key}/watering-stats", response_model=WateringStatsResponse)
def get_location_stats(
    location_key: Annotated[str, Path(description="Document key of the location.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """Return aggregated watering statistics for a location.

    A ``location_key`` belonging to another tenant reports zeroes rather than the
    other tenant's event count and applied volume (#927).
    """
    stats = service.get_stats(location_key, tenant_key=ctx.tenant_key)
    return WateringStatsResponse(**stats)


@router.post("/watering-events/confirm", response_model=WateringConfirmResponse, status_code=201)
def confirm_watering(
    body: WateringConfirmRequest,
    ctx: TenantContext = Depends(require_permission("watering-event", Action.CREATE)),
    service: WateringService = Depends(get_watering_service),
):
    """Confirm a scheduled watering task, creating the resulting event."""
    result = service.confirm_watering(
        run_key=body.run_key,
        task_key=body.task_key,
        measured_ec=body.measured_ec,
        measured_ph=body.measured_ph,
        volume_liters=body.volume_liters,
        overrides=body.overrides,
        tenant_key=ctx.tenant_key,
    )
    return WateringConfirmResponse(**result)


@router.post("/watering-events/quick-confirm", response_model=WateringConfirmResponse, status_code=201)
def quick_confirm_watering(
    body: WateringQuickConfirmRequest,
    ctx: TenantContext = Depends(require_permission("watering-event", Action.CREATE)),
    service: WateringService = Depends(get_watering_service),
):
    """Quick-confirm a scheduled watering task with default values."""
    result = service.quick_confirm_watering(body.run_key, body.task_key, tenant_key=ctx.tenant_key)
    return WateringConfirmResponse(**result)


@router.get(
    "/plant-instances/{plant_key}/watering-volume-suggestion",
    response_model=VolumeSuggestionResponse,
)
def suggest_watering_volume(
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    reference_date: date | None = Query(default=None, description="Reference date (defaults to today)."),
    hemisphere: str = Query(default="north", pattern="^(north|south)$", description="Hemisphere for seasonality."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringService = Depends(get_watering_service),
):
    """Suggest a watering volume for a plant instance based on phase and season.

    A ``plant_key`` outside the caller's tenant answers **404**, not a
    recommendation computed from the other tenant's plant (#952).
    """
    suggestion = service.suggest_volume(plant_key, reference_date, hemisphere, tenant_key=ctx.tenant_key)
    return VolumeSuggestionResponse(**suggestion.model_dump())

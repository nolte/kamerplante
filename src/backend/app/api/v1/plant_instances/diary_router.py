"""REQ-013 §4.7 — standalone (plant-centric) diary endpoints.

Mounted under ``/api/v1/t/{tenant_slug}/plant-instances/{key}/diary``, the same
shape as the REQ-034 photo gallery (``/plant-instances/{key}/photos``) so the
frontend consumes both the same way.

**Why these exist only now.** REQ-013 has listed them since v2.0, but only the
six *run-scoped* endpoints were ever built. A plant that is not part of a
planting run therefore had no reachable diary at all — although §1 of REQ-013
grants a standalone instance exactly that. REQ-050 §2.5.1 puts the diary on the
plant-instance detail page, which is where a standalone plant lives, so the gap
had to close here (REQ-050 §9, O-05: "blockierend").

The run-scoped endpoints stay exactly as they are; this is an addition, not a
replacement. Both prefixes drive the *same* service and the same documents — an
entry created here is visible in the run aggregation once the plant joins a run,
because the entry hangs off the plant, never off the run.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.v1.planting_runs.diary_schemas import (
    DiaryEntryCreateRequest,
    DiaryEntryResponse,
    DiaryEntryUpdateRequest,
    diary_entry_response_for_caller,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import get_plant_diary_service, get_plant_instance_service
from app.common.exceptions import NotFoundError
from app.common.openapi_responses import CRUD_RESPONSES
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action
from app.domain.models.plant_diary_entry import PlantDiaryEntry
from app.domain.models.tenant_context import TenantContext
from app.domain.services.plant_diary_service import PlantDiaryService
from app.domain.services.plant_instance_service import PlantInstanceService

router = APIRouter(prefix="/plant-instances/{key}/diary", tags=["plant-diary"], responses=CRUD_RESPONSES)


def _load_entry_in_scope(
    diary_service: PlantDiaryService,
    entry_key: str,
    plant_key: str,
    tenant_key: str,
) -> PlantDiaryEntry:
    """Load an entry, refusing anything outside this tenant *and* this plant.

    Both refusals are ``NotFoundError`` and never a permission error: a
    distinguishable "forbidden" would confirm that the key exists somewhere else
    in the installation (REQ-050 §4.0, AK-12).
    """
    entry = diary_service.get_entry_for_tenant(entry_key, tenant_key)
    if entry.plant_key != plant_key:
        raise NotFoundError("PlantDiaryEntry", entry_key)
    return entry


@router.get("", response_model=list[DiaryEntryResponse])
def list_plant_diary_entries(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """List one plant's diary entries, newest first (paginated).

    The plant is resolved against the caller's tenant first, so the listing can
    never be reached for a foreign plant — the entries hang off the plant, and
    the plant is the tenant anchor.

    Every row carries its own ``can_request_analysis`` (REQ-050 §7.2, AK-18a).
    The verdict depends on the *authorship* of each entry, so a shared garden's
    listing legitimately mixes ``true`` and ``false`` rows for one caller — which
    is why it is evaluated per entry and not once for the page.
    """
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    entries, _total = diary_service.list_entries_for_plant(
        key,
        tenant_key=ctx.tenant_key,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return [diary_entry_response_for_caller(e, diary_service=diary_service, ctx=ctx) for e in entries]


@router.post("", response_model=DiaryEntryResponse, status_code=201)
def create_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    body: DiaryEntryCreateRequest,
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.CREATE)),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Create a diary entry for a plant instance (REQ-050 §2.5.1).

    No ``run_key`` is passed: this path is the one for a plant *without* a run,
    and requiring run membership here would reinstate exactly the gap it closes.

    ``body.photo_refs`` is checked against the attachment catalogue by the
    service before anything is stored (SEC-003).

    ``body.capture_environment`` is popped out of the payload rather than passed
    through: it is an instruction to the *service*, not a field of the entry, and
    the snapshot it governs is resolved server-side (REQ-013 §2.3a). Nothing a
    client sends ever reaches ``entry.environment``.
    """
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    entry = PlantDiaryEntry(
        tenant_key=ctx.tenant_key,
        created_by=ctx.user_key,
        **body.model_dump(exclude={"capture_environment"}),
    )
    created = diary_service.create_entry(
        key,
        entry,
        actor_role=ctx.role,
        capture_environment=body.capture_environment,
    )
    return diary_entry_response_for_caller(created, diary_service=diary_service, ctx=ctx)


@router.get("/{entry_key}", response_model=DiaryEntryResponse)
def get_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(get_current_tenant),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Return a single diary entry of this plant."""
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    entry = _load_entry_in_scope(diary_service, entry_key, key, ctx.tenant_key)
    return diary_entry_response_for_caller(entry, diary_service=diary_service, ctx=ctx)


@router.put("/{entry_key}", response_model=DiaryEntryResponse)
def update_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    body: DiaryEntryUpdateRequest,
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.UPDATE)),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Update a diary entry of this plant.

    The analysis fields are not part of ``DiaryEntryUpdateRequest`` and the
    service refuses them anyway: a state change never travels through the
    generic update (REQ-013 §4.7, REQ-050 §2.2).
    """
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, key, ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = diary_service.update_entry(
        entry_key,
        data,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        actor_role=ctx.role,
    )
    return diary_entry_response_for_caller(updated, diary_service=diary_service, ctx=ctx)


@router.delete("/{entry_key}", status_code=204)
def delete_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.DELETE)),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Delete a diary entry of this plant, along with its analysis result (AK-23)."""
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, key, ctx.tenant_key)
    diary_service.delete_entry(entry_key)


# ── REQ-050 §2.5.1 — marking an entry for AI analysis ────────────────


@router.post("/{entry_key}/request-analysis", response_model=DiaryEntryResponse)
def request_plant_diary_entry_analysis(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.CREATE)),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Mark a diary entry for AI analysis — ``none|completed|failed → requested``.

    Role, consent, authorship and Light-mode handling are decided by
    :meth:`PlantDiaryService.request_analysis`, which is the same function the
    overview uses to compute ``can_request_analysis``. That flag is a display
    aid; this endpoint is the authorisation, and it re-evaluates the rule
    unconditionally (REQ-050 AK-18a).
    """
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, key, ctx.tenant_key)
    updated = diary_service.request_analysis(
        entry_key,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        role=ctx.role,
    )
    return diary_entry_response_for_caller(updated, diary_service=diary_service, ctx=ctx)


@router.delete("/{entry_key}/request-analysis", response_model=DiaryEntryResponse)
def cancel_plant_diary_entry_analysis(
    key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.UPDATE)),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Withdraw the marking — ``requested → none``, only while unclaimed (AK-03)."""
    plant_service.get_plant(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, key, ctx.tenant_key)
    updated = diary_service.cancel_analysis_request(
        entry_key,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        role=ctx.role,
    )
    return diary_entry_response_for_caller(updated, diary_service=diary_service, ctx=ctx)

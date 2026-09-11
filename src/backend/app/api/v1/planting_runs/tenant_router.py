from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.mapping import to_response
from app.api.v1.plant_instances.schemas import ActiveChannelResponse, CultivarSummary, SpeciesSummary
from app.api.v1.planting_runs.diary_schemas import (
    DiaryEntryCreateRequest,
    DiaryEntryResponse,
    DiaryEntryUpdateRequest,
    RunDiaryEntryResponse,
    diary_entry_response_for_caller,
)
from app.api.v1.planting_runs.schemas import (
    AdoptPlantsRequest,
    AdoptPlantsResponse,
    BatchCreatePlantsResponse,
    BatchRemoveRequest,
    BatchRemoveResponse,
    BatchUpdatePhaseDatesRequest,
    BatchUpdatePhaseDatesResponse,
    DetachPlantRequest,
    DetachPlantResponse,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    NutrientPlanAssignRequest,
    NutrientPlanAssignResponse,
    PhaseSummary,
    PlantingRunCreate,
    PlantingRunResponse,
    PlantingRunUpdate,
    PlantInRunResponse,
    RunTransitionRequest,
    RunTransitionResponse,
    WateringScheduleCalendarResponse,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import (
    get_nutrient_plan_service,
    get_plant_diary_service,
    get_plant_instance_service,
    get_planting_run_service,
    get_species_repo,
)
from app.common.enums import PlantingRunStatus
from app.common.exceptions import NotFoundError
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action, ResourceType
from app.domain.interfaces.species_repository import ISpeciesRepository
from app.domain.models.plant_diary_entry import PlantDiaryEntry
from app.domain.models.planting_run import PlantingRun, PlantingRunEntry
from app.domain.models.tenant_context import TenantContext
from app.domain.services.nutrient_plan_service import NutrientPlanService
from app.domain.services.plant_diary_service import PlantDiaryService
from app.domain.services.plant_instance_service import PlantInstanceService
from app.domain.services.planting_run_service import PlantingRunService

router = APIRouter(prefix="/planting-runs", tags=["planting-runs"], responses=NOT_FOUND_RESPONSE)


def _run_response(r: PlantingRun, phase_summary: dict | None = None) -> PlantingRunResponse:
    ps = PhaseSummary(**phase_summary) if phase_summary else None
    return to_response(r, PlantingRunResponse, phase_summary=ps)


def _entry_response(e: PlantingRunEntry) -> EntryResponse:
    return to_response(e, EntryResponse)


@router.get("", response_model=list[PlantingRunResponse])
def list_runs(
    pagination: PaginationParams = Depends(get_pagination),
    status: str | None = Query(default=None, description="Filter by planting-run status."),
    run_type: str | None = Query(default=None, description="Filter by planting-run type."),
    location_key: str | None = Query(default=None, description="Filter by location key."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """List the tenant's planting runs (paginated), optionally filtered."""
    filters: dict[str, str] = {}
    if status:
        filters["status"] = status
    if run_type:
        filters["run_type"] = run_type
    if location_key:
        filters["location_key"] = location_key
    items, _total = service.list_runs(pagination.offset, pagination.limit, filters or None, tenant_key=ctx.tenant_key)
    active_keys = [r.key for r in items if r.key and r.status != PlantingRunStatus.PLANNED]
    summaries = service.get_batch_phase_summaries(active_keys) if active_keys else {}
    return [_run_response(r, summaries.get(r.key)) for r in items]


@router.post("", response_model=PlantingRunResponse, status_code=201)
def create_run(
    body: PlantingRunCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.CREATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Create a planting run for the tenant, optionally with initial entries."""
    run = PlantingRun(**body.model_dump(exclude={"entries"}), tenant_key=ctx.tenant_key)
    entries = None
    if body.entries:
        entries = [PlantingRunEntry(**e.model_dump()) for e in body.entries]
    created = service.create_run(run, entries)
    return _run_response(created)


@router.get("/{key}", response_model=PlantingRunResponse)
def get_run(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Return a single planting run by key, with its phase summary."""
    r = service.get_run(key, tenant_key=ctx.tenant_key)
    ps = service.get_phase_summary(key) if r.status != PlantingRunStatus.PLANNED else None
    return _run_response(r, ps)


@router.put("/{key}", response_model=PlantingRunResponse)
def update_run(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: PlantingRunUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Update a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = service.update_run(key, data)
    return _run_response(updated)


@router.delete("/{key}", status_code=204)
def delete_run(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.DELETE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Delete a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    service.delete_run(key)


@router.get("/{key}/entries", response_model=list[EntryResponse])
def list_entries(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """List a planting run's entries."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    entries = service.list_entries(key)
    return [_entry_response(e) for e in entries]


@router.post("/{key}/entries", response_model=EntryResponse, status_code=201)
def add_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: EntryCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.CREATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Add an entry to a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    entry = PlantingRunEntry(**body.model_dump())
    created = service.add_entry(key, entry)
    return _entry_response(created)


@router.put("/{key}/entries/{entry_key}", response_model=EntryResponse)
def update_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    entry_key: Annotated[str, Path(description="Document key of the planting-run entry.")],
    body: EntryUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Partially update a planting-run entry."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    # Partial update: only fields explicitly sent by the client are applied.
    # ``exclude_unset`` (not ``exclude_none``) keeps an explicit ``null`` for a
    # nullable field distinguishable from "not sent" — the service merges the
    # patch onto the persisted entry and re-validates required fields.
    data = body.model_dump(exclude_unset=True)
    updated = service.update_entry(key, entry_key, data)
    return _entry_response(updated)


@router.delete("/{key}/entries/{entry_key}", status_code=204)
def delete_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    entry_key: Annotated[str, Path(description="Document key of the planting-run entry.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.DELETE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Delete a planting-run entry."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    service.delete_entry(key, entry_key)


@router.post("/{key}/create-plants", response_model=BatchCreatePlantsResponse, status_code=201)
def batch_create_plants(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANT, Action.CREATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Create plant instances in bulk from a planting run's entries."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    result = service.create_plants(key)
    return BatchCreatePlantsResponse(**result)


@router.post("/{key}/adopt-plants", response_model=AdoptPlantsResponse)
def adopt_plants(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: AdoptPlantsRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Attach existing plant instances to a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    result = service.adopt_plants(key, body.plant_keys)
    return AdoptPlantsResponse(**result)


@router.get("/{key}/phase-timeline")
def get_phase_timeline(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    species_repo: ISpeciesRepository = Depends(get_species_repo),
):
    """Return the per-species phase timeline for a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    timelines = service.get_phase_timeline(key)
    for tl in timelines:
        sp = species_repo.get_by_key(tl["species_key"])
        if sp:
            tl["species_name"] = sp.scientific_name
    return timelines


@router.post("/{key}/transition", response_model=RunTransitionResponse)
def transition_run(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: RunTransitionRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Transition all plants of a planting run to a target phase."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    result = service.transition(key, body.target_phase_key, body.target_phase_name)
    return RunTransitionResponse(**result)


@router.patch("/{key}/batch-update-phase-dates", response_model=BatchUpdatePhaseDatesResponse)
def batch_update_phase_dates(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: BatchUpdatePhaseDatesRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Bulk-update the entered/exited dates for a phase across a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    if body.entered_at is None and body.exited_at is None:
        raise HTTPException(status_code=422, detail="At least one of entered_at or exited_at must be provided")
    try:
        result = service.batch_update_phase_dates(key, body.phase_key, body.entered_at, body.exited_at)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return BatchUpdatePhaseDatesResponse(**result)


@router.post("/{key}/batch-remove", response_model=BatchRemoveResponse)
def batch_remove(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: BatchRemoveRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Bulk-remove the plants of a planting run with a shared reason."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    result = service.batch_remove(key, body.reason, body.target_status)
    return BatchRemoveResponse(**result)


@router.get("/{key}/plants", response_model=list[PlantInRunResponse])
def list_plants(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    include_detached: bool = Query(False, description="Include plants previously detached from the run."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    species_repo: ISpeciesRepository = Depends(get_species_repo),
):
    """List the plants belonging to a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    plants = service.get_plants(key, include_detached)

    # Resolve denormalized species/cultivar labels with a per-request cache to
    # avoid N+1 lookups for plants that share a species or cultivar.
    species_cache: dict[str, SpeciesSummary | None] = {}
    cultivar_cache: dict[str, CultivarSummary | None] = {}

    def _species_summary(species_key: str) -> SpeciesSummary | None:
        if not species_key:
            return None
        if species_key not in species_cache:
            sp = species_repo.get_by_key(species_key)
            species_cache[species_key] = (
                SpeciesSummary(scientific_name=sp.scientific_name, common_names=sp.common_names) if sp else None
            )
        return species_cache[species_key]

    def _cultivar_summary(cultivar_key: str | None) -> CultivarSummary | None:
        if not cultivar_key:
            return None
        if cultivar_key not in cultivar_cache:
            cv = species_repo.get_cultivar_by_key(cultivar_key)
            cultivar_cache[cultivar_key] = CultivarSummary(name=cv.name) if cv else None
        return cultivar_cache[cultivar_key]

    return [
        PlantInRunResponse(
            key=p.get("_key", ""),
            instance_id=p.get("instance_id", ""),
            species_key=p.get("species_key", ""),
            cultivar_key=p.get("cultivar_key"),
            plant_name=p.get("plant_name"),
            planted_on=p.get("planted_on", "1970-01-01"),
            removed_on=p.get("removed_on"),
            current_phase=p.get("current_phase", ""),
            species=_species_summary(p.get("species_key", "")),
            cultivar=_cultivar_summary(p.get("cultivar_key")),
            detached_at=p.get("_edge_detached_at"),
            detach_reason=p.get("_edge_detach_reason"),
        )
        for p in plants
    ]


@router.post("/{key}/plants/{plant_key}/detach", response_model=DetachPlantResponse)
def detach_plant(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance to detach.")],
    body: DetachPlantRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Detach a plant instance from a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    result = service.detach_plant(key, plant_key, body.reason)
    return DetachPlantResponse(**result)


@router.post("/{key}/nutrient-plan", response_model=NutrientPlanAssignResponse, status_code=201)
def assign_nutrient_plan(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    body: NutrientPlanAssignRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Assign a nutrient plan to a planting run."""
    result = service.assign_nutrient_plan(key, body.plan_key, body.assigned_by, tenant_key=ctx.tenant_key)
    return NutrientPlanAssignResponse(**result)


@router.get("/{key}/nutrient-plan")
def get_nutrient_plan(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Return the nutrient plan assigned to a planting run."""
    plan = service.get_nutrient_plan(key, tenant_key=ctx.tenant_key)
    if plan is None:
        return {"plan": None}
    return {"plan": plan}


@router.delete("/{key}/nutrient-plan", status_code=204)
def remove_nutrient_plan(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANTING_RUN, Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Remove the nutrient plan assigned to a planting run."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    service.remove_nutrient_plan(key)


@router.get("/{key}/active-channels", response_model=list[ActiveChannelResponse])
def get_active_channels(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    current_week: int | None = Query(
        default=None, ge=1, description="1-based week to evaluate; defaults to the run's elapsed week."
    ),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    plan_service: NutrientPlanService = Depends(get_nutrient_plan_service),
):
    """List the active nutrient channels for a planting run in the given week."""
    run = service.get_run(key, tenant_key=ctx.tenant_key)
    plan_key = service._repo.get_run_nutrient_plan_key(key)
    if plan_key is None:
        return []
    summary = service.get_phase_summary(key)
    dominant_phase = summary.get("dominant_phase")
    if not dominant_phase:
        return []
    if current_week is None:
        from datetime import datetime

        from app.common.datetimes import today_utc

        started = run.started_at
        if started is None:
            current_week = 1
        else:
            if isinstance(started, datetime):
                started_date = started.date() if started.tzinfo else started.replace(tzinfo=UTC).date()
            else:
                started_date = started
            # ``started_date`` was just normalized to UTC two lines up; the
            # subtrahend has to come off the same clock or the run would jump a
            # week early/late for part of every day (§12a).
            delta_days = (today_utc() - started_date).days
            current_week = max(1, delta_days // 7 + 1)
    channels = plan_service.get_active_channels_for_plan(
        plan_key, dominant_phase, current_week, tenant_key=ctx.tenant_key
    )
    return channels


@router.get("/{key}/watering-schedule", response_model=WateringScheduleCalendarResponse)
def get_watering_schedule(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    days_ahead: int = Query(14, ge=1, le=90, description="Number of days ahead to project the schedule."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
):
    """Return the projected watering schedule for a planting run.

    The service verifies the run against ``tenant_key`` itself and forwards the
    tenant to the "last watered" probe (#927), so the redundant pre-check that
    used to stand here is gone.
    """
    result = service.get_watering_schedule(key, days_ahead, tenant_key=ctx.tenant_key)
    return WateringScheduleCalendarResponse(**result)


# ── Plant diary endpoints ────────────────────────────────────────────


def _diary_response(
    entry: PlantDiaryEntry,
    diary_service: PlantDiaryService,
    ctx: TenantContext,
) -> DiaryEntryResponse:
    """Project a diary entry for the caller of this request.

    Thin on purpose: the projection *and* the §7.2 verdict live in
    :func:`diary_entry_response_for_caller`, shared with the standalone
    plant-instance router. An entry read through ``/planting-runs/…`` and the
    same entry read through ``/plant-instances/…`` must answer identically —
    including the corrected analysis state and the ``can_request_analysis``
    flag.
    """
    return diary_entry_response_for_caller(entry, diary_service=diary_service, ctx=ctx)


def _load_entry_in_scope(
    diary_service: PlantDiaryService,
    entry_key: str,
    plant_key: str,
    tenant_key: str,
) -> PlantDiaryEntry:
    """Load a diary entry, refusing anything outside this tenant *and* this plant.

    The run-scoped diary endpoints used to verify only the **run** against the
    caller's tenant and then load the entry by bare key
    (``diary_service.get_entry(entry_key)``). The entry key was never checked, so
    any member of any tenant could read, update and delete a foreign tenant's
    diary entry by pairing a run of their own with a key they guessed or learnt —
    the run in the URL had nothing to do with the document that was returned.

    Both halves are now checked here. The tenant half is
    :meth:`PlantDiaryService.get_entry_for_tenant`, which answers a foreign entry
    with ``NotFoundError`` and never with a permission error: telling the two
    apart would turn the endpoint into an oracle for the existence of other
    tenants' records (REQ-050 §4.0, AK-12). The plant half is the same answer for
    the same reason, one tenant further in — an entry of *another plant* is not
    addressable through this URL, and saying "forbidden" would confirm the key.
    """
    entry = diary_service.get_entry_for_tenant(entry_key, tenant_key)
    if entry.plant_key != plant_key:
        raise NotFoundError("PlantDiaryEntry", entry_key)
    return entry


@router.get(
    "/{key}/plants/{plant_key}/diary",
    response_model=list[DiaryEntryResponse],
)
def list_plant_diary_entries(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """List a plant instance's diary entries within a planting run (paginated).

    **Both** keys in the URL are checked, which they were not (SEC-002). Only
    the run used to be verified against the caller's tenant; ``plant_key`` went
    straight into the query, and the query itself had no tenant predicate — so
    an own run plus a foreign plant returned the other tenant's entries in full.

    The plant is resolved first and answers ``NotFoundError`` (404) for a
    foreign one, never 403 (AK-12): a distinguishable "forbidden" would confirm
    that the plant exists somewhere else in the installation. The listing read
    is tenant-scoped as well — the two guards are not redundant, they close
    different halves: the plant check refuses the *address*, the query filter
    refuses a mis-parented *document* that happens to hang off an own plant.
    """
    service.get_run(key, tenant_key=ctx.tenant_key)
    plant_service.get_plant(plant_key, tenant_key=ctx.tenant_key)
    entries, _total = diary_service.list_entries_for_plant(
        plant_key,
        tenant_key=ctx.tenant_key,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return [_diary_response(e, diary_service, ctx) for e in entries]


@router.post(
    "/{key}/plants/{plant_key}/diary",
    response_model=DiaryEntryResponse,
    status_code=201,
)
def create_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    body: DiaryEntryCreateRequest,
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.CREATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Create a diary entry for a plant instance within a planting run.

    ``body.photo_refs`` is checked against the attachment catalogue by the
    service before anything is stored (SEC-003) — it is caller-supplied input
    that decides which images REQ-050 §4.4 later hands to an external model.

    The environment snapshot (REQ-013 §2.3a) is captured here exactly as on the
    standalone prefix — the entry hangs off the plant either way, so an entry
    created through a run must not be poorer evidence than the same entry created
    from the plant page.
    """
    service.get_run(key, tenant_key=ctx.tenant_key)
    entry = PlantDiaryEntry(
        tenant_key=ctx.tenant_key,
        created_by=ctx.user_key,
        **body.model_dump(exclude={"capture_environment"}),
    )
    created = diary_service.create_entry(
        plant_key,
        entry,
        run_key=key,
        actor_role=ctx.role,
        capture_environment=body.capture_environment,
    )
    return _diary_response(created, diary_service, ctx)


@router.get(
    "/{key}/plants/{plant_key}/diary/{entry_key}",
    response_model=DiaryEntryResponse,
)
def get_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Return a single plant-diary entry by key."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    entry = _load_entry_in_scope(diary_service, entry_key, plant_key, ctx.tenant_key)
    return _diary_response(entry, diary_service, ctx)


@router.put(
    "/{key}/plants/{plant_key}/diary/{entry_key}",
    response_model=DiaryEntryResponse,
)
def update_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    body: DiaryEntryUpdateRequest,
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Update a plant-diary entry."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, plant_key, ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = diary_service.update_entry(
        entry_key,
        data,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        actor_role=ctx.role,
    )
    return _diary_response(updated, diary_service, ctx)


@router.delete(
    "/{key}/plants/{plant_key}/diary/{entry_key}",
    status_code=204,
)
def delete_plant_diary_entry(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.DELETE)),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Delete a plant-diary entry."""
    service.get_run(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, plant_key, ctx.tenant_key)
    diary_service.delete_entry(entry_key)


# ── REQ-050 §2.5.1 — marking an entry for AI analysis ────────────────


@router.post(
    "/{key}/plants/{plant_key}/diary/{entry_key}/request-analysis",
    response_model=DiaryEntryResponse,
)
def request_run_diary_entry_analysis(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.CREATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Mark a diary entry for AI analysis — ``none|completed|failed → requested``.

    The whole rule (role, consent, authorship, Light mode) lives in
    :meth:`PlantDiaryService.request_analysis` and is **not** re-implemented
    here: the overview's ``can_request_analysis`` flag is derived from the same
    function, and two copies would disagree at the next change. A viewer gets
    403, a non-author grower gets 403, and an entry an agent already holds gets
    409 ``conflict.invalid_state`` (REQ-050 §6, §7.2, §7.5, AK-01/02/03).
    """
    service.get_run(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, plant_key, ctx.tenant_key)
    updated = diary_service.request_analysis(
        entry_key,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        role=ctx.role,
    )
    return _diary_response(updated, diary_service, ctx)


@router.delete(
    "/{key}/plants/{plant_key}/diary/{entry_key}/request-analysis",
    response_model=DiaryEntryResponse,
)
def cancel_run_diary_entry_analysis(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    entry_key: Annotated[str, Path(description="Document key of the diary entry.")],
    ctx: TenantContext = Depends(require_permission("diary-entry", Action.UPDATE)),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """Withdraw the marking — ``requested → none``, only while unclaimed (AK-03).

    Returns the entry rather than 204: the caller needs to see the state it
    actually ended up in, and an entry an agent claimed between rendering and
    clicking answers 409 instead of silently doing nothing.
    """
    service.get_run(key, tenant_key=ctx.tenant_key)
    _load_entry_in_scope(diary_service, entry_key, plant_key, ctx.tenant_key)
    updated = diary_service.cancel_analysis_request(
        entry_key,
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        role=ctx.role,
    )
    return _diary_response(updated, diary_service, ctx)


@router.get(
    "/{key}/diary",
    response_model=list[RunDiaryEntryResponse],
)
def list_run_diary_entries(
    key: Annotated[str, Path(description="Document key of the planting run.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: PlantingRunService = Depends(get_planting_run_service),
    diary_service: PlantDiaryService = Depends(get_plant_diary_service),
):
    """List all diary entries across the plants of a planting run (paginated).

    **This used to be a second, hand-written copy of the projection.** The rows
    arrive from the repository as raw dicts (the aggregation carries plant
    labels alongside each entry), and the response was assembled here field by
    field. That is how the two halves of REQ-050 §5 got lost on this path: the
    lease correction was not applied, and a ``can_request_analysis`` added to
    the schema would have been filled with one blanket value for every row of
    the page — or not at all.

    The dict is therefore parsed back into the domain model and handed to the
    same :func:`_diary_response` every other diary endpoint uses. The parse is
    lossless rather than lenient: the repository already validates each document
    through ``PlantDiaryEntry`` and dumps it by alias
    (``plant_diary_repository.get_by_run``), so what arrives here is a
    round-trip of the model, not a raw ArangoDB document.
    """
    service.get_run(key, tenant_key=ctx.tenant_key)
    entries, _total = diary_service.list_entries_for_run(
        key,
        tenant_key=ctx.tenant_key,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    results = []
    for item in entries:
        diary_data = item.get("diary_entry") or {}
        if not diary_data:
            # A dangling edge: the entry document is gone while its edge to the
            # plant survived. Such a row is skipped instead of rendered from
            # defaults — a placeholder entry with an empty text and the type
            # "note" is not an entry anyone wrote, and the previous code raised
            # ``AttributeError`` (500) on it anyway.
            continue
        results.append(
            RunDiaryEntryResponse(
                plant_key=item.get("plant_key", ""),
                plant_id=item.get("plant_id", ""),
                plant_name=item.get("plant_name"),
                diary_entry=_diary_response(PlantDiaryEntry(**diary_data), diary_service, ctx),
            )
        )
    return results

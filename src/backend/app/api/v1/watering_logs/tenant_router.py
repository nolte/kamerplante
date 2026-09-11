from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.mapping import to_response
from app.api.v1.watering_logs.schemas import (
    ResolvedFertilizer,
    ResolvedPlant,
    RunoffAnalysisResponse,
    WateringConfirmRequest,
    WateringConfirmResponse,
    WateringLogCreate,
    WateringLogResponse,
    WateringLogUpdate,
    WateringLogWithWarnings,
    WateringQuickConfirmRequest,
    WateringStatsResponse,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import get_watering_log_service
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action
from app.domain.models.tenant_context import TenantContext
from app.domain.models.watering_log import WateringLog
from app.domain.services.watering_log_service import WateringLogService

router = APIRouter(tags=["watering-logs"], responses=NOT_FOUND_RESPONSE)


def _log_response(
    log: WateringLog,
    plant_name_map: dict[str, str] | None = None,
    fert_name_map: dict[str, str] | None = None,
) -> WateringLogResponse:
    resolved = []
    if plant_name_map:
        for pk in log.plant_keys:
            name = plant_name_map.get(pk, pk)
            resolved.append(ResolvedPlant(key=pk, name=name))
    resolved_ferts = []
    if fert_name_map:
        for fu in log.fertilizers_used:
            name = fert_name_map.get(fu.fertilizer_key, fu.fertilizer_key)
            resolved_ferts.append(ResolvedFertilizer(key=fu.fertilizer_key, name=name, ml_per_liter=fu.ml_per_liter))
    return to_response(
        log,
        WateringLogResponse,
        resolved_plants=resolved,
        resolved_fertilizers=resolved_ferts,
    )


@router.post("/watering-logs", response_model=WateringLogWithWarnings, status_code=201)
def create_log(
    body: WateringLogCreate,
    ctx: TenantContext = Depends(require_permission("watering-log", Action.CREATE)),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Create a watering log and return it with resolved names and warnings."""
    # ``WateringLogCreate`` already enforces the domain's cross-field rules, so this
    # construction can no longer raise on caller input. It stays unguarded on
    # purpose: a ``ValidationError`` from here would now mean *we* built the model
    # wrongly, and that is a genuine 500 which must reach error tracking (#970).
    log = WateringLog(**body.model_dump(), tenant_key=ctx.tenant_key)
    result = service.create_log(log)
    created = result["log"]
    fert_keys = list({fu.fertilizer_key for fu in created.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(fert_keys) if fert_keys else {}
    plant_map = service.resolve_plant_names(created.plant_keys, tenant_key=ctx.tenant_key) if created.plant_keys else {}
    return WateringLogWithWarnings(log=_log_response(created, plant_map, fert_map), warnings=result["warnings"])


@router.get("/watering-logs", response_model=list[WateringLogResponse])
def list_logs(
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """List the tenant's watering logs (paginated)."""
    items, _total = service.list_logs(pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    all_plant_keys = list({pk for log in items for pk in log.plant_keys})
    name_map = service.resolve_plant_names(all_plant_keys, tenant_key=ctx.tenant_key) if all_plant_keys else {}
    all_fert_keys = list({fu.fertilizer_key for log in items for fu in log.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(all_fert_keys) if all_fert_keys else {}
    return [_log_response(log, name_map, fert_map) for log in items]


@router.get("/watering-logs/{key}", response_model=WateringLogResponse)
def get_log(
    key: Annotated[str, Path(description="Document key of the watering log.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Return a single watering log by key with resolved names."""
    log = service.get_log(key, tenant_key=ctx.tenant_key)
    name_map = service.resolve_plant_names(log.plant_keys, tenant_key=ctx.tenant_key) if log.plant_keys else {}
    fert_keys = list({fu.fertilizer_key for fu in log.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(fert_keys) if fert_keys else {}
    return _log_response(log, name_map, fert_map)


@router.put("/watering-logs/{key}", response_model=WateringLogResponse)
def update_log(
    key: Annotated[str, Path(description="Document key of the watering log.")],
    body: WateringLogUpdate,
    ctx: TenantContext = Depends(require_permission("watering-log", Action.UPDATE)),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Update a watering log."""
    service.get_log(key, tenant_key=ctx.tenant_key)
    updated = service.update_log(key, body.model_dump(exclude_unset=True))
    name_map = service.resolve_plant_names(updated.plant_keys, tenant_key=ctx.tenant_key) if updated.plant_keys else {}
    fert_keys = list({fu.fertilizer_key for fu in updated.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(fert_keys) if fert_keys else {}
    return _log_response(updated, name_map, fert_map)


@router.delete("/watering-logs/{key}", status_code=204)
def delete_log(
    key: Annotated[str, Path(description="Document key of the watering log.")],
    ctx: TenantContext = Depends(require_permission("watering-log", Action.DELETE)),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Delete a watering log."""
    service.get_log(key, tenant_key=ctx.tenant_key)
    service.delete_log(key)


@router.get(
    "/watering-logs/{key}/runoff",
    response_model=RunoffAnalysisResponse,
    response_model_exclude_unset=True,
)
def get_runoff_analysis(
    key: Annotated[str, Path(description="Document key of the watering log.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Analyse a watering log's drain-to-waste runoff (or report incomplete data)."""
    service.get_log(key, tenant_key=ctx.tenant_key)
    return service.analyze_runoff(key)


@router.get("/watering-logs/plant/{plant_key}", response_model=list[WateringLogResponse])
def get_plant_logs(
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """List a plant instance's watering logs (paginated)."""
    logs = service.get_by_plant(plant_key, pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    all_pks = list({pk for log in logs for pk in log.plant_keys})
    name_map = service.resolve_plant_names(all_pks, tenant_key=ctx.tenant_key) if all_pks else {}
    all_fks = list({fu.fertilizer_key for log in logs for fu in log.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(all_fks) if all_fks else {}
    return [_log_response(log, name_map, fert_map) for log in logs]


@router.get("/slots/{slot_key}/watering-logs", response_model=list[WateringLogResponse])
def get_slot_logs(
    slot_key: Annotated[str, Path(description="Document key of the slot.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """List a slot's watering logs (paginated).

    A ``slot_key`` belonging to another tenant yields an empty list (#927).
    """
    logs = service.get_by_slot(slot_key, pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    all_pks = list({pk for log in logs for pk in log.plant_keys})
    name_map = service.resolve_plant_names(all_pks, tenant_key=ctx.tenant_key) if all_pks else {}
    all_fks = list({fu.fertilizer_key for log in logs for fu in log.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(all_fks) if all_fks else {}
    return [_log_response(log, name_map, fert_map) for log in logs]


@router.get("/locations/{location_key}/watering-logs", response_model=list[WateringLogResponse])
def get_location_logs(
    location_key: Annotated[str, Path(description="Document key of the location.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """List a location's watering logs (paginated).

    A ``location_key`` belonging to another tenant yields an empty list (#927).
    """
    logs = service.get_by_location(location_key, pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    all_pks = list({pk for log in logs for pk in log.plant_keys})
    name_map = service.resolve_plant_names(all_pks, tenant_key=ctx.tenant_key) if all_pks else {}
    all_fks = list({fu.fertilizer_key for log in logs for fu in log.fertilizers_used})
    fert_map = service.resolve_fertilizer_names(all_fks) if all_fks else {}
    return [_log_response(log, name_map, fert_map) for log in logs]


@router.get("/locations/{location_key}/watering-stats", response_model=WateringStatsResponse)
def get_location_watering_stats(
    location_key: Annotated[str, Path(description="Document key of the location.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Return aggregated watering statistics for a location.

    A ``location_key`` belonging to another tenant reports zeroes (#927).
    """
    stats = service.get_stats(location_key, tenant_key=ctx.tenant_key)
    return WateringStatsResponse(**stats)


@router.post("/watering-logs/confirm", response_model=WateringConfirmResponse, status_code=201)
def confirm_watering(
    body: WateringConfirmRequest,
    ctx: TenantContext = Depends(require_permission("watering-log", Action.UPDATE)),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Confirm a scheduled watering task, creating the resulting log."""
    result = service.confirm_watering(
        run_key=body.run_key,
        task_key=body.task_key,
        measured_ec=body.measured_ec,
        measured_ph=body.measured_ph,
        volume_liters=body.volume_liters,
        overrides=body.overrides.model_dump() if body.overrides else None,
        tenant_key=ctx.tenant_key,
    )
    return WateringConfirmResponse(**result)


@router.post("/watering-logs/quick-confirm", response_model=WateringConfirmResponse, status_code=201)
def quick_confirm_watering(
    body: WateringQuickConfirmRequest,
    ctx: TenantContext = Depends(require_permission("watering-log", Action.UPDATE)),
    service: WateringLogService = Depends(get_watering_log_service),
):
    """Quick-confirm a scheduled watering task with default values."""
    result = service.quick_confirm_watering(body.run_key, body.task_key, tenant_key=ctx.tenant_key)
    return WateringConfirmResponse(**result)

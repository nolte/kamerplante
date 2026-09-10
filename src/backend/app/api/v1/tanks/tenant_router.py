from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.mapping import to_response
from app.api.v1.tanks.schemas import (
    ActiveNutrientPlanResponse,
    ActivePlanFertilizerInfo,
    AlertResponse,
    DueMaintenanceResponse,
    EcDilutionRequest,
    EcDilutionResponse,
    FeedsFromLinkResponse,
    FeedsFromRequest,
    FillEventResultResponse,
    HAEntitySuggestion,
    LiveStateResponse,
    MaintenanceLogCreate,
    MaintenanceLogResponse,
    MaintenanceScheduleCreate,
    MaintenanceScheduleResponse,
    MaintenanceScheduleUpdate,
    SensorCreate,
    SensorResponse,
    SensorUpdate,
    TankCreate,
    TankFillEventCreate,
    TankFillEventResponse,
    TankFillEventStatsResponse,
    TankResponse,
    TankStateCreate,
    TankStateResponse,
    TankUpdate,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import get_sensor_service, get_tank_service
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action, ResourceType
from app.domain.engines.water_mix_engine import WaterMixCalculator
from app.domain.models.sensor import Sensor
from app.domain.models.tank import (
    FertilizerSnapshot,
    MaintenanceLog,
    MaintenanceSchedule,
    Tank,
    TankFillEvent,
    TankState,
)
from app.domain.models.tenant_context import TenantContext
from app.domain.services.sensor_service import SensorService
from app.domain.services.tank_service import TankService

router = APIRouter(prefix="/tanks", tags=["tanks"], responses=NOT_FOUND_RESPONSE)


def _tank_response(t: Tank) -> TankResponse:
    return to_response(t, TankResponse)


def _fill_event_response(e: TankFillEvent) -> TankFillEventResponse:
    return to_response(e, TankFillEventResponse)


@router.get("/maintenance/due", response_model=list[DueMaintenanceResponse])
def get_all_due_maintenances(
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List all due tank maintenances across the tenant."""
    dues = service.get_all_due_maintenances(tenant_key=ctx.tenant_key)
    return [DueMaintenanceResponse(**d) for d in dues]


@router.get("", response_model=list[TankResponse])
def list_tanks(
    pagination: PaginationParams = Depends(get_pagination),
    tank_type: str | None = Query(default=None, description="Filter by tank type."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List the tenant's tanks (paginated), optionally filtered by type."""
    filters: dict[str, str] = {}
    if tank_type:
        filters["tank_type"] = tank_type
    items, _total = service.list_tanks(pagination.offset, pagination.limit, filters or None, tenant_key=ctx.tenant_key)
    return [_tank_response(t) for t in items]


@router.post("", response_model=TankResponse, status_code=201)
def create_tank(
    body: TankCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.CREATE)),
    service: TankService = Depends(get_tank_service),
):
    """Create a tank for the tenant."""
    tank = Tank(**body.model_dump(), tenant_key=ctx.tenant_key)
    created = service.create_tank(tank)
    return _tank_response(created)


@router.get("/ha-entities", response_model=list[HAEntitySuggestion])
def list_ha_entities(
    ctx: TenantContext = Depends(get_current_tenant),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """List Home Assistant entities suggested for tank sensors."""
    return sensor_service.get_ha_entities()


@router.get("/{key}", response_model=TankResponse)
def get_tank(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """Return a single tank by key."""
    t = service.get_tank(key, tenant_key=ctx.tenant_key)
    return _tank_response(t)


@router.put("/{key}", response_model=TankResponse)
def update_tank(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: TankUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.UPDATE)),
    service: TankService = Depends(get_tank_service),
):
    """Update a tank's configuration."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = service.update_tank(key, data)
    return _tank_response(updated)


@router.delete("/{key}", status_code=204)
def delete_tank(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.DELETE)),
    service: TankService = Depends(get_tank_service),
):
    """Delete a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    service.delete_tank(key)


@router.post("/{key}/states", response_model=TankStateResponse, status_code=201)
def record_state(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: TankStateCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.CREATE)),
    service: TankService = Depends(get_tank_service),
):
    """Record a measured state snapshot for a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    state = TankState(**body.model_dump())
    created = service.record_state(key, state)
    return to_response(created, TankStateResponse)


@router.get("/{key}/states", response_model=list[TankStateResponse])
def get_states(
    key: Annotated[str, Path(description="Document key of the tank.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List a tank's recorded state snapshots (paginated)."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    states = service.get_states(key, pagination.offset, pagination.limit)
    return [to_response(s, TankStateResponse) for s in states]


@router.get("/{key}/states/latest", response_model=TankStateResponse | None)
def get_latest_state(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """Return a tank's most recent state snapshot, or null if none exists."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    state = service.get_latest_state(key)
    if state is None:
        return None
    return to_response(state, TankStateResponse)


@router.get("/{key}/alerts", response_model=list[AlertResponse])
def get_alerts(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List the active alerts for a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    alerts = service.get_alerts(key)
    return [AlertResponse(**a) for a in alerts]


@router.post("/{key}/maintenance", response_model=MaintenanceLogResponse, status_code=201)
def log_maintenance(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: MaintenanceLogCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.CREATE)),
    service: TankService = Depends(get_tank_service),
):
    """Log a completed maintenance action for a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    log = MaintenanceLog(**body.model_dump())
    created = service.log_maintenance(key, log)
    return to_response(created, MaintenanceLogResponse)


@router.get("/{key}/maintenance", response_model=list[MaintenanceLogResponse])
def get_maintenance_history(
    key: Annotated[str, Path(description="Document key of the tank.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List a tank's maintenance history (paginated)."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    logs = service.get_maintenance_history(key, pagination.offset, pagination.limit)
    return [to_response(log, MaintenanceLogResponse) for log in logs]


@router.get("/{key}/maintenance/due", response_model=list[DueMaintenanceResponse])
def get_due_maintenances(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List the due maintenances for a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    dues = service.get_due_maintenances(key)
    return [DueMaintenanceResponse(**d) for d in dues]


@router.post("/{key}/schedules", response_model=MaintenanceScheduleResponse, status_code=201)
def create_schedule(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: MaintenanceScheduleCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.CREATE)),
    service: TankService = Depends(get_tank_service),
):
    """Create a maintenance schedule for a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    schedule = MaintenanceSchedule(**body.model_dump())
    created = service.create_schedule(key, schedule)
    return to_response(created, MaintenanceScheduleResponse)


@router.get("/{key}/schedules", response_model=list[MaintenanceScheduleResponse])
def get_schedules(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List a tank's maintenance schedules."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    schedules = service.get_schedules(key)
    return [to_response(s, MaintenanceScheduleResponse) for s in schedules]


@router.put("/{key}/schedules/{skey}", response_model=MaintenanceScheduleResponse)
def update_schedule(
    key: Annotated[str, Path(description="Document key of the tank.")],
    skey: Annotated[str, Path(description="Document key of the maintenance schedule.")],
    body: MaintenanceScheduleUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.UPDATE)),
    service: TankService = Depends(get_tank_service),
):
    """Update a tank's maintenance schedule."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = service.update_schedule(skey, data)
    return to_response(updated, MaintenanceScheduleResponse)


@router.delete("/{key}/schedules/{skey}", status_code=204)
def delete_schedule(
    key: Annotated[str, Path(description="Document key of the tank.")],
    skey: Annotated[str, Path(description="Document key of the maintenance schedule.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.DELETE)),
    service: TankService = Depends(get_tank_service),
):
    """Delete a tank's maintenance schedule."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    service.delete_schedule(skey)


@router.post("/{key}/fills", response_model=FillEventResultResponse, status_code=201)
def record_fill_event(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: TankFillEventCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.CREATE)),
    service: TankService = Depends(get_tank_service),
):
    """Record a tank fill event and return the resulting state and warnings."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    ferts = [FertilizerSnapshot(**f.model_dump()) for f in body.fertilizers_used]
    event = TankFillEvent(**body.model_dump(exclude={"fertilizers_used"}), fertilizers_used=ferts)
    result = service.record_fill_event(key, event)
    return FillEventResultResponse(
        fill_event=_fill_event_response(result["fill_event"]),
        tank_state=(to_response(result["tank_state"], TankStateResponse) if result["tank_state"] else None),
        warnings=result["warnings"],
        water_defaults_source=result["water_defaults_source"],
    )


@router.get("/{key}/fills", response_model=list[TankFillEventResponse])
def get_fill_events(
    key: Annotated[str, Path(description="Document key of the tank.")],
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List a tank's fill events (paginated)."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    events = service.get_fill_history(key, pagination.offset, pagination.limit)
    return [_fill_event_response(e) for e in events]


@router.get("/{key}/fills/latest", response_model=TankFillEventResponse | None)
def get_latest_fill(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """Return a tank's most recent fill event, or null if none exists."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    event = service.get_latest_fill(key)
    if event is None:
        return None
    return _fill_event_response(event)


@router.get("/{key}/fills/stats", response_model=TankFillEventStatsResponse)
def get_fill_stats(
    key: Annotated[str, Path(description="Document key of the tank.")],
    start_date: str | None = Query(default=None, description="Inclusive start date (ISO 8601) of the stats window."),
    end_date: str | None = Query(default=None, description="Inclusive end date (ISO 8601) of the stats window."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """Return aggregated fill-event statistics for a tank over a date window."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    stats = service.get_fill_stats(key, start_date, end_date)
    return TankFillEventStatsResponse(**stats)


@router.get("/{key}/active-nutrient-plans", response_model=list[ActiveNutrientPlanResponse])
def get_active_nutrient_plans(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """List the nutrient plans currently fed by a tank."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    results = service.get_active_nutrient_plans(key)
    return [
        ActiveNutrientPlanResponse(
            run_key=r["run_key"],
            run_name=r["run_name"],
            run_status=r["run_status"],
            plan_key=r["plan_key"],
            plan_name=r["plan_name"],
            current_phase=r.get("current_phase"),
            plant_count=r.get("plant_count", 0),
            current_phase_entry=r.get("current_phase_entry"),
            all_phase_entries=r.get("all_phase_entries", []),
            fertilizers=[ActivePlanFertilizerInfo(**f) for f in r.get("fertilizers", [])],
            watering_schedule=r.get("watering_schedule"),
            water_mix_ratio_ro_percent=r.get("water_mix_ratio_ro_percent"),
        )
        for r in results
    ]


@router.post("/{key}/feeds-from", response_model=FeedsFromLinkResponse, status_code=201)
def link_feeds_from(
    key: Annotated[str, Path(description="Document key of the tank being fed.")],
    body: FeedsFromRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TANK, Action.UPDATE)),
    service: TankService = Depends(get_tank_service),
):
    """Link a tank to the source tank it is fed from."""
    service.get_tank(key, tenant_key=ctx.tenant_key)
    service.link_feeds_from(key, body.source_tank_key)
    return {"status": "linked"}


@router.get("/{key}/states/live", response_model=LiveStateResponse)
def get_live_state(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    tank_service: TankService = Depends(get_tank_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Return a tank's live sensor readings."""
    tank_service.get_tank(key, tenant_key=ctx.tenant_key)
    result = sensor_service.get_live_state(key)
    return LiveStateResponse(**result)


@router.get("/{key}/sensors", response_model=list[SensorResponse])
def get_sensors(
    key: Annotated[str, Path(description="Document key of the tank.")],
    ctx: TenantContext = Depends(get_current_tenant),
    tank_service: TankService = Depends(get_tank_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """List the sensors attached to a tank."""
    tank_service.get_tank(key, tenant_key=ctx.tenant_key)
    sensors = sensor_service.get_sensors_for_tank(key)
    return [to_response(s, SensorResponse) for s in sensors]


@router.post("/{key}/sensors", response_model=SensorResponse, status_code=201)
def create_sensor(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: SensorCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.CREATE)),
    tank_service: TankService = Depends(get_tank_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Attach a sensor to a tank."""
    tank_service.get_tank(key, tenant_key=ctx.tenant_key)
    sensor = Sensor(**body.model_dump(exclude={"tank_key"}), tank_key=key)
    created = sensor_service.create_sensor(sensor)
    return to_response(created, SensorResponse)


@router.put("/{key}/sensors/{sensor_key}", response_model=SensorResponse)
def update_sensor(
    key: Annotated[str, Path(description="Document key of the tank.")],
    sensor_key: Annotated[str, Path(description="Document key of the sensor.")],
    body: SensorUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.UPDATE)),
    tank_service: TankService = Depends(get_tank_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Update a sensor attached to a tank (REQ-005 §2, #1339).

    Scoped by the tank on purpose: a sensor carries no ``tenant_key``, so the
    tank verified here *is* the tenant anchor, and the service refuses a sensor
    that hangs off anything else.
    """
    tank_service.get_tank(key, tenant_key=ctx.tenant_key)
    updated = sensor_service.update_sensor(
        sensor_key,
        body.model_dump(exclude_none=True),
        parent_field="tank_key",
        parent_key=key,
    )
    return to_response(updated, SensorResponse)


@router.delete("/{key}/sensors/{sensor_key}", status_code=204)
def delete_sensor(
    key: Annotated[str, Path(description="Document key of the tank.")],
    sensor_key: Annotated[str, Path(description="Document key of the sensor.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.DELETE)),
    tank_service: TankService = Depends(get_tank_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Delete a sensor of a tank, with its edges (REQ-005 §2, #1339)."""
    tank_service.get_tank(key, tenant_key=ctx.tenant_key)
    sensor_service.delete_sensor(sensor_key, parent_field="tank_key", parent_key=key)


@router.post("/{key}/ec-dilution", response_model=EcDilutionResponse)
def calculate_ec_dilution(
    key: Annotated[str, Path(description="Document key of the tank.")],
    body: EcDilutionRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: TankService = Depends(get_tank_service),
):
    """Calculate the RO water needed to dilute a tank to a target EC."""
    tank = service.get_tank(key, tenant_key=ctx.tenant_key)
    volume = body.current_volume_liters if body.current_volume_liters is not None else tank.volume_liters
    calculator = WaterMixCalculator()
    result = calculator.calculate_ec_dilution(
        current_volume_liters=volume,
        current_ec_ms=body.current_ec_ms,
        target_ec_ms=body.target_ec_ms,
        ro_ec_ms=body.ro_ec_ms,
    )
    return EcDilutionResponse(
        **result.model_dump(),
        current_volume_liters=volume,
        current_ec_ms=body.current_ec_ms,
        target_ec_ms=body.target_ec_ms,
        ro_ec_ms=body.ro_ec_ms,
    )

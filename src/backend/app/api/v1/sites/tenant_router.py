from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.mapping import to_response
from app.api.v1.hardiness_zones.schemas import HardinessZoneResponse, SiteHardinessResponse
from app.api.v1.locations.schemas import LocationTreeNode
from app.api.v1.sites.schemas import SiteCreate, SiteResponse, WaterSourceWarningSchema
from app.api.v1.tanks.schemas import LiveStateResponse, SensorCreate, SensorResponse, SensorUpdate
from app.common.auth import get_current_tenant, require_permission, require_tenant_role
from app.common.dependencies import (
    get_hardiness_zone_service,
    get_plant_instance_service,
    get_sensor_service,
    get_site_service,
    get_tank_service,
)
from app.common.enums import TenantRole
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action, ResourceType
from app.domain.models.hardiness_zone import HardinessZone
from app.domain.models.sensor import Sensor
from app.domain.models.site import Location, Site
from app.domain.models.tenant_context import TenantContext
from app.domain.services.hardiness_zone_service import HardinessZoneService
from app.domain.services.plant_instance_service import PlantInstanceService
from app.domain.services.sensor_service import SensorService
from app.domain.services.site_service import SiteService
from app.domain.services.tank_service import TankService

router = APIRouter(prefix="/sites", tags=["sites"], responses=NOT_FOUND_RESPONSE)


def _site_response(site: Site, service: SiteService) -> SiteResponse:
    warnings = service.get_water_warnings(site)
    return to_response(
        site,
        SiteResponse,
        water_config_warnings=[
            WaterSourceWarningSchema(code=w.code, message=w.message, severity=w.severity) for w in warnings
        ],
    )


def _hardiness_response(site: Site, zone_doc: HardinessZone | None) -> SiteHardinessResponse:
    return SiteHardinessResponse(
        site_key=site.key or "",
        hardiness_zone=site.hardiness_zone,
        hardiness_zone_source=site.hardiness_zone_source,
        hardiness_zone_resolved_at=site.hardiness_zone_resolved_at,
        mean_annual_minimum_c=site.mean_annual_minimum_c,
        last_frost_date_avg=site.last_frost_date_avg,
        first_frost_date_avg=site.first_frost_date_avg,
        zone=to_response(zone_doc, HardinessZoneResponse) if zone_doc is not None else None,
    )


def _build_tree(
    locations: list[Location],
    slots_by_location: dict[str, int],
    plants_by_location: dict[str, int] | None = None,
    tank_names: dict[str, str] | None = None,
) -> list[LocationTreeNode]:
    plants_by_location = plants_by_location or {}
    tank_names = tank_names or {}
    nodes: dict[str, LocationTreeNode] = {}
    for loc in locations:
        loc_key = loc.key or ""
        nodes[loc_key] = LocationTreeNode(
            key=loc_key,
            name=loc.name,
            location_type_key=loc.location_type_key,
            depth=loc.depth,
            parent_location_key=loc.parent_location_key,
            slot_count=slots_by_location.get(loc_key, 0),
            active_plant_count=plants_by_location.get(loc_key, 0),
            tank_name=tank_names.get(loc_key),
        )
    roots: list[LocationTreeNode] = []
    for loc in locations:
        loc_key = loc.key or ""
        node = nodes[loc_key]
        if loc.parent_location_key and loc.parent_location_key in nodes:
            nodes[loc.parent_location_key].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get("", response_model=list[SiteResponse])
def list_sites(
    pagination: PaginationParams = Depends(get_pagination),
    ctx: TenantContext = Depends(get_current_tenant),
    service: SiteService = Depends(get_site_service),
):
    """List the tenant's sites (paginated)."""
    items, _total = service.list_sites(pagination.offset, pagination.limit, tenant_key=ctx.tenant_key)
    return [_site_response(s, service) for s in items]


@router.get("/{key}", response_model=SiteResponse)
def get_site(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: SiteService = Depends(get_site_service),
):
    """Return a single site by key."""
    s = service.get_site(key, tenant_key=ctx.tenant_key)
    return _site_response(s, service)


@router.post("", response_model=SiteResponse, status_code=201)
def create_site(
    body: SiteCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SITE, Action.CREATE)),
    service: SiteService = Depends(get_site_service),
):
    """Create a site for the tenant."""
    site = Site(**body.model_dump(), tenant_key=ctx.tenant_key)
    created = service.create_site(site)
    return _site_response(created, service)


@router.put("/{key}", response_model=SiteResponse)
def update_site(
    key: Annotated[str, Path(description="Document key of the site.")],
    body: SiteCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SITE, Action.UPDATE)),
    service: SiteService = Depends(get_site_service),
):
    """Update a site, preserving its resolved hardiness zone unless overridden."""
    existing = service.get_site(key, tenant_key=ctx.tenant_key)
    site = Site(**body.model_dump(), tenant_key=ctx.tenant_key)
    # REQ-039: ``SiteCreate`` carries no hardiness provenance fields. When the
    # caller does not set a manual zone, preserve the existing resolution so a
    # routine site edit never clobbers a derived zone / flips its source to
    # ``manual``; when a manual zone IS supplied, mark it as such.
    if body.hardiness_zone is None:
        site.hardiness_zone = existing.hardiness_zone
        site.hardiness_zone_source = existing.hardiness_zone_source
        site.hardiness_zone_resolved_at = existing.hardiness_zone_resolved_at
        site.mean_annual_minimum_c = existing.mean_annual_minimum_c
    else:
        site.hardiness_zone_source = "manual"
    updated = service.update_site(key, site)
    return _site_response(updated, service)


@router.delete("/{key}", status_code=204)
def delete_site(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.SITE, Action.DELETE)),
    service: SiteService = Depends(get_site_service),
):
    """Delete a site."""
    service.get_site(key, tenant_key=ctx.tenant_key)
    service.delete_site(key)


@router.get("/{key}/hardiness", response_model=SiteHardinessResponse)
def get_site_hardiness(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: HardinessZoneService = Depends(get_hardiness_zone_service),
):
    """Return the site's resolved hardiness zone and the matching catalog entry."""
    site, zone_doc = service.get_site_hardiness(key, ctx.tenant_key)
    return _hardiness_response(site, zone_doc)


@router.post("/{key}/resolve-hardiness-zone", response_model=SiteHardinessResponse)
def resolve_site_hardiness_zone(
    key: Annotated[str, Path(description="Document key of the site.")],
    force: bool = Query(False, description="Re-derive even when a manual zone is already set."),
    ctx: TenantContext = Depends(require_tenant_role(TenantRole.GROWER)),
    service: HardinessZoneService = Depends(get_hardiness_zone_service),
):
    """Derive the site's hardiness zone from its REQ-041 climate normals.

    Climate normals are fetched on demand from the site's GPS coordinates when
    not already cached, so this works immediately for a site that just got GPS
    (no waiting for the monthly climate-normals beat). A manually set zone is
    preserved unless ``force=true``. Returns 422 when no climate normals with a
    usable minimum temperature can be obtained (e.g. the site has no GPS).

    State-changing (mutates ``Site.hardiness_zone``), so it requires at least the
    ``grower`` role — a ``viewer`` cannot trigger a zone derivation (SEC-001).
    """
    site = service.resolve_for_site(key, ctx.tenant_key, force=force, fetch_if_missing=True)
    return _hardiness_response(site, service.catalog_entry(site.hardiness_zone))


@router.get("/{key}/location-tree", response_model=list[LocationTreeNode])
def get_location_tree(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: SiteService = Depends(get_site_service),
    plant_service: PlantInstanceService = Depends(get_plant_instance_service),
    tank_service: TankService = Depends(get_tank_service),
):
    """Return the site's location hierarchy with slot, plant and tank counts.

    The service verifies the site against ``tenant_key`` itself and scopes the
    traversal with it (#927), so the redundant pre-check is gone.
    """
    all_locations = service.get_location_tree(key, tenant_key=ctx.tenant_key)
    location_keys = {loc.key or "" for loc in all_locations}

    slots_by_location: dict[str, int] = {}
    for loc in all_locations:
        loc_key = loc.key or ""
        slots = service.list_slots(loc_key)
        slots_by_location[loc_key] = len(slots)

    # Count active plants per location
    plants_by_location: dict[str, int] = {}
    plants, _ = plant_service.list_plants(offset=0, limit=10000, tenant_key=ctx.tenant_key)
    for p in plants:
        if p.location_key and p.location_key in location_keys and not p.removed_on:
            plants_by_location[p.location_key] = plants_by_location.get(p.location_key, 0) + 1

    # Resolve tank names for locations with tank_key
    tank_names: dict[str, str] = {}
    for loc in all_locations:
        if loc.tank_key:
            loc_key = loc.key or ""
            try:
                tank = tank_service.get_tank(loc.tank_key, tenant_key=ctx.tenant_key)
                tank_names[loc_key] = tank.name
            except Exception:
                pass

    return _build_tree(all_locations, slots_by_location, plants_by_location, tank_names)


@router.get("/{key}/sensors", response_model=list[SensorResponse])
def get_site_sensors(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(get_current_tenant),
    site_service: SiteService = Depends(get_site_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """List the sensors attached to a site."""
    site_service.get_site(key, tenant_key=ctx.tenant_key)
    sensors = sensor_service.get_sensors_for_site(key)
    return [to_response(s, SensorResponse) for s in sensors]


@router.post("/{key}/sensors", response_model=SensorResponse, status_code=201)
def create_site_sensor(
    key: Annotated[str, Path(description="Document key of the site.")],
    body: SensorCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.CREATE)),
    site_service: SiteService = Depends(get_site_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Attach a sensor to a site."""
    site_service.get_site(key, tenant_key=ctx.tenant_key)
    sensor = Sensor(
        name=body.name,
        metric_type=body.metric_type,
        ha_entity_id=body.ha_entity_id,
        mqtt_topic=body.mqtt_topic,
        site_key=key,
    )
    created = sensor_service.create_sensor(sensor)
    return to_response(created, SensorResponse)


@router.put("/{key}/sensors/{sensor_key}", response_model=SensorResponse)
def update_site_sensor(
    key: Annotated[str, Path(description="Document key of the site.")],
    sensor_key: Annotated[str, Path(description="Document key of the sensor.")],
    body: SensorUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.UPDATE)),
    site_service: SiteService = Depends(get_site_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Update a sensor attached to a site (REQ-005 §2, #1339).

    Scoped by the site on purpose: a sensor carries no ``tenant_key``, so the
    site verified here *is* the tenant anchor, and the service refuses a sensor
    that hangs off anything else.
    """
    site_service.get_site(key, tenant_key=ctx.tenant_key)
    updated = sensor_service.update_sensor(
        sensor_key,
        # `exclude_unset`, not `exclude_none`: an explicit `null` is how the
        # client *clears* `ha_entity_id` / `mqtt_topic` / `unit_of_measurement`,
        # and `exclude_none` dropped exactly those keys — the write returned 200
        # and kept the old value (#1339 review).
        body.model_dump(exclude_unset=True),
        parent_field="site_key",
        parent_key=key,
    )
    return to_response(updated, SensorResponse)


@router.delete("/{key}/sensors/{sensor_key}", status_code=204)
def delete_site_sensor(
    key: Annotated[str, Path(description="Document key of the site.")],
    sensor_key: Annotated[str, Path(description="Document key of the sensor.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.SENSOR, Action.DELETE)),
    site_service: SiteService = Depends(get_site_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Delete a sensor of a site, with its edges (REQ-005 §2, #1339)."""
    site_service.get_site(key, tenant_key=ctx.tenant_key)
    sensor_service.delete_sensor(sensor_key, parent_field="site_key", parent_key=key, tenant_key=ctx.tenant_key)


@router.get("/{key}/sensors/live", response_model=LiveStateResponse)
def get_site_sensors_live(
    key: Annotated[str, Path(description="Document key of the site.")],
    ctx: TenantContext = Depends(get_current_tenant),
    site_service: SiteService = Depends(get_site_service),
    sensor_service: SensorService = Depends(get_sensor_service),
):
    """Return the live sensor readings for a site."""
    site_service.get_site(key, tenant_key=ctx.tenant_key)
    sensors = sensor_service.get_sensors_for_site(key)
    result = sensor_service.get_live_state_for_sensors(sensors)
    return LiveStateResponse(**result)

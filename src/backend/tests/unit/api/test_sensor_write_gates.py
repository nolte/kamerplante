"""The sensor write routes exist, are parent-scoped, and are role-gated (#1339).

Until #1339 a sensor could be **created and read and never changed or removed**:
there was no update or delete route at any prefix, while three detail pages and
an edit dialog offered both. This file pins the three properties of the repair
that a later edit could silently drop.

1. **The routes exist, on every parent.** Sensors hang off tanks, sites *and*
   locations, and the create routes already did so on all three. Adding the pair
   to whichever parent happened to be in front of the author is #948 exactly —
   two of four sibling routes repaired, the other two left open for months — so
   the pairing is asserted as a *set*, from the mounted route table.

2. **The role gate is the one REQ-049 §2.3 prescribes**: update reaches
   ``require_permission(..., UPDATE)`` (lead or grower), delete reaches
   ``require_permission(..., DELETE)`` (**lead only** — the irreversibility
   boundary). Reading the declared dependency is the shortest statement of the
   rule that can fail when someone swaps it back; a companion class drives the
   resolved dependency with each role, so the assertion is not merely "some
   callable is attached" (the wired-but-inert failure class).

3. **The parent is passed to the service, and named correctly.** A route that
   verifies its tank and then hands the service ``parent_field="site_key"``
   would pass both checks above and still be a cross-tenant write. The handlers
   are therefore called with doubles, and what reaches the service is asserted.

No TC-ID: these are route-surface invariants, not user-facing cases.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from app.api.v1.locations import tenant_router as locations_router
from app.api.v1.sites import tenant_router as sites_router
from app.api.v1.tanks import tenant_router as tanks_router
from app.api.v1.tanks.schemas import SensorUpdate
from app.common.auth import require_permission
from app.common.enums import TenantRole
from app.common.exceptions import ForbiddenError
from app.core.permissions import Action, ResourceType
from app.domain.models.sensor import Sensor
from app.domain.models.tenant_context import TenantContext

#: (handler, expected parent field, expected action) — one row per new route.
_WRITE_ROUTES = [
    (tanks_router.update_sensor, "tank_key", Action.UPDATE),
    (tanks_router.delete_sensor, "tank_key", Action.DELETE),
    (sites_router.update_site_sensor, "site_key", Action.UPDATE),
    (sites_router.delete_site_sensor, "site_key", Action.DELETE),
    (locations_router.update_location_sensor, "location_key", Action.UPDATE),
    (locations_router.delete_location_sensor, "location_key", Action.DELETE),
]

_IDS = [handler.__name__ for handler, _, _ in _WRITE_ROUTES]


def _ctx(role: TenantRole) -> TenantContext:
    return TenantContext(tenant_key="tenant-a", tenant_slug="mein-garten", user_key="user-a", role=role)


def _ctx_dependency(handler: Any) -> Any:
    """The callable behind the handler's ``ctx`` parameter default."""
    return inspect.signature(handler).parameters["ctx"].default.dependency


class RecordingSensorService:
    """Records what the route asked for, and answers with a plausible sensor."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def update_sensor(self, key: str, changes: dict, *, parent_field: str, parent_key: str) -> Sensor:
        self.calls.append(
            {"op": "update", "key": key, "changes": changes, "parent_field": parent_field, "parent_key": parent_key}
        )
        return Sensor(_key=key, name="EC", metric_type="ec_ms", **{parent_field: parent_key})

    def delete_sensor(self, key: str, *, parent_field: str, parent_key: str) -> bool:
        self.calls.append({"op": "delete", "key": key, "parent_field": parent_field, "parent_key": parent_key})
        return True


class ParentService:
    """Stands in for the tank / site service; records the tenant it was asked for."""

    def __init__(self) -> None:
        self.verified: list[tuple[str, str]] = []

    def get_tank(self, key: str, tenant_key: str = "") -> Any:
        self.verified.append((key, tenant_key))
        return object()

    def get_site(self, key: str, tenant_key: str = "") -> Any:
        self.verified.append((key, tenant_key))
        return object()

    def get_location(self, key: str) -> Any:
        # `_verify_location_tenant` resolves the site from the location; a
        # location has no tenant of its own either.
        return type("Loc", (), {"site_key": "site-of-loc", "key": key})()


class TestTheRoutesExistOnEveryParent:
    def test_all_six_are_mounted(self) -> None:
        from app.main import app

        mounted: set[tuple[str, str]] = set()

        def walk(router: Any, prefix: str = "") -> None:
            # `include_router` does not flatten — read `app.routes` directly and
            # you find six routes instead of ~800, and the scan looks like it
            # worked. The wrappers carry their children on `original_router`.
            for route in getattr(router, "routes", []):
                path = prefix + getattr(route, "path", "")
                if getattr(route, "endpoint", None) is not None:
                    for method in getattr(route, "methods", ()) or ():
                        mounted.add((method, path))
                inner = getattr(route, "original_router", None) or getattr(route, "app", None)
                if inner is not None and hasattr(inner, "routes"):
                    walk(inner, path)

        walk(app)
        assert len(mounted) > 500, "the route walk collapsed — this assertion would pass vacuously"

        for parent in ("tanks", "sites", "locations"):
            for method in ("PUT", "DELETE"):
                assert (method, f"/{parent}/{{key}}/sensors/{{sensor_key}}") in mounted, (
                    f"{method} on {parent} sensors is missing — the pair must exist on every parent"
                )


class TestTheDeclaredGate:
    @pytest.mark.parametrize(("handler", "_parent", "action"), _WRITE_ROUTES, ids=_IDS)
    def test_the_route_carries_the_prescribed_permission_gate(self, handler, _parent, action) -> None:
        expected = require_permission(ResourceType.SENSOR, action)
        dependency = _ctx_dependency(handler)

        # `require_permission` returns a fresh closure per call, so identity
        # cannot be compared; its captured `action` can, and that is the thing
        # that decides lead-only vs grower.
        assert dependency.__name__ == expected.__name__ == "_check"
        assert dependency.__closure__ is not None
        captured = {cell.cell_contents for cell in dependency.__closure__}
        assert action in captured, f"{handler.__name__} does not gate on {action}"


class TestTheGateActuallyRefuses:
    """Reading the dependency proves which is attached; this proves what it does."""

    @pytest.mark.parametrize(("handler", "_parent", "action"), _WRITE_ROUTES, ids=_IDS)
    def test_a_viewer_is_refused_every_sensor_write(self, handler, _parent, action) -> None:
        with pytest.raises(ForbiddenError):
            _ctx_dependency(handler)(ctx=_ctx(TenantRole.VIEWER))

    @pytest.mark.parametrize(("handler", "_parent", "action"), _WRITE_ROUTES, ids=_IDS)
    def test_only_a_lead_may_delete_while_a_grower_may_update(self, handler, _parent, action) -> None:
        """REQ-049 §2.3 — deletion is the irreversibility boundary."""
        dependency = _ctx_dependency(handler)

        if action is Action.DELETE:
            with pytest.raises(ForbiddenError):
                dependency(ctx=_ctx(TenantRole.GROWER))
        else:
            assert dependency(ctx=_ctx(TenantRole.GROWER)).role is TenantRole.GROWER

        assert dependency(ctx=_ctx(TenantRole.LEAD)).role is TenantRole.LEAD


class TestTheParentReachesTheService:
    """A route that verifies its tank and then names another parent is still a hole."""

    def test_tank_update_names_the_tank(self) -> None:
        sensors, tanks = RecordingSensorService(), ParentService()

        tanks_router.update_sensor(
            "tank-1",
            "sensor-1",
            SensorUpdate(name="EC"),
            ctx=_ctx(TenantRole.GROWER),
            tank_service=tanks,
            sensor_service=sensors,
        )

        assert tanks.verified == [("tank-1", "tenant-a")]
        assert sensors.calls == [
            {
                "op": "update",
                "key": "sensor-1",
                "changes": {"name": "EC"},
                "parent_field": "tank_key",
                "parent_key": "tank-1",
            }
        ]

    def test_tank_delete_names_the_tank(self) -> None:
        sensors, tanks = RecordingSensorService(), ParentService()

        tanks_router.delete_sensor(
            "tank-1", "sensor-1", ctx=_ctx(TenantRole.LEAD), tank_service=tanks, sensor_service=sensors
        )

        assert tanks.verified == [("tank-1", "tenant-a")]
        assert sensors.calls[0]["parent_field"] == "tank_key"
        assert sensors.calls[0]["parent_key"] == "tank-1"

    def test_site_routes_name_the_site(self) -> None:
        sensors, sites = RecordingSensorService(), ParentService()

        sites_router.update_site_sensor(
            "site-1",
            "sensor-1",
            SensorUpdate(is_active=False),
            ctx=_ctx(TenantRole.GROWER),
            site_service=sites,
            sensor_service=sensors,
        )
        sites_router.delete_site_sensor(
            "site-1", "sensor-1", ctx=_ctx(TenantRole.LEAD), site_service=sites, sensor_service=sensors
        )

        assert sites.verified == [("site-1", "tenant-a"), ("site-1", "tenant-a")]
        assert [c["parent_field"] for c in sensors.calls] == ["site_key", "site_key"]
        assert {c["parent_key"] for c in sensors.calls} == {"site-1"}

    def test_location_routes_name_the_location_and_verify_its_site(self) -> None:
        sensors, sites = RecordingSensorService(), ParentService()

        locations_router.update_location_sensor(
            "loc-1",
            "sensor-1",
            SensorUpdate(name="Air"),
            ctx=_ctx(TenantRole.GROWER),
            service=sites,
            sensor_service=sensors,
        )
        locations_router.delete_location_sensor(
            "loc-1", "sensor-1", ctx=_ctx(TenantRole.LEAD), service=sites, sensor_service=sensors
        )

        # The tenant anchor of a location is its site (a location has no
        # `tenant_key`), so that is what must be verified.
        assert sites.verified == [("site-of-loc", "tenant-a"), ("site-of-loc", "tenant-a")]
        assert [c["parent_field"] for c in sensors.calls] == ["location_key", "location_key"]
        assert {c["parent_key"] for c in sensors.calls} == {"loc-1"}

    def test_an_unset_field_is_not_written(self) -> None:
        """`exclude_none` — a PATCH-shaped body must not blank the other fields."""
        sensors, tanks = RecordingSensorService(), ParentService()

        tanks_router.update_sensor(
            "tank-1",
            "sensor-1",
            SensorUpdate(name="EC"),
            ctx=_ctx(TenantRole.GROWER),
            tank_service=tanks,
            sensor_service=sensors,
        )

        assert sensors.calls[0]["changes"] == {"name": "EC"}

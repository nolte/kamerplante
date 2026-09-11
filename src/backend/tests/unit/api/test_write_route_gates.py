"""Every write route resolves its caller through a gate, or is allowlisted with a reason (#1353).

Nothing enumerated the write surface. `check_route_role_guards.py` covers the
frontend router against the decision table and says so in its own docstring — a
new backend gate does not turn it red. `check_tenant_body_field.py` covers body
schemas. `test_require_permission_enforcement.py` and
`test_req049_scope_enforcement.py` drive hand-picked endpoints. So a write route
added with a copied `Depends(get_current_tenant)` was green everywhere, and #948
— a guard opted into at the call site — kept recurring because opting in was the
only mechanism there was.

**Two selectors, not one.** #1353 describes the tenant-scoped half. That half
alone would never have reached `/api/v1/admin/settings` (#1385) or
`/api/v1/admin/oidc-providers` (#1399), both of which write installation-wide
configuration and both of which drifted exactly the same way. The admin half is
here for that reason, and it found #1399 on its first run.

**Why a test and not a `scripts/check_*.py` sweep.** The question is which
dependency a mounted route actually resolves, and that is a property of the
assembled app, not of a file. The AST sweep quoted in #1353 keyed on the filename
`tenant_router.py` and therefore missed three routes that live in
`nutrient_calculations/router.py` and `plant_instances/diary_router.py` — the
same opt-in-list hole the sweep exists to close, one level up.

**The allowlist is the interesting half.** Not every ungated write route is a
defect: per-user state, a data-subject right, and POST-as-computation are all
legitimately open to any member. What was missing is anyone having written down
*which is which*. Each entry below carries its reason, and an entry that no
longer matches a route fails — the obsolescence rule `check_layer_imports` and
`check_route_role_guards` already follow.
"""

import inspect
from typing import Any

import pytest
from fastapi.params import Depends as DependsParam

from app.api.v1.router import api_router
from app.common.auth import get_current_tenant, get_current_user
from app.common.enums import TenantRole
from app.common.exceptions import ForbiddenError
from app.domain.models.tenant_context import TenantContext

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TENANT_PREFIX = "/t/{tenant_slug}"
ADMIN_PREFIX = "/api/v1/admin"


class Operation:
    """One mounted write operation, with the dependencies its signature declares."""

    def __init__(self, method: str, path: str, endpoint: Any) -> None:
        self.method = method
        self.path = path
        self.module = endpoint.__module__
        self.name = endpoint.__name__
        self.dependencies: dict[str, Any] = {}
        try:
            signature = inspect.signature(endpoint)
        except TypeError, ValueError:  # pragma: no cover - defensive
            return
        for parameter_name, parameter in signature.parameters.items():
            if isinstance(parameter.default, DependsParam):
                self.dependencies[parameter_name] = parameter.default.dependency

    @property
    def id(self) -> str:
        """`module.function`, the key the allowlist uses.

        Not `(METHOD, path)`: a path is edited for reasons that have nothing to do
        with authorisation, and an allowlist keyed on one would expire on a rename
        and quietly re-admit the route.
        """
        return f"{self.module.removeprefix('app.api.v1.')}.{self.name}"

    def __repr__(self) -> str:  # pragma: no cover - test output only
        return f"{self.method} {self.path} ({self.id})"


def mounted_write_operations() -> list[Operation]:
    """Every write operation the v1 router mounts, with its cumulative path.

    `include_router` does **not** flatten: it leaves `_IncludedRouter` wrappers
    that carry no `path` attribute at all, and whose prefix lives in
    `include_context.prefix`. A flat read of `api_router.routes` therefore finds
    ~50 routes instead of ~440, and every path comes out relative — the mistake
    `scripts/check_frontend_calls_served.py` documents at length after making it.
    `test_the_walk_sees_what_a_flat_read_cannot` below pins that this walk does
    not repeat it.
    """
    found: list[Operation] = []

    def walk(router: Any, prefix: str = "") -> None:
        for route in getattr(router, "routes", []):
            included = getattr(route, "original_router", None)
            if included is not None:
                context = getattr(route, "include_context", None)
                walk(included, prefix + (getattr(context, "prefix", "") or ""))
                continue
            endpoint = getattr(route, "endpoint", None)
            if endpoint is None:
                continue
            path = prefix + (getattr(route, "path", "") or "")
            for method in getattr(route, "methods", ()) or ():
                if method in WRITE_METHODS:
                    found.append(Operation(method, path, endpoint))

    walk(api_router)
    return found


#: Tenant-scoped write routes that may resolve `ctx` through bare
#: `get_current_tenant`. Three reasons qualify, and each entry says which.
_TENANT_ALLOWLIST: dict[str, str] = {
    # ── Per-user state. The row belongs to the caller, not to the tenant, so a
    # domain role is the wrong axis: a viewer manages their own favourites,
    # notifications and onboarding exactly as a lead does.
    "favorites.tenant_router.add_favorite": "per-user favourite",
    "favorites.tenant_router.remove_favorite": "per-user favourite",
    "notifications.tenant_router.mark_read": "per-user notification state",
    "notifications.tenant_router.mark_acted": "per-user notification state",
    "notifications.tenant_router.update_preferences": "per-user notification preferences",
    "notifications.tenant_router.subscribe_pwa": "per-user push subscription",
    "notifications.tenant_router.unsubscribe_pwa": "per-user push subscription",
    "notifications.tenant_router.send_test_notification": (
        "sends to the caller's own configured channel with a fixed body, rate-limited per client address"
    ),
    "onboarding.tenant_router.complete_onboarding": "per-user onboarding progress",
    "onboarding.tenant_router.skip_onboarding": "per-user onboarding progress",
    "onboarding.tenant_router.reset_onboarding": "per-user onboarding progress",
    "onboarding.tenant_router.update_onboarding_progress": "per-user onboarding progress",
    "user_preferences.tenant_router.update_preferences": "per-user preferences",
    "ki_assistent.tenant_router.dismiss_tip": "per-user tip state, generates nothing",
    "ki_assistent.tenant_router.acted_on_tip": "per-user tip state, generates nothing",
    "ki_assistent.tenant_router.dismiss_daily_tip": "per-user tip state, generates nothing",
    "ki_assistent.tenant_router.create_conversation": (
        "creates an empty per-user conversation record and calls no provider; send_message, which does, is gated"
    ),
    # ── A data-subject right. Gating erasure on a domain role would make the
    # right depend on rank, which is exactly what Art. 17 does not allow.
    "ki_assistent.tenant_router.delete_conversation": "DSGVO Art. 17 erasure of the caller's own conversation",
    # ── POST-as-computation. Reads its inputs, returns a result, writes nothing.
    # Verified per route: none of the service methods behind these reaches a
    # repository create/update/delete.
    "nutrient_plans.tenant_router.calculate_dosages": "computation, no write",
    "nutrient_calculations.router.area_dosing": "computation, no write",
    "tanks.tenant_router.calculate_ec_dilution": "computation over a read tank, no write",
    "plant_instances.tenant_router.validate_planting": "validation, no write",
    "tasks.tenant_router.validate_hst": "validation, no write",
    "actuators.tenant_router.test_rule": "dry-run of a control rule against supplied readings, no side effects",
}

#: Installation-wide write routes that may resolve their caller through bare
#: `get_current_user`. The bar is higher here: these change configuration for
#: everyone, so an entry needs a reason that survives the question "what stops a
#: viewer in an unrelated tenant from doing this?".
#: Empty, and that is the point. It held one entry —
#: ``admin.recognition.router.start_acquisition`` — whose reason was "deliberate and
#: documented at the site". The route's docstring did say so; the pre-merge review of
#: #1385 read it and found the argument justified the *card* being reachable, not the
#: *route* being open, while the identical ``/acquire`` on the ``admin/pests`` sibling
#: carried ``require_platform_admin`` all along. The entry is deleted rather than
#: reworded (#1401): an allowlist that writes a drift down as approved is worse than no
#: allowlist, because the next reader takes it as a decision someone made on purpose.
_ADMIN_ALLOWLIST: dict[str, str] = {}


def _tenant_write_operations() -> list[Operation]:
    return [op for op in mounted_write_operations() if TENANT_PREFIX in op.path]


def _admin_write_operations() -> list[Operation]:
    return [op for op in mounted_write_operations() if op.path.startswith(ADMIN_PREFIX)]


def _format(operations: list[Operation]) -> str:
    return "\n  ".join(f"{op.method:6} {op.path}  ({op.id})" for op in sorted(operations, key=lambda o: o.id))


class TestTheWalk:
    """The walk itself, pinned — a sweep that finds nothing is not a clean result."""

    def test_it_finds_a_realistic_number_of_write_operations(self):
        """A floor, not an exact count: the surface grows with every feature.

        Its job is to fail loudly if the walk ever returns almost nothing, which
        is what a flat read does and what would make every assertion below vacuous.
        """
        assert len(mounted_write_operations()) > 300

    def test_the_walk_sees_what_a_flat_read_cannot(self):
        """`include_router` leaves wrappers; reading `api_router.routes` flat misses them."""
        flat = [r for r in api_router.routes if getattr(r, "endpoint", None) is not None]
        assert len(flat) < len(mounted_write_operations()) / 5

    def test_both_scopes_are_actually_populated(self):
        """Either selector matching nothing would make its assertion vacuous."""
        assert len(_tenant_write_operations()) > 200
        assert len(_admin_write_operations()) > 10


class TestTenantWriteGates:
    def test_no_tenant_write_route_resolves_ctx_through_bare_get_current_tenant(self):
        offenders = [
            op
            for op in _tenant_write_operations()
            if op.dependencies.get("ctx") is get_current_tenant and op.id not in _TENANT_ALLOWLIST
        ]
        assert not offenders, (
            "These tenant-scoped write routes resolve `ctx` through bare `get_current_tenant`, "
            "so every member of the tenant may call them regardless of role. Gate them the way "
            "their siblings are gated, or add them to _TENANT_ALLOWLIST with a reason:\n  " + _format(offenders)
        )

    def test_every_allowlisted_tenant_route_still_exists_and_is_still_ungated(self):
        """An entry that no longer applies fails, rather than sitting there forever.

        Both directions: a route that was deleted, and a route that has since been
        gated. The second is the one that rots quietly — the allowlist would go on
        excusing a route that no longer needs excusing, and the next reader would
        take the entry as a statement that the route must stay open.
        """
        by_id = {op.id: op for op in _tenant_write_operations()}
        stale = []
        for route_id, reason in _TENANT_ALLOWLIST.items():
            operation = by_id.get(route_id)
            if operation is None:
                stale.append(f"{route_id}: no such tenant write route ({reason})")
            elif operation.dependencies.get("ctx") is not get_current_tenant:
                stale.append(f"{route_id}: now gated, drop the entry ({reason})")
        assert not stale, "Obsolete _TENANT_ALLOWLIST entries:\n  " + "\n  ".join(stale)

    def test_every_reason_is_written_out(self):
        """A blank or placeholder reason is an entry nobody has to justify."""
        for route_id, reason in _TENANT_ALLOWLIST.items():
            assert len(reason) >= 12, f"{route_id} carries no usable reason: {reason!r}"


class TestAdminWriteGates:
    def test_no_admin_write_route_resolves_its_caller_through_bare_get_current_user(self):
        offenders = [
            op
            for op in _admin_write_operations()
            if get_current_user in op.dependencies.values() and op.id not in _ADMIN_ALLOWLIST
        ]
        assert not offenders, (
            "These routes write installation-wide configuration behind `get_current_user` alone, "
            "so any authenticated member of any tenant may call them. Gate them with "
            "`require_platform_admin`, or add them to _ADMIN_ALLOWLIST with a reason:\n  " + _format(offenders)
        )

    def test_every_allowlisted_admin_route_still_exists_and_is_still_ungated(self):
        by_id = {op.id: op for op in _admin_write_operations()}
        stale = []
        for route_id, reason in _ADMIN_ALLOWLIST.items():
            operation = by_id.get(route_id)
            if operation is None:
                stale.append(f"{route_id}: no such admin write route ({reason})")
            elif get_current_user not in operation.dependencies.values():
                stale.append(f"{route_id}: now gated, drop the entry ({reason})")
        assert not stale, "Obsolete _ADMIN_ALLOWLIST entries:\n  " + "\n  ".join(stale)

    def test_every_reason_is_written_out(self):
        for route_id, reason in _ADMIN_ALLOWLIST.items():
            assert len(reason) >= 12, f"{route_id} carries no usable reason: {reason!r}"


class TestTheGuardCanFail:
    """Falsification, in-process: an assertion nobody has seen fail proves nothing.

    Each of these builds the same comparison the tests above make, against an
    operation known to violate it, and asserts the comparison catches it. Without
    them a typo in a selector — a prefix that matches nothing, a dependency
    identity that is never equal — leaves every test above green and silent.
    """

    def test_an_ungated_tenant_route_would_be_reported(self):
        def _handler(ctx=DependsParam(dependency=get_current_tenant)):  # pragma: no cover
            return None

        operation = Operation("POST", "/api/v1/t/{tenant_slug}/invented", _handler)
        assert operation.dependencies.get("ctx") is get_current_tenant
        assert operation.id not in _TENANT_ALLOWLIST

    def test_an_ungated_admin_route_would_be_reported(self):
        def _handler(_current_user=DependsParam(dependency=get_current_user)):  # pragma: no cover
            return None

        operation = Operation("POST", "/api/v1/admin/invented", _handler)
        assert get_current_user in operation.dependencies.values()
        assert operation.id not in _ADMIN_ALLOWLIST

    def test_a_gated_route_would_not_be_reported(self):
        """The control: a selector that reports everything is as useless as one that reports nothing."""

        def _handler(ctx=DependsParam(dependency=lambda: None)):  # pragma: no cover
            return None

        operation = Operation("POST", "/api/v1/t/{tenant_slug}/invented", _handler)
        assert operation.dependencies.get("ctx") is not get_current_tenant


@pytest.mark.parametrize("route_id", sorted(_TENANT_ALLOWLIST) + sorted(_ADMIN_ALLOWLIST))
def test_no_route_is_allowlisted_twice(route_id: str):
    """Two entries for one route would let a stale reason outlive a live one."""
    assert not (route_id in _TENANT_ALLOWLIST and route_id in _ADMIN_ALLOWLIST)


#: The routes this change moved off bare `get_current_tenant`. Listed so the
#: behavioural test below has something concrete to drive, and so a later reader
#: can see what the triage decided rather than having to diff for it.
_GATED_HERE = [
    "diagnose.tenant_router.analyze",
    "ki_assistent.tenant_router.explain",
    "ki_assistent.tenant_router.refresh_tips",
    "ki_assistent.tenant_router.send_message",
    "plant_instances.diary_router.request_plant_diary_entry_analysis",
    "plant_instances.diary_router.cancel_plant_diary_entry_analysis",
    "planting_runs.tenant_router.request_run_diary_entry_analysis",
    "planting_runs.tenant_router.cancel_run_diary_entry_analysis",
    "tasks.tenant_router.start_task",
    "tasks.tenant_router.complete_task",
    "tasks.tenant_router.skip_task",
    "tasks.tenant_router.reopen_task",
    "watering_events.tenant_router.confirm_watering",
    "watering_events.tenant_router.quick_confirm_watering",
    "watering_logs.tenant_router.confirm_watering",
    "watering_logs.tenant_router.quick_confirm_watering",
]


def _viewer() -> TenantContext:
    return TenantContext(tenant_key="tenant-a", tenant_slug="mein-garten", user_key="user-a", role=TenantRole.VIEWER)


def _grower() -> TenantContext:
    return TenantContext(tenant_key="tenant-a", tenant_slug="mein-garten", user_key="user-a", role=TenantRole.GROWER)


class TestTheGatesActuallyRefuse:
    """Reading a dependency proves which one is attached; this proves what it does.

    The sweep above is an identity comparison: it cannot tell a working gate from
    a hollowed-out one, which is the failure class this repository keeps paying
    for (#706, #1397). Driving the resolved dependency with a viewer context is
    the shortest statement of the rule that goes red when the gate stops gating.
    """

    @pytest.mark.parametrize("route_id", _GATED_HERE)
    def test_a_viewer_is_refused(self, route_id: str):
        by_id = {op.id: op for op in _tenant_write_operations()}
        operation = by_id.get(route_id)
        assert operation is not None, f"{route_id} no longer exists; update _GATED_HERE"
        check = operation.dependencies["ctx"]
        with pytest.raises(ForbiddenError):
            check(_viewer())

    @pytest.mark.parametrize("route_id", _GATED_HERE)
    def test_a_grower_passes(self, route_id: str):
        """The control. A gate that refuses everyone passes every test above."""
        by_id = {op.id: op for op in _tenant_write_operations()}
        check = by_id[route_id].dependencies["ctx"]
        assert check(_grower()) is not None

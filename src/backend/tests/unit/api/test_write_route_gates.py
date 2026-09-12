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
from app.common.enums import TenantRole
from app.common.exceptions import ForbiddenError
from app.domain.models.tenant_context import TenantContext

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TENANT_PREFIX = "/t/{tenant_slug}"
ADMIN_PREFIX = "/api/v1/admin"


class Operation:
    """One mounted write operation, with the dependencies its signature declares."""

    def __init__(self, method: str, path: str, endpoint: Any, route: Any = None) -> None:
        self.method = method
        self.path = path
        self.module = endpoint.__module__
        self.name = endpoint.__name__
        #: The mounted route itself, kept so the THIRD question below can read
        #: `route.dependant` transitively. `inspect.signature` sees only what the
        #: handler names; a router-level `APIRouter(dependencies=[...])` is
        #: invisible to it, in both directions — a correctly gated route passes
        #: for the wrong reason, and an ungated sibling passes identically.
        self.route = route
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
                    found.append(Operation(method, path, endpoint, route))

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
    "notifications.tenant_router.mark_acted": (
        "per-user notification state — and, for a care.* notification with a confirm "
        "action, a CareConfirmation and a WateringLog. That branch is gated inline on "
        "the domain role, because the notification is addressed to this user while the "
        "write it triggers is the one require_permission('watering-log', CREATE) gates "
        "on the direct route"
    ),
    "notifications.tenant_router.update_preferences": "per-user notification preferences",
    "notifications.tenant_router.subscribe_pwa": "per-user push subscription",
    "notifications.tenant_router.unsubscribe_pwa": "per-user push subscription",
    "notifications.tenant_router.send_test_notification": (
        "sends to the caller's own configured channel with a fixed body, rate-limited per client address"
    ),
    "onboarding.tenant_router.skip_onboarding": "per-user onboarding progress",
    "onboarding.tenant_router.reset_onboarding": "per-user onboarding progress",
    "onboarding.tenant_router.update_onboarding_progress": "per-user onboarding progress",
    "user_preferences.tenant_router.update_preferences": "per-user preferences",
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
    # The three below joined this list in #1402, and the route they took here is
    # worth stating: they were not "ungated members-only routes" being written
    # down — they answered an ANONYMOUS caller, and each of them reads the
    # fertilizer catalogue with `FertilizerService.get_fertilizer`, whose
    # `tenant_key=""` default skips its own ownership check. Gating them on
    # `get_current_tenant` and threading `ctx.tenant_key` into that call is what
    # moved them from "unauthenticated, reading across tenants" to "computation
    # any member may run" — the same category their `area_dosing` sibling was
    # always in. The four remaining calculators in that module need no entry:
    # they carry the router-level gate and no `ctx` parameter, so this sweep's
    # question ("is `ctx` bare?") does not apply to them at all.
    "nutrient_calculations.router.mixing_protocol": "computation over the caller's own catalogue, no write",
    "nutrient_calculations.router.mixing_safety": "computation over the caller's own catalogue, no write",
    "nutrient_calculations.router.ec_budget": "computation over the caller's own catalogue, no write",
    # These four reach no database at all — they compute from the request body
    # alone. They are listed here rather than left silent because the router-level
    # gate #1402 gave them removed `ctx` from their signatures, and the version of
    # this sweep that read `inspect.signature` therefore stopped reporting them
    # while the third question was satisfied by the router. Four routes reported by
    # nothing, recorded nowhere: the opt-in drift this file exists to catch, moved
    # one level up by the change that was closing it. The sweep now reads the
    # effective chain, so the router-level gate is visible to it and these four
    # need the same written decision as their siblings.
    "nutrient_calculations.router.flushing_protocol": "computation from the request body, no read, no write",
    "nutrient_calculations.router.runoff_analysis": "computation from the request body, no read, no write",
    "nutrient_calculations.router.water_mix": "computation from the request body, no read, no write",
    "nutrient_calculations.router.water_mix_reverse": "computation from the request body, no read, no write",
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


#: THE THIRD QUESTION (#1402), and it is a different one from the two above.
#:
#: Both selectors above key on the PRESENCE of a specific weak dependency: the
#: tenant half asks whether `ctx` IS `get_current_tenant`, the admin half whether
#: `get_current_user` appears. A route carrying NO dependency at all fails both
#: tests in the passing direction, and 133 write operations lie outside both
#: prefixes besides. Measured on 2026-09-12, before this question existed:
#: **24** of 439 mounted write operations resolved no authorisation dependency
#: anywhere — fourteen of them not deliberately public. Seven were the
#: calculators under `/api/v1/calculations`, invisible because they fall through
#: both prefixes; seven were under `/t/{tenant_slug}/nutrient-calculations`,
#: which the tenant selector SEES and does not report. Three of those seven also
#: read the fertilizer catalogue with `FertilizerService.get_fertilizer`'s
#: `tenant_key=""` default, which skips its own ownership check.
#:
#: This question asks instead: does the effective dependency chain of this write
#: operation contain ANY authorisation dependency? It reads `route.dependant`
#: transitively rather than `inspect.signature`, so a router-level
#: `APIRouter(dependencies=[...])` counts — which is how the fourteen were fixed,
#: and a per-handler read would have reported them as still open.
#:
#: It is deliberately coarse. "Carries some authorisation" is not "carries the
#: RIGHT authorisation": the installation-wide master data behind bare
#: `get_current_user` (#1402 group B) passes this question and is still a defect.
#: A coarse question that cannot be fooled by absence is worth more than a
#: precise one with a hole, and the precise one is the next refinement.
#: Dependencies that actually REFUSE a caller, by qualified name. A set of exact
#: names and not substring markers, because the first version of this list used
#: substrings and three of them were wrong in the permissive direction: `"mcp_"`
#: matched `require_mcp_enabled` (an operator feature flag that 404s when MCP is
#: off and authorises nobody when it is on) plus `get_mcp_dispatcher` and
#: `get_mcp_session_store`; `"api_key"` matched the `APIKeyHeader` scheme object,
#: which carries `auto_error=False` and therefore never refuses anything. No route
#: was saved by a weak match alone when this was found, so it was latent — but a
#: write route added under `/api/v1/mcp` carrying only `get_mcp_dispatcher` would
#: have counted as authorised and been anonymously reachable.
#:
#: `__qualname__` rather than `__name__`: the three `require_*` factories all
#: return a closure called `_check`, indistinguishable by name and exact by
#: qualified name.
_AUTHORISATION: frozenset[str] = frozenset(
    {
        "get_current_user",
        "get_current_tenant",
        "require_platform_admin",
        "_require_platform_admin",
        "require_permission.<locals>._check",
        "require_tenant_role.<locals>._check",
        "require_admin_scope.<locals>._check",
        "require_attachment_permission.<locals>._dependency",
        "get_mcp_principal",
    }
)

#: The subset above that gates on MORE than "is authenticated" or "is a member".
_ROLE_GATES: frozenset[str] = frozenset(
    {
        "require_permission.<locals>._check",
        "require_tenant_role.<locals>._check",
        "require_admin_scope.<locals>._check",
        "require_platform_admin",
        "_require_platform_admin",
        "require_attachment_permission.<locals>._dependency",
    }
)

#: Dependencies whose NAME reads like authorisation and which authorise nobody.
#: Enumerated with a reason so the classification cannot drift silently:
#: `test_every_auth_shaped_dependency_is_classified` fails on a name in the live
#: app that matches neither set — the obsolescence rule the allowlists already
#: follow, applied one level up to the vocabulary itself.
_NOT_AUTHORISATION: dict[str, str] = {
    "require_mcp_enabled": "operator feature flag; 404s when MCP is off, authorises nobody when on",
    "require_ai_tenant_enabled": "REQ-031 feature flag, not a caller check",
    "require_ai_feature_flag": "REQ-031 operator flag, not a caller check",
    "get_is_platform_admin": "returns a bool for the caller to branch on; refuses nobody",
    "APIKeyHeader": "scheme object with auto_error=False - extracts a header, never refuses",
    "HTTPBearer": "scheme object; extraction only, the provider decides",
    "get_auth_provider": "constructs the provider; get_current_user is what calls it",
    "get_auth_service": "service dependency",
    "get_tenant_service": "service dependency",
    "get_tenant_repo": "repository dependency",
    "get_user_service": "service dependency",
    "get_user_preference_service": "service dependency",
    "get_oauth_engine": "engine dependency",
    "get_active_tenant_key": "resolves the header slug; the refusal is the get_current_user beneath it",
    "get_active_tenant_context": "same - authorisation is the get_current_user it depends on",
    "get_mcp_dispatcher": "infrastructure; dispatches after get_mcp_principal has decided",
    # A FACTORY, not a gate, and it was in `_AUTHORISATION` for one commit — the
    # same mistake the substring `"mcp_"` made, repeated by hand after the
    # substrings were removed. `dependencies.py:879` constructs
    # `McpAuthenticator(...)` and refuses nobody; the refusal is
    # `authenticator.authenticate(...)`, called inside the handler. Its sibling
    # `get_task_entity_guard` has the same shape and was correctly left out,
    # which is what made the inconsistency visible.
    "get_mcp_authenticator": "constructs the authenticator; the handler's authenticate() call is the refusal",
    "get_mcp_session_store": "infrastructure",
}

#: Substrings that make a dependency name "auth-shaped" for the classification
#: guard. Deliberately generous: a name caught here and in neither set is a test
#: failure asking for a one-line decision, which is cheap. A name NOT caught here
#: is assumed infrastructure, which is the residual risk and why this leans wide.
_AUTH_SHAPED = ("auth", "admin", "tenant", "user", "principal", "permission", "role", "require_", "key")


#: Write operations that legitimately resolve no authorisation at all. Every entry
#: is an endpoint a caller must reach BEFORE having a session, or one the product
#: publishes on purpose. Anything else here is a defect wearing a reason.
_PUBLIC_ALLOWLIST: dict[str, str] = {
    "auth.router.login": "issues the session; cannot require one",
    "auth.router.register": "creates the account; cannot require one",
    "auth.router.refresh": "presents the refresh cookie, not an access token",
    "auth.router.logout": "must succeed for an expired or absent session",
    "auth.router.request_password_reset": "the caller has lost the credential",
    "auth.router.confirm_password_reset": "authorised by the emailed token",
    "auth.router.verify_email": "authorised by the emailed token",
    "auth.router.redeem_device_pairing": "authorised by the pairing code",
    "privacy.router.confirm_email_change": "authorised by the emailed token (REQ-025)",
    "ki_assistent.public_router.public_ask": "REQ-031 light-mode probe, published on purpose",
    # Authenticates from the API key in the REQUEST BODY, inside the handler, the
    # way `login` authenticates from a password — so it carries no transport
    # credential and never will. It was previously exempt by accident:
    # `get_mcp_authenticator` was miscounted as authorisation and this is the one
    # live route whose only `_AUTHORISATION` member it was. The exemption is the
    # same; what changed is that it is now written down.
    #
    # Not unguarded: `require_mcp_enabled` 404s the route when MCP is off, the
    # auth rate limiter applies per IP, and REQ-033 SEC-003 collapses the
    # valid-non-service case into the same generic 401 so it cannot be used as an
    # oracle.
    "auth.router.validate_service_account": "authenticates from the key in the body, like login",
}


def _authorisation_chain(operation: Operation) -> list[str]:
    """Every dependency name in the operation's effective chain, router level included."""
    dependant = getattr(operation.route, "dependant", None)
    if dependant is None:  # pragma: no cover - defensive
        return []

    names: list[str] = []
    seen: set[int] = set()

    def walk(node: Any) -> None:
        for sub in node.dependencies:
            if id(sub) in seen:
                continue
            seen.add(id(sub))
            call = sub.call
            names.append(getattr(call, "__qualname__", type(call).__name__))
            walk(sub)

    walk(dependant)
    return names


def _resolves_authorisation(operation: Operation) -> bool:
    return bool(set(_authorisation_chain(operation)) & _AUTHORISATION)


def _resolves_bare_tenant_context(operation: Operation) -> bool:
    """Authenticated and a member, and nothing beyond that.

    Read from the effective chain rather than `inspect.signature`. The signature
    read had a blind spot that #1402 created and then had to close: moving the
    `nutrient_calculations` gate onto its ROUTER removed `ctx` from four
    handlers' signatures, so this sweep stopped seeing them while the third
    question was satisfied by the router-level `get_current_tenant`. Four routes
    were reported by nothing and recorded in no allowlist — the opt-in drift this
    file exists to catch, relocated one level up.
    """
    names = set(_authorisation_chain(operation))
    return "get_current_tenant" in names and not (names & _ROLE_GATES)


def _resolves_bare_user(operation: Operation) -> bool:
    """Authenticated, with no role or scope gate above it."""
    names = set(_authorisation_chain(operation))
    return "get_current_user" in names and not (names & _ROLE_GATES)


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
        assert len(_admin_write_operations()) > 30

    def test_the_sweep_runs_against_the_full_route_surface(self):
        """In light mode half the admin surface is not mounted, and the sweep goes quiet.

        `api/v1/router.py` mounts `auth`, `privacy`, `admin/platform` and
        `admin/oidc-providers` only when `kamerplanter_mode == "full"`. Measured:
        38 admin write operations under `full`, **19** under `light`. The sweep
        passes in both — so under `light` it certifies half the surface while
        reading exactly the same.

        That is not hypothetical. `/admin/oidc-providers` (#1399) is one of the
        routers that disappears, and it is the finding this sweep is credited with.
        Run under `light`, it would have reported nothing and looked identical.

        So the mode is asserted rather than assumed, and this **fails** rather than
        skipping: a skip is indistinguishable from a pass in a CI summary, which is
        the property that let the original 37 accumulate. The floor above is raised
        to 30 for the same reason — it is now a number only `full` can satisfy, so
        deleting this test does not silently restore the hole.
        """
        from app.config.settings import settings

        assert settings.kamerplanter_mode == "full", (
            f"This sweep only covers the full route surface; it is running under "
            f"`{settings.kamerplanter_mode}`, where the auth, privacy, platform-admin "
            f"and OIDC-provider routers are not mounted at all. Run it with "
            f"KAMERPLANTER_MODE=full, or extend it with a light-mode expectation of "
            f"its own — but do not let it report green over half the surface."
        )


class TestTenantWriteGates:
    def test_no_tenant_write_route_resolves_ctx_through_bare_get_current_tenant(self):
        offenders = [
            op
            for op in _tenant_write_operations()
            if _resolves_bare_tenant_context(op) and op.id not in _TENANT_ALLOWLIST
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
            elif not _resolves_bare_tenant_context(operation):
                stale.append(f"{route_id}: now gated, drop the entry ({reason})")
        assert not stale, "Obsolete _TENANT_ALLOWLIST entries:\n  " + "\n  ".join(stale)

    def test_every_reason_is_written_out(self):
        """A blank or placeholder reason is an entry nobody has to justify."""
        for route_id, reason in _TENANT_ALLOWLIST.items():
            assert len(reason) >= 12, f"{route_id} carries no usable reason: {reason!r}"


class TestAdminWriteGates:
    def test_no_admin_write_route_resolves_its_caller_through_bare_get_current_user(self):
        offenders = [
            op for op in _admin_write_operations() if _resolves_bare_user(op) and op.id not in _ADMIN_ALLOWLIST
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
            elif not _resolves_bare_user(operation):
                stale.append(f"{route_id}: now gated, drop the entry ({reason})")
        assert not stale, "Obsolete _ADMIN_ALLOWLIST entries:\n  " + "\n  ".join(stale)

    def test_every_reason_is_written_out(self):
        for route_id, reason in _ADMIN_ALLOWLIST.items():
            assert len(reason) >= 12, f"{route_id} carries no usable reason: {reason!r}"


def _stub_operation(path: str, *dependency_names: str, module: str = "app.api.v1.invented.router") -> Operation:
    """An Operation whose effective chain is exactly `dependency_names`.

    The probes below build a stub `route.dependant` rather than a handler
    signature, because the sweeps read the effective chain now. A probe built
    from a signature has `route=None`, `_authorisation_chain` returns `[]` for
    it, and every predicate under test answers the same way regardless of what
    it does — which is how the first version of this class came to leave the
    admin sweep provably unguarded (see the docstring below).
    """

    class _Call:
        def __init__(self, name: str) -> None:
            self.__qualname__ = name

    subs = [type("Sub", (), {"call": _Call(name), "dependencies": []})() for name in dependency_names]

    class _Route:
        dependant = type("D", (), {"dependencies": subs})()

    def _handler() -> None: ...

    _handler.__module__ = module
    return Operation("POST", path, _handler, _Route())


class TestTheGuardCanFail:
    """Falsification, in-process: an assertion nobody has seen fail proves nothing.

    **These probes were wrong for exactly one commit and the way they were wrong
    is the point of the class.** When the two sweeps moved from `inspect.signature`
    to the effective chain, these kept asserting the signature expressions — a
    different statement from the one the sweeps now make. Measured by mutation at
    the time: replacing the body of `_resolves_bare_user` with `return False`
    left **all 84 tests in this file green**. `_ADMIN_ALLOWLIST` is empty by
    design, so the admin sweep had no other control either, and a typo making it
    constant-`False` would have shipped in silence.

    Every probe below therefore drives the predicate the sweep drives, by name.
    """

    def test_a_bare_tenant_route_is_reported(self):
        operation = _stub_operation("/api/v1/t/{tenant_slug}/invented", "get_current_tenant")
        assert _resolves_bare_tenant_context(operation)
        assert operation.id not in _TENANT_ALLOWLIST

    def test_a_role_gated_tenant_route_is_not_reported(self):
        """The control: a predicate that reports everything is as useless as one that reports nothing."""
        operation = _stub_operation(
            "/api/v1/t/{tenant_slug}/invented",
            "get_current_tenant",
            "require_permission.<locals>._check",
        )
        assert not _resolves_bare_tenant_context(operation)

    def test_a_bare_admin_route_is_reported(self):
        operation = _stub_operation("/api/v1/admin/invented", "get_current_user")
        assert _resolves_bare_user(operation)
        assert operation.id not in _ADMIN_ALLOWLIST

    def test_a_platform_admin_route_is_not_reported(self):
        """The admin sweep's only control — `_ADMIN_ALLOWLIST` is empty, so nothing else drives it."""
        operation = _stub_operation("/api/v1/admin/invented", "get_current_user", "require_platform_admin")
        assert not _resolves_bare_user(operation)

    def test_an_unauthenticated_route_is_reported_by_the_third_question(self):
        operation = _stub_operation("/api/v1/invented", "get_fertilizer_service")
        assert not _resolves_authorisation(operation)

    def test_the_three_predicates_disagree_on_the_same_operation(self):
        """They ask different questions, and a rewrite that collapsed them would show here.

        A tenant route behind bare `get_current_tenant`: reported by sweep 1,
        satisfied by sweep 3, untouched by sweep 2. If any two of these ever
        answer identically for every input, two of the three are redundant and one
        of them is not doing the job its name claims.
        """
        operation = _stub_operation("/api/v1/t/{tenant_slug}/invented", "get_current_tenant")
        assert _resolves_bare_tenant_context(operation)
        assert _resolves_authorisation(operation)
        assert not _resolves_bare_user(operation)


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


class TestEveryWriteOperationResolvesSomeAuthorisation:
    """The third question (#1402): is ANYTHING gating this route?

    The two sweeps above ask whether a specific weak dependency is present. This
    one asks whether any authorisation is, which is the question that catches a
    route carrying none — the case that passed both of them silently, 24 times.
    """

    def test_no_write_operation_is_reachable_without_authorisation(self):
        offenders = [
            op
            for op in mounted_write_operations()
            if not _resolves_authorisation(op) and op.id not in _PUBLIC_ALLOWLIST
        ]
        assert not offenders, (
            "These write operations resolve no authorisation dependency anywhere in their "
            "effective chain — not on the handler, not on their router, not on a parent "
            "router. Gate them, or add them to _PUBLIC_ALLOWLIST with a reason that "
            "survives the question 'why may an anonymous caller do this?':\n  " + _format(offenders)
        )

    def test_every_public_entry_still_exists_and_is_still_public(self):
        """Both halves of the obsolescence rule, and the second is the one that rots.

        An entry naming a route that was since gated would go on excusing a gate
        nobody needs excused, and the next reader takes it as a decision. The
        same rule `check_layer_imports` and `check_route_role_guards` follow.
        """
        by_id = {op.id: op for op in mounted_write_operations()}
        stale = []
        for route_id in _PUBLIC_ALLOWLIST:
            operation = by_id.get(route_id)
            if operation is None:
                stale.append(f"{route_id}: no longer mounted")
            elif _resolves_authorisation(operation):
                stale.append(f"{route_id}: now resolves authorisation — drop the entry")
        assert not stale, "Obsolete _PUBLIC_ALLOWLIST entries:\n  " + "\n  ".join(stale)

    def test_every_reason_is_written_out(self):
        for route_id, reason in _PUBLIC_ALLOWLIST.items():
            assert len(reason) >= 12, f"{route_id} carries no usable reason: {reason!r}"

    def test_the_allowlist_is_small(self):
        """A ceiling, because the cheapest way to make this test green is to grow the list.

        Ten entries today, all of them pre-session endpoints or a published probe.
        A twelfth is not automatically wrong, but it should cost a conversation.
        """
        assert len(_PUBLIC_ALLOWLIST) <= 12, (
            f"_PUBLIC_ALLOWLIST has grown to {len(_PUBLIC_ALLOWLIST)} entries. "
            "Adding a route here makes it anonymously reachable; say why in the issue, not only in the dict."
        )


class TestTheThirdQuestionCanFail:
    """Falsifiability for the question above — a sweep that cannot report is not a gate.

    `TestTheGuardCanFail` does this for the first two questions. This one exists
    because the third question is the one that was missing, and a question added
    to close a hole is exactly the kind that gets added inert.
    """

    def test_a_router_level_gate_counts_as_authorisation(self):
        """The positive control, and it is not decoration.

        The fourteen routes #1402 gated were fixed at the ROUTER, not the handler.
        Read through `inspect.signature` they still name no auth parameter, so a
        per-handler implementation of this question would report them as open
        forever and the triage would never end.
        """
        by_id = {op.id: op for op in mounted_write_operations()}
        operation = by_id["calculations.router.calc_vpd"]
        assert operation.dependencies == {} or "ctx" not in operation.dependencies
        assert _resolves_authorisation(operation), (
            "calc_vpd is gated by APIRouter(dependencies=[Depends(get_current_user)]); "
            "if this fails, the question reads the handler signature and not the effective chain"
        )

    def test_an_ungated_operation_would_be_reported(self):
        """The negative control, built rather than found — the tree has none left."""

        class _NoDependencies:
            dependencies: list[Any] = []

        class _BareRoute:
            dependant = _NoDependencies()

        def _probe() -> None: ...

        _probe.__module__ = "app.api.v1.calculations.router"
        operation = Operation("POST", "/api/v1/calculations/probe", _probe, _BareRoute())
        assert not _resolves_authorisation(operation)
        assert operation.id not in _PUBLIC_ALLOWLIST

    def test_a_non_authorising_dependency_does_not_count(self):
        """A service dependency must not read as authorisation.

        The first version of this file matched substrings, and `"api_key"` matched
        the `APIKeyHeader` scheme object while `"mcp_"` matched
        `require_mcp_enabled`. Both authorise nobody. This probes the real
        classification rather than a hand-picked name.
        """

        def _service_dependency() -> None: ...

        _service_dependency.__qualname__ = "get_fertilizer_service"

        class _Sub:
            call = _service_dependency
            dependencies: list[Any] = []

        class _Route:
            dependant = type("D", (), {"dependencies": [_Sub()]})()

        def _probe() -> None: ...

        _probe.__module__ = "app.api.v1.calculations.router"
        operation = Operation("POST", "/x", _probe, _Route())
        assert _authorisation_chain(operation) == ["get_fertilizer_service"]
        assert not _resolves_authorisation(operation)


class TestTheClassificationItselfCannotDrift:
    """The vocabulary is an allowlist too, and allowlists rot (#1402).

    `_AUTHORISATION` decides what the three sweeps above believe a gate is. A new
    dependency named like one and classified as neither would be treated as
    infrastructure and silently stop counting — the same failure shape as a seed
    file outside a `check-jsonschema` hook or a write route outside a selector.
    """

    def test_every_auth_shaped_dependency_is_classified(self):
        seen: set[str] = set()
        for operation in mounted_write_operations():
            seen.update(_authorisation_chain(operation))

        unclassified = sorted(
            name
            for name in seen
            if any(shape in name.lower() for shape in _AUTH_SHAPED)
            and name not in _AUTHORISATION
            and name not in _NOT_AUTHORISATION
        )
        assert not unclassified, (
            "These dependencies are mounted on write routes and read like authorisation, but the "
            "sweeps classify them as neither. Add each to _AUTHORISATION if it refuses a caller, or "
            "to _NOT_AUTHORISATION with the reason it does not:\n  " + "\n  ".join(unclassified)
        )

    def test_the_two_sets_are_disjoint(self):
        overlap = _AUTHORISATION & frozenset(_NOT_AUTHORISATION)
        assert not overlap, f"classified as both: {sorted(overlap)}"

    def test_role_gates_are_a_subset_of_authorisation(self):
        assert _ROLE_GATES <= _AUTHORISATION

    def test_every_non_authorisation_reason_is_written_out(self):
        for name, reason in _NOT_AUTHORISATION.items():
            assert len(reason) >= 12, f"{name} carries no usable reason: {reason!r}"

    def test_the_shape_filter_matches_a_realistic_share_of_the_live_inventory(self):
        """Anchored to the app the guard reads, not to two literals.

        The first version asserted against the strings `"require_platform_admin"`
        and `"get_fertilizer_service"`. Narrowing `_AUTH_SHAPED` to `("require_",)`
        would still match that literal while the guard above quietly stopped
        scanning most of the inventory — both tests green, the classification
        vacuous. A floor over the real dependency names cannot be satisfied that
        way. Measured today: 20 of roughly 90 distinct names match.
        """
        seen: set[str] = set()
        for operation in mounted_write_operations():
            seen.update(_authorisation_chain(operation))

        matched = {name for name in seen if any(shape in name.lower() for shape in _AUTH_SHAPED)}
        assert len(matched) >= 12, (
            f"_AUTH_SHAPED matches only {len(matched)} of {len(seen)} dependency names mounted on write "
            "routes. It has been narrowed to the point where the classification guard scans almost "
            f"nothing: {sorted(matched)}"
        )
        assert len(matched) < len(seen), (
            "_AUTH_SHAPED matches every dependency name, so the classification guard would demand a "
            "decision on every service and repository in the tree. Too wide is also a failure."
        )

    def test_every_non_authorisation_entry_is_still_mounted(self):
        """The obsolescence rule, applied to the vocabulary as well as the routes.

        This file's central argument is that an allowlist without one rots.
        `_NOT_AUTHORISATION` is an allowlist — it says "this name looks like a
        gate and is not" — and until this test it had no such rule, so an entry
        for a dependency deleted from the app would have sat there indefinitely,
        excusing nothing and reading like a decision.

        A generous floor rather than an exact match: some entries are classified
        against names that appear on READ routes only, and the sweeps walk write
        routes. What must not happen is the set drifting wholesale out of the
        tree.
        """
        seen: set[str] = set()
        for operation in mounted_write_operations():
            seen.update(_authorisation_chain(operation))

        mounted = {name for name in _NOT_AUTHORISATION if name in seen}
        assert len(mounted) >= len(_NOT_AUTHORISATION) // 2, (
            "More than half of _NOT_AUTHORISATION names no longer appear on any mounted write route. "
            "The set has drifted from the app it describes:\n  " + "\n  ".join(sorted(set(_NOT_AUTHORISATION) - seen))
        )

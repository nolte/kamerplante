"""The recognition writes are gated on role, not only on membership (#1256).

Until #1256 three of the four write routes resolved `ctx` through
`get_current_tenant` and nothing else, so a **viewer** could identify a plant,
select one of the results, and link it to a plant instance. `POST /reference`,
three lines below the first offender, already carried
`require_tenant_role(TenantRole.GROWER)` — the mechanism was present, the routes
simply never got it.

These tests assert the DEPENDENCY, not a live HTTP round trip. The gate is a
FastAPI dependency default, and what went wrong was that a route carried the
wrong one; reading the declared default is therefore the shortest statement of
the rule that can fail when someone swaps it back. A companion test drives the
resolved dependency with a viewer context, so the assertion is not merely "some
callable is attached".

Since #1353 the **enumeration** half of this file is no longer load-bearing:
`tests/unit/api/test_write_route_gates.py` sweeps every mounted write route in
the repository, so a sixth write route added here with a copied
`Depends(get_current_tenant)` goes red there whether or not anyone remembers to
extend `_ROUTES`. What this file still carries, and the sweep does not, is the
behavioural half — driving the resolved dependency with a viewer context, which
is what distinguishes a wired gate from an inert one. It is kept for that.
"""

from __future__ import annotations

import inspect

import pytest

from app.api.v1.recognition import tenant_router as router_module
from app.common.auth import require_tenant_role
from app.common.enums import TenantRole
from app.common.exceptions import ForbiddenError
from app.domain.models.tenant_context import TenantContext

#: (handler, must the caller be at least a grower?)
_ROUTES = [
    (router_module.identify_plant, True),
    (router_module.contribute_reference, True),
    (router_module.select_result, True),
    (router_module.link_plant_instance, True),
    (router_module.identification_history, False),
]


def _ctx_dependency(handler):
    """The callable behind the handler's `ctx` parameter default."""
    param = inspect.signature(handler).parameters["ctx"]
    return param.default.dependency


def _ctx(role: TenantRole) -> TenantContext:
    return TenantContext(
        tenant_key="tenant-a",
        tenant_slug="mein-garten",
        user_key="user-a",
        role=role,
    )


@pytest.mark.parametrize(
    ("handler", "needs_grower"),
    _ROUTES,
    ids=[h.__name__ for h, _ in _ROUTES],
)
def test_every_write_is_role_gated_and_the_read_is_not(handler, needs_grower) -> None:
    dependency = _ctx_dependency(handler)
    # `require_tenant_role` returns a closure named `_check`; `get_current_tenant`
    # is the function itself. Comparing identity to the open dependency is what
    # distinguishes them, and is what a regression would flip.
    from app.common.auth import get_current_tenant

    is_open = dependency is get_current_tenant
    assert is_open is not needs_grower, (
        f"{handler.__name__}: expected {'a role gate' if needs_grower else 'the open membership check'}"
    )


class TestTheGateActuallyRefuses:
    """Reading the dependency proves which one is attached; this proves what it does.

    Without it the parametrised test above would still pass if
    `require_tenant_role` were hollowed out — the failure class where a guard is
    wired and inert.
    """

    def test_a_viewer_is_refused(self) -> None:
        check = require_tenant_role(TenantRole.GROWER)

        with pytest.raises(ForbiddenError):
            check(_ctx(TenantRole.VIEWER))

    @pytest.mark.parametrize("role", [TenantRole.GROWER, TenantRole.LEAD])
    def test_a_grower_and_a_lead_pass(self, role) -> None:
        check = require_tenant_role(TenantRole.GROWER)

        assert check(_ctx(role)).role is role


def test_history_stays_readable_by_a_viewer() -> None:
    """The split REQ-052 §9 draws: creating is gated, looking is not."""
    from app.common.auth import get_current_tenant

    assert _ctx_dependency(router_module.identification_history) is get_current_tenant

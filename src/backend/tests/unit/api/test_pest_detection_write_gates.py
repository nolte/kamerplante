"""The pest-detection writes are gated on role, not only on membership (#1333).

Three of the four write routes in
``app/api/v1/pest_detection/tenant_router.py`` resolved ``ctx`` through
``get_current_tenant`` and nothing else, while the fourth — ``create-inspection``,
in the same file — already carried ``require_permission(IPM_TREATMENT, CREATE)``.
So a **viewer** could upload an image that leaves the installation for a
third-party recognition service, do it in a loop, and alter the recorded outcome
of someone else's detection through ``feedback``.

That is #1256's argument for ``POST /identification/identify`` applied to the
same shape, and the sibling drift sat inside a single file — the class #948 cost
this repository months on.

These tests assert the DEPENDENCY, not a live HTTP round trip, for the reason
``test_recognition_write_gates`` states: the gate *is* a FastAPI dependency
default, and what goes wrong is a route carrying the wrong one. The companion
class then drives the resolved dependency with a viewer context, so a hollowed-out
``require_tenant_role`` cannot leave these green — the "wired but inert" failure.

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

from app.api.v1.pest_detection import tenant_router as router_module
from app.common.auth import get_current_tenant
from app.common.enums import TenantRole
from app.common.exceptions import ForbiddenError
from app.domain.models.tenant_context import TenantContext

#: (handler, must the caller be more than a bare member?)
#:
#: ``create_inspection`` is gated through ``require_permission`` rather than
#: ``require_tenant_role``; it is listed because the question here is "is this
#: route open to any member", which both mechanisms answer no to. Leaving it out
#: would let the file's one already-gated route drift back unnoticed — which is
#: precisely how the other three were left behind.
_ROUTES = [
    (router_module.detect_pests_global, True),
    (router_module.detect_pests, True),
    (router_module.submit_feedback, True),
    (router_module.create_inspection, True),
    (router_module.pest_detection_status, False),
    (router_module.detection_history, False),
]


def _ctx_dependency(handler):
    """The callable behind the handler's ``ctx`` parameter default."""
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
    ("handler", "needs_gate"),
    _ROUTES,
    ids=[h.__name__ for h, _ in _ROUTES],
)
def test_every_write_is_gated_and_the_reads_are_not(handler, needs_gate) -> None:
    dependency = _ctx_dependency(handler)
    # Both gate factories return a closure named `_check`; `get_current_tenant`
    # is the function itself. Identity against the open dependency is what
    # separates them, and what a regression would flip back.
    is_open = dependency is get_current_tenant
    assert is_open is not needs_gate, (
        f"{handler.__name__}: expected {'a role gate' if needs_gate else 'the open membership check'}"
    )


_GATED = [handler for handler, needs_gate in _ROUTES if needs_gate]


class TestTheGateActuallyRefuses:
    """Reading the dependency proves *a* gate is attached; this drives the one
    that is. A freshly built ``require_tenant_role(GROWER)`` would prove nothing
    about the route — a route re-gated at ``VIEWER`` left that shape green."""

    @pytest.mark.parametrize("handler", _GATED, ids=[h.__name__ for h in _GATED])
    def test_a_viewer_is_refused_by_the_attached_gate(self, handler) -> None:
        with pytest.raises(ForbiddenError):
            _ctx_dependency(handler)(_ctx(TenantRole.VIEWER))

    @pytest.mark.parametrize("handler", _GATED, ids=[h.__name__ for h in _GATED])
    @pytest.mark.parametrize("role", [TenantRole.GROWER, TenantRole.LEAD])
    def test_a_grower_and_a_lead_pass_the_attached_gate(self, handler, role) -> None:
        assert _ctx_dependency(handler)(_ctx(role)).role is role


def test_the_two_reads_stay_open_to_a_viewer() -> None:
    """The split REQ-049 §2.3 draws: writing is gated, looking is not.

    ``/status`` in particular must stay open, and not only because it is a read:
    the frontend uses it to decide whether to show the capture button at all. A
    gate there would hide the feature's *existence* from a viewer rather than its
    action, and would turn a disabled-feature answer into a role answer.
    """
    assert _ctx_dependency(router_module.pest_detection_status) is get_current_tenant
    assert _ctx_dependency(router_module.detection_history) is get_current_tenant

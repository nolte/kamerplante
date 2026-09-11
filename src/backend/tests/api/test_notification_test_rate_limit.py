"""`POST /t/{slug}/notifications/test` spends a bounded budget (#1353).

The route's docstring promised "Rate limited to 5 requests per hour per user"
while `grep -c limiter` over the module returned **0** — a control certified in
prose and absent in code, found by the write-route sweep. The limit is real now,
and this file is what keeps it real: every other rate limit in this repository
has a test that drives the budget to refusal, and a limit whose only evidence is
a decorator is one refactor away from the state it was just repaired from.

Two things are asserted separately, because they fail separately:

* the budget is granted and then refused — the limit exists;
* a refused call never reaches `NotificationService.send_test` — the limit is in
  front of the work, not behind it. A 429 returned after the notification went
  out would satisfy the first assertion and defeat the purpose.

**Per client address, not per user.** The shared `limiter` keys on
`resolve_client_ip` (#1130). The docstring and the setting both say so; this file
does not pretend otherwise, and the budget it spends is one bucket for the whole
test client.
"""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.common.auth import get_current_tenant
from app.common.dependencies import get_notification_service
from app.common.enums import TenantRole
from app.config.settings import settings
from app.domain.models.tenant_context import TenantContext

TENANT_SLUG = "mein-garten"


def _allowed_calls() -> int:
    """The configured budget, read from settings rather than hard-coded.

    A literal here would pass while the setting drifted, which is the failure the
    docstring this file exists for already demonstrated once.
    """
    return int(settings.rate_limit_notification_test.split("/")[0])


def _ctx() -> TenantContext:
    return TenantContext(
        tenant_key="tenant-a",
        tenant_slug=TENANT_SLUG,
        user_key="user-a",
        role=TenantRole.GROWER,
    )


@pytest.fixture
def service() -> MagicMock:
    """One instance for the whole test, so call counts across requests add up.

    A factory minting a fresh mock per request would make the "never reached"
    assertion trivially true — a test that measures nothing.
    """
    notification_service = MagicMock()
    notification_service.send_test = AsyncMock(return_value={"status": "delivered", "success": True, "error": None})
    return notification_service


@pytest.fixture
def client(service: MagicMock) -> Iterator[TestClient]:
    # The budget is process-global state; `tests/api/conftest.py`'s autouse
    # `reset_rate_limiter` clears it around every test (#989), so this module
    # neither inherits a spent counter nor leaves one behind.
    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

        app.dependency_overrides[get_notification_service] = lambda: service
        app.dependency_overrides[get_current_tenant] = _ctx
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_notification_service, None)
            app.dependency_overrides.pop(get_current_tenant, None)


def _send_test(client: TestClient):  # noqa: ANN202 - httpx Response
    return client.post(
        f"/api/v1/t/{TENANT_SLUG}/notifications/test",
        json={"channel_key": "email"},
    )


class TestTheTestNotificationIsRateLimited:
    def test_the_budget_is_granted_then_refused(self, client: TestClient) -> None:
        allowed = [_send_test(client) for _ in range(_allowed_calls())]
        refused = _send_test(client)

        assert {response.status_code for response in allowed} == {200}
        assert refused.status_code == 429

    def test_a_refused_call_sends_no_notification(self, client: TestClient, service: MagicMock) -> None:
        """The point of the limit: the service is never reached, so nothing goes out."""
        for _ in range(_allowed_calls()):
            _send_test(client)
        assert service.send_test.await_count == _allowed_calls()

        refused = _send_test(client)

        assert refused.status_code == 429
        assert service.send_test.await_count == _allowed_calls()

    def test_the_budget_is_the_configured_one(self) -> None:
        """A hard-coded literal in the router would drift from the setting.

        Reads the limit off the registered route rather than off the source, so a
        decorator that was removed or reordered fails here too — which is the
        regression this route already had once, in prose form.
        """
        from app.api.v1.auth.router import limiter

        registered = {key: value for key, value in limiter._route_limits.items() if "send_test_notification" in key}
        assert registered, "no limit registered for send_test_notification — the decorator is gone or inert"
        limits = [str(limit.limit) for limits_ in registered.values() for limit in limits_]
        assert any(str(_allowed_calls()) in limit for limit in limits), (
            f"registered limits {limits} do not carry the configured budget {settings.rate_limit_notification_test}"
        )

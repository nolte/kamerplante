"""API-tier fixtures.

Both fixtures here are autouse and both exist for the same reason: process state
that one test can leave behind for another. ``block_datastore_access`` catches a
missing dependency override, ``reset_rate_limiter`` the shared rate-limit
counters (#989).

Carries the same datastore guard as the unit tier (#978). The tier builds the
real FastAPI app, but it drives it through ``dependency_overrides`` against
fakes — so a connection here means an override is missing, which is a wiring bug
of exactly the kind the guard exists to name. Measured before switching it on:
of 682 api+contracts tests, none reached ArangoDB or TimescaleDB and two reached
the Celery broker.
"""

from collections.abc import Iterator

import pytest

from app.api.v1.auth.router import limiter
from tests.support import db_guard


@pytest.fixture(autouse=True)
def block_datastore_access(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any real datastore connection from an API test fail immediately."""
    db_guard.install_unless_marked(request, monkeypatch, tier="api")


@pytest.fixture(autouse=True)
def restore_dependency_overrides() -> Iterator[None]:
    """Hand every API test the app's real dependency graph, and hand it back (#1402).

    ``app.main.app`` is a module-level singleton, so ``app.dependency_overrides``
    is process state exactly like the rate-limit counters below — and until this
    fixture existed, a module that installed an override and had no teardown left
    it in place for every test that ran afterwards.

    The failure that shape produces is the dangerous kind: it makes later tests
    **pass**. A file that substitutes a permissive auth provider and never removes
    it turns a subsequent "an expired token is refused" assertion into a 200 as
    somebody else's user, and the suite reports green. It was found by the
    pre-merge review of #1402, where two files that had to authenticate their
    calls installed exactly that and returned the client without a ``finally``.

    Restoring a *copy* rather than clearing: a fixture that emptied the dict would
    also discard overrides a session- or class-scoped fixture installed on
    purpose, which is a different bug in the opposite direction.
    """
    from unittest.mock import patch

    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

    snapshot = dict(app.dependency_overrides)
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(snapshot)


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> Iterator[None]:
    """Hand every API test the full rate-limit budget, and hand it back (#989).

    ``app.api.v1.auth.router.limiter`` is a single process-global SlowAPI
    instance — the only one the app builds — and SlowAPI counts against the
    *decorating* instance, not against ``app.state.limiter``. So the counters are
    module state shared by every test in the session, and under ``TestClient``
    every caller is the same IP (``testclient``) hitting the same path, i.e. the
    same bucket. Per-minute windows mostly hid that: a window that expires inside
    one module cannot reach the next. ``rate_limit_email_change`` is hourly and
    outlives a whole run, so a module that spends the budget makes the *next*
    module fail — a flake whose failing test is never the one at fault.

    Per test, not per module: the modules that assert a limit exists exhaust the
    budget deliberately *inside* a single test (see
    ``test_privacy_email_change_rate_limit`` and ``test_service_account_validate``),
    so resetting at the test boundary leaves them intact while still stopping the
    spend at the module boundary. Resetting per module would not: two such tests
    in one module already collide.

    ``enabled`` is restored for the same reason the counters are. Modules that
    would otherwise leak a lingering ``threading.Timer`` turn the limiter off via
    ``monkeypatch`` (``test_ai_endpoints``, ``test_glossary_endpoints``); one that
    ever leaves it off would silently disarm every later rate-limit assertion,
    which is the worse failure — a passing test that certifies nothing.
    """
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()

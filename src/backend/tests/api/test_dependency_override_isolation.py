"""The autouse override-restore fixture actually restores (#1402).

`app.main.app` is a process-global singleton, so `app.dependency_overrides` is
shared state between every test in the session. `tests/api/conftest.py` snapshots
and restores it per test; this file is the falsifier for that, because a fixture
whose only evidence is "the suite is green" is indistinguishable from a fixture
that does nothing — the suite was green before it existed too.

The two tests below run in file order and the second depends on the first. That
is normally a smell; here it is the measurement. Stated out loud so nobody
"fixes" it into independence and leaves the fixture unproven.
"""

from unittest.mock import patch

import pytest


def _sentinel() -> str:
    return "leaked"


def _app():
    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

        return app


def test_a_test_may_install_an_override():
    from app.common.dependencies import get_auth_provider

    app = _app()
    app.dependency_overrides[get_auth_provider] = _sentinel
    assert app.dependency_overrides[get_auth_provider] is _sentinel


def test_the_next_test_does_not_inherit_it():
    """Red without the fixture, green with it.

    Counter-checked by deleting `restore_dependency_overrides` from
    `tests/api/conftest.py` and running this file: the assertion below fails with
    the sentinel still installed.
    """
    from app.common.dependencies import get_auth_provider

    app = _app()
    assert app.dependency_overrides.get(get_auth_provider) is not _sentinel, (
        "an override installed by the previous test survived into this one; "
        "conftest's restore_dependency_overrides fixture is gone or inert"
    )


@pytest.mark.parametrize("run", [1, 2])
def test_the_restore_is_per_test_not_per_module(run: int):
    """Two parametrised runs in the same module: the second must not see the first."""
    from app.common.dependencies import get_auth_provider

    app = _app()
    assert app.dependency_overrides.get(get_auth_provider) is not _sentinel
    app.dependency_overrides[get_auth_provider] = _sentinel

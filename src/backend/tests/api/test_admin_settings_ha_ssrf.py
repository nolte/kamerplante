"""API tests for the SEC-B3 SSRF guard on the HA "test connection" endpoint.

``POST /admin/settings/home-assistant/test`` dials a request-body-supplied URL with
the long-lived bearer token attached, so it is the most dangerous HA path. The URL
is validated against SSRF BEFORE any request:

  * an internal / cloud-metadata URL is rejected with 422 and ``httpx.get`` is
    never called (the token is never sent);
  * the cloud-metadata range stays blocked even with the private opt-in on;
  * a LAN URL is dialed when ``ha_allow_private_endpoint`` is set.
"""

import ipaddress
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.api.v1.admin.settings.router import router as settings_router
from app.common.auth import get_current_user, require_platform_admin
from app.common.dependencies import get_system_settings_service
from app.common.error_handlers import app_error_handler, validation_error_handler
from app.common.exceptions import KamerplanterError
from app.domain.models.system_settings import SystemSettings
from app.domain.services.system_settings_service import SystemSettingsService


def _admin_user() -> SimpleNamespace:
    return SimpleNamespace(key="user_admin")


def _service() -> SystemSettingsService:
    repo = MagicMock()
    repo.get.return_value = SystemSettings()
    repo.upsert.side_effect = lambda s: s
    return SystemSettingsService(repo)


def _build_app(service: SystemSettingsService) -> FastAPI:
    app = FastAPI()
    app.include_router(settings_router, prefix="/api/v1")
    app.add_exception_handler(KamerplanterError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.dependency_overrides[get_system_settings_service] = lambda: service
    app.dependency_overrides[get_current_user] = _admin_user
    # #1385 moved every operation in this router behind ``require_platform_admin``.
    # Overridden here because authorisation is not what this file measures — the
    # gate itself is swept in ``test_admin_settings_gating.py``.
    app.dependency_overrides[require_platform_admin] = _admin_user
    return app


@pytest.mark.parametrize(
    ("url", "ip"),
    [
        ("http://169.254.169.254", "169.254.169.254"),  # cloud metadata / IMDS
        ("http://homeassistant.local:8123", "192.168.1.50"),  # RFC1918 LAN
        ("http://ha.internal:8123", "127.0.0.1"),  # loopback
    ],
)
def test_ha_test_rejects_ssrf_url_without_dialing(monkeypatch, url, ip):
    """SEC-B3: internal HA URLs are refused (422) BEFORE ``httpx.get`` is dialed."""
    import app.api.v1.admin.settings.router as router_mod

    monkeypatch.setattr(router_mod.settings, "ha_allow_private_endpoint", False)
    with (
        patch(
            "app.common.url_safety._resolved_addresses",
            return_value=[ipaddress.ip_address(ip)],
        ),
        patch("app.api.v1.admin.settings.router.httpx.get") as mock_get,
    ):
        client = TestClient(_build_app(_service()))
        resp = client.post(
            "/api/v1/admin/settings/home-assistant/test",
            json={"ha_url": url, "ha_access_token": "secret-llat"},
        )
    assert resp.status_code == 422
    # The crucial assertion: the URL was never dialed, so the token never left.
    mock_get.assert_not_called()


def test_ha_test_always_blocks_metadata_even_with_private_optin(monkeypatch):
    """SEC-B3: the metadata / link-local range stays blocked even with opt-in."""
    import app.api.v1.admin.settings.router as router_mod

    monkeypatch.setattr(router_mod.settings, "ha_allow_private_endpoint", True)
    with (
        patch(
            "app.common.url_safety._resolved_addresses",
            return_value=[ipaddress.ip_address("169.254.169.254")],
        ),
        patch("app.api.v1.admin.settings.router.httpx.get") as mock_get,
    ):
        client = TestClient(_build_app(_service()))
        resp = client.post(
            "/api/v1/admin/settings/home-assistant/test",
            json={"ha_url": "http://169.254.169.254/latest/meta-data", "ha_access_token": "secret"},
        )
    assert resp.status_code == 422
    mock_get.assert_not_called()


def test_ha_test_dials_lan_url_with_private_optin(monkeypatch):
    """SEC-B3: a legitimate LAN HA is probed when the operator opts in."""
    import app.api.v1.admin.settings.router as router_mod

    monkeypatch.setattr(router_mod.settings, "ha_allow_private_endpoint", True)
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"message": "API running.", "version": "2026.1.0"}
    with (
        patch(
            "app.common.url_safety._resolved_addresses",
            return_value=[ipaddress.ip_address("192.168.1.50")],
        ),
        patch("app.api.v1.admin.settings.router.httpx.get", return_value=mock_resp) as mock_get,
    ):
        client = TestClient(_build_app(_service()))
        resp = client.post(
            "/api/v1/admin/settings/home-assistant/test",
            json={"ha_url": "http://homeassistant.local:8123", "ha_access_token": "secret"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["ha_version"] == "2026.1.0"
    mock_get.assert_called_once()

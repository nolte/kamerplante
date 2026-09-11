"""API tests for the REQ-029 Pl@ntNet admin settings endpoints.

Covers the GET masking + source reporting, the PUT/DELETE write paths, and
that ``/recognition/status`` reports ``available: true`` once a DB-only key is
set (no env key, no pod restart).
"""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.admin.settings.router import router as settings_router
from app.api.v1.recognition.router import router as recognition_router
from app.common.auth import get_current_user, require_platform_admin
from app.common.dependencies import (
    get_identification_service,
    get_system_settings_service,
)
from app.domain.models.system_settings import (
    HomeAssistantSettings,
    PlantIdentificationSettings,
    SystemSettings,
)
from app.domain.services.system_settings_service import SystemSettingsService


def _fake_user() -> MagicMock:
    user = MagicMock()
    user.key = "user_admin"
    return user


def _build_app(service: SystemSettingsService) -> FastAPI:
    app = FastAPI()
    app.include_router(settings_router, prefix="/api/v1")
    app.dependency_overrides[get_system_settings_service] = lambda: service
    app.dependency_overrides[get_current_user] = _fake_user
    # #1385 moved every operation in this router behind ``require_platform_admin``.
    # Overridden here because authorisation is not what this file measures — the
    # gate itself is swept in ``test_admin_settings_gating.py``.
    app.dependency_overrides[require_platform_admin] = _fake_user
    return app


def _set_storage_env_defaults(env: MagicMock) -> None:
    """Give a patched ``env_settings`` MagicMock real storage defaults.

    Since SEC-001 the general ``GET /admin/settings`` no longer embeds the
    storage block, but the patched service still reads ``env_settings.storage_*``
    elsewhere; a bare MagicMock would yield non-serialisable MagicMock values, so
    set realistic env defaults to keep the patched env consistent.
    """
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


def _service_with(db_key: str = "", env_key: str = "") -> SystemSettingsService:
    repo = MagicMock()
    stored = SystemSettings(
        plant_identification=PlantIdentificationSettings(plantnet_api_key=db_key),
    )
    repo.get.return_value = stored
    repo.upsert.side_effect = lambda s: s
    service = SystemSettingsService(repo)
    return service, repo, env_key


def test_get_settings_masks_db_key():
    service, _repo, _ = _service_with(db_key="super-secret-key-12345")
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = ""
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.get("/api/v1/admin/settings")
    assert resp.status_code == 200
    pi = resp.json()["plant_identification"]
    # NEVER return the plaintext key.
    assert pi["plantnet_api_key_masked"] == "****2345"
    assert "super-secret-key-12345" not in resp.text
    assert pi["source_plantnet_api_key"] == "db"


def test_get_settings_reports_env_source():
    service, _repo, _ = _service_with(db_key="")
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = "env-key-abcd"
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.get("/api/v1/admin/settings")
    pi = resp.json()["plant_identification"]
    assert pi["source_plantnet_api_key"] == "env"
    assert pi["plantnet_api_key_masked"] == "****abcd"


def test_get_settings_reports_none_source():
    service, _repo, _ = _service_with(db_key="")
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = ""
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.get("/api/v1/admin/settings")
    pi = resp.json()["plant_identification"]
    assert pi["source_plantnet_api_key"] == "none"
    assert pi["plantnet_api_key_masked"] == ""


def test_put_sets_key_and_returns_masked():
    service, repo, _ = _service_with(db_key="")
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = ""
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.put(
            "/api/v1/admin/settings/plant-identification",
            json={"plantnet_api_key": "brand-new-key-9999"},
        )
    assert resp.status_code == 200
    repo.upsert.assert_called_once()
    upserted = repo.upsert.call_args[0][0]
    assert upserted.plant_identification.plantnet_api_key == "brand-new-key-9999"


def test_delete_clears_db_key():
    service, repo, _ = _service_with(db_key="db-key-1234")
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = ""
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.delete("/api/v1/admin/settings/plant-identification")
    assert resp.status_code == 204
    repo.upsert.assert_called_once()
    upserted = repo.upsert.call_args[0][0]
    assert upserted.plant_identification.plantnet_api_key == ""


def test_recognition_status_available_with_db_only_key():
    """A DB-only key (no env key) must flip ``/recognition/status`` to available.

    Uses the REAL ``PlantNetAdapter`` + REAL ``IdentificationService.get_status``
    logic, with only the DB-backed settings service stubbed to return a key and
    the env key forced empty. This proves end-to-end that ``available`` becomes
    true from a DB-only key without a pod restart.
    """
    from app.data_access.external.plantnet_adapter import PlantNetAdapter
    from app.domain.services.identification_service import IdentificationService

    settings_service = MagicMock()
    settings_service.get_effective_plantnet_api_key.return_value = "db-only-key"

    adapter = PlantNetAdapter()

    registry = MagicMock()
    registry.all_keys.return_value = ["plantnet"]
    registry.get.return_value = adapter
    registry.get_preferred.return_value = adapter

    real_service = IdentificationService(
        engine=MagicMock(),
        identification_repo=MagicMock(),
        consent_repo=MagicMock(),
        consent_engine=MagicMock(),
        rate_limiter=MagicMock(),
        registry=registry,
    )

    app = FastAPI()
    app.include_router(recognition_router, prefix="/api/v1")
    app.dependency_overrides[get_identification_service] = lambda: real_service

    with patch(
        "app.common.dependencies.get_system_settings_service",
        return_value=settings_service,
    ):
        # adapter.is_configured() resolves the DB key at call time → True.
        assert adapter.is_configured() is True
        client = TestClient(app)
        resp = client.get("/api/v1/recognition/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["adapters"]["plantnet"]["configured"] is True


def test_unused_ha_settings_fixture_keeps_ha_intact():
    """The Pl@ntNet section must not disturb the HA part of the response."""
    repo = MagicMock()
    repo.get.return_value = SystemSettings(
        home_assistant=HomeAssistantSettings(ha_url="http://ha:8123"),
        plant_identification=PlantIdentificationSettings(plantnet_api_key="k12345"),
    )
    repo.upsert.side_effect = lambda s: s
    service = SystemSettingsService(repo)
    with patch("app.domain.services.system_settings_service.env_settings") as env:
        env.plantnet_api_key = ""
        env.ha_url = ""
        env.ha_access_token = ""
        env.ha_timeout = 10
        _set_storage_env_defaults(env)
        client = TestClient(_build_app(service))
        resp = client.get("/api/v1/admin/settings")
    body = resp.json()
    assert body["home_assistant"]["ha_url"] == "http://ha:8123"
    assert body["plant_identification"]["source_plantnet_api_key"] == "db"

import httpx
import structlog
from fastapi import APIRouter, Depends

from app.api.v1.admin.settings.schemas import (
    HASettingsResponse,
    HASettingsUpdate,
    HATestRequest,
    HATestResponse,
    PlantIdentificationSettingsResponse,
    PlantIdentificationSettingsUpdate,
    PlantIdentificationTestRequest,
    PlantIdentificationTestResponse,
    StorageSettingsResponse,
    StorageSettingsUpdate,
    StorageTestRequest,
    StorageTestResponse,
    SystemSettingsResponse,
)
from app.common.auth import require_platform_admin
from app.common.dependencies import get_ha_client, get_system_settings_service
from app.common.exceptions import ValidationError
from app.common.openapi_responses import AUTH_RESPONSES
from app.common.url_safety import validate_ha_url, validate_storage_endpoint_url
from app.config.settings import settings
from app.data_access.storage.registry import build_storage_test_adapter
from app.domain.models.user import User
from app.domain.services.system_settings_service import SystemSettingsService

logger = structlog.get_logger()

# Every operation in this router reads or changes INSTALLATION-WIDE configuration
# and is therefore gated by ``require_platform_admin`` (#1385). Until then the
# storage half carried the gate and the Home-Assistant / plant-identification half
# resolved its caller through ``get_current_user``, so any authenticated member of
# any tenant could read the installation's HA URL, replace its URL and token, and
# clear the plant-identification provider for everyone — the #948 class, a guard
# opted into at the call site and not opted into by the siblings.
#
# NOT ``require_admin_scope(AdminScope.TECHNICAL)``, which REQ-049 §2.4 puts on the
# orthogonal administrative axis: that dependency resolves a ``TenantContext``
# through ``get_current_tenant`` and is therefore tenant-bound. These paths carry
# no tenant, so gating them that way needs a tenant resolution invented for the
# purpose. ``admin/platform``, the sibling router, uses ``require_platform_admin``.
#
# A new endpoint here inherits nothing automatically. ``tests/api/test_admin_settings_gating.py``
# sweeps the list it declares; add the route there in the same change.
router = APIRouter(prefix="/admin/settings", tags=["admin-settings"], responses=AUTH_RESPONSES)


def _build_storage_response(service: SystemSettingsService) -> StorageSettingsResponse:
    info = service.get_storage_settings_with_source()
    return StorageSettingsResponse(
        backend=info["backend"],
        local_fs_root=info["local_fs_root"] or "",
        local_fs_public_base_url=info["local_fs_public_base_url"] or "",
        s3_endpoint_url=info["s3_endpoint_url"] or "",
        s3_region=info["s3_region"] or "",
        s3_bucket=info["s3_bucket"] or "",
        s3_use_path_style=bool(info["s3_use_path_style"]),
        s3_kms_key_id=info["s3_kms_key_id"] or "",
        s3_force_tls=bool(info["s3_force_tls"]),
        s3_access_key_id_configured=info["s3_access_key_id_configured"],
        s3_secret_access_key_configured=info["s3_secret_access_key_configured"],
        source_backend=info["source_backend"],
        source_local_fs_root=info["source_local_fs_root"],
        source_local_fs_public_base_url=info["source_local_fs_public_base_url"],
        source_s3_endpoint_url=info["source_s3_endpoint_url"],
        source_s3_region=info["source_s3_region"],
        source_s3_bucket=info["source_s3_bucket"],
        source_s3_use_path_style=info["source_s3_use_path_style"],
        source_s3_kms_key_id=info["source_s3_kms_key_id"],
        source_s3_force_tls=info["source_s3_force_tls"],
    )


def _build_response(service: SystemSettingsService) -> SystemSettingsResponse:
    info = service.get_ha_settings_with_source()
    plantnet = service.get_plantnet_settings_with_source()
    return SystemSettingsResponse(
        home_assistant=HASettingsResponse(
            ha_url=info["ha_url"] or "",
            ha_access_token_masked=service.mask_token(info["ha_access_token"]),
            ha_timeout=info["ha_timeout"],
            source_ha_url=info["source_ha_url"],
            source_ha_access_token=info["source_ha_access_token"],
            source_ha_timeout=info["source_ha_timeout"],
        ),
        plant_identification=PlantIdentificationSettingsResponse(
            plantnet_api_key_masked=service.mask_token(plantnet["plantnet_api_key"]),
            source_plantnet_api_key=plantnet["source_plantnet_api_key"],
        ),
    )


@router.get("", response_model=SystemSettingsResponse)
def get_settings(
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Return the effective installation settings — platform-admin only (#1385).

    The HA token and the Pl@ntNet key are masked here and always were; the HA
    **URL** is not, and it is an internal address in most installations. That is
    the disclosure this gate closes, alongside the write operations below.
    """
    return _build_response(service)


@router.get("/storage", response_model=StorageSettingsResponse)
def get_storage_settings(
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Return the storage-infra config — platform-admin only (SEC-001).

    The storage block (endpoint, region, bucket, KMS key, credential-presence
    flags) is infrastructure disclosure and is therefore kept out of the general
    ``GET /admin/settings`` payload rather than merely behind the same gate. Both
    are platform-admin only since #1385; the separation predates that and still
    holds, because two readers of one payload are how a field ends up disclosed
    to the wider of the two audiences.
    """
    return _build_storage_response(service)


@router.put("/home-assistant", response_model=SystemSettingsResponse)
def update_ha_settings(
    body: HASettingsUpdate,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Update the Home Assistant connection settings."""
    service.update_ha_settings(
        ha_url=body.ha_url,
        ha_access_token=body.ha_access_token,
        ha_timeout=body.ha_timeout,
    )
    _sync_ha_notification_channel()
    return _build_response(service)


@router.post("/home-assistant/test", response_model=HATestResponse)
def test_ha_connection(
    body: HATestRequest,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Test HA connection using provided values or effective settings."""
    effective = service.get_effective_ha_settings()
    url = body.ha_url or effective["ha_url"]
    token = body.ha_access_token or effective["ha_access_token"]
    timeout = body.ha_timeout or effective["ha_timeout"]

    if not url:
        return HATestResponse(success=False, message="No Home Assistant URL configured.")

    # SEC-B3: this is the most dangerous path — the URL is taken straight from the
    # request body and dialed with the bearer token attached. Validate against SSRF
    # BEFORE any request so the token is never sent to an internal/metadata address.
    validate_ha_url(str(url), allow_private=settings.ha_allow_private_endpoint)

    try:
        resp = httpx.get(
            f"{str(url).rstrip('/')}/api/",
            headers={"Authorization": f"Bearer {token}"} if token else {},
            timeout=int(timeout),
        )
        resp.raise_for_status()
        data = resp.json()
        return HATestResponse(
            success=True,
            message=data.get("message", "Connection successful."),
            ha_version=data.get("version"),
        )
    except httpx.ConnectError:
        return HATestResponse(success=False, message="Cannot connect to Home Assistant.")
    except httpx.TimeoutException:
        return HATestResponse(success=False, message="Connection to Home Assistant timed out.")
    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code}: Home Assistant returned an error."
        return HATestResponse(success=False, message=msg)
    except Exception:
        return HATestResponse(success=False, message="An unexpected error occurred while testing the connection.")


@router.delete("/home-assistant", status_code=204)
def delete_ha_settings(
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Remove the stored Home Assistant settings, falling back to env values."""
    service.delete_ha_settings()
    _sync_ha_notification_channel()


# ── REQ-029 Pl@ntNet / plant identification ─────────────────────────
#
# The Pl@ntNet key is instance-wide (free-tier key for the whole instance,
# not tenant-scoped), so write/test/delete require platform-admin rights —
# consistent with the ``admin/platform`` endpoints.


@router.put("/plant-identification", response_model=SystemSettingsResponse)
def update_plant_identification_settings(
    body: PlantIdentificationSettingsUpdate,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Set the instance-wide Pl@ntNet API key (DB overrides the env value)."""
    service.update_plant_identification_settings(plantnet_api_key=body.plantnet_api_key)
    return _build_response(service)


@router.post("/plant-identification/test", response_model=PlantIdentificationTestResponse)
def test_plant_identification(
    body: PlantIdentificationTestRequest,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Validate a Pl@ntNet key against the API (provided value or effective key)."""
    api_key = body.plantnet_api_key or service.get_effective_plantnet_api_key()
    if not api_key:
        return PlantIdentificationTestResponse(
            success=False,
            message="No Pl@ntNet API key configured.",
        )

    try:
        resp = httpx.get(
            f"{settings.plantnet_base_url.rstrip('/')}/projects",
            params={"api-key": api_key, "lang": "en"},
            timeout=settings.identification_http_timeout,
        )
        if resp.status_code in (401, 403):
            return PlantIdentificationTestResponse(
                success=False,
                message="Pl@ntNet rejected the API key.",
            )
        resp.raise_for_status()
        return PlantIdentificationTestResponse(
            success=True,
            message="Pl@ntNet API key is valid.",
        )
    except httpx.ConnectError:
        return PlantIdentificationTestResponse(success=False, message="Cannot connect to Pl@ntNet.")
    except httpx.TimeoutException:
        return PlantIdentificationTestResponse(success=False, message="Connection to Pl@ntNet timed out.")
    except httpx.HTTPStatusError as exc:
        # NEVER include str(exc): an httpx message embeds the request URL,
        # which carries the ``api-key`` query parameter (a secret).
        return PlantIdentificationTestResponse(
            success=False,
            message=f"HTTP {exc.response.status_code}: Pl@ntNet returned an error.",
        )
    except Exception:
        return PlantIdentificationTestResponse(
            success=False,
            message="An unexpected error occurred while testing the key.",
        )


@router.delete("/plant-identification", status_code=204)
def delete_plant_identification_settings(
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Remove the DB Pl@ntNet key so resolution falls back to the env value."""
    service.delete_plant_identification_settings()


# ── NFR-013 Object storage backend selection ────────────────────────
#
# The storage backend is an instance-wide operator decision (NFR-013 §4.1), so
# these endpoints require platform-admin rights via ``require_platform_admin``.
# In light mode (REQ-027) there is no platform tenant; ``require_platform_admin``
# already treats the single anonymous system user as the operator/admin
# (app/common/auth.py), so the same dependency works in BOTH modes — the router
# itself is mode-agnostic and is registered once for both.
#
# SECRETS (NFR-013 §4.1, variant "a"): the S3 access key / secret are NOT
# accepted, persisted or returned here. They come exclusively from env /
# External Secrets Operator. The update payload carries only non-secret fields.


@router.put("/storage", response_model=StorageSettingsResponse)
def update_storage_settings(
    body: StorageSettingsUpdate,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Set the active storage backend + its non-secret config (DB overrides env).

    Returns the storage block only (SEC-001): the general system-settings
    response no longer carries storage, and this endpoint is already
    platform-admin gated, so the caller gets the freshly-persisted storage config
    back directly.
    """
    try:
        service.update_storage_settings(
            backend=body.backend,
            local_fs_root=body.local_fs_root,
            local_fs_public_base_url=body.local_fs_public_base_url,
            s3_endpoint_url=body.s3_endpoint_url,
            s3_region=body.s3_region,
            s3_bucket=body.s3_bucket,
            s3_use_path_style=body.s3_use_path_style,
            s3_kms_key_id=body.s3_kms_key_id,
            s3_force_tls=body.s3_force_tls,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return _build_storage_response(service)


@router.post("/storage/test", response_model=StorageTestResponse)
async def test_storage_connection(
    body: StorageTestRequest,
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Probe a backend (effective config + optional not-yet-saved overrides).

    Builds a throwaway adapter and runs ``health_check()``. The S3 credentials
    are injected from env / ESO inside the registry — never from this request —
    so the test neither accepts nor echoes a secret. The response message NEVER
    contains credentials or signed URLs (NFR-013 §9.2).
    """
    effective = service.get_effective_storage_settings()
    # Layer the not-yet-persisted overrides on top of the effective config.
    config = dict(effective)
    for field in (
        "backend",
        "local_fs_root",
        "local_fs_public_base_url",
        "s3_endpoint_url",
        "s3_region",
        "s3_bucket",
        "s3_use_path_style",
        "s3_kms_key_id",
        "s3_force_tls",
    ):
        value = getattr(body, field)
        if value is not None:
            config[field] = value

    backend = config.get("backend") or settings.storage_backend

    # SEC-002 (SSRF): the S3 endpoint is fully operator-supplied and dialed
    # server-side. In light mode the anonymous system user is the "operator", so
    # without this guard any internal URL (IMDS 169.254.169.254, ArangoDB,
    # RFC1918) could be probed. Validate the *effective* endpoint before building
    # the adapter. Link-local/metadata is always blocked; private/loopback (legit
    # in-cluster MinIO / localhost) only when explicitly opted in.
    if backend == "s3":
        endpoint = config.get("s3_endpoint_url") or settings.storage_s3_endpoint_url
        if endpoint:
            try:
                validate_storage_endpoint_url(
                    endpoint,
                    field="s3_endpoint_url",
                    allow_private=settings.storage_s3_allow_private_endpoint,
                )
            except ValidationError:
                logger.warning("storage_test_endpoint_rejected_ssrf", backend=backend)
                return StorageTestResponse(
                    success=False,
                    backend=backend,
                    message="Storage endpoint is not allowed.",
                )

    try:
        adapter = build_storage_test_adapter(config)
        status = await adapter.health_check()
    except ValueError as exc:
        # e.g. force_tls rejecting a plain-HTTP endpoint — message is safe.
        return StorageTestResponse(success=False, backend=backend, message=str(exc))
    except Exception:  # noqa: BLE001 — never surface backend internals/secrets
        logger.warning("storage_test_failed", backend=backend)
        return StorageTestResponse(
            success=False,
            backend=backend,
            message="Storage backend is not reachable with the current configuration.",
        )

    ready = bool(status.get("ready"))
    if backend == "local-fs":
        message = "Storage path is writable." if ready else "Storage path is not writable."
        return StorageTestResponse(success=ready, backend=backend, message=message, writable=ready)
    message = "Bucket is reachable." if ready else "Bucket is not reachable."
    return StorageTestResponse(success=ready, backend=backend, message=message, bucket_reachable=ready)


@router.delete("/storage", status_code=204)
def delete_storage_settings(
    _current_user: User = Depends(require_platform_admin),
    service: SystemSettingsService = Depends(get_system_settings_service),
):
    """Clear the DB storage override so resolution falls back to env vars."""
    service.delete_storage_settings()


def _sync_ha_notification_channel() -> None:
    """Re-register or remove the HA notification channel after settings change."""
    from app.data_access.external.ha_notification_channel import HomeAssistantNotificationChannel
    from app.domain.engines.notification_channel_registry import NotificationChannelRegistry

    ha_client = get_ha_client()
    if ha_client is not None:
        NotificationChannelRegistry.register(HomeAssistantNotificationChannel(ha_client))
    else:
        # Remove stale channel if HA was unconfigured
        NotificationChannelRegistry.unregister("home_assistant")

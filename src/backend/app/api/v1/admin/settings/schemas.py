from typing import Literal

from pydantic import BaseModel, Field


class HASettingsUpdate(BaseModel):
    ha_url: str | None = None
    ha_access_token: str | None = None
    ha_timeout: int | None = Field(default=None, ge=1, le=120)


class HASettingsResponse(BaseModel):
    ha_url: str
    ha_access_token_masked: str
    ha_timeout: int
    source_ha_url: str
    source_ha_access_token: str
    source_ha_timeout: str


class PlantIdentificationSettingsResponse(BaseModel):
    """Masked Pl@ntNet key plus its source (``db``/``env``/``none``)."""

    plantnet_api_key_masked: str
    source_plantnet_api_key: str


class StorageSettingsResponse(BaseModel):
    """Effective object-storage config (NFR-013 §4.1) for the admin UI.

    Carries only **non-secret** fields. The S3 credentials are never returned —
    only their *presence* (``s3_access_key_id_configured`` /
    ``s3_secret_access_key_configured``), because they live in env / ESO and
    must not leak through the API (NFR-013 §4.1, §9.2).
    """

    backend: str
    local_fs_root: str
    local_fs_public_base_url: str
    s3_endpoint_url: str
    s3_region: str
    s3_bucket: str
    s3_use_path_style: bool
    s3_kms_key_id: str
    s3_force_tls: bool
    # Credential presence flags (never the values).
    s3_access_key_id_configured: bool
    s3_secret_access_key_configured: bool
    # Per-field source (``db`` = UI override, ``env`` = environment / ESO).
    source_backend: str
    source_local_fs_root: str
    source_local_fs_public_base_url: str
    source_s3_endpoint_url: str
    source_s3_region: str
    source_s3_bucket: str
    source_s3_use_path_style: str
    source_s3_kms_key_id: str
    source_s3_force_tls: str


class StorageSettingsUpdate(BaseModel):
    """Update payload for the active backend + its non-secret fields.

    Deliberately carries **no** ``s3_access_key_id`` / ``s3_secret_access_key``
    field: secrets are configured exclusively via env / External Secrets
    Operator (NFR-013 §4.1, variant "a"). A ``None`` field is left unchanged.

    ``extra="forbid"`` (SEC-003): a stray/malicious ``s3_secret_access_key`` (or
    any unmodelled key) is rejected with HTTP 422 instead of being silently
    dropped — making credential-injection attempts loud and auditable.
    """

    model_config = {"extra": "forbid"}

    backend: Literal["local-fs", "s3"] | None = None
    local_fs_root: str | None = None
    local_fs_public_base_url: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_bucket: str | None = None
    s3_use_path_style: bool | None = None
    s3_kms_key_id: str | None = None
    s3_force_tls: bool | None = None


class StorageTestRequest(BaseModel):
    """Optional not-yet-persisted overrides for the connection test.

    No credential fields — the test adapter pulls S3 credentials from env / ESO
    (NFR-013 §4.1), so a test never accepts or echoes a secret. ``extra="forbid"``
    (SEC-003) rejects a smuggled credential field with HTTP 422.
    """

    model_config = {"extra": "forbid"}

    backend: Literal["local-fs", "s3"] | None = None
    local_fs_root: str | None = None
    local_fs_public_base_url: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_bucket: str | None = None
    s3_use_path_style: bool | None = None
    s3_kms_key_id: str | None = None
    s3_force_tls: bool | None = None


class StorageTestResponse(BaseModel):
    """Result of a storage connection test (NFR-013 §4.2 ``health_check``).

    ``success`` reflects backend reachability: local-fs writability or S3 bucket
    reachability. ``message`` is a user-facing summary that NEVER includes
    credentials or signed URLs (NFR-013 §9.2).
    """

    success: bool
    backend: str
    message: str
    # local-fs: path is writable; s3: bucket reachable. ``None`` = not probed.
    writable: bool | None = None
    bucket_reachable: bool | None = None


class SystemSettingsResponse(BaseModel):
    # NOTE (SEC-001): the storage-infra block is deliberately NOT embedded here.
    # When this note was written, ``GET /admin/settings`` was reachable by any
    # authenticated user, and embedding endpoint/region/bucket/KMS would have been
    # infrastructure disclosure. Since #1385 both reads are platform-admin only,
    # and the separation is kept anyway: the two payloads have different audiences
    # on the client (the account-settings page reads this one), and collapsing
    # them is how a field ends up served to the wider audience by accident.
    home_assistant: HASettingsResponse
    plant_identification: PlantIdentificationSettingsResponse


class HATestRequest(BaseModel):
    ha_url: str | None = None
    ha_access_token: str | None = None
    ha_timeout: int | None = Field(default=None, ge=1, le=120)


class HATestResponse(BaseModel):
    success: bool
    message: str
    ha_version: str | None = None


class PlantIdentificationSettingsUpdate(BaseModel):
    plantnet_api_key: str | None = None


class PlantIdentificationTestRequest(BaseModel):
    plantnet_api_key: str | None = None


class PlantIdentificationTestResponse(BaseModel):
    success: bool
    message: str

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.v1.admin.oidc_providers.schemas import (
    OidcProviderCreateRequest,
    OidcProviderResponse,
    OidcProviderUpdateRequest,
)
from app.api.v1.auth.schemas import MessageResponse
from app.common.auth import require_platform_admin
from app.common.dependencies import get_encryption_engine, get_oauth_engine, get_oidc_config_repo
from app.common.exceptions import DuplicateError, NotFoundError
from app.common.openapi_responses import CRUD_RESPONSES, UNAUTHORIZED_RESPONSE
from app.data_access.arango.oidc_config_repository import ArangoOidcConfigRepository
from app.domain.engines.encryption_engine import EncryptionEngine
from app.domain.engines.oauth_engine import OAuthEngine
from app.domain.models.oidc_config import OidcProviderConfig
from app.domain.models.user import User

# Every operation here configures installation-wide identity federation and is
# platform-admin only (#1399). Until then all six resolved their caller through
# ``get_current_user``, so any authenticated member of any tenant could register a
# provider pointing at a server they controlled — and the OAuth callback's
# auto-link path matches an asserted email against an existing verified account,
# which turns that into a login as that account. The sibling ``admin/platform``
# router, mounted on the next line of ``api/v1/router.py``, gates every operation.
#
# The two reads are gated too: ``client_id`` and ``issuer_url`` are the
# installation's federation topology, and #1385 made the same call for the HA URL.
#
# A new endpoint here inherits nothing automatically. ``tests/unit/api/test_write_route_gates.py``
# sweeps the write surface; add read endpoints to that judgement by hand.
router = APIRouter(
    prefix="/admin/oidc-providers",
    tags=["admin-oidc"],
    responses={**UNAUTHORIZED_RESPONSE, **CRUD_RESPONSES},
)


def _response(c: OidcProviderConfig) -> OidcProviderResponse:
    return OidcProviderResponse(
        key=c.key or "",
        slug=c.slug,
        display_name=c.display_name,
        provider_type=c.provider_type,
        issuer_url=c.issuer_url,
        client_id=c.client_id,
        scopes=c.scopes,
        enabled=c.enabled,
        icon_url=c.icon_url,
        auto_discover=c.auto_discover,
        discovery_refreshed_at=c.discovery_refreshed_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("", response_model=list[OidcProviderResponse])
def list_providers(
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
):
    """List all configured OIDC/OAuth providers."""
    return [_response(c) for c in repo.list_all()]


@router.post("", response_model=OidcProviderResponse, status_code=201)
def create_provider(
    body: OidcProviderCreateRequest,
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
    encryption: EncryptionEngine = Depends(get_encryption_engine),
):
    """Create a new OIDC/OAuth provider configuration."""
    existing = repo.get_by_slug(body.slug)
    if existing:
        raise DuplicateError("OidcProviderConfig", "slug", body.slug)

    config = OidcProviderConfig(
        slug=body.slug,
        display_name=body.display_name,
        provider_type=body.provider_type,
        issuer_url=body.issuer_url,
        client_id=body.client_id,
        client_secret_encrypted=encryption.encrypt(body.client_secret),
        scopes=body.scopes,
        authorization_url=body.authorization_url,
        token_url=body.token_url,
        userinfo_url=body.userinfo_url,
        auto_discover=body.auto_discover,
        enabled=body.enabled,
        icon_url=body.icon_url,
        default_tenant_key=body.default_tenant_key,
    )
    created = repo.create(config)
    return _response(created)


@router.get("/{key}", response_model=OidcProviderResponse)
def get_provider(
    key: Annotated[str, Path(description="Document key of the OIDC provider configuration.")],
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
):
    """Return a single OIDC/OAuth provider configuration by key."""
    config = repo.get_by_key(key)
    if config is None:
        raise NotFoundError("OidcProviderConfig", key)
    return _response(config)


@router.put("/{key}", response_model=OidcProviderResponse)
def update_provider(
    key: Annotated[str, Path(description="Document key of the OIDC provider configuration.")],
    body: OidcProviderUpdateRequest,
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
    encryption: EncryptionEngine = Depends(get_encryption_engine),
):
    """Update an existing OIDC/OAuth provider configuration."""
    config = repo.get_by_key(key)
    if config is None:
        raise NotFoundError("OidcProviderConfig", key)

    data = body.model_dump(exclude_none=True)
    for field, value in data.items():
        if field == "client_secret":
            config.client_secret_encrypted = encryption.encrypt(value)
        else:
            setattr(config, field, value)

    updated = repo.update(key, config)
    return _response(updated)


@router.delete("/{key}", status_code=204)
def delete_provider(
    key: Annotated[str, Path(description="Document key of the OIDC provider configuration.")],
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
):
    """Delete an OIDC/OAuth provider configuration."""
    config = repo.get_by_key(key)
    if config is None:
        raise NotFoundError("OidcProviderConfig", key)
    repo.delete(key)


@router.post("/{key}/test", response_model=MessageResponse)
def test_provider(
    key: Annotated[str, Path(description="Document key of the OIDC provider configuration.")],
    _current_user: User = Depends(require_platform_admin),
    repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
    oauth_engine: OAuthEngine = Depends(get_oauth_engine),
):
    """Fetch and validate the OIDC discovery document for the provider."""
    config = repo.get_by_key(key)
    if config is None:
        raise NotFoundError("OidcProviderConfig", key)

    try:
        discovery = oauth_engine.fetch_discovery_document(config.issuer_url)
    except Exception as e:
        return MessageResponse(message=f"Discovery fetch failed: {e}")

    # Validate required fields
    required = ["authorization_endpoint", "token_endpoint", "issuer"]
    missing = [f for f in required if f not in discovery]
    if missing:
        return MessageResponse(message=f"Discovery document missing fields: {', '.join(missing)}")

    # Save discovery document
    config.discovery_document = discovery
    from datetime import UTC, datetime

    config.discovery_refreshed_at = datetime.now(UTC)
    repo.update(key, config)

    return MessageResponse(
        message=f"OIDC discovery for '{config.slug}' validated successfully. "
        f"Endpoints: authorization={discovery.get('authorization_endpoint', 'N/A')}, "
        f"token={discovery.get('token_endpoint', 'N/A')}",
    )

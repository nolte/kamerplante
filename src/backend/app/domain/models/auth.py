from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import AuthProviderType

#: Cap on the client-supplied device label a paired device may attach to its
#: session (#1118). It lives here, next to the model that carries the field,
#: because both enforcing boundaries need it and neither may import the other:
#: ``app.api.v1.auth.schemas`` bounds the HTTP request (over-long input becomes
#: a 422, never a 500 — BACKEND.md §5.4) and ``AuthService`` bounds every
#: non-HTTP caller, but a domain service importing an API schema would invert
#: the NFR-001 layer order. One constant, two boundaries, no second literal.
DEVICE_NAME_MAX_LENGTH = 64


class AuthProvider(BaseModel):
    key: str | None = Field(default=None, alias="_key")
    user_key: str
    provider: AuthProviderType
    provider_user_id: str
    provider_email: str | None = None
    provider_display_name: str | None = None
    avatar_url: str | None = None
    access_token_encrypted: str | None = None
    refresh_token_encrypted: str | None = None
    token_expires_at: datetime | None = None
    last_used_at: datetime | None = None
    linked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}


class AuthProviderInfo(BaseModel):
    key: str
    provider: AuthProviderType
    provider_email: str | None
    provider_display_name: str | None
    linked_at: datetime | None
    last_used_at: datetime | None = None


class RefreshToken(BaseModel):
    key: str | None = Field(default=None, alias="_key")
    user_key: str
    token_hash: str
    user_agent: str | None = None
    #: Label a paired device supplied for itself (#1118), so a phone is
    #: distinguishable from a browser in the session list. ``None`` for every
    #: session minted by the browser login and OAuth paths, and for every
    #: document written before this field existed — ArangoDB is schemaless, so
    #: those documents simply arrive without the key and default here.
    #:
    #: Deliberately **unconstrained on the model**: the length cap is enforced
    #: on the two write boundaries (see :data:`DEVICE_NAME_MAX_LENGTH`), because
    #: a ``max_length`` here would turn a single over-long stored value into a
    #: 500 on ``GET /users/me/sessions`` — a read path failing on data it did
    #: not create is how "422 at the boundary" becomes "500 in the list".
    device_name: str | None = None
    ip_address: str | None = None
    ip_anonymized_at: datetime | None = None
    expires_at: datetime
    is_persistent: bool = False
    revoked: bool = False
    created_at: datetime | None = None

    model_config = {"populate_by_name": True}


class TokenPayload(BaseModel):
    sub: str  # user_key
    tenant_roles: dict[str, str] = Field(default_factory=dict)
    is_platform_admin: bool = False
    exp: int
    iat: int
    jti: str
    type: str = "access"


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class OAuthRedirect(BaseModel):
    authorization_url: str
    state: str
    nonce: str = ""
    code_verifier: str = ""


class OAuthUserInfo(BaseModel):
    provider: AuthProviderType
    provider_user_id: str
    email: str
    display_name: str
    avatar_url: str | None = None
    #: The provider's ``email_verified`` claim, or ``None`` when it said nothing
    #: (#1403). Three states, not two, and the third is the interesting one: many
    #: OIDC providers omit the claim entirely, and collapsing "absent" into
    #: ``False`` at the parse site would hide *which* providers are silent from
    #: the place that has to decide what silence means. The decision itself lives
    #: in :meth:`OAuthEngine.should_auto_link`.
    #:
    #: Until #1403 this field did not exist and the auto-link call site supplied
    #: a literal ``True`` for it, so the claim was never read at all.
    email_verified: bool | None = None


class SessionInfo(BaseModel):
    key: str
    user_agent: str | None
    #: ``None`` unless the session was created by a device pairing that supplied
    #: a label; the session list falls back to ``user_agent`` then.
    device_name: str | None = None
    ip_address: str | None
    created_at: datetime | None
    expires_at: datetime
    is_current: bool = False
    is_persistent: bool = False


class ApiKey(BaseModel):
    key: str | None = Field(default=None, alias="_key")
    user_key: str
    label: str = Field(min_length=1, max_length=100)
    key_hash: str
    key_prefix: str  # First 8 chars for identification
    tenant_scope: str | None = None  # If set, key only works for this tenant
    # REQ-023 v1.10 service-account hardening: optional CIDR allowlist
    # and per-key rate limit (requests per minute). Both fields default
    # to None which means "no restriction" — applies to both interactive
    # user keys and service-account keys.
    ip_allowlist: list[str] | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10000)
    revoked: bool = False
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}


class ApiKeyCreated(BaseModel):
    key: str
    label: str
    raw_key: str  # Only shown once at creation
    key_prefix: str
    tenant_scope: str | None
    created_at: datetime | None


class ApiKeySummary(BaseModel):
    key: str
    label: str
    key_prefix: str
    tenant_scope: str | None
    revoked: bool
    last_used_at: datetime | None
    created_at: datetime | None

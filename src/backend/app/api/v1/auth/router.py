import math
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Path, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.v1.auth.csrf import set_csrf_cookie, verify_csrf
from app.api.v1.auth.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeySummaryResponse,
    DevicePairingCreateResponse,
    DevicePairingRedeemRequest,
    LoginRequest,
    MessageResponse,
    OAuthProviderListItem,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    TokenResponse,
    UserProfileResponse,
    VerifyEmailRequest,
)
from app.api.v1.mcp.deps import require_mcp_enabled
from app.common.auth import get_current_user, get_refresh_token_from_cookie
from app.common.dependencies import get_auth_service, get_mcp_authenticator, get_oidc_config_repo
from app.common.exceptions import (
    InvalidTokenError,
    NotFoundError,
    OAuthAutoLinkRefusedError,
    UnauthorizedError,
    ValidationError,
)
from app.common.openapi_responses import CRUD_RESPONSES, UNAUTHORIZED_RESPONSE
from app.common.request_ip import resolve_client_ip
from app.config.settings import settings
from app.core.permissions import list_mcp_permissions
from app.data_access.arango.oidc_config_repository import ArangoOidcConfigRepository
from app.domain.models.user import User
from app.domain.services.auth_service import AuthService
from app.mcp_server.auth import McpAuthenticator

logger = structlog.get_logger(__name__)


def _rate_limit_key(request: Request) -> str:
    """Bucket a rate limit on the *caller's* address, not on the proxy's.

    ``get_remote_address`` reads ``request.client.host``, which behind the
    Traefik ingress is the ingress for every caller alive — so every
    ``@limiter.limit`` in this module shared **one** bucket across the whole
    deployment. Ten failed pairing redemptions from any single source answered
    429 to everybody else for the rest of the minute (#1130, measured); the same
    held for login, registration and password reset, which is why the key is
    fixed here rather than on the one route the issue was filed against.

    ``resolve_client_ip`` is the same resolution the pairing **lockout** and the
    service-account ``ip_allowlist`` already use, so the three IP-based controls
    now agree on who the caller is instead of two of them disagreeing with the
    third.

    **What makes the key trustworthy** is `resolve_client_ip` itself, not an
    assumption about the ingress. An earlier version of this docstring claimed
    the ingress strips inbound ``X-Forwarded-*`` so the left-most entry could be
    trusted; that was refuted from this repository (``nginx.conf`` appends via
    ``$proxy_add_x_forwarded_for``, and no ``forwardedHeaders`` is pinned in
    ``helm/``), and #1151 replaced the reading with one that counts in from the
    trusted end. A caller who prepends entries only pushes their claim further
    out of reach.

    The one path that reading cannot cover is a request that never traverses our
    proxies — the backend NetworkPolicy currently admits port 8000 without a
    ``from`` selector (#1159). There the header is whatever its sender wrote, for
    this limiter as for the lockout and the allowlist.

    Falls back to the socket peer when no header is present, which is what a
    direct call (and every ``TestClient`` caller that sets no header) gets.
    """
    return resolve_client_ip(request) or get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
router = APIRouter(prefix="/auth", tags=["auth"], responses={**UNAUTHORIZED_RESPONSE, **CRUD_RESPONSES})

#: API-key management, mounted in **both** deployment modes (REQ-027, REQ-033 §4.3).
#:
#: The rest of this module — login, registration, sessions, OAuth — exists only in
#: full mode, where accounts do. API keys are the exception because they are the
#: only credential the MCP interface accepts: without this router, enabling MCP on
#: a light-mode instance yields an endpoint nobody can ever obtain a key for.
#:
#: In light mode every request already resolves to the system user without
#: authentication (``LightAuthProvider``), so a key issued here grants nothing the
#: caller did not already have — it only makes that same access usable from an
#: external client. The trust boundary of a light instance is its network, which
#: is why REQ-027 keeps such a deployment off the public internet.
api_keys_router = APIRouter(prefix="/auth", tags=["auth"], responses={**UNAUTHORIZED_RESPONSE, **CRUD_RESPONSES})

#: Version of the QR device-pairing payload ``{"v": …, "url": …, "code": …}``
#: (#1118). Bumped only when the payload's *shape* changes, so a scanner built
#: against v1 can refuse a payload it does not understand instead of guessing.
#: The frontend composes the payload from the issuance response; this constant is
#: what it stamps into ``v``.
_QR_PAYLOAD_VERSION = 1

# AP-7 (FE-S3): the frontend maps these codes to localised messages. The backend
# NEVER forwards a raw provider error string — only one of these fixed codes.
_OAUTH_ERROR_CODES = frozenset(
    # `link_requires_password` is its own code rather than a flavour of
    # `provider_error` (#1403): the provider reported nothing wrong and retrying
    # cannot help, which is exactly what the generic message tells the user to do.
    {"access_denied", "invalid_state", "provider_error", "account_disabled", "link_requires_password"},
)


def _oauth_error_redirect(frontend_url: str, error_code: str) -> RedirectResponse:
    """Redirect to the frontend callback with a whitelisted error code (no token)."""
    code = error_code if error_code in _OAUTH_ERROR_CODES else "provider_error"
    return RedirectResponse(url=f"{frontend_url}/auth/callback?error={code}", status_code=302)


def _set_refresh_cookie(
    response: Response,
    raw_refresh_token: str,
    is_persistent: bool = False,
    max_age_days: int = 30,
) -> None:
    kwargs: dict = {
        "key": "kp_refresh",
        "value": raw_refresh_token,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/api/v1/auth",
    }
    if is_persistent:
        kwargs["max_age"] = max_age_days * 86400
    # When not persistent, omit max_age → browser session cookie
    response.set_cookie(**kwargs)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key="kp_refresh", path="/api/v1/auth")


def _enqueue_duplicate_registration_notice(user_key: str) -> None:
    """Hand the REQ-023 §3.2 notice to Celery, from a background task.

    Two properties are load-bearing and neither is visible at the call site, so
    they are written down here:

    * **It runs after the response.** Starlette sends the response and only then
      awaits ``response.background``, so no part of this — not the import, not
      the broker publish, not a broker that hangs — falls inside the window a
      caller with a stopwatch measures. That is what keeps the duplicate branch
      indistinguishable from a genuine registration, which sends no mail at all
      while ``require_email_verification`` is off.
    * **The import is lazy.** It keeps Celery and the whole task-module graph out
      of the API's import chain until something actually dispatches. Every other
      dispatch site in this codebase does the same.

      It is *not* what keeps the API's error tracking labelled ``backend``. This
      docstring used to claim that, and it was wrong in the direction that
      mattered: ``app.tasks`` initialised error tracking as ``component="worker"``
      at import time, so the lazy import merely moved the relabelling from
      startup — where ``app.main``'s own init corrected it afterwards — to the
      first dispatch, where nothing did. #991 moved that init to the worker's own
      Celery entry-point signals; importing ``app.tasks`` is now inert.
    """
    from app.tasks.auth_tasks import dispatch_duplicate_registration_notice

    dispatch_duplicate_registration_notice(user_key)


@router.post("/register", response_model=UserProfileResponse, status_code=201)
@limiter.limit(settings.rate_limit_auth)
def register(
    request: Request,
    body: RegisterRequest,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
):
    """Register a new local account with email and password."""
    profile = service.register_local(
        body.email,
        body.password,
        body.display_name,
        # Appending to the background list is the only work this adds to the
        # request; the enqueue itself happens once the 201 is on the wire.
        on_existing_address=lambda user_key: background_tasks.add_task(
            _enqueue_duplicate_registration_notice,
            user_key,
        ),
    )
    return UserProfileResponse(**profile.model_dump())


@router.post("/login", response_model=TokenPairResponse | TokenResponse)
@limiter.limit(settings.rate_limit_auth)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    """Authenticate with email and password, issuing access and refresh tokens.

    **Cookie transport (browsers, the default and unchanged).** The refresh token
    leaves as the HttpOnly ``kp_refresh`` cookie and never appears in the JSON
    (AP-7 / FE-S1); the CSRF cookie is set alongside it. Every existing client
    keeps this shape byte-for-byte, because the alternative below is opt-in.

    **Body transport (native clients, opt-in via** ``refresh_token_in_body``
    **, #1134).** A mobile app has no cookie jar by design. Before this, a
    password sign-in handed it a 15-minute access token and a refresh token it
    could never read — so the session died unrotatable, and the Android client
    had to drop the password path entirely
    (``nolte/kamerplanter-android#8``). Its remaining options were both bad:
    scrape ``kp_refresh`` through an OkHttp ``CookieJar`` (works, but leans on
    behaviour documented as browser-only, so a server upgrade could break it
    silently) or keep the user's password on the device. This route now offers
    the same affordance ``/device-pairing/redeem`` already does.

    **Why opt-in and not inferred.** The obvious alternative — detect the absence
    of a browser and switch transports — would decide a security property from a
    ``User-Agent`` string, which is caller-controlled. Worse, it would make the
    weaker transport the *fallback*: any request that failed the sniff would be
    handed a readable 30-day credential. XSS in the web app can read a response
    body; it cannot read an HttpOnly cookie. So the browser keeps the stronger
    transport unless a client explicitly asks for the other one, and that ask is
    visible in the request.

    **One credential, one transport.** When the body transport is chosen no
    ``kp_refresh`` cookie is set — the same rule ``/refresh`` and
    ``/device-pairing/redeem`` follow. Two transports for one credential double
    its exposure and leave no single place that revokes it. The CSRF cookie is
    also skipped: it exists to protect an *ambient* credential, and there is none
    here.

    ``remember_me`` still decides the refresh token's lifetime in both shapes; it
    is orthogonal to how the token is delivered.
    """
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    token_pair, raw_refresh, is_persistent = service.login_local(
        body.email,
        body.password,
        user_agent,
        ip_address,
        remember_me=body.remember_me,
    )
    if body.refresh_token_in_body:
        return TokenPairResponse(
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
            refresh_token=raw_refresh,
        )
    _set_refresh_cookie(response, raw_refresh, is_persistent=is_persistent)
    set_csrf_cookie(response)
    return TokenResponse(
        access_token=token_pair.access_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse | TokenResponse)
@limiter.limit(settings.rate_limit_token_refresh)
def refresh(
    response: Response,
    request: Request,
    body: RefreshRequest | None = None,
    kp_refresh: Annotated[
        str | None,
        Cookie(description="HttpOnly refresh-token cookie set by the login flow."),
    ] = None,
    service: AuthService = Depends(get_auth_service),
):
    """Rotate a refresh token and issue a fresh access token — two transports (#1118).

    **Cookie transport (browsers, unchanged).** No body, or a body without a
    token: the refresh token comes from the HttpOnly ``kp_refresh`` cookie, the
    CSRF double-submit is verified, the rotated token leaves as a cookie again
    and never appears in the JSON (AP-7 / FE-S1). The refusal order is the one
    this endpoint always had — a missing cookie answers 401 *before* CSRF is
    looked at, so nothing about the change is observable from the browser side.

    **Body transport (paired devices).** A device paired by QR code holds the raw
    refresh token in its platform keystore and has neither a cookie jar nor any
    way to obtain the ``csrf_token`` cookie. It presents the token as
    ``{"refresh_token": "…"}``; the response carries the rotated token in the
    body (``TokenPairResponse``) and sets **no** cookie — one credential on two
    transports would double its exposure and leave no single place that revokes
    it. Without this transport the pair minted by ``/device-pairing/redeem``
    would die 15 minutes later, unrotatable.

    **Why the body path needs no CSRF.** The double-submit defends *ambient*
    credentials: the browser attaches ``kp_refresh`` to a cross-site request on
    its own, so possession of the cookie proves nothing about who composed the
    request. A token in the body is not ambient — it must be read and typed in by
    the caller, and an attacker who can read this user's refresh token has the
    credential itself and needs no request forgery. (A cross-site page cannot
    even reach here: a JSON content type is not a CORS-simple request, so it is
    preflighted.)

    **Precedence, when both are present: the body wins and the cookie is ignored
    entirely.** Not "try the body, fall back to the cookie" — that fallback is
    the actual vulnerability, because a forged cross-site request carrying a
    junk body token would then spend the victim's ambient cookie with no CSRF
    header in sight. Here a request that names a body token is answered purely
    from that token: if it is invalid the answer is 401 and the cookie is left
    untouched and still valid. Nothing spends the ambient credential except the
    CSRF-verified branch below.
    """
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    body_token = body.refresh_token if body is not None else None
    if body_token:
        token_pair, new_raw_refresh, _is_persistent = service.refresh_tokens(body_token, user_agent, ip_address)
        return TokenPairResponse(
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
            refresh_token=new_raw_refresh,
        )

    # The cookie is read through the same helper the dependency used, so the
    # "missing refresh token cookie" refusal keeps exactly one definition. It is
    # called *here* rather than declared as `Depends(...)` because a dependency
    # raises before the handler ever sees the body, which would make the body
    # transport above unreachable for a client that has no cookie — i.e. for
    # every client this package exists for.
    raw_refresh = get_refresh_token_from_cookie(kp_refresh)
    verify_csrf(request)
    token_pair, new_raw_refresh, is_persistent = service.refresh_tokens(raw_refresh, user_agent, ip_address)
    _set_refresh_cookie(response, new_raw_refresh, is_persistent=is_persistent)
    set_csrf_cookie(response)
    return TokenResponse(
        access_token=token_pair.access_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    request: Request,
    kp_refresh: str | None = Cookie(default=None),
    service: AuthService = Depends(get_auth_service),
):
    """Revoke the current refresh token and clear the refresh cookie.

    Cookie-only by design, and deliberately **not** extended with the body-borne
    transport ``/refresh`` gained in #1118: this route is CSRF-verified first, so
    a caller without the ``csrf_token`` cookie is refused with 403 before the
    body would be read. A paired device therefore does not log out here — it
    revokes its own session through ``DELETE /users/me/sessions/{key}``
    (authenticated with its access token, no ambient credential involved) or
    simply discards the token, which becomes worthless at its expiry. Documented
    for the API reference rather than papered over here: adding a second,
    unauthenticated revocation path would widen the surface for a capability the
    session API already covers.
    """
    verify_csrf(request)
    if kp_refresh:
        service.logout(kp_refresh)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Revoke all of the current user's active sessions."""
    verify_csrf(request)
    count = service.logout_all(current_user.key or "")
    _clear_refresh_cookie(response)
    return MessageResponse(message=f"Revoked {count} session(s).")


@router.post("/verify-email", response_model=UserProfileResponse)
def verify_email(
    body: VerifyEmailRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Verify a user's email address from a signed token."""
    profile = service.verify_email(body.token)
    return UserProfileResponse(**profile.model_dump())


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_auth)
def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Send a password-reset link if an account exists for the email."""
    service.request_password_reset(body.email)
    return MessageResponse(message="If the email exists, a reset link has been sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
@limiter.limit(settings.rate_limit_auth)
def confirm_password_reset(
    request: Request,
    body: PasswordResetConfirm,
    service: AuthService = Depends(get_auth_service),
):
    """Set a new password from a valid password-reset token."""
    service.reset_password(body.token, body.new_password)
    return MessageResponse(message="Password has been reset successfully.")


# ── OAuth/OIDC ─────────────────────────────────────────────────────


@router.get("/oauth/providers", response_model=list[OAuthProviderListItem])
def list_oauth_providers(
    oidc_repo: ArangoOidcConfigRepository = Depends(get_oidc_config_repo),
):
    """List the enabled OAuth/OIDC providers offered for login."""
    configs = oidc_repo.list_enabled()
    return [OAuthProviderListItem(slug=c.slug, display_name=c.display_name, icon_url=c.icon_url) for c in configs]


@router.get("/oauth/{slug}")
def initiate_oauth(
    slug: Annotated[str, Path(description="Slug of the configured OAuth/OIDC provider.")],
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """302 Redirect to the OAuth provider's authorization URL."""
    # Build callback URL from request base
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/auth/oauth/{slug}/callback"
    oauth_redirect = service.initiate_oauth(slug, redirect_uri)
    return RedirectResponse(url=oauth_redirect.authorization_url, status_code=302)


@router.get("/oauth/{slug}/callback")
def oauth_callback(
    slug: Annotated[str, Path(description="Slug of the configured OAuth/OIDC provider.")],
    request: Request,
    response: Response,
    code: str | None = Query(default=None, description="Authorization code returned by the provider."),
    state: str | None = Query(default=None, description="Opaque anti-CSRF state echoed by the provider."),
    error: str | None = Query(default=None, description="Error code returned when the provider denied the request."),
    service: AuthService = Depends(get_auth_service),
):
    """OAuth callback: exchange code, set the refresh cookie, redirect to frontend.

    AP-7 (FE-S1): the access token is delivered exclusively through the HttpOnly
    refresh cookie. It is NEVER placed in the redirect URL (neither query nor
    fragment), so it cannot leak via browser history, Referer headers or proxy
    logs. The frontend completes the login through the cookie-based refresh flow.
    """
    frontend_url = service._frontend_url

    # Provider-side denial (e.g. the user cancelled) arrives with an `error`
    # param and without a code — or a malformed callback lacks code/state.
    if error is not None:
        return _oauth_error_redirect(frontend_url, "access_denied")
    if not code or not state:
        return _oauth_error_redirect(frontend_url, "provider_error")

    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    try:
        _token_pair, raw_refresh, is_persistent = service.complete_oauth(
            slug,
            code,
            state,
            user_agent,
            ip_address,
        )
    except InvalidTokenError:
        return _oauth_error_redirect(frontend_url, "invalid_state")
    except UnauthorizedError:
        return _oauth_error_redirect(frontend_url, "account_disabled")
    except OAuthAutoLinkRefusedError as exc:
        # Before its own code, this fell into the branch below and answered
        # `provider_error`. Since #1403 refuses the link whenever the provider
        # omits `email_verified` — the default for a GitHub provider without the
        # `user:email` scope — that would have been an ordinary path answering
        # with a message that is wrong in both halves.
        logger.info("oauth_callback_link_requires_password", provider=slug, error=str(exc))
        return _oauth_error_redirect(frontend_url, "link_requires_password")
    except (NotFoundError, ValidationError) as exc:
        # `as exc` keeps ruff-format from stripping the parens (which would turn
        # this into the `except A, B:` Python-2 syntax error).
        logger.info("oauth_callback_provider_error", provider=slug, error=str(exc))
        return _oauth_error_redirect(frontend_url, "provider_error")
    except Exception:  # noqa: BLE001 — never surface a JSON 500 to the browser
        logger.exception("oauth_callback_failed", provider=slug)
        return _oauth_error_redirect(frontend_url, "provider_error")

    redirect = RedirectResponse(url=f"{frontend_url}/auth/callback", status_code=302)
    _set_refresh_cookie(redirect, raw_refresh, is_persistent=is_persistent)
    set_csrf_cookie(redirect)
    return redirect


# ── Device pairing / QR login (REQ-023, #1118) ─────────────────────
#
# Both routes hang on ``router``, not on ``api_keys_router``, so they exist in
# full mode only. That is not a preference: redemption mints a session **for a
# specific account**, and a light-mode instance has no accounts — every request
# there already resolves to the system user without authenticating. Mounted in
# light mode the pair would be an unauthenticated route handing out tokens for
# the one privileged identity that instance has.


def _remaining_seconds(expires_at: datetime) -> int:
    """Seconds from now until ``expires_at``, never negative.

    Derived rather than read off the TTL setting: the store owns the expiry, and
    a second source for the same number is a second thing that can drift. Rounded
    **up**, so a request that spends a few hundred microseconds between the
    store's write and this line still reports the full TTL instead of one second
    less — a countdown that starts at 89 for a 90-second code looks like a bug,
    and overstating by well under a second costs nothing (the store, not this
    number, is what refuses an expired code).
    """
    return max(0, math.ceil((expires_at - datetime.now(UTC)).total_seconds()))


@router.post("/device-pairing", response_model=DevicePairingCreateResponse, status_code=201)
@limiter.limit(settings.rate_limit_auth)
def create_device_pairing(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Mint a one-time QR pairing code for the authenticated user (#1118).

    Bearer-authenticated, like ``create_api_key`` and for the same reason: the
    credential is presented in the ``Authorization`` header, not ambiently by the
    browser, so there is nothing for a cross-site request to ride on and no CSRF
    double-submit to verify. (``verify_csrf`` guards the routes that spend the
    ``kp_refresh`` cookie — refresh, logout, logout-all — which is the ambient
    credential this one does not use.)

    ``server_url`` comes from ``settings.app_base_url``, the base URL REQ-032
    already established as the SSOT for QR codes, and never from
    ``request.base_url``: behind the Traefik ingress the latter resolves to a
    cluster-internal address, so the QR would encode a URL the scanning phone
    cannot reach — and it would do so only in production, where nobody is
    running the test that would have caught it.
    """
    code, expires_at = service.create_device_pairing(
        current_user.key or "",
        # The proxy-aware helper, not ``request.client.host``: see the module
        # docstring of ``app.common.request_ip``. The address recorded here is
        # also the one the redemption throttle buckets on, and behind an ingress
        # the direct peer is the proxy for *every* caller — which would collapse
        # a per-IP guard into a single shared bucket.
        resolve_client_ip(request),
    )
    return DevicePairingCreateResponse(
        payload_version=_QR_PAYLOAD_VERSION,
        server_url=settings.app_base_url,
        code=code,
        expires_at=expires_at,
        expires_in=_remaining_seconds(expires_at),
    )


@router.post("/device-pairing/redeem", response_model=TokenPairResponse)
@limiter.limit(settings.rate_limit_device_pairing_redeem)
def redeem_device_pairing(
    request: Request,
    body: DevicePairingRedeemRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Exchange a scanned pairing code for the standard REQ-023 token pair (#1118).

    **Public by design.** The caller is a freshly installed app that holds no
    credential yet; the code it just scanned is the credential. The generated
    OpenAPI therefore carries ``security: []`` for this operation (stamped by
    ``main.py::_openapi_postprocessed`` for every operation with no security
    dependency), which is what keeps ``scripts/security/zap_auth_bypass.py`` from
    reporting it as an auth bypass — and what makes the property visible to a
    reviewer instead of implicit in the absence of a ``Depends``.

    **No cookie is set, deliberately.** The refresh token leaves in the JSON
    body (see ``TokenPairResponse``) because the client has no cookie jar. Adding
    the ``kp_refresh`` cookie *as well* would put one credential on two
    transports for no gain. No CSRF header is required either: there is no
    ambient credential here to protect — the request carries its own.

    The error surface is the service's, unchanged and answered by the global
    ``KamerplanterError`` handler: 423 while the source address is locked out,
    401 for a code that is unknown, used, expired or unreadable — one answer for
    all four, so nothing here works as an oracle — 401 for a deactivated account,
    422 for input the boundary let through but the service rejects.
    """
    token_pair, raw_refresh, _is_persistent = service.redeem_device_pairing(
        body.code,
        request.headers.get("user-agent"),
        resolve_client_ip(request),
        body.device_name,
    )
    return TokenPairResponse(
        access_token=token_pair.access_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        refresh_token=raw_refresh,
    )


# ── M2M API Keys ───────────────────────────────────────────────────


@api_keys_router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Create a new M2M API key for the current user."""
    created = service.create_api_key(current_user.key or "", body.label, body.tenant_scope)
    return ApiKeyCreatedResponse(**created.model_dump())


@api_keys_router.get("/api-keys", response_model=list[ApiKeySummaryResponse])
def list_api_keys(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """List the current user's M2M API keys (metadata only)."""
    keys = service.list_api_keys(current_user.key or "")
    return [ApiKeySummaryResponse(**k.model_dump()) for k in keys]


@api_keys_router.delete("/api-keys/{key_id}", response_model=MessageResponse)
def revoke_api_key(
    key_id: Annotated[str, Path(description="Identifier of the API key to revoke.")],
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Revoke one of the current user's M2M API keys."""
    service.revoke_api_key(current_user.key or "", key_id)
    return MessageResponse(message="API key revoked.")


# ── REQ-033 §5 — service-account API-key validation (M2M) ──────────────
class ServiceAccountValidateRequest(BaseModel):
    """A raw service-account API key to validate (never logged)."""

    api_key: str


class ServiceAccountTenantGrant(BaseModel):
    """One tenant a validated key may act in, with its role and MCP grants."""

    tenant_key: str
    tenant_slug: str
    role: str
    mcp_permissions: list[str]


class ServiceAccountValidateResponse(BaseModel):
    """Resolved service-account context for an MCP/M2M client (§4.3, §4.4).

    ``tenants`` carries every tenant the key may act in. A service account is
    usually bound to exactly one (via the key's ``tenant_scope``), but the field
    is a list because the acting tenant is chosen per tool call, not per key.
    """

    service_account_key: str
    display_name: str
    tenants: list[ServiceAccountTenantGrant]


@router.post("/service-accounts/validate", response_model=ServiceAccountValidateResponse)
@limiter.limit(settings.rate_limit_auth)
def validate_service_account(
    request: Request,
    body: ServiceAccountValidateRequest,
    _enabled: None = Depends(require_mcp_enabled),
    authenticator: McpAuthenticator = Depends(get_mcp_authenticator),
):
    """Validate a service-account API key and return its tenant + MCP grants (§5).

    The M2M validation entrypoint an external MCP-server process (future
    follow-up) calls to resolve a key into a bound service account. The raw key
    is hashed inside the authenticator and never persisted or logged (AC-S2).

    Hardened per the REQ-033 security review (SEC-003): gated behind the MCP
    enable flag (``require_mcp_enabled`` → 404 when MCP is off), per-IP rate
    limited (reusing the auth limiter) and the valid-non-service case is
    collapsed into the SAME generic 401 as an invalid/revoked key so the
    endpoint can never be used as an oracle to prove a valid non-service key
    exists (``mask_non_service=True``). The client IP is resolved so the key's
    ``ip_allowlist`` (SEC-004) is enforced here too.
    """

    principal = authenticator.authenticate(
        body.api_key,
        client_ip=resolve_client_ip(request),
        service_accounts_only=True,
        mask_non_service=True,
    )
    return ServiceAccountValidateResponse(
        service_account_key=principal.account_key,
        display_name=principal.display_name,
        tenants=[
            ServiceAccountTenantGrant(
                tenant_key=m.tenant_key,
                tenant_slug=m.tenant_slug,
                role=m.role.value,
                mcp_permissions=[p.value for p in list_mcp_permissions(m.role)],
            )
            for m in principal.memberships
        ],
    )

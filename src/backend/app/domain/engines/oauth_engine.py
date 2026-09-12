"""OAuth/OIDC engine — full implementation with Authlib PKCE.

Handles authorization URL generation, token exchange, provider-specific
user info extraction (Google, GitHub, Apple, generic OIDC).
"""

import hashlib
import hmac
import secrets

import httpx
import structlog

from app.common.enums import AuthProviderType
from app.domain.models.auth import OAuthRedirect, OAuthUserInfo
from app.domain.models.oidc_config import OidcProviderConfig

logger = structlog.get_logger()


def _as_optional_bool(claim: object) -> bool | None:
    """Normalise a provider's ``email_verified`` claim to three states (#1403).

    ``None`` means the provider said nothing, which is NOT the same as ``False``
    and is why this returns an optional rather than defaulting. OIDC Core 5.1
    specifies a boolean, but the claim is optional and real deployments send the
    strings ``"true"`` / ``"false"`` often enough that reading only ``bool``
    would turn a provider that *does* assert verification into one that appears
    silent — and under the rule in :meth:`OAuthEngine.should_auto_link` silence
    refuses the link, so that error is user-visible rather than merely untidy.

    Anything else — a number, a list, a typo — is ``None``. Guessing at a
    malformed claim is exactly the kind of leniency this issue exists to remove.
    """
    if isinstance(claim, bool):
        return claim
    if isinstance(claim, str):
        lowered = claim.strip().lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
    return None


# Well-known endpoints for built-in providers
_PROVIDER_ENDPOINTS: dict[str, dict[str, str]] = {
    "google": {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
    },
    "github": {
        "authorization_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
    },
    "apple": {
        "authorization_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "userinfo_url": "",  # Apple doesn't have a userinfo endpoint; data is in id_token
    },
}


class OAuthEngine:
    """Pure logic for OAuth/OIDC flows."""

    def build_authorization_url(
        self,
        config: OidcProviderConfig,
        redirect_uri: str,
    ) -> OAuthRedirect:
        """Build authorization URL with PKCE (S256) and state/nonce."""
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(16)
        code_verifier = secrets.token_urlsafe(64)

        # S256 code challenge
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        import base64

        code_challenge_b64 = base64.urlsafe_b64encode(code_challenge).rstrip(b"=").decode()

        auth_url = self._resolve_authorization_url(config)
        params = {
            "client_id": config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge_b64,
            "code_challenge_method": "S256",
        }
        # Apple requires response_mode=form_post
        if config.provider_type == "apple":
            params["response_mode"] = "form_post"

        query = "&".join(f"{k}={v}" for k, v in params.items())
        full_url = f"{auth_url}?{query}"

        return OAuthRedirect(
            authorization_url=full_url,
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
        )

    def exchange_code_for_tokens(
        self,
        config: OidcProviderConfig,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        client_secret: str,
    ) -> dict:
        """Exchange authorization code for tokens (synchronous with httpx)."""
        token_url = self._resolve_token_url(config)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": config.client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        }

        headers = {"Accept": "application/json"}

        with httpx.Client(timeout=30) as client:
            resp = client.post(token_url, data=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def extract_user_info(
        self,
        config: OidcProviderConfig,
        token_response: dict,
        access_token: str,
    ) -> OAuthUserInfo:
        """Extract user info, dispatching to provider-specific logic."""
        provider_type = config.provider_type

        if provider_type == "github":
            return self._fetch_github_user_info(access_token)
        elif provider_type == "apple":
            return self._extract_apple_user_info(token_response)
        else:
            # Google and generic OIDC — use userinfo endpoint
            userinfo_url = self._resolve_userinfo_url(config)
            if userinfo_url:
                return self._fetch_userinfo_endpoint(
                    userinfo_url,
                    access_token,
                    config.provider_type,
                )
            # Fallback: parse id_token claims
            return self._extract_from_id_token(token_response, config.provider_type)

    def _fetch_github_user_info(self, access_token: str) -> OAuthUserInfo:
        """GitHub requires separate API calls for profile and email."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=15) as client:
            # Get profile
            resp = client.get("https://api.github.com/user", headers=headers)
            resp.raise_for_status()
            profile = resp.json()

            # Get primary email (may be private)
            email = profile.get("email")

            # `/user` carries NO verification flag — GitHub keeps it on
            # `/user/emails`, one entry per address with its own `verified`
            # boolean (#1403). So the address list is fetched unconditionally
            # now, not only when the profile email is private: without it the
            # claim would be `None` for every GitHub caller whose email is
            # public, which under the "absent means unverified" rule would
            # switch auto-linking off for most of them. The information exists
            # and the token already grants it.
            #
            # A failure here must not break sign-in: an account that is ALREADY
            # linked logs in without ever reaching the auto-link branch, and the
            # branch that does reach it degrades to "not verified", which is the
            # safe direction. So this is caught rather than raised.
            verified: bool | None = None
            try:
                email_resp = client.get("https://api.github.com/user/emails", headers=headers)
                email_resp.raise_for_status()
                emails = email_resp.json()
                if not email:
                    primary = next((e for e in emails if e.get("primary")), None)
                    chosen = primary if primary else (emails[0] if emails else None)
                    if chosen is not None:
                        email = chosen["email"]
                        verified = bool(chosen.get("verified", False))
                else:
                    match = next((e for e in emails if e.get("email") == email), None)
                    if match is not None:
                        verified = bool(match.get("verified", False))
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                logger.warning("github_email_verification_unavailable", error=str(exc))

        return OAuthUserInfo(
            provider=AuthProviderType.GITHUB,
            provider_user_id=str(profile["id"]),
            email=email,
            display_name=profile.get("name") or profile.get("login", ""),
            avatar_url=profile.get("avatar_url"),
            email_verified=verified,
        )

    def _extract_apple_user_info(self, token_response: dict) -> OAuthUserInfo:
        """Apple embeds user info in the id_token JWT."""
        return self._extract_from_id_token(token_response, "apple")

    def _fetch_userinfo_endpoint(
        self,
        userinfo_url: str,
        access_token: str,
        provider_type: str,
    ) -> OAuthUserInfo:
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=15) as client:
            resp = client.get(userinfo_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return OAuthUserInfo(
            provider=self._to_provider_type(provider_type),
            provider_user_id=str(data.get("sub", "")),
            email=data.get("email", ""),
            display_name=data.get("name", data.get("preferred_username", "")),
            avatar_url=data.get("picture"),
            # OIDC Core 5.1: a standard boolean claim, and genuinely optional —
            # `None` when the provider omits it, which is a different answer from
            # `False` and is treated as one (#1403).
            email_verified=_as_optional_bool(data.get("email_verified")),
        )

    def _extract_from_id_token(self, token_response: dict, provider_type: str) -> OAuthUserInfo:
        """Decode id_token JWT claims without verification (tokens just received from IdP)."""
        id_token = token_response.get("id_token", "")
        if not id_token:
            raise ValueError("No id_token in token response.")

        import base64
        import json

        # Decode payload (middle part) — we trust it since we just got it from the IdP
        parts = id_token.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed id_token.")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))

        return OAuthUserInfo(
            provider=self._to_provider_type(provider_type),
            provider_user_id=str(claims.get("sub", "")),
            email=claims.get("email", ""),
            display_name=claims.get("name", claims.get("email", "")),
            avatar_url=claims.get("picture"),
            email_verified=_as_optional_bool(claims.get("email_verified")),
        )

    def fetch_discovery_document(self, issuer_url: str) -> dict:
        """Fetch OIDC discovery document from .well-known/openid-configuration."""
        url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
        with httpx.Client(timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()

    def should_auto_link(self, existing_email_verified: bool, oauth_email_verified: bool | None) -> bool:
        """Auto-link only if BOTH sides are verified, with absent counting as unverified.

        Auto-linking hands an OAuth assertion control of an existing local
        account purely because the two addresses match. The provider's
        ``email_verified`` claim is what bounds that: without it, any provider
        that will assert ``email = victim@example.org`` — one misconfigured in
        good faith, one that never verifies addresses, or one that is
        compromised — can log in as the victim, provided the victim's local
        account is email-verified, which every normally-registered account is.

        **Until #1403 the second argument was a literal ``True`` at the call
        site.** The parameter existed, its docstring said "both", and the value
        it guarded was hard-coded to the permissive answer, so the predicate
        reduced to a fact about the *victim's* account rather than about the
        assertion being trusted. NFR-018 §1 in its purest form: a check that
        cannot fail.

        **``None`` refuses**, and that is a decision rather than a default
        (operator, 2026-09-11). Many providers omit the claim; treating absence
        as ``True`` reproduces exactly the hole above, so absence is treated as
        "not asserted" and the caller is sent down the "log in with your
        password, then link" path that already exists. It is a behaviour change
        for any installation whose provider is silent, which is why it is
        written here and not only in the issue.
        """
        return existing_email_verified and oauth_email_verified is True

    @staticmethod
    def validate_state(state: str, expected: str) -> bool:
        """Constant-time comparison to prevent timing attacks."""
        return hmac.compare_digest(state, expected)

    # ── Internal helpers ─────────────────────────────────────────────

    def _resolve_authorization_url(self, config: OidcProviderConfig) -> str:
        if config.authorization_url:
            return config.authorization_url
        known = _PROVIDER_ENDPOINTS.get(config.provider_type, {})
        if known.get("authorization_url"):
            return known["authorization_url"]
        # Try discovery
        if config.discovery_document:
            return config.discovery_document.get("authorization_endpoint", "")
        raise ValueError(f"Cannot resolve authorization URL for provider '{config.slug}'.")

    def _resolve_token_url(self, config: OidcProviderConfig) -> str:
        if config.token_url:
            return config.token_url
        known = _PROVIDER_ENDPOINTS.get(config.provider_type, {})
        if known.get("token_url"):
            return known["token_url"]
        if config.discovery_document:
            return config.discovery_document.get("token_endpoint", "")
        raise ValueError(f"Cannot resolve token URL for provider '{config.slug}'.")

    def _resolve_userinfo_url(self, config: OidcProviderConfig) -> str | None:
        if config.userinfo_url:
            return config.userinfo_url
        known = _PROVIDER_ENDPOINTS.get(config.provider_type, {})
        if known.get("userinfo_url"):
            return known["userinfo_url"]
        if config.discovery_document:
            return config.discovery_document.get("userinfo_endpoint")
        return None

    @staticmethod
    def _to_provider_type(provider_type: str) -> AuthProviderType:
        mapping = {
            "google": AuthProviderType.GOOGLE,
            "github": AuthProviderType.GITHUB,
            "apple": AuthProviderType.APPLE,
        }
        return mapping.get(provider_type, AuthProviderType.OIDC)

"""GitHub's `email_verified` claim comes from `/user/emails` (#1403).

This branch had no test at all before #1403 rewrote it, and the pull-request
review found three defects living in exactly the untested part. The PR's own
thesis is that the original defect survived because its call site was untested;
shipping a rewritten branch with the same property would have been the same
mistake in the same change.

`/user` carries no verification flag. The address list does, one entry per
address, so the request is unconditional — a claim of `None` refuses the
auto-link, and leaving it absent for every GitHub caller with a public address
would switch auto-linking off for most of them.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.common.enums import AuthProviderType
from app.domain.engines.oauth_engine import OAuthEngine

PROFILE = {"id": 4711, "login": "octocat", "name": "Octo Cat", "avatar_url": None}


def _client(profile: dict, emails: Any, *, emails_status: int = 200):
    """A stubbed httpx client: `/user` then `/user/emails`."""

    def _get(url: str, headers: dict | None = None):
        response = MagicMock()
        if url.endswith("/user"):
            response.json.return_value = profile
            response.raise_for_status.return_value = None
            return response
        response.json.return_value = emails
        if emails_status >= 400:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "forbidden", request=MagicMock(), response=MagicMock(status_code=emails_status)
            )
        else:
            response.raise_for_status.return_value = None
        return response

    client = MagicMock()
    client.get.side_effect = _get
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    return client


def _extract(profile: dict, emails: Any, *, emails_status: int = 200):
    with patch(
        "app.domain.engines.oauth_engine.httpx.Client",
        return_value=_client(profile, emails, emails_status=emails_status),
    ):
        return OAuthEngine()._fetch_github_user_info("token")


class TestTheClaimComesFromTheAddressList:
    def test_a_public_address_still_gets_its_verified_flag(self):
        """The whole reason the request is unconditional now."""
        info = _extract(
            {**PROFILE, "email": "octo@example.org"},
            [{"email": "octo@example.org", "primary": True, "verified": True}],
        )
        assert info.email == "octo@example.org"
        assert info.email_verified is True
        assert info.provider is AuthProviderType.GITHUB

    def test_an_unverified_public_address_is_reported_as_such(self):
        info = _extract(
            {**PROFILE, "email": "octo@example.org"},
            [{"email": "octo@example.org", "primary": True, "verified": False}],
        )
        assert info.email_verified is False

    def test_the_flag_belongs_to_the_address_that_was_chosen(self):
        """A pairing bug here would attach a stranger's verification to this login."""
        info = _extract(
            {**PROFILE, "email": "octo@example.org"},
            [
                {"email": "other@example.org", "primary": True, "verified": True},
                {"email": "octo@example.org", "primary": False, "verified": False},
            ],
        )
        assert info.email == "octo@example.org"
        assert info.email_verified is False

    def test_a_private_address_is_taken_from_the_primary_entry_with_its_flag(self):
        info = _extract(
            {**PROFILE, "email": None},
            [
                {"email": "secondary@example.org", "primary": False, "verified": True},
                {"email": "primary@example.org", "primary": True, "verified": True},
            ],
        )
        assert info.email == "primary@example.org"
        assert info.email_verified is True

    def test_an_address_the_list_does_not_mention_yields_no_claim(self):
        info = _extract({**PROFILE, "email": "ghost@example.org"}, [{"email": "other@example.org", "verified": True}])
        assert info.email_verified is None

    def test_a_stringified_boolean_is_not_silently_truthy(self):
        """`bool("false")` is `True`. A GHE instance or proxy that stringifies
        booleans would otherwise grant the auto-link on an unverified address —
        the exact trap `_as_optional_bool` exists for, at the one construction
        site that reads third-party JSON."""
        info = _extract(
            {**PROFILE, "email": "octo@example.org"},
            [{"email": "octo@example.org", "verified": "false"}],
        )
        assert info.email_verified is False


class TestAVerificationGapNeverBreaksSignIn:
    """The claim degrades to `None`; the request itself must not propagate.

    `extract_user_info` runs BEFORE `complete_oauth` looks for an existing link,
    so an exception escaping here breaks sign-in for every GitHub user including
    those already linked. The first version of this block named only
    `(httpx.HTTPError, KeyError, IndexError, ValueError)` and its commit message
    claimed the opposite of what it did.
    """

    @pytest.mark.parametrize(
        ("emails", "what"),
        [
            ({"message": "Not Found", "documentation_url": "..."}, "an error envelope instead of a list"),
            (None, "a JSON null"),
            (["octo@example.org"], "a list of strings"),
            ([{"email": "octo@example.org"}], "entries without a verified key"),
        ],
    )
    def test_an_unexpected_shape_degrades_to_no_claim(self, emails: Any, what: str):
        info = _extract({**PROFILE, "email": "octo@example.org"}, emails)
        assert info.email == "octo@example.org", f"sign-in broke on {what}"
        assert info.email_verified is None

    def test_a_403_degrades_to_no_claim(self):
        """The default provider scopes do not include `user:email`, so this is
        not hypothetical: `OidcProviderConfig.scopes` defaults to
        `["openid", "email", "profile"]`, which GitHub ignores."""
        info = _extract({**PROFILE, "email": "octo@example.org"}, None, emails_status=403)
        assert info.email == "octo@example.org"
        assert info.email_verified is None


class TestNoAddressAtAllIsADifferentFailure:
    """A verification gap and "no email" must not wear the same clothes.

    `OAuthUserInfo.email` is a required `str`. Swallowing the failure and letting
    `None` through raises a pydantic ValidationError from the model constructor —
    a 500 far from its cause, under a log line calling it a verification problem.
    """

    def test_a_private_address_with_an_unreachable_list_raises(self):
        with pytest.raises(ValueError, match="no usable email"):
            _extract({**PROFILE, "email": None}, None, emails_status=403)

    def test_a_private_address_with_an_empty_list_raises(self):
        with pytest.raises(ValueError, match="no usable email"):
            _extract({**PROFILE, "email": None}, [])

"""The OAuth auto-link reads the provider's `email_verified` claim (#1403).

`OAuthEngine.should_auto_link` always implemented the right rule and always had
tests for it — `(True, False) is False` has been green since the engine was
written. The defect was one level up: `AuthService.complete_oauth` supplied a
literal `True` for the second argument, so the engine's second parameter was
never fed anything a provider said. NFR-018 §1 in its purest form, and the
reason the engine's own test suite could not find it.

**This file exists because that call site had no test at all.** Everything below
drives `complete_oauth` end to end with doubled collaborators, so the assertion
is about what the service does with a claim rather than about what the engine
would do if it were given one.

The decision under test — an ABSENT claim refuses — is an operator decision from
2026-09-11 and a behaviour change for any installation whose provider omits the
claim. It is asserted here, stated on `should_auto_link`, and nowhere else.
"""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import MagicMock

import pytest

from app.common.enums import AuthProviderType
from app.common.exceptions import ValidationError
from app.domain.engines.oauth_engine import OAuthEngine, _as_optional_bool
from app.domain.models.auth import OAuthUserInfo
from app.domain.models.oidc_config import OidcProviderConfig
from app.domain.models.user import User
from app.domain.services.auth_service import AuthService

VICTIM_EMAIL = "victim@example.org"


def _victim() -> User:
    """A normally-registered, email-verified local account — the target."""
    return User(
        key="user-victim",
        email=VICTIM_EMAIL,
        display_name="Victim",
        email_verified=True,
        is_active=True,
    )


def _oauth_user(email_verified: bool | None) -> OAuthUserInfo:
    return OAuthUserInfo(
        provider=AuthProviderType.GOOGLE,
        provider_user_id="attacker-subject",
        email=VICTIM_EMAIL,
        display_name="Not The Victim",
        email_verified=email_verified,
    )


def _service_without_local_account(oauth_user: OAuthUserInfo) -> tuple[AuthService, MagicMock]:
    """Same wiring, but no existing local account — the registration branch."""
    service, _ = _service(oauth_user)
    service._user_repo.get_by_email.return_value = None
    # `create` returns what it was handed, so the assertions read the User the
    # production code built rather than a mock's stand-in — the point of the test
    # is which value landed in `email_verified`.
    service._user_repo.create.side_effect = lambda user: user
    service._tenant_service = None
    return service, service._user_repo


def _service(oauth_user: OAuthUserInfo) -> tuple[AuthService, MagicMock]:
    """An AuthService whose OAuth collaborators are doubles, with a real engine.

    The engine is REAL on purpose: substituting it would move the rule under test
    into the double, which is how the original defect stayed invisible — the
    engine was never the problem.
    """
    user_repo = MagicMock()
    user_repo.get_by_email.return_value = _victim()

    auth_provider_repo = MagicMock()
    auth_provider_repo.get_by_provider.return_value = None  # no existing link

    oauth_engine = MagicMock(wraps=OAuthEngine())
    oauth_engine.exchange_code_for_tokens.return_value = {"access_token": "t", "id_token": ""}
    oauth_engine.extract_user_info.return_value = oauth_user

    state_store = MagicMock()
    state_store.get_and_delete.return_value = {"provider_slug": "acme", "code_verifier": "v"}

    config_repo = MagicMock()
    config_repo.get_by_slug.return_value = OidcProviderConfig(
        slug="acme",
        display_name="Acme",
        issuer_url="https://acme.example",
        client_id="cid",
        client_secret_encrypted="secret",
        enabled=True,
    )

    # `create_refresh_token` is unpacked into two values; a bare MagicMock
    # iterates as empty and fails with "not enough values to unpack" only on the
    # SUCCESS path — which would have left the positive control red for a reason
    # that has nothing to do with the claim under test.
    token_engine = MagicMock()
    token_engine.create_refresh_token.return_value = ("raw-refresh", "refresh-hash")

    service = AuthService(
        user_repo=user_repo,
        auth_provider_repo=auth_provider_repo,
        refresh_token_repo=MagicMock(),
        password_engine=MagicMock(),
        token_engine=token_engine,
        throttle_engine=MagicMock(),
        email_service=MagicMock(),
        frontend_url="https://kamerplanter.example",
        oauth_engine=oauth_engine,
        oauth_state_store=state_store,
        oidc_config_repo=config_repo,
        encryption_engine=None,
    )
    return service, auth_provider_repo


class TestTheProviderClaimDecidesTheAutoLink:
    @pytest.mark.parametrize(
        ("claim", "reason"),
        [
            (False, "the provider said the address is NOT verified"),
            (None, "the provider said nothing, and silence is not an assertion"),
        ],
    )
    def test_an_unverified_or_absent_claim_does_not_link(self, claim: bool | None, reason: str):
        """Red against the pre-#1403 call site, which passed a literal `True`."""
        service, auth_provider_repo = _service(_oauth_user(claim))

        with pytest.raises(ValidationError):
            service.complete_oauth("acme", "code", "state")

        assert auth_provider_repo.create.call_count == 0, (
            f"a provider link was created although {reason}; "
            "complete_oauth is passing something other than the provider's claim"
        )

    def test_a_verified_claim_still_links(self):
        """The control. A rule that refuses every claim would pass the test above."""
        service, auth_provider_repo = _service(_oauth_user(True))

        service.complete_oauth("acme", "code", "state")

        assert auth_provider_repo.create.call_count == 1


class TestTheClaimIsNormalisedToThreeStates:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("TRUE", True),
            (" true ", True),
            (None, None),
            ("yes", None),
            (1, None),
            ([], None),
        ],
    )
    def test_normalisation(self, raw: object, expected: bool | None):
        assert _as_optional_bool(raw) is expected

    def test_a_string_claim_is_not_silently_truthy(self):
        """`bool("false")` is `True`; the whole point of the helper.

        A provider sending the string `"false"` asserts the opposite of what a
        naive read would conclude, and under this rule that error links an
        account rather than refusing one.
        """
        assert _as_optional_bool("false") is False
        assert OAuthEngine().should_auto_link(True, _as_optional_bool("false")) is False


class TestNoCallerPassesAConstant:
    """The absence guard #1403 asks for, so the literal cannot come back.

    A rule repaired at one call site is a snapshot; this makes it an invariant.
    The same shape `check_layer_imports` and `check_route_role_guards` follow.
    """

    def test_should_auto_link_is_never_called_with_a_literal(self):
        root = pathlib.Path(__file__).resolve().parents[4] / "app"
        offenders: list[str] = []
        found = 0

        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr == "should_auto_link"):
                    continue
                found += 1
                for position, argument in enumerate(node.args):
                    if isinstance(argument, ast.Constant):
                        offenders.append(
                            f"{path.relative_to(root.parent)}:{node.lineno} "
                            f"positional argument {position} is the literal {argument.value!r}"
                        )
                # Keywords too. `should_auto_link(a, oauth_email_verified=True)`
                # is the most natural way to reintroduce the literal while making
                # it look deliberate, and the first version of this guard read
                # only `node.args`, so that form walked straight past it.
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Constant):
                        offenders.append(
                            f"{path.relative_to(root.parent)}:{node.lineno} "
                            f"keyword {keyword.arg} is the literal {keyword.value.value!r}"
                        )

        # THE ANCHOR, and without it this test passes by finding nothing.
        # `assert not offenders` is satisfied by an empty list, which is what a
        # rename, a move out of `app/`, or a `parents[4]` that stops resolving all
        # produce — `rglob` on a missing directory yields nothing and raises
        # nothing. The two controls below parse string literals: they verify the
        # predicate, not that the walk ever reached the real call site.
        assert found >= 1, (
            f"no call to should_auto_link was found under {root}. The guard examined nothing, so "
            "its verdict means nothing — check the path, or whether the method was renamed"
        )

        assert not offenders, (
            "A constant is being passed into should_auto_link. The parameter then guards nothing "
            "and the predicate reduces to the other argument — the #1403 defect, returning:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_guard_would_catch_the_original_defect(self):
        """Falsification: the pre-#1403 expression, parsed, must be reported."""
        tree = ast.parse("engine.should_auto_link(existing_user.email_verified, True)")
        call = tree.body[0].value
        assert isinstance(call, ast.Call)
        assert any(isinstance(argument, ast.Constant) for argument in call.args)

    def test_the_guard_does_not_flag_the_repaired_expression(self):
        """The control, so the guard is not simply reporting every call."""
        tree = ast.parse("engine.should_auto_link(existing_user.email_verified, oauth_user.email_verified)")
        call = tree.body[0].value
        assert isinstance(call, ast.Call)
        assert not any(isinstance(argument, ast.Constant) for argument in call.args)


class TestTheRegistrationPathAlsoReadsTheClaim:
    """The other literal, and the one the AST guard does not watch.

    `_register_oauth_user` set `email_verified=True` with the comment "OAuth
    emails are considered verified" — the same assumption #1403 invalidates, one
    branch over. It matters because the two are connected: an account created
    that way satisfies `existing_email_verified` for **every subsequent
    provider**, so refusing the auto-link while minting accounts that make the
    next one succeed would have fixed the symptom and kept the mechanism.
    """

    @pytest.mark.parametrize(
        ("claim", "expected"),
        [
            (True, True),
            (False, False),
            (None, False),
        ],
    )
    def test_the_new_account_inherits_the_provider_claim(self, claim: bool | None, expected: bool):
        service, user_repo = _service_without_local_account(_oauth_user(claim))

        service.complete_oauth("acme", "code", "state")

        assert user_repo.create.call_count == 1
        created = user_repo.create.call_args.args[0]
        assert created.email_verified is expected, (
            f"provider claim {claim!r} produced email_verified={created.email_verified!r}; "
            "a literal True here re-arms the auto-link for the next provider"
        )

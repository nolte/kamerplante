"""Every per-IP rate limit that gates a route is a decision for this harness.

The E2E stack violates the assumption every one of these limits is sized for.
They are keyed on the **client IP**, and in production one address is roughly one
human. Here four xdist workers drive four browsers through a single Selenium
node, so the backend sees the whole suite as one very busy client.

That is not hypothetical. Measured on the 2026-08-15 nightly (`e2e-nightly` run
31859469145, profile `full`): 4 137 calls to `POST /api/v1/auth/refresh`, **289
refused with 429**, against a 60/minute budget whose *median* load was 34/minute.
The refusals came from bursts — four browsers navigating together exhaust a
minute's budget in seconds. A refused refresh drops the browser to logged-out, and
every later `page.open()` times out waiting for a page it never reaches: 119
failures, every one a `TimeoutException`, evenly spread over the four workers
(30/30/30/29), and only in the three profiles that authenticate.

`RATE_LIMIT_AUTH` had already been raised for the login path, for exactly this
reason. The refresh path — the busier of the two, since `AuthProvider` dispatches
one refresh per app bootstrap and an E2E suite bootstraps on every page open — was
missed, and nothing noticed for as long as it stayed just under the budget.

So this file makes the omission impossible rather than unlikely: a new
rate-limited route must be classified once, here, as either raised for the harness
or deliberately left at production level. The list below is the record of those
decisions, not a description of the status quo.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_COMPOSE = _ROOT / "docker-compose.e2e.yml"
_API_ROOT = _ROOT / "src" / "backend" / "app" / "api" / "v1"

#: Limits deliberately left at their production value, with the reason.
#:
#: A limit belongs here only when the suite's traffic on that route is genuinely
#: human-scale. "We have not tripped it yet" is not a reason — that was true of
#: the refresh budget until the suite grew past it.
_LEFT_AT_PRODUCTION: dict[str, str] = {
    "rate_limit_device_pairing_redeem": (
        "One redemption per pairing test, a handful per run (#1118). Nowhere near a "
        "per-minute budget, and the limit is a brute-force defence whose behaviour "
        "the pairing tests themselves assert — raising it here would blunt the very "
        "thing they measure."
    ),
    "rate_limit_email_change": (
        "A couple of change requests per run; the flow is not on any journey path."
    ),
    "rate_limit_email_change_confirm": ("Same volume as the request half it follows."),
    "rate_limit_notification_test": (
        "Reachable only by an explicit click on the notification-settings tab — one "
        "deliberate send per channel a user is configuring. It is not on any bootstrap "
        "or navigation path, which is the property that made the refresh budget fail: "
        "that one fired once per `page.open()` and so scaled with the suite. This one "
        "scales with the number of tests that deliberately test a channel, and the "
        "budget is hourly rather than per-minute, so a burst of four workers cannot "
        "exhaust it the way a per-minute budget is exhausted in seconds. If a journey "
        "ever routes through here, this entry is wrong and the limit needs raising."
    ),
}


def _limits_gating_a_route() -> set[str]:
    """Every ``settings.rate_limit_*`` a route decorator applies.

    Read from the routers rather than from ``settings``: a setting nothing
    decorates cannot refuse a request, and listing those would pad the inventory
    with entries no decision is needed about.
    """
    found: set[str] = set()
    for path in _API_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"@limiter\.limit\(\s*settings\.(rate_limit_[a-z_]+)", text):
            found.add(match.group(1))
    return found


#: A ``RATE_LIMIT_*`` assignment in the compose file's environment block.
#: Anchored at the start of the line (after indentation) so a commented-out
#: override — the exact thing this guard must not accept as present — does not
#: match.
_OVERRIDE = re.compile(r"^\s*(RATE_LIMIT_[A-Z_]+)\s*:", re.MULTILINE)


def _harness_overrides() -> set[str]:
    """The ``RATE_LIMIT_*`` env keys the E2E compose sets, as setting names.

    Read as text rather than parsed as YAML on purpose: this file runs inside the
    ``e2e-selftest`` pre-commit hook, whose isolated environment installs only
    Selenium and pytest. That minimal env is deliberate — the hook's own comment
    explains that installing a different Selenium would verify the page-object
    proxy against a version the suite never runs on — so a guard that needed
    PyYAML would either grow that env for one check or, as it did on the first
    attempt, pass locally and fail in CI with ``No module named 'yaml'``.

    Text matching is sufficient here: the question is whether a key is *set*, and
    the pattern rejects a commented-out line, which is the one shape that would
    make a missing override look present.
    """
    return {
        match.group(1).lower() for match in _OVERRIDE.finditer(_COMPOSE.read_text(encoding="utf-8"))
    }


def test_the_scan_finds_something() -> None:
    """Loud when it finds nothing.

    A rename of the decorator or a move of the routers would leave every
    assertion below comparing empty sets — the vacuous-pass shape, in a file
    written to close one.
    """
    assert _limits_gating_a_route(), (
        f"no `@limiter.limit(settings.rate_limit_*)` found under {_API_ROOT}. Either the "
        "routes lost their limits or this check stopped being able to see them."
    )


@pytest.mark.parametrize("limit", sorted(_limits_gating_a_route()))
def test_every_rate_limited_route_is_classified(limit: str) -> None:
    """Raised for the harness, or listed as deliberately left alone."""
    overridden = limit in _harness_overrides()
    excused = limit in _LEFT_AT_PRODUCTION

    assert overridden or excused, (
        f"`settings.{limit}` gates a route but this harness neither raises it nor records "
        f"why it is left at the production value.\n\n"
        f"These budgets are per client IP and assume one address is roughly one human. This "
        f"suite drives four browsers through one Selenium node, so it is one client. If the "
        f"route is busy, add `{limit.upper()}` to the backend environment in "
        f"docker-compose.e2e.yml; if it is not, add it to _LEFT_AT_PRODUCTION with the reason.\n\n"
        f"Leaving it unclassified is how the refresh budget was missed until it produced 119 "
        f"failures in one nightly."
    )


@pytest.mark.parametrize("limit", sorted(_LEFT_AT_PRODUCTION))
def test_an_excused_limit_still_gates_a_route(limit: str) -> None:
    """The excuse list must not outlive its entries.

    A limit whose route was deleted leaves a rationale that reads as a live
    decision and is no longer about anything — and the next reader trusts it.
    """
    assert limit in _limits_gating_a_route(), (
        f"`{limit}` is recorded as deliberately unraised but no longer gates any route. "
        "Remove it from _LEFT_AT_PRODUCTION."
    )


def test_a_limit_is_not_both_raised_and_excused() -> None:
    """Two answers to one question, and only one of them is doing anything."""
    both = sorted(set(_LEFT_AT_PRODUCTION) & _harness_overrides())

    assert both == [], (
        f"{both} are raised in docker-compose.e2e.yml *and* listed as left at production. "
        "The compose value wins, so the rationale is misleading — drop one."
    )

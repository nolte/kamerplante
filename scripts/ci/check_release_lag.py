#!/usr/bin/env python3
"""Alert when `develop` carries commits that no PUBLISHED release contains.

Issue #1210. Production does not track `develop`; it tracks a **release tag** —
the ArgoCD `Application` in `nolte/k8s-home-lab` pins `targetRevision` to a
published tag for `path: helm/kamerplanter`. That is intended: production rolls
out release versions only. The consequence nothing in this repository could see
until now is that a merged fix is not a delivered fix, and the gap between the
two is invisible.

THE INCIDENT THIS EXISTS FOR
----------------------------
PR #1163 merged to `develop` on 2026-08-14T20:50Z, repairing two MCP tools that
returned 500. On 2026-08-16T12:00Z an operator hit the identical bug on the
running instance and re-diagnosed it from scratch. The fix was correct and
merged; it had simply never been delivered — the newest *published* release was
still `v0.2.0` (2026-08-13T18:09Z), and `v0.2.1` existed only as an **unpublished
draft**. Two days of invisibility, ended by re-encountering the bug.

The draft is the trap. `release-drafter.yml` keeps a draft current on every push
to `develop`, and `release-publish.yml` is `workflow_dispatch`-only — publishing
is a manual hop. So the repository's most visible release artefact is a draft
that reads as done and delivers nothing. `gh release list` prints `v0.2.1 Draft`;
this script therefore refuses to count a draft (or a prerelease) as a delivery,
and the report names the draft explicitly so the alert cannot be misread as
"a release exists, so we are fine".

WHAT COUNTS AS LAG
------------------
Lag is alertable when BOTH hold:

  1. the comparison `<newest published tag>...<base branch>` is ahead by at
     least one commit, AND
  2. the **oldest** of those un-released commits is at least
     RELEASE_LAG_THRESHOLD_DAYS old (default 3).

The grace window (2) is the point of the threshold: `develop` is ahead of the last release
almost all of the time, and alerting on that would be alerting on normal
development. What is not normal is a commit sitting undelivered for days. The
oldest un-released commit — not the newest, not the release date — is the right
clock, because it is the answer to "how long has the earliest undelivered change
been waiting?", which is precisely what nobody could answer on 2026-08-16.

A MEASURED LIMIT OF THE DEFAULT WINDOW, STATED HONESTLY
-------------------------------------------------------
With the default 3-day window this check would NOT have fired at the moment of
re-encounter: #1163's merge commit was ~1.6 days old on 2026-08-16T12:00Z. It
would have fired on 2026-08-17T20:50Z, roughly a day later — still far sooner
than "somebody hits the bug again", but not instantly. The unit tests pin BOTH
facts (see test_release_lag_check.py::TestTheIncident) rather than quietly
choosing a window that flatters the check. Tune RELEASE_LAG_THRESHOLD_DAYS if a
tighter window is wanted; the trade is alerting on ordinary weekend development.

WHY THE API AND NOT GIT
-----------------------
Everything is read from the GitHub REST API: the release list to find the newest
published release, and the compare endpoint to enumerate the commits `develop`
carries beyond that release's tag. No git operations at all, so this runs
correctly on the default shallow checkout, needs no tag fetch, and stays
injectable end-to-end in the unit tests (no network, no live git).

FAIL LOUD (NFR-018 section 2)
-----------------------------
An unreachable API, an unparseable release list, no published release at all, an
unparseable comparison, or a tag that cannot be resolved to a commit is NOT
"no lag". It raises, main() prints ``::error::`` and exits non-zero WITHOUT
writing the report — the workflow run goes red and opens NO issue. An
undetermined check must never read as a clean one, and a transient API blip must
not spam the tracker.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

API_ROOT = "https://api.github.com"

#: Written only on a DETERMINED result; the workflow's issue step keys off its
#: existence, so an undetermined run leaves it absent and opens nothing.
REPORT_PATH = "release-lag-report.json"

DEFAULT_REPOSITORY = "nolte/kamerplanter"
DEFAULT_BASE_BRANCH = "develop"
DEFAULT_THRESHOLD_DAYS = "3"

#: One page is plenty (this repository has ~27 releases) and keeps the check to
#: two API calls. If no published release appears on this page we fail loud
#: rather than page on: "the newest published release is older than the 100 most
#: recent release objects" is not a state to interpret silently.
RELEASE_PAGE_SIZE = 100

HTTP_TIMEOUT_SECONDS = 30

SECONDS_PER_DAY = 86400.0


class ReleaseLagError(RuntimeError):
    """A condition under which the check could not be determined — fail loud."""


@dataclass(frozen=True)
class Release:
    """One GitHub release object, reduced to what the lag question needs."""

    tag: str
    name: str
    draft: bool
    prerelease: bool
    published_at: datetime | None
    created_at: datetime | None
    url: str

    @property
    def is_delivery(self) -> bool:
        """Whether this release actually delivered anything to production.

        A draft has no git tag yet and no ArgoCD `targetRevision` can point at
        it; a prerelease is not what production tracks. Neither is a delivery.
        """
        return not self.draft and not self.prerelease and self.published_at is not None


@dataclass(frozen=True)
class Commit:
    """One commit the base branch carries beyond the released tag."""

    sha: str
    committed_at: datetime
    headline: str
    url: str

    @property
    def short_sha(self) -> str:
        return self.sha[:8]


def parse_timestamp(value: Any, *, context: str) -> datetime:
    """Parse an ISO-8601 GitHub timestamp into an aware UTC datetime.

    Args:
        value: The raw field value.
        context: What is being parsed, for the error message.

    Returns:
        A timezone-aware datetime.

    Raises:
        ReleaseLagError: The value is absent or unparseable. Never a fallback to
            "now" or "epoch" — a guessed timestamp would silently move the age
            this whole check turns on.
    """
    if not isinstance(value, str) or not value:
        raise ReleaseLagError(f"{context}: missing timestamp (got {value!r})")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReleaseLagError(f"{context}: unparseable timestamp {value!r}: {exc}") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_releases(payload: Any) -> list[Release]:
    """Turn the `/releases` payload into :class:`Release` objects.

    Args:
        payload: The decoded JSON body.

    Returns:
        Every release on the page, drafts and prereleases included — the caller
        needs the drafts to name them in the alert.

    Raises:
        ReleaseLagError: The payload is not a list of release objects, or a
            release lacks a tag. An unparseable release list is not "no lag".
    """
    if not isinstance(payload, list):
        raise ReleaseLagError(f"release list is not a JSON array (got {type(payload).__name__})")

    releases: list[Release] = []
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ReleaseLagError(f"release[{index}] is not an object (got {type(entry).__name__})")
        tag = entry.get("tag_name")
        if not isinstance(tag, str) or not tag:
            raise ReleaseLagError(f"release[{index}] has no tag_name")
        published_raw = entry.get("published_at")
        created_raw = entry.get("created_at")
        releases.append(
            Release(
                tag=tag,
                name=str(entry.get("name") or tag),
                draft=bool(entry.get("draft")),
                prerelease=bool(entry.get("prerelease")),
                published_at=(
                    parse_timestamp(published_raw, context=f"release {tag} published_at")
                    if published_raw is not None
                    else None
                ),
                created_at=(
                    parse_timestamp(created_raw, context=f"release {tag} created_at")
                    if created_raw is not None
                    else None
                ),
                url=str(entry.get("html_url") or ""),
            )
        )
    return releases


def newest_delivery(releases: list[Release]) -> Release:
    """The most recently published, non-prerelease release.

    Raises:
        ReleaseLagError: No release on the page is a delivery. That state is
            real (a repository that has only ever drafted) but it is not "no
            lag" — there is nothing to compare against, so the check is
            undetermined and must go red.
    """
    deliveries = [release for release in releases if release.is_delivery]
    if not deliveries:
        drafts = [release.tag for release in releases if release.draft]
        hint = f" ({len(drafts)} draft(s): {', '.join(drafts)})" if drafts else ""
        raise ReleaseLagError(
            f"no published release among the {len(releases)} most recent release object(s){hint} "
            "— refusing to report a clean release-lag check against nothing"
        )
    # published_at is non-None for every delivery by construction of is_delivery.
    return max(deliveries, key=lambda release: release.published_at or datetime.min.replace(tzinfo=timezone.utc))


def newest_unpublished_draft(releases: list[Release]) -> Release | None:
    """The most recently created draft, or None.

    This is the "reads as done, is not" state the incident turned on, so the
    report carries it even when it is None.
    """
    drafts = [release for release in releases if release.draft]
    if not drafts:
        return None
    return max(drafts, key=lambda release: release.created_at or datetime.min.replace(tzinfo=timezone.utc))


def parse_comparison(payload: Any, *, base_tag: str, head: str) -> tuple[int, list[Commit]]:
    """Turn a `/compare/{base}...{head}` payload into (ahead_by, commits).

    GitHub returns the ahead commits oldest-first, so ``commits[0]`` is the
    oldest un-released commit even when the array is truncated at its 250-entry
    cap — which is why the age clock is safe to read off it while ``ahead_by``
    carries the exact count.

    Raises:
        ReleaseLagError: The payload is not a comparison, or claims commits it
            does not carry (which is how an unresolvable tag would surface if
            the API answered 200 instead of 404).
    """
    if not isinstance(payload, dict):
        raise ReleaseLagError(f"comparison {base_tag}...{head} is not a JSON object")

    ahead_by = payload.get("ahead_by")
    if not isinstance(ahead_by, int) or isinstance(ahead_by, bool):
        raise ReleaseLagError(f"comparison {base_tag}...{head} has no integer ahead_by (got {ahead_by!r})")

    raw_commits = payload.get("commits")
    if not isinstance(raw_commits, list):
        raise ReleaseLagError(f"comparison {base_tag}...{head} has no commits array")

    commits: list[Commit] = []
    for index, entry in enumerate(raw_commits):
        if not isinstance(entry, dict):
            raise ReleaseLagError(f"comparison {base_tag}...{head}: commit[{index}] is not an object")
        sha = entry.get("sha")
        if not isinstance(sha, str) or not sha:
            raise ReleaseLagError(f"comparison {base_tag}...{head}: commit[{index}] has no sha")
        detail = entry.get("commit")
        if not isinstance(detail, dict):
            raise ReleaseLagError(f"comparison {base_tag}...{head}: commit {sha[:8]} has no commit object")
        committer = detail.get("committer")
        author = detail.get("author")
        source = committer if isinstance(committer, dict) and committer.get("date") else author
        if not isinstance(source, dict):
            raise ReleaseLagError(f"comparison {base_tag}...{head}: commit {sha[:8]} has no dated committer/author")
        message = detail.get("message")
        headline = str(message).splitlines()[0] if isinstance(message, str) and message else ""
        commits.append(
            Commit(
                sha=sha,
                committed_at=parse_timestamp(source.get("date"), context=f"commit {sha[:8]} date"),
                headline=headline,
                url=str(entry.get("html_url") or ""),
            )
        )

    if ahead_by > 0 and not commits:
        raise ReleaseLagError(
            f"comparison {base_tag}...{head} claims {ahead_by} ahead commit(s) but carries none — "
            "the tag could not be resolved to a commit range"
        )
    return ahead_by, commits


def _days_between(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / SECONDS_PER_DAY


def build_report(
    fetch: Callable[[str], Any],
    *,
    repository: str,
    base_branch: str,
    threshold_days: int,
    now: datetime,
) -> dict[str, Any]:
    """Measure the release lag and return the report the workflow acts on.

    Args:
        fetch: Returns the decoded JSON body for a URL, or raises
            :class:`ReleaseLagError`. Injected so the tests need no network.
        repository: ``owner/name``.
        base_branch: The branch that accumulates merges (``develop``).
        threshold_days: Grace window in days.
        now: Evaluation instant, timezone-aware.

    Returns:
        A JSON-serialisable report; ``alert`` is the single verdict the workflow
        keys off.

    Raises:
        ReleaseLagError: Anything that leaves the answer undetermined.
    """
    releases = parse_releases(fetch(f"{API_ROOT}/repos/{repository}/releases?per_page={RELEASE_PAGE_SIZE}"))
    delivered = newest_delivery(releases)
    draft = newest_unpublished_draft(releases)

    base = urllib.parse.quote(delivered.tag, safe="")
    head = urllib.parse.quote(base_branch, safe="")
    ahead_by, commits = parse_comparison(
        fetch(f"{API_ROOT}/repos/{repository}/compare/{base}...{head}"),
        base_tag=delivered.tag,
        head=base_branch,
    )

    oldest = commits[0] if commits else None
    # The compare API caps `commits` at 250 and returns them OLDEST-FIRST, so the
    # cap truncates the NEW end. `commits[0]` therefore stays the true oldest at
    # any size — which is what the age clock and the alert decision read — but
    # `commits[-1]` is only the true newest while nothing was dropped. Past the
    # cap it is the 250th commit wearing the newest's label, and nothing in the
    # rendered alert would reveal the substitution. Report nothing rather than
    # something plausible and wrong.
    truncated = ahead_by > len(commits)
    newest = commits[-1] if commits and not truncated else None
    oldest_age_days = _days_between(now, oldest.committed_at) if oldest else 0.0
    alert = ahead_by > 0 and oldest_age_days >= threshold_days

    def _commit_entry(commit: Commit | None) -> dict[str, Any] | None:
        if commit is None:
            return None
        return {
            "sha": commit.sha,
            "short_sha": commit.short_sha,
            "committed_at": commit.committed_at.isoformat(),
            "age_days": round(_days_between(now, commit.committed_at), 2),
            "headline": commit.headline,
            "url": commit.url,
        }

    published_at = delivered.published_at
    return {
        "repository": repository,
        "base_branch": base_branch,
        "threshold_days": threshold_days,
        "evaluated_at": now.isoformat(),
        "released": {
            "tag": delivered.tag,
            "name": delivered.name,
            "published_at": published_at.isoformat() if published_at else None,
            "age_days": round(_days_between(now, published_at), 2) if published_at else None,
            "url": delivered.url,
        },
        "unpublished_draft": (
            None
            if draft is None
            else {
                "tag": draft.tag,
                "name": draft.name,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
                "url": draft.url,
            }
        ),
        "unreleased_count": ahead_by,
        "oldest_unreleased": _commit_entry(oldest),
        "newest_unreleased": _commit_entry(newest),
        "alert": alert,
        # Ahead, but the oldest commit is still inside the grace window: normal
        # development, reported for visibility and deliberately not alertable.
        "within_grace": ahead_by > 0 and not alert,
    }


def api_json(url: str) -> Any:
    """GET *url* from the GitHub API and decode it.

    Raises:
        ReleaseLagError: Any transport, status or decode failure. Every branch
            raises; none returns a placeholder.
    """
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ReleaseLagError(f"GET {url} failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ReleaseLagError(f"GET {url} failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseLagError(f"GET {url} returned undecodable JSON: {exc}") from exc


def _threshold_days() -> int:
    raw = os.environ.get("RELEASE_LAG_THRESHOLD_DAYS") or DEFAULT_THRESHOLD_DAYS
    try:
        value = int(raw)
    except ValueError as exc:
        raise ReleaseLagError(f"RELEASE_LAG_THRESHOLD_DAYS must be an integer, got {raw!r}") from exc
    if value < 0:
        raise ReleaseLagError(f"RELEASE_LAG_THRESHOLD_DAYS must not be negative, got {value}")
    return value


def _render(report: dict[str, Any]) -> str:
    """The human summary printed to the job log."""
    released = report["released"]
    lines = [
        f"Newest published release: {released['tag']} "
        f"(published {released['published_at']}, {released['age_days']} day(s) ago).",
    ]
    draft = report["unpublished_draft"]
    if draft:
        lines.append(f"Unpublished draft present: {draft['tag']} (created {draft['created_at']}) — NOT a delivery.")
    count = report["unreleased_count"]
    if count == 0:
        lines.append(f"{report['base_branch']} carries no commits beyond {released['tag']} — nothing to release.")
        return "\n".join(lines)

    oldest = report["oldest_unreleased"]
    lines.append(
        f"{report['base_branch']} carries {count} commit(s) beyond {released['tag']}; "
        f"the oldest is {oldest['short_sha']} from {oldest['committed_at']} "
        f"({oldest['age_days']} day(s) old)."
    )
    if report["alert"]:
        lines.append(f"RELEASE LAG: oldest un-released commit is past the {report['threshold_days']}-day window.")
    else:
        lines.append(
            f"Within grace: {oldest['age_days']}d < {report['threshold_days']}d — not yet alertable."
        )
    return "\n".join(lines)


def main(
    argv: list[str] | None = None,
    *,
    fetch: Callable[[str], Any] | None = None,
    now: datetime | None = None,
) -> int:
    """Run the check and write the report.

    Args:
        argv: Optional ``[report_path]``; defaults to :data:`REPORT_PATH`.
        fetch: Injection point for the HTTP layer (tests pass a fake).
        now: Injection point for the clock (tests pass a fixed instant).

    Returns:
        0 on a determined result. Undetermined raises :class:`ReleaseLagError`,
        which the module entry point turns into a red run with no report.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) > 1:
        print("usage: check_release_lag.py [report.json]", file=sys.stderr)
        return 2
    report_path = arguments[0] if arguments else REPORT_PATH

    report = build_report(
        fetch or api_json,
        repository=os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPOSITORY,
        base_branch=os.environ.get("RELEASE_LAG_BASE_BRANCH") or DEFAULT_BASE_BRANCH,
        threshold_days=_threshold_days(),
        now=now or datetime.now(timezone.utc),
    )

    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(_render(report))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReleaseLagError as exc:
        # Loud, and no report written: an undetermined check is not a clean check.
        print(f"::error::release lag check could not be determined: {exc}", file=sys.stderr)
        sys.exit(1)

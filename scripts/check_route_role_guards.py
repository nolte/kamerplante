#!/usr/bin/env python3
"""Refuse a frontend route that carries no recorded role-guard decision.

Runs as a repo-local pre-commit hook in the required ``static`` lane, and can be
invoked directly::

    python3 scripts/check_route_role_guards.py
    python3 scripts/check_route_role_guards.py --list   # name every decided route
    python3 scripts/check_route_role_guards.py --json   # machine-readable

**What it enforces (#1261).** Until this existed the router consulted the acting
member's domain role nowhere at all: after #1260 gated ``POST /identify`` at
``grower``, a viewer could still open ``/pflanzen/identifikation``, work through
the whole wizard, and collect a 403 on the last step. The repair is a
``<RequireRole>`` wrapper in ``AppRoutes.tsx`` — but the repair alone reproduces
the defect it fixes one level up. A guard applied to the routes somebody happened
to look at is exactly #948, where two of four sibling routes were fixed and the
other two stayed open for months.

So the unit of enforcement is not "the guarded routes" but **every** route:

1. **Every ``path=`` in the router carries a decision** in
   ``src/frontend/src/routes/roleGuardedRoutes.ts`` — ``ROLE_GUARDED_ROUTES``,
   ``ACTION_GATED_ROUTES`` or ``UNGATED_ROUTES``. Adding a route without
   deciding is the failure this catches: nobody has to be *right*, but somebody
   has to have *looked*.
2. **No route is decided twice.** Two buckets disagreeing about one route is a
   table that no longer means anything.
3. **Every guarded route is actually wrapped**, with the minimum the table
   declares, and **no other route is wrapped**. Both directions matter: a
   dropped wrapper is the bug returning, and a wrapper on an undeclared route is
   a guard *stricter* than the API, which takes read access away from members the
   API admits — the mirror-image defect.
3a. **The same pairing on the platform-admin axis** (#1336): a route in
   ``PLATFORM_ADMIN_ROUTES`` carries ``<RequirePlatformAdmin>`` and no other
   route does. The two axes are checked separately because REQ-049 §2.4 keeps
   them disjoint — ``require_platform_admin`` consults no domain role and
   ``require_tenant_role`` consults no platform attribute, so a wrapper of one
   kind never substitutes for the other, and reading them as one bucket would let
   a route be "guarded" by the wrapper that answers the wrong question.
4. **No bucket entry names a route that no longer exists.** Without this rule the
   table decays into a set of pre-approvals: a deleted route leaves its entry
   behind, and a later route re-using the path inherits a decision nobody made
   for it. Same rule as ``check_layer_imports``' obsolete-allowlist-entry error
   and ``seed_steckbrief_consistency.ALLOWED_DISCREPANCIES``.

**There is deliberately no justification hatch.** The sibling checks in this
family accept a ``# <marker>: reason`` comment because their finding is a code
shape that is sometimes legitimate. Here the finding is *"this route has no
recorded decision"*, and the remedy is to record one — ``UNGATED_ROUTES`` **is**
the hatch, in a file whose entries are read, reviewed and diffed. A second way to
say "skip me" would only be a way to not decide.

**What it does not do, said out loud.** It does not verify that a decision is
*correct*. The route × backend-gate join that produced the initial table (216
gated operations across the mounted FastAPI app, matched against the endpoint
functions each page can reach through its import graph) needs the backend
importable, which the ``static`` lane does not have; re-deriving it here would
mean either a heavyweight import in a text-lint lane or a checked-in snapshot
that silently goes stale. So a *new backend gate* on an endpoint an existing page
already calls does not turn this red — only a new or changed **route** does. That
limit is the reason the decision table records the gate it mirrors verbatim per
guarded route: a reviewer can check the pairing by reading, which is the part a
script cannot do for them.

**A route needing both axes is refused, not silently half-read.** The scan reads
the *outermost* element of ``element={…}``, so a nested
``<RequirePlatformAdmin><RequireRole …>`` pair would be seen as the outer one
only — and the inner declaration would surface as ``missing-guard`` rather than
pass unnoticed. No route needs both today; the day one does, this check goes red
and gets nesting support, which is the honest order.

Traces to #1261 and #1336, REQ-049 §2.3/§2.4, and the 2026-08-08 issue-pattern
audit's "guard opt-in at the call site" cluster.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ROUTER = "src/frontend/src/routes/AppRoutes.tsx"
DEFAULT_TABLE = "src/frontend/src/routes/roleGuardedRoutes.ts"

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

#: One route's declaration, as the text between two ``<Route`` openings. Splitting
#: rather than matching a whole tag is deliberate: a route element embeds JSX
#: (``element={<RequireRole min="grower">…``), so the first ``>`` after ``<Route``
#: is *not* the end of the opening tag and any "match the tag" regex silently
#: truncates there — which is how the first version of this parser skipped every
#: guarded route without reporting anything.
ROUTE_SPLIT = "<Route"

#: A route's own ``path``. Index routes carry none and are not addressable, so they
#: are outside the decision table exactly as they are outside ``router.routes``'
#: path list.
ROUTE_PATH = re.compile(r'\bpath="([^"]+)"')

ROUTE_ELEMENT = re.compile(r"\belement=\{")

#: The first JSX element inside ``element={…}`` — the route's outermost wrapper.
ELEMENT_HEAD = re.compile(r"<(\w+)([^>]*)>")

MIN_PROP = re.compile(r'\bmin="(\w+)"')

GUARD_COMPONENT = "RequireRole"

#: The platform-admin wrapper (#1336) — the second, disjoint axis.
PLATFORM_GUARD_COMPONENT = "RequirePlatformAdmin"


class RouteGuardCheckError(Exception):
    """The check could not run — a missing file or an unparsable table."""


@dataclass(frozen=True)
class Finding:
    """One refused route, with the rule it broke."""

    rule: str
    route: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "route": self.route, "detail": self.detail}


@dataclass(frozen=True)
class Decisions:
    """The decision table, as declared in ``roleGuardedRoutes.ts``."""

    guarded: dict[str, str]
    action_gated: tuple[str, ...]
    ungated: tuple[str, ...]
    #: Route -> the ``require_platform_admin`` operation it mirrors (#1336).
    platform_admin: dict[str, str]

    @property
    def all_routes(self) -> list[str]:
        return [*self.guarded, *self.action_gated, *self.ungated, *self.platform_admin]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RouteGuardCheckError(f"cannot read {path}: {exc}") from exc


#: One pass over the source: a single- or double-quoted string literal (kept),
#: or a ``/* … */`` block or ``//`` line comment (dropped). Because the
#: alternation tries the string literal first, a ``//`` or ``/*`` *inside* a
#: quoted entry is part of the string and never starts a comment.
_TOKEN = re.compile(r"""'[^'\n]*'|"[^"\n]*"|(/\*.*?\*/|//[^\n]*)""", re.S)


def _strip_comments(source: str) -> str:
    """Drop both comment kinds so a route named in prose is not read as a decision.

    The table's own doc comments quote route paths (``'pflege'``,
    ``aufgaben/activity-plans*``) to explain the buckets, and the entries carry
    their reason as a ``//`` comment beside them — an English reason contains
    apostrophes. Parsing the file verbatim would count prose as entries (a
    checker green on the wrong evidence), and stripping comments blindly would
    cut an entry that itself contains ``//`` in half (an absolute URL in a
    ``gate``, say) and report the stump as a deleted route. Tokenising strings
    and comments together removes both failure modes at once: a comment is only
    ever recognised outside a string literal.
    """
    return _TOKEN.sub(lambda match: "" if match.group(1) else match.group(0), source)


#: One ``'route': { … }`` entry of a record-shaped bucket.
_RECORD_ENTRY = re.compile(
    r"""(?:'(?P<q>[^']+)'|"(?P<dq>[^"]+)"|(?P<bare>[A-Za-z_$][\w$]*))\s*:\s*\{(?P<body>[^}]*)\}"""
)


def _record_bucket(source: str, name: str, field: str) -> dict[str, str]:
    """Parse a ``Record<string, {…}>`` bucket into ``route -> field value``.

    Both record-shaped buckets are read the same way: ``ROLE_GUARDED_ROUTES``
    for its ``min`` and ``PLATFORM_ADMIN_ROUTES`` for its ``gate``. Sharing the
    parse rather than forking it keeps the two axes from drifting on how a table
    is *read* — they already differ on what they mean, which is enough.
    """
    block = _named_block(source, name, "{", "}")
    entries: dict[str, str] = {}
    for match in _RECORD_ENTRY.finditer(block):
        route = match.group("q") or match.group("dq") or match.group("bare")
        value = re.search(
            rf"""\b{re.escape(field)}\s*:\s*'([^']*)'""", match.group("body")
        )
        if value is None:
            raise RouteGuardCheckError(f"{name}['{route}'] declares no `{field}`")
        entries[route] = value.group(1)
    return entries


def parse_decisions(table_source: str) -> Decisions:
    """Extract the four buckets from the TypeScript decision table."""
    source = _strip_comments(table_source)

    guarded = _record_bucket(source, "ROLE_GUARDED_ROUTES", "min")
    # An *empty* ROLE_GUARDED_ROUTES is a legitimate state (nothing guarded), so it
    # is not treated as a parse failure — conflating "empty" with "unreadable" is
    # the same green-on-the-wrong-evidence shape this family exists to remove. A
    # parser that silently produced {} against the real table would still be
    # caught, by the `undeclared-guard` rule turning every wrapper in the router
    # red; an unreadable file raises out of `_named_block` above.

    action_gated = _string_list(_named_block(source, "ACTION_GATED_ROUTES", "[", "]"))
    ungated = _string_list(_named_block(source, "UNGATED_ROUTES", "[", "]"))
    # A table without the bucket is unreadable, not empty: `_named_block` raises,
    # which exits 2. "I could not measure this" must not report green (NFR-018 §2).
    platform_admin = _record_bucket(source, "PLATFORM_ADMIN_ROUTES", "gate")

    return Decisions(
        guarded=guarded,
        action_gated=action_gated,
        ungated=ungated,
        platform_admin=platform_admin,
    )


def _named_block(source: str, name: str, opener: str, closer: str) -> str:
    """Return the balanced ``opener…closer`` block assigned to ``name``."""
    anchor = re.search(rf"\b{re.escape(name)}\b[^=]*=\s*", source)
    if anchor is None:
        raise RouteGuardCheckError(f"{name} is not declared in the decision table")
    start = source.find(opener, anchor.end())
    if start == -1:
        raise RouteGuardCheckError(f"{name} has no `{opener}` after its assignment")
    depth = 0
    for index in range(start, len(source)):
        if source[index] == opener:
            depth += 1
        elif source[index] == closer:
            depth -= 1
            if depth == 0:
                return source[start + 1 : index]
    raise RouteGuardCheckError(f"{name} has an unbalanced `{opener}`")


def _string_list(block: str) -> tuple[str, ...]:
    return tuple(re.findall(r"'([^']*)'", block))


def parse_router(router_source: str) -> tuple[list[str], dict[str, str], list[str]]:
    """Return the route paths, the ``min`` per role-guarded route, and the
    platform-guarded routes.

    Raises:
        RouteGuardCheckError: a ``<Route>`` writes ``element`` before ``path``.
            The scan reads the element that *follows* a route's ``path``; with the
            attributes swapped it would attribute the element to the wrong route
            and could report a guard where there is none. Refusing is the honest
            answer — a checker that silently mis-attributes is worse than one that
            stops (NFR-018 §2).
    """
    paths: list[str] = []
    guarded: dict[str, str] = {}
    platform_guarded: list[str] = []

    for segment in router_source.split(ROUTE_SPLIT)[1:]:
        path_match = ROUTE_PATH.search(segment)
        element_match = ROUTE_ELEMENT.search(segment)
        if path_match is None:
            continue  # a layout or index route: not addressable, nothing to decide
        if element_match is not None and element_match.start() < path_match.start():
            raise RouteGuardCheckError(
                f'the <Route> for path="{path_match.group(1)}" declares `element` before '
                "`path`; this scan reads the element that follows `path` and cannot "
                "attribute it safely"
            )
        paths.append(path_match.group(1))
        if element_match is None:
            continue
        head = ELEMENT_HEAD.search(segment, element_match.end())
        if head is None:
            continue
        if head.group(1) == PLATFORM_GUARD_COMPONENT:
            platform_guarded.append(path_match.group(1))
            continue
        if head.group(1) != GUARD_COMPONENT:
            continue
        min_match = MIN_PROP.search(head.group(2))
        guarded[path_match.group(1)] = min_match.group(1) if min_match else ""

    return paths, guarded, platform_guarded


def collect(router_path: Path, table_path: Path) -> list[Finding]:
    """Run every rule and return the findings, ordered by rule then route."""
    router_source = _read(router_path)
    decisions = parse_decisions(_read(table_path))
    paths, wrapped, platform_wrapped = parse_router(router_source)

    findings: list[Finding] = []

    declared = decisions.all_routes
    seen: set[str] = set()
    duplicates = sorted(
        {route for route in declared if route in seen or seen.add(route)}
    )
    for route in duplicates:
        buckets = [
            name
            for name, bucket in (
                ("ROLE_GUARDED_ROUTES", decisions.guarded),
                ("ACTION_GATED_ROUTES", decisions.action_gated),
                ("UNGATED_ROUTES", decisions.ungated),
                ("PLATFORM_ADMIN_ROUTES", decisions.platform_admin),
            )
            if route in bucket
        ]
        findings.append(
            Finding("decided-twice", route, f"listed in {' and '.join(buckets)}")
        )

    declared_set = set(declared)
    for route in sorted(set(paths) - declared_set):
        findings.append(
            Finding(
                "undecided-route",
                route,
                "add it to ROLE_GUARDED_ROUTES, PLATFORM_ADMIN_ROUTES, "
                "ACTION_GATED_ROUTES or UNGATED_ROUTES "
                f"in {DEFAULT_TABLE} — every route needs a recorded decision, not "
                "necessarily a guard",
            )
        )

    for route in sorted(declared_set - set(paths)):
        findings.append(
            Finding(
                "obsolete-decision",
                route,
                "decided in the table but not registered in the router; drop the entry "
                "so it cannot pre-approve a future route that re-uses the path",
            )
        )

    for route, expected_min in sorted(decisions.guarded.items()):
        if route not in paths:
            continue  # already reported as obsolete
        if route not in wrapped:
            findings.append(
                Finding(
                    "missing-guard",
                    route,
                    f"ROLE_GUARDED_ROUTES declares min='{expected_min}' but the route "
                    f"element is not wrapped in <{GUARD_COMPONENT}>",
                )
            )
        elif wrapped[route] != expected_min:
            findings.append(
                Finding(
                    "guard-minimum-mismatch",
                    route,
                    f"table declares min='{expected_min}', router declares "
                    f"min='{wrapped[route] or '(none)'}'",
                )
            )

    for route in sorted(set(wrapped) - set(decisions.guarded)):
        findings.append(
            Finding(
                "undeclared-guard",
                route,
                f"wrapped in <{GUARD_COMPONENT}> but not in ROLE_GUARDED_ROUTES; a guard "
                "the table does not back may be stricter than the API, which takes read "
                "access away from members the API admits",
            )
        )

    # The same pairing on the platform-admin axis (#1336). Kept separate from the
    # loops above rather than merged into them: a `<RequireRole>` wrapper must not
    # be able to satisfy a `PLATFORM_ADMIN_ROUTES` entry (or the reverse), because
    # the two dependencies they mirror decide on different attributes and REQ-049
    # §2.4 gives no rank that would let one stand in for the other.
    for route in sorted(decisions.platform_admin):
        if route not in paths:
            continue  # already reported as obsolete
        if route not in platform_wrapped:
            findings.append(
                Finding(
                    "missing-platform-guard",
                    route,
                    f"PLATFORM_ADMIN_ROUTES declares it platform-admin-only "
                    f"({decisions.platform_admin[route] or 'no gate recorded'}) but the "
                    f"route element is not wrapped in <{PLATFORM_GUARD_COMPONENT}>",
                )
            )

    for route in sorted(set(platform_wrapped) - set(decisions.platform_admin)):
        findings.append(
            Finding(
                "undeclared-platform-guard",
                route,
                f"wrapped in <{PLATFORM_GUARD_COMPONENT}> but not in "
                "PLATFORM_ADMIN_ROUTES; this guard replaces the page for every member "
                "who is not a platform admin, so a route it was not measured for loses "
                "content the API serves",
            )
        )

    return findings


def report(
    findings: list[Finding], *, decisions: Decisions, list_all: bool, as_json: bool
) -> int:
    """Print the findings and return the process exit code."""
    if as_json:
        json.dump(
            {
                "findings": [f.as_dict() for f in findings],
                "decided": {
                    "guarded": decisions.guarded,
                    "platform_admin": decisions.platform_admin,
                    "action_gated": list(decisions.action_gated),
                    "ungated": list(decisions.ungated),
                },
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
        return EXIT_FINDINGS if findings else EXIT_OK

    if findings:
        print("Route role-guard decisions are incomplete or inconsistent (#1261):\n")
        for finding in findings:
            print(f"  [{finding.rule}] {finding.route}")
            print(f"      {finding.detail}")
        print(
            f"\n{len(findings)} finding(s). The table lives in {DEFAULT_TABLE}; "
            "a route needs a decision, not necessarily a guard."
        )
        return EXIT_FINDINGS

    total = len(decisions.all_routes)
    print(
        f"check_route_role_guards: {total} routes decided "
        f"({len(decisions.guarded)} guarded, {len(decisions.platform_admin)} platform-admin, "
        f"{len(decisions.action_gated)} action-gated, {len(decisions.ungated)} ungated)."
    )
    if list_all:
        for route, minimum in sorted(decisions.guarded.items()):
            print(f"  guarded      {route}  (min {minimum})")
        for route, gate in sorted(decisions.platform_admin.items()):
            print(f"  platform     {route}  ({gate})")
        for route in sorted(decisions.action_gated):
            print(f"  action-gated {route}")
        for route in sorted(decisions.ungated):
            print(f"  ungated      {route}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Run the check.

    Returns:
        0 when every route carries exactly one decision and the guards match it,
        1 when at least one does not, 2 on a usage or environment error.
    """
    parser = argparse.ArgumentParser(
        prog="check_route_role_guards.py",
        description=(
            "Refuse a frontend route that carries no recorded role-guard decision, and "
            "keep the <RequireRole> / <RequirePlatformAdmin> wrappers in AppRoutes.tsx "
            "paired with ROLE_GUARDED_ROUTES / PLATFORM_ADMIN_ROUTES in both directions "
            "(#1261, #1336, REQ-049 §2.3/§2.4)."
        ),
    )
    parser.add_argument(
        "--router",
        metavar="PATH",
        default=None,
        help=f"the router source to scan (default: {DEFAULT_ROUTER})",
    )
    parser.add_argument(
        "--table",
        metavar="PATH",
        default=None,
        help=f"the decision table to read (default: {DEFAULT_TABLE})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_all",
        help="also name every decided route when the check passes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the findings as JSON instead of the human report",
    )
    args = parser.parse_args(argv)

    router_path = _resolve(args.router, DEFAULT_ROUTER)
    table_path = _resolve(args.table, DEFAULT_TABLE)

    try:
        decisions = parse_decisions(_read(table_path))
        findings = collect(router_path, table_path)
    except RouteGuardCheckError as exc:
        print(f"check_route_role_guards: {exc}", file=sys.stderr)
        return EXIT_USAGE

    return report(
        findings, decisions=decisions, list_all=args.list_all, as_json=args.json
    )


def _resolve(raw: str | None, default: str) -> Path:
    value = raw or default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())

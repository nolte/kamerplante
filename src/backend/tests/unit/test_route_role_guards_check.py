"""Tests for the route role-guard gate (``scripts/check_route_role_guards.py``).

**What is under test.** The parsing and the five rules, driven against
*constructed* miniature routers and decision tables written into ``tmp_path`` —
never against the real ``AppRoutes.tsx``. A test asserting "the router has 85
decided routes" would go red on the next legitimate route and teach nobody
anything; one case below does read the real pair, but only to assert that the
shipped tree passes, which is a property that must hold at every commit.

**The deliberately-broken router.** :class:`TestItCanFail` drops a wrapper the
table declares, adds a route nobody decided, and points the table at a route that
no longer exists — the three shapes #1261 is about — and asserts the check goes
red and names each. A gate nobody has watched fail is a gate nobody knows works.

**The second axis (#1336).** ``PLATFORM_ADMIN_ROUTES`` /
``<RequirePlatformAdmin>`` are checked with the same two directions, plus the one
that only exists once there are two axes: a wrapper of the *other* kind must not
satisfy an entry. REQ-049 §2.4 gives the domain rank and the platform attribute
no common rank, so a route "guarded" by the wrapper that answers the other
question is ungated in fact — :class:`TestTheAxesDoNotSubstitute` asserts the
check says so.

**The obsolete-entry direction is the half that rots.** A deleted route leaving
its decision behind turns the table into a pre-approval: the next route to re-use
that path inherits a judgement nobody made for it. Same rule, same reason, as
``check_layer_imports``' obsolete-allowlist entry.

**Why here.** ``pytest tests/unit/`` from ``src/backend`` is a CI check, and the
script lives outside the backend package, so it is loaded by path.

Traces to #1261 / REQ-049 §2.3 (no TC-ID: a source-tree gate is not a
user-facing case).
"""

from __future__ import annotations

import json
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support.repo_scripts import find_repo_root, load_repo_script

checker = load_repo_script("check_route_role_guards")


ROUTER_TEMPLATE = """\
import {{ Route }} from 'react-router-dom';
import RequireRole from '@/auth/RequireRole';
import RequirePlatformAdmin from '@/auth/RequirePlatformAdmin';

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route element={{<ProtectedRoute />}}>
{routes}
    </Route>,
  ),
);
"""

GUARDED_ROUTE = """\
      <Route
        path="{path}"
        element={{
          <RequireRole min="{min}">
            <Suspense fallback={{<LoadingSkeleton variant="card" />}}>
              <{component} />
            </Suspense>
          </RequireRole>
        }}
      />
"""

PLATFORM_ROUTE = """\
      <Route
        path="{path}"
        element={{
          <RequirePlatformAdmin>
            <Suspense fallback={{<LoadingSkeleton variant="form" />}}>
              <{component} />
            </Suspense>
          </RequirePlatformAdmin>
        }}
      />
"""

PLAIN_ROUTE = """\
      <Route
        path="{path}"
        element={{
          <Suspense fallback={{<LoadingSkeleton variant="card" />}}>
            <{component} />
          </Suspense>
        }}
      />
"""


@pytest.fixture
def build_pair(tmp_path: Path) -> Callable[..., tuple[Path, Path]]:
    """Return a helper writing a miniature router + decision table into ``tmp_path``.

    Returns the ``(router, table)`` pair the check takes as its two inputs.
    """

    def _build(
        *,
        guarded_routes: dict[str, str] | None = None,
        plain_routes: tuple[str, ...] = (),
        declared_guarded: dict[str, str] | None = None,
        action_gated: tuple[str, ...] = (),
        ungated: tuple[str, ...] = (),
        platform_routes: tuple[str, ...] = (),
        declared_platform: tuple[str, ...] | None = None,
    ) -> tuple[Path, Path]:
        guarded_routes = {} if guarded_routes is None else guarded_routes
        declared = guarded_routes if declared_guarded is None else declared_guarded
        declared_platform_admin = platform_routes if declared_platform is None else declared_platform

        blocks = [
            GUARDED_ROUTE.format(path=path, min=minimum, component="PageFor" + str(index))
            for index, (path, minimum) in enumerate(guarded_routes.items())
        ]
        blocks += [
            PLATFORM_ROUTE.format(path=path, component="AdminPage" + str(index))
            for index, path in enumerate(platform_routes)
        ]
        blocks += [
            PLAIN_ROUTE.format(path=path, component="PlainPage" + str(index)) for index, path in enumerate(plain_routes)
        ]
        router = tmp_path / "AppRoutes.tsx"
        router.write_text(ROUTER_TEMPLATE.format(routes="".join(blocks)), encoding="utf-8")

        entries = "\n".join(
            f"  '{path}': {{ min: '{minimum}', gate: 'POST /x — require_tenant_role({minimum})' }},"
            for path, minimum in declared.items()
        )
        table = tmp_path / "roleGuardedRoutes.ts"
        table.write_text(
            textwrap.dedent(
                """\
                /* A doc comment naming 'not-a-real-route' in prose. */
                export const ROLE_GUARDED_ROUTES = {
                %(entries)s
                };

                export const ACTION_GATED_ROUTES: readonly string[] = [
                %(action)s
                ];

                export const UNGATED_ROUTES: readonly string[] = [
                %(ungated)s
                ];

                export const PLATFORM_ADMIN_ROUTES = {
                %(platform)s
                };
                """
            )
            % {
                "entries": entries,
                "action": "\n".join(f"  '{path}'," for path in action_gated),
                "ungated": "\n".join(f"  '{path}'," for path in ungated),
                "platform": "\n".join(
                    f"  '{path}': {{ gate: 'GET /api/v1/admin/platform/x — require_platform_admin' }},"
                    for path in declared_platform_admin
                ),
            },
            encoding="utf-8",
        )
        return router, table

    return _build


def rules(findings: list[object]) -> list[tuple[str, str]]:
    """Reduce findings to ``(rule, route)`` pairs for readable assertions."""
    return sorted((f.rule, f.route) for f in findings)  # type: ignore[attr-defined]


def _capture_json(module: object, argv: list[str]) -> str:
    """Run ``main`` with ``--json`` and return what it printed.

    ``capsys`` cannot be requested from a helper, and the JSON body is the part
    that proves the new bucket reaches the machine-readable output rather than
    only the human one.
    """
    import contextlib
    import io as _io

    buffer = _io.StringIO()
    with contextlib.redirect_stdout(buffer):
        module.main(argv)  # type: ignore[attr-defined]
    return buffer.getvalue()


class TestAcceptsACompleteTable:
    """A router whose every route is decided, with the declared guards in place."""

    def test_no_findings(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(
            guarded_routes={"pflanzen/identifikation": "grower"},
            plain_routes=("dashboard", "glossar"),
            action_gated=("dashboard",),
            ungated=("glossar",),
        )
        assert checker.collect(router, table) == []

    def test_exit_code_is_zero(
        self, build_pair: Callable[..., tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        router, table = build_pair(
            guarded_routes={"vermehrung": "grower"},
            plain_routes=("glossar",),
            ungated=("glossar",),
        )
        code = checker.main(["--router", str(router), "--table", str(table)])
        assert code == checker.EXIT_OK
        assert "1 guarded" in capsys.readouterr().out


class TestItCanFail:
    """The three shapes #1261 is about, each asserted to turn the check red."""

    def test_guard_declared_but_not_applied(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # The regression: a route loses its wrapper while the table still says it
        # is guarded — the state `develop` was in before #1261, one route at a time.
        router, table = build_pair(
            plain_routes=("pflanzen/identifikation",),
            declared_guarded={"pflanzen/identifikation": "grower"},
        )
        assert rules(checker.collect(router, table)) == [("missing-guard", "pflanzen/identifikation")]

    def test_route_with_no_decision(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(plain_routes=("brandneu",))
        assert rules(checker.collect(router, table)) == [("undecided-route", "brandneu")]

    def test_decision_for_a_route_that_no_longer_exists(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(plain_routes=("glossar",), ungated=("glossar", "entfernt"))
        assert rules(checker.collect(router, table)) == [("obsolete-decision", "entfernt")]

    def test_exit_code_is_one(
        self, build_pair: Callable[..., tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        router, table = build_pair(plain_routes=("brandneu",))
        code = checker.main(["--router", str(router), "--table", str(table)])
        assert code == checker.EXIT_FINDINGS
        assert "undecided-route" in capsys.readouterr().out


class TestGuardAndTableMustAgree:
    """Both directions of the pairing, and the minimum itself."""

    def test_wrapper_on_an_undeclared_route_is_refused(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # A guard the table does not back may be stricter than the API, which
        # removes read access the API grants — the mirror image of the bug.
        router, table = build_pair(
            guarded_routes={"glossar": "grower"},
            declared_guarded={},
            ungated=("glossar",),
        )
        assert rules(checker.collect(router, table)) == [("undeclared-guard", "glossar")]

    def test_minimum_mismatch_is_refused(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(
            guarded_routes={"vermehrung": "lead"},
            declared_guarded={"vermehrung": "grower"},
        )
        assert rules(checker.collect(router, table)) == [("guard-minimum-mismatch", "vermehrung")]

    def test_route_decided_in_two_buckets_is_refused(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(
            plain_routes=("dashboard",),
            action_gated=("dashboard",),
            ungated=("dashboard",),
        )
        assert ("decided-twice", "dashboard") in rules(checker.collect(router, table))


class TestThePlatformAdminAxis:
    """The #1336 bucket, in the same two directions as the domain one."""

    def test_a_declared_and_wrapped_route_passes(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        router, table = build_pair(platform_routes=("admin/tenants/:key",))
        assert checker.collect(router, table) == []

    def test_declared_but_not_wrapped_is_refused(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # The state `develop` was in before #1336: the two admin routes were
        # navigable by any member and the API answered 403.
        router, table = build_pair(
            plain_routes=("admin/tenants/:key",),
            declared_platform=("admin/tenants/:key",),
        )
        assert rules(checker.collect(router, table)) == [("missing-platform-guard", "admin/tenants/:key")]

    def test_wrapped_but_not_declared_is_refused(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # The other direction. This wrapper *replaces* the page for a non-admin,
        # so applying it to a route nobody measured removes content the API serves
        # — stricter than the API, the mirror-image defect.
        router, table = build_pair(
            platform_routes=("glossar",),
            declared_platform=(),
            ungated=("glossar",),
        )
        assert rules(checker.collect(router, table)) == [("undeclared-platform-guard", "glossar")]

    def test_an_entry_without_a_gate_is_a_parse_error(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # The recorded gate is the whole reviewable part of the pairing: the check
        # cannot verify that a route's decision is *correct*, so an entry that
        # names no backend operation is a decision nobody can read back.
        router, table = build_pair(platform_routes=("admin/users/:key",))
        source = table.read_text(encoding="utf-8")
        table.write_text(
            source.replace("gate: 'GET /api/v1/admin/platform/x — require_platform_admin'", "reason: 'because'"),
            encoding="utf-8",
        )
        with pytest.raises(checker.RouteGuardCheckError):
            checker.collect(router, table)

    def test_a_table_without_the_bucket_is_a_usage_error_not_a_pass(
        self, build_pair: Callable[..., tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        # A table predating the bucket must not read as "no platform-admin route
        # decided" — that would be green on the wrong evidence (NFR-018 §2), and
        # every wrapper in the router would then look undeclared instead.
        router, table = build_pair(platform_routes=("admin/users/:key",))
        source = table.read_text(encoding="utf-8")
        start = source.index("export const PLATFORM_ADMIN_ROUTES")
        table.write_text(source[:start], encoding="utf-8")

        code = checker.main(["--router", str(router), "--table", str(table)])
        assert code == checker.EXIT_USAGE
        assert "PLATFORM_ADMIN_ROUTES" in capsys.readouterr().err

    def test_the_bucket_counts_as_a_decision(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # Without this the route would be reported `undecided-route` — the bucket
        # has to join the other three, not sit beside them.
        router, table = build_pair(platform_routes=("admin/users/:key",))
        payload = json.loads(_capture_json(checker, ["--router", str(router), "--table", str(table), "--json"]))
        assert payload["decided"]["platform_admin"] == {
            "admin/users/:key": "GET /api/v1/admin/platform/x — require_platform_admin"
        }

    def test_a_route_in_two_buckets_across_the_axes_is_refused(
        self, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        router, table = build_pair(
            platform_routes=("admin/users/:key",),
            ungated=("admin/users/:key",),
        )
        assert ("decided-twice", "admin/users/:key") in rules(checker.collect(router, table))


class TestTheAxesDoNotSubstitute:
    """A wrapper of one axis never satisfies an entry of the other (REQ-049 §2.4).

    The failure this forbids is the plausible one: somebody "guards" an admin
    route with ``<RequireRole min="lead">`` because it reads like the strictest
    thing available. It is not the same question — a tenant lead is not a
    platform admin, and `require_platform_admin` would still answer 403 — so the
    check has to reject it rather than count it.
    """

    def test_a_role_wrapper_does_not_satisfy_a_platform_entry(
        self, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        router, table = build_pair(
            guarded_routes={"admin/users/:key": "lead"},
            declared_guarded={},
            declared_platform=("admin/users/:key",),
        )
        assert rules(checker.collect(router, table)) == [
            ("missing-platform-guard", "admin/users/:key"),
            ("undeclared-guard", "admin/users/:key"),
        ]

    def test_a_platform_wrapper_does_not_satisfy_a_role_entry(
        self, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        router, table = build_pair(
            platform_routes=("vermehrung",),
            declared_platform=(),
            declared_guarded={"vermehrung": "grower"},
        )
        assert rules(checker.collect(router, table)) == [
            ("missing-guard", "vermehrung"),
            ("undeclared-platform-guard", "vermehrung"),
        ]


class TestParsing:
    """Input handling that a green run would otherwise hide."""

    def test_a_route_named_only_in_prose_is_not_a_decision(self, build_pair: Callable[..., tuple[Path, Path]]) -> None:
        # The table's doc comments quote route paths to explain the buckets.
        # Counting those as entries would let the check pass on documentation
        # instead of on the lists — green on the wrong evidence.
        router, table = build_pair(plain_routes=("not-a-real-route",))
        assert rules(checker.collect(router, table)) == [("undecided-route", "not-a-real-route")]

    def test_a_line_comment_beside_an_entry_does_not_change_the_parse(
        self, tmp_path: Path, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        """A per-entry reason may contain an apostrophe (#1333).

        The buckets carry each decision's *reason* as a `//` comment beside it —
        that is what makes the table reviewable rather than a bare list. English
        reasons contain apostrophes, and before this was handled the first such
        comment made the parser read prose as route names: twelve decided routes
        were reported `undecided-route` and two comment fragments came back as
        `obsolete-decision`, on a table that was in fact complete.

        Fails against the pre-#1333 parser, which is the point.
        """
        router, table = build_pair(plain_routes=("a", "b"), ungated=("a", "b"))
        source = table.read_text(encoding="utf-8")
        source = source.replace(
            "  'a',",
            "  // RequireRole's restrict-only mode can't help here — it isn't a read page.\n  'a',",
            1,
        )
        table.write_text(source, encoding="utf-8")

        assert checker.collect(router, table) == []

    @pytest.mark.parametrize(
        "entries",
        [
            ("https://example.test/x", "a"),
            ("a", "https://example.test/x"),
            ("https://example.test/x",),
        ],
        ids=["first", "last", "sole"],
    )
    def test_an_entry_containing_comment_markers_is_parsed_intact(
        self, build_pair: Callable[..., tuple[Path, Path]], entries: tuple[str, ...]
    ) -> None:
        """A `//` or `/*` inside a quoted entry is part of the entry, not a comment.

        A stripper that cut comments blindly left a stump of the entry (or, for
        the last entry of a bucket, nothing at all) and reported it as a deleted
        route — a heuristic that only caught one of the shapes. The parser now
        recognises comments only outside string literals, so the entry survives
        in every position and the decision table is read as written. The URL is
        then simply a decision for a route the router does not have.
        """
        router, table = build_pair(plain_routes=("a",), ungated=entries)

        expected = [("obsolete-decision", "https://example.test/x")]
        if "a" not in entries:
            expected.append(("undecided-route", "a"))
        assert sorted(rules(checker.collect(router, table))) == sorted(expected)

    def test_element_before_path_is_refused_rather_than_mis_attributed(
        self, tmp_path: Path, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        _, table = build_pair(ungated=("a", "b"))
        router = tmp_path / "Swapped.tsx"
        router.write_text(
            '<Route element={<RequireRole min="grower"><A /></RequireRole>} path="a" />\n'
            '<Route path="b" element={<B />} />\n',
            encoding="utf-8",
        )
        with pytest.raises(checker.RouteGuardCheckError):
            checker.collect(router, table)

    def test_missing_table_is_a_usage_error_not_a_pass(
        self, tmp_path: Path, build_pair: Callable[..., tuple[Path, Path]]
    ) -> None:
        # NFR-018 §2: "I could not measure this" must never report green.
        router, _ = build_pair(plain_routes=("glossar",), ungated=("glossar",))
        code = checker.main(["--router", str(router), "--table", str(tmp_path / "nope.ts")])
        assert code == checker.EXIT_USAGE

    def test_json_output_carries_the_findings(
        self, build_pair: Callable[..., tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
    ) -> None:
        router, table = build_pair(plain_routes=("brandneu",))
        code = checker.main(["--router", str(router), "--table", str(table), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert code == checker.EXIT_FINDINGS
        assert payload["findings"][0]["route"] == "brandneu"


class TestShippedTree:
    """The one case that reads the real files: the tree in this commit passes."""

    def test_the_repository_router_is_fully_decided(self) -> None:
        repo_root = find_repo_root(Path(__file__).resolve())
        assert repo_root is not None
        router = repo_root / checker.DEFAULT_ROUTER
        table = repo_root / checker.DEFAULT_TABLE
        assert checker.collect(router, table) == []

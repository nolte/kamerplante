"""Tests for the join gate (``scripts/check_frontend_calls_served.py``).

**What is under test.** The extraction and the join, driven against *constructed*
miniature endpoint modules and route sets written into ``tmp_path`` — never
against the real ``src/frontend``. The shipped tree is joined for real by
``tests/unit/api/test_frontend_endpoints_are_served.py``; a second copy of that
assertion here would go red for the same reason twice and teach nobody anything.

**The deliberately-broken client.** :class:`TestItCanFail` reproduces the three
call shapes #1339 measured — including ``PUT``/``DELETE /tanks/sensors/{}``
verbatim, the paths the client actually held before this change — and asserts the
check goes red and names each. That is this file's red-first proof: the gate is
watched failing on the exact input it was built for, not merely passing on a tree
that has already been repaired. A gate nobody has seen fail is a gate nobody
knows works.

**The extraction traps, both measured on the real tree.** The join this file
guards was widened twice while #1339 was being fixed, because it was reporting a
clean result over less than it claimed:

* it anchored on the literal ``client.``, so the 18 modules that call
  ``tenantClient`` / ``globalClient`` / ``apiClient`` / ``plainClient`` were never
  scanned at all — 363 calls became 492 once that was fixed, and the extra ones
  turned up a fourth unserved call (``POST /starter-kits/{}/apply``);
* it resolved only ``const NAME = '…'`` bases, so the two nested resources whose
  base is a function (``diary.ts``, ``plantPhotos.ts``) produced eight ``{}/{}``
  false findings.

Both are pinned below, because a widening that is not tested is a widening that
the next refactor quietly reverts.

**The scan-shape trap.** ``include_router`` does not flatten, so a route walk
that reads ``app.routes`` directly finds *six* routes instead of ~790 and the
join then reports nearly everything as unserved. :func:`test_nested_routers_are_
walked_through_original_router` pins the walk that avoids it, on a router shaped
like FastAPI's wrapper rather than on the real app.

**Why here.** ``pytest tests/unit/`` from ``src/backend`` is a CI check, and the
script lives outside the backend package, so it is loaded by path.

Traces to #1334 / #1339 (no TC-ID: a source-tree gate is not a user-facing case).
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from tests.support.repo_scripts import load_repo_script

checker = load_repo_script("check_frontend_calls_served")


def write_module(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


class FakeRoute:
    """A leaf route, shaped like the attributes the walk reads."""

    def __init__(self, path: str, methods: set[str]) -> None:
        self.path = path
        self.methods = methods
        self.endpoint = object()


class FakeMount:
    """An ``include_router`` wrapper: its children hang off ``original_router``."""

    def __init__(self, path: str, inner: Any) -> None:
        self.path = path
        self.endpoint = None
        self.methods: set[str] = set()
        self.original_router = inner


class FakeRouter:
    def __init__(self, routes: list[Any]) -> None:
        self.routes = routes


class TestExtraction:
    def test_a_base_constant_is_resolved_into_the_path(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "tanks.ts",
            """
            const BASE = '/tanks';
            export async function getTank(key: string) {
              const { data } = await client.get<Tank>(`${BASE}/${key}`);
              return data;
            }
            """,
        )

        calls = checker.collect_frontend_calls(tmp_path)

        assert [(c.method, c.path) for c in calls] == [("GET", "/tanks/{}")]

    def test_every_interpolation_becomes_one_placeholder(self, tmp_path: Path) -> None:
        """Whatever the local variable is called, a ``${…}`` is a path parameter."""
        write_module(
            tmp_path,
            "sensors.ts",
            """
            const BASE = '/tanks';
            export async function update(tankKey: string, sensorKey: string) {
              await client.put(`${BASE}/${tankKey}/sensors/${sensorKey}`, payload);
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [
            ("PUT", "/tanks/{}/sensors/{}")
        ]

    def test_a_query_string_is_not_part_of_the_path(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "exports.ts",
            """
            const BASE = '/exports';
            export async function download(key: string) {
              await client.get(`${BASE}/${key}?format=pdf`);
            }
            """,
        )

        assert [c.path for c in checker.collect_frontend_calls(tmp_path)] == ["/exports/{}"]

    def test_the_type_parameter_between_verb_and_call_is_tolerated(self, tmp_path: Path) -> None:
        """``client.post<Foo>(`…`)`` is the dominant shape in the real modules."""
        write_module(
            tmp_path,
            "typed.ts",
            """
            const BASE = '/things';
            export async function make() {
              const { data } = await client.post<Thing>(`${BASE}`, body);
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [("POST", "/things")]

    def test_the_call_site_line_is_reported(self, tmp_path: Path) -> None:
        """The report has to say *where*, or a finding costs a grep to act on."""
        write_module(
            tmp_path,
            "lines.ts",
            """
            const BASE = '/things';

            export async function remove(key: string) {
              await client.delete(`${BASE}/${key}`);
            }
            """,
        )

        (call,) = checker.collect_frontend_calls(tmp_path)

        # The dedented body opens with a newline, so the call sits on line 5 of
        # the written file — counted from the file, which is what a reader greps.
        assert (call.line, call.module) == (5, "lines.ts")

    def test_every_client_identifier_is_scanned_not_only_the_literal_one(self, tmp_path: Path) -> None:
        """The gap that made this join measure a third less than it claimed.

        The modules reach for five request helpers — ``client``,
        ``tenantClient``, ``globalClient``, ``apiClient``, ``plainClient`` — and
        the original pattern anchored on the literal ``client.``. That silently
        skipped 18 of 60 endpoint modules, ``sites.ts`` among them, so a call
        added there could never be reported.
        """
        write_module(
            tmp_path,
            "many.ts",
            """
            const BASE = '/things';
            export async function a(k: string) { await client.get(`${BASE}/${k}`); }
            export async function b(k: string) { await tenantClient.put(`${BASE}/${k}`, x); }
            export async function c(k: string) { await globalClient.delete(`${BASE}/${k}`); }
            export async function d(k: string) { await apiClient.patch(`${BASE}/${k}`, x); }
            export async function e() { await plainClient.post(`${BASE}`, x); }
            """,
        )

        assert {c.method for c in checker.collect_frontend_calls(tmp_path)} == {
            "GET",
            "PUT",
            "DELETE",
            "PATCH",
            "POST",
        }

    def test_an_arrow_function_base_is_resolved(self, tmp_path: Path) -> None:
        """A nested resource names its base as a function, because the base has a parameter.

        Left unresolved, every call in ``diary.ts`` / ``plantPhotos.ts``
        normalises to ``{}/{}`` and is reported unserved — eight false findings,
        and a false finding is what turns a gate into a list of pre-approvals.
        """
        write_module(
            tmp_path,
            "diary.ts",
            """
            const base = (plantInstanceKey: string) =>
              `/plant-instances/${plantInstanceKey}/diary`;

            export async function get(plantKey: string, entryKey: string) {
              await tenantClient.get(`${base(plantKey)}/${entryKey}`);
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [
            ("GET", "/plant-instances/{}/diary/{}")
        ]

    def test_a_missing_directory_is_an_error_and_not_an_empty_scan(self, tmp_path: Path) -> None:
        """An empty operand must never read as "everything is served"."""
        with pytest.raises(checker.FrontendCallCheckError):
            checker.collect_frontend_calls(tmp_path / "gone")


class TestRouteWalk:
    def test_nested_routers_are_walked_through_original_router(self) -> None:
        app = FakeRouter(
            [
                FakeRoute("/health", {"GET"}),
                FakeMount(
                    "/api/v1/t/{tenant_slug}",
                    FakeRouter([FakeRoute("/tanks/{key}/sensors/{sensor_key}", {"PUT", "DELETE"})]),
                ),
            ]
        )

        assert checker.collect_mounted_routes(app) == {
            ("GET", "/health"),
            ("PUT", "/api/v1/t/{}/tanks/{}/sensors/{}"),
            ("DELETE", "/api/v1/t/{}/tanks/{}/sensors/{}"),
        }

    def test_a_flat_read_of_the_same_app_would_find_almost_nothing(self) -> None:
        """Pins *why* the walk exists, by measuring the shortcut that fails.

        Reading only the top level of the real app yields six routes; here it
        yields one. Either way the join then reports live calls as unserved.
        """
        app = FakeRouter(
            [
                FakeRoute("/health", {"GET"}),
                FakeMount("/api/v1", FakeRouter([FakeRoute("/tanks", {"GET"})])),
            ]
        )

        flat = {(method, route.path) for route in app.routes if route.endpoint is not None for method in route.methods}

        assert flat == {("GET", "/health")}
        assert len(checker.collect_mounted_routes(app)) == 2

    def test_a_websocket_style_route_without_methods_is_skipped(self) -> None:
        route = FakeRoute("/ws", set())
        route.methods = set()

        assert checker.collect_mounted_routes(FakeRouter([route])) == set()


class TestJoin:
    def test_a_call_matches_under_the_tenant_prefix(self) -> None:
        mounted = {("PUT", "/api/v1/t/{}/tanks/{}/sensors/{}")}

        assert checker.is_served("PUT", "/tanks/{}/sensors/{}", mounted)

    def test_a_call_matches_under_the_bare_api_prefix(self) -> None:
        mounted = {("GET", "/api/v1/species")}

        assert checker.is_served("GET", "/species", mounted)

    def test_the_method_is_part_of_the_match(self) -> None:
        """A path served for GET does not make its DELETE reachable."""
        mounted = {("GET", "/api/v1/t/{}/tanks/{}/sensors")}

        assert not checker.is_served("DELETE", "/tanks/{}/sensors", mounted)

    def test_the_placeholder_count_is_part_of_the_match(self) -> None:
        """``/tanks/sensors/{}`` and ``/tanks/{}/sensors/{}`` are different paths.

        This is the shape #1339 measured: the client's two-segment path looked
        close enough to a served three-segment one to survive review.
        """
        mounted = {("PUT", "/api/v1/t/{}/tanks/{}/sensors/{}")}

        assert not checker.is_served("PUT", "/tanks/sensors/{}", mounted)


class TestItCanFail:
    """The gate, watched failing on the three calls #1339 actually measured."""

    UNSERVED_CLIENT = """
        const BASE = '/tanks';
        export async function updateSensor(sensorKey: string) {
          await client.put(`${BASE}/sensors/${sensorKey}`, payload);
        }
        export async function deleteSensor(sensorKey: string) {
          await client.delete(`${BASE}/sensors/${sensorKey}`);
        }
    """
    TASKS_CLIENT = """
        const BASE = '/tasks';
        export async function uploadTaskPhoto(key: string) {
          await client.post(`${BASE}/${key}/photos`, formData);
        }
    """
    #: What the backend served before #1339 — create and list, no update, no
    #: delete, and nothing at all under ``/tasks/{}/photos``.
    MOUNTED_BEFORE = {
        ("GET", "/api/v1/t/{}/tanks/{}/sensors"),
        ("POST", "/api/v1/t/{}/tanks/{}/sensors"),
        ("POST", "/api/v1/t/{}/tasks/{}/complete"),
    }

    def test_the_three_measured_calls_are_reported(self, tmp_path: Path) -> None:
        write_module(tmp_path, "tanks.ts", self.UNSERVED_CLIENT)
        write_module(tmp_path, "tasks.ts", self.TASKS_CLIENT)

        unserved = checker.find_unserved(checker.collect_frontend_calls(tmp_path), self.MOUNTED_BEFORE)

        assert {(c.method, c.path) for c in unserved} == {
            ("PUT", "/tanks/sensors/{}"),
            ("DELETE", "/tanks/sensors/{}"),
            ("POST", "/tasks/{}/photos"),
        }

    def test_serving_them_clears_the_finding(self, tmp_path: Path) -> None:
        """The counter-check: the same client against the routes this PR adds."""
        write_module(
            tmp_path,
            "tanks.ts",
            """
            const BASE = '/tanks';
            export async function updateSensor(tankKey: string, sensorKey: string) {
              await client.put(`${BASE}/${tankKey}/sensors/${sensorKey}`, payload);
            }
            export async function deleteSensor(tankKey: string, sensorKey: string) {
              await client.delete(`${BASE}/${tankKey}/sensors/${sensorKey}`);
            }
            """,
        )
        write_module(tmp_path, "tasks.ts", self.TASKS_CLIENT)
        mounted = self.MOUNTED_BEFORE | {
            ("PUT", "/api/v1/t/{}/tanks/{}/sensors/{}"),
            ("DELETE", "/api/v1/t/{}/tanks/{}/sensors/{}"),
            ("POST", "/api/v1/t/{}/tasks/{}/photos"),
        }

        assert checker.find_unserved(checker.collect_frontend_calls(tmp_path), mounted) == []

    def test_the_report_exits_non_zero_and_names_the_call(self, tmp_path: Path, capsys) -> None:
        write_module(tmp_path, "tanks.ts", self.UNSERVED_CLIENT)
        calls = checker.collect_frontend_calls(tmp_path)

        code = checker.report(calls, checker.find_unserved(calls, self.MOUNTED_BEFORE), len(self.MOUNTED_BEFORE))

        assert code == checker.EXIT_FINDINGS
        assert "PUT /tanks/sensors/{} (tanks.ts:" in capsys.readouterr().err

    def test_a_clean_tree_exits_zero(self, tmp_path: Path) -> None:
        write_module(tmp_path, "tanks.ts", "const BASE = '/tanks';\n")
        calls = checker.collect_frontend_calls(tmp_path)

        assert checker.report(calls, [], 3) == checker.EXIT_OK

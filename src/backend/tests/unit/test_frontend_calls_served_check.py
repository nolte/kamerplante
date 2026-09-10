"""Tests for the join gate (``scripts/check_frontend_calls_served.py``).

**What is under test.** The extraction and the join, driven against *constructed*
miniature endpoint modules and — this is the part that had to change — a **real**
FastAPI application built with ``include_router(prefix=…)``. The shipped tree is
joined for real by ``tests/unit/api/test_frontend_endpoints_are_served.py``; a
second copy of that assertion here would go red for the same reason twice and
teach nobody anything.

**Why the route-side double is gone.** It used to be a hand-written ``FakeMount``
carrying a ``path`` attribute, and the walk under test read ``route.path``. Both
were wrong in the same direction: FastAPI's ``_IncludedRouter`` (0.139) has **no**
``path`` attribute at all — its prefix lives in ``include_context.prefix`` — so
the double invented a shape production never has and the test certified output
production never produced. That is the #947 / #1155 class exactly: a positive test
against an impossible fixture proves nothing. Measured against the real app before
the fix: 797 routes, **zero** carrying ``/t/{}``. After: 799 routes, 503 of them
tenant-scoped. The tests below therefore build a real app and assert against what
FastAPI actually mounts.

**The deliberately-broken client.** :class:`TestItCanFail` reproduces the three
call shapes #1339 measured — including ``PUT``/``DELETE /tanks/sensors/{}``
verbatim, the paths the client actually held before this change — and asserts the
check goes red and names each. That is this file's red-first proof: the gate is
watched failing on the exact input it was built for, not merely passing on a tree
that has already been repaired.

**The extraction traps, all measured on the real tree.** The join was widened
three times while #1339 was being fixed, because it kept reporting a clean result
over less than it claimed:

* it anchored on the literal ``client.``, so the 18 modules that call
  ``tenantClient`` / ``globalClient`` / ``apiClient`` / ``plainClient`` were never
  scanned — 363 calls became 492, and the extra ones turned up a fourth unserved
  call (``POST /starter-kits/{}/apply``);
* it resolved only ``const NAME = '…'`` bases, so the two nested resources whose
  base is a function (``diary.ts``, ``plantPhotos.ts``) produced eight ``{}/{}``
  false findings;
* it required a **backtick** argument, so ``client.get('/literal')``,
  ``client.get(BASE)`` and ``client.get(base(k))`` were dropped — 103 of 595 call
  sites, 17 %. 492 calls became 597.

Each is pinned below, and :func:`test_no_call_site_is_silently_skipped` pins the
*general* rule: an unsupported shape must be reported, never dropped. A scanner
that quietly narrows its own input is the same defect class as the unserved routes
it looks for.

**Why here.** ``pytest tests/unit/`` from ``src/backend`` is a CI check, and the
script lives outside the backend package, so it is loaded by path.

Traces to #1334 / #1339 (no TC-ID: a source-tree gate is not a user-facing case).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI

from tests.support.repo_scripts import load_repo_script

checker = load_repo_script("check_frontend_calls_served")


def write_module(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def build_app() -> FastAPI:
    """A real app mounted the way the production one is: nested prefixes.

    ``/api/v1`` → ``/t/{tenant_slug}`` → ``/tanks``, plus a global resource at
    ``/api/v1/species``. Built with the real ``include_router`` so the wrappers
    under test are real ``_IncludedRouter`` objects.
    """
    tanks = APIRouter(prefix="/tanks")

    @tanks.get("/{key}/sensors")
    def _list(key: str) -> dict:  # pragma: no cover - never called
        return {}

    @tanks.put("/{key}/sensors/{sensor_key}")
    def _update(key: str, sensor_key: str) -> dict:  # pragma: no cover
        return {}

    species = APIRouter(prefix="/species")

    @species.get("")
    def _species() -> dict:  # pragma: no cover
        return {}

    tenant = APIRouter(prefix="/t/{tenant_slug}")
    tenant.include_router(tanks)

    api = APIRouter(prefix="/api/v1")
    api.include_router(tenant)
    api.include_router(species)

    app = FastAPI()
    app.include_router(api)
    return app


class TestExtraction:
    def test_a_base_constant_is_resolved_into_the_path(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "tanks.ts",
            """
            import client from '../client';
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
            import client from '../client';
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
            import client from '../client';
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
            import client from '../client';
            const BASE = '/things';
            export async function make() {
              const { data } = await client.post<Thing>(`${BASE}`, body);
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [("POST", "/things")]

    def test_a_nested_generic_is_tolerated(self, tmp_path: Path) -> None:
        """``client.get<Record<string, X>>(…)`` — one of the 103 skipped shapes."""
        write_module(
            tmp_path,
            "nested.ts",
            """
            import client from '../client';
            export async function stats() {
              await client.get<Record<string, number>>('/stats');
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [("GET", "/stats")]

    def test_a_single_quoted_literal_is_resolved(self, tmp_path: Path) -> None:
        """No backticks, no interpolation — and formerly not scanned at all."""
        write_module(
            tmp_path,
            "plain.ts",
            """
            import client from '../client';
            export async function refresh() {
              await client.post('/ai/tips/refresh', null);
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [("POST", "/ai/tips/refresh")]

    def test_a_bare_base_constant_is_resolved(self, tmp_path: Path) -> None:
        """``client.get(BASE, { params })`` — a list route, formerly invisible."""
        write_module(
            tmp_path,
            "bare.ts",
            """
            import client from '../client';
            const BASE = '/activities';
            export async function list() {
              await client.get<Activity[]>(BASE, { params });
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [("GET", "/activities")]

    def test_an_arrow_function_base_is_resolved(self, tmp_path: Path) -> None:
        """A nested resource names its base as a function, because it has a parameter."""
        write_module(
            tmp_path,
            "diary.ts",
            """
            import { tenantClient } from '../client';
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

    def test_a_bare_arrow_base_call_is_resolved(self, tmp_path: Path) -> None:
        """``client.get(base(key))`` — the base *is* the whole path."""
        write_module(
            tmp_path,
            "photos.ts",
            """
            import { tenantClient } from '../client';
            const base = (key: string) => `/plant-instances/${key}/photos`;
            export async function list(key: string) {
              await tenantClient.get(base(key));
            }
            """,
        )

        assert [(c.method, c.path) for c in checker.collect_frontend_calls(tmp_path)] == [
            ("GET", "/plant-instances/{}/photos")
        ]

    def test_every_client_identifier_is_scanned_not_only_the_literal_one(self, tmp_path: Path) -> None:
        """The gap that made this join measure a third less than it claimed."""
        write_module(
            tmp_path,
            "many.ts",
            """
            import client from '../client';
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

    def test_the_call_site_line_is_reported(self, tmp_path: Path) -> None:
        """The report has to say *where*, or a finding costs a grep to act on."""
        write_module(
            tmp_path,
            "lines.ts",
            """
            import client from '../client';
            const BASE = '/things';

            export async function remove(key: string) {
              await client.delete(`${BASE}/${key}`);
            }
            """,
        )

        (call,) = checker.collect_frontend_calls(tmp_path)

        # The dedented body opens with a newline, so the call sits on line 6 of
        # the written file — counted from the file, which is what a reader greps.
        assert (call.line, call.module) == (6, "lines.ts")

    def test_a_missing_directory_is_an_error_and_not_an_empty_scan(self, tmp_path: Path) -> None:
        """An empty operand must never read as "everything is served"."""
        with pytest.raises(checker.FrontendCallCheckError):
            checker.collect_frontend_calls(tmp_path / "gone")


class TestNothingIsSilentlySkipped:
    """The check on the checker: an unsupported shape is reported, not dropped."""

    def test_a_shape_the_extractor_cannot_resolve_is_reported(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "weird.ts",
            """
            import client from '../client';
            export async function odd(url: string) {
              await client.get(buildSomeUrl(url) + suffix);
            }
            """,
        )

        unresolved = checker.unresolved_call_sites(tmp_path)

        assert [u.module for u in unresolved] == ["weird.ts"]
        assert "client.get(" in unresolved[0].source

    def test_a_resolvable_module_reports_nothing(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "fine.ts",
            """
            import client from '../client';
            const BASE = '/things';
            export async function list() { await client.get(BASE); }
            """,
        )

        assert checker.unresolved_call_sites(tmp_path) == []

    def test_an_unresolved_site_fails_the_report(self, tmp_path: Path, capsys) -> None:
        """Red, not merely printed — otherwise the invariant is decoration."""
        write_module(
            tmp_path,
            "weird.ts",
            """
            import client from '../client';
            export async function odd(u: string) { await client.get(makeUrl(u) + s); }
            """,
        )

        code = checker.report([], [], 10, checker.unresolved_call_sites(tmp_path))

        assert code == checker.EXIT_FINDINGS
        assert "could not resolve" in capsys.readouterr().err


class TestRouteWalk:
    """Driven against a real FastAPI app, because the wrapper shape is the trap."""

    def test_the_mount_prefixes_are_recovered(self) -> None:
        mounted = checker.collect_mounted_routes(build_app())

        assert ("GET", "/api/v1/t/{}/tanks/{}/sensors") in mounted
        assert ("PUT", "/api/v1/t/{}/tanks/{}/sensors/{}") in mounted
        assert ("GET", "/api/v1/species") in mounted

    def test_the_included_router_wrapper_really_has_no_path_attribute(self) -> None:
        """Pins *why* the walk reads ``include_context.prefix``.

        The previous walk did ``prefix + getattr(route, "path", "")`` and the
        test double invented the missing attribute, so both agreed on a shape
        FastAPI does not produce. If a future FastAPI grows ``path`` on the
        wrapper this test goes red and the walk can be simplified — deliberately,
        rather than by accident.
        """
        app = build_app()
        wrappers = [r for r in app.routes if hasattr(r, "original_router")]

        assert wrappers, "no _IncludedRouter wrapper — include_router changed shape"
        assert not hasattr(wrappers[0], "path")

        # And the prefix that *is* there is not the cumulative one, which is the
        # second thing a reader would guess wrong: `include_context.prefix` holds
        # the prefix of the router that performed the `include_router`, while the
        # included router's own prefix sits on `original_router.prefix` and is
        # already baked into its leaf paths. Accumulating the former down the
        # chain is therefore correct, and adding the latter would double-count.
        outer = wrappers[0]
        assert outer.include_context.prefix == ""
        assert outer.original_router.prefix == "/api/v1"
        inner = next(r for r in outer.original_router.routes if hasattr(r, "original_router"))
        assert inner.include_context.prefix == "/api/v1"
        assert inner.original_router.prefix == "/t/{tenant_slug}"

    def test_a_flat_read_of_the_same_app_finds_almost_nothing(self) -> None:
        """Pins the shortcut that fails, on the real object graph."""
        app = build_app()

        flat = {
            (method, route.path)
            for route in app.routes
            if getattr(route, "endpoint", None) is not None
            for method in getattr(route, "methods", ()) or ()
        }

        # FastAPI's own /docs, /redoc and /openapi.json are the only leaves at
        # the top level; every application route hides behind a wrapper.
        assert not any("/tanks" in path or "/species" in path for _method, path in flat)
        # The flat read finds not one application route; the walk finds all three.
        walked = checker.collect_mounted_routes(app)
        assert {path for _method, path in walked} >= {
            "/api/v1/species",
            "/api/v1/t/{}/tanks/{}/sensors",
            "/api/v1/t/{}/tanks/{}/sensors/{}",
        }

    def test_a_route_without_methods_is_skipped(self) -> None:
        class Router:
            routes: list = []

        assert checker.collect_mounted_routes(Router()) == set()


class TestJoin:
    def test_a_tenant_client_call_matches_a_tenant_route(self) -> None:
        mounted = checker.collect_mounted_routes(build_app())

        assert checker.is_served("PUT", "/tanks/{}/sensors/{}", mounted, checker.SCOPE_TENANT)

    def test_a_global_client_call_matches_a_global_route(self) -> None:
        mounted = checker.collect_mounted_routes(build_app())

        assert checker.is_served("GET", "/species", mounted, checker.SCOPE_GLOBAL)

    def test_a_tenant_route_issued_through_the_global_client_is_reported(self) -> None:
        """The 404 the prefix-less join could not see.

        ``/tanks/{key}/sensors`` exists only under ``/api/v1/t/{slug}``. Called
        through the default client the request goes to ``/api/v1/tanks/…`` and
        answers 404 — and with every mount prefix lost, both spellings looked
        identical to this check.
        """
        mounted = checker.collect_mounted_routes(build_app())
        call = checker.Call(
            method="GET", path="/tanks/{}/sensors", module="tanks.ts", line=1, scope=checker.SCOPE_GLOBAL
        )

        assert not checker.is_served(call.method, call.path, mounted, call.scope)
        assert checker.find_unserved([call], mounted) == [call]

    def test_the_scope_is_read_from_the_import_alias_not_the_identifier(self, tmp_path: Path) -> None:
        """24 modules bind the *tenant* client to the local name ``client``."""
        write_module(
            tmp_path,
            "tanks.ts",
            """
            import { tenantClient as client } from '../client';
            const BASE = '/tanks';
            export async function list() { await client.get(BASE); }
            """,
        )

        (call,) = checker.collect_frontend_calls(tmp_path)

        assert call.scope == checker.SCOPE_TENANT

    def test_a_default_import_is_the_global_scope(self, tmp_path: Path) -> None:
        write_module(
            tmp_path,
            "species.ts",
            """
            import client from '../client';
            const BASE = '/species';
            export async function list() { await client.get(BASE); }
            """,
        )

        (call,) = checker.collect_frontend_calls(tmp_path)

        assert call.scope == checker.SCOPE_GLOBAL

    def test_the_method_is_part_of_the_match(self) -> None:
        """A path served for GET does not make its DELETE reachable."""
        mounted = checker.collect_mounted_routes(build_app())

        assert not checker.is_served("DELETE", "/tanks/{}/sensors", mounted, checker.SCOPE_TENANT)

    def test_the_placeholder_count_is_part_of_the_match(self) -> None:
        """``/tanks/sensors/{}`` and ``/tanks/{}/sensors/{}`` are different paths.

        This is the shape #1339 measured: the client's two-segment path looked
        close enough to a served three-segment one to survive review.
        """
        mounted = checker.collect_mounted_routes(build_app())

        assert not checker.is_served("PUT", "/tanks/sensors/{}", mounted, checker.SCOPE_TENANT)


class TestItCanFail:
    """The gate, watched failing on the three calls #1339 actually measured."""

    UNSERVED_CLIENT = """
        import { tenantClient as client } from '../client';
        const BASE = '/tanks';
        export async function updateSensor(sensorKey: string) {
          await client.put(`${BASE}/sensors/${sensorKey}`, payload);
        }
        export async function deleteSensor(sensorKey: string) {
          await client.delete(`${BASE}/sensors/${sensorKey}`);
        }
    """
    TASKS_CLIENT = """
        import { tenantClient as client } from '../client';
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
            import { tenantClient as client } from '../client';
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
        assert "PUT /tanks/sensors/{}" in capsys.readouterr().err

    def test_a_clean_tree_exits_zero(self, tmp_path: Path) -> None:
        write_module(tmp_path, "tanks.ts", "const BASE = '/tanks';\n")
        calls = checker.collect_frontend_calls(tmp_path)

        assert checker.report(calls, [], 3) == checker.EXIT_OK

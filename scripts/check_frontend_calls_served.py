#!/usr/bin/env python3
"""Refuse a frontend API call that reaches no backend route.

Invoked directly::

    python3 scripts/check_frontend_calls_served.py
    python3 scripts/check_frontend_calls_served.py --list   # name every joined call
    python3 scripts/check_frontend_calls_served.py --json   # machine-readable

**What it enforces (#1334, #1339).** A frontend endpoint module can name a path
no route serves, and until #1334 nothing found out but a browser.
``POST /planting-runs/{}/batch-transition`` was live behind a button for as long
as the button existed, and its unit test asserted that *same wrong path*, so it
was green from the day it was written — a test that checks the client against
itself rather than against the contract. Running the join instead of fixing its
one instance turned up three more (#1339): sensor update, sensor delete (offered
from three pages) and task photo upload, all answering **404** to a live control.

The join is mechanical, so it is a check rather than a habit:

1. every ``<name>client.<verb>(`…`)`` call in
   ``src/frontend/src/api/endpoints/*.ts`` is resolved through its module-level
   base constants — both the ``const BASE = '…'`` form and the
   ``const base = (key) => `…`` form the nested resources use — its ``${…}``
   interpolations normalised to ``{}`` and its query string dropped;
2. every route the FastAPI app mounts is collected with its parameters
   normalised the same way;
3. a call must match one of them under the API prefix (``/api/v1``), under the
   tenant prefix (``/api/v1/t/{}``), or verbatim.

**Why this is not in the ``static`` pre-commit lane.** Its route operand is the
*mounted* app, which means importing ``app.main`` — FastAPI, pydantic, authlib,
the whole backend dependency set. The sibling gates in ``.pre-commit-config.yaml``
(``check_route_role_guards``, ``check_workflow_gate_integrity``) are pure text or
YAML checks precisely so they can run on a bare runner with none of this
project's dependencies installed. Re-deriving the route table from source text
would mean a second, drifting implementation of FastAPI's mounting rules — the
failure ``check_route_role_guards``' own docstring records for the same reason.
So this one runs where both operands already exist: the backend unit tier, via
``tests/unit/api/test_frontend_endpoints_are_served.py``, which is a required
per-PR gate.

**The mounting trap, said out loud.** ``include_router`` does **not** flatten:
read ``app.routes`` directly and you find *six* routes instead of ~790, the join
matches almost nothing, and — with the operands unchecked — it would report every
call as unserved or, with the assertion inverted, nothing at all. Both operands
are therefore size-checked by the calling test; an empty side is a broken scan,
never a pass.

**What it does not claim.** It matches on method + path template only. A route
that exists but rejects the body, or returns a shape the client mis-reads, passes
here — which is exactly what happened *around* #1334, whose response fields did
not match either. It rules out the one failure a browser is otherwise needed to
see: a call that cannot reach any handler at all.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where the frontend keeps one module per backend resource.
DEFAULT_ENDPOINT_DIR = "src/frontend/src/api/endpoints"
#: The backend package root, prepended to ``sys.path`` before importing the app.
DEFAULT_BACKEND_DIR = "src/backend"

#: ``<something>client.<verb>(`…`)`` — the request helpers every endpoint module
#: goes through. The identifier is matched as *any* name ending in ``client`` /
#: ``Client``, not the literal ``client``: the modules reach for five of them —
#: ``client``, ``tenantClient``, ``globalClient``, ``apiClient``, ``plainClient``
#: — some by import alias and some by their own name. Anchoring on the literal
#: (as this join originally did) silently skipped **18 of 60** endpoint modules,
#: including every call in ``sites.ts``: a check that reported a clean join over
#: a third of the surface it claimed to cover.
_CALL = re.compile(
    r"\b\w*[Cc]lient\.(get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*`([^`]+)`"
)
#: A module-level ``const NAME = 'value'`` — how most modules name their base
#: path. Any identifier, not only SCREAMING_CASE: the substitution only ever
#: fires on a ``${NAME}`` that appears inside a request template, so widening it
#: cannot pull in an unrelated constant.
_CONST = re.compile(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*'([^']+)'")
#: A module-level ``const base = (key) => `…`` — how the two nested resources
#: (``diary.ts``, ``plantPhotos.ts``) name theirs, because their base itself
#: carries a path parameter. Without resolving these, every one of their calls
#: normalises to ``{}/{}`` and is reported unserved: eight false findings that
#: would have to be silenced, and a silenced finding is how a register of
#: pre-approvals starts.
_ARROW_CONST = re.compile(
    r"const\s+([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=>\s*`([^`]+)`", re.DOTALL
)
#: Any ``${…}`` interpolation — a path parameter, whatever the local variable is called.
_INTERPOLATION = re.compile(r"\$\{[^}]*\}")
#: A path parameter on the backend side, ``{tenant_slug}`` and ``{key}`` alike.
_PATH_PARAM = re.compile(r"\{[^}]*\}")

_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


class FrontendCallCheckError(RuntimeError):
    """The check could not run at all — a broken operand, not a finding."""


@dataclass(frozen=True, order=True)
class Call:
    """One ``client.<verb>`` call site, with its path normalised for the join."""

    method: str
    path: str
    module: str
    line: int

    def describe(self) -> str:
        return f"{self.method} {self.path} ({self.module}:{self.line})"


def collect_frontend_calls(endpoint_dir: Path) -> list[Call]:
    """Every call the frontend endpoint modules issue, parameters as ``{}``.

    Args:
        endpoint_dir: Directory holding one ``*.ts`` module per backend resource.

    Returns:
        The calls, sorted, one entry per call site.

    Raises:
        FrontendCallCheckError: If *endpoint_dir* is not a directory.
    """
    if not endpoint_dir.is_dir():
        msg = f"{endpoint_dir} is not a directory"
        raise FrontendCallCheckError(msg)

    calls: list[Call] = []
    for module in sorted(endpoint_dir.glob("*.ts")):
        source = module.read_text(encoding="utf-8")
        constants = dict(_CONST.findall(source))
        base_functions = dict(_ARROW_CONST.findall(source))
        for match in _CALL.finditer(source):
            verb, template = match.group(1), match.group(2)
            path = template
            for name, value in constants.items():
                path = path.replace("${" + name + "}", value)
            for name, value in base_functions.items():
                path = re.sub(
                    r"\$\{" + re.escape(name) + r"\([^{}]*\)\}",
                    lambda _match, value=value: value,
                    path,
                )
            path = _INTERPOLATION.sub("{}", path).split("?")[0].rstrip("/") or "/"
            line = source.count("\n", 0, match.start()) + 1
            calls.append(
                Call(method=verb.upper(), path=path, module=module.name, line=line)
            )
    return sorted(calls)


def collect_mounted_routes(app: Any) -> set[tuple[str, str]]:
    """Every ``(method, path)`` the app serves, with parameters normalised to ``{}``.

    Walks ``original_router`` because ``include_router`` does not flatten: read
    ``app.routes`` and you find six routes instead of ~790, and the scan looks
    like it worked.

    Args:
        app: The mounted FastAPI application.

    Returns:
        The mounted operations as ``(METHOD, path)`` pairs.
    """
    found: set[tuple[str, str]] = set()

    def walk(router: Any, prefix: str = "") -> None:
        for route in getattr(router, "routes", []):
            path = prefix + getattr(route, "path", "")
            if getattr(route, "endpoint", None) is not None:
                for method in getattr(route, "methods", ()) or ():
                    if method in _HTTP_METHODS:
                        found.add((method, _PATH_PARAM.sub("{}", path)))
            inner = getattr(route, "original_router", None) or getattr(
                route, "app", None
            )
            if inner is not None and hasattr(inner, "routes"):
                walk(inner, path)

    walk(app)
    return found


def is_served(method: str, path: str, mounted: set[tuple[str, str]]) -> bool:
    """Whether *method* + *path* reaches a mounted route.

    A frontend path may be written with or without the API prefix and without
    the tenant segment, because the axios clients supply both.
    """
    candidates = (f"/api/v1{path}", "/api/v1/t/{}" + path, path)
    return any((method, candidate) in mounted for candidate in candidates)


def find_unserved(calls: list[Call], mounted: set[tuple[str, str]]) -> list[Call]:
    """The calls in *calls* that no route in *mounted* serves."""
    return [call for call in calls if not is_served(call.method, call.path, mounted)]


def load_app(backend_dir: Path) -> Any:
    """Import the mounted FastAPI application from *backend_dir*.

    Raises:
        FrontendCallCheckError: If the backend package is not importable.
    """
    if not (backend_dir / "app" / "main.py").is_file():
        msg = f"{backend_dir}/app/main.py does not exist"
        raise FrontendCallCheckError(msg)
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    try:
        from app.main import app
    except ImportError as exc:  # pragma: no cover — only without backend deps
        msg = f"the backend app is not importable ({exc}); this check needs the backend environment"
        raise FrontendCallCheckError(msg) from exc
    return app


def report(
    calls: list[Call],
    unserved: list[Call],
    route_count: int,
    *,
    list_all: bool = False,
    as_json: bool = False,
) -> int:
    """Print the outcome and return the process exit code."""
    if as_json:
        payload = {
            "calls": len(calls),
            "routes": route_count,
            "unserved": [
                {"method": c.method, "path": c.path, "module": c.module, "line": c.line}
                for c in unserved
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_FINDINGS if unserved else EXIT_OK

    if unserved:
        print(
            f"check_frontend_calls_served: {len(unserved)} of {len(calls)} frontend calls "
            f"reach none of the {route_count} mounted routes:",
            file=sys.stderr,
        )
        for call in unserved:
            print(f"  {call.describe()}", file=sys.stderr)
        print(
            "\nEach is a live control that answers 404. Either serve the path or "
            "take the control out of the UI (#1339).",
            file=sys.stderr,
        )
        return EXIT_FINDINGS

    print(
        f"check_frontend_calls_served: {len(calls)} frontend calls, all served by {route_count} mounted routes."
    )
    if list_all:
        for call in calls:
            print(f"  {call.describe()}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--endpoint-dir",
        metavar="PATH",
        default=None,
        help=f"frontend endpoint modules to scan (default: {DEFAULT_ENDPOINT_DIR})",
    )
    parser.add_argument(
        "--backend-dir",
        metavar="PATH",
        default=None,
        help=f"backend package root to import the app from (default: {DEFAULT_BACKEND_DIR})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_all",
        help="also name every call when the check passes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the findings as JSON instead of the human report",
    )
    args = parser.parse_args(argv)

    endpoint_dir = _resolve(args.endpoint_dir, DEFAULT_ENDPOINT_DIR)
    backend_dir = _resolve(args.backend_dir, DEFAULT_BACKEND_DIR)

    try:
        calls = collect_frontend_calls(endpoint_dir)
        mounted = collect_mounted_routes(load_app(backend_dir))
    except FrontendCallCheckError as exc:
        print(f"check_frontend_calls_served: {exc}", file=sys.stderr)
        return EXIT_USAGE

    return report(
        calls,
        find_unserved(calls, mounted),
        len(mounted),
        list_all=args.list_all,
        as_json=args.json,
    )


def _resolve(raw: str | None, default: str) -> Path:
    value = raw or default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())

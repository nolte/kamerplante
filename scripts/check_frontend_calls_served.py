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

1. every ``<name>client.<verb>(…)`` call in
   ``src/frontend/src/api/endpoints/*.ts`` has its **first argument** resolved —
   template literal, quoted string, bare base constant or base *function* call —
   through the module's own constants, with ``${…}`` interpolations normalised
   to ``{}`` and the query string dropped;
2. every route the FastAPI app mounts is collected **with its mount prefixes**,
   parameters normalised the same way;
3. the call must match a route **in its own scope**: a module that imports
   ``tenantClient`` (under any local alias) addresses ``/api/v1/t/{}/…``, one
   that imports the default client addresses ``/api/v1/…``.

**Two ways this check has already lied, both fixed here rather than trusted.**

*It lost every mount prefix.* The walk did ``prefix + route.path``, but FastAPI's
``_IncludedRouter`` (0.139) has **no** ``path`` attribute at all — the prefix
lives in ``include_context.prefix``. Measured before the fix: 797 routes, **zero**
carrying ``/t/{}`` and three starting with ``/api/v1``, so the tenant/global
distinction could not be made and only a verbatim match ever fired. After:
**799 routes, 503 of them under** ``/api/v1/t/{}``. That is what makes rule 3
possible at all — and rule 3 is what catches a call issued through the *wrong*
client, which is a 404 the old join could not see.

*It skipped 17 % of the call sites.* Anchoring on a backtick argument dropped
every ``client.get('/literal')``, ``client.get(BASE)`` and ``client.get(base(k))``
— 103 of 595 sites. Rule 1 now resolves all four shapes, and
:func:`unresolved_call_sites` reports any site the extractor could not resolve,
so the *next* unsupported shape is a red gate instead of a silent omission. That
invariant is the load-bearing one: a scanner that quietly narrows its own input
is the same defect class as the unserved routes it looks for.

**The mounting trap, said out loud.** ``include_router`` does **not** flatten:
read ``app.routes`` directly and you find *six* routes instead of ~800, the join
matches almost nothing, and — with the operands unchecked — it would report every
call as unserved or, with the assertion inverted, nothing at all. Both operands
are therefore size-checked by the calling test; an empty side is a broken scan,
never a pass.

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

#: The API prefix every axios instance carries as its ``baseURL``.
API_PREFIX = "/api/v1"
#: What ``tenantClient`` additionally prepends, with the slug normalised.
TENANT_PREFIX = "/api/v1/t/{}"

#: Scope names. ``tenant`` = the client that builds ``/t/{slug}/…`` into the URL;
#: ``global`` = the default client, which passes the tenant in a header instead.
SCOPE_TENANT = "tenant"
SCOPE_GLOBAL = "global"

#: ``<name>client.<verb>(`` — the request helpers every endpoint module goes
#: through. The identifier is matched as *any* name ending in ``client`` /
#: ``Client``, not the literal ``client``: the modules reach for five of them —
#: ``client``, ``tenantClient``, ``globalClient``, ``apiClient``, ``plainClient``
#: — some by import alias and some by their own name. Anchoring on the literal
#: (as this join originally did) silently skipped 18 of 60 endpoint modules,
#: ``sites.ts`` included.
_CALL_SITE = re.compile(
    r"\b(\w*[Cc]lient)\.(get|post|put|patch|delete)\s*(?:<.*?>)?\s*\("
)
#: A module-level ``const NAME = 'value'`` — how most modules name their base
#: path. Any identifier, not only SCREAMING_CASE: the substitution only ever
#: fires on a name that appears in request position, so widening it cannot pull
#: in an unrelated constant.
_CONST = re.compile(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*['\"]([^'\"]+)['\"]")
#: A module-level ``const base = (key) => `…`` — how the two nested resources
#: (``diary.ts``, ``plantPhotos.ts``) name theirs, because their base itself
#: carries a path parameter.
_ARROW_CONST = re.compile(
    r"const\s+([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=>\s*[`'\"]([^`'\"]+)[`'\"]",
    re.DOTALL,
)
#: ``import <default>, { a as b, c } from '../client'`` — how each module names
#: the axios instances it uses. Resolving this is what makes the join
#: scope-aware: 24 modules import ``tenantClient`` *under the local name*
#: ``client``, so the identifier alone says nothing about which prefix applies.
_IMPORT = re.compile(r"import\s+(.+?)\s+from\s+['\"][^'\"]*client['\"]", re.DOTALL)
#: Any ``${…}`` interpolation — a path parameter, whatever the local variable is called.
_INTERPOLATION = re.compile(r"\$\{[^}]*\}")
#: A path parameter on the backend side, ``{tenant_slug}`` and ``{key}`` alike.
_PATH_PARAM = re.compile(r"\{[^}]*\}")
#: A whole first argument that is just ``name`` or ``name(...)``.
_BARE_NAME = re.compile(r"^([A-Za-z_$][\w$]*)(?:\((?:[^()]|\([^()]*\))*\))?$")

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
    scope: str = SCOPE_GLOBAL

    def describe(self) -> str:
        return f"{self.method} {self.path} [{self.scope}] ({self.module}:{self.line})"


@dataclass(frozen=True, order=True)
class UnresolvedSite:
    """A ``client.<verb>(`` the extractor could not turn into a path."""

    module: str
    line: int
    source: str

    def describe(self) -> str:
        return f"{self.module}:{self.line}: {self.source}"


def _client_scopes(source: str) -> dict[str, str]:
    """Map each local axios identifier in *source* onto its scope.

    ``import { tenantClient as client }`` binds the *tenant* client to the name
    ``client``, which is why the identifier alone cannot decide the prefix.
    """
    scopes: dict[str, str] = {}
    for clause in _IMPORT.findall(source):
        named = re.search(r"\{(.*?)\}", clause, re.DOTALL)
        default = (
            re.sub(r"\{.*?\}", "", clause, flags=re.DOTALL).replace(",", " ").strip()
        )
        if default:
            scopes[default] = SCOPE_GLOBAL
        if named:
            for entry in named.group(1).split(","):
                parts = [p.strip() for p in entry.split(" as ") if p.strip()]
                if not parts:
                    continue
                imported, local = parts[0], parts[-1]
                scopes[local] = (
                    SCOPE_TENANT if imported == "tenantClient" else SCOPE_GLOBAL
                )
    return scopes


def _first_argument(source: str, open_paren: int) -> str | None:
    """Return the text of the call's first argument, or ``None`` if unbalanced."""
    depth = 0
    start = open_paren + 1
    for index in range(open_paren, len(source)):
        char = source[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                return source[start:index].strip()
        elif char == "," and depth == 1:
            return source[start:index].strip()
    return None


def _resolve(
    expression: str, constants: dict[str, str], bases: dict[str, str]
) -> str | None:
    """Turn a first-argument expression into a normalised path, or ``None``.

    Handles the four shapes the endpoint modules actually use: a template
    literal, a quoted string, a bare base constant, and a base *function* call.
    Anything else returns ``None`` and is reported as an unresolved site rather
    than silently dropped.
    """
    text = expression.strip()
    if not text:
        return None

    bare = _BARE_NAME.match(text)
    if bare:
        name = bare.group(1)
        value = bases.get(name) if text.endswith(")") else constants.get(name)
        if value is None:
            value = constants.get(name) or bases.get(name)
        if value is None:
            return None
        text = value
    elif text[0] in "`'\"" and text[-1] == text[0] and len(text) >= 2:
        text = text[1:-1]
    else:
        return None

    for name, value in constants.items():
        text = text.replace("${" + name + "}", value)
    for name, value in bases.items():
        text = re.sub(
            r"\$\{" + re.escape(name) + r"\([^{}]*\)\}", lambda _m, v=value: v, text
        )

    path = _INTERPOLATION.sub("{}", text).split("?")[0].rstrip("/") or "/"
    return path if path.startswith("/") else None


def _scan_module(module: Path) -> tuple[list[Call], list[UnresolvedSite]]:
    source = module.read_text(encoding="utf-8")
    constants = dict(_CONST.findall(source))
    bases = dict(_ARROW_CONST.findall(source))
    scopes = _client_scopes(source)

    calls: list[Call] = []
    unresolved: list[UnresolvedSite] = []
    for match in _CALL_SITE.finditer(source):
        identifier, verb = match.group(1), match.group(2)
        line = source.count("\n", 0, match.start()) + 1
        argument = _first_argument(source, match.end() - 1)
        path = _resolve(argument, constants, bases) if argument is not None else None
        if path is None:
            unresolved.append(
                UnresolvedSite(
                    module=module.name,
                    line=line,
                    source=source[match.start() : match.end() + 40].split("\n")[0],
                )
            )
            continue
        calls.append(
            Call(
                method=verb.upper(),
                path=path,
                module=module.name,
                line=line,
                scope=scopes.get(identifier, SCOPE_GLOBAL),
            )
        )
    return calls, unresolved


def collect_frontend_calls(endpoint_dir: Path) -> list[Call]:
    """Every call the frontend endpoint modules issue, parameters as ``{}``.

    Args:
        endpoint_dir: Directory holding one ``*.ts`` module per backend resource.

    Returns:
        The calls, sorted, one entry per resolvable call site.

    Raises:
        FrontendCallCheckError: If *endpoint_dir* is not a directory.
    """
    if not endpoint_dir.is_dir():
        msg = f"{endpoint_dir} is not a directory"
        raise FrontendCallCheckError(msg)

    calls: list[Call] = []
    for module in sorted(endpoint_dir.glob("*.ts")):
        found, _ = _scan_module(module)
        calls.extend(found)
    return sorted(calls)


def unresolved_call_sites(endpoint_dir: Path) -> list[UnresolvedSite]:
    """Call sites the extractor could not resolve into a path.

    This is the check on the checker. A scanner that narrows its own input
    without saying so reports a clean join over a surface it never looked at —
    which this one did twice before it was measured. Anything reported here is
    a shape the extractor must learn, not a call to excuse.

    Raises:
        FrontendCallCheckError: If *endpoint_dir* is not a directory.
    """
    if not endpoint_dir.is_dir():
        msg = f"{endpoint_dir} is not a directory"
        raise FrontendCallCheckError(msg)

    unresolved: list[UnresolvedSite] = []
    for module in sorted(endpoint_dir.glob("*.ts")):
        _, missed = _scan_module(module)
        unresolved.extend(missed)
    return sorted(unresolved)


def collect_mounted_routes(app: Any) -> set[tuple[str, str]]:
    """Every ``(method, path)`` the app serves, **with its mount prefixes**.

    ``include_router`` does not flatten: read ``app.routes`` and you find six
    routes instead of ~800. The wrappers FastAPI leaves behind are
    ``_IncludedRouter`` objects, and — this is the part that made the previous
    version of this walk useless — they carry **no** ``path`` attribute. Their
    prefix lives in ``include_context.prefix``. Reading ``route.path`` with a
    ``getattr`` default therefore silently produced ``""`` for every mount, and
    the whole route table came out relative: zero routes under ``/t/{}``, three
    under ``/api/v1``.

    Args:
        app: The mounted FastAPI application (or any router-shaped object).

    Returns:
        The mounted operations as ``(METHOD, path)`` pairs.
    """
    found: set[tuple[str, str]] = set()

    def walk(router: Any, prefix: str = "") -> None:
        for route in getattr(router, "routes", []):
            included = getattr(route, "original_router", None)
            if included is not None:
                context = getattr(route, "include_context", None)
                walk(included, prefix + (getattr(context, "prefix", "") or ""))
                continue
            path = prefix + (getattr(route, "path", "") or "")
            if getattr(route, "endpoint", None) is not None:
                for method in getattr(route, "methods", ()) or ():
                    if method in _HTTP_METHODS:
                        found.add((method, _PATH_PARAM.sub("{}", path)))
            sub = getattr(route, "app", None)
            if sub is not None and hasattr(sub, "routes"):
                walk(sub, path)

    walk(app)
    return found


def is_served(
    method: str, path: str, mounted: set[tuple[str, str]], scope: str = SCOPE_GLOBAL
) -> bool:
    """Whether *method* + *path* reaches a mounted route **in its own scope**.

    The scope is what the module's import decided: ``tenantClient`` builds
    ``/t/{slug}`` into the URL, the default client does not and passes the tenant
    in a header. A call issued through the wrong one is a 404 in the browser, and
    before the prefixes were recovered this join could not tell the two apart.
    """
    prefix = TENANT_PREFIX if scope == SCOPE_TENANT else API_PREFIX
    return (method, prefix + path) in mounted


def find_unserved(calls: list[Call], mounted: set[tuple[str, str]]) -> list[Call]:
    """The calls in *calls* that no route in *mounted* serves in their scope."""
    return [
        call
        for call in calls
        if not is_served(call.method, call.path, mounted, call.scope)
    ]


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
    unresolved: list[UnresolvedSite] | None = None,
    *,
    list_all: bool = False,
    as_json: bool = False,
) -> int:
    """Print the outcome and return the process exit code."""
    unresolved = unresolved or []
    if as_json:
        payload = {
            "calls": len(calls),
            "routes": route_count,
            "unserved": [
                {
                    "method": c.method,
                    "path": c.path,
                    "scope": c.scope,
                    "module": c.module,
                    "line": c.line,
                }
                for c in unserved
            ],
            "unresolved": [
                {"module": u.module, "line": u.line, "source": u.source}
                for u in unresolved
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return EXIT_FINDINGS if (unserved or unresolved) else EXIT_OK

    if unresolved:
        print(
            f"check_frontend_calls_served: {len(unresolved)} call site(s) the extractor could not resolve — "
            "the join would silently skip them:",
            file=sys.stderr,
        )
        for site in unresolved:
            print(f"  {site.describe()}", file=sys.stderr)

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

    if unserved or unresolved:
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

    endpoint_dir = _resolve_path(args.endpoint_dir, DEFAULT_ENDPOINT_DIR)
    backend_dir = _resolve_path(args.backend_dir, DEFAULT_BACKEND_DIR)

    try:
        calls = collect_frontend_calls(endpoint_dir)
        unresolved = unresolved_call_sites(endpoint_dir)
        mounted = collect_mounted_routes(load_app(backend_dir))
    except FrontendCallCheckError as exc:
        print(f"check_frontend_calls_served: {exc}", file=sys.stderr)
        return EXIT_USAGE

    return report(
        calls,
        find_unserved(calls, mounted),
        len(mounted),
        unresolved,
        list_all=args.list_all,
        as_json=args.json,
    )


def _resolve_path(raw: str | None, default: str) -> Path:
    value = raw or default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())

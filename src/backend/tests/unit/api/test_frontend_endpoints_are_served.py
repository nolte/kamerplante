"""Every frontend API call names a path some backend route serves (#1334, #1339).

A frontend endpoint module can name a path no route serves, and until #1334
nothing found out but a browser. ``POST /planting-runs/{}/batch-transition`` was
live behind a button for as long as the button existed; its unit test asserted
that same wrong path, so it was green from the day it was written — a test that
checks the client against itself rather than against the contract. Running the
join instead of repairing its one instance found three more (#1339).

The join itself lives in ``scripts/check_frontend_calls_served.py``, so it can
also be run by hand while a route is being written; this module is where it
*runs*, because the backend unit tier is a required per-PR gate and already
holds both operands — the FastAPI app is importable here and the endpoint
modules are text. #1334 supposed this would need a nightly lane, "because the
`static` lane does not have the importable app": measured, it needs neither.

**Three invariants, not one.** The join is only worth its green when the scan
that feeds it is honest, and this one was twice not:

1. *every call is served* — the rule itself, scope-aware since the mount
   prefixes were recovered (a tenant route called through the global client is a
   404 the prefix-less join could not see);
2. *no call site is silently skipped* — the extractor reports any shape it
   cannot resolve, and an unreported shape is how this check came to cover 82 %
   of the call sites while reporting a clean result;
3. *both operands are non-empty and correctly shaped* — an empty side passes
   vacuously, and a route table with no ``/t/{}`` in it means the prefixes were
   lost again.

There is deliberately **no register of known-unserved calls** any more. The one
#1334 introduced held #1339's three, and all three are served now; an empty
register with a test over it is a check that cannot fail (NFR-018 §2), and a
non-empty one is a list of pre-approvals. The rule is the plain one: zero.

**What it does not claim.** It matches on method + path template only. A route
that exists but rejects the body, or returns a shape the client mis-reads,
passes here — that is exactly what happened *around* #1334, whose response
fields did not match either.
"""

from __future__ import annotations

from pathlib import Path

from tests.support.repo_scripts import find_repo_root, load_repo_script

checker = load_repo_script("check_frontend_calls_served")

_REPO_ROOT = find_repo_root(Path(__file__).resolve())
_ENDPOINT_DIR = (_REPO_ROOT or Path()) / "src" / "frontend" / "src" / "api" / "endpoints"


def _mounted_routes() -> set[tuple[str, str]]:
    from app.main import app

    return checker.collect_mounted_routes(app)


def test_the_scan_found_both_operands() -> None:
    """Neither side may be silently empty — an empty join passes vacuously.

    Without this the whole file reads green if ``include_router`` changes shape
    (read flat, ``app.routes`` yields *six* routes) or the endpoint directory
    moves, which is the failure mode it exists to prevent.
    """
    assert len(_mounted_routes()) > 500
    # 597 calls at the time of writing. The bound sits close on purpose: the
    # scan found 363 while it recognised only one of the five request helpers,
    # and 492 while it required a backtick argument. A loose bound would have
    # reported either of those partial scans as healthy (#1339).
    assert len(checker.collect_frontend_calls(_ENDPOINT_DIR)) > 550


def test_the_mount_prefixes_survived_the_walk() -> None:
    """A route table with no tenant prefix in it means the walk lost them again.

    ``_IncludedRouter`` carries no ``path`` attribute, so a walk that reads
    ``route.path`` silently returns every route *relative* — measured once as
    797 routes with **zero** under ``/t/{}``. The join then cannot tell a
    tenant-scoped path from a global one, and rule 3 of the module docstring
    becomes decoration. 503 of 799 are tenant-scoped as this is written.
    """
    mounted = _mounted_routes()

    tenant_scoped = [path for _method, path in mounted if path.startswith("/api/v1/t/{}")]
    assert len(tenant_scoped) > 400, "the mount prefixes were lost — the walk is reading route.path again"
    assert all(path.startswith("/api") for _method, path in mounted if "health" not in path and "docs" not in path)


def test_no_call_site_is_silently_skipped() -> None:
    """The scanner must report a shape it cannot resolve, never drop it.

    This is the load-bearing one. A gate that quietly narrows its own input
    reports a clean join over a surface it never looked at, which is the same
    defect class as the unserved routes it exists to find — and it happened
    twice here before it was measured (18 of 60 modules, then 103 of 595 call
    sites).
    """
    unresolved = checker.unresolved_call_sites(_ENDPOINT_DIR)

    assert not unresolved, "call sites the join cannot resolve (teach the extractor the shape): " + "; ".join(
        site.describe() for site in unresolved
    )


def test_every_frontend_call_reaches_a_route() -> None:
    unserved = checker.find_unserved(checker.collect_frontend_calls(_ENDPOINT_DIR), _mounted_routes())

    assert not unserved, "frontend calls no backend route serves: " + "; ".join(call.describe() for call in unserved)

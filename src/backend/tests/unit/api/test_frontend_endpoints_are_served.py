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

**What it does not claim.** It matches on method + path template only. A route
that exists but rejects the body, or returns a shape the client mis-reads,
passes here — that is exactly what happened *around* #1334, whose response
fields did not match either. It rules out the one failure a browser is otherwise
needed to see: a call that cannot reach any handler at all.

There is deliberately **no register of known-unserved calls** any more. The one
#1334 introduced held #1339's three, and all three are served now; an empty
register with a test over it is a check that cannot fail (NFR-018 §2), and a
non-empty one is a list of pre-approvals. The rule is the plain one: zero.
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
    # 492 calls at the time of writing. The bound sits close on purpose: the
    # scan used to find 363 because it only recognised one of the five request
    # helpers the modules use, and a loose bound would have reported that
    # two-thirds scan as healthy (#1339).
    assert len(checker.collect_frontend_calls(_ENDPOINT_DIR)) > 450


def test_every_frontend_call_reaches_a_route() -> None:
    unserved = checker.find_unserved(checker.collect_frontend_calls(_ENDPOINT_DIR), _mounted_routes())

    assert not unserved, "frontend calls no backend route serves: " + "; ".join(call.describe() for call in unserved)

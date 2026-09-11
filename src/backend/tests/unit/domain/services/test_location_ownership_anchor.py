"""The shared Location/Slot ownership anchor, and that it has no private copies left (#1397).

``Location`` and ``Slot`` carry a ``tenant_key`` the write path never fills:
``LocationCreate`` may not declare one (``check_tenant_body_field``, #1000) and
``create_location`` does ``Location(**body.model_dump())``. Nine sites read that
empty field as if it meant something, failing in three directions — five refusing
the tenant's own data, two holding a condition that can never be true, one
projection answering ``null`` where a name belongs.

Two things are asserted here, and the second is the one that matters in a year:

1. The anchor answers correctly in both directions, with a control against the
   over-rejecting failure that made the whole class invisible (#706, #1352) — a
   guard that refuses everything passes every negative test ever written for it.
2. No module resolves ownership against ``location.tenant_key`` or
   ``slot.tenant_key`` again. That is a source sweep, not a behaviour test,
   because the failure mode is a *new* call site rather than a changed one.
"""

import ast
import pathlib
from collections.abc import Callable

import pytest

from app.common.exceptions import NotFoundError
from app.domain.models.site import Location, Site, Slot
from app.domain.services.location_ownership import (
    find_owned_location,
    require_owned_site,
    resolve_owned_location,
    resolve_owned_slot,
)

TENANT = "tenant_own"
OTHER = "tenant_other"


class FakeSiteSource:
    """Sites, locations and slots shaped the way the application stores them.

    Locations and slots are built **without** a ``tenant_key`` on purpose: a
    double that invents one lets an ownership check written against that field
    pass, which is exactly how nine broken sites stayed green. Name an input this
    accepts and the real repository would not, and the double is wrong — there is
    none, because the rows here are the rows ``create_location`` writes.
    """

    def __init__(self) -> None:
        self.sites = {
            "site_own": Site(_key="site_own", tenant_key=TENANT, name="Zuhause", type="indoor"),
            "site_other": Site(_key="site_other", tenant_key=OTHER, name="Woanders", type="indoor"),
        }
        self.locations = {
            "loc_own": Location(_key="loc_own", name="Beet A", area_m2=1.0, site_key="site_own"),
            "loc_other": Location(_key="loc_other", name="Beet B", area_m2=1.0, site_key="site_other"),
            "loc_orphan": Location(_key="loc_orphan", name="Beet C", area_m2=1.0, site_key=""),
        }
        self.slots = {
            "slot_own": Slot(_key="slot_own", location_key="loc_own", slot_id="LOCOWN_A1"),
            "slot_other": Slot(_key="slot_other", location_key="loc_other", slot_id="LOCOTHER_B1"),
        }

    def get_site_by_key(self, key):
        return self.sites.get(key)

    def get_location_by_key(self, key):
        return self.locations.get(key)

    def get_slot_by_key(self, key):
        return self.slots.get(key)


@pytest.fixture
def source() -> FakeSiteSource:
    return FakeSiteSource()


class TestResolveOwnedLocation:
    def test_the_tenants_own_location_is_found(self, source):
        """The control, and the case that was red before #1397.

        Without this assertion the three refusals below are satisfied by a guard
        that refuses *everything* — which is what five sites actually did.
        """
        assert resolve_owned_location(source, "loc_own", TENANT).key == "loc_own"

    def test_a_foreign_location_is_refused(self, source):
        with pytest.raises(NotFoundError):
            resolve_owned_location(source, "loc_other", TENANT)

    def test_an_absent_location_is_refused(self, source):
        with pytest.raises(NotFoundError):
            resolve_owned_location(source, "loc_missing", TENANT)

    def test_a_location_without_a_site_is_refused(self, source):
        """There is nothing to anchor against, so the answer is no, not yes."""
        with pytest.raises(NotFoundError):
            resolve_owned_location(source, "loc_orphan", TENANT)

    def test_absent_and_foreign_answer_identically(self, source):
        """Otherwise the message is the existence oracle the 404 exists to prevent."""
        with pytest.raises(NotFoundError) as absent:
            resolve_owned_location(source, "loc_missing", TENANT)
        with pytest.raises(NotFoundError) as foreign:
            resolve_owned_location(source, "loc_other", TENANT)
        assert str(absent.value).replace("loc_missing", "X") == str(foreign.value).replace("loc_other", "X")

    def test_the_refusal_never_names_the_site(self, source):
        """A message naming ``site_other`` would disclose the site behind the wall."""
        with pytest.raises(NotFoundError) as exc:
            resolve_owned_location(source, "loc_other", TENANT)
        assert "site_other" not in str(exc.value)


class TestResolveOwnedSlot:
    def test_the_tenants_own_slot_is_found_with_its_location(self, source):
        slot, location = resolve_owned_slot(source, "slot_own", TENANT)
        assert slot.key == "slot_own"
        assert location.key == "loc_own"

    def test_a_slot_in_a_foreign_location_is_refused(self, source):
        with pytest.raises(NotFoundError):
            resolve_owned_slot(source, "slot_other", TENANT)

    def test_an_absent_slot_is_refused(self, source):
        with pytest.raises(NotFoundError):
            resolve_owned_slot(source, "slot_missing", TENANT)

    def test_a_refused_slot_is_named_as_a_slot_not_as_its_location(self, source):
        """A slot whose location is foreign must not disclose that location's key."""
        with pytest.raises(NotFoundError) as exc:
            resolve_owned_slot(source, "slot_other", TENANT)
        assert "loc_other" not in str(exc.value)


class TestRequireOwnedSite:
    def test_own_site_passes_and_returns_it(self, source):
        assert require_owned_site(source, "site_own", TENANT, "Location", "loc_own").key == "site_own"

    def test_foreign_site_refuses_under_the_callers_entity_name(self, source):
        with pytest.raises(NotFoundError) as exc:
            require_owned_site(source, "site_other", TENANT, "Location", "loc_x")
        assert "Location" in str(exc.value)
        assert "loc_x" in str(exc.value)

    def test_an_empty_site_key_refuses(self, source):
        with pytest.raises(NotFoundError):
            require_owned_site(source, "", TENANT, "Location", "loc_orphan")


class TestFindOwnedLocation:
    """The non-raising reader, for the label and the system-task filter."""

    def test_true_for_the_tenants_own(self, source):
        assert find_owned_location(source, "loc_own", TENANT) is not None

    @pytest.mark.parametrize("key", ["loc_other", "loc_missing", "loc_orphan"])
    def test_false_for_foreign_absent_and_site_less(self, source, key):
        assert find_owned_location(source, key, TENANT) is None


# ── The sweep ────────────────────────────────────────────────────────────────

_APP_ROOT = pathlib.Path(__file__).resolve().parents[4] / "app"

#: Reading the field is legitimate in two places, each for a reason that is not
#: an ownership decision. Every entry names *why*; an entry whose file no longer
#: contains the pattern fails below, so this cannot outlive its subject.
_ALLOWED: dict[str, str] = {
    "domain/models/site.py": "declares the field; the model is where it lives",
    "data_access/arango/plant_instance_repository.py": (
        "three AQL projections that null a label instead of deciding ownership — the C-group "
        "of #1397, tracked and repaired separately because the fix is a different shape"
    ),
}


#: Names a local variable holding a ``Location`` or ``Slot`` plausibly goes by.
#: A name list rather than a type inference: the latter is the right answer and a
#: much larger one, and this list is checked by the two-direction falsification
#: below rather than trusted.
_LOCATION_LIKE = {"location", "loc", "slot"}


#: What each exemption actually excuses, as a predicate. An entry is stale when its
#: predicate stops holding — not when the word ``tenant_key`` stops appearing, which
#: was the first version and could never fail: the allowlisted repository file
#: contains that word a dozen times for ordinary tenant-scoped filters, so repairing
#: the three projections the entry names would have left the guard green.
_EXEMPTION_STILL_APPLIES: dict[str, Callable[[pathlib.Path], bool]] = {
    "domain/models/site.py": lambda p: "tenant_key: str" in p.read_text(),
    "data_access/arango/plant_instance_repository.py": (
        lambda p: "location.tenant_key == @tenant_key" in p.read_text()
    ),
}


def _ownership_reads(path: pathlib.Path) -> list[str]:
    """Reads of ``tenant_key`` on a name that looks like a location or slot.

    An AST walk rather than a grep: a grep matches the pattern inside a comment
    explaining that the pattern is wrong, and this repository has three such
    comments — one sweep already reported a fixed defect as open that way.

    **Two forms, because the first version of this only caught one.** It matched
    `ast.Attribute` and therefore missed `getattr(location, "tenant_key", "")`,
    which is what two live sites actually used — one fail-open
    (`nutrient_plan_service`, where ``"" in ("", tenant_key)`` made the guard
    unfireable) and one over-rejecting (`fertilizer_service`). Both were invisible
    to the sweep while its failure message claimed no module reads the field. The
    class is eleven sites, not the nine the first pass found.
    """
    tree = ast.parse(path.read_text())
    hits = []
    for node in ast.walk(tree):
        # `location.tenant_key`
        if isinstance(node, ast.Attribute) and node.attr == "tenant_key":
            target = node.value
            if isinstance(target, ast.Name) and target.id in _LOCATION_LIKE:
                hits.append(f"{path.name}:{node.lineno} {ast.unparse(node)}")
            continue
        # `getattr(location, "tenant_key", …)` — the form the first pass missed.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in _LOCATION_LIKE
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "tenant_key"
        ):
            hits.append(f"{path.name}:{node.lineno} {ast.unparse(node)}")
    return hits


def test_no_module_decides_ownership_from_location_or_slot_tenant_key():
    """The sweep: a new site reading the empty field fails here rather than in production.

    This is the half that survives. The behaviour tests above prove the anchor is
    right today; this one is what stops a tenth site from being written, which is
    how the first nine appeared — each individually reasonable, none aware of the
    others.
    """
    offenders: list[str] = []
    for path in sorted(_APP_ROOT.rglob("*.py")):
        relative = path.relative_to(_APP_ROOT).as_posix()
        if relative in _ALLOWED:
            continue
        offenders.extend(_ownership_reads(path))

    assert not offenders, (
        "These read Location.tenant_key / Slot.tenant_key, which the write path never fills "
        "(#1397). Use app.domain.services.location_ownership instead:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("relative", sorted(_ALLOWED))
def test_every_allowlisted_file_still_contains_what_it_excuses(relative: str):
    """An obsolete exemption fails, the way check_layer_imports already does.

    Without this the allowlist silently grows into a list of files nobody may
    check — the shape that lets the next drift in.
    """
    path = _APP_ROOT / relative
    assert path.exists(), f"{relative} is allowlisted but does not exist: {_ALLOWED[relative]}"
    assert _EXEMPTION_STILL_APPLIES[relative](path), (
        f"{relative} no longer contains what its entry excuses; drop it ({_ALLOWED[relative]})"
    )

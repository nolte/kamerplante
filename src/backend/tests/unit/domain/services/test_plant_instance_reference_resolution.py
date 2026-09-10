"""Every caller-supplied foreign key on a plant is resolved before it is stored (#1335).

``POST``/``PUT``/``PATCH /t/{slug}/plant-instances`` assign the body's foreign
keys onto the row verbatim. Until this change only ``site_key`` was resolved
(#719, and ``cultivar_key`` one layer down at
:attr:`ArangoPlantInstanceRepository._owned_reference_fields`, #1090); the rest —
``species_key``, ``location_key``, ``slot_key``, ``substrate_batch_key``,
``substrate_key`` — were written unchecked, so a caller could point a plant at a
key that does not exist or belongs to another tenant.

The resolution lives in :class:`PlantInstanceService`, not in the router, because
the router would have to repeat it three times and the fourth caller would not
get it — the #948 shape this repository keeps paying for. There is exactly one
seam per direction: ``create_plant`` and ``update_plant``.

Two properties are asserted here rather than described in a comment:

* **No existence oracle.** Absent and foreign answer the *same*
  :class:`NotFoundError`; only the amendment refusal (422) is distinguishable,
  and it is reachable only for a substrate the caller can already see.
* **Tenant before amendment.** A *foreign* amendment answers 404, never "that is
  an amendment" — the same assertion ``test_the_scope_check_runs_before_the_amendment_check``
  makes for the MCP setter (#1332), on the REST seam.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
import structlog.testing

from app.common.enums import SiteType
from app.common.exceptions import NotFoundError, ValidationError
from app.domain.models.plant_instance import PlantInstance
from app.domain.models.site import Location, Site, Slot
from app.domain.models.species import Species
from app.domain.models.substrate import Substrate, SubstrateBatch
from app.domain.services.plant_instance_service import PlantInstanceService
from app.domain.services.species_service import SpeciesService
from app.domain.services.substrate_service import SubstrateService

TENANT = "tenant-anna"
FOREIGN = "tenant-bob"


# ── Doubles ─────────────────────────────────────────────────────────────
#
# Deliberately *stores* whole domain models and serves them by key, rather than
# returning whatever it is asked for. A MagicMock repository would answer every
# key with a truthy object carrying whatever attribute is read, so the guards
# below would pass on a service that checks nothing — the "double invents an
# impossible record" failure (#947, #1155). Name an input these fakes accept that
# the real repository would not: there is none, because the fakes only ever hand
# back models that were put in.


class FakeSiteRepo:
    def __init__(
        self,
        sites: dict[str, Site] | None = None,
        locations: dict[str, Location] | None = None,
        slots: dict[str, Slot] | None = None,
    ) -> None:
        self.sites = sites or {}
        self.locations = locations or {}
        self.slots = slots or {}

    def get_site_by_key(self, key: str) -> Site | None:
        return self.sites.get(key)

    def get_location_by_key(self, key: str) -> Location | None:
        return self.locations.get(key)

    def get_slot_by_key(self, key: str) -> Slot | None:
        return self.slots.get(key)

    def update_slot(self, key, slot):
        self.slots[key] = slot
        return slot


class FakeSubstrateRepo:
    def __init__(
        self,
        substrates: dict[str, Substrate] | None = None,
        batches: dict[str, SubstrateBatch] | None = None,
    ) -> None:
        self.substrates = substrates or {}
        self.batches = batches or {}

    def get_substrate_or_raise(self, key: str) -> Substrate:
        substrate = self.substrates.get(key)
        if substrate is None:
            raise NotFoundError("Substrate", key)
        return substrate

    def get_batch_or_raise(self, key: str) -> SubstrateBatch:
        batch = self.batches.get(key)
        if batch is None:
            raise NotFoundError("SubstrateBatch", key)
        return batch


class FakeSpeciesRepo:
    def __init__(self, species: dict[str, Species] | None = None, grants: dict[str, set[str]] | None = None) -> None:
        self.species = species or {}
        self.grants = grants or {}

    def get_or_raise(self, key: str) -> Species:
        found = self.species.get(key)
        if found is None:
            raise NotFoundError("Species", key)
        return found

    def is_granted_to(self, key: str, tenant_key: str) -> bool:
        return tenant_key in self.grants.get(key, set())


# ── Builders ────────────────────────────────────────────────────────────


def _site(key: str, tenant: str = TENANT) -> Site:
    return Site(key=key, tenant_key=tenant, name=key, type=SiteType.INDOOR, climate_zone="")


def _location(key: str, site_key: str) -> Location:
    # NOTE the empty ``tenant_key``: that is what a stored Location really looks
    # like. ``LocationCreate`` does not carry the field and ``create_location``
    # builds ``Location(**body.model_dump())``, so no write path ever fills it —
    # which is exactly why the guard has to anchor on the parent site (#706, #927).
    return Location(key=key, name=key, site_key=site_key, area_m2=1.0)


def _slot(key: str, location_key: str) -> Slot:
    return Slot(key=key, slot_id="TENT01_A1", location_key=location_key)


def _substrate(key: str, *, tenant: str = TENANT, is_amendment: bool = False) -> Substrate:
    return Substrate(_key=key, name_de=key, tenant_key=tenant, is_amendment=is_amendment)


def _batch(key: str, *, tenant: str = TENANT) -> SubstrateBatch:
    return SubstrateBatch(_key=key, tenant_key=tenant, batch_id=key, volume_liters=10.0, mixed_on=date(2026, 1, 1))


def _species(key: str, *, tenant: str = TENANT) -> Species:
    return Species(_key=key, tenant_key=tenant, scientific_name=f"Testus {key}")


def _plant(*, tenant: str = TENANT, key: str | None = None, **fields) -> PlantInstance:
    return PlantInstance(
        _key=key,
        tenant_key=tenant,
        instance_id="i1",
        species_key=fields.pop("species_key", "sp-own"),
        planted_on=date(2026, 1, 1),
        **fields,
    )


def _service(
    *,
    sites: dict[str, Site] | None = None,
    locations: dict[str, Location] | None = None,
    slots: dict[str, Slot] | None = None,
    substrates: dict[str, Substrate] | None = None,
    batches: dict[str, SubstrateBatch] | None = None,
    species: dict[str, Species] | None = None,
    grants: dict[str, set[str]] | None = None,
) -> tuple[PlantInstanceService, MagicMock]:
    """A service whose writes are observable and whose reads are real models."""
    plant_repo = MagicMock()
    plant_repo.create.side_effect = lambda p: p
    plant_repo.update.side_effect = lambda key, p: p
    site_repo = FakeSiteRepo(sites or {}, locations or {}, slots or {})
    substrate_service = SubstrateService(FakeSubstrateRepo(substrates or {}, batches or {}))
    species_service = SpeciesService(
        FakeSpeciesRepo(species if species is not None else {"sp-own": _species("sp-own")}, grants),
        MagicMock(),
        MagicMock(),
    )
    service = PlantInstanceService(
        plant_repo,
        site_repo,
        MagicMock(),
        MagicMock(),
        substrate_service=substrate_service,
        species_service=species_service,
    )
    return service, plant_repo


# ── substrate_key — the #1175 half, and the two halves under it ──────────


def test_a_non_existent_substrate_is_refused_and_nothing_is_written() -> None:
    """AC-1. Red against the pre-#1335 code, which stored the dangling key and answered 201."""
    service, plant_repo = _service()

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(substrate_key="sub-ghost"))

    plant_repo.create.assert_not_called()


def test_a_foreign_substrate_is_refused_indistinguishably_from_an_absent_one() -> None:
    """AC-2, at the service seam: the two refusals must carry the same message shape.

    Asserted by comparing the two raised errors with the caller's own key removed,
    not by reading the branch that raises them. What is left after that removal is
    everything the caller can observe.
    """
    service, plant_repo = _service(substrates={"sub-foreign": _substrate("sub-foreign", tenant=FOREIGN)})

    with pytest.raises(NotFoundError) as foreign:
        service.create_plant(_plant(substrate_key="sub-foreign"))
    with pytest.raises(NotFoundError) as absent:
        service.create_plant(_plant(substrate_key="sub-ghost"))

    def shape(exc: NotFoundError, key: str) -> tuple:
        return (
            exc.status_code,
            exc.error_code,
            exc.message.replace(key, "<key>"),
            [{k: v.replace(key, "<key>") for k, v in d.items()} for d in exc.details],
        )

    assert shape(foreign.value, "sub-foreign") == shape(absent.value, "sub-ghost")
    plant_repo.create.assert_not_called()


def test_an_own_amendment_is_refused_as_a_growing_medium() -> None:
    """AC-3, first half — 422, because the record *is* visible to the caller."""
    service, plant_repo = _service(substrates={"sub-amend": _substrate("sub-amend", is_amendment=True)})

    with pytest.raises(ValidationError) as exc:
        service.create_plant(_plant(substrate_key="sub-amend"))

    assert exc.value.status_code == 422
    plant_repo.create.assert_not_called()


def test_a_foreign_amendment_answers_404_not_422() -> None:
    """AC-3, second half — the tenant check demonstrably runs first.

    The same assertion ``test_the_scope_check_runs_before_the_amendment_check``
    makes for the MCP setter, on the REST seam. If the amendment check ran first,
    the 422 would tell the caller that a substrate they cannot see exists and what
    kind of thing it is — an existence oracle walkable key by key.
    """
    service, _ = _service(substrates={"sub-foreign": _substrate("sub-foreign", tenant=FOREIGN, is_amendment=True)})

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(substrate_key="sub-foreign"))


def test_a_global_growing_medium_stays_bindable() -> None:
    """Control. Without it, a guard that refused every substrate would pass above.

    The catalogue is a hybrid: the seeded media carry ``tenant_key == ""`` and
    must stay referenceable by every tenant, exactly as the fertilizer catalogue
    does. A strict ``== tenant_key`` here would blank the whole seeded catalogue.
    """
    service, plant_repo = _service(substrates={"sub-global": _substrate("sub-global", tenant="")})

    created = service.create_plant(_plant(substrate_key="sub-global"))

    assert created.substrate_key == "sub-global"
    plant_repo.create.assert_called_once()


# ── substrate_batch_key ─────────────────────────────────────────────────


def test_a_foreign_batch_is_refused() -> None:
    service, plant_repo = _service(batches={"batch-foreign": _batch("batch-foreign", tenant=FOREIGN)})

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(substrate_batch_key="batch-foreign"))

    plant_repo.create.assert_not_called()


def test_an_own_batch_is_accepted() -> None:
    service, plant_repo = _service(batches={"batch-own": _batch("batch-own")})

    created = service.create_plant(_plant(substrate_batch_key="batch-own"))

    assert created.substrate_batch_key == "batch-own"
    plant_repo.create.assert_called_once()


# ── location_key / slot_key — anchored on the parent site, not on the row ─


def test_an_own_location_is_accepted_although_its_own_tenant_key_is_empty() -> None:
    """The load-bearing control for the #706 trap.

    Every stored ``Location`` carries ``tenant_key == ""``. A guard written as
    ``location.tenant_key == tenant_key`` would therefore refuse **every**
    location — an over-rejecting guard that looks like a security fix and loses
    the feature. ``SiteService.get_location(key, tenant_key=…)`` is written that
    way, which is why this path does not call it.
    """
    service, plant_repo = _service(
        sites={"site-own": _site("site-own")},
        locations={"loc-own": _location("loc-own", "site-own")},
    )

    created = service.create_plant(_plant(location_key="loc-own"))

    assert created.location_key == "loc-own"
    plant_repo.create.assert_called_once()


def test_a_location_under_a_foreign_site_is_refused() -> None:
    service, plant_repo = _service(
        sites={"site-foreign": _site("site-foreign", tenant=FOREIGN)},
        locations={"loc-foreign": _location("loc-foreign", "site-foreign")},
    )

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(location_key="loc-foreign"))

    plant_repo.create.assert_not_called()


def test_an_unknown_location_is_refused() -> None:
    service, plant_repo = _service()

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(location_key="loc-ghost"))

    plant_repo.create.assert_not_called()


def test_an_own_slot_is_accepted() -> None:
    service, plant_repo = _service(
        sites={"site-own": _site("site-own")},
        locations={"loc-own": _location("loc-own", "site-own")},
        slots={"slot-own": _slot("slot-own", "loc-own")},
    )

    created = service.create_plant(_plant(slot_key="slot-own"), skip_validation=True)

    assert created.slot_key == "slot-own"
    plant_repo.create.assert_called_once()


def test_a_slot_under_a_foreign_site_is_refused() -> None:
    """Two hops: slot → location → site. The slot's own ``tenant_key`` is as empty
    as the location's, so neither is an anchor."""
    service, plant_repo = _service(
        sites={"site-foreign": _site("site-foreign", tenant=FOREIGN)},
        locations={"loc-foreign": _location("loc-foreign", "site-foreign")},
        slots={"slot-foreign": _slot("slot-foreign", "loc-foreign")},
    )

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(slot_key="slot-foreign"), skip_validation=True)

    plant_repo.create.assert_not_called()


def test_the_reference_guard_runs_before_the_rotation_and_companion_engines() -> None:
    """A foreign slot must not reach the engines that read its neighbourhood.

    Those reads are tenant-scoped, so they would return nothing and *pass* — the
    request would then be refused only later, or not at all. Ordering is asserted
    on the collaborators, not on a comment.
    """
    service, plant_repo = _service(slots={"slot-ghostloc": _slot("slot-ghostloc", "loc-ghost")})
    rotation, companion = service._rotation, service._companion

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(slot_key="slot-ghostloc"))

    rotation.validate_or_raise.assert_not_called()
    companion.check_or_raise.assert_not_called()
    plant_repo.create.assert_not_called()


# ── species_key ─────────────────────────────────────────────────────────


def test_a_foreign_species_is_refused() -> None:
    service, plant_repo = _service(species={"sp-foreign": _species("sp-foreign", tenant=FOREIGN)})

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(species_key="sp-foreign"))

    plant_repo.create.assert_not_called()


def test_a_global_species_stays_bindable() -> None:
    """The seeded catalogue is global (``tenant_key == ""``) and must stay usable."""
    service, plant_repo = _service(species={"sp-global": _species("sp-global", tenant="")})

    created = service.create_plant(_plant(species_key="sp-global"))

    assert created.species_key == "sp-global"
    plant_repo.create.assert_called_once()


def test_a_granted_species_stays_bindable() -> None:
    """#1092 — an explicit grant is the third way in, and the guard must honour it.

    Without this arm the check would look correct and would silently refuse every
    species another tenant shared with the caller.
    """
    service, plant_repo = _service(
        species={"sp-shared": _species("sp-shared", tenant=FOREIGN)},
        grants={"sp-shared": {TENANT}},
    )

    created = service.create_plant(_plant(species_key="sp-shared"))

    assert created.species_key == "sp-shared"
    plant_repo.create.assert_called_once()


def test_an_unknown_species_is_refused() -> None:
    service, plant_repo = _service(species={})

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(species_key="sp-ghost"))

    plant_repo.create.assert_not_called()


# ── update: only what the update re-points ──────────────────────────────


def test_updating_re_points_a_substrate_and_the_new_one_is_resolved() -> None:
    service, plant_repo = _service(substrates={"sub-foreign": _substrate("sub-foreign", tenant=FOREIGN)})
    plant_repo.get_or_raise.return_value = _plant(key="p1", substrate_key=None)

    with pytest.raises(NotFoundError):
        service.update_plant("p1", _plant(key="p1", substrate_key="sub-foreign"))

    plant_repo.update.assert_not_called()


def test_an_unchanged_reference_does_not_make_the_row_uneditable() -> None:
    """Changed-only, deliberately — the #1090 C-9 semantics, for the same reasons.

    A substrate flagged as an amendment *after* a plant was potted in it, or a
    referenced document deleted since, is a data-integrity fact and not a
    disclosure route. Re-verifying an untouched reference would make the plant
    uneditable through every internal path that rewrites the full model (phase
    transitions, removal, planting-run materialisation) — a guard that refuses
    work nobody asked it to inspect.
    """
    service, plant_repo = _service(substrates={"sub-amend": _substrate("sub-amend", is_amendment=True)})
    stored = _plant(key="p1", substrate_key="sub-amend")
    plant_repo.get_or_raise.return_value = stored

    updated = service.update_plant("p1", _plant(key="p1", substrate_key="sub-amend", plant_name="renamed"))

    assert updated.plant_name == "renamed"
    plant_repo.update.assert_called_once()


def test_clearing_a_reference_is_never_refused() -> None:
    """``PUT`` clears nullable fields by omission and ``PATCH`` by an explicit
    ``null``; neither dereferences anything, so neither can be refused."""
    service, plant_repo = _service(substrates={"sub-amend": _substrate("sub-amend", is_amendment=True)})
    plant_repo.get_or_raise.return_value = _plant(key="p1", substrate_key="sub-amend")

    updated = service.update_plant("p1", _plant(key="p1", substrate_key=None))

    assert updated.substrate_key is None
    plant_repo.update.assert_called_once()


# ── the escapes the other guards on this service already take ───────────


def test_a_tenantless_plant_skips_resolution() -> None:
    """Mirrors the ``if tenant_key`` gate on ``get_plant`` / ``_verify_site_ownership``.

    Seeds, migrations and light-mode callers create plants without a tenant; there
    is nothing to anchor against, and refusing them would cost those callers their
    records over a check that cannot be performed.
    """
    service, plant_repo = _service()

    created = service.create_plant(_plant(tenant="", substrate_key="sub-ghost", species_key="sp-ghost"))

    assert created.substrate_key == "sub-ghost"
    plant_repo.create.assert_called_once()


def test_resolution_is_skipped_when_the_collaborators_are_unwired() -> None:
    """Pure-domain construction (no substrate/species service) must stay usable.

    The wiring itself is pinned by :func:`test_the_dependency_wiring_supplies_both_resolvers`
    below, so this escape cannot quietly become the production behaviour — which is
    how an opt-in guard normally goes inert.
    """
    plant_repo = MagicMock()
    plant_repo.create.side_effect = lambda p: p
    service = PlantInstanceService(plant_repo, FakeSiteRepo(), MagicMock(), MagicMock())

    created = service.create_plant(_plant(substrate_key="sub-ghost"))

    assert created.substrate_key == "sub-ghost"


# NOTE — the absence check that stood here read
# ``inspect.getsource(get_plant_instance_service)`` and asserted the two kwargs
# appeared as substrings. Measured during the #1349 review: commenting the two
# lines out leaves the substrings in the source, and the check **passed** on
# wiring that was not wired. It is replaced by
# ``test_the_dependency_wiring_produces_a_service_with_every_catalogue_resolver``
# below, which builds the real factory and inspects the resulting object.


# ── Pre-merge review, finding 1: "" is a reference, not an absence ───────
#
# ``if not value: continue`` read an empty string as "the caller supplied no
# reference". It is not: ``species_key: str`` is *required*, so ``""`` is a value
# the caller chose, and the row it produces points at a species that does not
# exist. Measured against the pre-review branch: ``POST`` with
# ``"species_key": ""`` answered **201**.


def test_an_empty_species_key_is_resolved_and_refused_rather_than_skipped() -> None:
    service, plant_repo = _service()

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(species_key=""))

    plant_repo.create.assert_not_called()


def test_an_empty_substrate_key_is_resolved_and_refused_rather_than_skipped() -> None:
    service, plant_repo = _service()

    with pytest.raises(NotFoundError):
        service.create_plant(_plant(substrate_key=""))

    plant_repo.create.assert_not_called()


def test_an_update_cannot_strip_a_species_to_the_empty_string() -> None:
    """The ``PUT`` half: ``""`` differs from the stored value, so it is a change —
    and a change to a key that resolves to nothing."""
    service, plant_repo = _service(species={"sp-own": _species("sp-own")})
    plant_repo.get_or_raise.return_value = _plant(key="p1", species_key="sp-own")

    with pytest.raises(NotFoundError):
        service.update_plant("p1", _plant(key="p1", species_key=""))

    plant_repo.update.assert_not_called()


def test_clearing_an_optional_reference_to_none_is_still_never_refused() -> None:
    """The control that keeps the rule above from becoming "refuse everything falsy".

    ``None`` means *no reference*; ``""`` means *this reference*, spelled badly.
    Only the first may skip resolution — a ``PUT`` clears nullable fields by
    omission and must not be refused for it.
    """
    service, plant_repo = _service(substrates={"sub-own": _substrate("sub-own")})
    plant_repo.get_or_raise.return_value = _plant(key="p1", substrate_key="sub-own")

    updated = service.update_plant("p1", _plant(key="p1", substrate_key=None))

    assert updated.substrate_key is None
    plant_repo.update.assert_called_once()


# ── Pre-merge review, finding 2: the placement chain ────────────────────
#
# Each placement key was anchored on its own parent's tenant *in isolation*, so
# three keys that each belong to the caller could still describe an impossible
# plant. Measured against the pre-review branch: ``site_key=site-a``,
# ``location_key`` under ``site-b`` and a slot in that same foreign-to-the-site
# location answered **201**.


def _two_site_service():
    return _service(
        sites={"site-a": _site("site-a"), "site-b": _site("site-b")},
        locations={"loc-a": _location("loc-a", "site-a"), "loc-b": _location("loc-b", "site-b")},
        slots={"slot-a": _slot("slot-a", "loc-a"), "slot-b": _slot("slot-b", "loc-b")},
    )


def test_a_location_under_a_different_site_than_the_plants_own_is_refused() -> None:
    """Both objects are the caller's own — this is a shape error, not a disclosure,
    so it is a 422 and names what is wrong (#970: a well-formed request the domain
    rejects)."""
    service, plant_repo = _two_site_service()

    with pytest.raises(ValidationError) as exc:
        service.create_plant(_plant(site_key="site-a", location_key="loc-b"))

    assert exc.value.status_code == 422
    plant_repo.create.assert_not_called()


def test_a_slot_in_a_different_location_than_the_plants_own_is_refused() -> None:
    service, plant_repo = _two_site_service()

    with pytest.raises(ValidationError) as exc:
        service.create_plant(_plant(site_key="site-a", location_key="loc-a", slot_key="slot-b"), skip_validation=True)

    assert exc.value.status_code == 422
    plant_repo.create.assert_not_called()


def test_the_full_measured_incoherent_placement_is_refused() -> None:
    """The exact triple the review measured a 201 for."""
    service, plant_repo = _two_site_service()

    with pytest.raises(ValidationError):
        service.create_plant(_plant(site_key="site-a", location_key="loc-b", slot_key="slot-b"), skip_validation=True)

    plant_repo.create.assert_not_called()


def test_a_coherent_placement_chain_is_accepted() -> None:
    """Control. Without it, a chain check that refused every placement would pass
    all three assertions above."""
    service, plant_repo = _two_site_service()

    created = service.create_plant(_plant(site_key="site-a", location_key="loc-a", slot_key="slot-a"))

    assert (created.site_key, created.location_key, created.slot_key) == ("site-a", "loc-a", "slot-a")
    plant_repo.create.assert_called_once()


def test_a_slot_without_a_location_derives_the_location_from_the_slot() -> None:
    """Decision: derive, do not refuse.

    A slot *is* in exactly one location, so the pair cannot disagree when only one
    of them was supplied — the row is completed rather than rejected, and the
    completion is the slot's own parent, never the caller's assertion about it.
    Refusing instead would break ``PATCH {"slot_key": …}`` on a plant that has no
    location yet, which is the ordinary way a plant is first placed.
    """
    service, plant_repo = _two_site_service()

    created = service.create_plant(_plant(slot_key="slot-b"), skip_validation=True)

    assert created.location_key == "loc-b"
    plant_repo.create.assert_called_once()


def test_changing_only_the_site_re_checks_the_location_that_did_not_change() -> None:
    """The update half, and the reason the chain is not evaluated field by field.

    ``location_key`` is unchanged, so a per-field changed-only rule skips it — and
    the plant ends up on ``site-b`` while sitting in a location of ``site-a``. The
    chain is therefore re-run whenever *any* of the three placement keys moved.
    """
    service, plant_repo = _two_site_service()
    plant_repo.get_or_raise.return_value = _plant(key="p1", site_key="site-a", location_key="loc-a")

    with pytest.raises(ValidationError):
        service.update_plant("p1", _plant(key="p1", site_key="site-b", location_key="loc-a"))

    plant_repo.update.assert_not_called()


def test_an_update_that_touches_no_placement_key_costs_no_placement_read() -> None:
    """Control for the rule above: a rename must still not dial the site repo."""
    service, plant_repo = _two_site_service()
    stored = _plant(key="p1", site_key="site-a", location_key="loc-a")
    plant_repo.get_or_raise.return_value = stored
    reads: list[str] = []
    service._site_repo.get_location_by_key = lambda key: (  # type: ignore[method-assign]
        reads.append(key) or _location("loc-a", "site-a")
    )

    service.update_plant("p1", _plant(key="p1", site_key="site-a", location_key="loc-a", plant_name="renamed"))

    assert reads == []
    plant_repo.update.assert_called_once()


# ── Pre-merge review, finding 5: the dispatch cannot drift ──────────────


def test_every_dispatched_reference_field_exists_on_the_plant_model() -> None:
    """A renamed or removed field must break the test, not silently stop being checked.

    The previous dispatch read ``getattr(plant, field, None)`` and fell through an
    ``if/elif`` chain with no ``else``, so a field renamed on the model — or a name
    that never matched one — resolved to ``None``, was skipped, and left the guard
    inert while every test above stayed green.
    """
    service, _ = _service()
    declared = set(PlantInstanceService._CATALOGUE_REFERENCE_FIELDS) | set(PlantInstanceService._PLACEMENT_FIELDS)

    assert declared <= set(PlantInstance.model_fields)
    assert declared, "the dispatch must not be empty"
    # A resolver that no declared field dispatches to would never run; a declared
    # field with no resolver is reported at the skip point, never silently dropped.
    assert set(service._reference_resolvers) == set(PlantInstanceService._CATALOGUE_REFERENCE_FIELDS)
    assert all(callable(resolver) for resolver in service._reference_resolvers.values())


def test_the_dependency_wiring_produces_a_service_with_every_catalogue_resolver() -> None:
    """Absence check, on the constructed object rather than on the source text.

    The previous version substring-matched ``inspect.getsource`` and therefore
    stayed green when the two kwargs were *commented out* — a wiring check that
    passes on unwired wiring. Building the real factory against a stub ``get_db``
    asserts the outcome instead: a resolver is inserted only when its collaborator
    was actually supplied.
    """
    from app.common import dependencies

    original_get_db = dependencies.get_db
    dependencies.get_db = lambda: MagicMock()  # type: ignore[assignment]
    try:
        service = dependencies.get_plant_instance_service()
    finally:
        dependencies.get_db = original_get_db  # type: ignore[assignment]

    assert set(service._reference_resolvers) == {"species_key", "substrate_batch_key", "substrate_key"}


def test_a_reference_that_goes_unchecked_because_of_an_unwired_collaborator_is_logged() -> None:
    """The escape stays available for pure-domain construction, but it is announced.

    Same shape as ``owned_reference_check_skipped_tenantless_row``: a check that
    does not run must leave a trace, or "unwired" and "wired" are indistinguishable
    from the outside. Logged at the **skip**, not at construction — a service that
    is never asked to resolve anything has skipped nothing, and a warning per
    constructed object would drown the one that matters.
    """
    plant_repo = MagicMock()
    plant_repo.create.side_effect = lambda p: p
    service = PlantInstanceService(plant_repo, FakeSiteRepo(), MagicMock(), MagicMock())

    with structlog.testing.capture_logs() as logs:
        service.create_plant(_plant(substrate_key="sub-ghost", species_key="sp-ghost"))

    warnings = [entry for entry in logs if entry.get("event") == "reference_resolver_unwired"]
    assert len(warnings) == 1
    assert warnings[0]["log_level"] == "warning"
    assert sorted(warnings[0]["fields"]) == ["species_key", "substrate_key"]
    assert warnings[0]["tenant_key"] == TENANT


def test_a_wired_service_logs_nothing_when_every_reference_resolves() -> None:
    """Control for the warning above: it must fire on a gap, not on every write."""
    service, _ = _service(substrates={"sub-own": _substrate("sub-own")})

    with structlog.testing.capture_logs() as logs:
        service.create_plant(_plant(substrate_key="sub-own"))

    assert [entry for entry in logs if entry.get("event") == "reference_resolver_unwired"] == []

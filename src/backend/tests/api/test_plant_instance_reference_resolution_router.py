"""`POST`/`PUT`/`PATCH /t/{slug}/plant-instances` refuse an unresolvable reference (#1335).

The sibling unit suite
(``tests/unit/domain/services/test_plant_instance_reference_resolution.py``) pins
the predicate. This one pins the **contract the caller sees**, over HTTP, on all
three write routes — because the acceptance criterion is about status codes and
response bodies, and a service-level assertion cannot show that a
:class:`NotFoundError` really arrives as a 404 whose body is indistinguishable
from the other 404.

Measured against the pre-#1335 code, the three routes answered:

    POST  -> 201 | stored substrate_key = 'sub_does_not_exist'
    PUT   -> 200 | stored substrate_key = 'sub_does_not_exist'
    PATCH -> 200 | stored substrate_key = 'sub_does_not_exist'

The service under test here is the **real** :class:`PlantInstanceService` with
fake repositories, not the response-shaped double the other plant-instance router
tests use. A double would have to be told what to refuse, which is the assertion
itself. No datastore is touched (#978).
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.plant_instances.tenant_router import router as plants_router
from app.common import auth as auth_mod
from app.common.dependencies import get_plant_instance_service
from app.common.enums import SiteType, TenantRole
from app.common.error_handlers import app_error_handler
from app.common.exceptions import KamerplanterError, NotFoundError
from app.domain.models.plant_instance import PlantInstance
from app.domain.models.site import Location, Site, Slot
from app.domain.models.species import Species
from app.domain.models.substrate import Substrate
from app.domain.models.tenant_context import TenantContext
from app.domain.services.plant_instance_service import PlantInstanceService
from app.domain.services.species_service import SpeciesService
from app.domain.services.substrate_service import SubstrateService

TENANT = "t1"
FOREIGN = "t2"

#: The caller's own tenant holds one global medium; everything else in the
#: catalogue belongs to someone else or does not exist.
_CATALOGUE: dict[str, Substrate] = {
    "sub_own": Substrate(_key="sub_own", name_de="Eigenes Substrat", tenant_key=TENANT),
    "sub_amendment": Substrate(_key="sub_amendment", name_de="BioBizz Pre·Mix", tenant_key=TENANT, is_amendment=True),
    "sub_foreign": Substrate(_key="sub_foreign", name_de="Fremdes Substrat", tenant_key=FOREIGN),
    "sub_foreign_amendment": Substrate(
        _key="sub_foreign_amendment", name_de="Fremder Bodenverbesserer", tenant_key=FOREIGN, is_amendment=True
    ),
}

_SPECIES: dict[str, Species] = {
    "sp_tomato": Species(_key="sp_tomato", tenant_key="", scientific_name="Solanum lycopersicum")
}

_STORED = PlantInstance(
    key="plant_1",
    instance_id="TOM-001",
    species_key="sp_tomato",
    tenant_key=TENANT,
    planted_on=date(2026, 4, 1),
)


class _SubstrateRepo:
    def get_substrate_or_raise(self, key: str) -> Substrate:
        found = _CATALOGUE.get(key)
        if found is None:
            raise NotFoundError("Substrate", key)
        return found

    def get_batch_or_raise(self, key: str):  # pragma: no cover - no batch case here
        raise NotFoundError("SubstrateBatch", key)


class _SpeciesRepo:
    def get_or_raise(self, key: str) -> Species:
        found = _SPECIES.get(key)
        if found is None:
            raise NotFoundError("Species", key)
        return found

    def is_granted_to(self, key: str, tenant_key: str) -> bool:
        return False


#: Two sites of the *same* tenant, one location and one slot under each. Both
#: halves of every pair are legitimately the caller's own, which is what makes
#: the incoherent combination a shape error rather than an ownership question.
_SITES: dict[str, Site] = {
    "site_own": Site(key="site_own", tenant_key=TENANT, name="own", type=SiteType.INDOOR, climate_zone=""),
    "site_other": Site(key="site_other", tenant_key=TENANT, name="other", type=SiteType.INDOOR, climate_zone=""),
}
#: NOTE the empty ``tenant_key`` — that is what a stored Location really looks
#: like (#706), which is why the guard anchors on the parent site.
_LOCATIONS: dict[str, Location] = {
    "loc_own": Location(key="loc_own", name="loc_own", site_key="site_own", area_m2=1.0),
    "loc_other": Location(key="loc_other", name="loc_other", site_key="site_other", area_m2=1.0),
}
_SLOTS: dict[str, Slot] = {
    "slot_own": Slot(key="slot_own", slot_id="TENT01_A1", location_key="loc_own"),
    "slot_other": Slot(key="slot_other", slot_id="TENT02_A1", location_key="loc_other"),
}


class _SiteRepo:
    def get_site_by_key(self, key: str) -> Site | None:
        return _SITES.get(key)

    def get_location_by_key(self, key: str) -> Location | None:
        return _LOCATIONS.get(key)

    def get_slot_by_key(self, key: str) -> Slot | None:
        return _SLOTS.get(key)

    def update_slot(self, key, slot):  # pragma: no cover - no slot case here
        return slot


@pytest.fixture
def plant_repo() -> MagicMock:
    repo = MagicMock()
    repo.create.side_effect = lambda p: p.model_copy(update={"key": "plant_new"})
    repo.update.side_effect = lambda key, p: p
    repo.get_or_raise.side_effect = lambda key: _STORED.model_copy(deep=True)
    return repo


@pytest.fixture
def client(plant_repo: MagicMock) -> TestClient:
    service = PlantInstanceService(
        plant_repo,
        _SiteRepo(),
        MagicMock(),
        MagicMock(),
        substrate_service=SubstrateService(_SubstrateRepo()),
        species_service=SpeciesService(_SpeciesRepo(), MagicMock(), MagicMock()),
    )
    app = FastAPI()
    app.add_exception_handler(KamerplanterError, app_error_handler)  # type: ignore[arg-type]
    app.include_router(plants_router, prefix="/api/v1/t/{tenant_slug}")
    app.dependency_overrides[auth_mod.get_current_user] = lambda: SimpleNamespace(key="u1", account_type="user")
    app.dependency_overrides[get_plant_instance_service] = lambda: service
    app.dependency_overrides[auth_mod.get_current_tenant] = lambda: TenantContext(
        tenant_key=TENANT, tenant_slug=TENANT, user_key="u1", role=TenantRole.LEAD, admin_scopes=[]
    )
    return TestClient(app)


_COLLECTION = f"/api/v1/t/{TENANT}/plant-instances"
_ITEM = f"{_COLLECTION}/plant_1"


def _body(**overrides) -> dict:
    return {"instance_id": "TOM-002", "species_key": "sp_tomato", "planted_on": "2026-04-01", **overrides}


def _mask(value: object, key: str) -> object:
    """Replace every occurrence of ``key`` with a placeholder, at any depth."""
    if isinstance(value, str):
        return value.replace(key, "<key>")
    if isinstance(value, dict):
        return {k: _mask(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v, key) for v in value]
    return value


def _observable(payload: dict, key: str) -> dict:
    """Everything in an error body the caller cannot attribute to its own input.

    ``error_id`` and ``timestamp`` are per-response by construction, and the
    supplied key is echoed back — the caller sent it, so it carries no information
    it did not already have. What remains is the entire observable difference
    between two refusals; if that is equal, the two are indistinguishable.
    """
    stripped = {k: v for k, v in payload.items() if k not in ("error_id", "timestamp")}
    return _mask(stripped, key)  # type: ignore[return-value]


# ── AC-1: a non-existent reference is refused, on every write route ──────


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("post", _COLLECTION, _body(substrate_key="sub_ghost")),
        ("put", _ITEM, _body(substrate_key="sub_ghost")),
        ("patch", _ITEM, {"substrate_key": "sub_ghost"}),
    ],
)
def test_a_non_existent_substrate_is_refused_with_404(
    client: TestClient, plant_repo: MagicMock, method: str, url: str, payload: dict
) -> None:
    """Red against the pre-#1335 code, which answered 201/200/200 and stored the key."""
    response = getattr(client, method)(url, json=payload)

    assert response.status_code == 404, response.text
    plant_repo.create.assert_not_called()
    plant_repo.update.assert_not_called()


# ── AC-2: foreign and absent are indistinguishable ──────────────────────


def test_a_foreign_substrate_answers_exactly_what_an_absent_one_answers(client: TestClient) -> None:
    """Asserted by comparing the two responses, not by reading the handler.

    If the foreign one answered anything else — a 403, a different message, even a
    different ``error_code`` — the route would be a cross-tenant existence oracle:
    a caller could enumerate substrate keys and learn which of them other tenants
    hold, without ever reading one.
    """
    foreign = client.post(_COLLECTION, json=_body(substrate_key="sub_foreign"))
    absent = client.post(_COLLECTION, json=_body(substrate_key="sub_ghost"))

    assert foreign.status_code == absent.status_code == 404
    assert _observable(foreign.json(), "sub_foreign") == _observable(absent.json(), "sub_ghost")


def test_a_foreign_species_answers_exactly_what_an_absent_one_answers(client: TestClient) -> None:
    """The same property on a second field, so it reads as a rule and not a one-off."""
    _SPECIES["sp_foreign"] = Species(_key="sp_foreign", tenant_key=FOREIGN, scientific_name="Secretus hortensis")
    try:
        foreign = client.post(_COLLECTION, json=_body(species_key="sp_foreign"))
        absent = client.post(_COLLECTION, json=_body(species_key="sp_ghost"))
    finally:
        _SPECIES.pop("sp_foreign")

    assert foreign.status_code == absent.status_code == 404
    assert _observable(foreign.json(), "sp_foreign") == _observable(absent.json(), "sp_ghost")


# ── AC-3: the amendment gate, and the order it runs in ──────────────────


def test_an_own_amendment_is_refused_with_422(client: TestClient, plant_repo: MagicMock) -> None:
    """422, not 404: the caller can already see this record in its own catalogue,
    so naming the reason discloses nothing — and the caller needs the reason to
    know which of several selections was rejected (#1175)."""
    response = client.post(_COLLECTION, json=_body(substrate_key="sub_amendment"))

    assert response.status_code == 422, response.text
    assert "amendment" in response.json()["message"]
    plant_repo.create.assert_not_called()


def test_a_foreign_amendment_answers_404_and_not_422(client: TestClient) -> None:
    """The tenant check demonstrably runs first — the REST pendant of #1332's
    ``test_the_scope_check_runs_before_the_amendment_check``.

    A 422 here would confirm that ``sub_foreign_amendment`` exists *and* what kind
    of product it is, for a tenant that cannot read it. The refusal is instead
    byte-identical to the one an invented key gets.
    """
    foreign_amendment = client.post(_COLLECTION, json=_body(substrate_key="sub_foreign_amendment"))
    absent = client.post(_COLLECTION, json=_body(substrate_key="sub_ghost"))

    assert foreign_amendment.status_code == 404, foreign_amendment.text
    assert _observable(foreign_amendment.json(), "sub_foreign_amendment") == _observable(absent.json(), "sub_ghost")


# ── The happy path, without which every assertion above also passes on a
#    route that refused everything ───────────────────────────────────────


def test_an_own_medium_is_still_accepted(client: TestClient, plant_repo: MagicMock) -> None:
    response = client.post(_COLLECTION, json=_body(substrate_key="sub_own"))

    assert response.status_code == 201, response.text
    assert response.json()["substrate_key"] == "sub_own"
    plant_repo.create.assert_called_once()


def test_patching_an_unrelated_field_dials_no_reference(client: TestClient, plant_repo: MagicMock) -> None:
    """Changed-only: a rename must not be refused because of a reference it never
    touched, and must not cost a catalogue read either."""
    response = client.patch(_ITEM, json={"plant_name": "Fensterbank-Tomate"})

    assert response.status_code == 200, response.text
    plant_repo.update.assert_called_once()


# ── Pre-merge review, finding 1: "" is refused at the boundary ──────────
#
# ``PlantCreate.species_key`` was a bare ``str`` with no ``min_length``, and the
# service read ``if not value: continue`` — so an empty string was neither
# validated nor resolved. Measured against the pre-review branch:
#
#     POST {"species_key": ""}                -> 201, stored species_key = ''
#     PUT  {"species_key": ""}                -> 200, species stripped
#
# The boundary is the right place: ``""`` is not a well-formed key for any of
# these fields, and 422 with the field name says so far more usefully than the
# 404 the service would otherwise raise.


@pytest.mark.parametrize(
    ("method", "url", "payload", "field"),
    [
        ("post", _COLLECTION, _body(species_key=""), "species_key"),
        ("post", _COLLECTION, _body(substrate_key=""), "substrate_key"),
        ("post", _COLLECTION, _body(location_key=""), "location_key"),
        ("put", _ITEM, _body(species_key=""), "species_key"),
        ("patch", _ITEM, {"species_key": ""}, "species_key"),
        ("patch", _ITEM, {"substrate_batch_key": ""}, "substrate_batch_key"),
    ],
)
def test_an_empty_reference_key_is_refused_with_422(
    client: TestClient, plant_repo: MagicMock, method: str, url: str, payload: dict, field: str
) -> None:
    response = getattr(client, method)(url, json=payload)

    assert response.status_code == 422, response.text
    assert field in response.text
    plant_repo.create.assert_not_called()
    plant_repo.update.assert_not_called()


def test_an_explicit_null_still_clears_an_optional_reference(client: TestClient, plant_repo: MagicMock) -> None:
    """The control: ``min_length`` must constrain the string arm of the union only.

    ``PATCH {"substrate_key": null}`` is the documented way to clear a reference
    (#1098). If the constraint had been put on the union it would refuse ``null``
    too, and the only way to unset a field would be gone.
    """
    response = client.patch(_ITEM, json={"substrate_key": None})

    assert response.status_code == 200, response.text
    assert response.json()["substrate_key"] is None
    plant_repo.update.assert_called_once()


# ── Pre-merge review, finding 2: the placement chain, over HTTP ─────────
#
# Measured against the pre-review branch:
#
#     POST {"site_key": "site_own", "location_key": "loc_other",
#           "slot_key": "slot_other"}          -> 201
#
# Every one of those three keys belongs to the caller. Read one at a time they
# all pass; read as a chain they describe a plant in a location that is not in
# its site, in a slot that is not in its location.


def test_a_placement_chain_that_does_not_hold_together_is_refused_with_422(
    client: TestClient, plant_repo: MagicMock
) -> None:
    """422, not 404: the caller can see all three objects, so naming the
    inconsistency discloses nothing (the #970 boundary convention — a well-formed
    request the domain rejects)."""
    response = client.post(
        _COLLECTION, json=_body(site_key="site_own", location_key="loc_other", slot_key="slot_other")
    )

    assert response.status_code == 422, response.text
    plant_repo.create.assert_not_called()


def test_a_coherent_placement_chain_is_still_accepted(client: TestClient, plant_repo: MagicMock) -> None:
    """Control — without it a chain check that refused every placement would pass."""
    response = client.post(_COLLECTION, json=_body(site_key="site_own", location_key="loc_own", slot_key="slot_own"))

    assert response.status_code == 201, response.text
    assert response.json()["location_key"] == "loc_own"
    plant_repo.create.assert_called_once()

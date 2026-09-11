"""API tests for /nutrient-calculations (AP-10 mixing-protocol, AP-11 area-dosing).

The mixing-protocol endpoint now runs the canonical EcBudgetCalculator
(REQ-004-A) instead of the removed NutrientSolutionCalculator: doses drop by
the pH reserve and the legacy response shape is preserved plus additive
transparency fields.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.common.auth import get_current_tenant
from app.common.dependencies import get_fertilizer_service
from app.common.enums import FertilizerType, SiteType, TenantRole
from app.common.exceptions import NotFoundError
from app.domain.models.fertilizer import Fertilizer
from app.domain.models.site import Location, Site
from app.domain.models.tenant_context import TenantContext
from app.domain.services.fertilizer_service import FertilizerService


class _FakeFertRepo:
    def __init__(self, ferts: dict[str, Fertilizer]) -> None:
        self._ferts = ferts

    def get_by_key(self, key: str) -> Fertilizer | None:
        return self._ferts.get(key)

    def get_or_raise(self, key: str) -> Fertilizer:
        fert = self._ferts.get(key)
        if fert is None:
            raise NotFoundError("Fertilizer", key)
        return fert


class _FakeSiteRepo:
    """A site repository that stores what the write path stores.

    `Location` rows carry **no** `tenant_key` — `LocationCreate` may not declare
    one (#1000) and `create_location` does `Location(**body.model_dump())`. The
    tenant lives on the parent site, so this double serves sites too (#1397).

    It used to invent the field, and that is why nobody noticed that
    `FertilizerService`'s guard refused every location including the caller's own:
    the positive test passed on a row the application cannot produce, and the
    negative test would have passed against a guard that refused everything.
    """

    #: Which tenant each fixture site belongs to.
    _SITE_TENANTS = {"site-1": "personal", "site-2": "other"}

    def __init__(self, locations: dict[str, Location]) -> None:
        self._locations = locations

    def get_location_by_key(self, key: str) -> Location | None:
        return self._locations.get(key)

    def get_site_by_key(self, key: str) -> Site | None:
        tenant = self._SITE_TENANTS.get(key)
        if tenant is None:
            return None
        return Site(_key=key, tenant_key=tenant, name=key, type=SiteType.OUTDOOR)

    def get_location_or_raise(self, key: str) -> Location:
        location = self._locations.get(key)
        if location is None:
            raise NotFoundError("Location", key)
        return location


def _fertilizers() -> dict[str, Fertilizer]:
    return {
        "fert-a": Fertilizer(
            _key="fert-a",
            product_name="Base A",
            fertilizer_type=FertilizerType.BASE,
            ec_contribution_per_ml=0.1,
        ),
        "hornspaene": Fertilizer(
            _key="hornspaene",
            product_name="Hornspäne",
            fertilizer_type=FertilizerType.ORGANIC,
            npk_ratio=(14.0, 0.0, 0.0),
            application_rate_g_per_m2=80.0,
        ),
    }


def _locations() -> dict[str, Location]:
    return {
        "loc-1": Location(_key="loc-1", name="Bed 1", site_key="site-1", area_m2=2.5),
        "loc-empty": Location(_key="loc-empty", name="Bed 0", site_key="site-1", area_m2=0.0),
        # Under site-2, which belongs to another tenant — "foreign" expressed the way
        # the data expresses it, not as an invented field on the row itself.
        "loc-other": Location(_key="loc-other", name="Bed X", site_key="site-2", area_m2=5.0),
    }


def _ctx() -> TenantContext:
    return TenantContext(tenant_key="personal", tenant_slug="personal", user_key="u1", role=TenantRole.GROWER)


@pytest.fixture
def client():
    service = FertilizerService(_FakeFertRepo(_fertilizers()), site_repo=_FakeSiteRepo(_locations()))
    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

        app.dependency_overrides[get_fertilizer_service] = lambda: service
        app.dependency_overrides[get_current_tenant] = _ctx
        yield TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides.pop(get_fertilizer_service, None)
        app.dependency_overrides.pop(get_current_tenant, None)


# ── Mixing protocol (AP-10) ──────────────────────────────────────────


class TestMixingProtocol:
    def test_ph_reserve_deducted_hard_water(self, client):
        """EC net = 1.8 - 0.4 = 1.4; hard water reserve 0.05 → dose ≈ 13.5 ml/L."""
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/mixing-protocol",
            json={
                "target_volume_liters": 10.0,
                "target_ec_ms": 1.8,
                "target_ph": 6.0,
                "base_water_ec": 0.4,
                "base_water_ph": 7.0,
                "fertilizer_keys": ["fert-a"],
                "substrate_type": "coco",
                "alkalinity_ppm": 200,
                "recipe_ml_per_liter": {"fert-a": 10.0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ec_ph_reserve"] == pytest.approx(0.05)
        assert data["ec_net"] == pytest.approx(1.4, abs=0.01)
        assert data["dosages"][0]["ml_per_liter"] == pytest.approx(13.5, abs=0.1)
        # Legacy over-concentrated dose (14.0 ml/L) must no longer appear.
        assert data["dosages"][0]["ml_per_liter"] < 14.0

    def test_response_shape_backward_compatible(self, client):
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/mixing-protocol",
            json={
                "target_volume_liters": 10.0,
                "target_ec_ms": 1.5,
                "target_ph": 5.8,
                "base_water_ec": 0.3,
                "base_water_ph": 7.2,
                "fertilizer_keys": ["fert-a"],
                "recipe_ml_per_liter": {"fert-a": 8.0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Legacy keys preserved
        assert {"dosages", "calculated_ec", "ph_adjustment", "warnings", "instructions"} <= data.keys()
        dosage = data["dosages"][0]
        assert {"fertilizer_key", "product_name", "ml_per_liter", "total_ml", "ec_contribution"} <= dosage.keys()
        assert {"needed", "direction", "delta"} <= data["ph_adjustment"].keys()
        assert data["ph_adjustment"]["direction"] == "down"
        # Additive transparency fields
        assert {"ec_net", "ec_ph_reserve", "valid"} <= data.keys()


# ── Area dosing (AP-11) ──────────────────────────────────────────────


class TestAreaDosing:
    def test_area_dosing_explicit_area(self, client):
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/area-dosing",
            json={"fertilizer_keys": ["hornspaene"], "area_m2": 2.5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["area_m2"] == 2.5
        assert data["items"][0]["total_grams"] == pytest.approx(200.0)

    def test_area_dosing_from_location(self, client):
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/area-dosing",
            json={"fertilizer_keys": ["hornspaene"], "location_key": "loc-1"},
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["total_grams"] == pytest.approx(200.0)

    def test_area_override_wins_over_location(self, client):
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/area-dosing",
            json={"fertilizer_keys": ["hornspaene"], "location_key": "loc-1", "area_m2": 1.0},
        )
        assert response.status_code == 200
        assert response.json()["items"][0]["total_grams"] == pytest.approx(80.0)

    def test_location_without_area_returns_422(self, client):
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/area-dosing",
            json={"fertilizer_keys": ["hornspaene"], "location_key": "loc-empty"},
        )
        assert response.status_code == 422

    def test_cross_tenant_location_is_not_resolved(self, client):
        """AP-8/AP-11: a location owned by another tenant must not resolve its
        area for the caller — it is reported as not found (404), not leaked."""
        response = client.post(
            "/api/v1/t/personal/nutrient-calculations/area-dosing",
            json={"fertilizer_keys": ["hornspaene"], "location_key": "loc-other"},
        )
        assert response.status_code == 404

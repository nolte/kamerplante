"""Test calculation endpoints that don't require database.

**These endpoints are authenticated since #1402** and were not before. The
override below is the whole difference: until #1402 this file drove
``/api/v1/calculations/*`` with no credential at all and every call answered 200,
which is precisely what made the defect invisible — an endpoint whose test never
supplies a caller cannot notice that it never asks for one.

The override supplies a caller rather than removing the gate, so the 401 path
stays real; ``TestTheCalculationsRouterIsGated`` at the end of this file asserts
it, because a suite that only ever calls through an override proves the handler
works and says nothing about who may reach it.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.common.auth import get_current_user
from app.common.dependencies import get_auth_provider
from app.common.exceptions import UnauthorizedError
from app.domain.interfaces.auth_provider import IAuthProvider
from app.domain.models.user import User


def _user() -> User:
    return User(
        key="user-a",
        email="caller@example.org",
        display_name="Caller",
        email_verified=True,
    )


class _HeaderAuthProvider(IAuthProvider):
    """Refuses an absent Authorization header, accepts any present one.

    Deliberately the REAL dependency chain rather than an override of
    ``get_current_user``: overriding the gate itself would make the refusal test
    below assert the override, not the router. The production provider needs a
    database connection this file does not stand up, so an anonymous call
    without this substitution answers **500** — which is not a refusal, and
    accepting it as one is how a test passes for the wrong reason.
    """

    def resolve_user(self, authorization: str | None) -> User:
        if not authorization:
            raise UnauthorizedError("Missing credentials.")
        return _user()

    def resolve_user_optional(self, authorization: str | None) -> User | None:
        return _user() if authorization else None

    def is_authentication_required(self) -> bool:
        return True


def _get_client(*, authenticated: bool = True):
    """Create test client, mocking DB connection."""
    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

        app.dependency_overrides[get_auth_provider] = _HeaderAuthProvider
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app, raise_server_exceptions=False)
        if authenticated:
            client.headers["Authorization"] = "Bearer test-token"
        return client


class TestVPDCalculation:
    def test_vpd_calculation(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/vpd",
            json={
                "temp_c": 25.0,
                "humidity_percent": 60.0,
                "phase": "vegetative",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "vpd_kpa" in data
        assert "status" in data
        assert "recommendation" in data
        assert data["vpd_kpa"] > 0

    def test_vpd_high_humidity(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/vpd",
            json={
                "temp_c": 25.0,
                "humidity_percent": 95.0,
                "phase": "seedling",
            },
        )
        data = response.json()
        assert data["vpd_kpa"] < 0.5


class TestGDDCalculation:
    def test_gdd_calculation(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/gdd",
            json={
                "daily_temps": [[30.0, 20.0], [28.0, 18.0]],
                "base_temp_c": 10.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["accumulated_gdd"] == 28.0
        assert data["days_counted"] == 2


class TestSlotCapacity:
    def test_slot_capacity(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/slot-capacity",
            json={
                "area_m2": 4.0,
                "plant_spacing_cm": 50.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_capacity"] == 16
        assert len(data["optimal_range"]) == 2
        assert data["plants_per_m2"] > 0


class TestPhotoperiodTransition:
    def test_transition(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/photoperiod-transition",
            json={
                "current_hours": 18.0,
                "target_hours": 12.0,
                "transition_days": 7,
                "ppfd": 400,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["schedule"]) == 7
        assert data["schedule"][-1]["photoperiod_hours"] == 12.0


class TestHealthEndpoints:
    def test_liveness(self):
        client = _get_client()
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestTheCalculationsRouterIsGated:
    """The gate itself (#1402), asserted without the override that hides it.

    Every other test in this file passes a caller. This one does not, and it is
    the only thing here that would go red if the router-level
    ``Depends(get_current_user)`` were dropped again.
    """

    def test_an_anonymous_caller_is_refused(self):
        client = _get_client(authenticated=False)
        response = client.post(
            "/api/v1/calculations/vpd",
            json={"temp_c": 25.0, "humidity_percent": 60.0, "phase": "vegetative"},
        )
        assert response.status_code in (401, 403), (
            f"anonymous POST /calculations/vpd answered {response.status_code}; "
            "the router-level gate from #1402 is gone or inert"
        )

    def test_an_authenticated_caller_passes(self):
        """The control. A gate that refuses everyone would satisfy the test above."""
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/vpd",
            json={"temp_c": 25.0, "humidity_percent": 60.0, "phase": "vegetative"},
        )
        assert response.status_code == 200

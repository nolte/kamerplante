"""NFR-006: Verify structured error responses and no information leakage."""

import re
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.common.dependencies import get_auth_provider
from app.common.exceptions import UnauthorizedError
from app.domain.interfaces.auth_provider import IAuthProvider
from app.domain.models.user import User


class _HeaderAuthProvider(IAuthProvider):
    """Refuses an absent Authorization header, accepts any present one (#1402)."""

    def resolve_user(self, authorization: str | None) -> User:
        if not authorization:
            raise UnauthorizedError("Missing credentials.")
        return User(key="user-a", email="caller@example.org", display_name="Caller", email_verified=True)

    def resolve_user_optional(self, authorization: str | None) -> User | None:
        return self.resolve_user(authorization) if authorization else None

    def is_authentication_required(self) -> bool:
        return True


FORBIDDEN_PATTERNS = [
    r"ArangoDB",
    r"arango",
    r"DocumentInsertError",
    r"DocumentUpdateError",
    r"Traceback",
    r'File "/',
    r"\.py",
    r"localhost:",
    r"redis://",
    r"uvicorn",
    r"FastAPI",
    r"Pydantic",
    r"python-arango",
    r"celery",
    r"idx_\d+",
    r"172\.\d+\.\d+\.\d+",
    r"/app/app/",
    r"/usr/local/lib/",
    r"ARANGODB_",
    r"REDIS_URL",
]


def _get_client():
    """An AUTHENTICATED client, because the probe endpoint is gated since #1402.

    This file tests the NFR-006 error envelope and uses ``/api/v1/calculations/vpd``
    only as a convenient operation to provoke a 422 against. That endpoint answered
    an anonymous caller until #1402 gated its router; without a credential every
    assertion here would now measure the 401 envelope instead of the validation
    one, which is a different contract and would pass or fail for reasons that have
    nothing to do with what the file is about.

    The substitution is at the auth PROVIDER, not at ``get_current_user``: the
    production provider needs a database connection this file does not stand up,
    so an anonymous call answers 500 rather than 401.
    """
    with patch("app.main.get_connection"), patch("app.main.ensure_collections"):
        from app.main import app

        app.dependency_overrides[get_auth_provider] = _HeaderAuthProvider
        client = TestClient(app, raise_server_exceptions=False)
        client.headers["Authorization"] = "Bearer test-token"
        return client


def _assert_error_schema(body: dict) -> None:
    """Assert the response body matches NFR-006 ErrorResponse schema."""
    assert "error_id" in body, "Missing error_id"
    assert body["error_id"].startswith("err_"), f"error_id must start with 'err_': {body['error_id']}"
    assert "error_code" in body, "Missing error_code"
    assert "message" in body, "Missing message"
    assert "details" in body, "Missing details"
    assert "timestamp" in body, "Missing timestamp"
    assert "path" in body, "Missing path"
    assert "method" in body, "Missing method"


def _assert_no_leakage(body: dict) -> None:
    """Assert the response body doesn't contain forbidden patterns."""
    body_str = str(body)
    for pattern in FORBIDDEN_PATTERNS:
        assert not re.search(pattern, body_str, re.IGNORECASE), (
            f"Forbidden pattern '{pattern}' found in error response: {body_str[:200]}"
        )


class TestValidationErrorFormat:
    def test_missing_required_field(self):
        client = _get_client()
        response = client.post("/api/v1/calculations/vpd", json={})
        assert response.status_code == 422
        body = response.json()
        _assert_error_schema(body)
        assert body["error_code"] == "VALIDATION_ERROR"
        assert len(body["details"]) > 0
        _assert_no_leakage(body)

    def test_invalid_field_type(self):
        client = _get_client()
        response = client.post(
            "/api/v1/calculations/vpd",
            json={
                "temp_c": "not_a_number",
                "humidity_percent": 60.0,
            },
        )
        assert response.status_code == 422
        body = response.json()
        _assert_error_schema(body)
        assert body["error_code"] == "VALIDATION_ERROR"
        _assert_no_leakage(body)

    def test_detail_has_field_and_reason(self):
        client = _get_client()
        response = client.post("/api/v1/calculations/vpd", json={})
        body = response.json()
        for detail in body["details"]:
            assert "field" in detail
            assert "reason" in detail
            assert "code" in detail


class TestUnhandledErrorFormat:
    def test_unhandled_exception_returns_safe_500(self):
        client = _get_client()
        with patch(
            "app.api.v1.calculations.router.calculate_vpd",
            side_effect=RuntimeError("DB connection pool exhausted on 172.21.0.3"),
        ):
            response = client.post(
                "/api/v1/calculations/vpd",
                json={
                    "temp_c": 25.0,
                    "humidity_percent": 60.0,
                    "phase": "vegetative",
                },
            )
        assert response.status_code == 500
        body = response.json()
        _assert_error_schema(body)
        assert body["error_code"] == "INTERNAL_ERROR"
        assert body["details"] == []
        assert "172.21.0.3" not in str(body)
        assert "DB connection" not in str(body)
        assert "RuntimeError" not in str(body)
        _assert_no_leakage(body)


class TestErrorIdUniqueness:
    def test_each_error_has_unique_id(self):
        client = _get_client()
        ids = set()
        for _ in range(5):
            response = client.post("/api/v1/calculations/vpd", json={})
            body = response.json()
            ids.add(body["error_id"])
        assert len(ids) == 5, "Each error response must have a unique error_id"


class TestErrorResponsePathAndMethod:
    def test_path_and_method_correct(self):
        client = _get_client()
        response = client.post("/api/v1/calculations/vpd", json={})
        body = response.json()
        assert body["path"] == "/api/v1/calculations/vpd"
        assert body["method"] == "POST"

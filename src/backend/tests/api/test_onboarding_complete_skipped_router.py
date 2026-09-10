"""``POST /t/{slug}/onboarding/complete`` reports what it could not provision.

The sibling unit suite
(``tests/unit/domain/services/test_onboarding_plant_creation.py``) pins the
service. This one pins the fact that the report **survives the response model** —
which is the half a service-level assertion cannot show: FastAPI filters the
returned dict through ``OnboardingCompleteResponse``, so a ``skipped`` list the
service produces and the schema does not declare is dropped between the two, and
the endpoint answers ``200 completed`` exactly as it did before the fix.

No datastore is touched (#978).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.onboarding.tenant_router import router as onboarding_router
from app.common import auth as auth_mod
from app.common.dependencies import get_onboarding_service
from app.common.enums import TenantRole
from app.domain.models.tenant_context import TenantContext

TENANT = "t1"
_URL = f"/api/v1/t/{TENANT}/onboarding/complete"


class _OnboardingService:
    """Returns what the real service returns for one resolvable + one ghost species."""

    def complete_wizard(self, **kwargs: object) -> dict:
        return {
            "status": "completed",
            "created_entities": {"plant_instances": ["plant-1"]},
            "skipped": [
                {
                    "entity_type": "plant_instance",
                    "key": "sp-ghost",
                    "reason": "Species with key 'sp-ghost' not found.",
                }
            ],
        }


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(onboarding_router, prefix="/api/v1/t/{tenant_slug}")
    app.dependency_overrides[auth_mod.get_current_user] = lambda: SimpleNamespace(key="u1", account_type="user")
    app.dependency_overrides[get_onboarding_service] = _OnboardingService
    app.dependency_overrides[auth_mod.get_current_tenant] = lambda: TenantContext(
        tenant_key=TENANT, tenant_slug=TENANT, user_key="u1", role=TenantRole.LEAD, admin_scopes=[]
    )
    return TestClient(app)


def test_a_skipped_plant_reaches_the_caller(client: TestClient) -> None:
    """Red against the pre-review schema, which declared only ``status`` and
    ``created_entities`` and therefore dropped the list on the way out."""
    response = client.post(_URL, json={"plant_configs": [{"species_key": "sp-ghost", "count": 1}]})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["skipped"] == [
        {"entity_type": "plant_instance", "key": "sp-ghost", "reason": "Species with key 'sp-ghost' not found."}
    ]


def test_the_field_is_always_present_and_empty_on_the_happy_path(client: TestClient) -> None:
    """A caller that has to test for the key's existence before reading it will
    eventually not test — so the field is declared with a default, not omitted."""
    from app.api.v1.onboarding.schemas import OnboardingCompleteResponse

    response = OnboardingCompleteResponse(status="completed", created_entities={})

    assert response.skipped == []

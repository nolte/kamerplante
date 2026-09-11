"""Tenant-scoped onboarding router.

Wraps onboarding endpoints under /t/{tenant_slug}/onboarding so that
get_current_tenant enforces membership. Onboarding state itself is
user-global (not per-tenant).
"""

from fastapi import APIRouter, Depends

from app.api.mapping import to_response
from app.api.v1.onboarding.schemas import (
    OnboardingCompleteRequest,
    OnboardingCompleteResponse,
    OnboardingProgressUpdate,
    OnboardingStateResponse,
)
from app.common.auth import get_current_tenant, require_permission
from app.common.dependencies import get_onboarding_service
from app.core.permissions import Action, ResourceType
from app.domain.models.onboarding import PlantConfig
from app.domain.models.tenant_context import TenantContext
from app.domain.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/state", response_model=OnboardingStateResponse)
def get_onboarding_state(
    ctx: TenantContext = Depends(get_current_tenant),
    service: OnboardingService = Depends(get_onboarding_service),
):
    """Return the caller's current onboarding-wizard state."""
    state = service.get_state(ctx.user_key)
    return to_response(state, OnboardingStateResponse)


@router.post("/complete", response_model=OnboardingCompleteResponse)
def complete_onboarding(
    body: OnboardingCompleteRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.PLANT, Action.CREATE)),
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingCompleteResponse:
    """Finish the onboarding wizard and provision the selected starter entities."""
    plant_configs = (
        [
            PlantConfig(species_key=c.species_key, count=c.count, initial_phase=c.initial_phase)
            for c in body.plant_configs
        ]
        if body.plant_configs
        else None
    )
    result = service.complete_wizard(
        user_key=ctx.user_key,
        tenant_key=ctx.tenant_key,
        kit_id=body.kit_id,
        experience_level=body.experience_level.value if body.experience_level else None,
        site_name=body.site_name,
        selected_site_key=body.selected_site_key,
        plant_count=body.plant_count,
        plant_configs=plant_configs,
        has_ro_system=body.has_ro_system,
        tap_water_ec_ms=body.tap_water_ec_ms,
        tap_water_ph=body.tap_water_ph,
        favorite_species_keys=body.favorite_species_keys,
        favorite_nutrient_plan_keys=body.favorite_nutrient_plan_keys,
        smart_home_enabled=body.smart_home_enabled,
    )
    return OnboardingCompleteResponse(**result)


@router.post("/skip", response_model=OnboardingStateResponse)
def skip_onboarding(
    ctx: TenantContext = Depends(get_current_tenant),
    service: OnboardingService = Depends(get_onboarding_service),
):
    """Skip the onboarding wizard for the caller."""
    state = service.skip_wizard(ctx.user_key)
    return to_response(state, OnboardingStateResponse)


@router.post("/reset", response_model=OnboardingStateResponse)
def reset_onboarding(
    ctx: TenantContext = Depends(get_current_tenant),
    service: OnboardingService = Depends(get_onboarding_service),
):
    """Reset the caller's onboarding wizard back to its initial state."""
    state = service.reset_wizard(ctx.user_key)
    return to_response(state, OnboardingStateResponse)


@router.patch("/state", response_model=OnboardingStateResponse)
def update_onboarding_progress(
    body: OnboardingProgressUpdate,
    ctx: TenantContext = Depends(get_current_tenant),
    service: OnboardingService = Depends(get_onboarding_service),
):
    """Persist partial onboarding-wizard progress for the caller."""
    kwargs = {}
    if body.selected_kit_id is not None:
        kwargs["selected_kit_id"] = body.selected_kit_id
    if body.selected_experience_level is not None:
        kwargs["selected_experience_level"] = body.selected_experience_level.value
    if body.site_name is not None:
        kwargs["site_name"] = body.site_name
    if body.site_type is not None:
        kwargs["site_type"] = body.site_type
    if body.plant_count is not None:
        kwargs["plant_count"] = body.plant_count
    if body.favorite_species_keys is not None:
        kwargs["favorite_species_keys"] = body.favorite_species_keys
    if body.favorite_nutrient_plan_keys is not None:
        kwargs["favorite_nutrient_plan_keys"] = body.favorite_nutrient_plan_keys
    state = service.save_progress(ctx.user_key, body.wizard_step, **kwargs)
    return to_response(state, OnboardingStateResponse)

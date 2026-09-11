from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.activities.router import router as activities_router
from app.api.v1.admin.harvest_indicators.router import router as harvest_indicators_admin_router
from app.api.v1.admin.pests.router import router as pests_admin_router
from app.api.v1.admin.recognition.router import router as recognition_admin_router
from app.api.v1.admin.reference_images.router import router as reference_images_router
from app.api.v1.admin.settings.router import router as admin_settings_router
from app.api.v1.admin.weather_providers.router import router as weather_providers_admin_router
from app.api.v1.attachments.token_router import router as attachment_token_router
from app.api.v1.botanical_families.router import router as families_router
from app.api.v1.calculations.router import router as calculations_router
from app.api.v1.care_reminders.router import router as care_reminders_router
from app.api.v1.companion_planting.router import router as companion_router
from app.api.v1.crop_rotation.router import router as rotation_router
from app.api.v1.cultivars.router import router as cultivars_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.enrichment.router import router as enrichment_router
from app.api.v1.family_relationships.router import router as family_relationships_router
from app.api.v1.fish_species.router import router as fish_species_router
from app.api.v1.growth_phases.router import router as phases_router
from app.api.v1.hardiness_zones.router import router as hardiness_zones_router
from app.api.v1.health.router import router as health_router
from app.api.v1.imports.router import router as imports_router
from app.api.v1.ipm.pest_images_router import router as pest_images_router
from app.api.v1.ipm.router import router as ipm_router
from app.api.v1.lifecycle_configs.router import router as lifecycle_router
from app.api.v1.location_types.router import router as location_types_router
from app.api.v1.observations.router import router as observations_router
from app.api.v1.phase_sequences.router import router as phase_sequences_router
from app.api.v1.phases.router import router as phase_control_router
from app.api.v1.privacy.router import public_router as privacy_public_router
from app.api.v1.profiles.router import router as profiles_router
from app.api.v1.recognition.router import router as recognition_router
from app.api.v1.species.router import router as species_router
from app.api.v1.starter_kits.router import router as starter_kits_router
from app.api.v1.substrates.router import router as substrates_router
from app.api.v1.tenant_scoped.router import tenant_scoped_router
from app.api.v1.tenants.router import router as tenants_router
from app.api.v1.users.router import router as users_router
from app.common.openapi_responses import VALIDATION_RESPONSE
from app.config.settings import settings

# The 422 envelope is documented globally: every operation is behind the same
# RequestValidationError handler, and the envelope replaces FastAPI's default
# HTTPValidationError schema (spec/project/api-documentation/).
api_router = APIRouter(prefix="/api/v1", responses=VALIDATION_RESPONSE)


# ── REQ-027 Mode endpoint ───────────────────────────────────────────
mode_router = APIRouter(tags=["mode"])


class ModeFeatures(BaseModel):
    """Feature flags derived from the active deployment mode."""

    auth: bool
    multi_tenant: bool
    privacy_consent: bool


class ModeResponse(BaseModel):
    """Current deployment mode and its feature flags (REQ-027)."""

    mode: str
    features: ModeFeatures


@mode_router.get("/mode", response_model=ModeResponse)
def get_mode():
    """Return current deployment mode and feature flags."""
    is_full = settings.kamerplanter_mode == "full"
    return {
        "mode": settings.kamerplanter_mode,
        "features": {
            "auth": is_full,
            "multi_tenant": is_full,
            "privacy_consent": is_full,
        },
    }


api_router.include_router(mode_router)

# Admin settings — available in both modes
# REQ-007 §4 — the global harvest-indicator catalogue is platform-admin
# territory; it used to be writable from the tenant mount (#1249).
api_router.include_router(harvest_indicators_admin_router)
api_router.include_router(admin_settings_router)
# REQ-046 — central public weather-provider admin. platform-admin-gated
# (light-mode-aware, like admin/settings/storage), so it is mode-agnostic and
# registered once for both light and full mode.
api_router.include_router(weather_providers_admin_router)
# Recognition admin, available in both light and full mode (the inference feature
# itself is optional). Platform-admin-gated on both its operations since #1401,
# matching the pests router mounted below.
#
# Two earlier versions of this comment were wrong, in opposite directions, and the
# pair is worth keeping visible: it first said "read-only + get_current_user-gated,
# like admin settings" (both halves went false when #1385 gated admin settings and
# when anyone read /acquire), and the correction then described /acquire as still
# carrying get_current_user alone — which #1401 fixed two commits later, in this
# same branch. A comment that states a measured gate goes stale the moment the gate
# moves; this one now names the issue that set it, so the next reader can check.
api_router.include_router(recognition_admin_router)
# REQ-044 pest few-shot index admin (coverage, gallery, acquisition).
# Platform-admin-gated, available in light + full mode — the same gate the
# recognition router above now carries. This comment briefly read "not like
# recognition admin", which was true for exactly the two commits between #1385 and
# #1401.
api_router.include_router(pests_admin_router)
# Reference-image acquisition + manual curation (REQ-029-A) belongs to the same
# optional inference feature and is available in both modes. Its endpoints are
# require_platform_admin-gated; in light mode the sole system user is treated as
# admin (see require_platform_admin), so the operator can curate their index.
api_router.include_router(reference_images_router)

# Privacy policy endpoint is public in both modes per REQ-025 §3.6
# (DSGVO Art. 13/14 Hinweispflicht applies regardless of auth mode).
api_router.include_router(privacy_public_router)

# API-key management is mounted in BOTH modes (REQ-033 §4.3). It is the one part
# of the auth surface a light-mode instance needs: MCP accepts nothing but a
# `kp_` API key, so without this the MCP interface could be switched on but never
# actually used there. In light mode the key is issued to the system user, which
# every request already resolves to anyway — it grants no new authority, it only
# makes the existing access reachable from an external client.
from app.api.v1.auth.router import api_keys_router  # noqa: E402

api_router.include_router(api_keys_router)

# The remaining auth surface — login, registration, sessions, OAuth, privacy —
# presupposes real accounts and therefore exists only in full mode.
if settings.kamerplanter_mode == "full":
    from app.api.v1.admin.oidc_providers.router import router as oidc_providers_router
    from app.api.v1.admin.platform.router import router as platform_admin_router
    from app.api.v1.auth.router import router as auth_router
    from app.api.v1.privacy.router import router as privacy_router

    api_router.include_router(auth_router)
    api_router.include_router(oidc_providers_router)
    api_router.include_router(platform_admin_router)
    api_router.include_router(privacy_router)

api_router.include_router(users_router)
api_router.include_router(health_router)
api_router.include_router(families_router)
api_router.include_router(hardiness_zones_router)
api_router.include_router(calculations_router)
api_router.include_router(companion_router)
api_router.include_router(rotation_router)
api_router.include_router(cultivars_router)
api_router.include_router(phases_router)
api_router.include_router(lifecycle_router)
api_router.include_router(location_types_router)
api_router.include_router(phase_control_router)
api_router.include_router(profiles_router)
api_router.include_router(species_router)
api_router.include_router(substrates_router)
api_router.include_router(enrichment_router)
api_router.include_router(family_relationships_router)
# REQ-026 Aquaponics — global fish-species catalog (not tenant-scoped)
api_router.include_router(fish_species_router)
api_router.include_router(ipm_router)
# REQ-010 — global, read-only content endpoint for *promoted* pest images
# (cross-tenant pixels). Authenticated-only, no tenant prefix; promotion is the
# authorization. Available in both modes (the gate is status=promoted, not auth
# mode). Mounted before the tenant-scoped router so /ipm/pest-images/... is
# matched as a global route, not under a tenant slug.
api_router.include_router(pest_images_router)
api_router.include_router(tenants_router)
# NFR-013 §4.2 — local-fs signed-token download redemption (global, not
# tenant-scoped; the token is the authorization). Mounted before the
# tenant-scoped router so /attachments/token/{token} is matched specifically.
api_router.include_router(attachment_token_router)
api_router.include_router(tenant_scoped_router)
api_router.include_router(care_reminders_router)
api_router.include_router(dashboard_router)
api_router.include_router(starter_kits_router)
api_router.include_router(imports_router)
api_router.include_router(activities_router)
# ``/activity-plans/apply`` moved under the tenant-scoped router (#1000); the
# global activity-plans router had nothing left on it and was removed. Generation
# and the template writes already live on ``activity_plans.tenant_router``.
api_router.include_router(observations_router)
api_router.include_router(phase_sequences_router)
api_router.include_router(recognition_router)

# ── Knowledge / RAG (conditional on knowledge service) ────────────
if settings.knowledge_service_enabled:
    from app.api.v1.knowledge.router import router as knowledge_router

    api_router.include_router(knowledge_router)

# ── REQ-031 KI-Assistent — public (light-mode) + global (platform-admin) ──
# Always mounted; the operator flag (AI_FEATURES_ENABLED) is enforced in-router
# and returns 404 when off, so the endpoints appear non-existent (§1.3 stage 1).
# The tenant-scoped /ai/* routes live under the tenant_scoped_router.
from app.api.v1.ki_assistent.global_router import router as ai_global_router  # noqa: E402
from app.api.v1.ki_assistent.public_router import router as ai_public_router  # noqa: E402
from app.api.v1.ki_assistent.status_router import router as ai_status_router  # noqa: E402

# Issue #685 — public availability probe. Ungated by the operator flag (it
# reports it) and mounted in both modes so the frontend can hide the nav entry.
api_router.include_router(ai_status_router)
api_router.include_router(ai_public_router)
if settings.kamerplanter_mode == "full":
    api_router.include_router(ai_global_router)

# ── REQ-035 KI terminology glossary ──────────────────────────────────
# Knowledge feature (no PII, §6): the public/light endpoints are always mounted;
# the platform-admin term CRUD is full-mode only. The tenant-scoped read routes
# live under the tenant_scoped_router (/t/{slug}/glossary/*).
from app.api.v1.glossar.public_router import router as glossary_public_router  # noqa: E402

api_router.include_router(glossary_public_router)
if settings.kamerplanter_mode == "full":
    from app.api.v1.glossar.admin_router import router as glossary_admin_router  # noqa: E402

    api_router.include_router(glossary_admin_router)

# ── REQ-033 MCP server (Model Context Protocol) ───────────────────────
# Always mounted; the operator flag (MCP_SERVER_ENABLED) is enforced per-request
# and returns 404 when off, so the endpoints appear non-existent (§6). MCP
# authenticates service-account API keys only (REQ-023), which exist in full
# mode, but the flag/auth gate handles light mode gracefully.
from app.api.v1.mcp.router import router as mcp_router  # noqa: E402

api_router.include_router(mcp_router)

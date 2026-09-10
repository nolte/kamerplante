"""Tenant-scoped router.

Mounts tenant-aware resource routers under /t/{tenant_slug}/ prefix.
All endpoints in this router require authentication and tenant membership.
The TenantContext is available via Depends(get_current_tenant).

Global resources (botanical_families, species, cultivars, IPM reference data)
remain at /api/v1/ without tenant scoping.
"""

from fastapi import APIRouter

from app.api.v1.activity_plans.tenant_router import router as tenant_activity_plans_router
from app.api.v1.actuators.tenant_router import router as tenant_actuators_router
from app.api.v1.aquaponik.tenant_router import router as tenant_aquaponics_router
from app.api.v1.attachments.tenant_router import router as tenant_attachments_router
from app.api.v1.calendar.tenant_router import router as tenant_calendar_router
from app.api.v1.care_reminders.tenant_router import router as tenant_care_reminders_router
from app.api.v1.dashboard.tenant_router import router as tenant_dashboard_router
from app.api.v1.diagnose.tenant_router import router as tenant_diagnosis_router
from app.api.v1.diary.tenant_router import router as tenant_diary_router
from app.api.v1.equipment.tenant_router import router as tenant_equipment_router
from app.api.v1.favorites.tenant_router import router as tenant_favorites_router
from app.api.v1.feeding_events.tenant_router import router as tenant_feeding_events_router
from app.api.v1.fertilizers.tenant_router import router as tenant_fertilizers_router
from app.api.v1.glossar.router import router as tenant_glossary_router
from app.api.v1.ha_publish.tenant_router import router as tenant_ha_publish_router
from app.api.v1.harvest.tenant_router import router as tenant_harvest_router
from app.api.v1.inventree.tenant_router import router as tenant_inventree_router
from app.api.v1.ipm.tenant_router import router as tenant_ipm_router
from app.api.v1.ki_assistent.tenant_router import router as tenant_ai_router
from app.api.v1.locations.tenant_router import router as tenant_locations_router
from app.api.v1.notifications.tenant_router import router as tenant_notifications_router
from app.api.v1.nutrient_calculations.router import router as nutrient_calculations_router
from app.api.v1.nutrient_plans.tenant_router import router as tenant_nutrient_plans_router
from app.api.v1.observations.tenant_router import router as tenant_observations_router
from app.api.v1.onboarding.tenant_router import router as tenant_onboarding_router
from app.api.v1.overwintering_profiles.tenant_router import router as tenant_overwintering_profiles_router
from app.api.v1.pest_detection.tenant_router import router as tenant_pest_detection_router
from app.api.v1.plant_instances.diary_router import router as tenant_plant_diary_router
from app.api.v1.plant_instances.environment_router import router as tenant_plant_environment_router
from app.api.v1.plant_instances.photo_router import router as tenant_plant_photos_router
from app.api.v1.plant_instances.tenant_router import router as tenant_plants_router
from app.api.v1.planting_runs.tenant_router import router as tenant_planting_runs_router
from app.api.v1.post_harvest.tenant_router import router as tenant_post_harvest_router
from app.api.v1.print.tenant_router import router as tenant_print_router
from app.api.v1.propagation.tenant_router import router as tenant_propagation_router
from app.api.v1.recognition.tenant_router import router as tenant_recognition_router
from app.api.v1.season.tenant_router import router as tenant_season_router
from app.api.v1.sites.tenant_router import router as tenant_sites_router
from app.api.v1.slots.tenant_router import router as tenant_slots_router
from app.api.v1.starter_kits.tenant_router import router as tenant_starter_kits_router
from app.api.v1.succession_plans.tenant_router import router as tenant_succession_plans_router
from app.api.v1.tanks.tenant_router import router as tenant_tanks_router
from app.api.v1.tasks.photo_router import router as tenant_task_photos_router
from app.api.v1.tasks.tenant_router import router as tenant_tasks_router
from app.api.v1.tenant_scoped.cv_diagnosis.tenant_router import router as tenant_cv_diagnosis_router
from app.api.v1.tenant_scoped.weather.tenant_router import router as tenant_weather_router
from app.api.v1.user_preferences.tenant_router import router as tenant_user_preferences_router
from app.api.v1.watering_events.tenant_router import router as tenant_watering_events_router
from app.api.v1.watering_logs.tenant_router import router as tenant_watering_logs_router
from app.common.openapi_responses import AUTH_RESPONSES

# Every operation below requires authentication and tenant membership, so the
# 401/403 envelope is documented once for the whole tenant-scoped surface.
tenant_scoped_router = APIRouter(
    prefix="/t/{tenant_slug}",
    tags=["tenant-scoped"],
    responses=AUTH_RESPONSES,
)

# Mount tenant-scoped resource routers
# These routers enforce tenant isolation via get_current_tenant() dependency.
tenant_scoped_router.include_router(tenant_sites_router)
tenant_scoped_router.include_router(tenant_locations_router)
tenant_scoped_router.include_router(tenant_slots_router)
tenant_scoped_router.include_router(tenant_plants_router)
tenant_scoped_router.include_router(tenant_plant_photos_router)
# REQ-013 §4.7 — standalone plant diary (/plant-instances/{key}/diary). Same
# shape as the photo gallery above; a plant without a planting run had no
# reachable diary before this, although REQ-013 §1 grants it one.
tenant_scoped_router.include_router(tenant_plant_diary_router)
# REQ-013 §2.3a — read-only preview of what a diary entry's environment snapshot
# would contain (/plant-instances/{key}/environment). Called before an entry
# exists, so it hangs off the plant rather than off the diary prefix.
tenant_scoped_router.include_router(tenant_plant_environment_router)
tenant_scoped_router.include_router(tenant_planting_runs_router)
# REQ-050 §2.5.2 — tenant-wide diary overview (/diary). The run aggregation
# covers one run; a plant without a run appears in none of them.
tenant_scoped_router.include_router(tenant_diary_router)
tenant_scoped_router.include_router(tenant_succession_plans_router)
tenant_scoped_router.include_router(tenant_tanks_router)
tenant_scoped_router.include_router(tenant_fertilizers_router)
tenant_scoped_router.include_router(tenant_nutrient_plans_router)
tenant_scoped_router.include_router(tenant_feeding_events_router)
tenant_scoped_router.include_router(nutrient_calculations_router)
tenant_scoped_router.include_router(tenant_watering_events_router)
tenant_scoped_router.include_router(tenant_watering_logs_router)
tenant_scoped_router.include_router(tenant_harvest_router)
tenant_scoped_router.include_router(tenant_post_harvest_router)
tenant_scoped_router.include_router(tenant_tasks_router)
# REQ-006 — task photo upload (/tasks/{key}/photos), on the NFR-013
# attachment fundament. Same shape as the plant gallery above; the
# completion form's upload button posted to a path no router served, so a
# `requires_photo` task could not be completed at all (#1339).
tenant_scoped_router.include_router(tenant_task_photos_router)
# REQ-006 §activity plans — the write routes on a plan's task templates (#992),
# plan generation (#1003), and applying a plan to a plant/run (#1000). All the
# writes on this feature are tenant-scoped now: generation and apply each need
# the caller's tenant (the private copy of a forked plan, and the tenant the
# created tasks are stamped with), and no route on it is global any more.
tenant_scoped_router.include_router(tenant_activity_plans_router)
tenant_scoped_router.include_router(tenant_ipm_router)
tenant_scoped_router.include_router(tenant_pest_detection_router)
tenant_scoped_router.include_router(tenant_calendar_router)
tenant_scoped_router.include_router(tenant_care_reminders_router)
tenant_scoped_router.include_router(tenant_dashboard_router)
tenant_scoped_router.include_router(tenant_overwintering_profiles_router)
tenant_scoped_router.include_router(tenant_season_router)
# REQ-031 KI-Assistent — /t/{slug}/ai/* (three-stage toggle enforced in-router)
tenant_scoped_router.include_router(tenant_ai_router)
# REQ-035 KI terminology glossary — /t/{slug}/glossary/* (no tenant data, §3.1)
tenant_scoped_router.include_router(tenant_glossary_router)
# REQ-036 KI-Diagnose — /t/{slug}/diagnosis/* (shares the KI three-stage toggle)
tenant_scoped_router.include_router(tenant_diagnosis_router)
tenant_scoped_router.include_router(tenant_starter_kits_router)
tenant_scoped_router.include_router(tenant_onboarding_router)
tenant_scoped_router.include_router(tenant_favorites_router)
tenant_scoped_router.include_router(tenant_notifications_router)
tenant_scoped_router.include_router(tenant_user_preferences_router)
tenant_scoped_router.include_router(tenant_observations_router)
tenant_scoped_router.include_router(tenant_ha_publish_router)
tenant_scoped_router.include_router(tenant_print_router)
tenant_scoped_router.include_router(tenant_recognition_router)
tenant_scoped_router.include_router(tenant_attachments_router)
tenant_scoped_router.include_router(tenant_weather_router)
tenant_scoped_router.include_router(tenant_cv_diagnosis_router)
# REQ-026 Aquaponics
tenant_scoped_router.include_router(tenant_aquaponics_router)
# REQ-018 Environment control / actuators
tenant_scoped_router.include_router(tenant_actuators_router)
# REQ-016 InvenTree integration (optional) — connections/references/sync + equipment
tenant_scoped_router.include_router(tenant_inventree_router)
tenant_scoped_router.include_router(tenant_equipment_router)
# REQ-017 Propagation / lineage
tenant_scoped_router.include_router(tenant_propagation_router)

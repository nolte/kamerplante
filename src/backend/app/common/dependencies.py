from arango.database import StandardDatabase

from app.config.settings import settings
from app.data_access.arango.auth_provider_repository import ArangoAuthProviderRepository
from app.data_access.arango.botanical_family_repository import ArangoBotanicalFamilyRepository
from app.data_access.arango.care_reminder_repository import ArangoCareReminderRepository
from app.data_access.arango.connection import ArangoConnection
from app.data_access.arango.enrichment_repository import (
    ArangoExternalMappingRepository,
    ArangoExternalSourceRepository,
    ArangoSyncRunRepository,
)
from app.data_access.arango.feeding_repository import ArangoFeedingRepository
from app.data_access.arango.fertilizer_repository import ArangoFertilizerRepository
from app.data_access.arango.graph_repository import ArangoGraphRepository
from app.data_access.arango.harvest_repository import ArangoHarvestRepository
from app.data_access.arango.invitation_repository import ArangoInvitationRepository
from app.data_access.arango.ipm_repository import ArangoIpmRepository
from app.data_access.arango.lifecycle_repository import ArangoLifecycleRepository
from app.data_access.arango.location_assignment_repository import ArangoLocationAssignmentRepository
from app.data_access.arango.membership_repository import ArangoMembershipRepository
from app.data_access.arango.nutrient_plan_repository import ArangoNutrientPlanRepository
from app.data_access.arango.oidc_config_repository import ArangoOidcConfigRepository
from app.data_access.arango.overwintering_profile_repository import ArangoOverwinteringProfileRepository
from app.data_access.arango.overwintering_profile_template_repository import (
    ArangoOverwinteringProfileTemplateRepository,
)
from app.data_access.arango.plant_instance_repository import ArangoPlantInstanceRepository
from app.data_access.arango.planting_run_repository import ArangoPlantingRunRepository
from app.data_access.arango.post_harvest_repository import ArangoPostHarvestRepository
from app.data_access.arango.refresh_token_repository import ArangoRefreshTokenRepository
from app.data_access.arango.site_repository import ArangoSiteRepository
from app.data_access.arango.species_repository import ArangoSpeciesRepository
from app.data_access.arango.substrate_repository import ArangoSubstrateRepository
from app.data_access.arango.succession_plan_repository import ArangoSuccessionPlanRepository
from app.data_access.arango.tank_repository import ArangoTankRepository
from app.data_access.arango.task_repository import ArangoTaskRepository
from app.data_access.arango.tenant_repository import ArangoTenantRepository
from app.data_access.arango.user_repository import ArangoUserRepository
from app.data_access.arango.watering_log_repository import ArangoWateringLogRepository
from app.data_access.arango.watering_repository import ArangoWateringRepository
from app.data_access.external.console_email_adapter import ConsoleEmailAdapter
from app.data_access.external.smtp_email_adapter import SmtpEmailAdapter
from app.data_access.repositories.propagation_repository import PropagationRepository
from app.domain.engines.care_reminder_engine import CareReminderEngine
from app.domain.engines.companion_planting_engine import CompanionPlantingEngine
from app.domain.engines.crop_rotation_validator import CropRotationValidator
from app.domain.engines.dependency_resolver import DependencyResolver
from app.domain.engines.enrichment_engine import EnrichmentEngine
from app.domain.engines.hst_validator import HSTValidator
from app.domain.engines.inspection_scheduler import InspectionScheduler
from app.domain.engines.invitation_engine import InvitationEngine
from app.domain.engines.lineage_engine import LineageEngine
from app.domain.engines.login_throttle_engine import LoginThrottleEngine
from app.domain.engines.membership_engine import MembershipEngine
from app.domain.engines.nutrient_plan_engine import NutrientPlanValidator
from app.domain.engines.password_engine import PasswordEngine
from app.domain.engines.phase_transition_engine import PhaseTransitionEngine
from app.domain.engines.planting_run_engine import PlantingRunEngine
from app.domain.engines.quality_scoring_engine import QualityScoringEngine
from app.domain.engines.readiness_engine import ReadinessEngine
from app.domain.engines.recurrence_engine import RecurrenceEngine
from app.domain.engines.resistance_engine import ResistanceManager
from app.domain.engines.safety_interval_engine import SafetyIntervalValidator
from app.domain.engines.tank_engine import TankEngine
from app.domain.engines.tenant_engine import TenantEngine
from app.domain.engines.token_engine import TokenEngine
from app.domain.engines.watering_engine import WateringEngine
from app.domain.interfaces.device_pairing_store import IDevicePairingCodeStore
from app.domain.interfaces.device_pairing_throttle import IDevicePairingThrottleStore
from app.domain.interfaces.email_service import IEmailService
from app.domain.interfaces.object_storage_adapter import IObjectStorageAdapter
from app.domain.services.auth_service import AuthService
from app.domain.services.care_reminder_service import CareReminderService
from app.domain.services.enrichment_service import EnrichmentService
from app.domain.services.feeding_service import FeedingService
from app.domain.services.fertilizer_service import FertilizerService
from app.domain.services.harvest_service import HarvestService
from app.domain.services.ipm_service import IpmService
from app.domain.services.nutrient_plan_service import NutrientPlanService
from app.domain.services.overwintering_profile_service import OverwinteringProfileService
from app.domain.services.phase_service import PhaseService
from app.domain.services.plant_instance_service import PlantInstanceService
from app.domain.services.planting_run_service import PlantingRunService
from app.domain.services.post_harvest_service import PostHarvestService
from app.domain.services.propagation_service import PropagationService
from app.domain.services.site_service import SiteService
from app.domain.services.species_service import SpeciesService
from app.domain.services.substrate_service import SubstrateService
from app.domain.services.succession_plan_service import SuccessionPlanService
from app.domain.services.tank_service import TankService
from app.domain.services.task_service import TaskService
from app.domain.services.tenant_service import TenantService
from app.domain.services.user_service import UserService
from app.domain.services.watering_log_service import WateringLogService
from app.domain.services.watering_service import WateringService

_connection: ArangoConnection | None = None
_timescale_connection = None
_object_storage = None


def get_connection() -> ArangoConnection:
    global _connection
    if _connection is None:
        _connection = ArangoConnection(settings)
    return _connection


def get_timescale_connection():
    from app.data_access.timescale.connection import TimescaleConnection

    global _timescale_connection
    if not settings.timescaledb_enabled:
        return None
    if _timescale_connection is None:
        _timescale_connection = TimescaleConnection(settings)
    return _timescale_connection


def get_db() -> StandardDatabase:
    return get_connection().db


def get_aquaponik_repo():
    """REQ-026 aquaponics repository (systems + fish/water child collections)."""
    from app.data_access.arango.aquaponik_repository import ArangoAquaponikRepository

    return ArangoAquaponikRepository(get_db())


def get_aquaponik_service():
    """REQ-026 aquaponics service with its domain engines."""
    from app.domain.services.aquaponik_service import AquaponikService

    return AquaponikService(get_aquaponik_repo())


def get_actuator_repo():
    """REQ-018 environment-control repository (actuators + child collections)."""
    from app.data_access.arango.actuator_repository import ArangoActuatorRepository

    return ArangoActuatorRepository(get_db())


def get_actuator_service():
    """REQ-018 environment-control service with control engine + HA graceful degradation."""
    from app.domain.services.actuator_service import ActuatorService

    return ActuatorService(
        get_actuator_repo(),
        ha_client_factory=get_ha_client,
        task_repo=get_task_repo(),
    )


def get_inventree_repo():
    """REQ-016 InvenTree integration repository (connections/refs/txns/equipment)."""
    from app.data_access.arango.inventree_repository import ArangoInvenTreeRepository

    return ArangoInvenTreeRepository(get_db())


def get_inventree_service():
    """REQ-016 InvenTree integration service (Fernet-encrypted token, SSRF-guarded)."""
    from app.domain.services.inventree_service import InvenTreeService

    return InvenTreeService(get_inventree_repo(), get_encryption_engine(), redis_client=_get_redis_client())


def get_species_repo() -> ArangoSpeciesRepository:
    return ArangoSpeciesRepository(get_db())


def get_family_repo() -> ArangoBotanicalFamilyRepository:
    return ArangoBotanicalFamilyRepository(get_db())


def get_lifecycle_repo() -> ArangoLifecycleRepository:
    return ArangoLifecycleRepository(get_db())


def get_site_repo() -> ArangoSiteRepository:
    return ArangoSiteRepository(get_db())


def get_substrate_repo() -> ArangoSubstrateRepository:
    return ArangoSubstrateRepository(get_db())


def get_plant_repo() -> ArangoPlantInstanceRepository:
    return ArangoPlantInstanceRepository(get_db())


def get_graph_repo() -> ArangoGraphRepository:
    return ArangoGraphRepository(get_db())


def get_phase_sequence_binder():
    """Construct the species → phase-sequence binder (#1006).

    Imported lazily for the same reason ``get_phase_sequence_repo`` is defined lazily
    below: the repository module is not loaded at import time of this module.
    """
    from app.domain.services.phase_sequence_binder import PhaseSequenceBinder

    return PhaseSequenceBinder(get_phase_sequence_repo(), get_lifecycle_repo())


def get_species_service() -> SpeciesService:
    return SpeciesService(get_species_repo(), get_graph_repo(), get_phase_sequence_binder())


def get_site_service() -> SiteService:
    return SiteService(get_site_repo())


def get_substrate_service() -> SubstrateService:
    return SubstrateService(get_substrate_repo())


def get_propagation_repo() -> PropagationRepository:
    """REQ-017 propagation repository (events / batches / protocols / phenotypes / lineage)."""
    return PropagationRepository(get_db())


def get_lineage_engine() -> LineageEngine:
    """REQ-017 lineage engine — graph traversal + graft compatibility."""
    return LineageEngine(get_propagation_repo(), get_species_repo())


def get_propagation_service() -> PropagationService:
    """REQ-017 propagation service.

    Wires the full propagation surface (events / batches / protocols / mothers /
    phenotypes / lineage / stats). The D10 clone path (``record``) keeps working
    against the same tenant-scoped ``propagation_events`` collection.
    """
    prop_repo = get_propagation_repo()
    return PropagationService(
        propagation_repo=prop_repo,
        lineage_engine=LineageEngine(prop_repo, get_species_repo()),
        planting_run_repo=get_planting_run_repo(),
    )


def get_plant_instance_service() -> PlantInstanceService:
    rotation_validator = CropRotationValidator(get_plant_repo(), get_species_repo(), get_graph_repo())
    companion_engine = CompanionPlantingEngine(get_graph_repo(), get_plant_repo(), get_species_repo())
    return PlantInstanceService(
        get_plant_repo(),
        get_site_repo(),
        rotation_validator,
        companion_engine,
        phase_repo=get_lifecycle_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
        task_repo=get_task_repo(),
        species_repo=get_species_repo(),
        planting_run_repo=get_planting_run_repo(),
        photo_cleanup=_cascade_plant_photo_cleanup,
        propagation_service=get_propagation_service(),
        overwintering_materializer=get_overwintering_materializer(),
        overwintering_service=get_overwintering_profile_service(),
        # #1335 — the resolvers for the caller-supplied catalogue references a plant
        # carries (substrate / batch / species). Both are optional on the service so
        # it stays constructible in pure-domain contexts; they are NOT optional in
        # production, and an absence check reads this call to keep it that way.
        substrate_service=get_substrate_service(),
        species_service=get_species_service(),
    )


def _cascade_plant_photo_cleanup(plant) -> None:  # type: ignore[no-untyped-def]
    """REQ-034 §2.1 / AC-08 — bridge the async gallery cascade into the sync
    plant-instance removal path (run on an isolated loop, see ``run_async``)."""
    from app.common.async_bridge import run_async

    service = get_plant_photo_service()
    run_async(service.delete_all_photos(plant, plant.tenant_key))


def get_plant_photo_service():
    """REQ-034 §2.1 / §4a — plant-instance photo gallery service."""
    from app.domain.services.plant_photo_service import PlantPhotoService

    return PlantPhotoService(
        plant_repo=get_plant_repo(),
        attachment_repo=get_attachment_repo(),
        attachment_service=get_attachment_service(),
        settings=settings,
        identification_service=get_identification_service(),
        species_repo=get_species_repo(),
    )


def get_phase_service() -> PhaseService:
    service = PhaseService(get_lifecycle_repo(), get_plant_repo(), phase_seq_repo=get_phase_sequence_repo())
    # REQ-006: Activate dormant tasks when a plant transitions to a new phase
    task_service = get_task_service()
    service.register_on_transition(task_service.activate_dormant_tasks_for_phase)
    # REQ-003 D10 / REQ-017: when a monocarpic mother enters its terminal
    # reproductive phase, spawn one clonal pup (new instance + descended_from
    # edge) instead of a cycle restart. The callback is a no-op for every other
    # transition (non-monocarpic, non-terminal, or an already-continued mother).
    plant_service = get_plant_instance_service()
    service.register_on_transition(plant_service.handle_monocarpic_terminal_transition)
    return service


def get_source_repo() -> ArangoExternalSourceRepository:
    return ArangoExternalSourceRepository(get_db())


def get_mapping_repo() -> ArangoExternalMappingRepository:
    return ArangoExternalMappingRepository(get_db())


def get_sync_run_repo() -> ArangoSyncRunRepository:
    return ArangoSyncRunRepository(get_db())


def get_enrichment_engine() -> EnrichmentEngine:
    return EnrichmentEngine(get_species_repo(), get_mapping_repo(), get_sync_run_repo(), get_family_repo())


def get_enrichment_service() -> EnrichmentService:
    return EnrichmentService(get_source_repo(), get_mapping_repo(), get_sync_run_repo(), get_enrichment_engine())


def get_planting_run_repo() -> ArangoPlantingRunRepository:
    return ArangoPlantingRunRepository(get_db())


def get_plant_diary_repo():
    from app.data_access.arango.plant_diary_repository import ArangoPlantDiaryRepository

    return ArangoPlantDiaryRepository(get_db())


def get_diary_analysis_consent_checker():
    """REQ-050 §7.1 — the real probe for the ``diary_ai_analysis`` purpose.

    Reads the REQ-025 consent store through :class:`ConsentGuard`, so a purpose
    that was never granted, or one whose record was revoked (``granted=False``),
    both answer ``False``. A revocation therefore blocks *new* markings while
    every stored analysis result stays exactly where it is — nothing on this path
    writes to an entry.

    **Light mode is deliberately not special-cased here.** §7.5 ("the purpose
    counts as granted") is one rule and lives in
    ``evaluate_analysis_request_permission``; repeating it in the probe would be
    a second place to forget. The probe stays a plain question to the consent
    store and honestly answers ``False`` on a Light instance, where nobody can
    grant anything.

    The answer is memoised per checker instance. The provider below is a
    per-request FastAPI dependency, and the tenant-wide diary overview evaluates
    the permission once per row (``can_request_analysis``) — without the cache
    that would be one consent query per listed entry.
    """
    from app.domain.engines.consent_engine import DIARY_AI_ANALYSIS
    from app.domain.guards.consent_guard import ConsentGuard

    guard = ConsentGuard(get_consent_repo())
    answers: dict[str, bool] = {}

    def _consent_granted(user_key: str) -> bool:
        if user_key not in answers:
            answers[user_key] = guard.has_consent(user_key, DIARY_AI_ANALYSIS)
        return answers[user_key]

    return _consent_granted


def get_environment_snapshot_service():
    """REQ-013 §2.3a — resolves a plant's live environment for a diary entry.

    Every optional collaborator is passed even though the chain tolerates their
    absence: an installation without TimescaleDB or without weather sources still
    produces an honest (shorter) chain, and wiring them all here means the chain
    degrades because a *source* is missing, never because the wiring forgot one.

    **Call this only when a snapshot is actually wanted.** The body opens six
    repositories plus a Home Assistant client, so it is a real database round
    trip — see the ``environment_service_factory`` note in
    :func:`get_plant_diary_service`.
    """
    from app.domain.services.environment_snapshot_service import EnvironmentSnapshotService

    return EnvironmentSnapshotService(
        plant_repo=get_plant_repo(),
        sensor_repo=get_sensor_repo(),
        sensor_service=get_sensor_service(),
        observation_repo=get_observation_repo(),
        weather_forecast_repo=get_weather_forecast_repo(),
        site_repo=get_site_repo(),
    )


def get_plant_diary_service():
    from app.domain.services.plant_diary_service import PlantDiaryService

    return PlantDiaryService(
        diary_repo=get_plant_diary_repo(),
        run_repo=get_planting_run_repo(),
        plant_repo=get_plant_repo(),
        # REQ-013 §2.3a — the environment snapshot taken on create. Passed as a
        # **factory**, deliberately un-called: building it opens six repositories
        # and a Home Assistant client, none of which the diary service needs in
        # order to exist. Calling it here made every construction of this service
        # a database round trip and broke a consent-wiring unit test that touches
        # no environment at all. Same shape as ``ha_client_factory`` on
        # ``ActuatorService``.
        #
        # Absent — or answering ``None`` — an entry is stored with
        # ``environment_status: not_attempted``, which says exactly that and is
        # not mistakable for "we looked and found nothing".
        environment_service_factory=get_environment_snapshot_service,
        # REQ-050 §7.1 — replaces the ``_consent_not_evaluated`` placeholder.
        # Both the enforcement (``request_analysis``) and the display flag
        # (``can_request_analysis``) go through
        # ``evaluate_request_permission``, so this single injection covers both.
        consent_checker=get_diary_analysis_consent_checker(),
        # SEC-003 — resolves ``photo_refs`` so tenant, category and uploader of
        # every referenced attachment are checked before an entry is stored.
        # Without it the service refuses *any* photo reference rather than
        # accepting it unchecked.
        attachment_repo=get_attachment_repo(),
    )


def get_planting_run_service() -> PlantingRunService:
    from app.domain.engines.watering_schedule_engine import WateringScheduleEngine

    rotation_validator = CropRotationValidator(get_plant_repo(), get_species_repo(), get_graph_repo())
    companion_engine = CompanionPlantingEngine(get_graph_repo(), get_plant_repo(), get_species_repo())
    return PlantingRunService(
        get_planting_run_repo(),
        get_plant_repo(),
        PlantingRunEngine(),
        watering_schedule_engine=WateringScheduleEngine(),
        nutrient_plan_repo=get_nutrient_plan_repo(),
        watering_repo=get_watering_repo(),
        phase_repo=get_lifecycle_repo(),
        site_repo=get_site_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
        rotation_validator=rotation_validator,
        companion_engine=companion_engine,
    )


def get_succession_plan_repo() -> ArangoSuccessionPlanRepository:
    return ArangoSuccessionPlanRepository(get_db())


def get_succession_plan_service() -> SuccessionPlanService:
    return SuccessionPlanService(
        get_succession_plan_repo(),
        get_planting_run_service(),
        site_repo=get_site_repo(),
    )


def get_tank_repo() -> ArangoTankRepository:
    return ArangoTankRepository(get_db())


def get_tank_service() -> TankService:
    return TankService(get_tank_repo(), TankEngine())


def get_task_entity_guard():
    """Guard that anchors a task's entity binding in the caller's tenant (#1102).

    Bundles the four services behind one dependency rather than putting four more
    ``Depends`` on the task-create route: they are needed together or not at all,
    and the route already carries five parameters.
    """
    from app.domain.services.task_entity_guard import TaskEntityGuard

    # Factories, not instances: the guard calls one only when a binding actually
    # needs resolving, so an unbound create opens no database handle at all.
    return TaskEntityGuard(
        get_plant_instance_service,
        get_planting_run_service,
        get_tank_service,
        get_site_service,
    )


def get_fertilizer_repo() -> ArangoFertilizerRepository:
    return ArangoFertilizerRepository(get_db())


def get_nutrient_plan_repo() -> ArangoNutrientPlanRepository:
    return ArangoNutrientPlanRepository(get_db())


def get_feeding_repo() -> ArangoFeedingRepository:
    return ArangoFeedingRepository(get_db())


def get_fertilizer_service() -> FertilizerService:
    return FertilizerService(get_fertilizer_repo(), site_repo=get_site_repo())


def get_nutrient_plan_service() -> NutrientPlanService:
    return NutrientPlanService(
        get_nutrient_plan_repo(),
        get_fertilizer_repo(),
        NutrientPlanValidator(),
        site_repo=get_site_repo(),
    )


def get_feeding_service() -> FeedingService:
    return FeedingService(get_feeding_repo())


def get_watering_repo() -> ArangoWateringRepository:
    return ArangoWateringRepository(get_db())


def get_watering_service() -> WateringService:
    return WateringService(
        get_watering_repo(),
        WateringEngine(),
        get_site_repo(),
        run_repo=get_planting_run_repo(),
        task_repo=get_task_repo(),
        feeding_repo=get_feeding_repo(),
        nutrient_plan_repo=get_nutrient_plan_repo(),
        care_repo=get_care_reminder_repo(),
        plant_repo=get_plant_repo(),
        species_repo=get_species_repo(),
        substrate_repo=get_substrate_repo(),
        lifecycle_repo=get_lifecycle_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
        sensor_service=get_sensor_service(),
        irrigation_demand_repo=get_irrigation_demand_repo(),
    )


def get_watering_log_repo() -> ArangoWateringLogRepository:
    return ArangoWateringLogRepository(get_db())


def get_watering_log_service() -> WateringLogService:
    return WateringLogService(
        get_watering_log_repo(),
        WateringEngine(),
        get_site_repo(),
        run_repo=get_planting_run_repo(),
        task_repo=get_task_repo(),
        nutrient_plan_repo=get_nutrient_plan_repo(),
        care_repo=get_care_reminder_repo(),
        care_service=get_care_reminder_service(),
        plant_repo=get_plant_repo(),
    )


def get_ipm_repo() -> ArangoIpmRepository:
    return ArangoIpmRepository(get_db())


def get_ipm_service() -> IpmService:
    return IpmService(
        get_ipm_repo(),
        SafetyIntervalValidator(),
        ResistanceManager(),
        InspectionScheduler(),
    )


def get_pest_image_repo():
    from app.data_access.arango.pest_image_repository import ArangoPestImageRepository

    return ArangoPestImageRepository(get_db())


def get_pest_image_service():
    from app.domain.services.pest_image_service import PestImageService

    return PestImageService(
        repo=get_pest_image_repo(),
        attachment_service=get_attachment_service(),
        ipm_service=get_ipm_service(),
        inference_client=get_pest_inference_client(),
    )


def get_harvest_repo() -> ArangoHarvestRepository:
    return ArangoHarvestRepository(get_db())


def get_phase_transition_engine() -> PhaseTransitionEngine:
    return PhaseTransitionEngine(
        get_lifecycle_repo(),
        get_plant_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
    )


def get_harvest_service() -> HarvestService:
    return HarvestService(
        get_harvest_repo(),
        get_ipm_service(),
        ReadinessEngine(),
        QualityScoringEngine(),
        plant_repo=get_plant_repo(),
        run_repo=get_planting_run_repo(),
        phase_engine=get_phase_transition_engine(),
    )


def get_post_harvest_repo() -> ArangoPostHarvestRepository:
    return ArangoPostHarvestRepository(get_db())


def get_post_harvest_service() -> PostHarvestService:
    return PostHarvestService(
        get_post_harvest_repo(),
        harvest_repo=get_harvest_repo(),
    )


def get_task_repo() -> ArangoTaskRepository:
    return ArangoTaskRepository(get_db())


def get_recurrence_engine() -> RecurrenceEngine:
    return RecurrenceEngine()


def get_notification_propagation_service():
    """REQ-030 §4.2 in-app source→notification coupling (Issue #742).

    Repository-only, synchronous: the coupling maintains persisted notification
    rows for the in-app centre. Channel delivery stays on the async engine path.
    """
    from app.domain.services.notification_propagation_service import (
        NotificationPropagationService,
    )

    return NotificationPropagationService(get_notification_repo())


def get_task_service() -> TaskService:
    return TaskService(
        get_task_repo(),
        HSTValidator(),
        DependencyResolver(),
        recurrence=get_recurrence_engine(),
        notification_propagation=get_notification_propagation_service(),
    )


# ── REQ-023 Auth dependencies ───────────────────────────────────────


def get_user_repo() -> ArangoUserRepository:
    return ArangoUserRepository(get_db())


def get_auth_provider_repo() -> ArangoAuthProviderRepository:
    return ArangoAuthProviderRepository(get_db())


def get_refresh_token_repo() -> ArangoRefreshTokenRepository:
    return ArangoRefreshTokenRepository(get_db())


def get_oidc_config_repo() -> ArangoOidcConfigRepository:
    return ArangoOidcConfigRepository(get_db())


def get_token_engine() -> TokenEngine:
    return TokenEngine(settings.jwt_secret_key, settings.jwt_algorithm)


def get_password_engine() -> PasswordEngine:
    return PasswordEngine()


def get_email_service() -> IEmailService:
    if settings.email_adapter == "smtp":
        return SmtpEmailAdapter(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_email=settings.smtp_from_email,
            use_tls=settings.smtp_use_tls,
        )
    return ConsoleEmailAdapter()


def get_oauth_engine():
    from app.domain.engines.oauth_engine import OAuthEngine

    return OAuthEngine()


def get_encryption_engine():
    from app.domain.engines.encryption_engine import EncryptionEngine

    return EncryptionEngine(settings.fernet_key)


def get_oauth_state_store():
    from app.data_access.external.redis_oauth_state import RedisOAuthStateStore

    return RedisOAuthStateStore(settings.redis_url)


def get_unknown_account_store():
    """SEC-H-010 lockout counter for addresses that have no account.

    Redis-backed so replicas share one counter; degrades to the process-wide
    in-memory tier when Redis is unreachable (see the store's module docstring —
    failing open here would reopen the enumeration oracle, not just skip a
    rate limit).
    """
    from app.data_access.external.unknown_account_store import RedisUnknownAccountStore

    return RedisUnknownAccountStore(_get_redis_client())


def get_device_pairing_code_store() -> IDevicePairingCodeStore:
    """REQ-023 / #1118 one-time custody of QR pairing codes.

    Redis-only, with **no** in-process fallback: this store hands out
    credentials rather than counting against a caller, and a per-replica
    fallback would make a code redeemable only on the replica that minted it.
    See the store's module docstring for the asymmetry between ``issue``
    (fails loud) and ``consume`` (fails closed).
    """
    from app.data_access.external.redis_device_pairing import RedisDevicePairingCodeStore

    return RedisDevicePairingCodeStore(
        _get_redis_client(),
        ttl_seconds=settings.device_pairing_ttl_seconds,
    )


def get_device_pairing_throttle_store() -> IDevicePairingThrottleStore:
    """#1118 lockout counter for failed pairing redemptions, per source IP.

    Redis-backed so replicas share one counter; degrades to the process-wide
    in-memory tier when Redis is unreachable. Failing open here would reopen
    unbounded guessing against an unauthenticated endpoint that mints sessions,
    which the route's per-minute rate limit bounds but never stops.
    """
    from app.data_access.external.device_pairing_throttle import RedisDevicePairingThrottleStore

    return RedisDevicePairingThrottleStore(_get_redis_client())


def get_registration_notice_store():
    """REQ-023 §3.2 suppression window of the duplicate-registration notice.

    Redis-backed so all workers share one window per recipient; degrades to the
    process-wide in-memory tier when Redis is unreachable. Consumed by the
    Celery task, never by the request path — see
    ``app.tasks.auth_tasks.send_duplicate_registration_notice``.
    """
    from app.data_access.external.registration_notice_store import RedisRegistrationNoticeStore

    return RedisRegistrationNoticeStore(_get_redis_client())


def get_api_key_repo():
    from app.data_access.arango.api_key_repository import ArangoApiKeyRepository

    return ArangoApiKeyRepository(get_db())


def get_auth_provider():
    if settings.kamerplanter_mode == "light":
        from app.domain.engines.light_auth_provider import LightAuthProvider

        return LightAuthProvider(get_user_repo())
    from app.domain.engines.full_auth_provider import FullAuthProvider

    return FullAuthProvider(get_token_engine(), get_user_repo(), get_auth_service())


def get_auth_service() -> AuthService:
    return AuthService(
        user_repo=get_user_repo(),
        auth_provider_repo=get_auth_provider_repo(),
        refresh_token_repo=get_refresh_token_repo(),
        password_engine=get_password_engine(),
        token_engine=get_token_engine(),
        throttle_engine=LoginThrottleEngine(),
        email_service=get_email_service(),
        frontend_url=settings.frontend_url,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
        session_token_expire_hours=settings.session_token_expire_hours,
        tenant_service=get_tenant_service(),
        require_email_verification=settings.require_email_verification,
        oauth_engine=get_oauth_engine(),
        oauth_state_store=get_oauth_state_store(),
        api_key_repo=get_api_key_repo(),
        oidc_config_repo=get_oidc_config_repo(),
        encryption_engine=get_encryption_engine(),
        unknown_account_store=get_unknown_account_store(),
        # #1118 — wired here rather than left to the router, so the capability
        # and its guard travel together: an ``AuthService`` built without the
        # throttle store would still redeem codes, only without a lockout.
        device_pairing_code_store=get_device_pairing_code_store(),
        device_pairing_throttle_store=get_device_pairing_throttle_store(),
    )


def get_user_service() -> UserService:
    return UserService(get_user_repo(), get_refresh_token_repo(), get_membership_repo())


# ── REQ-024 Tenant dependencies ──────────────────────────────────────


def get_tenant_repo() -> ArangoTenantRepository:
    return ArangoTenantRepository(get_db())


def get_membership_repo() -> ArangoMembershipRepository:
    return ArangoMembershipRepository(get_db())


def get_invitation_repo() -> ArangoInvitationRepository:
    return ArangoInvitationRepository(get_db())


def get_assignment_repo() -> ArangoLocationAssignmentRepository:
    return ArangoLocationAssignmentRepository(get_db())


def get_tenant_service() -> TenantService:
    return TenantService(
        tenant_repo=get_tenant_repo(),
        membership_repo=get_membership_repo(),
        invitation_repo=get_invitation_repo(),
        assignment_repo=get_assignment_repo(),
        tenant_engine=TenantEngine(),
        membership_engine=MembershipEngine(),
        invitation_engine=InvitationEngine(),
        storage_adapter=get_object_storage(),
        attachment_repo=get_attachment_repo(),
        reference_index_store=get_reference_index_store(),
        pest_image_repo=get_pest_image_repo(),
        ipm_repo=get_ipm_repo(),
        pest_inference_client=get_pest_inference_client(),
    )


# ── REQ-033 MCP server dependencies ────────────────────────────────


def get_mcp_audit_repo():
    from app.data_access.arango.mcp_repository import ArangoMcpAuditRepository

    return ArangoMcpAuditRepository(get_db())


def get_mcp_idempotency_repo():
    from app.data_access.arango.mcp_repository import ArangoMcpIdempotencyRepository

    return ArangoMcpIdempotencyRepository(get_db())


def get_mcp_authenticator():
    from app.mcp_server.auth import McpAuthenticator
    from app.mcp_server.rate_limit import McpRateLimiter

    return McpAuthenticator(
        get_api_key_repo(),
        get_user_repo(),
        get_tenant_service(),
        rate_limiter=McpRateLimiter(_get_redis_client()),
    )


def get_mcp_session_store():
    """Streamable-HTTP session store for the MCP transport (REQ-033 §4.3a)."""
    from app.mcp_server.session import McpSessionStore

    return McpSessionStore(_get_redis_client())


def get_mcp_dispatcher():
    from app.mcp_server.audit import MCPAuditLogger
    from app.mcp_server.dispatcher import ToolDispatcher
    from app.mcp_server.idempotency import IdempotencyStore
    from app.mcp_server.registry import load_tools

    registry = load_tools()
    audit_logger = MCPAuditLogger(get_mcp_audit_repo())
    idempotency = IdempotencyStore(
        get_mcp_idempotency_repo(),
        ttl_hours=settings.mcp_idempotency_ttl_hours,
    )
    return ToolDispatcher(registry, audit_logger, idempotency)


# ── REQ-022 Care Reminder dependencies ─────────────────────────────


# ── REQ-020 Onboarding dependencies ────────────────────────────────


def get_favorites_service():
    from app.domain.services.favorites_service import FavoritesService

    return FavoritesService(get_db())


def get_starter_kit_service():
    from app.domain.services.starter_kit_service import StarterKitService

    return StarterKitService(get_db())


def get_onboarding_service():
    from app.domain.services.onboarding_service import OnboardingService

    return OnboardingService(get_db(), get_starter_kit_service())


def get_user_preference_service():
    from app.domain.services.user_preference_service import UserPreferenceService

    return UserPreferenceService(get_db())


def get_care_reminder_repo() -> ArangoCareReminderRepository:
    return ArangoCareReminderRepository(get_db())


def get_overwintering_profile_repo() -> ArangoOverwinteringProfileRepository:
    return ArangoOverwinteringProfileRepository(get_db())


def get_overwintering_template_repo() -> ArangoOverwinteringProfileTemplateRepository:
    return ArangoOverwinteringProfileTemplateRepository(get_db())


def get_overwintering_profile_service() -> OverwinteringProfileService:
    return OverwinteringProfileService(
        get_overwintering_profile_repo(),
        site_repo=get_site_repo(),
        plant_repo=get_plant_repo(),
        planting_run_repo=get_planting_run_repo(),
        template_repo=get_overwintering_template_repo(),
        species_repo=get_species_repo(),
    )


def get_care_reminder_service() -> CareReminderService:
    return CareReminderService(
        get_care_reminder_repo(),
        CareReminderEngine(),
        get_task_repo(),
        watering_log_repo=get_watering_log_repo(),
        plant_repo=get_plant_repo(),
        lifecycle_repo=get_lifecycle_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
        species_repo=get_species_repo(),
        nutrient_plan_repo=get_nutrient_plan_repo(),
        overwintering_repo=get_overwintering_profile_repo(),
        overwintering_template_repo=get_overwintering_template_repo(),
        recurrence=get_recurrence_engine(),
        notification_propagation=get_notification_propagation_service(),
    )


# ── REQ-047 Season & overwintering automation dependencies ─────────


def get_season_state_repo():
    from app.data_access.arango.season_state_repository import ArangoSeasonStateRepository

    return ArangoSeasonStateRepository(get_db())


def get_season_signal_resolver():
    from app.domain.services.season_signal_resolver import SeasonSignalResolver

    return SeasonSignalResolver(get_weather_forecast_repo(), get_climate_normal_repo())


def get_overwintering_materializer():
    from app.domain.services.overwintering_materializer import OverwinteringMaterializer

    return OverwinteringMaterializer(
        get_overwintering_profile_service(),
        get_overwintering_profile_repo(),
        get_species_repo(),
        template_repo=get_overwintering_template_repo(),
    )


def get_season_state_service():
    from app.domain.engines.season_state_engine import SeasonStateEngine
    from app.domain.services.dormancy_care_activator import DormancyCareActivator
    from app.domain.services.season_phase_coupler import SeasonPhaseCoupler
    from app.domain.services.season_state_service import SeasonStateService

    return SeasonStateService(
        get_season_state_repo(),
        get_season_signal_resolver(),
        SeasonStateEngine(),
        get_overwintering_materializer(),
        DormancyCareActivator(get_care_reminder_repo()),
        get_care_reminder_service(),
        get_overwintering_profile_repo(),
        get_plant_repo(),
        get_site_repo(),
        # ADR-006 E3 — season ↔ growth-phase coupling (REQ-047 ↔ REQ-003).
        SeasonPhaseCoupler(get_phase_service(), get_lifecycle_repo(), get_phase_sequence_repo()),
    )


def get_quarter_climate_service():
    """REQ-047 §3.7.3 / AC-22 — winter-quarter climate warning service."""
    from app.domain.services.quarter_climate_service import QuarterClimateService

    return QuarterClimateService(
        get_overwintering_profile_repo(),
        get_care_reminder_repo(),
        get_sensor_repo(),
        get_observation_repo(),
        get_plant_repo(),
        get_task_repo(),
    )


# ── Phase Sequence dependencies ────────────────────────────────────


def get_phase_sequence_repo():
    from app.data_access.arango.phase_sequence_repository import ArangoPhaseSequenceRepository

    return ArangoPhaseSequenceRepository(get_db())


def get_phase_sequence_service():
    from app.domain.services.phase_sequence_service import PhaseSequenceService

    return PhaseSequenceService(get_phase_sequence_repo())


# ── REQ-032 Print dependencies ──────────────────────────────────────


def get_print_service():
    from app.domain.services.print_service import PrintService

    return PrintService(
        nutrient_plan_service=get_nutrient_plan_service(),
        care_reminder_service=get_care_reminder_service(),
        fertilizer_repo=get_fertilizer_repo(),
        plant_repo=get_plant_repo(),
        species_repo=get_species_repo(),
        site_repo=get_site_repo(),
        app_base_url=settings.app_base_url,
    )


# ── REQ-012 Import dependencies ──────────────────────────────────────


def get_import_job_repo():
    from app.data_access.arango.import_job_repository import ArangoImportJobRepository

    return ArangoImportJobRepository(get_db())


def get_import_service():
    from app.domain.services.import_service import ImportService

    return ImportService(
        get_import_job_repo(),
        get_species_repo(),
        get_family_repo(),
        get_phase_sequence_binder(),
    )


# ── REQ-015 Calendar dependencies ───────────────────────────────────


def get_calendar_feed_repo():
    from app.data_access.arango.calendar_feed_repository import ArangoCalendarFeedRepository

    return ArangoCalendarFeedRepository(get_db())


def get_calendar_aggregation_engine():
    from app.domain.engines.calendar_aggregation_engine import CalendarAggregationEngine

    return CalendarAggregationEngine(get_db())


def get_calendar_service():
    from app.domain.services.calendar_service import CalendarService

    return CalendarService(
        get_calendar_feed_repo(),
        get_calendar_aggregation_engine(),
        species_repo=get_species_repo(),
        site_repo=get_site_repo(),
        planting_run_service=get_planting_run_service(),
    )


# ── REQ-005 Sensor dependencies ───────────────────────────────────


def get_sensor_repo():
    from app.data_access.arango.sensor_repository import ArangoSensorRepository

    return ArangoSensorRepository(get_db())


# ── REQ-046 Weather data source dependencies ──────────────────────


def get_weather_forecast_repo():
    from app.data_access.arango.weather_forecast_repository import ArangoWeatherForecastRepository

    return ArangoWeatherForecastRepository(get_db())


def get_weather_source_config_repo():
    from app.data_access.arango.weather_source_config_repository import ArangoWeatherSourceConfigRepository

    return ArangoWeatherSourceConfigRepository(get_db())


def get_climate_normal_repo():
    from app.data_access.arango.climate_normal_repository import ArangoClimateNormalRepository

    return ArangoClimateNormalRepository(get_db())


def get_hardiness_zone_repo():
    from app.data_access.arango.hardiness_zone_repository import ArangoHardinessZoneRepository

    return ArangoHardinessZoneRepository(get_db())


def get_hardiness_zone_service():
    from app.domain.services.climate_normal_fetcher import ClimateNormalFetcher
    from app.domain.services.hardiness_zone_service import HardinessZoneService

    normal_repo = get_climate_normal_repo()
    return HardinessZoneService(
        zone_repo=get_hardiness_zone_repo(),
        site_repo=get_site_repo(),
        climate_normal_repo=normal_repo,
        normals_fetcher=ClimateNormalFetcher(normal_repo),
    )


def get_irrigation_demand_repo():
    from app.data_access.arango.irrigation_demand_repository import ArangoIrrigationDemandRepository

    return ArangoIrrigationDemandRepository(get_db())


def get_weather_settings_service():
    from app.domain.services.weather_settings_service import WeatherSettingsService

    return WeatherSettingsService(get_system_settings_repo(), get_encryption_engine())


def _effective_weather_settings():
    """Callable injected into the resolver / source service so both use the
    DB-backed effective provider config (base URL, timeout, enable flags, global
    OWM fallback key) instead of the raw env defaults."""
    return get_weather_settings_service().get_effective_weather_settings()


def get_weather_source_service():
    from app.domain.services.weather_source_resolver import WeatherSourceResolver
    from app.domain.services.weather_source_service import WeatherSourceService

    encryption = get_encryption_engine()
    resolver = WeatherSourceResolver(
        encryption,
        get_ha_client,
        weather_settings_provider=_effective_weather_settings,
    )
    return WeatherSourceService(
        weather_source_config_repo=get_weather_source_config_repo(),
        site_repo=get_site_repo(),
        encryption_engine=encryption,
        resolver=resolver,
        ha_client_factory=get_ha_client,
        weather_settings_provider=_effective_weather_settings,
        climate_normal_repo=get_climate_normal_repo(),
    )


def get_system_settings_repo():
    from app.data_access.arango.system_settings_repository import ArangoSystemSettingsRepository

    return ArangoSystemSettingsRepository(get_db())


def get_system_settings_service():
    from app.domain.services.system_settings_service import SystemSettingsService

    return SystemSettingsService(get_system_settings_repo())


def get_ha_publish_repo():
    from app.data_access.arango.ha_publish_repository import ArangoHaPublishRepository

    return ArangoHaPublishRepository(get_db())


def get_ha_publish_service():
    from app.domain.services.ha_publish_service import HaPublishService

    return HaPublishService(get_ha_publish_repo())


def get_ha_client():
    from app.data_access.external.ha_client import HomeAssistantClient

    try:
        svc = get_system_settings_service()
        effective = svc.get_effective_ha_settings()
    except Exception:
        # Collection may not exist yet — fall back to env
        effective = {
            "ha_url": settings.ha_url,
            "ha_access_token": settings.ha_access_token,
            "ha_timeout": settings.ha_timeout,
        }
    url = effective["ha_url"]
    if not url:
        return None
    return HomeAssistantClient(
        str(url),
        str(effective["ha_access_token"]),
        int(effective["ha_timeout"]),
        allow_private=settings.ha_allow_private_endpoint,
    )


def get_observation_repo():
    conn = get_timescale_connection()
    if conn is None:
        from app.data_access.timescale.null_observation_repository import NullObservationRepository

        return NullObservationRepository()
    from app.data_access.timescale.observation_repository import TimescaleObservationRepository

    return TimescaleObservationRepository(conn.pool)


def get_observation_service():
    from app.domain.services.observation_service import ObservationService

    return ObservationService(get_observation_repo(), get_sensor_repo())


def get_sensor_service():
    from app.domain.services.sensor_service import SensorService

    return SensorService(
        get_sensor_repo(),
        get_ha_client(),
        weather_forecast_repo=get_weather_forecast_repo(),
        site_repo=get_site_repo(),
    )


# ── REQ-002 LocationType dependencies ───────────────────────────────


def get_location_type_repo():
    from app.data_access.arango.location_type_repository import ArangoLocationTypeRepository

    return ArangoLocationTypeRepository(get_db())


def get_location_type_service():
    from app.domain.services.location_type_service import LocationTypeService

    return LocationTypeService(get_location_type_repo())


# ── Activity dependencies ──────────────────────────────────────────


def get_activity_repo():
    from app.data_access.arango.activity_repository import ArangoActivityRepository

    return ArangoActivityRepository(get_db())


def get_activity_service():
    from app.domain.services.activity_service import ActivityService

    return ActivityService(get_activity_repo())


def get_activity_plan_service():
    from app.domain.engines.activity_plan_engine import ActivityPlanEngine
    from app.domain.services.activity_plan_service import ActivityPlanService

    return ActivityPlanService(
        engine=ActivityPlanEngine(),
        activity_repo=get_activity_repo(),
        phase_repo=get_lifecycle_repo(),
        task_repo=get_task_repo(),
        planting_run_repo=get_planting_run_repo(),
        species_repo=get_species_repo(),
        family_repo=get_family_repo(),
        phase_seq_repo=get_phase_sequence_repo(),
    )


# ── REQ-030 Notification dependencies ────────────────────────────────


def get_notification_repo():
    from app.data_access.arango.notification_repository import ArangoNotificationRepository

    return ArangoNotificationRepository(get_db())


def get_notification_preference_repo():
    from app.data_access.arango.notification_preference_repository import (
        ArangoNotificationPreferenceRepository,
    )

    return ArangoNotificationPreferenceRepository(get_db())


def _get_redis_client():
    """Get a Redis client for notification dedup and caching."""
    import redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def get_notification_service():
    from app.domain.engines.notification_channel_registry import NotificationChannelRegistry
    from app.domain.engines.notification_engine import NotificationEngine
    from app.domain.services.notification_service import NotificationService

    engine = NotificationEngine(
        notification_repo=get_notification_repo(),
        preference_repo=get_notification_preference_repo(),
        channel_registry=NotificationChannelRegistry,
        redis_client=_get_redis_client(),
    )
    return NotificationService(
        engine=engine,
        notification_repo=get_notification_repo(),
        preference_repo=get_notification_preference_repo(),
    )


# ── REQ-025 Privacy dependencies ─────────────────────────────────


def get_data_export_repo():
    from app.data_access.arango.data_export_repository import (
        ArangoDataExportRepository,
    )

    return ArangoDataExportRepository(get_db())


def get_consent_repo():
    from app.data_access.arango.consent_repository import ArangoConsentRepository

    return ArangoConsentRepository(get_db())


def get_processing_restriction_repo():
    from app.data_access.arango.processing_restriction_repository import (
        ArangoProcessingRestrictionRepository,
    )

    return ArangoProcessingRestrictionRepository(get_db())


def get_erasure_repo():
    from app.data_access.arango.erasure_repository import ArangoErasureRepository

    return ArangoErasureRepository(get_db())


def get_email_change_repo():
    from app.data_access.arango.email_change_repository import (
        ArangoEmailChangeRepository,
    )

    return ArangoEmailChangeRepository(get_db())


def get_data_export_engine():
    from app.domain.engines.data_export_engine import DataExportEngine

    return DataExportEngine()


def get_erasure_engine():
    from app.domain.engines.erasure_engine import ErasureEngine

    return ErasureEngine()


def get_consent_engine():
    from app.domain.engines.consent_engine import ConsentEngine

    return ConsentEngine()


# ── REQ-029 Plant identification dependencies ────────────────────


def get_identification_repo():
    from app.data_access.arango.identification_repository import (
        ArangoIdentificationRepository,
    )

    return ArangoIdentificationRepository(get_db())


def get_identification_service():
    from app.domain.engines.consent_engine import ConsentEngine
    from app.domain.engines.identification_engine import IdentificationEngine
    from app.domain.services.identification_rate_limiter import IdentificationRateLimiter
    from app.domain.services.identification_registry import IdentificationAdapterRegistry
    from app.domain.services.identification_service import IdentificationService

    identification_repo = get_identification_repo()
    engine = IdentificationEngine(
        species_repo=get_species_repo(),
        identification_repo=identification_repo,
    )
    return IdentificationService(
        engine=engine,
        identification_repo=identification_repo,
        consent_repo=get_consent_repo(),
        consent_engine=ConsentEngine(),
        rate_limiter=IdentificationRateLimiter(_get_redis_client()),
        registry=IdentificationAdapterRegistry,
        # #630 — needed to tenant-verify the plant instance a result is linked to.
        plant_instance_repo=get_plant_repo(),
    )


# ── REQ-044 Pest detection dependencies ─────────────────────────


def get_pest_detection_repo():
    from app.data_access.arango.pest_detection_repository import (
        ArangoPestDetectionRepository,
    )

    return ArangoPestDetectionRepository(get_db())


def get_pest_detection_service():
    from app.domain.engines.consent_engine import ConsentEngine
    from app.domain.engines.pest_detection_engine import PestDetectionEngine
    from app.domain.services.pest_detection_registry import PestDetectionAdapterRegistry
    from app.domain.services.pest_detection_service import PestDetectionService

    repo = get_pest_detection_repo()
    engine = PestDetectionEngine(ipm_repo=get_ipm_repo(), pest_detection_repo=repo)
    return PestDetectionService(
        engine=engine,
        repo=repo,
        ipm_service=get_ipm_service(),
        consent_repo=get_consent_repo(),
        consent_engine=ConsentEngine(),
        registry=PestDetectionAdapterRegistry,
    )


# ── REQ-038 CV disease diagnosis dependencies ───────────────────


def get_plant_diagnosis_repo():
    from app.data_access.arango.plant_diagnosis_repository import (
        ArangoPlantDiagnosisRepository,
    )

    return ArangoPlantDiagnosisRepository(get_db())


def get_cv_diagnosis_service():
    from app.domain.engines.consent_engine import ConsentEngine
    from app.domain.engines.cv_diagnosis_engine import CvDiagnosisEngine
    from app.domain.services.cv_diagnosis_service import CvDiagnosisService
    from app.domain.services.ipm_diagnosis_matcher import IpmDiagnosisMatcher

    matcher = IpmDiagnosisMatcher(get_ipm_repo())
    engine = CvDiagnosisEngine(
        matcher,
        confidence_show=settings.cv_classifier_confidence_show,
        confidence_highlight=settings.cv_classifier_confidence_highlight,
    )
    return CvDiagnosisService(
        adapter=_get_cv_diagnosis_adapter(),
        engine=engine,
        repo=get_plant_diagnosis_repo(),
        ipm_service=get_ipm_service(),
        consent_repo=get_consent_repo(),
        consent_engine=ConsentEngine(),
    )


def _get_cv_diagnosis_adapter():
    from app.data_access.external.local_cv_diagnosis_adapter import LocalCvDiagnosisAdapter

    return LocalCvDiagnosisAdapter()


def get_retention_service():
    from app.domain.services.retention_service import RetentionService

    return RetentionService()


def get_data_subject_service():
    from app.domain.services.data_subject_service import DataSubjectService

    return DataSubjectService(get_privacy_service())


def get_privacy_service():
    from app.domain.services.privacy_service import PrivacyService

    return PrivacyService(
        export_repo=get_data_export_repo(),
        consent_repo=get_consent_repo(),
        restriction_repo=get_processing_restriction_repo(),
        erasure_repo=get_erasure_repo(),
        email_change_repo=get_email_change_repo(),
        user_repo=get_user_repo(),
        refresh_token_repo=get_refresh_token_repo(),
        data_export_engine=get_data_export_engine(),
        erasure_engine=get_erasure_engine(),
        consent_engine=get_consent_engine(),
        password_engine=get_password_engine(),
        token_engine=get_token_engine(),
        email_service=get_email_service(),
        frontend_url=settings.frontend_url,
        data_controller_name=settings.privacy_data_controller_name,
        data_controller_email=settings.privacy_data_controller_email,
        storage_adapter=get_object_storage(),
        attachment_repo=get_attachment_repo(),
        membership_repo=get_membership_repo(),
        reference_index_store=get_reference_index_store(),
        pest_image_repo=get_pest_image_repo(),
        ipm_repo=get_ipm_repo(),
        pest_inference_client=get_pest_inference_client(),
    )


# ── Knowledge Service client ─────────────────────────────────────


def get_knowledge_client():
    """Return a KnowledgeServiceClient or None if disabled."""
    if not settings.knowledge_service_enabled:
        return None

    from app.data_access.external.knowledge_service_client import KnowledgeServiceClient

    return KnowledgeServiceClient(base_url=settings.knowledge_service_url)


# ── REQ-031 KI-Assistent dependencies ────────────────────────────


def get_knowledge_service_adapter():
    """Async ``IKnowledgeService`` adapter (circuit-breaker, REQ-031 §4.1)."""
    from app.data_access.external.knowledge_service_adapter import HttpKnowledgeServiceAdapter

    return HttpKnowledgeServiceAdapter(base_url=settings.knowledge_service_url)


def get_ai_tip_cache_repo():
    from app.data_access.arango.ai_repository import ArangoAiTipCacheRepository

    return ArangoAiTipCacheRepository(get_db())


def get_ai_conversation_repo():
    from app.data_access.arango.ai_repository import ArangoAiConversationRepository

    return ArangoAiConversationRepository(get_db())


def get_ai_provider_repo():
    from app.data_access.arango.ai_repository import ArangoAiProviderRepository

    return ArangoAiProviderRepository(get_db())


def get_ai_audit_repo():
    from app.data_access.arango.ai_repository import ArangoAiAuditRepository

    return ArangoAiAuditRepository(get_db())


def get_ai_audit_logger():
    from app.domain.services.ai_audit_logger import AiAuditLogger

    return AiAuditLogger(get_ai_audit_repo())


def get_ai_consent_guard():
    from app.domain.guards.consent_guard import ConsentGuard

    return ConsentGuard(get_consent_repo())


def get_ai_context_builder():
    """AiContextBuilder wired with parent/family resolvers (ADR-002)."""
    from app.domain.services.ai_context_builder import AiContextBuilder

    species_repo = get_species_repo()
    family_repo = get_family_repo()

    def _resolve_parent(parent_key: str):
        return species_repo.get_by_key(parent_key)

    def _resolve_family(family_key: str):
        family = family_repo.get_by_key(family_key)
        return getattr(family, "name", None) if family else None

    return AiContextBuilder(parent_resolver=_resolve_parent, family_resolver=_resolve_family)


def get_ai_assistant_service():
    """REQ-031 §4.3 — the KI orchestration service."""
    from app.domain.services.ai_assistant_service import AiAssistantService

    return AiAssistantService(
        knowledge_adapter=get_knowledge_service_adapter(),
        consent_guard=get_ai_consent_guard(),
        audit_logger=get_ai_audit_logger(),
        tip_cache_repo=get_ai_tip_cache_repo(),
        conversation_repo=get_ai_conversation_repo(),
        provider_repo=get_ai_provider_repo(),
    )


# ── REQ-035 KI terminology glossary dependencies ─────────────────


def get_glossary_term_repo():
    from app.data_access.arango.glossary_repository import ArangoGlossaryTermRepository

    return ArangoGlossaryTermRepository(get_db())


def get_glossary_cache_repo():
    from app.data_access.arango.glossary_repository import ArangoGlossaryTermCacheRepository

    return ArangoGlossaryTermCacheRepository(get_db())


def get_glossary_service():
    """REQ-035 §4.1 — the cache-first glossary term-explanation service.

    Consumes the REQ-031 foundation: the async KnowledgeServiceAdapter (with its
    circuit breaker), the shared AiAuditLogger, and — for the tenant cloud gate —
    the REQ-031 ConsentGuard + provider repository. The Redis hot cache is
    best-effort (a Redis outage degrades to the ArangoDB persist cache).
    """
    from app.domain.services.glossary_service import GlossaryService

    try:
        redis_client = _get_redis_client()
    except Exception:  # noqa: BLE001 — Redis is an optional accelerator (§2.2).
        redis_client = None

    return GlossaryService(
        term_repo=get_glossary_term_repo(),
        cache_repo=get_glossary_cache_repo(),
        knowledge_adapter=get_knowledge_service_adapter(),
        audit_logger=get_ai_audit_logger(),
        consent_guard=get_ai_consent_guard(),
        provider_repo=get_ai_provider_repo(),
        redis_client=redis_client,
    )


# ── REQ-036 KI-Diagnose dependencies ─────────────────────────────


def get_diagnose_service():
    """REQ-036 §4.2 — the structured KI diagnosis service (stateless, IPM-bridged)."""
    from app.domain.engines.diagnosis_analysis_engine import DiagnosisAnalysisEngine
    from app.domain.services.diagnose_service import DiagnoseService

    return DiagnoseService(
        analysis_engine=DiagnosisAnalysisEngine(get_knowledge_service_adapter()),
        consent_guard=get_ai_consent_guard(),
        audit_logger=get_ai_audit_logger(),
        ipm_repo=get_ipm_repo(),
        context_builder=get_ai_context_builder(),
        plant_repo=get_plant_repo(),
        species_repo=get_species_repo(),
        provider_repo=get_ai_provider_repo(),
    )


def get_dashboard_service():
    """REQ-009 dashboard aggregation service."""
    from app.domain.services.dashboard_service import DashboardService

    return DashboardService(
        plant_repo=get_plant_repo(),
        task_repo=get_task_repo(),
        tank_repo=get_tank_repo(),
        care_repo=get_care_reminder_repo(),
        activity_repo=get_activity_repo(),
    )


# ── REQ-029 KI-Bilderkennung dependencies ────────────────────────


def get_reference_image_repo():
    from app.data_access.arango.reference_image_repository import (
        ArangoReferenceImageRepository,
    )

    return ArangoReferenceImageRepository(get_db())


def get_pest_inference_client():
    """REQ-044 — HTTP client for the self-hosted pest-inference service."""
    from app.data_access.external.pest_inference_client import PestDetectionInferenceClient

    return PestDetectionInferenceClient(settings.inference_service_url)


def _build_pest_media_source(source_key: str):
    """REQ-044 WP-3 — instantiate one pest media source by its settings key."""
    from app.data_access.external.gbif_pest_media_source import GBIFPestMediaSource
    from app.data_access.external.idigbio_media_client import IDigBioMediaClient
    from app.data_access.external.inaturalist_media_client import INaturalistMediaClient

    factories = {
        GBIFPestMediaSource.source_key: GBIFPestMediaSource,
        INaturalistMediaClient.source_key: INaturalistMediaClient,
        IDigBioMediaClient.source_key: IDigBioMediaClient,
    }
    factory = factories.get(source_key)
    if factory is None:
        raise ValueError(f"Unknown pest media source: {source_key!r} (known: {sorted(factories)})")
    return factory()


def get_pest_media_sources(source_keys: list[str] | None = None):
    """REQ-044 WP-3 — build the configured pest media sources in priority order.

    ``source_keys`` overrides ``settings.pest_reference_sources`` (e.g. the CLI
    ``--source`` filter for testing a single source).
    """
    keys = source_keys if source_keys is not None else settings.pest_reference_sources
    return [_build_pest_media_source(key) for key in keys]


def get_pest_dataset_acquisition_service(source_keys: list[str] | None = None):
    """REQ-044 WP-3 — cold-start few-shot prototype acquisition (no credentials)."""
    from app.domain.services.pest_dataset_acquisition import PestDatasetAcquisitionService

    return PestDatasetAcquisitionService(
        sources=get_pest_media_sources(source_keys),
        inference=get_pest_inference_client(),
    )


def get_reference_image_service():
    """REQ-029-A §4 — reference-image acquisition pipeline (DINOv2 index).

    Also serves the interactive user-contribution path (issue #447), which needs
    the per-user rate limiter and the identification engine (image hashing) — the
    acquisition pipeline itself does not use those.
    """
    from app.data_access.external.gbif_adapter import GBIFAdapter
    from app.data_access.external.gbif_media_client import GBIFMediaClient
    from app.data_access.external.inference_service_client import InferenceServiceClient
    from app.data_access.external.wikimedia_media_client import WikimediaCommonsMediaClient
    from app.domain.engines.identification_engine import IdentificationEngine
    from app.domain.services.identification_rate_limiter import IdentificationRateLimiter
    from app.domain.services.reference_image_service import ReferenceImageService

    wikimedia = WikimediaCommonsMediaClient() if settings.reference_image_use_wikimedia else None
    identification_engine = IdentificationEngine(
        species_repo=get_species_repo(),
        identification_repo=get_identification_repo(),
    )
    return ReferenceImageService(
        gbif_adapter=GBIFAdapter(),
        media_client=GBIFMediaClient(),
        inference_client=InferenceServiceClient(settings.inference_service_url),
        reference_repo=get_reference_image_repo(),
        wikimedia_client=wikimedia,
        species_repo=get_species_repo(),
        rate_limiter=IdentificationRateLimiter(_get_redis_client()),
        identification_engine=identification_engine,
    )


# ── NFR-013 Object storage dependencies ───────────────────────────


def get_attachment_repo():
    from app.data_access.arango.attachment_repository import ArangoAttachmentRepository

    return ArangoAttachmentRepository(get_db())


def get_attachment_service():
    from app.domain.services.attachment_service import AttachmentService

    return AttachmentService(
        storage=get_object_storage(),
        attachment_repo=get_attachment_repo(),
        settings=settings,
    )


def get_reference_index_store():
    """REQ-025 Phase 0.5 / REQ-029-A — DINOv2 reference-index store.

    Returns the no-op store until the physical pgvector ``species_embeddings``
    index ships (DINOv2 Phase 2). Swap the binding here once the real store
    exists — the erasure pipeline and engine rules need no change.
    """
    from app.data_access.vectordb.noop_reference_index_store import (
        NoopReferenceIndexStore,
    )

    return NoopReferenceIndexStore()


def get_object_storage() -> IObjectStorageAdapter:
    """Return the configured object-storage adapter (cached singleton).

    Builds the adapter from ``settings.storage_backend`` via the
    ``StorageAdapterRegistry`` and wires the attachments repository so the
    REQ-025 erasure hooks (``delete_for_user`` / ``strip_exif_for_user``) can
    look up a user's objects.
    """
    from app.data_access.storage.registry import StorageAdapterRegistry

    global _object_storage
    if _object_storage is None:
        _object_storage = StorageAdapterRegistry.get_for_backend(
            settings.storage_backend,
            attachment_repo=get_attachment_repo(),
        )
    return _object_storage


def close_timescale_connection() -> None:
    global _timescale_connection
    if _timescale_connection is not None:
        _timescale_connection.close()
        _timescale_connection = None


def close_connection() -> None:
    global _connection
    close_timescale_connection()
    if _connection is not None:
        _connection.close()
        _connection = None

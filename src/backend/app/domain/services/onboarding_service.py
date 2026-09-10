"""Onboarding wizard service — manages wizard state and entity creation."""

import contextlib
from datetime import UTC, datetime

import structlog

from app.common.datetimes import today_utc
from app.common.enums import SiteType
from app.common.exceptions import DuplicateError, NotFoundError, ValidationError
from app.data_access.arango.base_repository import BaseArangoRepository
from app.domain.engines.onboarding_engine import OnboardingEngine
from app.domain.models.onboarding import OnboardingState, PlantConfig
from app.domain.models.plant_instance import PlantInstance
from app.domain.models.site import Site
from app.domain.services.singleton_document import pick_singleton
from app.domain.services.starter_kit_service import StarterKitService

logger = structlog.get_logger()


class OnboardingService:
    def __init__(self, db, starter_kit_service: StarterKitService) -> None:
        from app.data_access.arango import collections as col

        # Service-embedded dict view: methods below wrap the raw dict into
        # OnboardingState themselves, so opt into raw mode (FR-002 A3).
        self._repo = BaseArangoRepository(db, col.ONBOARDING_STATES, raw=True)
        self._db = db
        self._kit_service = starter_kit_service
        self._engine = OnboardingEngine()

    def get_state(self, user_key: str) -> OnboardingState:
        from app.data_access.arango import collections as col

        docs = self._repo.find_by_field("user_key", user_key)
        if docs:
            return OnboardingState(**pick_singleton(docs, collection=col.ONBOARDING_STATES, user_key=user_key))
        # Auto-create initial state. Two concurrent cold reads both find the
        # collection empty and both try to insert; the unique index on
        # ``user_key`` makes the loser's insert raise DuplicateError. Re-read and
        # return the winner's document instead of surfacing a 409 (upsert
        # semantics) — this is the auto-create race that used to mint duplicate
        # singletons under parallel load.
        state = OnboardingState(user_key=user_key)
        try:
            doc = self._repo.create(state)
        except DuplicateError:
            docs = self._repo.find_by_field("user_key", user_key)
            return OnboardingState(**pick_singleton(docs, collection=col.ONBOARDING_STATES, user_key=user_key))
        return OnboardingState(**doc)

    def save_progress(self, user_key: str, wizard_step: int, **kwargs) -> OnboardingState:
        state = self.get_state(user_key)
        data = state.model_dump()
        data["wizard_step"] = wizard_step
        data.update(kwargs)
        updated = OnboardingState(**data)
        doc = self._repo.update(state.key or "", updated)
        return OnboardingState(**doc)

    def complete_wizard(
        self,
        user_key: str,
        tenant_key: str = "",
        kit_id: str | None = None,
        experience_level: str | None = None,
        site_name: str = "",
        selected_site_key: str | None = None,
        plant_count: int = 3,
        has_ro_system: bool | None = None,
        tap_water_ec_ms: float | None = None,
        tap_water_ph: float | None = None,
        plant_configs: list[PlantConfig] | None = None,
        favorite_species_keys: list[str] | None = None,
        favorite_nutrient_plan_keys: list[str] | None = None,
        smart_home_enabled: bool | None = None,
    ) -> dict:
        """Complete the onboarding wizard, creating site and plants."""
        state = self.get_state(user_key)
        created_entities: dict[str, list[str]] = {}

        # Derive plant_count from plant_configs if provided
        configs = plant_configs or []
        if configs:
            plant_count = sum(c.count for c in configs)

        if kit_id:
            kit = self._kit_service.get_kit_by_id(kit_id)
            errors = self._engine.validate_kit_application(kit, site_name, plant_count)
            if errors:
                raise ValidationError(
                    "Invalid kit application",
                    [{"field": "kit", "reason": e, "code": "VALIDATION_ERROR"} for e in errors],
                )
            entity_plan = self._engine.build_entity_plan(
                kit,
                site_name,
                plant_count,
                has_ro_system=has_ro_system,
                tap_water_ec_ms=tap_water_ec_ms,
                tap_water_ph=tap_water_ph,
            )
            created_entities["plan"] = [str(entity_plan)]

        # --- Create actual entities ---
        site_key = selected_site_key
        site_type = state.site_type or "indoor"

        # Create site if a name was provided and no existing site selected
        if site_name and not selected_site_key:
            site_key = self._create_site(site_name, site_type, tenant_key)
            created_entities["sites"] = [site_key]

        # Create plant instances from plant_configs or favorite_species. A plant
        # whose species does not resolve is skipped, not silently dropped — the
        # keys and reasons travel back to the caller on the response.
        plant_keys, skipped_plants = self._create_plants(
            configs=configs,
            favorite_species_keys=favorite_species_keys or [],
            site_key=site_key,
            tenant_key=tenant_key,
        )
        if plant_keys:
            created_entities["plant_instances"] = plant_keys

        # Process favorites via FavoritesService
        fav_species = favorite_species_keys or []
        fav_plans = favorite_nutrient_plan_keys or []

        if fav_species or fav_plans:
            from app.domain.services.favorites_service import FavoritesService

            fav_service = FavoritesService(self._db)
            for species_key in fav_species:
                with contextlib.suppress(ValueError, Exception):
                    fav_service.add_favorite(user_key, species_key, tenant_key=tenant_key, source="onboarding")
            for plan_key in fav_plans:
                with contextlib.suppress(ValueError, Exception):
                    # The explicit `cascade_fertilizers` call that stood here was
                    # removed in #1233: `add_favorite` cascades on a nutrient-plan
                    # target now, so the wizard is no longer the only path that
                    # does. Two callers of one rule is how the rule drifts.
                    fav_service.add_favorite(user_key, plan_key, tenant_key=tenant_key, source="onboarding")

        state_data = state.model_dump()
        state_data.update(
            {
                "completed": True,
                "completed_at": datetime.now(UTC).isoformat(),
                "selected_kit_id": kit_id,
                "selected_experience_level": experience_level,
                "selected_site_key": site_key,
                "wizard_step": 6,
                "created_entities": created_entities,
                "plant_configs": [c.model_dump() for c in configs],
                "favorite_species_keys": fav_species,
                "favorite_nutrient_plan_keys": fav_plans,
            }
        )
        updated = OnboardingState(**state_data)
        self._repo.update(state.key or "", updated)

        # Persist preferences
        pref_updates: dict = {}
        if experience_level is not None:
            pref_updates["experience_level"] = experience_level
        if smart_home_enabled is not None:
            pref_updates["smart_home_enabled"] = smart_home_enabled
        if pref_updates:
            from app.domain.services.user_preference_service import UserPreferenceService

            pref_service = UserPreferenceService(self._db)
            pref_service.update_preferences(user_key, pref_updates)

        return {
            "status": "completed",
            "created_entities": created_entities,
            # Always present, empty on the happy path: a caller that has to check
            # whether the key exists before reading it will eventually not check.
            "skipped": skipped_plants,
        }

    def _create_site(self, site_name: str, site_type: str, tenant_key: str) -> str:
        """Create a site from onboarding data. Returns the site key."""
        from app.common.dependencies import get_site_service

        site_service = get_site_service()
        try:
            site_type_enum = SiteType(site_type)
        except ValueError:
            site_type_enum = SiteType.INDOOR

        site = site_service.create_site(
            Site(
                name=site_name,
                type=site_type_enum,
                tenant_key=tenant_key,
            )
        )
        logger.info("onboarding_site_created", site_key=site.key, name=site_name)
        return site.key or ""

    def _create_plants(
        self,
        configs: list[PlantConfig],
        favorite_species_keys: list[str],
        site_key: str | None,
        tenant_key: str,
    ) -> tuple[list[str], list[dict[str, str]]]:
        """Create plant instances from configs or favorite species.

        Returns the keys created **and** the plants that were not, with the reason.

        Both halves are load-bearing. A species the caller names may not resolve —
        a stale favourite, a species deleted since, a kit entry pointing at a row
        another tenant owns. Refusing the whole wizard over one of them would be
        wrong: onboarding is the user's first interaction, and the site, the
        preferences and the plants that *did* resolve are all fine.

        But so is the previous behaviour, which caught ``Exception``, wrote a
        server-side warning and returned as if nothing had happened. Until #1335 it
        was survivable — ``create_plant`` accepted a ghost ``species_key`` and
        produced a plant with ``current_phase_key = None`` (the documented "never
        refuse a record over a master-data gap" policy, #1006), which the user could
        see and repair. Now ``_resolve_references`` runs *before* the
        ``skip_validation`` gate and raises :class:`NotFoundError`, so the same
        handler turns a missing species into a plant that was never created and never
        mentioned: ``200 completed`` with fewer plants than the user asked for.

        So: skip the plant, and say which one and why. The caller surfaces this as
        ``skipped`` on the completion response. Silently is the one option that is
        not available.
        """
        from app.common.dependencies import get_plant_instance_service

        plant_service = get_plant_instance_service()
        created_keys: list[str] = []
        skipped: list[dict[str, str]] = []
        # ``planted_on`` is a persisted domain date that plant age, phase
        # progress and GDD accumulation are computed from — all against UTC
        # timestamps, so the seed date is UTC (§12a).
        today = today_utc()

        # Build assignments: prefer explicit configs, fallback to favorites
        assignments: list[tuple[str, int]] = []
        if configs:
            assignments = [(c.species_key, c.count) for c in configs if c.count > 0]
        elif favorite_species_keys:
            assignments = [(key, 1) for key in favorite_species_keys]

        for species_key, count in assignments:
            for i in range(count):
                instance_id = f"onb-{species_key}-{i + 1}"
                plant = PlantInstance(
                    instance_id=instance_id,
                    species_key=species_key,
                    planted_on=today,
                    tenant_key=tenant_key,
                )
                try:
                    created = plant_service.create_plant(plant, skip_validation=True)
                except NotFoundError as exc:
                    # The expected refusal: the species (or another reference the
                    # wizard carries) does not resolve under this tenant. Named
                    # separately from the catch-all below because it is the one the
                    # user can act on — the message says which key was not found.
                    logger.warning(
                        "onboarding_plant_skipped_unresolvable_reference",
                        species_key=species_key,
                        instance_id=instance_id,
                        reason=exc.message,
                    )
                    skipped.append({"entity_type": "plant_instance", "key": species_key, "reason": exc.message})
                    continue
                except Exception:  # noqa: BLE001 — one bad plant must not end the wizard
                    # Everything else: still reported, but with a fixed reason. The
                    # exception text of an unexpected failure is a storage/driver
                    # message, and putting it in an HTTP response is the leak the
                    # error contract exists to prevent. The detail stays in the log.
                    logger.warning(
                        "onboarding_plant_create_failed",
                        species_key=species_key,
                        instance_id=instance_id,
                        exc_info=True,
                    )
                    skipped.append(
                        {
                            "entity_type": "plant_instance",
                            "key": species_key,
                            "reason": "The plant could not be created.",
                        }
                    )
                    continue
                if created.key:
                    created_keys.append(created.key)

        if created_keys:
            logger.info("onboarding_plants_created", count=len(created_keys))
        if skipped:
            logger.warning("onboarding_plants_skipped", count=len(skipped))
        return created_keys, skipped

    def ensure_onboarding_state_for_user(
        self,
        user_key: str,
        tenant_key: str,
        takeover_accepted: bool | None = None,
    ) -> OnboardingState:
        """Ensure an onboarding state exists for a user.

        - takeover_accepted=None: returns current state (or creates initial)
        - takeover_accepted=True: marks completed (system-user takeover, no wizard)
        - takeover_accepted=False: creates fresh state with wizard_step=1

        # TODO: REQ-027 — full mode-switch integration
        """
        if takeover_accepted is None:
            return self.get_state(user_key)

        state = self.get_state(user_key)
        data = state.model_dump()
        if takeover_accepted:
            data.update(
                {
                    "completed": True,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "wizard_step": 0,
                }
            )
        else:
            data.update(
                {
                    "completed": False,
                    "skipped": False,
                    "completed_at": None,
                    "wizard_step": 1,
                }
            )
        updated = OnboardingState(**data)
        doc = self._repo.update(state.key or "", updated)
        return OnboardingState(**doc)

    def reset_wizard(self, user_key: str) -> OnboardingState:
        """Reset wizard to initial state, allowing re-run.

        Removes **all** onboarding-sourced and cascade-sourced favorite edges
        for the user — not just those still tracked in the OnboardingState
        snapshot. The snapshot can drift behind the canonical
        ``user_favorites`` edge collection (concurrent E2E worker writes,
        prior incomplete resets, manual API calls), so we read the live
        edge list and prune by ``source`` to make the reset deterministic.
        Manually added favorites (``source='manual'``) are preserved.
        """
        state = self.get_state(user_key)

        from app.domain.services.favorites_service import FavoritesService

        fav_service = FavoritesService(self._db)
        for edge in fav_service.list_favorites(user_key):
            if edge.get("source") not in ("onboarding", "cascade"):
                continue
            target_id = edge.get("_to") or ""
            target_key = target_id.split("/", 1)[-1]
            if not target_key:
                continue
            with contextlib.suppress(Exception):
                fav_service.remove_favorite(user_key, target_key)

        data = state.model_dump()
        data.update(
            {
                "completed": False,
                "skipped": False,
                "completed_at": None,
                "wizard_step": 0,
                "selected_kit_id": None,
                "selected_experience_level": None,
                "created_entities": {},
                "site_name": "",
                "site_type": None,
                "selected_site_key": None,
                "plant_count": None,
                "plant_configs": [],
                "favorite_species_keys": [],
                "favorite_nutrient_plan_keys": [],
            }
        )
        updated = OnboardingState(**data)
        doc = self._repo.update(state.key or "", updated)
        return OnboardingState(**doc)

    def skip_wizard(self, user_key: str) -> OnboardingState:
        state = self.get_state(user_key)
        data = state.model_dump()
        data["skipped"] = True
        data["completed_at"] = datetime.now(UTC).isoformat()
        updated = OnboardingState(**data)
        doc = self._repo.update(state.key or "", updated)
        return OnboardingState(**doc)

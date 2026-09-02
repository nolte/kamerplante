from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from app.common.datetimes import today_utc
from app.common.enums import (
    TerminationCause,
    TerminationType,
    TransitionTrigger,
)
from app.common.exceptions import NotFoundError, ValidationError
from app.common.tenant_guard import verify_tenant_ownership
from app.common.types import PlantID, SlotKey, SpeciesKey
from app.domain.engines.companion_planting_engine import CompanionPlantingEngine
from app.domain.engines.crop_rotation_validator import CropRotationValidator
from app.domain.engines.cyclic_lifecycle_engine import CyclicLifecycleEngine
from app.domain.engines.frost_exposure_resolver import resolve_frost_exposure
from app.domain.engines.phase_key_resolver import PhaseKeyResolver
from app.domain.engines.phase_transition_engine import PhaseTransitionEngine
from app.domain.interfaces.phase_repository import IPhaseRepository
from app.domain.interfaces.phase_sequence_repository import IPhaseSequenceRepository
from app.domain.interfaces.plant_instance_repository import IPlantInstanceRepository
from app.domain.interfaces.planting_run_repository import IPlantingRunRepository
from app.domain.interfaces.site_repository import ISiteRepository
from app.domain.interfaces.species_repository import ISpeciesRepository
from app.domain.interfaces.task_repository import ITaskRepository
from app.domain.models.phase import PhaseHistory
from app.domain.models.plant_instance import PlantInstance
from app.domain.models.propagation import PropagationEvent
from app.domain.models.site import Location
from app.domain.models.species import Cultivar, Species
from app.domain.models.survival_stats import (
    PhaseLossCount,
    SurvivalStats,
    TerminationCauseCount,
    TerminationTypeCount,
)
from app.domain.services.propagation_service import PropagationService

if TYPE_CHECKING:
    from app.domain.services.overwintering_materializer import OverwinteringMaterializer
    from app.domain.services.overwintering_profile_service import OverwinteringProfileService
    from app.domain.services.species_service import SpeciesService
    from app.domain.services.substrate_service import SubstrateService

logger = structlog.get_logger()


class PlantInstanceService:
    def __init__(
        self,
        plant_repo: IPlantInstanceRepository,
        site_repo: ISiteRepository,
        rotation_validator: CropRotationValidator,
        companion_engine: CompanionPlantingEngine,
        phase_repo: IPhaseRepository | None = None,
        phase_seq_repo: IPhaseSequenceRepository | None = None,
        task_repo: ITaskRepository | None = None,
        species_repo: ISpeciesRepository | None = None,
        planting_run_repo: IPlantingRunRepository | None = None,
        photo_cleanup: Callable[[PlantInstance], None] | None = None,
        propagation_service: PropagationService | None = None,
        overwintering_materializer: OverwinteringMaterializer | None = None,
        overwintering_service: OverwinteringProfileService | None = None,
        substrate_service: SubstrateService | None = None,
        species_service: SpeciesService | None = None,
    ) -> None:
        self._repo = plant_repo
        self._site_repo = site_repo
        self._rotation = rotation_validator
        self._companion = companion_engine
        self._phase_repo = phase_repo
        self._phase_seq_repo = phase_seq_repo
        # Resolves a phase key across the PhaseSequenceEntry and legacy GrowthPhase
        # key-spaces (#579) — only usable when a phase repo is wired.
        self._phase_resolver = PhaseKeyResolver(phase_repo, phase_seq_repo) if phase_repo else None
        self._task_repo = task_repo
        self._species_repo = species_repo
        self._run_repo = planting_run_repo
        # REQ-047 §3.4 — eager overwintering automation. Both are optional so the
        # service stays usable in overwintering-less contexts (tests / internal
        # callers): the materialiser derives the winter profile when a plant lands
        # on an outdoor/greenhouse site, the profile service removes a purely
        # auto-generated profile when it is moved back indoors.
        self._overwintering_materializer = overwintering_materializer
        self._overwintering_service = overwintering_service
        # REQ-003 D10 / REQ-017 — clonal-continuation collaborators. The engine
        # is pure (the terminal decision); the PropagationEvent persistence is
        # optional so the service stays usable in propagation-less contexts.
        self._cyclic = CyclicLifecycleEngine()
        self._propagation = propagation_service
        # REQ-034 §2.1 / AC-08 — cascade gallery-photo deletion when an instance
        # is removed. Injected to avoid a service→service import cycle; no-op
        # when unwired (keeps the service usable in photo-less contexts).
        self._photo_cleanup = photo_cleanup
        # #1335 — the resolvers for the caller-supplied catalogue references a plant
        # carries. Optional, like every other collaborator here, so the service stays
        # constructible in pure-domain contexts; the production wiring supplies both
        # and an absence check pins that, so the escape cannot become the default.
        self._substrate_service = substrate_service
        self._species_service = species_service

    def list_plants(self, offset: int = 0, limit: int = 50, tenant_key: str = "") -> tuple[list[PlantInstance], int]:
        return self._repo.get_all(offset, limit, tenant_key=tenant_key)

    def get_plant(self, key: PlantID, tenant_key: str = "") -> PlantInstance:
        plant = self._repo.get_or_raise(key)
        if tenant_key:
            verify_tenant_ownership(plant, tenant_key, "PlantInstance")
        return plant

    def _verify_site_ownership(self, plant: PlantInstance) -> None:
        """Re-verify a client-supplied ``site_key`` belongs to the plant's tenant (#719).

        Mirrors the location #717 fix and the create/update asymmetry it closed: a
        ``site_key`` taken from the request body must never move (or create) a plant
        onto a site owned by another tenant (IDOR). Unlike ``Location`` documents —
        which persist an empty ``tenant_key`` and are only tenant-verified through
        their parent site (#706) — ``Site`` documents carry a real ``tenant_key``, so
        ownership is anchored directly on the resolved site here and the guard is not
        inert. Raises :class:`NotFoundError` (via ``get_site_or_raise`` for an unknown
        site, via ``verify_tenant_ownership`` for a foreign one) so the write path is
        never reached. Skipped when the plant carries no ``tenant_key`` (internal
        callers / tests) or no ``site_key`` — matching the ``if tenant_key`` gate used
        by ``get_plant``/``remove_plant``.
        """
        if not plant.tenant_key or not plant.site_key:
            return
        site = self._site_repo.get_site_by_key(plant.site_key)
        if site is None:
            raise NotFoundError("Site", plant.site_key)
        verify_tenant_ownership(site, plant.tenant_key, "Site")

    # ── Caller-supplied reference resolution (#1335) ──────────────────────

    #: The reference fields resolved by :meth:`_resolve_references`, in check order.
    #:
    #: ``site_key`` is absent because :meth:`_verify_site_ownership` (#719) already
    #: owns it, unconditionally on both paths; ``cultivar_key`` is absent because it
    #: is resolved one layer down, by
    #: :attr:`ArangoPlantInstanceRepository._owned_reference_fields` (#1090). Order
    #: between fields is not decision-bearing — each answers 404 on its own — but it
    #: is *inside* ``get_growing_medium``, where scope precedes classification.
    _RESOLVED_REFERENCE_FIELDS: tuple[str, ...] = (
        "location_key",
        "slot_key",
        "species_key",
        "substrate_batch_key",
        "substrate_key",
    )

    def _resolve_references(self, plant: PlantInstance, *, previous: PlantInstance | None = None) -> None:
        """Resolve the caller-supplied foreign keys on ``plant`` before it is stored (#1335).

        ``POST``/``PUT``/``PATCH /t/{slug}/plant-instances`` assign the body's keys
        onto the row verbatim, so before this existed a caller could point a plant at
        a substrate / location / slot / batch / species that does not exist or belongs
        to another tenant, and the amendment gate #1332 shipped had no REST seam to
        attach to.

        **Here rather than in the router.** The router would have to repeat it in
        three handlers and the fourth caller would not get it — the #948 shape this
        repository keeps paying for. There is one seam per direction
        (:meth:`create_plant` / :meth:`update_plant`), so the MCP tools, the
        onboarding service and any future caller are covered by construction rather
        than by remembering.

        **What each key is anchored on is not uniform, and that is the difficulty:**

        * ``location_key`` / ``slot_key`` carry **no usable** ``tenant_key``.
          ``LocationCreate`` has no such field and ``create_location`` builds
          ``Location(**body.model_dump())``, so every stored row is ``""`` — and a
          full-replace ``PUT`` even wipes what the one-off ``v0004`` backfill wrote.
          A guard written as ``location.tenant_key == tenant_key`` would refuse
          *every* location: an over-rejecting guard that looks like a security fix
          and loses the feature (#706, #927). They are anchored on the parent
          :class:`~app.domain.models.site.Site`, a slot through its location.
        * ``species_key`` is a hybrid catalogue — own rows, the global seeds
          (``tenant_key == ""``) and, since #1092, an explicitly granted species. The
          predicate used is :meth:`SpeciesService.get_species` itself, not a copy of
          its three arms.
        * ``substrate_batch_key`` is strictly owned, no global arm (#1195).
        * ``substrate_key`` goes through :meth:`SubstrateService.get_growing_medium`,
          the single predicate #1332 introduced: it resolves under the caller's scope
          **first** and only then refuses an amendment (#1175). That order is what
          keeps the 422 from becoming a cross-tenant existence oracle.

        Every refusal is a :class:`NotFoundError` (404) except the amendment, which is
        a :class:`ValidationError` (422). 422 is honest there and only there: such a
        substrate is already visible to the caller, so the answer discloses nothing it
        could not read from the catalogue directly.

        ``previous`` makes the update half **changed-only**, for the reasons
        :meth:`BaseArangoRepository._verify_changed_owned_references` gives (#1090
        C-9): an untouched reference whose target was deleted since, or reclassified
        as an amendment after the plant was potted in it, is an integrity fact and not
        a disclosure route — re-verifying it would make the row uneditable through
        every internal path that rewrites the full model (phase transitions, removal,
        planting-run materialisation).

        Skipped entirely for a plant with no ``tenant_key`` (seeds, migrations, light
        mode): there is nothing to anchor against, matching the ``if tenant_key`` gate
        on :meth:`get_plant` and :meth:`_verify_site_ownership`.
        """
        if not plant.tenant_key:
            return
        for field in self._RESOLVED_REFERENCE_FIELDS:
            value = getattr(plant, field, None)
            if not value:
                continue
            if previous is not None and value == getattr(previous, field, None):
                continue
            self._resolve_reference(field, value, plant.tenant_key)

    def _resolve_reference(self, field: str, value: str, tenant_key: str) -> None:
        """Resolve one reference under ``tenant_key``, or raise. No return value: the
        resolved documents are not used, only the fact that they resolve."""
        if field == "location_key":
            location = self._site_repo.get_location_by_key(value)
            if location is None:
                raise NotFoundError("Location", value)
            self._require_owned_site(location.site_key, tenant_key, "Location", value)
        elif field == "slot_key":
            slot = self._site_repo.get_slot_by_key(value)
            location = self._site_repo.get_location_by_key(slot.location_key) if slot and slot.location_key else None
            if slot is None or location is None:
                raise NotFoundError("Slot", value)
            self._require_owned_site(location.site_key, tenant_key, "Slot", value)
        elif field == "species_key" and self._species_service is not None:
            self._species_service.get_species(value, tenant_key=tenant_key)
        elif field == "substrate_batch_key" and self._substrate_service is not None:
            self._substrate_service.get_batch(value, tenant_key=tenant_key)
        elif field == "substrate_key" and self._substrate_service is not None:
            # ``get_growing_medium``, not ``get_substrate``: this is the medium the
            # plant grows *in*, and a soil amendment is not one (#1175). The predicate
            # scopes before it classifies, so a foreign amendment answers 404.
            self._substrate_service.get_growing_medium(value, tenant_key=tenant_key)

    def _require_owned_site(self, site_key: str, tenant_key: str, entity_name: str, entity_key: str) -> None:
        """Anchor a row that carries no usable ``tenant_key`` on its parent site.

        The raised :class:`NotFoundError` names the **referenced entity**, not the
        site behind it: an absent location and a location under a foreign site must
        answer identically, or the difference between the two messages is itself the
        oracle the 404 exists to prevent.
        """
        site = self._site_repo.get_site_by_key(site_key) if site_key else None
        if site is None or site.tenant_key != tenant_key:
            raise NotFoundError(entity_name, entity_key)

    def create_plant(self, plant: PlantInstance, skip_validation: bool = False) -> PlantInstance:
        # SEC (#719): reject a foreign/unknown site_key before any write, mirroring the
        # location create path — a client must not create a plant on another tenant's site.
        self._verify_site_ownership(plant)
        # #1335: …and every other caller-supplied foreign key with it. Before the
        # rotation/companion engines below, deliberately: those read the slot's
        # neighbourhood tenant-scoped, so a foreign slot yields no findings and
        # *passes* — the reference has to be refused before it is interpreted.
        self._resolve_references(plant)

        if not skip_validation and plant.slot_key:
            # Both engines read the slot's neighbourhood/history, which is
            # tenant-scoped since #927 — the plant being created carries the
            # tenant those reads must be bound to.
            # Validate rotation
            self._rotation.validate_or_raise(plant.slot_key, plant.species_key, tenant_key=plant.tenant_key)
            # Validate companion planting
            self._companion.check_or_raise(plant.species_key, plant.slot_key, tenant_key=plant.tenant_key)

        if plant.current_phase_started_at is None:
            plant.current_phase_started_at = datetime.now(UTC)

        # Resolve / validate the initial phase (REQ-003 #539). A caller-supplied
        # phase captures the plant's *actual current state* (e.g. an existing plant
        # already flowering) and must belong to the species' phase set; an unknown
        # or foreign key is rejected (422) instead of being stored silently. When no
        # phase is given, auto-resolve the species' first phase — prefer
        # PhaseSequence, fall back to LifecycleConfig.
        first_key = self._resolve_initial_phase_key(plant.species_key)
        is_actual_state_capture = False
        if plant.current_phase_key:
            valid_keys = self._valid_phase_keys(plant.species_key)
            if valid_keys and plant.current_phase_key not in valid_keys:
                raise ValidationError(
                    f"Phase '{plant.current_phase_key}' is not part of the phase sequence "
                    f"of species '{plant.species_key}'.",
                    details=[
                        {
                            "field": "current_phase_key",
                            "reason": "Phase does not belong to the species' phase sequence/lifecycle.",
                            "code": "PHASE_NOT_IN_SEQUENCE",
                        }
                    ],
                )
            # A deliberately chosen non-first phase is an actual-state capture, not a
            # start-from-scratch: mark it so downstream GDD/lifecycle/analytics can tell
            # "entered mid-lifecycle" apart from "germinated here" (#539 gap 2).
            is_actual_state_capture = bool(first_key) and plant.current_phase_key != first_key
        elif first_key:
            plant.current_phase_key = first_key
        else:
            # No phase could be resolved at all: the species has neither a bound
            # PhaseSequence nor a LifecycleConfig with growth phases. Until #1006 this
            # branch did not exist — creation fell through silently and produced a plant
            # with ``current_phase_key: null``, which is what DRACA-0616-OWL still looked
            # like two months after planting. Everything the lifecycle carries
            # (typical_duration_days, stress_tolerance, watering_interval_days) hangs off
            # the phase, so a null phase makes the plant unreachable for the engine while
            # looking identical to "between phases".
            #
            # Deliberately NOT a hard failure: a species created through the identify flow
            # (REQ-048) legitimately has no sequence yet, and refusing the plant would cost
            # the user their record over a master-data gap. It is logged so the state is
            # discoverable instead of silent, and the history entry below is skipped rather
            # than written empty.
            logger.warning(
                "plant_created_without_phase",
                species_key=plant.species_key,
                plant_key=plant.key,
                instance_id=plant.instance_id,
                reason="no phase sequence resolvable",
            )

        created = self._repo.create(plant)

        # Create initial phase history entry — only when a phase was actually resolved.
        # An "initial" entry carrying an empty ``phase_key`` used to be written for the
        # no-phase case (#1006): it makes the history look enrolled while pointing at
        # nothing, so a consumer reading the history cannot tell the state apart from a
        # real one. No phase, no entry — the warning above is the record of it.
        if created.key and self._phase_repo and plant.current_phase_key:
            phase_name = self.resolve_phase_name(plant.current_phase_key)
            history = PhaseHistory(
                plant_instance_key=created.key,
                phase_key=plant.current_phase_key,
                phase_name=phase_name,
                entered_at=plant.current_phase_started_at or datetime.now(UTC),
                transition_reason="initial_actual_state" if is_actual_state_capture else "initial",
            )
            self._phase_repo.create_phase_history(history)

        # Mark slot as occupied
        if plant.slot_key:
            slot = self._site_repo.get_slot_by_key(plant.slot_key)
            if slot:
                slot.currently_occupied = True
                self._site_repo.update_slot(plant.slot_key, slot)

        # REQ-047 §3.4 — eager overwintering materialisation. A plant created on an
        # outdoor/greenhouse site derives its winter profile immediately, instead of
        # waiting for the lazy growing→pre_winter season transition. Best-effort: a
        # failure here must never fail plant creation.
        self._sync_overwintering_for_site(created)

        return created

    # ── Clonal continuation (REQ-003 D10 / REQ-017) ───────────────────────────

    def handle_monocarpic_terminal_transition(
        self,
        mother_key: PlantID,
        phase_name: str,
        *,
        trigger: TransitionTrigger = TransitionTrigger.MANUAL,
    ) -> PlantInstance | None:
        """Post-transition seam: spawn one clonal pup for a terminal monocarpic mother.

        Registered as an ``on_transition`` callback of the phase service. When a
        **monocarpic** mother **auto**-transitions into the **last phase of its
        species sequence** — which for a monocarp is its terminal reproductive
        phase — continuation happens through a **new** plant instance (the pup)
        linked by a ``descended_from`` edge (REQ-017), explicitly NOT a seasonal
        cycle restart (R1/R8). Returns the spawned pup, or ``None`` when the
        transition does not qualify or a pup already exists (idempotent, R7).

        Gating (all must hold):

        * ``trigger`` is ``AUTO`` — a manual correction into the terminal phase must
          not spawn a clone (Q1, Fix #5);
        * the lifecycle ``is_monocarpic`` and ``phase_name`` is a reproductive
          terminal phase (the pure engine decision);
        * the mother's current phase is the **last** phase of its configured
          sequence — a monocarp with ``…→flowering→fruit_development→ripening`` only
          continues at ``ripening``, not already at ``flowering`` (Fix #4).

        The pure terminal decision lives in :class:`CyclicLifecycleEngine`; only the
        spawn/edge/event side effects live here (NFR-001, R11). Tenant isolation is
        preserved by inheriting the mother's ``tenant_key`` on every new record (R10).

        Failures are caught and logged here rather than surfacing as a broken phase
        transition: a spawn is a best-effort continuation, and re-evaluation is
        idempotent, so a transient failure is recovered on the next AUTO scan.
        """
        # Q1 / Fix #5: only an automatic transition continues a monocarp.
        if trigger != TransitionTrigger.AUTO:
            return None

        mother = self._repo.get_by_key(mother_key)
        if mother is None or mother.key is None:
            return None

        lifecycle = self._phase_repo.get_lifecycle_by_species(mother.species_key) if self._phase_repo else None
        if lifecycle is None or not self._cyclic.is_monocarpic_terminal(lifecycle, phase_name):
            return None

        # Fix #4: reproductive-terminal is necessary but not sufficient — the mother
        # must be in the ACTUAL last phase of its sequence (no successor), so a
        # species that still has fruit_development/ripening ahead does not continue
        # prematurely at flowering.
        if not self._is_last_phase(mother.species_key, mother.current_phase_key or ""):
            return None

        try:
            return self._spawn_pup(mother)
        except Exception:
            logger.error(
                "clonal_pup_spawn_failed",
                mother_key=mother.key,
                tenant_key=mother.tenant_key,
                species_key=mother.species_key,
                phase_name=phase_name,
                exc_info=True,
            )
            # Swallowed on purpose: the phase transition itself must stand, and the
            # next AUTO re-evaluation retries idempotently (Fix #1).
            return None

    def _spawn_pup(self, mother: PlantInstance) -> PlantInstance | None:
        """Create the pup instance, its lineage edge and a clone PropagationEvent.

        The pup inherits ``tenant_key``, ``species_key``, ``cultivar_key`` and the
        mother's **location** — but NOT the slot (R4): the mother lives on senescent
        and still occupies it. ``planted_on`` is the terminal-transition date. The
        pup's phase is forced to ``pup_establishment`` when the species models it,
        else falls back to the first sequence phase (R2).

        Idempotency (R7 / Fix #1) is keyed on the **existence of the pup document**,
        not merely the lineage edge. The pup's ``instance_id`` is the deterministic
        ``{mother.instance_id}-pup``; a prior partial spawn (doc written, then a
        transient failure before the edge/event) would otherwise collide on the
        global unique ``instance_id`` index on retry. So: if the pup already exists
        its missing lineage edge/event are back-filled and the method returns
        ``None`` (no second ``create``); only a genuinely absent pup is created.
        """
        assert mother.key is not None  # guarded by the caller

        # Fix #1: guard on the pup DOCUMENT, not just the edge. A partially-spawned
        # orphan pup (doc without edge) is completed idempotently instead of
        # colliding on the unique instance_id index.
        pup_instance_id = f"{mother.instance_id}-pup"
        existing_pup = self._repo.get_by_instance_id(pup_instance_id, tenant_key=mother.tenant_key)
        if existing_pup is not None:
            self._ensure_lineage_complete(mother, existing_pup)
            return None

        # Fallback edge-based guard (covers a pup whose instance_id was later
        # changed): a mother that already has a descendant must not spawn again.
        if self._repo.has_descendants(mother.key):
            logger.warning(
                "clonal_pup_spawn_skipped_existing_descendant",
                mother_key=mother.key,
                tenant_key=mother.tenant_key,
            )
            return None

        now = datetime.now(UTC)
        pup = PlantInstance(
            tenant_key=mother.tenant_key,
            instance_id=pup_instance_id,
            species_key=mother.species_key,
            cultivar_key=mother.cultivar_key,
            site_key=mother.site_key,
            location_key=mother.location_key,
            slot_key=None,  # R4: mother still holds the slot while senescing
            substrate_key=mother.substrate_key,
            planted_on=now.date(),
            current_phase_key=self._resolve_pup_phase_key(mother.species_key),
            current_phase_started_at=now,
            mother_key=mother.key,
        )
        # No slot_key → the repository creates the doc without a PLACED_IN edge.
        created = self._repo.create(pup)

        # Initial phase-history entry for the pup (mirrors create_plant).
        if created.key and self._phase_repo:
            phase_name = self.resolve_phase_name(pup.current_phase_key or "")
            self._phase_repo.create_phase_history(
                PhaseHistory(
                    plant_instance_key=created.key,
                    phase_key=pup.current_phase_key or "",
                    phase_name=phase_name,
                    entered_at=now,
                    transition_reason="clonal_pup",
                )
            )

        # REQ-017 lineage edge child (pup) → mother.
        if created.key:
            self._repo.create_descended_from_edge(created.key, mother.key)

        # REQ-017 provenance: persist the clone event (mother → pup).
        self._record_clone_event(mother, created, now)

        logger.info(
            "clonal_pup_spawned",
            mother_key=mother.key,
            pup_key=created.key,
            tenant_key=mother.tenant_key,
            species_key=mother.species_key,
            pup_phase_key=created.current_phase_key,
        )
        return created

    def _ensure_lineage_complete(self, mother: PlantInstance, pup: PlantInstance) -> None:
        """Back-fill a partially-spawned pup's lineage edge/event idempotently (Fix #1).

        Reached when the pup document already exists (a prior spawn wrote it but a
        transient failure struck before the edge/event). If the mother still has no
        descendant edge the edge — and the provenance event that goes with it — are
        created now; otherwise the lineage is already complete and this is a no-op.
        Never issues a second ``create`` for the pup, so the unique ``instance_id``
        index is never violated.
        """
        assert mother.key is not None
        if pup.key is None:
            logger.warning("clonal_pup_backfill_skipped_no_key", mother_key=mother.key, tenant_key=mother.tenant_key)
            return
        if self._repo.has_descendants(mother.key):
            # Doc + edge both present — fully consistent, nothing to do.
            logger.debug("clonal_pup_already_complete", mother_key=mother.key, pup_key=pup.key)
            return
        # Orphan pup: complete the missing edge + provenance event.
        self._repo.create_descended_from_edge(pup.key, mother.key)
        self._record_clone_event(mother, pup, datetime.now(UTC))
        logger.warning(
            "clonal_pup_lineage_backfilled",
            mother_key=mother.key,
            pup_key=pup.key,
            tenant_key=mother.tenant_key,
        )

    def _record_clone_event(self, mother: PlantInstance, pup: PlantInstance, when: datetime) -> None:
        """Persist the REQ-017 clone ``PropagationEvent`` (mother → pup), if wired."""
        if self._propagation is None or mother.key is None or pup.key is None:
            return
        self._propagation.record(
            PropagationEvent(
                tenant_key=mother.tenant_key,
                method="clone",
                parent_plant_keys=[mother.key],
                child_plant_keys=[pup.key],
                happened_at=when,
            )
        )

    def _is_last_phase(self, species_key: str, current_phase_key: str) -> bool:
        """Whether ``current_phase_key`` is the last phase of the species' sequence (Fix #4).

        The last phase is the terminal node of the configured sequence: the entry
        (PhaseSequence, preferred) or GrowthPhase (LifecycleConfig fallback) with
        the highest ``sequence_order`` and no successor. Pure resolution over the
        repositories the service already holds — the engine stays free of I/O (R11).
        Returns ``False`` when the phase key is empty or the sequence cannot be
        resolved (fail-closed: no spawn on ambiguity).
        """
        if not current_phase_key:
            return False

        # PhaseSequence first.
        if self._phase_seq_repo:
            seq = self._phase_seq_repo.get_sequence_by_species(species_key)
            if seq:
                entries = self._phase_seq_repo.get_entries_for_sequence(seq.key or "")
                if entries:
                    last = max(entries, key=lambda e: e.sequence_order)
                    return last.key == current_phase_key

        # LifecycleConfig fallback.
        if self._phase_repo:
            lifecycle = self._phase_repo.get_lifecycle_by_species(species_key)
            if lifecycle:
                growth_phases = self._phase_repo.get_phases_by_lifecycle(lifecycle.key or "")
                if growth_phases:
                    last = max(growth_phases, key=lambda gp: gp.sequence_order)
                    return last.key == current_phase_key

        return False

    def update_plant(self, key: PlantID, plant: PlantInstance) -> PlantInstance:
        # Read the persisted state *before* the write so a genuine site change can be
        # detected (REQ-047 §3.4): the caller has already mutated ``plant`` in memory,
        # so the DB copy still carries the old site_key.
        existing = self.get_plant(key)
        old_site_key = existing.site_key
        # SEC (#719): re-verify the (possibly changed) client-supplied site_key against
        # the plant's tenant before persisting — closes the same IDOR as #717 did for
        # locations. A foreign/unknown site raises NotFoundError; the write below and
        # the overwintering sync are never reached.
        self._verify_site_ownership(plant)
        # #1335: resolve the references this update actually **re-points**. The
        # stored copy read above is the comparison basis, so an untouched reference
        # is never dialled — see :meth:`_resolve_references` for why changed-only is
        # the correct semantics here and not merely the cheap one.
        self._resolve_references(plant, previous=existing)
        updated = self._repo.update(key, plant)
        self._sync_overwintering_on_move(updated, old_site_key)
        return updated

    # ── REQ-047 §3.4 overwintering-profile sync ──────────────────────────

    def _sync_overwintering_for_site(self, plant: PlantInstance) -> None:
        """Materialise the winter profile for a plant on an outdoor/greenhouse site.

        No-op when the materialiser is unwired, the plant has no site, the site is
        indoor, or the site cannot be resolved. The materialiser itself enforces the
        winter-hardiness (green→no profile), idempotency and ``user_overridden``
        guards; the outdoor/greenhouse guard is applied *here*, in the caller, so an
        indoor plant with a yellow/red ampel never gets a profile. Best-effort: an
        overwintering failure must never surface as a failed plant write.
        """
        if self._overwintering_materializer is None or not plant.site_key:
            return
        try:
            site = self._site_repo.get_site_by_key(plant.site_key)
            if site is None:
                return
            # Fail-safe tenant guard: never derive a profile against a site owned by
            # another tenant (defence in depth alongside the router's isolation).
            if plant.tenant_key and site.tenant_key != plant.tenant_key:
                return
            # Issue #706: location-first frost exposure — a per-location override wins,
            # ``None`` inherits from the site type (unchanged outdoor/greenhouse gate).
            location = self._load_plant_location(plant)
            if not resolve_frost_exposure(location, site):
                return
            self._overwintering_materializer.materialize(plant, site)
        except Exception as exc:  # noqa: BLE001 — best-effort side effect (REQ-047)
            logger.warning("overwintering_materialize_failed", plant_key=plant.key, error=str(exc))

    def _sync_overwintering_on_move(self, plant: PlantInstance, old_site_key: str | None) -> None:
        """Keep the winter profile in sync when a plant changes site (REQ-047 §3.4).

        Only a genuine site change is acted on — a pure field update (same site_key)
        neither materialises nor removes anything. Moving onto an outdoor/greenhouse
        site materialises the profile; moving onto any other site (indoor et al.) or
        losing the site removes a *purely auto-generated* profile — a manually
        overridden one is always left untouched. Best-effort throughout.
        """
        new_site_key = plant.site_key
        if new_site_key == old_site_key:
            return  # no real move — reject reminders churn on unrelated field edits
        try:
            new_site = self._site_repo.get_site_by_key(new_site_key) if new_site_key else None
            # Issue #706: location-first frost exposure at the target site — a
            # per-location override wins, ``None`` inherits from the site type.
            location = self._load_plant_location(plant) if new_site is not None else None
            target_frost_exposed = new_site is not None and resolve_frost_exposure(location, new_site)
            if target_frost_exposed:
                if plant.tenant_key and new_site.tenant_key != plant.tenant_key:
                    return
                if self._overwintering_materializer is not None:
                    self._overwintering_materializer.materialize(plant, new_site)
            elif self._overwintering_service is not None and plant.key:
                # Moved indoors / lost its site: drop an auto-generated profile only.
                self._overwintering_service.remove_auto_profile_for_plant(plant.key, plant.tenant_key)
        except Exception as exc:  # noqa: BLE001 — best-effort side effect (REQ-047)
            logger.warning("overwintering_move_sync_failed", plant_key=plant.key, error=str(exc))

    def _load_plant_location(self, plant: PlantInstance) -> Location | None:
        """Load the plant's :class:`Location` for the frost-exposure resolver (#706).

        Returns ``None`` — so the resolver falls back to the site type — when the plant
        carries no ``location_key``, the location is unknown, or it does not belong to
        the plant's own site. Ownership is anchored on the SITE, not on
        ``location.tenant_key``: ``Location`` documents are persisted with an empty
        ``tenant_key`` and are tenant-verified through their parent site (see
        ``_verify_location_tenant`` in the router). Since the plant and its site are
        already tenant-verified, requiring ``location.site_key == plant.site_key``
        keeps a location under a foreign/other site from ever contributing its
        ``frost_exposed`` override (fail-safe: inherit from the site type instead).
        """
        if not plant.location_key or not plant.site_key:
            return None
        location = self._site_repo.get_location_by_key(plant.location_key)
        if location is None:
            return None
        if not location.site_key or location.site_key != plant.site_key:
            return None
        return location

    def remove_plant(
        self,
        key: PlantID,
        *,
        termination_type: TerminationType | None = None,
        termination_cause: TerminationCause | None = None,
        tenant_key: str = "",
    ) -> PlantInstance:
        """Soft-remove a plant, optionally classifying how its lifecycle ended (E5).

        Backward compatible: with no ``termination_type`` the plant is simply marked
        ``removed_on`` (the previous behaviour). When ``termination_type='died'`` the
        current growth phase is **frozen** via the transition engine — the open
        phase-history entry is closed in place and NO senescence transition happens —
        and ``termination_cause`` is recorded for failure analytics. ``termination_cause``
        is only valid together with ``died``.

        ``tenant_key`` re-verifies ownership inside the service (SEC-001, defence in
        depth): the isolation invariant must not depend solely on the router fetching
        the plant first. Empty (the default) preserves the pre-existing behaviour for
        internal callers and tests.
        """
        plant = self.get_plant(key, tenant_key=tenant_key)

        # E5: a cause only makes sense for an unplanned death.
        if termination_cause is not None and termination_type != TerminationType.DIED:
            raise ValidationError("termination_cause is only valid for termination_type='died'")

        # REQ-034 §2.1 / AC-08 — hard-delete the gallery photos before the
        # instance is removed so no orphan storage bytes remain.
        # Order is deliberate (security review SEC-002, Low): bytes are deleted
        # before the metadata update so a failure leaves at worst dangling refs
        # (skipped on list) rather than orphaned personal bytes (the DSGVO-worse
        # outcome). A fully transactional cascade is a follow-up.
        if self._photo_cleanup is not None and plant.photo_refs:
            self._photo_cleanup(plant)
            plant.photo_refs = []
            plant.cover_photo_ref = None
            # Persist the cleanup now: the 'died' path below reloads the plant
            # through the transition engine, which would otherwise not see it.
            plant = self._repo.update(key, plant)

        if termination_type == TerminationType.DIED and self._phase_repo is not None:
            # Freeze the current phase and record the unplanned loss (no senescence).
            engine = PhaseTransitionEngine(self._phase_repo, self._repo, self._phase_seq_repo)
            updated = engine.terminate(key, TerminationType.DIED, termination_cause=termination_cause)
        else:
            plant.termination_type = termination_type
            plant.termination_cause = termination_cause
            # The sibling path above records the loss through the transition
            # engine, which stamps ``datetime.now(UTC)``; this one must not use
            # a different clock for the same event (§12a).
            plant.removed_on = today_utc()
            updated = self._repo.update(key, plant)

        # Remove the now-obsolete open tasks of this plant from the queue — this
        # includes the CARE_REMINDER-category tasks that surface care reminders
        # (REQ-022), so removing/terminating a plant cancels its reminders too.
        # Completed/skipped/failed tasks are kept as history.
        self._delete_open_tasks_for_plant(key, tenant_key=plant.tenant_key)
        # Watering/feeding tasks hang off the planting run, not the instance, so
        # they are cleaned up separately — but only once the run has no active
        # instances left (a run may contain several plants).
        self._delete_orphaned_run_tasks(key, tenant_key=plant.tenant_key)

        if plant.slot_key:
            slot = self._site_repo.get_slot_by_key(plant.slot_key)
            if slot:
                active = self._repo.get_active_by_slot(plant.slot_key, tenant_key=plant.tenant_key)
                if len(active) <= 1:
                    slot.currently_occupied = False
                    self._site_repo.update_slot(plant.slot_key, slot)

        return updated

    # Tasks that are still actionable when a plant is removed.
    _OPEN_TASK_STATUSES = ("pending", "in_progress", "dormant")

    def _delete_open_tasks_for_plant(self, key: PlantID, *, tenant_key: str) -> int:
        """Delete all open tasks attached to the given plant.

        Returns the number of deleted tasks. No-op when no task repository is
        wired (keeps the service usable in contexts without tasks).

        A plant with no tenant is skipped, because the task lookup is
        tenant-scoped since #927 and a tenantless read would be exactly the
        cross-tenant scan that fix removes. Fail-closed is right for a read; here
        it **omits work that must happen**, so it no longer does so silently
        (#952): the open tasks of the removed plant — including its REQ-022 care
        reminders — stay in the queue and something has to say so. The warning
        mirrors ``tank_maintenance_tasks``' ``runoff_trend_check_skipped_tenantless_plant``.
        """
        if self._task_repo is None:
            return 0
        if not tenant_key:
            logger.warning("open_task_cleanup_skipped_tenantless_plant", plant_key=key)
            return 0
        deleted = 0
        for task in self._task_repo.get_tasks_for_plant(key, tenant_key=tenant_key):
            if task.key and task.status in self._OPEN_TASK_STATUSES:
                self._task_repo.delete_task(task.key)
                deleted += 1
        return deleted

    def _delete_orphaned_run_tasks(self, key: PlantID, *, tenant_key: str) -> int:
        """Delete open run-level tasks (watering/feeding) orphaned by this removal.

        These tasks carry ``planting_run_key`` instead of a plant ``entity_key``,
        so ``_delete_open_tasks_for_plant`` cannot reach them. A planting run can
        contain several instances, so its tasks only become obsolete once every
        instance in the run is removed; while any sibling is still active the run
        keeps generating and needing them. No-op when either repository is unwired.

        ``get_tasks_for_run`` is tenant-scoped since #952, so a tenantless plant
        is skipped here for the same reason and with the same warning as its
        sibling above — omitted cleanup, said out loud.
        """
        if self._task_repo is None or self._run_repo is None:
            return 0
        if not tenant_key:
            logger.warning("orphaned_run_task_cleanup_skipped_tenantless_plant", plant_key=key)
            return 0
        deleted = 0
        for run in self._run_repo.get_runs_for_plant(key):
            if not run.key:
                continue
            # ``get_run_plants`` returns the run's non-detached instances; the
            # just-removed plant is among them with ``removed_on`` set, so a run
            # with any remaining active instance is detected here and skipped.
            siblings = self._run_repo.get_run_plants(run.key)
            if any(s.get("removed_on") is None for s in siblings):
                continue
            for task in self._task_repo.get_tasks_for_run(run.key, tenant_key=tenant_key):
                if task.key and task.status in self._OPEN_TASK_STATUSES:
                    self._task_repo.delete_task(task.key)
                    deleted += 1
        return deleted

    def get_survival_stats(self, tenant_key: str) -> SurvivalStats:
        """Aggregate the tenant's plant instances for survival analytics (REQ-003 G1).

        ``terminated`` counts instances that have concluded (``removed_on`` set);
        ``active`` are those still in cultivation. ``survived`` is every concluded
        instance that was NOT an unplanned loss (harvested/senesced/cancelled/
        plain-removed all count as survived; only ``died`` is a loss), and
        ``survival_rate`` is ``survived / terminated`` over concluded instances —
        still-growing instances are excluded so an all-active tenant does not read
        as a misleading 100 %. Unplanned losses are additionally broken down by the
        frozen growth phase they occurred in — merged by resolved phase *name* so
        the same canonical phase across species aggregates, most-affected first.
        """
        if not tenant_key:
            raise ValidationError("tenant_key is required for survival statistics")

        raw = self._repo.get_survival_stats(tenant_key)
        total = int(raw.get("total", 0))
        terminated = int(raw.get("terminated", 0))
        died = int(raw.get("died", 0))
        active = total - terminated
        survived = max(terminated - died, 0)
        survival_rate = round(survived / terminated, 4) if terminated else 0.0

        by_type = [
            TerminationTypeCount(termination_type=TerminationType(row["value"]), count=row["count"])
            for row in raw.get("by_type", [])
            if row.get("value") is not None
        ]
        by_cause = [
            TerminationCauseCount(termination_cause=TerminationCause(row["value"]), count=row["count"])
            for row in raw.get("by_cause", [])
            if row.get("value") is not None
        ]

        # Merge loss counts by resolved phase NAME: phase keys are per-lifecycle,
        # so the same canonical phase across species must be summed together.
        phase_counts: dict[str, int] = {}
        for row in raw.get("by_phase", []):
            phase_key = row.get("value")
            name = self.resolve_phase_name(phase_key) if phase_key else ""
            phase_counts[name] = phase_counts.get(name, 0) + int(row["count"])
        loss_by_phase = [
            PhaseLossCount(phase_name=name, count=count)
            for name, count in sorted(phase_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

        return SurvivalStats(
            total=total,
            terminated=terminated,
            active=active,
            died=died,
            survived=survived,
            survival_rate=survival_rate,
            by_termination_type=by_type,
            by_termination_cause=by_cause,
            loss_by_phase=loss_by_phase,
        )

    def list_active_in_phase_definition(self, tenant_key: str, phase_definition_key: str) -> list[dict]:
        """List a tenant's active plant instances currently in a phase definition (FIX-01 R1/R8).

        Tenant-scoped (SEC-001): the empty ``tenant_key`` sentinel is rejected before any
        query runs (defence in depth — the repository rejects it too). "Active" means the
        plant is still in cultivation (``removed_on == null``, A2). The current-phase→
        definition indirection (A1) is resolved in the repository. Returns enriched row
        dicts; an empty list is a valid result (R4).
        """
        if not tenant_key:
            raise ValidationError("tenant_key is required to list plant instances in a phase definition.")
        return self._repo.list_active_in_phase_definition(tenant_key, phase_definition_key)

    def get_plants_in_slot(self, slot_key: SlotKey, *, tenant_key: str) -> list[PlantInstance]:
        """Plants occupying a slot, scoped to ``tenant_key`` (#927)."""
        return self._repo.get_active_by_slot(slot_key, tenant_key=tenant_key)

    def get_slot_history(self, slot_key: SlotKey, years: int = 3, *, tenant_key: str) -> list[PlantInstance]:
        """A slot's planting history, scoped to ``tenant_key`` (#927)."""
        return self._repo.get_history_by_slot(slot_key, years, tenant_key=tenant_key)

    def _resolve_initial_phase_key(self, species_key: str) -> str | None:
        """Resolve the first phase key for a species.

        Tries PhaseSequence first, falls back to LifecycleConfig.
        """
        # Try PhaseSequence first
        if self._phase_seq_repo:
            seq = self._phase_seq_repo.get_sequence_by_species(species_key)
            if seq:
                entries = self._phase_seq_repo.get_entries_for_sequence(seq.key or "")
                if entries:
                    first = min(entries, key=lambda e: e.sequence_order)
                    return first.key

        # Fallback to LifecycleConfig
        if self._phase_repo:
            lifecycle = self._phase_repo.get_lifecycle_by_species(species_key)
            if lifecycle:
                growth_phases = self._phase_repo.get_phases_by_lifecycle(lifecycle.key)
                if growth_phases:
                    first = min(growth_phases, key=lambda gp: gp.sequence_order)
                    return first.key

        return None

    def _valid_phase_keys(self, species_key: str) -> set[str]:
        """Return the set of phase keys valid as a *start* phase for a species (#539 gap 1).

        Mirrors :meth:`_resolve_initial_phase_key` resolution order: PhaseSequence
        entry keys are authoritative; LifecycleConfig growth-phase keys are the
        fallback. An empty set means the species has no configured phases — in which
        case a supplied phase cannot be validated and is left untouched (no phase set
        to reject against, so creation must not be blocked).
        """
        if self._phase_seq_repo:
            seq = self._phase_seq_repo.get_sequence_by_species(species_key)
            if seq:
                entries = self._phase_seq_repo.get_entries_for_sequence(seq.key or "")
                if entries:
                    return {entry.key for entry in entries if entry.key}

        if self._phase_repo:
            lifecycle = self._phase_repo.get_lifecycle_by_species(species_key)
            if lifecycle:
                growth_phases = self._phase_repo.get_phases_by_lifecycle(lifecycle.key)
                if growth_phases:
                    return {gp.key for gp in growth_phases if gp.key}

        return set()

    #: Canonical entry phase for a clonal pup (REQ-003 D10 flow-template vocab).
    _PUP_PHASE_NAME = "pup_establishment"

    def _resolve_pup_phase_key(self, species_key: str) -> str | None:
        """Resolve the forced ``pup_establishment`` phase key for a monocarpic pup.

        Prefers a phase named ``pup_establishment`` in the species' PhaseSequence
        (then LifecycleConfig); falls back to the species' first phase via
        :meth:`_resolve_initial_phase_key` when no dedicated pup-entry phase is
        modelled (R2). Bypasses the normal resolver only for the forced phase.
        """
        # PhaseSequence: match the entry whose definition is the pup-entry phase.
        if self._phase_seq_repo:
            seq = self._phase_seq_repo.get_sequence_by_species(species_key)
            if seq:
                for entry in self._phase_seq_repo.get_entries_for_sequence(seq.key or ""):
                    defn = self._phase_seq_repo.get_definition_by_key(entry.phase_definition_key)
                    if defn and defn.name == self._PUP_PHASE_NAME:
                        return entry.key

        # LifecycleConfig: match the growth phase by name.
        if self._phase_repo:
            lifecycle = self._phase_repo.get_lifecycle_by_species(species_key)
            if lifecycle:
                for gp in self._phase_repo.get_phases_by_lifecycle(lifecycle.key or ""):
                    if gp.name == self._PUP_PHASE_NAME:
                        return gp.key

        # No dedicated pup-entry phase — fall back to the first sequence phase.
        return self._resolve_initial_phase_key(species_key)

    def resolve_phase_name(self, phase_key: str) -> str:
        """Resolve a phase key to its name across both key-spaces (#579).

        A plant's ``current_phase_key`` is a PhaseSequenceEntry key for
        sequence-driven species and a GrowthPhase key for legacy LifecycleConfig
        species; the resolver checks the entry key-space first and falls back to
        the legacy one, so the transition response no longer returns an empty name
        for PhaseSequence-driven plants.
        """
        if not phase_key or not self._phase_resolver:
            return ""
        return self._phase_resolver.resolve_name(phase_key)

    def resolve_species(self, species_key: str) -> Species | None:
        """Resolve a Species key to its full model (for denormalized labels)."""
        if not species_key or not self._species_repo:
            return None
        return self._species_repo.get_by_key(species_key)

    def resolve_cultivar(self, cultivar_key: str | None) -> Cultivar | None:
        """Resolve a Cultivar key to its full model (for denormalized labels)."""
        if not cultivar_key or not self._species_repo:
            return None
        return self._species_repo.get_cultivar_by_key(cultivar_key)

    def validate_planting(self, slot_key: SlotKey, species_key: SpeciesKey, *, tenant_key: str) -> dict:
        """Rotation + companion verdict for a slot of ``tenant_key`` (#927).

        Both halves read the slot's neighbourhood and history, and both name the
        species found there in their messages — so a foreign ``slot_key`` must
        produce no findings rather than a description of another tenant's bed.
        """
        rotation_results = self._rotation.validate_planting(slot_key, species_key, tenant_key=tenant_key)
        rotation_valid = all(r.severity != "CRITICAL" for r in rotation_results)
        rotation_warnings = [r.message for r in rotation_results if r.severity in ("CRITICAL", "WARNING")]
        companion_ok, companion_warnings, companion_benefits = self._companion.check_compatibility(
            species_key, slot_key, tenant_key=tenant_key
        )
        return {
            "valid": rotation_valid and companion_ok,
            "warnings": rotation_warnings + companion_warnings,
            "benefits": companion_benefits,
        }

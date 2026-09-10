from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.common.enums import CycleType, SubstrateType, TerminationCause, TerminationType

#: A caller-supplied document key. ``min_length=1`` because ``""`` is not a key:
#: it resolves to nothing, and before this constraint existed it was *also* not
#: resolved — ``PlantInstanceService._resolve_references`` read ``if not value``
#: and treated an empty string as "no reference supplied". Measured on the
#: pre-constraint route: ``POST {"species_key": ""}`` answered **201** and stored
#: a plant whose species does not exist; ``PUT`` stripped an existing plant's
#: species the same way.
#:
#: Refusing it here rather than in the service is deliberate — ``""`` is
#: malformed input, not a reference to something the caller may not see, so the
#: honest answer is a 422 naming the field and not the 404 the service would
#: raise. The service still resolves a stored ``""`` (other callers exist), so
#: the two halves overlap rather than depend on each other.
ReferenceKey = Annotated[str, Field(min_length=1)]

#: The nullable form. The constraint sits on the ``str`` arm of the union, never
#: on the union itself: ``None`` must stay accepted, because an explicit ``null``
#: is how ``PATCH`` clears a reference (#1098) and omission is how ``PUT`` does.
OptionalReferenceKey = ReferenceKey | None


class PlantCreate(BaseModel):
    instance_id: str
    species_key: ReferenceKey
    cultivar_key: OptionalReferenceKey = None
    site_key: OptionalReferenceKey = None
    location_key: OptionalReferenceKey = None
    slot_key: OptionalReferenceKey = None
    substrate_batch_key: OptionalReferenceKey = None
    substrate_key: OptionalReferenceKey = None
    plant_name: str | None = None
    planted_on: date
    current_phase_key: OptionalReferenceKey = None
    container_volume_liters: float | None = Field(default=None, ge=0.1, le=500)
    substrate_type_override: SubstrateType | None = None
    # ADR-006 E1 — per-instance cultivation cycle override; None = "same as the species".
    cultivation_cycle_type: CycleType | None = None


class PlantPatch(BaseModel):
    """Partial update of a plant instance — only the fields actually sent (#1098).

    The sibling ``PUT`` takes :class:`PlantCreate` and is a **full replacement**:
    it assigns thirteen of the fourteen body fields onto the stored row, so every
    optional field the caller omits is written back as ``None`` and — because
    ``ArangoPlantInstanceRepository._update_is_full_replace`` is ``True``, which it
    must be so a ``PUT`` can *clear* a nullable field — removed from the document.

    Measured on the real route: a call carrying only the three required fields
    plus the one being changed erases ``location_key``, ``slot_key``,
    ``cultivar_key``, ``plant_name``, ``container_volume_liters`` and
    ``substrate_batch_key``. Nothing in the endpoint's name or its schema says so.
    That is fine for the edit form, which always sends the whole record, and a trap
    for anything composing a request from the schema alone.

    Here **omitted means untouched** and an explicit ``null`` means *clear this
    field*. The two are distinguished by ``model_fields_set`` (via
    ``exclude_unset``), not by the value — a dump that could not tell them apart
    would make one of the two intents unreachable.

    ``instance_id`` and ``current_phase_key`` are deliberately **absent**.
    ``instance_id`` is the plant's human-facing identity, and renaming a plant as
    a side effect of setting its substrate is the class of surprise this endpoint
    removes. ``current_phase_key`` is server-managed — the ``PUT`` excludes it too
    — and moves only through the phase-transition path, which enforces the state
    machine (REQ-003); accepting it here would be a second, ungated way to set a
    phase. ``extra="forbid"`` rejects both outright rather than dropping them,
    because a silently ignored field reads to the caller as success.
    """

    species_key: OptionalReferenceKey = None
    cultivar_key: OptionalReferenceKey = None
    site_key: OptionalReferenceKey = None
    location_key: OptionalReferenceKey = None
    slot_key: OptionalReferenceKey = None
    substrate_batch_key: OptionalReferenceKey = None
    substrate_key: OptionalReferenceKey = None
    plant_name: str | None = None
    planted_on: date | None = None
    container_volume_liters: float | None = Field(default=None, ge=0.1, le=500)
    substrate_type_override: SubstrateType | None = None
    cultivation_cycle_type: CycleType | None = None

    model_config = {"extra": "forbid"}


class RemovePlantRequest(BaseModel):
    """Optional body for POST /{key}/remove (REQ-003 E5).

    Backward compatible: an empty body keeps the previous plain-removal behaviour.
    ``termination_cause`` is only valid together with ``termination_type='died'``.
    """

    termination_type: TerminationType | None = None
    termination_cause: TerminationCause | None = None


class SpeciesSummary(BaseModel):
    """Denormalized species fields for human-readable plant labels."""

    scientific_name: str
    common_names: list[str] = Field(default_factory=list)


class CultivarSummary(BaseModel):
    """Denormalized cultivar fields for human-readable plant labels."""

    name: str


class PlantResponse(BaseModel):
    key: str
    instance_id: str
    species_key: str
    cultivar_key: str | None
    site_key: str | None = None
    location_key: str | None = None
    slot_key: str | None
    substrate_batch_key: str | None
    substrate_key: str | None = None
    plant_name: str | None
    planted_on: date
    removed_on: date | None
    termination_type: TerminationType | None = None
    termination_cause: TerminationCause | None = None
    current_phase: str = ""
    current_phase_key: str | None = None
    current_phase_started_at: datetime | None = None
    # REQ-017 / REQ-003 D10 — clonal-pup ancestry pointer (mother instance key).
    mother_key: str | None = None
    container_volume_liters: float | None = None
    substrate_type_override: SubstrateType | None = None
    # ADR-006 E1 — per-instance cultivation cycle override (None = same as the species).
    cultivation_cycle_type: CycleType | None = None
    species: SpeciesSummary | None = None
    cultivar: CultivarSummary | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TerminationTypeCountResponse(BaseModel):
    termination_type: TerminationType
    count: int


class TerminationCauseCountResponse(BaseModel):
    termination_cause: TerminationCause
    count: int


class PhaseLossCountResponse(BaseModel):
    phase_name: str
    count: int


class SurvivalStatsResponse(BaseModel):
    """Survival-rate / failure-cause analytics for the tenant (REQ-003 G1)."""

    total: int
    terminated: int
    active: int
    died: int
    survived: int
    survival_rate: float
    by_termination_type: list[TerminationTypeCountResponse] = Field(default_factory=list)
    by_termination_cause: list[TerminationCauseCountResponse] = Field(default_factory=list)
    loss_by_phase: list[PhaseLossCountResponse] = Field(default_factory=list)


class PlantInstanceInPhaseResponse(BaseModel):
    """A tenant's active plant instance currently in a given phase definition (FIX-01 List 1).

    ``days_in_phase`` is intentionally NOT part of the payload: the frontend derives it
    from ``current_phase_started_at`` so the elapsed count stays live without re-fetching.
    """

    key: str
    instance_id: str
    plant_name: str | None = None
    species_key: str
    species_scientific_name: str | None = None
    species_common_names: list[str] = Field(default_factory=list)
    location_key: str | None = None
    location_name: str | None = None
    slot_key: str | None = None
    slot_label: str | None = None
    current_phase_key: str | None = None
    current_phase_started_at: datetime | None = None


class PlantInstancesInPhaseResponse(BaseModel):
    """List-1 payload: the tenant's active instances in a phase definition + total count (R3)."""

    total: int
    items: list[PlantInstanceInPhaseResponse] = Field(default_factory=list)


class ValidatePlantingRequest(BaseModel):
    species_key: str


class ValidatePlantingResponse(BaseModel):
    valid: bool
    warnings: list[str]
    benefits: list[str]


class ActiveChannelDosage(BaseModel):
    fertilizer_key: str
    product_name: str
    ml_per_liter: float
    optional: bool = False
    mixing_priority: int = 50


class ActiveChannelResponse(BaseModel):
    channel_id: str
    label: str
    application_method: str
    target_ec_ms: float | None = None
    target_ph: float | None = None
    plan_key: str
    plan_name: str
    entry_key: str | None = None
    phase_name: str
    week_start: int
    week_end: int
    dosages: list[ActiveChannelDosage] = Field(default_factory=list)


class AssignNutrientPlanRequest(BaseModel):
    plan_key: str
    assigned_by: str = ""


class AssignNutrientPlanStatusResponse(BaseModel):
    """Acknowledgement that a nutrient plan was assigned to a plant instance."""

    status: str = Field(description="Assignment status marker (always ``assigned``).")


class PlantRunSummaryResponse(BaseModel):
    """A compact reference to a planting run a plant instance belongs to."""

    key: str = Field(description="Document key of the planting run.")
    name: str = Field(description="Human-readable name of the planting run.")
    status: str = Field(description="Current lifecycle status of the planting run.")

from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import ExperienceLevel
from app.domain.models.onboarding import PlantConfig


class OnboardingStateResponse(BaseModel):
    key: str
    user_key: str
    completed: bool
    skipped: bool
    completed_at: datetime | None = None
    selected_kit_id: str | None = None
    selected_experience_level: ExperienceLevel | None = None
    wizard_step: int
    created_entities: dict[str, list[str]]
    site_name: str = ""
    site_type: str | None = None
    selected_site_key: str | None = None
    plant_count: int | None = None
    plant_configs: list[PlantConfig] = Field(default_factory=list)
    favorite_species_keys: list[str] = Field(default_factory=list)
    favorite_nutrient_plan_keys: list[str] = Field(default_factory=list)


class PlantConfigSchema(BaseModel):
    species_key: str
    count: int = Field(default=1, ge=1, le=50)
    initial_phase: str = "germination"


class OnboardingCompleteRequest(BaseModel):
    kit_id: str | None = None
    experience_level: ExperienceLevel | None = None
    site_name: str = ""
    selected_site_key: str | None = None
    plant_count: int = Field(default=3, ge=1, le=50)
    plant_configs: list[PlantConfigSchema] = Field(default_factory=list)
    has_ro_system: bool | None = None
    tap_water_ec_ms: float | None = Field(default=None, ge=0, le=2.0)
    tap_water_ph: float | None = Field(default=None, ge=3.0, le=10.0)
    favorite_species_keys: list[str] = Field(default_factory=list)
    favorite_nutrient_plan_keys: list[str] = Field(default_factory=list)
    smart_home_enabled: bool | None = None


class OnboardingProgressUpdate(BaseModel):
    wizard_step: int = Field(ge=0, le=6)
    selected_kit_id: str | None = None
    selected_experience_level: ExperienceLevel | None = None
    site_name: str | None = None
    site_type: str | None = None
    selected_site_key: str | None = None
    plant_count: int | None = Field(default=None, ge=1, le=50)
    plant_configs: list[PlantConfigSchema] | None = None
    favorite_species_keys: list[str] | None = None
    favorite_nutrient_plan_keys: list[str] | None = None
    smart_home_enabled: bool | None = None


class OnboardingSkippedEntity(BaseModel):
    """An entity the wizard could not provision, and why (#1335 review, finding 3).

    The wizard does not fail as a whole over one unresolvable reference — a stale
    favourite or a species deleted since must not cost the user the site, the
    preferences and the plants that did resolve. It must, however, *say* that it
    skipped something: answering ``200 completed`` with fewer plants than were
    asked for, and only a server-side log line, is a silent data loss the user
    cannot see or act on.
    """

    entity_type: str = Field(description="Kind of entity that was skipped (e.g. ``plant_instance``).")
    key: str = Field(description="The reference that could not be resolved (e.g. the species key).")
    reason: str = Field(description="Why it was skipped, in the words of the refusal itself.")


class OnboardingCompleteResponse(BaseModel):
    """Outcome of finishing the onboarding wizard."""

    status: str = Field(description="Completion status marker (always ``completed``).")
    created_entities: dict[str, list[str]] = Field(
        description="Keys of the entities created by the wizard, grouped by entity type.",
    )
    skipped: list[OnboardingSkippedEntity] = Field(
        default_factory=list,
        description="Entities the wizard could not provision, with the reason. Empty on the happy path.",
    )

"""The onboarding wizard never loses a plant silently (#1335 pre-merge review).

``_create_plants`` called ``create_plant(..., skip_validation=True)`` inside a
blanket ``except Exception: logger.warning(...)``. Before reference resolution
existed that was survivable: a ghost ``species_key`` produced a plant with
``current_phase_key = None`` — the documented "never refuse a record over a
master-data gap" policy (#1006), visible in the UI and repairable.

With resolution in place ``_resolve_references`` runs *before* the
``skip_validation`` gate and raises :class:`NotFoundError`, which that blanket
handler swallows. ``POST /t/{slug}/onboarding/complete`` then answers
``200 completed`` with fewer plants — or none — and the only trace is a
server-side warning the user never sees.

The wizard must still not fail as a whole over one unresolvable species (it is
the user's *first* interaction, and the other plants are fine). So: skip the
plant, and **say so in the response**. Silently is the one option that is not
available.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.common.exceptions import NotFoundError
from app.domain.engines.onboarding_engine import OnboardingEngine
from app.domain.models.onboarding import OnboardingState, PlantConfig
from app.domain.models.plant_instance import PlantInstance
from app.domain.services.onboarding_service import OnboardingService

USER_KEY = "user-1"
TENANT_KEY = "tenant-anna"

#: The only species the catalogue resolves. Everything else is a ghost — the
#: shape a stale favourite, a deleted species or a mistyped kit entry produces.
KNOWN_SPECIES = "sp-known"


class _StateRepo:
    """Enough of ``BaseArangoRepository`` for one wizard completion."""

    def __init__(self) -> None:
        self.doc: dict[str, Any] = {"_key": "onb-1", "user_key": USER_KEY, "wizard_step": 1}
        self.updated: OnboardingState | None = None

    def find_by_field(self, field: str, value: Any) -> list[dict[str, Any]]:
        return [dict(self.doc)]

    def update(self, key: str, model: OnboardingState) -> dict[str, Any]:
        self.updated = model
        return model.model_dump(by_alias=True)


class _PlantService:
    """Resolves exactly one species and refuses the rest, as the real service does.

    A ``MagicMock`` here would answer every key with a truthy plant, so a test of
    "the unresolvable one is skipped" would certify nothing (#947, #1155). Name an
    input this double accepts that the real service would not: there is none — it
    refuses with the same :class:`NotFoundError` ``SpeciesService.get_species``
    raises.
    """

    def __init__(self) -> None:
        self.created: list[PlantInstance] = []

    def create_plant(self, plant: PlantInstance, skip_validation: bool = False) -> PlantInstance:
        if plant.species_key != KNOWN_SPECIES:
            raise NotFoundError("Species", plant.species_key)
        stored = plant.model_copy(update={"key": f"plant-{len(self.created) + 1}"})
        self.created.append(stored)
        return stored


@pytest.fixture
def plant_service(monkeypatch: pytest.MonkeyPatch) -> _PlantService:
    from app.common import dependencies

    service = _PlantService()
    monkeypatch.setattr(dependencies, "get_plant_instance_service", lambda: service)
    return service


def _service(repo: _StateRepo) -> OnboardingService:
    service = OnboardingService.__new__(OnboardingService)
    service._repo = repo  # type: ignore[attr-defined]
    service._db = None  # type: ignore[attr-defined]
    service._kit_service = None  # type: ignore[attr-defined]
    service._engine = OnboardingEngine()  # type: ignore[attr-defined]
    return service


def test_one_resolvable_and_one_ghost_species_creates_one_and_reports_the_other(
    plant_service: _PlantService,
) -> None:
    """Red against the pre-review branch, which answered ``created_entities`` with
    one plant, no ``skipped`` key at all, and swallowed the ghost entirely."""
    repo = _StateRepo()

    result = _service(repo).complete_wizard(
        user_key=USER_KEY,
        tenant_key=TENANT_KEY,
        plant_configs=[PlantConfig(species_key=KNOWN_SPECIES, count=1), PlantConfig(species_key="sp-ghost", count=1)],
    )

    assert len(plant_service.created) == 1
    assert result["created_entities"]["plant_instances"] == ["plant-1"]
    assert [(s["key"], s["entity_type"]) for s in result["skipped"]] == [("sp-ghost", "plant_instance")]
    assert result["skipped"][0]["reason"]


def test_a_wizard_whose_species_all_resolve_reports_nothing_skipped(plant_service: _PlantService) -> None:
    """Control. Without it, a change that reported *every* plant as skipped would
    satisfy the assertion above."""
    repo = _StateRepo()

    result = _service(repo).complete_wizard(
        user_key=USER_KEY,
        tenant_key=TENANT_KEY,
        plant_configs=[PlantConfig(species_key=KNOWN_SPECIES, count=2)],
    )

    assert len(plant_service.created) == 2
    assert result["skipped"] == []


def test_a_single_unresolvable_species_does_not_fail_the_whole_wizard(plant_service: _PlantService) -> None:
    """The other direction: refusing the completion outright would be just as wrong.

    Onboarding is the user's first interaction, and one stale favourite must not
    cost them the site, the preferences and the plants that *did* resolve.
    """
    repo = _StateRepo()

    result = _service(repo).complete_wizard(
        user_key=USER_KEY,
        tenant_key=TENANT_KEY,
        plant_configs=[PlantConfig(species_key="sp-ghost", count=1)],
    )

    assert result["status"] == "completed"
    assert result["created_entities"].get("plant_instances") is None
    assert len(result["skipped"]) == 1
    assert repo.updated is not None and repo.updated.completed

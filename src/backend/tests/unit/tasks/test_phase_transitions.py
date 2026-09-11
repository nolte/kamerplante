"""Unit tests for the phase auto-transition Celery task (REQ-003).

The task module imports its dependency getters at module level, so the mock
``app.common.dependencies`` module is installed before the task module is
imported. Collaborators are doubled with ``MagicMock``. Tests assert the
result dict and which phase-service methods are invoked.
"""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.common.enums import (
    CycleType,
    GrowthDeterminacy,
    LightType,
    PhotoperiodType,
    TransitionTrigger,
    TransitionTriggerType,
)
from app.domain.models.site import Location, Site
from app.domain.services.phase_service import SequenceAutoTarget


@pytest.fixture(autouse=True)
def _task_module(monkeypatch):
    """Import the task module once, then patch its module-level getters.

    The task module captures ``get_phase_service`` / ``get_plant_repo`` at
    import time, so the bindings are overridden directly on the module.
    """
    mock_deps = ModuleType("app.common.dependencies")
    mock_deps.get_phase_service = MagicMock()  # type: ignore[attr-defined]
    mock_deps.get_plant_repo = MagicMock()  # type: ignore[attr-defined]
    mock_deps.get_lifecycle_repo = MagicMock()  # type: ignore[attr-defined]
    mock_deps.get_site_repo = MagicMock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "app.common.dependencies", mock_deps)

    import app.tasks.phase_transitions as module

    monkeypatch.setattr(module, "get_phase_service", mock_deps.get_phase_service)
    monkeypatch.setattr(module, "get_plant_repo", mock_deps.get_plant_repo)
    monkeypatch.setattr(module, "get_lifecycle_repo", mock_deps.get_lifecycle_repo)
    monkeypatch.setattr(module, "get_site_repo", mock_deps.get_site_repo)

    deps = SimpleNamespace(
        get_phase_service=mock_deps.get_phase_service,
        get_plant_repo=mock_deps.get_plant_repo,
        get_lifecycle_repo=mock_deps.get_lifecycle_repo,
        get_site_repo=mock_deps.get_site_repo,
    )
    yield module, deps


def _plant(**overrides):
    data = {
        "key": "plant_1",
        "tenant_key": "tenant_1",
        "removed_on": None,
        "current_phase_key": "phase_veg",
        "species_key": "species_1",
        "site_key": None,
        "location_key": None,
        "chill_days_accumulated": 0,
        # ADR-006 E1 — per-instance cycle override; None = "same as the species".
        "cultivation_cycle_type": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _indoor_location(**overrides):
    """A grow-tent Location with an artificial light schedule (REQ-018).

    No ``tenant_key`` on the row: the write path never fills it (#1397), and the
    tenant is read from the parent site. A fixture that invents it made the
    SEC-B4 guard in ``_indoor_day_length_for_plant`` look exercised while the
    guard itself short-circuited on that very field and trusted every location.
    """
    data = {
        "name": "Tent 1",
        "area_m2": 1.5,
        "site_key": "site_1",
        "light_type": LightType.LED,
        "lights_on": "18:00",
        "lights_off": "06:00",  # 12h (12/12 bloom flip)
        "use_dynamic_sunrise": False,
    }
    data.update(overrides)
    return Location(**data)


def _serve_own_site(deps) -> None:
    """Let the site repository double answer the ownership walk (#1397).

    ``site_1`` belongs to ``tenant_1``, which is the tenant the plants in these
    tests carry — so the SEC-B4 guard admits the location instead of skipping it,
    and the photoperiod trigger is reached. A double that answered for any key
    would make the guard untestable from here.
    """
    deps.get_site_repo.return_value.get_site_by_key.side_effect = lambda key: (
        Site(_key=key, tenant_key="tenant_1", name=key, type="indoor") if key == "site_1" else None
    )


def _photoperiod_phase_service(days_in_phase: int = 5):
    phase_service = MagicMock()
    phase_service.get_current_phase.return_value = {"days_in_phase": days_in_phase}
    phase_service.get_transition_rules.return_value = [
        SimpleNamespace(
            trigger_type=TransitionTriggerType.PHOTOPERIOD_BASED,
            auto_transition_after_days=None,
            to_phase_key="phase_flower",
        )
    ]
    return phase_service


class TestCheckAutoTransitions:
    def test_no_plants(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([], 0)
        deps.get_phase_service.return_value = MagicMock()

        result = module.check_auto_transitions()

        assert result == {"transitioned": 0, "errors": 0, "checked": 0}

    def test_skips_removed_and_phaseless_plants(self, _task_module):
        module, deps = _task_module
        plants = [_plant(removed_on="2026-01-01"), _plant(current_phase_key=None)]
        deps.get_plant_repo.return_value.get_all.return_value = (plants, 2)
        phase_service = MagicMock()
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result == {"transitioned": 0, "errors": 0, "checked": 2}
        phase_service.transition_phase.assert_not_called()

    def test_transitions_when_time_rule_met(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)

        phase_service = MagicMock()
        phase_service.get_current_phase.return_value = {"days_in_phase": 30}
        phase_service.get_transition_rules.return_value = [
            SimpleNamespace(
                trigger_type=TransitionTriggerType.TIME_BASED,
                auto_transition_after_days=28,
                to_phase_key="phase_flower",
            )
        ]
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result == {"transitioned": 1, "errors": 0, "checked": 1}
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_flower", reason="auto_time_based", trigger=TransitionTrigger.AUTO
        )

    def test_no_transition_when_days_below_threshold(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)

        phase_service = MagicMock()
        phase_service.get_current_phase.return_value = {"days_in_phase": 10}
        phase_service.get_transition_rules.return_value = [
            SimpleNamespace(
                trigger_type=TransitionTriggerType.TIME_BASED,
                auto_transition_after_days=28,
                to_phase_key="phase_flower",
            )
        ]
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result == {"transitioned": 0, "errors": 0, "checked": 1}
        phase_service.transition_phase.assert_not_called()

    def test_counts_error_without_crashing(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)

        phase_service = MagicMock()
        phase_service.get_current_phase.side_effect = RuntimeError("lookup failed")
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result == {"transitioned": 0, "errors": 1, "checked": 1}

    def test_photoperiod_fires_for_short_day(self, _task_module, monkeypatch):
        module, deps = _task_module
        # short-day species, current day length 10h < critical 12h -> fire
        monkeypatch.setattr(module, "_day_length_for_plant", lambda _plant, _site_repo: 10.0)
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(site_key="site_1")], 1)
        lifecycle = SimpleNamespace(
            photoperiod_type=PhotoperiodType.SHORT_DAY,
            critical_day_length_hours=12.0,
            vernalization_min_days=None,
            growth_determinacy=None,
        )
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = lifecycle

        phase_service = MagicMock()
        phase_service.get_current_phase.return_value = {"days_in_phase": 5}
        phase_service.get_transition_rules.return_value = [
            SimpleNamespace(
                trigger_type=TransitionTriggerType.PHOTOPERIOD_BASED,
                auto_transition_after_days=None,
                to_phase_key="phase_flower",
            )
        ]
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_flower", reason="auto_photoperiod", trigger=TransitionTrigger.AUTO
        )

    def _productive_lifecycle(self, determinacy: GrowthDeterminacy) -> SimpleNamespace:
        return SimpleNamespace(
            growth_determinacy=determinacy,
            photoperiod_type=PhotoperiodType.DAY_NEUTRAL,
            critical_day_length_hours=None,
            vernalization_min_days=None,
        )

    def _productive_phase_service(self) -> MagicMock:
        phase_service = MagicMock()
        # a would-fire time trigger out of the productive phase (fruiting -> ripening)
        phase_service.get_current_phase.return_value = {"days_in_phase": 30, "phase": "fruiting"}
        phase_service.get_transition_rules.return_value = [
            SimpleNamespace(
                trigger_type=TransitionTriggerType.TIME_BASED,
                auto_transition_after_days=28,
                to_phase_key="phase_ripening",
            )
        ]
        return phase_service

    def test_indeterminate_stays_in_productive_phase(self, _task_module):
        """E4: an indeterminate plant in its productive phase is not auto-advanced."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(current_phase_key="phase_fruit")], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._productive_lifecycle(
            GrowthDeterminacy.INDETERMINATE
        )
        phase_service = self._productive_phase_service()
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_determinate_proceeds_out_of_productive_phase(self, _task_module):
        """E4: a determinate plant follows the linear path (fruiting -> ripening)."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(current_phase_key="phase_fruit")], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._productive_lifecycle(
            GrowthDeterminacy.DETERMINATE
        )
        phase_service = self._productive_phase_service()
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_ripening", reason="auto_time_based", trigger=TransitionTrigger.AUTO
        )

    def test_vernalization_fires_when_chill_met(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(chill_days_accumulated=60)], 1)
        lifecycle = SimpleNamespace(
            vernalization_min_days=60,
            photoperiod_type=PhotoperiodType.DAY_NEUTRAL,
            critical_day_length_hours=None,
            growth_determinacy=None,
        )
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = lifecycle

        phase_service = MagicMock()
        phase_service.get_current_phase.return_value = {"days_in_phase": 5}
        phase_service.get_transition_rules.return_value = [
            SimpleNamespace(
                trigger_type=TransitionTriggerType.VERNALIZATION_BASED,
                auto_transition_after_days=None,
                to_phase_key="phase_bolting",
            )
        ]
        deps.get_phase_service.return_value = phase_service

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_bolting", reason="auto_vernalization", trigger=TransitionTrigger.AUTO
        )

    # ── E1 indoor light-schedule photoperiod trigger (REQ-018, issue #382) ──

    def _lifecycle(self, **overrides):
        data = {
            "photoperiod_type": PhotoperiodType.SHORT_DAY,
            "critical_day_length_hours": 13.0,
            "vernalization_min_days": None,
            "growth_determinacy": None,
        }
        data.update(overrides)
        return SimpleNamespace(**data)

    def test_indoor_short_day_fires_from_light_schedule(self, _task_module):
        """Short-day induction fires when the grow-light photoperiod (12h) is
        shorter than the species' critical day length (13h)."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(location_key="loc_1")], 1)
        _serve_own_site(deps)
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location()
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle()
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_flower", reason="auto_photoperiod", trigger=TransitionTrigger.AUTO
        )

    def test_indoor_long_day_fires_from_light_schedule(self, _task_module):
        """Long-day induction fires when the grow-light photoperiod (18h) is
        longer than the species' critical day length (14h)."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(location_key="loc_1")], 1)
        # 06:00 -> 00:00 = 18h
        _serve_own_site(deps)
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location(
            lights_on="06:00", lights_off="00:00"
        )
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle(
            photoperiod_type=PhotoperiodType.LONG_DAY, critical_day_length_hours=14.0
        )
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "phase_flower", reason="auto_photoperiod", trigger=TransitionTrigger.AUTO
        )

    def test_dynamic_sunrise_falls_back_to_outdoor(self, _task_module):
        """A sun-tracking location (use_dynamic_sunrise=True) does not use its
        artificial schedule; it falls through to the outdoor path (no GPS site
        here -> trigger skipped, no fire)."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(location_key="loc_1", site_key=None)], 1)
        # 12h schedule would fire short-day, but dynamic sunrise disqualifies it
        _serve_own_site(deps)
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location(use_dynamic_sunrise=True)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle()
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_natural_light_type_does_not_fire_from_schedule(self, _task_module):
        """A natural-light location (windowsill) has no controllable artificial
        photoperiod; with no GPS site the trigger is skipped."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(location_key="loc_1", site_key=None)], 1)
        _serve_own_site(deps)
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location(
            light_type=LightType.NATURAL
        )
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle()
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_autoflower_does_not_fire_via_photoperiod(self, _task_module):
        """Regression: an autoflower plant (day-neutral, time-based) never fires
        on photoperiod even with a firing indoor schedule and a photoperiod rule
        present — the evaluator only fires short-/long-day species."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant(location_key="loc_1")], 1)
        _serve_own_site(deps)
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location()
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle(
            photoperiod_type=PhotoperiodType.DAY_NEUTRAL, critical_day_length_hours=None
        )
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    # ── WP-2: PhaseSequence-driven cyclic advance (Weg B, #565) ──

    def _seq_phase_service(self, *, is_terminal: bool, is_restart: bool, cycle_number: int = 1, days: int = 200):
        phase_service = MagicMock()
        phase_service.get_current_phase.return_value = {
            "days_in_phase": days,
            "source": "phase_sequence",
            "phase": "dormancy" if is_terminal else "sprouting",
            "cycle_number": cycle_number,
            "is_terminal": is_terminal,
        }
        phase_service.resolve_sequence_auto_target.return_value = SequenceAutoTarget(
            target_phase_key="e-target",
            duration_days=120 if is_terminal else 21,
            is_restart=is_restart,
            current_is_terminal=is_terminal,
        )
        return phase_service

    def test_sequence_forward_advance_fires(self, _task_module):
        """A PhaseSequence-driven plant advances to the next entry on time."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = SimpleNamespace(
            cultivation_cycle_type=None, cycle_type=CycleType.PERENNIAL, growth_determinacy=None
        )
        deps.get_phase_service.return_value = phase_service = self._seq_phase_service(
            is_terminal=False, is_restart=False
        )

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "e-target", reason="auto_time_based", trigger=TransitionTrigger.AUTO
        )

    def test_sequence_restart_fires_for_perennial(self, _task_module):
        """From the terminal phase, a perennial restarts its cycle."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = SimpleNamespace(
            cultivation_cycle_type=None,
            cycle_type=CycleType.PERENNIAL,
            max_seasons=None,
            flowering_strategy=None,
            growth_determinacy=None,
        )
        deps.get_phase_service.return_value = phase_service = self._seq_phase_service(is_terminal=True, is_restart=True)

        result = module.check_auto_transitions()

        assert result["transitioned"] == 1
        phase_service.transition_phase.assert_called_once_with(
            "plant_1", "e-target", reason="auto_cycle_restart", trigger=TransitionTrigger.AUTO
        )

    def test_sequence_restart_suppressed_for_biennial(self, _task_module):
        """should_restart_cycle terminates a bounded (biennial) lifecycle instead of looping."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = SimpleNamespace(
            cultivation_cycle_type=None,
            cycle_type=CycleType.BIENNIAL,
            max_seasons=None,
            flowering_strategy=None,
            growth_determinacy=None,
        )
        deps.get_phase_service.return_value = phase_service = self._seq_phase_service(
            is_terminal=True, is_restart=True, cycle_number=2
        )

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_sequence_restart_suppressed_for_tender_perennial_grown_annual(self, _task_module):
        """A tender perennial (botanical perennial + cultivation annual) must NOT loop.

        ADR-006 E1 negative proof for the tomato-cohort reclassification: making the
        species botanically ``perennial`` (so grown_as_annual fires) does not resurrect the
        seasonal restart, because the restart gate resolves the EFFECTIVE cycle (annual) via
        ``resolve_effective_cycle`` and hands it to ``should_restart_cycle``.
        """
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = SimpleNamespace(
            cultivation_cycle_type=CycleType.ANNUAL,
            cycle_type=CycleType.PERENNIAL,
            max_seasons=None,
            flowering_strategy=None,
            growth_determinacy=None,
        )
        deps.get_phase_service.return_value = phase_service = self._seq_phase_service(is_terminal=True, is_restart=True)

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_sequence_not_due_does_not_fire(self, _task_module):
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = ([_plant()], 1)
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = SimpleNamespace(
            cultivation_cycle_type=None, cycle_type=CycleType.PERENNIAL, growth_determinacy=None
        )
        deps.get_phase_service.return_value = phase_service = self._seq_phase_service(
            is_terminal=False, is_restart=False, days=5
        )

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

    def test_cross_tenant_location_is_ignored(self, _task_module):
        """SEC-B4: a location belonging to another tenant is not trusted; with no
        GPS site the trigger is skipped rather than firing from foreign data."""
        module, deps = _task_module
        deps.get_plant_repo.return_value.get_all.return_value = (
            [_plant(location_key="loc_1", tenant_key="tenant_1", site_key=None)],
            1,
        )
        _serve_own_site(deps)
        # "Foreign" is now expressed the way the data expresses it: a location
        # under a site this tenant does not own. Written as ``tenant_key="tenant_2"``
        # on the location itself, this test passed while the guard it covers was
        # inert in production — the field is persisted empty there (#1397), so the
        # condition short-circuited and every location was trusted.
        deps.get_site_repo.return_value.get_location_by_key.return_value = _indoor_location(site_key="site_2")
        deps.get_lifecycle_repo.return_value.get_lifecycle_by_species.return_value = self._lifecycle()
        deps.get_phase_service.return_value = phase_service = _photoperiod_phase_service()

        result = module.check_auto_transitions()

        assert result["transitioned"] == 0
        phase_service.transition_phase.assert_not_called()

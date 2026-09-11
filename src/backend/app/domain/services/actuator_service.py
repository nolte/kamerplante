"""REQ-018 Environment-control service.

Owns the actuator lifecycle, control schedules/rules, manual overrides, the
immutable control-event log and the phase control profiles. It drives the
:class:`ControlEngine` (priority + hysteresis) and dispatches the winning command
to the physical device over Home Assistant, MQTT or a manual-task fallback.

Graceful degradation (REQ-018 §6 scenarios 6/7): when the Home Assistant call
fails or the actuator is manual, no exception bubbles up — instead a maintenance
task (REQ-006) is created, the actuator is flagged offline and a
``fallback_task`` control event is logged.

Every read/write is tenant-scoped: actuator ownership is verified against
``tenant_key`` before any child (schedule/rule/override/event) is touched,
preventing cross-tenant leakage (SEC-B4).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

from app.common.async_bridge import run_async
from app.common.enums import (
    ActuatorProtocol,
    ControlEventSource,
    TaskCategory,
    TaskPriority,
)
from app.common.exceptions import NotFoundError, ValidationError
from app.common.tenant_guard import verify_tenant_ownership
from app.data_access.arango.actuator_repository import ArangoActuatorRepository
from app.domain.engines.actuator_control_engine import (
    ControlEngine,
    DesiredState,
    HomeAssistantCommandMapper,
    clamp_to_bounds,
    derive_actuator_command,
)
from app.domain.interfaces.site_repository import ISiteRepository
from app.domain.models.actuator import (
    Actuator,
    ControlEvent,
    ControlRule,
    ControlSchedule,
    ManualOverride,
    PhaseControlProfile,
)
from app.domain.models.task import Task
from app.domain.services.location_ownership import require_owned_site

logger = structlog.get_logger(__name__)


class ActuatorService:
    """Business logic for REQ-018 environment control."""

    def __init__(
        self,
        repo: ArangoActuatorRepository,
        ha_client_factory: Callable[[], Any] | None = None,
        task_repo: Any | None = None,
        engine: ControlEngine | None = None,
        mapper: HomeAssistantCommandMapper | None = None,
        site_repo: ISiteRepository | None = None,
    ) -> None:
        self._repo = repo
        # A location's tenant lives on its parent site, and the actuator
        # repository reads locations but not sites (#1397). Optional so the
        # service stays constructible in pure-domain contexts; when it is absent
        # the ownership check says so rather than quietly passing — see
        # :meth:`_verify_location`.
        self._site_repo = site_repo
        self._ha_client_factory = ha_client_factory
        self._task_repo = task_repo
        self._engine = engine or ControlEngine()
        self._mapper = mapper or HomeAssistantCommandMapper()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    # ── Actuator CRUD ────────────────────────────────────────────────────

    def list_for_tenant(
        self,
        tenant_key: str,
        actuator_type: str | None = None,
        protocol: str | None = None,
        is_online: bool | None = None,
    ) -> list[Actuator]:
        return self._repo.list_for_tenant(tenant_key, actuator_type, protocol, is_online)

    def list_for_location(self, location_key: str, tenant_key: str) -> list[Actuator]:
        self._verify_location(location_key, tenant_key)
        return self._repo.list_for_location(location_key, tenant_key)

    def get_actuator(self, key: str, tenant_key: str) -> Actuator:
        actuator = self._repo.get_or_raise(key)
        verify_tenant_ownership(actuator, tenant_key, "Actuator")
        return actuator

    def create_actuator(self, location_key: str, tenant_key: str, actuator: Actuator) -> Actuator:
        self._verify_location(location_key, tenant_key)
        actuator.location_key = location_key
        actuator.tenant_key = tenant_key
        return self._repo.create_actuator(actuator)

    def update_actuator(self, key: str, tenant_key: str, data: dict[str, Any]) -> Actuator:
        actuator = self.get_actuator(key, tenant_key)
        updated = actuator.model_copy(update=data)
        return self._repo.update_actuator(key, updated)

    def delete_actuator(self, key: str, tenant_key: str) -> None:
        self.get_actuator(key, tenant_key)
        self._repo.delete_actuator(key)

    def _verify_location(self, location_key: str, tenant_key: str) -> None:
        """Require ``location_key`` to belong to ``tenant_key``.

        Anchored on the parent site (#1397). Written as
        ``verify_tenant_ownership(location, …)`` this compared against
        ``Location.tenant_key``, which the write path never fills — so it refused
        **every** location, the caller's own included.

        With no site repository wired there is nothing to anchor against, and the
        check refuses rather than passes: an actuator is a device that acts on the
        physical world, so "cannot tell" is not a reason to proceed.
        """
        location = self._repo.get_location(location_key)
        if location is None:
            raise NotFoundError("Location", location_key)
        if self._site_repo is None:
            raise NotFoundError("Location", location_key)
        require_owned_site(self._site_repo, location.site_key, tenant_key, "Location", location_key)

    # ── Command dispatch & graceful degradation ──────────────────────────

    def send_command(
        self,
        key: str,
        tenant_key: str,
        command: str,
        value: float | None = None,
        *,
        source: ControlEventSource = ControlEventSource.MANUAL,
        user: str | None = None,
    ) -> ControlEvent:
        """Send a direct command to an actuator and log the resulting event."""
        actuator = self.get_actuator(key, tenant_key)
        return self._dispatch(actuator, command, value, source, triggered_by_user=user)

    def _dispatch(
        self,
        actuator: Actuator,
        command: str,
        value: float | None,
        source: ControlEventSource,
        *,
        triggered_by_rule_key: str | None = None,
        triggered_by_schedule_key: str | None = None,
        triggered_by_user: str | None = None,
        sensor_reading: float | None = None,
        on_unsafe_value: Literal["raise", "skip"] = "raise",
    ) -> ControlEvent | None:
        # SEC (REQ-018): single chokepoint for every command path (direct, rule,
        # schedule, override, emergency). The safety invariant enforced here is:
        # a numeric value can NEVER reach a physical actuator without a validated,
        # finite [min_value, max_value] envelope, and is always clamped into it.
        #   * SEC-002 — a non-finite value (NaN/Infinity) is refused outright; it
        #     would otherwise defeat the comparison-based clamp.
        #   * SEC-001 — a numeric value for an actuator with NO configured envelope
        #     is refused (fail-closed): forwarding an unbounded number to hardware
        #     (e.g. climate.set_temperature=999) could drive the device out of any
        #     safe envelope. Command paths raise 422; loop/safety paths skip + log.
        # Only once both hold is the value clamped into [min_value, max_value]; the
        # clamped value is what reaches hardware, is stored and is logged.
        if value is not None:
            if not math.isfinite(value):
                return self._refuse_unsafe_value(
                    actuator, value, on_unsafe_value, reason="Numeric actuator value must be finite (no NaN/Infinity)."
                )
            if actuator.min_value is None or actuator.max_value is None:
                return self._refuse_unsafe_value(
                    actuator,
                    value,
                    on_unsafe_value,
                    reason=(
                        "Actuator has no configured [min_value, max_value] envelope; "
                        "a numeric value cannot be dispatched to hardware safely."
                    ),
                )
        value = clamp_to_bounds(value, actuator.min_value, actuator.max_value)

        previous_state = actuator.current_state
        new_state = "off" if command == "turn_off" or value == 0 else "on"

        success = True
        error_message: str | None = None
        effective_source = source

        if actuator.protocol == ActuatorProtocol.MANUAL:
            # Manual actuator: never a direct command — always a task (§6 scenario 7).
            self._create_fallback_task(actuator, command, value, reason="manual_actuator")
            effective_source = ControlEventSource.FALLBACK_TASK
        elif actuator.protocol == ActuatorProtocol.HOME_ASSISTANT:
            success, error_message = self._dispatch_home_assistant(actuator, command, value)
            if not success:
                # Graceful degradation: HA unreachable -> manual task (§6 scenario 6).
                self._create_fallback_task(actuator, command, value, reason="ha_unreachable")
                effective_source = ControlEventSource.FALLBACK_TASK
        elif actuator.protocol == ActuatorProtocol.MQTT:
            # MQTT command is queued to the broker topic; the state topic confirms
            # asynchronously (sync_actuator_states). No MQTT broker client is wired
            # in the backend yet, so the command is recorded optimistically.
            logger.info(
                "actuator_mqtt_command_queued",
                actuator=actuator.key,
                topic=actuator.mqtt_command_topic,
                command=command,
                value=value,
            )

        now = self._now()
        if success:
            updated = actuator.model_copy(
                update={
                    "current_state": new_state,
                    "current_value": value,
                    "last_state_change": now,
                    "last_seen": now,
                    "is_online": True,
                }
            )
        else:
            updated = actuator.model_copy(update={"is_online": False, "last_seen": now})
        self._repo.update_actuator(actuator.key or "", updated)

        event = ControlEvent(
            tenant_key=actuator.tenant_key,
            actuator_key=actuator.key or "",
            location_key=actuator.location_key,
            timestamp=now,
            event_source=effective_source,
            command=command,
            value=value,
            previous_state=previous_state,
            new_state=new_state if success else (previous_state or "off"),
            success=success,
            error_message=error_message,
            triggered_by_rule_key=triggered_by_rule_key,
            triggered_by_schedule_key=triggered_by_schedule_key,
            triggered_by_user=triggered_by_user,
            sensor_reading_at_trigger=sensor_reading,
        )
        return self._repo.create_event(event)

    def _refuse_unsafe_value(
        self,
        actuator: Actuator,
        value: float,
        on_unsafe_value: Literal["raise", "skip"],
        *,
        reason: str,
    ) -> None:
        """Refuse a numeric value that cannot be dispatched safely (SEC-001/002).

        Command paths ask to ``raise`` (surfaces as HTTP 422); the control loop and
        emergency-stop ask to ``skip`` — the offending device is left untouched and
        the refusal is logged, never letting an unbounded/non-finite number reach
        hardware.
        """
        logger.warning(
            "actuator_unsafe_value_refused",
            actuator=actuator.key,
            actuator_type=actuator.actuator_type.value,
            value=value,
            min_value=actuator.min_value,
            max_value=actuator.max_value,
            reason=reason,
        )
        if on_unsafe_value == "raise":
            raise ValidationError(reason)
        return None

    def _dispatch_home_assistant(
        self, actuator: Actuator, command: str, value: float | None
    ) -> tuple[bool, str | None]:
        """Attempt an HA service call; return ``(success, error_message)``."""
        if self._ha_client_factory is None:
            return False, "Home Assistant is not configured"
        client = self._ha_client_factory()
        if client is None:
            return False, "Home Assistant is not configured"
        domain, service, data = self._mapper.map_command(
            actuator.actuator_type.value, actuator.ha_entity_id or "", command, value
        )
        try:
            run_async(client.call_service(domain, service, data))
            return True, None
        except Exception as exc:  # noqa: BLE001 — degrade gracefully on any transport error
            logger.warning(
                "actuator_ha_call_failed",
                actuator=actuator.key,
                entity=actuator.ha_entity_id,
                error=str(exc),
            )
            return False, f"Home Assistant call failed: {exc}"

    def _create_fallback_task(self, actuator: Actuator, command: str, value: float | None, *, reason: str) -> None:
        if self._task_repo is None:
            return
        action = "turn off" if command == "turn_off" else "turn on"
        detail = f" ({value})" if value is not None else ""
        task = Task(
            tenant_key=actuator.tenant_key,
            name=f"Manual: {action} {actuator.name}{detail}",
            name_de=f"Manuell: {actuator.name} {('ausschalten' if command == 'turn_off' else 'einschalten')}{detail}",
            instruction=(
                "Home Assistant not reachable — switch the actuator manually."
                if reason == "ha_unreachable"
                else "This actuator is manually operated — perform the action by hand."
            ),
            instruction_de=(
                "Home Assistant nicht erreichbar — Aktor bitte manuell schalten."
                if reason == "ha_unreachable"
                else "Dieser Aktor wird manuell bedient — Aktion bitte von Hand ausführen."
            ),
            category=TaskCategory.MAINTENANCE,
            entity_key=actuator.key,
            entity_type="actuator",
            priority=TaskPriority.HIGH,
        )
        try:
            self._task_repo.create_task(task)
        except Exception as exc:  # noqa: BLE001 — a failed fallback task must not break dispatch
            logger.warning("actuator_fallback_task_failed", actuator=actuator.key, error=str(exc))

    # ── Manual override ──────────────────────────────────────────────────

    def set_override(self, key: str, tenant_key: str, override: ManualOverride, user: str) -> ManualOverride:
        actuator = self.get_actuator(key, tenant_key)
        # SEC (REQ-018): reject an override that is already expired. The model only
        # guarantees expires_at > started_at, so a caller can still submit a cap
        # whose window lies entirely in the past; applying it would drive the
        # actuator with a cap the control loop immediately ignores. An override
        # must be in force (expires_at > now) to take effect.
        if override.expires_at <= self._now():
            raise ValidationError("Manual override expires_at must be in the future.")
        override.actuator_key = key
        override.tenant_key = tenant_key
        override.created_by = user
        # Only one active override per actuator.
        self._repo.deactivate_overrides_for_actuator(key)
        created = self._repo.create_override(override)
        # Apply the override immediately. SEC-003: derive the command through the
        # SAME decision function the control loop uses so the immediate-apply and
        # loop paths can never diverge — in particular ``override_value == 0`` maps
        # to *off* (turn_off) instead of falling through to turn_on, which would
        # leave HA on while the recorded state is off.
        command, value, _state = derive_actuator_command(override.override_value, override.override_state)
        self._dispatch(
            actuator,
            command,
            value,
            ControlEventSource.MANUAL,
            triggered_by_user=user,
        )
        return created

    def clear_override(self, key: str, tenant_key: str) -> None:
        self.get_actuator(key, tenant_key)
        self._repo.deactivate_overrides_for_actuator(key)

    def get_state(self, key: str, tenant_key: str) -> dict[str, Any]:
        actuator = self.get_actuator(key, tenant_key)
        override = self._repo.get_active_override(key)
        return {
            "actuator_key": actuator.key,
            "current_state": actuator.current_state,
            "current_value": actuator.current_value,
            "is_online": actuator.is_online,
            "last_state_change": actuator.last_state_change,
            "has_override": override is not None,
        }

    # ── Schedules ────────────────────────────────────────────────────────

    def create_schedule(self, actuator_key: str, tenant_key: str, schedule: ControlSchedule) -> ControlSchedule:
        self.get_actuator(actuator_key, tenant_key)
        schedule.actuator_key = actuator_key
        schedule.tenant_key = tenant_key
        return self._repo.create_schedule(schedule)

    def list_schedules(self, actuator_key: str, tenant_key: str) -> list[ControlSchedule]:
        self.get_actuator(actuator_key, tenant_key)
        return self._repo.list_schedules(actuator_key, tenant_key)

    def update_schedule(
        self, actuator_key: str, schedule_key: str, tenant_key: str, data: dict[str, Any]
    ) -> ControlSchedule:
        schedule = self._get_schedule(actuator_key, schedule_key, tenant_key)
        updated = schedule.model_copy(update=data)
        return self._repo.update_schedule(schedule_key, updated)

    def delete_schedule(self, actuator_key: str, schedule_key: str, tenant_key: str) -> None:
        self._get_schedule(actuator_key, schedule_key, tenant_key)
        self._repo.delete_schedule(schedule_key)

    def toggle_schedule(self, actuator_key: str, schedule_key: str, tenant_key: str) -> ControlSchedule:
        schedule = self._get_schedule(actuator_key, schedule_key, tenant_key)
        updated = schedule.model_copy(update={"is_active": not schedule.is_active})
        return self._repo.update_schedule(schedule_key, updated)

    def _get_schedule(self, actuator_key: str, schedule_key: str, tenant_key: str) -> ControlSchedule:
        self.get_actuator(actuator_key, tenant_key)
        schedule = self._repo.get_schedule_or_raise(schedule_key)
        verify_tenant_ownership(schedule, tenant_key, "ControlSchedule")
        if schedule.actuator_key != actuator_key:
            raise ValidationError("ControlSchedule does not belong to this actuator.")
        return schedule

    # ── Rules ────────────────────────────────────────────────────────────

    def create_rule(self, actuator_key: str, tenant_key: str, rule: ControlRule) -> ControlRule:
        self.get_actuator(actuator_key, tenant_key)
        rule.actuator_key = actuator_key
        rule.tenant_key = tenant_key
        return self._repo.create_rule(rule)

    def list_rules(self, actuator_key: str, tenant_key: str) -> list[ControlRule]:
        self.get_actuator(actuator_key, tenant_key)
        return self._repo.list_rules(actuator_key, tenant_key)

    def list_rules_for_tenant(
        self,
        tenant_key: str,
        sensor_parameter: str | None = None,
        is_active: bool | None = None,
        is_safety: bool | None = None,
    ) -> list[ControlRule]:
        return self._repo.list_rules_for_tenant(tenant_key, sensor_parameter, is_active, is_safety)

    def update_rule(self, actuator_key: str, rule_key: str, tenant_key: str, data: dict[str, Any]) -> ControlRule:
        rule = self._get_rule(actuator_key, rule_key, tenant_key)
        updated = rule.model_copy(update=data)
        return self._repo.update_rule(rule_key, updated)

    def delete_rule(self, actuator_key: str, rule_key: str, tenant_key: str) -> None:
        self._get_rule(actuator_key, rule_key, tenant_key)
        self._repo.delete_rule(rule_key)

    def toggle_rule(self, actuator_key: str, rule_key: str, tenant_key: str) -> ControlRule:
        rule = self._get_rule(actuator_key, rule_key, tenant_key)
        updated = rule.model_copy(update={"is_active": not rule.is_active})
        return self._repo.update_rule(rule_key, updated)

    def test_rule(self, rule_key: str, tenant_key: str, sensor_readings: dict[str, float]) -> dict[str, Any]:
        """Dry-run a rule against supplied sensor readings — no side effects."""
        rule = self._repo.get_rule_or_raise(rule_key)
        verify_tenant_ownership(rule, tenant_key, "ControlRule")
        actuator = self.get_actuator(rule.actuator_key, tenant_key)
        return self._engine.test_rule(rule, actuator, sensor_readings, self._now())

    def _get_rule(self, actuator_key: str, rule_key: str, tenant_key: str) -> ControlRule:
        self.get_actuator(actuator_key, tenant_key)
        rule = self._repo.get_rule_or_raise(rule_key)
        verify_tenant_ownership(rule, tenant_key, "ControlRule")
        if rule.actuator_key != actuator_key:
            raise ValidationError("ControlRule does not belong to this actuator.")
        return rule

    # ── Control loop (used by the Celery evaluator) ──────────────────────

    def evaluate_actuator(self, actuator: Actuator, sensor_readings: dict[str, float]) -> ControlEvent | None:
        """Evaluate one actuator against its inputs and dispatch the winner."""
        rules = self._repo.list_active_rules(actuator.key or "")
        schedules = self._repo.list_active_schedules(actuator.key or "")
        override = self._repo.get_active_override(actuator.key or "")
        decision: DesiredState | None = self._engine.evaluate_actuator_state(
            actuator, rules, schedules, override, sensor_readings, self._now()
        )
        if decision is None:
            return None
        is_rule = decision.source in (ControlEventSource.RULE, ControlEventSource.SAFETY)
        is_schedule = decision.source == ControlEventSource.SCHEDULE
        # Loop path: never raise on an unsafe numeric value — skip + log so one
        # misconfigured actuator can't abort the periodic evaluation of the rest.
        return self._dispatch(
            actuator,
            decision.command,
            decision.value,
            decision.source,
            triggered_by_rule_key=decision.source_key if is_rule else None,
            triggered_by_schedule_key=decision.source_key if is_schedule else None,
            sensor_reading=decision.sensor_reading,
            on_unsafe_value="skip",
        )

    # ── Events & stats ───────────────────────────────────────────────────

    def list_events(self, actuator_key: str, tenant_key: str, offset: int = 0, limit: int = 50) -> list[ControlEvent]:
        self.get_actuator(actuator_key, tenant_key)
        return self._repo.list_events(actuator_key, tenant_key, offset, limit)

    def list_location_events(
        self, location_key: str, tenant_key: str, offset: int = 0, limit: int = 50
    ) -> list[ControlEvent]:
        self._verify_location(location_key, tenant_key)
        return self._repo.list_events_for_location(location_key, tenant_key, offset, limit)

    def get_event_stats(self, actuator_key: str, tenant_key: str) -> dict[str, Any]:
        actuator = self.get_actuator(actuator_key, tenant_key)
        events = self._repo.list_events(actuator_key, tenant_key, offset=0, limit=500)
        switch_cycles = sum(1 for e in events if e.previous_state != e.new_state)
        failures = sum(1 for e in events if not e.success)
        return {
            "actuator_key": actuator.key,
            "total_events": len(events),
            "switch_cycles": switch_cycles,
            "failures": failures,
            "power_watts": actuator.power_watts,
        }

    def get_location_energy(self, location_key: str, tenant_key: str, hours_per_day: float = 24.0) -> dict[str, Any]:
        """Rough kWh estimate from rated power and assumed daily on-time."""
        self._verify_location(location_key, tenant_key)
        actuators = self._repo.list_for_location(location_key, tenant_key)
        breakdown: list[dict[str, Any]] = []
        total_kwh = 0.0
        for actuator in actuators:
            if actuator.power_watts is None:
                continue
            dimmer = (actuator.current_value or 100.0) / 100.0 if actuator.current_state == "on" else 0.0
            daily_kwh = round(actuator.power_watts * dimmer * hours_per_day / 1000, 3)
            total_kwh += daily_kwh
            breakdown.append(
                {
                    "actuator_key": actuator.key,
                    "name": actuator.name,
                    "power_watts": actuator.power_watts,
                    "estimated_kwh_per_day": daily_kwh,
                }
            )
        return {"location_key": location_key, "total_kwh_per_day": round(total_kwh, 3), "actuators": breakdown}

    # ── Phase control profiles ───────────────────────────────────────────

    def create_profile(self, tenant_key: str, profile: PhaseControlProfile) -> PhaseControlProfile:
        profile.tenant_key = tenant_key
        return self._repo.create_profile(profile)

    def list_profiles(self, tenant_key: str, is_template: bool | None = None) -> list[PhaseControlProfile]:
        return self._repo.list_profiles(tenant_key, is_template)

    def get_profile(self, key: str, tenant_key: str) -> PhaseControlProfile:
        profile = self._repo.get_profile_or_raise(key)
        verify_tenant_ownership(profile, tenant_key, "PhaseControlProfile")
        return profile

    def update_profile(self, key: str, tenant_key: str, data: dict[str, Any]) -> PhaseControlProfile:
        profile = self.get_profile(key, tenant_key)
        updated = profile.model_copy(update=data)
        return self._repo.update_profile(key, updated)

    def delete_profile(self, key: str, tenant_key: str) -> None:
        self.get_profile(key, tenant_key)
        self._repo.delete_profile(key)

    def apply_profile(self, key: str, tenant_key: str, location_key: str) -> dict[str, Any]:
        self.get_profile(key, tenant_key)
        self._verify_location(location_key, tenant_key)
        self._repo.apply_profile_to_location(key, location_key)
        return {"profile_key": key, "location_key": location_key, "applied": True}

    # ── Home Assistant integration ───────────────────────────────────────

    def ha_status(self) -> dict[str, Any]:
        """Report HA connectivity without leaking credentials (graceful)."""
        if self._ha_client_factory is None:
            return {"configured": False, "reachable": False, "reason": "not_configured"}
        client = self._ha_client_factory()
        if client is None:
            return {"configured": False, "reachable": False, "reason": "not_configured"}
        try:
            client.list_sensor_entities()
            return {"configured": True, "reachable": True}
        except Exception as exc:  # noqa: BLE001 — status endpoint must never 500 on HA outage
            logger.warning("actuator_ha_status_failed", error=str(exc))
            return {"configured": True, "reachable": False, "reason": "unreachable"}

    def ha_entities(self) -> list[dict[str, Any]]:
        """List HA entities available for actuator mapping (empty on outage)."""
        if self._ha_client_factory is None:
            return []
        client = self._ha_client_factory()
        if client is None:
            return []
        try:
            return client.list_sensor_entities()
        except Exception as exc:  # noqa: BLE001 — degrade to empty list on HA outage
            logger.warning("actuator_ha_entities_failed", error=str(exc))
            return []

    # ── Emergency stop ───────────────────────────────────────────────────

    def emergency_stop(self, tenant_key: str, scenario: str, user: str) -> dict[str, Any]:
        """Switch off the actuators affected by a predefined emergency scenario."""
        affected_types = _EMERGENCY_SCENARIOS.get(scenario)
        if affected_types is None:
            raise ValidationError(f"Unknown emergency-stop scenario '{scenario}'.")
        actuators = self._repo.list_for_tenant(tenant_key)
        stopped: list[str] = []
        forced_on: list[str] = []
        failed: list[str] = []
        for actuator in actuators:
            atype = actuator.actuator_type.value
            # Per-actuator isolation (bulkhead): one repository/dispatch failure
            # must never abort stopping the remaining safety-relevant devices.
            try:
                if atype in affected_types.get("off", ()):
                    self._dispatch(
                        actuator,
                        "turn_off",
                        None,
                        ControlEventSource.SAFETY,
                        triggered_by_user=user,
                        on_unsafe_value="skip",
                    )
                    stopped.append(actuator.key or "")
                elif atype in affected_types.get("on", ()):
                    # Force the device on. Prefer the max numeric level, but only when
                    # a validated envelope exists; otherwise force plain ON so the
                    # unbounded-numeric invariant (SEC-001) still holds.
                    if actuator.min_value is not None and actuator.max_value is not None:
                        self._dispatch(
                            actuator,
                            "set_value",
                            100.0,
                            ControlEventSource.SAFETY,
                            triggered_by_user=user,
                            on_unsafe_value="skip",
                        )
                    else:
                        self._dispatch(
                            actuator,
                            "turn_on",
                            None,
                            ControlEventSource.SAFETY,
                            triggered_by_user=user,
                            on_unsafe_value="skip",
                        )
                    forced_on.append(actuator.key or "")
            except Exception as exc:  # noqa: BLE001 — isolate one device's failure from the rest
                logger.warning(
                    "actuator_emergency_stop_failed",
                    actuator=actuator.key,
                    scenario=scenario,
                    error=str(exc),
                )
                failed.append(actuator.key or "")
        return {"scenario": scenario, "stopped": stopped, "forced_on": forced_on, "failed": failed}


# Predefined emergency-stop scenarios (REQ-018 §1).
_EMERGENCY_SCENARIOS: dict[str, dict[str, tuple[str, ...]]] = {
    "water_leak": {"off": ("pump", "irrigation_valve", "dosing_pump")},
    "co2_leak": {"off": ("co2_doser",), "on": ("exhaust_fan",)},
    "fire_alarm": {
        "off": (
            "light",
            "heater",
            "co2_doser",
            "pump",
            "irrigation_valve",
            "dosing_pump",
            "humidifier",
            "dehumidifier",
            "cooler",
            "chiller",
            "air_pump",
            "uv_sterilizer",
            "fogger",
            "exhaust_fan",
            "circulation_fan",
        )
    },
}

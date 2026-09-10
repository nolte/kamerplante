import time
from datetime import UTC, datetime, timedelta

import structlog

from app.common.exceptions import NotFoundError
from app.config.settings import settings
from app.data_access.external.ha_client import HomeAssistantClient
from app.domain.engines.frost_warning_engine import (
    evaluate_forecast_frost_warning,
    evaluate_frost_warning,
    pick_air_temperature,
)
from app.domain.engines.live_state import derive_single_value_view
from app.domain.interfaces.observation_repository import IObservationRepository
from app.domain.interfaces.sensor_repository import ISensorRepository
from app.domain.interfaces.site_repository import ISiteRepository
from app.domain.interfaces.weather_forecast_repository import IWeatherForecastRepository
from app.domain.models.sensor import Sensor
from app.domain.models.weather import WeatherForecast

logger = structlog.get_logger(__name__)

#: The parent keys a :class:`Sensor` may hang off — at most one is ever set
#: (``Sensor._at_most_one_parent``). A sensor has no ``tenant_key`` of its own,
#: so exactly one of these is its tenant anchor, and every write route must name
#: which one it verified (#1339).
SENSOR_PARENT_FIELDS = ("tank_key", "site_key", "location_key")


class SensorService:
    def __init__(
        self,
        repo: ISensorRepository,
        ha_client: HomeAssistantClient | None,
        weather_forecast_repo: IWeatherForecastRepository | None = None,
        site_repo: ISiteRepository | None = None,
        observation_repo: IObservationRepository | None = None,
    ) -> None:
        self._repo = repo
        self._ha_client = ha_client
        # Optional (Issue #392): the proactive forecast path degrades gracefully
        # when either is absent — the reactive path never depends on them.
        self._weather_forecast_repo = weather_forecast_repo
        self._site_repo = site_repo
        # The time-series side of a sensor (#1339 review). Optional because the
        # TimescaleDB connection is optional: without it the repository is the
        # null implementation, and every other SensorService caller predates
        # this argument. Deleting a sensor must still take its readings with it
        # — see :meth:`delete_sensor`.
        self._observation_repo = observation_repo

    def create_sensor(self, sensor: Sensor) -> Sensor:
        return self._repo.create(sensor)

    def get_sensors_for_tank(self, tank_key: str) -> list[Sensor]:
        return self._repo.find_by_tank(tank_key)

    def get_sensors_for_site(self, site_key: str) -> list[Sensor]:
        return self._repo.find_by_site(site_key)

    def get_sensors_for_location(self, location_key: str) -> list[Sensor]:
        return self._repo.find_by_location(location_key)

    def get_sensor(self, key: str) -> Sensor | None:
        return self._repo.get(key)

    def get_sensor_in_parent(self, key: str, *, parent_field: str, parent_key: str) -> Sensor:
        """Load a sensor, refusing one that hangs off a different parent (#1339).

        A ``Sensor`` carries no ``tenant_key``; its only tenant anchor is the
        tank / site / location it is attached to, which the route has already
        verified against the caller's tenant. That verification is worth nothing
        unless the sensor is then checked to actually *belong* to that parent —
        otherwise a caller pairs their own tank key with a foreign sensor key and
        writes across the tenant boundary. The check therefore lives here, in the
        service, rather than being opted into at each of the six call sites: that
        is the sibling-drift failure of #948, where two of four routes of one
        shape were repaired and the other two stayed open for months.

        ``parent_field`` and ``parent_key`` are keyword-only and have no
        defaults, so no caller can reach this method without naming the anchor.

        Args:
            key: Document key of the sensor.
            parent_field: One of ``tank_key``, ``site_key``, ``location_key``.
            parent_key: Document key of that parent, already tenant-verified.

        Returns:
            The sensor.

        Raises:
            ValueError: If ``parent_field`` is not a parent field of ``Sensor``.
            NotFoundError: If no such sensor exists, or it hangs off another
                parent. Both are deliberately the *same* answer: a
                distinguishable "forbidden" would confirm that the key exists
                somewhere else in the installation.
        """
        if parent_field not in SENSOR_PARENT_FIELDS:
            msg = f"parent_field must be one of {SENSOR_PARENT_FIELDS}, got {parent_field!r}"
            raise ValueError(msg)
        sensor = self._repo.get(key)
        if sensor is None or getattr(sensor, parent_field) != parent_key:
            raise NotFoundError("Sensor", key)
        return sensor

    def update_sensor(self, key: str, changes: dict, *, parent_field: str, parent_key: str) -> Sensor:
        """Apply ``changes`` to a sensor of the given parent (REQ-005, #1339).

        Only the fields named in ``changes`` are written, and the parent keys are
        skipped even if present, so an update can never re-parent a sensor — and
        therefore never move one into another tenant.

        Args:
            key: Document key of the sensor.
            changes: Allow-listed field/value pairs, from a validated
                ``SensorUpdate`` rather than a raw request body.
            parent_field: One of ``tank_key``, ``site_key``, ``location_key``.
            parent_key: Document key of that parent, already tenant-verified.

        Returns:
            The updated sensor.
        """
        sensor = self.get_sensor_in_parent(key, parent_field=parent_field, parent_key=parent_key)
        for field, value in changes.items():
            if field in SENSOR_PARENT_FIELDS:
                continue
            setattr(sensor, field, value)
        return self._repo.update(key, sensor)

    def delete_sensor(self, key: str, *, parent_field: str, parent_key: str, tenant_key: str) -> bool:
        """Delete a sensor with its edges *and its readings* (REQ-005, #1339).

        The readings are not housekeeping. A sensor's TimescaleDB series is
        personal data under NFR-011: CO2 and motion series reveal when somebody
        was in the room, which is why REQ-025 §DSFA names exactly those. Deleting
        the sensor document while its series stays behind leaves that trace with
        nothing left in the UI pointing at it — undiscoverable, and therefore
        undeletable through any surface a user can reach.

        ``ObservationService.delete_readings_for_sensor`` and
        ``IObservationRepository.delete_by_sensor`` had existed with **zero**
        callers; this is the caller. The delete is ordered readings-first, so a
        failure there aborts before the document goes and the operation stays
        retryable; the other order would strand the series permanently.

        A service assembled without an observation repository (the DI factory
        always supplies one — the null implementation when TimescaleDB is absent)
        skips the readings step rather than failing the delete.

        Args:
            key: Document key of the sensor.
            parent_field: One of ``tank_key``, ``site_key``, ``location_key``.
            parent_key: Document key of that parent, already tenant-verified.
            tenant_key: Owning tenant, for the tenant-scoped readings delete.

        Returns:
            ``True`` when the document was removed.
        """
        self.get_sensor_in_parent(key, parent_field=parent_field, parent_key=parent_key)
        if self._observation_repo is not None:
            deleted = self._observation_repo.delete_by_sensor(key, tenant_key)
            logger.info("sensor_readings_deleted", sensor_key=key, readings=deleted)
        return self._repo.delete(key)

    def get_live_state_for_sensors(self, sensors: list[Sensor], *, deadline: float | None = None) -> dict:
        """Read-through live query for a list of sensors — NO persistence.

        The map is keyed by **sensor**, so nothing collapses: two thermometers at
        opposite ends of a tent — exactly what a grower installs when a gradient
        is suspected — are two entries (Issue #977 items 1 and 2). The
        ``ha_live_reading_discarded`` warning that item 3 added to report the
        loss is gone with it: there is no longer a reading to discard, and a
        warning that can never fire is worse than none. What the derived view
        leaves out it reports in-band instead, per entry, via ``sensor_count``.

        Args:
            sensors: The sensors to read. Those without an ``ha_entity_id`` are
                skipped — they have nothing live to read.
            deadline: Optional :func:`time.monotonic` instant after which no
                further entity is read. ``None`` (the default) keeps the previous
                behaviour: every sensor is read with the client's own timeout, so
                the worst case grows with the number of entities. A caller on a
                latency budget — the diary environment capture writes an entry
                behind this read (REQ-013 §2.3a) — passes a deadline, and each
                remaining call is then capped by the time left, so the whole loop
                stays inside it.

        Returns:
            A mapping with four keys:

            * ``readings`` — **the full truth**, keyed by *sensor key*: one entry
              per sensor that answered, each carrying its own ``sensor_key``,
              ``sensor_name`` and ``metric_type``. Two sensors reporting the same
              metric on one location are both present; nothing collapses
              (Issue #977).
            * ``values`` — the derived single-value view keyed by ``metric_type``,
              for consumers that want one number per metric. The freshest reading
              wins and the entry says how many there were; see
              :mod:`app.domain.engines.live_state` for the rule and its rationale.
            * ``errors`` — one entry per entity that failed. An exhausted
              ``deadline`` is reported here as ``error: "timeout"``, never raised:
              the caller's job is to record an incomplete read, not to abort.
            * ``source`` — ``ha_live``, or ``unavailable`` when Home Assistant is
              not configured at all.
        """
        if not self._ha_client:
            return {
                "readings": {},
                "values": {},
                "errors": [],
                "source": "unavailable",
                "message": "Home Assistant not configured",
            }

        readings: dict = {}
        errors: list[dict] = []
        for sensor in sensors:
            if not sensor.ha_entity_id:
                continue
            remaining: float | None = None
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    errors.append({"entity_id": sensor.ha_entity_id, "error": "timeout"})
                    continue
            try:
                result = self._ha_client.get_state(sensor.ha_entity_id, timeout=remaining)
                if result and result["value"] is not None:
                    # The document key identifies the sensor. A ``Sensor`` without
                    # one never comes out of a repository — every route loads them
                    # through one — so it exists only in-process; it is filed under
                    # its entity id, the only identity it has, and its entry's
                    # ``sensor_key`` stays honestly ``None``.
                    readings[sensor.key or sensor.ha_entity_id] = {
                        "sensor_key": sensor.key,
                        "sensor_name": sensor.name,
                        "metric_type": sensor.metric_type,
                        "value": result["value"],
                        "last_changed": result["last_changed"],
                        # ``last_changed`` only moves when the state *string*
                        # changes, so it cannot tell a constant live reading from
                        # a dead sensor. ``last_reported`` can — the staleness
                        # bound of the diary snapshot and the freshness rule of
                        # the derived view both need it.
                        "last_updated": result.get("last_updated"),
                        "last_reported": result.get("last_reported"),
                        "entity_id": sensor.ha_entity_id,
                        "unit": result["unit"],
                    }
            except Exception as exc:
                logger.warning(
                    "ha_live_query_failed",
                    entity_id=sensor.ha_entity_id,
                    error=str(exc),
                )
                errors.append(
                    {
                        "entity_id": sensor.ha_entity_id,
                        "error": str(exc),
                    }
                )

        return {
            "readings": readings,
            "values": derive_single_value_view(readings),
            "errors": errors,
            "source": "ha_live",
        }

    def get_ha_entities(self) -> list[dict]:
        """Return HA sensor entities with inferred metric_type and suggested name."""
        if not self._ha_client:
            return []

        device_class_map = {
            "ph": "ph",
            "ec": "ec_ms",
            "electrical_conductivity": "ec_ms",
            "temperature": "water_temp_celsius",
            "humidity": "humidity_percent",
            "carbon_dioxide": "co2_ppm",
            "volatile_organic_compounds": "co2_ppm",
        }
        unit_map = {
            "mS/cm": "ec_ms",
            "µS/cm": "ec_ms",
            "mS": "ec_ms",
            "°C": "water_temp_celsius",
            "°F": "water_temp_celsius",
            "%": "fill_level_percent",
            "ppm": "tds_ppm",
            "pH": "ph",
        }

        entities = self._ha_client.list_sensor_entities()
        result = []
        for e in entities:
            if e["entity_id"].startswith("sensor.kp_"):
                continue
            device_class = (e.get("device_class") or "").lower()
            unit = e.get("unit_of_measurement") or ""
            friendly = e.get("friendly_name") or e["entity_id"]

            suggested_metric = device_class_map.get(device_class) or unit_map.get(unit)

            result.append(
                {
                    "entity_id": e["entity_id"],
                    "friendly_name": friendly,
                    "unit_of_measurement": e.get("unit_of_measurement"),
                    "device_class": e.get("device_class"),
                    "state": e.get("state"),
                    "suggested_metric_type": suggested_metric,
                    "suggested_name": friendly,
                }
            )

        result.sort(key=lambda x: (x["suggested_metric_type"] is None, x["friendly_name"].lower()))
        return result

    def get_live_state(self, tank_key: str) -> dict:
        """Read-through live query for a tank — NO persistence."""
        sensors = self._repo.find_by_tank(tank_key)
        return self.get_live_state_for_sensors(sensors)

    def get_location_frost_warning(
        self,
        location_key: str,
        threshold_celsius: float | None = None,
    ) -> dict:
        """Compute the reactive frost-warning state for a location — NO persistence.

        Backs the Home Assistant ``binary_sensor.kp_{location}_frost_warning``
        entity. The reactive ``frost_warning`` is derived from the location's most
        recent ambient temperature reading (read-through via Home Assistant) and
        the configured threshold; when no reading is available it is ``None``
        (Home Assistant reports ``unknown``) rather than a fabricated ``False``.

        The proactive forecast early-warning is NOT read here (Issue #409, F1): a
        site with N locations would otherwise trigger N identical site-level
        forecast reads on the HA poll hot path. Home Assistant reads the frost
        forecast once per site via ``GET /sites/{site_key}/weather-forecast``.

        The temperature is picked from the **full** ``readings`` map, not from the
        derived single-value view: with two thermometers at opposite ends of one
        location the coldest is the one that matters, and a warning that missed
        frost at one end because the other end reported more recently would be a
        warning that costs a crop (Issue #977).
        """
        threshold = threshold_celsius if threshold_celsius is not None else settings.frost_warning_threshold_celsius

        sensors = self._repo.find_by_location(location_key)
        live = self.get_live_state_for_sensors(sensors)
        temperature, entity_id = pick_air_temperature(live["readings"])
        frost_warning = evaluate_frost_warning(temperature, threshold)

        if live["source"] == "unavailable":
            source = "unavailable"
        elif temperature is None:
            source = "no_temperature"
        else:
            source = "ha_live"

        return {
            "location_key": location_key,
            "frost_warning": frost_warning,
            "temperature_celsius": temperature,
            "threshold_celsius": threshold,
            "source": source,
            "entity_id": entity_id,
        }

    def get_site_weather_forecast(self, site_key: str, tenant_key: str) -> dict:
        """Return the in-horizon daily forecast for a site plus the frost summary.

        Backs the dashboard/per-site ``WeatherForecastWidget`` (Issue #392, R7):
        the in-horizon daily forecast rows (with ``source`` / ``data_kind``
        provenance) and the proactive frost early-warning summary. Graceful: no
        forecast repo, ``weather_enabled`` off, unknown/foreign site, no
        coordinates, or no forecast records all yield an empty ``forecasts`` list
        with ``None`` summary fields — never a 500.
        """
        empty: dict = {
            "site_key": site_key,
            "forecasts": [],
            "forecast_frost_warning": None,
            "forecast_min_temperature": None,
            "forecast_expected_date": None,
            "forecast_source": None,
        }
        try:
            forecasts = self._load_site_forecasts(site_key, tenant_key)
            if forecasts is None:
                return empty

            today = datetime.now(UTC).date()
            horizon_days = settings.frost_forecast_horizon_days
            horizon_end = today + timedelta(days=horizon_days - 1)
            in_horizon = sorted(
                (record for record in forecasts if today <= record.forecast_date <= horizon_end),
                key=lambda record: record.forecast_date,
            )
            summary = evaluate_forecast_frost_warning(
                forecasts,
                settings.frost_forecast_threshold_celsius,
                horizon_days,
                today,
            )
            return {
                "site_key": site_key,
                "forecasts": [self._forecast_day_dict(record) for record in in_horizon],
                "forecast_frost_warning": summary["predicted"],
                "forecast_min_temperature": summary["min_temp"],
                "forecast_expected_date": summary["expected_date"],
                "forecast_source": summary["source"],
            }
        except Exception as exc:
            logger.warning("site_weather_forecast_failed", site_key=site_key, error=str(exc))
            return empty

    @staticmethod
    def _forecast_day_dict(record: WeatherForecast) -> dict:
        return {
            "forecast_date": record.forecast_date,
            "temp_min_c": record.temp_min_c,
            "temp_max_c": record.temp_max_c,
            "precipitation_mm": record.precipitation_mm,
            "wind_speed_kmh": record.wind_speed_kmh,
            "humidity_percent": record.humidity_percent,
            "weather_code": record.weather_code,
            "source": record.source,
            "data_kind": record.data_kind,
        }

    def _load_site_forecasts(self, site_key: str | None, tenant_key: str) -> list[WeatherForecast] | None:
        """Load the persisted daily forecasts for a site, or ``None`` when the
        proactive path is unavailable (repo missing, weather disabled, no
        ``site_key``, unknown/foreign site, or a site without coordinates).

        Tenant isolation (R10): the forecast read is scoped by ``tenant_key``, and
        when the site repo is available the site's own ``tenant_key`` is verified
        fail-closed so a foreign site key cannot probe the proactive path. The
        comparison is unconditional: an empty ``tenant_key`` (light mode) only
        matches a site whose ``tenant_key`` is likewise empty — never a bypass.
        """
        if self._weather_forecast_repo is None or not settings.weather_enabled or not site_key:
            return None
        if self._site_repo is not None:
            site = self._site_repo.get_site_by_key(site_key)
            if site is None or site.gps_coordinates is None:
                return None
            if site.tenant_key != tenant_key:
                return None
        return self._weather_forecast_repo.find_by_site(site_key, tenant_key)

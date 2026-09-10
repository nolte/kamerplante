from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
import structlog.testing

from app.common.exceptions import NotFoundError
from app.config.settings import settings
from app.domain.models.sensor import Sensor
from app.domain.models.site import Site
from app.domain.models.weather import WeatherForecast
from app.domain.services.sensor_service import SensorService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_ha_client():
    return MagicMock()


@pytest.fixture
def service(mock_repo, mock_ha_client):
    return SensorService(mock_repo, mock_ha_client)


@pytest.fixture
def service_no_ha(mock_repo):
    return SensorService(mock_repo, None)


class TestGetLiveState:
    def test_no_ha_client(self, service_no_ha, mock_repo):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="EC", metric_type="ec_ms", ha_entity_id="sensor.ec", tank_key="t1"),
        ]
        result = service_no_ha.get_live_state("t1")
        assert result["source"] == "unavailable"
        assert result["values"] == {}
        assert result["message"] == "Home Assistant not configured"

    def test_no_sensors(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = []
        result = service.get_live_state("t1")
        assert result["source"] == "ha_live"
        assert result["values"] == {}
        assert result["errors"] == []

    def test_success(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="EC Sensor", metric_type="ec_ms", ha_entity_id="sensor.tank_ec", tank_key="t1"),
        ]
        mock_ha_client.get_state.return_value = {
            "value": 1.45,
            "last_changed": "2026-03-01T10:00:00Z",
            "entity_id": "sensor.tank_ec",
            "unit": "mS/cm",
        }
        result = service.get_live_state("t1")
        assert result["source"] == "ha_live"
        assert "ec_ms" in result["values"]
        assert result["values"]["ec_ms"]["value"] == 1.45
        assert result["values"]["ec_ms"]["entity_id"] == "sensor.tank_ec"
        assert result["values"]["ec_ms"]["unit"] == "mS/cm"
        assert result["errors"] == []

    def test_ha_error(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="EC Sensor", metric_type="ec_ms", ha_entity_id="sensor.tank_ec", tank_key="t1"),
        ]
        mock_ha_client.get_state.side_effect = Exception("Connection refused")
        result = service.get_live_state("t1")
        assert result["source"] == "ha_live"
        assert result["values"] == {}
        assert len(result["errors"]) == 1
        assert result["errors"][0]["entity_id"] == "sensor.tank_ec"
        assert "Connection refused" in result["errors"][0]["error"]

    def test_entity_unavailable(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="EC Sensor", metric_type="ec_ms", ha_entity_id="sensor.tank_ec", tank_key="t1"),
        ]
        mock_ha_client.get_state.return_value = {
            "value": None,
            "last_changed": "2026-03-01T10:00:00Z",
            "entity_id": "sensor.tank_ec",
            "unit": None,
        }
        result = service.get_live_state("t1")
        assert result["source"] == "ha_live"
        assert result["values"] == {}  # value was None, not included
        assert result["errors"] == []

    def test_multiple_sensors(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="EC", metric_type="ec_ms", ha_entity_id="sensor.ec", tank_key="t1"),
            Sensor(name="pH", metric_type="ph", ha_entity_id="sensor.ph", tank_key="t1"),
        ]
        mock_ha_client.get_state.side_effect = [
            {"value": 1.2, "last_changed": "2026-03-01T10:00:00Z", "entity_id": "sensor.ec", "unit": "mS/cm"},
            {"value": 6.1, "last_changed": "2026-03-01T10:01:00Z", "entity_id": "sensor.ph", "unit": "pH"},
        ]
        result = service.get_live_state("t1")
        assert len(result["values"]) == 2
        assert result["values"]["ec_ms"]["value"] == 1.2
        assert result["values"]["ph"]["value"] == 6.1

    def test_sensor_without_entity_id_skipped(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_tank.return_value = [
            Sensor(name="MQTT only", metric_type="ec_ms", mqtt_topic="tank/ec", tank_key="t1"),
        ]
        result = service.get_live_state("t1")
        assert result["source"] == "ha_live"
        assert result["values"] == {}
        mock_ha_client.get_state.assert_not_called()


class TestCreateSensor:
    def test_create(self, service, mock_repo):
        sensor = Sensor(name="EC", metric_type="ec_ms", tank_key="t1")
        mock_repo.create.return_value = Sensor(
            _key="s1",
            name="EC",
            metric_type="ec_ms",
            tank_key="t1",
        )
        result = service.create_sensor(sensor)
        assert result.key == "s1"
        mock_repo.create.assert_called_once_with(sensor)


class TestDeleteSensor:
    def test_delete(self, service, mock_repo):
        mock_repo.get.return_value = Sensor(_key="s1", name="EC", metric_type="ec_ms", tank_key="t1")
        mock_repo.delete.return_value = True
        result = service.delete_sensor("s1", parent_field="tank_key", parent_key="t1")
        assert result is True
        mock_repo.delete.assert_called_once_with("s1")


class TestParentScopedWrites:
    """A sensor write is anchored on its parent, because it has no tenant (#1339).

    ``Sensor`` carries no ``tenant_key``; the tank / site / location it hangs off
    is its only tenant anchor, and the route verifies *that* against the caller.
    The check that the sensor actually belongs to the verified parent therefore
    has to happen here — otherwise a caller pairs their own tank key with a
    foreign sensor key and the route's verification proves nothing.

    A hand-written repository double rather than ``MagicMock``: a mock answers
    ``get`` with another mock whose ``tank_key`` is a mock too, which compares
    unequal to everything and would make the guard *look* effective no matter
    what it did (#1155).
    """

    class FakeRepo:
        def __init__(self, sensors: dict[str, Sensor]) -> None:
            self._sensors = sensors
            self.deleted: list[str] = []
            self.updated: list[tuple[str, Sensor]] = []

        def get(self, key: str) -> Sensor | None:
            return self._sensors.get(key)

        def update(self, key: str, sensor: Sensor) -> Sensor:
            self.updated.append((key, sensor))
            self._sensors[key] = sensor
            return sensor

        def delete(self, key: str) -> bool:
            self.deleted.append(key)
            return self._sensors.pop(key, None) is not None

    @pytest.fixture
    def scoped(self):
        repo = self.FakeRepo(
            {
                "mine": Sensor(_key="mine", name="EC", metric_type="ec_ms", tank_key="my-tank"),
                "theirs": Sensor(_key="theirs", name="EC", metric_type="ec_ms", tank_key="their-tank"),
                "on-a-site": Sensor(_key="on-a-site", name="Air", metric_type="temperature_celsius", site_key="s1"),
            }
        )
        return SensorService(repo, None), repo

    def test_update_writes_only_the_named_fields(self, scoped):
        service, repo = scoped

        updated = service.update_sensor(
            "mine", {"name": "EC (new)", "is_active": False}, parent_field="tank_key", parent_key="my-tank"
        )

        assert (updated.name, updated.is_active) == ("EC (new)", False)
        assert updated.metric_type == "ec_ms"
        assert repo.updated[0][0] == "mine"

    def test_update_cannot_re_parent_a_sensor(self, scoped):
        """Re-parenting would move a sensor into another tenant in one PUT."""
        service, repo = scoped

        updated = service.update_sensor(
            "mine",
            {"name": "EC", "tank_key": "their-tank", "site_key": "s1"},
            parent_field="tank_key",
            parent_key="my-tank",
        )

        assert (updated.tank_key, updated.site_key) == ("my-tank", None)

    def test_a_foreign_sensor_is_refused_exactly_like_a_missing_one(self, scoped):
        """Same exception, same message — a distinguishable 403 would confirm the key exists."""
        service, repo = scoped

        with pytest.raises(NotFoundError) as foreign:
            service.delete_sensor("theirs", parent_field="tank_key", parent_key="my-tank")
        with pytest.raises(NotFoundError) as missing:
            service.delete_sensor("no-such-key", parent_field="tank_key", parent_key="my-tank")

        assert str(foreign.value).replace("theirs", "X") == str(missing.value).replace("no-such-key", "X")
        assert repo.deleted == []

    def test_a_sensor_of_another_parent_type_is_refused(self, scoped):
        """A site sensor is not reachable through a tank route, and vice versa."""
        service, _repo = scoped

        with pytest.raises(NotFoundError):
            service.update_sensor("on-a-site", {"name": "x"}, parent_field="tank_key", parent_key="s1")

    def test_the_parent_field_must_be_one_a_sensor_has(self, scoped):
        """Fail loudly rather than compare against an attribute that is not there."""
        service, _repo = scoped

        with pytest.raises(ValueError, match="parent_field"):
            service.get_sensor_in_parent("mine", parent_field="tenant_key", parent_key="t1")


class TestGetSensorsForSite:
    def test_get_sensors_for_site(self, service, mock_repo):
        mock_repo.find_by_site.return_value = [
            Sensor(name="Weather Station", metric_type="temperature_celsius", site_key="site1"),
        ]
        result = service.get_sensors_for_site("site1")
        assert len(result) == 1
        assert result[0].site_key == "site1"
        mock_repo.find_by_site.assert_called_once_with("site1")

    def test_get_sensors_for_site_empty(self, service, mock_repo):
        mock_repo.find_by_site.return_value = []
        result = service.get_sensors_for_site("site1")
        assert result == []


class TestGetSensorsForLocation:
    def test_get_sensors_for_location(self, service, mock_repo):
        mock_repo.find_by_location.return_value = [
            Sensor(name="Tent Climate", metric_type="humidity_percent", location_key="loc1"),
        ]
        result = service.get_sensors_for_location("loc1")
        assert len(result) == 1
        assert result[0].location_key == "loc1"
        mock_repo.find_by_location.assert_called_once_with("loc1")


class TestGetLiveStateForSensors:
    def test_direct_sensor_list(self, service, mock_ha_client):
        sensors = [
            Sensor(name="Temp", metric_type="temperature_celsius", ha_entity_id="sensor.outdoor_temp", site_key="s1"),
        ]
        mock_ha_client.get_state.return_value = {
            "value": 22.5,
            "last_changed": "2026-03-01T12:00:00Z",
            "entity_id": "sensor.outdoor_temp",
            "unit": "°C",
        }
        result = service.get_live_state_for_sensors(sensors)
        assert result["source"] == "ha_live"
        assert result["values"]["temperature_celsius"]["value"] == 22.5

    def test_no_ha_client_returns_unavailable(self, service_no_ha):
        sensors = [
            Sensor(name="Temp", metric_type="temperature_celsius", ha_entity_id="sensor.temp", site_key="s1"),
        ]
        result = service_no_ha.get_live_state_for_sensors(sensors)
        assert result["source"] == "unavailable"
        assert result["message"] == "Home Assistant not configured"
        # Both maps exist and are empty — a consumer that reads ``readings``
        # unconditionally must not have to special-case the unconfigured case.
        assert result["readings"] == {}
        assert result["values"] == {}


class TestTwoSensorsOfOneMetric:
    """Issue #977 — the reading belongs to the sensor, not to the metric.

    A grower who hangs a second thermometer at the other end of a tent has done
    so *because* the two ends differ. Every one of these assertions failed before
    the live-state map was re-keyed on the sensor: the map physically held one
    entry per metric.
    """

    def _two_thermometers(self) -> list[Sensor]:
        return [
            Sensor(
                _key="s-front",
                name="Zelt vorne",
                metric_type="temperature_celsius",
                ha_entity_id="sensor.zelt_vorne",
                location_key="loc1",
            ),
            Sensor(
                _key="s-back",
                name="Zelt hinten",
                metric_type="temperature_celsius",
                ha_entity_id="sensor.zelt_hinten",
                location_key="loc1",
            ),
        ]

    def _states(self) -> list[dict]:
        return [
            {
                "value": 21.4,
                "last_changed": "2026-08-06T05:50:00Z",
                "last_reported": "2026-08-06T05:50:00Z",
                "entity_id": "sensor.zelt_vorne",
                "unit": "°C",
            },
            {
                "value": 23.9,
                "last_changed": "2026-08-06T05:59:00Z",
                "last_reported": "2026-08-06T05:59:00Z",
                "entity_id": "sensor.zelt_hinten",
                "unit": "°C",
            },
        ]

    def test_both_readings_survive(self, service, mock_ha_client):
        mock_ha_client.get_state.side_effect = self._states()

        result = service.get_live_state_for_sensors(self._two_thermometers())

        assert set(result["readings"]) == {"s-front", "s-back"}
        assert result["readings"]["s-front"]["value"] == 21.4
        assert result["readings"]["s-back"]["value"] == 23.9

    def test_each_reading_names_its_own_sensor(self, service, mock_ha_client):
        mock_ha_client.get_state.side_effect = self._states()

        result = service.get_live_state_for_sensors(self._two_thermometers())

        front = result["readings"]["s-front"]
        assert front["sensor_key"] == "s-front"
        assert front["sensor_name"] == "Zelt vorne"
        assert front["metric_type"] == "temperature_celsius"
        assert front["entity_id"] == "sensor.zelt_vorne"

    def test_the_derived_view_shows_one_and_admits_it(self, service, mock_ha_client):
        mock_ha_client.get_state.side_effect = self._states()

        result = service.get_live_state_for_sensors(self._two_thermometers())

        entry = result["values"]["temperature_celsius"]
        assert entry["value"] == 23.9  # the freshest of the two
        assert entry["sensor_key"] == "s-back"
        assert entry["sensor_count"] == 2
        assert entry["superseded_sensor_keys"] == ["s-front"]

    def test_a_single_sensor_per_metric_is_unchanged(self, service, mock_ha_client):
        mock_ha_client.get_state.side_effect = self._states()[:1]
        sensors = self._two_thermometers()[:1]

        result = service.get_live_state_for_sensors(sensors)

        entry = result["values"]["temperature_celsius"]
        assert entry["value"] == 21.4
        assert entry["entity_id"] == "sensor.zelt_vorne"
        assert entry["unit"] == "°C"
        assert entry["last_changed"] == "2026-08-06T05:50:00Z"
        assert entry["sensor_count"] == 1
        assert entry["superseded_sensor_keys"] == []
        assert list(result["readings"]) == ["s-front"]

    def test_a_sensor_without_a_key_is_filed_under_its_entity_id(self, service, mock_ha_client):
        # Only constructible in-process: every route loads sensors from a
        # repository, which always supplies ``_key``. It must still not vanish.
        mock_ha_client.get_state.side_effect = self._states()[:1]
        sensors = [
            Sensor(name="Zelt vorne", metric_type="temperature_celsius", ha_entity_id="sensor.zelt_vorne"),
        ]

        result = service.get_live_state_for_sensors(sensors)

        assert list(result["readings"]) == ["sensor.zelt_vorne"]
        assert result["readings"]["sensor.zelt_vorne"]["sensor_key"] is None

    def test_frost_warning_uses_the_coldest_of_the_two(self, service, mock_repo, mock_ha_client):
        # The consumer-specific answer (Issue #977, item 2): the warm end must not
        # silence the cold one. The cold sensor is deliberately the *first* and the
        # *older* of the two, so neither the old last-wins map nor the freshest-wins
        # derived view would have reported it — both would say "no frost".
        mock_repo.find_by_location.return_value = self._two_thermometers()
        mock_ha_client.get_state.side_effect = [
            {
                "value": 1.1,
                "last_changed": "2026-08-06T05:50:00Z",
                "last_reported": "2026-08-06T05:50:00Z",
                "entity_id": "sensor.zelt_vorne",
                "unit": "°C",
            },
            {
                "value": 8.0,
                "last_changed": "2026-08-06T05:59:00Z",
                "last_reported": "2026-08-06T05:59:00Z",
                "entity_id": "sensor.zelt_hinten",
                "unit": "°C",
            },
        ]

        result = service.get_location_frost_warning("loc1")

        assert result["frost_warning"] is True
        assert result["temperature_celsius"] == 1.1
        assert result["entity_id"] == "sensor.zelt_vorne"


class TestNoReadingIsDiscarded:
    """Issue #977 — what item 3 could only *report*, items 1 and 2 prevent.

    #981 made the collapse visible: every reading the metric-keyed map threw
    away emitted an ``ha_live_reading_discarded`` warning. Re-keying on the
    sensor removes the throwing-away, and with it the warning — a log line for
    an event that can no longer happen is worse than no line, because the next
    reader takes its absence for evidence.

    These are the cases that warning covered, restated as the property that
    replaced it: nothing is discarded, so nothing is reported.
    """

    @staticmethod
    def _thermometer(name: str, entity: str, key: str) -> Sensor:
        return Sensor(
            _key=key,
            name=name,
            metric_type="temperature_celsius",
            ha_entity_id=entity,
            location_key="tent-1",
        )

    @staticmethod
    def _state(entity: str, value: float) -> dict:
        return {
            "value": value,
            "last_changed": "2026-03-01T12:00:00Z",
            "entity_id": entity,
            "unit": "°C",
        }

    def test_a_rack_of_three_probes_keeps_all_three(self, service, mock_ha_client):
        """N sensors on one metric used to lose N-1 readings. Now they lose none."""
        sensors = [
            self._thermometer("Tent front", "sensor.tent_front_temp", "sensor-front"),
            self._thermometer("Tent middle", "sensor.tent_middle_temp", "sensor-middle"),
            self._thermometer("Tent back", "sensor.tent_back_temp", "sensor-back"),
        ]
        mock_ha_client.get_state.side_effect = [
            self._state("sensor.tent_front_temp", 21.0),
            self._state("sensor.tent_middle_temp", 24.0),
            self._state("sensor.tent_back_temp", 27.5),
        ]

        with structlog.testing.capture_logs() as logs:
            result = service.get_live_state_for_sensors(sensors)

        assert sorted(result["readings"]) == ["sensor-back", "sensor-front", "sensor-middle"]
        assert sorted(entry["value"] for entry in result["readings"].values()) == [21.0, 24.0, 27.5]
        # The derived view still shows one number — and names the other two.
        derived = result["values"]["temperature_celsius"]
        assert derived["sensor_count"] == 3
        assert sorted(derived["superseded_sensor_keys"]) == ["sensor-front", "sensor-middle"]
        # And the warning that reported the loss is unreachable, because there is none.
        assert [entry for entry in logs if entry["event"] == "ha_live_reading_discarded"] == []

    def test_distinct_metrics_are_unaffected(self, service, mock_ha_client):
        sensors = [
            self._thermometer("Tent front", "sensor.tent_front_temp", "sensor-front"),
            Sensor(
                _key="sensor-humidity",
                name="Tent humidity",
                metric_type="humidity_percent",
                ha_entity_id="sensor.tent_humidity",
                location_key="tent-1",
            ),
        ]
        mock_ha_client.get_state.side_effect = [
            self._state("sensor.tent_front_temp", 21.0),
            self._state("sensor.tent_humidity", 55.0),
        ]

        result = service.get_live_state_for_sensors(sensors)

        assert set(result["values"]) == {"temperature_celsius", "humidity_percent"}
        assert all(entry["sensor_count"] == 1 for entry in result["values"].values())

    def test_a_sensor_that_returns_nothing_displaces_nothing(self, service, mock_ha_client):
        """The entity that answered ``None`` never enters the map — and never did."""
        sensors = [
            self._thermometer("Tent front", "sensor.tent_front_temp", "sensor-front"),
            self._thermometer("Tent back", "sensor.tent_back_temp", "sensor-back"),
        ]
        mock_ha_client.get_state.side_effect = [
            self._state("sensor.tent_front_temp", 21.0),
            {"value": None, "last_changed": None, "entity_id": "sensor.tent_back_temp", "unit": "°C"},
        ]

        result = service.get_live_state_for_sensors(sensors)

        assert list(result["readings"]) == ["sensor-front"]
        assert result["values"]["temperature_celsius"]["value"] == 21.0
        assert result["values"]["temperature_celsius"]["sensor_count"] == 1


class TestGetLocationFrostWarning:
    def _temp_sensor(self) -> Sensor:
        return Sensor(
            name="Air Temp",
            metric_type="temperature_celsius",
            ha_entity_id="sensor.loc_temp",
            location_key="loc1",
        )

    def test_frost_warning_true_below_threshold(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        mock_ha_client.get_state.return_value = {
            "value": 1.0,
            "last_changed": "2026-03-01T02:00:00Z",
            "entity_id": "sensor.loc_temp",
            "unit": "°C",
        }
        result = service.get_location_frost_warning("loc1")
        assert result["frost_warning"] is True
        assert result["temperature_celsius"] == 1.0
        assert result["threshold_celsius"] == 3.0
        assert result["source"] == "ha_live"
        assert result["entity_id"] == "sensor.loc_temp"
        mock_repo.find_by_location.assert_called_once_with("loc1")

    def test_frost_warning_false_above_threshold(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        mock_ha_client.get_state.return_value = {
            "value": 12.5,
            "last_changed": "2026-03-01T14:00:00Z",
            "entity_id": "sensor.loc_temp",
            "unit": "°C",
        }
        result = service.get_location_frost_warning("loc1")
        assert result["frost_warning"] is False
        assert result["source"] == "ha_live"

    def test_unknown_when_no_temperature_sensor(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_location.return_value = [
            Sensor(name="Humidity", metric_type="humidity_percent", ha_entity_id="sensor.hum", location_key="loc1"),
        ]
        mock_ha_client.get_state.return_value = {
            "value": 60.0,
            "last_changed": "2026-03-01T14:00:00Z",
            "entity_id": "sensor.hum",
            "unit": "%",
        }
        result = service.get_location_frost_warning("loc1")
        assert result["frost_warning"] is None
        assert result["temperature_celsius"] is None
        assert result["source"] == "no_temperature"

    def test_unknown_when_temperature_state_non_numeric(self, service, mock_repo, mock_ha_client):
        # Home Assistant reports "unavailable"/"unknown" as the *value* of an
        # otherwise-live entity. That must not raise (→ 500); the endpoint reports
        # an honest unknown instead.
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        mock_ha_client.get_state.return_value = {
            "value": "unavailable",
            "last_changed": "2026-03-01T02:00:00Z",
            "entity_id": "sensor.loc_temp",
            "unit": "°C",
        }
        result = service.get_location_frost_warning("loc1")
        assert result["frost_warning"] is None
        assert result["temperature_celsius"] is None
        assert result["source"] == "no_temperature"

    def test_unknown_when_ha_unavailable(self, service_no_ha, mock_repo):
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        result = service_no_ha.get_location_frost_warning("loc1")
        assert result["frost_warning"] is None
        assert result["source"] == "unavailable"

    def test_custom_threshold_override(self, service, mock_repo, mock_ha_client):
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        mock_ha_client.get_state.return_value = {
            "value": 2.0,
            "last_changed": "2026-03-01T02:00:00Z",
            "entity_id": "sensor.loc_temp",
            "unit": "°C",
        }
        result = service.get_location_frost_warning("loc1", threshold_celsius=0.0)
        assert result["frost_warning"] is False
        assert result["threshold_celsius"] == 0.0

    def test_no_forecast_fields_on_per_location_response(self, service, mock_repo, mock_ha_client):
        # Issue #409 (F1): the per-location hot path carries only the reactive
        # state; the proactive forecast fields moved to the per-site endpoint.
        mock_repo.find_by_location.return_value = [self._temp_sensor()]
        mock_ha_client.get_state.return_value = {
            "value": 1.0,
            "last_changed": "2026-03-01T02:00:00Z",
            "entity_id": "sensor.loc_temp",
            "unit": "°C",
        }
        result = service.get_location_frost_warning("loc1")
        assert result["frost_warning"] is True  # reactive unchanged
        assert "forecast_frost_warning" not in result
        assert "forecast_min_temperature" not in result
        assert "forecast_expected_date" not in result
        assert "forecast_source" not in result


TENANT_KEY = "t-1"
SITE_KEY = "site-1"


def _site(gps=(52.5, 13.4), tenant_key=TENANT_KEY) -> Site:
    return Site(_key=SITE_KEY, tenant_key=tenant_key, name="Garden", gps_coordinates=gps)


def _forecast(day_offset: int, temp_min_c: float | None, source: str = "open-meteo") -> WeatherForecast:
    return WeatherForecast(
        site_key=SITE_KEY,
        forecast_date=datetime.now(UTC).date() + timedelta(days=day_offset),
        temp_min_c=temp_min_c,
        temp_max_c=None if temp_min_c is None else temp_min_c + 8.0,
        source=source,
        fetched_at=datetime(2026, 7, 5, 6, 0, 0),
    )


@pytest.fixture
def mock_forecast_repo():
    return MagicMock()


@pytest.fixture
def mock_site_repo():
    repo = MagicMock()
    repo.get_site_by_key.return_value = _site()
    return repo


@pytest.fixture
def forecast_service(mock_repo, mock_ha_client, mock_forecast_repo, mock_site_repo):
    return SensorService(
        mock_repo,
        mock_ha_client,
        weather_forecast_repo=mock_forecast_repo,
        site_repo=mock_site_repo,
    )


@pytest.fixture(autouse=True)
def _weather_enabled(monkeypatch):
    monkeypatch.setattr(settings, "weather_enabled", True)
    monkeypatch.setattr(settings, "frost_forecast_threshold_celsius", 2.0)
    monkeypatch.setattr(settings, "frost_forecast_horizon_days", 2)


class TestGetSiteWeatherForecast:
    def test_returns_in_horizon_rows_and_summary(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.find_by_site.return_value = [
            _forecast(0, 5.0),
            _forecast(1, -2.0),
            _forecast(3, -9.0),  # beyond horizon → excluded from rows and summary
        ]
        result = forecast_service.get_site_weather_forecast(SITE_KEY, TENANT_KEY)
        assert result["site_key"] == SITE_KEY
        # Only in-horizon rows (offsets 0 and 1), sorted by date.
        assert [row["forecast_date"] for row in result["forecasts"]] == [
            datetime.now(UTC).date(),
            datetime.now(UTC).date() + timedelta(days=1),
        ]
        assert result["forecasts"][0]["data_kind"] == "forecast"
        assert result["forecast_frost_warning"] is True
        assert result["forecast_expected_date"] == datetime.now(UTC).date() + timedelta(days=1)
        assert result["forecast_min_temperature"] == -2.0

    def test_tenant_scoped_read(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.find_by_site.return_value = []
        forecast_service.get_site_weather_forecast(SITE_KEY, TENANT_KEY)
        mock_forecast_repo.find_by_site.assert_called_once_with(SITE_KEY, TENANT_KEY)

    def test_graceful_empty_without_repo(self, mock_repo, mock_ha_client):
        service = SensorService(mock_repo, mock_ha_client)
        result = service.get_site_weather_forecast(SITE_KEY, TENANT_KEY)
        assert result["forecasts"] == []
        assert result["forecast_frost_warning"] is None

    def test_graceful_empty_when_no_gps(self, forecast_service, mock_forecast_repo, mock_site_repo):
        mock_site_repo.get_site_by_key.return_value = _site(gps=None)
        result = forecast_service.get_site_weather_forecast(SITE_KEY, TENANT_KEY)
        assert result["forecasts"] == []
        assert result["forecast_frost_warning"] is None
        mock_forecast_repo.find_by_site.assert_not_called()

    def test_repo_exception_returns_empty(self, forecast_service, mock_forecast_repo):
        mock_forecast_repo.find_by_site.side_effect = RuntimeError("db down")
        result = forecast_service.get_site_weather_forecast(SITE_KEY, TENANT_KEY)
        assert result["forecasts"] == []
        assert result["forecast_frost_warning"] is None

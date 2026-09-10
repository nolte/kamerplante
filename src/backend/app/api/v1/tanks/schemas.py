from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ── Tank schemas ────────────────────────────────────────────────────


class TankCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    tank_type: str
    volume_liters: float = Field(gt=0)
    material: str = "plastic"
    has_lid: bool = False
    has_air_pump: bool = False
    has_circulation_pump: bool = False
    has_heater: bool = False
    is_light_proof: bool = False
    has_uv_sterilizer: bool = False
    has_ozone_generator: bool = False
    installed_on: date | None = None
    location_key: str | None = None
    notes: str | None = None


class TankUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    tank_type: str | None = None
    volume_liters: float | None = Field(default=None, gt=0)
    material: str | None = None
    has_lid: bool | None = None
    has_air_pump: bool | None = None
    has_circulation_pump: bool | None = None
    has_heater: bool | None = None
    is_light_proof: bool | None = None
    has_uv_sterilizer: bool | None = None
    has_ozone_generator: bool | None = None
    installed_on: date | None = None
    location_key: str | None = None
    notes: str | None = None


class TankResponse(BaseModel):
    key: str
    name: str
    tank_type: str
    volume_liters: float
    material: str
    has_lid: bool
    has_air_pump: bool
    has_circulation_pump: bool
    has_heater: bool
    is_light_proof: bool = False
    has_uv_sterilizer: bool = False
    has_ozone_generator: bool = False
    installed_on: date | None
    location_key: str | None
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── TankState schemas ───────────────────────────────────────────────


class TankStateCreate(BaseModel):
    fill_level_liters: float | None = Field(default=None, ge=0)
    fill_level_percent: float | None = Field(default=None, ge=0, le=100)
    ph: float | None = Field(default=None, ge=0, le=14)
    ec_ms: float | None = Field(default=None, ge=0)
    water_temp_celsius: float | None = Field(default=None, ge=0, le=50)
    tds_ppm: float | None = Field(default=None, ge=0)
    dissolved_oxygen_mgl: float | None = Field(default=None, ge=0, le=20)
    orp_mv: int | None = Field(default=None, ge=-500, le=1000)
    source: str = "manual"


class TankStateResponse(BaseModel):
    key: str
    tank_key: str
    recorded_at: datetime | None
    fill_level_liters: float | None
    fill_level_percent: float | None
    ph: float | None
    ec_ms: float | None
    water_temp_celsius: float | None
    tds_ppm: float | None
    dissolved_oxygen_mgl: float | None = None
    orp_mv: int | None = None
    source: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── MaintenanceLog schemas ──────────────────────────────────────────


class MaintenanceLogCreate(BaseModel):
    maintenance_type: str
    performed_by: str = ""
    duration_minutes: int | None = Field(default=None, ge=0)
    products_used: list[str] = Field(default_factory=list)
    notes: str | None = None


class MaintenanceLogResponse(BaseModel):
    key: str
    tank_key: str
    maintenance_type: str
    performed_at: datetime | None
    performed_by: str
    duration_minutes: int | None
    products_used: list[str]
    notes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── MaintenanceSchedule schemas ─────────────────────────────────────


class MaintenanceScheduleCreate(BaseModel):
    maintenance_type: str
    interval_days: int = Field(gt=0)
    reminder_days_before: int = Field(default=3, ge=0)
    is_active: bool = True
    priority: str = "medium"
    auto_create_task: bool = False
    instructions: str | None = None


class MaintenanceScheduleUpdate(BaseModel):
    interval_days: int | None = Field(default=None, gt=0)
    reminder_days_before: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    priority: str | None = None
    auto_create_task: bool | None = None
    instructions: str | None = None


class MaintenanceScheduleResponse(BaseModel):
    key: str
    tank_key: str
    maintenance_type: str
    interval_days: int
    reminder_days_before: int
    is_active: bool
    priority: str
    auto_create_task: bool
    instructions: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ── Alert & Due Maintenance schemas ─────────────────────────────────


class AlertResponse(BaseModel):
    type: str
    severity: str
    message: str
    value: float
    limit: float | None = None
    limit_min: float | None = None
    limit_max: float | None = None
    factors: list[str] | None = None
    temp: float | None = None


class DueMaintenanceResponse(BaseModel):
    tank_key: str
    tank_name: str | None = None
    schedule_key: str | None
    maintenance_type: str
    next_due: str
    days_until: float
    status: str
    priority: str


# ── TankFillEvent schemas ──────────────────────────────────────────


class FertilizerSnapshotSchema(BaseModel):
    product_key: str | None = None
    product_name: str
    ml_per_liter: float = Field(gt=0)


class TankFillEventCreate(BaseModel):
    fill_type: str
    volume_liters: float = Field(gt=0)
    mixing_result_key: str | None = None
    nutrient_plan_key: str | None = None
    target_ec_ms: float | None = Field(default=None, ge=0)
    target_ph: float | None = Field(default=None, ge=0, le=14)
    measured_ec_ms: float | None = Field(default=None, ge=0)
    measured_ph: float | None = Field(default=None, ge=0, le=14)
    water_source: str | None = None
    water_mix_ratio_ro_percent: float | None = Field(default=None, ge=0, le=100)
    source_tank_key: str | None = None
    fertilizers_used: list[FertilizerSnapshotSchema] = Field(default_factory=list)
    base_water_ec_ms: float | None = Field(default=None, ge=0)
    chlorine_ppm: float | None = Field(default=None, ge=0)
    chloramine_ppm: float | None = Field(default=None, ge=0)
    alkalinity_ppm: float | None = Field(default=None, ge=0)
    is_organic_fertilizers: bool = False
    performed_by: str | None = None
    notes: str | None = None


class TankFillEventResponse(BaseModel):
    key: str
    tank_key: str
    filled_at: datetime | None
    fill_type: str
    volume_liters: float
    mixing_result_key: str | None = None
    nutrient_plan_key: str | None = None
    target_ec_ms: float | None = None
    target_ph: float | None = None
    measured_ec_ms: float | None = None
    measured_ph: float | None = None
    water_source: str | None = None
    water_mix_ratio_ro_percent: float | None = None
    source_tank_key: str | None = None
    fertilizers_used: list[FertilizerSnapshotSchema] = Field(default_factory=list)
    base_water_ec_ms: float | None = None
    chlorine_ppm: float | None = None
    chloramine_ppm: float | None = None
    alkalinity_ppm: float | None = None
    is_organic_fertilizers: bool = False
    performed_by: str | None = None
    notes: str | None = None
    water_defaults_source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TankFillEventStatsResponse(BaseModel):
    fill_type_counts: dict[str, int]
    total_volume_liters: float
    total_count: int
    avg_ec_deviation_ms: float | None = None


class FillEventResultResponse(BaseModel):
    fill_event: TankFillEventResponse
    tank_state: TankStateResponse | None = None
    warnings: list[str] = Field(default_factory=list)
    water_defaults_source: str | None = None


# ── Relationship schemas ────────────────────────────────────────────


class FeedsFromRequest(BaseModel):
    source_tank_key: str


class FeedsFromLinkResponse(BaseModel):
    """Acknowledgement returned after a tank is linked to its source tank."""

    status: str


class LocationTankValidationResponse(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)


# ── Sensor schemas ─────────────────────────────────────────────────


class SensorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    metric_type: str
    ha_entity_id: str | None = None
    unit_of_measurement: str | None = None
    mqtt_topic: str | None = None
    tank_key: str | None = None


class SensorUpdate(BaseModel):
    """Editable fields of a sensor (REQ-005 §2).

    ``is_active`` is deliberately **not** here, although the model carries it.
    Every read filters it — ``find_by_tank`` / ``find_by_site`` /
    ``find_by_location`` all end in ``AND s.is_active == true``, there is no
    get-by-key route and no ``include_inactive`` — so a client that could write
    ``false`` would make the sensor vanish from the only surfaces that can list
    it, with no way back through the API. Offering a switch whose one direction
    is irreversible is worse than not offering it (#1339 review). Restoring it
    means adding the read path first; see the follow-up issue.

    Every field is optional and unset-aware: the routes dump with
    ``exclude_unset``, so an explicit ``null`` clears a value and an omitted key
    leaves it alone.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    metric_type: str | None = None
    ha_entity_id: str | None = None
    unit_of_measurement: str | None = None
    mqtt_topic: str | None = None


class SensorResponse(BaseModel):
    key: str
    name: str
    metric_type: str
    ha_entity_id: str | None = None
    unit_of_measurement: str | None = None
    mqtt_topic: str | None = None
    tank_key: str | None = None
    site_key: str | None = None
    location_key: str | None = None
    is_active: bool


class HAEntitySuggestion(BaseModel):
    entity_id: str
    friendly_name: str
    unit_of_measurement: str | None = None
    device_class: str | None = None
    state: str | None = None
    suggested_metric_type: str | None = None
    suggested_name: str | None = None


class LiveReadingEntry(BaseModel):
    """One live reading, from one sensor (REQ-005 §2).

    Filed under the sensor that produced it, because that is what a reading
    belongs to. Two sensors reporting the same metric on one location are two
    entries here, and neither is dropped.
    """

    sensor_key: str | None = Field(
        default=None,
        description="Document key of the sensor. Null only for a sensor that was never persisted.",
    )
    sensor_name: str | None = Field(default=None, description="The sensor's display name.")
    metric_type: str | None = Field(default=None, description="What the sensor measures, verbatim.")
    value: float
    last_changed: str | None = None
    last_updated: str | None = None
    last_reported: str | None = Field(
        default=None,
        description="When the entity last reported (Home Assistant >= 2024.6). The most reliable measurement instant.",
    )
    entity_id: str | None = None
    unit: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sensor_key": "884210",
                    "sensor_name": "Zelt vorne",
                    "metric_type": "temperature_celsius",
                    "value": 21.4,
                    "last_changed": "2026-08-06T05:12:44Z",
                    "last_updated": "2026-08-06T05:12:44Z",
                    "last_reported": "2026-08-06T06:03:01Z",
                    "entity_id": "sensor.zelt_vorne_temperatur",
                    "unit": "°C",
                }
            ]
        }
    )


class LiveValueEntry(LiveReadingEntry):
    """The one reading a metric is represented by in the derived view.

    Same fields as a reading, plus the two that keep the collapse visible: a
    consumer reading ``values`` must be able to tell that more than one sensor
    answered, and where to find the others.
    """

    sensor_count: int = Field(
        default=1,
        ge=1,
        description="How many sensors answered this metric. 1 means nothing was left out.",
    )
    superseded_sensor_keys: list[str] = Field(
        default_factory=list,
        description="Keys of the readings this view does not show. Look them up in `readings`.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "sensor_key": "884211",
                    "sensor_name": "Zelt hinten",
                    "metric_type": "temperature_celsius",
                    "value": 23.9,
                    "last_changed": "2026-08-06T06:01:10Z",
                    "last_updated": "2026-08-06T06:01:10Z",
                    "last_reported": "2026-08-06T06:04:55Z",
                    "entity_id": "sensor.zelt_hinten_temperatur",
                    "unit": "°C",
                    "sensor_count": 2,
                    "superseded_sensor_keys": ["884210"],
                }
            ]
        }
    )


class LiveStateResponse(BaseModel):
    """The live sensor state of a tank, a site or a location.

    ``readings`` is the complete answer, keyed by sensor key. ``values`` is a
    *derived* single-value view keyed by metric type, kept for consumers that
    want one number per metric: the freshest reading wins, ties are broken by
    sensor key, and the entry reports how many readings there were. Anything that
    must not miss a reading — a frost warning, an alarm — reads ``readings``.
    """

    readings: dict[str, LiveReadingEntry] = Field(
        default_factory=dict,
        description="Every sensor that answered, keyed by its document key.",
    )
    values: dict[str, LiveValueEntry] = Field(
        default_factory=dict,
        description="Derived single-value view, keyed by metric type. Never more complete than `readings`.",
    )
    errors: list[dict] = Field(default_factory=list)
    source: str
    message: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "readings": {
                        "884210": {
                            "sensor_key": "884210",
                            "sensor_name": "Zelt vorne",
                            "metric_type": "temperature_celsius",
                            "value": 21.4,
                            "last_reported": "2026-08-06T06:03:01Z",
                            "entity_id": "sensor.zelt_vorne_temperatur",
                            "unit": "°C",
                        },
                        "884211": {
                            "sensor_key": "884211",
                            "sensor_name": "Zelt hinten",
                            "metric_type": "temperature_celsius",
                            "value": 23.9,
                            "last_reported": "2026-08-06T06:04:55Z",
                            "entity_id": "sensor.zelt_hinten_temperatur",
                            "unit": "°C",
                        },
                    },
                    "values": {
                        "temperature_celsius": {
                            "sensor_key": "884211",
                            "sensor_name": "Zelt hinten",
                            "metric_type": "temperature_celsius",
                            "value": 23.9,
                            "last_reported": "2026-08-06T06:04:55Z",
                            "entity_id": "sensor.zelt_hinten_temperatur",
                            "unit": "°C",
                            "sensor_count": 2,
                            "superseded_sensor_keys": ["884210"],
                        }
                    },
                    "errors": [],
                    "source": "ha_live",
                }
            ]
        }
    )


# ── Active Nutrient Plan schemas ──────────────────────────────────


# ── EC Dilution schemas ──────────────────────────────────────────


class EcDilutionRequest(BaseModel):
    current_ec_ms: float = Field(gt=0, description="Current EC of the tank solution (mS/cm)")
    target_ec_ms: float = Field(gt=0, description="Desired target EC (mS/cm)")
    current_volume_liters: float | None = Field(
        default=None,
        gt=0,
        description="Current volume in the tank (L). Defaults to tank's nominal volume.",
    )
    ro_ec_ms: float = Field(
        default=0.02,
        ge=0,
        description="EC of the RO/dilution water (mS/cm). Default 0.02.",
    )


class EcDilutionResponse(BaseModel):
    ro_volume_liters: float
    final_volume_liters: float
    dilution_factor: float
    feasible: bool
    reason: str
    current_volume_liters: float
    current_ec_ms: float
    target_ec_ms: float
    ro_ec_ms: float


# ── Active Nutrient Plan schemas ──────────────────────────────────


class ActivePlanFertilizerInfo(BaseModel):
    key: str
    product_name: str
    brand: str = ""
    fertilizer_type: str
    npk_ratio: list[float] = Field(default_factory=list)
    ec_contribution_per_ml: float = 0.0
    mixing_priority: int = 50


class ActiveNutrientPlanResponse(BaseModel):
    run_key: str
    run_name: str
    run_status: str
    plan_key: str
    plan_name: str
    current_phase: str | None = None
    plant_count: int = 0
    current_phase_entry: dict | None = None
    all_phase_entries: list[dict] = Field(default_factory=list)
    fertilizers: list[ActivePlanFertilizerInfo] = Field(default_factory=list)
    watering_schedule: dict | None = None
    water_mix_ratio_ro_percent: int | None = None

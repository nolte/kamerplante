import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# What ``/api/health`` reports when no build stamped a revision into the image
# (#1210). A fixed literal, not a formatted fallback: a consumer compares against
# it to decide "this instance cannot identify itself", which a value that varied
# with the environment would make impossible.
#
# It says "willing to disclose, but nothing was baked in". It does NOT say
# "configured not to disclose" — that state is the **absence** of the
# ``build_revision`` key from the payload (see ``health_expose_build_revision``).
# Collapsing the two would make the drift-detection job unable to tell a
# deliberately silent instance from a broken build.
UNKNOWN_BUILD_REVISION = "unknown"

# The only shape ``/api/health`` will report as a build identity (#1210, SEC-002).
# Lower-case hex, 7 (git's shortest unambiguous abbreviation) to 40 characters.
#
# **Not an injection defence** — there is no injection path: the value reaches the
# client through ``JSONResponse`` with no string interpolation anywhere, and its
# only supplier is ``github.sha``. The reason is downstream integrity: the payload
# is read by operator tooling and by a CI drift job, and a misconfigured
# arbitrary-length or markup-bearing value would propagate uncontrolled into
# dashboards and scripts. The check restores what the field claims to be — a SHA,
# or an honest admission of not knowing, and nothing in between.
_BUILD_REVISION_SHAPE = re.compile(r"^[0-9a-f]{7,40}$")


class GBIFSettings(BaseModel):
    base_url: str = "https://api.gbif.org/v1"
    rate_limit_per_minute: int = 60
    http_timeout: int = 30
    incremental_exact_threshold: int = 97
    incremental_fuzzy_threshold: int = 95
    full_exact_threshold: int = 80
    full_fuzzy_threshold: int = 90
    vernacular_languages: list[str] = ["deu", "eng"]
    backbone_dataset_key: str = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
    plantae_taxon_key: int = 6
    max_description_length: int = 2000
    max_habitat_length: int = 500


class Settings(BaseSettings):
    app_name: str = "Kamerplanter API"
    app_version: str = "1.0.0"

    # Build identity of the running image (#1210) — deliberately a SECOND field,
    # never a repurposing of ``app_version``. ``app_version`` is the API contract
    # version: it feeds OpenAPI ``info.version`` (and with it the published
    # openapi.json release asset and the API docs), the mDNS advertisement and the
    # Sentry release. Overloading it with a build identifier would silently
    # rewrite all four.
    #
    # Carries the full 40-character git SHA the image was built from, baked in by
    # ``src/backend/Dockerfile`` (``ARG``/``ENV BUILD_REVISION``) from
    # ``.github/workflows/docker-publish.yml``
    # (``build-args: BUILD_REVISION=${{ github.sha }}``) — the same value
    # docker/metadata-action writes to the image's
    # ``org.opencontainers.image.revision`` annotation, so the two compare without
    # truncation. Full, not short, for exactly that reason.
    #
    # Empty on a local checkout, on the ``dev`` image target and on any image
    # built without the build-arg; :meth:`resolve_build_revision` turns that into
    # the honest ``"unknown"`` rather than a guess.
    build_revision: str = ""

    #: Whether ``GET /api/health`` discloses ``build_revision`` at all (#1210).
    #:
    #: **Off by default, and the default is the security decision.** The SHA
    #: itself is public — the repository is. What is not public is the mapping
    #: *this host → that commit*, and that mapping is the entire attacker-relevant
    #: content of the field on an unauthenticated endpoint. From an exact commit
    #: follows the exact hash-pinned dependency set (``requirements.txt`` is in the
    #: public tree) and the exact patch distance: ``git log <revision>..develop``
    #: enumerates the security fixes this instance has **not** received. This
    #: repository also publishes its own open findings
    #: (``spec/analysis/code-security-review.md``, the advisory scan lanes in
    #: ``CLAUDE.md``), so the reader does not even have to guess which of them
    #: still apply here. An operator who wants the diagnostic turns it on for their
    #: own instance and accepts that trade knowingly; nobody inherits it silently.
    #:
    #: **Off means the key is absent, not ``"unknown"``.** Three states must stay
    #: distinguishable for the drift-detection consumer: key absent = configured
    #: not to disclose (nothing is wrong); ``"unknown"`` = willing, but no build
    #: stamped a revision in; a SHA = the real answer. Reporting "unknown" for a
    #: deliberately silent instance would make a healthy deployment indistinguishable
    #: from a broken build pipeline.
    health_expose_build_revision: bool = False

    debug: bool = False

    arangodb_host: str = "localhost"
    arangodb_port: int = 8529
    arangodb_database: str = "kamerplanter"
    arangodb_username: str = "root"
    arangodb_password: str = "rootpassword"

    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # REQ-027 Light-Modus
    kamerplanter_mode: Literal["light", "full"] = "full"

    # REQ-032 Print: base URL for QR codes on plant labels
    app_base_url: str = "http://localhost:5173"

    perenual_api_key: str = ""
    trefle_api_key: str = ""
    enrichment_http_timeout: int = 30

    gbif: GBIFSettings = GBIFSettings()

    # REQ-029 / REQ-029-A Phase 1 — Plant identification (all optional).
    #
    # SEC-001: every identification setting below is defined EXACTLY ONCE here.
    # Python keeps the *last* class-body assignment for a duplicated field, so a
    # second definition would silently shadow these documented defaults and make
    # the effective config non-auditable. ``test_settings_identification_defaults``
    # pins the documented effective values so a re-introduced duplicate fails CI.
    #
    # Pl@ntNet is the Phase-1 primary adapter (free tier, <=500/day).
    plantnet_api_key: str = ""  # Pl@ntNet free API key; empty = adapter disabled
    plantnet_enabled: bool = True  # disable the Pl@ntNet adapter entirely
    plantnet_base_url: str = "https://my-api.plantnet.org/v2"
    # Plant.id remains an operator opt-in (no default, never auto-primary).
    plant_id_api_key: str = ""  # Plant.id (Kindwise) — opt-in only
    plant_id_base_url: str = "https://plant.id/api/v3"
    # Self-hosted DINOv2 inference-service (REQ-029-A Phase 2 priority-1 adapter).
    # Disabled by default until the service is deployed (WS-6); while disabled the
    # local adapter is unavailable and the registry falls back to Pl@ntNet.
    inference_service_enabled: bool = False
    inference_service_url: str = "http://kamerplanter-recognition:8000"
    # Config-driven adapter priority (REQ-029-A §0.1.1 point 1) — never hard-coded.
    # Phase-1 primary adapter is Pl@ntNet (REQ-029-A §0.1.1: DINOv2/local_embedding
    # is Phase 2). Phase 2 switches this to "local_embedding" without touching
    # engine/service/API.
    identification_primary_adapter: str = "plantnet"
    # HTTP timeout (seconds) for the external identification call, env-configurable
    # via ``IDENTIFICATION_HTTP_TIMEOUT``. The Pl@ntNet ``/identify`` request
    # (multipart image upload + server-side ML inference) regularly exceeds the
    # previous 30s default under load, surfacing as a ReadTimeout in the UI.
    identification_http_timeout: int = 60
    identification_confidence_auto_accept: float = 0.85
    identification_confidence_min_show: float = 0.10
    identification_max_image_size_mb: int = 5
    # Longest edge (px) the user image is downscaled to before it is uploaded to
    # the identification adapter, env-configurable via
    # ``IDENTIFICATION_MAX_IMAGE_DIMENSION``. Smaller = faster upload and less
    # third-party bandwidth; Pl@ntNet works well from ~1024px. See
    # ``image_preprocessor.strip_exif_and_normalize``.
    identification_max_image_dimension: int = 1024
    # Per-user daily rate limit (REQ-029 §7). SEC-003: a sensible per-user floor so
    # a single account cannot consume the whole shared adapter free-tier quota.
    # ``0`` falls back to the adapter's own free-tier default.
    identification_rate_limit_per_user_day: int = 50
    # REQ-034 §4a.3 — operator opt-in for the *external* recognition path
    # (Pl@ntNet) in Light mode. In Light mode (REQ-027) there is no consent
    # subsystem, so sending a gallery photo to a third party requires a deliberate
    # operator decision. Off by default → in Light mode only the self-hosted
    # ``local_embedding`` path is usable (and only once Phase 2 is enabled).
    identification_external_in_light_mode: bool = False
    # REQ-029-A §4 reference-image acquisition (DINOv2 index population).
    reference_image_max_candidates: int = 40  # n_max queried per species
    reference_image_min_usable: int = 5  # below this a species is "not recognizable"
    reference_image_min_dimension: int = 224  # px on the shorter edge (model input)
    reference_image_max_aspect_ratio: float = 3.0  # reject extreme crops/banners
    reference_image_use_wikimedia: bool = True  # query Wikimedia Commons as a 2nd source
    wikimedia_commons_api_url: str = "https://commons.wikimedia.org/w/api.php"

    # REQ-044 Bildbasierte Schädlingserkennung (alle optional, Default-Privacy §8).
    # Das Feature ist standardmäßig AUS; der Self-Hosted-Symptom-Adapter ist der
    # Default-Adapter, der Cloud-Adapter ist opt-in und einwilligungspflichtig.
    pest_detection_enabled: bool = False  # master switch (Default-Privacy)
    # Self-hosted symptom adapter (Modus 2, Phase-1-Default). Nutzt den
    # REQ-029-A-Inferenz-Service; die trainierten Few-Shot-Prototypen sind extern
    # blockiert (WP-3) → bis dahin nur aktiv, wenn der Service erreichbar ist.
    pest_detection_symptom_enabled: bool = True
    # Self-hosted detector (Modus 1, Phase 2 — D-FINE/RF-DETR ONNX, WP-1/2/3).
    pest_detection_detector_enabled: bool = False
    # Demo adapter (no external service, no real model). Lets operators preview
    # the full pest-detection UI flow while the trained backend is externally
    # blocked (WP-1/2/3). Returns clearly-labelled placeholder findings. Off by
    # default; never use in production for real decisions.
    pest_detection_demo_enabled: bool = False
    # Cloud adapter (Kindwise plant.health, opt-in, WP-7). Default aus, bis die
    # Vertrags-/DSGVO-Fragen (WP-7 Show-Stopper) geklärt sind.
    pest_detection_cloud_enabled: bool = False
    pest_detection_cloud_api_key: str = ""
    pest_detection_cloud_base_url: str = "https://plant.id/api/v3"
    # Config-driven primary adapter (analog identification) — nie hart kodiert.
    pest_detection_primary_adapter: str = "local_pest_symptom"
    pest_detection_max_image_size_mb: int = 8  # §6 multipart upload limit
    # EXIF-Strip behält für das Tiling mehr Auflösung als der ID-Pfad (1024).
    pest_detection_max_image_dimension: int = 2048
    pest_detection_tile_size: int = 512  # §4.3 / WP-3.3 SAHI slice
    pest_detection_tile_overlap: float = 0.2  # §4.3 / WP-3.3 SAHI overlap
    # WP-3 cold-start dataset acquisition (frozen-DINOv2 few-shot prototypes).
    # Pull CC0/CC-BY images per class from GBIF (public occurrence search, no
    # credentials) and index ~30/class. Insects are tighter-cropped than plants.
    pest_reference_max_candidates: int = 150  # candidates queried per class (NC-heavy classes need headroom)
    pest_reference_min_usable: int = 30  # target accepted prototypes per class
    pest_reference_min_dimension: int = 256  # px on the shorter edge
    pest_reference_max_aspect_ratio: float = 2.5
    # Accept CC-BY-NC images in addition to CC0/CC-BY. Reversible by design.
    #
    # ONLY permissible while the application is operated NON-COMMERCIALLY: CC-BY-NC
    # is redistributable-with-attribution for non-commercial use, which is the
    # current operating assumption. Upon any COMMERCIALISATION this MUST be set to
    # False — CC-BY-NC is then no longer redistributable and would taint the
    # embedding index. Copyleft (-SA) / no-derivatives (-ND) variants stay
    # rejected regardless of this flag. See
    # spec/analysis/pest-image-sources-analysis.md §4.3.
    pest_reference_allow_noncommercial: bool = True
    # Active acquisition sources and their priority order (first = highest).
    # Configurable so a single source can be enabled/disabled or reordered
    # without code changes; the orchestrator iterates them in this order.
    pest_reference_sources: list[str] = ["gbif", "inaturalist", "idigbio"]
    # iNaturalist direct API (per-photo license + lifeStage annotation filter).
    inaturalist_base_url: str = "https://api.inaturalist.org/v1"
    inaturalist_http_timeout: int = 30
    inaturalist_per_page: int = 100  # iNat hard cap is 200; stay polite
    # iDigBio media search (specimen-biased; live-pest yield is thin, §4.1).
    idigbio_base_url: str = "https://search.idigbio.org/v2"
    idigbio_http_timeout: int = 30

    # REQ-038 CV disease diagnosis (ONNX PlantDoc classifier + PlantCV phenotype).
    # Opt-in (default-privacy): while disabled the self-hosted adapter reports
    # itself unconfigured and the diagnosis flow degrades gracefully. Reuses the
    # shared ``inference_service_url`` + ``internal_service_token``.
    cv_diagnosis_enabled: bool = False
    # Softmax-probability gates (REQ-038 §4). ``show`` is the drop floor; classes
    # at/above ``highlight`` are emphasised. Neither implies auto-accept — a CV
    # diagnosis is always a hypothesis. Backend-side enforcement complements the
    # inference-service floor so the operator can tighten it without a redeploy.
    cv_classifier_confidence_show: float = 0.10
    cv_classifier_confidence_highlight: float = 0.75
    # PlantCV phenotype panel (measurement only). Requested per call; effective
    # only when the inference-service has PlantCV installed.
    cv_phenotype_enabled: bool = True
    cv_diagnosis_max_image_size_mb: int = 5  # §4.4 multipart upload limit

    # REQ-023 Auth
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    session_token_expire_hours: int = 24
    fernet_key: str = ""  # For encrypting OIDC provider secrets
    frontend_url: str = "http://localhost:5173"
    hibp_enabled: bool = False
    require_email_verification: bool = False  # Set True in production
    cookie_secure: bool = True  # Set False for HTTP-only E2E environments

    #: E2E only (#1155) — email of a second, platform-admin account to seed.
    #:
    #: The full-mode E2E suite needs an account that may mutate the global
    #: catalogues, because #1120 made those platform-admin-only. It cannot be the
    #: demo user: half the suite exists to assert what an *ordinary member* is
    #: refused, and promoting the one account both roles run through would make
    #: those assertions vacuous — including #1120's own.
    #:
    #: Seeding an administrator from an environment variable is a dangerous shape
    #: on its own, so it is not gated on this alone. See
    #: ``seed_e2e_platform_admin`` for the second condition and why it was chosen.
    e2e_platform_admin_email: str | None = None

    #: Password for :attr:`e2e_platform_admin_email`. Both must be set; the seed
    #: refuses a half-configured pair rather than inventing the missing half.
    e2e_platform_admin_password: str | None = None

    #: REQ-023 / #1118 — lifetime of a QR device-pairing code, in seconds.
    #:
    #: The bounds are the guard, not the default. A pairing code is a bearer
    #: credential displayed on a screen: whoever reads it first gets a session.
    #: Below 60 s a user who has to unlock their phone and open the app cannot
    #: finish in time and re-requests codes until one lands, which turns the
    #: feature into a code generator. Above 120 s the code outlives the moment
    #: the user was looking at the screen — a QR left on an unattended monitor,
    #: in a screen share or in a shoulder-surfer's camera roll stays redeemable.
    #:
    #: Enforced by the settings model rather than by a comment or a service-side
    #: clamp: an out-of-range ``DEVICE_PAIRING_TTL_SECONDS`` refuses startup,
    #: where an operator sees it, instead of being silently reinterpreted.
    device_pairing_ttl_seconds: int = Field(default=90, ge=60, le=120)

    # REQ-016 InvenTree integration (optional). Disabled by default — a missing
    # or switched-off configuration must never crash the app (graceful
    # degradation). ``inventree_allow_private_endpoint`` opts a LAN / in-cluster
    # InvenTree instance out of the SSRF private-address block (analogous to
    # ``HA_ALLOW_PRIVATE_ENDPOINT``).
    inventree_enabled: bool = False
    inventree_allow_private_endpoint: bool = False

    # Email
    email_adapter: str = "console"  # console | smtp | resend
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@kamerplanter.example"
    smtp_use_tls: bool = True

    # Home Assistant (optional — for sensor live-query)
    ha_url: str = ""  # e.g. "http://homeassistant.local:8123"
    ha_access_token: str = ""  # Long-Lived Access Token
    ha_timeout: int = 10  # HTTP timeout in seconds
    # SSRF opt-in (SEC-B3): the HA base_url is tenant/admin-configurable and is
    # dialed server-side with the bearer token attached. By default only public
    # addresses are allowed; the cloud-metadata / link-local range
    # (169.254.0.0/16) is ALWAYS blocked regardless of this flag. Home Assistant
    # commonly runs in the LAN over http (homeassistant.local, 192.168.x.x), so
    # operators who run it on an RFC1918/loopback address must opt in explicitly.
    ha_allow_private_endpoint: bool = False

    # Reactive frost-warning threshold (°C) for the HA
    # ``binary_sensor.kp_{location}_frost_warning`` entity. A warning fires when
    # a location's latest ambient temperature is at/below this value. The small
    # positive margin over 0 °C accounts for ground frost occurring while
    # screen-height air temperature still reads a few degrees higher.
    frost_warning_threshold_celsius: float = 3.0

    # Proactive (forecast-based) frost early-warning (Issue #392, REQ-005 /
    # REQ-039). Evaluated over the persisted daily ``weather_forecasts`` records
    # (REQ-046) instead of the current air temperature, so a grower is warned
    # *before* a frost night. Deliberately kept SEPARATE from the reactive
    # ``frost_warning_threshold_celsius`` (3.0 °C): the forecast threshold is set
    # a touch more conservative (closer to 0 °C) because a multi-day-ahead daily
    # minimum carries more forecast uncertainty than a just-measured reading, so
    # only a clearer frost signal should raise the proactive warning.
    frost_forecast_threshold_celsius: float = 2.0
    # Horizon as the *number of calendar days scanned starting today* (inclusive).
    # Default 2 = today + the next day (≈ the 24–48 h window of Issue #392); 1 =
    # only today; 0 scans no day.
    frost_forecast_horizon_days: int = 2

    # REQ-046 Weather data sources (public services + Home Assistant)
    weather_enabled: bool = False
    weather_default_public_source: str = "open-meteo"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    dwd_base_url: str = "https://api.brightsky.dev"
    openweathermap_base_url: str = "https://api.openweathermap.org/data/2.5"
    open_meteo_enabled: bool = True
    dwd_enabled: bool = True
    openweathermap_enabled: bool = True
    weather_fetch_timeout_s: int = 20
    weather_max_rps_per_provider: float = 1.0

    # REQ-041 NASA POWER — global, keyless reanalysis source for daily values and
    # long-term climate normals (power.larc.nasa.gov). CC-BY-4.0 / US-public-domain
    # (attribution requested; see ``weather_attributions.py`` + NOTICE.md).
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal"
    #: NASA POWER daily values lag real time (quality control); skip the most
    #: recent ``latency`` days and fetch a ``days_back`` look-back window ending
    #: there. Both are configurable so a slow-to-publish region can widen them.
    nasa_power_data_latency_days: int = 7
    nasa_power_daily_days_back: int = 14
    #: Climate normals are near-static, so a fetched record is re-pulled only after
    #: this TTL — keeps the monthly beat idempotent and NASA POWER un-hammered.
    nasa_power_climate_ttl_days: int = 180
    #: Kill-switch for the monthly ``fetch_climate_normals`` beat (independent of
    #: the daily-forecast ``weather_enabled`` switch; both must be on to run).
    nasa_power_climate_enabled: bool = True

    # REQ-039 — quarterly beat that re-derives ``Site.hardiness_zone`` from the
    # climate normals for non-manually-set sites. Kill-switch; consumes the
    # REQ-041 climate normals, so it is only useful when those are being fetched.
    hardiness_zone_refresh_enabled: bool = True

    # REQ-037 Evapotranspiration / irrigation demand — the daily
    # ``compute_irrigation_demand`` beat materialises FAO-56 ET₀ → net irrigation
    # demand for outdoor/greenhouse sites. Gated additionally by ``weather_enabled``
    # (no forecasts → nothing to compute).
    irrigation_demand_enabled: bool = True
    #: Assumed effective root-zone depth (mm of soil) when converting a substrate's
    #: water-holding-capacity percentage into a millimetre cap on the net demand.
    irrigation_root_zone_depth_mm: float = 300.0

    # REQ-047 Season & overwintering automation — transition thresholds (°C) and
    # the hysteresis window; SEASON_STATE_EVAL_ENABLED is the Celery kill-switch.
    season_pre_winter_temp_c: float = 5.0
    season_frost_temp_c: float = 2.0
    season_spring_temp_c: float = 10.0
    season_signal_threshold_days: int = 3
    season_state_eval_enabled: bool = True
    #: Look-ahead window (days) for the live frost forecast — the single source of
    #: truth shared by the signal resolver and the state engine (no copy-paste).
    season_live_forecast_window_days: int = 7

    # REQ-018 environment-control loop (opt-in kill-switch). When off, the
    # evaluate_control_rules / sync_actuator_states / expire_manual_overrides
    # beats are not scheduled — actuators are still fully manageable via the API.
    actuator_control_loop_enabled: bool = False

    # TimescaleDB (optional — for sensor time-series)
    timescaledb_enabled: bool = False
    timescaledb_host: str = "localhost"
    timescaledb_port: int = 5432
    timescaledb_database: str = "kamerplanter_sensors"
    timescaledb_username: str = "postgres"
    timescaledb_password: str = "changeme"
    timescaledb_pool_min_size: int = 2
    timescaledb_pool_max_size: int = 10

    # Knowledge Service (optional — standalone RAG microservice)
    knowledge_service_enabled: bool = False
    knowledge_service_url: str = "http://knowledge-service:8000"

    # REQ-031 KI-Assistent — three-stage feature toggle (§1.3).
    # Stage 1 (Operator): when false the whole KI API answers HTTP 404, as if
    # the endpoints did not exist. Stages 2 (tenant setting) and 3 (user consent)
    # are evaluated per request in the service layer.
    ai_features_enabled: bool = False
    # Async KnowledgeServiceAdapter timeout + circuit-breaker tuning (§4.1).
    ai_knowledge_service_timeout_s: float = 60.0
    ai_circuit_breaker_threshold: int = 3
    ai_circuit_breaker_window_s: float = 60.0
    ai_circuit_breaker_cooldown_s: float = 60.0
    # Light-mode public /ai/ask rate limit (per client IP).
    ai_public_rate_limit_per_min: int = 10

    # REQ-033 MCP server (Model Context Protocol). Opt-in aggregation layer over
    # the existing services, served in-process by the backend and gated by
    # service-account API keys (§4.3). When false, the MCP endpoints answer
    # HTTP 404 as if they did not exist (mirrors the AI operator flag).
    mcp_server_enabled: bool = False
    #: Idempotency-record TTL for MCP write tools (§2.6, AC-22).
    mcp_idempotency_ttl_hours: int = 24
    #: mcp_audit_log retention window (NFR-011, AC-S4).
    mcp_audit_retention_days: int = 90
    #: Ceiling on the **Base-64** image payload of a single ``get_diary_entry_photos``
    #: call (REQ-050 §4.4, REQ-033 §4.3b). Measured on the encoded wire size,
    #: because that is what a model's context actually pays for. Exceeding it is
    #: answered with ``payload.too_large``; the call is **never** silently
    #: truncated (AK-08) — an agent that believes it saw every photo while two
    #: were missing draws wrong conclusions and never finds out.
    #:
    #: ``ge=1`` is load-bearing (SEC-008). The reader used to clamp the value at
    #: zero and the guard returned early on a non-positive ceiling, so
    #: ``MCP_MAX_IMAGE_PAYLOAD_MB=0`` — and every negative value — meant
    #: **unlimited**: the exact opposite of what an operator setting it to zero
    #: intends, and the amplifier for any unbounded-assembly bug. There is no
    #: sensible "off" for this ceiling, so the value is refused at startup
    #: instead of being reinterpreted.
    mcp_max_image_payload_mb: int = Field(default=4, ge=1)

    # ── REQ-013 §2.3a — diary environment snapshot ───────────────────────────
    #: Kill-switch. Off means every new entry is stored with
    #: ``environment_status: not_attempted`` — honest, and distinguishable from
    #: "we looked and found nothing".
    diary_environment_capture_enabled: bool = True
    #: A reading older than this is **not** captured. An entry that claims
    #: "22 °C" from a sensor that last spoke yesterday is worse evidence than an
    #: entry with no climate at all, so the bound errs towards dropping.
    #:
    #: 60 minutes: indoor climate sensors report every few minutes, and even a
    #: battery-powered Zigbee/BLE hygrometer with a heartbeat sends within the
    #: hour, so a healthy sensor is always well inside the window. An hour is
    #: also the coarsest resolution at which "the conditions when the grower
    #: looked" is still the same weather situation — beyond it the value
    #: describes a different afternoon.
    #:
    #: Global rather than per-tenant on purpose: the bound follows from sensor
    #: reporting cadence, which is a property of hardware, not of a garden.
    diary_environment_max_age_minutes: int = Field(default=60, ge=1)
    #: Hard wall-clock ceiling for the whole capture. Creating a diary entry is
    #: an interactive POST and the write itself costs milliseconds; a sensor read
    #: that hangs must not hold it. Every outbound call inside the capture is
    #: given at most the time left of this budget, so the create can never wait
    #: longer than this on the environment.
    #:
    #: 3 s: still inside "the save felt immediate", and generous enough for a LAN
    #: Home Assistant to answer several entities. Overrunning it is not an error
    #: state of the entry — it is recorded as ``environment_status: unavailable``
    #: with whatever arrived in time.
    diary_environment_capture_timeout_seconds: float = Field(default=3.0, gt=0)

    # Shared secret for the cluster-internal M2M services (knowledge-service,
    # inference-service). Sent as ``Authorization: Bearer <token>`` on every
    # call. Must match the token those services expect (same key in
    # ``kamerplanter-secrets``). Required in production once either service is
    # enabled — the startup gate refuses to boot without it (AP-4, INF-S1/S2).
    internal_service_token: str = ""

    # mDNS / Zeroconf Discovery
    mdns_enabled: bool = False  # Enable only for local/on-premise deployments (opt-in)
    # Auto-generated UUID prefix if empty; alphanumeric + hyphens only, max 64 chars
    instance_id: Annotated[str, Field(max_length=64, pattern=r"^[a-zA-Z0-9\-]*$")] = ""

    # Rate limiting
    rate_limit_auth: str = "20/minute"
    rate_limit_general: str = "100/minute"
    #: ``POST /api/v1/privacy/email-change`` (REQ-025 Art. 16), per client IP.
    #:
    #: Deliberately far below ``rate_limit_auth`` rather than equal to it. The
    #: ``/auth/*`` routes are interactive retry surfaces — a user who mistypes a
    #: password legitimately submits several times a minute — and their per-minute
    #: budget is sized for that. This endpoint is different in kind: every call
    #: mails a **caller-chosen address**, either the verification link (free
    #: address) or the "someone tried to use your address" notice (taken one), so
    #: its limit bounds outbound mail to third parties, not login retries.
    #: 20/minute would allow 1200 such mails an hour from one source. Changing an
    #: account's address is a rare, deliberate act; a handful of attempts an hour
    #: covers a typo plus a change of mind.
    rate_limit_email_change: str = "5/hour"
    #: ``POST /api/v1/privacy/email-change/confirm`` (REQ-025 Art. 16), per client IP.
    #:
    #: **Why there is a limit at all** (#990). The endpoint is unauthenticated and
    #: state-changing. The argument for leaving it alone — the token is 32 random
    #: bytes compared by hash, so guessing is not a realistic attack — is true
    #: today and is a property of *code*, which can change without anyone
    #: re-deriving this decision. A limit is cheap insurance that does not depend
    #: on that property holding.
    #:
    #: **Why not ``rate_limit_email_change``.** That one bounds outbound mail to a
    #: caller-chosen address, so its budget is cumulative and its window is an
    #: hour. Confirming sends no mail; it bounds token *attempts*, where the thing
    #: worth bounding is a burst from one source, not an hourly quota. An hourly
    #: budget would also keep punishing a legitimate user long after a retry storm
    #: spent it. A limit sized for a different threat is a limit nobody can reason
    #: about, so this is its own setting with its own window.
    #:
    #: **Where 10 comes from — the legitimate side, not the attacker side.** No
    #: per-IP figure makes a 2^256 token guessable or ungessable; an attacker with
    #: many source addresses is not bounded by anything ``get_remote_address`` can
    #: see. So the number is chosen as "comfortably above legitimate use, and no
    #: higher". Legitimate use is one request; a reload or a retry over a flaky
    #: connection makes two or three. Ten leaves room for several people
    #: confirming in the same minute behind one NAT — for an act each account
    #: performs a handful of times ever.
    #:
    #: **Link prefetching does not apply here**, which is the standard objection
    #: to a tight limit on a confirm link. Outlook Safe Links, Gmail's proxy and
    #: corporate URL detonation issue **GET** requests; this is a ``POST`` with a
    #: JSON body, so a prefetcher cannot spend the budget. A sandbox that renders
    #: the landing page and executes its JavaScript could — ten absorbs that too.
    rate_limit_email_change_confirm: str = "10/minute"
    #: ``POST /api/v1/auth/refresh``, per client IP (#1131).
    #:
    #: **Why its own setting and not ``rate_limit_auth``.** That budget's own
    #: docstring sizes it for "an interactive retry surface — a user who mistypes
    #: a password". Refresh is the opposite of interactive: ``AuthProvider``
    #: dispatches one on **every** app bootstrap — every tab, every reload, and
    #: anonymous visitors too (they get 401, but the limiter runs first and the
    #: attempt is spent) — plus one per 401 the interceptor retries. Behind a
    #: corporate NAT or CGNAT, twenty page loads a minute from one address is
    #: ordinary traffic, and the twenty-first would be refused.
    #:
    #: **Why a limit at all**, given that the token is a 512-bit-class secret
    #: looked up by hash: this is the only public token-*accepting* endpoint in
    #: ``/auth/*`` with a body transport (#1118), and every other one carries a
    #: budget. Defence in depth, sized so it cannot fire on legitimate use.
    rate_limit_token_refresh: str = "60/minute"
    #: ``POST /api/v1/auth/device-pairing/redeem`` (#1118), per client IP.
    #:
    #: **Why its own setting and not ``rate_limit_auth``.** The ``/auth/*`` budget
    #: is sized for an interactive retry surface — a user who mistypes a password
    #: legitimately submits several times a minute. Redemption is not that: the
    #: code is scanned from a QR image, so the legitimate client submits it
    #: **once**, and a second attempt only happens after re-scanning a fresh code.
    #: There is no typo to retry, hence no reason to fund twenty attempts a minute.
    #:
    #: **What it does and does not bound.** It bounds a burst from one source
    #: address; it is not what makes the 256-bit code unguessable (nothing per-IP
    #: is, against an attacker with many addresses — that is the code's entropy
    #: plus the 60–120 s TTL). The behavioural guard is the per-IP lockout in
    #: ``AuthService.redeem_device_pairing``; this limit sits in front of it so a
    #: flood never reaches the code store at all.
    #:
    #: **Where 10 comes from — the legitimate side.** One scan is one request.
    #: Ten leaves room for several people pairing devices in the same minute
    #: behind one NAT address, and stays deliberately below ``rate_limit_auth`` so
    #: the two surfaces cannot be confused for one budget.
    rate_limit_device_pairing_redeem: str = "10/minute"
    #: ``GET /api/health``, per client IP (#1210, SEC-003).
    #:
    #: **Why this endpoint has a limit and the Kubernetes probes do not.** The
    #: cluster probes ``/api/v1/health/live`` and ``/api/v1/health/ready``
    #: (``helm/kamerplanter/values.yaml``), which stay unlimited — throttling a
    #: kubelet would restart healthy pods. ``/api/health`` is the *public* M2M
    #: endpoint: unauthenticated by design (major negotiation happens before there
    #: is a token, #1124) and doing real work per call — it walks the whole router
    #: graph for ``supported_majors`` and, where those integrations are enabled,
    #: performs **synchronous** probes against TimescaleDB and the knowledge
    #: service. That last part is the actual amplification: an unauthenticated
    #: caller could drive load into internal services one cheap request at a time.
    #: The limiter had no ``default_limits``, so an undecorated route was
    #: unbounded; this route is decorated rather than a global default being
    #: introduced, because a global default would silently re-price every route in
    #: the application.
    #:
    #: **Where 60 comes from — the legitimate side.** A Home Assistant integration
    #: polls on the order of once a minute, an Android client calls this once per
    #: base-URL negotiation, an operator during an incident a handful of times.
    #: Sixty a minute leaves an order of magnitude of headroom for several such
    #: clients behind one NAT address while still bounding a flood.
    rate_limit_health: str = "60/minute"

    #: How many proxy addresses **our own** infrastructure appends to the right
    #: end of ``X-Forwarded-For`` (#1151).
    #:
    #: Every proxy in the chain appends, so the trustworthy entries sit at the
    #: right and anything a caller invents is pushed left. `resolve_client_ip`
    #: therefore counts in from the right by this many entries. Reading the
    #: *left-most* entry — what it did before — hands the caller the pen:
    #: ``nginx.conf`` proxies with ``$proxy_add_x_forwarded_for``, so a
    #: client-supplied header survives as the left-most value, and the controls
    #: that key on it (the device-pairing lockout, the service-account
    #: ``ip_allowlist``) could be walked around by rotating it.
    #:
    #:   * ``0`` — client → nginx → backend (the e2e and dev stacks): the caller
    #:     is the last entry, the one nginx wrote.
    #:   * ``1`` — client → ingress → nginx → backend (production): nginx
    #:     appended the ingress's address, so the caller is second to last.
    #:
    #: **The default is the shallow one deliberately.** Set too low, the resolved
    #: address drifts towards the nearest proxy and the controls bind more
    #: coarsely than intended — a degradation (this is the shared-bucket problem
    #: #1130 describes). Set too high, the resolver starts reading entries a
    #: caller can write — a bypass. A deployment that adds a hop must raise this;
    #: forgetting to is safe, forgetting the other direction is not.
    #:
    #: ``ge=0`` is not decoration: a negative value made `resolve_client_ip`
    #: index past the end of the chain and raise ``IndexError`` on every request
    #: carrying the header — a typo would have become an HTTP 500 crashloop on
    #: device pairing, MCP auth and service-account validation instead of a
    #: startup failure.
    trusted_proxy_hops: int = Field(default=0, ge=0)

    # REQ-025 Privacy / GDPR
    erasure_tombstone_salt: str = ""  # NFR-011 §4: must be >= 32 chars in production
    privacy_data_controller_name: str = "Kamerplanter Operator"
    privacy_data_controller_email: str = "privacy@kamerplanter.example"
    privacy_export_retention_hours: int = 72  # NFR-011 R-05
    privacy_hard_delete_after_days: int = 90  # NFR-011 R-01
    privacy_email_change_ttl_hours: int = 24

    # REQ-030 Notifications
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    vapid_contact_email: str = ""
    # SEC-001 — optional operator allowlist for Web Push endpoints (SSRF hardening).
    # Comma-separated host suffixes (e.g. "fcm.googleapis.com,updates.push.services.mozilla.com").
    # Empty (default) → fall back to https + private-IP rejection so self-hosted push works.
    pwa_push_endpoint_allowed_hosts: str = ""
    notification_quiet_hours_default: str = "22:00-07:00"
    notification_batch_window_minutes: int = 30
    notification_escalation_days: str = "2,4,7"

    # NFR-013 Object storage (§4.1) — defaults target the local-fs backend.
    storage_backend: str = "local-fs"  # local-fs | s3
    storage_max_file_size_mb: int = 25
    storage_presign_ttl_seconds: int = 900
    storage_virus_scan_enabled: bool = False
    storage_virus_scan_endpoint: str = ""
    # NFR-013 §5.1 step 1 — per-tenant attachment quota (0 = unlimited).
    storage_tenant_quota_mb: int = 2048
    # NFR-013 §5.1 step 7 — strip image EXIF/GPS on upload by default.
    storage_strip_exif: bool = True
    # REQ-034 §3 (SR-004) — max gallery photos per plant instance (0 = unlimited).
    storage_max_photos_per_instance: int = 50
    # REQ-034 §4.3 (SR-005a) — per-tenant cap on open ``pending_review``
    # user-contributed DINOv2 reference embeddings (index-poisoning guard).
    reference_contribution_pending_limit: int = 100
    # SEC-002 (issue #447) — per-user daily cap on interactive reference
    # contributions (``POST /identification/reference``). Guards the global
    # reference index against a single account poisoning/flooding it. ``0``
    # disables the limit. Local (self-hosted) path → fails open on a Redis outage.
    reference_contribution_rate_limit_per_user_day: int = 20
    # NFR-013 §5.2 — global MIME whitelist (CSV string). Per-category overrides
    # are read from ``storage_allowed_mime_types_<category>`` (empty = default).
    storage_allowed_mime_types: str = (
        "image/jpeg,image/png,image/webp,image/heic,application/pdf,text/csv,application/zip"
    )
    storage_allowed_mime_types_diary: str = ""
    storage_allowed_mime_types_ipm: str = ""
    storage_allowed_mime_types_harvest: str = ""
    storage_allowed_mime_types_post_harvest: str = ""
    storage_allowed_mime_types_plant: str = ""
    storage_allowed_mime_types_pest_reference: str = ""
    storage_allowed_mime_types_id_recognition: str = ""
    storage_allowed_mime_types_task: str = ""
    storage_allowed_mime_types_import: str = "text/csv,application/zip"
    storage_allowed_mime_types_export: str = "application/pdf,text/csv,application/zip"
    storage_allowed_mime_types_tenant_export: str = "application/pdf,text/csv,application/zip"
    # local-fs backend
    storage_local_fs_root: str = "/data/attachments"
    storage_local_fs_public_base_url: str = ""
    # Signing secret for local-fs token URLs; falls back to jwt_secret_key /
    # fernet_key when left empty (resolved at adapter construction).
    storage_localfs_signing_secret: str = ""
    # s3 backend
    storage_s3_endpoint_url: str = ""
    storage_s3_region: str = ""
    storage_s3_bucket: str = ""
    storage_s3_access_key_id: str = ""
    storage_s3_secret_access_key: str = ""
    storage_s3_use_path_style: bool = False
    storage_s3_kms_key_id: str = ""
    storage_s3_force_tls: bool = True
    # SSRF guard for the admin "test connection" probe (SEC-002, NFR-013).
    # Link-local / cloud-metadata ranges (169.254.0.0/16, fd00:ec2::254) are
    # ALWAYS blocked. Private / loopback S3 endpoints (e.g. an in-cluster MinIO
    # at http://minio.default.svc or http://localhost:9000) are legitimate but
    # are only probed when this opt-in is enabled by the operator.
    storage_s3_allow_private_endpoint: bool = False

    model_config = {"env_prefix": "", "case_sensitive": False, "env_nested_delimiter": "__"}

    def resolve_build_revision(self) -> str:
        """Resolve the git SHA the running build was made from (#1210).

        The resolution is deliberately trivial, and each part of it is a decision:

        * **Verbatim when set and shaped like a revision.** The value exists to be
          compared against the image's ``org.opencontainers.image.revision``
          annotation and against ``git log``. Truncating, case-folding or deriving
          anything here would defeat the one question it answers — "is the build I
          am looking at the commit I think it is?".
        * **``"unknown"`` when absent.** An unset ``BUILD_REVISION`` and the empty
          ``ENV BUILD_REVISION=""`` that an unbaked image carries are the same
          situation and must not be told apart. Never substituted with
          ``app_version``: a plausible-looking wrong answer is worse than no
          answer, because it is the answer an operator would act on.
        * **``"unknown"`` when malformed** (SEC-002). Only ``[0-9a-f]{7,40}``
          leaves this method. Surrounding whitespace is stripped first, because a
          Helm- or shell-rendered value arrives padded and the SHA inside it is
          recoverable *exactly* — reporting "unknown" for a correctly stamped build
          because YAML added a newline would destroy information, not protect it.
          Anything the strip does not rescue is not a revision and is not reported
          as one.

        **What this field is evidence of — and what it is not** (SEC-007). It is an
        **operational** signal answering "did my fix arrive?". It is **not an
        integrity attestation**. ``Settings`` runs with ``env_prefix: ""``, so any
        ``BUILD_REVISION`` present in the environment overrides whatever the image
        baked in; a compromised or hand-edited deployment can therefore report a
        benign SHA while running something else. The authoritative proof of what an
        image contains is ``gh attestation verify`` against the image digest read
        from ``.status.containerStatuses[].imageID`` — the same distinction
        ``.github/workflows/docker-publish.yml`` draws for build provenance. Never
        cite this field as a compliance record.

        Returns:
            The full git SHA as baked into the image, or :data:`UNKNOWN_BUILD_REVISION`.
        """
        candidate = self.build_revision.strip()
        # ``fullmatch``, not ``match``: Python's ``$`` also matches before a
        # trailing newline, so ``match`` would admit ``"<sha>\n"`` if the strip
        # above were ever removed. Two guards, because only one of them is visible
        # in the pattern text.
        return candidate if _BUILD_REVISION_SHAPE.fullmatch(candidate) else UNKNOWN_BUILD_REVISION

    def allowed_mime_types_for_category(self, category: str) -> list[str]:
        """Resolve the allowed-MIME whitelist for an attachment category (NFR-013 §5.2).

        Resolution order:
          1. An explicit ``storage_allowed_mime_types_<category>`` override, if set.
          2. For photo categories without an override, an image-only subset of
             the global whitelist (``image/jpeg,png,webp,heic``).
          3. The global ``storage_allowed_mime_types`` list.
        """
        global_types = _split_csv(self.storage_allowed_mime_types)

        override = _split_csv(getattr(self, f"storage_allowed_mime_types_{category}", ""))
        if override:
            return override

        if category in _PHOTO_CATEGORIES:
            image_types = [m for m in global_types if m in _PHOTO_MIME_TYPES]
            return image_types or global_types

        return global_types


# Categories that semantically only accept images (NFR-013 §5.2). Without an
# explicit override these fall back to the image-only subset of the whitelist.
_PHOTO_CATEGORIES: frozenset[str] = frozenset(
    {"diary", "ipm", "harvest", "post_harvest", "plant", "pest_reference", "id_recognition", "task"}
)
_PHOTO_MIME_TYPES: frozenset[str] = frozenset({"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"})


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


settings = Settings()

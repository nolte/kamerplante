# Environment Variables

All configuration parameters for the Kamerplanter backend are controlled via environment variables. Variables are loaded by `pydantic-settings` — case sensitivity is not relevant.

!!! tip "Local configuration"
    For the Docker Compose environment, add all values to a `.env` file in the repository root directory. A template is provided as `.env.example`:
    ```bash
    cp .env.example .env
    ```

---

## Database Connection

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `ARANGODB_HOST` | `localhost` | Yes | Hostname or IP address of the ArangoDB instance |
| `ARANGODB_PORT` | `8529` | No | TCP port of ArangoDB |
| `ARANGODB_DATABASE` | `kamerplanter` | Yes | Name of the target database |
| `ARANGODB_USERNAME` | `root` | Yes | Database user |
| `ARANGODB_PASSWORD` | — | Yes | Password for the database user |
| `ARANGO_ROOT_PASSWORD` | — | Yes* | Root password for the ArangoDB container (Docker only) |

*`ARANGO_ROOT_PASSWORD` is passed directly to the ArangoDB container and is required to start the database.

!!! warning "Production passwords"
    Never use the default value `rootpassword` in production environments. Generate secure passwords: `openssl rand -hex 32`

---

## Cache and Task Queue

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Yes | Connection URL for Redis or Valkey (Celery broker and backend cache) |

**Format:** `redis://[user]:[password]@[host]:[port]/[db]`

**Examples:**
```
redis://localhost:6379/0                    # Local without auth
redis://:mypassword@redis:6379/0            # With password
rediss://user:pass@redis-host:6380/1        # TLS (rediss://)
```

---

## Security and Authentication

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production-...` | Yes | Secret key for JWT signing (HS256) |
| `JWT_ALGORITHM` | `HS256` | No | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | No | JWT access token validity in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | No | Refresh token validity in days |
| `SESSION_TOKEN_EXPIRE_HOURS` | `24` | No | Validity of server-side session tokens, in hours. |
| `FERNET_KEY` | — | Yes | Fernet key for encrypting OIDC provider secrets. **Required regardless of whether OIDC is used** — the startup gate refuses to start in production when this is empty (AP-4, INF-S5). Must be a valid Fernet key: 32 bytes, url-safe base64-encoded (44 characters) — generate e.g. with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | No | Require email verification at registration |
| `HIBP_ENABLED` | `false` | No | Enable "Have I Been Pwned" check on password change |
| `COOKIE_SECURE` | `true` | No | Sets the `Secure` flag on the refresh-token cookie. Only set to `false` for plain-HTTP E2E test environments without TLS — **always** leave `true` in production. |

!!! danger "Change JWT_SECRET_KEY in production"
    The default value `change-me-in-production-use-openssl-rand-hex-32` **must not** be used in production. Generate a secure value:
    ```bash
    openssl rand -hex 32
    ```
    Changing `JWT_SECRET_KEY` invalidates all active tokens — all users will be logged out.

---

## Privacy & GDPR (REQ-025 / NFR-011) {#datenschutz-dsgvo-req-025-nfr-011}

These variables control the legally mandated deletion/anonymization of personal data (see [Privacy (GDPR)](../user-guide/privacy.md)) and are independent of the operating mode — they apply in both Light and Full mode.

<!-- Source: src/backend/app/config/settings.py (erasure_tombstone_salt, privacy_data_controller_name, privacy_data_controller_email, privacy_export_retention_hours, privacy_hard_delete_after_days, privacy_email_change_ttl_hours); src/backend/app/main.py (insecure_default_secrets) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `ERASURE_TOMBSTONE_SALT` | — | Yes | High-entropy secret (at least 32 characters) used to pseudonymize deleted user accounts (tombstone hashing, NFR-011 §4). **The startup gate refuses to start in production** if this value is empty or shorter than 32 characters — regardless of operating mode. Generate with `openssl rand -hex 32`. |
| `PRIVACY_DATA_CONTROLLER_NAME` | `Kamerplanter Operator` | No | Name of the data controller, shown in export and disclosure documents. |
| `PRIVACY_DATA_CONTROLLER_EMAIL` | `privacy@kamerplanter.example` | No | Contact email of the controller for GDPR requests. |
| `PRIVACY_EXPORT_RETENTION_HOURS` | `72` | No | How long a generated data export (Art. 15/20 GDPR) is kept before automatic deletion. |
| `PRIVACY_HARD_DELETE_AFTER_DAYS` | `90` | No | Grace period before an account marked for deletion is permanently (hard-)deleted. |
| `PRIVACY_EMAIL_CHANGE_TTL_HOURS` | `24` | No | Validity of the confirmation link when changing an email address. |

!!! danger "ERASURE_TOMBSTONE_SALT — a boot blocker in production"
    Unlike most other variables on this page, `ERASURE_TOMBSTONE_SALT` is **not an optional feature flag**: in production (`DEBUG=false`) the backend simply refuses to start when this value is missing or too short — regardless of whether GDPR erasure requests are actively used. For a full list of unconditionally required secrets, see [Configuration Matrix — Mandatory Secrets per Enabled Feature](../deployment/konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

---

## Operating Mode

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `KAMERPLANTER_MODE` | `full` | No | Operating mode: `full` (auth + tenants) or `light` (no auth, local single-user) |
| `DEBUG` | `false` | No | Enable debug logging (verbose — never use in production). Also disables the startup gate for production secrets — **never** set this in production. |
| `FRONTEND_URL` | `http://localhost:5173` | No | Frontend URL (used for email links) |
| `APP_BASE_URL` | `http://localhost:5173` | No | Base URL for QR codes on plant labels (print views, see [Print & Export](../user-guide/print-export.md)). Set to the publicly reachable frontend URL in production, otherwise printed QR codes point to `localhost`. |

### Light Mode (`KAMERPLANTER_MODE=light`)

In Light Mode, token authentication is disabled. The API is usable without login. This mode is intended for local single-user installations that are not exposed to the internet.

!!! danger "Do not expose Light Mode publicly"
    Light Mode disables all authentication layers. Never run it with a publicly accessible port.

---

## CORS Configuration

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | No | JSON array of allowed origins for CORS |

**Format:** Always as a JSON array in string format:
```bash
CORS_ORIGINS='["https://app.example.com","https://app2.example.com"]'
```

---

## Email

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `EMAIL_ADAPTER` | `console` | No | Email adapter: `console` (output to log), `smtp`, `resend` |
| `SMTP_HOST` | `localhost` | No | SMTP server hostname |
| `SMTP_PORT` | `587` | No | SMTP port |
| `SMTP_USERNAME` | — | No | SMTP username |
| `SMTP_PASSWORD` | — | No | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@kamerplanter.example` | No | Sender address for system emails |
| `SMTP_USE_TLS` | `true` | No | Enable STARTTLS for SMTP |

In development mode (`EMAIL_ADAPTER=console`), emails are not sent but printed to the backend log.

!!! note "Also used by the notification system"
    These variables also configure the email channel of the [notification system](../user-guide/notifications.md#email) — there is no separate SMTP configuration for notifications.

---

## External Data Enrichment (REQ-011)

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `PERENUAL_API_KEY` | — | No | API key for Perenual plant database |
| `TREFLE_API_KEY` | — | No | API key for Tréflé plant database |
| `ENRICHMENT_HTTP_TIMEOUT` | `30` | No | HTTP timeout for external API requests (seconds) |

GBIF is used without an API key (public API). Perenual and Tréflé require free registration.

---

## Knowledge Service — Re-Ranking (optional)

These variables configure the optional cross-encoder re-ranker of the Knowledge Service. When `RERANKER_URL` is empty, the Knowledge Service operates in hybrid-search-only mode (graceful degradation). See [ADR-007](../adr/007-cross-encoder-reranking.md).

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `RERANKER_URL` | `` (empty) | No | HTTP URL of the reranker microservice, e.g. `http://reranker-service:8081`. Empty = re-ranking disabled. |
| `RERANKER_INITIAL_K` | `20` | No | Number of chunks retrieved from the Hybrid Search step (over-retrieval). |
| `RERANKER_TOP_K` | `5` | No | Number of chunks passed to the LLM context after re-ranking. |
| `RERANKER_MODEL` | `bge-reranker-v2-m3` | No | ONNX model name in the reranker service container (directory under `/app/models/onnx/`). |

!!! note "RERANKER_MODEL belongs to the reranker service, not the knowledge service"
    `RERANKER_MODEL` is set as an environment variable on the `reranker-service` container — not on the `knowledge-service`. The other three variables (`RERANKER_URL`, `RERANKER_INITIAL_K`, `RERANKER_TOP_K`) belong to the Knowledge Service.

!!! tip "Resource requirements"
    The reranker service requires 1.5–4 GB RAM (depending on the model) and adds ~500ms latency per request. For Raspberry Pi and resource-constrained environments, it is recommended to leave `RERANKER_URL` empty.

---

## AI Assistant <!-- REQ-031 --> {#ki-assistent}

These variables belong to the **Kamerplanter backend** and control the three-stage toggle mechanism as well as the connection to the Knowledge Service (see [AI Assistant — User Guide](../user-guide/ai-assistant.md)). Provider selection (Ollama/Anthropic/OpenAI-compatible) is a separate configuration **on the Knowledge Service itself** — see [AI Provider Setup](../user-guide/ai-providers.md).

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `AI_FEATURES_ENABLED` | `false` | No | Stage 1 of the three-stage toggle. `false` makes every `/ai/*` endpoint respond with HTTP 404 — the AI API then effectively doesn't exist. |
| `KNOWLEDGE_SERVICE_ENABLED` | `false` | No | Enables the connection to the Knowledge Service (needed by both the older `/api/v1/knowledge/*` path and internally by the AI Assistant). |
| `KNOWLEDGE_SERVICE_URL` | `http://knowledge-service:8000` | No | Base URL of the Knowledge Service microservice. |
| `AI_KNOWLEDGE_SERVICE_TIMEOUT_S` | `60` | No | HTTP timeout of the `KnowledgeServiceAdapter` against the Knowledge Service (seconds). |
| `AI_CIRCUIT_BREAKER_THRESHOLD` | `3` | No | Number of consecutive failures after which the adapter marks the Knowledge Service unreachable. |
| `AI_CIRCUIT_BREAKER_WINDOW_S` | `60` | No | Time window (seconds) over which failures are counted for `AI_CIRCUIT_BREAKER_THRESHOLD`. |
| `AI_CIRCUIT_BREAKER_COOLDOWN_S` | `60` | No | Wait time (seconds) before the adapter allows requests to the Knowledge Service again after the circuit breaker trips. |
| `AI_PUBLIC_RATE_LIMIT_PER_MIN` | `10` | No | IP rate limit for the anonymous, Light-Mode-capable endpoint `POST /api/v1/public/ai/ask` (requests per minute). |
| `INTERNAL_SERVICE_TOKEN` | — | Conditional | Shared secret for cluster-internal M2M calls (including to the Knowledge Service). Required once `KNOWLEDGE_SERVICE_ENABLED=true` is set — without a token, the startup gate refuses to boot (AP-4). |

!!! warning "Instance-wide activation alone isn't enough"
    `AI_FEATURES_ENABLED=true` only unlocks the AI API instance-wide (stage 1). For a specific tenant (garden) to actually use AI features, `tenant.settings.ai_features_enabled` must additionally be set for that tenant (stage 2) — there is currently neither a UI nor a dedicated API endpoint for this, see [AI Assistant — For Technical Users / Self-Hosters](../user-guide/ai-assistant.md#for-technical-users-self-hosters).

!!! info "Provider configuration lives on the Knowledge Service, not the backend"
    `LLM_PROVIDER`, `LLM_API_URL`, `LLM_API_KEY`, and `LLM_MODEL` are environment variables of the standalone Knowledge Service deployment (`src/knowledge-service/`), not this backend. Details: [AI Provider Setup](../user-guide/ai-providers.md).

---

## MCP Server <!-- REQ-033 --> {#mcp-server}

These variables control the [MCP server](../api/mcp-server.md) — the tool interface through which external LLM clients (Claude Desktop, Claude Code, custom agents) can access Kamerplanter via a service-account API key.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `MCP_SERVER_ENABLED` | `false` | No | Master switch. Until set to `true`, all `/mcp/*` endpoints answer HTTP 404 — the interface effectively does not exist. |
| `MCP_IDEMPOTENCY_TTL_HOURS` | `24` | No | Validity window for a write tool's `idempotency_key` — after it expires, a repeated call is treated as a new action. |
| `MCP_AUDIT_RETENTION_DAYS` | `90` | No | Retention window for the `mcp_audit_log` (NFR-011) — older entries are automatically deleted. |
| `MCP_MAX_IMAGE_PAYLOAD_MB` | `4` | No | Ceiling on the total payload of one call to the diary tool `get_diary_entry_photos`, in megabytes (Base64-encoded). Exceeding it returns the error code `payload.too_large` instead of silently dropping photos — see [MCP Server — Diary Analysis](../api/mcp-server.md#diary-analysis-external-agents). |

!!! note "No standalone process, no dedicated connection variables"
    The MCP server runs in-process with the existing backend and shares its ArangoDB/Redis connection — there is no separate host, port or credential configuration.

---

## Diary — Environment Snapshot

When a diary entry is created, Kamerplanter reads the sensor values covering the plant and stores them alongside — never merged into — the hand-noted measurements. See [Diary — The environment is recorded automatically](../user-guide/plant-diary.md#environment).

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DIARY_ENVIRONMENT_CAPTURE_ENABLED` | `true` | No | Master switch. With `false`, every new entry is stored marked "not attempted" — distinguishable from "we looked and found nothing". |
| `DIARY_ENVIRONMENT_MAX_AGE_MINUTES` | `60` | No | A reading older than this is **not** captured at all. An entry presenting yesterday's sensor value as current is worse evidence than an entry with no climate values. |
| `DIARY_ENVIRONMENT_CAPTURE_TIMEOUT_SECONDS` | `3.0` | No | Hard ceiling for the whole capture. When it runs out, the entry is stored with whatever arrived in time — creating an entry never waits longer on a sensor. |

!!! note "A failure never blocks the entry"
    An unreachable Home Assistant, a missing TimescaleDB or an exhausted time budget produce an entry **without** (or with incomplete) environment values, never a rejected creation.

---

## mDNS / Zeroconf Discovery

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `MDNS_ENABLED` | `false` | No | Enable mDNS service announcement (`_kamerplanter._tcp.local.`) |
| `INSTANCE_ID` | *(auto)* | No | Unique instance ID (e.g. `kp-abc123`). Auto-generated at startup if empty. |

When enabled, the backend announces a `_kamerplanter._tcp.local.` service on the local network. Home Assistant detects this service automatically and offers to set up the Kamerplanter integration.

!!! info "Stable Instance ID"
    The `INSTANCE_ID` is used for duplicate detection in Home Assistant. If left empty, a new ID is generated on every restart. For stable discovery, set a fixed value, e.g. `INSTANCE_ID=kp-my-server`.

### mDNS and Kubernetes

mDNS relies on Multicast UDP (port 5353) within the local Layer 2 network. In standard Kubernetes clusters, mDNS **does not work** because:

1. **Overlay network blocks multicast** — Standard CNIs (Calico, Cilium, Flannel) only route L3 traffic. Multicast packets from a pod never reach the physical LAN — Home Assistant cannot see the announcements.
2. **Pod IP is not LAN-reachable** — Even if multicast worked, the announced pod IP (e.g. `10.42.x.x`) would not be reachable from outside the cluster.

| Deployment | `MDNS_ENABLED` | Rationale |
|------------|:-----------:|-----------|
| Docker Compose / Bare Metal | `true` | Backend runs directly on the LAN — set `MDNS_ENABLED=true` |
| K3s / MicroK8s single-node + `hostNetwork: true` | `true` | Pod shares host network — multicast reaches the LAN |
| Standard K8s Cluster | `false` | Overlay network blocks multicast — use manual config flow in HA as fallback |
| Cloud (AWS, GCP, Azure) | `false` | No local network available |

!!! warning "hostNetwork is a trade-off"
    With `hostNetwork: true`, the pod shares the host's network namespace. Multicast works, but at the cost of network isolation (port conflicts possible, no NetworkPolicy enforcement). Only recommended for homelab / Raspberry Pi scenarios.

The Helm chart sets `MDNS_ENABLED` to `false` by default. The manual config flow in Home Assistant (URL input) works in every deployment scenario as a fallback.

---

## Home Assistant Integration (REQ-005)

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `HA_URL` | — | No | Home Assistant base URL, e.g. `http://homeassistant.local:8123` |
| `HA_ACCESS_TOKEN` | — | No | Long-Lived Access Token from Home Assistant |
| `HA_TIMEOUT` | `10` | No | HTTP timeout for HA requests (seconds) |
| `HA_ALLOW_PRIVATE_ENDPOINT` | `false` | No | SSRF opt-in: Home Assistant commonly runs on the LAN over HTTP at a private/RFC1918 address (`homeassistant.local`, `192.168.x.x`) or `localhost`. Without this opt-in, the SSRF guard blocks connections to such addresses. The cloud-metadata / link-local range (`169.254.0.0/16`) is **always** blocked regardless of this flag. |

When both `HA_URL`/`HA_ACCESS_TOKEN` are set, the backend also enables the Home Assistant channel of the [notification system](../user-guide/notifications.md#home-assistant) (persistent notifications, mobile push, TTS).

!!! warning "Apprise channel requires an additional Python package"
    The `apprise` notification channel is always active regardless of the Home Assistant variables, but requires the optional `apprise` Python package in the backend image (`pip install apprise`) — there is no dedicated environment variable for it. See [Notifications — Apprise](../user-guide/notifications.md#apprise) for details.

---

## Time-Series Data (TimescaleDB, REQ-005) {#zeitreihendaten-timescaledb-req-005}

These variables enable the optional TimescaleDB connection for high-frequency sensor time-series with automatic downsampling (see [Sensors](../user-guide/sensors.md)). Without `TIMESCALEDB_ENABLED=true`, manual and automatic readings are still stored in ArangoDB — the app remains fully functional, just without automatic multi-stage downsampling.

<!-- Source: src/backend/app/config/settings.py (timescaledb_enabled, timescaledb_host, timescaledb_port, timescaledb_database, timescaledb_username, timescaledb_password, timescaledb_pool_min_size, timescaledb_pool_max_size) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `TIMESCALEDB_ENABLED` | `false` | No | Master switch for the TimescaleDB connection. |
| `TIMESCALEDB_HOST` | `localhost` | No | Hostname of the TimescaleDB instance. |
| `TIMESCALEDB_PORT` | `5432` | No | TCP port. |
| `TIMESCALEDB_DATABASE` | `kamerplanter_sensors` | No | Database name. |
| `TIMESCALEDB_USERNAME` | `postgres` | No | Database user. |
| `TIMESCALEDB_PASSWORD` | `changeme` | Conditional | Database password. **Required in production** — the startup gate refuses to start when `TIMESCALEDB_ENABLED=true` is set and this value is still the unchanged `changeme` (see [Configuration Matrix — Mandatory Secrets per Enabled Feature](../deployment/konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion)). |
| `TIMESCALEDB_POOL_MIN_SIZE` | `2` | No | Minimum connection pool size. |
| `TIMESCALEDB_POOL_MAX_SIZE` | `10` | No | Maximum connection pool size. |

!!! note "Docker Compose: dedicated profile"
    In the local Docker Compose environment, TimescaleDB only starts with `docker-compose --profile timescaledb up -d`. In Kubernetes, the `timescaledb` controller is commented out in the chart by default — the operator adds it via `valuesObject` (see [Helm Charts](../deployment/helm.md)).

---

## Environment Control & Actuators (REQ-018) {#environment-control-actuators-req-018}

This variable controls the periodic evaluation of schedules and rules, the hourly override-expiry sweep, and the 5-minute online/offline sync with Home Assistant for [Environment Control & Actuators](../user-guide/actuator-control.md).

<!-- Source: src/backend/app/config/settings.py (actuator_control_loop_enabled) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `ACTUATOR_CONTROL_LOOP_ENABLED` | `false` | No | Kill switch for the three periodic actuator-control tasks (`evaluate_control_rules` every 30 s, `expire_manual_overrides` hourly, `sync_actuator_states` every 5 min). When disabled, schedules and rules are not evaluated automatically — actuators remain controllable via the REST API at any time regardless (direct command, override, emergency stop). |

!!! note "No separate HA toggle needed"
    Unlike the other Home Assistant features, actuator control needs no additional opt-in — as long as `HA_URL`/`HA_ACCESS_TOKEN` are set and `ACTUATOR_CONTROL_LOOP_ENABLED=true`, the system dispatches commands to Home Assistant actuators automatically.

---

## InvenTree Integration (REQ-016)

These variables enable the optional integration with [InvenTree](https://github.com/inventree/inventree). Without `INVENTREE_ENABLED=true`, every InvenTree endpoint returns a "feature disabled" error (HTTP 409) without blocking the app.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `INVENTREE_ENABLED` | `false` | No | Kill switch for the entire InvenTree integration. |
| `INVENTREE_ALLOW_PRIVATE_ENDPOINT` | `false` | No | Allows an InvenTree instance with a private/LAN address (analogous to `HA_ALLOW_PRIVATE_ENDPOINT`). Without this opt-in, SSRF protection blocks connections to internal addresses. |

You then set up the connection (including the API token) and links via the REST API — see [Equipment & Inventory (InvenTree) — For Technical Users / Self-Hosters](../user-guide/inventree.md#for-technical-users-self-hosters) for details.

---

## Weather Forecast & Frost Early-Warning <!-- REQ-046 / Issue #392 --> {#weather-forecast-frost-early-warning}

These variables control the weather forecast fetching and the proactive frost early-warning built on top of it. Without `WEATHER_ENABLED=true`, both features stay fully disabled — sites without a configured weather source are likewise unaffected.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `WEATHER_ENABLED` | `false` | No | Kill switch for the entire weather feature (source fetching + frost early-warning). See [Weather Sources per Location](../user-guide/weather-sources.md) for the actual source configuration. |
| `WEATHER_DEFAULT_PUBLIC_SOURCE` | `open-meteo` | No | Factory-default public weather source for new locations without an explicit choice. |
| `OPEN_METEO_ENABLED` | `true` | No | Instance-wide default for the Open-Meteo source (keyless, EU-focused). Overridable per instance by the platform admin via weather-service management (see [Configuring Weather Services](../user-guide/weather-services.md)) — this variable only sets the starting value. |
| `DWD_ENABLED` | `true` | No | Instance-wide default for the DWD/Bright Sky source (Deutscher Wetterdienst). Also platform-admin overridable. |
| `OPENWEATHERMAP_ENABLED` | `true` | No | Instance-wide default for the OpenWeatherMap source. Also platform-admin overridable. |
| `FROST_FORECAST_HORIZON_DAYS` | `2` | No | Forecast horizon in days from today (inclusive) scanned for an expected frost day — the default covers today plus the next day. |
| `FROST_FORECAST_THRESHOLD_CELSIUS` | `2.0` | No | Minimum temperature at or below which a forecast day counts as a frost day. Deliberately **separate** from the reactive threshold below, set a touch more conservative (closer to 0 °C) since a multi-day-ahead forecast carries more uncertainty than a live reading. |

For comparison — the existing **reactive** frost threshold (current measured temperature, unchanged by this feature):

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `FROST_WARNING_THRESHOLD_CELSIUS` | `3.0` | No | Threshold for the reactive frost warning (`binary_sensor.kp_{location}_frost_warning`), based on the most recently measured air temperature. |

---

## Climate Normals (NASA POWER) <!-- REQ-041 --> {#climate-normals-nasa-power}

These variables control the monthly background fetch of long-term climate normals (the "Climate at the Site" section) via the keyless NASA POWER reanalysis interface. Both `WEATHER_ENABLED` and `NASA_POWER_CLIMATE_ENABLED` must be active for the fetch to run.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `NASA_POWER_CLIMATE_ENABLED` | `true` | No | Dedicated kill switch for the monthly climate-normals task, independent of the general `WEATHER_ENABLED` — both must be active for the task to run. |
| `NASA_POWER_BASE_URL` | `https://power.larc.nasa.gov/api/temporal` | No | Base URL of the NASA POWER API. Only relevant for self-hosters with a different network/proxy setup. |
| `NASA_POWER_CLIMATE_TTL_DAYS` | `180` | No | Climate normals barely change; an already-fetched record is only re-fetched after this TTL expires — keeps the monthly task idempotent and spares the NASA POWER API. |
| `NASA_POWER_DATA_LATENCY_DAYS` | `7` | No | Affects the separate daily-values fetch (not the climate normals): number of days NASA POWER needs for quality control of its most recent daily values. |
| `NASA_POWER_DAILY_DAYS_BACK` | `14` | No | Also affects only the daily-values fetch: size of the look-back window in days. |

!!! note "Only affects outdoor and greenhouse sites with GPS coordinates"
    Climate normals are materialised only for sites of type **Outdoor** or **Greenhouse** with stored GPS coordinates — they're of no use for indoor sites and are not fetched for them. NASA POWER is usable without an API key; the data is licensed under CC BY 4.0 (attribution is delivered automatically alongside the data, see [Climate at the Site](../user-guide/weather-sources.md#climate-at-the-site)). <!-- REQ-041 -->

---

## Hardiness Zones (USDA) <!-- REQ-039 --> {#hardiness-zones-usda}

This variable controls the quarterly background refresh of a site's hardiness zone, automatically derived from its climate normals (see [Climate Zones & Hardiness](../guides/climate-zones.md)). The derivation builds on the climate normals — the associated task therefore only runs when both `WEATHER_ENABLED` and `NASA_POWER_CLIMATE_ENABLED` are also active.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `HARDINESS_ZONE_REFRESH_ENABLED` | `true` | No | Dedicated kill switch for the quarterly hardiness-zone task (Jan 1 / Apr 1 / Jul 1 / Oct 1, 05:00 UTC), independent of `NASA_POWER_CLIMATE_ENABLED` — both must be active for the task to run. Manually set zones (`hardiness_zone_source: manual`) are never overwritten by the task. |

!!! note "Only affects outdoor and greenhouse sites with GPS coordinates and existing climate normals"
    Like the climate normals themselves, the hardiness zone is only computed for sites of type **Outdoor** or **Greenhouse** with GPS coordinates — and only once at least one climate-normal record with a usable minimum temperature already exists for that site. Triggering it immediately and manually (independent of this schedule) is possible via the API — see [API Reference — Hardiness Zones](api-reference.md#hardiness-zones-usda). <!-- REQ-039 -->

---

## Irrigation Demand (ET₀) <!-- REQ-037 --> {#irrigation-demand-et0}

These variables control the daily background task that derives the FAO-56 reference evapotranspiration (ET₀) from an outdoor or greenhouse site's weather data and, from it, the net irrigation demand per planting run. The task additionally requires `WEATHER_ENABLED=true` — without fetched weather data there is nothing to compute. The resulting behaviour for end users is described in [Watering Log: Suggested Watering Volume](../user-guide/watering-log.md#suggested-watering-volume) and [Care Reminders: Why a Reminder Might Not Appear](../user-guide/care-reminders.md#why-a-reminder-might-not-appear).

<!-- Source: src/backend/app/config/settings.py (irrigation_demand_enabled, irrigation_root_zone_depth_mm) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `IRRIGATION_DEMAND_ENABLED` | `true` | No | Dedicated kill switch for the daily `compute_irrigation_demand` task (06:15), independent of the general `WEATHER_ENABLED` — both must be active for the task to run. |
| `IRRIGATION_ROOT_ZONE_DEPTH_MM` | `300.0` | No | Assumed effective root-zone depth in millimetres of soil. Used to convert a substrate's water-holding capacity (in percent) into a millimetre cap on the net irrigation demand — prevents an overly high daily recommendation under very dry starting conditions. |

!!! note "Outdoor and greenhouse sites only, no new REST endpoints"
    Irrigation demand is calculated only for sites of type **Outdoor** or **Greenhouse** with stored GPS coordinates — indoor sites stay on the interval-based watering schedule (REQ-022). There is no dedicated REST endpoint for it; the result flows into the UI through the existing watering-volume suggestion (`suggest_volume`) and the care-reminder engine.

!!! info "Calculation basis: aquacropeto (BSD-3-Clause)"
    The FAO-56 Penman-Monteith and Hargreaves formulas for ET₀ are computed via the Python library `aquacropeto` (PyPI package `aquacropeto`, BSD-3-Clause licence) — no ShareAlike/copyleft obligations for the Kamerplanter codebase. See `NOTICE.md` in the project root for details.

---

## Health endpoint and build identity {#health-endpoint}

The unauthenticated endpoint `GET /api/health` can answer which build is currently running. Because it is unauthenticated, that answer is off by default and the endpoint is rate-limited.

<!-- Quelle: src/backend/app/config/settings.py (health_expose_build_revision, build_revision, rate_limit_health), src/backend/app/main.py (root_health) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `HEALTH_EXPOSE_BUILD_REVISION` | `false` (the Helm chart sets `true`) | No | Whether `GET /api/health` discloses the `build_revision` field at all. With `false` the key is absent from the response entirely. The **application** default stays `false` — `helm/kamerplanter/values.yaml` sets `true` for Kubernetes installations since #1236, so the delivery state is auditable. |
| `BUILD_REVISION` | *(empty)* | No | The full Git commit the image was built from. It is baked in at container build time (`docker-publish.yml` passes it into the Dockerfile as a build argument); you only need to set it yourself when you build your own image. |
| `RATE_LIMIT_HEALTH` | `60/minute` | No | Rate limit for `GET /api/health`, per client IP. The Kubernetes probes point at `/api/v1/health/live` and `/api/v1/health/ready` and are **not** affected. |

!!! warning "Why the build identity is absent by default"

    What is sensitive is not the commit hash — the repository is public anyway —
    but the mapping *this host runs that commit*. From it follows the exact lag
    behind the development state, and with it the list of fixes this instance is
    missing. So enable the field deliberately — for instance on an instance that
    is only reachable inside your own network, or for the duration of an
    investigation. <!-- #1210 -->

**Three distinguishable response states** that must not be confused:

| Response | Meaning |
|---|---|
| The `build_revision` key is **absent** | `HEALTH_EXPOSE_BUILD_REVISION` is `false`. Deliberate configuration, not a defect. |
| `"unknown"` | Disclosure is allowed, but no revision was baked in (development image, unstamped build). |
| A 7- to 40-character hexadecimal value | The real answer. An image built by `docker-publish.yml` reports the full 40-character SHA; a self-built image using `BUILD_REVISION=$(git rev-parse --short HEAD)` reports correspondingly fewer. |

Before it is reported, the value is checked against `^[0-9a-f]{7,40}$` (after stripping whitespace, so a YAML-folded or shell-quoted value survives). Anything else becomes `"unknown"` — never a fabricated or derived value.

!!! note "An operational signal, not an attestation"
    `build_revision` states what the instance claims about itself. Whoever compromised the deployment can make it report any hash. The load-bearing proof remains `gh attestation verify` together with the digest from the pod's `.status.containerStatuses[].imageID` — see [CI/CD — Checks along the delivery chain](../deployment/ci-cd.md#checks-delivery-chain).

---

## Rate Limiting

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `RATE_LIMIT_AUTH` | `20/minute` | No | Rate limit for authentication endpoints |
| `TRUSTED_PROXY_HOPS` | `0` | **Yes, behind two proxies** | How many proxy addresses your infrastructure appends to `X-Forwarded-For`, counted from the right. `0` = client → nginx → backend (dev/e2e); `1` = client → Traefik → nginx → backend (the Helm chart sets this). Too low resolves every caller to the nearest proxy — the device-pairing lockout then locks all users at once and IP-allowlisted service accounts fail closed; too high reads entries a caller can forge. |
| `RATE_LIMIT_GENERAL` | `100/minute` | No | Rate limit for general API endpoints |
| `RATE_LIMIT_HEALTH` | `60/minute` | No | Rate limit for `GET /api/health` — see [Health endpoint and build identity](#health-endpoint) |

**Format:** `[count]/[unit]` — units: `second`, `minute`, `hour`, `day`

---

## Nested Configuration (GBIF)

GBIF settings can be passed using the double-underscore delimiter for nesting:

| Variable | Default | Description |
|----------|---------|-------------|
| `GBIF__BASE_URL` | `https://api.gbif.org/v1` | GBIF API base URL |
| `GBIF__RATE_LIMIT_PER_MINUTE` | `60` | Requests per minute to GBIF |
| `GBIF__HTTP_TIMEOUT` | `30` | Timeout for GBIF requests (seconds) |

---

## Photo Identification (REQ-029)

These variables configure optional plant recognition by photo. If none of the API keys are set, the feature is completely disabled — all camera buttons are hidden and no consent dialog is shown.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `PLANTNET_API_KEY` | — | No | API key for Pl@ntNet (free tier: ≤ 500 identifications/day). Register at [my.plantnet.org](https://my.plantnet.org). |
| `PLANTNET_ENABLED` | `true` | No | Disables the Pl@ntNet adapter entirely, even if `PLANTNET_API_KEY` is set. Set to `false` to turn off Pl@ntNet despite a configured key (e.g. when relying exclusively on self-hosted DINOv2 recognition). |
| `PLANTNET_BASE_URL` | `https://my-api.plantnet.org/v2` | No | Pl@ntNet API base URL. Only change for self-hosting or test endpoints. |
| `PLANT_ID_API_KEY` | — | No | API key for Plant.id (Kindwise) — an additional, purely operator-opt-in cloud adapter (never auto-primary, unlike Pl@ntNet). |
| `PLANT_ID_BASE_URL` | `https://plant.id/api/v3` | No | Plant.id API base URL. |
| `INFERENCE_SERVICE_ENABLED` | `false` | No | Enables the self-hosted DINOv2 recognition path (REQ-029-A). For the full setup (VectorDB, reference-index population, activation order) see [Setting Up Plant Identification](../deployment/inference-service.md). |
| `INFERENCE_SERVICE_URL` | `http://kamerplanter-recognition:8000` | No | Internal URL of the inference service. |
| `IDENTIFICATION_PRIMARY_ADAPTER` | `plantnet` | No | Preferred adapter. Possible values: `plantnet`, `local_embedding` (DINOv2, once `INFERENCE_SERVICE_ENABLED=true`). |
| `IDENTIFICATION_HTTP_TIMEOUT` | `60` | No | HTTP timeout (seconds) for the external identification call (Pl@ntNet's upload + server-side ML inference can exceed the previous 30-second default under load). |
| `IDENTIFICATION_CONFIDENCE_AUTO_ACCEPT` | `0.85` | No | Confidence threshold (0–1) above which a suggestion is highlighted as "very certain". |
| `IDENTIFICATION_CONFIDENCE_MIN_SHOW` | `0.10` | No | Minimum confidence (0–1) required to show a suggestion. Results below this are filtered out. |
| `IDENTIFICATION_MAX_IMAGE_SIZE_MB` | `5` | No | Maximum image size in megabytes. Larger images are rejected with HTTP 400. |
| `IDENTIFICATION_MAX_IMAGE_DIMENSION` | `1024` | No | Longest edge (px) the user image is downscaled to before upload to the adapter. Smaller = faster upload and less third-party bandwidth. |
| `IDENTIFICATION_RATE_LIMIT_PER_USER_DAY` | `50` | No | Maximum requests per user per day (SEC-003 floor, preventing a single account from consuming the whole shared free-tier quota). `0` uses the adapter default limit instead (500 for Pl@ntNet). |
| `IDENTIFICATION_EXTERNAL_IN_LIGHT_MODE` | `false` | No | Operator opt-in for the *external* recognition path (Pl@ntNet) in [Light Mode](../user-guide/light-mode.md). Light Mode has no consent subsystem, so sending a photo to a third party requires a deliberate operator decision. While this stays `false`, only the self-hosted `local_embedding` path is usable in Light Mode (once `INFERENCE_SERVICE_ENABLED=true` is set). |
| `REFERENCE_CONTRIBUTION_RATE_LIMIT_PER_USER_DAY` | `20` | No | Maximum number of reference-image contributions (`POST /identification/reference`) per user per day — protects the recognition index against abuse/flooding from a single account. `0` disables the limit. Only relevant when self-hosted DINOv2 recognition is active (see [Self-Hosted Recognition with DINOv2](../user-guide/plant-identification.md#self-hosted-recognition-with-dinov2)). <!-- Issue #447 --> |

!!! warning "Pl@ntNet for non-commercial use only"
    The Pl@ntNet free tier is licensed for non-commercial use. For commercial instances review the terms of use at [my.plantnet.org](https://my.plantnet.org).

!!! tip "Kubernetes Secrets"
    The `PLANTNET_API_KEY` should be stored as a Kubernetes Secret:
    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: kamerplanter-identification
    type: Opaque
    stringData:
      PLANTNET_API_KEY: "your-api-key"
    ```

### Feature Toggle Logic

```
PLANTNET_API_KEY set?
  ├── Yes  → Pl@ntNet active (species identification, ≤ 500 IDs/day)
  └── No   → Feature completely disabled
             (camera buttons hidden, no consent dialog)
```

---

## Pest Detection (REQ-044) {#pest-detection-req-044}

These variables configure the optional image-based pest detection feature. The feature is disabled by default — without `PEST_DETECTION_ENABLED=true`, the "Check for Pests" button is hidden and the app is fully functional.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PEST_DETECTION_ENABLED` | `false` | No | Master switch. Set to `true` to enable the feature. |
| `PEST_DETECTION_SYMPTOM_ENABLED` | `true` | No | Damage pattern / symptom detection (mode 2) on/off. Active when `PEST_DETECTION_ENABLED=true`. |
| `PEST_DETECTION_DETECTOR_ENABLED` | `false` | No | Direct detector (mode 1, Phase 2) on/off. Requires a trained ONNX detector. |
| `PEST_DETECTION_DEMO_ENABLED` | `false` | No | Demo adapter (no external service, no real model). Previews the full UI flow with clearly-labelled placeholder findings while the trained backend is externally blocked. Preview only — not for real decisions. Active when `PEST_DETECTION_ENABLED=true` is also set. |
| `PEST_DETECTION_CLOUD_ENABLED` | `false` | No | Cloud adapter (Kindwise) on/off. Requires `PEST_DETECTION_CLOUD_API_KEY`. |
| `PEST_DETECTION_CLOUD_API_KEY` | — | No | API key for Kindwise (cloud detection). Without a key the cloud adapter is disabled. |
| `PEST_DETECTION_PRIMARY_ADAPTER` | `local_pest_symptom` | No | Preferred adapter. Possible values: `local_pest_symptom`, `local_pest_detector` (Phase 2), `kindwise`. |
| `PEST_DETECTION_MAX_IMAGE_SIZE_MB` | `8` | No | Maximum image size in megabytes. Larger images are rejected with HTTP 400. |

!!! note "Self-hosted first"
    The local adapter (`local_pest_symptom`) requires no API key and no user consent. Cloud detection is opt-in and requires consent (consent purpose `pest_detection_cloud`).

---

## CV Disease Diagnosis (REQ-038) {#cv-disease-diagnosis-req-038}

These variables configure the optional, self-hosted photo diagnosis for **diseases and nutrient deficiencies** (distinct from [Pest Detection](#pest-detection-req-044) above). The feature is disabled by default; without `CV_DIAGNOSIS_ENABLED=true` the `/status` API endpoint stays at `available: false` and the app keeps working without restriction.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CV_DIAGNOSIS_ENABLED` | `false` | No | Master switch. Set to `true` to enable the feature. |
| `CV_CLASSIFIER_CONFIDENCE_SHOW` | `0.10` | No | Minimum confidence (0–1) for a hit to be shown. Results below this floor are dropped. |
| `CV_CLASSIFIER_CONFIDENCE_HIGHLIGHT` | `0.75` | No | Confidence threshold (0–1) above which a hit is visually highlighted. Never triggers an automatic creation. |
| `CV_PHENOTYPE_ENABLED` | `true` | No | PlantCV phenotype metrics (leaf area, green index, discoloration ratio) in the inference service on/off. |
| `CV_DIAGNOSIS_MAX_IMAGE_SIZE_MB` | `5` | No | Maximum image size in megabytes. Larger images are rejected with HTTP 413. |

The classifier runs in the existing inference service and reuses its already-configured connection (`INFERENCE_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`) — no additional connection variables are needed.

!!! note "Self-hosted, no cloud adapter"
    Unlike pest detection, CV disease diagnosis (as of this version) has **no** cloud adapter — photos never leave the instance. Consent `plant_diagnosis` is still required (Full mode) because a photo is processed (see [Privacy & GDPR](../user-guide/privacy.md#ai-disease-diagnosis-plant_diagnosis)).

!!! info "License notices"
    The model is fine-tuned on the CC-BY-4.0-licensed PlantDoc dataset; the phenotype pipeline uses PlantCV (MPL-2.0). Full attributions: [`NOTICE.md`](https://github.com/nolte/kamerplanter/blob/main/NOTICE.md#cv-disease-diagnosis-req-038).

---

## Browser Push / PWA (VAPID)

These variables enable the browser push notification channel (`channel_key: "pwa"`). When all three variables are empty, the channel is disabled — the application remains fully functional and users see "Not configured" in their notification settings.

!!! tip "Step-by-step guide"
    The [Set Up Browser Push](../guides/browser-push-setup.md) guide walks through generating the key pair, storing it in Docker Compose or Kubernetes, and verifying the setup.

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `VAPID_PUBLIC_KEY` | — | No* | VAPID public key (Base64url, 87 characters). Sent to the browser and used in the PWA subscription. |
| `VAPID_PRIVATE_KEY` | — | No* | VAPID private key (Base64url or PEM). **Server-side only** — never expose in the frontend or logs. |
| `VAPID_CONTACT_EMAIL` | — | No* | Contact email for the push service (format: `mailto:admin@example.com`). Used by push services (FCM, APNS, Mozilla) to report issues. |
| `PWA_PUSH_ENDPOINT_ALLOWED_HOSTS` | — (empty) | No | SSRF hardening (SEC-001): comma-separated list of allowed host suffixes for web push endpoints, e.g. `fcm.googleapis.com,updates.push.services.mozilla.com`. Empty (default) falls back to an HTTPS requirement plus rejection of private IP addresses, so self-hosted push servers keep working. |

*All three `VAPID_*` variables must be set for the browser push channel to become active. If any variable is missing, the channel remains disabled. `PWA_PUSH_ENDPOINT_ALLOWED_HOSTS` is independently optional.

### Generating a Key Pair

```bash
npx web-push generate-vapid-keys
```

Output:
```
Public Key:
BNm...

Private Key:
8Kv...
```

Alternatively with `pywebpush` (Python) — the `b64urlencode` step is required because `v.public_key`/`v.private_key` are key objects and only serialization yields the Base64url strings:
```bash
pip install pywebpush
python3 - <<'PY'
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from cryptography.hazmat.primitives import serialization

v = Vapid()
v.generate_keys()
pub_raw = v.public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
)
priv_raw = v.private_key.private_numbers().private_value.to_bytes(32, "big")
pub, priv = b64urlencode(pub_raw), b64urlencode(priv_raw)
assert pub_raw[0] == 0x04 and len(pub_raw) == 65 and len(pub) == 87, "invalid public key"
assert len(priv_raw) == 32 and len(priv) == 43, "invalid private key"
print("VAPID_PUBLIC_KEY =", pub)
print("VAPID_PRIVATE_KEY=", priv)
PY
```

!!! danger "Keep the private key server-side"
    The `VAPID_PRIVATE_KEY` must **never** appear in the frontend, in logs, or in public configuration files. Store it as a Kubernetes Secret or Docker Secret — analogous to `JWT_SECRET_KEY`.

!!! tip "Kubernetes Secret for VAPID"
    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: kamerplanter-vapid
    type: Opaque
    stringData:
      VAPID_PUBLIC_KEY: "BNm..."
      VAPID_PRIVATE_KEY: "8Kv..."
      VAPID_CONTACT_EMAIL: "mailto:admin@example.com"
    ```

---

## Season & Overwintering Automation

These variables control the thresholds of the automatic season/overwintering detection (see [Season Automation](../user-guide/season-automation.md)). They only affect the live and climatological tiers of the detection cascade — the calendar fallback is independent of them.

<!-- Source: src/backend/app/config/settings.py (season_pre_winter_temp_c, season_frost_temp_c, season_spring_temp_c, season_signal_threshold_days, season_state_eval_enabled) -->

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `SEASON_PRE_WINTER_TEMP_C` | `5.0` | No | Temperature threshold (°C) for the transition from "Growing" to "Winter approaching". |
| `SEASON_FROST_TEMP_C` | `2.0` | No | Temperature threshold (°C) for the transition into winter dormancy. |
| `SEASON_SPRING_TEMP_C` | `10.0` | No | Temperature threshold (°C) for the transition into spring reactivation. |
| `SEASON_SIGNAL_THRESHOLD_DAYS` | `3` | No | Number of consecutive signal days required before a transition is triggered (oscillation protection). |
| `SEASON_STATE_EVAL_ENABLED` | `true` | No | Switch for the daily evaluation task. Set to `false` to disable season automation entirely. |

---

## Error Tracking (optional)

Reports runtime failures to a Sentry-protocol-compatible tracker (reference: GlitchTip). **With `SENTRY_DSN` empty nothing happens** — the SDK is never initialised and the frontend does not even download its SDK bundle. Full detail: [Error tracking](../deployment/fehler-tracking.md).

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SENTRY_DSN` | — (empty) | No | The tracker's ingest URL, shaped `https://<public-key>@host/<project-id>`. Carries only a public key, not a secret. Empty = off. |
| `SENTRY_ENVIRONMENT` | `development` | No | Stage from the closed vocabulary `development`, `e2e`, `staging`, `production`. Alert rules filter on these exact values; a deviating value still reports but is logged. |
| `SENTRY_RELEASE` | component + version | No | Image tag or commit SHA. Without it, regression detection and "which deploy introduced this" attribution are impossible. |
| `SENTRY_SAMPLE_RATE` | `1.0` | No | Fraction of events reported (0–1). `1.0` is a deliberate decision for this volume, not an untouched default. Unparseable values fall back to `1.0`. |

All four apply to the backend, Celery worker and beat, the inference and knowledge services, and the frontend. In the frontend they are injected at runtime via `runtime-config.js` rather than baked into the build — one image serves every stage.

!!! danger "Self-hosted tracker: do not forget the NetworkPolicy"
    On Kubernetes the backend's egress rule excludes the private address ranges. A tracker in your own cluster or LAN therefore needs an additional egress rule — otherwise events are dropped silently.

## Complete .env Example

```bash
# Database
ARANGO_ROOT_PASSWORD=secure-root-password
ARANGODB_HOST=arangodb
ARANGODB_PORT=8529
ARANGODB_DATABASE=kamerplanter
ARANGODB_USERNAME=root
ARANGODB_PASSWORD=secure-root-password

# Cache / Queue
REDIS_URL=redis://valkey:6379/0

# Security (all three are mandatory secrets, startup gate in production)
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32
FERNET_KEY=generate-with-Fernet.generate_key
ERASURE_TOMBSTONE_SALT=generate-with-openssl-rand-hex-32
REQUIRE_EMAIL_VERIFICATION=false

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Operating mode
KAMERPLANTER_MODE=full
DEBUG=false

# Email (development)
EMAIL_ADAPTER=console

# mDNS Discovery (LAN only, opt-in)
# MDNS_ENABLED=false
# INSTANCE_ID=

# Optional external APIs
PERENUAL_API_KEY=
HA_URL=
HA_ACCESS_TOKEN=

# Knowledge Service — Re-Ranking (empty = disabled)
RERANKER_URL=
RERANKER_INITIAL_K=20
RERANKER_TOP_K=5

# AI Assistant (disabled instance-wide unless explicitly enabled)
AI_FEATURES_ENABLED=false
KNOWLEDGE_SERVICE_ENABLED=false
KNOWLEDGE_SERVICE_URL=http://knowledge-service:8000

# Photo identification (empty = feature disabled)
# PLANTNET_API_KEY=
# IDENTIFICATION_RATE_LIMIT_PER_USER_DAY=50

# Browser Push / PWA (empty = channel disabled)
# VAPID_PUBLIC_KEY=
# VAPID_PRIVATE_KEY=
# VAPID_CONTACT_EMAIL=mailto:admin@example.com
```

---

## Object Storage (NFR-013)

These variables configure the storage adapter for binary data (photos, imports, exports). The active backend is determined by `STORAGE_BACKEND`. By default, `local-fs` is active — no additional configuration required.

For background information, see [Configure Storage (Object Storage)](../user-guide/object-storage.md) and [Helm Charts — Storage Configuration](../deployment/helm.md#storage-configuration-nfr-013).

### General Storage Settings

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `STORAGE_BACKEND` | `local-fs` | No | Active backend: `local-fs` or `s3` |
| `STORAGE_MAX_FILE_SIZE_MB` | `25` | No | Maximum upload size in megabytes (applies to all categories, overridable per category) |
| `STORAGE_PRESIGN_TTL_SECONDS` | `900` | No | Validity period of pre-signed URLs in seconds (max. 3600) |
| `STORAGE_ALLOWED_MIME_TYPES` | *(list)* | No | Comma-separated global whitelist of allowed MIME types |
| `STORAGE_ALLOWED_MIME_TYPES_<CATEGORY>` | *(per category)* | No | Category-specific whitelist, e.g. `STORAGE_ALLOWED_MIME_TYPES_IMPORT=text/csv` |
| `STORAGE_VIRUS_SCAN_ENABLED` | `false` | No | Enable virus scanning via ClamAV REST wrapper |
| `STORAGE_VIRUS_SCAN_ENDPOINT` | *(empty)* | No | URL of the ClamAV REST wrapper |
| `STORAGE_STRIP_EXIF` | `true` | No | Strips EXIF/GPS metadata from image uploads globally at save time (NFR-013 §5.1). There is **no** per-category override variable — unlike the MIME whitelists, this is a single global switch. |
| `STORAGE_TENANT_QUOTA_MB` | `2048` | No | Storage quota per tenant, in megabytes. `0` disables the quota (unlimited). |
| `STORAGE_MAX_PHOTOS_PER_INSTANCE` | `50` | No | Maximum number of gallery photos per plant instance (REQ-034). `0` disables the limit. |

**Default MIME whitelist per category:**

| Category | Allowed MIME types | Max size |
|---------|--------------------|---------|
| `diary`, `ipm`, `harvest`, `post_harvest`, `task`, `id_recognition`, `plant` | `image/jpeg`, `image/png`, `image/webp`, `image/heic` | 25 MB |
| `import` | `text/csv`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 50 MB |
| `export` | `application/pdf`, `text/csv`, `application/zip` | 200 MB |
| `tenant_export` | `application/zip` | 5 GB |

### Backend: Local Filesystem (`local-fs`)

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `STORAGE_LOCAL_FS_ROOT` | `/data/attachments` | No | Mount path inside the container |
| `STORAGE_LOCAL_FS_PUBLIC_BASE_URL` | *(empty)* | Yes* | Full URL of the token download endpoint, e.g. `https://api.kamerplanter.example.com/api/v1/attachments/token`. Must point to `https://<host>/api/v1/attachments/token`. |
| `STORAGE_LOCALFS_SIGNING_SECRET` | *(ephemeral)* | Yes** | Secret key for token signatures. **Required when running more than one replica**, otherwise tokens cannot be validated by other pods. |

*Required for local-fs token downloads to work.
**Required in multi-replica operation.

!!! warning "Store signing secret as a Kubernetes Secret"
    `STORAGE_LOCALFS_SIGNING_SECRET` is a cryptographic secret and must not be committed to `values.yaml` or Git in plain text. Create it as a Kubernetes Secret:
    ```bash
    kubectl create secret generic kamerplanter-storage-signing \
      --from-literal=STORAGE_LOCALFS_SIGNING_SECRET="$(openssl rand -hex 32)" \
      --namespace kamerplanter
    ```

### Backend: S3-compatible (`s3`)

| Variable | Default | Required | Description |
|----------|---------|---------|-------------|
| `STORAGE_S3_ENDPOINT_URL` | *(empty)* | Yes | Full endpoint URL, e.g. `https://s3.eu-central-1.amazonaws.com` |
| `STORAGE_S3_REGION` | *(empty)* | Yes | Region, e.g. `eu-central-1` (also required for MinIO) |
| `STORAGE_S3_BUCKET` | *(empty)* | Yes | Bucket name (must be created beforehand) |
| `STORAGE_S3_ACCESS_KEY_ID` | *(empty)* | Yes | Access key (from External Secrets Operator — never in plain text in Git) |
| `STORAGE_S3_SECRET_ACCESS_KEY` | *(empty)* | Yes | Secret access key (from External Secrets Operator — never in plain text in Git) |
| `STORAGE_S3_USE_PATH_STYLE` | `false` | No | `true` for MinIO and most non-AWS providers |
| `STORAGE_S3_FORCE_TLS` | `true` | No | Block plain HTTP; set to `false` in dev environments |
| `STORAGE_S3_KMS_KEY_ID` | *(empty)* | No | Optional customer-managed key for server-side encryption (SSE-KMS) |
| `STORAGE_S3_ALLOW_PRIVATE_ENDPOINT` | `false` | No | `true` for in-cluster MinIO that is not publicly reachable |

!!! danger "Never put S3 credentials in Git or values.yaml"
    `STORAGE_S3_ACCESS_KEY_ID` and `STORAGE_S3_SECRET_ACCESS_KEY` are secrets and must be provided exclusively through the External Secrets Operator (ESO) or Kubernetes Secrets. For details, see [Helm Charts — Storage Configuration](../deployment/helm.md#storage-configuration-nfr-013).

#### Example Configurations

=== "AWS S3 (eu-central-1)"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=https://s3.eu-central-1.amazonaws.com
    STORAGE_S3_REGION=eu-central-1
    STORAGE_S3_BUCKET=my-kamerplanter-bucket
    STORAGE_S3_ACCESS_KEY_ID=<from secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<from secret>
    STORAGE_S3_USE_PATH_STYLE=false
    STORAGE_S3_FORCE_TLS=true
    ```

=== "MinIO in-cluster"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=http://minio.kamerplanter.svc:9000
    STORAGE_S3_REGION=us-east-1
    STORAGE_S3_BUCKET=kamerplanter
    STORAGE_S3_ACCESS_KEY_ID=<from secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<from secret>
    STORAGE_S3_USE_PATH_STYLE=true
    STORAGE_S3_FORCE_TLS=false
    STORAGE_S3_ALLOW_PRIVATE_ENDPOINT=true
    ```

=== "Hetzner Object Storage"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=https://fsn1.your-objectstorage.com
    STORAGE_S3_REGION=eu-central
    STORAGE_S3_BUCKET=my-kamerplanter-bucket
    STORAGE_S3_ACCESS_KEY_ID=<from secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<from secret>
    STORAGE_S3_USE_PATH_STYLE=false
    STORAGE_S3_FORCE_TLS=true
    ```

---

## Frequently Asked Questions

??? question "Can I store environment variables as Kubernetes Secrets?"
    Yes. Use Kubernetes Secrets for sensitive values (`ARANGODB_PASSWORD`, `JWT_SECRET_KEY`) and reference them in the Deployment manifest via `valueFrom.secretKeyRef`.

??? question "How can I verify which values the backend is actually using?"
    With `DEBUG=true`, the backend logs all loaded settings at startup. Alternatively, inside the container:
    ```bash
    docker compose exec backend python -c "from app.config.settings import settings; print(settings.model_dump())"
    ```
    Passwords and secrets are not shown in plain text.

---

## See Also

- [Configuration Matrix](../deployment/konfigurationsmatrix.md) — Feature → services → switches → mandatory secrets → resources in a single table
- [Deployment Profiles](../deployment/betriebsprofile.md) — Recommended component bundles for typical use cases
- [Local Setup](../development/local-setup.md)
- [Operations Troubleshooting](../development/troubleshooting.md)
- [Kubernetes Deployment](../deployment/kubernetes.md)
- [Weather Sources per Location — User Guide](../user-guide/weather-sources.md)
- [Notifications: Frost Early-Warning — User Guide](../user-guide/notifications.md#frost-early-warning)
- [API Reference: CV Disease Diagnosis](api-reference.md#cv-disease-diagnosis)
- [MCP Server](../api/mcp-server.md)
- [Privacy & GDPR — AI Disease Diagnosis](../user-guide/privacy.md#ai-disease-diagnosis-plant_diagnosis)
- [Watering Log: Suggested Watering Volume — User Guide](../user-guide/watering-log.md#suggested-watering-volume)
- [Equipment & Inventory (InvenTree) — User Guide](../user-guide/inventree.md)
- [Environment Control & Actuators — User Guide](../user-guide/actuator-control.md)
- [API Reference: Environment Control & Actuators](api-reference.md#environment-control-actuators)

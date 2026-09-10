# Kamerplanter Backend

Python/FastAPI REST API for plant lifecycle management with polyglot persistence.

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.14+ | Runtime |
| FastAPI | >= 0.115 | Web framework |
| Pydantic | >= 2.10 | Data validation & models |
| python-arango | >= 8.1 | ArangoDB driver |
| Redis | >= 5.2 | Cache & Celery broker |
| Celery | >= 5.4 | Async task queue |
| authlib | >= 1.3 | JWT, OAuth2, OIDC |
| bcrypt | >= 4.0 | Password hashing |
| structlog | - | Structured logging |
| Uvicorn | - | ASGI server |

## Getting Started

```bash
# Install the locked dependency set plus the dev extra (needs uv)
uv sync --locked --extra dev
source .venv/bin/activate

# Run API server
uvicorn app.main:app --reload --port 8000

# Run Celery worker
celery -A app.tasks worker --loglevel=info

# Run Celery beat scheduler
celery -A app.tasks beat --loglevel=info
```

### Required Services

- **ArangoDB** (3.11+) on `localhost:8529`
- **Redis** (7.2+) on `localhost:6379`
- **TimescaleDB** (2.13+) for sensor time-series (future)

## Scripts

| Command | Description |
|---|---|
| `pytest tests/unit/ -v` | Run unit tests |
| `pytest tests/unit/ --cov` | Tests with coverage |
| `ruff check .` | Lint check |
| `ruff format --check .` | Format check |

## Project Structure

```
app/
  api/v1/                   # 43 REST API routers
    activities/             # REQ-006 Activity CRUD
    admin/                  # Admin settings, OIDC provider management
    auth/                   # REQ-023 Login, register, token refresh, OAuth
    botanical_families/     # REQ-001 Botanical family CRUD
    calendar/               # REQ-015 Calendar aggregation, iCal feeds
    care_reminders/         # REQ-022 Care reminder generation & confirmation
    companion_planting/     # REQ-001 Graph-based plant compatibility
    crop_rotation/          # REQ-001 4-year rotation planning
    cultivars/              # REQ-001 Cultivar CRUD
    enrichment/             # REQ-011 External data enrichment (GBIF, Perenual)
    feeding_events/         # REQ-004 Feeding event logging
    fertilizers/            # REQ-004 Fertilizer CRUD & stock management
    growth_phases/          # REQ-003 Growth phase definitions
    harvest/                # REQ-007 Harvest batches, quality assessment
    health/                 # Liveness & readiness probes
    imports/                # REQ-012 CSV import with validation
    ipm/                    # REQ-010 Pest, disease, treatment management
    location_types/         # REQ-002 Location type system (10 seeds)
    locations/              # REQ-002 Recursive location hierarchy
    nutrient_calculations/  # REQ-004 Nutrient solution calculator
    nutrient_plans/         # REQ-004 Nutrient plan CRUD
    onboarding/             # REQ-020 Onboarding wizard & starter kits
    phases/                 # REQ-003 Phase transition state machine
    plant_instances/        # REQ-013 Plant instance lifecycle
    planting_runs/          # REQ-013 Batch planting runs
    profiles/               # REQ-001 Species profile management
    sites/                  # REQ-002 Site CRUD with water source config
    slots/                  # REQ-002 Slot capacity management
    species/                # REQ-001 Species CRUD
    substrates/             # REQ-019 Substrate lifecycle management
    tanks/                  # REQ-014 Tank & tank state management
    tasks/                  # REQ-006 Task execution & workflows
    tenants/                # REQ-024 Multi-tenancy & invitations
    users/                  # REQ-023 User profile management
    user_preferences/       # REQ-021 Experience level preferences
    watering_events/        # REQ-014 Watering event logging
    watering_logs/          # Watering log CRUD
    router.py               # Main router (aggregates all sub-routers)

  common/                   # Shared types & utilities
  config/
    settings.py             # Pydantic settings (env-based configuration)
    constants.py            # Application constants

  data_access/
    arango/                 # ArangoDB repository implementations
    external/               # External API adapters (GBIF, Perenual, HA)

  domain/
    engines/                # Pure business logic (no I/O)
      care_reminder_engine  # 9 presets, adaptive learning, seasonal multipliers
      csv_parser            # Encoding/delimiter auto-detection
      dependency_resolver   # Task dependency DAG resolution
      ec_budget_engine      # EC budget calculation
      hst_validator         # Phase-based training restrictions
      nutrient_engine       # Nutrient solution calculation, mixing safety
      nutrient_plan_engine  # Nutrient plan validation
      onboarding_engine     # Starter kit application
      row_validator         # Import row validation
      sowing_calendar_engine # Sowing date calculation
      season_overview_engine # 12-month season overview
      substrate_mix_engine  # Substrate composition
      tank_engine           # Tank state management
      water_mix_engine      # RO/tap water mixing, CalMag correction
      watering_engine       # Watering schedule, dosage resolution
      watering_forecast_engine # Watering forecast
      watering_volume_engine # Volume suggestion
    interfaces/             # Repository ABCs (port definitions)
    models/                 # Pydantic domain models
    services/               # Orchestration layer (calls engines + repositories)

  migrations/
    seed_data/              # YAML seed files
    seed_*.py               # Database seeding scripts

  tasks/                    # Celery task definitions
    care_tasks.py           # Daily care reminder generation
    __init__.py             # Celery app & beat schedule
```

## Architecture

### 5-Layer Architecture (NFR-001)

```
Presentation (React) -> API (FastAPI routers) -> Services -> Engines -> Repositories -> ArangoDB
```

- **API layer**: FastAPI routers with Pydantic request/response schemas. Input validation at this layer.
- **Service layer**: Orchestrates engines and repositories. Transaction boundaries.
- **Engine layer**: Pure business logic, no I/O. Stateless, testable in isolation.
- **Repository layer**: ABC interfaces in `domain/interfaces/`, implementations in `data_access/arango/`.
- **Persistence**: ArangoDB named graph `kamerplanter_graph` with 54+ document and 75+ edge collections.

### Key Patterns

- **Polyglot persistence**: ArangoDB (documents + graph), Redis (cache + Celery broker), TimescaleDB (sensor time-series, future).
- **Adapter pattern**: External integrations (GBIF, Perenual, Home Assistant) behind ABC interfaces.
- **REQ-027 Light-Modus**: `kamerplanter_mode=light` disables auth, multi-tenancy, and privacy features for simple local deployments.
- **REQ-023 Dual auth**: Local (email + bcrypt) and federated (OAuth2/OIDC via authlib). JWT access tokens (15min) + refresh tokens (30 days, HttpOnly cookie rotation).
- **REQ-024 Multi-tenancy**: Tenant-scoped resources via URL routing `/api/v1/t/{tenant_slug}/...`. Global resources (species, cultivars) at `/api/v1/...`.

### Celery Tasks

- `generate_due_care_reminders` (daily) - REQ-022
- `watering-generate-tasks-daily` - Watering schedule task generation
- Enrichment tasks - REQ-011 background data enrichment

## Configuration

Environment-based via Pydantic `Settings`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `ARANGO_HOST` | `localhost` | ArangoDB host |
| `ARANGO_PORT` | `8529` | ArangoDB port |
| `ARANGO_DB` | `kamerplanter` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `KAMERPLANTER_MODE` | `full` | `full` or `light` (REQ-027) |
| `JWT_SECRET_KEY` | - | JWT signing secret |
| `CORS_ORIGINS` | `localhost:3000,5173` | Allowed CORS origins |

## Demo

Seed user: `demo@kamerplanter.local` / `demo-passwort-2024`

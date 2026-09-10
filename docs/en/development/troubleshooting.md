# Operations Troubleshooting

Solutions to common technical problems when installing, operating, and using Kamerplanter — for developers and self-hosters. The steps below apply to both the Docker Compose and Kubernetes environments.

!!! info "Looking for help with an unwell plant?"
    This page covers **technical problems** with the Kamerplanter application itself (installation, login, error messages). If you're instead dealing with symptoms on one of your plants (yellow leaves, pests, growth issues), see [My Plant Doesn't Look Well](../user-guide/plant-health-troubleshooting.md) instead.

---

## Backend and Services Won't Start

??? question "The backend won't start — how do I diagnose the problem?"
    **Step 1 — Check the logs:**

    === "Docker Compose"
        ```bash
        docker compose logs backend --tail=50
        ```

    === "Kubernetes"
        ```bash
        kubectl logs deployment/kamerplanter-backend --tail=50
        ```

    **Common error messages and solutions:**

    | Error message | Cause | Solution |
    |---------------|-------|---------|
    | `Connection refused: arangodb:8529` | ArangoDB not reachable | Check ArangoDB container (`docker compose ps`) |
    | `AUTH_EXCEPTION` | Wrong ArangoDB password | Verify `ARANGODB_PASSWORD` in `.env` |
    | `redis.exceptions.ConnectionError` | Redis/Valkey not reachable | Restart Redis container |
    | `pydantic_settings.SettingsError` | Missing required environment variable | Set all required variables in `.env` |
    | `Cannot import name 'X'` | Missing Python dependency | `uv sync --locked` inside container |

??? question "ArangoDB container won't start"
    The most common cause is a data volume from an older ArangoDB version. Check:

    ```bash
    docker compose logs arangodb --tail=30
    ```

    If "Invalid version" or "upgrade required" appears:

    ```bash
    docker compose down
    docker volume rm kamerplanter_arangodb_data
    docker compose up -d
    ```

    !!! danger "Data loss warning"
        Removing the volume deletes all database data. Only do this in development environments without important data.

??? question "Celery worker is not running — tasks are not being generated"
    Check worker status:

    === "Docker Compose"
        ```bash
        docker compose logs celery-worker --tail=30
        docker compose logs celery-beat --tail=30
        ```

    === "Kubernetes"
        ```bash
        kubectl logs deployment/kamerplanter-celery-worker --tail=30
        ```

    Common cause: `REDIS_URL` not set or Redis not reachable. Test the Redis connection:

    ```bash
    docker compose exec valkey valkey-cli ping
    # Expected response: PONG
    ```

---

## Database Problems

??? question "Database collections missing or 'collection not found' errors"
    Kamerplanter automatically creates all collections on startup. If collections are missing, the startup hook was not executed. Restart the backend:

    === "Docker Compose"
        ```bash
        docker compose restart backend
        ```

    === "Kubernetes"
        ```bash
        kubectl rollout restart deployment/kamerplanter-backend
        ```

    Alternatively, check the ArangoDB web UI (default: `http://localhost:8529`) to verify that the `kamerplanter` database and `kamerplanter_graph` exist.

??? question "Migration fails — seed data is not loaded"
    Kamerplanter runs seed migrations at startup (`seed_data`, `seed_starter_kits`, `seed_location_types`). On failure, check the backend logs for the full stack trace.

    Common cause: ArangoDB starts slower than the backend. Increase the healthcheck interval or use `depends_on` with `condition: service_healthy`. Restart the backend after ArangoDB is fully started.

??? question "'graph not found' error in AQL queries"
    The named graph `kamerplanter_graph` is created on first startup. If it is missing, `ensure_collections()` initialization was skipped. Restart the backend or create the graph manually in the ArangoDB web UI under "Graphs".

---

## Authentication and Users

??? question "Login fails — 401 Unauthorized"
    Check:

    1. **Correct email and password?** Demo account: `demo@kamerplanter.local` / `demo-passwort-2024`
    2. **Email verification required?** If `REQUIRE_EMAIL_VERIFICATION=true` is set, the email must be confirmed. Set to `false` for development.
    3. **JWT secret key changed?** All active tokens become invalid. Users must log in again.

??? question "Registration fails — 'Email already registered'"
    The email address already exists in the system. Use the password reset flow, or check the email in the ArangoDB web UI under the `users` collection.

??? question "Token expires — constant logouts"
    JWT access tokens expire after 15 minutes (default). The frontend client automatically renews the token using the refresh token (valid 30 days). If refresh token renewal fails:

    - Check `JWT_SECRET_KEY` in the environment — if this value was changed, all refresh tokens become invalid.
    - Check browser cookies — the HttpOnly cookie `refresh_token` must be set.

---

## CORS Errors in the Browser

??? question "CORS errors when making API calls from the browser"
    CORS errors appear in the browser console as:
    ```
    Access to XMLHttpRequest at 'http://localhost:8000/api/...' has been blocked by CORS policy
    ```

    **Solution:** Add the frontend origin to `CORS_ORIGINS`:

    ```bash
    # .env
    CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
    ```

    Format: JSON array as a string. Separate multiple entries with commas.

    !!! warning "No wildcards in production"
        `CORS_ORIGINS=["*"]` allows all origins — only suitable for local development. Always specify concrete URLs in production environments.

??? question "CORS error despite correct CORS_ORIGINS configuration"
    Check the `Origin` header actually being sent:

    1. Browser DevTools → Network → Request Headers → `Origin`
    2. Add this exact value (including `http://` vs. `https://` and port) to `CORS_ORIGINS`.
    3. Restart the backend after the configuration change.

---

## Harvest and IPM

??? question "Harvest is blocked (422 pre-harvest interval violation)"
    An active IPM treatment has an open pre-harvest interval (PHI). The harvest is blocked until the PHI has passed.

    **Steps:**

    1. Navigate to **Pest Management > Treatment Applications**.
    2. Check active treatments with status "active" or "pre-harvest interval".
    3. The system shows the earliest possible harvest date.

    !!! danger "Do not bypass the pre-harvest interval"
        The PHI is a legal requirement (CanG — the German Cannabis Act; PflSchG — the German Plant Protection Act). The system intentionally prevents the harvest — manual bypass is not provided.

??? question "Observation cannot be marked as harvest-ready"
    Check whether harvest indicators are configured for the plant species. Navigate to **Master Data > [Species] > Harvest Indicators** and add at least one indicator.

---

## Calendar and iCal

??? question "iCal feed shows no events"
    Check:

    1. **Feed token valid?** Under **Calendar > iCal Feeds**, verify the feed is active.
    2. **Calendar app:** URL must follow the format `https://[host]/api/v1/calendar/ical/[token]`.
    3. **Time zone:** iCal feeds use UTC. Check whether your calendar application interprets time zones correctly.

??? question "Calendar view does not load or shows no data"
    Navigate to **Calendar** and check:

    - Are there planting runs or tasks in the selected period?
    - Are the filters (phase, category) set too narrowly?
    - Any backend API errors in browser DevTools (F12 → Network → `/api/v1/...`)?

---

## Onboarding Wizard

??? question "Onboarding wizard fails at step 3 (Starter Kit)"
    Check whether starter kit seed data was loaded:

    ```bash
    docker compose logs backend | grep -i "seed_starter_kits"
    ```

    If "0 starter kits loaded" appears, trigger the seed migration manually:

    ```bash
    docker compose exec backend python -c "from app.migrations.seed_starter_kits import run_seed_starter_kits; run_seed_starter_kits()"
    ```

??? question "After onboarding, no tenant appears in the selection"
    The personal tenant is automatically created at registration. If it is missing:

    1. `GET /api/v1/t/` — check whether the tenant endpoint returns data.
    2. If empty: run through the onboarding again or create a tenant manually under **Settings > Tenants**.

---

## Performance and Connection Issues

??? question "API requests are slow (> 2 seconds)"
    Common causes:

    | Cause | Check | Solution |
    |-------|-------|---------|
    | Missing ArangoDB index | ArangoDB web UI → Collection → Indexes | Re-run `ensure_collections()` |
    | Too many graph traversal steps | AQL EXPLAIN in web UI | Reduce traversal depth |
    | Redis cache cold | First request after restart | Normal — cache warms up |

??? question "503 Service Unavailable when accessing the API"
    The backend container is not running or is failing its health check:

    ```bash
    docker compose ps
    # Status "unhealthy" or "Exit X" → restart container

    docker compose up -d backend
    ```

    Test the health check endpoint directly:

    ```bash
    curl http://localhost:8000/api/v1/health/live
    # Expected response: {"status": "ok"}
    ```

---

## Kubernetes: Pod Won't Start

??? question "Pod is in 'CrashLoopBackOff' status"
    `CrashLoopBackOff` (a Kubernetes error meaning the container repeatedly starts and fails) indicates the container crashes shortly after starting. Retrieve the logs from the last crash:

    ```bash
    kubectl logs deployment/kamerplanter-backend --previous
    ```

    Common causes: missing environment variables, an unreachable database connection, or an invalid configuration file. The error message in the log usually indicates the exact cause.

---

## Light Mode vs. Full Mode

??? question "Authentication is required even though Light Mode is configured"
    In Light Mode (`KAMERPLANTER_MODE=light`), token authentication is disabled for most endpoints. Check:

    1. Is `KAMERPLANTER_MODE=light` set in the backend environment?
    2. Was the backend restarted after the change?
    3. Is the request actually reaching the backend port (8000) and not a proxy?

    ```bash
    docker compose exec backend env | grep KAMERPLANTER_MODE
    # Expected output: KAMERPLANTER_MODE=light
    ```

---

## Common Issues After an Update

??? question "Database queries fail after a version update"
    New collections or edge definitions are handled by `ensure_collections()` on startup. If collections are missing or newly added:

    1. Check backend logs for startup errors.
    2. Make sure the backend container was fully restarted during the update.
    3. Verify ArangoDB collections manually via the web UI.

??? question "Frontend shows '404 Not Found' after deployment"
    In Kubernetes deployments, the frontend build is served as static files by the backend. Check:

    ```bash
    kubectl describe pod kamerplanter-backend-[hash]
    # Check volume mounts for /app/static
    ```

    Alternatively: deploy the frontend as a separate Nginx container.

---

## Diagnostic Tools

### Check API health

```bash
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
```

### Query ArangoDB directly

Open `http://localhost:8529` in your browser (default credentials: `root` / value from `ARANGO_ROOT_PASSWORD`).

### Backend logs with timestamp

```bash
docker compose logs backend --timestamps --tail=100
```

### Show all service statuses

```bash
docker compose ps
```

---

## See Also

- [Environment Variables](../reference/environment-variables.md)
- [Local Setup](local-setup.md)
- [Deployment](../deployment/index.md)
- [My Plant Doesn't Look Well](../user-guide/plant-health-troubleshooting.md) — symptom diagnosis for plant problems rather than technical errors

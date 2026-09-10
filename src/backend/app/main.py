import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.auth.router import limiter
from app.api.v1.openapi_tags import OPENAPI_TAGS
from app.api.v1.router import api_router
from app.common.dependencies import close_connection, get_connection, get_ha_client
from app.common.error_handlers import (
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from app.common.exceptions import KamerplanterError
from app.common.middleware import request_id_middleware
from app.config.logging import setup_logging
from app.config.settings import settings
from app.data_access.arango.collections import ensure_collections
from app.data_access.external.registration import register_external_adapters
from app.observability.error_tracking import init_error_tracking, resolve_release

logger = structlog.get_logger()

# Optional error tracking (#777). Called at process entry, before the app object
# exists and long before the first request, so a failure raised during startup is
# already captured. Without SENTRY_DSN this is a no-op and nothing about the
# process changes — which is why it is unconditional here rather than hidden
# behind a settings flag.
init_error_tracking(
    component="backend",
    release=resolve_release("kamerplanter-backend", settings.app_version),
)

# Register every self-registering adapter (weather, pest, identification, storage
# factories) so they are available to the FastAPI process. The Celery worker does
# the same in :mod:`app.tasks`; both share one central list.
register_external_adapters()

# NFR-011 §4: the erasure tombstone salt must be a high-entropy secret; a value
# shorter than this is treated as unset/insecure.
_MIN_TOMBSTONE_SALT_LENGTH = 32


def insecure_default_secrets() -> list[str]:
    """Return the names of default/missing secrets that block a secure startup.

    Empty list => safe to start. Extracted from the lifespan so it can be
    unit-tested directly (AP-4, INF-S5). Evaluated against the module-level
    ``settings`` singleton.
    """
    insecure: list[str] = []
    if settings.jwt_secret_key == "change-me-in-production-use-openssl-rand-hex-32":
        insecure.append("jwt_secret_key")
    if settings.arangodb_password == "rootpassword":
        insecure.append("arangodb_password")
    if settings.timescaledb_enabled and settings.timescaledb_password == "changeme":
        insecure.append("timescaledb_password")
    # INF-S5: OIDC provider-secret encryption key (Fernet). Must be provisioned.
    if not settings.fernet_key:
        insecure.append("fernet_key")
    # NFR-011 §4: GDPR erasure tombstone salt (>= 32 chars).
    if len(settings.erasure_tombstone_salt) < _MIN_TOMBSTONE_SALT_LENGTH:
        insecure.append("erasure_tombstone_salt")
    # AP-4: shared secret for the internal M2M services — required only when the
    # backend actually calls them.
    if (
        settings.knowledge_service_enabled or settings.inference_service_enabled
    ) and not settings.internal_service_token:
        insecure.append("internal_service_token")
    return insecure


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.debug)
    logger.info("startup", app=settings.app_name, version=settings.app_version)

    # Check for default secrets in production
    if not settings.debug:
        _insecure = insecure_default_secrets()
        if _insecure:
            msg = (
                "FATAL: Default secrets detected for: "
                f"{', '.join(_insecure)}. "
                "Set proper values via environment variables "
                "before running in production."
            )
            logger.critical("insecure_defaults", fields=_insecure)
            raise SystemExit(msg)

    conn = get_connection()
    db = conn.connect()
    ensure_collections(db)
    logger.info("database_ready")

    # NFR-016 / ADR-005: versioned, tracked, lock-guarded migrations run FIRST
    # (fatal on failure — a stale-enum volume must be repaired before any seed
    # reads it, e.g. the retired `harvest` phase from #306). Then the seed
    # registry runs with per-seed error isolation (a bad reference-data seed no
    # longer wedges the whole startup).
    from app.migrations.framework.runner import run_pending_migrations
    from app.migrations.seeds.registry import run_seeds

    run_pending_migrations(db)
    run_seeds(db)

    if settings.kamerplanter_mode == "light":
        logger.info("light_mode_active")

    # Register notification channels
    from app.domain.engines.notification_channel_registry import NotificationChannelRegistry

    # Home Assistant is optional — a missing, unreachable or unresolvable HA_URL
    # must never break startup (graceful degradation, REQ-018). Any failure here
    # just skips the HA notification channel.
    try:
        ha_client = get_ha_client()
        if ha_client is not None:
            from app.data_access.external.ha_notification_channel import HomeAssistantNotificationChannel

            NotificationChannelRegistry.register(HomeAssistantNotificationChannel(ha_client))
            logger.info("notification_channel_registered", channel="home_assistant")
    except Exception:
        logger.warning("notification_channel_registration_failed", channel="home_assistant", exc_info=True)

    from app.data_access.external.apprise_notification_channel import AppriseNotificationChannel

    NotificationChannelRegistry.register(AppriseNotificationChannel())
    logger.info("notification_channel_registered", channel="apprise")

    # Email channel (unconditional, best-effort — must not break startup)
    try:
        from app.common.dependencies import get_email_service
        from app.data_access.external.email_notification_channel import EmailNotificationChannel

        NotificationChannelRegistry.register(EmailNotificationChannel(get_email_service()))
        logger.info("notification_channel_registered", channel="email")
    except Exception:
        logger.warning("notification_channel_registration_failed", channel="email", exc_info=True)

    # Web Push (PWA / browser) channel — only if VAPID keys are configured
    if settings.vapid_public_key and settings.vapid_private_key:
        from app.data_access.external.pwa_notification_channel import PwaNotificationChannel

        NotificationChannelRegistry.register(
            PwaNotificationChannel(settings.vapid_private_key, settings.vapid_contact_email)
        )
        logger.info("notification_channel_registered", channel="pwa")

    # mDNS / Zeroconf Discovery (optional)
    mdns_announcer = None
    if settings.mdns_enabled:
        from app.common.mdns import MdnsAnnouncer, create_service_info, generate_instance_id

        instance_id = settings.instance_id or generate_instance_id()
        info = create_service_info(
            port=8000,
            version=settings.app_version,
            mode=settings.kamerplanter_mode,
            instance_id=instance_id,
        )
        mdns_announcer = MdnsAnnouncer(info)
        mdns_announcer.start()

    # TimescaleDB init (optional)
    if settings.timescaledb_enabled:
        from app.common.dependencies import get_timescale_connection
        from app.data_access.timescale.schema import ensure_timescale_schema

        ts_conn = get_timescale_connection()
        if ts_conn:
            ts_conn.connect()
            ensure_timescale_schema(ts_conn.pool)
            logger.info("timescaledb_ready")
        else:
            logger.warning("timescaledb_enabled_but_connection_failed")

    yield

    if mdns_announcer:
        mdns_announcer.stop()
    close_connection()
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API of Kamerplanter, an agricultural technology system for plant "
        "lifecycle management (houseplants, vegetables, herbs, cannabis): master "
        "data, sites and locations, phase-driven growing logic, fertilization and "
        "watering, hybrid sensing, tasks, harvest and post-harvest, IPM, "
        "multi-tenancy and GDPR self-service. Authentication uses Bearer tokens "
        "(JWT access tokens or `kp_`-prefixed service-account API keys); "
        "operations marked with an empty security list are deliberately public."
    ),
    contact={"name": "Kamerplanter", "url": "https://github.com/nolte/kamerplanter"},
    license_info={"name": "MIT", "identifier": "MIT"},
    servers=[
        {"url": "/", "description": "Current deployment (same origin)"},
        {"url": "http://localhost:8000", "description": "Local development backend"},
    ],
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# OpenAPI post-processing (documentation only, spec/project/api-documentation/):
#  1. FastAPI only emits a `security` requirement on operations whose dependency
#     tree contains a security scheme (HTTPBearer in app.common.auth). An
#     operation without any requirement is deliberately public — stamp it with
#     an explicit `security: []` so document consumers can tell "public by
#     design" from "forgotten security".
#  2. A router mounted under a parameterised prefix (e.g. /t/{tenant_slug})
#     whose operations never consume that path parameter still matches it at
#     runtime, but FastAPI omits it from the generated parameter list — declare
#     it so the document satisfies the OpenAPI path-params contract.
_fastapi_openapi = app.openapi
_PATH_PARAM_RE = re.compile(r"\{([^}]+)\}")


def _openapi_postprocessed() -> dict:
    """Fill in path parameters FastAPI cannot see, and nothing else.

    Deliberately absent: response schemas for the ~31 operations that return
    without one. Those are streaming, file, redirect and SSE responses plus
    dynamic passthrough dicts — a response schema would be a lie about what the
    endpoint sends, so they are documented gaps with a reason rather than
    missing work (#850, from the 2026-07-24 API documentation audit). An audit
    that re-reports them should be pointed at this note instead of at the
    operations.
    """
    schema = _fastapi_openapi()
    http_methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    for path, path_item in schema.get("paths", {}).items():
        template_params = _PATH_PARAM_RE.findall(path)
        for method, operation in path_item.items():
            if method not in http_methods:
                continue
            if "security" not in operation:
                operation["security"] = []
            declared = {p["name"] for p in operation.get("parameters", []) if p.get("in") == "path"}
            for name in template_params:
                if name not in declared:
                    operation.setdefault("parameters", []).append(
                        {
                            "name": name,
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "title": name.replace("_", " ").title()},
                            "description": "Path segment matched by the mount prefix.",
                        }
                    )
    return schema


app.openapi = _openapi_postprocessed  # type: ignore[method-assign]

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # API responses are JSON. A `default-src 'none'` CSP is the strictest
    # safe option: nothing should be loaded from a JSON document. The
    # /docs and /redoc endpoints serve HTML+JS via FastAPI's bundled
    # CDN-based Swagger UI; relaxing CSP for them would defeat the
    # purpose, so the deployment is expected to disable those endpoints
    # in production (NFR-014 §3.2 / kamerplanter-debug-endpoints.yaml).
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Request-ID middleware — registered AFTER security_headers so it runs FIRST (LIFO)
@app.middleware("http")
async def _request_id_middleware(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    return await request_id_middleware(request, call_next)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


_API_MAJOR_PATH = re.compile(r"^/api/v(\d+)(?:/|$)")


def supported_api_majors(application: FastAPI) -> list[int]:
    """Return the API major versions this deployment actually serves (#1124).

    **Derived from the mounted routes, never a maintained list.** The Android
    client is a separate release train against a *self-hosted* backend, so the two
    drift in both directions and the client has to negotiate the highest major both
    sides support. Until now it probed ``/api/v{n}/openapi.json`` downward from the
    highest major it knew — a workaround, and one that cannot distinguish "major
    not served" from "server briefly unreachable".

    A hand-maintained constant would answer that question and then go stale the
    first time a major is added or retired — replacing a probe that is at least
    *true* with a declaration that might not be. Reading the router table means the
    answer is wrong only if the routes are.

    Sorted ascending; the client takes the highest it also supports.

    **Deliberately recomputed per request, measured rather than assumed** (#1210,
    SEC-003). The walk covers 793 paths at 0.37 ms per call on the current tree —
    below the noise of the HTTP round trip, and not what made this endpoint an
    amplification point (the synchronous TimescaleDB / knowledge-service probes in
    ``root_health`` are, and the rate limit now bounds those). Caching it would buy
    that 0.37 ms for two real costs: computing it at startup is not even
    observable in this suite, because ``TestClient(app)`` outside a context manager
    never runs the lifespan — a startup-filled cache would answer ``[]`` to every
    api-tier test and to anything else that skips it — and memoising it lazily
    reintroduces exactly the staleness this function exists to eliminate, since the
    answer would then be "the routes as they were at the first request" rather than
    "the routes".
    """
    return sorted({int(m.group(1)) for path in _mounted_paths(application) if (m := _API_MAJOR_PATH.match(path))})


def _mounted_paths(application: Any, _depth: int = 0) -> Iterator[str]:
    """Yield every route path reachable from ``application``, following inclusions.

    ``include_router`` does not flatten child routes onto ``app.routes`` in this
    FastAPI version — it appends an ``_IncludedRouter`` wrapper that keeps the real
    router behind ``original_router``. A first version of this walked ``app.routes``
    only and *appeared* to work: it returned ``[1]`` for the real application, but
    from ``/api/v1/openapi.json`` — a **docs** route — rather than from any API
    route. Right answer, accidental derivation, and it yielded an empty list for a
    freshly mounted v2 in a test, which is how it was caught.

    ``_depth`` bounds the recursion: a router graph is never deep, and a cycle here
    would hang the health endpoint.
    """
    if _depth > 10:
        return
    for route in getattr(application, "routes", []) or []:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            yield path
        nested = getattr(route, "original_router", None)
        if nested is not None:
            yield from _mounted_paths(nested, _depth + 1)


@app.get("/api/health", tags=["health"])
@limiter.limit(settings.rate_limit_health)
def root_health(request: Request) -> dict:
    """Root-level health endpoint for M2M consumers (HA integration).

    Carries ``supported_majors`` (#1124) because this is the one endpoint a client
    can reach *before* it has chosen an API major — putting the negotiation input
    behind a versioned path would be circular. It is also unauthenticated, which
    the negotiation needs: a client picks its base URL before it has a token.

    May carry ``build_revision`` (#1210) because ``version`` cannot answer "which
    build am I running?". ``version`` is the API contract version — a constant
    that stays ``1.0.0`` across every deployment — so an operator holding a merged
    fix had no way to tell whether it had arrived, other than re-triggering the
    bug. When present it is reported *in addition to* ``version``, never instead of
    it: ``version`` also feeds OpenAPI ``info.version`` and the mDNS advertisement,
    which must keep describing the contract rather than the build.

    **The field is opt-in and absent by default** (``HEALTH_EXPOSE_BUILD_REVISION``).
    On an unauthenticated endpoint the SHA is not the sensitive part — the
    repository is public — the mapping *this host → that commit* is, because it
    yields the exact hash-pinned dependency set and the exact list of merged
    security fixes this instance is missing. Absent, the key does not appear at
    all; it is never reported as ``"unknown"``, which means something else
    ("willing to answer, nothing baked in") and which a drift-detection consumer
    has to be able to tell apart from a deliberately silent instance.

    Rate-limited per client IP (``rate_limit_health``, SEC-003). The endpoint is
    unauthenticated and does real work — the router-graph walk below plus, where
    enabled, **synchronous** probes into TimescaleDB and the knowledge service —
    which made it a cheap amplification point into internal services. The
    Kubernetes liveness/readiness probes hit ``/api/v1/health/live`` and
    ``/api/v1/health/ready`` instead and stay unlimited.

    ``request`` is unused by the body: SlowAPI resolves the client from it, and
    requires it by that name.
    """
    result: dict = {
        "status": "healthy",
        "version": settings.app_version,
        "mode": settings.kamerplanter_mode,
        "supported_majors": supported_api_majors(app),
    }
    if settings.health_expose_build_revision:
        result["build_revision"] = settings.resolve_build_revision()
    if settings.timescaledb_enabled:
        from app.common.dependencies import get_observation_repo

        result["timescaledb"] = "available" if get_observation_repo().is_available() else "unavailable"
    if settings.knowledge_service_enabled:
        from app.common.dependencies import get_knowledge_client

        client = get_knowledge_client()
        result["knowledge_service"] = "available" if client and client.health() else "unavailable"
    return result


# The unauthenticated ``/uploads/tasks`` static mount that stood here is gone
# with #1339. It was the surviving half of a task-photo design that was never
# finished: no route ever wrote into that directory (the upload button posted to
# a path no router served), so it has been empty in every deployment and served
# nothing. Had the missing half ever landed in that shape it would have published
# every tenant's task photos to anyone who could guess a filename — no auth, no
# tenant check. Task photos now go through the NFR-013 attachment fundament
# instead (``app/api/v1/tasks/photo_router.py``), which is tenant-scoped,
# permission-gated and covered by the DSGVO retention scope.

app.add_exception_handler(KamerplanterError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]

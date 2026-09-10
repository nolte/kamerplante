# Multi-target image — dev and prod share one base stage (no duplicated apt/uv
# logic, no separate Dockerfile.dev).
#   prod (default, built by CI):   docker build .
#   dev  (built by skaffold):      docker build --target dev .
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS base

LABEL org.opencontainers.image.title="kamerplanter-backend" \
      org.opencontainers.image.description="Kamerplanter core REST API and business logic (FastAPI) for plant lifecycle, phases, fertilizing, tasks and multi-tenant data" \
      org.opencontainers.image.source="https://github.com/nolte/kamerplanter" \
      org.opencontainers.image.vendor="Kamerplanter" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

# uv is the lock toolchain (NFR-009 §2.3; [tool.uv] in pyproject.toml says why it
# replaced pip-tools). It is one static binary, copied from its own image and
# digest-pinned so Renovate's dockerfile manager ages it exactly like the base
# image above. The environment pins uv to the interpreter this image ships —
# no managed-Python download, no cache layer to carry, bytecode compiled once at
# build time — and puts the project environment on PATH so the CMD lines below
# resolve `uvicorn` without an activation step.
COPY --from=ghcr.io/astral-sh/uv:0.12.12@sha256:73d2665b478d8fa2de1cf105c6841f8e9cb6b09e568fc7700440c09f8fcd7ac4 /uv /bin/uv
ENV UV_PYTHON=/usr/local/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy the abstract source (pyproject.toml) and the compiled locks up front so
# the dependency-install layers are cached independently of application code.
# The locks are the single source of truth for what actually gets installed
# (NFR-009 §2.3/§6.1); pyproject.toml is only used for the app package itself.
COPY pyproject.toml uv.lock ./

# ── Development target: hot-reload + debugpy (skaffold dev syncs app/**/*.py) ──
# Runs as root by design; values-dev.yaml sets runAsUser:0 for the writable
# rootfs the hot-reload/__pycache__ needs.
FROM base AS dev
# Install the pinned, hash-verified dev lock, then add the app package itself as
# an editable install with --no-deps (deps already satisfied from the lock).
# Editable keeps hot-reload working while the install set stays reproducible.
# hadolint ignore=DL3013
# Two syncs on purpose: the first installs the locked dependency set from the
# two files copied above (a cacheable layer that survives source edits), the
# second adds the project itself — editable, so the bind mount in Skaffold dev
# is what runs. `--locked` verifies the lock against pyproject.toml and every
# artifact against its recorded hash; a stale lock or a tampered wheel fails the
# build instead of installing something else. debugpy goes in last because
# `uv sync` makes the environment exact and would otherwise remove it again.
RUN uv sync --locked --extra dev --no-install-project
COPY . .
RUN uv sync --locked --extra dev \
    && uv pip install debugpy
# Own /app as UID 1000 so the non-root dev pod (values-dev runAsUser:1000) can
# hot-reload (__pycache__) and receive skaffold file-sync writes.
RUN chown -R 1000:1000 /app
ENV PYTHONUNBUFFERED=1 \
    WATCHFILES_FORCE_POLLING=true
EXPOSE 8000 5678
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD ["curl", "-f", "http://localhost:8000/api/v1/health/live"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production target (default; last stage, so CI's untargeted build picks it) ──
FROM base AS prod
# Install the exact pinned, hash-verified dependency set from the lock, then add
# the app package with --no-deps so nothing is re-resolved from PyPI. This makes
# the shipped image reproducible: two builds of the same commit install byte-for-
# byte the same wheels (NFR-009 §2.3/§6.1). Hash pinning verified feasible for
# all native wheels (weasyprint, psycopg[binary], aquacropeto) on Python 3.14.
# Same two-step shape as dev, minus the dev extra and with the project
# installed non-editable: the image runs the packaged copy, not a path back
# into /app/app.
RUN uv sync --locked --no-install-project
COPY . .
RUN uv sync --locked --no-editable
# Run as a non-root numeric user. UID 1000 matches the deployment's
# fsGroup:1000 so the mounted attachments PVC stays writable.
RUN groupadd -g 1000 app && useradd -u 1000 -g 1000 -d /app -s /usr/sbin/nologin app \
    && chown -R 1000:1000 /app
USER 1000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["curl", "-f", "http://localhost:8000/api/v1/health/live"]

# Build identity (#1210) — deliberately the LAST thing in the stage. The value
# changes on every single commit, so anything below it would be rebuilt every
# time; here, every expensive layer above (apt, the hash-verified `uv sync`,
# COPY, chown, useradd) is already cached and an ARG/ENV pair adds only metadata.
#
# CI passes it in from .github/workflows/docker-publish.yml
# (`build-args: BUILD_REVISION=${{ github.sha }}`) — the same full 40-character
# SHA docker/metadata-action writes to org.opencontainers.image.revision, so
# `GET /api/health` and the image annotation compare with no truncation.
#
# The empty default is load-bearing: an image built without the build-arg (the
# `dev` target, a local `docker build`) reports "unknown" rather than a stale or
# invented SHA. Settings.resolve_build_revision() maps both unset and empty there.
ARG BUILD_REVISION=""
ENV BUILD_REVISION=${BUILD_REVISION}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

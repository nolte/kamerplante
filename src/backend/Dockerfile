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
# resolve `uvicorn` without an activation step. The environment lives in
# /opt/venv, OUTSIDE /app, on purpose: the stages below `chown -R 1000:1000 /app`
# for the source tree, and a venv under /app would (a) be copied wholesale into
# that chown layer (~420 MB per build, measured) and (b) leave site-packages
# writable by the UID the server runs as.
COPY --from=ghcr.io/astral-sh/uv:0.12.13@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 /uv /bin/uv
ENV UV_PYTHON=/usr/local/bin/python3 \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

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

# Copy the abstract source (pyproject.toml) and the lock up front so the
# dependency-install layer is cached independently of application code. The
# lock is the single source of truth for what actually gets installed
# (NFR-009 §2.3/§6.1).
COPY pyproject.toml uv.lock ./

# ── Development target: hot-reload + debugpy (skaffold dev syncs app/**/*.py) ──
# Runs as root by design; values-dev.yaml sets runAsUser:0 for the writable
# rootfs the hot-reload/__pycache__ needs.
FROM base AS dev
# Two syncs on purpose: the first installs the locked dependency set from the
# two files copied above (a cacheable layer that survives source edits), the
# second adds the project itself — editable, so the bind mount in Skaffold dev
# is what runs. `--locked` verifies the lock against pyproject.toml and every
# artifact against its recorded hash; a stale lock or a tampered wheel fails the
# build instead of installing something else. debugpy goes in last because
# `uv sync` makes the environment exact and would otherwise remove it again; it
# is the one package outside the lock, as it was under pip.
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
# One sync, dependencies only: the application is imported from /app (the
# working directory, which uvicorn and celery put on sys.path), exactly as it
# was when `pip install --no-deps .` sat beside `COPY . .`. Not building the
# project wheel also keeps the build backend out of the prod image build; the
# two sdist-only dependencies still need one, pinned through
# `[tool.uv].build-constraint-dependencies` in pyproject.toml. `--locked`
# verifies every artifact hash, so two builds of one commit install the same
# bytes (NFR-009 §2.3/§6.1).
RUN uv sync --locked --no-install-project
COPY . .
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

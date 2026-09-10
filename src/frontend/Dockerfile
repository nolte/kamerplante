# Multi-target image — dev (Vite HMR server) and prod (static nginx) share one
# node base that installs deps once. No separate Dockerfile.dev.
#   prod (default, built by CI):   docker build .
#   dev  (built by skaffold):      docker build --target dev .

# ── Shared node base: install dependencies once ──
FROM node:24-alpine@sha256:50c8e8ca1d27439048670df5883f32d57cf81cff6233222c893fd0d9884cbd81 AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ── Development target: Vite dev server with HMR (skaffold dev syncs src/**) ──
FROM base AS dev
LABEL org.opencontainers.image.title="kamerplanter-frontend-dev" \
      org.opencontainers.image.description="Kamerplanter frontend UI (development with Vite HMR)" \
      org.opencontainers.image.source="https://github.com/nolte/kamerplanter" \
      org.opencontainers.image.vendor="Kamerplanter" \
      org.opencontainers.image.licenses="MIT"
COPY . .
EXPOSE 5173
COPY docker-entrypoint.dev.sh /docker-entrypoint.dev.sh
# Make the entrypoint executable and own /app (incl. node_modules for Vite's
# cache) as UID 1000 so the non-root dev pod (values-dev runAsUser:1000) can run
# the Vite HMR server + file-sync.
RUN chmod +x /docker-entrypoint.dev.sh && chown -R 1000:1000 /app
ENTRYPOINT ["/docker-entrypoint.dev.sh"]
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ── Build stage: compile static assets for production ──
# Copy only what the production build (`tsc -p tsconfig.build.json --noEmit &&
# vite build`) actually reads, so unrelated context files (nginx.conf,
# entrypoints, Dockerfile, README, eslint/prettier config, and the git-ignored
# tsconfig.tsbuildinfo) no longer bust this expensive layer.
# tsconfig.build.json excludes tests, so the prod build compiles only app code —
# it does NOT pull in test-only tooling (e.g. scripts/check-bundle-budget.mjs,
# which is imported solely by a test). Tests stay type-checked separately by
# `tsc --noEmit` in CI (.github/workflows/frontend.yml) and pre-commit.
# NOTE: this is an allow-list — if a new non-test build input appears, add it.
FROM base AS build
COPY tsconfig.json tsconfig.build.json tsconfig.node.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src
RUN npm run build

# ── Production target (default; last stage): non-root nginx-unprivileged ──
# Runs as UID 101, listens on 8080 — no root, no privileged port.
FROM nginxinc/nginx-unprivileged:1.31-alpine@sha256:2ddec616f1cb58bcac057aa388f28cb81e35137641ef4226d321714499329bd1 AS prod

LABEL org.opencontainers.image.title="kamerplanter-frontend" \
      org.opencontainers.image.description="Kamerplanter web UI (React single-page app served by nginx) for managing plants, locations, tasks and dashboards" \
      org.opencontainers.image.source="https://github.com/nolte/kamerplanter" \
      org.opencontainers.image.vendor="Kamerplanter" \
      org.opencontainers.image.licenses="MIT"

# Lay down assets as root (UID 0), then hand ownership to UID 101 so the
# runtime-config and backend-proxy entrypoint scripts can write to the html root
# and conf.d when running non-root (Compose path). In the K8s path these paths
# are mounted read-only / emptyDir and the scripts are suppressed, so the chown
# is harmless. Root is named by its numeric UID per hadolint DL3066.
USER 0
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-security-headers.inc /etc/nginx/conf.d/nginx-security-headers.inc
COPY docker-entrypoint.d/ /docker-entrypoint.d/
RUN chown -R 101:101 /usr/share/nginx/html /etc/nginx/conf.d
USER 101

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

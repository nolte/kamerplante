# Local Setup

This page explains how to set up a complete local development environment for Kamerplanter. Skaffold is the only authorized tool for the development workflow — it handles image building and deployment in the Kubernetes cluster. Manual `docker build` or `kubectl apply` commands are not used.

---

## Prerequisites

Install the following tools before you begin:

| Tool | Min. Version | Purpose |
|------|-------------|---------|
| [Docker](https://docs.docker.com/get-docker/) | 24+ | Container runtime for Kind |
| [Kind](https://kind.sigs.k8s.io/) | 0.20+ | Local Kubernetes cluster |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | 1.28+ | Kubernetes CLI |
| [Skaffold](https://skaffold.dev/docs/install/) | 2.10+ | Build and deploy automation |
| [Helm](https://helm.sh/docs/intro/install/) | 3.14+ | Kubernetes package manager |
| [asdf](https://asdf-vm.com/) | 0.14+ | Node.js version management |
| Python | 3.14+ | Backend development without cluster |
| Node.js | 25.1.0 | Frontend development without cluster |

!!! note "Node.js version via asdf"
    A `.tool-versions` file in `src/frontend/` pins Node.js to `25.1.0`. After installing asdf, the correct version is activated automatically:
    ```bash
    asdf plugin add nodejs
    asdf install
    ```

---

## Creating the Kind Cluster

The repository includes a pre-configured Kind configuration with three nodes (1 control plane, 2 workers) and predefined port mappings:

```bash
kind create cluster --config kind-config.yaml --name kamerplanter
```

The cluster only publishes the ingress ports 80 and 443 on the host. Access to the backend (8000), frontend (3000), and ArangoDB (8529) goes through Skaffold's `--port-forward` (see table below), so those host ports must be free at startup.

!!! warning "Existing cluster"
    If a cluster named `kamerplanter` already exists, delete it first:
    ```bash
    kind delete cluster --name kamerplanter
    ```

After creation, verify that `kubectl` points to the new cluster:

```bash
kubectl cluster-info --context kind-kamerplanter
```

---

## Creating the Secret

The backend, Celery worker, and the AI services reference the Kubernetes secret `kamerplanter-secrets` via `envFrom` or `secretKeyRef` (defined in `helm/kamerplanter/values.yaml`). The dev overrides do **not** remove this reference, so the secret must exist in the `default` namespace **before** you start Skaffold — otherwise the affected pods stay stuck in `CreateContainerConfigError`. `FERNET_KEY` and `ERASURE_TOMBSTONE_SALT` are additionally validated as mandatory values at backend startup (fail-fast).

Create the secret once per freshly created cluster:

```bash
kubectl create secret generic kamerplanter-secrets -n default \
  --from-literal=ARANGODB_PASSWORD=your-secure-password \
  --from-literal=ARANGO_ROOT_PASSWORD=your-secure-password \
  --from-literal=JWT_SECRET_KEY=dev-only-not-for-production-secret-key-1234 \
  --from-literal=POSTGRES_PASSWORD=foba123456 \
  --from-literal=VECTORDB_PASSWORD=foba123456 \
  --from-literal=FERNET_KEY=$(python3 -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())") \
  --from-literal=ERASURE_TOMBSTONE_SALT=$(openssl rand -hex 32) \
  --from-literal=INTERNAL_SERVICE_TOKEN=$(openssl rand -hex 32)
```

!!! note "FERNET_KEY format"
    `FERNET_KEY` must be a valid Fernet key: **32 bytes, url-safe base64-encoded** (44 characters) — exactly what `cryptography.fernet.Fernet.generate_key()` produces. An `openssl rand -hex 32` (64 hex characters) is **not** a valid Fernet key: the backend still starts, but any endpoint that encrypts later fails with `ValueError: Fernet key must be 32 url-safe base64-encoded bytes`. Only `FERNET_KEY` needs this format; `ERASURE_TOMBSTONE_SALT` and `INTERNAL_SERVICE_TOKEN` are arbitrary random values.

!!! note "ArangoDB password"
    `ARANGODB_PASSWORD` and `ARANGO_ROOT_PASSWORD` must hold the **same value**: ArangoDB initialises its root password from `ARANGO_ROOT_PASSWORD`, while the backend and Celery connect using `ARANGODB_PASSWORD`. Both come solely from this Secret — `values-dev.yaml` no longer sets them inline. If the values differ, the backend crashes at startup with HTTP 401.

!!! warning "Local development only"
    These values are intentionally weak and must never be used in a production environment. For production and GitOps, the [ArgoCD deployment](../deployment/argocd.md) describes secure secret management (Sealed Secrets, External Secrets Operator).

---

## Starting Development with Skaffold

Skaffold builds container images locally (without pushing to a registry) and deploys them via Helm into the Kind cluster. File changes are synced directly into running containers without a full rebuild.

### Full stack

```bash
skaffold dev --trigger=manual --port-forward
```

With `--trigger=manual`, a rebuild only happens when you press `r`. This prevents unwanted restarts during rapid file changes. Skaffold activates port forwarding automatically (see table below).

### Backend only

```bash
skaffold dev --trigger=manual --port-forward -p backend-only
```

The `backend-only` profile removes the frontend artifact and its port forward from the build pipeline.

### Frontend only

```bash
skaffold dev --trigger=manual --port-forward -p frontend-only
```

### With debugger (debugpy)

```bash
skaffold debug --port-forward
```

The `debug` profile sets `DEBUGPY_ENABLED=true` as a Docker build argument in the backend container. The debugpy port `5678` then becomes available (see [Debugging](debugging.md)).

### With KI stack (RAG / Knowledge Service)

```bash
# Main app + KI stack simultaneously
skaffold dev --trigger=manual --port-forward -m kamerplanter,ki

# KI stack only (for RAG development)
skaffold dev --trigger=manual --port-forward -m ki
```

The KI module (`-m ki`) is a standalone Skaffold configuration in the same `skaffold.yaml`. It deploys the Knowledge Service (port `8090`), Embedding Service (port `8080`), and VectorDB/TimescaleDB (port `5433`) independently from the main application. See [Infrastructure — KI Module](../architecture/infrastructure.md#ki-module) for details.

---

## Port Forwards

Skaffold automatically forwards the following ports when `--port-forward` is set:

| Service | Local Port | Cluster Target | Module |
|---------|-----------|---------------|--------|
| Frontend | `3000` | Vite dev server on `5173` | kamerplanter |
| Backend API | `8000` | FastAPI on `8000` | kamerplanter |
| ArangoDB Web UI | `8529` | ArangoDB on `8529` | kamerplanter |
| Home Assistant | `8123` | Home Assistant on `8123` | kamerplanter |
| VectorDB (TimescaleDB) | `5433` | TimescaleDB on `5432` | ki |
| Knowledge Service | `8090` | Knowledge Service on `8000` | ki |
| Embedding Service | `8080` | Embedding Service on `8080` | ki |

!!! tip "API documentation"
    Once running, the auto-generated Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs). ReDoc is at [http://localhost:8000/redoc](http://localhost:8000/redoc).

---

## Demo Credentials

The backend container runs seed scripts automatically on first startup. A demo user is then available:

| Field | Value |
|-------|-------|
| Email | `demo@kamerplanter.local` |
| Password | `demo-passwort-2024` |
| Tenant slug | `demo` |

---

## Backend Locally Without Kubernetes

For pure backend development without cluster overhead, you can start the FastAPI server directly. A running ArangoDB instance is required (e.g. via Docker Compose).

```bash
# Start ArangoDB and Redis with Docker Compose
docker-compose up -d arangodb valkey

# Install Python dependencies from the lock (uv: https://docs.astral.sh/uv/)
cd src/backend
uv sync --locked --extra dev
source .venv/bin/activate

# Set environment variables
export ARANGODB_HOST=localhost
export ARANGODB_PORT=8529
export ARANGODB_DATABASE=kamerplanter
export ARANGODB_USERNAME=root
export ARANGODB_PASSWORD=rootpassword
export REDIS_URL=redis://localhost:6379/0
export DEBUG=true
export REQUIRE_EMAIL_VERIFICATION=false

# Start the server
uvicorn app.main:app --reload --port 8000
```

!!! note "Hot reload"
    `uvicorn --reload` watches all `.py` files in the `app/` directory and restarts the server automatically on changes. In the Kind cluster, Skaffold handles this via its `sync` mechanism.

---

## Frontend Locally Without Kubernetes

The Vite dev server can run independently of the cluster. It proxies all `/api` requests to the backend (default: `http://127.0.0.1:8000`).

```bash
cd src/frontend
npm install
npm run dev
```

The dev server starts on port `5173`. The backend URL can be overridden via the `VITE_BACKEND_URL` environment variable:

```bash
VITE_BACKEND_URL=http://localhost:8000 npm run dev
```

---

## Home Assistant Integration

The HA integration in `custom_components/kamerplanter/` is **not** automatically deployed by Skaffold. After modifying HA integration files, the contents must be copied manually into the running pod:

```bash
# Copy files into the pod
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# Delete the Python cache (MUST always be done, otherwise HA loads old bytecode)
kubectl exec default/homeassistant-0 -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# Restart the HA process (NOT kubectl delete pod!)
# kill 1 restarts only the container — initContainers do NOT re-run,
# so the kubectl-cp'd files are preserved.
kubectl exec homeassistant-0 -n default -- kill 1
```

---

## Troubleshooting

??? question "Skaffold cannot find the Kind cluster"
    Make sure the kubectl context is set correctly:
    ```bash
    kubectl config use-context kind-kamerplanter
    ```

??? question "Backend pod not starting (CrashLoopBackOff)"
    Check the pod logs:
    ```bash
    kubectl logs -l app=kamerplanter-backend --tail=50
    ```
    Common cause: ArangoDB is not yet ready. The liveness probe waits up to 150 seconds (`initialDelaySeconds: 30`, `failureThreshold: 10`).

??? question "Port 8000 or 3000 is already in use"
    Kill all processes on the affected port:
    ```bash
    lsof -ti:8000 | xargs kill -9
    ```

??? question "Seed data is missing after restart"
    Seed scripts only run on first startup or when the ArangoDB database is recreated. To rerun seeds:
    ```bash
    kubectl exec -it deployment/kamerplanter-backend -- \
      python -m app.migrations.seed_auth
    ```

## See also

- [Code Standards](code-standards.md)
- [Testing](testing/index.md)
- [Debugging](debugging.md)

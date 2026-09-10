# Helm Charts

The Kamerplanter Helm chart is based on the [bjw-s common library](https://bjw-s-labs.github.io/helm-charts/) and defines all Kubernetes resources in a single chart. Container images and the chart itself are published as OCI artifacts on the GitHub Container Registry.

---

## Registry overview

| Artifact | OCI URL |
|----------|---------|
| Helm chart | `oci://ghcr.io/nolte/charts/kamerplanter` |
| Backend image | `ghcr.io/nolte/kamerplanter-backend` |
| Frontend image | `ghcr.io/nolte/kamerplanter-frontend` |

---

## Chart information

<!-- Source: helm/kamerplanter/Chart.yaml -->

```yaml
name: kamerplanter
type: application
version: 0.2.1-dev      # Chart version in the develop tree — pre-release channel
appVersion: "1.0.0"     # Application version
```

!!! danger "`-dev` is the development channel, not a release"

    The `-dev` suffix is not a typo. The `develop` tree always carries a
    pre-release with that suffix, and `helm push` derives the OCI tag verbatim
    from this line. The tag
    `oci://ghcr.io/nolte/charts/kamerplanter:0.2.1-dev` is therefore overwritten
    by every merge into `develop` that touches `helm/` — that is what the
    channel is for.

    A release, by contrast, publishes under the bare version without a suffix,
    for example `0.1.0`. The two channels are disjoint and cannot overlap: the
    `dev` pre-release identifier is refused on the release path, so a tag
    `v0.3.0-dev` is rejected. `-rc` and `-beta` remain legal.

    What is enforced is the `dev` identifier alone, not the number in front of
    it. `0.2.1` names the intended next release and nothing keeps it ahead of
    the published line — once `v0.2.1` ships, `0.2.1-dev` sorts below it, and no
    schedule bumps this value. That is deliberate: any `-dev` number is
    collision-proof, so a periodic bump would buy nothing.

    **Never use a `-dev` version in a deployment.** Pin a published version or
    the manifest digest. Why this is not theoretical, and how both channels are
    enforced: [CI/CD — Two channels](ci-cd.md#two-channels).
    <!-- #1222 -->

### Dependencies

| Dependency | Version | Source | Purpose |
|-----------|---------|--------|---------|
| common (bjw-s) | 5.0.1 | bjw-s-labs Helm Charts | Library chart for standardized Kubernetes resources |
| valkey | 0.10.0 | OCI: ghcr.io/valkey-io/valkey-helm | Redis-compatible cache + Celery broker |

<!-- Source: helm/kamerplanter/Chart.yaml -->

!!! note "Ollama subchart is commented out"
    `Chart.yaml` contains a third, **commented-out** dependency entry for an Ollama Helm chart (`otwld/ollama-helm`). It is not active — in Kubernetes deployments, Ollama currently runs as a separate controller added by the operator (see [Deployment Profiles → Professional](betriebsprofile.md#profi)), not as a sub-chart dependency.

---

## Chart structure

```
helm/kamerplanter/
├── Chart.yaml            # Chart metadata and dependencies
├── Chart.lock            # Pinned dependency versions
├── values.yaml           # Default values (production)
├── values-dev.yaml       # Override for development
├── templates/
│   └── common.yaml       # bjw-s library loader
└── charts/
    ├── common-4.6.2.tgz  # bjw-s Common Library
    └── valkey-0.9.3.tgz  # Valkey sub-chart
```

The chart uses the bjw-s `common.loader.all` approach: all Kubernetes resources (Deployments, StatefulSets, Services, ConfigMaps, Ingress) are defined declaratively via `values.yaml` — there are no custom templates.

---

## Configuration reference

### Controllers (Deployments & StatefulSets)

#### Backend

```yaml
controllers:
  backend:
    type: deployment
    replicas: 1                    # Chart default; typically raised to 2 for production (see Kubernetes Deployment)
    strategy: RollingUpdate
    containers:
      main:
        image:
          repository: ghcr.io/nolte/kamerplanter-backend
          tag: 0.2.1@sha256:af9bec…    # immutable digest, written by the release job — see "Pin a specific image version"
        envFrom:
          - secret: kamerplanter-secrets    # ARANGODB_PASSWORD, JWT_SECRET_KEY, FERNET_KEY, ERASURE_TOMBSTONE_SALT
        env:
          ARANGODB_HOST: "..."
          ARANGODB_PORT: "8529"
          ARANGODB_DATABASE: "kamerplanter"
          ARANGODB_USERNAME: "root"
          REDIS_URL: "redis://kamerplanter-valkey:6379/0"
          CORS_ORIGINS: '["..."]'
          DEBUG: "false"
          KAMERPLANTER_MODE: "light"    # or "full" (chart default)
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: "1"
            memory: 2Gi                 # Image uploads (REQ-034) decode in memory — 512Mi OOMKills on upload
```

!!! danger "`ARANGODB_PASSWORD`, `JWT_SECRET_KEY`, `FERNET_KEY`, `ERASURE_TOMBSTONE_SALT` never come from `env:`"
    The real chart deliberately does **not** declare these four values under `env:` — they come exclusively via `envFrom: - secret: kamerplanter-secrets` from a secret you create beforehand. Without that secret (or with an unchanged default value inside it), the backend refuses to start when `DEBUG=false`. Details: [Kubernetes Deployment — Create the mandatory secrets](kubernetes.md), [Configuration Matrix — Mandatory secrets](konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

#### Frontend

```yaml
controllers:
  frontend:
    type: deployment
    replicas: 1                    # Chart default; typically raised to 2 for production
    containers:
      main:
        image:
          repository: ghcr.io/nolte/kamerplanter-frontend
          tag: latest@sha256:fea5a3…
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
```

The frontend is served behind nginx. The nginx configuration is automatically mounted as a ConfigMap and proxies `/api/` requests to the backend.

#### ArangoDB

```yaml
controllers:
  arangodb:
    type: statefulset
    replicas: 1                    # Single node (no cluster)
    containers:
      main:
        image:
          repository: arangodb
          tag: "3.12.9"
        envFrom:
          - secret: kamerplanter-secrets    # ARANGO_ROOT_PASSWORD
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: "1"
            memory: 1Gi
    statefulset:
      volumeClaimTemplates:
        - name: data
          accessMode: ReadWriteOnce
          size: 5Gi                 # Adjustable
          globalMounts:
            - path: /var/lib/arangodb3
```

### Services

```yaml
service:
  backend:
    controller: backend
    ports:
      http:
        port: 8000
  frontend:
    controller: frontend
    ports:
      http:
        port: 80          # Service port stays 80 (Ingress/DNS)
        targetPort: 8080  # nginx-unprivileged container listens on 8080, not 80
  arangodb:
    controller: arangodb
    ports:
      http:
        port: 8529
```

### Ingress

```yaml
ingress:
  main:
    enabled: true                   # Default: disabled
    hosts:
      - host: plants.example.com
        paths:
          - path: /api
            pathType: Prefix
            service:
              identifier: backend
          - path: /
            pathType: Prefix
            service:
              identifier: frontend
```

!!! tip "TLS"
    For HTTPS, add a `tls` section and use e.g. cert-manager with Let's Encrypt:

    ```yaml
    ingress:
      main:
        enabled: true
        annotations:
          cert-manager.io/cluster-issuer: letsencrypt-prod
        hosts:
          - host: plants.example.com
            paths: [...]
        tls:
          - secretName: kamerplanter-tls
            hosts:
              - plants.example.com
    ```

### Valkey (Redis-compatible cache)

```yaml
valkey:
  dataStorage:
    enabled: true
    size: 1Gi
```

---

## Environment variables

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `ARANGODB_HOST` | Yes | — | Hostname of the ArangoDB service |
| `ARANGODB_PORT` | Yes | `8529` | Port of the ArangoDB service |
| `ARANGODB_DATABASE` | Yes | `kamerplanter` | Database name |
| `ARANGODB_USERNAME` | Yes | `root` | Database user |
| `ARANGODB_PASSWORD` | Yes | — | Database password. Comes from the `kamerplanter-secrets` secret (`envFrom`) in the chart, **not** from `env:`. |
| `ARANGO_ROOT_PASSWORD` | Yes | — | ArangoDB root password, also from `kamerplanter-secrets`. Must match `ARANGODB_PASSWORD`. |
| `JWT_SECRET_KEY` | Yes | — | JWT signing key, from `kamerplanter-secrets`. Boot blocker with `DEBUG=false` if the chart-internal default is left unchanged. |
| `FERNET_KEY` | Yes | — | Encryption key for OIDC provider secrets, from `kamerplanter-secrets`. Boot blocker with `DEBUG=false` if empty. |
| `ERASURE_TOMBSTONE_SALT` | Yes | — | GDPR pseudonymization salt (≥ 32 characters), from `kamerplanter-secrets`. Boot blocker with `DEBUG=false` if empty or too short. |
| `INTERNAL_SERVICE_TOKEN` | Conditional | — | Only required once `KNOWLEDGE_SERVICE_ENABLED=true` or `INFERENCE_SERVICE_ENABLED=true` is set, also from `kamerplanter-secrets`. |
| `REDIS_URL` | Yes | — | Valkey/Redis connection URL |
| `CORS_ORIGINS` | Yes | — | Allowed origins as JSON array |
| `DEBUG` | No | `false` | Enable debug mode. Setting `true` also disables the boot blocker for the five rows above — **never** set this in production. |
| `KAMERPLANTER_MODE` | No | `full` | `light` (no auth, single user) or `full` (with JWT auth and tenant management). The chart does **not** set this variable on the backend controller by default — the Python-side default `full` applies. On the frontend init container it is hard-set to `full` and must be explicitly overridden for light mode. |
| `REQUIRE_EMAIL_VERIFICATION` | No | `false` | Email verification on registration |

Full list of every mandatory secret per enabled feature: [Configuration Matrix — Mandatory secrets](konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

---

## Development overrides (values-dev.yaml)

A separate values file exists for local development, used automatically by Skaffold:

<!-- Source: helm/kamerplanter/values.yaml, helm/kamerplanter/values-dev.yaml -->

| Setting | Production (`values.yaml`) | Development (`values-dev.yaml`) |
|---------|-----------|-------------|
| Replicas (backend/frontend) | 1 (chart default — typically raised to 2 manually for production, see [Kubernetes Deployment](kubernetes.md)) | 1 |
| Update strategy | RollingUpdate | Recreate |
| DEBUG | false | true |
| Resource limits | Strict | Generous |
| Frontend port | 80 (nginx) | 5173 (Vite dev server) |
| ArangoDB PVC | 5 Gi (chart default) | 2 Gi |
| Ingress host | (configurable) | `kamerplanter.local` |

---

## Common customizations

### Reduce resources (small cluster / Raspberry Pi)

```yaml
controllers:
  backend:
    replicas: 1
    containers:
      main:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
  frontend:
    replicas: 1
    containers:
      main:
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
          limits:
            cpu: 250m
            memory: 128Mi
  arangodb:
    containers:
      main:
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

### Pin a specific image version

A published chart already ships pinned digests (the release job writes them at packaging time) — override them only if you want a version other than the one the chart carries. In that case, override them completely, digest included:

```yaml
controllers:
  backend:
    containers:
      main:
        image:
          tag: "1.2.3@sha256:c6689b…"    # (1)!
  frontend:
    containers:
      main:
        image:
          tag: "1.2.3@sha256:6727d2…"
```

1. Resolve the digest with:
   `docker buildx imagetools inspect ghcr.io/nolte/kamerplanter-backend:1.2.3`

!!! danger "An override without a digest undoes the chart's pinning"
    The override beats the chart default. `tag: "1.2.3"` — without the part
    after the `@` — replaces an immutable reference with a name that can be
    re-pushed. Combined with `pullPolicy: IfNotPresent`, a node may then keep
    serving old bytes without that showing up anywhere. This is exactly what the
    `inference-service` incident hung on.

!!! tip "And do not use `latest` at all"
    `latest` moves on every push to `develop`. A reference that moves cannot be
    rolled back: "the previous image" resolves to the current one. See
    [Deployment and rollback](ci-cd.md#deployment-and-rollback).

---

## Storage Configuration (NFR-013) {#storage-configuration-nfr-013}

Kamerplanter stores all binary data (photos, imports, exports) through an interchangeable storage adapter. The choice of backend and the associated Kubernetes persistence are fully controlled through `values.yaml`.

### Local Filesystem (Default)

In the default setup, the chart automatically creates the PVC `backend-attachments` and mounts it in the backend and Celery worker pods at `/data/attachments`.

```yaml
storage:
  backend: local-fs                  # Default; no external storage needed
  maxFileSizeMb: 25
  presignTtlSeconds: 900
  virusScan:
    enabled: false
    endpoint: ""

  localFs:
    root: /data/attachments           # Container-internal mount path
    pvc:
      size: 20Gi                      # Chart default; increase as needed
      accessMode: ReadWriteOnce       # For single-replica (default)
      storageClass: ""                # Empty = cluster default
```

**Multi-replica operation** (backend replicas > 1):

```yaml
storage:
  localFs:
    pvc:
      accessMode: ReadWriteMany       # Requires an RWX-capable StorageClass
      storageClass: longhorn          # Or: nfs, cephfs, etc.
```

!!! warning "Signing secret required with RWX"
    With more than one backend replica, `STORAGE_LOCALFS_SIGNING_SECRET` must be set as a stable Kubernetes Secret. Without it, each pod generates its own ephemeral signing secret — token-based downloads fail when the validation request reaches a different pod than the one that signed the token.

    ```bash
    kubectl create secret generic kamerplanter-storage-signing \
      --from-literal=STORAGE_LOCALFS_SIGNING_SECRET="$(openssl rand -hex 32)" \
      --namespace kamerplanter
    ```

    Reference it in the chart via `envFrom`:

    ```yaml
    controllers:
      backend:
        containers:
          main:
            envFrom:
              - secretRef:
                  name: kamerplanter-storage-signing
    ```

### S3-compatible (Production)

Non-secret S3 parameters are set directly in `values.yaml`. Credentials come exclusively from the External Secrets Operator (ESO) — never as plain text in Git.

```yaml
storage:
  backend: s3
  maxFileSizeMb: 25
  presignTtlSeconds: 900

  s3:
    endpointUrl: https://s3.eu-central-1.amazonaws.com
    region: eu-central-1
    bucket: kamerplanter-prod
    usePathStyle: false               # true for MinIO and non-AWS providers
    forceTls: true
    kmsKeyId: ""                      # Optional: customer-managed key (SSE-KMS)

    # S3 credentials via External Secrets Operator (NEVER plain text)
    credentialsRef:
      secretName: storage-s3-credentials
      accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
      secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
```

**External Secrets Operator — ESO Secret:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: storage-s3-credentials
  namespace: kamerplanter
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend              # Or AWS Secrets Manager, etc.
    kind: ClusterSecretStore
  target:
    name: storage-s3-credentials
    creationPolicy: Owner
  data:
    - secretKey: STORAGE_S3_ACCESS_KEY_ID
      remoteRef:
        key: kamerplanter/storage
        property: access_key_id
    - secretKey: STORAGE_S3_SECRET_ACCESS_KEY
      remoteRef:
        key: kamerplanter/storage
        property: secret_access_key
```

!!! tip "Without ESO: manual Kubernetes Secret"
    If no External Secrets Operator is available, create the secret manually:
    ```bash
    kubectl create secret generic storage-s3-credentials \
      --from-literal=STORAGE_S3_ACCESS_KEY_ID="your-access-key" \
      --from-literal=STORAGE_S3_SECRET_ACCESS_KEY="your-secret-key" \
      --namespace kamerplanter
    ```
    The secret should come from a secure vault and must **never** be stored in Git.

#### NetworkPolicy for S3 Endpoints

The chart includes a NetworkPolicy that restricts outbound connections to the configured S3 endpoint and blocks access to the cloud metadata IP (`169.254.169.254`) (SSRF protection):

```yaml
networkPolicies:
  storage:
    enabled: true
    blockMetadataEndpoint: true      # Blocks 169.254.169.254 (default: true)
```

#### MinIO In-Cluster

```yaml
storage:
  backend: s3
  s3:
    endpointUrl: http://minio.kamerplanter.svc:9000
    region: us-east-1
    bucket: kamerplanter
    usePathStyle: true
    forceTls: false
    allowPrivateEndpoint: true       # Permits a non-publicly-reachable endpoint
    credentialsRef:
      secretName: storage-s3-credentials
      accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
      secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
```

### Virus Scanning (optional)

```yaml
storage:
  virusScan:
    enabled: true
    endpoint: http://clamav-rest.kamerplanter.svc:9000
```

ClamAV must run as a separate deployment in the cluster. The backend blocks an upload when the scanner reports a finding.

### Common Provider Configurations

=== "Hetzner Object Storage"

    ```yaml
    storage:
      backend: s3
      s3:
        endpointUrl: https://fsn1.your-objectstorage.com
        region: eu-central
        bucket: my-kamerplanter-bucket
        usePathStyle: false
        forceTls: true
        credentialsRef:
          secretName: storage-s3-credentials
          accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
          secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
    ```

=== "Cloudflare R2"

    ```yaml
    storage:
      backend: s3
      s3:
        endpointUrl: https://<account-id>.r2.cloudflarestorage.com
        region: auto
        bucket: kamerplanter
        usePathStyle: false
        forceTls: true
        credentialsRef:
          secretName: storage-s3-credentials
          accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
          secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
    ```

=== "Backblaze B2 (S3 API)"

    ```yaml
    storage:
      backend: s3
      s3:
        endpointUrl: https://s3.eu-central-003.backblazeb2.com
        region: eu-central-003
        bucket: kamerplanter
        usePathStyle: false
        forceTls: true
        credentialsRef:
          secretName: storage-s3-credentials
          accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
          secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
    ```

---

## See also

- [Kubernetes Deployment](kubernetes.md) — Step-by-step guide
- [Environment Variables](../reference/environment-variables.md) — Full reference of all environment variables
- [Configure Storage (Object Storage)](../user-guide/object-storage.md) — Admin UI and migration

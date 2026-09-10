# Helm Charts

Das Kamerplanter Helm-Chart basiert auf der [bjw-s common library](https://bjw-s-labs.github.io/helm-charts/) und definiert alle Kubernetes-Ressourcen in einem einzigen Chart. Container-Images und das Chart selbst werden als OCI-Artefakte über die GitHub Container Registry bereitgestellt.

---

## Registry-Übersicht

| Artefakt | OCI-URL |
|----------|---------|
| Helm-Chart | `oci://ghcr.io/nolte/charts/kamerplanter` |
| Backend-Image | `ghcr.io/nolte/kamerplanter-backend` |
| Frontend-Image | `ghcr.io/nolte/kamerplanter-frontend` |

---

## Chart-Informationen

<!-- Quelle: helm/kamerplanter/Chart.yaml -->

```yaml
name: kamerplanter
type: application
version: 0.2.1-dev      # Chart-Version im develop-Baum — Vorabkanal
appVersion: "1.0.0"     # Anwendungs-Version
```

!!! danger "`-dev` ist der Entwicklungskanal, kein Release"

    Der Zusatz `-dev` ist kein Schreibfehler. Der `develop`-Baum trägt immer
    eine Vorabversion mit diesem Zusatz, und `helm push` leitet den OCI-Tag
    wörtlich aus dieser Zeile ab. Der Tag
    `oci://ghcr.io/nolte/charts/kamerplanter:0.2.1-dev` wird deshalb bei jedem
    Merge nach `develop` überschrieben, der `helm/` berührt — das ist der Zweck
    dieses Kanals.

    Ein Release publiziert dagegen unter der reinen Version ohne Zusatz, etwa
    `0.1.0`. Die beiden Kanäle sind disjunkt und können sich nicht überschneiden:
    Der Vorab-Bezeichner `dev` ist im Release-Pfad gesperrt, ein Tag `v0.3.0-dev`
    wird abgewiesen. `-rc` und `-beta` bleiben erlaubt.

    Erzwungen ist allein der Bezeichner `dev`, nicht die Nummer davor. `0.2.1`
    benennt das beabsichtigte nächste Release, ohne dass irgendetwas den Wert
    vor der veröffentlichten Linie hält — sobald `v0.2.1` erscheint, sortiert
    `0.2.1-dev` darunter, und kein Turnus hebt ihn an. Das ist Absicht: Jede
    `-dev`-Nummer ist kollisionssicher, ein regelmäßiger Bump brächte nichts.

    **Verwende in keinem Deployment eine `-dev`-Version.** Pinne eine
    veröffentlichte Version oder den Manifest-Digest. Warum das keine Theorie
    ist, und wie beide Kanäle abgesichert sind:
    [CI/CD — Zwei Kanäle](ci-cd.md#zwei-kanaele).
    <!-- #1222 -->

### Abhängigkeiten

| Dependency | Version | Quelle | Zweck |
|-----------|---------|--------|-------|
| common (bjw-s) | 5.0.1 | bjw-s-labs Helm-Charts | Library-Chart für einheitliche Kubernetes-Ressourcen |
| valkey | 0.10.0 | OCI: ghcr.io/valkey-io/valkey-helm | Redis-kompatibler Cache + Celery-Broker |

<!-- Quelle: helm/kamerplanter/Chart.yaml -->

!!! note "Ollama-Subchart auskommentiert"
    `Chart.yaml` enthält einen dritten, **auskommentierten** Dependency-Eintrag für einen Ollama-Helm-Chart (`otwld/ollama-helm`). Er ist nicht aktiv — Ollama wird in Kubernetes-Deployments aktuell als eigener, vom Operator ergänzter Controller betrieben (siehe [Betriebsprofile → Profi](betriebsprofile.md#profi)), nicht als Sub-Chart-Abhängigkeit.

---

## Chart-Struktur

```
helm/kamerplanter/
├── Chart.yaml            # Chart-Metadaten und Abhängigkeiten
├── Chart.lock            # Pinned Dependency-Versionen
├── values.yaml           # Standard-Werte (Produktion)
├── values-dev.yaml       # Override für Entwicklung
├── templates/
│   └── common.yaml       # bjw-s Library-Loader
└── charts/
    ├── common-4.6.2.tgz  # bjw-s Common Library
    └── valkey-0.9.3.tgz  # Valkey Sub-Chart
```

Das Chart nutzt den bjw-s `common.loader.all`-Ansatz: Alle Kubernetes-Ressourcen (Deployments, StatefulSets, Services, ConfigMaps, Ingress) werden deklarativ über `values.yaml` definiert — es gibt keine eigenen Templates.

---

## Konfigurationsreferenz

### Controller (Deployments & StatefulSets)

#### Backend

```yaml
controllers:
  backend:
    type: deployment
    replicas: 1                    # Chart-Default; für Produktion i. d. R. auf 2 erhöhen (siehe Kubernetes-Deployment)
    strategy: RollingUpdate
    containers:
      main:
        image:
          repository: ghcr.io/nolte/kamerplanter-backend
          tag: 0.2.1@sha256:af9bec…    # unveränderlicher Digest, vom Release-Job gesetzt — siehe "Bestimmte Image-Version pinnen"
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
          KAMERPLANTER_MODE: "light"    # oder "full" (Chart-Default)
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: "1"
            memory: 2Gi                 # Bild-Uploads (REQ-034) dekodieren im Speicher — 512Mi OOMKillt beim Upload
```

!!! danger "`ARANGODB_PASSWORD`, `JWT_SECRET_KEY`, `FERNET_KEY`, `ERASURE_TOMBSTONE_SALT` kommen NIE aus `env:`"
    Der reale Chart deklariert diese vier Werte absichtlich **nicht** im `env:`-Block — sie kommen ausschließlich per `envFrom: - secret: kamerplanter-secrets` aus einem vorher angelegten Kubernetes-Secret. Ohne dieses Secret (bzw. mit einem unveränderten Default-Wert darin) verweigert das Backend bei `DEBUG=false` den Start. Details: [Kubernetes-Deployment — Pflicht-Secrets anlegen](kubernetes.md), [Konfigurationsmatrix — Pflicht-Secrets](konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

#### Frontend

```yaml
controllers:
  frontend:
    type: deployment
    replicas: 1                    # Chart-Default; für Produktion i. d. R. auf 2 erhöhen
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

Das Frontend wird hinter nginx ausgeliefert. Die nginx-Konfiguration wird automatisch als ConfigMap gemountet und leitet `/api/`-Anfragen an das Backend weiter.

#### ArangoDB

```yaml
controllers:
  arangodb:
    type: statefulset
    replicas: 1                    # Single-Node (kein Cluster)
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
          size: 5Gi                 # Anpassbar
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
        port: 80          # Service-Port bleibt 80 (Ingress/DNS)
        targetPort: 8080  # nginx-unprivileged-Container lauscht auf 8080, nicht 80
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
    enabled: true                   # Standard: deaktiviert
    hosts:
      - host: pflanzen.example.com
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
    Für HTTPS füge eine `tls`-Sektion hinzu und verwende z.B. cert-manager mit Let's Encrypt:

    ```yaml
    ingress:
      main:
        enabled: true
        annotations:
          cert-manager.io/cluster-issuer: letsencrypt-prod
        hosts:
          - host: pflanzen.example.com
            paths: [...]
        tls:
          - secretName: kamerplanter-tls
            hosts:
              - pflanzen.example.com
    ```

### Valkey (Redis-kompatibler Cache)

```yaml
valkey:
  dataStorage:
    enabled: true
    size: 1Gi
```

---

## Umgebungsvariablen

| Variable | Pflicht | Standard | Beschreibung |
|----------|:-------:|----------|-------------|
| `ARANGODB_HOST` | Ja | — | Hostname des ArangoDB-Service |
| `ARANGODB_PORT` | Ja | `8529` | Port des ArangoDB-Service |
| `ARANGODB_DATABASE` | Ja | `kamerplanter` | Datenbankname |
| `ARANGODB_USERNAME` | Ja | `root` | Datenbank-Benutzer |
| `ARANGODB_PASSWORD` | Ja | — | Datenbank-Passwort. Kommt im Chart aus dem Secret `kamerplanter-secrets` (`envFrom`), **nicht** aus `env:`. |
| `ARANGO_ROOT_PASSWORD` | Ja | — | ArangoDB Root-Passwort, ebenfalls aus `kamerplanter-secrets`. Muss identisch mit `ARANGODB_PASSWORD` sein. |
| `JWT_SECRET_KEY` | Ja | — | JWT-Signierschlüssel, aus `kamerplanter-secrets`. Boot-Blocker bei `DEBUG=false`, wenn der Chart-interne Default unverändert bleibt. |
| `FERNET_KEY` | Ja | — | Verschlüsselungsschlüssel für OIDC-Provider-Secrets, aus `kamerplanter-secrets`. Boot-Blocker bei `DEBUG=false`, wenn leer. |
| `ERASURE_TOMBSTONE_SALT` | Ja | — | DSGVO-Pseudonymisierungs-Salt (≥ 32 Zeichen), aus `kamerplanter-secrets`. Boot-Blocker bei `DEBUG=false`, wenn leer oder zu kurz. |
| `INTERNAL_SERVICE_TOKEN` | Bedingt | — | Nur Pflicht, sobald `KNOWLEDGE_SERVICE_ENABLED=true` oder `INFERENCE_SERVICE_ENABLED=true` gesetzt ist, ebenfalls aus `kamerplanter-secrets`. |
| `REDIS_URL` | Ja | — | Valkey/Redis-Verbindungs-URL |
| `CORS_ORIGINS` | Ja | — | Erlaubte Origins als JSON-Array |
| `DEBUG` | Nein | `false` | Debug-Modus aktivieren. Deaktiviert bei `true` zusätzlich den Boot-Blocker der fünf Zeilen oben — **niemals** in Produktion setzen. |
| `KAMERPLANTER_MODE` | Nein | `full` | `light` (ohne Auth, ein Nutzer) oder `full` (mit JWT-Auth und Mandantenverwaltung). Der Chart setzt diese Variable am Backend-Controller standardmäßig **nicht** — es gilt der Python-seitige Default `full`. Am Frontend-InitContainer ist sie fest auf `full` gesetzt und muss für den Light-Modus explizit überschrieben werden. |
| `REQUIRE_EMAIL_VERIFICATION` | Nein | `false` | E-Mail-Verifikation bei Registrierung |

Vollständige Liste aller Pflicht-Secrets je aktivierter Funktion: [Konfigurationsmatrix — Pflicht-Secrets](konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

---

## Entwicklungs-Overrides (values-dev.yaml)

Für die lokale Entwicklung existiert eine separate Values-Datei, die Skaffold automatisch verwendet:

<!-- Quelle: helm/kamerplanter/values.yaml, helm/kamerplanter/values-dev.yaml -->

| Einstellung | Produktion (`values.yaml`) | Entwicklung (`values-dev.yaml`) |
|------------|-----------|-------------|
| Replicas (Backend/Frontend) | 1 (Chart-Default — für Produktion i. d. R. manuell auf 2 erhöht, siehe [Kubernetes-Deployment](kubernetes.md)) | 1 |
| Update-Strategie | RollingUpdate | Recreate |
| DEBUG | false | true |
| Resource Limits | Streng | Großzügig |
| Frontend-Port | 80 (nginx) | 5173 (Vite Dev Server) |
| ArangoDB PVC | 5 Gi (Chart-Default) | 2 Gi |
| Ingress-Host | (konfigurierbar) | `kamerplanter.local` |

---

## Häufige Anpassungen

### Ressourcen reduzieren (kleiner Cluster / Raspberry Pi)

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

### Bestimmte Image-Version pinnen

Ein veröffentlichtes Chart bringt bereits gepinnte Digests mit (der Release-Job setzt sie beim Packen) — du überschreibst sie nur, wenn du eine andere Version willst als die, die das Chart mitliefert. Dann aber vollständig, also mit Digest:

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

1. Digest ermitteln:
   `docker buildx imagetools inspect ghcr.io/nolte/kamerplanter-backend:1.2.3`

!!! danger "Ein Override ohne Digest macht das Pinning des Charts rückgängig"
    Der Override gewinnt gegen den Chart-Default. `tag: "1.2.3"` — ohne den Teil
    hinter dem `@` — ersetzt eine unveränderliche Referenz durch einen Namen, der
    neu gepusht werden kann. Zusammen mit `pullPolicy: IfNotPresent` liefert ein
    Node dann unter Umständen weiter alte Bytes aus, ohne dass es irgendwo
    auffällt. Genau daran hing der `inference-service`-Vorfall.

!!! tip "Und `latest` gar nicht"
    `latest` bewegt sich bei jedem Push auf `develop`. Eine Referenz, die sich
    bewegt, kann nicht zurückgerollt werden: „das vorherige Image" löst sich auf
    das aktuelle auf. Siehe [Deployment und Rollback](ci-cd.md#deployment-und-rollback).

---

## Storage-Konfiguration (NFR-013) {#storage-konfiguration-nfr-013}

Kamerplanter speichert alle Binärdaten (Fotos, Importe, Exporte) über einen austauschbaren Storage-Adapter. Die Wahl des Backends und die zugehörige Kubernetes-Persistenz werden vollständig über `values.yaml` gesteuert.

### Local Filesystem (Standard)

Im Default-Betrieb legt das Chart automatisch das PVC `backend-attachments` an und mountet es in den Backend- und Celery-Worker-Pods unter `/data/attachments`.

```yaml
storage:
  backend: local-fs                  # Standard; kein externes Storage nötig
  maxFileSizeMb: 25
  presignTtlSeconds: 900
  virusScan:
    enabled: false
    endpoint: ""

  localFs:
    root: /data/attachments           # Container-interner Mount-Pfad
    pvc:
      size: 20Gi                      # Chart-Default; nach Bedarf erhöhen
      accessMode: ReadWriteOnce       # Für Single-Replica (Standard)
      storageClass: ""                # Leer = Cluster-Default
```

**Multi-Replica-Betrieb** (Backend-Replicas > 1):

```yaml
storage:
  localFs:
    pvc:
      accessMode: ReadWriteMany       # RWX-fähige StorageClass erforderlich
      storageClass: longhorn          # Oder: nfs, cephfs, etc.
```

!!! warning "Signing-Secret bei RWX zwingend"
    Bei mehr als einer Backend-Replica muss `STORAGE_LOCALFS_SIGNING_SECRET` als stabiles Kubernetes-Secret gesetzt sein. Ohne dieses Secret generiert jeder Pod ein eigenes ephemeres Signing-Secret — Token-Downloads schlagen fehl, wenn die Validierungsanfrage einen anderen Pod erreicht als die Signierung.

    ```bash
    kubectl create secret generic kamerplanter-storage-signing \
      --from-literal=STORAGE_LOCALFS_SIGNING_SECRET="$(openssl rand -hex 32)" \
      --namespace kamerplanter
    ```

    Im Chart über `envFrom` referenzieren:

    ```yaml
    controllers:
      backend:
        containers:
          main:
            envFrom:
              - secretRef:
                  name: kamerplanter-storage-signing
    ```

### S3-kompatibel (Production)

Nicht-geheime S3-Parameter werden direkt in `values.yaml` gesetzt. Die Credentials kommen ausschließlich aus dem External Secrets Operator (ESO) — nie als Klartext in Git.

```yaml
storage:
  backend: s3
  maxFileSizeMb: 25
  presignTtlSeconds: 900

  s3:
    endpointUrl: https://s3.eu-central-1.amazonaws.com
    region: eu-central-1
    bucket: kamerplanter-prod
    usePathStyle: false               # true für MinIO und Nicht-AWS-Anbieter
    forceTls: true
    kmsKeyId: ""                      # Optional: Customer-Managed Key (SSE-KMS)

    # S3-Credentials via External Secrets Operator (NIEMALS Klartext)
    credentialsRef:
      secretName: storage-s3-credentials
      accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
      secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
```

**External Secrets Operator — ESO-Secret:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: storage-s3-credentials
  namespace: kamerplanter
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend              # Oder AWS Secrets Manager, etc.
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

!!! tip "Ohne ESO: manuelles Kubernetes-Secret"
    Wenn kein External Secrets Operator verfügbar ist, lege das Secret manuell an:
    ```bash
    kubectl create secret generic storage-s3-credentials \
      --from-literal=STORAGE_S3_ACCESS_KEY_ID="dein-access-key" \
      --from-literal=STORAGE_S3_SECRET_ACCESS_KEY="dein-secret-key" \
      --namespace kamerplanter
    ```
    Das Secret sollte aus einem sicheren Vault kommen und **niemals** in Git gespeichert werden.

#### NetworkPolicy für S3-Endpoints

Das Chart enthält eine NetworkPolicy, die ausgehende Verbindungen auf den konfigurierten S3-Endpunkt beschränkt und den Zugriff auf die Cloud-Metadata-IP (`169.254.169.254`) blockiert (SSRF-Schutz):

```yaml
networkPolicies:
  storage:
    enabled: true
    blockMetadataEndpoint: true      # Blockiert 169.254.169.254 (Default: true)
```

#### MinIO im Cluster

```yaml
storage:
  backend: s3
  s3:
    endpointUrl: http://minio.kamerplanter.svc:9000
    region: us-east-1
    bucket: kamerplanter
    usePathStyle: true
    forceTls: false
    allowPrivateEndpoint: true       # Erlaubt nicht öffentlich erreichbaren Endpunkt
    credentialsRef:
      secretName: storage-s3-credentials
      accessKeyIdKey: STORAGE_S3_ACCESS_KEY_ID
      secretAccessKeyKey: STORAGE_S3_SECRET_ACCESS_KEY
```

### Virenscan (optional)

```yaml
storage:
  virusScan:
    enabled: true
    endpoint: http://clamav-rest.kamerplanter.svc:9000
```

ClamAV muss als separates Deployment im Cluster laufen. Das Backend blockiert einen Upload, wenn der Scanner einen Fund meldet.

### Häufige Provider-Konfigurationen

=== "Hetzner Object Storage"

    ```yaml
    storage:
      backend: s3
      s3:
        endpointUrl: https://fsn1.your-objectstorage.com
        region: eu-central
        bucket: mein-kamerplanter-bucket
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

=== "Backblaze B2 (S3-API)"

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

## Siehe auch

- [Kubernetes-Deployment](kubernetes.md) — Schritt-für-Schritt-Anleitung
- [Umgebungsvariablen](../reference/environment-variables.md) — Vollständige Referenz aller Umgebungsvariablen
- [Speicher konfigurieren (Object Storage)](../user-guide/object-storage.md) — Admin-UI und Migration

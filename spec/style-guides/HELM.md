# Helm Style Guide — Kubernetes / Skaffold

> Verbindlicher Style Guide fuer die Kamerplanter Helm-Charts und Kubernetes-Manifeste.
> Wird durch **helm lint**, **helm template** und **Skaffold diagnose** automatisch geprueft.

**Scope:** `helm/`, `deploy/`, `skaffold.yaml`

---

## 1. Statische Analyse & Tooling

| Tool | Zweck | CI-Befehl |
|------|-------|-----------|
| **helm lint** | Chart-Validierung | `helm lint helm/kamerplanter -f helm/kamerplanter/values-dev.yaml` |
| **helm template** | Template-Rendering pruefen | `helm template kamerplanter helm/kamerplanter/ -f values-dev.yaml` |
| **skaffold diagnose** | Skaffold-Config validieren | `skaffold diagnose` |
| **skaffold render** | Manifest-Rendering | `skaffold render` |

### 1.1 CI-Pruefung

```bash
# Chart Dependencies aufloesen
helm repo add bjw-s https://bjw-s-labs.github.io/helm-charts/
helm dependency build helm/kamerplanter

# Linting
helm lint helm/kamerplanter -f helm/kamerplanter/values-dev.yaml

# Template-Rendering (erkennt Syntax-Fehler)
helm template kamerplanter helm/kamerplanter/ -f helm/kamerplanter/values-dev.yaml > /dev/null

# Skaffold-Validierung
skaffold diagnose
```

---

## 2. Chart-Architektur

### 2.1 Umbrella-Chart Pattern

```
helm/kamerplanter/
├── Chart.yaml                 # Chart-Definition (apiVersion: v2)
├── Chart.lock                 # Dependency Lock
├── charts/                    # Heruntergeladene Subcharts (nicht einchecken)
├── templates/
│   └── common.yaml            # Einzige Datei: {{ include "bjw-s.common.loader.all" . }}
├── values.yaml                # Produktions-Defaults
└── values-dev.yaml            # Entwicklungs-Overrides
```

**Regeln:**
- **Ein** Umbrella-Chart fuer das gesamte Projekt
- **bjw-s/common** Library-Chart: Alle Manifeste werden ueber `values.yaml` gesteuert
- **Keine** eigenen Template-Dateien ausser `common.yaml`
- **Keine** `_helpers.tpl` — bjw-s stellt alle Helpers bereit
- `charts/` Verzeichnis: Nur generierte Dateien, nie manuell einchecken

### 2.2 Dependencies

```yaml
# Chart.yaml
apiVersion: v2
name: kamerplanter
version: 0.2.1-dev
type: application

dependencies:
  - name: common
    version: 4.6.2
    repository: https://bjw-s-labs.github.io/helm-charts/
  - name: valkey
    version: 0.9.3
    repository: oci://ghcr.io/valkey-io/valkey-helm
```

- Subchart-Versionen werden **gepinnt** (exakte Version)
- `Chart.lock` wird mit eingecheckt
- OCI-Registry fuer neue Charts bevorzugt

---

## 3. values.yaml Konventionen

### 3.1 Namensgebung

| Konvention | Beispiel |
|------------|----------|
| **camelCase** fuer alle Keys | `defaultPodOptions`, `readOnlyRootFilesystem` |
| Controller-Namen: **Lowercase** | `backend`, `frontend`, `arangodb` |
| Service-Identifier: **Controller-Name** | `identifier: backend` |
| Persistence-Keys: **beschreibend** | `nginx-config`, `nginx-cache`, `backend-tmp` |

### 3.2 Top-Level Struktur

```yaml
# 1. Pod-Defaults (Sicherheit)
defaultPodOptions:
  securityContext:
    runAsNonRoot: true
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault

# 2. Controller (Deployments/StatefulSets)
controllers:
  backend:
    # ...
  frontend:
    # ...
  arangodb:
    # ...

# 3. ConfigMaps
configMaps:
  frontend-nginx:
    data:
      default.conf: |
        # Nginx config...

# 4. Services
service:
  backend:
    controller: backend
    ports:
      http:
        port: 8000
  # ...

# 5. Persistence
persistence:
  # ...

# 6. Ingress
ingress:
  # ...

# 7. Network Policies
networkpolicies:
  # ...

# 8. Subchart-Konfiguration
valkey:
  # ...
```

### 3.3 YAML Anchors fuer Port-Referenzen

```yaml
containers:
  main:
    env:
      PORT: &backend-port "8000"    # Definiere einmal
    probes:
      liveness:
        spec:
          httpGet:
            port: *backend-port     # Referenziere ueberall
      readiness:
        spec:
          httpGet:
            port: *backend-port
```

### 3.4 Image-Referenzen: Digest im Release, `latest` im Baum

**Regel:** Jedes von diesem Projekt veroeffentlichte Image
(`ghcr.io/nolte/kamerplanter-*`) wird im **veroeffentlichten Chart** mit
unveraenderlichem Digest referenziert; im Repository steht `latest`:

```yaml
# helm/kamerplanter/values.yaml auf develop — kein Deploy-Kanal
image:
  repository: ghcr.io/nolte/kamerplanter-backend
  tag: latest
  pullPolicy: IfNotPresent

# dasselbe Feld im Release-Chart, vom Release-Job umgeschrieben
  tag: 0.2.1@sha256:af9bec…   # Digest entscheidet, Version ist nur ein Etikett
```

- Der Digest steht **im `tag`-Feld**, nicht im `digest`-Feld, das bjw-s/common
  ebenfalls anbietet: `scripts/ci/pin_chart_image_digests.sh` schreibt die
  ganze Referenz in EIN Feld, und eine Referenz in einem Feld kann nicht halb
  aktualisiert werden.
- `pullPolicy: IfNotPresent` ist bei einer Digest-Referenz korrekt und sicher:
  Ein vorhandenes Image *ist* das angeforderte. Bei einem beweglichen Tag ist
  derselbe Wert eine Falle — er schlaegt das implizite `Always`, das Kubernetes
  fuer `:latest` setzt. Deshalb ist der `develop`-Baum mit `tag: latest`
  ausdruecklich **kein Deploy-Kanal** (siehe „Zwei Kanaele" in
  `docs/*/deployment/ci-cd.md`).
- Ausnahme: **lokal von Skaffold gebaute** Images (`kamerplanter-backend` ohne
  Registry-Praefix in `values-dev*.yaml`). Die existieren in keiner Registry,
  haben keinen Digest, und Skaffold ersetzt die Referenz ohnehin.
- Durchgesetzt **beim Release**: `pin_chart_image_digests.sh` pinnt auf
  `<version>@sha256:<digest>`, und `scripts/check_chart_image_digests.py`
  prueft direkt danach im selben Job, dass kein Kamerplanter-Image ohne Digest
  ins gepackte Chart gelangt.

Begruendung: Eine bewegliche Referenz macht Rollback unmoeglich — „das
vorherige Image" loest sich auf das aktuelle auf (#987). Bis 2026-09-10 trug
auch der `develop`-Baum `latest@sha256:…`, nachgefuehrt von einer Renovate-
Regel; das versorgte kein Deployment und die Renovate-PR wurde von jedem
Publish neu rebased und nie gemergt (#1326), deshalb ist es weg.

---

## 4. Controller-Definition

### 4.1 Deployment (Stateless)

```yaml
controllers:
  backend:
    type: Deployment
    replicas: 1
    strategy: RollingUpdate
    rollingUpdate:
      surge: 1
      unavailable: 0
    containers:
      main:
        image:
          repository: kamerplanter-backend
          tag: latest
          pullPolicy: IfNotPresent
        env:
          ARANGODB_HOST: kamerplanter-arangodb
          ARANGODB_PORT: "8529"
          # ...
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: "1"
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: ["ALL"]
```

### 4.2 StatefulSet (Stateful)

```yaml
controllers:
  arangodb:
    type: StatefulSet
    replicas: 1
    statefulset:
      volumeClaimTemplates:
        - name: data
          accessMode: ReadWriteOnce
          size: 5Gi
          globalMounts:
            - path: /var/lib/arangodb3
```

**Regeln:**
- `type: Deployment` fuer stateless Services
- `type: StatefulSet` nur fuer Datenbanken mit PVC
- Container heisst immer `main` (bjw-s Konvention)
- Environment-Variablen: `UPPER_SNAKE_CASE` Keys, String-Werte in Anfuehrungszeichen

---

## 5. Security-Patterns

### 5.1 Pod-Level (alle Controller)

```yaml
defaultPodOptions:
  securityContext:
    runAsNonRoot: true
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
```

### 5.2 Container-Level (Produktion)

```yaml
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Pflicht fuer Produktion:**
- `runAsNonRoot: true`
- `readOnlyRootFilesystem: true` (emptyDir fuer Temp-Dateien)
- `allowPrivilegeEscalation: false`
- `capabilities.drop: ["ALL"]`
- `seccompProfile.type: RuntimeDefault`

### 5.3 Network Policies

```yaml
networkpolicies:
  frontend:
    controller: frontend
    policyTypes: [Egress]
    rules:
      egress:
        - to:
            - podSelector:
                matchLabels:
                  app.kubernetes.io/controller: backend
          ports:
            - port: 8000
              protocol: TCP
        - to: [{}]              # DNS
          ports:
            - port: 53
              protocol: UDP
            - port: 53
              protocol: TCP
```

**Regeln:**
- Jeder Controller hat eine eigene NetworkPolicy
- Egress ist explizit erlaubt (Deny-All Default)
- DNS (Port 53 UDP+TCP) immer erlauben
- Inter-Service Kommunikation ueber `podSelector` + `matchLabels`

---

## 6. Health Checks

```yaml
probes:
  liveness:
    enabled: true
    custom: true
    spec:
      httpGet:
        path: /api/v1/health/live    # Anwendungsspezifischer Endpunkt
        port: *backend-port
      initialDelaySeconds: 15
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
  readiness:
    enabled: true
    custom: true
    spec:
      httpGet:
        path: /api/v1/health/ready
        port: *backend-port
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 5
      failureThreshold: 3
```

**Regeln:**
- **Immer** Custom Probes (`custom: true`)
- **Separate** Liveness- und Readiness-Endpunkte
- Readiness hat kuerzere Intervalle als Liveness
- ArangoDB: Basic Auth Header in Probe

---

## 7. Persistence

### 7.1 ConfigMap-Mount

```yaml
persistence:
  nginx-config:
    enabled: true
    type: configMap
    identifier: frontend-nginx
    advancedMounts:
      frontend:
        main:
          - path: /etc/nginx/conf.d/default.conf
            subPath: default.conf
            readOnly: true
```

### 7.2 emptyDir (Temp-Dateien)

```yaml
persistence:
  nginx-cache:
    enabled: true
    type: emptyDir
    medium: Memory          # RAM-backed (schnell, klein)
    sizeLimit: 64Mi
    advancedMounts:
      frontend:
        main:
          - path: /var/cache/nginx
```

### 7.3 PVC (Datenbank)

Ueber `statefulset.volumeClaimTemplates` (siehe 4.2).

**Regeln:**
- `readOnly: true` fuer ConfigMap-Mounts
- `medium: Memory` fuer kurzlebige Caches
- `sizeLimit` immer angeben bei emptyDir
- `advancedMounts` mit Controller + Container (`main`)

---

## 8. Environment-Handling

### 8.1 Direkt in values.yaml

```yaml
env:
  ARANGODB_HOST: kamerplanter-arangodb   # Service-Name
  ARANGODB_PORT: "8529"                   # Strings in Anfuehrungszeichen
  DEBUG: "false"
```

### 8.2 Dev-Overrides

```yaml
# values-dev.yaml — ueberschreibt nur Delta
controllers:
  backend:
    containers:
      main:
        env:
          DEBUG: "true"
          KAMERPLANTER_MODE: "light"
          REQUIRE_EMAIL_VERIFICATION: "false"
```

**Regeln:**
- **Keine** Secrets direkt in values.yaml (Produktions-Secrets via Sealed Secrets / External Secrets)
- Dev-Overrides in separater `values-dev.yaml`
- Service-Discovery ueber Kubernetes Service-Namen (z.B. `kamerplanter-arangodb`)
- Alle Werte als Strings (YAML Boolean-Fallstricke vermeiden)

---

## 9. Labels

```yaml
# Automatisch durch bjw-s/common generiert:
app.kubernetes.io/name: kamerplanter
app.kubernetes.io/instance: <release-name>
app.kubernetes.io/controller: backend    # Pro Controller
app.kubernetes.io/version: <chart-version>

# Zusaetzlich fuer HA-Deployment:
app.kubernetes.io/part-of: kamerplanter
```

**Regeln:**
- Ausschliesslich `app.kubernetes.io/` Label-Domain
- Keine Custom-Label-Praefixe
- `controller` Label wird fuer NetworkPolicy-Selektoren genutzt

---

## 10. Skaffold-Integration

### 10.1 Entwicklungs-Workflow

```yaml
# skaffold.yaml
build:
  local:
    push: false               # Lokal bauen, nicht pushen
  artifacts:
    - image: kamerplanter-backend
      context: src/backend
      docker:
        dockerfile: Dockerfile.dev
    - image: kamerplanter-frontend
      context: src/frontend
      docker:
        dockerfile: Dockerfile.dev

deploy:
  helm:
    releases:
      - name: kamerplanter
        chartPath: helm/kamerplanter
        valuesFiles:
          - helm/kamerplanter/values-dev.yaml
        setValueTemplates:
          controllers.backend.containers.main.image.repository: "{{.IMAGE_REPO_kamerplanter_backend}}"
          controllers.backend.containers.main.image.tag: "{{.IMAGE_TAG_kamerplanter_backend}}"
```

### 10.2 Profiles

```yaml
profiles:
  - name: backend-only      # Nur Backend bauen/deployen
  - name: frontend-only     # Nur Frontend bauen/deployen
  - name: debug              # debugpy aktivieren
```

**Regeln:**
- **Skaffold ist das einzige Deploy-Tool** — keine manuellen `docker build`/`kubectl apply`
- Image-Tags werden dynamisch von Skaffold injiziert (`setValueTemplates`)
- Port-Forwarding in `skaffold.yaml` definiert
- Profiles fuer spezialisierte Entwicklungs-Szenarien

---

## 11. Resource-Budgets

| Controller | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| **backend** | 250m | 1000m | 256Mi | 512Mi |
| **frontend** | 100m | 500m | 128Mi | 256Mi |
| **arangodb** | 250m | 1000m | 512Mi | 1Gi |

Dev-Overrides verwenden gelockerte Limits (siehe `values-dev.yaml`).

**Regeln:**
- Requests und Limits **immer** angeben
- CPU als Millicores (`250m`), Memory als MiB/GiB (`256Mi`)
- Dev-Limits grosszuegiger fuer Hot-Reload

---

## 12. Ingress

```yaml
# values-dev.yaml (Entwicklung)
ingress:
  main:
    enabled: true
    hosts:
      - host: kamerplanter.local
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

**Regeln:**
- Ingress in Produktion **deaktiviert** (extern konfiguriert)
- Dev-Ingress ueber `values-dev.yaml`
- Service-Referenz ueber `identifier` (bjw-s Pattern)
- `/api` → Backend, `/` → Frontend

---

## 13. Chart-Versionierung & Publishing

```yaml
# Chart.yaml
version: 0.2.1-dev   # Chart-Version (SemVer), develop-Kanal
appVersion: "1.0.0"  # App-Version
```

**Zwei Kanäle, und sie sind disjunkt.** Der develop-Baum trägt eine Version mit
dem Pre-Release-Bezeichner `dev` (derzeit `0.2.1-dev`); ein Release publiziert
unter einer reinen Version. Erzwungen ist nur der **Bezeichner**, nicht die
Zahl: `check_chart_develop_version.py` verlangt ein `dev`-Pre-Release, prüft
aber nicht, ob die Zahl der nächsten Version entspricht. Kein Turnus hebt sie
an, und sobald das gleichnamige Release erschienen ist, sortiert der
develop-Wert *unter* ihm. Das ist bewusst so — ein Wächter, der nach jedem
Release einen Handgriff verlangt, wird zur Pflichtübung, die ausfällt. Der Versions-Rewrite im
Release-Pfad ist an den Tag-Ref gebunden, ein develop-Push packt die
Chart-Version also wortwörtlich.

Trüge develop eine reine Version, überschriebe jeder `helm/**`-Merge den
OCI-Chart-Tag eines veröffentlichten Releases. Genau das ist passiert: der Tag
`0.2.0` wurde fünf Tage nach dem zugehörigen Release aus develop neu gebaut,
gemessen an seiner `org.opencontainers.image.created`-Annotation. <!-- #1222 -->

Zwei Prüfungen halten die Regel:

- `scripts/check_chart_develop_version.py` verlangt im required `static`-Lane,
  dass `helm/*/Chart.yaml` ein Pre-Release trägt, dessen erster Bezeichner
  `dev` ist.
- `scripts/ci/determine_chart_version.sh` weist ein Release-Tag ab, das `dev`
  als ersten Pre-Release-Bezeichner trägt. `-rc` und `-beta` bleiben erlaubt.

!!! warning "Ein Overlay zeigt nie auf den `-dev`-Kanal"

    Der develop-Tag wird bei jedem `helm/**`-Merge überschrieben — das ist sein
    Zweck. Ein Deployment, das `targetRevision` oder `--version` darauf richtet,
    folgt still dem jeweils letzten Merge.

**CI-Publishing:**
```bash
helm package helm/kamerplanter
helm push kamerplanter-0.2.1-dev.tgz oci://ghcr.io/<org>/charts/
```

- **SemVer** fuer Chart-Version
- OCI-Registry (GHCR) fuer Chart-Distribution
- GitHub Actions Pipeline fuer automatisches Publishing

---

## 14. Zusammenfassung der Pruefkette

```
Chart-Aenderung
    │
    ├─→ helm dependency build  → Dependencies aufloesen
    ├─→ helm lint              → Chart-Struktur, values.yaml Validierung
    ├─→ helm template          → Template-Rendering (Syntax-Fehler)
    ├─→ skaffold diagnose      → Skaffold-Config Validierung
    └─→ skaffold render        → Vollstaendige Manifest-Generierung
```

Alle Tools muessen in CI/CD **fehlerfrei** durchlaufen.

# Lokales Setup

Diese Seite beschreibt, wie du eine vollständige lokale Entwicklungsumgebung für Kamerplanter aufsetzt. Skaffold ist das einzige autorisierte Werkzeug für den Entwicklungsprozess — es übernimmt Image-Building und Deployment im Kubernetes-Cluster. Manuelle `docker build`- oder `kubectl apply`-Befehle werden nicht verwendet.

---

## Voraussetzungen

Installiere folgende Werkzeuge, bevor du beginnst:

| Werkzeug | Mindestversion | Zweck |
|----------|---------------|-------|
| [Docker](https://docs.docker.com/get-docker/) | 24+ | Container-Runtime für Kind |
| [Kind](https://kind.sigs.k8s.io/) | 0.20+ | Lokaler Kubernetes-Cluster |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | 1.28+ | Kubernetes CLI |
| [Skaffold](https://skaffold.dev/docs/install/) | 2.10+ | Build- und Deploy-Automatisierung |
| [Helm](https://helm.sh/docs/intro/install/) | 3.14+ | Kubernetes Package Manager |
| [asdf](https://asdf-vm.com/) | 0.14+ | Node.js-Versionsverwaltung |
| Python | 3.14+ | Backend-Entwicklung ohne Cluster |
| Node.js | 25.1.0 | Frontend-Entwicklung ohne Cluster |

!!! note "Node.js-Version via asdf"
    Im `src/frontend/`-Verzeichnis liegt eine `.tool-versions`-Datei mit `nodejs 25.1.0`. Nach der asdf-Installation wird die korrekte Version automatisch aktiviert:
    ```bash
    asdf plugin add nodejs
    asdf install
    ```

---

## Kind-Cluster erstellen

Das Repository enthält eine vorkonfigurierte Kind-Konfiguration mit drei Knoten (1 Control Plane, 2 Worker) und vordefinierten Port-Mappings:

```bash
kind create cluster --config kind-config.yaml --name kamerplanter
```

Der Cluster veröffentlicht auf dem Host-System nur die Ingress-Ports 80 und 443. Der Zugriff auf Backend (8000), Frontend (3000) und ArangoDB (8529) läuft über Skaffolds `--port-forward` (siehe Tabelle unten) — diese Host-Ports müssen beim Start also frei sein.

!!! warning "Bereits vorhandener Cluster"
    Falls ein Cluster mit dem Namen `kamerplanter` existiert, lösche ihn zunächst:
    ```bash
    kind delete cluster --name kamerplanter
    ```

Nach dem Erstellen prüfst du, ob `kubectl` auf den neuen Cluster zeigt:

```bash
kubectl cluster-info --context kind-kamerplanter
```

---

## Secret anlegen

Backend, Celery-Worker und die KI-Dienste referenzieren das Kubernetes-Secret `kamerplanter-secrets` per `envFrom` bzw. `secretKeyRef` (definiert in `helm/kamerplanter/values.yaml`). Die Dev-Overrides heben diese Referenz **nicht** auf, daher muss das Secret im Namespace `default` existieren, **bevor** du Skaffold startest — sonst bleiben die betroffenen Pods in `CreateContainerConfigError` hängen. `FERNET_KEY` und `ERASURE_TOMBSTONE_SALT` werden zusätzlich beim Backend-Start als Pflichtwerte geprüft (Fail-Fast).

Lege das Secret einmalig pro frisch erstelltem Cluster an:

```bash
kubectl create secret generic kamerplanter-secrets -n default \
  --from-literal=ARANGODB_PASSWORD=dein-sicheres-passwort \
  --from-literal=ARANGO_ROOT_PASSWORD=dein-sicheres-passwort \
  --from-literal=JWT_SECRET_KEY=dev-only-not-for-production-secret-key-1234 \
  --from-literal=POSTGRES_PASSWORD=foba123456 \
  --from-literal=VECTORDB_PASSWORD=foba123456 \
  --from-literal=FERNET_KEY=$(python3 -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())") \
  --from-literal=ERASURE_TOMBSTONE_SALT=$(openssl rand -hex 32) \
  --from-literal=INTERNAL_SERVICE_TOKEN=$(openssl rand -hex 32)
```

!!! note "FERNET_KEY-Format"
    `FERNET_KEY` muss ein gültiger Fernet-Schlüssel sein: **32 Bytes, url-safe base64-kodiert** (44 Zeichen) — genau das, was `cryptography.fernet.Fernet.generate_key()` erzeugt. Ein `openssl rand -hex 32` (64 Hex-Zeichen) ist **kein** gültiger Fernet-Schlüssel: Das Backend startet zwar, aber jeder verschlüsselnde Endpunkt scheitert später mit `ValueError: Fernet key must be 32 url-safe base64-encoded bytes`. Nur `FERNET_KEY` braucht dieses Format; `ERASURE_TOMBSTONE_SALT` und `INTERNAL_SERVICE_TOKEN` sind beliebige Zufallswerte.

!!! note "ArangoDB-Passwort"
    `ARANGODB_PASSWORD` und `ARANGO_ROOT_PASSWORD` müssen **denselben Wert** haben: ArangoDB initialisiert sein Root-Passwort aus `ARANGO_ROOT_PASSWORD`, während Backend und Celery sich mit `ARANGODB_PASSWORD` verbinden. Beide kommen ausschließlich aus diesem Secret — `values-dev.yaml` setzt sie **nicht** mehr inline. Weichen die Werte voneinander ab, scheitert der Backend-Start mit HTTP 401.

!!! warning "Nur für die lokale Entwicklung"
    Diese Werte sind bewusst schwach und gehören niemals in eine Produktivumgebung. Für Produktion und GitOps beschreibt das [ArgoCD-Deployment](../deployment/argocd.md) die sichere Secret-Verwaltung (Sealed Secrets, External Secrets Operator).

---

## Entwicklungsstart mit Skaffold

Skaffold baut die Container-Images lokal (ohne Push in eine Registry) und deployt sie per Helm ins Kind-Cluster. Dateiänderungen werden per `sync` direkt in laufende Container übertragen, ohne ein komplettes Rebuild.

### Vollstack starten

```bash
skaffold dev --trigger=manual --port-forward
```

Mit `--trigger=manual` erfolgt ein Rebuild nur, wenn du `r` drückst. Das verhindert ungewollte Neustarts bei schnellen Dateiänderungen. Skaffold aktiviert die Port-Weiterleitungen automatisch (siehe Tabelle unten).

### Nur Backend

```bash
skaffold dev --trigger=manual --port-forward -p backend-only
```

Das `backend-only`-Profil entfernt das Frontend-Artifact und dessen Port-Weiterleitung aus dem Build-Prozess.

### Nur Frontend

```bash
skaffold dev --trigger=manual --port-forward -p frontend-only
```

### Mit Debugger (debugpy)

```bash
skaffold debug --port-forward
```

Das `debug`-Profil aktiviert `DEBUGPY_ENABLED=true` als Build-Argument im Backend-Container. Der debugpy-Port `5678` ist dann erreichbar (siehe [Debugging](debugging.md)).

### Mit KI-Stack (RAG / Knowledge-Service)

```bash
# Hauptapp + KI-Stack gleichzeitig
skaffold dev --trigger=manual --port-forward -m kamerplanter,ki

# Nur KI-Stack (fuer RAG-Entwicklung)
skaffold dev --trigger=manual --port-forward -m ki
```

Das KI-Modul (`-m ki`) ist eine eigenstaendige Skaffold-Konfiguration im selben `skaffold.yaml`. Es deployt Knowledge-Service (Port `8090`), Embedding-Service (Port `8080`) und VectorDB/TimescaleDB (Port `5433`) unabhaengig von der Hauptapplikation. Weitere Details unter [Infrastruktur — KI-Modul](../architecture/infrastructure.md#ki-modul).

---

## Port-Weiterleitungen

Skaffold leitet folgende Ports automatisch weiter, sobald `--port-forward` gesetzt ist:

| Service | Lokaler Port | Ziel im Cluster | Modul |
|---------|-------------|-----------------|-------|
| Frontend | `3000` | Vite-Dev-Server auf `5173` | kamerplanter |
| Backend API | `8000` | FastAPI auf `8000` | kamerplanter |
| ArangoDB Web-UI | `8529` | ArangoDB auf `8529` | kamerplanter |
| Home Assistant | `8123` | Home Assistant auf `8123` | kamerplanter |
| VectorDB (TimescaleDB) | `5433` | TimescaleDB auf `5432` | ki |
| Knowledge-Service | `8090` | Knowledge-Service auf `8000` | ki |
| Embedding-Service | `8080` | Embedding-Service auf `8080` | ki |

!!! tip "API-Dokumentation"
    Nach dem Start ist die automatisch generierte Swagger-UI unter [http://localhost:8000/docs](http://localhost:8000/docs) erreichbar. ReDoc ist unter [http://localhost:8000/redoc](http://localhost:8000/redoc) verfügbar.

---

## Demo-Zugangsdaten

Der Backend-Container führt beim ersten Start automatisch Seed-Skripte aus. Danach steht ein Demo-Benutzer bereit:

| Feld | Wert |
|------|------|
| E-Mail | `demo@kamerplanter.local` |
| Passwort | `demo-passwort-2024` |
| Tenant-Slug | `demo` |

---

## Backend lokal ohne Kubernetes

Für reine Backend-Entwicklung ohne Cluster-Overhead kannst du den FastAPI-Server direkt starten. Voraussetzung ist eine laufende ArangoDB-Instanz (z. B. per Docker Compose).

```bash
# ArangoDB und Redis mit Docker Compose starten
docker-compose up -d arangodb valkey

# Python-Abhängigkeiten aus dem Lock installieren (uv: https://docs.astral.sh/uv/)
cd src/backend
uv sync --locked --extra dev
source .venv/bin/activate

# Umgebungsvariablen setzen
export ARANGODB_HOST=localhost
export ARANGODB_PORT=8529
export ARANGODB_DATABASE=kamerplanter
export ARANGODB_USERNAME=root
export ARANGODB_PASSWORD=rootpassword
export REDIS_URL=redis://localhost:6379/0
export DEBUG=true
export REQUIRE_EMAIL_VERIFICATION=false

# Server starten
uvicorn app.main:app --reload --port 8000
```

!!! note "Hot-Reload"
    `uvicorn --reload` überwacht alle `.py`-Dateien im `app/`-Verzeichnis und startet den Server bei Änderungen automatisch neu. Im Kind-Cluster übernimmt Skaffold diese Aufgabe über den `sync`-Mechanismus.

---

## Frontend lokal ohne Kubernetes

Der Vite-Dev-Server kann unabhängig vom Cluster laufen. Er proxyt alle `/api`-Anfragen an das Backend (Standard: `http://127.0.0.1:8000`).

```bash
cd src/frontend
npm install
npm run dev
```

Der Dev-Server startet auf Port `5173`. Die Backend-URL kann über die Umgebungsvariable `VITE_BACKEND_URL` überschrieben werden:

```bash
VITE_BACKEND_URL=http://localhost:8000 npm run dev
```

---

## Home Assistant Integration

Die HA-Integration in `custom_components/kamerplanter/` wird **nicht** automatisch von Skaffold deployed. Nach Änderungen an den HA-Integrationsdateien muss der Inhalt manuell in den laufenden Pod kopiert werden:

```bash
# Dateien in den Pod kopieren
kubectl cp custom_components/kamerplanter/ \
  default/homeassistant-0:/config/custom_components/kamerplanter/

# Python-Cache löschen (MUSS immer gemacht werden, sonst lädt HA alten Bytecode)
kubectl exec default/homeassistant-0 -- \
  rm -rf /config/custom_components/kamerplanter/__pycache__

# HA-Prozess neustarten (NICHT kubectl delete pod!)
# kill 1 startet nur den Container neu — InitContainers laufen NICHT erneut,
# d.h. die per kubectl cp kopierten Dateien bleiben erhalten.
kubectl exec homeassistant-0 -n default -- kill 1
```

---

## Fehlerbehebung

??? question "Skaffold findet den Kind-Cluster nicht"
    Stelle sicher, dass der kubectl-Kontext korrekt gesetzt ist:
    ```bash
    kubectl config use-context kind-kamerplanter
    ```

??? question "Backend-Pod startet nicht (CrashLoopBackOff)"
    Sieh dir die Pod-Logs an:
    ```bash
    kubectl logs -l app=kamerplanter-backend --tail=50
    ```
    Häufige Ursache: ArangoDB ist noch nicht bereit. Die Liveness-Probe wartet bis zu 150 Sekunden (`initialDelaySeconds: 30`, `failureThreshold: 10`).

??? question "Port 8000 oder 3000 ist belegt"
    Beende alle Prozesse auf dem betreffenden Port:
    ```bash
    lsof -ti:8000 | xargs kill -9
    ```

??? question "Seed-Daten fehlen nach Neustart"
    Die Seed-Skripte laufen nur beim ersten Start oder wenn die ArangoDB-Datenbank neu erstellt wird. Um die Seeds erneut auszuführen:
    ```bash
    kubectl exec -it deployment/kamerplanter-backend -- \
      python -m app.migrations.seed_auth
    ```

## Siehe auch

- [Code-Standards](code-standards.md)
- [Testen](testing/index.md)
- [Debugging](debugging.md)

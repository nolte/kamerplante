---
ID: TECH-STACK-001
Titel: Technologie-Stack & Architektur-Entscheidungen
Kategorie: Architektur / Infrastructure
Fokus: Beides
Technologie: Python 3.14, FastAPI, ArangoDB, Kubernetes, Helm
Status: Produktionsreif Priorität: Kritisch
---

# TECH-STACK-001: Technologie-Stack & Architektur-Entscheidungen

## 1. Übersicht

### 1.1 Systemarchitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Web App    │  │  Mobile App  │  │ IoT Devices  │         │
│  │   (React)    │  │  (Flutter)   │  │   (MQTT)     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/WSS
┌────────────────────────▼────────────────────────────────────────┐
│                     API GATEWAY LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Traefik    │  │  Kong (opt)  │  │ Rate Limiter │         │
│  │   Ingress    │  │  API Gateway │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   FastAPI    │  │    Celery    │  │   GraphQL    │         │
│  │   Backend    │  │   Workers    │  │  (Optional)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   ArangoDB   │  │ TimescaleDB  │  │    Valkey    │         │
│  │ Multi-Model  │  │  Time-Series │  │    Cache     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    AI / RAG LAYER (optional)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   pgvector   │  │  Embedding   │  │ LLM Adapter  │         │
│  │ PostgreSQL18 │  │ Service(ONNX)│  │ (Anthropic / │         │
│  │  VectorDB    │  │   E5-base    │  │ Ollama/vLLM) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Backend-Stack (Python)

### 2.1 Core Framework

#### FastAPI (Primary)

- **Version**: >= 0.115.0
- **Python Version**: >= 3.14
- **Begründung**:
    - Automatische OpenAPI-Dokumentation
    - Native async/await Support
    - Pydantic Integration für Type Safety
    - Hohe Performance (Starlette + uvloop)
    - WebSocket Support für Real-Time Features

**Installation**:

```bash
pip install fastapi[all]==0.109.0
```

**Kernfeatures**:

```python
# backend/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB-Connections, Cache, etc.
    await init_database()
    await init_cache()
    yield
    # Shutdown: Cleanup
    await close_database()
    await close_cache()

app = FastAPI(
    title="Agrotech Plant Care API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.agrotech.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### 2.2 Python 3.14 Features & Vorteile

#### Neue Features für Agrotech

**1. Improved Type System (PEP 702)**:

```python
# backend/models/plant.py
from typing import TypedDict, NotRequired

class PlantMetadata(TypedDict):
    """Flexible Metadaten mit optionalen Feldern"""
    strain_name: str
    breeder: NotRequired[str]  # Optional ohne | None
    seed_batch: NotRequired[str]
    terpene_profile: NotRequired[dict[str, float]]

def update_plant_metadata(plant_id: str, metadata: PlantMetadata) -> None:
    """Type-safe Metadaten-Update"""
    # TypedDict erzwingt korrekte Keys
    ...
```

**2. PEP 695: Type Parameter Syntax**:

```python
# backend/repositories/base.py
from collections.abc import Sequence

class Repository[T]:
    """Generic Repository Pattern mit neuer Syntax"""

    def get_by_id(self, id: str) -> T | None:
        ...

    def list_all(self) -> Sequence[T]:
        ...

class PlantRepository(Repository[Plant]):
    """Plant-spezifisches Repository"""
    pass
```

**3. Performance-Verbesserungen**:

- **JIT Compilation**: Bis zu 20% schneller für rechenintensive Tasks (GDD-Berechnungen)
- **Improved GC**: Besseres Memory-Management für Long-Running Services
- **Faster asyncio**: Wichtig für FastAPI High-Throughput

**4. Better Error Messages**:

```python
# Alte Fehlermeldung (3.11):
# TypeError: 'int' object is not subscriptable

# Neue Fehlermeldung (3.14):
# TypeError: 'int' object is not subscriptable
#   Did you mean to use '[]' with a list or dict instead?
#   Note: gdd_accumulated is of type int (line 42)
```

#### Dockerfile für Python 3.14

```dockerfile
# backend/Dockerfile
FROM python:3.14-slim AS builder

WORKDIR /build

# System-Dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python-Dependencies — aus dem Lock, hash-verifiziert (NFR-009 §2.3)
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

# Runtime Stage
FROM python:3.14-slim

# Non-root User
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application
COPY --chown=appuser:appuser . .

# Set PATH
ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser

EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 2.2 Datenvalidierung & Serialisierung

#### Pydantic v2

- **Version**: >= 2.5.0
- **Verwendung**: Request/Response Schemas, Config Management

```python
# backend/schemas/plant.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from uuid import UUID

class PlantCreate(BaseModel):
    species_id: UUID = Field(..., description="Species UUID")
    location_id: UUID = Field(..., description="Location UUID")
    planted_date: date = Field(default_factory=date.today)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "species_id": "550e8400-e29b-41d4-a716-446655440000",
                "location_id": "660e8400-e29b-41d4-a716-446655440001",
                "planted_date": "2026-02-25"
            }
        }
    )

class PlantResponse(BaseModel):
    id: UUID
    species_name: str
    current_phase: str
    gdd_accumulated: float

    model_config = ConfigDict(from_attributes=True)
```

### 2.3 Asynchrone Task-Verarbeitung

#### Celery + Valkey

- **Celery**: >= 5.4.0
- **Valkey**: >= 8.0 (primäre Lösung, als Broker & Result Backend) — Wire-Protokoll-kompatibel zu Redis, daher wird der Standard-Python-Client `redis-py` verwendet. Helm-Charts (NFR-002) deployen Valkey-Images. <!-- W-008 -->
- **Hinweis:** In Code-Beispielen, Variablennamen und Library-Imports bleibt der Begriff "redis" erhalten, weil `redis-py` der maintainede Python-Client ist und Valkey via Redis-Wire-Protocol bedient. Die Tech-Stack-Entscheidung Valkey betrifft die deployte Server-Komponente, nicht die Client-Library.

**Use Cases**:

- Zeitgesteuerte Bewässerung
- GDD-Batch-Berechnungen
- Email-Benachrichtigungen
- Report-Generierung
- Sensor-Daten-Aggregation

```python
# backend/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "agrotech",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1"
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Berlin",
    enable_utc=True,
    beat_schedule={
        "check-irrigation-needs": {
            "task": "tasks.irrigation.check_all_plants",
            "schedule": crontab(minute="*/15"),  # Alle 15 Minuten
        },
        "calculate-daily-gdd": {
            "task": "tasks.gdd.calculate_daily",
            "schedule": crontab(hour=1, minute=0),  # 01:00 Uhr
        },
    }
)

# backend/tasks/irrigation.py
from celery_app import celery_app
from services.irrigation import IrrigationService

@celery_app.task(name="tasks.irrigation.check_all_plants")
def check_irrigation_needs():
    """Prüft alle Pflanzen auf Bewässerungsbedarf"""
    service = IrrigationService()
    results = service.check_all_plants()
    return {
        "checked": len(results),
        "needs_water": sum(1 for r in results if r.needs_irrigation)
    }
```

### 2.4 API-Dokumentation

#### OpenAPI / Swagger UI

- **Automatisch generiert** durch FastAPI
- **Endpoint**: `/api/docs` (Swagger UI)
- **Endpoint**: `/api/redoc` (ReDoc)

```python
# Erweiterte Metadaten
app = FastAPI(
    title="Agrotech Plant Care API",
    description="""
    ## Pflanzen Pflege & Ernte Helfer API

    Verwaltet:
    - 🌱 Pflanzen-Lifecycle (Keimung bis Ernte)
    - 💧 Bewässerungsmanagement
    - 🌡️ Klimadaten & VPD-Optimierung
    - 🐛 Integriertes Pest Management (IPM)
    - 📊 Ernteprognosen & Analysen
    """,
    version="1.0.0",
    contact={
        "name": "Agrotech Support",
        "email": "support@agrotech.example.com"
    },
    license_info={
        "name": "Proprietary"
    }
)
```

---

## 3. Datenbank-Stack

### 3.1 ArangoDB (Multi-Model Database)

#### Version & Deployment

- **Version**: >= 3.11
- **Edition**: Community Edition (für Production: Enterprise empfohlen)
- **Deployment**: StatefulSet in Kubernetes

#### Datenmodelle

**1. Document Collections** (wie NoSQL):

```javascript
// Species Collection
db._create("species");
db.species.save({
    _key: "tomato_brandywine",
    scientific_name: "Solanum lycopersicum",
    common_name: "Brandywine Tomato",
    lifecycle_type: "annual",
    base_temp_c: 10,
    optimal_temp_range: [18, 27],
    photoperiod_type: "day_neutral",
    gdd_to_harvest: 2400
});
```

**2. Graph (Relationships)**:

```javascript
// Edge Collections
db._createEdgeCollection("located_in");
db._createEdgeCollection("requires_nutrient");
db._createEdgeCollection("incompatible_with");

// Pflanze → Standort
db.located_in.save({
    _from: "plants/plant_001",
    _to: "locations/greenhouse_a_slot_12",
    planted_date: "2026-02-25"
});

// Mischkultur-Inkompatibilität
db.incompatible_with.save({
    _from: "species/tomato_brandywine",
    _to: "species/potato_russet",
    reason: "Solanaceae family - disease transmission risk",
    allelopathy_score: -0.8
});
```

**3. AQL Graph Traversals**:

```javascript
// Finde alle Pflanzen in einem Gewächshaus mit Nachbarschafts-Graph
FOR plant IN plants
    FILTER plant.active == true
    LET location = FIRST(
        FOR v IN 1..1 OUTBOUND plant located_in
            RETURN v
    )
    FILTER location.site_name == "Greenhouse A"

    LET neighbors = (
        FOR v, e IN 1..1 ANY location._id neighbor_of
            FOR p IN 1..1 INBOUND v located_in
                RETURN {
                    plant: p,
                    distance_cm: e.distance_cm
                }
    )

    RETURN {
        plant: plant,
        location: location,
        neighbors: neighbors
    }
```

#### Vorteile für Agrotech

- **Multi-Model**: Documents + Graphs + Key-Value in einer DB
- **AQL**: SQL-ähnliche Syntax, einfacher als Cypher
- **Flexible Schema**: Perfekt für evolvierende Pflanzen-Metadaten
- **Graph-Queries**: Mischkultur, Fruchtfolge, Standort-Hierarchien
- **Performance**: Schnelle Aggregationen für Sensordaten

#### ArangoDB-Konfiguration

```yaml
# k8s/arangodb-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: arangodb
spec:
  serviceName: arangodb
  replicas: 3  # Cluster-Modus für HA
  template:
    spec:
      containers:
      - name: arangodb
        image: arangodb:3.11
        env:
        - name: ARANGO_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: arangodb-credentials
              key: password
        - name: ARANGO_STORAGE_ENGINE
          value: "rocksdb"
        ports:
        - containerPort: 8529
        volumeMounts:
        - name: data
          mountPath: /var/lib/arangodb3
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

### 3.2 TimescaleDB (Zeit-Reihen für Sensordaten)

#### Version & Purpose

- **Version**: >= 2.13 (PostgreSQL 16 Extension)
- **Verwendung**: Sensor-Readings (Temp, Humidity, pH, EC, PPFD)

#### Schema-Design

```sql
-- Hypertable für Sensor-Readings
CREATE TABLE sensor_readings (
    time        TIMESTAMPTZ NOT NULL,
    location_id UUID NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(20),
    source      VARCHAR(50) DEFAULT 'manual', -- 'auto', 'manual', 'homeassistant'
    metadata    JSONB
);

-- Konvertiere zu Hypertable (automatisches Partitionieren)
SELECT create_hypertable('sensor_readings', 'time');

-- Indizes
CREATE INDEX ON sensor_readings (location_id, time DESC);
CREATE INDEX ON sensor_readings (sensor_type, time DESC);

-- Automatische Aggregation (Continuous Aggregates)
CREATE MATERIALIZED VIEW sensor_readings_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    location_id,
    sensor_type,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    COUNT(*) AS num_readings
FROM sensor_readings
GROUP BY bucket, location_id, sensor_type;

-- Auto-Refresh Policy
SELECT add_continuous_aggregate_policy('sensor_readings_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Retention Policy (behalte Rohdaten für 90 Tage)
SELECT add_retention_policy('sensor_readings', INTERVAL '90 days');
```

#### Use Cases

- **Minutengenaue Sensor-Logs** (Temperatur, Luftfeuchtigkeit)
- **VPD-Berechnungen** über Zeiträume
- **Trendanalysen** (Wachstumsverlauf)
- **Anomalie-Erkennung** (Sensor-Ausfall, Extremwerte)

### 3.3 Valkey (Cache & Session Store)

#### Version & Verwendung

- **Version**: Valkey >= 8.0 (primäre Lösung, Redis-Wire-Protokoll-kompatibel, NFR-012 §3.4) <!-- W-008 -->
- **Modi**:
    - Cache (TTL-basiert)
    - Session Store
    - Celery Broker/Backend
    - Rate Limiting Counter

```python
# backend/cache/redis_client.py
from redis.asyncio import Redis
from typing import Optional
import json

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def get_plant(self, plant_id: str) -> Optional[dict]:
        """Hole Pflanze aus Cache"""
        data = await self.redis.get(f"plant:{plant_id}")
        return json.loads(data) if data else None

    async def set_plant(self, plant_id: str, plant_data: dict, ttl: int = 300):
        """Speichere Pflanze im Cache (5 Minuten TTL)"""
        await self.redis.setex(
            f"plant:{plant_id}",
            ttl,
            json.dumps(plant_data)
        )

    async def invalidate_plant(self, plant_id: str):
        """Lösche Cache bei Updates"""
        await self.redis.delete(f"plant:{plant_id}")

    # Rate Limiting
    async def check_rate_limit(self, user_id: str, limit: int = 100) -> bool:
        """100 Requests pro Minute"""
        key = f"rate_limit:{user_id}:{int(time.time() // 60)}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)
        return count <= limit
```

### 3.4 KI/AI-Stack (RAG-basierte Wissensdatenbank)

#### Übersicht

Kamerplanter enthält eine optionale KI-Komponente zur Beantwortung von Pflanzenpflege-Fragen. Die Architektur folgt dem **RAG-Pattern** (Retrieval-Augmented Generation): Nutzerfragen werden semantisch in einer Vektor-Datenbank gesucht, relevante Wissens-Chunks als Kontext an ein LLM übergeben, und die Antwort wird mit Quellenangaben zurückgegeben.

```
┌──────────────────────────────────────────────────────────────────┐
│                        RAG PIPELINE                               │
│                                                                    │
│  Nutzer-Frage                                                      │
│       │                                                            │
│       ▼                                                            │
│  ┌────────────────┐    ┌────────────────────┐                     │
│  │   Embedding    │───▶│   pgvector Search  │                     │
│  │   Service      │    │   (Cosine Sim.)    │                     │
│  │   (ONNX RT)    │    │   PostgreSQL 18    │                     │
│  └────────────────┘    └────────┬───────────┘                     │
│                                 │ Top-K Chunks                     │
│                                 ▼                                  │
│                        ┌────────────────┐                         │
│                        │  LLM Adapter   │                         │
│                        │  (Anthropic /  │                         │
│                        │   Ollama /     │                         │
│                        │   OpenAI-comp.)│                         │
│                        └────────┬───────┘                         │
│                                 │                                  │
│                                 ▼                                  │
│                        Antwort + Quellen                           │
└──────────────────────────────────────────────────────────────────┘
```

Alle KI-Komponenten sind **optional** — das System funktioniert vollständig ohne aktivierte VectorDB/LLM. Die API liefert HTTP 503 wenn der Knowledge Service nicht verfügbar ist.

#### 3.4.1 VectorDB (PostgreSQL + pgvector)

- **Basis**: PostgreSQL >= 18 (Bookworm)
- **Extension**: pgvector 0.8.2
- **Embedding-Dimensionen**: 768 (multilingual-e5-base, siehe ADR-006)
- **Index**: HNSW mit Cosine-Distanz (`vector_cosine_ops`)
- **Hybrid Search**: Reciprocal Rank Fusion (RRF) — kombiniert Vektor-Similarity (Cosine) mit Full-Text-Search (BM25 via PostgreSQL `tsvector`). Default-Gewichtung: 0.5 Vektor / 0.5 Text
- **Docker**: Custom Image (`docker/vectordb/Dockerfile`) basierend auf `postgres:18-bookworm`
- **Docker Compose Profile**: `vectordb` (opt-in)

**Schema**:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE ai_vector_chunks (
    id          SERIAL PRIMARY KEY,
    source_key  TEXT NOT NULL UNIQUE,      -- '{category}/{file}#{chunk_id}'
    source_type TEXT NOT NULL,             -- 'care_rule'
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding    vector(768) NOT NULL,
    search_text  tsvector GENERATED ALWAYS AS (to_tsvector('german', title || ' ' || content)) STORED,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_chunks_embedding
    ON ai_vector_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_ai_chunks_search_text
    ON ai_vector_chunks USING gin (search_text);
```

**Migrations**: Automatisch via `VectorDbConnection` + `schema.py` (Tracking-Tabelle `schema_migrations`).

#### 3.4.2 Embedding Service

- **Runtime**: ONNX Runtime >= 1.20 (CPU-only, kein PyTorch)
- **Tokenizer**: HuggingFace Transformers >= 4.46 (nur Tokenizer, kein Torch)
- **Primärmodell**: `multilingual-e5-base` (768 Dimensionen, multilingual DE/EN, siehe ADR-006)
- **Fallback-Modell**: `multilingual-e5-small` (384 Dimensionen, multilingual, für ressourcenarme Umgebungen)
- **E5-Prefix-Konvention**: Queries mit `"query: "` Prefix, Dokumente mit `"passage: "` Prefix
- **API**: FastAPI-Microservice auf Port 8080 (`/embed`, `/health`, `/ready`)
- **Pooling**: Mean Pooling + L2-Normalisierung
- **Max Token Length**: 512 (Truncation)
- **Docker**: `docker/embedding-service/Dockerfile` (Python 3.14-slim)
- **Deployment**: Kubernetes via Helm (optional, `embedding-service` Controller)

```python
# Embedding-Aufruf (Backend → Embedding Service)
embedding_engine = EmbeddingEngine(
    service_url="http://kamerplanter-embedding-service:8080",
    model_name="multilingual-e5-base",
)
vector = embedding_engine.embed("query: Stickstoffmangel erkennen")  # → list[float], len=768
```

**Begründung ONNX statt PyTorch**:
- ~10x kleineres Docker Image (kein 2 GB PyTorch)
- Schnellerer Kaltstart (Modell in ~2s geladen)
- CPU-optimiert, keine GPU erforderlich
- Ausreichend für Batch-Ingestion und On-Demand-Queries

#### 3.4.3 LLM-Adapter (Multi-Provider)

Das System unterstützt drei LLM-Provider über ein gemeinsames Interface (`ILlmAdapter`). Die Adapter leben in `data_access/external/` gemäß NFR-001 Schichtenarchitektur.

| Adapter | Provider | Modell (Default) | Einsatz |
|---------|----------|-------------------|---------|
| `AnthropicLlmAdapter` | Anthropic Messages API | `claude-sonnet-4-20250514` | Cloud, höchste Qualität |
| `OllamaLlmAdapter` | Ollama (lokal) | `llama3` | Self-hosted, Privacy-First |
| `OpenAiCompatibleLlmAdapter` | OpenAI / vLLM / LM Studio / llama.cpp | `gpt-4o-mini` | Flexibel, jeder OpenAI-kompatible Endpunkt |

**Interface**:

```python
class ILlmAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> LlmResponse: ...
```

**Begründung Multi-Provider**:
- **Privacy**: Ollama-Adapter ermöglicht vollständig lokale Verarbeitung (DSGVO-konform ohne Cloud-Abhängigkeit)
- **Flexibilität**: OpenAI-kompatibler Adapter unterstützt beliebige Inferenz-Server (vLLM, LM Studio, llama.cpp)
- **Qualität**: Anthropic-Adapter für höchste Antwortqualität bei Cloud-Einsatz
- **Keine SDK-Abhängigkeit**: Alle Adapter nutzen `httpx` direkt (kein `anthropic`/`openai` SDK)

#### 3.4.4 Knowledge Base (Wissens-YAML)

Die Wissensdatenbank besteht aus ~30 kuratierten YAML-Dateien unter `spec/knowledge/rag/`, organisiert nach Fachbereichen:

```
spec/knowledge/rag/
├── allgemein/          # Anfänger-Tipps, Fehler vermeiden, Ertragsoptimierung
├── bewaesserung/       # Gießstrategien, Wasserqualität, Überwässerung
├── diagnostik/         # Nährstoffmangel, pH/EC-Abweichungen, Schädlinge, Pilzkrankheiten
├── duengung/           # EC-Management, CalMag, PK-Boost, Mischsicherheit, organisch
├── outdoor/            # Fruchtfolge, Mischkultur, Saisonplanung, Wetter
├── phasen/             # Keimung, Vegetativ, Blüte, Ernte, Überwintern
├── umwelt/             # Licht, VPD, CO2, Luftzirkulation, Temperatur, Growzelt
└── eval/               # Benchmark-Fragen, Topic-Synonyme (RAG-Evaluation)
```

**YAML-Format** (pre-chunked):

```yaml
category: diagnostik
tags: [naehrstoffmangel, blaetter, symptome]
expertise_level: [beginner, intermediate, expert]
applicable_phases: [vegetative, flowering]
chunks:
  - id: nitrogen-deficiency
    title: "Stickstoffmangel (N) erkennen"
    content: "Symptome: Untere Blätter werden gleichmäßig hellgrün..."
    metadata:
      nutrient: nitrogen
      symbol: "N"
      deficiency_type: mobile
```

**Ingestion-Pipeline**:
1. `KnowledgeIngestor` liest alle YAML-Dateien aus dem Knowledge-Verzeichnis
2. Chunks werden mit Metadaten-Anreicherung als Embed-Text aufbereitet
3. Batch-Embedding über den Embedding Service
4. Batch-Upsert in pgvector (`source_key` als Unique Constraint)
5. Celery Beat Task (`reindex_vector_chunks`) läuft wöchentlich

#### 3.4.5 RAG-Service (Knowledge Service)

Der `KnowledgeService` orchestriert die gesamte RAG-Pipeline:

1. **Semantic Search** (`/api/v1/knowledge/search`): Query → Embedding → pgvector Cosine Similarity → Top-K Chunks
2. **RAG Ask** (`/api/v1/knowledge/ask`): Search + LLM-Generierung mit Kontext-Prompt

**System-Prompt-Regeln**:
- Antwort in der Sprache der Frage (DE/EN)
- Nur Kontext-basierte Antworten (kein Halluzinieren)
- Quellenangabe in Klammern
- Technische Werte mit Einheiten und Bereichen

**API-Endpunkte**:

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/knowledge/search?q=...&top_k=5` | Semantische Suche (Chunks) |
| POST | `/api/v1/knowledge/ask` | RAG-Frage-Antwort mit LLM |

Beide Endpunkte sind **öffentlich** (keine JWT-Authentifizierung erforderlich).

#### 3.4.6 RAG Evaluation

Unter `tools/rag-eval/` liegt ein Evaluierungs-Framework:

- **Benchmark-Fragen**: `spec/rag-eval/benchmark_questions.yaml` mit erwarteten Themen/Quellen
- **Topic-Synonyme**: `spec/rag-eval/topic_synonyms.yaml` für Retrieval-Qualitätsmessung
- **Eval-Script**: `tools/rag-eval/eval_rag.py` — automatisierte Qualitätsprüfung der RAG-Pipeline
- **Notebook**: `tools/rag-eval/rag_eval.ipynb` — interaktive Analyse und Visualisierung

#### 3.4.7 Abhängigkeiten (Python)

| Paket | Version | Zweck |
|-------|---------|-------|
| `httpx` | >= 0.28 | HTTP-Client für LLM- und Embedding-Aufrufe |
| `psycopg[binary]` | >= 3.2 | PostgreSQL-Treiber für pgvector |
| `psycopg_pool` | >= 3.2 | Connection Pooling für VectorDB |
| `onnxruntime` | >= 1.20 | ONNX-Inferenz (nur Embedding Service) |
| `transformers` | >= 4.46 | Tokenizer (nur Embedding Service, ohne PyTorch) |
| `numpy` | latest | Numerische Operationen (Embedding Service) |
| `sentencepiece` | latest | Tokenizer-Backend für multilinguales Modell |

---

## 4. Frontend-Stack

### 4.1 Web-Application

#### React 19 + TypeScript

- **React**: >= 19.0.0
- **TypeScript**: >= 5.9
- **Build Tool**: Vite >= 6.4

**Projektstruktur**:

```
frontend/
├── src/
│   ├── components/       # UI Components
│   │   ├── plants/
│   │   ├── dashboard/
│   │   └── shared/
│   ├── features/         # Feature-basierte Organisation
│   │   ├── irrigation/
│   │   ├── harvest/
│   │   └── ipm/
│   ├── hooks/            # Custom React Hooks
│   ├── services/         # API Client
│   ├── store/            # State Management (Redux Toolkit)
│   ├── types/            # TypeScript Definitions
│   └── utils/
├── package.json
└── vite.config.ts
```

#### State Management: Redux Toolkit

```typescript
// src/store/plantsSlice.ts
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { apiClient } from '../services/api';

interface Plant {
  id: string;
  species_name: string;
  current_phase: string;
  gdd_accumulated: number;
}

interface PlantsState {
  items: Plant[];
  loading: boolean;
  error: string | null;
}

export const fetchPlants = createAsyncThunk(
  'plants/fetchAll',
  async (locationId: string) => {
    const response = await apiClient.get(`/plants?location_id=${locationId}`);
    return response.data;
  }
);

const plantsSlice = createSlice({
  name: 'plants',
  initialState: {
    items: [],
    loading: false,
    error: null
  } as PlantsState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchPlants.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchPlants.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(fetchPlants.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch plants';
      });
  }
});

export default plantsSlice.reducer;
```

#### UI-Bibliothek: Material-UI (MUI)

```bash
npm install @mui/material @emotion/react @emotion/styled
```

```typescript
// src/components/plants/PlantCard.tsx
import { Card, CardContent, Chip, Typography } from '@mui/material';
import { LocalFlorist, WaterDrop } from '@mui/icons-material';

interface PlantCardProps {
  plant: Plant;
}

export const PlantCard: React.FC<PlantCardProps> = ({ plant }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6">
          <LocalFlorist /> {plant.species_name}
        </Typography>
        <Chip
          label={plant.current_phase}
          color={getPhaseColor(plant.current_phase)}
          size="small"
        />
        <Typography variant="body2" color="text.secondary">
          GDD: {plant.gdd_accumulated.toFixed(0)}
        </Typography>
      </CardContent>
    </Card>
  );
};
```

### 4.2 Mobile Application (Optional)

#### Flutter

- **Version**: >= 3.16
- **Begründung**: Cross-Platform (iOS + Android), native Performance

```dart
// lib/services/api_client.dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  final String baseUrl = 'https://api.agrotech.example.com';
  final String _token;

  ApiClient(this._token);

  Future<List<Plant>> fetchPlants(String locationId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/plants?location_id=$locationId'),
      headers: {'Authorization': 'Bearer $_token'}
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Plant.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load plants');
    }
  }
}

// lib/models/plant.dart
class Plant {
  final String id;
  final String speciesName;
  final String currentPhase;
  final double gddAccumulated;

  Plant({
    required this.id,
    required this.speciesName,
    required this.currentPhase,
    required this.gddAccumulated
  });

  factory Plant.fromJson(Map<String, dynamic> json) {
    return Plant(
      id: json['id'],
      speciesName: json['species_name'],
      currentPhase: json['current_phase'],
      gddAccumulated: json['gdd_accumulated'].toDouble()
    );
  }
}
```

---

## 5. DevOps & Infrastructure

### 5.1 Container-Orchestrierung: Kubernetes

#### K8s-Version

- **Version**: >= 1.28
- **Distribution**:
    - **Entwicklung**: k3s / Minikube
    - **Produktion**: EKS (AWS) / GKE (Google) / AKS (Azure)

#### Namespace-Struktur

```yaml
# k8s/namespaces.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agrotech-prod
---
apiVersion: v1
kind: Namespace
metadata:
  name: agrotech-staging
---
apiVersion: v1
kind: Namespace
metadata:
  name: agrotech-dev
```

#### Helm Chart Management

##### BJW-S Common Library Chart

- **Repository**: https://github.com/bjw-s-labs/helm-charts
- **Chart**: `library/common` (v3.x)
- **Begründung**:
    - Wiederverwendbare Templates für Deployments, Services, Ingress
    - Best Practices für Kubernetes Manifests
    - Reduktion von YAML-Duplikation
    - Community-maintained, production-ready

**Installation der Common Library**:

```bash
# Helm Repository hinzufügen
helm repo add bjw-s https://bjw-s.github.io/helm-charts
helm repo update

# Chart-Abhängigkeit prüfen
helm search repo bjw-s/common
```

**bjw-s/common Library Features**:

Die bjw-s/common Library bietet vordefinierte Templates für:

1. **Controller Types**:

    - `deployment` - Standard Kubernetes Deployment
    - `statefulset` - Für zustandsbehaftete Applikationen
    - `daemonset` - Auf jedem Node
    - `cronjob` - Zeitgesteuerte Jobs
2. **Service Types**:

    - `ClusterIP` - Interner Service
    - `LoadBalancer` - Externer Zugriff
    - `NodePort` - Port auf jedem Node
    - `ExternalName` - DNS-Alias
3. **Ingress Management**:

    - Automatische TLS-Konfiguration
    - Multiple Hosts/Paths
    - Annotation-basierte Middleware
4. **Persistence**:

    - `persistentVolumeClaim` - Standard PVC
    - `emptyDir` - Temporärer Speicher
    - `configMap` / `secret` - Als Volume
    - `hostPath` - Node-lokaler Pfad
5. **ConfigMaps & Secrets**:

    - Automatische Creation aus values
    - Environment-Variable-Injection
    - File-Mounting
6. **Probes & Health Checks**:

    - Liveness Probes
    - Readiness Probes
    - Startup Probes
7. **Autoscaling**:

    - HPA (Horizontal Pod Autoscaler)
    - VPA (Vertical Pod Autoscaler) Support
8. **Security**:

    - ServiceAccounts
    - PodSecurityContext
    - SecurityContext (Container-level)
    - NetworkPolicies

**Beispiel: Minimales Chart mit bjw-s/common**:

```yaml
# Chart.yaml
dependencies:
  - name: common
    repository: https://bjw-s.github.io/helm-charts
    version: 3.0.0

# values.yaml (minimal)
controllers:
  main:
    containers:
      main:
        image:
          repository: nginx
          tag: latest

service:
  main:
    controller: main
    ports:
      http:
        port: 80
```

Dies generiert automatisch:

- Deployment mit Nginx
- ClusterIP Service
- Alle Best Practices (Labels, Selectors, etc.)

**Projektstruktur für Helm Charts**:

```
helm/
├── agrotech-backend/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-staging.yaml
│   ├── values-prod.yaml
│   └── templates/
│       ├── configmap.yaml
│       ├── secret.yaml
│       └── _helpers.tpl
├── agrotech-frontend/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── agrotech-arangodb/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── agrotech-umbrella/
    ├── Chart.yaml  # Meta-Chart für alle Services
    └── values.yaml
```

##### Backend Helm Chart

**Chart.yaml**:

```yaml
# helm/agrotech-backend/Chart.yaml
apiVersion: v2
name: agrotech-backend
description: Agrotech Plant Care Backend API
type: application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: common
    repository: https://bjw-s.github.io/helm-charts
    version: 3.0.0
```

**values.yaml** (mit bjw-s/common Pattern):

```yaml
# helm/agrotech-backend/values.yaml
controllers:
  main:
    type: deployment
    replicas: 3

    strategy:
      type: RollingUpdate
      rollingUpdate:
        maxSurge: 1
        maxUnavailable: 0

    containers:
      main:
        image:
          repository: agrotech/backend
          tag: "1.0.0"
          pullPolicy: IfNotPresent

        env:
          # ArangoDB Connection
          - name: ARANGODB_URL
            valueFrom:
              secretKeyRef:
                name: arangodb-credentials
                key: url
          - name: ARANGODB_DATABASE
            value: "agrotech_db"
          - name: ARANGODB_USER
            valueFrom:
              secretKeyRef:
                name: arangodb-credentials
                key: user
          - name: ARANGODB_PASSWORD
            valueFrom:
              secretKeyRef:
                name: arangodb-credentials
                key: password

          # Redis Connection
          - name: REDIS_URL
            value: "redis://redis:6379/0"

          # JWT Configuration (REQ-023: Authlib)
          - name: JWT_SECRET
            valueFrom:
              secretKeyRef:
                name: backend-secrets
                key: jwt-secret
          - name: JWT_ALGORITHM
            value: "HS256"
          - name: JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            value: "15"
          - name: JWT_REFRESH_TOKEN_EXPIRE_DAYS
            value: "30"

          # Encryption Key for Provider Secrets (REQ-023)
          - name: FERNET_KEY
            valueFrom:
              secretKeyRef:
                name: backend-secrets
                key: fernet-key

          # Email Adapter (REQ-023: console | smtp | resend)
          - name: EMAIL_ADAPTER
            value: "console"

          # Application Settings
          - name: LOG_LEVEL
            value: "INFO"
          - name: ENVIRONMENT
            value: "production"

        probes:
          liveness:
            enabled: true
            type: http
            path: /health/live
            port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3

          readiness:
            enabled: true
            type: http
            path: /health/ready
            port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          startup:
            enabled: true
            type: http
            path: /health/startup
            port: 8000
            initialDelaySeconds: 0
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 30

        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi

        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
              - ALL

service:
  main:
    controller: main
    type: ClusterIP
    ports:
      http:
        port: 8000
        protocol: HTTP
        appProtocol: http

ingress:
  main:
    enabled: true
    className: traefik
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
      traefik.ingress.kubernetes.io/router.middlewares: default-ratelimit@kubernetescrd
    hosts:
      - host: api.agrotech.example.com
        paths:
          - path: /
            pathType: Prefix
            service:
              identifier: main
              port: http
    tls:
      - secretName: api-tls
        hosts:
          - api.agrotech.example.com

persistence:
  tmp:
    type: emptyDir
    medium: Memory
    globalMounts:
      - path: /tmp

  cache:
    type: emptyDir
    globalMounts:
      - path: /app/.cache

serviceAccount:
  create: true
  name: backend-sa

podDisruptionBudget:
  enabled: true
  minAvailable: 1

autoscaling:
  enabled: true
  target: main
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Prometheus Monitoring
serviceMonitor:
  main:
    enabled: true
    serviceName: main
    endpoints:
      - port: http
        path: /metrics
        interval: 30s
        scrapeTimeout: 10s

# Pod Annotations für Prometheus
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

**values-prod.yaml** (Production Overrides):

```yaml
# helm/agrotech-backend/values-prod.yaml
controllers:
  main:
    replicas: 5

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20

controllers:
  main:
    containers:
      main:
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi

ingress:
  main:
    annotations:
      traefik.ingress.kubernetes.io/router.middlewares: |
        default-ratelimit@kubernetescrd,
        default-compress@kubernetescrd,
        default-security-headers@kubernetescrd
```

##### Celery Worker Helm Chart

**values-worker.yaml**:

```yaml
# helm/agrotech-backend/values-worker.yaml
controllers:
  worker:
    type: deployment
    replicas: 2

    containers:
      main:
        image:
          repository: agrotech/backend
          tag: "1.0.0"

        command:
          - celery
          - -A
          - celery_app
          - worker
          - --loglevel=info
          - --concurrency=4

        env:
          - name: ARANGODB_URL
            valueFrom:
              secretKeyRef:
                name: arangodb-credentials
                key: url
          - name: REDIS_URL
            value: "redis://redis:6379/0"

        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi

  beat:
    type: deployment
    replicas: 1  # Nur ein Beat-Scheduler!

    containers:
      main:
        image:
          repository: agrotech/backend
          tag: "1.0.0"

        command:
          - celery
          - -A
          - celery_app
          - beat
          - --loglevel=info

        env:
          - name: REDIS_URL
            value: "redis://redis:6379/0"

        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi

# Kein Service nötig für Worker/Beat
service:
  main:
    enabled: false
```

##### Frontend Helm Chart

**values.yaml**:

```yaml
# helm/agrotech-frontend/values.yaml
controllers:
  main:
    type: deployment
    replicas: 2

    containers:
      main:
        image:
          repository: agrotech/frontend
          tag: "1.0.0"

        env:
          - name: REACT_APP_API_URL
            value: "https://api.agrotech.example.com"
          - name: REACT_APP_SENTRY_DSN
            valueFrom:
              secretKeyRef:
                name: frontend-secrets
                key: sentry-dsn

        probes:
          liveness:
            enabled: true
            type: http
            path: /
            port: 80
          readiness:
            enabled: true
            type: http
            path: /
            port: 80

        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi

service:
  main:
    controller: main
    type: ClusterIP
    ports:
      http:
        port: 80

ingress:
  main:
    enabled: true
    className: traefik
    annotations:
      cert-manager.io/cluster-issuer: letsencrypt-prod
      traefik.ingress.kubernetes.io/router.middlewares: |
        default-compress@kubernetescrd,
        default-security-headers@kubernetescrd
    hosts:
      - host: app.agrotech.example.com
        paths:
          - path: /
            pathType: Prefix
            service:
              identifier: main
              port: http
    tls:
      - secretName: app-tls
        hosts:
          - app.agrotech.example.com
```

##### ArangoDB Helm Chart

**values.yaml**:

```yaml
# helm/agrotech-arangodb/values.yaml
controllers:
  main:
    type: statefulset
    replicas: 3  # Cluster-Modus

    statefulset:
      volumeClaimTemplates:
        - name: data
          globalMounts:
            - path: /var/lib/arangodb3
          accessMode: ReadWriteOnce
          size: 50Gi
          storageClass: fast-ssd

    containers:
      main:
        image:
          repository: arangodb
          tag: "3.11"

        env:
          - name: ARANGO_ROOT_PASSWORD
            valueFrom:
              secretKeyRef:
                name: arangodb-credentials
                key: password
          - name: ARANGO_STORAGE_ENGINE
            value: "rocksdb"

        probes:
          liveness:
            enabled: true
            type: http
            path: /_api/version
            port: 8529
          readiness:
            enabled: true
            type: http
            path: /_api/version
            port: 8529

        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi

service:
  main:
    controller: main
    type: ClusterIP
    ports:
      http:
        port: 8529

# Headless Service für StatefulSet
service:
  headless:
    controller: main
    type: ClusterIP
    clusterIP: None
    ports:
      http:
        port: 8529
```

##### Umbrella Chart (alle Services zusammen)

**Chart.yaml**:

```yaml
# helm/agrotech-umbrella/Chart.yaml
apiVersion: v2
name: agrotech
description: Complete Agrotech Plant Care System
type: application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: agrotech-backend
    version: 1.0.0
    repository: "file://../agrotech-backend"
    condition: backend.enabled

  - name: agrotech-frontend
    version: 1.0.0
    repository: "file://../agrotech-frontend"
    condition: frontend.enabled

  - name: agrotech-arangodb
    version: 1.0.0
    repository: "file://../agrotech-arangodb"
    condition: arangodb.enabled

  - name: redis
    version: 18.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: redis.enabled

  - name: postgresql
    version: 13.0.0
    repository: https://charts.bitnami.com/bitnami
    condition: postgresql.enabled
    alias: timescaledb
```

**values.yaml**:

```yaml
# helm/agrotech-umbrella/values.yaml
backend:
  enabled: true

frontend:
  enabled: true

arangodb:
  enabled: true

redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: true
    password: "changeme"
  master:
    persistence:
      enabled: true
      size: 8Gi

timescaledb:
  enabled: true
  auth:
    postgresPassword: "changeme"
    database: agrotech_sensors
  primary:
    persistence:
      enabled: true
      size: 100Gi
    initdb:
      scripts:
        01-timescale.sql: |
          CREATE EXTENSION IF NOT EXISTS timescaledb;
```

##### Helm Deployment-Workflow

```bash
# 1. Dependencies installieren
cd helm/agrotech-umbrella
helm dependency build

# 2. Dry-run für Validation
helm install agrotech . \
  --namespace agrotech-prod \
  --create-namespace \
  --values values.yaml \
  --values values-prod.yaml \
  --dry-run --debug

# 3. Installation
helm install agrotech . \
  --namespace agrotech-prod \
  --create-namespace \
  --values values.yaml \
  --values values-prod.yaml

# 4. Upgrade
helm upgrade agrotech . \
  --namespace agrotech-prod \
  --values values.yaml \
  --values values-prod.yaml \
  --atomic \
  --timeout 10m

# 5. Rollback bei Problemen
helm rollback agrotech -n agrotech-prod

# 6. Uninstall
helm uninstall agrotech -n agrotech-prod
```

##### Helm Entwicklungs-Workflow

**Lokale Entwicklung mit Minikube**:

```bash
# 1. Minikube starten
minikube start --cpus=4 --memory=8192

# 2. Lokales Docker-Image in Minikube laden
eval $(minikube docker-env)
docker build -t agrotech/backend:dev ./backend

# 3. Chart installieren mit dev-Image
helm install agrotech-backend ./helm/agrotech-backend \
  --namespace agrotech-dev \
  --create-namespace \
  --set controllers.main.containers.main.image.tag=dev \
  --set controllers.main.containers.main.image.pullPolicy=Never

# 4. Port-Forward für lokalen Zugriff
kubectl port-forward -n agrotech-dev svc/agrotech-backend-main 8000:8000

# 5. Logs anschauen
kubectl logs -n agrotech-dev -l app.kubernetes.io/name=agrotech-backend -f

# 6. Änderungen testen (Rebuild + Upgrade)
docker build -t agrotech/backend:dev ./backend
helm upgrade agrotech-backend ./helm/agrotech-backend \
  --namespace agrotech-dev \
  --reuse-values
```

**Helm Template Debugging**:

```bash
# 1. Generierte Manifests anschauen
helm template agrotech-backend ./helm/agrotech-backend \
  --values ./helm/agrotech-backend/values.yaml \
  --debug

# 2. Nur bestimmtes Template rendern
helm template agrotech-backend ./helm/agrotech-backend \
  --show-only templates/deployment.yaml

# 3. Mit spezifischen Values
helm template agrotech-backend ./helm/agrotech-backend \
  --set controllers.main.replicas=10 \
  --set controllers.main.containers.main.image.tag=test

# 4. Validierung gegen Kubernetes API
helm template agrotech-backend ./helm/agrotech-backend | kubectl apply --dry-run=server -f -
```

**Chart-Unterschiede zwischen Umgebungen**:

```bash
# Diff zwischen dev und prod
helm diff upgrade agrotech-backend ./helm/agrotech-backend \
  -n agrotech-prod \
  --values ./helm/agrotech-backend/values-prod.yaml

# Requires: helm plugin install https://github.com/databus23/helm-diff
```

##### Helmfile (Alternative für Multi-Environment)

```yaml
# helmfile.yaml
repositories:
  - name: bjw-s
    url: https://bjw-s.github.io/helm-charts
  - name: bitnami
    url: https://charts.bitnami.com/bitnami

environments:
  dev:
    values:
      - environments/dev/values.yaml
  staging:
    values:
      - environments/staging/values.yaml
  prod:
    values:
      - environments/prod/values.yaml

releases:
  - name: agrotech-backend
    namespace: agrotech-{{ .Environment.Name }}
    chart: ./helm/agrotech-backend
    values:
      - ./helm/agrotech-backend/values.yaml
      - ./helm/agrotech-backend/values-{{ .Environment.Name }}.yaml

  - name: agrotech-frontend
    namespace: agrotech-{{ .Environment.Name }}
    chart: ./helm/agrotech-frontend
    values:
      - ./helm/agrotech-frontend/values.yaml

  - name: redis
    namespace: agrotech-{{ .Environment.Name }}
    chart: bitnami/redis
    version: 18.0.0
    values:
      - ./helm/redis/values.yaml

# Deployment
# helmfile -e prod sync
```

### 5.2 Service Mesh (Optional): Istio

#### Use Cases

- **Mutual TLS** zwischen Services
- **Traffic Management** (Canary Deployments)
- **Observability** (Distributed Tracing)
- **Circuit Breaker** für Resilienz

```yaml
# k8s/istio/virtual-service.yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backend
spec:
  hosts:
  - backend.agrotech.svc.cluster.local
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: backend
        subset: v2
      weight: 10
  - route:
    - destination:
        host: backend
        subset: v1
      weight: 90
```

### 5.3 CI/CD Pipeline: GitLab CI / GitHub Actions

#### GitHub Actions Workflow

```yaml
# .github/workflows/backend.yml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          cd backend
          uv sync --locked --extra dev
          echo "$PWD/.venv/bin" >> "$GITHUB_PATH"

      - name: Run Ruff (Linting)
        run: cd backend && ruff check .

      - name: Run Black (Formatting)
        run: cd backend && black --check .

      - name: Run mypy (Type Checking)
        run: cd backend && mypy .

      - name: Run Pytest
        run: cd backend && pytest --cov=. --cov-report=xml

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker Image
        run: |
          docker build -t agrotech/backend:${{ github.sha }} backend/

      - name: Push to Registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push agrotech/backend:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBE_CONFIG }}

      - name: Install Helm
        uses: azure/setup-helm@v3
        with:
          version: '3.13.0'

      - name: Add Helm Repositories
        run: |
          helm repo add bjw-s https://bjw-s.github.io/helm-charts
          helm repo add bitnami https://charts.bitnami.com/bitnami
          helm repo update

      - name: Lint Helm Chart
        run: |
          cd helm/agrotech-backend
          helm dependency build
          helm lint .

      - name: Deploy to Kubernetes (Helm)
        run: |
          helm upgrade --install agrotech-backend \
            ./helm/agrotech-backend \
            --namespace agrotech-prod \
            --create-namespace \
            --values ./helm/agrotech-backend/values.yaml \
            --values ./helm/agrotech-backend/values-prod.yaml \
            --set controllers.main.containers.main.image.tag=${{ github.sha }} \
            --atomic \
            --timeout 10m \
            --wait

      - name: Run Helm Tests
        run: |
          helm test agrotech-backend -n agrotech-prod

      - name: Notify Deployment
        if: success()
        run: |
          echo "Deployment successful: agrotech/backend:${{ github.sha }}"
```

### 5.4 Infrastructure as Code: Terraform

```hcl
# terraform/main.tf
provider "aws" {
  region = "eu-central-1"
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "agrotech-prod"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 2
      max_size     = 5

      instance_types = ["t3.medium"]
      capacity_type  = "SPOT"  # Kostenoptimierung
    }
  }
}

# RDS für TimescaleDB
resource "aws_db_instance" "timescale" {
  identifier        = "agrotech-timescale"
  engine            = "postgres"
  engine_version    = "16.1"
  instance_class    = "db.t3.medium"
  allocated_storage = 100

  db_name  = "agrotech_sensors"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  skip_final_snapshot     = false
}
```

---

## 6. Monitoring & Observability

### 6.1 Metrics: Prometheus + Grafana

#### Prometheus Stack

```yaml
# k8s/monitoring/prometheus.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s

    scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
```

#### Grafana Dashboards

- **System Overview**: CPU, Memory, Network
- **API Metrics**: Request Rate, Latency, Error Rate
- **Business Metrics**:
    - Aktive Pflanzen pro Phase
    - Bewässerungsevents pro Tag
    - GDD-Akkumulation
    - Ernte-Pipeline

### 6.2 Logging: EFK Stack (Elasticsearch + Fluentd + Kibana)

```yaml
# k8s/logging/fluentd-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    spec:
      containers:
      - name: fluentd
        image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
        env:
        - name: FLUENT_ELASTICSEARCH_HOST
          value: "elasticsearch.logging.svc.cluster.local"
        - name: FLUENT_ELASTICSEARCH_PORT
          value: "9200"
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: containers
          mountPath: /var/lib/docker/containers
          readOnly: true
```

### 6.3 Tracing: Jaeger (OpenTelemetry)

```python
# backend/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def init_tracer():
    trace.set_tracer_provider(TracerProvider())
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger.monitoring.svc.cluster.local",
        agent_port=6831,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

# Verwendung
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.get("/api/v1/plants/{plant_id}")
async def get_plant(plant_id: str):
    with tracer.start_as_current_span("get_plant"):
        with tracer.start_as_current_span("fetch_from_cache"):
            plant = await cache.get_plant(plant_id)

        if not plant:
            with tracer.start_as_current_span("fetch_from_db"):
                plant = await db.get_plant(plant_id)

        return plant
```

---

## 7. Sicherheit

### 7.1 Secrets Management: HashiCorp Vault

```yaml
# k8s/vault/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vault
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: vault
        image: vault:1.15
        env:
        - name: VAULT_ADDR
          value: "http://127.0.0.1:8200"
        - name: VAULT_DEV_ROOT_TOKEN_ID
          valueFrom:
            secretKeyRef:
              name: vault-root-token
              key: token
```

```python
# backend/config.py
import hvac

class VaultSecrets:
    def __init__(self, vault_url: str, token: str):
        self.client = hvac.Client(url=vault_url, token=token)

    def get_db_credentials(self) -> dict:
        """Hole DB-Credentials aus Vault"""
        secret = self.client.secrets.kv.v2.read_secret_version(
            path="agrotech/database"
        )
        return secret['data']['data']
```

### 7.2 Network Policies

```yaml
# k8s/network-policies/backend.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: arangodb
    ports:
    - protocol: TCP
      port: 8529
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### 7.3 Authentifizierung & Autorisierung (REQ-023 / REQ-024)

> **Vollständige Spezifikation:** Siehe REQ-023 (Benutzerverwaltung & Authentifizierung) und REQ-024 (Mandantenverwaltung & Gemeinschaftsgärten). Diese Sektion gibt nur den Stack-Überblick.

**Library-Stack:**

| Paket | Version | Zweck |
|-------|---------|-------|
| `authlib` | >= 1.3.0 | JWT (HS256), OAuth2 Client, OIDC Discovery, PKCE |
| `bcrypt` | >= 4.0 | Passwort-Hashing (Bcrypt direkt, Cost Factor 12, siehe ADR-004) |
| `slowapi` | >= 0.1.9 | Rate Limiting (IP-basiert, nutzt Redis) |
| `cryptography` | >= 42.0 | Fernet/AES-256 für Provider-Secret-Verschlüsselung |

> **Hinweis:** `authlib` ersetzt `python-jose` (letztes Release 2022, unmaintained). Authlib bietet JWT + OAuth2/OIDC in einer Library und wird aktiv gewartet. NFR-001 §6.1 wurde entsprechend als abgelöst markiert.

**Token-Architektur:**

| Token | TTL | Speicherort | Library |
|-------|-----|-------------|---------|
| Access Token (JWT) | 15 Min | Memory (Frontend) | `authlib.jose.jwt` |
| Refresh Token | 30 Tage | HttpOnly Secure Cookie | `secrets.token_urlsafe` + SHA-256 Hash in ArangoDB |
| OAuth State | 5 Min | Redis | `secrets.token_urlsafe` |

**Unterstützte Auth-Provider:**
- Lokal (E-Mail + Passwort)
- Google OAuth2 + OIDC
- GitHub OAuth2
- Apple Sign-In (OAuth2 + OIDC)
- Generische OIDC-Provider (Keycloak, Authentik, Azure AD, Okta — per Konfiguration)

**E-Mail-Service (Adapter-Pattern):**
Abstraktes `IEmailService`-Interface (analog GBIF/Perenual-Adapter in REQ-011). Konkrete Implementierung per Konfiguration (`EMAIL_ADAPTER`):
- `console` — Entwicklungsumgebung (stdout)
- `smtp` — Direkter SMTP-Versand (`aiosmtplib`)
- `resend` — Transactional API

---

## 8. Entwicklungs-Tools

### 8.1 Python Development

#### Python 3.14 Installation

```bash
# Über pyenv (empfohlen)
pyenv install 3.14
pyenv local 3.14

# Oder via Docker
docker run -it python:3.14-slim bash
```

#### Dependency Management

Deklariert in `pyproject.toml` (`[project].dependencies`, Dev-Extra), aufgelöst in `uv.lock` (`uv lock`), installiert mit `uv sync --locked` (NFR-009). Zur Orientierung der Kern der Deklaration:

```txt
# pyproject.toml — [project].dependencies (Auszug)
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.10.0
python-arango>=8.1.0
redis>=5.2.0
celery>=5.4.0
httpx>=0.28.0
structlog>=24.4.0
prometheus-client>=0.19.0

# Auth & Security (REQ-023)
authlib>=1.3.0                    # JWT (HS256), OAuth2 Client, OIDC Discovery, PKCE — ersetzt python-jose
bcrypt>=4.0                       # Passwort-Hashing (bcrypt direkt, siehe ADR-004)
slowapi>=0.1.9                    # Rate Limiting (nutzt Redis als Backend)
cryptography>=42.0                # Fernet/AES-256 für Provider-Secret-Verschlüsselung

# pyproject.toml — [project.optional-dependencies].dev (Auszug)
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
ruff==0.1.9
black==23.12.1
mypy==1.8.0
```

#### IDE-Setup (VSCode)

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "python.analysis.typeCheckingMode": "strict",
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### 8.2 Frontend Development

```json
// package.json
{
  "name": "agrotech-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@reduxjs/toolkit": "^2.5.0",
    "react-redux": "^9.2.0",
    "@mui/material": "^7.0.0",
    "axios": "^1.9.0",
    "react-router-dom": "^7.0.0",
    "react-i18next": "^16.0.0",
    "zod": "^3.25.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript-eslint": "^8.30.0",
    "@vitejs/plugin-react": "^4.5.0",
    "eslint": "^9.0.0",
    "eslint-plugin-react-hooks": "^5.2.0",
    "typescript": "~5.9.0",
    "vite": "^6.4.0",
    "vitest": "^3.0.0"
  }
}
```

---

## 9. Kosten-Optimierung

### 9.1 Cloud-Provider Empfehlungen

#### AWS (Beispiel-Setup für mittelgroße Farm)

```
Compute:
- EKS Control Plane: $0.10/h = ~$73/Monat
- 3x t3.medium Nodes (Spot): ~$50/Monat
- 2x t3.small (On-Demand) für Kritisches: ~$30/Monat

Datenbank:
- RDS PostgreSQL (TimescaleDB): db.t3.medium = ~$60/Monat
- ElastiCache Redis: cache.t3.micro = ~$15/Monat

Storage:
- EBS für ArangoDB: 50GB GP3 = ~$5/Monat
- S3 für Backups: ~$10/Monat

Monitoring:
- CloudWatch: ~$20/Monat

TOTAL: ~$263/Monat
```

### 9.2 Self-Hosted Alternative (On-Premise)

```
Hardware (Einmalig):
- Server: Intel NUC i5 (32GB RAM, 1TB NVMe): ~€800
- Raspberry Pi 4 (8GB) für Edge-Computing: ~€100

Software:
- k3s (kostenlos)
- ArangoDB Community (kostenlos)
- PostgreSQL + TimescaleDB (kostenlos)
- Alle Open-Source Tools

Recurring:
- Strom (~50W 24/7): ~€10/Monat
- Internet: ~€30/Monat

TOTAL: ~€40/Monat + €900 Initial
```

---

## 10. Technologie-Entscheidungs-Matrix

|Anforderung|Technologie|Alternativen|Begründung|
|---|---|---|---|
|**Python Version**|3.14|3.15|Stabil, breite Library-Kompatibilitaet|
|**Backend Framework**|FastAPI|Django, Flask|Async, Auto-Docs, Type-Safety|
|**API Standard**|REST|GraphQL|Einfachheit, Cache-freundlich|
|**Multi-Model DB**|ArangoDB|Neo4j+Mongo|Ein System für Graphs+Docs|
|**Time-Series DB**|TimescaleDB|InfluxDB|SQL-kompatibel, Retention Policies|
|**Cache**|Redis|Memcached|Pub/Sub, Data Structures|
|**Task Queue**|Celery|RQ, Dramatiq|Reife, Beat-Scheduler|
|**Container Orchestration**|Kubernetes|Docker Swarm|Industry Standard, Ecosystem|
|**Package Manager (K8s)**|Helm|Kustomize|Templating, Versioning, Rollback|
|**Helm Base Chart**|bjw-s/common|Custom|Best Practices, DRY, Community|
|**Frontend Framework**|React|Vue, Svelte|Ecosystem, Talent Pool|
|**Mobile**|Flutter|React Native|Performance, Single Codebase|
|**Monitoring**|Prometheus|Datadog|Open-Source, K8s-native|
|**CI/CD**|GitHub Actions|GitLab CI|Integration, Free Tier|

---

## 11. Migration & Rollout-Strategie

### Phase 1: MVP (Wochen 1-8)

- [x] Backend: FastAPI + ArangoDB
- [x] Frontend: React Prototype
- [x] Features: Plant CRUD, Basic Dashboard
- [x] Deployment: Docker Compose (Dev)

### Phase 2: Production-Ready (Wochen 9-16)

- [ ] Kubernetes-Migration
- [ ] TimescaleDB für Sensordaten
- [ ] Celery für Async Tasks
- [ ] Monitoring (Prometheus + Grafana)

### Phase 3: Scale & Optimize (Wochen 17-24)

- [ ] Redis Caching
- [ ] Mobile App (Flutter)
- [ ] Advanced Features (ML, Computer Vision)
- [ ] Multi-Tenancy

---

## 12. Backup & Disaster Recovery

### 12.1 ArangoDB Backup

```bash
# Automatisches Backup-Script
#!/bin/bash
# backup_arangodb.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/arangodb"

# ArangoDB Dump
arangodump \
  --server.endpoint tcp://arangodb:8529 \
  --server.database agrotech_db \
  --server.username root \
  --server.password "$ARANGO_PASSWORD" \
  --output-directory "$BACKUP_DIR/$TIMESTAMP"

# Upload to S3
aws s3 sync "$BACKUP_DIR/$TIMESTAMP" \
  s3://agrotech-backups/arangodb/$TIMESTAMP

# Retention (30 Tage)
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} \;
```

```yaml
# k8s/cronjobs/backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: arangodb-backup
spec:
  schedule: "0 2 * * *"  # 02:00 Uhr täglich
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: agrotech/backup-tool:latest
            command: ["/scripts/backup_arangodb.sh"]
            volumeMounts:
            - name: backup-scripts
              mountPath: /scripts
```

### 12.2 Disaster Recovery Plan

**RTO (Recovery Time Objective)**: 2 Stunden  
**RPO (Recovery Point Objective)**: 24 Stunden

**Recovery Steps**:

1. Restore ArangoDB from latest backup
2. Restore TimescaleDB (Point-in-Time Recovery)
3. Redeploy Kubernetes Manifests
4. Verify Data Integrity
5. Resume Operations

---

## Anhang A: Glossar

|Begriff|Beschreibung|
|---|---|
|**AQL**|ArangoDB Query Language - SQL-ähnliche Graph-Query-Sprache|
|**GDD**|Growing Degree Days - Temperatur-basierte Wachstumseinheit|
|**VPD**|Vapor Pressure Deficit - Wasserdampfdruckdefizit|
|**HPA**|Horizontal Pod Autoscaler - K8s Auto-Skalierung|
|**StatefulSet**|K8s Resource für zustandsbehaftete Applikationen|
|**Hypertable**|TimescaleDB-Feature für automatisches Partitionieren|
|**Helm**|Kubernetes Package Manager mit Templating|
|**Chart**|Helm-Package (Collection von K8s Manifests)|
|**bjw-s/common**|Wiederverwendbare Helm Library Chart|

---

## Anhang B: Helm Best Practices

### Chart-Versionierung

```yaml
# Semantic Versioning für Charts
# Chart.yaml
version: 1.2.3
#         │ │ └─ Patch: Bugfixes, keine Breaking Changes
#         │ └─── Minor: Neue Features, abwärtskompatibel
#         └───── Major: Breaking Changes

appVersion: "1.0.0"  # Version der Application selbst
```

### Secrets Management in Helm

**Option 1: Sealed Secrets**:

```bash
# Installiere Sealed Secrets Controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# Verschlüssele Secret
kubectl create secret generic backend-secrets \
  --from-literal=jwt-secret=supersecret \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Deploye verschlüsseltes Secret
kubectl apply -f sealed-secret.yaml
```

**Option 2: External Secrets Operator**:

```yaml
# helm/agrotech-backend/templates/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: backend-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: backend-secrets
  data:
    - secretKey: jwt-secret
      remoteRef:
        key: secret/agrotech/backend
        property: jwt_secret
```

### Helm Testing

```yaml
# helm/agrotech-backend/templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "common.names.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
    - name: wget
      image: busybox
      command: ['wget']
      args: ['{{ include "common.names.fullname" . }}:8000/health/live']
  restartPolicy: Never
```

```bash
# Tests ausführen
helm test agrotech -n agrotech-prod
```

### Helm Hooks

```yaml
# helm/agrotech-backend/templates/job-db-migration.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation
spec:
  template:
    spec:
      containers:
      - name: migration
        image: agrotech/backend:{{ .Values.image.tag }}
        command:
          - python
          - manage.py
          - migrate
      restartPolicy: Never
  backoffLimit: 3
```

### Chart Repository (Harbor)

```bash
# Harbor als Chart Repository nutzen
helm repo add agrotech https://harbor.agrotech.example.com/chartrepo/agrotech
helm repo update

# Chart pushen
helm package helm/agrotech-backend
helm push agrotech-backend-1.0.0.tgz oci://harbor.agrotech.example.com/agrotech

# Chart installieren
helm install backend oci://harbor.agrotech.example.com/agrotech/agrotech-backend
```

---

**Dokumenten-Ende**

**Version**: 1.0 (Vollständig)  
**Status**: Produktionsreif  
**Letzte Aktualisierung**: 2026-02-25  
**Review**: Pending  
**Genehmigung**: Pending

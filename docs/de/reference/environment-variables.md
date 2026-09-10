# Umgebungsvariablen

Alle Konfigurationsparameter des Kamerplanter-Backends werden über Umgebungsvariablen gesteuert. Die Variablen werden von `pydantic-settings` geladen — Groß-/Kleinschreibung ist nicht relevant.

!!! tip "Lokale Konfiguration"
    Für die Docker-Compose-Umgebung alle Werte in eine `.env`-Datei im Repository-Wurzelverzeichnis eintragen. Eine Vorlage liegt als `.env.example` bereit:
    ```bash
    cp .env.example .env
    ```

---

## Datenbankverbindung

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `ARANGODB_HOST` | `localhost` | Ja | Hostname oder IP-Adresse der ArangoDB-Instanz |
| `ARANGODB_PORT` | `8529` | Nein | TCP-Port der ArangoDB |
| `ARANGODB_DATABASE` | `kamerplanter` | Ja | Name der Zieldatenbank |
| `ARANGODB_USERNAME` | `root` | Ja | Datenbanknutzer |
| `ARANGODB_PASSWORD` | — | Ja | Passwort des Datenbanknutzers |
| `ARANGO_ROOT_PASSWORD` | — | Ja* | Root-Passwort für den ArangoDB-Container (nur Docker) |

*`ARANGO_ROOT_PASSWORD` wird direkt an den ArangoDB-Container übergeben und ist für den Start der Datenbank erforderlich.

!!! warning "Produktionspasswörter"
    Verwenden Sie niemals den Standardwert `rootpassword` in produktiven Umgebungen. Generieren Sie sichere Passwörter: `openssl rand -hex 32`

---

## Cache und Aufgaben-Queue

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Ja | Verbindungs-URL für Redis oder Valkey (Celery Broker und Backend-Cache) |

**Format:** `redis://[user]:[password]@[host]:[port]/[db]`

**Beispiele:**
```
redis://localhost:6379/0                    # Lokal ohne Auth
redis://:meinpasswort@redis:6379/0          # Mit Passwort
rediss://user:pass@redis-host:6380/1        # TLS (rediss://)
```

---

## Sicherheit und Authentifizierung

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `JWT_SECRET_KEY` | `change-me-in-production-...` | Ja | Geheimer Schlüssel für JWT-Signierung (HS256) |
| `JWT_ALGORITHM` | `HS256` | Nein | JWT-Signaturalgorithmus |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Nein | Gültigkeitsdauer des JWT-Access-Tokens in Minuten |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Nein | Gültigkeitsdauer des Refresh-Tokens in Tagen |
| `SESSION_TOKEN_EXPIRE_HOURS` | `24` | Nein | Gültigkeitsdauer serverseitiger Session-Tokens in Stunden. |
| `FERNET_KEY` | — | Ja | Fernet-Schlüssel zum Verschlüsseln von OIDC-Provider-Secrets. **Unabhängig davon, ob OIDC genutzt wird** — der Startup-Gate verweigert den Produktionsstart bei leerem Wert (AP-4, INF-S5). Muss ein gültiger Fernet-Schlüssel sein: 32 Bytes, url-safe base64-kodiert (44 Zeichen) — erzeugt z. B. mit `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | Nein | E-Mail-Verifikation bei Registrierung erzwingen |
| `HIBP_ENABLED` | `false` | Nein | "Have I Been Pwned"-Prüfung bei Passwortänderung aktivieren |
| `COOKIE_SECURE` | `true` | Nein | Setzt das `Secure`-Flag auf dem Refresh-Token-Cookie. Nur für reine HTTP-E2E-Testumgebungen ohne TLS auf `false` setzen — in Produktion **immer** `true` belassen. |

!!! danger "JWT_SECRET_KEY in Produktion ändern"
    Der Standardwert `change-me-in-production-use-openssl-rand-hex-32` darf in produktiven Umgebungen **nicht** verwendet werden. Generieren Sie einen sicheren Wert:
    ```bash
    openssl rand -hex 32
    ```
    Änderungen des `JWT_SECRET_KEY` machen alle aktiven Tokens ungültig — alle Nutzer werden abgemeldet.

---

## Datenschutz & DSGVO (REQ-025 / NFR-011) {#datenschutz-dsgvo-req-025-nfr-011}

Diese Variablen steuern die datenschutzrechtlich vorgeschriebene Löschung/Anonymisierung personenbezogener Daten (siehe [Datenschutz (DSGVO)](../user-guide/privacy.md)) und sind vom Betriebsmodus unabhängig — sie gelten sowohl im Light- als auch im Full-Modus.

<!-- Quelle: src/backend/app/config/settings.py (erasure_tombstone_salt, privacy_data_controller_name, privacy_data_controller_email, privacy_export_retention_hours, privacy_hard_delete_after_days, privacy_email_change_ttl_hours); src/backend/app/main.py (insecure_default_secrets) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `ERASURE_TOMBSTONE_SALT` | — | Ja | Hochentropisches Geheimnis (mindestens 32 Zeichen) zur Pseudonymisierung gelöschter Nutzerkonten (Tombstone-Hashing, NFR-011 §4). **Der Startup-Gate verweigert den Produktionsstart**, wenn der Wert leer oder kürzer als 32 Zeichen ist — unabhängig vom Betriebsmodus. Erzeugen mit `openssl rand -hex 32`. |
| `PRIVACY_DATA_CONTROLLER_NAME` | `Kamerplanter Operator` | Nein | Name des datenschutzrechtlich Verantwortlichen, erscheint in Export- und Auskunftsdokumenten. |
| `PRIVACY_DATA_CONTROLLER_EMAIL` | `privacy@kamerplanter.example` | Nein | Kontakt-E-Mail des Verantwortlichen für DSGVO-Anfragen. |
| `PRIVACY_EXPORT_RETENTION_HOURS` | `72` | Nein | Aufbewahrungsdauer eines generierten Datenexports (Art. 15/20 DSGVO), bevor er automatisch gelöscht wird. |
| `PRIVACY_HARD_DELETE_AFTER_DAYS` | `90` | Nein | Frist, nach der ein zur Löschung markiertes Konto endgültig (Hard-Delete) entfernt wird. |
| `PRIVACY_EMAIL_CHANGE_TTL_HOURS` | `24` | Nein | Gültigkeitsdauer des Bestätigungslinks bei einer E-Mail-Adressänderung. |

!!! danger "ERASURE_TOMBSTONE_SALT — Boot-Blocker in Produktion"
    Anders als die meisten anderen Variablen auf dieser Seite ist `ERASURE_TOMBSTONE_SALT` **kein optionales Feature-Flag**: Das Backend startet in Produktion (`DEBUG=false`) grundsätzlich nicht, wenn dieser Wert fehlt oder zu kurz ist — unabhängig davon, ob DSGVO-Löschanfragen aktiv genutzt werden. Details zu allen unbedingt erforderlichen Secrets: [Konfigurationsmatrix — Pflicht-Secrets je aktivierter Funktion](../deployment/konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion).

---

## Betriebsmodus

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `KAMERPLANTER_MODE` | `full` | Nein | Betriebsmodus: `full` (Auth + Mandanten) oder `light` (kein Auth, lokale Einzelnutzung) |
| `DEBUG` | `false` | Nein | Debug-Logging aktivieren (verbose, nie in Produktion). Deaktiviert zusätzlich den Startup-Gate für Produktions-Secrets — **niemals** in Produktion setzen. |
| `FRONTEND_URL` | `http://localhost:5173` | Nein | URL des Frontends (wird für E-Mail-Links verwendet) |
| `APP_BASE_URL` | `http://localhost:5173` | Nein | Basis-URL für QR-Codes auf Pflanzen-Etiketten (Druckansichten, siehe [Druckansichten & Export](../user-guide/print-export.md)). In Produktion auf die öffentlich erreichbare Frontend-URL setzen, sonst zeigen gedruckte QR-Codes auf `localhost`. |

### Light-Modus (`KAMERPLANTER_MODE=light`)

Im Light-Modus entfällt die Token-Authentifizierung. Die API ist ohne Anmeldung verwendbar. Dieser Modus ist für lokale Einzelinstallationen ohne Internet-Exposition gedacht.

!!! danger "Light-Modus nicht öffentlich exponieren"
    Der Light-Modus deaktiviert alle Authentifizierungsschichten. Niemals mit einem öffentlich erreichbaren Port betreiben.

---

## CORS-Konfiguration

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:5173"]` | Nein | JSON-Array erlaubter Origins für CORS |

**Format:** Immer als JSON-Array im String-Format:
```bash
CORS_ORIGINS='["https://app.example.com","https://app2.example.com"]'
```

---

## E-Mail

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `EMAIL_ADAPTER` | `console` | Nein | E-Mail-Adapter: `console` (Ausgabe im Log), `smtp`, `resend` |
| `SMTP_HOST` | `localhost` | Nein | SMTP-Server-Hostname |
| `SMTP_PORT` | `587` | Nein | SMTP-Port |
| `SMTP_USERNAME` | — | Nein | SMTP-Benutzername |
| `SMTP_PASSWORD` | — | Nein | SMTP-Passwort |
| `SMTP_FROM_EMAIL` | `noreply@kamerplanter.example` | Nein | Absenderadresse für System-E-Mails |
| `SMTP_USE_TLS` | `true` | Nein | STARTTLS für SMTP aktivieren |

Im Entwicklungsmodus (`EMAIL_ADAPTER=console`) werden E-Mails nicht gesendet, sondern im Backend-Log ausgegeben.

!!! note "Wird auch vom Benachrichtigungssystem genutzt"
    Diese Variablen konfigurieren zugleich den E-Mail-Kanal des [Benachrichtigungssystems](../user-guide/notifications.md#e-mail) — es gibt keine separate SMTP-Konfiguration für Benachrichtigungen.

---

## Externe Datenanreicherung (REQ-011)

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `PERENUAL_API_KEY` | — | Nein | API-Schlüssel für Perenual-Pflanzendatenbank |
| `TREFLE_API_KEY` | — | Nein | API-Schlüssel für Tréflé-Pflanzendatenbank |
| `ENRICHMENT_HTTP_TIMEOUT` | `30` | Nein | HTTP-Timeout für externe API-Anfragen (Sekunden) |

GBIF wird ohne API-Key verwendet (öffentliche API). Perenual und Tréflé erfordern kostenlose Registrierung.

---

## Knowledge Service — Re-Ranking (optional)

Diese Variablen konfigurieren den optionalen Cross-Encoder-Re-Ranker des Knowledge Service. Ist `RERANKER_URL` leer, arbeitet der Knowledge Service im Hybrid-Search-only-Modus (Graceful Degradation). Siehe [ADR-007](../adr/007-cross-encoder-reranking.md).

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `RERANKER_URL` | `` (leer) | Nein | HTTP-URL des Reranker-Microservice, z. B. `http://reranker-service:8081`. Leer = Re-Ranking deaktiviert. |
| `RERANKER_INITIAL_K` | `20` | Nein | Anzahl der Chunks, die aus dem Hybrid-Search-Schritt abgerufen werden (Over-Retrieval). |
| `RERANKER_TOP_K` | `5` | Nein | Anzahl der Chunks, die nach dem Re-Ranking an den LLM-Kontext übergeben werden. |
| `RERANKER_MODEL` | `bge-reranker-v2-m3` | Nein | ONNX-Modellname im Reranker-Service-Container (Verzeichnis unter `/app/models/onnx/`). |

!!! note "RERANKER_MODEL gehört zum Reranker-Service, nicht zum Knowledge Service"
    `RERANKER_MODEL` wird als Umgebungsvariable am `reranker-service`-Container gesetzt — nicht am `knowledge-service`. Die anderen drei Variablen (`RERANKER_URL`, `RERANKER_INITIAL_K`, `RERANKER_TOP_K`) gehören zum Knowledge Service.

!!! tip "Ressourcenbedarf"
    Der Reranker-Service benötigt 1,5–4 GB RAM (je nach Modell) und addiert ~500ms Latenz pro Anfrage. Für Raspberry Pi und ressourcenarme Umgebungen empfiehlt sich, `RERANKER_URL` leer zu lassen.

---

## KI-Assistent <!-- REQ-031 --> {#ki-assistent}

Diese Variablen gehören zum **Kamerplanter-Backend** und steuern den dreistufigen Freischalt-Mechanismus sowie die Anbindung an den Knowledge Service (siehe [KI-Assistent — Benutzerhandbuch](../user-guide/ai-assistant.md)). Die Provider-Auswahl (Ollama/Anthropic/OpenAI-kompatibel) ist eine separate Konfiguration **am Knowledge Service selbst** — siehe [KI-Provider einrichten](../user-guide/ai-providers.md).

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `AI_FEATURES_ENABLED` | `false` | Nein | Stufe 1 des dreistufigen Freischalt-Mechanismus. `false` lässt sämtliche `/ai/*`-Endpunkte mit HTTP 404 antworten — die KI-API existiert dann faktisch nicht. |
| `KNOWLEDGE_SERVICE_ENABLED` | `false` | Nein | Aktiviert die Anbindung an den Knowledge Service (wird sowohl vom älteren `/api/v1/knowledge/*`-Pfad als auch intern vom KI-Assistenten benötigt). |
| `KNOWLEDGE_SERVICE_URL` | `http://knowledge-service:8000` | Nein | Basis-URL des Knowledge-Service-Microservice. |
| `AI_KNOWLEDGE_SERVICE_TIMEOUT_S` | `60` | Nein | HTTP-Timeout des `KnowledgeServiceAdapter` gegen den Knowledge Service (Sekunden). |
| `AI_CIRCUIT_BREAKER_THRESHOLD` | `3` | Nein | Anzahl aufeinanderfolgender Fehler, ab der der Adapter den Knowledge Service als nicht erreichbar markiert. |
| `AI_CIRCUIT_BREAKER_WINDOW_S` | `60` | Nein | Zeitfenster (Sekunden), in dem die Fehler für `AI_CIRCUIT_BREAKER_THRESHOLD` gezählt werden. |
| `AI_CIRCUIT_BREAKER_COOLDOWN_S` | `60` | Nein | Wartezeit (Sekunden), bevor der Adapter nach dem Auslösen des Circuit Breakers erneut Anfragen an den Knowledge Service zulässt. |
| `AI_PUBLIC_RATE_LIMIT_PER_MIN` | `10` | Nein | IP-Ratenbegrenzung für den anonymen, Light-Modus-fähigen Endpunkt `POST /api/v1/public/ai/ask` (Anfragen pro Minute). |
| `INTERNAL_SERVICE_TOKEN` | — | Bedingt | Gemeinsames Geheimnis für cluster-interne M2M-Aufrufe (u. a. an den Knowledge Service). Pflicht, sobald `KNOWLEDGE_SERVICE_ENABLED=true` gesetzt ist — ohne Token verweigert der Startup-Gate den Start (AP-4). |

!!! warning "Instanzweite Freischaltung reicht allein nicht aus"
    `AI_FEATURES_ENABLED=true` schaltet die KI-API nur instanzweit frei (Stufe 1). Damit ein konkreter Mandant (Garten) KI-Funktionen tatsächlich nutzen kann, muss zusätzlich `tenant.settings.ai_features_enabled` für diesen Mandanten gesetzt sein (Stufe 2) — dafür existiert aktuell weder eine Oberfläche noch ein eigener API-Endpunkt, siehe [KI-Assistent — Für technische Nutzer / Self-Hoster](../user-guide/ai-assistant.md#fuer-technische-nutzer-self-hoster).

!!! info "Provider-Konfiguration liegt am Knowledge Service, nicht am Backend"
    `LLM_PROVIDER`, `LLM_API_URL`, `LLM_API_KEY` und `LLM_MODEL` sind Umgebungsvariablen des eigenständigen Knowledge-Service-Deployments (`src/knowledge-service/`), nicht dieses Backends. Details: [KI-Provider einrichten](../user-guide/ai-providers.md).

---

## MCP-Server <!-- REQ-033 --> {#mcp-server}

Diese Variablen steuern den [MCP-Server](../api/mcp-server.md) — die Werkzeug-Schnittstelle, über die externe LLM-Clients (Claude Desktop, Claude Code, eigene Agenten) per Service-Account-API-Key auf Kamerplanter zugreifen können.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `MCP_SERVER_ENABLED` | `false` | Nein | Gesamtschalter. Solange nicht `true`, antworten alle `/mcp/*`-Endpunkte mit HTTP 404 — die Schnittstelle existiert dann faktisch nicht. |
| `MCP_IDEMPOTENCY_TTL_HOURS` | `24` | Nein | Gültigkeitsdauer eines `idempotency_key` für Schreibwerkzeuge — danach wird ein Wiederholungs-Aufruf als neue Aktion behandelt. |
| `MCP_AUDIT_RETENTION_DAYS` | `90` | Nein | Aufbewahrungsdauer des `mcp_audit_log` (NFR-011) — ältere Einträge werden automatisch gelöscht. |
| `MCP_MAX_IMAGE_PAYLOAD_MB` | `4` | Nein | Obergrenze der Gesamt-Nutzlast eines Aufrufs des Tagebuch-Werkzeugs `get_diary_entry_photos` in Megabyte (Base-64-kodiert). Wird sie überschritten, antwortet das Werkzeug mit dem Fehlercode `payload.too_large`, statt Fotos still wegzulassen — siehe [MCP-Server — Tagebuch-Analyse](../api/mcp-server.md#tagebuch-analyse-externe-agenten). |

!!! note "Kein eigener Prozess, keine eigenen Verbindungsvariablen"
    Der MCP-Server läuft im bestehenden Backend-Prozess mit und nutzt dessen ArangoDB-/Redis-Verbindung mit — es gibt keine separate Host-, Port- oder Credential-Konfiguration.

---

## Tagebuch — Umgebungs-Schnappschuss

Beim Anlegen eines Tagebuch-Eintrags liest Kamerplanter die Sensorwerte, die die Pflanze abdecken, und speichert sie getrennt von den handnotierten Messwerten mit — siehe [Tagebuch — Die Umgebung wird automatisch mitgeschrieben](../user-guide/plant-diary.md#umgebung).

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `DIARY_ENVIRONMENT_CAPTURE_ENABLED` | `true` | Nein | Gesamtschalter. Auf `false` wird jeder neue Eintrag mit dem Vermerk „nicht versucht" gespeichert — unterscheidbar von „gesucht und nichts gefunden". |
| `DIARY_ENVIRONMENT_MAX_AGE_MINUTES` | `60` | Nein | Ein Messwert, der älter ist, wird **gar nicht** erfasst. Ein Eintrag, der einen gestrigen Sensorwert als aktuell ausweist, ist schlechteres Belegmaterial als ein Eintrag ohne Klimawerte. |
| `DIARY_ENVIRONMENT_CAPTURE_TIMEOUT_SECONDS` | `3.0` | Nein | Harte Obergrenze für die gesamte Erfassung. Läuft sie ab, wird der Eintrag mit dem gespeichert, was rechtzeitig ankam — das Anlegen wartet nie länger auf einen Sensor. |

!!! note "Ein Ausfall verhindert nie den Eintrag"
    Nicht erreichbares Home Assistant, fehlende TimescaleDB oder ein abgelaufenes Zeitbudget führen zu einem Eintrag **ohne** (oder mit unvollständigen) Umgebungswerten, nie zu einer abgelehnten Anlage.

---

## mDNS / Zeroconf Discovery

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `MDNS_ENABLED` | `false` | Nein | mDNS-Service-Announcement aktivieren (`_kamerplanter._tcp.local.`) |
| `INSTANCE_ID` | *(auto)* | Nein | Eindeutige Instanz-ID (z. B. `kp-abc123`). Wird beim Start automatisch generiert, wenn leer. |

Wenn aktiviert, annonciert das Backend einen `_kamerplanter._tcp.local.`-Service im lokalen Netzwerk. Home Assistant erkennt diesen Service automatisch und bietet die Einrichtung der Kamerplanter-Integration an.

!!! info "Stabile Instanz-ID"
    Die `INSTANCE_ID` wird für die Duplikat-Erkennung in Home Assistant verwendet. Wenn sie leer bleibt, wird bei jedem Neustart eine neue ID generiert. Für stabile Discovery sollte ein fester Wert gesetzt werden, z. B. `INSTANCE_ID=kp-mein-server`.

### mDNS und Kubernetes

mDNS basiert auf Multicast-UDP (Port 5353) im lokalen Layer-2-Netzwerk. In Standard-Kubernetes-Clustern funktioniert mDNS **nicht**, da:

1. **Overlay-Netzwerk blockiert Multicast** — Standard-CNIs (Calico, Cilium, Flannel) routen nur L3-Traffic. Multicast-Pakete aus einem Pod erreichen das physische LAN nicht — Home Assistant sieht die Announcements nie.
2. **Pod-IP ist nicht LAN-erreichbar** — Selbst bei funktionierendem Multicast wuerde die annoncierte Pod-IP (z. B. `10.42.x.x`) von ausserhalb des Clusters nicht erreichbar sein.

| Deployment | `MDNS_ENABLED` | Begruendung |
|------------|:-----------:|-------------|
| Docker Compose / Bare Metal | `true` | Backend laeuft direkt im LAN — `MDNS_ENABLED=true` setzen |
| K3s / MicroK8s Single-Node + `hostNetwork: true` | `true` | Pod teilt Host-Netzwerk — Multicast erreicht das LAN |
| Standard K8s Cluster | `false` | Overlay-Netzwerk blockiert Multicast — manueller Config Flow in HA als Fallback |
| Cloud (AWS, GCP, Azure) | `false` | Kein lokales Netzwerk vorhanden |

!!! warning "hostNetwork ist ein Trade-off"
    Mit `hostNetwork: true` teilt der Pod den Netzwerk-Namespace des Hosts. Multicast funktioniert, aber auf Kosten der Netzwerk-Isolation (Port-Konflikte möglich, keine NetworkPolicy-Enforcement). Nur für Homelab-/Raspberry-Pi-Szenarien empfohlen.

Im Helm-Chart ist `MDNS_ENABLED` standardmaessig auf `false` gesetzt. Der manuelle Config Flow in Home Assistant (URL-Eingabe) funktioniert in jedem Deployment-Szenario als Fallback.

---

## Home Assistant Integration (REQ-005)

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `HA_URL` | — | Nein | Home-Assistant-Basis-URL, z. B. `http://homeassistant.local:8123` |
| `HA_ACCESS_TOKEN` | — | Nein | Long-Lived Access Token aus Home Assistant |
| `HA_TIMEOUT` | `10` | Nein | HTTP-Timeout für HA-Anfragen (Sekunden) |
| `HA_ALLOW_PRIVATE_ENDPOINT` | `false` | Nein | SSRF-Opt-in: Home Assistant läuft üblicherweise im LAN über HTTP auf einer privaten/RFC1918-Adresse (`homeassistant.local`, `192.168.x.x`) oder `localhost`. Ohne diese Freigabe blockiert der SSRF-Schutz Verbindungen zu solchen Adressen. Der Cloud-Metadaten-/Link-Local-Bereich (`169.254.0.0/16`) bleibt **immer** blockiert, unabhängig von dieser Variable. |

Sind beide Variablen `HA_URL`/`HA_ACCESS_TOKEN` gesetzt, aktiviert das Backend zusätzlich den Home-Assistant-Kanal des [Benachrichtigungssystems](../user-guide/notifications.md#home-assistant) (persistente Notifications, Mobile Push, TTS).

!!! warning "Apprise-Kanal erfordert zusätzliches Python-Paket"
    Der `apprise`-Benachrichtigungskanal ist unabhängig von den Home-Assistant-Variablen immer aktiv, benötigt aber das optionale Python-Paket `apprise` im Backend-Image (`pip install apprise`) — dafür gibt es keine eigene Umgebungsvariable. Details siehe [Benachrichtigungen — Apprise](../user-guide/notifications.md#apprise).

---

## Zeitreihendaten (TimescaleDB, REQ-005) {#zeitreihendaten-timescaledb-req-005}

Diese Variablen aktivieren die optionale TimescaleDB-Anbindung für hochfrequente Sensor-Zeitreihen mit automatischem Downsampling (siehe [Sensorik](../user-guide/sensors.md)). Ohne `TIMESCALEDB_ENABLED=true` werden manuelle und automatische Messwerte weiterhin in ArangoDB gespeichert — die App bleibt voll funktionsfähig, nur ohne automatisches mehrstufiges Downsampling.

<!-- Quelle: src/backend/app/config/settings.py (timescaledb_enabled, timescaledb_host, timescaledb_port, timescaledb_database, timescaledb_username, timescaledb_password, timescaledb_pool_min_size, timescaledb_pool_max_size) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `TIMESCALEDB_ENABLED` | `false` | Nein | Gesamtschalter für die TimescaleDB-Anbindung. |
| `TIMESCALEDB_HOST` | `localhost` | Nein | Hostname der TimescaleDB-Instanz. |
| `TIMESCALEDB_PORT` | `5432` | Nein | TCP-Port. |
| `TIMESCALEDB_DATABASE` | `kamerplanter_sensors` | Nein | Datenbankname. |
| `TIMESCALEDB_USERNAME` | `postgres` | Nein | Datenbankbenutzer. |
| `TIMESCALEDB_PASSWORD` | `changeme` | Bedingt | Datenbankpasswort. **Pflicht in Produktion** — der Startup-Gate verweigert den Start, wenn `TIMESCALEDB_ENABLED=true` gesetzt ist und dieser Wert unverändert `changeme` lautet (siehe [Konfigurationsmatrix — Pflicht-Secrets je aktivierter Funktion](../deployment/konfigurationsmatrix.md#pflicht-secrets-je-aktivierter-funktion)). |
| `TIMESCALEDB_POOL_MIN_SIZE` | `2` | Nein | Minimale Connection-Pool-Größe. |
| `TIMESCALEDB_POOL_MAX_SIZE` | `10` | Nein | Maximale Connection-Pool-Größe. |

!!! note "Docker Compose: eigenes Profil"
    In der lokalen Docker-Compose-Umgebung startet TimescaleDB nur mit `docker-compose --profile timescaledb up -d`. In Kubernetes ist der `timescaledb`-Controller im Chart standardmäßig auskommentiert — der Operator ergänzt ihn per `valuesObject` (siehe [Helm Charts](../deployment/helm.md)).

---

## Umgebungssteuerung & Aktorik (REQ-018) {#umgebungssteuerung-aktorik-req-018}

Diese Variable steuert die periodische Auswertung von Zeitplänen und Regeln, den stündlichen Override-Ablauf und den 5-Minuten-Online/Offline-Abgleich mit Home Assistant für [Umgebungssteuerung & Aktorik](../user-guide/actuator-control.md).

<!-- Quelle: src/backend/app/config/settings.py (actuator_control_loop_enabled) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `ACTUATOR_CONTROL_LOOP_ENABLED` | `false` | Nein | Kill-Switch für die drei periodischen Aktor-Steuerungs-Tasks (`evaluate_control_rules` alle 30 s, `expire_manual_overrides` stündlich, `sync_actuator_states` alle 5 min). Ist die Variable deaktiviert, laufen Zeitpläne und Regeln nicht automatisch — Aktoren bleiben aber jederzeit über die REST-API steuerbar (direkter Befehl, Override, Notabschaltung). |

!!! note "Kein eigener HA-Schalter nötig"
    Anders als die anderen Home-Assistant-Funktionen benötigt die Aktor-Steuerung keine zusätzliche Freischaltung — solange `HA_URL`/`HA_ACCESS_TOKEN` gesetzt sind und `ACTUATOR_CONTROL_LOOP_ENABLED=true` ist, dispatcht das System Befehle an Home-Assistant-Aktoren automatisch.

---

## InvenTree-Integration (REQ-016)

Diese Variablen aktivieren die optionale Anbindung an [InvenTree](https://github.com/inventree/inventree). Ohne `INVENTREE_ENABLED=true` liefern alle InvenTree-Endpunkte den Fehler „Funktion deaktiviert" (HTTP 409), ohne die App zu blockieren.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `INVENTREE_ENABLED` | `false` | Nein | Kill-Switch für die gesamte InvenTree-Integration. |
| `INVENTREE_ALLOW_PRIVATE_ENDPOINT` | `false` | Nein | Erlaubt eine InvenTree-Instanz mit privater/LAN-Adresse (analog zu `HA_ALLOW_PRIVATE_ENDPOINT`). Ohne diese Freigabe blockiert der SSRF-Schutz Verbindungen zu internen Adressen. |

Verbindung (inkl. API-Token) und Verknüpfungen richtest du anschließend über die REST-API ein — Details siehe [Betriebsmittel & Inventar (InvenTree) — Für technische Nutzer / Self-Hoster](../user-guide/inventree.md#fuer-technische-nutzer-self-hoster).

---

## Wettervorhersage & Frost-Frühwarnung <!-- REQ-046 / Issue #392 --> {#wettervorhersage-frost-fruehwarnung}

Diese Variablen steuern die Wettervorhersage-Abholung und die darauf aufbauende proaktive Frost-Frühwarnung. Ohne `WEATHER_ENABLED=true` bleiben beide Funktionen vollständig deaktiviert — Standorte ohne konfigurierte Wetterquelle sind davon unabhängig ebenfalls nicht betroffen.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `WEATHER_ENABLED` | `false` | Nein | Kill-Switch für die gesamte Wetterfunktion (Quellenabholung + Frost-Frühwarnung). Details zur eigentlichen Quellenkonfiguration siehe [Wetterquellen je Standort](../user-guide/weather-sources.md). |
| `WEATHER_DEFAULT_PUBLIC_SOURCE` | `open-meteo` | Nein | Werkseitig voreingestellte öffentliche Wetterquelle für neue Standorte ohne explizite Auswahl. |
| `OPEN_METEO_ENABLED` | `true` | Nein | Instanzweiter Default für die Quelle Open-Meteo (keyless, EU-Fokus). Vom Platform-Admin pro Instanz über die Wetterdienste-Verwaltung überschreibbar (siehe [Wetterdienste konfigurieren](../user-guide/weather-services.md)) — diese Variable setzt nur den Ausgangswert. |
| `DWD_ENABLED` | `true` | Nein | Instanzweiter Default für die Quelle DWD/Bright Sky (Deutscher Wetterdienst). Ebenfalls Platform-Admin-überschreibbar. |
| `OPENWEATHERMAP_ENABLED` | `true` | Nein | Instanzweiter Default für die Quelle OpenWeatherMap. Ebenfalls Platform-Admin-überschreibbar. |
| `FROST_FORECAST_HORIZON_DAYS` | `2` | Nein | Vorhersage-Zeitraum in Tagen ab heute (inklusive), der auf einen erwarteten Frosttag geprüft wird — Standard deckt heute plus den Folgetag ab. |
| `FROST_FORECAST_THRESHOLD_CELSIUS` | `2.0` | Nein | Minimaltemperatur, ab der ein vorhergesagter Tag als Frosttag gilt. Bewusst **getrennt** vom reaktiven Schwellwert unten, mit einem etwas konservativeren (näher an 0 °C liegenden) Wert, da eine mehrtägige Vorhersage unsicherer ist als eine aktuelle Messung. |

Zum Vergleich — der bestehende **reaktive** Frost-Schwellwert (aktuell gemessene Temperatur, unverändert durch diese Erweiterung):

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `FROST_WARNING_THRESHOLD_CELSIUS` | `3.0` | Nein | Schwellwert für die reaktive Frost-Warnung (`binary_sensor.kp_{location}_frost_warning`), basierend auf der zuletzt gemessenen Lufttemperatur. |

---

## Klimanormalen (NASA POWER) <!-- REQ-041 --> {#klimanormalen-nasa-power}

Diese Variablen steuern die monatliche Hintergrund-Abholung der langjährigen Klima-Normalwerte (Abschnitt „Klima am Standort") über die keyless NASA-POWER-Reanalyse-Schnittstelle. Für die Abholung müssen sowohl `WEATHER_ENABLED` als auch `NASA_POWER_CLIMATE_ENABLED` aktiv sein.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `NASA_POWER_CLIMATE_ENABLED` | `true` | Nein | Eigener Kill-Switch für den monatlichen Klimanormalen-Task, unabhängig vom allgemeinen `WEATHER_ENABLED` — beide müssen aktiv sein, damit der Task läuft. |
| `NASA_POWER_BASE_URL` | `https://power.larc.nasa.gov/api/temporal` | Nein | Basis-URL der NASA-POWER-API. Nur für Self-Hoster mit abweichender Netzwerk-/Proxy-Konfiguration relevant. |
| `NASA_POWER_CLIMATE_TTL_DAYS` | `180` | Nein | Klimanormalen ändern sich kaum; ein bereits abgeholter Datensatz wird erst nach Ablauf dieser TTL erneut abgeholt — hält den monatlichen Task idempotent und schont die NASA-POWER-API. |
| `NASA_POWER_DATA_LATENCY_DAYS` | `7` | Nein | Betrifft die separate Tageswerte-Abholung (nicht die Klimanormalen): Anzahl Tage, die NASA POWER für die Qualitätskontrolle seiner jüngsten Tageswerte benötigt. |
| `NASA_POWER_DAILY_DAYS_BACK` | `14` | Nein | Betrifft ebenfalls nur die Tageswerte-Abholung: Größe des Rückblick-Fensters in Tagen. |

!!! note "Betrifft nur Freiland- und Gewächshaus-Standorte mit GPS-Koordinaten"
    Klimanormalen werden ausschließlich für Standorte vom Typ **Außenbereich** oder **Gewächshaus** mit hinterlegten GPS-Koordinaten materialisiert — für Innenraum-Standorte sind sie ohne Nutzen und werden nicht abgeholt. NASA POWER ist keyless nutzbar; die Daten unterliegen der CC-BY-4.0-Lizenz (Attribution wird automatisch mit ausgeliefert, siehe [Klima am Standort](../user-guide/weather-sources.md#klima-am-standort)). <!-- REQ-041 -->

---

## Winterhärtezonen (USDA) <!-- REQ-039 --> {#winterhaertezonen-usda}

Diese Variable steuert die vierteljährliche Hintergrund-Aktualisierung der automatisch aus den Klimanormalen abgeleiteten Winterhärtezone eines Standorts (siehe [Klimazonen & Winterhärte](../guides/climate-zones.md)). Die Ableitung baut auf den Klimanormalen auf — der zugehörige Task läuft daher nur, wenn zusätzlich sowohl `WEATHER_ENABLED` als auch `NASA_POWER_CLIMATE_ENABLED` aktiv sind.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `HARDINESS_ZONE_REFRESH_ENABLED` | `true` | Nein | Eigener Kill-Switch für den vierteljährlichen Winterhärtezonen-Task (1. Januar/April/Juli/Oktober, 05:00 UTC), unabhängig von `NASA_POWER_CLIMATE_ENABLED` — beide müssen aktiv sein, damit der Task läuft. Manuell gesetzte Zonen (`hardiness_zone_source: manual`) werden vom Task nie überschrieben. |

!!! note "Betrifft nur Freiland- und Gewächshaus-Standorte mit GPS-Koordinaten und vorhandenen Klimanormalen"
    Wie die Klimanormalen selbst wird die Winterhärtezone nur für Standorte vom Typ **Außenbereich** oder **Gewächshaus** mit GPS-Koordinaten berechnet — und erst, sobald für diesen Standort bereits mindestens ein Klimanormalen-Datensatz mit verwertbarer Minimaltemperatur vorliegt. Ein sofortiges manuelles Auslösen (unabhängig von diesem Zeitplan) ist über die API möglich, siehe [API-Referenz — Winterhärtezonen](api-reference.md#winterhaertezonen-usda). <!-- REQ-039 -->

---

## Bewässerungsbedarf (ET₀) <!-- REQ-037 --> {#bewaesserungsbedarf-et0}

Diese Variablen steuern den täglichen Hintergrund-Task, der aus den Wetterdaten eines Freiland- oder Gewächshaus-Standorts die Referenz-Evapotranspiration (FAO-56, ET₀) und daraus den Netto-Bewässerungsbedarf je Pflanzdurchlauf berechnet. Der Task benötigt zusätzlich `WEATHER_ENABLED=true` — ohne abgeholte Wetterdaten gibt es nichts zu berechnen. Ergebnis und Verhalten für Endnutzer sind unter [Gießprotokoll: Vorgeschlagene Gießmenge](../user-guide/watering-log.md#vorgeschlagene-giessmenge) und [Pflegeerinnerungen: Warum eine Erinnerung ausbleiben kann](../user-guide/care-reminders.md#warum-eine-erinnerung-ausbleiben-kann) beschrieben.

<!-- Quelle: src/backend/app/config/settings.py (irrigation_demand_enabled, irrigation_root_zone_depth_mm) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `IRRIGATION_DEMAND_ENABLED` | `true` | Nein | Eigener Kill-Switch für den täglichen `compute_irrigation_demand`-Task (06:15 Uhr), unabhängig vom allgemeinen `WEATHER_ENABLED` — beide müssen aktiv sein, damit der Task läuft. |
| `IRRIGATION_ROOT_ZONE_DEPTH_MM` | `300.0` | Nein | Angenommene effektive Wurzelzonentiefe in Millimeter Boden. Wird verwendet, um die Wasserhaltekapazität eines Substrats (in Prozent) in eine Millimeter-Obergrenze für den Netto-Bewässerungsbedarf umzurechnen — verhindert eine rechnerisch zu hohe Tagesempfehlung bei sehr trockenen Ausgangsbedingungen. |

!!! note "Nur Freiland- und Gewächshaus-Standorte, keine neuen REST-Endpunkte"
    Der Bewässerungsbedarf wird ausschließlich für Standorte vom Typ **Außenbereich** oder **Gewächshaus** mit hinterlegten GPS-Koordinaten berechnet — Innenraum-Standorte bleiben beim intervallbasierten Gießplan (REQ-022). Es gibt keinen eigenen REST-Endpunkt dafür; das Ergebnis fließt über den bestehenden Gießmengen-Vorschlag (`suggest_volume`) und die Pflegeerinnerungs-Engine in die Oberfläche ein.

!!! info "Berechnungsgrundlage: aquacropeto (BSD-3-Clause)"
    Die FAO-56-Penman-Monteith- und Hargreaves-Formeln für ET₀ werden über die Python-Bibliothek `aquacropeto` (PyPI-Paket `aquacropeto`, BSD-3-Clause-Lizenz) berechnet — keine ShareAlike-/Copyleft-Pflichten für den Kamerplanter-Code. Details siehe `NOTICE.md` im Projekt-Root.

---

## Health-Endpunkt und Build-Kennung {#health-endpunkt}

Der unauthentifizierte Endpunkt `GET /api/health` kann beantworten, welcher Build gerade läuft. Weil er unauthentifiziert ist, ist diese Auskunft standardmäßig abgeschaltet und der Endpunkt mengenbegrenzt.

<!-- Quelle: src/backend/app/config/settings.py (health_expose_build_revision, build_revision, rate_limit_health), src/backend/app/main.py (root_health) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `HEALTH_EXPOSE_BUILD_REVISION` | `false` (Helm-Chart setzt `true`) | Nein | Ob `GET /api/health` das Feld `build_revision` überhaupt ausliefert. Bei `false` fehlt der Schlüssel vollständig in der Antwort. Der **Anwendungs**-Standard bleibt `false` — `helm/kamerplanter/values.yaml` setzt für Kubernetes-Installationen seit #1236 `true`, damit der Auslieferungsstand prüfbar ist. |
| `BUILD_REVISION` | *(leer)* | Nein | Der vollständige Git-Commit, aus dem das Image gebaut wurde. Wird beim Container-Build eingebacken (`docker-publish.yml` reicht ihn als Build-Argument in das Dockerfile); von Hand setzen musst du ihn nur, wenn du selbst baust. |
| `RATE_LIMIT_HEALTH` | `60/minute` | Nein | Mengenbegrenzung für `GET /api/health`, je Client-IP. Die Kubernetes-Proben zeigen auf `/api/v1/health/live` und `/api/v1/health/ready` und sind davon **nicht** betroffen. |

!!! warning "Warum die Build-Kennung standardmäßig fehlt"

    Öffentlich ist nicht der Commit-Hash — das Repository ist ohnehin offen —,
    sondern die Zuordnung *dieser Host läuft auf jenem Commit*. Aus ihr folgt
    der exakte Rückstand gegenüber dem Entwicklungsstand und damit die Liste der
    Fehlerbehebungen, die dieser Instanz fehlen. Aktiviere das Feld deshalb
    bewusst — etwa auf einer Instanz, die ohnehin nur im eigenen Netz erreichbar
    ist, oder für die Dauer einer Fehlersuche. <!-- #1210 -->

**Drei unterscheidbare Antwortzustände**, die nicht verwechselt werden dürfen:

| Antwort | Bedeutung |
|---|---|
| Der Schlüssel `build_revision` **fehlt** | `HEALTH_EXPOSE_BUILD_REVISION` ist `false`. Bewusste Konfiguration, kein Defekt. |
| `"unknown"` | Auskunft ist erlaubt, aber es ist keine Revision eingebacken (Entwicklungs-Image, ungestempelter Build). |
| Ein 7- bis 40-stelliger Hexadezimal-Wert | Die echte Antwort. Ein von `docker-publish.yml` gebautes Image meldet den vollen 40-stelligen SHA; ein selbst gebautes Image mit `BUILD_REVISION=$(git rev-parse --short HEAD)` meldet entsprechend weniger. |

Der Wert wird vor der Ausgabe gegen `^[0-9a-f]{7,40}$` geprüft (nach dem Abschneiden von Leerraum, damit ein in YAML umbrochener oder in der Shell gequoteter Wert überlebt). Alles andere wird zu `"unknown"` — nie zu einem erfundenen oder abgeleiteten Wert.

!!! note "Betriebssignal, keine Attestierung"
    `build_revision` sagt, was die Instanz über sich behauptet. Wer das Deployment kompromittiert hat, kann sie jeden Hash melden lassen. Der belastbare Nachweis bleibt `gh attestation verify` zusammen mit dem Digest aus `.status.containerStatuses[].imageID` des Pods — siehe [CI/CD — Prüfungen entlang der Auslieferungskette](../deployment/ci-cd.md#pruefungen-auslieferungskette).

---

## Rate Limiting

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `RATE_LIMIT_AUTH` | `20/minute` | Nein | Rate-Limit für Authentifizierungsendpunkte |
| `TRUSTED_PROXY_HOPS` | `0` | **Ja, hinter zwei Proxys** | Wie viele Proxy-Adressen die eigene Infrastruktur an `X-Forwarded-For` anhängt, von rechts gezählt. `0` = Client → nginx → Backend (Dev/E2E); `1` = Client → Traefik → nginx → Backend (das Helm-Chart setzt diesen Wert). Zu niedrig löst jeden Aufrufer auf den nächsten Proxy auf — der Device-Pairing-Lockout sperrt dann alle Nutzer gleichzeitig und IP-Allowlist-Service-Accounts scheitern; zu hoch liest Einträge, die ein Aufrufer fälschen kann. |
| `RATE_LIMIT_GENERAL` | `100/minute` | Nein | Rate-Limit für allgemeine API-Endpunkte |
| `RATE_LIMIT_HEALTH` | `60/minute` | Nein | Rate-Limit für `GET /api/health` — siehe [Health-Endpunkt und Build-Kennung](#health-endpunkt) |

**Format:** `[anzahl]/[einheit]` — Einheiten: `second`, `minute`, `hour`, `day`

---

## Verschachtelte Konfiguration (GBIF)

GBIF-Einstellungen können über den Unterstrich-Doppelpunkt-Delimiter verschachtelt werden:

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `GBIF__BASE_URL` | `https://api.gbif.org/v1` | GBIF-API-Basis-URL |
| `GBIF__RATE_LIMIT_PER_MINUTE` | `60` | Anfragen pro Minute an GBIF |
| `GBIF__HTTP_TIMEOUT` | `30` | Timeout für GBIF-Anfragen (Sekunden) |

---

## Foto-Identifikation (REQ-029)

Diese Variablen konfigurieren die optionale Pflanzenerkennung per Foto. Wenn keine der API-Schlüssel gesetzt ist, ist das Feature vollständig deaktiviert — alle Kamera-Schaltflächen sind ausgeblendet und es wird keine Einwilligung abgefragt.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `PLANTNET_API_KEY` | — | Nein | API-Schlüssel für Pl@ntNet (Free-Tier: ≤ 500 Identifikationen/Tag). Registrierung unter [my.plantnet.org](https://my.plantnet.org). |
| `PLANTNET_ENABLED` | `true` | Nein | Schaltet den Pl@ntNet-Adapter komplett ab, auch wenn `PLANTNET_API_KEY` gesetzt ist. Auf `false` setzen, um Pl@ntNet trotz vorhandenem Key zu deaktivieren (z. B. bei ausschließlicher Nutzung der selbst-gehosteten DINOv2-Erkennung). |
| `PLANTNET_BASE_URL` | `https://my-api.plantnet.org/v2` | Nein | Basis-URL der Pl@ntNet-API. Nur für Self-Hosting oder Test-Endpunkte ändern. |
| `PLANT_ID_API_KEY` | — | Nein | API-Schlüssel für Plant.id (Kindwise) — ein zusätzlicher, rein Betreiber-initiierter Cloud-Adapter (niemals automatisch primär, anders als Pl@ntNet). |
| `PLANT_ID_BASE_URL` | `https://plant.id/api/v3` | Nein | Basis-URL der Plant.id-API. |
| `INFERENCE_SERVICE_ENABLED` | `false` | Nein | Aktiviert den selbst-gehosteten DINOv2-Erkennungspfad (REQ-029-A). Details zur vollständigen Inbetriebnahme (VectorDB, Referenz-Index-Befüllung, Aktivierungsreihenfolge) siehe [Bilderkennung in Betrieb nehmen](../deployment/inference-service.md). |
| `INFERENCE_SERVICE_URL` | `http://kamerplanter-recognition:8000` | Nein | Interne URL des Inferenz-Service. |
| `IDENTIFICATION_PRIMARY_ADAPTER` | `plantnet` | Nein | Bevorzugter Adapter. Mögliche Werte: `plantnet`, `local_embedding` (DINOv2, sobald `INFERENCE_SERVICE_ENABLED=true`). |
| `IDENTIFICATION_HTTP_TIMEOUT` | `60` | Nein | HTTP-Timeout (Sekunden) für den externen Identifikations-Aufruf (Pl@ntNet-Upload + serverseitige ML-Inferenz kann den früheren 30-Sekunden-Standard unter Last überschreiten). |
| `IDENTIFICATION_CONFIDENCE_AUTO_ACCEPT` | `0.85` | Nein | Übereinstimmungsschwelle (0–1), ab der ein Vorschlag als „sehr sicher" hervorgehoben wird. |
| `IDENTIFICATION_CONFIDENCE_MIN_SHOW` | `0.10` | Nein | Mindest-Übereinstimmung (0–1) für die Anzeige eines Vorschlags. Ergebnisse darunter werden gefiltert. |
| `IDENTIFICATION_MAX_IMAGE_SIZE_MB` | `5` | Nein | Maximale Bildgröße in Megabyte. Größere Bilder werden mit HTTP 400 abgelehnt. |
| `IDENTIFICATION_MAX_IMAGE_DIMENSION` | `1024` | Nein | Längste Kante (px), auf die das Nutzerbild vor dem Upload an den Adapter herunterskaliert wird. Kleiner = schnellerer Upload und weniger Drittanbieter-Bandbreite. |
| `IDENTIFICATION_RATE_LIMIT_PER_USER_DAY` | `50` | Nein | Maximale Anfragen pro Nutzer pro Tag (SEC-003-Untergrenze, verhindert dass ein einzelnes Konto das geteilte Free-Tier-Kontingent aufbraucht). `0` verwendet stattdessen das Adapter-Standard-Limit (500 bei Pl@ntNet). |
| `IDENTIFICATION_EXTERNAL_IN_LIGHT_MODE` | `false` | Nein | Betreiber-Opt-in für den *externen* Erkennungspfad (Pl@ntNet) im [Light-Modus](../user-guide/light-mode.md). Im Light-Modus gibt es kein Einwilligungssystem — ein Foto an Dritte zu senden erfordert daher eine bewusste Betreiber-Entscheidung. Solange diese Variable `false` bleibt, ist im Light-Modus ausschließlich der selbst-gehostete `local_embedding`-Pfad nutzbar (sobald `INFERENCE_SERVICE_ENABLED=true` gesetzt ist). |
| `REFERENCE_CONTRIBUTION_RATE_LIMIT_PER_USER_DAY` | `20` | Nein | Maximale Anzahl Referenzbild-Beiträge (`POST /identification/reference`) pro Nutzer pro Tag — schützt den Erkennungsindex vor Missbrauch/Flutung durch ein einzelnes Konto. `0` deaktiviert das Limit. Nur relevant, wenn die selbst-gehostete DINOv2-Erkennung aktiv ist (siehe [Self-Hosted-Erkennung mit DINOv2](../user-guide/plant-identification.md#self-hosted-erkennung-mit-dinov2)). <!-- Issue #447 --> |

!!! warning "Pl@ntNet nur für nicht-kommerzielle Nutzung"
    Der Pl@ntNet Free-Tier ist für nicht-kommerzielle Nutzung zugelassen. Für kommerzielle Instanzen die Nutzungsbedingungen unter [my.plantnet.org](https://my.plantnet.org) prüfen.

!!! tip "Kubernetes Secrets"
    Der `PLANTNET_API_KEY` sollte als Kubernetes Secret hinterlegt werden:
    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: kamerplanter-identification
    type: Opaque
    stringData:
      PLANTNET_API_KEY: "dein-api-schluessel"
    ```

### Feature-Toggle-Logik

```
PLANTNET_API_KEY gesetzt?
  ├── Ja  → Pl@ntNet aktiv (Artbestimmung, ≤ 500 IDs/Tag)
  └── Nein → Feature vollständig deaktiviert
             (Kamera-Buttons ausgeblendet, kein Consent-Dialog)
```

---

## Schädlingserkennung (REQ-044) {#schaedlingserkennung-req-044}

Diese Variablen konfigurieren die optionale bildbasierte Schädlingserkennung. Das Feature ist standardmäßig deaktiviert — ohne gesetztes `PEST_DETECTION_ENABLED=true` ist der Button „Auf Schädlinge prüfen" ausgeblendet und die App voll funktionsfähig.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `PEST_DETECTION_ENABLED` | `false` | Nein | Gesamtschalter. Auf `true` setzen, um die Funktion zu aktivieren. |
| `PEST_DETECTION_SYMPTOM_ENABLED` | `true` | Nein | Schadbild-/Symptom-Erkennung (Modus 2) ein/aus. Aktiv wenn `PEST_DETECTION_ENABLED=true`. |
| `PEST_DETECTION_DETECTOR_ENABLED` | `false` | Nein | Direkt-Detektor (Modus 1, Phase 2) ein/aus. Erfordert trainierten ONNX-Detektor. |
| `PEST_DETECTION_DEMO_ENABLED` | `false` | Nein | Demo-Adapter (kein externer Service, kein echtes Modell). Zeigt den kompletten UI-Ablauf mit klar gekennzeichneten Platzhalter-Befunden, während das trainierte Backend extern blockiert ist. Nur zur Vorschau — nicht für echte Entscheidungen. Aktiv, wenn zusätzlich `PEST_DETECTION_ENABLED=true`. |
| `PEST_DETECTION_CLOUD_ENABLED` | `false` | Nein | Cloud-Adapter (Kindwise) ein/aus. Erfordert `PEST_DETECTION_CLOUD_API_KEY`. |
| `PEST_DETECTION_CLOUD_API_KEY` | — | Nein | API-Key für Kindwise (Cloud-Erkennung). Ohne Key ist der Cloud-Adapter deaktiviert. |
| `PEST_DETECTION_PRIMARY_ADAPTER` | `local_pest_symptom` | Nein | Bevorzugter Adapter. Mögliche Werte: `local_pest_symptom`, `local_pest_detector` (Phase 2), `kindwise`. |
| `PEST_DETECTION_MAX_IMAGE_SIZE_MB` | `8` | Nein | Maximale Bildgröße in Megabyte. Größere Bilder werden mit HTTP 400 abgelehnt. |

!!! note "Self-Hosted-First"
    Der lokale Adapter (`local_pest_symptom`) benötigt keinen API-Key und erfordert keine Nutzereinwilligung. Cloud-Erkennung ist opt-in und einwilligungspflichtig (Consent-Zweck `pest_detection_cloud`).

---

## CV-Krankheitsdiagnose (REQ-038) {#cv-krankheitsdiagnose-req-038}

Diese Variablen konfigurieren die optionale, self-hosted Foto-Diagnose für **Krankheiten und Nährstoffmängel** (abgegrenzt von der [Schädlingserkennung](#schaedlingserkennung-req-044) oben). Das Feature ist standardmäßig deaktiviert; ohne `CV_DIAGNOSIS_ENABLED=true` bleibt der API-Endpunkt `/status` auf `available: false`, die App läuft uneingeschränkt weiter.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `CV_DIAGNOSIS_ENABLED` | `false` | Nein | Gesamtschalter. Auf `true` setzen, um die Funktion zu aktivieren. |
| `CV_CLASSIFIER_CONFIDENCE_SHOW` | `0.10` | Nein | Mindest-Konfidenz (0–1) für die Anzeige eines Treffers. Ergebnisse darunter werden verworfen. |
| `CV_CLASSIFIER_CONFIDENCE_HIGHLIGHT` | `0.75` | Nein | Konfidenz-Schwelle (0–1), ab der ein Treffer visuell hervorgehoben wird. Löst **kein** automatisches Anlegen aus. |
| `CV_PHENOTYPE_ENABLED` | `true` | Nein | PlantCV-Phänotyp-Kennzahlen (Blattfläche, Grün-Index, Verfärbungsanteil) im Inference-Service ein/aus. |
| `CV_DIAGNOSIS_MAX_IMAGE_SIZE_MB` | `5` | Nein | Maximale Bildgröße in Megabyte. Größere Bilder werden mit HTTP 413 abgelehnt. |

Der Klassifikator läuft im bestehenden Inference-Service und nutzt die dort bereits konfigurierte Anbindung (`INFERENCE_SERVICE_URL`, `INTERNAL_SERVICE_TOKEN`) — es sind keine zusätzlichen Verbindungsvariablen nötig.

!!! note "Self-Hosted, kein Cloud-Adapter"
    Anders als bei der Schädlingserkennung gibt es für die CV-Krankheitsdiagnose (Stand dieser Version) **keinen** Cloud-Adapter — Fotos verlassen die Instanz nie. Die Einwilligung `plant_diagnosis` ist trotzdem erforderlich (Voll-Modus), weil ein Foto verarbeitet wird (siehe [Datenschutz & DSGVO](../user-guide/privacy.md#ki-krankheitsdiagnose-plant_diagnosis)).

!!! info "Lizenzhinweise"
    Das Modell wird auf dem CC-BY-4.0-lizenzierten PlantDoc-Datensatz fine-getunt; die Phänotyp-Pipeline nutzt PlantCV (MPL-2.0). Vollständige Attributionen: [`NOTICE.md`](https://github.com/nolte/kamerplanter/blob/main/NOTICE.md#cv-disease-diagnosis-req-038).

---

## Browser Push / PWA (VAPID)

Diese Variablen aktivieren den Browser-Push-Benachrichtigungskanal (`channel_key: "pwa"`). Sind alle drei Variablen leer, ist der Kanal deaktiviert — die Anwendung bleibt vollständig funktionsfähig, Nutzer sehen dann die Meldung "Nicht konfiguriert" in den Benachrichtigungseinstellungen.

!!! tip "Schritt-für-Schritt-Anleitung"
    Der Guide [Browser-Push einrichten](../guides/browser-push-setup.md) führt durch das Erzeugen des Schlüsselpaars, das Eintragen in Docker Compose bzw. Kubernetes und die Verifikation der Einrichtung.

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `VAPID_PUBLIC_KEY` | — | Nein* | VAPID-Public-Key (Base64url, 87 Zeichen). Wird an den Browser übermittelt und in der PWA-Subscription verwendet. |
| `VAPID_PRIVATE_KEY` | — | Nein* | VAPID-Private-Key (Base64url oder PEM). **Nur serverseitig** — niemals im Frontend oder in Logs ausgeben. |
| `VAPID_CONTACT_EMAIL` | — | Nein* | Kontakt-E-Mail für den Push-Service (Format: `mailto:admin@example.com`). Von den Push-Diensten (FCM, APNS, Mozilla) bei Problemen genutzt. |
| `PWA_PUSH_ENDPOINT_ALLOWED_HOSTS` | — (leer) | Nein | SSRF-Härtung (SEC-001): Kommagetrennte Liste erlaubter Host-Suffixe für Web-Push-Endpunkte, z. B. `fcm.googleapis.com,updates.push.services.mozilla.com`. Leer (Standard) fällt auf eine HTTPS-Pflicht plus Ablehnung privater IP-Adressen zurück, sodass selbst gehostete Push-Server weiterhin funktionieren. |

*Alle drei `VAPID_*`-Variablen müssen gesetzt sein, damit der Browser-Push-Kanal aktiv wird. Fehlt eine Variable, bleibt der Kanal deaktiviert. `PWA_PUSH_ENDPOINT_ALLOWED_HOSTS` ist unabhängig davon optional.

### Schlüsselpaar generieren

```bash
npx web-push generate-vapid-keys
```

Ausgabe:
```
Public Key:
BNm...

Private Key:
8Kv...
```

Alternativ mit `pywebpush` (Python) — `b64urlencode` ist nötig, da `v.public_key`/`v.private_key` Schlüsselobjekte sind und erst die Serialisierung die Base64url-Strings liefert:
```bash
pip install pywebpush
python3 - <<'PY'
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from cryptography.hazmat.primitives import serialization

v = Vapid()
v.generate_keys()
pub_raw = v.public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
)
priv_raw = v.private_key.private_numbers().private_value.to_bytes(32, "big")
pub, priv = b64urlencode(pub_raw), b64urlencode(priv_raw)
assert pub_raw[0] == 0x04 and len(pub_raw) == 65 and len(pub) == 87, "invalid public key"
assert len(priv_raw) == 32 and len(priv) == 43, "invalid private key"
print("VAPID_PUBLIC_KEY =", pub)
print("VAPID_PRIVATE_KEY=", priv)
PY
```

!!! danger "Private Key serverseitig halten"
    Der `VAPID_PRIVATE_KEY` darf **niemals** im Frontend, in Logs oder in öffentlichen Konfigurationsdateien erscheinen. Speichere ihn als Kubernetes Secret oder Docker-Secret — analog zu `JWT_SECRET_KEY`.

!!! tip "Kubernetes Secret für VAPID"
    ```yaml
    apiVersion: v1
    kind: Secret
    metadata:
      name: kamerplanter-vapid
    type: Opaque
    stringData:
      VAPID_PUBLIC_KEY: "BNm..."
      VAPID_PRIVATE_KEY: "8Kv..."
      VAPID_CONTACT_EMAIL: "mailto:admin@example.com"
    ```

---

## Saison- & Überwinterungs-Automatik

Diese Variablen steuern die Schwellwerte der automatischen Saison-/Überwinterungserkennung (siehe [Saison-Automatik](../user-guide/season-automation.md)). Sie betreffen nur die Live- und Klimatologie-Stufen der Erkennungs-Kaskade — der Kalender-Fallback ist davon unabhängig.

<!-- Quelle: src/backend/app/config/settings.py (season_pre_winter_temp_c, season_frost_temp_c, season_spring_temp_c, season_signal_threshold_days, season_state_eval_enabled) -->

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `SEASON_PRE_WINTER_TEMP_C` | `5.0` | Nein | Temperaturschwelle (°C) für den Übergang von „Wachstumsphase" zu „Winter kündigt sich an". |
| `SEASON_FROST_TEMP_C` | `2.0` | Nein | Temperaturschwelle (°C) für den Übergang in die Winterruhe. |
| `SEASON_SPRING_TEMP_C` | `10.0` | Nein | Temperaturschwelle (°C) für den Übergang in die Frühjahrs-Rückholung. |
| `SEASON_SIGNAL_THRESHOLD_DAYS` | `3` | Nein | Anzahl aufeinanderfolgender Signaltage, bevor ein Übergang ausgelöst wird (Oszillationsschutz). |
| `SEASON_STATE_EVAL_ENABLED` | `true` | Nein | Schalter für den täglichen Auswertungs-Task. Auf `false` setzen, um die Saison-Automatik komplett zu deaktivieren. |

---

## Fehler-Tracking (optional)

Meldet Laufzeitfehler an einen Sentry-protokollkompatiblen Tracker (Referenz: GlitchTip). **Ist `SENTRY_DSN` leer, passiert nichts** — das SDK wird nie initialisiert, das Frontend lädt sein SDK-Bündel nicht einmal herunter. Ausführlich: [Fehler-Tracking](../deployment/fehler-tracking.md).

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `SENTRY_DSN` | — (leer) | Nein | Ingest-URL des Trackers, Form `https://<public-key>@host/<projekt-id>`. Enthält nur einen öffentlichen Schlüssel, kein Geheimnis. Leer = abgeschaltet. |
| `SENTRY_ENVIRONMENT` | `development` | Nein | Stufe aus dem festen Vokabular `development`, `e2e`, `staging`, `production`. Alarmregeln filtern auf genau diese Werte; ein abweichender Wert meldet trotzdem, wird aber protokolliert. |
| `SENTRY_RELEASE` | Komponente + Version | Nein | Image-Tag oder Commit-SHA. Ohne sie sind Regressionserkennung und die Zuordnung „welches Deployment war es" unmöglich. |
| `SENTRY_SAMPLE_RATE` | `1.0` | Nein | Anteil der gemeldeten Ereignisse (0–1). `1.0` ist eine bewusste Entscheidung für dieses Aufkommen, keine unangetastete Voreinstellung. Unlesbare Werte fallen auf `1.0` zurück. |

Alle vier Variablen gelten für Backend, Celery Worker und Beat, Inference- und Knowledge-Service sowie das Frontend. Im Frontend werden sie zur Laufzeit über `runtime-config.js` eingespeist, nicht ins Build gebacken — ein Image bedient damit alle Stufen.

!!! danger "Selbst gehosteter Tracker: NetworkPolicy nicht vergessen"
    Unter Kubernetes schließt die Egress-Regel des Backends die privaten Adressbereiche aus. Ein Tracker im eigenen Cluster oder LAN braucht deshalb eine zusätzliche Egress-Regel — sonst werden Ereignisse stillschweigend verworfen.

## Vollständiges .env-Beispiel

```bash
# Datenbank
ARANGO_ROOT_PASSWORD=sicheres-root-passwort
ARANGODB_HOST=arangodb
ARANGODB_PORT=8529
ARANGODB_DATABASE=kamerplanter
ARANGODB_USERNAME=root
ARANGODB_PASSWORD=sicheres-root-passwort

# Cache / Queue
REDIS_URL=redis://valkey:6379/0

# Sicherheit (alle drei sind Pflicht-Secrets, Startup-Gate in Produktion)
JWT_SECRET_KEY=erzeugen-mit-openssl-rand-hex-32
FERNET_KEY=erzeugen-mit-Fernet.generate_key
ERASURE_TOMBSTONE_SALT=erzeugen-mit-openssl-rand-hex-32
REQUIRE_EMAIL_VERIFICATION=false

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Betriebsmodus
KAMERPLANTER_MODE=full
DEBUG=false

# E-Mail (Entwicklung)
EMAIL_ADAPTER=console

# mDNS Discovery (LAN-only, opt-in)
# MDNS_ENABLED=false
# INSTANCE_ID=

# Optionale externe APIs
PERENUAL_API_KEY=
HA_URL=
HA_ACCESS_TOKEN=

# Knowledge Service — Re-Ranking (leer = deaktiviert)
RERANKER_URL=
RERANKER_INITIAL_K=20
RERANKER_TOP_K=5

# KI-Assistent (instanzweit deaktiviert, solange nicht explizit aktiviert)
AI_FEATURES_ENABLED=false
KNOWLEDGE_SERVICE_ENABLED=false
KNOWLEDGE_SERVICE_URL=http://knowledge-service:8000

# Foto-Identifikation (leer = Feature deaktiviert)
# PLANTNET_API_KEY=
# IDENTIFICATION_RATE_LIMIT_PER_USER_DAY=50

# Browser Push / PWA (leer = Kanal deaktiviert)
# VAPID_PUBLIC_KEY=
# VAPID_PRIVATE_KEY=
# VAPID_CONTACT_EMAIL=mailto:admin@example.com
```

---

## Object Storage (NFR-013)

Diese Variablen konfigurieren den Storage-Adapter für Binärdaten (Fotos, Importe, Exporte). Das aktive Backend wird durch `STORAGE_BACKEND` bestimmt. Standardmäßig ist `local-fs` aktiv — keine weitere Konfiguration nötig.

Weitere Hintergrundinformationen: [Speicher konfigurieren (Object Storage)](../user-guide/object-storage.md) und [Helm Charts — Storage-Konfiguration](../deployment/helm.md#storage-konfiguration-nfr-013).

### Allgemeine Storage-Einstellungen

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `STORAGE_BACKEND` | `local-fs` | Nein | Aktives Backend: `local-fs` oder `s3` |
| `STORAGE_MAX_FILE_SIZE_MB` | `25` | Nein | Maximale Upload-Größe in Megabyte (gilt für alle Kategorien, überschreibbar per Kategorie) |
| `STORAGE_PRESIGN_TTL_SECONDS` | `900` | Nein | Gültigkeitsdauer von Pre-Signed URLs in Sekunden (max. 3600) |
| `STORAGE_ALLOWED_MIME_TYPES` | *(Liste)* | Nein | Kommagetrennte globale Whitelist erlaubter MIME-Types |
| `STORAGE_ALLOWED_MIME_TYPES_<CATEGORY>` | *(pro Kategorie)* | Nein | Kategorie-spezifische Whitelist, z. B. `STORAGE_ALLOWED_MIME_TYPES_IMPORT=text/csv` |
| `STORAGE_VIRUS_SCAN_ENABLED` | `false` | Nein | Virenscan via ClamAV-REST-Wrapper aktivieren |
| `STORAGE_VIRUS_SCAN_ENDPOINT` | *(leer)* | Nein | URL des ClamAV-REST-Wrappers |
| `STORAGE_STRIP_EXIF` | `true` | Nein | Entfernt EXIF-/GPS-Metadaten aus Bild-Uploads global beim Speichern (NFR-013 §5.1). Es gibt **keine** Kategorie-spezifische Override-Variable — anders als bei den MIME-Whitelists ist dies ein einzelner, globaler Schalter. |
| `STORAGE_TENANT_QUOTA_MB` | `2048` | Nein | Speicherkontingent pro Mandant in Megabyte. `0` deaktiviert das Kontingent (unbegrenzt). |
| `STORAGE_MAX_PHOTOS_PER_INSTANCE` | `50` | Nein | Maximale Anzahl Galerie-Fotos je Pflanzeninstanz (REQ-034). `0` deaktiviert das Limit. |

**Standard-MIME-Whitelist pro Kategorie:**

| Kategorie | Erlaubte MIME-Types | Max-Größe |
|-----------|---------------------|-----------|
| `diary`, `ipm`, `harvest`, `post_harvest`, `task`, `id_recognition`, `plant` | `image/jpeg`, `image/png`, `image/webp`, `image/heic` | 25 MB |
| `import` | `text/csv`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 50 MB |
| `export` | `application/pdf`, `text/csv`, `application/zip` | 200 MB |
| `tenant_export` | `application/zip` | 5 GB |

### Backend: Lokales Dateisystem (`local-fs`)

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `STORAGE_LOCAL_FS_ROOT` | `/data/attachments` | Nein | Mount-Pfad innerhalb des Containers |
| `STORAGE_LOCAL_FS_PUBLIC_BASE_URL` | *(leer)* | Ja* | Vollständige URL des Token-Download-Endpunkts, z. B. `https://api.kamerplanter.example.com/api/v1/attachments/token`. Muss auf `https://<host>/api/v1/attachments/token` zeigen. |
| `STORAGE_LOCALFS_SIGNING_SECRET` | *(ephemer)* | Ja** | Geheimer Schlüssel für Token-Signaturen. **Pflicht bei mehr als einer Replica**, sonst können Tokens von anderen Pods nicht validiert werden. |

*Pflicht, damit local-fs Token-Downloads einlösen kann.
**Pflicht bei Multi-Replica-Betrieb.

!!! warning "Signing-Secret als Kubernetes-Secret speichern"
    Der `STORAGE_LOCALFS_SIGNING_SECRET` ist ein kryptographisches Secret und darf nicht im Klartext in `values.yaml` oder Git committet werden. Anlegen als Kubernetes Secret:
    ```bash
    kubectl create secret generic kamerplanter-storage-signing \
      --from-literal=STORAGE_LOCALFS_SIGNING_SECRET="$(openssl rand -hex 32)" \
      --namespace kamerplanter
    ```

### Backend: S3-kompatibel (`s3`)

| Variable | Standard | Pflicht | Beschreibung |
|----------|---------|---------|-------------|
| `STORAGE_S3_ENDPOINT_URL` | *(leer)* | Ja | Vollständige Endpunkt-URL, z. B. `https://s3.eu-central-1.amazonaws.com` |
| `STORAGE_S3_REGION` | *(leer)* | Ja | Region, z. B. `eu-central-1` (auch bei MinIO erforderlich) |
| `STORAGE_S3_BUCKET` | *(leer)* | Ja | Bucket-Name (muss vorab angelegt sein) |
| `STORAGE_S3_ACCESS_KEY_ID` | *(leer)* | Ja | Access Key (aus External Secrets Operator — niemals im Klartext in Git) |
| `STORAGE_S3_SECRET_ACCESS_KEY` | *(leer)* | Ja | Secret Access Key (aus External Secrets Operator — niemals im Klartext in Git) |
| `STORAGE_S3_USE_PATH_STYLE` | `false` | Nein | `true` für MinIO und die meisten Nicht-AWS-Anbieter |
| `STORAGE_S3_FORCE_TLS` | `true` | Nein | Plain-HTTP verbieten; in Dev-Umgebungen auf `false` setzen |
| `STORAGE_S3_KMS_KEY_ID` | *(leer)* | Nein | Optionaler Customer-Managed Key für serverseitige Verschlüsselung (SSE-KMS) |
| `STORAGE_S3_ALLOW_PRIVATE_ENDPOINT` | `false` | Nein | `true` für in-Cluster MinIO, das nicht öffentlich erreichbar ist |

!!! danger "S3-Credentials niemals in Git oder values.yaml"
    `STORAGE_S3_ACCESS_KEY_ID` und `STORAGE_S3_SECRET_ACCESS_KEY` sind Secrets und werden ausschließlich über den External Secrets Operator (ESO) oder Kubernetes Secrets bereitgestellt. Weitere Details: [Helm Charts — Storage-Konfiguration](../deployment/helm.md#storage-konfiguration-nfr-013).

#### Beispielkonfigurationen

=== "AWS S3 (eu-central-1)"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=https://s3.eu-central-1.amazonaws.com
    STORAGE_S3_REGION=eu-central-1
    STORAGE_S3_BUCKET=mein-kamerplanter-bucket
    STORAGE_S3_ACCESS_KEY_ID=<aus Secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<aus Secret>
    STORAGE_S3_USE_PATH_STYLE=false
    STORAGE_S3_FORCE_TLS=true
    ```

=== "MinIO im Cluster"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=http://minio.kamerplanter.svc:9000
    STORAGE_S3_REGION=us-east-1
    STORAGE_S3_BUCKET=kamerplanter
    STORAGE_S3_ACCESS_KEY_ID=<aus Secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<aus Secret>
    STORAGE_S3_USE_PATH_STYLE=true
    STORAGE_S3_FORCE_TLS=false
    STORAGE_S3_ALLOW_PRIVATE_ENDPOINT=true
    ```

=== "Hetzner Object Storage"

    ```bash
    STORAGE_BACKEND=s3
    STORAGE_S3_ENDPOINT_URL=https://fsn1.your-objectstorage.com
    STORAGE_S3_REGION=eu-central
    STORAGE_S3_BUCKET=mein-kamerplanter-bucket
    STORAGE_S3_ACCESS_KEY_ID=<aus Secret>
    STORAGE_S3_SECRET_ACCESS_KEY=<aus Secret>
    STORAGE_S3_USE_PATH_STYLE=false
    STORAGE_S3_FORCE_TLS=true
    ```

---

## Häufige Fragen

??? question "Kann ich Umgebungsvariablen in Kubernetes als Secrets hinterlegen?"
    Ja. Verwenden Sie Kubernetes Secrets für sensible Werte (`ARANGODB_PASSWORD`, `JWT_SECRET_KEY`) und referenzieren Sie sie im Deployment-Manifest über `valueFrom.secretKeyRef`.

??? question "Wo kann ich prüfen, welche Werte das Backend tatsächlich verwendet?"
    Mit `DEBUG=true` loggt das Backend beim Start alle geladenen Einstellungen. Alternativ im Container:
    ```bash
    docker compose exec backend python -c "from app.config.settings import settings; print(settings.model_dump())"
    ```
    Passwörter und Secrets werden dabei nicht im Klartext angezeigt.

---

## Siehe auch

- [Konfigurationsmatrix](../deployment/konfigurationsmatrix.md) — Funktion → Dienste → Schalter → Pflicht-Secrets → Ressourcen in einer Tabelle
- [Betriebsprofile](../deployment/betriebsprofile.md) — Empfohlene Komponenten-Bündel für typische Anwendungsfälle
- [Lokales Setup](../development/local-setup.md)
- [Betriebs-Fehlerbehebung](../development/troubleshooting.md)
- [Deployment Kubernetes](../deployment/kubernetes.md)
- [Wetterquellen je Standort — Benutzerhandbuch](../user-guide/weather-sources.md)
- [Benachrichtigungen: Frost-Frühwarnung — Benutzerhandbuch](../user-guide/notifications.md#frost-fruehwarnung)
- [API-Referenz: CV-Krankheitsdiagnose](api-reference.md#cv-krankheitsdiagnose)
- [MCP-Server](../api/mcp-server.md)
- [Datenschutz & DSGVO — KI-Krankheitsdiagnose](../user-guide/privacy.md#ki-krankheitsdiagnose-plant_diagnosis)
- [Gießprotokoll: Vorgeschlagene Gießmenge — Benutzerhandbuch](../user-guide/watering-log.md#vorgeschlagene-giessmenge)
- [Betriebsmittel & Inventar (InvenTree) — Benutzerhandbuch](../user-guide/inventree.md)
- [Umgebungssteuerung & Aktorik — Benutzerhandbuch](../user-guide/actuator-control.md)
- [API-Referenz: Umgebungssteuerung & Aktorik](api-reference.md#umgebungssteuerung-aktorik)

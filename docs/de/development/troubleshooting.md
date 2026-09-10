# Betriebs-Fehlerbehebung

Lösungen zu häufigen technischen Problemen bei Installation, Betrieb und Nutzung von Kamerplanter — für Entwickler und Self-Hoster. Die Hinweise gelten für die Docker-Compose- und die Kubernetes-Umgebung.

!!! info "Suchst du Hilfe zu einer kranken Pflanze?"
    Diese Seite behandelt **technische Probleme** der Kamerplanter-Anwendung selbst (Installation, Login, Fehlermeldungen). Geht es stattdessen um Symptome an einer deiner Pflanzen (gelbe Blätter, Schädlinge, Wachstumsprobleme), findest du Hilfe unter [Meiner Pflanze geht es schlecht](../user-guide/plant-health-troubleshooting.md).

---

## Backend und Dienste starten nicht

??? question "Das Backend startet nicht — wie diagnostiziere ich das Problem?"
    **Schritt 1 — Logs prüfen:**

    === "Docker Compose"
        ```bash
        docker compose logs backend --tail=50
        ```

    === "Kubernetes"
        ```bash
        kubectl logs deployment/kamerplanter-backend --tail=50
        ```

    **Typische Fehlermeldungen und Lösungen:**

    | Fehlermeldung | Ursache | Lösung |
    |---------------|---------|--------|
    | `Connection refused: arangodb:8529` (Verbindung verweigert) | ArangoDB nicht erreichbar | ArangoDB-Container prüfen (`docker compose ps`) |
    | `AUTH_EXCEPTION` | Falsches ArangoDB-Passwort | `ARANGODB_PASSWORD` in `.env` prüfen |
    | `redis.exceptions.ConnectionError` (Verbindungsfehler) | Redis/Valkey nicht erreichbar | Redis-Container neu starten |
    | `pydantic_settings.SettingsError` | Fehlende Pflicht-Umgebungsvariable | Alle Pflicht-Variablen in `.env` setzen |
    | `Cannot import name 'X'` (Importfehler) | Fehlende Python-Abhängigkeit | `uv sync --locked` im Container |

??? question "ArangoDB-Container startet nicht"
    Häufigste Ursache ist ein Datenvolume aus einer alten ArangoDB-Version. Prüfe:

    ```bash
    docker compose logs arangodb --tail=30
    ```

    Wenn "Invalid version" oder "upgrade required" erscheint:

    ```bash
    docker compose down
    docker volume rm kamerplanter_arangodb_data
    docker compose up -d
    ```

    !!! danger "Datenverlust"
        Das Löschen des Volumes löscht alle Datenbankdaten. Nur in Entwicklungsumgebungen ohne wichtige Daten durchführen.

??? question "Celery-Worker läuft nicht — Aufgaben werden nicht generiert"
    Prüfe den Worker-Status:

    === "Docker Compose"
        ```bash
        docker compose logs celery-worker --tail=30
        docker compose logs celery-beat --tail=30
        ```

    === "Kubernetes"
        ```bash
        kubectl logs deployment/kamerplanter-celery-worker --tail=30
        ```

    Häufige Ursache: `REDIS_URL` nicht gesetzt oder Redis nicht erreichbar. Redis-Verbindung testen:

    ```bash
    docker compose exec valkey valkey-cli ping
    # Erwartete Antwort: PONG
    ```

---

## Datenbankprobleme

??? question "Datenbank-Collections fehlen oder Fehler 'collection not found'"
    Kamerplanter legt beim Start automatisch alle Collections an. Wenn Collections fehlen, wurde der Startup-Hook nicht ausgeführt. Backend neu starten:

    === "Docker Compose"
        ```bash
        docker compose restart backend
        ```

    === "Kubernetes"
        ```bash
        kubectl rollout restart deployment/kamerplanter-backend
        ```

    Alternativ in der ArangoDB-Web-UI (Standard: `http://localhost:8529`) prüfen, ob die Datenbank `kamerplanter` und der Graph `kamerplanter_graph` existieren.

??? question "Migration schlägt fehl — Seed-Daten werden nicht geladen"
    Kamerplanter führt Seed-Migrationen beim Startup aus (`seed_data`, `seed_starter_kits`, `seed_location_types`). Bei Fehler im Log:

    1. Vollständigen Stack-Trace aus den Backend-Logs entnehmen.
    2. Häufige Ursache: ArangoDB startet langsamer als das Backend — Healthcheck-Intervall erhöhen oder depends_on mit `condition: service_healthy` nutzen.
    3. Backend erneut starten nach vollständig gestartetem ArangoDB.

??? question "AQL-Query schlägt fehl mit 'graph not found'"
    Der Named Graph `kamerplanter_graph` wird beim ersten Start erstellt. Wenn er fehlt, wurde die `ensure_collections()`-Initialisierung übersprungen. Backend neu starten oder manuell in der ArangoDB-Web-UI unter "Graphs" den Graph anlegen.

---

## Authentifizierung und Benutzer

??? question "Login schlägt fehl — 401 Unauthorized (keine Berechtigung)"
    Prüfe:

    1. **Korrekte E-Mail und Passwort?** Demo-Account: `demo@kamerplanter.local` / `demo-passwort-2024`
    2. **E-Mail-Verifikation erforderlich?** Wenn `REQUIRE_EMAIL_VERIFICATION=true` gesetzt ist, muss die E-Mail bestätigt sein. In der Entwicklungsumgebung auf `false` setzen.
    3. **JWT-Schlüssel geändert?** Alle aktiven Tokens verlieren ihre Gültigkeit. Neu anmelden.

??? question "Registrierung schlägt fehl — 'Email already registered'"
    Die E-Mail-Adresse existiert bereits im System. Passwort-zurücksetzen verwenden oder die E-Mail in der ArangoDB-Web-UI unter `users`-Collection prüfen.

??? question "Token abgelaufen — ständige Abmeldungen"
    JWT-Access-Token läuft nach 15 Minuten ab (Standard). Der Frontend-Client erneuert den Token automatisch per Refresh-Token (gültig 30 Tage). Wenn Refresh-Token-Erneuerung fehlschlägt:

    - `JWT_SECRET_KEY` in der Umgebung prüfen — wenn dieser Wert geändert wurde, werden alle Refresh-Tokens ungültig.
    - Browser-Cookies prüfen — HttpOnly-Cookie `refresh_token` muss gesetzt sein.

---

## CORS-Fehler im Browser

??? question "CORS-Fehler bei API-Aufrufen aus dem Browser"
    CORS-Fehler (Zugriffssperre durch Browser-Sicherheitsrichtlinie) erscheinen in der Browser-Konsole als:
    ```
    Access to XMLHttpRequest at 'http://localhost:8000/api/...' has been blocked by CORS policy
    ```

    **Lösung:** Den Origin des Frontend in `CORS_ORIGINS` eintragen:

    ```bash
    # .env
    CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
    ```

    Format: JSON-Array als String. Mehrere Einträge durch Komma trennen.

    !!! warning "Keine Wildcards in Produktion"
        `CORS_ORIGINS=["*"]` erlaubt alle Origins — nur für lokale Entwicklung geeignet. In Produktionsumgebungen immer konkrete URLs angeben.

??? question "CORS-Fehler trotz korrekter CORS_ORIGINS-Konfiguration"
    Prüfe den tatsächlich gesendeten `Origin`-Header:

    1. Browser DevTools → Network → Request-Header → `Origin`
    2. Diesen Wert exakt (inkl. `http://` vs. `https://` und Port) in `CORS_ORIGINS` eintragen.
    3. Backend neu starten nach Konfigurationsänderung.

---

## Ernte und IPM

??? question "Ernte wird blockiert (422 Karenzzeit-Verletzung)"
    Eine aktive IPM-Behandlung hat eine offene Karenzzeit (Pre-Harvest Interval). Die Ernte ist bis zum Ende der Karenzzeit gesperrt.

    **Vorgehen:**

    1. Navigiere zu **Pflanzenschutz > Behandlungsanwendungen**.
    2. Prüfe aktive Behandlungen mit dem Status "aktiv" oder "karenzzeit".
    3. Das System zeigt das früheste mögliche Erntedatum an.

    !!! danger "Karenzzeit nicht umgehen"
        Die Karenzzeit ist eine gesetzliche Anforderung (CanG, PflSchG). Das System verhindert die Ernte bewusst — eine manuelle Umgehung ist nicht vorgesehen.

??? question "Beobachtung kann nicht als Erntereif markiert werden"
    Prüfe, ob alle Ernteindikatoren für die Pflanzenart konfiguriert sind. Navigiere zu **Stammdaten > [Art] > Ernteindikatoren** und trage mindestens einen Indikator ein.

---

## Kalender und iCal

??? question "iCal-Feed zeigt keine Ereignisse"
    Prüfe:

    1. **Feed-Token gültig?** Unter **Kalender > iCal-Feeds** prüfen ob der Feed aktiv ist.
    2. **Kalender-App:** URL muss das Format `https://[host]/api/v1/calendar/ical/[token]` haben.
    3. **Zeitzone:** iCal-Feeds verwenden UTC. Prüfe ob deine Kalenderanwendung Zeitzonen korrekt interpretiert.

??? question "Kalenderansicht lädt nicht oder zeigt keine Daten"
    Navigiere zu **Kalender** und prüfe:

    - Sind Pflanzdurchläufe oder Aufgaben im gewählten Zeitraum vorhanden?
    - Sind die Filter (Phase, Kategorie) zu eng gesetzt?
    - Backend-API-Fehler in den Browser DevTools (F12 → Network → `/api/v1/...`)?

---

## Onboarding-Wizard

??? question "Onboarding-Wizard schlägt in Schritt 3 (Starter-Kit) fehl"
    Prüfe ob Starter-Kit-Seeddaten geladen wurden:

    ```bash
    docker compose logs backend | grep -i "seed_starter_kits"
    ```

    Wenn "0 starter kits loaded" erscheint, Seed-Migration manuell auslösen:

    ```bash
    docker compose exec backend python -c "from app.migrations.seed_starter_kits import run_seed_starter_kits; run_seed_starter_kits()"
    ```

??? question "Nach dem Onboarding erscheint kein Mandant in der Auswahl"
    Der persönliche Mandant wird automatisch bei der Registrierung erstellt. Falls er fehlt:

    1. `GET /api/v1/t/` — prüfen ob der Tenant-Endpoint Daten zurückliefert.
    2. Falls leer: Onboarding erneut durchlaufen oder Mandant manuell unter **Einstellungen > Mandanten** anlegen.

---

## Leistungs- und Verbindungsprobleme

??? question "API-Anfragen sind langsam (> 2 Sekunden)"
    Häufige Ursachen:

    | Ursache | Prüfung | Lösung |
    |---------|---------|--------|
    | ArangoDB-Index fehlt | ArangoDB-Web-UI → Collection → Indexes | `ensure_collections()` erneut ausführen |
    | Zu viele Graph-Traversal-Schritte | AQL EXPLAIN-Query in Web-UI | Query-Tiefe reduzieren |
    | Redis-Cache kalt | Erste Anfrage nach Neustart | Normal — Cache wärmt sich auf |

??? question "503 Service Unavailable beim Zugriff auf die API"
    Der Backend-Container läuft nicht oder besteht den Healthcheck nicht:

    ```bash
    docker compose ps
    # Status "unhealthy" oder "Exit X" → Container neu starten

    docker compose up -d backend
    ```

    Healthcheck-Endpunkt direkt prüfen:

    ```bash
    curl http://localhost:8000/api/v1/health/live
    # Erwartete Antwort: {"status": "ok"}
    ```

---

## Kubernetes: Pod startet nicht

??? question "Pod im Status 'CrashLoopBackOff'"
    `CrashLoopBackOff` (Kubernetes-Fehler: Container startet wiederholt und schlägt fehl) bedeutet, dass der Container kurz nach dem Start abstürzt. Logs des letzten Absturzes abrufen:

    ```bash
    kubectl logs deployment/kamerplanter-backend --previous
    ```

    Häufige Ursachen: fehlende Umgebungsvariablen, Datenbankverbindung nicht erreichbar oder fehlerhafte Konfigurationsdatei. Die Fehlermeldung im Log gibt in der Regel den genauen Grund an.

---

## Light-Modus vs. Full-Modus

??? question "Authentifizierung wird trotz Light-Modus verlangt"
    Im Light-Modus (`KAMERPLANTER_MODE=light`) entfällt die Token-Authentifizierung für die meisten Endpunkte. Prüfe:

    1. `KAMERPLANTER_MODE=light` in der Backend-Umgebung gesetzt?
    2. Backend nach der Änderung neu gestartet?
    3. Anfrage geht tatsächlich an den Backend-Port (8000) und nicht an einen Proxy?

    ```bash
    docker compose exec backend env | grep KAMERPLANTER_MODE
    # Erwartete Ausgabe: KAMERPLANTER_MODE=light
    ```

---

## Häufige Fehler nach Update

??? question "Nach einem Versions-Update schlagen Datenbankabfragen fehl"
    Bei neuen Collections oder Kanten-Definitionen aktualisiert `ensure_collections()` den Graphen. Falls alte Collections fehlen oder neue hinzugekommen sind:

    1. Backend-Logs auf Startup-Fehler prüfen.
    2. Sicherstellen, dass der Backend-Container beim Update vollständig neugestartet wurde.
    3. ArangoDB-Collections manuell über die Web-UI prüfen.

??? question "Frontend zeigt '404 Not Found' nach Deployment"
    Bei Kubernetes-Deployments wird der Frontend-Build als Static Files durch das Backend ausgeliefert. Prüfe:

    ```bash
    kubectl describe pod kamerplanter-backend-[hash]
    # Volume-Mounts auf /app/static prüfen
    ```

    Alternativ: Frontend separat als Nginx-Container deployen.

---

## Diagnosewerkzeuge

### API-Gesundheit prüfen

```bash
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
```

### ArangoDB direkt abfragen

Öffne `http://localhost:8529` im Browser (Standard-Credentials: `root` / Wert aus `ARANGO_ROOT_PASSWORD`).

### Backend-Logs mit Zeitstempel

```bash
docker compose logs backend --timestamps --tail=100
```

### Alle Dienste-Status anzeigen

```bash
docker compose ps
```

---

## Siehe auch

- [Umgebungsvariablen](../reference/environment-variables.md)
- [Lokales Setup](local-setup.md)
- [Deployment](../deployment/index.md)
- [Meiner Pflanze geht es schlecht](../user-guide/plant-health-troubleshooting.md) — Symptom-Diagnose für Pflanzenprobleme statt technischer Fehler

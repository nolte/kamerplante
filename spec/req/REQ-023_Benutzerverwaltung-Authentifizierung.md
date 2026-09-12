# Spezifikation: REQ-023 - Benutzerverwaltung & Authentifizierung

```yaml
ID: REQ-023
Titel: Benutzerverwaltung & Authentifizierung
Kategorie: Plattform & Sicherheit
Fokus: Beides
Technologie: Python, FastAPI, ArangoDB, Authlib, React, TypeScript, MUI
Status: Entwurf
Version: 1.13 (Rechte-Vokabular auf REQ-049 §3.1/§3.4 umgestellt)
Abhängigkeit: REQ-024 v1.4 (Permission-Matrix), UI-NFR-012 (PWA-Offline)
```

### Changelog

| Version | Datum | Änderungen |
|---------|-------|-----------|
| 1.12 | 2026-08-12 | **QR-Gerätekopplung für native Clients (#1118):** Neuer §3.8 — eine per QR-Code gekoppelte App tauscht einen Einmalcode gegen das **bestehende** REQ-023-Token-Paar (keine neue Token-Klasse, kein neuer Claim). Der Code liegt ausschließlich in Redis (kein neuer ArangoDB-Node, keine neue Collection); die Prüfspur sind structlog-Events, kein persistiertes Protokoll (§9). Einlösung ist rate-limitiert (`rate_limit_device_pairing_redeem`, Default 10/min) und zusätzlich per Quell-IP über den `LoginThrottleEngine` gesperrt — dieselbe Engine wie `login_local` —, wobei die Sperre **vor** dem Code-Store greift. `POST /auth/refresh` erhält einen Body-Transport (`{"refresh_token": …}`) für Clients ohne Cookie-Jar: Body schlägt Cookie, CSRF entfällt auf dem Body-Pfad (die Double-Submit-Tabelle in §1 ist entsprechend präzisiert). Neuer Frontend-Dialog „Gerät verbinden" im Sessions-Tab (§4.6). TTL `device_pairing_ttl_seconds` (Default 90, validiert 60–120). |
| 1.11 | 2026-08-07 | **SEC-H-009 Info-Mail gebaut (#958):** Die in §3.2 seit v1.8 geforderte Info-Mail an die bereits registrierte Adresse ist implementiert — aber unter zwei Bedingungen, die §3.2 jetzt ausformuliert, weil die naive Variante genau das Enumeration-Orakel wieder öffnet, das #957 geschlossen hat: (1) **asynchrone Zustellung** über den Celery-Task `app.tasks.auth_tasks.send_duplicate_registration_notice`, eingereiht in einem FastAPI-Background-Task, also erst nachdem die Antwort geschrieben ist; (2) **Sperrfenster je Empfängeradresse** (24 h, `IRegistrationNoticeStore`) statt je Absender-IP. Zusätzlich: `POST /api/v1/privacy/email-change` erhält ein eigenes Rate-Limit (`rate_limit_email_change`, Default 5/hour). |
| 1.10 | 2026-04-27 | **W-015:** §3.7 M2M-Auth um Light-Modus-Hinweis ergänzt — Service Accounts und API-Keys sind im Light-Modus deaktiviert (REQ-027 §2.1). Bei Mode-Switch Light→Full müssen externe Integrationen neue Keys generieren. |
| 1.9 | 2026-04-27 | **W-004 Fix (Refresh-Token Family + Offline-Grace-Window):** RefreshToken-Modell um `family_key`, `device_id`, `rotated_at`, `successor_key` erweitert. Token-Rotation idempotent innerhalb 60s Grace-Window bei Device-Match (für PWA-Reconnect-Race UI-NFR-012 R-049). Echter Replay (außerhalb Grace-Window oder Device-Mismatch) sprengt die ganze Token-Family. **Hard Cutover bei Deployment** — alle bestehenden Refresh-Tokens werden invalidiert, alle User müssen neu einloggen. Telemetrie: structlog `auth.refresh_replay_detected` + Prometheus `kp_auth_refresh_replay_total`. |
| 1.8 | 2026-03-18 | **Security-Hardening (IT-Security-Review):** (1) SEC-M-001: PII-Minimierung im JWT-Payload — `email` und `display_name` entfernt, nur `sub`, `tenant_roles`, `is_platform_admin` im Access Token. (2) SEC-H-009: Account-Enumeration-Schutz bei Registrierung — generische Antwort bei existierender E-Mail. (3) SEC-M-002: RS256/ES256-Migrationsplan dokumentiert, JWT-Secret >= 256 Bit. |
| 1.7 | 2026-03-17 | **Service Accounts, RBAC-Erweiterung & Tenant-Notfallverwaltung:** (1) `account_type: Literal['human', 'service']` auf User-Modell. Service Accounts als eigenständige, nicht-interaktive Konten für Third-Party-Systeme (Home Assistant, Grafana, CI/CD). Keine Passwort/SSO-Fähigkeit, API-Key-only. Tenant-scoped oder Platform-scoped. ServiceAccountEngine, ServiceAccountService, 15 neue API-Endpoints. Rate-Limit und IP-Allowlist pro Service Account. (2) Tenant-Notfallverwaltung: Emergency-Admin-Ernennung bei verwaisten Tenants (`orphaned_since`), Tenant-Suspendierung/Reaktivierung, User-Suspendierung/Reaktivierung durch Platform-Admin. 7 neue Admin-API-Endpoints. Celery-Task für Verwaist-Erkennung. |
| 1.6 | 2026-03-16 | **Platform-Admin-Rolle:** Neues Konzept Platform-Tenant (`is_platform: true`) als Träger der KA-Admin-Berechtigung. Platform-Admins verwalten globale Stammdaten, `tenant_has_access`-Zuweisungen und Promotions. User kann gleichzeitig Platform-Admin und regulärer Tenant-Nutzer sein. Neue User Stories, JWT-Erweiterung (`is_platform_admin`), Dependency `is_platform_admin`. |
| 1.5 | 2026-02-28 | Home Assistant Integration: `ha_url` + `ha_token_encrypted` auf User-Modell, neuer Tab „Integrationen" in AccountSettingsPage, Verbindungstest-Endpoint. Temperatureinheit: Verweis auf `temperature_unit` in UserPreference (REQ-020 v1.2). |
| 1.4 | 2026-02-27 | M2M-Authentifizierung: API-Key-Modell (`kp_`-Prefix, SHA-256-Hash), `api_keys` Collection, `has_api_key` Edge, 3 Endpoints (erstellen/auflisten/revoken), Bearer-Erkennung neben JWT, Rate Limit 1000 req/min. |
| 1.3 | 2026-02-27 | „Angemeldet bleiben"-Option: Session-Cookie (Browser-Session) vs. persistentes Cookie (30 Tage) via `remember_me`-Flag. Neue User Story, Login-Checkbox, `is_persistent`-Feld auf RefreshToken, differenzierte Cookie-Strategie. |
| 1.2 | 2026-02-27 | SEC-K-002: IP-Anonymisierung nach 7 Tagen, `ip_anonymized_at` Feld. SEC-K-004: CSRF-Strategie — `SameSite=Lax` (statt Strict) + Double-Submit Cookie für zustandsändernde Cookie-Endpunkte. |
| 1.1 | 2026-02-25 | Tech-Stack-Review: Authlib statt python-jose, Token-TTL-Anpassungen |
| 1.0 | 2026-02-24 | Erstversion |

## 1. Business Case

**User Story (Lokale Registrierung):** "Als Einzelgärtner möchte ich mich mit E-Mail und Passwort registrieren können, ohne einen externen Anbieter wie Google nutzen zu müssen — weil ich meine Pflanzendaten privat halten möchte und keinen Social-Login verwenden will."

**User Story (SSO-Anmeldung):** "Als Hobby-Gärtner möchte ich mich mit meinem bestehenden Google-Konto anmelden können — damit ich kein weiteres Passwort verwalten muss und sofort loslegen kann."

**User Story (Account-Verknüpfung):** "Als Nutzer, der sich initial mit Google angemeldet hat, möchte ich nachträglich ein lokales Passwort setzen können — damit ich auch ohne Google-Verfügbarkeit auf meine Pflanzen zugreifen kann."

**User Story (Profilpflege):** "Als registrierter Nutzer möchte ich meinen Anzeigenamen, mein Profilbild und meine Sprach-/Zeitzoneneinstellungen verwalten können — damit andere Gartenmitglieder mich erkennen und das System in meiner Zeitzone arbeitet."

**User Story (Angemeldet bleiben):** "Als Gärtner möchte ich auf meinem privaten Gerät angemeldet bleiben können, damit ich nicht bei jedem Besuch erneut E-Mail und Passwort eingeben muss — auf öffentlichen Geräten möchte ich aber bewusst darauf verzichten können."

**User Story (Passwort-Reset):** "Als Nutzer, der sein Passwort vergessen hat, möchte ich über meine E-Mail-Adresse ein neues Passwort setzen können — ohne den Support kontaktieren zu müssen."

**User Story (OIDC-Anbindung):** "Als Systemadministrator möchte ich einen eigenen OpenID-Connect-Provider (z.B. Keycloak, Authentik) konfigurieren können — damit unser Gemeinschaftsgarten den zentralen Identity Provider der Organisation nutzen kann."

<!-- Quelle: Platform-Admin v1.6 -->
**User Story (Platform-Admin):** "Als Plattform-Betreiber möchte ich globale Stammdaten (Pflanzenarten, Sorten, Schädlinge) zentral pflegen und einzelnen Tenants zuweisen können — damit jeder Tenant nur die für ihn relevanten Daten sieht und die Datenqualität zentral sichergestellt wird."

**User Story (Doppelrolle):** "Als KA-Admin möchte ich gleichzeitig meinen eigenen privaten Garten als normaler Tenant-Nutzer verwalten können — ohne zwischen verschiedenen Accounts wechseln zu müssen."
<!-- /Quelle: Platform-Admin v1.6 -->

<!-- Quelle: Service Accounts v1.7 -->
**User Story (Home Assistant Integration):** "Als Hobby-Gärtner mit Home Assistant möchte ich einen Service Account für meine HA-Installation erstellen können — damit HA automatisch Sensordaten liefert und Aktoren steuert, ohne dass mein persönlicher Account dafür missbraucht wird."

**User Story (CI/CD Pipeline):** "Als Plattform-Betreiber möchte ich einen Service Account für meine CI/CD-Pipeline erstellen können — damit automatisierte Tests und Deployments API-Zugriff haben, ohne menschliche Credentials zu verwenden."

**User Story (Monitoring-System):** "Als Tenant-Admin möchte ich einen Service Account für Grafana/Prometheus erstellen können — damit das Monitoring-System Metriken abrufen kann, mit eigenen Rate-Limits und eingeschränktem Zugriff nur auf meinen Tenant."

**User Story (Service Account Verwaltung):** "Als Tenant-Admin möchte ich Service Accounts für meinen Garten erstellen, deren Berechtigungen steuern und sie bei Bedarf deaktivieren können — damit ich volle Kontrolle über maschinelle Zugriffe auf meine Daten habe."

**User Story (Platform Service Account):** "Als KA-Admin möchte ich Service Accounts auf Plattformebene erstellen können — damit zentrale Systeme (Backup, Monitoring, Enrichment-Pipelines) über einen dedizierten, auditierbaren Account auf globale Daten zugreifen."

**User Story (IP-Einschränkung):** "Als sicherheitsbewusster Admin möchte ich Service Accounts auf bestimmte IP-Bereiche einschränken können — damit ein kompromittierter API-Key nicht von beliebigen Netzwerken aus genutzt werden kann."
<!-- /Quelle: Service Accounts v1.7 -->

**Beschreibung:**
Kamerplanter ist aktuell ein Einbenutzer-System ohne Authentifizierung. Für Mehrbenutzerbetrieb (Gemeinschaftsgärten, Mikro-Farmen, Anbauvereinigungen) ist eine vollständige Benutzerverwaltung die **Grundvoraussetzung**. Diese REQ **ersetzt NFR-001 §6.1** (JWT-Skizze mit `python-jose`, 1h Access Token) durch eine vollständige Spezifikation und bildet die Basis für REQ-024 (Mandantenverwaltung).

**Technologie-Entscheidung (JWT/OAuth-Library):**
Diese Spezifikation verwendet **Authlib** (aktiv maintained) anstelle von `python-jose` (letztes Release 2022, in NFR-001 §6.1 referenziert). Authlib bietet:
- JWT-Signierung/-Validierung (ersetzt `python-jose`)
- OAuth2/OIDC Client mit PKCE-Support (ersetzt manuelle `httpx`-Implementierung)
- OIDC Discovery (`.well-known/openid-configuration`) built-in
- Flask/FastAPI-Integration

**Abweichungen von NFR-001 §6.1:**
| Aspekt | NFR-001 §6.1 (alt) | REQ-023 (neu) | Begründung |
|--------|--------------------|--------------|-----------|
| Library | `python-jose` + `passlib` | `authlib` + `passlib` | `python-jose` unmaintained seit 2022; Authlib bietet OIDC/PKCE built-in |
| Access Token TTL | 1 Stunde | **15 Minuten** | Kürzeres Fenster bei Token-Kompromittierung; Refresh-Token-Mechanismus kompensiert UX |
| Refresh Token | Nicht spezifiziert | 30 Tage (persistent) oder 24h (Session), HttpOnly Cookie, Rotation, steuerbar via „Angemeldet bleiben" | Erforderlich für 15-Min-Access-Tokens ohne ständige Neuanmeldung; Session-Cookie als sicherer Standard für geteilte Geräte |
| Token Payload | `sub`, `exp`, `type` | `sub`, `tenant_roles`, `is_platform_admin`, `exp`, `iat`, `type` | Mandanten-Rollen für REQ-024 im Token; PII-Minimierung (SEC-M-001): kein email/display_name |
| Refresh Grace Window <!-- W-004 --> | Nicht spezifiziert | **60 Sekunden** | Idempotenter Refresh innerhalb dieses Fensters (bei Device-Match) — toleriert paralleles `POST /auth/refresh` aus PWA-Reconnect (Service-Worker + UI-Thread). Nach 60s: strikte Replay-Detection mit Family-Sprengung. (UI-NFR-012 R-049) |
| Token Family <!-- W-004 --> | Nicht spezifiziert | **`family_key` pro Login**, geteilt durch alle aus Rotation entstandenen Nachfolger | Replay-Detection sprengt die ganze Family; jeder neue Login startet eine neue Family — Multi-Device-Nutzung bleibt unbeeinträchtigt |

**Kernkonzepte:**

**Dual-Authentifizierung — Lokal + Föderiert:**
Das System unterstützt zwei gleichberechtigte Authentifizierungspfade:
1. **Lokale Accounts** — E-Mail + Passwort (Bcrypt-gehasht), vollständig self-contained
2. **Föderierte Accounts** — OAuth2/OIDC mit benannten Providern (Google, GitHub, Apple) und beliebig vielen generischen OIDC-Providern

Ein User kann mehrere Auth-Methoden verknüpfen (z.B. Google + lokales Passwort). Die erste erfolgreiche Anmeldung erstellt den User-Account; weitere Provider werden verknüpft.

**Benannte SSO-Provider:**

| Provider | Protokoll | Scope | Besonderheit |
|----------|-----------|-------|-------------|
| Google | OAuth2 + OIDC | `openid email profile` | Größte Verbreitung, E-Mail immer verifiziert |
| GitHub | OAuth2 | `read:user user:email` | Technische Nutzer, E-Mail ggf. privat → separater API-Call |
| Apple | OAuth2 + OIDC | `name email` | Name nur beim ersten Login übermittelt, muss gespeichert werden |

**Generischer OIDC-Provider:**
Zusätzlich können beliebig viele OIDC-Provider über Konfiguration registriert werden (z.B. Keycloak, Authentik, Azure AD, Okta). Die Konfiguration erfolgt per Provider-Eintrag:

```yaml
# Konfigurationsbeispiel: Generischer OIDC-Provider
oidc_providers:
  - slug: "keycloak-gemeinschaftsgarten"
    display_name: "Gemeinschaftsgarten Berlin"
    issuer_url: "https://auth.garden-berlin.org/realms/garten"
    client_id: "kamerplanter"
    client_secret: "${KEYCLOAK_SECRET}"
    scopes: ["openid", "email", "profile"]
    icon_url: "https://auth.garden-berlin.org/logo.png"  # Optional
    auto_discover: true  # .well-known/openid-configuration
```

**JWT-Token-Lifecycle:**

| Token | Lebensdauer | Speicherort | Refresh-Mechanismus |
|-------|-------------|-------------|---------------------|
| Access Token | 15 Minuten | Memory (Frontend) | Automatisch via Refresh Token |
| Refresh Token (persistent) | 30 Tage | HttpOnly Secure Cookie (`Expires` gesetzt) | Rotation bei Nutzung (altes Token wird invalidiert) |
| Refresh Token (Session) | Browser-Session | HttpOnly Secure Session-Cookie (kein `Expires`/`Max-Age`) | Rotation bei Nutzung |

- **Access Token:** Enthält `sub` (user_key), `tenant_roles` (Mapping tenant_key → role), `exp`, `iat`, `type`. Kurzlebig, wird bei jedem API-Request als `Authorization: Bearer <token>` mitgesendet.
  - **PII-Minimierung (SEC-M-001):** `email` und `display_name` werden **nicht** im JWT-Payload übertragen, um die Exposition personenbezogener Daten bei Token-Leaks zu minimieren. Diese Daten werden bei Bedarf über `GET /api/v1/users/me` abgefragt (gecacht im Frontend-State).
- **Refresh Token:** Wird als HttpOnly/Secure/SameSite=Lax Cookie gespeichert. Bei Nutzung wird ein neues Refresh-Token-Paar ausgestellt und das alte invalidiert (Token-Rotation verhindert Token-Diebstahl).
- **Token-Revocation:** Logout invalidiert alle Refresh Tokens des Nutzers. Optional: "Von allen Geräten abmelden" invalidiert alle Sessions.

**„Angemeldet bleiben"-Strategie:**

Das Login-Formular bietet eine Checkbox „Angemeldet bleiben" (`remember_me`). Diese steuert die **Cookie-Persistenz** des Refresh Tokens:

| `remember_me` | Cookie-Typ | Verhalten | Serverseitige TTL |
|----------------|------------|-----------|-------------------|
| `true` (aktiviert) | **Persistentes Cookie** — `Max-Age: 30 Tage` | Cookie überlebt Browser-Neustart. Nutzer bleibt bis zu 30 Tage angemeldet (sliding window durch Token-Rotation). | 30 Tage |
| `false` (Standard) | **Session-Cookie** — kein `Expires`/`Max-Age` | Cookie wird gelöscht, wenn der Browser geschlossen wird. Nutzer muss sich nach Browser-Neustart erneut anmelden. | 24 Stunden |

- **Standard:** `remember_me = false` — sicherere Standardeinstellung, besonders relevant für öffentliche/geteilte Geräte
- **Session-TTL bei `remember_me=false`:** Das Refresh Token hat serverseitig eine verkürzte Lebensdauer von 24 Stunden (statt 30 Tage). Selbst wenn der Browser die Session wider Erwarten beibehält (z.B. Session-Restore-Feature), läuft das Token nach 24h ab.
- **SSO-Logins:** OAuth/OIDC-Logins setzen `remember_me` implizit auf `true`, da der Nutzer bereits einen bewussten Redirect-Flow durchlaufen hat. Der Nutzer kann dies über die Session-Verwaltung (`AccountSettingsPage → Sessions`) jederzeit widerrufen.
- **Token-Rotation:** Bei jedem Refresh wird der Cookie-Typ (persistent vs. Session) des ursprünglichen Tokens beibehalten. Ein Session-Token wird nicht durch Rotation zu einem persistenten Token.

**CSRF-Schutz-Strategie (SEC-K-004):**

Da Refresh Tokens als HttpOnly Cookie übertragen werden, sind zustandsändernde Endpunkte, die diesen Cookie verwenden, potenziell CSRF-anfällig. Die Strategie kombiniert zwei Maßnahmen:

1. **`SameSite=Lax`** (statt `Strict`): OAuth-Callbacks sind Top-Level-Navigationen (Redirect von Google/GitHub/Apple zurück zur App). `SameSite=Strict` würde den Refresh-Token-Cookie bei diesen Cross-Origin-Navigationen blockieren. `SameSite=Lax` erlaubt den Cookie bei Top-Level-Navigationen (GET), blockiert ihn aber bei Cross-Origin POST/PUT/DELETE (CSRF-Schutz für die meisten Szenarien).

2. **Double-Submit Cookie Pattern** für POST-Endpunkte, die den Refresh-Token-Cookie verwenden:
   - Bei Token-Refresh (`POST /auth/refresh`): Server setzt zusätzlich einen nicht-HttpOnly Cookie `csrf_token` mit einem zufälligen Wert. Client muss diesen Wert als `X-CSRF-Token`-Header mitsenden. Server vergleicht Cookie-Wert mit Header-Wert.
   - Betroffene Endpunkte: `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/logout-all`
   - Der CSRF-Token wird bei jedem Token-Refresh erneuert (analog zur Refresh-Token-Rotation)
   - **Nicht** betroffen: `POST /auth/login`, `POST /auth/register` (verwenden keinen Cookie, sondern Request-Body-Credentials)
   - **Nur der Cookie-Pfad** von `POST /auth/refresh` ist Double-Submit-geschützt (#1118): Seit v1.12 akzeptiert dieser Endpunkt zusätzlich einen optionalen Refresh-Token im JSON-Body (§3.8). Ein Body-Token ist kein *ambient* übertragenes Credential — der Browser hängt ihn nicht selbsttätig an —, deshalb entfällt die Double-Submit-Prüfung auf dem Body-Pfad. Der Cookie-Pfad bleibt unverändert CSRF-pflichtig.

| Endpunkt | Cookie-basiert | CSRF-Schutz |
|----------|---------------|-------------|
| `POST /auth/login` | Nein (Body) | Nicht nötig |
| `POST /auth/register` | Nein (Body) | Nicht nötig |
| `POST /auth/refresh` (Cookie-Pfad) | Ja (Refresh Cookie) | Double-Submit Cookie |
| `POST /auth/refresh` (Body-Pfad, #1118) | Nein (Refresh-Token im Body) | Nicht nötig (kein ambient Credential) |
| `POST /auth/logout` | Ja (Refresh Cookie) | Double-Submit Cookie |
| `POST /auth/logout-all` | Ja (Refresh Cookie) | Double-Submit Cookie |
| `GET /auth/oauth/{slug}/callback` | Nein (OAuth State) | OAuth State-Parameter |
| Alle anderen Endpunkte | Nein (Bearer Token) | Nicht nötig (Token im Header) |

**Passwort-Policy:**
- Minimale Länge: 10 Zeichen
- Keine Komplexitätsregeln (NIST 800-63B Empfehlung: Länge > Komplexität)
- Bcrypt mit Cost Factor 12
- Breach-Check gegen HaveIBeenPwned API (SHA-1-Prefix, k-Anonymity, optional)
- Rate Limiting: Max. 5 fehlgeschlagene Login-Versuche pro 15 Minuten pro E-Mail

**E-Mail-Verifizierung:**
- Lokale Registrierung: Verifizierungs-Link per E-Mail (Token gültig 24h)
- SSO-Registrierung: E-Mail automatisch als verifiziert markiert (Provider garantiert Verifizierung)
- Unbestätigte Accounts können das System nutzen, aber keine Einladungen (REQ-024) versenden

**Account-Linking:**
Ein User kann mehrere Auth-Provider verknüpfen:
- Matching erfolgt über **verifizierte E-Mail-Adresse**: Login mit Google (`max@example.com`) wird automatisch mit dem lokalen Account (`max@example.com`) verknüpft
- Kein Auto-Link bei unverifizierter E-Mail (verhindert Account-Übernahme)
- User kann jederzeit zusätzliche Provider verknüpfen oder entfernen (mindestens eine Auth-Methode muss bestehen bleiben)

### 1.1 Szenarien

**Szenario 1: Lokale Registrierung — Einzelgärtner**
```
1. Nutzer öffnet /register
2. Gibt ein: E-Mail "max@example.com", Anzeigename "Max", Passwort "mein-sicheres-passwort-2024"
3. System erstellt User-Account (status: unverified)
4. Verifizierungs-E-Mail wird gesendet (Token: 24h gültig)
5. Nutzer klickt Verifizierungs-Link → status: active
6. Nutzer wird eingeloggt (Access Token + Refresh Token)
7. System erstellt automatisch einen persönlichen Tenant "Maxs Garten"
```

**Szenario 2: Google-SSO — Schnelleinstieg**
```
1. Nutzer klickt "Mit Google anmelden"
2. Redirect zu Google OAuth2 Consent Screen
3. Google gibt zurück: email="lisa@gmail.com", name="Lisa Müller", picture_url="..."
4. System prüft: Existiert User mit email="lisa@gmail.com"?
   → Nein: Neuer User wird erstellt (status: active, email_verified: true)
   → Ja: Bestehender User wird eingeloggt, Google-Provider wird verknüpft
5. JWT-Token-Paar wird ausgestellt
6. Redirect zu Dashboard
```

**Szenario 3: Generischer OIDC — Gemeinschaftsgarten mit Keycloak**
```
1. Admin hat OIDC-Provider "keycloak-gemeinschaftsgarten" konfiguriert
2. Nutzer öffnet /login → sieht Button "Gemeinschaftsgarten Berlin"
3. Redirect zu Keycloak-Login-Seite der Organisation
4. Nach Authentifizierung: OIDC-Token mit sub/email/name
5. System erstellt/verknüpft User-Account
6. Nutzer wird in den zugehörigen Tenant eingeladen (falls konfiguriert)
```

**Szenario 4: Account-Linking — Google-User setzt lokales Passwort**
```
1. Nutzer hat sich initial mit Google angemeldet
2. Navigiert zu /settings/account
3. Wählt "Lokales Passwort hinzufügen"
4. Setzt Passwort → system speichert Bcrypt-Hash
5. Nutzer kann sich jetzt wahlweise mit Google ODER E-Mail/Passwort anmelden
```

**Szenario 5: Angemeldet bleiben — Privates Gerät**
```
1. Nutzer öffnet /login
2. Gibt E-Mail und Passwort ein
3. Aktiviert Checkbox "Angemeldet bleiben"
4. POST /auth/login mit { email, password, remember_me: true }
5. Server erstellt RefreshToken (is_persistent: true, expires_at: +30 Tage)
6. Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000
7. Nutzer schließt Browser und öffnet die App am nächsten Tag
8. Browser sendet persistenten Cookie → automatischer Token-Refresh → Nutzer ist eingeloggt
```

**Szenario 6: Ohne "Angemeldet bleiben" — Öffentliches Gerät**
```
1. Nutzer öffnet /login auf einem geteilten Gerät
2. Gibt E-Mail und Passwort ein, lässt Checkbox "Angemeldet bleiben" deaktiviert
3. POST /auth/login mit { email, password, remember_me: false }
4. Server erstellt RefreshToken (is_persistent: false, expires_at: +24 Stunden)
5. Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Lax  (KEIN Max-Age/Expires)
6. Nutzer arbeitet normal — Token-Refresh funktioniert transparent
7. Nutzer schließt Browser → Session-Cookie wird gelöscht
8. Nutzer öffnet Browser erneut → kein Cookie → Redirect zu /login
```

**Szenario 7: Passwort-Reset**
```
1. Nutzer klickt "Passwort vergessen" auf /login
2. Gibt E-Mail ein → System sendet Reset-Link (Token: 1h gültig, einmalig verwendbar)
3. Nutzer klickt Link → Setzt neues Passwort
4. Alle bestehenden Refresh Tokens werden invalidiert (erzwingt Neuanmeldung auf allen Geräten)
```

## 2. ArangoDB-Modellierung

### Nodes:

- **`:User`** — Benutzerkonto (menschliche User und Service Accounts)
  - Collection: `users`
  - Properties:
    - `email: str` (UNIQUE, lowercase-normalisiert)
    - `display_name: str` (Anzeigename, z.B. "Max Mustermann")
    - `avatar_url: Optional[str]` (Profilbild-URL, von SSO übernommen oder manuell gesetzt)
    - `locale: str` (Default: `de`, Sprachpräferenz für i18n)
    - `timezone: str` (Default: `Europe/Berlin`, IANA-Zeitzone)
    <!-- Quelle: Service Accounts v1.7 -->
    - `account_type: Literal['human', 'service']` (Default: `human`) — Unterscheidet menschliche Nutzer von Service Accounts. Service Accounts können sich nicht interaktiv anmelden (kein Passwort, kein SSO), werden ausschließlich per API-Key authentifiziert.
    <!-- /Quelle: Service Accounts v1.7 -->
    - `status: Literal['unverified', 'active', 'suspended', 'deleted']`
    - `email_verified: bool` (Default: `false`)
    - `email_verification_token: Optional[str]` (Einmalig, gehashed gespeichert)
    - `email_verification_expires: Optional[datetime]`
    - `password_hash: Optional[str]` (Bcrypt, `null` bei reinen SSO-Accounts und Service Accounts)
    - `password_reset_token: Optional[str]` (Einmalig, gehashed gespeichert)
    - `password_reset_expires: Optional[datetime]`
    - `failed_login_attempts: int` (Default: 0, Reset nach erfolgreichem Login)
    - `locked_until: Optional[datetime]` (Temporäre Sperrung nach zu vielen Fehlversuchen)
    - `last_login_at: Optional[datetime]`
    - `ha_url: Optional[str]` (Home Assistant URL, z.B. `"http://homeassistant.local:8123"`)
    - `ha_token_encrypted: Optional[str]` (Home Assistant Long-Lived Access Token, AES-256 verschlüsselt gespeichert. Wird vom `HomeAssistantConnector` (REQ-005) zur Kommunikation mit der HA REST API verwendet.)
    <!-- Quelle: Service Accounts v1.7 -->
    - `description: Optional[str]` (Nur für Service Accounts — Zweck/Beschreibung, z.B. "Home Assistant Zelt 1", "Grafana Monitoring")
    - `created_by: Optional[str]` (user_key des Erstellers, nur für Service Accounts)
    - `rate_limit_rpm: Optional[int]` (Rate Limit pro Minute, nur für Service Accounts. Default: `1000`. `null` = globaler Default.)
    - `allowed_ip_ranges: Optional[list[str]]` (CIDR-Notation, nur für Service Accounts. `null` = keine Einschränkung. z.B. `["192.168.1.0/24", "10.0.0.0/8"]`)
    - `last_active_at: Optional[datetime]` (Letzte API-Aktivität, nur für Service Accounts — wird bei jedem API-Key-Zugriff aktualisiert)
    <!-- /Quelle: Service Accounts v1.7 -->
    - `created_at: datetime`
    - `updated_at: datetime`

- **`:AuthProvider`** — Verknüpfter Authentifizierungsprovider
  - Collection: `auth_providers`
  - Properties:
    - `provider: str` (z.B. `google`, `github`, `apple`, `keycloak-gemeinschaftsgarten`)
    - `provider_user_id: str` (Eindeutige ID beim Provider, z.B. Google `sub`)
    - `provider_email: Optional[str]` (E-Mail beim Provider, kann von User.email abweichen)
    - `provider_name: Optional[str]` (Name beim Provider)
    - `provider_avatar_url: Optional[str]`
    - `access_token_encrypted: Optional[str]` (Verschlüsselt, für API-Zugriff beim Provider)
    - `refresh_token_encrypted: Optional[str]` (Verschlüsselt, für Token-Refresh beim Provider)
    - `token_expires_at: Optional[datetime]`
    - `linked_at: datetime`
    - `last_used_at: Optional[datetime]`

- **`:RefreshToken`** — Aktive Refresh-Token-Sessions
  - Collection: `refresh_tokens`
  - Properties:
    - `token_hash: str` (SHA-256 Hash des Tokens, UNIQUE)
    - `device_info: Optional[str]` (User-Agent, für "Aktive Sessions"-Übersicht)
    - `ip_address: Optional[str]` (Letzte bekannte IP; **Rechtsgrundlage:** Art. 6(1)(f) berechtigtes Interesse — Erkennung kompromittierter Sessions)
    - `ip_anonymized_at: Optional[datetime]` (Zeitpunkt der IP-Anonymisierung; `null` = noch nicht anonymisiert)
    - `issued_at: datetime`
    - `expires_at: datetime`
    - `is_persistent: bool` (Default: `false` — `true` wenn Login mit „Angemeldet bleiben", steuert Cookie-Typ bei Rotation)
    - `revoked: bool` (Default: `false`)
    - `replaced_by: Optional[str]` (Token-Hash des Nachfolgers bei Rotation)
    <!-- Quelle: Widerspruchsanalyse W-004 -->
    - `family_key: str` (UUID; alle aus Rotation desselben Logins entstehenden Tokens teilen die `family_key`. Bei nachgewiesenem Replay wird die ganze Family invalidiert. Jeder neue Login startet eine neue Family — Multi-Device-Nutzung bleibt unbeeinträchtigt.)
    - `device_id: Optional[str]` (Stable Device-Identifier vom Frontend, persistiert in IndexedDB als UUID — siehe UI-NFR-012 R-049b. Default `null` für migrierte Tokens und API-Clients ohne PWA-Setup. Bei `null` greift der Grace-Window-Schutz nicht.)
    - `rotated_at: Optional[datetime]` (Wann wurde dieses Token durch Rotation invalidiert; `null` = noch aktiv. Wird beim Refresh auf den Vorgänger gesetzt.)
    - `successor_key: Optional[str]` (Token-Hash des direkten Nachfolgers nach Rotation; nur für Grace-Window-Lookup. Identisch zu `replaced_by` für Tokens nach v1.9; bei Migration werden ältere Tokens mit eigenem Hash gefüllt.)
    <!-- /Quelle: Widerspruchsanalyse W-004 -->
  - **IP-Anonymisierung (SEC-K-002):** Nach 7 Tagen wird `ip_address` automatisch anonymisiert (Celery-Task, NFR-011 R-03):
    - IPv4: Letztes Oktett → `0` (z.B. `192.168.1.42` → `192.168.1.0`)
    - IPv6: Auf `/48`-Präfix gekürzt (z.B. `2001:db8:85a3::8a2e:370:7334` → `2001:db8:85a3::`)
    - `ip_anonymized_at` wird auf den Anonymisierungszeitpunkt gesetzt

- **`:OidcProviderConfig`** — Konfigurierte OIDC-Provider (System-Level)
  - Collection: `oidc_provider_configs`
  - Properties:
    - `slug: str` (URL-sicher, UNIQUE, z.B. `keycloak-gemeinschaftsgarten`)
    - `display_name: str` (Anzeigename auf Login-Seite)
    - `provider_type: Literal['google', 'github', 'apple', 'oidc']`
    - `issuer_url: Optional[str]` (OIDC Discovery URL, für generische Provider)
    - `authorization_url: str`
    - `token_url: str`
    - `userinfo_url: Optional[str]`
    - `jwks_url: Optional[str]` (JSON Web Key Set für Token-Validierung)
    - `client_id: str`
    - `client_secret_encrypted: str` (Verschlüsselt gespeichert)
    - `scopes: list[str]` (Default: `['openid', 'email', 'profile']`)
    - `icon_url: Optional[str]` (Für Login-Button)
    - `enabled: bool` (Default: `true`)
    - `auto_discover: bool` (Default: `true`, nutzt `.well-known/openid-configuration`)
    - `default_tenant_key: Optional[str]` (Forward-Referenz → REQ-024: Neuen Usern automatisch diesem Tenant zuweisen. Wird erst mit REQ-024 aktiv.)
    - `created_at: datetime`
    - `updated_at: datetime`

### Edges:

```
has_auth_provider:  users → auth_providers     (1:N, User hat Auth-Provider)
has_session:        users → refresh_tokens      (1:N, User hat aktive Sessions)
```

### Indizes:

```
users:
  - PERSISTENT INDEX on [email] UNIQUE
  - PERSISTENT INDEX on [status]

auth_providers:
  - PERSISTENT INDEX on [provider, provider_user_id] UNIQUE  (eindeutig pro Provider)

refresh_tokens:
  - PERSISTENT INDEX on [token_hash] UNIQUE
  - PERSISTENT INDEX on [expires_at]  (für TTL-Cleanup)
  - TTL INDEX on [expires_at] expireAfter: 0  (automatische Bereinigung abgelaufener Tokens)

oidc_provider_configs:
  - PERSISTENT INDEX on [slug] UNIQUE
  - PERSISTENT INDEX on [provider_type]
```

### AQL-Beispiellogik:

**User mit allen Auth-Providern laden:**
```aql
LET user = DOCUMENT(users, @user_key)
LET providers = (
  FOR ap IN 1..1 OUTBOUND user GRAPH 'kamerplanter_graph'
    OPTIONS { edgeCollections: ['has_auth_provider'] }
    RETURN {
      provider: ap.provider,
      provider_email: ap.provider_email,
      linked_at: ap.linked_at,
      last_used_at: ap.last_used_at
    }
)
RETURN MERGE(user, { auth_providers: providers })
```

**User per Provider-ID finden (SSO-Login):**
```aql
FOR ap IN auth_providers
  FILTER ap.provider == @provider AND ap.provider_user_id == @provider_user_id
  LET user = FIRST(
    FOR u IN 1..1 INBOUND ap GRAPH 'kamerplanter_graph'
      OPTIONS { edgeCollections: ['has_auth_provider'] }
      RETURN u
  )
  RETURN { auth_provider: ap, user: user }
```

**Aktive Sessions eines Users:**
```aql
FOR rt IN 1..1 OUTBOUND DOCUMENT(users, @user_key) GRAPH 'kamerplanter_graph'
  OPTIONS { edgeCollections: ['has_session'] }
  FILTER rt.revoked == false AND rt.expires_at > DATE_ISO8601(DATE_NOW())
  SORT rt.issued_at DESC
  RETURN {
    device_info: rt.device_info,
    ip_address: rt.ip_address,
    issued_at: rt.issued_at,
    expires_at: rt.expires_at
  }
```

**Abgelaufene/Revoked Tokens bereinigen (Celery-Task):**
```aql
FOR rt IN refresh_tokens
  FILTER rt.revoked == true OR rt.expires_at < DATE_ISO8601(DATE_NOW())
  REMOVE rt IN refresh_tokens
```

## 3. Backend-Architektur

### 3.1 Engine-Schicht

**`PasswordEngine`** — Passwort-Hashing und -Validierung (pure Logik, kein I/O):

```python
class PasswordEngine:
    BCRYPT_ROUNDS = 12
    MIN_LENGTH = 10

    def hash_password(self, password: str) -> str: ...
    def verify_password(self, password: str, password_hash: str) -> bool: ...
    def validate_password_policy(self, password: str) -> list[str]: ...
        # Gibt Liste von Fehlermeldungen zurück, leer = gültig
        # Prüft: Mindestlänge, nicht identisch mit E-Mail
```

**`TokenEngine`** — JWT-Erstellung und -Validierung (pure Logik, nutzt `authlib.jose`):

```python
# Implementierung nutzt authlib.jose.jwt (nicht python-jose)
# pip install authlib

class TokenEngine:
    def create_access_token(self, user: User, tenant_roles: dict[str, str]) -> str: ...
        # Payload: { sub: user_key, tenant_roles, is_platform_admin, exp, iat, type: "access" }
        # PII-Minimierung (SEC-M-001): KEIN email/display_name im Payload
        # Algorithmus: HS256 (via authlib.jose.jwt.encode), Lebensdauer: 15 Minuten
        # Migration zu RS256/ES256 (SEC-M-002): Langfristig geplant — ermöglicht Token-Validierung
        # ohne Shared Secret. Voraussetzung: JWK-Rotation-Infrastruktur. Kurzfristig:
        # JWT-Secret MUSS >= 256 Bit sein, Secret-Rotation über ENV-Variable mit Overlap-Periode.

    def create_refresh_token(self) -> tuple[str, str]: ...
        # Gibt (raw_token, token_hash) zurück
        # raw_token = secrets.token_urlsafe(32), token_hash = SHA-256(raw_token)
        # raw_token wird an Client gesendet, token_hash wird gespeichert

    def decode_access_token(self, token: str) -> TokenPayload: ...
        # Validiert Signatur, Ablaufdatum, Typ (via authlib.jose.jwt.decode)
        # Wirft InvalidTokenError bei Fehler

    def hash_token(self, raw_token: str) -> str: ...
        # SHA-256 Hash für DB-Speicherung (hashlib.sha256)
```

**`OAuthEngine`** — OAuth2/OIDC-Flow-Logik (nutzt `authlib.integrations.httpx_client`):

Authlib stellt `AsyncOAuth2Client` bereit, der PKCE, OIDC Discovery und Token-Exchange kapselt. Der `OAuthEngine` nutzt diesen Client intern und normalisiert die Provider-spezifischen Unterschiede:

```python
# Implementierung nutzt authlib.integrations.httpx_client.AsyncOAuth2Client
# PKCE (S256) wird automatisch von Authlib gehandhabt

class OAuthEngine:
    def create_oauth_client(self, provider_config: OidcProviderConfig) -> AsyncOAuth2Client: ...
        # Erstellt konfigurierten Authlib-Client mit PKCE-Support
        # Bei auto_discover=True: nutzt Authlib's OIDC Discovery automatisch

    def build_authorization_url(self, client: AsyncOAuth2Client, state: str, nonce: str) -> str: ...
        # Delegiert an client.create_authorization_url() (PKCE code_verifier wird automatisch generiert)

    def exchange_code_for_token(self, client: AsyncOAuth2Client, code: str, code_verifier: str) -> dict: ...
        # Delegiert an client.fetch_token() — gibt id_token + access_token zurück

    def validate_state(self, state: str, expected_state: str) -> bool: ...
        # CSRF-Schutz: Vergleicht state-Parameter

    def extract_user_info(self, provider_type: str, id_token: dict, userinfo: dict) -> OAuthUserInfo: ...
        # Normalisiert Provider-spezifische Claims zu einheitlichem Format
        # Google: sub, email, name, picture
        # GitHub: id, email (separater API-Call), login, avatar_url
        # Apple: sub, email, name (nur beim ersten Login — muss gespeichert werden!)
        # OIDC: sub, email, preferred_username, name, picture

    def should_auto_link(
        self, existing_email_verified: bool, oauth_email_verified: bool | None
    ) -> bool: ...
        # True nur wenn BEIDE Seiten bestätigt sind (#1403).
        #
        # Der zweite Parameter ist der `email_verified`-Anspruch des Anbieters und
        # hat DREI Zustände: True, False und None — None heißt, der Anbieter hat
        # nichts gesagt. Der Anspruch ist in OIDC optional, und viele Anbieter
        # lassen ihn weg; GitHub führt ihn gar nicht auf `/user`, sondern pro
        # Adresse auf `/user/emails` (dafür ist der Scope `user:email` nötig).
        #
        # **None lehnt ab.** Schweigen als Bestätigung zu werten reproduziert
        # genau die Lücke, gegen die der Anspruch existiert: ein falsch
        # konfigurierter oder kompromittierter Anbieter behauptet
        # `email = opfer@example.org` und übernimmt das Konto, sofern das lokale
        # Konto bestätigt ist — was jedes regulär registrierte ist. Der Aufrufer
        # landet stattdessen auf dem vorhandenen Weg „mit Passwort anmelden, dann
        # verknüpfen".
        #
        # Bis #1403 reichte der Aufrufort ein literales `True` für den zweiten
        # Parameter, der Anspruch wurde also nie gelesen. Dieselbe Annahme stand
        # im Neuanlage-Pfad: ein über OAuth erzeugtes Konto galt unbesehen als
        # bestätigt und erfüllte damit die erste Bedingung für jeden späteren
        # Anbieter.
```

**`LoginThrottleEngine`** — Brute-Force-Schutz (pure Logik):

```python
class LoginThrottleEngine:
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    def check_allowed(self, failed_attempts: int, locked_until: Optional[datetime]) -> bool: ...
    def calculate_lockout(self, failed_attempts: int) -> Optional[datetime]: ...
        # Exponentielle Verzögerung: 15min, 30min, 1h, 2h, 4h
```

### 3.2 Service-Schicht

**`AuthService`** — Orchestriert Authentifizierungsflows:

```python
class AuthService:
    def __init__(self, user_repo, auth_provider_repo, refresh_token_repo,
                 oidc_config_repo, password_engine, token_engine,
                 oauth_engine, login_throttle_engine, email_service): ...

    # --- Lokale Authentifizierung ---
    async def register_local(self, email: str, password: str, display_name: str,
                             *, on_existing_address: Callable[[UserKey], None] | None = None) -> User: ...
        # 1. Validiert Passwort-Policy (PasswordEngine)
        # 2. Prüft E-Mail-Eindeutigkeit
        # 3. Erstellt User (status: unverified)
        # 4. Sendet Verifizierungs-E-Mail
        # 5. Erstellt persönlichen Default-Tenant (REQ-024)
        # SEC-H-009 (Account-Enumeration-Schutz): Bei bereits existierender E-Mail wird
        # die gleiche generische Antwort zurückgegeben ("Verifizierungs-E-Mail gesendet").
        # An die existierende Adresse wird stattdessen eine Info-Mail gesendet:
        # "Jemand hat versucht, ein Konto mit deiner E-Mail zu erstellen."
        # Der Service verschickt sie NICHT selbst — er reicht nur den Key des
        # existierenden Kontos an `on_existing_address` weiter (Details: §3.2a).

    async def login_local(self, email: str, password: str, remember_me: bool = False) -> TokenPair: ...
        # 1. Prüft Throttle (LoginThrottleEngine)
        # 2. Findet User per E-Mail
        # 3. Verifiziert Passwort (PasswordEngine)
        # 4. Erstellt Token-Paar (TokenEngine), TTL abhängig von remember_me:
        #    - remember_me=True:  Refresh Token 30 Tage, persistentes Cookie
        #    - remember_me=False: Refresh Token 24 Stunden, Session-Cookie
        # 5. Speichert RefreshToken mit is_persistent=remember_me
        # 6. Aktualisiert last_login_at

    async def verify_email(self, token: str) -> User: ...
    async def request_password_reset(self, email: str) -> None: ...
        # Sendet Reset-E-Mail, KEIN Fehler wenn E-Mail nicht existiert (Enumeration-Schutz)
    async def reset_password(self, token: str, new_password: str) -> None: ...
        # Invalidiert alle Refresh Tokens nach Reset

    # --- Föderierte Authentifizierung ---
    async def initiate_oauth(self, provider_slug: str) -> OAuthRedirect: ...
        # 1. Lädt OidcProviderConfig
        # 2. Generiert state + nonce (CSRF-Schutz)
        # 3. Speichert state in Redis (5 Min TTL)
        # 4. Gibt Authorization URL zurück

    async def complete_oauth(self, provider_slug: str, code: str, state: str) -> TokenPair: ...
        # 1. Validiert state (OAuthEngine)
        # 2. Tauscht code gegen Token beim Provider
        # 3. Extrahiert User-Info (OAuthEngine)
        # 4. Findet/erstellt User + AuthProvider
        # 5. Auto-Link falls gleiche verifizierte E-Mail (OAuthEngine)
        # 6. Erstellt JWT-Token-Paar

    # --- Token-Management ---
    async def refresh_tokens(
        self,
        refresh_token: str,
        *,
        device_id: Optional[str] = None,                      # W-004
    ) -> TokenPair: ...
        # Token-Rotation mit Offline-Grace-Window (W-004, UI-NFR-012 R-049):
        #
        # Standard-Pfad (Token noch nicht rotiert):
        #   1. Token validieren (Signatur, Ablauf, revoked-Flag)
        #   2. Neues Token-Paar generieren, family_key vom Vorgänger erben
        #   3. Vorgänger markieren: rotated_at=now, successor_key=neues_hash
        #   4. Neues Token zurückgeben
        #
        # Grace-Window-Pfad (Token bereits rotiert, innerhalb 60s):
        #   - Wenn rotated_at != null UND
        #     (now - rotated_at) <= REFRESH_GRACE_WINDOW_SECONDS UND
        #     stored.device_id == request.device_id (beide nicht null):
        #     → Bereits ausgestellten Nachfolger zurückgeben (idempotent),
        #       KEIN neues Token erzeugen, KEINE Family-Sprengung.
        #
        # Replay-Pfad (Token rotiert, außerhalb Grace-Window oder Device-Mismatch):
        #   - Logge security_event: auth.refresh_replay_detected mit reason
        #     ('grace_expired' | 'device_mismatch' | 'no_device_id')
        #   - Inkrementiere kp_auth_refresh_replay_total{reason=...}
        #   - Invalidiere ALLE Tokens mit gleicher family_key (Family-Sprengung)
        #   - Werfe HTTPException 401 mit error_code='refresh_replay_detected'
        # is_persistent wird vom alten Token übernommen (Session bleibt Session, persistent bleibt persistent)

    async def logout(self, refresh_token: str) -> None: ...
        # Invalidiert das aktuelle Refresh Token

    async def logout_all_devices(self, user_key: str) -> int: ...
        # Invalidiert ALLE Refresh Tokens des Users, gibt Anzahl zurück

    # --- Account-Linking ---
    async def link_provider(self, user_key: str, provider_slug: str, code: str, state: str) -> AuthProvider: ...
    async def unlink_provider(self, user_key: str, provider_key: str) -> None: ...
        # Fehler wenn es die letzte Auth-Methode wäre

    async def add_local_password(self, user_key: str, password: str) -> None: ...
        # Für SSO-Only-User die ein lokales Passwort setzen wollen

    # --- M2M API-Key-Management ---
    async def create_api_key(self, user_key: str, label: str) -> ApiKeyCreated: ...
        # Generiert kryptografisch sicheren Key (kp_ + 48 Hex-Zeichen)
        # Speichert SHA-256-Hash in DB, gibt Klartext einmalig zurück
    async def list_api_keys(self, user_key: str) -> list[ApiKeySummary]: ...
        # Gibt alle aktiven Keys des Users zurück (ohne Hash, mit Prefix-Preview)
    async def revoke_api_key(self, user_key: str, key_id: str) -> None: ...
        # Setzt revoked_at, Key ist sofort ungültig
```

<!-- Quelle: Issue #942 / PR #957 / Issue #958 -->
#### SEC-H-009 — Info-Mail an die bereits registrierte Adresse

Die Info-Mail aus dem Kommentar oben ist **gebaut** (v1.11). Sie steht und fällt
mit zwei Bedingungen. Beide sind hier festgehalten, damit die nächste Person sie
nicht neu herleiten muss — und damit niemand die Mail „vereinfacht" und dabei
genau das Orakel wieder öffnet, das SEC-H-009 schließen soll.

**Bedingung 1 — asynchrone Zustellung, nach der Antwort.**
`require_email_verification` ist per Default `false`. Eine *echte* Registrierung
verschickt also **gar keine Mail**. Ein synchroner SMTP-Roundtrip nur im
Duplikat-Zweig macht diesen Zweig damit messbar **langsamer** als eine echte
Registrierung — dieselbe Auskunft, nur über die Uhr statt über den Body. Schlimmer
noch: `SmtpEmailAdapter._send` wirft weiter, ein Zustellfehler würde aus dem
Duplikat-Zweig eine **500** machen, während die echte Registrierung 201 antwortet.
Das wäre ein *stärkeres* Orakel als das ursprüngliche.

Deshalb:

* `AuthService.register_local` verschickt nichts. Es ruft nur den Callback
  `on_existing_address(user_key)` auf — vertraglich nicht-blockierend.
* Der Router (`POST /auth/register`) hängt daran einen **FastAPI-Background-Task**.
  Starlette sendet erst die Response und ruft danach `response.background` auf;
  weder der Import noch das Einreihen noch ein hängender Broker liegen im
  Zeitfenster, das ein Aufrufer mit Stoppuhr misst.
* Der Background-Task reiht den Celery-Task
  `app.tasks.auth_tasks.send_duplicate_registration_notice` ein und schluckt eine
  Broker-Störung (geloggt, nicht geworfen). Kein Retry, kein Outbox — die Mail ist
  rein informativ.
* Nutzlast ist der **Konto-Key**, nicht die Adresse: die Adresse gehört einem
  Dritten und läge sonst im Klartext in der Broker-Queue (NFR-011).

Gemessen (Median über 25 bzw. 15 Durchläufe je Zweig, gleiche Maschine, gleiche
Bedingungen wie in #957): Verhältnis echt/duplikat **1.000× vorher → 0.999×
nachher** auf Service-Ebene und **1.001× → 1.001× (Broker ok), 1.002× (Broker
tot), 0.999× (Broker hängt 5 s)** über HTTP. Der hängende Broker ist der
eigentliche Beweis: er kostet den Duplikat-Zweig nichts, weil er hinter der
Antwort liegt.

**Bedingung 2 — Sperrfenster je Empfängeradresse, nicht je Absender-IP.**
`/auth/register` ist anonym: der Angreifer wählt Empfänger *und* Auslöser. Ohne
Schranke pro Empfänger ist die Mail ein unauthentifiziertes Mail-Bombing-Primitiv
auf Kosten der Absender-Reputation dieser Installation. Eine Sperre gegen die
*Quelle* hilft nicht — sie legt Passwort-Reset und E-Mail-Verifikation für alle
mit lahm.

* `IRegistrationNoticeStore.claim(email)` gewährt pro Adresse **einen** Versand
  pro Fenster (24 h). Der Anspruch wird atomar erhoben (`SET … NX EX`), sonst
  senden zwei gleichzeitige Versuche beide.
* Zwei Stufen, analog `IUnknownAccountStore`: Valkey (geteilt über Worker) mit
  Rückfall auf eine beschränkte In-Process-Map. Bei Redis-Störung wird **nicht**
  fail-open entschieden — das wäre genau der unbeschränkte Versand.
* Schlüssel ist der SHA-256 der normalisierten Adresse; die Adresse selbst wird
  nirgends im Klartext abgelegt oder geloggt (NFR-011).
* Der Anspruch wird **vor** dem Versand erhoben. Ein Zustellfehler verbrennt damit
  das Fenster — bewusst: die Schranke existiert gegen den anonymen Auslöser, und
  ein SMTP-Ausfall darf sie nicht aufheben.

**Inhalt der Mail** (DE kanonisch, EN als Spiegel;
`RegistrationNoticeEngine`, Auswahl über `user.locale`, Fallback `de`):
Sie nennt genau den Vorgang, stellt fest, dass **nichts** passiert ist, und
verlinkt Anmeldung und Passwort-Reset (aus `frontend_url`, nie aus Request-Daten).
Sie enthält **nicht**: den vom Aufrufer gewählten Anzeigenamen (sonst wird die
Mail zum Nachrichtenkanal in fremde Postfächer), das eingegebene Passwort, die
IP, irgendein Feld des betroffenen Kontos und keinerlei Token oder Ein-Klick-Aktion.
Sie geht nicht an deaktivierte oder gelöschte Konten.

<!-- Quelle: Widerspruchsanalyse W-004 -->
### 3.2a Refresh-Token Family + Offline-Grace-Window (W-004)

Diese Sektion spezifiziert die in §3.2 angedeutete Grace-Window-Logik im Detail. Hintergrund: PWA-Reconnect-Race nach Offline-Phase (UI-NFR-012 R-049).

#### Konzept Token-Family

Jeder erfolgreiche Login (Local oder OAuth) erzeugt ein **frisches Refresh-Token mit neuer `family_key` (UUID4)**. Bei Token-Rotation wird die `family_key` an den Nachfolger weitergegeben — alle aus diesem Login entstehenden Tokens teilen die Family.

```
Login Tablet (12:00)        →  T1 (family=F1)
  Refresh Tablet (13:00)    →  T2 (family=F1, T1.successor_key=T2.hash)
    Refresh Tablet (14:00)  →  T3 (family=F1, T2.successor_key=T3.hash)

Login Desktop (12:30)       →  T4 (family=F2)              # andere Family!
  Refresh Desktop (13:30)   →  T5 (family=F2, T4.successor_key=T5.hash)
```

Replay-Detection auf F1 (z.B. T1 wird nach 14:00 nochmal eingereicht) sprengt nur F1 — Desktop (F2) bleibt unbetroffen.

#### Grace-Window-Algorithmus (Pseudocode)

```python
GRACE_WINDOW = timedelta(seconds=60)


async def refresh_tokens(
    raw_token: str,
    *,
    device_id: Optional[str],
) -> TokenPair:
    stored = await refresh_token_repo.get_by_hash(sha256(raw_token))
    if stored is None or stored.revoked or stored.expires_at < now():
        raise UnauthorizedError("invalid_token")

    # --- Grace-Window-Pfad ---
    if stored.rotated_at is not None:
        age = now() - stored.rotated_at
        device_match = (
            stored.device_id is not None
            and device_id is not None
            and stored.device_id == device_id
        )

        if age <= GRACE_WINDOW and device_match:
            # Idempotent: bereits ausgestellten Nachfolger zurückgeben
            successor = await refresh_token_repo.get_by_hash(stored.successor_key)
            return TokenPair(
                access_token=mint_access_token(successor.user_key),
                refresh_token_handle=successor.handle,
            )

        # Replay erkannt — Family sprengen
        reason = (
            "grace_expired" if age > GRACE_WINDOW
            else "device_mismatch" if (stored.device_id and device_id)
            else "no_device_id"
        )
        await _detect_and_handle_replay(stored, reason)
        raise UnauthorizedError(
            error_code="refresh_replay_detected",
            family_invalidated=stored.family_key,
        )

    # --- Standard-Pfad (Token noch nicht rotiert) ---
    new_token = await _create_refresh_token(
        user_key=stored.user_key,
        family_key=stored.family_key,           # Family weitergeben
        device_id=device_id or stored.device_id,
        is_persistent=stored.is_persistent,
    )
    await refresh_token_repo.mark_rotated(
        token_hash=stored.token_hash,
        successor_key=new_token.token_hash,
        rotated_at=now(),
    )
    return TokenPair(
        access_token=mint_access_token(stored.user_key),
        refresh_token_handle=new_token.handle,
    )


async def _detect_and_handle_replay(stored: RefreshToken, reason: str) -> None:
    """Telemetrie + Family-Sprengung bei nachgewiesenem Replay."""
    logger.warning(
        "auth.refresh_replay_detected",
        family_key=stored.family_key,
        user_key=stored.user_key,
        reason=reason,
        token_age_seconds=(now() - stored.rotated_at).total_seconds(),
    )
    metrics.kp_auth_refresh_replay_total.labels(reason=reason).inc()

    # Alle Tokens der Family invalidieren (hard)
    affected = await refresh_token_repo.revoke_family(stored.family_key)
    logger.info(
        "auth.token_family_invalidated",
        family_key=stored.family_key,
        revoked_count=affected,
    )
```

#### Verhaltenstabelle

| Situation | `rotated_at` | Alter | Device-Match | Verhalten |
|-----------|--------------|-------|--------------|-----------|
| Token aktiv | `null` | — | — | Standard-Rotation, neues Paar ausstellen |
| Bereits rotiert, Grace, Match | gesetzt | ≤ 60s | ja | **Idempotent:** vorhandenen Nachfolger zurückgeben |
| Bereits rotiert, Grace, Mismatch | gesetzt | ≤ 60s | nein | **Replay:** Family sprengen, 401 |
| Bereits rotiert, Grace, no `device_id` | gesetzt | ≤ 60s | n/a (eines `null`) | **Replay:** Family sprengen, 401 |
| Bereits rotiert, außerhalb Grace | gesetzt | > 60s | beliebig | **Replay:** Family sprengen, 401 |

`device_id=null` auf beiden Seiten → kein Match möglich → kein Grace-Window. Das schützt API-Clients ohne PWA-Setup vor einem versehentlichen Replay-Schutz, indem solche Clients schlicht nicht doppelt rotieren dürfen.

#### Telemetrie

**Structlog-Event** (`logger.warning`):

```python
event="auth.refresh_replay_detected"
fields=[family_key, user_key, reason, token_age_seconds]
```

`reason` ∈ `{"grace_expired", "device_mismatch", "no_device_id"}`.

**Prometheus-Counter:**

```
kp_auth_refresh_replay_total{reason="grace_expired|device_mismatch|no_device_id"}
kp_auth_token_family_invalidated_total
```

Alerts (NFR-012, optional):
- > 5 Replay-Events pro 5 min für denselben User → wahrscheinlich Bug oder Angriff
- > 50 Replay-Events pro 5 min systemweit → systematischer Angriff oder Deployment-Regression

#### Hard Cutover bei v1.9-Deployment

Bei Deployment dieser Version werden **alle bestehenden Refresh-Tokens invalidiert** — bestehende Tokens haben kein `family_key`, kein `device_id`, kein `successor_key` und können nicht zuverlässig im Grace-Window-Schema betrieben werden.

```python
# Migrations-Skript (einmalig zur Deployment-Zeit)
async def cutover_refresh_tokens_v19():
    """W-004: Hard Cutover beim Upgrade auf v1.9.

    Alle bestehenden Refresh-Tokens werden revoked. Alle User müssen
    sich neu anmelden. Begründung: Bestehende Tokens haben kein
    family_key/device_id — Grace-Window-Schutz wäre nicht zuverlässig.
    """
    affected = await refresh_token_repo.revoke_all_active()
    logger.warning(
        "auth.v19_cutover_completed",
        revoked_count=affected,
        note="All active refresh tokens invalidated; users must re-login",
    )
```

Operator-Kommunikation: Im Release-Notes-Hinweis vermerken, dass alle User nach dem Upgrade neu einloggen müssen — analog zu Hash-Algorithmus-Wechseln in der Vergangenheit.

#### Frontend-Verhalten (Cross-Reference)

Frontend-Anforderungen sind in **UI-NFR-012 §3.9** definiert:
- R-049: `X-Device-Id`-Header beim Refresh-Aufruf mitsenden
- R-049a: Bei `error_code='refresh_replay_detected'` lokale Tokens löschen, Re-Login auffordern, Offline-Daten erhalten
- R-049b: `device_id` als UUIDv4 in IndexedDB persistieren, beim ersten Login generiert

<!-- /Quelle: Widerspruchsanalyse W-004 -->

<!-- Quelle: Smart-Home-HA-Integration Review A-003 -->
### 3.7 M2M-Authentifizierung (API-Keys)

Neben der JWT-basierten Browser-Authentifizierung unterstützt Kamerplanter **langlebige API-Keys** für Machine-to-Machine-Zugriff. Hauptanwendungsfälle: Home Assistant Custom Integration, CI/CD-Pipelines, Monitoring-Systeme.

<!-- Quelle: Widerspruchsanalyse W-015 -->
**Light-Modus-Hinweis (W-015):** Service Accounts und API-Keys sind im Light-Modus (REQ-027) **deaktiviert** — die Light-Modus-Endpunkte sind ohne Auth erreichbar, externe Integrationen brauchen keinen Bearer-Token. Bei Upgrade Light→Full (REQ-027 §1.1 Szenario 5) müssen externe Integrationen auf Service-Account-API-Keys umgestellt werden; bestehende Konfigurationen erhalten 401 beim nächsten API-Aufruf nach Mode-Switch.
<!-- /Quelle: Widerspruchsanalyse W-015 -->

#### Datenmodell

**`ApiKey`** — ArangoDB Document Collection `api_keys`:

```python
class ApiKey(BaseModel):
    _key: str                          # Auto-generiert
    user_key: str                      # Besitzer (human User ODER Service Account)
    label: str                         # Vom User vergebener Name (z.B. "Home Assistant")
    key_prefix: str                    # Erste 8 Zeichen des Keys (für Anzeige: "kp_a3f8...")
    key_hash: str                      # SHA-256-Hash des vollständigen Keys
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    tenant_scope: str | None = None    # Optional: Key auf einen Tenant beschränken
```

**Edge:** `has_api_key` (User → ApiKey) — funktioniert für `account_type: 'human'` und `account_type: 'service'` gleichermaßen, da Service Accounts als User modelliert sind.

#### Key-Format

```
kp_<48 hex characters>
```

- Prefix `kp_` identifiziert Kamerplanter-Keys (unterscheidbar von JWTs)
- 48 Hex-Zeichen = 192 Bit Entropie (kryptografisch sicher via `secrets.token_hex(24)`)
- Speicherung in DB: **nur SHA-256-Hash** — Klartext wird bei Erstellung einmalig angezeigt

#### Middleware-Erkennung

```python
# Authorization-Header-Auswertung:
# Bearer kp_...  → API-Key-Lookup (SHA-256-Hash vergleichen)
# Bearer eyJ...  → JWT-Validierung (bestehender Flow)
```

Die Middleware erkennt anhand des `kp_`-Prefix automatisch, ob ein API-Key oder JWT vorliegt. API-Keys werden gegen den gespeicherten Hash validiert und `last_used_at` wird aktualisiert.

<!-- Quelle: Service Accounts v1.7 -->
**Erweiterter Flow bei Service-Account-API-Keys:**

Bei API-Key-Authentifizierung wird zusätzlich geprüft:
1. **IP-Allowlist:** Wenn `allowed_ip_ranges` auf dem zugehörigen User (Service Account) gesetzt ist, wird die Client-IP gegen die CIDR-Bereiche geprüft. Mismatch → 403 Forbidden.
2. **Service-Account-Status:** `status` des Service Accounts muss `active` sein. Suspended/Deleted → 401 Unauthorized.
3. **Rate Limit:** `rate_limit_rpm` des Service Accounts wird als individuelle Obergrenze verwendet (statt des globalen 1000 req/min Defaults).
4. **`last_active_at`:** Wird bei jedem erfolgreichen API-Key-Zugriff auf dem Service Account aktualisiert.
<!-- /Quelle: Service Accounts v1.7 -->

#### Rate Limiting

| Auth-Methode | Rate Limit | Begründung |
|-------------|-----------|-----------|
| JWT (Browser) | 100 req/min | Interaktive Nutzung, geringere Last |
| API-Key (M2M) | 1000 req/min | Coordinator-Polling, Batch-Operationen |

#### API-Endpoints

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| `POST` | `/api/v1/auth/api-keys` | Neuen API-Key erstellen | JWT (nur authentifizierte User) |
| `GET` | `/api/v1/auth/api-keys` | Alle eigenen Keys auflisten | JWT |
| `DELETE` | `/api/v1/auth/api-keys/{key_id}` | Key revoken | JWT |

**POST /api/v1/auth/api-keys — Request:**
```json
{
  "label": "Home Assistant",
  "tenant_scope": "mein-garten"
}
```

**POST /api/v1/auth/api-keys — Response (einmalig mit Klartext):**
```json
{
  "_key": "ak_001",
  "label": "Home Assistant",
  "api_key": "kp_a3f8e7b2c9d4f1a6e8b3c5d7f9a2b4c6d8e0f1a3b5c7d9e1f3",
  "key_prefix": "kp_a3f8...",
  "created_at": "2026-02-27T14:30:00Z",
  "tenant_scope": "mein-garten"
}
```

> **Hinweis:** Der vollständige Key wird nur bei der Erstellung angezeigt. Nach dem Schließen des Dialogs ist er nicht mehr abrufbar. Bei Verlust muss ein neuer Key erstellt werden.

**`UserService`** — Benutzerprofil-Verwaltung:

```python
class UserService:
    def __init__(self, user_repo, auth_provider_repo): ...

    async def get_profile(self, user_key: str) -> UserProfile: ...
    async def update_profile(self, user_key: str, updates: UserProfileUpdate) -> User: ...
        # Erlaubte Felder: display_name, avatar_url, locale, timezone
    async def list_auth_providers(self, user_key: str) -> list[AuthProviderInfo]: ...
    async def list_active_sessions(self, user_key: str) -> list[SessionInfo]: ...
    async def delete_account(self, user_key: str) -> None: ...
        # Soft-Delete: status → deleted, E-Mail anonymisiert
        # Alle Refresh Tokens invalidiert
        # Tenant-Mitgliedschaften entfernt (REQ-024)
```

### 3.3 API-Schicht

**Router: `/api/v1/auth`** — Authentifizierung:

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| POST | `/auth/register` | Lokale Registrierung | Nein |
| POST | `/auth/login` | Lokaler Login (Body: `email`, `password`, `remember_me: bool = false`) | Nein |
| POST | `/auth/logout` | Logout (aktuelles Gerät) | Ja |
| POST | `/auth/logout-all` | Logout (alle Geräte) | Ja |
| POST | `/auth/refresh` | Token-Refresh (Cookie-Pfad **oder** optionaler Body-Token `{"refresh_token"}` für native Clients, #1118 — siehe §3.8) | Nein (Cookie oder Body) |
| POST | `/auth/device-pairing` | Einmaligen QR-Kopplungscode erzeugen (#1118, §3.8) | Ja (Bearer) |
| POST | `/auth/device-pairing/redeem` | QR-Kopplungscode gegen Token-Paar einlösen (#1118, §3.8) | Nein (öffentlich) |
| POST | `/auth/verify-email` | E-Mail bestätigen | Nein |
| POST | `/auth/password-reset/request` | Passwort-Reset anfordern | Nein |
| POST | `/auth/password-reset/confirm` | Passwort-Reset durchführen | Nein |
| GET | `/auth/oauth/providers` | Aktivierte Provider auflisten (für Login-Seite) | Nein |
| GET | `/auth/oauth/{provider_slug}` | OAuth-Redirect initiieren | Nein |
| GET | `/auth/oauth/{provider_slug}/callback` | OAuth-Callback verarbeiten | Nein |

**Router: `/api/v1/users`** — Benutzerverwaltung:

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| GET | `/users/me` | Eigenes Profil abrufen | Ja |
| PATCH | `/users/me` | Eigenes Profil aktualisieren | Ja |
| GET | `/users/me/providers` | Verknüpfte Auth-Provider auflisten | Ja |
| POST | `/users/me/providers/{provider_slug}/link` | Provider verknüpfen | Ja |
| DELETE | `/users/me/providers/{provider_key}` | Provider-Verknüpfung entfernen | Ja |
| POST | `/users/me/password` | Lokales Passwort setzen/ändern | Ja |
| GET | `/users/me/sessions` | Aktive Sessions auflisten | Ja |
| DELETE | `/users/me/sessions/{session_key}` | Einzelne Session beenden | Ja |
| DELETE | `/users/me` | Account löschen (Soft-Delete) | Ja |

**Router: `/api/v1/admin/oidc-providers`** — OIDC-Provider-Verwaltung (nur System-Admin):

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| GET | `/admin/oidc-providers` | Alle konfigurierten Provider auflisten | Plattform-Admin |
| POST | `/admin/oidc-providers` | Neuen OIDC-Provider registrieren | Plattform-Admin |
| GET | `/admin/oidc-providers/{slug}` | Provider-Details abrufen | Plattform-Admin |
| PATCH | `/admin/oidc-providers/{slug}` | Provider aktualisieren | Plattform-Admin |
| DELETE | `/admin/oidc-providers/{slug}` | Provider deaktivieren | Plattform-Admin |
| POST | `/admin/oidc-providers/{slug}/test` | OIDC-Discovery testen | Plattform-Admin |

**Gesamtanzahl API-Endpunkte:** ~25

### 3.4 Middleware

**`AuthMiddleware`** — FastAPI Dependency für geschützte Endpunkte:

```python
async def get_current_user(
    authorization: str = Header(None),
    token_engine: TokenEngine = Depends(get_token_engine),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    """Extrahiert und validiert den Access Token.
    Gibt den vollständigen User zurück.
    Wirft 401 bei fehlendem/ungültigem Token."""

async def get_current_user_optional(
    authorization: str = Header(None),
    token_engine: TokenEngine = Depends(get_token_engine),
    user_repo: UserRepository = Depends(get_user_repo),
) -> Optional[User]:
    """Wie get_current_user, gibt aber None statt 401 bei fehlendem Token.
    Für Endpunkte die sowohl authentifiziert als auch anonym funktionieren."""

def require_role(role: str):
    """Factory für Dependency die eine bestimmte Tenant-Rolle erfordert.
    Wird in REQ-024 vollständig spezifiziert."""
```

### 3.5 Celery-Tasks

| Task | Schedule | Beschreibung |
|------|----------|-------------|
| `cleanup_expired_tokens` | Stündlich | Entfernt abgelaufene/revoked Refresh Tokens |
| `cleanup_unverified_accounts` | Täglich 03:00 | Löscht unbestätigte Accounts älter als 7 Tage |
| `rotate_oidc_discovery` | Alle 6 Stunden | Aktualisiert OIDC-Discovery-Dokumente (JWKS, Endpoints) |

<!-- Quelle: Issue #1118 -->
### 3.8 Gerätekopplung per QR-Code (#1118)

Eine native App (aktuell nur der Kontrakt, die Flutter-App selbst ist ausgeklammert — siehe §9) meldet sich ohne Passwort-Eingabe an, indem sie einen im Browser erzeugten QR-Code scannt. Der Flow ist vollständig aus der bestehenden REQ-023-Maschinerie zusammengesetzt: er stellt **keine** neue Token-Klasse und **keinen** neuen Claim aus.

**Einmalcode nur in Redis — kein neuer Node, keine neue Collection.**
Der Kopplungscode wird ausschließlich in Redis abgelegt (Store `IDevicePairingCodeStore` / `RedisDevicePairingCodeStore`, TTL-`SET` + pipelined `GET`+`DEL` für atomaren Einmalgebrauch, analog zum OAuth-State-Store). Es gibt **bewusst** keinen ArangoDB-Node und keine neue Collection dafür — die Einlösung ist ein flüchtiger Vorgang, kein zu persistierender Datensatz. Der Rohcode ist nie Redis-Key oder -Value; gespeichert wird `sha256(code)`. Die **Prüfspur** sind strukturierte structlog-Events (`device_pairing_created`, `device_pairing_redeemed`, `device_pairing_redeem_failed`) — genau wie jedes andere Auth-Ereignis in diesem Code, **nicht** ein persistiertes Protokoll (siehe §9 und die Abgrenzung des allgemeinen Audit-Logs).

**TTL-Grenzen.**
Die Lebensdauer des Codes steuert `settings.device_pairing_ttl_seconds` (Default `90`, im Settings-Modell validiert `ge=60, le=120`). Ein Wert außerhalb 60–120 s verweigert den Start, statt still geklemmt zu werden. Unter 60 s läuft der Code ab, bevor der Nutzer scannen kann; über 120 s überlebt er den Moment, in dem der Nutzer auf den Bildschirm sah.

**Rate-Limit und Sperre bei Einlösung.**
Die Einlösung ist rate-limitiert (`settings.rate_limit_device_pairing_redeem`, Default `10/minute`, bewusst unter `rate_limit_auth`). Der slowapi-Limiter arbeitet dabei — wie an allen Auth-Routen — **global** (nicht pro IP). Der eigentliche verhaltensbasierte Schutz ist eine **Sperre pro Quell-IP**: `AuthService.redeem_device_pairing` zählt Fehlversuche je Adresse (`resolve_client_ip`, proxy-bewusst) und entscheidet die Sperre über **denselben** `LoginThrottleEngine`, den auch `login_local` nutzt (kein zweiter Schwellwert). **Reihenfolge:** Die Sperre wird geprüft, **bevor** der Code-Store konsultiert wird — ein gesperrter Versuch verbraucht den Code also nicht. Ein erfolgreicher Versuch leert den Zähler der IP.

**Einlösung liefert das bestehende Token-Paar.**
`redeem_device_pairing` ruft dieselbe Fabrik `_create_tokens` wie `login_local` und `complete_oauth` — dasselbe Access-/Refresh-Paar, dieselbe `RefreshToken`-Session (in der Sessions-Liste sichtbar und dort widerrufbar), keine neue Token-Art. Das Konto stammt aus dem gespeicherten Code-Record, nie aus einer vom Aufrufer gelieferten Identität. Unbekannter, benutzter, abgelaufener und unlesbarer Code liefern **eine** generische 401 (kein Orakel); ein deaktiviertes Konto 401; eine gesperrte IP 423 mit Restminuten.

**Autorisierung pro Request, nicht im Token eingefroren.**
Das Access Token trägt — wie bei jedem Login — nur die zum Ausstellungszeitpunkt aufgelösten Tenant-Rollen; die tatsächliche Zugriffsentscheidung fällt pro Request aus der Mitgliedschaft (`get_current_tenant`, REQ-024). Ein gekoppeltes Gerät verliert den Zugriff auf einen Tenant daher **sofort**, sobald die Mitgliedschaft entzogen wird — die Kopplung schafft keinen von der Mitgliedschaft entkoppelten Dauerzugriff.

**Body-getragener Refresh für native Clients.**
Ein per QR gekoppeltes Gerät hält den Rohwert des Refresh-Tokens im Plattform-Keystore und hat weder Cookie-Jar noch `csrf_token`-Cookie. Damit das ausgestellte Paar überhaupt rotierbar ist, akzeptiert `POST /auth/refresh` seit v1.12 einen **optionalen** JSON-Body `{"refresh_token": "…"}`:

- Ist ein Body-Token vorhanden, **schlägt der Body den Cookie** (kein „erst Body, dann Cookie"-Fallback — der wäre die eigentliche Lücke). Der Cookie wird vollständig ignoriert, es wird **kein** `kp_refresh`-Cookie gesetzt, und der rotierte Token kommt im Body zurück (`TokenPairResponse`).
- Auf dem Body-Pfad wird `verify_csrf` **nicht** aufgerufen: Ein Body-Token ist kein ambient übertragenes Credential, daher greift die Double-Submit-Abwehr nicht (siehe präzisierte CSRF-Tabelle in §1). Ein ungültiger Body-Token liefert 401, **ohne** den Cookie zu verbrauchen.
- Der **Cookie-Pfad bleibt byte-identisch**: fehlender Cookie → 401 vor jeder CSRF-Prüfung; vorhandener Cookie → `verify_csrf` wie bisher, Rotation als Cookie.

Die Ausgabe-Endpunkte:

- `POST /auth/device-pairing` — **Bearer-authentifiziert** (`get_current_user`, kein CSRF, wie `create_api_key`), liefert `{payload_version, server_url, code, expires_at, expires_in}`. `server_url` stammt aus `settings.app_base_url` (der QR-SSOT aus REQ-032), nie aus `request.base_url` (hinter Traefik cluster-intern und für das scannende Telefon unerreichbar). QR-Nutzlast: `{"v": payload_version, "url": server_url, "code": code}`.
- `POST /auth/device-pairing/redeem` — **öffentlich** (`security: []` in der generierten OpenAPI, damit der ZAP-Auth-Bypass-Check korrekt einordnet), liefert `{access_token, token_type, expires_in, refresh_token}` und setzt **keinen** Cookie.

Beide Endpunkte hängen am `auth_router` (nicht am `api_keys_router`) und sind daher im Light-Modus (REQ-027) nicht gemountet — eine Light-Instanz antwortet auf beide mit **404**.
<!-- /Quelle: Issue #1118 -->

## 4. Frontend

### 4.1 Neue Seiten

| Seite | Route | Beschreibung |
|-------|-------|-------------|
| `LoginPage` | `/login` | E-Mail/Passwort-Login + SSO-Buttons |
| `RegisterPage` | `/register` | Lokale Registrierung |
| `EmailVerificationPage` | `/verify-email/:token` | E-Mail-Bestätigung |
| `PasswordResetRequestPage` | `/password-reset` | Passwort-Reset anfordern |
| `PasswordResetConfirmPage` | `/password-reset/:token` | Neues Passwort setzen |
| `AccountSettingsPage` | `/settings/account` | Profil, Auth-Provider, Sessions |

### 4.2 Komponenten

**`LoginPage`:**
- E-Mail + Passwort-Formular
- **Checkbox „Angemeldet bleiben"** (`remember_me`) — unterhalb des Passwort-Felds, vor dem Login-Button. Standard: nicht aktiviert. Tooltip: „Aktiviere diese Option nur auf privaten Geräten. Deine Sitzung bleibt bis zu 30 Tage aktiv."
- Divider "oder"
- SSO-Buttons (dynamisch aus `/api/v1/auth/oauth/providers`):
  - Google: Offizielles Google-Sign-In-Branding
  - GitHub: GitHub-Logo + "Mit GitHub anmelden"
  - Apple: Offizielles Apple-Sign-In-Branding (Dark/Light Modus)
  - Generische OIDC: icon_url + display_name
- Link zu "Passwort vergessen"
- Link zu "Registrieren"

**`AccountSettingsPage`:**
- **Tab "Profil":** Anzeigename, Avatar (URL-Eingabe), Sprache (DE/EN), Zeitzone
- **Tab "Sicherheit":** Passwort ändern/setzen, Verknüpfte Provider (Google ✓, GitHub ✓, etc.), Provider entfernen
- **Tab "Sessions":** Liste aktiver Sessions (Gerät, IP, Zeitpunkt, „Angemeldet bleiben" Ja/Nein), "Andere Sessions beenden"-Button
- **Tab "API-Keys":** Verwaltung von M2M-API-Keys (siehe §3.7)
- **Tab "Integrationen":** Home Assistant Verbindung konfigurieren (siehe Detailbeschreibung unten)
- **Tab "Account":** Account löschen (Bestätigungs-Dialog mit Passworteingabe)

**Tab "Integrationen" — Detailbeschreibung:**

Ermöglicht dem Nutzer, seine Home Assistant Instanz mit Kamerplanter zu verbinden. Der hier hinterlegte Long-Lived Access Token wird vom `HomeAssistantConnector` (REQ-005) verwendet, um Sensordaten automatisch von Home Assistant abzurufen.

**Sichtbarkeit:** Der Tab „Integrationen" ist immer sichtbar — er dient als zentrale Stelle, an der der Nutzer die HA-Integration aktivieren oder deaktivieren kann. Solange die HA-Integration nicht aktiviert ist (`ha_token_set == false`), werden in allen anderen Bereichen des Systems (Sensoren, Aktoren, Tanks, Dashboard) die HA-spezifischen Felder und Panels ausgeblendet (siehe REQ-005 §4a Optionalitätsprinzip).

**Felder:**

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| Home Assistant URL | Text | URL der HA-Instanz (z.B. `http://homeassistant.local:8123`). Validierung: gültige URL, erreichbar beim Verbindungstest. |
| Long-Lived Access Token | Passwort | HA-Token aus Profil → Sicherheit → Long-Lived Access Tokens. Wird AES-256-verschlüsselt gespeichert, in der UI nach dem Speichern nur als `••••••••` angezeigt. |
| Verbindungsstatus | Chip | Zeigt den aktuellen Status: ✅ Verbunden (HA-Version), ⚠️ Nicht erreichbar, ❌ Nicht konfiguriert |

**Aktionen:**

- **Verbindung testen** → `POST /api/v1/auth/ha-connection/test` — Ruft HA `/api/` auf, zeigt Erfolg/Fehler mit HA-Version
- **Speichern** → `PATCH /api/v1/users/me` mit `ha_url` und `ha_token` (Token wird serverseitig verschlüsselt)
- **Token entfernen** → Setzt `ha_url` und `ha_token_encrypted` auf `null`

**Sicherheitshinweis:** Der Token wird niemals im Klartext an das Frontend zurückgegeben. `GET /api/v1/users/me` liefert nur `ha_url` und `ha_token_set: bool` (ob ein Token hinterlegt ist).

<!-- Quelle: Smart-Home-HA-Integration Review A-003 -->
**Tab "API-Keys" — Detailbeschreibung:**

Ermöglicht dem Nutzer, beliebig viele personalisierte API-Keys zu erstellen und zu verwalten — für Home Assistant, Monitoring, CI/CD oder andere M2M-Consumer.

**Ansicht: Key-Liste (Tabelle)**

| Spalte | Beschreibung |
|--------|-------------|
| Label | Vom User vergebener Name (z.B. "Home Assistant Zelt 1") |
| Key-Prefix | Erste 8 Zeichen (`kp_a3f8...`) — zur Identifikation |
| Tenant-Scope | Eingeschränkter Tenant oder "Alle" |
| Erstellt | Erstelldatum (relativ, z.B. "vor 3 Tagen") |
| Letzter Zugriff | Zeitpunkt der letzten Nutzung oder "Nie verwendet" |
| Aktion | Revoke-Button (Mülleimer-Icon) |

**Aktion: Neuen Key erstellen (Dialog)**

- **Label** (Pflicht): Freitext-Eingabe, z.B. "Home Assistant", "Grafana", "CI/CD Pipeline"
- **Tenant-Scope** (Optional): Dropdown mit eigenen Tenants + Option "Alle Tenants"
- **Erstellen-Button** → `POST /api/v1/auth/api-keys`
- **Ergebnis-Dialog (einmalig):** Zeigt den vollständigen Key im Klartext in einem read-only Textfeld mit Copy-Button. **Warnhinweis:** "Dieser Key wird nur einmal angezeigt. Kopieren Sie ihn jetzt und speichern Sie ihn sicher. Nach dem Schließen dieses Dialogs ist der Klartext-Key nicht mehr abrufbar."

**Aktion: Key revoken (Bestätigung)**

- Klick auf Revoke-Button → Bestätigungs-Dialog: "API-Key '{label}' wirklich widerrufen? Alle Anwendungen die diesen Key verwenden verlieren sofort den Zugriff."
- Bestätigen → `DELETE /api/v1/auth/api-keys/{key_id}`
- Key verschwindet aus der Liste (oder wird als "Widerrufen" markiert)

**Leerzustand:** "Keine API-Keys vorhanden. Erstellen Sie einen Key für Home Assistant, Monitoring oder andere Anwendungen."

### 4.3 Auth-State-Management (Redux)

```typescript
interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// Thunks:
// loginLocal(email, password, rememberMe) → setzt user + accessToken
// loginOAuth(providerSlug) → Redirect zu OAuth-Provider
// oauthCallback(providerSlug, code, state) → setzt user + accessToken
// refreshToken() → nutzt Cookie, aktualisiert accessToken
// logout() → löscht State + Cookie
```

### 4.4 Axios-Interceptor

```typescript
// Request-Interceptor: Fügt Authorization-Header hinzu
// Response-Interceptor: Bei 401 → automatischer Token-Refresh → Retry
// Falls Refresh fehlschlägt → Logout + Redirect zu /login
```

### 4.5 Route-Guards

```typescript
// ProtectedRoute: Erfordert authentifizierten User, Redirect zu /login
// PublicOnlyRoute: Nur für nicht-authentifizierte User (Login/Register), Redirect zu /dashboard
```

<!-- Quelle: Issue #1118 -->
### 4.6 Gerät-verbinden-Dialog (Sessions-Tab, #1118)

Im Tab „Sessions" der `AccountSettingsPage` (der ohnehin nur im Full-Modus existiert, sodass der Light-Modus baulich ausgeschlossen ist) öffnet eine Aktion „Gerät verbinden" den Dialog `ConnectDeviceDialog`. Er fordert über `POST /auth/device-pairing` einen Einmalcode an und rendert die QR-Nutzlast `{"v":…,"url":…,"code":…}` als `<QRCodeSVG>`.

- Ein Countdown zeigt die Restsekunden (`expires_in`); bei Null wird der QR durch einen Ablauf-Zustand mit „Neu erzeugen"-Aktion ersetzt, die einen frischen Code holt.
- Der Code erscheint **nirgends** als sichtbarer Text im Dialog (Schutz gegen Shoulder-Surfing) — nur im `value`-Prop des QR-Codes.
- Der Code wird nicht in Redux oder `localStorage` gehalten; Schließen des Dialogs verwirft ihn aus dem Komponenten-State. Nach dem Schließen wird die Sessions-Liste neu geladen, sodass ein frisch gekoppeltes Gerät dort erscheint.
- Alle Nutzertexte liegen als i18n-Keys unter `pages.auth.*` in DE und EN vor.

Im **Light-Modus** (REQ-027) existiert weder der Sessions-Tab noch ein Konto, und die Kopplungs-Endpunkte antworten mit `404`. Damit ein anonymer Nutzer eine Mobil-App dennoch auf die Instanz ausrichten kann, ist `ConnectDeviceDialog` modus-abhängig: Über einen eigenen Tab „App verbinden" (`connect`) im Light-Modus-Tab-Set öffnet er dort eine **reine URL-Variante**. Diese rendert seit #1118 P13 einen **App-Link-URL-String** `https://<window.location.origin>/connect?v=1` (kein JSON, kein `code`) als QR — bewusst eine URL und kein JSON-Blob, damit die System-Kamera eines Smartphones ihn als Link erkennt. Sie führt **keinen** Backend-Aufruf durch und hat weder Countdown noch Ablauf/Neu-Erzeugen; sie dient ausschließlich der Instanz-Erkennung und meldet niemanden an. Der Full-Modus-Pfad (Sessions-Tab, opakes JSON `{"v","url","code"}`, ausschließlich in-App scanbar) bleibt **unverändert**: Der Einmalcode darf kein abfangbarer Deep Link werden.

Der Pfad `/connect` rendert im Browser eine schlanke, credential-freie Landing-Seite (`ConnectLandingPage`, außerhalb von Auth-Guard und Modus-Weiche, in Light- **und** Full-Modus), damit der Link nie in ein 404 läuft: Sie erklärt, den Link mit der Kamerplanter-App zu öffnen, und bietet „Im Browser fortfahren" an. Der **App-seitige** Kontrakt — den die künftige Android-App implementieren wird — ist ein `intent-filter` mit **Wildcard-Host** (`android:host="*"`) auf dem Pfad `/connect` (unverifizierter Deep Link → System-Auswahldialog). Automatisch **verifizierte** App Links sind hier bewusst **nicht** möglich, weil sie an feste, im Manifest deklarierte Domains binden, Kamerplanter aber selbst gehostet wird und jede Instanz eine im Voraus unbekannte Domain hat. Der `intent-filter` selbst ist **nicht** Teil dieses Umfangs (die App ist nicht implementiert); gebaut ist hier nur die vom Frontend emittierte URL und der Browser-Fallback.
<!-- /Quelle: Issue #1118 -->

## 5. Seed-Daten

### Benannte SSO-Provider (Vorkonfiguriert):

```json
[
  {
    "slug": "google",
    "display_name": "Google",
    "provider_type": "google",
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
    "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
    "scopes": ["openid", "email", "profile"],
    "enabled": false,
    "auto_discover": true
  },
  {
    "slug": "github",
    "display_name": "GitHub",
    "provider_type": "github",
    "authorization_url": "https://github.com/login/oauth/authorize",
    "token_url": "https://github.com/login/oauth/access_token",
    "userinfo_url": "https://api.github.com/user",
    "scopes": ["read:user", "user:email"],
    "enabled": false,
    "auto_discover": false
  },
  {
    "slug": "apple",
    "display_name": "Apple",
    "provider_type": "apple",
    "authorization_url": "https://appleid.apple.com/auth/authorize",
    "token_url": "https://appleid.apple.com/auth/token",
    "jwks_url": "https://appleid.apple.com/auth/keys",
    "scopes": ["name", "email"],
    "enabled": false,
    "auto_discover": false
  }
]
```

**Hinweis:** Benannte Provider werden mit `enabled: false` ausgeliefert. Aktivierung erfordert das Setzen von `client_id` und `client_secret` durch den System-Admin.

### Demo-User (Nur Entwicklungsumgebung):

```json
{
  "email": "demo@kamerplanter.local",
  "display_name": "Demo-Gärtner",
  "password": "demo-passwort-2024",
  "status": "active",
  "email_verified": true,
  "locale": "de",
  "timezone": "Europe/Berlin"
}
```

<!-- Quelle: Platform-Admin v1.6 -->
## 5a. Platform-Admin-Rolle

### 5a.1 Konzept

Der **Platform-Admin** (KA-Admin) ist ein Benutzer mit Membership im **Platform-Tenant** (REQ-024 v1.3). Die Platform-Admin-Berechtigung wird über das bestehende Tenant/Membership-Modell abgebildet — es gibt kein separates Rollen-System.

**Architektur-Entscheidung:** Die Platform-Admin-Rolle nutzt das bestehende Membership-Modell (Variante 1: Platform-Tenant) statt eines `is_platform_admin`-Flags auf User-Ebene. Begründung:
- Wiederverwendung der bestehenden Tenant/Membership-Mechanik
- Differenzierte Rollen im Platform-Tenant möglich (z.B. `admin` = volle Rechte, `viewer` = Read-Only-Zugang zu globalem Admin-Panel)
- Kein zweites Rollen-System neben dem Tenant-scoped-Modell

**Doppelrolle:**
Ein User kann gleichzeitig Memberships in beliebig vielen Tenants haben, inklusive dem Platform-Tenant:

```
User "anna"
  ├── Membership in tenant/platform (role: admin) → KA-Admin
  ├── Membership in tenant/annas-garten (role: admin) → Privater Garten
  └── Membership in tenant/gruene-oase (role: grower) → Gemeinschaftsgarten
```

### 5a.2 JWT-Erweiterung

Das JWT Access Token wird um ein `is_platform_admin`-Flag erweitert:

```python
# Token Payload (Erweiterung)
{
    "sub": "users/anna",
    "email": "anna@example.com",
    "display_name": "Anna",
    "tenant_roles": {
        "platform": "lead",         # Platform-Tenant Membership
        "annas-garten": "lead",
        "gruene-oase": "grower"
    },
    "is_platform_admin": true,       # NEU: Shortcut für Frontend/Backend
    "exp": 1711276800,
    "iat": 1711275900,
    "type": "access"
}
```

Das `is_platform_admin`-Flag wird beim Token-Erstellen aus den `tenant_roles` abgeleitet:

```python
is_platform_admin = "platform" in tenant_roles and tenant_roles["platform"] == "admin"
```

### 5a.3 Backend-Dependency

Neue FastAPI-Dependency für Platform-Admin-geschützte Endpunkte:

```python
def get_platform_admin(
    current_user: User = Depends(get_current_user),
    membership_repo: IMembershipRepository = Depends(get_membership_repo),
) -> User:
    """Stellt sicher, dass der aktuelle User Platform-Admin ist.
    Wirft ForbiddenError wenn keine admin-Membership im Platform-Tenant."""
    platform_membership = membership_repo.get_by_user_and_tenant(
        current_user.key, "platform"
    )
    if not platform_membership or platform_membership.role != "admin":
        raise ForbiddenError("Platform admin access required.")
    return current_user
```

Verwendung in Routern:

```python
@router.post("/species/{species_key}/assign-to-tenant/{tenant_key}")
def assign_species_to_tenant(
    species_key: str,
    tenant_key: str,
    admin: User = Depends(get_platform_admin),  # Platform-Admin-Guard
):
    ...
```

### 5a.4 Platform-Admin-Rechte

| Aktion | Berechtigung | Endpoint-Pattern |
|--------|-------------|------------------|
| Globale Species/Cultivars erstellen/bearbeiten/löschen | Plattform-Admin | `POST/PUT/DELETE /api/v1/species/*` |
| `tenant_has_access`-Kanten verwalten (zuweisen/entziehen) | Plattform-Admin | `POST/DELETE /api/v1/admin/species/{key}/tenants/{tenant_key}` |
| Tenant-Species zu global promoten | Plattform-Admin | `POST /api/v1/admin/species/{key}/promote` |
| Alle Tenants auflisten | Plattform-Admin | `GET /api/v1/admin/tenants` |
| Globale IPM-Daten verwalten | Plattform-Admin | `POST/PUT/DELETE /api/v1/pests/*`, `/diseases/*`, `/treatments/*` |
| OIDC-Provider konfigurieren | Plattform-Admin | `POST/PUT/DELETE /api/v1/admin/oidc-providers/*` (bereits vorhanden) |
<!-- Quelle: Tenant-Notfallverwaltung v1.7 -->
| Verwaisten Tenant einsehen (Mitglieder, Status) | Plattform-Admin | `GET /api/v1/admin/tenants/{tenant_key}/members` |
| Neuen Admin in Tenant ernennen (Notfall) | Plattform-Admin | `POST /api/v1/admin/tenants/{tenant_key}/emergency-admin` |
| Tenant suspendieren | Plattform-Admin | `POST /api/v1/admin/tenants/{tenant_key}/suspend` |
| Tenant reaktivieren | Plattform-Admin | `POST /api/v1/admin/tenants/{tenant_key}/reactivate` |
| User-Status ändern (suspend/reactivate) | Plattform-Admin | `POST /api/v1/admin/users/{user_key}/suspend`, `POST .../reactivate` |
<!-- /Quelle: Tenant-Notfallverwaltung v1.7 -->

<!-- Quelle: Tenant-Notfallverwaltung v1.7 -->
### 5a.5 Tenant-Notfallverwaltung durch Platform-Admin

**Problem:** Wenn alle Admins eines Organisations-Tenants ausfallen (Account gelöscht, suspended, alle verlassen den Tenant), ist der Tenant verwaist — kein Mitglied kann Verwaltungsaktionen durchführen. Ohne Eingriffsmöglichkeit ist der Tenant und alle seine Daten faktisch verloren.

**Lösung:** Platform-Admins erhalten die Fähigkeit, in verwaiste Tenants einzugreifen und einen neuen Admin zu ernennen. Dieser Eingriff ist an strenge Bedingungen geknüpft und wird vollständig protokolliert.

#### 5a.5.1 Verwaist-Erkennung

Ein Tenant gilt als **verwaist** wenn:
```python
def is_orphaned(tenant_key: str) -> bool:
    """Verwaist = kein aktives Mitglied mit der Zusatzberechtigung `management`.

    Der Anker ist Achse 2, NICHT der fachliche Rang (REQ-024 AK-10): Ein
    Mandant ohne Leitung ist bedienbar -- niemand darf loeschen, aber alles
    andere laeuft. Ein Mandant ohne `management` ist handlungsunfaehig, weil
    niemand mehr Mitglieder einladen, Rollen aendern oder Einstellungen
    pflegen kann. Nur der zweite Fall rechtfertigt die Notfallverwaltung.
    """
    active_managers = membership_repo.count_active_managers(tenant_key)
    return active_managers == 0
```

**Automatische Erkennung:** Ein Celery-Task prüft wöchentlich alle Organisations-Tenants auf Verwaist-Status und setzt ggf. ein Flag `orphaned_since: datetime` auf dem Tenant. Platform-Admins sehen verwaiste Tenants prominent im Admin-Panel.

#### 5a.5.2 Emergency-Admin-Ernennung

```python
@router.post("/admin/tenants/{tenant_key}/emergency-admin")
def appoint_emergency_admin(
    tenant_key: str,
    request: EmergencyAdminRequest,
    admin: User = Depends(get_platform_admin),
    tenant_service: TenantService = Depends(get_tenant_service),
) -> EmergencyAdminResponse:
    """Ernennt einen neuen Admin in einem verwaisten Tenant.

    Bedingungen:
    1. Aufrufender muss Platform-Admin sein
    2. Tenant muss verwaist sein (keine aktiven Admins)
    3. Ziel-User muss existieren und status 'active' haben
    4. Ziel-User darf bereits Mitglied sein (Rolle wird auf 'admin' hochgestuft)
       ODER wird als neues Mitglied mit Rolle 'admin' hinzugefügt
    5. Aktion wird im Audit-Log protokolliert
    """
```

**Request:**
```json
{
  "user_key": "users/max",
  "reason": "Bisherige Admins Lisa und Tom haben Verein verlassen. Max ist stellvertretender Vorsitzender."
}
```

**Response:**
```json
{
  "tenant_key": "gruene-oase",
  "user_key": "users/max",
  "previous_role": "grower",
  "new_role": "admin",
  "reason": "Bisherige Admins Lisa und Tom haben Verein verlassen. Max ist stellvertretender Vorsitzender.",
  "appointed_by": "users/anna",
  "appointed_at": "2026-03-17T14:30:00Z",
  "orphaned_since": "2026-03-10T00:00:00Z"
}
```

**Sicherheitsregeln:**
- **Nur bei verwaisten Tenants:** Wenn der Tenant noch aktive Admins hat → 409 Conflict ("Tenant hat aktive Admins — Notfall-Eingriff nicht erforderlich")
- **Reason ist Pflichtfeld:** Der Grund wird persistent gespeichert (Audit-Trail)
- **Benachrichtigung:** Alle aktiven Mitglieder des Tenants werden benachrichtigt (E-Mail/In-App), dass ein neuer Admin durch Platform-Admin ernannt wurde
- **Keine Selbst-Ernennung:** Platform-Admin darf sich selbst als Emergency-Admin einsetzen (sinnvoll für kleine Instanzen mit einem einzigen KA-Admin)

#### 5a.5.3 Tenant-Suspendierung

Platform-Admins können Tenants bei Bedarf suspendieren (z.B. bei Missbrauch, Rechtsstreitigkeiten, nicht-zahlenden Kunden im SaaS-Modell):

```python
@router.post("/admin/tenants/{tenant_key}/suspend")
def suspend_tenant(
    tenant_key: str,
    request: TenantSuspendRequest,  # { reason: str }
    admin: User = Depends(get_platform_admin),
) -> Tenant:
    """Setzt Tenant auf status='suspended'.
    Alle API-Zugriffe im Tenant-Scope geben 403 zurück.
    Memberships bleiben erhalten, aber Zugriff wird blockiert."""
```

```python
@router.post("/admin/tenants/{tenant_key}/reactivate")
def reactivate_tenant(
    tenant_key: str,
    admin: User = Depends(get_platform_admin),
) -> Tenant:
    """Setzt Tenant zurück auf status='active'."""
```

**Verhalten bei suspendiertem Tenant:**
- Alle tenant-scoped API-Requests (`/api/v1/t/{slug}/...`) geben 403 zurück mit Meldung "Tenant ist suspendiert. Kontaktieren Sie den Plattform-Administrator."
- Tenant erscheint im Tenant-Switcher ausgegraut mit Hinweis
- Memberships bleiben erhalten → bei Reaktivierung sofort wieder funktionsfähig
- Celery-Tasks für den Tenant werden pausiert (kein Care-Reminder, kein Watering-Task)
- Platform-Tenant kann NICHT suspendiert werden (Schutz)
- Persönliche Tenants können suspendiert werden (z.B. bei Account-Missbrauch)

#### 5a.5.4 User-Verwaltung durch Platform-Admin

Platform-Admins können User-Accounts verwalten (z.B. bei Missbrauch, kompromittierten Accounts):

```python
@router.post("/admin/users/{user_key}/suspend")
def suspend_user(
    user_key: str,
    request: UserSuspendRequest,  # { reason: str }
    admin: User = Depends(get_platform_admin),
) -> User:
    """Setzt User auf status='suspended'.
    Alle Refresh Tokens werden invalidiert.
    Alle API-Keys werden suspendiert.
    User kann sich nicht mehr anmelden."""

@router.post("/admin/users/{user_key}/reactivate")
def reactivate_user(
    user_key: str,
    admin: User = Depends(get_platform_admin),
) -> User:
    """Setzt User zurück auf status='active'.
    User muss sich erneut anmelden (keine automatische Session-Wiederherstellung)."""
```

**Schutzregeln:**
- Platform-Admin kann sich NICHT selbst suspendieren
- Wenn der suspendierte User der letzte Admin eines Tenants ist → Tenant wird als verwaist markiert (`orphaned_since` gesetzt)
- System-User (Light-Modus) kann nicht suspendiert werden

#### 5a.5.5 Szenarien

**Szenario 12: Verwaister Gemeinschaftsgarten — Notfall-Admin**
```
Voraussetzung: Tenant "Grüne Oase e.V." mit 12 Mitgliedern
  Lisa (Admin) hat Account gelöscht
  Tom (Admin, Stellvertreter) hat Verein verlassen

1. Celery-Task erkennt: "Grüne Oase e.V." hat 0 aktive Admins
   → orphaned_since: 2026-03-10
2. KA-Admin Anna sieht im Admin-Panel: "1 verwaister Tenant"
3. Anna öffnet Tenant-Details → sieht Mitgliederliste:
   - Lisa (deleted), Tom (left), Max (grower), ...
4. Anna wählt "Notfall-Admin ernennen" → Max (Grower)
5. Grund: "Bisherige Admins haben Verein verlassen. Max ist Kassenwart."
6. System:
   a) Max' Rolle: grower → admin
   b) orphaned_since: null (Tenant nicht mehr verwaist)
   c) E-Mail an alle 10 verbleibenden Mitglieder:
      "Max wurde von der Plattform-Administration als neuer Admin ernannt."
7. Max kann jetzt Mitglieder verwalten, Einladungen erstellen, etc.
```

**Szenario 13: Tenant-Suspendierung bei Missbrauch**
```
1. KA-Admin erhält Hinweis: Tenant "spam-garden" missbraucht Plattform
2. Anna navigiert zu Admin-Panel → Tenant-Liste
3. Klickt auf "spam-garden" → "Tenant suspendieren"
4. Gibt Grund ein: "Spam-Inhalte, Meldung von 3 Nutzern"
5. System setzt status='suspended'
6. Alle 5 Mitglieder von "spam-garden":
   - Sehen im Tenant-Switcher: "spam-garden (suspendiert)"
   - API-Zugriffe auf /t/spam-garden/* → 403
   - Andere Tenants der Mitglieder funktionieren normal
7. Nach Klärung: Anna reaktiviert → sofort wieder funktionsfähig
```

**Szenario 14: User-Suspendierung bei kompromittiertem Account**
```
1. KA-Admin bemerkt: User "hacker@example.com" zeigt verdächtige Aktivität
2. Anna suspendiert den User über Admin-Panel
3. System:
   a) status → suspended
   b) Alle Refresh Tokens invalidiert (sofortiger Logout auf allen Geräten)
   c) Alle API-Keys suspendiert
   d) Prüfung: War User letzter Admin in einem Tenant?
      → Ja in "kleiner-garten" → Tenant als verwaist markiert
4. Anna untersucht den Vorfall
5. Nach Klärung: Reaktivierung → User muss sich neu anmelden
```
<!-- /Quelle: Tenant-Notfallverwaltung v1.7 -->

### 5a.6 Szenario: Platform-Admin verwaltet Stammdaten

```
1. Anna ist Platform-Admin (Membership in tenant/platform, role: admin)
2. Anna navigiert zum Admin-Panel (/admin/stammdaten)
3. Anna sieht alle globalen Species mit Zuweisungsstatus pro Tenant
4. Anna wählt Species "Cannabis sativa" und weist sie Tenant "grow-op" zu:
   → tenant_has_access-Kante wird erstellt
5. Anna entzieht Species "Cannabis sativa" von Tenant "gemuese-garten":
   → tenant_has_access-Kante wird gelöscht
6. Tenant "grow-op" sieht Cannabis, Tenant "gemuese-garten" nicht
7. Anna wechselt zu ihrem privaten Garten (Tenant-Switcher → "Annas Garten")
   → Anna arbeitet als normaler Tenant-Admin, nicht als KA-Admin
```
<!-- /Quelle: Platform-Admin v1.6 -->

<!-- Quelle: Service Accounts v1.7 -->
## 5b. Service Accounts

### 5b.1 Konzept

**Service Accounts** sind nicht-interaktive Konten für maschinellen API-Zugriff. Sie werden als User mit `account_type: 'service'` modelliert und nutzen die bestehende Membership- und API-Key-Infrastruktur. Hauptanwendungsfälle:

| System | Typische Rolle | Zugriff |
|--------|---------------|---------|
| **Home Assistant** | `grower` im Tenant | Sensordaten schreiben, Aktoren steuern, Tasks lesen |
| **Grafana/Prometheus** | `viewer` im Tenant | Metriken/Sensordaten lesen, Dashboard-Daten abfragen |
| **CI/CD Pipeline** | `admin` im Tenant | Seed-Daten deployen, Konfiguration aktualisieren |
| **Enrichment-Pipeline** | Platform `viewer` | Globale Stammdaten lesen, Enrichment-Ergebnisse schreiben |
| **Backup-System** | Platform `admin` | Cross-Tenant Read-Access für Datensicherung |

**Architektur-Entscheidung:** Service Accounts als User-Subtyp (Variante B) statt separater Entity (Variante A). Begründung:
- Wiederverwendung der gesamten Membership/API-Key/RBAC-Infrastruktur ohne Code-Duplikation
- `get_current_user`-Dependency funktioniert unverändert — gibt User zurück, egal ob `human` oder `service`
- Permission-Prüfung (REQ-024 Permission Matrix) greift identisch für beide Account-Typen
- Audit-Trail mit `user_key` funktioniert transparent (Service Account Keys sind in Logs identifizierbar)

### 5b.2 Abgrenzung: Service Account vs. API-Key eines menschlichen Users

| Eigenschaft | API-Key (human User) | Service Account |
|-------------|---------------------|-----------------|
| **Besitzer** | Menschlicher User | Eigenständiges Konto (`account_type: 'service'`) |
| **Erstellung** | User erstellt selbst | Tenant-Admin oder Platform-Admin erstellt |
| **Interaktiver Login** | User kann sich per Passwort/SSO anmelden | Kein Login möglich (kein Passwort, kein SSO) |
| **JWT-Tokens** | Ja (interaktive Sessions) | Nein (nur API-Key-Authentifizierung) |
| **Refresh Tokens** | Ja | Nein |
| **Membership** | Eigene Memberships des Users | Eigene Memberships — vom Ersteller festgelegt |
| **IP-Einschränkung** | Nicht unterstützt | `allowed_ip_ranges` (CIDR-Notation) |
| **Individuelles Rate Limit** | Nein (globaler Default) | `rate_limit_rpm` pro Account konfigurierbar |
| **Sichtbarkeit** | Nur für den User selbst | Für Tenant-Admins und Platform-Admins sichtbar |
| **Verantwortung** | User selbst | `created_by` → Ersteller ist verantwortlich |

### 5b.3 Tenant-scoped Service Accounts

Tenant-Admins können Service Accounts für ihren Tenant erstellen. Der Service Account erhält eine Membership im Tenant mit einer vom Admin festgelegten Rolle.

**Regeln:**
- Nur Tenant-Admins dürfen Service Accounts erstellen (`role: admin` im Tenant erforderlich)
- Die zugewiesene Rolle darf maximal `grower` sein — ein Service Account kann nicht `admin` im Tenant werden (verhindert Privilege Escalation über maschinelle Konten)
- Ausnahme: Platform-Admins dürfen Service Accounts mit jeder Rolle erstellen (auch `admin`)
- Service Accounts werden dem Tenant via Membership zugeordnet (analog zu menschlichen Usern)
- Ein Service Account kann Memberships in mehreren Tenants haben (z.B. Home Assistant, das mehrere Growzelte überwacht)
- Die `email` des Service Accounts folgt dem Pattern `{slugified-name}@service.{tenant_slug}.local` (nicht routbar, nur für Eindeutigkeit)

### 5b.4 Platform-scoped Service Accounts

Platform-Admins können Service Accounts auf Plattformebene erstellen. Diese erhalten eine Membership im Platform-Tenant und können zusätzlich Memberships in beliebigen regulären Tenants erhalten.

**Regeln:**
- Nur Platform-Admins dürfen Platform Service Accounts erstellen
- Platform Service Accounts können Rollen im Platform-Tenant haben (`admin` oder `viewer`)
- Platform Service Accounts mit `admin`-Rolle im Platform-Tenant haben KA-Admin-Rechte (globale Stammdaten, `tenant_has_access`-Verwaltung)
- Platform Service Accounts mit `viewer`-Rolle im Platform-Tenant haben Read-Only-Zugriff auf das Admin-Panel (z.B. für Monitoring/Dashboards)

### 5b.5 Service Account Lifecycle

```
Erstellt (active) → Suspendiert (suspended) → Reaktiviert (active) → Gelöscht (deleted)
                  ↘                                                  ↗
                    → Gelöscht (deleted) ─────────────────────────────
```

| Status | Verhalten |
|--------|----------|
| `active` | API-Keys funktionieren, normale Zugriffskontrolle |
| `suspended` | Alle API-Keys sofort ungültig (401), Daten bleiben erhalten. Reaktivierung möglich. |
| `deleted` | Soft-Delete — Alle API-Keys invalidiert, Memberships auf `status: 'left'` gesetzt. Nicht reaktivierbar. |

### 5b.6 Backend-Architektur

**`ServiceAccountEngine`** — Validierungslogik (pure Logik, kein I/O):

```python
class ServiceAccountEngine:
    MAX_SERVICE_ACCOUNTS_PER_TENANT = 20
    DEFAULT_RATE_LIMIT_RPM = 1000

    def validate_name(self, name: str) -> list[str]: ...
        # Min 2, Max 100 Zeichen
        # Nur alphanumerisch, Leerzeichen, Bindestriche

    def generate_email(self, name: str, tenant_slug: str) -> str: ...
        # "Home Assistant" + "mein-garten" → "home-assistant@service.mein-garten.local"

    def validate_ip_ranges(self, ip_ranges: list[str]) -> list[str]: ...
        # Prüft gültige CIDR-Notation (IPv4 und IPv6)
        # Maximale Range: /8 (IPv4), /32 (IPv6) — verhindert "0.0.0.0/0"

    def check_ip_allowed(self, client_ip: str, allowed_ranges: list[str]) -> bool: ...
        # Prüft ob Client-IP in einem der erlaubten CIDR-Bereiche liegt
        # None/leere Liste → alle IPs erlaubt

    def can_assign_role(self, creator_role: str, target_role: str,
                        is_platform_admin: bool) -> bool: ...
        # Tenant-Admin: max. grower
        # Platform-Admin: alle Rollen (inkl. admin)

    def validate_rate_limit(self, rpm: int) -> list[str]: ...
        # Min: 10, Max: 10000 req/min
```

**`ServiceAccountService`** — Orchestriert Service-Account-CRUD:

```python
class ServiceAccountService:
    def __init__(self, user_repo, membership_repo, api_key_repo,
                 service_account_engine, membership_engine, tenant_repo): ...

    async def create_service_account(
        self,
        creator: User,
        tenant_key: str,
        name: str,
        role: str,
        description: str | None = None,
        rate_limit_rpm: int | None = None,
        allowed_ip_ranges: list[str] | None = None,
    ) -> ServiceAccountCreated: ...
        # 1. Prüft: Creator ist Admin im Tenant (oder Platform-Admin)
        # 2. Prüft: Max. 20 Service Accounts pro Tenant
        # 3. Validiert Name, IP-Ranges, Rate Limit, Rollen-Zuweisung
        # 4. Erstellt User mit account_type='service', generierter E-Mail
        # 5. Erstellt Membership im Tenant mit gewählter Rolle
        # 6. Erstellt initialen API-Key (kp_...)
        # 7. Gibt ServiceAccountCreated zurück (inkl. einmaligem API-Key-Klartext)

    async def list_service_accounts(
        self, tenant_key: str, actor: User
    ) -> list[ServiceAccountInfo]: ...
        # Alle Service Accounts des Tenants (nur für Tenant-Admins)

    async def get_service_account(
        self, service_account_key: str, actor: User
    ) -> ServiceAccountDetail: ...
        # Inkl. Memberships, API-Key-Liste, letzte Aktivität

    async def update_service_account(
        self, service_account_key: str, actor: User,
        updates: ServiceAccountUpdate
    ) -> ServiceAccountDetail: ...
        # Aktualisiert: name, description, rate_limit_rpm, allowed_ip_ranges
        # Rollen-Änderung über separate Membership-Verwaltung

    async def suspend_service_account(
        self, service_account_key: str, actor: User
    ) -> None: ...
        # Setzt status='suspended', alle API-Keys sofort ungültig

    async def reactivate_service_account(
        self, service_account_key: str, actor: User
    ) -> None: ...
        # Setzt status='active', bestehende (nicht-revoked) API-Keys funktionieren wieder

    async def delete_service_account(
        self, service_account_key: str, actor: User
    ) -> None: ...
        # Soft-Delete: status='deleted', alle API-Keys revoked, Memberships 'left'

    async def rotate_api_key(
        self, service_account_key: str, actor: User
    ) -> ApiKeyCreated: ...
        # Revoked alten Key, erstellt neuen Key
        # Gibt einmalig den neuen Key-Klartext zurück

    async def add_tenant_membership(
        self, service_account_key: str, target_tenant_key: str,
        role: str, actor: User
    ) -> Membership: ...
        # Fügt Service Account als Mitglied in einem weiteren Tenant hinzu
        # Nur Platform-Admin für Cross-Tenant, Tenant-Admin für eigenen Tenant
```

### 5b.7 API-Endpoints

**Router: `/api/v1/t/{tenant_slug}/service-accounts`** — Tenant-scoped Service Account Verwaltung:

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| `POST` | `/t/{slug}/service-accounts` | Service Account erstellen (inkl. initialer API-Key) | Verwaltung |
| `GET` | `/t/{slug}/service-accounts` | Alle Service Accounts des Tenants auflisten | Verwaltung |
| `GET` | `/t/{slug}/service-accounts/{sa_key}` | Details eines Service Accounts | Verwaltung |
| `PATCH` | `/t/{slug}/service-accounts/{sa_key}` | Service Account aktualisieren (Name, Beschreibung, Rate Limit, IP-Ranges) | Verwaltung |
| `POST` | `/t/{slug}/service-accounts/{sa_key}/suspend` | Service Account suspendieren | Verwaltung |
| `POST` | `/t/{slug}/service-accounts/{sa_key}/reactivate` | Service Account reaktivieren | Verwaltung |
| `DELETE` | `/t/{slug}/service-accounts/{sa_key}` | Service Account löschen (Soft-Delete) | Verwaltung |
| `POST` | `/t/{slug}/service-accounts/{sa_key}/rotate-key` | API-Key rotieren (alter Key revoked, neuer Key erstellt) | Verwaltung |

**Router: `/api/v1/admin/platform/service-accounts`** — Platform-scoped Service Account Verwaltung:

| Methode | Pfad | Beschreibung | Auth |
|---------|------|-------------|------|
| `POST` | `/admin/platform/service-accounts` | Platform Service Account erstellen | Plattform-Admin |
| `GET` | `/admin/platform/service-accounts` | Alle Platform Service Accounts auflisten | Plattform-Admin |
| `GET` | `/admin/platform/service-accounts/{sa_key}` | Details eines Platform Service Accounts | Plattform-Admin |
| `PATCH` | `/admin/platform/service-accounts/{sa_key}` | Platform Service Account aktualisieren | Plattform-Admin |
| `POST` | `/admin/platform/service-accounts/{sa_key}/tenants/{tenant_key}` | Service Account Membership in weiterem Tenant hinzufügen | Plattform-Admin |
| `DELETE` | `/admin/platform/service-accounts/{sa_key}/tenants/{tenant_key}` | Service Account Membership aus Tenant entfernen | Plattform-Admin |
| `DELETE` | `/admin/platform/service-accounts/{sa_key}` | Platform Service Account löschen | Plattform-Admin |

**Gesamt:** 15 neue API-Endpoints

**POST /api/v1/t/{slug}/service-accounts — Request:**
```json
{
  "name": "Home Assistant Growzelt",
  "description": "Sensordaten und Aktorsteuerung für Zelt 1",
  "role": "grower",
  "rate_limit_rpm": 500,
  "allowed_ip_ranges": ["192.168.1.0/24"]
}
```

**POST /api/v1/t/{slug}/service-accounts — Response (einmalig mit API-Key-Klartext):**
```json
{
  "_key": "sa_homeassistant_001",
  "name": "Home Assistant Growzelt",
  "description": "Sensordaten und Aktorsteuerung für Zelt 1",
  "account_type": "service",
  "email": "home-assistant-growzelt@service.mein-garten.local",
  "role": "grower",
  "status": "active",
  "rate_limit_rpm": 500,
  "allowed_ip_ranges": ["192.168.1.0/24"],
  "api_key": {
    "_key": "ak_sa_001",
    "api_key": "kp_b7e2f8a1c3d5e9f0a2b4c6d8e0f2a4b6c8d0e2f4a6b8c0d2e4",
    "key_prefix": "kp_b7e2...",
    "created_at": "2026-03-17T10:00:00Z"
  },
  "created_by": "users/anna",
  "created_at": "2026-03-17T10:00:00Z"
}
```

> **Hinweis:** Der vollständige API-Key wird nur bei der Erstellung und bei Key-Rotation angezeigt. Danach ist er nicht mehr abrufbar.

### 5b.8 JWT-Erweiterung

Das JWT Access Token (§5a.2) wird um `account_type` erweitert:

```python
{
    "sub": "users/sa_homeassistant_001",
    "email": "home-assistant-growzelt@service.mein-garten.local",
    "display_name": "Home Assistant Growzelt",
    "account_type": "service",          # NEU: Unterscheidung human/service
    "tenant_roles": {
        "mein-garten": "grower"
    },
    "is_platform_admin": false,
    "exp": 1711276800,
    "iat": 1711275900,
    "type": "access"
}
```

**Hinweis:** Service Accounts erhalten kein JWT-Token über Login — das Token wird nur intern für die API-Key→User-Auflösung im Middleware-Kontext verwendet. Der `account_type` im Token ermöglicht es Endpunkten, Service-Account-Zugriffe gesondert zu behandeln (z.B. keine interaktiven Operationen wie Passwort-Änderung).

### 5b.9 Szenarien

**Szenario 8: Home Assistant Service Account erstellen**
```
1. Anna (Tenant-Admin von "Annas Garten") navigiert zu /t/annas-garten/settings/service-accounts
2. Klickt "Service Account erstellen"
3. Dialog: Name "Home Assistant", Beschreibung "Sensor- und Aktor-Integration",
   Rolle: Gärtner (grower), IP-Bereich: 192.168.1.0/24
4. System erstellt Service Account + initialen API-Key
5. Dialog zeigt API-Key einmalig an: "kp_b7e2f8a1..."
6. Anna kopiert Key und hinterlegt ihn in der HA-Konfiguration
7. HA authentifiziert sich per API-Key → Middleware erkennt kp_-Prefix
   → löst Service Account auf → prüft IP (192.168.1.x ✓) → Zugriff OK
8. HA kann im Tenant "Annas Garten" Sensordaten schreiben und Tasks lesen
```

**Szenario 9: Monitoring Service Account mit Platform-Zugriff**
```
1. KA-Admin erstellt Platform Service Account "Grafana Monitoring"
   → POST /api/v1/admin/platform/service-accounts
   → Rolle im Platform-Tenant: viewer
2. KA-Admin fügt Service Account als viewer in 3 Tenants hinzu:
   → POST /api/v1/admin/platform/service-accounts/{key}/tenants/annas-garten
   → POST /api/v1/admin/platform/service-accounts/{key}/tenants/gruene-oase
   → POST /api/v1/admin/platform/service-accounts/{key}/tenants/cannabis-club
3. Grafana nutzt den API-Key um Metriken aus allen 3 Tenants abzurufen
4. Read-Only: Grafana kann keine Daten ändern (viewer-Rolle)
```

**Szenario 10: Service Account Key-Rotation**
```
1. Anna vermutet, dass der HA-API-Key kompromittiert wurde
2. Navigiert zu Service Account Details
3. Klickt "Key rotieren"
4. System: Alter Key wird sofort revoked, neuer Key wird erstellt
5. Dialog zeigt neuen Key einmalig an
6. Anna aktualisiert den Key in der HA-Konfiguration
7. HA nutzt ab sofort den neuen Key — alter Key ist ungültig
```

**Szenario 11: Service Account suspendieren**
```
1. Anna bemerkt verdächtige API-Zugriffe vom HA-Service-Account
2. Klickt "Suspendieren" → sofortige Wirkung
3. Alle API-Keys des Service Accounts geben 401 zurück
4. Anna untersucht das Problem
5. Problem gelöst → "Reaktivieren" → API-Keys funktionieren wieder
```

### 5b.10 Frontend

**Service Account Verwaltung im Tenant-Settings-Bereich:**

| Seite | Route | Beschreibung |
|-------|-------|-------------|
| `ServiceAccountListPage` | `/t/{slug}/settings/service-accounts` | Liste aller Service Accounts des Tenants |
| `ServiceAccountDetailPage` | `/t/{slug}/settings/service-accounts/{sa_key}` | Details, API-Keys, Memberships, Aktivitätslog |

**ServiceAccountListPage (Tabelle):**

| Spalte | Beschreibung |
|--------|-------------|
| Name | Anzeigename (z.B. "Home Assistant Growzelt") |
| Rolle | Rolle im Tenant (Chip: grower, viewer) |
| Status | Status-Chip (active: grün, suspended: orange, deleted: grau) |
| Letzte Aktivität | Zeitpunkt des letzten API-Zugriffs oder "Nie aktiv" |
| IP-Bereich | Konfigurierte Allowlist oder "Alle" |
| Aktionen | Suspendieren/Reaktivieren, Löschen |

**ServiceAccountDetailPage (Tabs):**

- **Tab "Übersicht":** Name, Beschreibung, Status, Erstellt von, Rate Limit, IP-Bereiche — editierbar
- **Tab "API-Keys":** Aktive Keys (Label, Prefix, Erstellt, Letzter Zugriff). Button "Key rotieren" (revoked alten, erstellt neuen)
- **Tab "Tenants":** Alle Memberships des Service Accounts (Tenant-Name, Rolle). Nur bei Platform Service Accounts: Tenants hinzufügen/entfernen

**Erstell-Dialog:**

- **Name** (Pflicht): z.B. "Home Assistant", "Grafana"
- **Beschreibung** (Optional): Freitext
- **Rolle** (Pflicht): Dropdown (Gärtner, Beobachter — kein Admin für Tenant-scoped)
- **Rate Limit** (Optional): Zahleneingabe, Default 1000 req/min
- **IP-Bereiche** (Optional): Chip-Input für CIDR-Notation
- **Erstellen** → API-Key wird einmalig angezeigt (Copy-Button, Warnhinweis wie bei normalen API-Keys)

**Sichtbarkeit:**
- Service Account Menüpunkt nur für Tenant-Admins sichtbar
- Im Light-Modus (REQ-027): Sichtbar, da System-User Admin ist — nützlich für HA-Integration
- Expertise-Level (REQ-021): Nur ab `intermediate` sichtbar (beginners brauchen keine Service Accounts)

### 5b.11 Light-Modus-Integration (REQ-027)

Im Light-Modus funktionieren Service Accounts uneingeschränkt:
- System-User ist Admin im System-Tenant → kann Service Accounts erstellen
- Nützlichster Use-Case: Home Assistant Service Account für lokale HA-Integration
- Service Account API-Keys funktionieren auch ohne JWT (LightAuthProvider gibt System-User zurück, aber API-Keys werden direkt per Hash validiert — kein Bypass)

**Sicherheitsaspekt:** Im Light-Modus gibt es keine Authentifizierung — aber Service Accounts mit API-Keys bieten eine optionale Sicherheitsebene für automatisierte Zugriffe. Ein Admin kann Service Accounts mit IP-Allowlist konfigurieren, auch wenn der Browser-Zugang offen ist.

### 5b.12 Seed-Daten

**Demo Service Account (nur Entwicklungsumgebung):**

```json
{
  "email": "demo-ha@service.demo-garten.local",
  "display_name": "Demo Home Assistant",
  "account_type": "service",
  "description": "Demo Service Account für Home Assistant Integration",
  "status": "active",
  "rate_limit_rpm": 1000,
  "allowed_ip_ranges": null,
  "created_by": "users/demo-user"
}
```

Membership: `grower` im Demo-Tenant. API-Key: `kp_demo000000000000000000000000000000000000000000000000` (nur in Seed-Daten, nicht für Produktion).
<!-- /Quelle: Service Accounts v1.7 -->

## 6. Abnahmekriterien

### Funktionale Kriterien:

| # | Kriterium | Prüfmethode |
|---|-----------|-------------|
| AK-01 | Lokale Registrierung erstellt User mit `status: unverified` und sendet Verifizierungs-E-Mail | Integration |
| AK-02 | Verifizierungs-Link setzt `status: active` und `email_verified: true` | Integration |
| AK-03 | Lokaler Login mit `remember_me=true` gibt Access Token (15 Min) + persistentes Refresh Token (30 Tage, HttpOnly Cookie mit `Max-Age`) zurück | Integration |
| AK-03a | Lokaler Login mit `remember_me=false` (Standard) gibt Access Token (15 Min) + Session-Refresh-Token (24h TTL, HttpOnly Session-Cookie ohne `Max-Age`/`Expires`) zurück | Integration |
| AK-03b | SSO-Login setzt `is_persistent=true` (persistentes Cookie, 30 Tage) | Integration |
| AK-04 | Token-Refresh erstellt neues Token-Paar und invalidiert altes Refresh Token (Rotation); `is_persistent` wird vom Vorgänger-Token übernommen | Integration |
| AK-05 | Nach 5 Fehlversuchen wird Account 15 Minuten gesperrt (`locked_until` gesetzt) | Unit + Integration |
| AK-06 | Passwort-Reset-Token ist 1 Stunde gültig und einmalig verwendbar | Integration |
| AK-07 | Nach Passwort-Reset sind alle bestehenden Refresh Tokens invalidiert | Integration |
| AK-08 | Google-OAuth2-Login erstellt User mit `email_verified: true` und verknüpftem AuthProvider | Integration |
| AK-09 | GitHub-OAuth2-Login holt E-Mail via separatem API-Call wenn privat | Integration |
| AK-10 | Apple-Sign-In speichert Name beim ersten Login (wird nur einmal übermittelt) | Integration |
| AK-11 | Generischer OIDC-Provider mit `auto_discover: true` nutzt `.well-known/openid-configuration` | Integration |
| AK-12 | Account-Linking: SSO-Login mit gleicher verifizierter E-Mail verknüpft automatisch mit bestehendem Account | Integration |
| AK-13 | Account-Linking: Entfernen des letzten Auth-Providers wird verhindert (mindestens eine Methode) | Unit |
| AK-14 | Logout invalidiert Refresh Token; Logout-All invalidiert alle Tokens des Users | Integration |
| AK-15 | Profil-Update (display_name, locale, timezone) persistiert korrekt | Integration |
| AK-16 | Account-Löschung setzt `status: deleted`, anonymisiert E-Mail, invalidiert alle Tokens | Integration |
| AK-17 | Celery-Task bereinigt abgelaufene Tokens stündlich und unbestätigte Accounts nach 7 Tagen | Integration |
<!-- Quelle: Platform-Admin v1.6 -->
| AK-18 | Platform-Admin-Dependency (`get_platform_admin`) prüft Membership im Platform-Tenant mit `role: admin` | Unit + Integration |
| AK-19 | JWT Access Token enthält `is_platform_admin: true` wenn User Platform-Admin ist | Unit |
| AK-20 | User kann gleichzeitig Platform-Admin und regulärer Tenant-Nutzer sein (Doppelrolle) | Integration |
| AK-21 | Nicht-Platform-Admins erhalten 403 bei Zugriff auf Platform-Admin-Endpunkte | Integration |
| AK-22 | Platform-Admin kann globale Species/Cultivars erstellen, bearbeiten, löschen | Integration |
| AK-23 | Platform-Admin kann `tenant_has_access`-Kanten erstellen und entfernen | Integration |
| AK-24 | Platform-Admin kann Tenant-eigene Species zu globalen promoten (origin: tenant → system, tenant_key → null) | Integration |
<!-- /Quelle: Platform-Admin v1.6 -->
<!-- Quelle: Service Accounts v1.7 -->
| AK-25 | Service Account Erstellung erzeugt User mit `account_type: 'service'`, generierter E-Mail und Membership im Tenant | Integration |
| AK-26 | Service Account bekommt bei Erstellung automatisch einen API-Key (Klartext einmalig in Response) | Integration |
| AK-27 | Service Account kann sich NICHT per Passwort oder SSO anmelden (kein `password_hash`, kein AuthProvider) | Unit + Integration |
| AK-28 | Tenant-Admin kann Service Accounts nur mit Rolle `grower` oder `viewer` erstellen (kein `admin`) | Unit |
| AK-29 | Platform-Admin kann Service Accounts mit jeder Rolle erstellen (inkl. `admin`) | Integration |
| AK-30 | Maximal 20 Service Accounts pro Tenant (429 bei Überschreitung) | Unit + Integration |
| AK-31 | `allowed_ip_ranges` wird bei API-Key-Authentifizierung geprüft — Zugriff von nicht-erlaubter IP gibt 403 | Integration |
| AK-32 | `rate_limit_rpm` wird als individuelles Rate Limit pro Service Account angewendet | Integration |
| AK-33 | Suspendierung eines Service Accounts macht alle seine API-Keys sofort ungültig (401) | Integration |
| AK-34 | Reaktivierung eines Service Accounts stellt API-Key-Funktionalität wieder her (nicht-revoked Keys funktionieren) | Integration |
| AK-35 | Löschung (Soft-Delete) revoked alle API-Keys und setzt Memberships auf `status: 'left'` | Integration |
| AK-36 | Key-Rotation revoked den alten Key und erstellt einen neuen (Klartext einmalig in Response) | Integration |
| AK-37 | Platform Service Account kann Memberships in mehreren Tenants erhalten | Integration |
| AK-38 | `last_active_at` wird bei jedem API-Key-Zugriff des Service Accounts aktualisiert | Integration |
| AK-39 | Service Account E-Mail folgt Pattern `{slug}@service.{tenant_slug}.local` und ist UNIQUE | Unit |
| AK-40 | Service Accounts sind in der User-Auflistung (`GET /users/me/providers` etc.) nicht sichtbar — eigene Verwaltung über `/service-accounts` | Integration |
| AK-41 | `account_type` ist im JWT-Token enthalten und korrekt gesetzt (`human` oder `service`) | Unit |
<!-- /Quelle: Service Accounts v1.7 -->
<!-- Quelle: Tenant-Notfallverwaltung v1.7 -->
| AK-42 | Verwaist-Erkennung: Tenant ohne aktive Admins wird korrekt als verwaist erkannt (`is_orphaned() == True`) | Unit + Integration |
| AK-43 | Emergency-Admin-Ernennung nur bei verwaisten Tenants möglich (409 wenn aktive Admins vorhanden) | Integration |
| AK-44 | Emergency-Admin-Ernennung erfordert Platform-Admin-Berechtigung (403 für Nicht-Platform-Admins) | Integration |
| AK-45 | Emergency-Admin-Ernennung: `reason` ist Pflichtfeld (422 bei fehlendem Grund) | Unit |
| AK-46 | Emergency-Admin-Ernennung: Ziel-User wird korrekt zum Admin befördert (bestehende Membership) oder als Admin hinzugefügt (neue Membership) | Integration |
| AK-47 | Emergency-Admin-Ernennung: `orphaned_since` wird auf `null` zurückgesetzt | Integration |
| AK-48 | Emergency-Admin-Ernennung: Alle aktiven Mitglieder des Tenants werden benachrichtigt | Integration |
| AK-49 | Tenant-Suspendierung: Alle tenant-scoped API-Requests geben 403 zurück | Integration |
| AK-50 | Tenant-Suspendierung: Platform-Tenant kann NICHT suspendiert werden (400) | Unit |
| AK-51 | Tenant-Reaktivierung: Zugriff wird sofort wiederhergestellt | Integration |
| AK-52 | User-Suspendierung: Alle Refresh Tokens invalidiert, alle API-Keys suspendiert | Integration |
| AK-53 | User-Suspendierung: Platform-Admin kann sich NICHT selbst suspendieren (400) | Unit |
| AK-54 | User-Suspendierung: Wenn User letzter Admin eines Tenants → Tenant als verwaist markiert | Integration |
| AK-55 | Celery-Task erkennt verwaiste Tenants wöchentlich und setzt `orphaned_since` | Integration |
<!-- /Quelle: Tenant-Notfallverwaltung v1.7 -->

### Sicherheitskriterien:

| # | Kriterium | Prüfmethode |
|---|-----------|-------------|
| SK-01 | Passwörter sind ausschließlich als Bcrypt-Hash (Cost 12) gespeichert | Code Review |
| SK-02 | Refresh Tokens sind als SHA-256-Hash gespeichert (Klartext nie in DB) | Code Review |
| SK-03 | OAuth-state-Parameter verhindert CSRF (Redis, 5 Min TTL) | Integration |
| SK-04 | PKCE (Proof Key for Code Exchange) wird für alle OAuth-Flows verwendet | Integration |
| SK-05 | Passwort-Reset-Request gibt keinen Hinweis ob E-Mail existiert (Enumeration-Schutz) | Integration |
| SK-06 | Client Secrets und Provider-Tokens sind AES-256-verschlüsselt in der Datenbank | Code Review |
| SK-07 | Alle Auth-Endpunkte haben Rate Limiting (100/min pro IP) | Integration |
| SK-08 | Access Token enthält keine sensitiven Daten (kein Passwort-Hash, keine Provider-Tokens) | Unit |
<!-- Quelle: Widerspruchsanalyse W-004 -->
| SK-09 | **Token-Family bei Login:** Jeder erfolgreiche Login (Local oder OAuth) erzeugt ein Refresh-Token mit neuer `family_key` (UUID4). Bei Token-Rotation erbt der Nachfolger die `family_key` vom Vorgänger. | Unit |
| SK-10 | **Grace-Window-Idempotenz:** `POST /auth/refresh` mit einem bereits rotierten Refresh-Token ≤ 60s nach Rotation und passender `device_id` liefert den bereits ausgestellten Nachfolger zurück (KEIN neues Token-Paar, KEINE Family-Sprengung). | Integration |
| SK-11 | **Replay-Detection außerhalb Grace:** `POST /auth/refresh` mit einem Token, das vor mehr als 60s rotiert wurde, sprengt die ganze Family (alle Tokens mit gleicher `family_key` werden revoked) und liefert HTTP 401 mit `error_code='refresh_replay_detected'`. | Integration |
| SK-12 | **Replay-Detection bei Device-Mismatch:** Auch innerhalb 60s führt eine abweichende `device_id` zu Family-Sprengung und HTTP 401. | Integration |
| SK-13 | **Family-Isolation Multi-Device:** Family-Sprengung von F1 (Tablet-Login) hat keinen Einfluss auf F2 (Desktop-Login desselben Users) — Desktop-Session bleibt aktiv. | Integration |
| SK-14 | **Telemetrie:** Bei jedem Replay-Event wird structlog-Event `auth.refresh_replay_detected` mit `family_key`, `user_key`, `reason`, `token_age_seconds` geloggt; Counter `kp_auth_refresh_replay_total{reason=...}` wird inkrementiert. | Integration |
| SK-15 | **Hard Cutover v1.9:** Beim Deployment von v1.9 werden alle bestehenden Refresh-Tokens via `cutover_refresh_tokens_v19()` revoked. Nach Deployment werden alle Auth-Endpunkte mit altem Refresh-Token mit 401 abgelehnt. | Integration |
<!-- /Quelle: Widerspruchsanalyse W-004 -->

### Frontend-Kriterien:

| # | Kriterium | Prüfmethode |
|---|-----------|-------------|
| FK-01 | Login-Seite zeigt dynamisch alle aktivierten SSO-Provider als Buttons | E2E |
| FK-01a | Login-Seite zeigt Checkbox „Angemeldet bleiben" unterhalb des Passwort-Felds, Standard: nicht aktiviert | E2E |
| FK-02 | Nach erfolgreichem Login wird User zum Dashboard redirected | E2E |
| FK-03 | 401-Response löst automatischen Token-Refresh aus; bei Refresh-Fehler → Redirect zu /login | Integration |
| FK-04 | AccountSettingsPage zeigt verknüpfte Provider und aktive Sessions korrekt an | E2E |
| FK-05 | Account-Löschung erfordert Passwort-Bestätigung im Dialog | E2E |
| FK-06 | Tab "API-Keys" zeigt Liste aller eigenen Keys mit Label, Prefix, Tenant-Scope, Erstellt, Letzter Zugriff | E2E |
| FK-07 | Neuen API-Key erstellen zeigt Klartext-Key einmalig im Dialog mit Copy-Button und Warnhinweis | E2E |
| FK-08 | Key revoken erfordert Bestätigungs-Dialog und entfernt Key aus der Liste | E2E |

## 7. Abhängigkeiten

### Abhängig von (bestehend):

| REQ/NFR | Bezug |
|---------|-------|
| NFR-001 | Architektur-Layer (erweitert §6.1 JWT-Skizze zur vollständigen Spezifikation) |
| NFR-006 | API-Fehlerbehandlung (401 UNAUTHORIZED, 403 FORBIDDEN) |
| NFR-007 | Retry-Logik (Auth-Fehler sind nicht retryable) |

### Wird benötigt von:

| REQ | Bezug |
|-----|-------|
| REQ-024 | Mandantenverwaltung — baut auf User-Entität und JWT-Token auf |
| REQ-006 | Task-Zuweisung an User (zukünftige Erweiterung) |
| REQ-015 | Kalenderansicht — "vorbereitet für JWT-Auth" |

### Neue Infrastruktur-Abhängigkeiten:

| Komponente | Zweck |
|------------|-------|
| Redis | OAuth-State-Speicherung (5 Min TTL), Rate Limiting |
| Fernet/AES-256 | Verschlüsselung von Provider-Secrets und -Tokens |

### E-Mail-Service (Adapter-Pattern):

Der E-Mail-Versand wird über ein **abstraktes Interface** entkapselt (analog zum bestehenden Adapter-Pattern für GBIF/Perenual in REQ-011):

```python
# domain/interfaces/email_service.py
class IEmailService(ABC):
    @abstractmethod
    async def send_verification_email(self, to: str, token: str, display_name: str) -> None: ...
    @abstractmethod
    async def send_password_reset_email(self, to: str, token: str) -> None: ...
    @abstractmethod
    async def send_invitation_email(self, to: str, tenant_name: str, inviter_name: str, token: str, role: str) -> None: ...
```

Konkrete Implementierungen (austauschbar, nicht Teil dieser REQ):
- `SmtpEmailAdapter` — Direkter SMTP-Versand (`aiosmtplib`)
- `ResendEmailAdapter` — Transactional API (Resend)
- `ConsoleEmailAdapter` — Entwicklungsumgebung (loggt E-Mails auf stdout)

Die Wahl der konkreten Implementierung erfolgt per Konfiguration (`EMAIL_ADAPTER=smtp|resend|console`). Für die Entwicklungsumgebung genügt der `ConsoleEmailAdapter`.

## 8. Neue Python-Dependencies

| Paket | Version | Zweck | Status im Stack |
|-------|---------|-------|----------------|
| `authlib` | `>=1.3.0` | JWT (HS256), OAuth2 Client, OIDC Discovery, PKCE | **Neu** — ersetzt `python-jose` aus NFR-001 §6.1 |
| `passlib[bcrypt]` | `>=1.7.4` | Passwort-Hashing (Bcrypt, Cost 12) | **Neu** — in NFR-001 §6.1 referenziert, aber nicht installiert |
| `slowapi` | `>=0.1.9` | Rate Limiting (nutzt Redis als Backend) | **Neu** |
| `cryptography` | `>=42.0` | Fernet-Verschlüsselung für Provider-Secrets | **Neu** |
| `httpx` | `>=0.28.0` | HTTP-Client für GitHub-API, HIBP-Check | **Bereits vorhanden** |
| `redis` | `>=5.2.0` | OAuth-State, Rate Limiting, Token-Blocklist | **Bereits vorhanden** (Celery-Broker) |

## 9. Scope-Abgrenzung

**In Scope:**
- Lokale Benutzerkonten (E-Mail + Passwort)
- OAuth2/OIDC mit Google, GitHub, Apple (benannt) + generische OIDC-Provider
- JWT Access/Refresh Token Lifecycle mit Rotation
- Benutzerprofil-Verwaltung (Name, Avatar, Locale, Timezone)
- Passwort-Reset per E-Mail
- Account-Linking (mehrere Auth-Methoden pro User)
- Login-Throttling und Rate Limiting
- Session-Verwaltung (aktive Geräte, Logout-All)
- OIDC-Provider-Konfiguration durch System-Admin
<!-- Quelle: Service Accounts v1.7 -->
- Service Accounts (`account_type: 'service'`) als nicht-interaktive Konten für Third-Party-Systeme
- Tenant-scoped und Platform-scoped Service Accounts
- API-Key-only Authentifizierung für Service Accounts (kein Passwort, kein SSO)
- IP-Allowlist und individuelles Rate Limit pro Service Account
- Service Account Lifecycle (erstellen, suspendieren, reaktivieren, löschen, Key-Rotation)
- 15 neue API-Endpoints für Service Account Verwaltung
<!-- /Quelle: Service Accounts v1.7 -->
<!-- Quelle: Tenant-Notfallverwaltung v1.7 -->
- Tenant-Notfallverwaltung: Emergency-Admin-Ernennung bei verwaisten Tenants
- Tenant-Suspendierung/Reaktivierung durch Platform-Admin
- User-Suspendierung/Reaktivierung durch Platform-Admin
- Verwaist-Erkennung via Celery-Task (wöchentlich)
- 7 neue Admin-API-Endpoints (`/admin/tenants/{key}/emergency-admin`, `/suspend`, `/reactivate`, `/admin/users/{key}/suspend`, `/reactivate`, `/admin/tenants/{key}/members`)
<!-- /Quelle: Tenant-Notfallverwaltung v1.7 -->

**Nicht in Scope (bewusst ausgeklammert):**
- Mandanten/Tenants und Rollenkonzept → REQ-024
- 2-Faktor-Authentifizierung (TOTP, WebAuthn) → zukünftige Erweiterung
- Social-Login-Profilsynchronisation (regelmäßiger Name/Bild-Abgleich) → zukünftig
- SAML 2.0 → Enterprise-Segment, aktuell nicht priorisiert
- E-Mail-Template-Customization → Standard-Templates genügen initial
- User-Administration durch Nicht-Admins (Nutzer können nur ihr eigenes Profil verwalten)
<!-- Quelle: Service Accounts v1.7 -->
- OAuth2 Client Credentials Grant für Service Accounts → API-Keys sind einfacher und ausreichend
- Service Account Impersonation (ein SA agiert im Namen eines menschlichen Users) → Sicherheitsrisiko, nicht unterstützt
- Automatische Service Account Erstellung bei Third-Party-Integration → immer manuell durch Admin
- Service Account Audit-Log (detailliertes Zugriffsprotokoll) → zukünftig, nach allgemeinem Audit-Log
<!-- /Quelle: Service Accounts v1.7 -->
<!-- Quelle: Issue #1118 -->
- Persistiertes Audit-Log der QR-Gerätekopplung (§3.8) → **bewusst nicht** eingeführt: die Prüfspur sind structlog-Events (`device_pairing_created` / `device_pairing_redeemed` / `device_pairing_redeem_failed`), kein ArangoDB-Datensatz und keine neue Collection. Ein persistiertes Zugriffsprotokoll bleibt an das allgemeine Audit-Log gebunden (siehe Service-Account-Audit-Log oben), damit dessen Zurückstellung kohärent bleibt.
<!-- /Quelle: Issue #1118 -->

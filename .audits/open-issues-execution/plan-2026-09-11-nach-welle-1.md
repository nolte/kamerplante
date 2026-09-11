# Umsetzungsplan der offenen Issues — Stand nach Welle 1

**Gemessen gegen `origin/develop` @ `831b283f7`, 2026-09-11.** Jede tragende
Behauptung unten ist gegen den Quelltext, die GitHub-API oder die Lauf-Historie
nachgemessen, nicht aus dem Issue-Text übernommen. Sechs Messungen überholen den
Issue-Text so weit, dass eine autonome Abarbeitung nach Aktenlage falsche Arbeit
produzieren würde.

**26 offene Issues**, davon eines das Renovate-Dashboard (#12) → **25
Arbeitsposten**. **1 offener PR**: #1348 (Draft, blockiert durch #1368).

Der Vorgängerplan `plan-2026-09-11.md` deckte Welle 1 ab (#1385, #1352/#1372,
#1353). Alle drei sind gemergt, alle zugehörigen Issues geschlossen. Dieser Plan
beginnt bei dem, was danach offen ist — einschließlich der fünf Issues, die
**beim Abarbeiten von Welle 1 entstanden sind** (#1402, #1403, #1404, #1405,
#1406).

---

## 0. Was die Messung gegen den Issue-Text kippt

| Posten | Der Issue-Text sagt | Gemessen |
|---|---|---|
| #1404 Prämisse | `develop` verlangt zwei Pflicht-Checks | **bestätigt** — `["static / Static CI Tests","lint-test-build (22)"]`, `strict: true` |
| #1397 Umfang | neun Fundstellen offen, A/B/D-Gruppe inbegriffen | **A, B und D sind erledigt**; offen sind drei AQL-Projektionen |
| #1292 Status | „wartet auf das nächste Auftreten" | die Selbstdiagnose feuerte **zweimal**, 08.09. und 11.09., beide Male derselbe Zweig |
| #1236 Zustand | drei Dateien unversioniert in einem Harness-Worktree, kein PR | Skript **und** 674-Zeilen-Test liegen auf develop, ein Taskfile-Ziel ruft sie; nur der geplante Workflow fehlt |
| #1406 Reichweite | „eine Opt-in-Liste" | **16 von 36** Seed-Dateien unter keinem Schema-Hook |
| #1403 Aufwand | „das literale `True` am Aufrufort entfernen" | `OAuthUserInfo` trägt **kein** `email_verified`; drei Bauplätze müssen es erst führen |

### F-1 — #1397 ist zu drei Zeilen geschrumpft, und der Issue-Körper sagt es nicht

`a3ad72329` (PR #1398) hat die A-, B- und D-Gruppe repariert. Gemessen enthält
`src/backend/app/` keine einzige lebende Prüfung mehr gegen `location.tenant_key`
oder `slot.tenant_key`. Jede verbliebene Fundstelle ist ein **Kommentar**, der den
reparierten Zustand erklärt:

```
overwintering_profile_service.py:279, :774, :896   Kommentar
succession_plan_service.py:162                      Kommentar
site_service.py:58                                  Kommentar
plant_instance_service.py:250, :434, :864           Kommentar
season_state_service.py:231                         Kommentar
tasks/phase_transitions.py:55                       Kommentar
```

Offen sind genau drei Ausdrücke, alle in `data_access/arango/plant_instance_repository.py`:

```aql
:309  location_name: (location != null AND location.tenant_key == @tenant_key) ? location.name : null,
:311  slot_label:    (slot != null AND slot.tenant_key == @tenant_key) ? slot.slot_id : null,
:453  location_name: location != null AND location.tenant_key == @tenant_key ? location.name : null,
```

Das ist die C-Gruppe: keine Ablehnung und keine Preisgabe, sondern eine
Projektion, die für **jede** Zeile `null` liefert. Ein Bearbeiter, der dem
Issue-Körper folgt, beginnt mit der Fixture-Korrektur der A-Gruppe und findet
neun bereits reparierte Stellen. **Der Körper muss vor der Bearbeitung
geschrumpft werden** — das ist Arbeitspaket P2.3 und nicht optional.

Dies ist zugleich die Falle, die dieses Repository am häufigsten getroffen hat:
Grep findet die **Erklärung** eines behobenen Defekts und meldet ihn als offen.

### F-2 — #1292 wartet nicht mehr, seit drei Tagen

`create_care_task` hat in zwei der letzten acht Nächte versagt, und die
Selbstdiagnose aus #1288 hat beide Male **denselben** Zweig benannt:

| Nacht | Profil | Aussage |
|---|---|---|
| 2026-09-08 | light | „the queue was scoped to that plant on at least one pass, so the card is genuinely absent — look at the create, not the lookup" |
| 2026-09-11 | full-tablet | identisch |

Der Filter hat also gegriffen, und die Karte war trotzdem nicht da. Die
Untersuchung gehört an den **Create-Pfad**, nicht an die Suche. Der Issue-Titel
(„awaiting the next occurrence") ist überholt; der Posten ist bearbeitbar.

Die Warnung im Issue bleibt gültig und ist jetzt doppelt begründet: **das
15-Sekunden-Budget nicht als ersten Schritt erhöhen.** Die Schleife navigiert und
filtert bei jedem Durchlauf neu; ist die Karte wirklich abwesend, macht eine
längere Wartezeit den Fehlschlag nur langsamer. In diesem Repository gibt es dafür
den Präzedenzfall #1204, wo eine Live-Karte *umgewandelt* statt verspätet war.

### F-3 — #1236s Fähigkeit liegt auf develop und hat keine automatische Lane

Der Issue-Körper beschreibt drei unversionierte Dateien in einem Harness-Worktree.
Gemessen:

| Datei | auf develop |
|---|---|
| `scripts/ci/check_deployed_build.py` | **ja** (via `b760da40c`, #1318) |
| `src/backend/tests/unit/test_deployed_build_check.py` | **ja** |
| `.github/workflows/deployed-build-freshness.yml` | **nein** |

Ein Konsument existiert: `.taskfiles/deploy.yaml:107` ruft das Skript als
`task verify:deployed-build INSTANCE_URL=… CHART_VERSION=…`. Das ist ein
**manueller** Aufruf. Kein Workflow, kein Zeitplan, kein Hook. Und
`helm/kamerplanter/values.yaml:257` setzt `HEALTH_EXPOSE_BUILD_REVISION: "true"`,
die Instanz würde also antworten.

Damit ist der Zustand nicht „Implementierung fehlt", sondern **„Prüfung
vorhanden, nichts ruft sie"** — die teuerste Klasse dieses Repositories. Der
Restaufwand ist die geplante Lane, nicht die 1810 Zeilen.

### F-4 — #1406 ist doppelt so groß wie beschrieben

12 `check-jsonschema`-Hooks mit `files:`-Mustern gegen 36 Seed-Dateien in
`src/backend/app/migrations/seed_data/`. Gemessen durch Anwendung der echten
Regexes:

**16 Dateien liegen unter keinem Hook**, darunter tragende:

```
activities.yaml          fertilizers.yaml           nutrient_plans_hydro.yaml
adventskalender.yaml     fish_species.yaml          nutrient_plans_outdoor.yaml
botanical_families.yaml  gardol.yaml                nutrient_plans_ro.yaml
companion_planting.yaml  glossary_terms.yaml        plagron.yaml
harvest_indicators.yaml  hardiness_zones.yaml       substrate_defaults.yaml
workflows.yaml
```

`fertilizers.yaml` speist die Mischreihenfolge (`mixing_priority`), die drei
`nutrient_plans_*.yaml` speisen die Düngeberechnung. Das ist nicht der Randfall,
den „eine Opt-in-Liste" nahelegt.

### F-5 — #1403 ist kein Einzeiler

`auth_service.py:792` trägt das literale `True` unverändert. Aber:
`OAuthUserInfo` (`domain/models/auth.py:95`) führt `provider`, `provider_user_id`,
`email`, `display_name`, `avatar_url` — **kein `email_verified`**. Das Modell wird
an drei Stellen gebaut (`oauth_engine.py:157`, `:181`, `:205`), je eine pro
Provider. Der Anspruch muss also erst durch Modell und drei Bauplätze gezogen
werden, bevor der Aufrufort ihn weiterreichen kann.

Das Issue nennt diese Frage in §1 und lässt sie offen; die Antwort ist gemessen
und lautet: er existiert nicht.

### F-6 — die Pflicht-Checks sind zwei, nicht vier

```
$ gh api repos/nolte/kamerplanter/branches/develop/protection --jq '.required_status_checks.contexts'
["static / Static CI Tests","lint-test-build (22)"]
```

`security / Build` und `chain-bench / Chain Bench` laufen auf jedem PR und sind
**nicht** erzwungen. Der Vorgängerplan und die Merge-Serie vom 11.09. haben sie
als erzwungen behandelt; das war folgenlos (es wurde auf mehr gewartet als nötig),
aber es steht falsch im Repository und ist hiermit korrigiert. #1404s Prämisse
stimmt unverändert.

---

## 1. Abhängigkeiten und Widersprüche

### Abhängigkeitsgraph

```
#1404 (Backend-Lane erzwingen)  ──> #1402 (dritter Selektor)   [sonst blockiert der erweiterte Sweep nichts]
                                └─> #1406 (Seed-Schema-Reichweite)  [gleiche Durchsetzungsmechanik]

Doku-Wiederherstellung ──> #1404, #1405, #1406   [ihre §-Verweise lösen sich sonst nicht auf]

#1403 ──> OAuthUserInfo.email_verified ──> oauth_engine.py:157/:181/:205 (3 Provider)

#1397-Rest (C-Gruppe) ── unabhängig, aber Körper vorher schrumpfen

#1368 ──> PR #1348 ──> #1175 ──> #1347 (extern blockiert: gesourcte Massewerte)

#1383 (uv selbstprüfend) ──> #1374 (Side-Services auf uv)   [AK „poetry darf nicht gelistet sein"]

#1402, #1403 ──> #1361 (Release v0.4.0)   [Nutzerentscheidung, siehe §2]

#1376, #1389 ──> Dedup in security-zap-postmerge.yml   [Ursache, nicht Symptom]

#1061 Phase 0 ──> Phasen 1–3 ──> Phase 4 (Gates)
```

### W-1 — Drei Issues berufen sich auf Dokumente, die es nicht gibt

#1404, #1405 und #1406 tragen alle die Zeile „Derived from
`spec/analysis/development-process-review-2026-09-11.md`" und verweisen auf §U1,
§M1, §M5, §M6 eines `development-process-improvement-plan-2026-09-11.md`.

**Beide Dokumente liegen nicht im Repository.**

| Dokument | Historie |
|---|---|
| `development-process-review-2026-09-11.md` (218 Z.) | in `679278985` auf dem #1397-Branch hinzugefügt, in `9218aa3d5` vor dem Merge wieder entfernt — **nie auf develop** |
| `development-process-improvement-plan-2026-09-11.md` (330 Z.) | über #1395 auf develop gemergt, in #1407 wieder entfernt |

Die zweite Entfernung war meine eigene: das Dokument war per `git add -A`
ungelesen mitgefahren, und ich habe es herausgenommen, weil ein ungeprüftes
Dokument nicht auf develop gehört. Dass drei offene Issues davon abhängen, habe
ich dabei nicht geprüft.

**Auflösung (Nutzerentscheidung, §2):** beide Dokumente werden nach
`spec/analysis/` zurückgeholt, in einem eigenen PR mit Review — die Prüfung, die
beim ersten Mal übersprungen wurde. Erst danach sind #1404/#1405/#1406 nach
Aktenlage bearbeitbar.

Inhaltlich tragen sie: fünf Fehlerklassen K1–K5 aus 325 geschlossenen Issues,
drei Ursachen U1–U3, und sieben Maßnahmen M1–M7 mit einer Reichweiten-Tabelle.
**M2, M3, M4 und M7 gehören zu `claude-shared` bzw. `pre-commit-hooks`, nicht zu
kamerplanter** — sie fehlen hier also nicht, sie sind auswärts verortet. Nur M1,
M5 und M6 sind kamerplanter-Posten, und genau diese drei sind als #1404, #1405,
#1406 gefilt. Der Issue-Bestand ist damit vollständig; nur die Quelle fehlt.

### W-2 — #1061 Phase 2 fordert etwas, das der Zielzustand verbietet

Das Abnahmekriterium lautet: „Zero notification writes outside the propagation
path". Gemessen schreibt `NotificationPropagationService` **direkt** in das
Repository (`:380`), und sein eigener Modul-Docstring sagt, warum:

> **not** re-dispatch through the async `NotificationEngine`: channel …

Es gibt also zwei Schreiber **mit Absicht**: den synchronen Propagationspfad
(in-band, idempotent über `group_key`) und die asynchrone `NotificationEngine`
(Kanalversand, vier `_notification_repo.create(...)`-Aufrufe). Wörtlich genommen
verlangt Phase 2, den Kanalversand durch den synchronen Pfad zu leiten — was der
Propagationspfad ausdrücklich nicht tun soll.

**Auflösung, im Plan verbindlich:** Phase 0 definiert **zuerst**, was als Verstoß
zählt, und zwar als Prädikat, nicht als Grep. Die Zählung „(b)" zählt
Notification-Schreibzugriffe, die *weder* über den Propagationspfad *noch* über
die Engine laufen. Ohne diese Definition ist die Grundlinie beliebig und das
Abnahmekriterium unerreichbar.

Dasselbe gilt für Zählung „(a)". Ein Grep über `timedelta` liefert 20 Treffer,
von denen die meisten Ablauffristen sind (Token-TTL, Passwort-Reset, Sitzungen)
und keine Wiederholungsrechnung. **Ein bestätigter Treffer** ist
`tank_engine.py:492`:

```python
next_due = last_log.performed_at + timedelta(days=schedule.interval_days)
```

Das ist eine Nächste-Fälligkeit außerhalb der `RecurrenceEngine`. Die übrigen
brauchen Triage. Ich nenne hier **keine Zahl**, weil ich sie nicht sauber
hergeleitet habe — und eine erfundene Grundlinie wäre genau der Ratschen-Fehler,
den Phase 0 verhindern soll.

### W-3 — #1376 und #1389 sind dasselbe Falschpositiv, und es kommen weitere

Beide melden `40018 — SQL Injection` auf `http://backend:8000`, Parameter `token`
von `POST /api/v1/privacy/email-change/confirm`. Der Vorgängerplan hat das als
**Falschpositiv** nachgemessen: die einzige SQL-Schnittstelle des Systems ist
`psycopg` gegen TimescaleDB in `data_access/timescale/observation_repository.py`,
bind-parametrisiert; der Angriffsstring kann als Syntax nirgends ankommen.

Gemessen sind es **vier** solcher Issues insgesamt (#1065, #1158 geschlossen;
#1376, #1389 offen), und `security-zap-postmerge.yml:298` ruft
`github.rest.issues.create` **ohne jede Deduplizierung**, mit dem Commit-SHA im
Titel. Ein dauerhafter Fund erzeugt damit unbegrenzt viele Issues.

**Der Unterdrückungspfad kann den Fall nicht ausdrücken.**
`tests/security/zap-api-rules.tsv` hat das Format
`<PluginID> <THRESHOLD> <Confidence> <Note>` — **keine URL-Spalte**. Ein
`40018 IGNORE` würde den Scanner an der einzigen Stelle blind machen, an der SQL
wirklich vorkommt.

**Auflösung:** die Arbeit ist nicht „die zwei Issues schließen", sondern
**Deduplizierung im Workflow** plus eine **URI-gebundene Ausnahme mit
geschriebenem Grund und Ablaufdatum** in `scripts/security/zap_gate.py`, wo die
§5.1/§5.2-Matrix ohnehin liegt und wo `IGNORE_EXPIRY` bereits eine
Ablaufprüfung führt. Die zwei Issues schließen dann als Duplikate mit Verweis.

### W-4 — #1223s Abbruchbedingung ist nicht eingetreten

Das Issue hält fest, dass der Gegen-Check *nicht* gebaut wird, und benennt die
Bedingung, die das umkehrt: **ein beobachteter `changes`-Job mit `failure` oder
`cancelled` auf einem develop-Push.**

Gemessen über die letzten 40 `docker-publish.yml`-Läufe auf develop:
**40× `success`, 0× `failure`, 0× `cancelled`.** Die Bedingung ist nicht erfüllt.
#1223 bleibt als bewusste Nicht-Entscheidung stehen und ist **kein**
Arbeitsposten dieses Plans.

Dass diese Bedingung überhaupt nachprüfbar formuliert ist, ist der Grund, warum
sie hier in einem Satz erledigt werden kann statt in einer Neubewertung.

### W-5 — #1321 ist aus diesem Repository nicht umsetzbar

Beide Hooks sind aktiv (`.pre-commit-config.yaml:579` `actionlint-docker`,
`:585` `shellcheck`), beide ziehen bei jedem Lauf ein Docker-Hub-Image, beide
liegen in der **erzwungenen** `static`-Lane. Cachen ist unmöglich, nicht bloß
unterlassen: pre-commits `languages/docker_image.py` setzt
`ENVIRONMENT_DIR = None`, das Image liegt nie unter `~/.cache/pre-commit`.

`static` ist ein aus `nolte/gh-plumbing` konsumierter Reusable-Workflow; ein
`uses:`-Job nimmt keine eingefügten Schritte an. Die Prävention gehört dorthin.

**Auflösung:** #1321 bleibt offen und wird **nicht** in eine Welle einsortiert. Es
ist ein Upstream-Posten mit einem hier gemessenen Befund. Der Plan führt ihn als
solchen, damit der nächste Leser ihn nicht erneut herleitet.

### W-6 — #1347 ist extern blockiert und bleibt es

Eine CEC-Plausibilitätsspanne braucht **zitierte massebasierte Werte je Material
mit der Rohdichte, bei der die Quelle gemessen hat**. Das Issue rechnet vor,
warum eine aus den heutigen Werten abgeleitete Spanne nur diese ratifizieren
würde (elf Boden-Datensätze bei einem Viertel bis der Hälfte der REQ-019-Spanne;
Sphagnum bei 267 meq/100 g über jeder Bande). Das ist keine Programmieraufgabe.

#1347 steht im Plan als **extern blockiert**, mit der Bedingung, die ihn
entblockt.

---

## 2. Entscheidungen, die vor der Arbeit getroffen wurden

Vom Betreiber am 2026-09-11 entschieden, damit die Abarbeitung nicht auf
Rückfragen wartet:

| Frage | Entscheidung | Folge für den Plan |
|---|---|---|
| Die beiden fehlenden Analyse-Dokumente | **beide nach `spec/analysis/` zurückholen** | eigenes Arbeitspaket P1.2, **vor** #1404/#1405/#1406 |
| Release v0.4.0 | **bis nach der nächsten Sicherheitswelle halten** | #1361 kommt nach Welle 2, nicht davor |
| #1403, fehlender `email_verified`-Anspruch | **fehlend = nicht verifiziert, kein Auto-Link** | Verhaltensänderung; braucht eine Notiz am Aufrufort und im Änderungsprotokoll |
| Große Posten | **nur #1061** | #779 und #618 bleiben geparkt |

Zur zweiten Entscheidung, damit sie nachvollziehbar bleibt: der Rückstand beträgt
heute **60 Commits und 11 Tage**, und `v0.4.0` ist seit dem 31.08. Entwurf. Ein
Entwurf ist keine Auslieferung — er hat kein Tag, ArgoCD kann ihn nicht pinnen.
Das Halten ist bewusst und kostet weitere Tage; der Plan hält beides fest, damit
die nächste Lag-Meldung nicht als Neuigkeit gelesen wird.

Zur dritten: „fehlend = nicht verifiziert" ändert das Verhalten jeder
Installation, deren Provider den Anspruch weglässt. Der Nutzer landet dann auf dem
bereits vorhandenen Pfad „mit Passwort anmelden, dann verknüpfen". Die
Entscheidung gehört **an den Code**, nicht nur in dieses Dokument.

---

## 3. Die Wellen

### Welle 1 — Fundament (nichts davon hängt an etwas anderem)

| Paket | Issue | Inhalt |
|---|---|---|
| P1.1 | **#1404** | Wächter-Lane in `backend.yml` ohne `paths:`-Filter, als Pflicht-Check eintragen |
| P1.2 | W-1 | Review- und Maßnahmenplan-Dokument nach `spec/analysis/` zurückholen, mit Review |
| P1.3 | **#1405** | Falsifizierbarkeits-Fähigkeit adoptieren, zwei lokale Skills zurückziehen |

P1.1 zuerst, weil ohne erzwungene Lane kein weiterer mechanischer Wächter eine
Zusammenführung aufhalten kann — das ist die Begründung, die der Maßnahmenplan
selbst führt. P1.2 parallel, weil es P1.3 und Welle 4 lesbar macht. P1.3
parallel, weil reine Adoption; die Plugin-Pendants sind gemessen vorhanden
(`nolte-engineering:test-pyramid-check`, `nolte-engineering:quality-gate`,
`spec/project/test-falsifiability/`).

### Welle 2 — Sicherheit

| Paket | Issue | Inhalt |
|---|---|---|
| P2.1 | **#1402** | dritter Selektor bzw. andere Frage; Triage der 133 Durchfaller |
| P2.2 | **#1403** | `email_verified` durch Modell und drei Bauplätze ziehen; fehlend = nicht verifiziert |
| P2.3 | **#1397-Rest** | die drei AQL-Projektionen; **vorher** den Issue-Körper schrumpfen |

P2.1 nach P1.1, damit der erweiterte Sweep tatsächlich blockiert. P2.2 und P2.3
unabhängig voneinander und von P2.1.

### Welle 3 — Auslieferung

| Paket | Issue | Inhalt |
|---|---|---|
| P3.1 | **#1361** | `v0.4.0` veröffentlichen — **erst nach Welle 2** (Betreiberentscheidung) |
| P3.2 | **#1236** | die fehlende Lane für das vorhandene Prüfskript |
| P3.3 | **#1376/#1389** | Deduplizierung im ZAP-Postmerge-Workflow + URI-gebundene Ausnahme |

### Welle 4 — Daten und Schema

| Paket | Issue | Inhalt |
|---|---|---|
| P4.1 | **#1406** | Abdeckungsprüfung, die aufzählt statt aufzulisten; 16 ungeprüfte Dateien |
| P4.2 | **#1368** | WHC-Signal entscheiden + Seeder-Upsert → entblockt PR #1348 → #1175 |

### Welle 5 — Frontend

| Paket | Issue | Inhalt |
|---|---|---|
| P5.1 | **#1373** | Ladebereich des Dashboards deckt die zwei selbstfetchenden Widgets |
| P5.2 | **#1390** | `AdminEdit*Page`: Fehlerzustand statt „nicht gefunden" |
| P5.3 | **#1393** | verwaiste Aufgabenfotos: Janitor, `DELETE`-Route, Löschkaskade, `add_photo_ref` zurückziehen |

### Welle 6 — Werkzeugkette und Tests

| Paket | Issue | Inhalt |
|---|---|---|
| P6.1 | **#1383** | uv-Kette und Renovate-Pfad selbstprüfend machen |
| P6.2 | **#1374** | vier Side-Services auf uv-Locks — **nach** P6.1 |
| P6.3 | **#1375** | Plan-Stub in `scripts/worktree_add.sh` |
| P6.4 | **#1292** | den benannten Zweig reparieren: der Create-Pfad |

### Welle 7 — #1061, ADR-008

Fünf Phasen, jede für sich lieferbar. Phase 0 definiert **zuerst** die beiden
Prädikate (siehe W-2), dann die Grundlinie.

---

## 4. Reihenfolge und Begründung

```
Welle 1  P1.1 ─┬─> Welle 2  P2.1
         P1.2 ─┼─> P1.3, Welle 4
         P1.3 ─┘
Welle 2  P2.1, P2.2, P2.3  (untereinander unabhängig)
             └─> Welle 3  P3.1 (Release, Betreiberentscheidung)
Welle 3  P3.2, P3.3  (unabhängig von P3.1)
Welle 4  P4.1, P4.2  (unabhängig von Welle 2 und 3)
Welle 5  P5.1, P5.2  (unabhängig von allem)
Welle 6  P6.1 ──> P6.2 ;  P6.3, P6.4 unabhängig
Welle 7  Phase 0 ──> 1,2,3 ──> 4
```

Parallelisierbar ohne Konflikt: Welle 5 und Welle 6 berühren keine Datei der
Wellen 1–4. Welle 4 berührt `seed_data/` und `tests/unit/migrations/`, Welle 2
berührt `app/api/`, `app/domain/` und `tests/unit/api/`.

**Der Merge-Zug ist die Begrenzung, nicht die Bearbeitung.** `strict: true` macht
jeden offenen PR nach jeder Zusammenführung ungültig. Aus dem Sweep vom 2026-08-14
stammt die Erfahrungszahl von etwa drei PRs gleichzeitig; sie ist **hier nicht neu
gemessen** und steht als Richtwert, nicht als Messung. Mehr parallel zu bearbeiten
erzeugt Rebase-Arbeit, keine Geschwindigkeit.

---

## 5. Arbeitspakete im Detail

### P1.1 — #1404, die Wächter-Lane wird erzwungen

Ein Job in `.github/workflows/backend.yml`, der **nur** die mechanischen Wächter
fährt (`tests/unit/api/test_write_route_gates.py` und die Geschwister-Zusicherungen),
**ohne `paths:`-Filter**, auf `push` jedes Branches, mit `concurrency` +
`cancel-in-progress`. Die teure volle Suite bleibt pfadgefiltert und beratend.

Dann der neue Check-Name in `contexts` in `.github/settings.yml`, mit dem
Kommentar in der Form, die diese Datei schon führt: warum befördert, auf welcher
Messung, und unter welcher Bedingung zurückgenommen.

**Messung vor der Beförderung:** die Laufzeit des Jobs. `strict: true`
multipliziert jeden Pflicht-Check über den Merge-Zug; bleibt der Job nicht unter
zwei Minuten, ist der Schnitt falsch.

**Falsifizierung — und das ist der ganze Posten:** ein Wegwerf-PR, der eine
ungegatete Schreibroute **zusammen mit einer reinen Frontend-Änderung** hinzufügt.
Der neue Check muss rot werden und den PR unzusammenführbar lassen. Ein grünes
Ergebnis heißt, der Pfadfilter greift weiterhin und die Beförderung ist wirkungslos.

**Stabilität, hier neu gemessen** (das Issue nennt ältere Zahlen; meine sind
günstiger, und die Differenz gehört benannt, damit niemand sie für einen Tippfehler
hält):

| Lane | Erfolg | Fehlschlag | Abbruch |
|---|---:|---:|---:|
| `Backend CI` (letzte 40) | 33 | **0** | 7 |
| `Static CI Tests` (letzte 40, bereits erzwungen) | 34 | 2 | 4 |

Die zu befördernde Lane hat über dieses Fenster **keinen einzigen Fehlschlag**,
die bereits erzwungene zwei. Der als Blocker genannte Flake #836 ist am
2026-07-28 geschlossen worden (verifiziert). Abbrüche sind der Merge-Zug, nicht
Instabilität: `strict: true` bricht laufende Prüfungen ab, sobald ein anderer PR
landet.

### P1.2 — die beiden Analyse-Dokumente zurückholen

```bash
git show 679278985:spec/analysis/development-process-review-2026-09-11.md
git show e69d69828:spec/analysis/development-process-improvement-plan-2026-09-11.md
```

Beide nach `spec/analysis/` schreiben, **mit** dem Review, das beim ersten Mal
ausgefallen ist. Das ist der Grund, warum sie entfernt wurden; das Zurückholen
ohne Prüfung würde denselben Fehler wiederholen.

Beim Review besonders zu prüfen: die Zahlenbehauptungen (325 geschlossene Issues,
die Klassen-Zählungen K1–K5, die Lauf-Statistiken in §U1) — jede davon ist
nachmessbar, und keine ist bisher nachgemessen worden.

### P2.1 — #1402, die andere Frage

Der Sweep fragt heute „trägt diese Route das bestimmte `ctx`". Die richtige Frage
ist „trägt die effektive Dependency-Kette dieser Schreiboperation **überhaupt**
eine Autorisierung". `route.dependant` transitiv zu lesen statt
`inspect.signature` erfasst auch Router-Ebene-Gates.

Gemessen auf `831b283f7`, mit dem Walker des Sweeps plus transitivem
`dependant`-Lesen:

| Größe | Wert |
|---|---|
| Schreiboperationen unter `/api/v1` | 439 |
| davon außerhalb beider Selektoren | 133 |
| ohne jede Auth-Dependency | 24 |
| davon bauartbedingt öffentlich | 10 |
| **verbleibend, nicht öffentlich gewollt** | **14** |
| nur per API-Key authentifiziert | 5 |

Die vierzehn: sieben in `calculations/router.py` (`/vpd`, `/gdd`,
`/photoperiod-transition`, `/sun-times`, `/sun-times-range`, `/slot-capacity`,
`/vernalization`) und sieben in `nutrient_calculations/router.py`
(`/mixing-protocol`, `/flushing`, `/runoff`, `/mixing-safety`, `/water-mix`,
`/water-mix/reverse`, `/ec-budget`). Die achte Schreibroute des zweiten Moduls,
`/area-dosing`, trägt `get_current_tenant` und gehört nicht dazu — deshalb heißt
die Zahl vierzehn und nicht fünfzehn.

Drei der zweiten Gruppe lesen zusätzlich ungescopt: `mixing-protocol` (`:69`),
`mixing-safety` (`:179`) und `ec-budget` (`:270`/`:287`/`:293`) rufen
`service.get_fertilizer(...)`, und `FertilizerService.get_fertilizer` überspringt
seine Prüfung beim Default `tenant_key=""`.

**Der Issue-Körper von #1402 nennt weiterhin nur eine der beiden Gruppen.** Die
korrigierte Tabelle steht im jüngsten Kommentar. Wer #1402 bearbeitet, nimmt die
aus dem Kommentar. Den Körper nachzuziehen ist Teil des Pakets.

Erwartung: der dritte Selektor läuft beim ersten Lauf gegen eine große Zahl von
Routen rot. Das ist der Zweck, und die Triage **ist** die Arbeit.

### P2.2 — #1403, der Anspruch muss erst existieren

Reihenfolge, die aus der Messung folgt:

1. `OAuthUserInfo` um `email_verified: bool | None = None` erweitern (`None`
   heißt „Provider hat nichts gesagt", und das ist nach Entscheidung §2
   **nicht** verifiziert).
2. Die drei Bauplätze in `oauth_engine.py` (`:157`, `:181`, `:205`) den Anspruch
   aus der jeweiligen Provider-Nutzlast lesen lassen.
3. Erst dann `auth_service.py:792` das literale `True` durch den echten Wert
   ersetzen.
4. Die Entscheidung „fehlend = nicht verifiziert" **am Aufrufort** notieren, nicht
   nur im Issue.

**Falsifizierung:** ein Test, der mit einem *unverifizierten* Anspruch nicht
auto-verknüpft und gegen den heutigen Code rot ist. Dazu ein zweiter für den
*fehlenden* Anspruch, der die getroffene Entscheidung festhält. Und eine
Absenzprüfung, dass kein Aufrufer je wieder eine Konstante in `should_auto_link`
schiebt — sonst ist die Reparatur eine Momentaufnahme.

Offen und im Issue benannt: ob die `auth_providers`-Zeilen zu prüfen sind, die
entstanden, solange die Route ungegatet war. Der Guard ist änderungswirksam und
fasst Bestandsdaten nicht an.

### P2.3 — #1397, zuerst den Körper schrumpfen

**Reihenfolge ist hier nicht Geschmack.** Der Issue-Körper beschreibt neun
Fundstellen; acht davon sind erledigt. Wer ihn unverändert abarbeitet, beginnt mit
der Fixture-Korrektur der A-Gruppe und findet reparierten Code.

1. Körper auf die C-Gruppe reduzieren, mit einem Satz dazu, was erledigt ist und
   durch welchen Commit.
2. Die drei AQL-Projektionen: entweder den Anker in AQL mitlaufen lassen
   (`Location → Site → tenant_key`), oder die Projektion aufhören lassen, eine
   Prüfung vorzutäuschen.
3. **Nachweis nicht durch einen grünen Test**, sondern durch eine gerenderte
   Liste, die die Namen zeigt. Das Issue verlangt das ausdrücklich, und es ist
   richtig: ein Test, der `null` erwartet, wäre heute grün.
4. Die offene Entscheidung aus dem Issue: ob `Location.tenant_key` und
   `Slot.tenant_key` überhaupt am Modell bleiben. Ein Feld, das immer leer ist und
   das fünf Stellen bereits als bedeutungstragend gelesen haben, ist eine Falle,
   die neu gestellt wird. Entscheidung gehört ans Modell geschrieben.

### P3.2 — #1236, nur die Lane fehlt

Nicht die 1810 Zeilen bauen — die liegen auf develop. Zu bauen ist der geplante
Workflow, der das vorhandene Skript fährt.

Vor der Übernahme zu prüfen, was der Issue-Körper selbst nennt und was seither
dazugekommen ist:

- ob das Erreichen einer privaten Instanz aus der CI überhaupt im Rahmen liegt
  oder ob die Prüfung in den Cluster gehört;
- ob `HEALTH_EXPOSE_BUILD_REVISION` — in `values.yaml:257` auf `"true"` gesetzt,
  im Backend aber **standardmäßig aus** — die Prüfung in genau der Umgebung
  wirkungslos macht, die sie beobachten soll;
- die Drei-Antworten-Regel des Skripts (kein Schlüssel / `"unknown"` / 40-stelliger
  SHA) ist die Stelle, an der „unentschieden" nicht als sauber durchgehen darf.

### P4.1 — #1406, aufzählen statt auflisten

`scripts/check_seed_schema_coverage.py` plus Hook: jede Datei unter dem
Seed-Baum ist von einem Schema gedeckt, **aus dem Baum aufgezählt**, nicht aus
einer Liste. Eine ungedeckte Datei ist rot; ein Eintrag, der eine nicht mehr
existierende Datei nennt, ebenfalls — die Veraltungsregel, der
`check_layer_imports` und `check_route_role_guards` schon folgen.

Gemessener Ausgangspunkt: **16 von 36** ungedeckt (Liste in §0/F-4). Die Prüfung
wird beim ersten Lauf rot sein, und das ist richtig so.

Zweite Hälfte, aus #1005: Schema-Felder, deren **Abwesenheit** stromabwärts als
Freigabe gelesen wird, beginnend bei Toxizität. Je Feld entscheiden: erforderlich
machen, oder die Konsumenten hören auf, Abwesenheit als Freigabe zu lesen.

**Falsifizierung, zwei Nachweise:** eine neue Datei im Seed-Baum, die in keiner
Hook-Liste steht → rot. Und `substrates.yaml` auf den Stand vor #1152
zurückversetzen → rot.

### P5.3 — #1393, verwaiste Aufgabenfotos

**Betreiberentscheidung vom 2026-09-11, damit dieses Paket nicht erneut auf eine
Rückfrage wartet:** Janitor **und** `DELETE`-Route **und** Löschkaskade, und
`add_photo_ref` wird zurückgezogen. Alle vier Halbsätze des Issues sind damit
beantwortet.

Gemessen auf `831b283f7`, alle drei Lecks bestehen unverändert:

| Behauptung | Messung |
|---|---|
| `add_photo_ref` hat keinen Produktionsaufrufer | `task_service.py:1036` definiert es; genau **eine** Fundstelle außerhalb, und die liegt in `tests/` |
| keine `DELETE`-Route für Aufgabenfotos | `tasks/photo_router.py` führt genau einen Dekorator: `@router.post("")` |
| `delete_task` fasst `photo_refs` nicht an | keine Erwähnung von `photo_refs` oder Attachments im Rumpf |

Reihenfolge, die aus den Abhängigkeiten folgt:

1. **`add_photo_ref` entfernen.** Es hängt an nichts, und es ist die geladene
   Waffe: es hängt an `photo_refs` an, **ohne** die Referenz gegen den
   Attachment-Katalog aufzulösen — also genau das Loch, das #1388 gerade
   geschlossen hat. Zuerst weg, damit die folgenden Schritte es nicht bedienen
   müssen.
2. **`DELETE /tasks/{key}/photos/{attachment_id}`** mit dem Attachment-Gate, der
   Galerie nachgebildet. Danach macht der Entfernen-Knopf im Frontend das, wonach
   er aussieht — heute filtert `PhotoUpload.handleRemove` nur lokalen Zustand.
3. **Löschkaskade in `delete_task`.** Eine Aufgabe ist nur in `pending`,
   `skipped`, `cancelled` oder `dormant` löschbar, die Dokumentation einer
   abgeschlossenen Aufgabe geht also nie auf diesem Weg verloren. Das macht die
   Kaskade sicher — **und es gehört ausdrücklich hingeschrieben**, weil sie
   unumkehrbar ist.
4. **Janitor** (Celery, NFR-011-Nachbarschaft) für den verbleibenden Fall: ein
   Upload, der nie abgeschickt wurde. Der ist weder von 2 noch von 3 erfasst.

**Nachweis:** eine Quotenmessung vor und nach jedem der vier Schritte. Ein grüner
Test allein zeigt nicht, dass die Bytes freigegeben wurden, und die Quote ist der
Grund, warum dieser Posten überhaupt einer ist: `AttachmentService._enforce_quota`
(`:210`) zählt **jede** Attachment-Zeile des Mandanten, verknüpft oder nicht.

### P6.4 — #1292, der Create-Pfad

Die Beweislage ist da (§0/F-2), der Zweig benannt. Zu untersuchen ist, warum die
Karte nach dem Anlegen nicht in der Warteschlange auftaucht, obwohl der Filter
gegriffen hat.

**Nicht** das Budget erhöhen. Ein browserfreier Selbsttest unter
`tests/e2e_selftest/`, der gegen das vorige Verhalten rot ist, ist Abnahmebedingung —
und danach ein voller Sechs-Profil-Lauf von `e2e-nightly`.

---

## 6. Methodische Regeln für die autonome Abarbeitung

Diese Regeln stammen aus den teuersten Fehlern der letzten Wellen, nicht aus
allgemeiner Sorgfalt.

1. **Die im Issue behauptete Ursache vor der Umsetzung nachmessen.** In den
   Sweeps vom 15.08. und 22.08. war die Diagnose je dreimal falsch, und der
   vorgeschlagene Fix wäre wirkungslos gewesen. In diesem Plan überholt die
   Messung sechs Issue-Körper.

2. **Rot zuerst, und auf demselben Ausdruck.** Ein Falsifizierungstest, der eine
   benachbarte Aussage prüft, ist grün, während die Regel wirkungslos ist. Den
   alten Zustand mit `cp` wiederherstellen, nicht mit `git stash` — `git stash`
   entfernt die Datei aus dem Index, und der Commit enthält dann nur den Test.

3. **Die Prüffrage für jede Fixture und jedes Double:** nenne eine Eingabe, die
   das Echte ablehnt und das Double annimmt. #1397 ist der Musterfall — die
   Fixtures bauen Locations, die der Schreibpfad nie erzeugt.

4. **Bei jedem Guard die Geschwister suchen.** Ein am Aufrufort eingebauter
   Wächter driftet. Die Suche ist mechanisch: Schreibrouten derselben Form, in
   denen nicht jedes Pfadsegment in einem Lookup vorkommt.

5. **Das eigene Messwerkzeug ist so fehleranfällig wie der Code.** In der Sitzung
   vom 11.09. waren drei in Folge defekt, alle in Richtung „meldet nichts": ein
   Routenscan über `app.routes` (nicht flach — `include_router` hinterlässt
   `_IncludedRouter`-Hüllen), eine Warteschleife mit einer Wortgrenze hinter einer
   Klammer, und eine Tabelle mit Branch-SHAs, die der Squash-Merge auflöst. Jedes
   Werkzeug braucht eine Positivkontrolle.

6. **Grep findet die Erklärung, nicht nur den Defekt.** Ein Kommentar im Perfekt
   neben repariertem Code liest sich wie ein offener Fund. #1397 ist in diesem
   Plan genau daran erkannt worden.

7. **Ein Review über einen früheren Kopf ist keine Freigabe für den aktuellen.**
   Am 11.09. sind zwei PRs auf grünen Checks gemergt worden, während ihr Review
   noch lief, und beide Male fand er danach echte Defekte.

8. **Agenten arbeiten auf derselben Arbeitskopie.** Ein Review-Fork hat am 11.09.
   den Branch gewechselt und ihn gewechselt stehen lassen; die folgenden Messungen
   liefen gegen die falsche Fassung. Vor und nach einem Fork `git rev-parse HEAD`
   lesen.

9. **Die Vollständigkeit des Plans mechanisch prüfen, nicht durch Nachzählen.**
   Der Vorgängerplan hat #1402 in keiner Welle geführt, und das fiel erst einer
   Review auf. Die Prüfung ist billig: alle offenen Issue-Nummern gegen die in §3
   und §7 genannten abgleichen. Auf diesen Plan angewandt hat sie **#1393**
   gefunden, das ich beim Schneiden der Wellen übersehen hatte. Ein Plan, der
   einen Posten auslässt, sieht genauso aus wie einer, der ihn bewusst zurückstellt
   — der Unterschied ist nur mechanisch sichtbar.

---

## 7. Was dieser Plan bewusst auslässt

| Posten | Grund |
|---|---|
| **#779** API v2 | Betreiberentscheidung 2026-09-11: geparkt. Vollständige Vertragsänderung über Backend und SPA, 2711 snake_case-Felder allein in `types.ts`. |
| **#618** KAMI-Pipeline | blockiert durch fehlende Cloudflare-Zugangsdaten. Ohne die Schlüssel ist nur der PR für `feat/kami-media-pipeline` möglich, nicht der Lauf. |
| **#1321** Docker-Hub-Limit | aus diesem Repository nicht umsetzbar (W-5). Upstream-Posten in `nolte/gh-plumbing`. |
| **#1223** docker-publish S4 | bewusste Nicht-Entscheidung; die Abbruchbedingung ist gemessen nicht eingetreten (W-4). |
| **#1347** CEC-Bande | extern blockiert: braucht zitierte massebasierte Werte je Material (W-6). |
| **#1175** Restposten | hängt an #1368 und PR #1348; im Plan über P4.2 erreicht, nicht als eigener Posten. |
| **#12** | Renovate-Dashboard, kein Arbeitsposten. |
| **M2, M3, M4, M7** | gehören laut Reichweiten-Tabelle des Maßnahmenplans zu `claude-shared` bzw. `pre-commit-hooks`, nicht zu kamerplanter. |

**Und eine Zahl, die dieser Plan nicht nennt:** die Grundlinie für #1061 Phase 0.
Ein Grep liefert Kandidaten, keine Zählung, und die Definition, was als Verstoß
zählt, steht noch aus (W-2). Eine hier erfundene Grundlinie wäre die erste
Instanz des Fehlers, den Phase 4 verhindern soll.

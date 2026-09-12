# Entwicklungsprozess-Review aus 325 geschlossenen Issues

Stand: 2026-09-11. Datenbasis: alle 325 geschlossenen Issues von `nolte/kamerplanter`
(322 `COMPLETED`, 3 `NOT_PLANNED`), gemessen über `gh issue list --state closed`,
ergänzt um Branch-Protection, Workflow-Trigger und den Bestand an mechanischen
Prüfungen im Baum.

!!! info "Nachgeprüft am 2026-09-12 vor der Aufnahme ins Repository"
    Dieses Dokument entstand am 2026-09-11 auf dem Branch zu #1397 und wurde dort
    vor dem Merge wieder entfernt, weil es per `git add -A` ungeprüft mitgefahren
    war. Es kommt hier mit der Prüfung zurück, die damals ausfiel.

    **Stichprobe der tragenden Zahlen, gegen die GitHub-API gemessen:** alle neun
    Titel-Ketten in K1 und alle elf zitierten Titel in K2 sind wörtlich korrekt.
    `#1353` trägt die genannten 37 von 243 im Körper. 43 geschlossene Issues
    führen überhaupt eine Issue-Nummer im Titel; die 23 in K1 sind die Teilmenge,
    die damit einen *Vorgängerdefekt* benennt und nicht eine Automatik-Meldung.

    **Abweichung durch Zeitablauf, und nur dort:** die Kopfzahlen in §1 sind vom
    2026-09-11. Am 2026-09-12 sind es 327 geschlossene Issues statt 325
    (324 `COMPLETED` / 3 `NOT_PLANNED` statt 322/3) und 122 `bug` statt 121;
    `security` steht unverändert bei 47. Die Zahlen bleiben so stehen, wie sie
    gemessen wurden — ein Datenstand mit Datum ist nachvollziehbar, ein
    fortlaufend überschriebener nicht.

    Drei Maßnahmen dieses Dokuments sind als #1404, #1405 und #1406 gefilt und
    verwiesen bis heute auf eine Quelle, die nicht im Repository lag.

## 1. Gemessenes Bild

| Kennzahl | Wert |
|---|---|
| Geschlossene Issues gesamt | 325 |
| davon `bug` | 121 |
| davon `security` | 47 |
| Gegenstand ist Test / Check / CI-Gate statt Produkt | 77 (24 %) |
| Lebensdauer Median / p90 | 0,7 d / 6,2 d |

Zeitverlauf der Mandanten- und Gate-Klasse (Titel nennt `tenant`, `role gate`,
`gated on membership`, `cross-tenant`, `IDOR` oder `foreign`):

| Monat | alle | bug | security | tenant/gate | inerte Kontrolle | Folge-Defekt |
|---|---|---|---|---|---|---|
| 2026-07 | 166 | 45 | 3 | 6 | 3 | 7 |
| 2026-08 | 144 | 76 | 40 | 29 | 10 | 11 |
| 2026-09 (11 Tage) | 14 | 0 | 4 | 4 | 1 | 0 |

Die Klasse konvergiert nicht. Sie wird schneller geschlossen, nicht seltener.

## 2. Die fünf teuersten Fehlerklassen

### K1 — Geschwister-Drift: der Wächter wird am Aufrufort opt-in eingebaut

Die mit Abstand größte Klasse. 23 geschlossene Issues benennen im Titel selbst
einen Vorgänger. Die Ketten:

- `#717` → `#719` („same IDOR as #717")
- `#927` → `#948` („write-side twin") → `#950` → `#952` („survive #947") → `#1263`
- `#997` → `#1018` („same shape as #997")
- `#993` → `#1013` („same shape as #993, longer job")
- `#901` → `#942` („three auth surfaces that #901 deliberately left out")
- `#808` → `#1090` / `#1091` / `#1092` → `#1112`
- `#706` → `#713` / `#714`
- `#1060` → `#1094` / `#1095` / `#1096`
- `#949` → `#1146` („still on indoor_default, the very case #949 fixed")

`#1353` beziffert die Klasse zum ersten Mal: 37 von 243 Mandanten-Schreibrouten
lösten den Kontext noch über ein blankes `get_current_tenant` auf. Der Sweep
dazu fand `#1399` und `#1401` beim ersten Lauf. Genau so soll es laufen, und
genau das ist der Beleg, dass Einzelreparatur die Klasse nie erreicht hat.

### K2 — Die Kontrolle existiert, kann aber nicht fehlschlagen

19 Titel beschreiben eine Prüfung, einen Wächter oder ein Gate, das strukturell
nichts leisten konnte:

- `#1153` E2E-Test behauptet einen Create und prüft nichts, blieb grün während der Server ablehnte
- `#1056` Assertion ist tautologisch
- `#802` 13 E2E-Tests nehmen einen Vorzustand auf und werten ihn nie aus
- `#986` Eingabe-Helfer meldet Erfolg gegen ein Feld, in das niemand tippen konnte
- `#814` Frontend-Pre-commit-Hooks melden Erfolg, wenn sie gar nicht laufen können
- `#1235` Freshness-Check kann nie alarmieren, Fenster am falschen Anker
- `#1302` Pin-Assertion kann auf dem PR, der den Pin ändert, nicht feuern
- `#1228` Gate verlangt einen Check, der an dieser Stelle nicht berichten kann
- `#1308` sauberer Scan und nie gelaufener Scan sind stromabwärts ununterscheidbar
- `#1042` `require_permission()` war dokumentiert als erzwungen und nirgends verdrahtet
- `#1159` NetworkPolicy lässt Port 8000 von überall zu, die Regel daneben ist damit wirkungslos
- `#786` / `#818` / `#1233` Komponente implementiert, von keiner Seite gerendert bzw. außerhalb des Wizards inert

Diese Klasse ist gefährlicher als K1, weil sie Vertrauen erzeugt.

### K3 — Der Kontrakt ist nirgends normativ, also reparieren wir Fundorte

Die UTC-Kalendertag-Kette ist der Musterfall: `#772` (ein Fundort) → `#812`
(„drei weitere Stellen, und der Kontrakt ist nirgends normativ") → `#858`
(„17 verbleibende `date.today()`-Aufrufstellen") → `#836` (die Tests kodierten
dieselbe Verwechslung). Gleiche Form bei der Validierung: `#970` benennt es
explizit als „eine Klasse, nicht zwei Endpunkte", `#968` und `#825`
(„~27 weitere Dialoge") sind die Geschwister.

### K4 — Daten außerhalb der Reichweite des Schemas

`#1152` (`substrates.yaml` ist schema-befreit und trägt unmögliche Werte),
`#1001`, `#1002`, `#1004`, `#1005` („ein weggelassenes Toxizitätsfeld liest sich
als Unbedenklichkeit, die niemand erteilt hat"), `#1008`. Jedes dieser Issues
existiert, weil eine Datei die Schema-Prüfung nicht durchlief oder das Schema
das Feld nicht kannte.

### K5 — Gemergt ist nicht ausgeliefert

`#1210` (Fix zwei Tage nach dem Merge nicht in der laufenden Instanz, kein
Release geschnitten), `#1218` (Helm-Chart-Asset fehlt seit v0.2.0 in jedem
Release), `#1222`, `#987` (Rollback-Pfad gegen eine bewegliche Referenz),
`#1025`.

## 3. Warum der Prozess diese Klassen produziert

### U1 — Nur eine Lane ist erzwungen, und die Backend-Tests sind nicht darin

Gemessen:

```
$ gh api repos/nolte/kamerplanter/branches/develop/protection \
    --jq '.required_status_checks.contexts'
["static / Static CI Tests", "lint-test-build (22)"]
```

`static` fährt pre-commit über jeden Push, ungefiltert. `lint-test-build (22)`
ist das Frontend. `Backend CI` ist pfadgefiltert und nicht erzwungen. Das
Projekt hat daraus die richtige Konsequenz gezogen und praktisch jede
Fehlerklasse in einen pre-commit-Hook übersetzt, benannt nach ihrem Issue: 20
solche Hooks stehen in `.pre-commit-config.yaml`, von `boundary-validation`
(`#970`) über `utc-calendar-day` (`#858`) bis `workflow-gate-integrity` (`#1313`).

Der neueste und wichtigste Wächter folgt dem Muster nicht. Der Sweep zu `#1353`
legte `src/backend/tests/unit/api/test_write_route_gates.py` an, 395 Zeilen, und
der Kopfkommentar begründet sorgfältig, warum er ein Test und keine
AST-Prüfung sein muss. Er liegt damit in der einzigen Lane, die nicht
erzwungen ist, und deckt die größte Fehlerklasse des Projekts ab.

Der genannte Blocker der Beförderung ist weg: `#836` wurde am 2026-07-28
geschlossen. Die Stabilität trägt heute:

| Lane | letzte 40 Läufe |
|---|---|
| `Backend CI` | 31 grün, 1 rot, 8 abgebrochen |
| `Static CI Tests` (erzwungen) | 32 grün, 2 rot, 6 abgebrochen |

### U2 — Der Reparatur-Scope ist der Fundort, nicht die Klasse

Median-Lebensdauer 0,7 Tage. Der Durchsatz ist hoch, und die Ketten in K1 sind
der Preis dafür: geschlossen wird, was im Issue steht. Kein Schritt im Prozess
verlangt, vor dem Schließen die Geschwister maschinell aufzuzählen.

### U3 — Die Fehlerklassen sind dokumentiert, aber in keinem Skill verdrahtet

Der Erfahrungsbestand unter `memory/` benennt alle fünf Klassen präzise, samt
Prüffragen. Keiner der 18 Skills unter `.claude/skills/` liest ihn oder setzt
ihn als Schritt um. `implement` kennt keinen Klassen-Sweep. `pre-pr` fährt
lokal Lint und Tests und lässt zwei Agenten laufen, prüft aber nicht, ob eine
neu hinzugekommene Schreibroute ein Gate hat, und verlangt keine
Falsifizierung. `check-test-pyramid` prüft, ob alle vier Testebenen vorhanden
sind, nicht ob ein Test fehlschlagen kann — K2 ist damit an keiner Stelle
adressiert.

## 4. Maßnahmen Prozess

**P1 — `Backend CI` als erzwungenen Check auf `develop` setzen.** Damit der
`test_write_route_gates.py`-Wächter und die 16 weiteren mechanischen Prüfungen
im Backend-Testbaum tatsächlich blockieren. Die Pfadfilter müssen dafür fallen
oder der Guard-Anteil in einen ungefilterten Job wandern, sonst berichtet der
erzwungene Check auf einem reinen Frontend-PR nicht. Messgrundlage steht oben,
die Regel dafür hat sich das Projekt in NFR-018 §4 selbst gegeben.

**P2 — Wächter-Heimat-Regel.** Ein neuer Wächter gehört in eine erzwungene
Lane. Solange P1 offen ist, heißt das pre-commit-Hook plus `scripts/check_*.py`.
Die bestehende Namenskonvention (Hook-Name trägt die Issue-Nummer) bleibt.

**P3 — Klassen-Sweep vor dem Schließen.** Ein Bugfix darf nicht schließen, bevor
die Geschwister maschinell aufgezählt sind. Konkret als Pflichtabschnitt im
PR-Body: welches Prädikat beschreibt die Klasse, wie viele Treffer hat es, wie
viele sind repariert, welcher Wächter hält den Rest. `#1353` ist die Vorlage,
inklusive des Teils, der am meisten wert ist: die Allowlist mit Begründung pro
Eintrag und der Regel, dass ein veralteter Eintrag rot wird.

**P4 — Falsifizierungspflicht.** Zu jeder Reparatur wird der alte Zustand
wiederhergestellt und Rot erwartet, und zwar auf demselben Ausdruck, den die
Regel prüft. Ohne diesen Schritt ist K2 nicht ausschließbar. Der
Erfahrungsbestand nennt drei Fälle an einem Tag, in denen ein
Falsifizierungstest eine Nachbaraussage prüfte.

**P5 — Auslieferung an den Issue-Abschluss koppeln.** Ein Issue, dessen Defekt
in der laufenden Instanz sichtbar war, schließt erst nach verifizierter
Auslieferung. `#1210` ist der Beleg für die Lücke.

## 5. Maßnahmen Skills

**S1 — `implement` um zwei Schritte erweitern.**
Nach der Implementierung: *Klassen-Sweep* (welches Muster habe ich angefasst,
welche Geschwister hat es, Aufzählung per Prädikat) und *Wächter-Registrierung*
(das Muster bekommt eine mechanische Prüfung in einer erzwungenen Lane, oder es
gibt eine begründete Allowlist). Ziel: K1 und K3.

**S2 — `check-test-pyramid` um eine Vakuitätsprüfung erweitern.**
Heute prüft der Skill Vorhandensein pro Ebene. Ergänzen: assertionsfreie Tests,
tautologische Assertions (`assert a() or b()` über komplementären Prädikaten),
aufgenommene und nie ausgewertete Vorzustände, Tests, die über einen anderen
Pfad an die Regel kommen als die Produktion. `#1056`, `#802` und `#1153` wären
damit vor dem Merge gefallen. Ziel: K2.

**S3 — `pre-pr` um drei Tore erweitern.**
Erstens Gate-Abdeckung: bringt der Diff eine neue Schreibroute, einen neuen
Admin-Endpunkt oder eine neue Frontend-Route mit, muss die zugehörige
mechanische Prüfung sie sehen. Zweitens Wächter-Heimat: fügt der Diff einen
Wächter hinzu, muss dieser in einer erzwungenen Lane liegen. Drittens
Falsifizierungsnachweis: der PR-Body nennt den wiederhergestellten alten
Zustand und das beobachtete Rot. Ziel: K1, K2, U1.

**S4 — `check-seed-data` auf Schema-Reichweite ausdehnen.**
Die Prüfung muss fehlschlagen, wenn eine Seed-Datei von keinem
`check-jsonschema`-Hook erfasst ist, und wenn ein Feld, dessen Fehlen als
Freigabe gelesen wird, optional ist. Ziel: K4, konkret `#1152` und `#1005`.

**S5 — Den Erfahrungsbestand in die Skills ziehen.**
Die fünf Klassen und ihre Prüffragen gehören als Checkliste in `implement` und
`pre-pr`, nicht nur in `memory/`. Ohne diese Verdrahtung wirkt der Bestand nur,
wenn er zufällig in den Kontext geladen wird.

**S6 — Einen Skill `check-guard-coverage` ergänzen.**
Er beantwortet eine Frage, die heute kein Skill stellt: welche Regeln des
Projekts sind mechanisch erzwungen, in welcher Lane, und welche stehen nur in
`CLAUDE.md` oder in einem NFR. `#1042` — dokumentiert als erzwungen, nirgends
verdrahtet — ist genau dieser Befund, und er wurde von Hand gefunden.

## 6. Reihenfolge

P1 und P2 zuerst: ohne erzwungene Lane wirkt kein weiterer Wächter. Dann S3,
weil `pre-pr` das letzte Tor vor dem Merge ist. Dann S1 und S2. P3 bis P5 und
S4 bis S6 danach, in beliebiger Reihenfolge.

# Umsetzungsplan zu den Maßnahmen aus dem Prozess-Review

Begleitdokument zu `development-process-review-2026-09-11.md`. Stand 2026-09-11.

!!! info "Stand der Umsetzung am 2026-09-12"
    **M1 ist umgesetzt und geschlossen** (#1404, PR #1411): die Wächter-Lane
    `Write-route and tree guards` ist ein erzwungener Check auf `develop`,
    gemessen 41 s.

    **Die Falsifizierung, und ihre eigene Geschichte.** §M1 verlangt zwei Dinge:
    der neue Check muss rot sein **und** `mergeable_state` blockiert. Der erste
    Versuch belegte nur die erste Hälfte — er lief auf einem Branch, zu dem nie
    eine Pull-Request existierte (`event: push`, `pull_requests: 0`), und eine
    frühere Fassung dieses Vermerks nannte ihn trotzdem „eine echte Wegwerf-PR".
    Nachgeholt als PR #1417: der Check meldet `failure`, `mergeStateStatus` ist
    `BLOCKED`. Beide Hälften liegen damit vor.

    **M2, M3, M4 und M7 sind ebenfalls erledigt**, in `nolte/claude-shared` und
    noch am 2026-09-11, also vor diesem Dokument im Repository:

    | Maßnahme | Commit | Artefakt |
    |---|---|---|
    | M2 + M4 | `4ef3e97` (#576) | erzwungene Lane je Testebene, `## Class sweep` in `pull-request-workflow/en.md` |
    | M3 | `bf626ff` (#578) | `spec/project/defect-class-guards/` |
    | M7 | `46bac9a` (#579) | Skill `guard-coverage-check` samt Scanner |

    Eine frühere Fassung dieses Vermerks schrieb nur, sie „liegen bei
    `claude-shared` bzw. `pre-commit-hooks`" — in einem Block über den
    Umsetzungsstand liest sich das als offen, und wer es so las, hätte vier
    fertige Maßnahmen neu eingeplant.

    **Offen bleiben M5 (#1405) und M6 (#1406).**

    **Drei Zahlen in diesem Dokument waren schon beim Schreiben falsch:**

    - **§M2 „neunzehn Monate"** — das Repository wurde am 2026-02-25 angelegt,
      also 6,5 Monate. Die Zahl überzeichnet die Begründung gegenüber dem
      Portfolio.
    - **§M6 „13 `check-jsonschema`-Hooks, jeweils eine benannte Datei"** — es sind
      zwölf mit `files:`-Muster, und eines davon ist ein Glob über neun
      `plant_info*`-Dateien, keine benannte Datei. Das Opt-in-Argument trägt
      weiterhin; die Zahl und die Nebenaussage nicht. **#1406 hat den Fehler
      übernommen.**
    - **§M5 „16 Agenten und 3 Skills"** — am Stichtag waren es 15 Agenten und
      3 Skills.

    **Zwei Dinge, die dieser Plan nicht vorhergesehen hat**, und beide gehören zur
    Maßnahme:

    - **M1 war ohne die Sweep-Erweiterung aus #1402 nicht umsetzbar.** Das
      Abnahmekriterium von #1404 kam gegen den damaligen Sweep **grün** zurück,
      weil dessen beide Prädikate auf die *Anwesenheit* einer schwachen
      Dependency prüften und eine Route ohne jede Dependency sie in der falschen
      Richtung besteht. Die Lane zuerst zu befördern hätte einen erzwungenen
      Check erzeugt, der für seinen Namensfall nicht rot werden kann — K2, erzeugt
      von der Maßnahme gegen K2.
    - **„Ein Job in `backend.yml` ohne `paths:`-Filter" ist nicht baubar.** `on:`
      gilt workflow-weit; ein Job kann die Trigger seines Workflows nicht
      aufweiten. Die Lane ist eine eigene Datei. Deren `push`-Trigger berichtet
      allerdings nicht auf Fork-PRs — vermerkt im Kopf von `backend-guards.yml`.

Der Plan verortet jede Maßnahme in dem Portfolio-Repository, das die Fähigkeit
besitzt, beschreibt die Umsetzung, und benennt für jede einen
Falsifizierungsnachweis. Ohne diesen Nachweis wäre der Plan selbst ein Beispiel
für die Fehlerklasse K2, die er beheben soll.

## 1. Verortungsprinzip

kamerplanter hat sich in `CLAUDE.md` die DRY-Regel gegeben: generische Fähigkeiten
kommen aus den Portfolio-Plugins, nur domänenspezifische Assets bleiben lokal.
Der Plan wendet dieselbe Regel auf die Maßnahmen an. Die Leitfrage pro Maßnahme
lautet: *ist die Regel eine Eigenschaft von Pflanzenbau und Mandanten, oder eine
Eigenschaft von Softwarelieferung?*

| Repository | Besitzt | Reichweite |
|---|---|---|
| `nolte/claude-shared` | Specs unter `spec/project/`, Skills und Agenten der Plugins `nolte-shared`, `nolte-engineering`, `nolte-claude-dev` | jedes Repo, das die Plugins lädt |
| `nolte/gh-plumbing` | wiederverwendbare Workflows, `commons-settings.yml`, Branch-Protection-Audit | 10 Repos konsumieren heute `reusable-pre-commit` |
| `nolte/pre-commit-hooks` | portfolio-generische Hooks, `spec/hook-authoring` | jedes Repo mit `.pre-commit-config.yaml` |
| `nolte/kamerplanter` | Domänen-Wächter (Mandant, Seed-Daten, Pflanzenphasen), Repo-eigene `settings.yml` | nur dieses Repo |

Zwei Befunde aus der Bestandsaufnahme verschieben die Verortung gegenüber dem
Review deutlich:

**Befund A.** `spec/project/test-falsifiability/` existiert bereits in
`claude-shared` und ist in 16 Agenten und 3 Skills von `nolte-engineering`
verdrahtet, inklusive einer Taxonomie nicht-falsifizierbarer Tests mit
statischen, dynamischen und Review-Kriterien. Die Fähigkeit gegen K2 ist im
Portfolio vorhanden. kamerplanter erreicht sie nicht, weil es mit den lokalen
Skills `check-test-pyramid` und `pre-pr` an den Plugin-Pendants
`nolte-engineering:test-pyramid-check` und `nolte-engineering:quality-gate`
vorbeiarbeitet. Maßnahme S2 ist damit überwiegend eine Adoptionsaufgabe, keine
Autorenaufgabe.

**Befund B.** Für die stärkste Praxis des Projekts gibt es umgekehrt gar keine
Portfolio-Fähigkeit. kamerplanter führt 20 pre-commit-Hooks und 17
`scripts/check_*.py`, jeder benannt nach dem Issue, dessen Fehlerklasse er
einsperrt. `nolte/pre-commit-hooks` führt zwei generische Hooks und kennt die
Methode nicht. Der Portfolio-Mehrwert liegt nicht in den Hooks selbst, die
domänenspezifisch sind, sondern in der Methode: *eine geschlossene Fehlerklasse
hinterlässt einen mechanischen Wächter in einer erzwungenen Lane*.

## 2. Maßnahmen im Detail

### M1 — Die Backend-Testsuite wird ein erzwungener Check

**Ist.** `develop` verlangt `static / Static CI Tests` und `lint-test-build (22)`.
Der zweite ist die Frontend-Lane. `Backend CI` ist pfadgefiltert und beratend.
Der Wächter gegen die größte Fehlerklasse des Projekts,
`src/backend/tests/unit/api/test_write_route_gates.py`, liegt darin.

**Analyse.** Die Deklaration ist die Quelle der Wahrheit: die Commons in
`gh-plumbing` liefern bewusst `contexts: []`, jedes Repo deklariert seine
eigenen Kontexte in `.github/settings.yml`. Das bestehende
`reusable-branch-protection-audit.yaml` vergleicht Deklaration gegen
Durchsetzung und ist deshalb grün, obwohl die Deklaration selbst unvollständig
ist. Es gibt im Portfolio keine Regel, die verlangt, dass eine vorhandene
Testsuite auch in einer erzwungenen Lane läuft.

Die Pfadfilterung ist der eigentliche Knoten. Ein erzwungener Check, der auf
einem reinen Frontend-PR nicht berichtet, blockiert den Merge dauerhaft. Drei
Wege stehen offen:

1. Pfadfilter aus `backend.yml` entfernen. Einfach, führt aber die volle
   Backend-Suite auf jedem Dokumentations-PR aus.
2. Das Muster von `static` kopieren: ein ungefilterter Job, der immer läuft und
   auf `push` jeder Branch triggert. `build-static-tests.yaml` begründet genau
   diese Wahl bereits im Kopfkommentar.
3. Nur den Wächteranteil in die bereits erzwungene `static`-Lane ziehen, als
   pre-commit-Hook über `scripts/check_*.py`.

Weg 3 scheidet für diesen Wächter aus, und zwar mit einer Begründung, die schon
im Kopf von `test_write_route_gates.py` steht: die Frage ist, welche Dependency
eine *montierte* Route tatsächlich auflöst, und das ist eine Eigenschaft der
zusammengebauten App, nicht einer Datei. Der dort zitierte AST-Sweep hatte
`tenant_router.py` als Dateinamen-Selektor und übersah drei Routen — dieselbe
Opt-in-Lücke eine Ebene höher. Weg 2 ist damit der richtige.

Die Stabilität trägt die Beförderung: `Backend CI` steht bei 31 grün, 1 rot, 8
abgebrochen über 40 Läufe, die bereits erzwungene `static`-Lane bei 32, 2, 6.
Der in `#836` genannte Blocker, drei Tests, die „heute" als Wanduhr-Offset
kodierten, ist seit 2026-07-28 geschlossen.

**Verortung.** Repo-spezifisch: `kamerplanter/.github/workflows/backend.yml` und
`kamerplanter/.github/settings.yml`. Die verallgemeinerbare Regel geht nach
`claude-shared`, siehe M2.

**Umsetzung.**
1. In `backend.yml` einen Job ergänzen, der die Wächtertests ohne Pfadfilter
   fährt, mit `concurrency` und `cancel-in-progress` wie in
   `build-static-tests.yaml`. Der bestehende, teure Voll-Lauf bleibt
   pfadgefiltert und beratend.
2. Den Namen des neuen Checks in `.github/settings.yml` unter `contexts`
   aufnehmen, mit Kommentar in der Form, die die Datei bereits für `#828`
   und für die ADR-011-Rücknahme führt: warum befördert, auf welcher Messung,
   und wann zurückzunehmen.
3. Erst nach dem Merge auf `develop` wirksam, weil die Probot-Settings-App vom
   Default-Branch synchronisiert. Danach verifizieren.

**QS-Nachweis.** Reihenfolge zwingend, sonst beweist der Test nichts:
```
gh api repos/nolte/kamerplanter/branches/develop/protection \
  --jq '.required_status_checks.contexts'
```
muss den neuen Kontext führen. Dann ein Wegwerf-PR, der eine Schreibroute ohne
Gate hinzufügt und **nur** Frontend-Dateien mit ändert: der neue Check muss rot
sein und `mergeable_state` blockiert. Grün auf diesem PR bedeutet, dass der
Pfadfilter noch greift.

**Risiko.** Die Merge-Train-Latenz steigt, weil `strict: true` jeden erzwungenen
Check über alle offenen PRs multipliziert. Deshalb nur der Wächteranteil, nicht
die Vollsuite. Mitigation messbar: Laufzeit des neuen Jobs vor der Beförderung
protokollieren, Schwelle bei zwei Minuten.

### M2 — Portfolio-Regel: jede Testebene braucht eine erzwungene Lane

**Analyse.** `spec/project/pull-request-workflow/` verlangt, dass erforderliche
Checks als Code in `.github/settings.yml` deklariert werden und dass die
GitHub-Oberfläche dafür nicht benutzt wird. Es verlangt nirgends, dass die
*vorhandenen* Testsuiten darunter sind. Genau diese Lücke hat kamerplanter
neunzehn Monate lang ungesehen getragen, und sie ist nicht
kamerplanter-spezifisch: 23 Portfolio-Repos haben eine Testsuite.

**Verortung.** `claude-shared`, zwei Orte.
- `spec/project/quality-gate/en.md` und `de.md`: eine Anforderung, dass jede
  Ebene, die das lokale Gate fährt, mindestens eine Lane unter den
  erforderlichen Kontexten hat, oder eine im Repo dokumentierte Ausnahme mit
  Begründung und Rücknahmebedingung.
- `plugins/nolte-engineering/agents/quality-gate-enforcer.md`: der Agent
  auditiert heute die Verdrahtung des Gates. Er bekommt die Prüfung
  „erzwungene Lane pro Ebene" als zusätzliche Dimension.

Optional und stärker: `gh-plumbing` erweitert
`reusable-branch-protection-audit.yaml` um eine Suffizienzprüfung. Sie ist
schwieriger, weil der Workflow die Testebenen eines fremden Repos erkennen muss.
Empfehlung: zuerst Spec und Agent, die Workflow-Variante erst, wenn der Agent
über mehrere Repos gelaufen ist und das Erkennungsprädikat sich bewährt hat.

**QS-Nachweis.** Den erweiterten `quality-gate-enforcer` gegen kamerplanter im
Zustand *vor* M1 laufen lassen. Er muss den Befund melden. Das ist der einzige
Nachweis, der die Regel von einer Behauptung unterscheidet. Danach gegen ein
zweites Repo mit Testsuite und ohne erzwungene Testlane laufen lassen, um zu
zeigen, dass das Prädikat nicht auf kamerplanter überangepasst ist.

### M3 — Die Methode „mechanischer Wächter" wird eine Portfolio-Fähigkeit

**Analyse.** Das ist die Maßnahme mit dem breitesten Mehrwert, weil sie eine
bewährte lokale Praxis überträgt statt eine neue zu erfinden. kamerplanters 20
Hooks belegen die Methode, und `test_write_route_gates.py` belegt ihre
schwierigste Regel: die Allowlist. Nicht jede ungegatete Schreibroute ist ein
Defekt, und der Wert des Wächters liegt darin, dass jemand aufgeschrieben hat,
welche welche ist, mit Begründung pro Eintrag und der Regel, dass ein Eintrag,
der auf keine Route mehr passt, rot wird.

Die Methode in Regeln gefasst:
1. Eine geschlossene Fehlerklasse hinterlässt einen Wächter, oder eine
   begründete Notiz, warum keiner möglich ist.
2. Der Wächter läuft in einer erzwungenen Lane.
3. Der Wächter zählt die Klasse **auf**, er prüft nicht den Fundort. Das
   Prädikat steht im Kopf der Datei, nicht im Commit.
4. Ausnahmen stehen in einer Allowlist mit Begründung pro Eintrag, und ein
   obsoleter Eintrag lässt den Wächter fehlschlagen.
5. Der Wächter trägt die Issue-Nummer im Namen, damit der Fund und die Regel
   auffindbar zusammenbleiben.
6. Der Selektor darf nicht der Dateiname sein, wenn die Eigenschaft eine
   Eigenschaft der zusammengebauten Anwendung ist.

**Verortung.** Neuer Spec `spec/project/defect-class-guards/` in `claude-shared`,
kanonisch nach dessen Sprachregel, mit Übersetzung. Verdrahtet in:
- `spec/project/test-falsifiability/` als Querverweis, weil Regel 3 und Regel 6
  dieselbe Fehlerklasse adressieren wie dessen Taxonomie, nur auf der Seite des
  Wächters statt auf der des Tests,
- `plugins/nolte-shared/skills/issue-orchestrate/` als Abschlussbedingung,
- `plugins/nolte-engineering/skills/source-code-review/` als Review-Dimension.

`nolte/pre-commit-hooks` bekommt aus kamerplanter genau die Hooks, die
domänenfrei sind. Nach Sichtung kommen dafür `workflow-gate-integrity`
(`#1313`, prüft, dass kein CI-Gate existiert, das nicht fehlschlagen kann) und
`layer-imports` in generischer Form infrage. Beide sind Kandidaten, keine
Selbstverständlichkeit: die Übernahme setzt voraus, dass der Hook ohne
kamerplanter-Pfadannahmen konfigurierbar ist. `workflow-gate-integrity` ist der
stärkste Kandidat, weil er K2 auf der CI-Seite maschinell einsperrt und jedes
Repo mit GitHub Actions betrifft.

**QS-Nachweis.** Für jeden übernommenen Hook: gegen den Stand *vor* dem
ursprünglichen Fix laufen lassen und Rot erwarten. Für
`workflow-gate-integrity` heißt das konkret, den Zustand aus `#1235` oder
`#1302` wiederherzustellen. Ein Hook, der im Ursprungs-Repo grün ist und im
neuen Repo nie rot war, ist nicht verifiziert.

### M4 — Klassen-Sweep als Abschlussbedingung

**Analyse.** 23 geschlossene Issues benennen im Titel einen Vorgänger. Die
Median-Lebensdauer von 0,7 Tagen zeigt, dass der Durchsatz nicht das Problem
ist; der Scope ist es. Kein Schritt im Prozess verlangt heute, vor dem Schließen
die Geschwister aufzuzählen.

Die Regel braucht eine Form, die nicht auf Disziplin angewiesen ist. Ein
Pflichtabschnitt im PR-Body ist diese Form, weil
`spec/project/pull-request-workflow/` bereits einen Check kennt, der die
fünf Abschnitte des Bodys erzwingt und als erforderlicher Status gemeldet wird.
Der Sweep-Abschnitt hängt sich daran an: welches Prädikat beschreibt die Klasse,
wie viele Treffer, wie viele repariert, welcher Wächter hält den Rest.

**Verortung.** `claude-shared`.
- `spec/project/pull-request-workflow/`: der Abschnitt wird für PRs vom Typ
  `fix` verlangt.
- `spec/project/issue-orchestration/`: der Sweep wird Abschlussbedingung, nicht
  nur Empfehlung.
- `plugins/nolte-shared/skills/pull-request-create/`: der Skill fragt den
  Abschnitt ab und füllt ihn.

**QS-Nachweis.** Der Body-Check muss auf einem `fix`-PR ohne den Abschnitt rot
werden. Dazu gehört die Gegenprobe: derselbe PR mit dem Abschnitt wird grün.
Nur beide Richtungen zusammen zeigen, dass der Check nicht konstant ist.

**Risiko.** Ein Pflichtabschnitt erzeugt Ritualtext, wenn er nichts erzwingt.
Deshalb muss der Abschnitt eine Zahl tragen, das Ergebnis des Prädikats, nicht
eine Prosa-Zusicherung. Eine Zahl ist überprüfbar, ein Satz nicht.

### M5 — kamerplanter adoptiert die Falsifizierbarkeits-Fähigkeit

**Analyse.** Reine Adoption, siehe Befund A. Der lokale Skill
`check-test-pyramid` prüft Vorhandensein pro Ebene und kennt
`test-falsifiability` nicht. Das Plugin-Pendant
`nolte-engineering:test-pyramid-check` referenziert es. Derselbe Schnitt trennt
den lokalen `pre-pr` von `nolte-engineering:quality-gate`.

Die DRY-Regel in `CLAUDE.md` schreibt den Ablauf vor: verifizieren, dass das
Pendant zur Laufzeit vorhanden ist, Verhaltensparität an einem echten Eingang
prüfen, erst dann das lokale Asset entfernen.

**Verortung.** `kamerplanter/.claude/skills/`. Kein Neuschreiben.

**Umsetzung.**
1. `nolte-engineering:test-pyramid-check` gegen ein Modul laufen lassen, das
   der lokale Skill schon auditiert hat, und die Berichte vergleichen.
2. Bei Parität `check-test-pyramid` entfernen und die Aufrufer umbiegen.
3. Dasselbe für `pre-pr` gegen `nolte-engineering:quality-gate`, mit der
   Einschränkung, dass `pre-pr` zusätzlich i18n-Prüfung und Security-Review
   startet. Der lokale Skill schrumpft damit auf die Orchestrierung dieser
   Zusätze, oder die Zusätze wandern in die Plugin-Kette.

**QS-Nachweis.** Die drei Issues, die die Fähigkeit hätte fangen müssen, als
Prüfeingang benutzen: `#1056` (tautologische Assertion), `#802` (aufgenommener,
nie ausgewerteter Vorzustand), `#1153` (Test behauptet einen Create und prüft
nichts). Den Stand vor dem jeweiligen Fix wiederherstellen und den adoptierten
Skill darauf ansetzen. Findet er alle drei nicht, ist die Parität nicht gegeben
und der lokale Skill bleibt, bis das Plugin nachgezogen hat.

### M6 — Seed-Daten: Schema-Reichweite statt Schema-Konformität

**Analyse.** `#1152` ist der Beleg für die eigentliche Lücke:
`substrates.yaml` war schema-befreit. Die 13 `check-jsonschema`-Hooks prüfen
jeweils eine benannte Datei, also eine Opt-in-Liste — dieselbe Form, die K1
erzeugt. Ein neues Seed-File erscheint in keiner Liste und ist damit ungeprüft.
`#1005` ist die zweite Hälfte: ein weggelassenes Toxizitätsfeld liest sich als
Unbedenklichkeit, das Schema erlaubt das Weglassen.

**Verortung.** Domänenspezifisch, bleibt in kamerplanter:
`scripts/check_seed_schema_coverage.py` plus Hook, und der lokale Skill
`check-seed-data`. Die generische Hälfte, dass eine Schema-Abdeckung
aufzählend statt opt-in sein muss, ist eine Instanz von M3 Regel 3 und braucht
keinen eigenen Portfolio-Artefakt.

**QS-Nachweis.** Eine neue Datei unter `seed_data/` anlegen, die in keiner
Hook-Liste steht. Der neue Wächter muss rot werden. Dann `substrates.yaml` in
den Zustand vor `#1152` zurücksetzen und Rot erwarten.

### M7 — Skill `check-guard-coverage`

**Analyse.** `#1042` lautete: `require_permission()` ist dokumentiert als
erzwungen und nirgends verdrahtet. Der Befund wurde von Hand gemacht. Die Frage
dahinter stellt heute kein Skill: welche Regeln behauptet das Projekt, welche
davon sind mechanisch erzwungen, in welcher Lane, und welche stehen nur in
`CLAUDE.md` oder einem NFR. Das ist K2 auf der Ebene der Projektregeln statt auf
der Ebene einzelner Tests.

**Verortung.** `claude-shared`, `plugins/nolte-engineering/`, weil die Frage in
jedem Repo mit Architekturregeln gilt. Der Skill baut auf M3: der Spec
`defect-class-guards` liefert ihm das Vokabular, was ein Wächter ist und was
eine erzwungene Lane.

**Abhängigkeit.** Nach M3. Vorher fehlt dem Skill die Definition, gegen die er
prüft.

**QS-Nachweis.** Gegen kamerplanter im Stand vor `#1042` laufen lassen. Der
Befund muss auftauchen. Zusätzlich gegen den heutigen Stand: er muss die
Aussagen in `CLAUDE.md` Abschnitt 9 und 11, die ausdrücklich zwischen
spezifiziertem und tatsächlich erzwungenem Zustand unterscheiden, als erzwungen
bestätigen und nicht fälschlich melden.

## 3. Reihenfolge

Die Abhängigkeiten erzwingen drei Wellen.

**Welle 1, Fundament.** M1 und M5. M1, weil ohne erzwungene Lane kein weiterer
Wächter wirkt und die Maßnahme allein in kamerplanter liegt. M5 parallel, weil
reine Adoption und von M1 unabhängig.

**Welle 2, Portfolio-Fähigkeiten.** M3 zuerst, weil M2 und M7 seine Definitionen
brauchen. Dann M2 und M4 parallel, beide in `claude-shared`, beide schreiben in
verschiedene Specs.

**Welle 3, Ausbreitung.** M7 nach M3. M6 jederzeit, hängt an nichts. Die
Hook-Übernahme nach `pre-commit-hooks` aus M3 zuletzt, weil sie den bewährten
Zustand der Regeln voraussetzt.

## 4. Reichweite

| Maßnahme | Repo | Profitierende Repos |
|---|---|---|
| M1 erzwungene Backend-Lane | kamerplanter | 1 |
| M2 Regel Testebene zu Lane | claude-shared | 23 mit Testsuite |
| M3 Spec Fehlerklassen-Wächter | claude-shared, pre-commit-hooks | alle Plugin-Konsumenten |
| M4 Klassen-Sweep im PR | claude-shared | alle Plugin-Konsumenten |
| M5 Falsifizierbarkeit adoptieren | kamerplanter | 1 |
| M6 Seed-Schema-Abdeckung | kamerplanter | 1 |
| M7 `check-guard-coverage` | claude-shared | alle Plugin-Konsumenten |

## 5. Die Regel, an der dieser Plan selbst zu messen ist

Jede Maßnahme oben trägt einen Falsifizierungsnachweis, und jeder dieser
Nachweise hat dieselbe Form: den Zustand vor dem Fix wiederherstellen und Rot
erwarten, auf demselben Ausdruck, den die Regel prüft. Eine Maßnahme, die
umgesetzt wird, ohne dass dieser Nachweis einmal rot war, ist nicht umgesetzt.
Sie ist die nächste Instanz von K2.

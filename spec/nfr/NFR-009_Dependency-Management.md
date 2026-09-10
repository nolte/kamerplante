---
ID: NFR-009
Titel: Dependency-Management & Aktualisierungsstrategie
Kategorie: Wartbarkeit / Sicherheit
Unterkategorie: Dependency-Lifecycle, Automatisierung, Compliance
Fokus: Beides (Zierpflanze & Nutzpflanze)
Technologie: Renovate Bot, npm, pip, Docker, Helm, GitHub Actions
Status: Genehmigt
Priorität: Hoch
Version: 1.0
Autor: Business Analyst - Agrotech
Datum: 2026-02-26
Tags: [dependency-management, renovate, security, cve, npm, pip, docker, helm, semver, license-compliance]
Abhängigkeiten: [NFR-003, NFR-008]
Betroffene Module: [ALL]
---

# NFR-009: Dependency-Management & Aktualisierungsstrategie

## Abgrenzung zu bestehenden NFRs

| NFR | Fokus | Definiert |
|---|---|---|
| NFR-003 (Abschnitt 4–6) | Linting-Tools und deren Versionen | **Werkzeugversionen & Konfiguration** |
| NFR-008 | Teststrategie, CI-Testausführung | **Wie Updates getestet werden** |
| **NFR-009 (dieses Dokument)** | Dependency-Lifecycle, Update-Automatisierung, Sicherheits-Scanning | **Wann und wie Dependencies aktualisiert werden** |

NFR-009 definiert die **übergreifende Strategie für Dependency-Management** — von der automatisierten Erkennung veralteter Pakete über die Update-Automatisierung bis hin zum Sicherheits- und Lizenz-Scanning. Die Teststrategie aus NFR-008 und die Code-Qualitätsvorgaben aus NFR-003 gelten als Voraussetzung für die Verifikation von Dependency-Updates.

---

## 1. Business Case

### 1.1 User Stories

**Als** DevOps Engineer
**möchte ich** dass Dependencies automatisch auf neue Versionen geprüft und aktualisiert werden
**um** den manuellen Wartungsaufwand zu eliminieren und Sicherheitslücken frühzeitig zu schließen.

**Als** Entwickler
**möchte ich** dass Patch- und Minor-Updates automatisch gemergt werden, wenn alle Tests grün sind
**um** mich auf Feature-Entwicklung statt Dependency-Pflege konzentrieren zu können.

**Als** Security Officer
**möchte ich** dass kritische CVEs innerhalb von 24 Stunden gepatcht werden
**um** die Angriffsfläche des Systems minimal zu halten.

**Als** Tech Lead
**möchte ich** eine dokumentierte Strategie für Major-Version-Upgrades
**um** Breaking Changes kontrolliert und planbar einzuführen.

### 1.2 Geschäftliche Motivation

**Sicherheit**:
- 84% aller Sicherheitsvorfälle in Open-Source-Projekten gehen auf bekannte, aber ungepatchte Schwachstellen zurück (Quelle: Snyk State of Open Source Security 2024)
- Das Kamerplanter-System verarbeitet Sensor- und Erntedaten — eine Kompromittierung hätte direkten geschäftlichen Schaden zur Folge

**Wartbarkeit**:
- Beim Frontend-Upgrade (Februar 2026) wurden 21 veraltete Pakete mit bis zu 2 Major-Versionen Rückstand identifiziert
- Je länger Updates aufgeschoben werden, desto aufwändiger und riskanter wird die Migration
- Regelmäßige kleine Updates sind 5–10× günstiger als seltene große Sprünge

**Compliance**:
- Open-Source-Lizenzen müssen kontinuierlich geprüft werden
- GPL- oder AGPL-lizenzierte Pakete könnten die Nutzungsbedingungen des Projekts beeinflussen

### 1.3 Fachliche Beschreibung

Praktisches Beispiel:

> **Szenario**: Die Bibliothek `python-arango` veröffentlicht Version 8.2.0 mit einem Fix für eine kritische Deserialisierungs-Schwachstelle (CVE).
> **Ohne NFR-009**: Der Entwickler bemerkt den CVE erst Wochen später bei einem manuellen `pip-audit`. Die Aktualisierung erfordert manuelle Prüfung, ob Breaking Changes vorliegen. Das Update wird auf „nächsten Sprint“ verschoben.
> **Mit NFR-009**: Renovate Bot erstellt innerhalb von Stunden einen PR mit dem Update. Die CI-Pipeline führt automatisch alle Tests aus NFR-008 durch. Bei grüner Pipeline wird der PR auto-gemergt (Minor-Update). Der CVE ist innerhalb eines Tages geschlossen.

---

## 2. Strategie & Grundsätze

### 2.1 Semantic Versioning Regeln

Das Projekt folgt den Grundsätzen des [Semantic Versioning 2.0.0](https://semver.org/):

| Update-Typ | Beispiel | Risiko | Behandlung |
|---|---|---|---|
| **Patch** (`x.y.Z`) | `1.2.3` → `1.2.4` | Niedrig — nur Bugfixes | Auto-Merge nach grüner CI |
| **Minor** (`x.Y.0`) | `1.2.3` → `1.3.0` | Mittel — neue Features, abwärtskompatibel | Auto-Merge nach grüner CI |
| **Major** (`X.0.0`) | `1.2.3` → `2.0.0` | Hoch — Breaking Changes möglich | Manuelles Review, Feature-Branch |

**MUSS**: Alle Dependencies verwenden Version-Pinning mit Kompatibilitätsbereich:
- Python (`pyproject.toml`): `>=`-Pinning mit oberer Grenze, z.B. `fastapi>=0.115.0,<1.0.0`
- Node.js (`package.json`): Caret-Notation `^`, z.B. `"react": "^19.0.0"`
- Docker: Spezifische Tags mit Minor-Version, z.B. `python:3.14-slim` (nicht `latest`)
- Helm Charts: Version-Range in `Chart.yaml`

### 2.2 Update-Frequenz

| Kategorie | Frequenz | Zeitfenster |
|---|---|---|
| **Patch-Updates** | Wöchentlich | Montag 06:00–08:00 UTC |
| **Minor-Updates** | Wöchentlich | Montag 06:00–08:00 UTC |
| **Major-Updates** | Monatlich (erster Montag) | Manuelles Review innerhalb 1 Woche |
| **Security-Fixes (Critical/High)** | Sofort | Kein Schedule — wird sofort erstellt |
| **Container-Base-Images** | Wöchentlich | Montag 06:00–08:00 UTC |
| **Helm Chart Dependencies** | Monatlich | Erster Montag des Monats |

**MUSS**: Security-relevante Updates (CVE Critical/High) dürfen nicht durch den Zeitplan verzögert werden. Renovate erstellt diese PRs sofort und unabhängig vom Zeitfenster.

### 2.3 Lockfile-Pflicht

**MUSS**: Lockfiles sind verpflichtend und werden im Repository eingecheckt:

| Ökosystem | Lockfile | Erzeugt durch |
|---|---|---|
| Node.js (Frontend) | `package-lock.json` | `npm install` |
| Python (Backend, inkl. Dev-Extra) | `uv.lock` (mit Hashes) | `uv lock` |

**MUSS**: `package-lock.json` wird bei jedem Dependency-Update mit aktualisiert.
**MUSS**: `uv.lock` wird über `uv lock` aus `pyproject.toml` generiert — manuelle Bearbeitung ist nicht erlaubt. Die Version von uv ist in `[tool.uv].required-version` verankert; Dockerfile, CI und Renovate lesen dieselbe Untergrenze.
**MUSS**: CI prüft die Integrität der Lockfiles (`npm ci` statt `npm install`; `uv lock --check` als Gate und `uv sync --locked` statt `pip install .` — `--locked` verweigert ein Lock, das `pyproject.toml` nicht mehr erfüllt, und verifiziert jedes Artefakt gegen den im Lock hinterlegten Hash).

```bash
# Python: Lockfile generieren bzw. prüfen
uv lock            # task deps:compile
uv lock --check    # task deps:check — das Gate „Lock staleness" in backend.yml
uv sync --locked --extra dev   # task deps:sync — lokale Umgebung aus dem Lock

# Node.js: Lockfile-Integrität prüfen (CI)
npm ci --ignore-scripts
```

---

## 3. Renovate Bot Konfiguration

### 3.1 Warum Renovate (vs. Dependabot)

| Kriterium | Renovate | Dependabot |
|---|---|---|
| **Gruppierung** | Flexibel — beliebige Pakete gruppierbar | Eingeschränkt — nur Ökosystem-basiert |
| **Auto-Merge** | Nativ mit Branch-Protection | Erfordert zusätzliche GitHub Actions |
| **Schedule** | Fein konfigurierbar (Cron-Syntax) | Nur daily/weekly/monthly |
| **Konfiguration** | `renovate.json5` — ausdrucksstark, vererbbar | `dependabot.yml` — limitiert |
| **Monorepo-Support** | Erstklassig (Package-Rules pro Pfad) | Grundlegend |
| **Custom Managers** | Regex-Manager für beliebige Dateien | Nicht möglich |
| **Dashboard** | Dependency-Dashboard als GitHub Issue | Nicht verfügbar |
| **Lockfile-Handling** | Automatisch (`lockFileMaintenance`) | Grundlegend |
| **Preis** | Kostenlos (Open Source & GitHub App) | Kostenlos (GitHub-integriert) |

**Entscheidung**: Renovate Bot wird eingesetzt, da die Gruppierungsfähigkeit (z.B. alle MUI-Pakete in einem PR), der fein konfigurierbare Zeitplan und der native Auto-Merge-Support für das Kamerplanter-Projekt entscheidend sind.

### 3.2 renovate.json5 Referenz-Konfiguration

```json5
// renovate.json5 — Kamerplanter Dependency-Management
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended",
    "docker:enableMajor",
    ":semanticCommits",
    ":automergePatch",
    "helpers:pinGitHubActionDigests"
  ],

  // Dependency Dashboard als GitHub Issue
  "dependencyDashboard": true,
  "dependencyDashboardTitle": "Dependency Dashboard — Kamerplanter",

  // Zeitfenster für PR-Erstellung
  "schedule": ["before 8am on monday"],
  "timezone": "Europe/Berlin",

  // Labels für PRs
  "labels": ["dependencies"],
  "prHourlyLimit": 5,
  "prConcurrentLimit": 10,

  // Branch-Präfix
  "branchPrefix": "deps/",

  // Commit-Message-Format
  "commitMessagePrefix": "deps:",
  "commitMessageAction": "update",

  // Lockfile-Wartung
  "lockFileMaintenance": {
    "enabled": true,
    "schedule": ["before 6am on monday"]
  },

  // Paket-spezifische Regeln
  "packageRules": [
    // ── Gruppierung: MUI (Frontend) ───────────────────────
    {
      "groupName": "MUI packages",
      "matchPackagePatterns": ["^@mui/"],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "mui"
    },

    // ── Gruppierung: React Ökosystem ──────────────────────
    {
      "groupName": "React packages",
      "matchPackageNames": [
        "react",
        "react-dom",
        "@types/react",
        "@types/react-dom"
      ],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "react"
    },

    // ── Gruppierung: Testing (Frontend) ───────────────────
    {
      "groupName": "Frontend testing packages",
      "matchPackagePatterns": [
        "^@testing-library/",
        "^vitest",
        "^@vitest/"
      ],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "frontend-testing"
    },

    // ── Gruppierung: ESLint Ökosystem ─────────────────────
    {
      "groupName": "ESLint packages",
      "matchPackagePatterns": [
        "^eslint",
        "^@eslint/",
        "^typescript-eslint"
      ],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "eslint"
    },

    // ── Gruppierung: i18n ─────────────────────────────────
    {
      "groupName": "i18next packages",
      "matchPackagePatterns": ["^i18next", "^react-i18next"],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "i18n"
    },

    // ── Gruppierung: Redux ────────────────────────────────
    {
      "groupName": "Redux packages",
      "matchPackageNames": [
        "@reduxjs/toolkit",
        "react-redux"
      ],
      "matchFileNames": ["src/frontend/package.json"],
      "groupSlug": "redux"
    },

    // ── Gruppierung: Pydantic (Backend) ───────────────────
    {
      "groupName": "Pydantic packages",
      "matchPackagePatterns": ["^pydantic"],
      "matchFileNames": ["src/backend/pyproject.toml"],
      "groupSlug": "pydantic"
    },

    // ── Gruppierung: Python Linting/Formatting ────────────
    {
      "groupName": "Python linting packages",
      "matchPackageNames": ["ruff", "black", "mypy"],
      "matchFileNames": ["src/backend/pyproject.toml"],
      "groupSlug": "python-linting"
    },

    // ── Gruppierung: Python Testing ───────────────────────
    {
      "groupName": "Python testing packages",
      "matchPackagePatterns": ["^pytest"],
      "matchFileNames": ["src/backend/pyproject.toml"],
      "groupSlug": "python-testing"
    },

    // ── Auto-Merge: Patch-Updates ─────────────────────────
    {
      "description": "Auto-merge patch updates after CI passes",
      "matchUpdateTypes": ["patch"],
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash"
    },

    // ── Auto-Merge: Minor-Updates (non-major frameworks) ──
    {
      "description": "Auto-merge minor updates for non-critical packages",
      "matchUpdateTypes": ["minor"],
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash",
      "excludePackagePatterns": [
        "^react$",
        "^react-dom$",
        "^fastapi$",
        "^typescript$",
        "^@mui/material$"
      ]
    },

    // ── Kein Auto-Merge: Major-Updates ────────────────────
    {
      "description": "Major updates require manual review",
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "labels": ["dependencies", "major-update"],
      "reviewers": ["team:kamerplanter-maintainers"]
    },

    // ── Kein Auto-Merge: Kern-Frameworks (auch Minor) ─────
    {
      "description": "Core frameworks require manual review even for minor",
      "matchPackageNames": [
        "react",
        "react-dom",
        "fastapi",
        "typescript"
      ],
      "matchUpdateTypes": ["minor", "major"],
      "automerge": false,
      "labels": ["dependencies", "core-framework"],
      "reviewers": ["team:kamerplanter-maintainers"]
    },

    // ── Security: Sofortige PRs für CVEs ──────────────────
    {
      "description": "Security updates bypass schedule",
      "matchCategories": ["security"],
      "schedule": ["at any time"],
      "automerge": true,
      "automergeType": "pr",
      "automergeStrategy": "squash",
      "prPriority": 10,
      "labels": ["dependencies", "security"]
    },

    // ── Container-Images ──────────────────────────────────
    {
      "groupName": "Container base images",
      "matchDatasources": ["docker"],
      "matchFileNames": [
        "src/backend/Dockerfile*",
        "src/frontend/Dockerfile*"
      ],
      "groupSlug": "docker-images",
      "schedule": ["before 8am on monday"]
    },

    // ── GitHub Actions ────────────────────────────────────
    {
      "groupName": "GitHub Actions",
      "matchManagers": ["github-actions"],
      "groupSlug": "github-actions",
      "automerge": true
    },

    // ── Helm Charts ───────────────────────────────────────
    {
      "groupName": "Helm chart dependencies",
      "matchManagers": ["helmv3"],
      "matchFileNames": ["helm/**/Chart.yaml"],
      "groupSlug": "helm-charts",
      "schedule": ["before 8am on the first day of the month"]
    }
  ]
}
```

### 3.3 Gruppierungsregeln

**MUSS**: Zusammengehörige Pakete werden in einem PR gruppiert, um atomare Updates zu gewährleisten:

| Gruppe | Pakete | Begründung |
|---|---|---|
| **MUI** | `@mui/material`, `@mui/icons-material`, `@mui/x-date-pickers` | Gemeinsames Design-System, Versionen müssen kompatibel sein |
| **React** | `react`, `react-dom`, `@types/react`, `@types/react-dom` | React-Kern — separate Updates können Type-Fehler verursachen |
| **Redux** | `@reduxjs/toolkit`, `react-redux` | Eng gekoppelt, gemeinsame Breaking Changes |
| **i18n** | `i18next`, `react-i18next`, `i18next-browser-languagedetector` | Plugin-Kompatibilität erfordert gemeinsames Update |
| **ESLint** | `eslint`, `@eslint/js`, `typescript-eslint`, `eslint-*` | Config-Kompatibilität zwischen Plugins |
| **Frontend Testing** | `vitest`, `@vitest/*`, `@testing-library/*` | Test-Runner und Assertions müssen zusammenpassen |
| **Pydantic** | `pydantic`, `pydantic-settings` | Gemeinsames Typsystem, Schema-Kompatibilität |
| **Python Linting** | `ruff`, `black`, `mypy` | Formatting-Konsistenz |
| **Python Testing** | `pytest`, `pytest-asyncio`, `pytest-cov` | Test-Runner-Ökosystem |
| **Container Images** | `python:*`, `node:*`, `nginx:*` | Dockerfile-Base-Images |
| **GitHub Actions** | `actions/*`, `docker/*` | CI-Workflow-Stabilität |
| **Helm Charts** | Alle `Chart.yaml`-Dependencies | Deployment-Konsistenz |

### 3.4 Auto-Merge-Regeln

```
┌─────────────────────────────────────────────────────────────────┐
│                    Update-Typ empfangen                         │
└─────────────────┬───────────────────────────────────────────────┘
                  │
          ┌───────▼───────┐
          │  Security?    │──── Ja ──→ Sofort PR → CI → Auto-Merge
          └───────┬───────┘
                  │ Nein
          ┌───────▼───────┐
          │   Patch?      │──── Ja ──→ Scheduled PR → CI → Auto-Merge
          └───────┬───────┘
                  │ Nein
          ┌───────▼───────┐
          │   Minor?      │──── Ja ──→ Kern-Framework? ──→ Manuelles Review
          └───────┬───────┘              │ Nein
                  │ Nein                 └──→ CI → Auto-Merge
          ┌───────▼───────┐
          │   Major?      │──── Ja ──→ Manuelles Review (Feature-Branch)
          └───────────────┘
```

**MUSS**: Auto-Merge erfordert:
1. Alle CI-Jobs grün (Tests, Lint, Build)
2. Branch-Protection-Rules aktiv auf `main`
3. Mindestens 1 erfolgreiche CI-Run

**MUSS**: Auto-Merge ist deaktiviert für:
- Major-Updates jeglicher Pakete
- Minor-Updates von Kern-Frameworks (`react`, `react-dom`, `fastapi`, `typescript`)

### 3.5 Schedule & Rate Limiting

**MUSS**: Renovate erstellt PRs nur im definierten Zeitfenster (Ausnahme: Security-Fixes).
**MUSS**: Maximal 5 PRs pro Stunde und 10 gleichzeitig offene Dependency-PRs.

| Parameter | Wert | Begründung |
|---|---|---|
| `schedule` | `before 8am on monday` | PRs stehen zum Wochenbeginn bereit |
| `timezone` | `Europe/Berlin` | Standort des Entwicklungsteams |
| `prHourlyLimit` | 5 | CI nicht überlasten |
| `prConcurrentLimit` | 10 | Übersichtlichkeit wahren |
| `lockFileMaintenance` | Montag vor 06:00 | Lockfiles aktuell halten |

---

## 4. Sicherheitsaspekte

### 4.1 CVE-Scanning

**MUSS**: Jeder Dependency-PR und jeder Push auf `develop` löst automatisches Vulnerability-Scanning aus:

| Werkzeug | Ökosystem | Integration |
|---|---|---|
| `npm audit` (via `scripts/security/npm_audit_gate.py`) | Node.js (Frontend) | `frontend.yml`, Jobs `npm-audit` (ausgeliefert, pro PR) und `npm-audit-dev` (wöchentlich) |
| `pip-audit` | Python (Backend) | `backend.yml`, Job `pip-audit` (ausgeliefert pro PR, dev wöchentlich) |
| **GitHub Security Advisories** | Alle | Automatisch (GitHub Dependabot Alerts) |
| **Renovate vulnerabilityAlerts** | Alle | Renovate-Bot-Konfiguration |

!!! warning "Diese Anforderung war über lange Zeit nur zur Hälfte umgesetzt"

    Die Frontend-Zeile dieser Tabelle stand hier, ohne dass ein `npm audit`
    irgendwo lief. Trivy erreichte `package-lock.json` nur auf Stufe
    `CRITICAL`, also war eine **High**-Severity-Advisory in ausgeliefertem
    JavaScript für jedes Gate im Repository unsichtbar — und eine lag vor
    (GHSA-qwww-vcr4-c8h2 in `react-router`, gefunden erst beim CI/CD-Audit am
    2026-08-01). Der Befund war damit kein fehlendes Requirement, sondern
    Drift zwischen Spec und Implementierung. Siehe NFR-018 §1 für die
    Fehlerklasse und §6 für die daraus abgeleiteten Regeln.

**MUSS**: Eine bewusst akzeptierte Advisory wird als Eintrag in
`tests/security/npm-audit-allowlist.yaml` geführt — mit **Begründung und
Ablaufdatum**, nie durch Absenken der Schwelle. Die Begründung MUSS einen
Mechanismus nennen, warum der verwundbare Codepfad in dieser Anwendung nicht
existiert. Das Ablaufdatum ist verpflichtend: Ein Eintrag, der nie verfällt, ist
keine Entscheidung mehr, sondern Inventar. Details in NFR-018 §6.

**MUSS**: CI-Job für Sicherheits-Scanning:

```yaml
# .github/workflows/security-audit.yml
name: Security Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: "0 6 * * 1"  # Montags 06:00 UTC

jobs:
  npm-audit:
    name: npm audit (Frontend)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: "src/frontend/.tool-versions"
      - run: npm ci --ignore-scripts
      - run: npm audit --audit-level=high

  pip-audit:
    name: pip-audit (Backend)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - run: pip install pip-audit
      - run: pip install -r requirements.txt
      - run: pip-audit --strict --desc
```

### 4.2 Kritische Sicherheitsupdates — SLA

| Schweregrad (CVSS) | SLA | Verantwortlich | Eskalation |
|---|---|---|---|
| **Critical** (9.0–10.0) | 24 Stunden | DevOps / Maintainer | Direkte Benachrichtigung |
| **High** (7.0–8.9) | 7 Tage | Entwickler via PR-Review | Dependency Dashboard |
| **Medium** (4.0–6.9) | 30 Tage | Nächster Sprint | Backlog |
| **Low** (0.1–3.9) | 90 Tage | Reguläres Update-Fenster | — |

**MUSS**: Critical-CVEs werden außerhalb des regulären Schedules behandelt — Renovate erstellt sofort einen PR.
**MUSS**: GitHub Security Advisories sind aktiviert und senden Benachrichtigungen an das Maintainer-Team.
**SOLL**: Bei Critical-CVEs wird ein Hotfix-Branch erstellt, wenn der reguläre PR nicht innerhalb von 8 Stunden gemergt werden kann.

### 4.3 License Compliance

**MUSS**: Nur Pakete mit folgenden Lizenzen werden akzeptiert:

| Lizenz | Status | Begründung |
|---|---|---|
| MIT | Erlaubt | Permissiv, keine Einschränkungen |
| Apache-2.0 | Erlaubt | Permissiv, Patent-Grant |
| BSD-2-Clause | Erlaubt | Permissiv |
| BSD-3-Clause | Erlaubt | Permissiv |
| ISC | Erlaubt | Permissiv (npm-Standard) |
| 0BSD | Erlaubt | Public-Domain-äquivalent |
| CC0-1.0 | Erlaubt | Public Domain |

**MUSS**: Folgende Lizenzen sind ausgeschlossen:

| Lizenz | Status | Begründung |
|---|---|---|
| GPL-2.0 / GPL-3.0 | Verboten | Copyleft — erzwingt Open-Source-Veröffentlichung |
| AGPL-3.0 | Verboten | Netzwerk-Copyleft — auch Server-Nutzung betroffen |
| SSPL | Verboten | Server-Side Public License — restriktiv |
| Unlicensed / UNLICENSED | Verboten | Kein Nutzungsrecht ohne Lizenz |

**MUSS**: Lizenz-Prüfung in der CI-Pipeline:

```bash
# Frontend: Lizenz-Check (frontend.yml, Job `npm-licenses`)
npx --yes license-checker-rseidelsohn@4.4.2 --production \
  --excludePackages 'kamerplanter-frontend@0.1.0' \
  --onlyAllow 'MIT;ISC;BSD-3-Clause;BSD-2-Clause;Apache-2.0;0BSD;CC0-1.0;Unlicense;MIT AND ISC'

# Backend: Lizenz-Check (backend.yml, Job `pip-licenses`)
pip-licenses --from=mixed --allow-only='…'   # vollständige Liste im Workflow
```

Beide Gates arbeiten mit einer **Allowlist**, nicht mit einer Blockliste: Eine
neue Abhängigkeit unter einer unbekannten Lizenz — auch einer harmlosen — fällt
auf und wird geprüft, statt durchzurutschen, weil sie zufällig auf keiner
Verbotsliste steht. Das Ausschließen des Workspace-Pakets selbst ist nötig, weil
es als `private` markiert ist und der Scanner es deshalb als `UNLICENSED`
meldet, obwohl `package.json` MIT deklariert.

**SOLL**: Neue Dependencies mit unbekannter oder fehlender Lizenz müssen manuell geprüft und freigegeben werden.

---

## 5. CI/CD-Integration

### 5.1 Automatische Tests bei Dependency-PRs

**MUSS**: Jeder von Renovate erstellte PR durchläuft die vollständige CI-Pipeline:

```yaml
# .github/workflows/ci.yml (relevanter Auszug)
on:
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    name: Backend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - run: pip install -r requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy app/
      - run: pytest tests/ -v --cov=app --cov-report=xml

  frontend-tests:
    name: Frontend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: "src/frontend/.tool-versions"
      - run: npm ci --ignore-scripts
      - run: npm run lint
      - run: npx tsc --noEmit
      - run: npm run test
      - run: npm run build
```

### 5.2 Build-Verifikation

**MUSS**: Dependency-PRs müssen zusätzlich zur Testsuite einen vollständigen Build durchlaufen:

| Artefakt | Befehl | Prüft |
|---|---|---|
| Frontend-Bundle | `npm run build` | Vite-Build, Tree-Shaking, TypeScript-Kompilierung |
| Backend-Package | `pip install -r requirements.txt && pip install --no-deps .` | Lock-Installierbarkeit, Import-Prüfung |
| Docker-Images | `docker build .` | Base-Image-Kompatibilität, Multi-Stage-Build |
| Helm Chart | `helm lint helm/` | Chart-Validität, Values-Schema |

**SOLL**: Build-Artefakte werden auf signifikante Größenänderungen (>20%) geprüft — ein plötzliches Wachstum kann auf Dependency-Tree-Probleme hinweisen.

### 5.3 Breaking-Change-Detection

**MUSS**: Bei Minor- und Major-Updates prüft die CI-Pipeline auf Breaking Changes:

1. **TypeScript**: `npx tsc --noEmit` — Typ-Fehler nach Update erkennen
2. **Python**: `mypy app/` — Typ-Kompatibilität prüfen
3. **Runtime**: Vollständige Testsuite (Unit + Integration + API) gemäß NFR-008
4. **Bundle-Size**: Vergleich der Frontend-Bundle-Größe vor/nach Update

**SOLL**: Bei Major-Updates wird zusätzlich ein manueller Smoke-Test auf dem Staging-System durchgeführt (vgl. NFR-007 Abschnitt 6).

---

## 6. Sprachspezifische Regeln

### 6.1 Python (Backend)

**Werkzeuge**:

| Werkzeug | Zweck | Konfiguration |
|---|---|---|
| `uv` (`uv lock`, `uv sync --locked`) | Lockfile-Generierung aus `pyproject.toml` und hash-verifizierte Installation | `uv.lock`, `[tool.uv]` in `pyproject.toml` |
| `pip-audit` | CVE-Scanning (liest `uv export --format requirements.txt`) | CI-Pipeline |
| `pip-licenses` | Lizenz-Prüfung | CI-Pipeline |

**MUSS**: `pyproject.toml` enthält Dependencies mit `>=`-Pinning:

```toml
# pyproject.toml (aktueller Stand)
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "python-arango>=8.1.0",
    "redis>=5.2.0",
    "celery>=5.4.0",
    "structlog>=24.4.0",
    "httpx>=0.28.0",
]
```

**MUSS**: Renovate aktualisiert `pyproject.toml` und regeneriert `uv.lock` in derselben Pull Request. Der eingebaute `pep621`-Manager erkennt `uv.lock` neben `pyproject.toml` und führt `uv lock --upgrade-package` aus; Updates innerhalb einer Range (`>=x,<y`) erreichen das Lock über `rangeStrategy: update-lockfile`, ohne die Range zu verändern. Kein anderer Manager (`poetry`, `pip_requirements`, `pip-compile`) darf dieselbe Datei lesen:

```json5
// renovate.json5 — Python-spezifisch (in packageRules)
{
  matchManagers: ['poetry', 'pip_requirements', 'pip-compile'],
  matchFileNames: ['src/backend/**'],
  enabled: false,
},
{
  matchManagers: ['pep621'],
  matchFileNames: ['src/backend/**'],
  rangeStrategy: 'update-lockfile',
}
```

> **Warum uv und nicht mehr pip-tools (2026-09-10):** Renovates `pip-compile`-Manager akzeptiert nur eine feste Liste von Header-Optionen; die hier nötigen `--no-strip-extras` und `--no-build-isolation` gehörten nicht dazu, sodass der Manager ab 2026-08-02 still nichts extrahierte und die Locks sechs Wochen nicht regeneriert wurden. Zudem ließ sich die Toolchain des Renovate-Sidecars (pip, click) nicht auf die Versionen festhalten, die pip-tools überlebte. uv ist eine statische Binary mit einer Version, die alle drei Konsumenten (Dockerfile, CI, Renovate) aus `[tool.uv].required-version` lesen.

**MUSS**: Kompatibilität mit Ruff und mypy wird durch CI sichergestellt (vgl. NFR-003). Ein Dependency-Update, das Ruff- oder mypy-Fehler verursacht, kann nicht auto-gemergt werden.

### 6.2 Node.js (Frontend)

**Werkzeuge**:

| Werkzeug | Zweck | Konfiguration |
|---|---|---|
| `npm` | Paketmanager, Lockfile | `package-lock.json` |
| `npm audit` | CVE-Scanning | CI-Pipeline |
| `license-checker` | Lizenz-Prüfung | CI-Pipeline |

**MUSS**: `package.json` verwendet Caret-Notation (`^`) für Dependencies:

```json
{
  "dependencies": {
    "@mui/material": "^7.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "axios": "^1.9.0"
  }
}
```

**MUSS**: Renovate aktualisiert `package.json` und führt automatisch `npm install` aus, um `package-lock.json` zu aktualisieren.
**MUSS**: CI verwendet `npm ci` (nicht `npm install`), um Lockfile-Integrität zu gewährleisten.
**MUSS**: ESLint-Kompatibilität wird durch CI sichergestellt — ein Update, das Lint-Fehler verursacht, kann nicht auto-gemergt werden.

### 6.3 Container-Images

**MUSS**: Dockerfile-Base-Images verwenden spezifische Minor-Version-Tags:

```dockerfile
# Backend
FROM python:3.14-slim AS base

# Frontend Build
FROM node:22-alpine AS build

# Frontend Serve
FROM nginx:1.27-alpine AS serve
```

**MUSS**: Renovate erkennt und aktualisiert Base-Image-Tags in Dockerfiles.
**MUSS**: Base-Image-Updates durchlaufen den vollständigen Docker-Build in der CI.
**SOLL**: Alpine-basierte Images werden bevorzugt, um die Angriffsfläche zu minimieren.

### 6.4 Helm Charts

**MUSS**: Helm-Chart-Dependencies in `Chart.yaml` werden von Renovate verwaltet:

```yaml
# helm/kamerplanter/Chart.yaml (Beispiel)
apiVersion: v2
name: kamerplanter
version: 0.1.0
dependencies:
  - name: arangodb
    version: "~1.2.0"
    repository: "https://arangodb.github.io/kube-arangodb"
  - name: redis
    version: "~18.0.0"
    repository: "https://charts.bitnami.com/bitnami"
```

**MUSS**: Helm-Chart-Updates werden monatlich geprüft (niedrigere Frequenz wegen Deployment-Risiko).
**MUSS**: Helm-Chart-Updates erfordern immer manuelles Review — kein Auto-Merge.

---

## 7. Major-Version-Upgrade-Prozess

### 7.1 Bewertungscheckliste

Vor jedem Major-Upgrade **MUSS** folgende Checkliste abgearbeitet werden:

| # | Prüfpunkt | Aktion | Status |
|---|---|---|---|
| 1 | **Changelog lesen** | Release Notes und Migration Guide der neuen Version lesen | ☐ |
| 2 | **Breaking Changes identifizieren** | Alle Breaking Changes auflisten, die das Projekt betreffen | ☐ |
| 3 | **Ecosystem-Readiness prüfen** | Sind abhängige Plugins/Erweiterungen kompatibel? (z.B. MUI-Icons bei MUI-Update) | ☐ |
| 4 | **Type-Änderungen prüfen** | TypeScript- bzw. Python-Type-Änderungen identifizieren | ☐ |
| 5 | **Deprecation Warnings beheben** | Alle Deprecation Warnings der aktuellen Version vor dem Upgrade beheben | ☐ |
| 6 | **Aufwand schätzen** | Story Points / Zeitaufwand für Migration abschätzen | ☐ |
| 7 | **Sprint-Planung** | Major-Upgrade in Sprint einplanen (nicht nebenbei) | ☐ |
| 8 | **Rollback-Plan definieren** | Strategie für Rollback dokumentieren (vgl. 7.3) | ☐ |

### 7.2 Feature-Branch-Strategie

**MUSS**: Major-Updates werden auf einem dedizierten Feature-Branch durchgeführt:

```
main ─────────────────────────────────────────── main
  │                                               ▲
  └── deps/major-react-20 ──── Commits ──── PR ──┘
       │
       ├── deps: update react to v20
       ├── fix: adapt components to new API
       ├── fix: update type definitions
       └── test: verify all tests pass
```

**MUSS**: Der Feature-Branch wird regelmäßig mit `main` synchronisiert (Rebase oder Merge).
**MUSS**: Mindestens ein Maintainer muss den PR reviewen und freigeben.
**SOLL**: Große Major-Updates (z.B. React 19 → 20) werden in einer separaten Spike-Story vorab evaluiert.

### 7.3 Rollback-Plan

**MUSS**: Für jedes Major-Update existiert ein dokumentierter Rollback-Plan:

1. **Git Revert**: PR-Merge rückgängig machen via `git revert`
2. **Lockfile wiederherstellen**: `package-lock.json` / `requirements.txt` auf vorherigen Stand zurücksetzen
3. **CI-Verifikation**: Vollständige Pipeline nach Rollback ausführen
4. **Deployment**: Rollback auf vorheriges Container-Image (vgl. NFR-007)

**MUSS**: Vor dem Merge eines Major-Updates wird sichergestellt, dass der aktuelle Stand von `main` als Git-Tag markiert ist:

```bash
# Vor Major-Update-Merge
git tag -a pre-react-20 -m "State before React 20 upgrade"
git push origin pre-react-20
```

---

## 8. Monitoring & Reporting

### 8.1 Dependency-Alter-Dashboard

**MUSS**: Renovate Dependency Dashboard ist als GitHub Issue aktiviert und zeigt:
- Offene Dependency-PRs mit Status
- Ausstehende Major-Updates (warten auf Freigabe)
- Ignorierte oder zurückgestellte Updates mit Begründung

**SOLL**: Monatliches Review des Dependency Dashboards im Team-Meeting.

### 8.2 Vulnerability-Report

**MUSS**: GitHub Security Advisories sind aktiviert für das Repository.
**MUSS**: Wöchentlicher automatischer Security-Audit in der CI-Pipeline (vgl. Abschnitt 4.1).

**SOLL**: Monatlicher Vulnerability-Report mit folgenden Kennzahlen:

| Metrik | Zielwert |
|---|---|
| Offene Critical/High-CVEs | 0 |
| Durchschnittliche Time-to-Patch (Critical) | < 24h |
| Durchschnittliche Time-to-Patch (High) | < 7 Tage |
| Dependencies mit bekannten Vulnerabilities | 0 |

### 8.3 Compliance-Übersicht

**SOLL**: Quartalsweise Übersicht über den Lizenz-Status aller Dependencies:

```bash
# Frontend: Lizenz-Report generieren
npx license-checker --production --csv > license-report-frontend.csv

# Backend: Lizenz-Report generieren
pip-licenses --format=csv --output-file=license-report-backend.csv
```

**SOLL**: Bei jedem neuen Paket wird die Lizenz vor dem Merge geprüft und dokumentiert.

---

## 9. Akzeptanzkriterien

### Definition of Done

- [ ] **Renovate Bot**
    - [ ] Renovate Bot ist als GitHub App installiert und für das Repository aktiviert
    - [ ] `renovate.json5` ist im Repository-Root eingecheckt und valide
    - [ ] Dependency Dashboard ist als GitHub Issue sichtbar
- [ ] **Auto-Merge**
    - [ ] Patch-Updates werden nach grüner CI automatisch gemergt
    - [ ] Minor-Updates (nicht Kern-Frameworks) werden nach grüner CI automatisch gemergt
    - [ ] Major-Updates erfordern manuelles Review
    - [ ] Kern-Frameworks (`react`, `fastapi`, `typescript`) erfordern immer manuelles Review
- [ ] **CI-Integration**
    - [ ] Alle Dependency-PRs durchlaufen die vollständige CI-Pipeline (Tests, Lint, Build)
    - [ ] `npm audit` und `pip-audit` sind in der CI-Pipeline integriert
    - [ ] Lizenz-Prüfung ist in der CI-Pipeline integriert
    - [ ] Wöchentlicher Security-Audit-Job ist konfiguriert
- [ ] **CVE-Scanning**
    - [ ] GitHub Security Advisories sind aktiviert
    - [ ] Critical-CVEs werden innerhalb von 24 Stunden adressiert
    - [ ] High-CVEs werden innerhalb von 7 Tagen adressiert
- [ ] **Lockfiles**
    - [ ] `package-lock.json` wird bei jedem Frontend-Update aktualisiert
    - [ ] `uv.lock` wird via `uv lock` generiert
    - [ ] CI verwendet `npm ci` und `uv sync --locked`
- [ ] **Major-Upgrade-Prozess**
    - [ ] Bewertungscheckliste ist dokumentiert und wird angewendet
    - [ ] Feature-Branch-Strategie ist definiert
    - [ ] Rollback-Plan ist dokumentiert
- [ ] **Dokumentation**
    - [ ] Gruppierungsregeln sind vollständig definiert
    - [ ] Update-Frequenzen und Zeitfenster sind festgelegt
    - [ ] Erlaubte und verbotene Lizenzen sind gelistet
    - [ ] SLAs für Sicherheitsupdates sind definiert

---

## 10. Abhängigkeiten

### 10.1 Technische Abhängigkeiten

| Abhängigkeit | Typ | Beschreibung |
|---|---|---|
| **NFR-003** (Code-Standard & Linting) | Voraussetzung | Ruff, mypy, ESLint müssen in CI grün sein, bevor ein Dependency-PR gemergt wird |
| **NFR-008** (Teststrategie) | Voraussetzung | Vollständige Testsuite (Unit, Integration, API) muss bei Dependency-PRs durchlaufen |
| **NFR-007** (Betriebsstabilität) | Ergänzung | Rollback-Strategie für fehlgeschlagene Updates im Deployment |
| **GitHub Actions CI** | Infrastruktur | CI-Pipeline muss konfiguriert sein, bevor Auto-Merge aktiviert werden kann |

### 10.2 Externe Abhängigkeiten

| Abhängigkeit | Typ | Risiko | Mitigation |
|---|---|---|---|
| **GitHub** | Plattform | Vendor Lock-In für PR-Workflow | Renovate auch self-hosted möglich |
| **Renovate Bot** (Mend) | SaaS / GitHub App | Dienst-Ausfall → keine automatischen PRs | Self-hosted Renovate als Fallback |
| **npm Registry** | Paket-Registry | Registry-Ausfall → keine Frontend-Updates | `npm ci` mit Cache, Lockfile als Fallback |
| **PyPI** | Paket-Registry | Registry-Ausfall → keine Backend-Updates | `uv sync --locked` mit Cache |
| **GitHub Advisory Database** | Vulnerability-Daten | Unvollständige CVE-Abdeckung | Ergänzend `npm audit` und `pip-audit` |

---

## 11. Risiken bei Nicht-Einhaltung

| Risiko | Auswirkung | Wahrscheinlichkeit | Mitigation |
|---|---|---|---|
| **Sicherheitslücken durch veraltete Dependencies** | Kompromittierung des Systems, Datenverlust, Reputationsschaden | Hoch | Automatisches CVE-Scanning, SLA-basierte Patching-Zeiten |
| **Breaking Changes bei verspäteten Major-Updates** | Aufwändige Migration, Feature-Freeze während Upgrade, instabile Zwischenzustände | Hoch | Regelmäßige Minor-Updates verhindern Rückstände, dokumentierter Major-Upgrade-Prozess |
| **License-Compliance-Verstöße** | Rechtliche Konsequenzen bei Verwendung von Copyleft-Lizenzen in proprietärem Kontext | Mittel | Automatische Lizenz-Prüfung in CI, Allowlist erlaubter Lizenzen |
| **Dependency-Konflikte durch fehlende Gruppierung** | Inkompatible Paketversionen (z.B. MUI-Komponenten mit unterschiedlichen Versionen) | Mittel | Renovate-Gruppierungsregeln stellen atomare Updates sicher |
| **CI-Überlastung durch zu viele Dependency-PRs** | Lange Wartezeiten für Feature-PRs, erhöhte GitHub Actions-Kosten | Niedrig | Rate Limiting (5/Stunde, 10 gleichzeitig), wöchentliches Schedule |
| **Lockfile-Drift zwischen Entwicklern** | „Works on my machine“-Probleme, nicht reproduzierbare Builds | Mittel | Lockfile-Pflicht, `npm ci` in CI, `uv lock --check` für Python |

---

**Dokumenten-Ende**

**Version**: 1.0
**Status**: Genehmigt
**Letzte Aktualisierung**: 2026-02-26
**Review**: Genehmigt
**Genehmigung**: Genehmigt (2026-06-11)

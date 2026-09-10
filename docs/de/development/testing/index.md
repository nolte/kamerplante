# Testen

Kamerplanter verfügt über eine umfangreiche Testsuite für Backend und Frontend. Alle Tests müssen grün sein, bevor ein Pull Request gemergt wird.

**Aktueller Stand:** 821 Backend-Tests (pytest), 198 Frontend-Tests (vitest) — alle grün.

---

## Testkonzept

Kamerplanter testet auf mehreren **Teststufen** — von schnellen, isolierten Unit-Tests bis zu vollständigen End-to-End-Durchläufen im echten Browser. Die Stufen bilden eine klassische Testpyramide: viele schnelle Tests an der Basis, wenige langsame an der Spitze.

!!! tip "Teststufen im Detail"
    Diese Seite bündelt das praktische Testkonzept entlang der **Werkzeuge** (pytest, vitest, Selenium): Voraussetzungen, Ausführung, Teststruktur und Konventionen. Eine konzeptionelle Übersicht entlang der **Teststufen** (Unit → Integration → Component → E2E) findest du unter [Teststufen](stufen/index.md).

---

## Backend-Tests (pytest)

### Voraussetzungen

```bash
cd src/backend
uv sync --locked --extra dev      # oder: task deps:sync
source .venv/bin/activate
```

Das installiert exakt die in `uv.lock` festgehaltenen Produktions- und Entwicklungsabhängigkeiten (hash-verifiziert), einschließlich pytest, pytest-asyncio und pytest-cov. uv installieren: <https://docs.astral.sh/uv/>.

### Tests ausführen

```bash
# Alle Tests
pytest

# Mit ausführlicher Ausgabe
pytest -v

# Einzelne Testdatei
pytest tests/test_onboarding_engine.py -v

# Einzelnen Test
pytest tests/test_onboarding_engine.py::TestValidateKitApplication::test_valid_application -v

# Tests nach Namenspattern filtern
pytest -k "substrate" -v
```

### Teststruktur

```
src/backend/tests/
├── conftest.py                        # Gemeinsame Fixtures (Species, Site, Substrate, ...)
├── unit/                              # Einheitentests ohne externe Abhängigkeiten
│   ├── domain/
│   │   └── test_calculations.py      # VPD, GDD, EC-Berechnungen
│   └── adapters/
│       └── test_enrichment.py        # GBIF/Perenual Adapter-Logik
├── api/                               # API-Schicht-Tests
│   └── test_error_handling.py
├── integration/                       # Integrationstests (erfordern ArangoDB)
│   └── test_arango_integration.py
├── test_care_reminder_engine.py       # Engine-Tests (direkte Klassen-Instantiierung)
├── test_onboarding_engine.py
├── test_substrate_lifecycle_manager.py
└── test_*.py                          # Weitere Engine-/Service-Tests
```

### pytest-asyncio Konfiguration

pytest-asyncio ist mit `asyncio_mode = "auto"` konfiguriert. Asynchrone Testfunktionen benötigen kein explizites `@pytest.mark.asyncio`-Dekorator:

```python
# Funktioniert ohne explizites Dekorator
async def test_service_creates_species():
    service = SpeciesService(mock_repo)
    result = await service.create(sample_data)
    assert result.scientific_name == "Solanum lycopersicum"
```

### Fixtures (conftest.py)

Die zentrale `conftest.py` stellt typische Datensätze als Fixtures bereit:

```python
def test_substrate_lifecycle(sample_substrate_data):
    substrate = Substrate(**sample_substrate_data)
    manager = SubstrateLifecycleManager()
    result = manager.prepare_for_reuse(substrate)
    assert result.reuse_cycle == 1
```

Verfügbare Fixtures: `sample_species_data`, `sample_site_data`, `sample_location_data`, `sample_substrate_data`.

### Integrationstests

Integrationstests unter `tests/integration/` erfordern eine laufende ArangoDB-Instanz. Sie werden automatisch übersprungen, wenn keine Verbindung besteht:

```python
@pytest.mark.skipif(not ARANGO_AVAILABLE, reason="ArangoDB not available")
class TestArangoSetup:
    ...
```

Um sie gezielt auszuführen:

```bash
# ArangoDB starten (z. B. via Docker Compose)
docker-compose up -d arangodb

# Nur Integrationstests
pytest tests/integration/ -v
```

### Code Coverage

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

Der HTML-Report wird in `htmlcov/` gespeichert und kann im Browser geöffnet werden.

### Neue Tests schreiben

**Engine-Tests** — direkte Klassen-Instantiierung, keine Mocks für Repositories nötig:

```python
class TestEcBudgetCalculator:
    calc = EcBudgetCalculator()

    def test_ec_net_calculation(self):
        # Netto-EC-Budget = Ziel-EC minus Basiswasser-EC
        result = compute_ec_net(target_ec=1.8, base_water_ec=0.3)
        assert result == pytest.approx(1.5, abs=0.01)

    def test_temperature_correction_to_25c(self):
        # EC-Messwerte werden auf 25 °C Referenztemperatur korrigiert
        corrected = self.calc.correct_ec_at_25(measured_ec=1.6, temp_celsius=20)
        assert corrected == pytest.approx(1.7778, abs=0.001)

    def test_living_soil_bypass(self):
        result = self.calc.calculate(
            EcBudgetInput(
                base_water_ec=0.3,
                target_ec=1.8,
                substrate=SubstrateType.LIVING_SOIL,
                volume_liters=10,
            )
        )
        assert result.living_soil_bypass is True
```

**Service-Tests** — Repositories werden gemockt:

```python
class TestSpeciesService:
    async def test_create_species(self):
        mock_repo = AsyncMock(spec=SpeciesRepository)
        mock_repo.create.return_value = Species(key="sp-1", ...)
        service = SpeciesService(mock_repo)
        result = await service.create(CreateSpeciesRequest(...))
        mock_repo.create.assert_called_once()
        assert result.key == "sp-1"
```

---

## Frontend-Tests (vitest)

### Voraussetzungen

```bash
cd src/frontend
npm install
```

Node.js 25.1.0 ist erforderlich (via asdf, `.tool-versions` im Frontend-Verzeichnis).

### Tests ausführen

```bash
# Alle Tests (einmaliger Durchlauf)
npm test

# Watch-Modus (Tests bei Dateiänderungen neu ausführen)
npm run test:watch

# Mit Coverage-Report
npm run test:coverage
```

### Teststruktur

```
src/frontend/src/test/
├── setup.ts                   # Globales Test-Setup (MSW, jest-dom, Cleanup)
├── helpers.tsx                # renderWithProviders, createTestStore
├── mocks/
│   ├── handlers.ts            # MSW Request-Handler (API-Mocks)
│   └── server.ts              # MSW Node-Server
├── components/                # Komponenten-Tests
│   ├── ConfirmDialog.test.tsx
│   ├── DataTable.test.tsx
│   ├── FormTextField.test.tsx
│   └── ...
├── hooks/                     # Hook-Tests (useApiError, useDebounce, ...)
├── pages/                     # Seiten-Komponenten-Tests
├── store/                     # Redux Slice-Tests
├── api/                       # API-Client-Tests
└── a11y/                      # Barrierefreiheits-Tests (vitest-axe)
```

### Test-Infrastruktur (setup.ts)

Das Setup initialisiert vor allen Tests den MSW-Server und setzt einen Tenant-Slug in `localStorage`. Nach jedem Test wird der DOM bereinigt und die MSW-Handler werden zurückgesetzt:

```typescript
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
beforeEach(() => {
  window.localStorage.setItem('kp_active_tenant_slug', 'test-tenant');
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
```

### renderWithProviders (helpers.tsx)

Alle Komponenten-Tests verwenden `renderWithProviders` aus `src/test/helpers.tsx`. Diese Funktion wickelt die Komponente in alle erforderlichen Provider ein:

```typescript
import { renderWithProviders } from '@/test/helpers';
import { screen } from '@testing-library/react';
import { SpeciesDetailPage } from '@/pages/stammdaten/SpeciesDetailPage';

test('renders species name', () => {
  renderWithProviders(<SpeciesDetailPage />, { route: '/stammdaten/species/sp-1' });
  expect(screen.getByText('Solanum lycopersicum')).toBeInTheDocument();
});
```

**Enthaltene Provider:** Redux Store, React Router (`createMemoryRouter`), MUI Theme, `SnackbarProvider`.

!!! warning "userPreferences-Reducer erforderlich"
    Komponenten, die `useExpertiseLevel` verwenden, benötigen den `userPreferences`-Reducer im Test-Store. `createTestStore()` schließt ihn bereits ein. Beim manuellen Erstellen eines Test-Stores muss er explizit hinzugefügt werden:
    ```typescript
    configureStore({
      reducer: {
        userPreferences: userPreferencesReducer,
        // ... weitere Reducer
      }
    });
    ```

### API-Mocks mit MSW

API-Aufrufe werden durch [Mock Service Worker (MSW)](https://mswjs.io/) abgefangen. Handler sind in `src/test/mocks/handlers.ts` definiert:

```typescript
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/v1/botanical-families', () => {
    return HttpResponse.json(mockFamilies);
  }),

  http.post('/api/v1/t/:tenantSlug/species', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ key: 'sp-new', ...body }, { status: 201 });
  }),
];
```

Für testspezifisches Verhalten können Handler temporär überschrieben werden:

```typescript
test('shows error on API failure', () => {
  server.use(
    http.get('/api/v1/botanical-families', () => {
      return HttpResponse.error();
    })
  );
  renderWithProviders(<BotanicalFamilyList />);
  expect(screen.getByText(/Fehler beim Laden/)).toBeInTheDocument();
});
```

### Barrierefreiheits-Tests (vitest-axe)

Kritische Formulare und Dialogfelder haben automatische Accessibility-Tests:

```typescript
import { axe } from 'vitest-axe';

test('form has no accessibility violations', async () => {
  const { container } = renderWithProviders(<SpeciesCreateDialog open />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Neue Tests schreiben

**Konventionen für Komponenten-Tests:**

```typescript
import { describe, test, expect } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/helpers';

describe('FormTextField', () => {
  test('displays validation error', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <FormTextField name="email" label="E-Mail" required />
    );
    await user.click(screen.getByLabelText('E-Mail'));
    await user.tab(); // Fokus verlassen, um Validierung auszulösen
    expect(screen.getByText(/Pflichtfeld/)).toBeInTheDocument();
  });
});
```

**Redux Slice-Tests — ohne React:**

```typescript
import { describe, test, expect } from 'vitest';
import onboardingReducer, { setStep } from '@/store/slices/onboardingSlice';

describe('onboardingSlice', () => {
  test('advances step', () => {
    const initial = { currentStep: 0, completed: false };
    const next = onboardingReducer(initial, setStep(1));
    expect(next.currentStep).toBe(1);
  });
});
```

### Formular-Validierung: was vitest hier *nicht* prüfen kann

!!! warning "jsdom erzwingt keine native Constraint-Validierung"
    Ein Test der Form „Pflichtfeld leer lassen, abschicken, zod-Meldung erwarten"
    ist im Frontend **nicht fehlschlagbar** — er wird grün, egal ob das Formular
    `noValidate` trägt oder nicht.

    Im echten Browser bricht die native Validierung das Abschicken ab, *bevor*
    das `submit`-Event feuert: `handleSubmit` läuft nie, zod läuft nie, es
    rendert kein `helperText`, und der Nutzer sieht eine native Sprechblase in
    der **Browser-Sprache** statt in der App-Sprache. jsdom implementiert diesen
    Abbruch nicht und ruft den Handler einfach auf — der Test misst also genau
    das Gegenteil dessen, was er zu prüfen scheint.

    Das ist kein theoretisches Risiko: Genau so blieb der Defekt aus
    [#825](https://github.com/nolte/kamerplanter/issues/825) über ~55 Dateien
    unsichtbar, und [#822](https://github.com/nolte/kamerplanter/issues/822)
    verwarf einen so geschriebenen Test bewusst wieder, statt eine Prüfung
    auszuliefern, die nicht fehlschlagen kann.

**Was stattdessen schützt — drei Ebenen, keine davon ein Verhaltens-Unit-Test:**

1. **`<Form>` statt `<form>`** (`@/components/form/Form`). Der Wrapper setzt
   `noValidate` *nach* dem Prop-Spread, ist also von außen nicht abschaltbar.
   Jedes RHF-Formular nutzt ihn.
2. **ESLint-Regel** (`no-restricted-syntax` in `src/frontend/eslint.config.js`).
   Ein rohes `<form>` oder ein `component="form"` ohne `noValidate` bricht den
   Build. Damit scheitert der nächste ungeschützte Fall im CI statt in Produktion.
3. **E2E im echten Browser.** Nur dort ist die Verhaltenszusage überhaupt
   messbar. Page-Objects müssen den Dialog deshalb über den **echten
   Absende-Button** bedienen — ein per JavaScript abgesetztes `submit`-Event
   umgeht die native Validierung genauso wie jsdom und macht den Test wertlos
   (siehe [#815](https://github.com/nolte/kamerplanter/issues/815)).

Auf Unit-Ebene sinnvoll bleibt nur die *strukturelle* Zusicherung — dass das
Attribut am DOM-Knoten ankommt und nicht überschreibbar ist. Genau das prüft
`src/test/components/Form.test.tsx`.

---

## E2E-Tests (Selenium)

End-to-End-Tests prüfen komplette Benutzer-Workflows in einem echten Browser. Sie verwenden Selenium WebDriver mit dem Page-Object-Pattern und erzeugen Markdown-Testprotokolle mit Screenshots (NFR-008).

### Voraussetzungen

```bash
pip install -r tests/e2e/requirements.txt
```

Abhängigkeiten: `selenium>=4.25.0`, `webdriver-manager>=4.0.0`, `pytest>=8.3.0`.

### Lokal ausführen

Tests laufen gegen eine lokale Applikations-Instanz mit einem lokalen Chrome/Firefox-Browser:

```bash
# Standard: Chrome headless gegen localhost:5173
pytest tests/e2e/ -v

# Firefox
pytest tests/e2e/ --browser firefox -v

# Eigene Base-URL (z. B. Docker-Compose-Dev-Stack auf Port 8080)
pytest tests/e2e/ --base-url http://localhost:8080 -v

# Mit Testprotokoll-Generierung (NFR-008 §4.4)
pytest tests/e2e/ --generate-protocol
```

Reports und Screenshots werden in `test-reports/e2e/<timestamp>/` gespeichert.

### Dedizierte Docker-Umgebung

Ein eigener Docker-Compose-Stack startet die komplette Applikation plus Selenium Grid in einem isolierten Netzwerk — keine Host-Ports nötig, läuft parallel zum Kind/Skaffold-Cluster ohne Konflikte.

```bash
# Empfohlen: Wrapper-Skript (startet Stack, sammelt Logs, räumt auf)
./scripts/run-e2e.sh

# Oder manuell:
docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit
docker compose -f docker-compose.e2e.yml down -v
```

Der Stack umfasst:

| Service | Zweck |
|---------|-------|
| `arangodb` | Isolierte Testdatenbank (`kamerplanter_e2e`) |
| `valkey` | Redis-kompatibler Cache/Queue |
| `backend` | FastAPI-Applikation |
| `celery-worker` | Hintergrund-Taskverarbeitung |
| `frontend` | React-App via nginx |
| `selenium-hub` | Selenium-Grid-Hub |
| `chrome` | Chrome-Node (bis zu 4 parallele Sessions) |
| `e2e-tests` | Test-Runner-Container |

Reports werden auf dem Host nach `./test-reports/e2e/<timestamp>/` geschrieben:

- `protokoll.md` — Markdown-Testprotokoll mit Ergebnissen und eingebetteten Screenshots
- `screenshots/` — alle Screenshots (explizite Checkpoints + automatische Failure-Captures)
- `logs/` — Container-Logs aller Services (Backend, Frontend, Selenium, ArangoDB, ...)
- `junit-<profil>.xml` — JUnit-XML-Report je Compose-Profil (z. B. `junit-smoke.xml`, `junit-full.xml`); jeder Testfall trägt seine TC-ID als `tc_id`-`user_property`. In CI wird diese Datei zu einem GitHub-Check-Run mit konkreten Fehlermeldungen gerendert — siehe [Teststufen → E2E-Tests](stufen/e2e.md#ci-testberichte).

**Funktionsweise:** Der Test-Runner verbindet sich über Selenium Grid mit Chrome (`SELENIUM_REMOTE_URL`) und erreicht das Frontend über Dockers internes Netzwerk (`E2E_BASE_URL=http://frontend:80`). Die `conftest.py`-Browser-Fixture schaltet automatisch zwischen lokalem und Remote-WebDriver um, basierend auf der Umgebungsvariable `SELENIUM_REMOTE_URL`.

### Teststruktur

```
tests/e2e/
├── conftest.py              # Browser-Fixtures, CLI-Optionen, Screenshot-Erfassung
├── protocol_plugin.py       # Markdown-Protokoll-Generator (NFR-008 §4.4)
├── requirements.txt         # E2E Python-Abhängigkeiten
├── Dockerfile               # Test-Runner-Container für Docker Compose
├── pages/
│   ├── base_page.py         # BasePage mit gemeinsamen Selenium-Hilfsmethoden
│   ├── login_page.py        # Page Objects (eins pro Bildschirm)
│   └── ...
├── test_req001_*.py         # Tests nach Anforderung organisiert
├── test_req006_*.py
└── ...
```

### Page-Object-Pattern

Alle Page Objects erben von `BasePage` und verwenden `data-testid`-Locator:

```python
from .base_page import BasePage
from selenium.webdriver.common.by import By

class LoginPage(BasePage):
    PATH = "/login"
    USERNAME_INPUT = (By.CSS_SELECTOR, "[data-testid='email-input'] input")
    PASSWORD_INPUT = (By.CSS_SELECTOR, "[data-testid='password-input'] input")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "[data-testid='login-submit']")

    def login(self, email: str, password: str):
        self.navigate(self.PATH)
        self.wait_for_element(self.USERNAME_INPUT).send_keys(email)
        self.wait_for_element(self.PASSWORD_INPUT).send_keys(password)
        self.wait_for_element_clickable(self.SUBMIT_BUTTON).click()
```

### Screenshots

Screenshots werden bei Fehlern automatisch erstellt und können während der Tests explizit aufgenommen werden:

```python
class TestDashboard:
    def test_dashboard_loads(self, screenshot, browser, base_url):
        browser.get(base_url)
        screenshot("001_dashboard_loaded", "Dashboard nach initialem Laden")
```

---

## RAG-Qualitätsbenchmark

Ein Standalone-Runner (`tools/rag-eval/eval_rag.py`) misst die Antwortqualitaet der RAG-Pipeline unabhaengig vom Backend. Er verbindet sich direkt mit Embedding Service, VectorDB (pgvector) und Ollama.

### Voraussetzungen

- Embedding Service laeuft (Standard: `http://localhost:8080`)
- VectorDB (PostgreSQL mit pgvector) laeuft (Standard: `localhost:5433`)
- Ollama laeuft mit geladenem Modell (Standard: `gemma3:4b`)

### Tests ausfuehren

```bash
# Vollstaendiger Benchmark (100 Fragen)
python tools/rag-eval/eval_rag.py

# Schneller Smoke-Test (bricht beim ersten Fehler ab)
python tools/rag-eval/eval_rag.py --smoke

# Unterbrochenen Lauf fortsetzen
python tools/rag-eval/eval_rag.py --resume

# Nur bestimmte Kategorien
python tools/rag-eval/eval_rag.py --categories diagnostik duengung

# Retrieval debuggen ohne LLM-Generierung
python tools/rag-eval/eval_rag.py --retrieval-only
```

### CLI-Parameter

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `--smoke` | - | Schneller Smoke-Test, bricht beim ersten Fehler ab |
| `--resume` | - | Setzt unterbrochenen Lauf fort (laedt `eval_results_partial.json`) |
| `--categories` | alle | Nur bestimmte Kategorien evaluieren |
| `--retrieval-only` | - | Zeigt abgerufene Chunks ohne LLM-Generierung |
| `--top-k` | 5 | Anzahl der RAG-Chunks pro Frage |
| `--doc-language` | kein Filter | Chunks nach Sprache filtern (`de`/`en`/`all`) |
| `--prompt-language` | `de` | Sprache des System-Prompts (`de`/`en`) |
| `--model` | `gemma3:4b` | Ollama-Modellname |
| `--embedding-url` | `http://localhost:8080` | Embedding Service URL |
| `--ollama-url` | `http://localhost:11434` | Ollama API URL |
| `--vectordb-dsn` | `localhost:5433` | PostgreSQL DSN für VectorDB |
| `--output`, `-o` | `eval_results.json` | Ausgabepfad für Ergebnis-JSON |

### Umgebungsvariablen

Werden als Defaults verwendet wenn kein CLI-Argument gesetzt ist:

| Variable | Default |
|----------|---------|
| `EMBEDDING_SERVICE_URL` | `http://localhost:8080` |
| `VECTORDB_DSN` | `host=localhost port=5433 dbname=kamerplanter_vectors ...` |
| `LLM_API_URL` | `http://localhost:11434` |
| `LLM_MODEL` | `gemma3:4b` |
| `EVAL_DATA_DIR` | `spec/rag-eval/` |

### Resume-Mechanismus

Nach jeder evaluierten Frage wird `eval_results_partial.json` geschrieben. Bei `--resume` werden vorherige Ergebnisse geladen und bereits evaluierte Fragen übersprungen. Alte und neue Ergebnisse werden für den finalen Score zusammengeführt.

### Scoring

Jede Frage wird gegen erwartete Topics (`expected_topics`) und Ausschluss-Topics (`expected_NOT`) geprueft. Der Gesamtscore ist der Durchschnitt aller Einzelscores — ab 70% gilt der Benchmark als bestanden.

### Testdaten

```
spec/rag-eval/
├── benchmark_questions.yaml   # 100 kuratierte Fragen mit erwarteten Topics
├── smoke_questions.yaml       # Schnelle Smoke-Test-Teilmenge
├── topic_synonyms.yaml        # Synonym-Woerterbuch fuer Topic-Matching
├── eval_results.json          # Letztes vollstaendiges Ergebnis
└── RAG_EVAL_SPEC.md           # Detaillierte Framework-Spezifikation
```

Detaillierte Spezifikation des Frameworks: `spec/rag-eval/RAG_EVAL_SPEC.md`

---

## Gemeinsame Regeln für beide Test-Suites

- Tests laufen in CI bei jedem Push auf `develop` und bei jedem Pull Request.
- Neue Features erfordern mindestens einen Unit-Test für die Business-Logik.
- Bug-Fixes erfordern einen Regressionstest, der den Bug reproduziert.
- Kein `.skip` oder `.only` in gemergten Tests ohne Kommentar und Issue-Referenz.

## Siehe auch

- [Teststufen](stufen/index.md)
- [Code-Standards](../code-standards.md)
- [Lokales Setup](../local-setup.md)
- [Debugging](../debugging.md)

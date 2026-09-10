# Testing

Kamerplanter has a comprehensive test suite for both backend and frontend. All tests must be green before a pull request is merged.

**Current status:** 821 backend tests (pytest), 198 frontend tests (vitest) — all passing.

---

## Testing concept

Kamerplanter tests across several **test levels** — from fast, isolated unit tests to full end-to-end runs in a real browser. The levels form a classic test pyramid: many fast tests at the base, few slow ones at the top.

!!! tip "Test levels in detail"
    This page bundles the practical testing concept organized by **tooling** (pytest, vitest, Selenium): prerequisites, execution, test structure and conventions. For a conceptual overview organized by **test level** (unit → integration → component → E2E), see [Test Levels](stufen/index.md).

---

## Backend Tests (pytest)

### Prerequisites

```bash
cd src/backend
uv sync --locked --extra dev      # or: task deps:sync
source .venv/bin/activate
```

This installs exactly the production and development dependencies recorded in `uv.lock` (hash-verified), including pytest, pytest-asyncio, and pytest-cov. Install uv from <https://docs.astral.sh/uv/>.

### Running Tests

```bash
# All tests
pytest

# With verbose output
pytest -v

# Single test file
pytest tests/test_onboarding_engine.py -v

# Single test
pytest tests/test_onboarding_engine.py::TestValidateKitApplication::test_valid_application -v

# Filter tests by name pattern
pytest -k "substrate" -v
```

### Test Structure

```
src/backend/tests/
├── conftest.py                        # Shared fixtures (Species, Site, Substrate, ...)
├── unit/                              # Unit tests without external dependencies
│   ├── domain/
│   │   └── test_calculations.py      # VPD, GDD, EC calculations
│   └── adapters/
│       └── test_enrichment.py        # GBIF/Perenual adapter logic
├── api/                               # API layer tests
│   └── test_error_handling.py
├── integration/                       # Integration tests (require ArangoDB)
│   └── test_arango_integration.py
├── test_care_reminder_engine.py       # Engine tests (direct class instantiation)
├── test_onboarding_engine.py
├── test_substrate_lifecycle_manager.py
└── test_*.py                          # Further engine/service tests
```

### pytest-asyncio Configuration

pytest-asyncio is configured with `asyncio_mode = "auto"`. Async test functions do not need an explicit `@pytest.mark.asyncio` decorator:

```python
# Works without explicit decorator
async def test_service_creates_species():
    service = SpeciesService(mock_repo)
    result = await service.create(sample_data)
    assert result.scientific_name == "Solanum lycopersicum"
```

### Fixtures (conftest.py)

The central `conftest.py` provides typical datasets as fixtures:

```python
def test_substrate_lifecycle(sample_substrate_data):
    substrate = Substrate(**sample_substrate_data)
    manager = SubstrateLifecycleManager()
    result = manager.prepare_for_reuse(substrate)
    assert result.reuse_cycle == 1
```

Available fixtures: `sample_species_data`, `sample_site_data`, `sample_location_data`, `sample_substrate_data`.

### Integration Tests

Integration tests under `tests/integration/` require a running ArangoDB instance. They are automatically skipped when no connection is available:

```python
@pytest.mark.skipif(not ARANGO_AVAILABLE, reason="ArangoDB not available")
class TestArangoSetup:
    ...
```

To run them explicitly:

```bash
# Start ArangoDB (e.g. via Docker Compose)
docker-compose up -d arangodb

# Integration tests only
pytest tests/integration/ -v
```

### Code Coverage

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

The HTML report is saved in `htmlcov/` and can be opened in a browser.

### Writing New Tests

**Engine tests** — direct class instantiation, no repository mocks needed:

```python
class TestEcBudgetCalculator:
    calc = EcBudgetCalculator()

    def test_ec_net_calculation(self):
        # Net EC budget = target EC minus base-water EC
        result = compute_ec_net(target_ec=1.8, base_water_ec=0.3)
        assert result == pytest.approx(1.5, abs=0.01)

    def test_temperature_correction_to_25c(self):
        # EC readings are corrected to the 25 °C reference temperature
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

**Service tests** — repositories are mocked:

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

## Frontend Tests (vitest)

### Prerequisites

```bash
cd src/frontend
npm install
```

Node.js 25.1.0 is required (via asdf, `.tool-versions` in the frontend directory).

### Running Tests

```bash
# All tests (single run)
npm test

# Watch mode (re-run on file changes)
npm run test:watch

# With coverage report
npm run test:coverage
```

### Test Structure

```
src/frontend/src/test/
├── setup.ts                   # Global test setup (MSW, jest-dom, cleanup)
├── helpers.tsx                # renderWithProviders, createTestStore
├── mocks/
│   ├── handlers.ts            # MSW request handlers (API mocks)
│   └── server.ts              # MSW node server
├── components/                # Component tests
│   ├── ConfirmDialog.test.tsx
│   ├── DataTable.test.tsx
│   ├── FormTextField.test.tsx
│   └── ...
├── hooks/                     # Hook tests (useApiError, useDebounce, ...)
├── pages/                     # Page component tests
├── store/                     # Redux slice tests
├── api/                       # API client tests
└── a11y/                      # Accessibility tests (vitest-axe)
```

### Test Infrastructure (setup.ts)

The setup initializes the MSW server before all tests and sets a tenant slug in `localStorage`. After each test, the DOM is cleaned up and MSW handlers are reset:

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

All component tests use `renderWithProviders` from `src/test/helpers.tsx`. This function wraps the component in all required providers:

```typescript
import { renderWithProviders } from '@/test/helpers';
import { screen } from '@testing-library/react';
import { SpeciesDetailPage } from '@/pages/stammdaten/SpeciesDetailPage';

test('renders species name', () => {
  renderWithProviders(<SpeciesDetailPage />, { route: '/stammdaten/species/sp-1' });
  expect(screen.getByText('Solanum lycopersicum')).toBeInTheDocument();
});
```

**Included providers:** Redux Store, React Router (`createMemoryRouter`), MUI Theme, `SnackbarProvider`.

!!! warning "userPreferences reducer required"
    Components using `useExpertiseLevel` require the `userPreferences` reducer in the test store. `createTestStore()` already includes it. When creating a test store manually, add it explicitly:
    ```typescript
    configureStore({
      reducer: {
        userPreferences: userPreferencesReducer,
        // ... other reducers
      }
    });
    ```

### API Mocks with MSW

API calls are intercepted by [Mock Service Worker (MSW)](https://mswjs.io/). Handlers are defined in `src/test/mocks/handlers.ts`:

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

For test-specific behavior, handlers can be temporarily overridden:

```typescript
test('shows error on API failure', () => {
  server.use(
    http.get('/api/v1/botanical-families', () => {
      return HttpResponse.error();
    })
  );
  renderWithProviders(<BotanicalFamilyList />);
  expect(screen.getByText(/Error loading/)).toBeInTheDocument();
});
```

### Accessibility Tests (vitest-axe)

Critical forms and dialogs have automated accessibility tests:

```typescript
import { axe } from 'vitest-axe';

test('form has no accessibility violations', async () => {
  const { container } = renderWithProviders(<SpeciesCreateDialog open />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

### Writing New Tests

**Component test conventions:**

```typescript
import { describe, test, expect } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/helpers';

describe('FormTextField', () => {
  test('displays validation error', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <FormTextField name="email" label="Email" required />
    );
    await user.click(screen.getByLabelText('Email'));
    await user.tab(); // Leave focus to trigger validation
    expect(screen.getByText(/Required/)).toBeInTheDocument();
  });
});
```

**Redux slice tests — without React:**

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

### Form validation: what vitest *cannot* check here

!!! warning "jsdom does not enforce native constraint validation"
    A test shaped like "leave a required field empty, submit, expect the zod
    message" **cannot fail** in the frontend suite — it passes whether or not
    the form carries `noValidate`.

    In a real browser, native validation aborts the submission *before* the
    `submit` event fires: `handleSubmit` never runs, zod never runs, no
    `helperText` renders, and the user gets a native bubble in the **browser's**
    locale rather than the app's. jsdom does not implement that abort and simply
    calls the handler — so the test measures the exact opposite of what it
    appears to check.

    This is not a theoretical risk. It is how the defect in
    [#825](https://github.com/nolte/kamerplanter/issues/825) stayed invisible
    across ~55 files, and why
    [#822](https://github.com/nolte/kamerplanter/issues/822) deliberately threw
    such a test away rather than ship a check that cannot fail.

**What protects instead — three layers, none of them a behavioural unit test:**

1. **`<Form>` rather than `<form>`** (`@/components/form/Form`). The wrapper
   applies `noValidate` *after* the prop spread, so a call site cannot switch it
   off. Every RHF form uses it.
2. **An ESLint rule** (`no-restricted-syntax` in `src/frontend/eslint.config.js`).
   A raw `<form>`, or a `component="form"` without `noValidate`, breaks the
   build — so the next unguarded case fails in CI instead of in production.
3. **E2E in a real browser.** That is the only place the behavioural promise is
   measurable at all. Page objects must therefore drive the dialog through the
   **real submit button**: a JavaScript-dispatched `submit` event bypasses
   native validation just as jsdom does, which makes the test worthless (see
   [#815](https://github.com/nolte/kamerplanter/issues/815)).

The only assertion worth making at the unit tier is the *structural* one — that
the attribute reaches the DOM node and cannot be overridden. That is exactly
what `src/test/components/Form.test.tsx` checks.

---

## E2E Tests (Selenium)

End-to-end tests verify complete user workflows through a real browser. They use Selenium WebDriver with the Page Object pattern and generate Markdown test protocols with screenshots (NFR-008).

### Prerequisites

```bash
pip install -r tests/e2e/requirements.txt
```

Dependencies: `selenium>=4.25.0`, `webdriver-manager>=4.0.0`, `pytest>=8.3.0`.

### Running Locally

Tests run against a local application instance with a local Chrome/Firefox browser:

```bash
# Default: Chrome headless against localhost:5173
pytest tests/e2e/ -v

# Firefox
pytest tests/e2e/ --browser firefox -v

# Custom base URL (e.g. Docker Compose dev stack on port 8080)
pytest tests/e2e/ --base-url http://localhost:8080 -v

# With test protocol generation (NFR-008 §4.4)
pytest tests/e2e/ --generate-protocol
```

Reports and screenshots are saved to `test-reports/e2e/<timestamp>/`.

### Dedicated Docker Environment

A dedicated Docker Compose stack runs the complete application plus Selenium Grid in an isolated network — no host ports needed, runs in parallel with Kind/Skaffold without conflicts.

```bash
# Recommended: wrapper script (starts stack, collects logs, tears down)
./scripts/run-e2e.sh

# Or manually:
docker compose -f docker-compose.e2e.yml up --build --abort-on-container-exit
docker compose -f docker-compose.e2e.yml down -v
```

The stack includes:

| Service | Purpose |
|---------|---------|
| `arangodb` | Isolated test database (`kamerplanter_e2e`) |
| `valkey` | Redis-compatible cache/queue |
| `backend` | FastAPI application |
| `celery-worker` | Background task processing |
| `frontend` | React app served via nginx |
| `selenium-hub` | Selenium Grid hub |
| `chrome` | Chrome node (up to 4 parallel sessions) |
| `e2e-tests` | Test runner container |

Reports are written to `./test-reports/e2e/<timestamp>/` on the host:

- `protokoll.md` — Markdown test protocol with results and inline screenshots
- `screenshots/` — all screenshots (explicit checkpoints + automatic failure captures)
- `logs/` — container logs for all services (backend, frontend, selenium, arangodb, ...)
- `junit-<profile>.xml` — JUnit XML report per compose profile (e.g. `junit-smoke.xml`, `junit-full.xml`); every test case carries its TC-ID as a `tc_id` `user_property`. In CI this file is rendered into a GitHub check run with concrete failure messages — see [Test Levels → E2E Tests](stufen/e2e.md#ci-test-reports).

**How it works:** The test runner connects to Chrome via Selenium Grid (`SELENIUM_REMOTE_URL`), and reaches the frontend via Docker's internal network (`E2E_BASE_URL=http://frontend:80`). The `conftest.py` browser fixture automatically switches between local and remote WebDriver based on the `SELENIUM_REMOTE_URL` environment variable.

### Test Structure

```
tests/e2e/
├── conftest.py              # Browser fixtures, CLI options, screenshot capture
├── protocol_plugin.py       # Markdown protocol report generator (NFR-008 §4.4)
├── requirements.txt         # E2E Python dependencies
├── Dockerfile               # Test runner container for Docker Compose
├── pages/
│   ├── base_page.py         # BasePage with shared Selenium utilities
│   ├── login_page.py        # Page objects (one per screen)
│   └── ...
├── test_req001_*.py         # Tests organized by requirement
├── test_req006_*.py
└── ...
```

### Page Object Pattern

All page objects inherit from `BasePage` and use `data-testid` locators:

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

Screenshots are captured automatically on failure and can be taken explicitly during tests:

```python
class TestDashboard:
    def test_dashboard_loads(self, screenshot, browser, base_url):
        browser.get(base_url)
        screenshot("001_dashboard_loaded", "Dashboard after initial load")
```

---

## RAG Quality Benchmark

A standalone runner (`tools/rag-eval/eval_rag.py`) measures the response quality of the RAG pipeline independently of the backend. It connects directly to the Embedding Service, VectorDB (pgvector), and Ollama.

### Prerequisites

- Embedding Service running (default: `http://localhost:8080`)
- VectorDB (PostgreSQL with pgvector) running (default: `localhost:5433`)
- Ollama running with a loaded model (default: `gemma3:4b`)

### Running Tests

```bash
# Full benchmark (100 questions)
python tools/rag-eval/eval_rag.py

# Quick smoke test (aborts on first failure)
python tools/rag-eval/eval_rag.py --smoke

# Resume an interrupted run
python tools/rag-eval/eval_rag.py --resume

# Only specific categories
python tools/rag-eval/eval_rag.py --categories diagnostik duengung

# Debug retrieval without LLM generation
python tools/rag-eval/eval_rag.py --retrieval-only
```

### CLI Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--smoke` | - | Quick smoke test, aborts on first failure |
| `--resume` | - | Resume interrupted run (loads `eval_results_partial.json`) |
| `--categories` | all | Only evaluate specific categories |
| `--retrieval-only` | - | Show retrieved chunks without LLM generation |
| `--top-k` | 5 | Number of RAG chunks to retrieve per question |
| `--doc-language` | no filter | Filter chunks by language (`de`/`en`/`all`) |
| `--prompt-language` | `de` | System prompt language (`de`/`en`) |
| `--model` | `gemma3:4b` | Ollama model name |
| `--embedding-url` | `http://localhost:8080` | Embedding service URL |
| `--ollama-url` | `http://localhost:11434` | Ollama API URL |
| `--vectordb-dsn` | `localhost:5433` | PostgreSQL DSN for VectorDB |
| `--output`, `-o` | `eval_results.json` | Output path for result JSON |

### Environment Variables

Used as defaults when no CLI argument is provided:

| Variable | Default |
|----------|---------|
| `EMBEDDING_SERVICE_URL` | `http://localhost:8080` |
| `VECTORDB_DSN` | `host=localhost port=5433 dbname=kamerplanter_vectors ...` |
| `LLM_API_URL` | `http://localhost:11434` |
| `LLM_MODEL` | `gemma3:4b` |
| `EVAL_DATA_DIR` | `spec/rag-eval/` |

### Resume Mechanism

After each evaluated question, `eval_results_partial.json` is written. With `--resume`, previous results are loaded and already-evaluated questions are skipped. Old and new results are merged for the final score.

### Scoring

Each question is checked against expected topics (`expected_topics`) and exclusion topics (`expected_NOT`). The overall score is the average of all individual scores — the benchmark passes at 70% or above.

### Test Data

```
spec/rag-eval/
├── benchmark_questions.yaml   # 100 curated questions with expected topics
├── smoke_questions.yaml       # Quick smoke test subset
├── topic_synonyms.yaml        # Synonym dictionary for topic matching
├── eval_results.json          # Last complete result
└── RAG_EVAL_SPEC.md           # Detailed framework specification
```

Detailed framework specification: `spec/rag-eval/RAG_EVAL_SPEC.md`

---

## Common Rules for Both Test Suites

- Tests run in CI on every push to `develop` and every pull request.
- New features require at least one unit test for the business logic.
- Bug fixes require a regression test that reproduces the bug.
- No `.skip` or `.only` in merged tests without a comment and issue reference.

## See also

- [Test Levels](stufen/index.md)
- [Code Standards](../code-standards.md)
- [Local Setup](../local-setup.md)
- [Debugging](../debugging.md)

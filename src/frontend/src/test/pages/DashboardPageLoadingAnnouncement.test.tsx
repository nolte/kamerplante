import { screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import i18n from 'i18next';
import DashboardPage from '@/pages/DashboardPage';
import { fetchAggregated } from '@/store/slices/dashboardSlice';
import { dismissPersonalizationHint } from '@/lib/dashboardLayoutStorage';
import { createTestStore, renderWithProviders, type TestStore } from '../helpers';
import { server } from '../mocks/server';
import { expectNoA11yViolations } from '../a11y/expectNoA11yViolations';
import { deFull, enFull } from '../i18nTestResources';
import type { DashboardLayout } from '@/api/types';

/**
 * Issue #1337 item 1 — the dashboard announces its load **once**, from the page,
 * and it announces the thing that is actually still in flight.
 *
 * Everything here is driven through the real store and real MSW responses. The
 * defect this replaces was invisible to a harness-driven test: the region read
 * `state.dashboard.loading`, which only `fetchWidgetCatalog` ever writes, so it
 * fell silent when the ~80ms catalogue arrived while the ~600ms aggregate was
 * still pending. A test that sets "loading" by hand cannot tell the two fetches
 * apart, and therefore cannot see that.
 *
 * The two responses are consequently held apart on purpose: the catalogue
 * answers immediately, the aggregate answers only when a test releases it.
 */

/** The five aggregated widgets the issue measured standing at once. */
const WIDGET_KEYS = [
  'tasks_today',
  'care_reminders',
  'active_plants_summary',
  'daily_tip',
  'onboarding_progress',
] as const;

const LAYOUT: DashboardLayout = {
  schema_version: 2,
  widgets: WIDGET_KEYS.map((key) => ({ instance_id: key, widget_key: key, config: {} })),
  placements: {
    lg: WIDGET_KEYS.map((key, i) => ({
      instance_id: key,
      x: (i % 3) * 4,
      y: Math.floor(i / 3),
      w: 4,
      h: 3,
    })),
  },
};

const CATALOG = WIDGET_KEYS.map((key) => ({
  widget_key: key,
  category: 'overview',
  default_level: 'beginner' as const,
  default_size: { w: 4, h: 3 },
  min_size: { w: 2, h: 2 },
  max_size: { w: 12, h: 8 },
  required_module: null,
  available: true,
  unavailable_reason: null,
}));

const LOADING_MESSAGE_EN = 'Dashboard is loading...';
const LOADING_MESSAGE_DE = 'Dashboard wird geladen...';

/** A promise a test resolves when it wants the aggregate request to answer. */
let aggregateGate: {
  promise: Promise<Record<string, unknown>>;
  release: (widgets: Record<string, unknown>) => void;
};

function armAggregateGate(): void {
  let release!: (widgets: Record<string, unknown>) => void;
  const promise = new Promise<Record<string, unknown>>((resolve) => {
    release = resolve;
  });
  aggregateGate = { promise, release };
}

function installDashboardHandlers(): void {
  server.use(
    http.get('/api/v1/t/:tenant/dashboard/widgets/catalog', () =>
      HttpResponse.json({ widgets: CATALOG }),
    ),
    http.get('/api/v1/t/:tenant/dashboard/aggregated', async () => {
      const widgets = await aggregateGate.promise;
      return HttpResponse.json({
        generated_at: '2026-09-10T00:00:00Z',
        tenant_key: 'tenant-1',
        widgets,
      });
    }),
  );
}

/**
 * Install a working in-memory `localStorage`.
 *
 * Not a convenience — the ambient one differs between a local run and CI, and
 * that difference decides what this page renders. Measured: under the local Node
 * runtime `globalThis.localStorage` is an empty plain object with no `getItem`,
 * so `isPersonalizationHintDismissed()` throws, lands in its "storage
 * unavailable → don't nag" catch, and the personalization coachmark **never**
 * appears. jsdom's real storage in CI returns `null`, the hint counts as not
 * dismissed, and the coachmark renders — as a MUI `Alert`, i.e. a `role="alert"`
 * live region carrying text. Four assertions here were green locally and red in
 * CI for exactly that reason. Pinning storage puts the decision in the test
 * instead of in the environment.
 */
function installMemoryStorage(): void {
  const data = new Map<string, string>();
  const storage: Storage = {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, String(value));
    },
    removeItem: (key: string) => {
      data.delete(key);
    },
    clear: () => data.clear(),
    key: (index: number) => Array.from(data.keys())[index] ?? null,
    get length() {
      return data.size;
    },
  };
  for (const target of [window, globalThis]) {
    Object.defineProperty(target, 'localStorage', {
      value: storage,
      configurable: true,
      writable: true,
    });
  }
}

function storeWithStoredLayout(): TestStore {
  return createTestStore({
    userPreferences: {
      preferences: {
        key: 'pref-1',
        user_key: 'user-1',
        experience_level: 'beginner',
        onboarding_completed: true,
        locale: 'en',
        theme: 'light',
        watering_can_liters: 5,
        smart_home_enabled: false,
        // `daily_tip` sits behind the REQ-042 `ai` module and would otherwise be
        // filtered out of the grid, leaving four of the five placeholders the
        // issue measured.
        module_visibility: { ai: 'enabled' },
        dashboard_layout: LAYOUT,
      },
      loading: false,
      error: null,
    },
  });
}

/**
 * Every live region on the page that currently has something to say.
 *
 * Deliberately not "every `role="status"`": the page keeps a second, empty
 * status region for the edit-mode move/resize announcements, and an *empty*
 * live region announces nothing. What must be unique is the set of regions
 * speaking at one moment — that is the chatter the single-region decision
 * exists to prevent, and counting mounted nodes would not measure it.
 */
function speakingRegions(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>('[role="status"], [role="alert"], [aria-live]'),
  ).filter((el) => (el.textContent ?? '').trim().length > 0);
}

/**
 * `aria-label` on an element with no role of its own. `div`/`span` map to
 * `generic`, which ARIA prohibits naming, so the name is silently dropped.
 *
 * This is the **complete** check for the defect class on this subject, and axe
 * is not. Measured on this page: axe reports `aria-prohibited-attr` for only two
 * of the five placeholders, because the rule is suppressed for any node under an
 * `<a>` or `<button>` ancestor — and three of the five widget panels are wrapped
 * in the issue-#439 `CardActionArea` panel anchor. The axe assertion below is
 * therefore a floor, not the measurement; this function is the measurement.
 */
function droppedNames(root: HTMLElement): string[] {
  return Array.from(root.querySelectorAll('[aria-label]:not([role])'))
    .filter((el) => el.tagName === 'DIV' || el.tagName === 'SPAN')
    .map((el) => el.outerHTML.slice(0, 200));
}

async function renderLoadingDashboard() {
  const rendered = renderWithProviders(<DashboardPage />, { store: storeWithStoredLayout() });
  // Every widget body is lazily imported, so they do not all mount in the same
  // tick. `findAllBy*` resolves on the *first* match and would hand back a
  // half-mounted grid; wait for the full set instead.
  await waitFor(() =>
    expect(screen.getAllByTestId(/^widget-.*-loading$/)).toHaveLength(WIDGET_KEYS.length),
  );
  return rendered;
}

describe('dashboard loading announcement (#1337 item 1)', () => {
  beforeEach(() => {
    installMemoryStorage();
    // The first-visit personalization coachmark is a `role="alert"` live region
    // with content. It is not a *loading* announcer — one static, dismissible
    // banner shown once ever — so it is dismissed here rather than filtered out
    // of `speakingRegions`, which would also hide a real regression. The test
    // below pins that this is the only thing being excluded.
    dismissPersonalizationHint();
    void i18n.changeLanguage('en');
    armAggregateGate();
    installDashboardHandlers();
  });

  it('announces once for the whole page while the aggregate is in flight', async () => {
    const { container } = await renderLoadingDashboard();

    const speaking = speakingRegions(container);
    expect(
      speaking.map((r) => r.outerHTML.slice(0, 160)),
      'mid-load the dashboard must expose exactly one speaking live region for ' +
        'the whole page — one per loading widget would announce five times',
    ).toHaveLength(1);
    expect(speaking[0]).toHaveTextContent(LOADING_MESSAGE_EN);
    // Pin *which* node it is, so a future speaking region cannot take this
    // assertion over while the loading announcement quietly falls silent.
    expect(speaking[0]).toBe(screen.getByTestId('dashboard-loading-status'));
  });

  it('excludes the first-visit coachmark deliberately, and nothing else', async () => {
    // Fresh storage → the hint is *not* dismissed, which is the state CI renders
    // by default and the local runtime cannot reach on its own.
    installMemoryStorage();
    const { container } = await renderLoadingDashboard();

    expect(
      speakingRegions(container).map((r) => r.getAttribute('data-testid')),
      'the coachmark is a static onboarding banner, not a loading announcer; ' +
        'anything else speaking here is a regression',
    ).toEqual(['dashboard-coachmark', 'dashboard-loading-status']);
  });

  it('keeps announcing after the catalogue resolves, while the aggregate is still pending', async () => {
    const { container, store } = await renderLoadingDashboard();

    // The catalogue is the *fast* request; the aggregate is the slow one. A
    // region driven by the catalogue flag falls silent right here, with five
    // skeletons still on screen.
    await waitFor(() => expect(store.getState().dashboard.catalogLoaded).toBe(true));
    expect(screen.getAllByTestId(/^widget-.*-loading$/)).toHaveLength(WIDGET_KEYS.length);

    expect(
      speakingRegions(container).map((r) => r.textContent),
      'the catalogue arriving is not the dashboard finishing — the aggregate ' +
        'the placeholders are waiting for is still in flight',
    ).toEqual([LOADING_MESSAGE_EN]);
  });

  it('empties the region — but keeps it mounted — once the aggregate arrives', async () => {
    const { container } = await renderLoadingDashboard();
    const region = screen.getByTestId('dashboard-loading-status');

    aggregateGate.release(Object.fromEntries(WIDGET_KEYS.map((k) => [k, { count: 3 }])));
    await waitFor(() => expect(screen.queryAllByTestId(/^widget-.*-loading$/)).toHaveLength(0));

    // Still in the DOM: a live region has to exist *before* its content changes
    // for the change to be announced, so unmounting it would swallow the next load.
    expect(region).toBeInTheDocument();
    expect(region).toHaveTextContent('');
    expect(region).not.toHaveAttribute('aria-label');
    expect(speakingRegions(container)).toEqual([]);
  });

  it('leaves no live region behind when the widgets settle with no data', async () => {
    // The aggregate answers, but carries no slice for any widget — every widget
    // falls to its empty state at the same instant. Those empty states must be
    // plain text: five live regions inserted with content in one tick is the
    // very chatter the single region exists to replace, one step later in time.
    const { container } = await renderLoadingDashboard();

    aggregateGate.release({});
    await waitFor(() => expect(screen.queryAllByTestId(/^widget-.*-loading$/)).toHaveLength(0));
    expect(screen.getAllByTestId(/^widget-.*-empty$/)).toHaveLength(WIDGET_KEYS.length);

    expect(
      speakingRegions(container).map((r) => r.outerHTML.slice(0, 160)),
      'a settled dashboard announces nothing; the "in preparation" empty state ' +
        'is visible text, not an announcement',
    ).toEqual([]);
  });

  it('announces again when a later aggregate fetch starts', async () => {
    const { store } = await renderLoadingDashboard();
    const region = screen.getByTestId('dashboard-loading-status');

    aggregateGate.release(Object.fromEntries(WIDGET_KEYS.map((k) => [k, { count: 3 }])));
    await waitFor(() => expect(region).toHaveTextContent(''));

    // A refresh — e.g. the user changed the layout — refetches only the
    // aggregate. The catalogue is not touched, so a catalogue-driven region
    // would stay silent through the whole second load.
    armAggregateGate();
    void store.dispatch(fetchAggregated([...WIDGET_KEYS]));
    await waitFor(() => expect(region).toHaveTextContent(LOADING_MESSAGE_EN));
    aggregateGate.release({});
  });

  it('does not refetch the catalogue once it is loaded', async () => {
    const { store } = await renderLoadingDashboard();
    await waitFor(() => expect(store.getState().dashboard.catalogLoaded).toBe(true));

    let catalogRequests = 0;
    server.use(
      http.get('/api/v1/t/:tenant/dashboard/widgets/catalog', () => {
        catalogRequests += 1;
        return HttpResponse.json({ widgets: CATALOG });
      }),
    );

    aggregateGate.release({});
    await waitFor(() => expect(screen.queryAllByTestId(/^widget-.*-loading$/)).toHaveLength(0));
    // Re-navigating onto a cached dashboard must not re-skeleton it.
    renderWithProviders(<DashboardPage />, { store });
    await waitFor(() => expect(screen.getAllByTestId('dashboard-page').length).toBeGreaterThan(1));
    expect(catalogRequests).toBe(0);
  });

  it('keeps aria-busy on the widget placeholders but strips their dropped name', async () => {
    const { container } = await renderLoadingDashboard();

    for (const key of WIDGET_KEYS) {
      const placeholder = screen.getByTestId(`widget-${key}-loading`);
      expect(placeholder).toHaveAttribute('aria-busy', 'true');
      expect(placeholder).not.toHaveAttribute('aria-label');
    }
    expect(droppedNames(container)).toEqual([]);
  });

  it('reports no serious a11y violation while the placeholders stand', async () => {
    const { container } = await renderLoadingDashboard();
    // `aria-prohibited-attr` is `serious`, so the default `critical` floor would
    // not see this defect class at all.
    await expectNoA11yViolations(container, { minImpact: 'serious', minElements: 20 });
  });

  it('carries the announcement in DE and EN', () => {
    const path = ['dashboard', 'loading', 'announcement'];
    const read = (locale: unknown) =>
      path.reduce<unknown>(
        (node, key) => (node as Record<string, unknown> | undefined)?.[key],
        locale,
      );
    expect(read(deFull)).toBe(LOADING_MESSAGE_DE);
    expect(read(enFull)).toBe(LOADING_MESSAGE_EN);
  });
});

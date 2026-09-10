import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterAll, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import i18n from 'i18next';
import TankDetailPage from '@/pages/standorte/TankDetailPage';
import { renderWithProviders, createStoreWithSmartHome } from '../helpers';
import { server } from '../mocks/server';

// Issue #587: tank sensor surfaces are gated behind the smart-home toggle. Render
// with smart home enabled by default; the disabled case has a dedicated test.
const renderPage = (opts?: { route?: string }) =>
  renderWithProviders(<TankDetailPage />, { store: createStoreWithSmartHome(), ...opts });

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (orig) => {
  const actual = await orig<typeof import('react-router-dom')>();
  return { ...actual, useParams: () => ({ key: 'tank-1' }), useNavigate: () => mockNavigate };
});

// Controllable viewport: flip to mobile to exercise DataTable's mobile-card
// renderers (which never run under the default desktop media query).
const mq = vi.hoisted(() => ({ mobile: false }));
vi.mock('@mui/material/useMediaQuery', () => ({ default: () => mq.mobile }));

const baseTank: Record<string, unknown> = {
  key: 'tank-1',
  name: 'Nutrient Tank',
  tank_type: 'nutrient',
  volume_liters: 50,
  material: 'plastic',
  has_lid: true,
  has_air_pump: false,
  has_circulation_pump: false,
  has_heater: false,
  is_light_proof: false,
  has_uv_sterilizer: false,
  has_ozone_generator: false,
  installed_on: null,
  location_key: null,
  notes: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
};

type MountOpts = {
  tank?: Record<string, unknown>;
  latestState?: unknown;
  alerts?: unknown[];
  states?: unknown[];
  due?: unknown[];
  logs?: unknown[];
  schedules?: unknown[];
  fills?: unknown[];
  sensors?: unknown[];
  tsAvailable?: boolean;
  sites?: unknown[];
  location?: unknown;
};

/** Registers all GET handlers the page's load() fan-out needs. */
function mount(opts: MountOpts = {}) {
  const {
    tank = {},
    latestState = null,
    alerts = [],
    states = [],
    due = [],
    logs = [],
    schedules = [],
    fills = [],
    sensors = [],
    tsAvailable = false,
    sites = [{ key: 'site-1', name: 'Greenhouse' }],
    location = null,
  } = opts;
  server.use(
    http.get('/api/v1/t/:tenant/tanks/tank-1', () => HttpResponse.json({ ...baseTank, ...tank })),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    http.get('/api/v1/t/:tenant/tanks/:key/states/latest', () => HttpResponse.json(latestState as any)),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    http.get('/api/v1/t/:tenant/tanks/:key/states', () => HttpResponse.json(states as any)),
    http.get('/api/v1/t/:tenant/tanks/:key/alerts', () => HttpResponse.json(alerts)),
    http.get('/api/v1/t/:tenant/tanks/:key/maintenance/due', () => HttpResponse.json(due)),
    http.get('/api/v1/t/:tenant/tanks/:key/maintenance', () => HttpResponse.json(logs)),
    http.get('/api/v1/t/:tenant/tanks/:key/schedules', () => HttpResponse.json(schedules)),
    http.get('/api/v1/t/:tenant/tanks/:key/fills', () => HttpResponse.json(fills)),
    http.get('/api/v1/t/:tenant/tanks/:key/sensors', () => HttpResponse.json(sensors)),
    http.get('/api/v1/t/:tenant/observations/status', () => HttpResponse.json({ available: tsAvailable })),
    http.get('/api/v1/t/:tenant/sites', () => HttpResponse.json(sites)),
    http.get('/api/v1/t/:tenant/tanks/:key/live-state', () => HttpResponse.json({ available: false })),
    http.get('/api/v1/t/:tenant/ha/*', () => HttpResponse.json({ published: false, available: false })),
  );
  if (location) {
    server.use(http.get('/api/v1/t/:tenant/locations/:key', () => HttpResponse.json(location)));
  }
}

function minutesAgo(min: number): string {
  return new Date(Date.now() - min * 60_000).toISOString();
}

function state(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    key: 'st-1',
    recorded_at: minutesAgo(30),
    source: 'manual',
    ph: null,
    ec_ms: null,
    water_temp_celsius: null,
    fill_level_percent: null,
    fill_level_liters: null,
    dissolved_oxygen_mgl: null,
    orp_mv: null,
    tds_ppm: null,
    ...overrides,
  };
}

describe('TankDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mq.mobile = false;
    i18n.changeLanguage('de');
  });

  afterAll(() => {
    i18n.changeLanguage('en');
  });

  it('renders the tank detail page from the loaded tank', async () => {
    mount();
    renderPage();

    expect(await screen.findByTestId('tank-detail-page')).toBeTruthy();
    expect(screen.getAllByText('Nutrient Tank').length).toBeGreaterThan(0);
    expect(screen.getByTestId('tank-delete-button')).toBeTruthy();
  });

  it('shows the error state when the tank fails to load', async () => {
    server.use(
      http.get('/api/v1/t/:tenant/tanks/tank-1', () =>
        HttpResponse.json({ message: 'boom', error_code: 'INTERNAL_ERROR', details: [] }, { status: 500 }),
      ),
      http.get('/api/v1/t/:tenant/sites', () => HttpResponse.json([])),
    );
    renderPage();
    expect(await screen.findByTestId('error-display')).toBeInTheDocument();
  });

  it('renders equipment, notes, location link and a warning-range latest state (ha_live, recent)', async () => {
    mount({
      tank: {
        location_key: 'loc-1',
        notes: 'Keep covered',
        has_lid: true,
        has_air_pump: true,
        has_circulation_pump: true,
        has_heater: true,
        is_light_proof: true,
        has_uv_sterilizer: true,
        has_ozone_generator: true,
      },
      sites: [{ key: 'site-1', name: 'Greenhouse' }],
      location: { key: 'loc-1', site_key: 'site-1', name: 'Bench', path: 'Greenhouse / Bench' },
      latestState: state({
        source: 'ha_live',
        recorded_at: minutesAgo(30),
        ph: 6.8,
        ec_ms: 3.5,
        water_temp_celsius: 24,
        fill_level_percent: 80,
        fill_level_liters: 40,
        dissolved_oxygen_mgl: 9,
        orp_mv: 400,
      }),
    });
    renderPage();
    await screen.findByTestId('tank-detail-page');

    expect(screen.getByText('Keep covered')).toBeInTheDocument();
    expect(screen.getByText(i18n.t('pages.tanks.equipment'))).toBeInTheDocument();
    expect(screen.getByText('6.8')).toBeInTheDocument();
    expect(screen.getByText('3.5')).toBeInTheDocument();
    expect(screen.getAllByText('Greenhouse').length).toBeGreaterThan(0);
  });

  it('renders an error-range latest state (mqtt_auto, stale)', async () => {
    mount({
      latestState: state({
        source: 'mqtt_auto',
        recorded_at: minutesAgo(120),
        ph: 7.5,
        ec_ms: 4.5,
        water_temp_celsius: 30,
        dissolved_oxygen_mgl: 12,
      }),
    });
    renderPage();
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText('7.5')).toBeInTheDocument();
    expect(screen.getByText(i18n.t('pages.tanks.latestState'))).toBeInTheDocument();
  });

  it('renders a success-range latest state (ha_auto, live)', async () => {
    mount({
      latestState: state({
        source: 'ha_auto',
        recorded_at: minutesAgo(1),
        ph: 6.0,
        ec_ms: 1.5,
        water_temp_celsius: 20,
        dissolved_oxygen_mgl: 6.5,
      }),
    });
    renderPage();
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('renders algae-risk and generic tank alerts', async () => {
    mount({
      alerts: [
        {
          type: 'algae_risk',
          severity: 'high',
          factors: ['no_lid', 'warm_water', 'nutrient_rich'],
          temp: 26,
        },
        { type: 'ph_out_of_range', severity: 'medium', value: 7.8, limit_max: 6.5, message: 'pH too high' },
      ],
    });
    renderPage();
    await screen.findByTestId('tank-detail-page');
    const alerts = screen.getAllByRole('alert');
    expect(alerts.length).toBeGreaterThanOrEqual(2);
  });

  it('renders the states tab with a chart and table, and its empty state', async () => {
    mount({
      states: [
        state({ key: 's1', ph: 6.1, ec_ms: 1.4, water_temp_celsius: 20, fill_level_percent: 70, tds_ppm: 700 }),
        state({ key: 's2', ph: 6.3, ec_ms: 1.6, water_temp_celsius: 21, fill_level_percent: 60, tds_ppm: 720 }),
      ],
    });
    const { unmount } = renderPage({ route: '/#states' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByTestId('tank-record-state-button')).toBeInTheDocument();
    unmount();

    mount({ states: [] });
    renderPage({ route: '/#states' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText(i18n.t('pages.tanks.noMeasurements'))).toBeInTheDocument();
  });

  it('renders the maintenance tab with due maintenances, logs and the overdue quick-info chip', async () => {
    mount({
      due: [
        { schedule_key: 'sc-1', maintenance_type: 'cleaning', next_due: '2024-06-01', status: 'overdue', priority: 'high' },
        { schedule_key: 'sc-2', maintenance_type: 'calibration', next_due: '2024-06-10', status: 'due_soon', priority: 'medium' },
        { schedule_key: 'sc-3', maintenance_type: 'inspection', next_due: '2024-07-10', status: 'ok', priority: 'low' },
      ],
      logs: [
        { key: 'log-1', maintenance_type: 'cleaning', performed_at: '2024-05-01T09:00:00Z', performed_by: 'Sam', duration_minutes: 30, notes: 'done' },
      ],
    });
    renderPage({ route: '/#maintenance' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText(i18n.t('pages.tanks.dueMaintenances'))).toBeInTheDocument();
    expect(screen.getByTestId('tank-log-maintenance-button')).toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });

  it('renders the empty maintenance history state', async () => {
    mount({ due: [], logs: [] });
    renderPage({ route: '/#maintenance' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText(i18n.t('pages.tanks.noMaintenanceLogs'))).toBeInTheDocument();
  });

  it('renders schedules and deletes one through the confirm dialog', async () => {
    mount({
      schedules: [
        { key: 'sched-1', maintenance_type: 'cleaning', interval_days: 14, reminder_days_before: 2, priority: 'high', is_active: true },
        { key: 'sched-2', maintenance_type: 'calibration', interval_days: 30, reminder_days_before: 3, priority: 'low', is_active: false },
      ],
    });
    let deleted = false;
    server.use(
      http.delete('/api/v1/t/:tenant/tanks/:key/schedules/:scheduleKey', () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderPage({ route: '/#schedules' });
    await screen.findByTestId('tank-detail-page');

    await user.click(screen.getByTestId('schedule-delete-sched-1'));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));
    await waitFor(() => expect(deleted).toBe(true));
  });

  it('renders the empty schedules state', async () => {
    mount({ schedules: [] });
    renderPage({ route: '/#schedules' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText(i18n.t('pages.tanks.noSchedules'))).toBeInTheDocument();
  });

  it('renders the fills tab with fill events and its empty state', async () => {
    mount({
      fills: [
        { key: 'fill-1', filled_at: '2024-05-05T10:00:00Z', fill_type: 'refill', volume_liters: 20, measured_ec_ms: 1.1, measured_ph: 6.2, water_source: 'tap' },
      ],
    });
    const { unmount } = renderPage({ route: '/#fills' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByTestId('tank-record-fill-button')).toBeInTheDocument();
    unmount();

    mount({ fills: [] });
    renderPage({ route: '/#fills' });
    await screen.findByTestId('tank-detail-page');
    expect(screen.getByText(i18n.t('pages.tanks.noFills'))).toBeInTheDocument();
  });

  it('renders the edit tab and saves the tank', async () => {
    mount();
    let saved = false;
    server.use(
      http.put('/api/v1/t/:tenant/tanks/tank-1', () => {
        saved = true;
        return HttpResponse.json({ ...baseTank });
      }),
    );
    const user = userEvent.setup();
    renderPage({ route: '/#edit' });
    await screen.findByTestId('tank-detail-page');

    const airPump = await screen.findByTestId('form-field-has_air_pump');
    await user.click(airPump.querySelector('input')!);
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(saved).toBe(true));
  });

  it('deletes a sensor from the edit tab through the confirm dialog', async () => {
    mount({
      sensors: [
        { key: 'sensor-1', name: 'pH Probe', metric_type: 'ph', ha_entity_id: 'sensor.ph', is_active: true, unit_of_measurement: 'pH' },
      ],
    });
    // Registered on `/tanks/sensors/{key}` until #1339 — a path no backend route
    // has ever served. The doubled boundary answered it anyway, so this test was
    // green while every real delete returned 404. The concrete pathname is
    // asserted, not just "some delete arrived": a pattern handler matches
    // `/tanks/sensor-1/sensors/undefined` too, which is exactly what the
    // pre-#1339 call shape would have produced against the new route.
    let deleted: string | null = null;
    server.use(
      http.delete('/api/v1/t/:tenant/tanks/:tankKey/sensors/:sensorKey', ({ request }) => {
        deleted = new URL(request.url).pathname;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderPage({ route: '/#edit' });
    await screen.findByTestId('tank-detail-page');

    await user.click(await screen.findByTestId('sensor-delete-sensor-1'));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));
    await waitFor(() =>
      expect(deleted).toBe('/api/v1/t/test-tenant/tanks/tank-1/sensors/sensor-1'),
    );
  });

  it('deletes the tank through the confirm dialog and navigates to the list', async () => {
    mount();
    server.use(http.delete('/api/v1/t/:tenant/tanks/tank-1', () => new HttpResponse(null, { status: 204 })));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('tank-detail-page');
    await user.click(screen.getByTestId('tank-delete-button'));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/standorte/tanks'));
  });

  it('shows the pending state on the confirm dialog while deleting the tank', async () => {
    mount();
    let release!: () => void;
    const gate = new Promise<void>((res) => {
      release = res;
    });
    server.use(
      http.delete('/api/v1/t/:tenant/tanks/tank-1', async () => {
        await gate;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('tank-detail-page');
    await user.click(screen.getByTestId('tank-delete-button'));
    const confirm = await screen.findByTestId('confirm-dialog-confirm');
    await user.click(confirm);

    await waitFor(() => expect(confirm).toBeDisabled());
    expect(screen.getByTestId('confirm-dialog-live-region')).toHaveTextContent(
      i18n.t('common.processing'),
    );
    release();
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/standorte/tanks'));
  });

  it('surfaces an error and does not navigate when deletion fails', async () => {
    mount();
    server.use(
      http.delete('/api/v1/t/:tenant/tanks/tank-1', () =>
        HttpResponse.json(
          { error_id: 'e1', error_code: 'INTERNAL_ERROR', message: 'boom', details: [], timestamp: '', path: '', method: '' },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('tank-detail-page');
    await user.click(screen.getByTestId('tank-delete-button'));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    expect(await screen.findByText(i18n.t('errors.server'))).toBeTruthy();
    expect(mockNavigate).not.toHaveBeenCalledWith('/standorte/tanks');
  });

  it('cancels the delete confirmation without deleting', async () => {
    mount();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('tank-detail-page');
    await user.click(screen.getByTestId('tank-delete-button'));
    await user.click(await screen.findByTestId('confirm-dialog-cancel'));

    await waitFor(() => expect(screen.queryByTestId('confirm-dialog')).toBeNull());
    expect(mockNavigate).not.toHaveBeenCalledWith('/standorte/tanks');
  });

  it('renders all data tabs in the mobile viewport (mobile-card renderers)', async () => {
    mq.mobile = true;
    mount({
      latestState: state({ source: 'ha_live', ph: 6.2, ec_ms: 1.5, water_temp_celsius: 20, fill_level_percent: 70 }),
      states: [
        state({ key: 's1', ph: 6.1, ec_ms: 1.4, water_temp_celsius: 20, fill_level_percent: 70 }),
        state({ key: 's2', ph: 6.3, ec_ms: 1.6, water_temp_celsius: 21, fill_level_percent: 60 }),
      ],
      due: [{ schedule_key: 'sc-1', maintenance_type: 'cleaning', next_due: '2024-06-01', status: 'due_soon', priority: 'high' }],
      logs: [{ key: 'log-1', maintenance_type: 'cleaning', performed_at: '2024-05-01T09:00:00Z', performed_by: 'Sam', duration_minutes: 30, notes: 'n' }],
      schedules: [{ key: 'sched-1', maintenance_type: 'cleaning', interval_days: 14, reminder_days_before: 2, priority: 'high', is_active: true }],
      fills: [{ key: 'fill-1', filled_at: '2024-05-05T10:00:00Z', fill_type: 'refill', volume_liters: 20, measured_ec_ms: 1.1, measured_ph: 6.2, water_source: 'tap' }],
    });

    for (const route of ['/#states', '/#maintenance', '/#schedules', '/#fills']) {
      const { unmount } = renderPage({ route });
      await screen.findByTestId('tank-detail-page');
      unmount();
    }
  });

  it('opens the create dialogs from each tab action button', async () => {
    mount();
    const user = userEvent.setup();

    const cases: Array<[string, string]> = [
      ['/#states', 'tank-record-state-button'],
      ['/#maintenance', 'tank-log-maintenance-button'],
      ['/#schedules', 'tank-create-schedule-button'],
      ['/#fills', 'tank-record-fill-button'],
    ];
    for (const [route, testid] of cases) {
      const { unmount } = renderPage({ route });
      await screen.findByTestId('tank-detail-page');
      await user.click(screen.getByTestId(testid));
      // a dialog opens
      await screen.findByRole('dialog');
      unmount();
    }
  });

  it('opens create dialogs from the empty-state action buttons', async () => {
    mount({ states: [], logs: [], due: [], schedules: [], fills: [] });
    const user = userEvent.setup();

    const routes = ['/#states', '/#maintenance', '/#schedules', '/#fills'];
    for (const route of routes) {
      const { unmount } = renderPage({ route });
      await screen.findByTestId('tank-detail-page');
      // EmptyState renders its own action button with the same label as the header
      const buttons = screen.getAllByRole('button');
      // click the last action button (the empty-state CTA)
      const cta = buttons[buttons.length - 1];
      await user.click(cta);
      unmount();
    }
  });

  it('navigates via the overdue quick-info chip and switches tabs', async () => {
    mount({
      due: [{ schedule_key: 'sc-1', maintenance_type: 'cleaning', next_due: '2024-06-01', status: 'overdue', priority: 'high' }],
    });
    const user = userEvent.setup();
    renderPage();
    await screen.findByTestId('tank-detail-page');

    // overdue quick-info chip is clickable
    await user.click(screen.getByText(i18n.t('pages.tanks.quickInfoDueMaint', { count: 1 })));
    // switch to the states tab through the tab bar
    await user.click(screen.getByRole('tab', { name: i18n.t('pages.tanks.tabStates') }));
    expect(screen.getByTestId('tank-detail-page')).toBeInTheDocument();
  });

  it('changes the site in the edit tab and cancels the form', async () => {
    mount({ sites: [{ key: 'site-1', name: 'Greenhouse' }, { key: 'site-2', name: 'Balcony' }] });
    const user = userEvent.setup();
    renderPage({ route: '/#edit' });
    await screen.findByTestId('tank-detail-page');

    // open the MUI site select and choose an option (drives handleSiteChange)
    const siteField = screen.getByTestId('form-field-site');
    await user.click(within(siteField).getByRole('combobox'));
    await user.click(await screen.findByRole('option', { name: 'Balcony' }));

    // FormActions cancel resets the form
    await user.click(screen.getByTestId('form-cancel-button'));
    expect(screen.getByTestId('tank-detail-page')).toBeInTheDocument();
  });

  it('opens the add-sensor dialog and cancels a sensor delete', async () => {
    mount({
      sensors: [
        { key: 'sensor-1', name: 'pH Probe', metric_type: 'ph', ha_entity_id: 'sensor.ph', is_active: true, unit_of_measurement: 'pH' },
      ],
    });
    const user = userEvent.setup();
    renderPage({ route: '/#edit' });
    await screen.findByTestId('tank-detail-page');

    await user.click(screen.getByTestId('tank-add-sensor-button'));
    await screen.findByRole('dialog');
    // close via Escape to reach the onClose handler
    await user.keyboard('{Escape}');

    await user.click(await screen.findByTestId('sensor-delete-sensor-1'));
    await user.click(await screen.findByTestId('confirm-dialog-cancel'));
    await waitFor(() => expect(screen.queryByTestId('confirm-dialog')).toBeNull());
  });

  it('renders sensor history charts when timeseries is available', async () => {
    mount({
      tsAvailable: true,
      sensors: [
        { key: 'sensor-1', name: 'pH Probe', metric_type: 'ph', ha_entity_id: 'sensor.ph', is_active: true, unit_of_measurement: 'pH' },
      ],
    });
    server.use(
      http.get('/api/v1/observations/status', () => HttpResponse.json({ available: true })),
      http.get('/api/v1/observations/*', () => HttpResponse.json([])),
      http.get('/api/v1/t/:tenant/observations/*', () => HttpResponse.json([])),
    );
    renderPage();
    await screen.findByTestId('tank-detail-page');
    expect(await screen.findByText(i18n.t('pages.tanks.sensorHistory'))).toBeInTheDocument();
  });

  it('hides tank sensor surfaces when smart home is disabled (#587)', async () => {
    mount({
      tsAvailable: true,
      sensors: [
        { key: 'sensor-1', name: 'pH Probe', metric_type: 'ph', ha_entity_id: 'sensor.ph', is_active: true, unit_of_measurement: 'pH' },
      ],
    });
    server.use(
      http.get('/api/v1/observations/status', () => HttpResponse.json({ available: true })),
      http.get('/api/v1/observations/*', () => HttpResponse.json([])),
      http.get('/api/v1/t/:tenant/observations/*', () => HttpResponse.json([])),
    );
    // Default store → smart_home_enabled falsy → sensor card + history hidden.
    renderWithProviders(<TankDetailPage />, { route: '/#edit' });
    await screen.findByTestId('tank-detail-page');

    expect(screen.queryByTestId('tank-sensors-section')).toBeNull();
    expect(screen.queryByTestId('tank-add-sensor-button')).toBeNull();
    expect(screen.queryByText(i18n.t('pages.tanks.sensorHistory'))).toBeNull();
  });
});

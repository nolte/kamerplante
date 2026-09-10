import { cleanup, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import i18n from 'i18next';
import LocationDetailPage from '@/pages/standorte/LocationDetailPage';
import { renderWithProviders, createStoreWithSmartHome } from '../helpers';
import { server } from '../mocks/server';

// Issue #587: sensor UI is gated behind the smart-home toggle. Default the page
// renders with smart home enabled so the existing sensor assertions hold; the
// disabled (hidden) case is covered by a dedicated test.
const renderPage = () =>
  renderWithProviders(<LocationDetailPage />, { store: createStoreWithSmartHome() });

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (orig) => {
  const actual = await orig<typeof import('react-router-dom')>();
  return { ...actual, useParams: () => ({ key: 'loc-1' }), useNavigate: () => mockNavigate };
});

const baseLocation = {
  key: 'loc-1',
  site_key: 'site-1',
  name: 'Zone A',
  location_type_key: 'lt-bed',
  parent_location_key: null as string | null,
  depth: 0,
  path: 'Zone A',
  area_m2: 5,
  light_type: 'led',
  irrigation_system: 'drip',
  lights_on: '06:00',
  lights_off: '00:00',
  use_dynamic_sunrise: false,
  tank_key: null as string | null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
};

const slot = {
  key: 'slot-1',
  location_key: 'loc-1',
  slot_id: 'A1',
  position: [1, 2] as [number, number],
  capacity_plants: 4,
  currently_occupied: true,
  last_sanitization: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
};

const childLocation = {
  ...baseLocation,
  key: 'loc-child',
  name: 'Bed 1',
  parent_location_key: 'loc-1',
  area_m2: 2,
};

const tank = { key: 'tank-1', name: 'Tank One', volume_liters: 100, location_key: 'loc-1' };

const sensor = {
  key: 'sensor-1',
  name: 'Soil Sensor',
  metric_type: 'moisture',
  ha_entity_id: 'sensor.soil',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
};

const run = {
  key: 'run-1',
  name: 'Run Alpha',
  status: 'active',
  run_type: 'batch',
  actual_quantity: 3,
  location_key: 'loc-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
};

const runPlant = { key: 'plant-in-run', instance_id: 'TOM-001' };

const standaloneInstance = {
  key: 'plant-solo',
  instance_id: 'TOM-002',
  species_key: 'sp-1',
  cultivar_key: null,
  slot_key: null,
  substrate_batch_key: null,
  plant_name: 'Solo Plant',
  planted_on: '2024-03-15',
  removed_on: null,
  current_phase: 'vegetative',
  current_phase_key: null,
  current_phase_started_at: null,
  location_key: 'loc-1',
  created_at: '2024-03-15T00:00:00Z',
  updated_at: null,
};

const wateringEvent = {
  key: 'we-1',
  location_key: 'loc-1',
  watered_at: '2024-05-01T08:00:00Z',
  application_method: 'drip',
  volume_liters: 3,
  plant_keys: ['plant-solo'],
  water_source: 'tap',
  created_at: '2024-05-01T00:00:00Z',
  updated_at: null,
};

const wateringStats = {
  total_events: 5,
  total_volume: 15,
  by_method: [{ method: 'drip', count: 3, total_volume: 9 }],
};

function errorEnvelope(status: number) {
  return HttpResponse.json(
    {
      error_id: 'e1',
      error_code: 'INTERNAL_ERROR',
      message: 'boom',
      details: [],
      timestamp: '',
      path: '',
      method: '',
    },
    { status },
  );
}

/** Seeds a fully-populated location: parent chain, slots, children, tank,
 *  watering data, sensors, an assigned run and a standalone plant instance. */
function useFullLocation(locOverrides: Record<string, unknown> = {}) {
  const location = { ...baseLocation, parent_location_key: 'loc-parent', tank_key: 'tank-1', ...locOverrides };
  server.use(
    http.get('/api/v1/t/:tenant/locations/:key', ({ params }) => {
      if (params.key === 'loc-parent') {
        return HttpResponse.json({ ...baseLocation, key: 'loc-parent', name: 'Parent Zone', parent_location_key: null });
      }
      return HttpResponse.json(location);
    }),
    http.get('/api/v1/t/:tenant/sites/:key', () =>
      HttpResponse.json({ key: 'site-1', name: 'Main Greenhouse', type: 'greenhouse' }),
    ),
    http.get('/api/v1/t/:tenant/slots', () => HttpResponse.json([slot])),
    http.get('/api/v1/t/:tenant/locations/:key/children', () => HttpResponse.json([childLocation])),
    http.get('/api/v1/t/:tenant/tanks/:key', () => HttpResponse.json(tank)),
    http.get('/api/v1/t/:tenant/tanks', () => HttpResponse.json([tank])),
    http.get('/api/v1/t/:tenant/locations/:key/watering-events', () => HttpResponse.json([wateringEvent])),
    http.get('/api/v1/t/:tenant/locations/:key/watering-stats', () => HttpResponse.json(wateringStats)),
    http.get('/api/v1/t/:tenant/locations/:key/sensors', () => HttpResponse.json([sensor])),
    http.get('/api/v1/t/:tenant/planting-runs', () => HttpResponse.json([run])),
    http.get('/api/v1/t/:tenant/planting-runs/:key/plants', () => HttpResponse.json([runPlant])),
    http.get('/api/v1/t/:tenant/plant-instances', () =>
      HttpResponse.json([{ ...runPlant, location_key: 'loc-1' }, standaloneInstance]),
    ),
  );
}

/** A location whose collaborators exercise the alternate ("empty field")
 *  branches: no tank_key (tank resolved via fallback list), a failing parent
 *  and site fetch, a not-occupied slot, a typeless child, a null-scheduled
 *  mixed-light location, a nameless standalone plant, a timeless watering event
 *  and an inactive sensor without an HA entity. */
function useVariantLocation() {
  server.use(
    http.get('/api/v1/t/:tenant/locations/:key', ({ params }) => {
      // Parent lookup fails -> the ancestor loop breaks (catch path).
      if (params.key === 'loc-parent') return errorEnvelope(500);
      return HttpResponse.json({
        ...baseLocation,
        light_type: 'mixed',
        lights_on: null,
        lights_off: null,
        use_dynamic_sunrise: true,
        parent_location_key: 'loc-parent',
        tank_key: null,
      });
    }),
    // Site fetch fails -> siteName stays empty (no site breadcrumb).
    http.get('/api/v1/t/:tenant/sites/:key', () => errorEnvelope(404)),
    http.get('/api/v1/t/:tenant/slots', () =>
      HttpResponse.json([{ ...slot, currently_occupied: false, position: [0, 0] }]),
    ),
    http.get('/api/v1/t/:tenant/locations/:key/children', () =>
      HttpResponse.json([{ ...childLocation, location_type_key: null }]),
    ),
    // No tank_key on the location -> fallback list resolves the assigned tank.
    http.get('/api/v1/t/:tenant/tanks', () => HttpResponse.json([tank])),
    http.get('/api/v1/t/:tenant/locations/:key/watering-events', () =>
      HttpResponse.json([{ ...wateringEvent, watered_at: null, water_source: null }]),
    ),
    http.get('/api/v1/t/:tenant/locations/:key/watering-stats', () => HttpResponse.json(wateringStats)),
    http.get('/api/v1/t/:tenant/locations/:key/sensors', () =>
      HttpResponse.json([{ ...sensor, ha_entity_id: '', is_active: false }]),
    ),
    http.get('/api/v1/t/:tenant/planting-runs', () =>
      HttpResponse.json([{ ...run, status: 'planned', run_type: 'succession' }]),
    ),
    http.get('/api/v1/t/:tenant/planting-runs/:key/plants', () => HttpResponse.json([runPlant])),
    http.get('/api/v1/t/:tenant/plant-instances', () =>
      HttpResponse.json([
        { ...runPlant, location_key: 'loc-1' },
        { ...standaloneInstance, plant_name: null, current_phase: null, planted_on: null },
      ]),
    ),
  );
}

/** Minimal, empty deps — no children/slots/runs/etc. (all empty states). */
function useEmptyLocation() {
  server.use(
    http.get('/api/v1/t/:tenant/locations/:key/children', () => HttpResponse.json([])),
    http.get('/api/v1/t/:tenant/slots', () => HttpResponse.json([])),
    http.get('/api/v1/t/:tenant/tanks', () => HttpResponse.json([])),
    http.get('/api/v1/t/:tenant/locations/:key/sensors', () => HttpResponse.json([])),
    http.get('/api/v1/t/:tenant/planting-runs', () => HttpResponse.json([])),
    http.get('/api/v1/t/:tenant/plant-instances', () => HttpResponse.json([])),
  );
}

function useDeleteResponse(status: number) {
  server.use(
    http.delete('/api/v1/t/:tenant/locations/:key', () =>
      status < 400 ? new HttpResponse(null, { status }) : errorEnvelope(status),
    ),
  );
}

describe('LocationDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    i18n.changeLanguage('de');
  });
  afterEach(() => {
    // Unmount before resetting the language: the file's afterEach runs before
    // testing-library's auto-cleanup (LIFO), so an i18n reset here would
    // otherwise re-render every still-mounted useTranslation() consumer
    // outside act(). Unmounting first makes the reset touch nothing.
    cleanup();
    vi.unstubAllGlobals();
    i18n.changeLanguage('en');
  });

  it('renders a fully populated location with all sections', async () => {
    useFullLocation();
    renderPage();

    expect(await screen.findByTestId('location-detail-page')).toBeTruthy();
    expect(screen.getAllByText('Zone A').length).toBeGreaterThan(0);
    // Assigned tank chip, sub-location, slot, run, standalone plant, sensor.
    expect(await screen.findByText(/Tank One/)).toBeTruthy();
    expect(await screen.findByText('Bed 1')).toBeTruthy();
    expect(await screen.findByText('A1')).toBeTruthy();
    expect(await screen.findByText('Run Alpha')).toBeTruthy();
    expect(await screen.findByText('TOM-002')).toBeTruthy();
    expect(await screen.findByText('Soil Sensor')).toBeTruthy();
    // Watering stats card total.
    expect(await screen.findByText('15 L')).toBeTruthy();
  });

  it('renders the empty states and triggers their create actions', async () => {
    useEmptyLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    expect(await screen.findByText(i18n.t('pages.locations.noPlantsOrRuns'))).toBeTruthy();
    // No tank assigned.
    expect(screen.getByText(i18n.t('pages.locations.noTank'))).toBeTruthy();

    // Each empty state that carries a create action opens the matching dialog.
    // DOM order of action-bearing empty states: sub-locations, slots, sensors.
    const actions = screen.getAllByTestId('empty-state-action');
    expect(actions.length).toBeGreaterThanOrEqual(3);
    for (const action of actions) {
      await user.click(action);
      expect(await screen.findByRole('dialog')).toBeTruthy();
      await user.keyboard('{Escape}');
      await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    }
  });

  it('opens the sensor create dialog from the add button', async () => {
    useEmptyLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByTestId('add-sensor-button'));
    expect(await screen.findByRole('dialog')).toBeTruthy();
  });

  it('hides the sensor section when smart home is disabled (#587)', async () => {
    useEmptyLocation();
    // Default store → smart_home_enabled falsy → sensor surfaces hidden.
    renderWithProviders(<LocationDetailPage />);

    await screen.findByTestId('location-detail-page');
    expect(screen.queryByTestId('location-sensors-section')).toBeNull();
    expect(screen.queryByTestId('add-sensor-button')).toBeNull();
  });

  it('renders the alternate field variants (empty/inactive collaborators)', async () => {
    useVariantLocation();
    renderPage();

    await screen.findByTestId('location-detail-page');
    // Tank resolved through the fallback list despite no tank_key.
    expect(await screen.findByText(/Tank One/)).toBeTruthy();
    // Mixed light type keeps showing the dynamic-sunrise switch.
    expect(screen.getByText(i18n.t('pages.locations.useDynamicSunrise'))).toBeTruthy();
    // Standalone plant with no name and no phase still lists its instance id.
    expect(await screen.findByText('TOM-002')).toBeTruthy();
    // Inactive sensor without an HA entity id renders a placeholder cell.
    expect(await screen.findByText('Soil Sensor')).toBeTruthy();
  });

  it('renders the alternate field variants as mobile cards', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }));
    useVariantLocation();
    renderPage();

    await screen.findByTestId('location-detail-page');
    expect(await screen.findAllByText('Soil Sensor')).toBeTruthy();
    expect(screen.getAllByText('TOM-002').length).toBeGreaterThan(0);
  });

  it('saves a location with a cleared light schedule', async () => {
    useVariantLocation();
    let putBody: Record<string, unknown> | null = null;
    server.use(
      http.put('/api/v1/t/:tenant/locations/:key', async ({ request }) => {
        putBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...baseLocation, ...putBody });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByTestId('form-submit-button'));

    await waitFor(() => expect(putBody).not.toBeNull());
    // Empty schedule fields collapse to undefined in the payload.
    expect(putBody!.lights_on).toBeUndefined();
    expect(putBody!.lights_off).toBeUndefined();
  });

  it('shows the error state when the location fetch fails', async () => {
    server.use(http.get('/api/v1/t/:tenant/locations/:key', () => errorEnvelope(500)));
    renderPage();

    expect(await screen.findByTestId('error-display')).toBeTruthy();
    expect(screen.queryByTestId('location-detail-page')).toBeNull();
  });

  it('renders the dynamic-sunrise switch for a natural light type', async () => {
    useFullLocation({ light_type: 'natural', use_dynamic_sunrise: true });
    renderPage();

    await screen.findByTestId('location-detail-page');
    expect(await screen.findByText(i18n.t('pages.locations.useDynamicSunrise'))).toBeTruthy();
  });

  it('saves the edited location and notifies success', async () => {
    useFullLocation();
    let putBody: Record<string, unknown> | null = null;
    server.use(
      http.put('/api/v1/t/:tenant/locations/:key', async ({ request }) => {
        putBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ ...baseLocation, ...putBody });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByTestId('form-submit-button'));

    await waitFor(() => expect(putBody).not.toBeNull());
    expect(putBody!.name).toBe('Zone A');
    expect(putBody!.lights_on).toBe('06:00');
  });

  it('surfaces an API error when saving the location fails', async () => {
    useFullLocation();
    server.use(http.put('/api/v1/t/:tenant/locations/:key', () => errorEnvelope(500)));
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByTestId('form-submit-button'));

    expect(await screen.findByText(i18n.t('errors.server'))).toBeTruthy();
  });

  it('navigates back when cancelling the form', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByTestId('form-cancel-button'));
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('navigates to the assigned tank on chip click', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(await screen.findByText(/Tank One/));
    expect(mockNavigate).toHaveBeenCalledWith('/standorte/tanks/tank-1');
  });

  it('navigates from the run, plant, sub-location and slot rows', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');

    await user.click(await screen.findByText('Run Alpha'));
    expect(mockNavigate).toHaveBeenCalledWith('/durchlaeufe/planting-runs/run-1');

    await user.click(screen.getByText('TOM-002'));
    expect(mockNavigate).toHaveBeenCalledWith('/pflanzen/plant-instances/plant-solo');

    await user.click(screen.getByText('Bed 1'));
    expect(mockNavigate).toHaveBeenCalledWith('/standorte/locations/loc-child');

    await user.click(screen.getByText('A1'));
    expect(mockNavigate).toHaveBeenCalledWith('/standorte/slots/slot-1');
  });

  it('opens the create dialogs from their add buttons', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');

    await user.click(screen.getByTestId('add-sublocation-button'));
    expect(await screen.findByRole('dialog')).toBeTruthy();
    // Close by pressing Escape so the next dialog can be asserted cleanly.
    await user.keyboard('{Escape}');

    await user.click(screen.getByTestId('create-slot-button'));
    expect(await screen.findByRole('dialog')).toBeTruthy();
    await user.keyboard('{Escape}');

    await user.click(screen.getByTestId('create-watering-button'));
    expect(await screen.findByRole('dialog')).toBeTruthy();
  });

  it('opens the sensor edit dialog from the row action', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    const sensorRow = (await screen.findByText('Soil Sensor')).closest('tr')!;
    await user.click(within(sensorRow).getByTestId('EditIcon').closest('button')!);
    expect(await screen.findByRole('dialog')).toBeTruthy();
  });

  it('deletes a sensor through its confirm dialog', async () => {
    useFullLocation();
    // Registered on `/tanks/sensors/{key}` until #1339 — a path no backend route
    // has ever served. The doubled boundary answered it anyway, so this test was
    // green while every real delete returned 404. The concrete pathname is
    // asserted, because a pattern handler also matches a call with the sensor
    // key in the parent position.
    let deleteCalled: string | null = null;
    server.use(
      http.delete('/api/v1/t/:tenant/locations/:locationKey/sensors/:key', ({ request }) => {
        deleteCalled = new URL(request.url).pathname;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    const sensorRow = (await screen.findByText('Soil Sensor')).closest('tr')!;
    await user.click(within(sensorRow).getByTestId('DeleteIcon').closest('button')!);
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    await waitFor(() =>
      expect(deleteCalled).toBe('/api/v1/t/test-tenant/locations/loc-1/sensors/sensor-1'),
    );
  });

  it('surfaces an error when sensor deletion fails', async () => {
    useFullLocation();
    server.use(
      http.delete('/api/v1/t/:tenant/locations/:locationKey/sensors/:key', () => errorEnvelope(500)),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    const sensorRow = (await screen.findByText('Soil Sensor')).closest('tr')!;
    await user.click(within(sensorRow).getByTestId('DeleteIcon').closest('button')!);
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    expect(await screen.findByText(i18n.t('errors.server'))).toBeTruthy();
  });

  it('renders the tables as mobile cards on a small screen', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }));
    useFullLocation();
    renderPage();

    await screen.findByTestId('location-detail-page');
    expect(await screen.findAllByText('Soil Sensor')).toBeTruthy();
    expect(screen.getAllByText('A1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Run Alpha').length).toBeGreaterThan(0);
  });

  it('deletes the location through the confirm dialog and navigates back', async () => {
    useFullLocation();
    useDeleteResponse(204);
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByRole('button', { name: i18n.t('common.delete') }));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(-1));
    await waitFor(() =>
      expect(screen.queryByTestId('confirm-dialog')).toBeNull(),
    );
  });

  it('shows the pending state on the delete dialog while deleting', async () => {
    useFullLocation();
    server.use(
      http.delete('/api/v1/t/:tenant/locations/:key', async () => {
        await delay(60);
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByRole('button', { name: i18n.t('common.delete') }));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('confirm-dialog-confirm')).toBeDisabled(),
    );
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith(-1));
  });

  it('surfaces an error and does not navigate when deletion fails', async () => {
    useFullLocation();
    useDeleteResponse(500);
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByRole('button', { name: i18n.t('common.delete') }));
    await user.click(await screen.findByTestId('confirm-dialog-confirm'));

    expect(await screen.findByText(i18n.t('errors.server'))).toBeTruthy();
    expect(mockNavigate).not.toHaveBeenCalledWith(-1);
  });

  it('cancels the delete confirmation without deleting', async () => {
    useFullLocation();
    const user = userEvent.setup();
    renderPage();

    await screen.findByTestId('location-detail-page');
    await user.click(screen.getByRole('button', { name: i18n.t('common.delete') }));
    await user.click(await screen.findByTestId('confirm-dialog-cancel'));

    await waitFor(() =>
      expect(screen.queryByTestId('confirm-dialog')).toBeNull(),
    );
    expect(mockNavigate).not.toHaveBeenCalledWith(-1);
  });
});

import { describe, it, expect, beforeEach, afterAll, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import i18n from 'i18next';
import SensorCreateDialog, {
  type SensorContext,
} from '@/pages/standorte/SensorCreateDialog';
import { renderWithProviders } from '../helpers';
import { server } from '../mocks/server';
import type { Sensor } from '@/api/types';

/**
 * P7e — SensorCreateDialog. A leaf dialog opened by SiteDetailPage /
 * LocationDetailPage / TankDetailPage. Rendered as a unit; every collaborator
 * (HA-entity discovery + the three create endpoints + the update endpoint) is
 * doubled at the process boundary via msw. Asserts observable output and the
 * onSaved/onClose callbacks — never internal form state.
 */

const HA_ENTITIES = [
  {
    entity_id: 'sensor.ph_probe',
    friendly_name: 'pH Probe',
    unit_of_measurement: 'pH',
    device_class: null,
    state: '6.2',
    suggested_metric_type: 'ph',
    suggested_name: 'Reservoir pH',
  },
  {
    entity_id: 'sensor.plain',
    friendly_name: 'Plain Sensor',
    unit_of_measurement: null,
    device_class: null,
    state: null,
    suggested_metric_type: null,
    suggested_name: null,
  },
];

const EDIT_SENSOR: Sensor = {
  key: 'sensor-9',
  name: 'Existing Probe',
  metric_type: 'ph',
  ha_entity_id: 'sensor.ph_probe',
  unit_of_measurement: 'pH',
  mqtt_topic: 'tanks/ph',
  tank_key: 'tank-1',
  site_key: null,
  location_key: null,
  is_active: true,
};

interface Opts {
  haEntities?: unknown[];
  createStatus?: number;
}

/**
 * Paths the dialog actually requested, in order.
 *
 * The update handler below used to be registered on
 * `/tanks/sensors/:sensorKey` — a path no backend route has ever served, so
 * the doubled boundary certified the wrong contract and the edit test was green
 * while every real edit answered 404 (#1339). Recording the URL is what makes
 * the reshape falsifiable here: an assertion on `onSaved` alone passes against
 * any path msw happens to be told about.
 */
const requested: string[] = [];

function registerHandlers(opts: Opts = {}) {
  const { haEntities = [], createStatus } = opts;
  requested.length = 0;
  const ok = <T,>(body: T) => HttpResponse.json(body as unknown as Record<string, unknown>);
  const err = () =>
    HttpResponse.json(
      { error_id: 'e', error_code: 'INTERNAL_ERROR', message: 'boom', details: [], timestamp: '', path: '', method: '' },
      { status: 500 },
    );
  server.use(
    http.get('/api/v1/t/:tenant/tanks/ha-entities', () => HttpResponse.json(haEntities)),
    http.post('/api/v1/t/:tenant/tanks/:tankKey/sensors', () =>
      createStatus ? err() : ok({ ...EDIT_SENSOR, key: 'new-1' }),
    ),
    http.post('/api/v1/t/:tenant/sites/:siteKey/sensors', () =>
      createStatus ? err() : ok({ ...EDIT_SENSOR, key: 'new-2' }),
    ),
    http.post('/api/v1/t/:tenant/locations/:locKey/sensors', () =>
      createStatus ? err() : ok({ ...EDIT_SENSOR, key: 'new-3' }),
    ),
    // One update route per parent, exactly as the backend serves them: a sensor
    // carries no tenant of its own, so its parent is the tenant anchor.
    http.put('/api/v1/t/:tenant/tanks/:tankKey/sensors/:sensorKey', ({ request }) => {
      requested.push(new URL(request.url).pathname);
      return createStatus ? err() : ok({ ...EDIT_SENSOR });
    }),
    http.put('/api/v1/t/:tenant/sites/:siteKey/sensors/:sensorKey', ({ request }) => {
      requested.push(new URL(request.url).pathname);
      return createStatus ? err() : ok({ ...EDIT_SENSOR });
    }),
    http.put('/api/v1/t/:tenant/locations/:locKey/sensors/:sensorKey', ({ request }) => {
      requested.push(new URL(request.url).pathname);
      return createStatus ? err() : ok({ ...EDIT_SENSOR });
    }),
  );
}

type MountProps = {
  open?: boolean;
  context?: SensorContext;
  sensor?: Sensor;
  onClose?: () => void;
  onSaved?: () => void;
};

function mount(props: MountProps = {}) {
  const onClose = props.onClose ?? vi.fn();
  const onSaved = props.onSaved ?? vi.fn();
  const utils = renderWithProviders(
    <SensorCreateDialog
      open={props.open ?? true}
      onClose={onClose}
      onSaved={onSaved}
      context={props.context ?? { parentType: 'tank', parentKey: 'tank-1' }}
      sensor={props.sensor}
    />,
  );
  return { ...utils, onClose, onSaved };
}

async function fillName(user: ReturnType<typeof userEvent.setup>, value: string) {
  const nameField = screen.getByTestId('form-field-name');
  const input = nameField.querySelector('input')!;
  await user.clear(input);
  await user.type(input, value);
}

describe('SensorCreateDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    i18n.changeLanguage('de');
  });

  afterAll(() => {
    i18n.changeLanguage('en');
  });

  it('renders nothing when closed', () => {
    registerHandlers();
    mount({ open: false });
    expect(screen.queryByTestId('sensor-create-dialog')).not.toBeInTheDocument();
  });

  it('renders the add form with the manual ha_entity_id field when no HA entities are available', async () => {
    registerHandlers({ haEntities: [] });
    mount({ context: { parentType: 'site', parentKey: 'site-1' } });
    expect(await screen.findByTestId('sensor-create-dialog')).toBeInTheDocument();
    expect(screen.getByText(i18n.t('pages.sensors.add'))).toBeInTheDocument();
    // No HA entities -> the manual entity-id field is shown, no autocomplete.
    expect(await screen.findByTestId('form-field-ha_entity_id')).toBeInTheDocument();
    // Add mode hides the is_active switch.
    expect(screen.queryByTestId('form-field-is_active')).not.toBeInTheDocument();
  });

  it('renders the HA-entity autocomplete (and hides the manual field) when entities are available', async () => {
    registerHandlers({ haEntities: HA_ENTITIES });
    mount();
    await screen.findByTestId('sensor-create-dialog');
    expect(await screen.findByLabelText(i18n.t('pages.sensors.haEntitySelect'))).toBeInTheDocument();
    expect(screen.queryByTestId('form-field-ha_entity_id')).not.toBeInTheDocument();
  });

  it('populates fields when an HA entity with suggestions is picked', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: HA_ENTITIES });
    mount();
    await screen.findByTestId('sensor-create-dialog');
    const combobox = await screen.findByLabelText(i18n.t('pages.sensors.haEntitySelect'));
    await user.click(combobox);
    await user.click(await screen.findByRole('option', { name: /pH Probe/ }));
    // suggested_name flows into the name field.
    await waitFor(() =>
      expect(screen.getByTestId('form-field-name').querySelector('input')).toHaveValue('Reservoir pH'),
    );
  });

  it('creates a tank sensor and calls onSaved', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({ context: { parentType: 'tank', parentKey: 'tank-1' } });
    await screen.findByTestId('sensor-create-dialog');
    await fillName(user, 'New Tank Sensor');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it('creates a site sensor and calls onSaved', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({ context: { parentType: 'site', parentKey: 'site-1' } });
    await screen.findByTestId('sensor-create-dialog');
    await fillName(user, 'New Site Sensor');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it('creates a location sensor and calls onSaved', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({ context: { parentType: 'location', parentKey: 'loc-1' } });
    await screen.findByTestId('sensor-create-dialog');
    await fillName(user, 'New Location Sensor');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it('does not submit when the required name is empty (validation blocks it)', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount();
    await screen.findByTestId('sensor-create-dialog');
    // Leave name empty and submit.
    await user.click(screen.getByTestId('form-submit-button'));
    // onSaved must never fire because zod validation fails.
    await new Promise((r) => setTimeout(r, 50));
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('renders the edit form with the active switch and updates the sensor on its tank', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({ sensor: EDIT_SENSOR });
    await screen.findByTestId('sensor-create-dialog');
    expect(screen.getByText(i18n.t('pages.sensors.edit'))).toBeInTheDocument();
    // Edit mode reveals the is_active switch and pre-fills the name.
    expect(screen.getByTestId('form-field-is_active')).toBeInTheDocument();
    expect(screen.getByTestId('form-field-name').querySelector('input')).toHaveValue('Existing Probe');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(requested).toEqual(['/api/v1/t/test-tenant/tanks/tank-1/sensors/sensor-9']);
  });

  it('updates a site sensor on its site', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({
      sensor: EDIT_SENSOR,
      context: { parentType: 'site', parentKey: 'site-1' },
    });
    await screen.findByTestId('sensor-create-dialog');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(requested).toEqual(['/api/v1/t/test-tenant/sites/site-1/sensors/sensor-9']);
  });

  it('updates a location sensor on its location', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onSaved } = mount({
      sensor: EDIT_SENSOR,
      context: { parentType: 'location', parentKey: 'loc-1' },
    });
    await screen.findByTestId('sensor-create-dialog');
    await user.click(screen.getByTestId('form-submit-button'));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(requested).toEqual(['/api/v1/t/test-tenant/locations/loc-1/sensors/sensor-9']);
  });

  it('surfaces an API error and keeps the dialog open when saving fails', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [], createStatus: 500 });
    const { onSaved } = mount();
    await screen.findByTestId('sensor-create-dialog');
    await fillName(user, 'Doomed Sensor');
    await user.click(screen.getByTestId('form-submit-button'));
    expect(await screen.findByText(i18n.t('errors.server'))).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('closes via the cancel button', async () => {
    const user = userEvent.setup();
    registerHandlers({ haEntities: [] });
    const { onClose } = mount();
    await screen.findByTestId('sensor-create-dialog');
    await user.click(screen.getByTestId('form-cancel-button'));
    expect(onClose).toHaveBeenCalled();
  });

  it('falls back to an empty entity list when HA discovery fails', async () => {
    server.use(
      http.get('/api/v1/t/:tenant/tanks/ha-entities', () =>
        HttpResponse.json({ message: 'nope' }, { status: 500 }),
      ),
    );
    mount();
    await screen.findByTestId('sensor-create-dialog');
    // On discovery failure the manual entity-id field is shown.
    expect(await screen.findByTestId('form-field-ha_entity_id')).toBeInTheDocument();
  });
});

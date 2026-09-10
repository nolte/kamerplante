import { describe, it, expect, beforeEach, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const client = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  return { client };
});

vi.mock('@/api/client', () => ({
  __esModule: true,
  default: mocks.client,
  tenantClient: mocks.client,
}));

import * as tanks from '@/api/endpoints/tanks';
import { twoThermometersLiveState } from '../liveStateFixture';

const client = mocks.client;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('tanks endpoints — tank CRUD', () => {
  it('listTanks uses default pagination', async () => {
    client.get.mockResolvedValue({ data: [] });
    await expect(tanks.listTanks()).resolves.toEqual([]);
    expect(client.get).toHaveBeenCalledWith('/tanks', { params: { offset: 0, limit: 50 } });
  });

  it('listTanks adds tank_type filter when provided', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.listTanks(5, 10, 'reservoir');
    expect(client.get).toHaveBeenCalledWith('/tanks', {
      params: { offset: 5, limit: 10, tank_type: 'reservoir' },
    });
  });

  it('getTank gets tank by key', async () => {
    client.get.mockResolvedValue({ data: { key: 't1' } });
    await tanks.getTank('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1');
  });

  it('createTank posts payload', async () => {
    client.post.mockResolvedValue({ data: { key: 't1' } });
    const payload = { name: 'Tank' } as never;
    await tanks.createTank(payload);
    expect(client.post).toHaveBeenCalledWith('/tanks', payload);
  });

  it('updateTank puts payload by key', async () => {
    client.put.mockResolvedValue({ data: { key: 't1' } });
    const payload = { name: 'X' } as never;
    await tanks.updateTank('t1', payload);
    expect(client.put).toHaveBeenCalledWith('/tanks/t1', payload);
  });

  it('deleteTank deletes by key', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tanks.deleteTank('t1');
    expect(client.delete).toHaveBeenCalledWith('/tanks/t1');
  });
});

describe('tanks endpoints — states', () => {
  it('recordState posts state for tank', async () => {
    client.post.mockResolvedValue({ data: { key: 's1' } });
    const payload = { ph: 6 } as never;
    await tanks.recordState('t1', payload);
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/states', payload);
  });

  it('getStates gets paginated states', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getStates('t1', 5, 10);
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/states', {
      params: { offset: 5, limit: 10 },
    });
  });

  it('getLatestState gets latest state', async () => {
    client.get.mockResolvedValue({ data: null });
    await expect(tanks.getLatestState('t1')).resolves.toBeNull();
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/states/latest');
  });
});

describe('tanks endpoints — alerts, maintenance, schedules', () => {
  it('getAlerts gets alerts for tank', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getAlerts('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/alerts');
  });

  it('logMaintenance posts maintenance log', async () => {
    client.post.mockResolvedValue({ data: { key: 'm1' } });
    const payload = { type: 'clean' } as never;
    await tanks.logMaintenance('t1', payload);
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/maintenance', payload);
  });

  it('getMaintenanceHistory gets paginated history', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getMaintenanceHistory('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/maintenance', {
      params: { offset: 0, limit: 50 },
    });
  });

  it('getDueMaintenances gets due list for tank', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getDueMaintenances('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/maintenance/due');
  });

  it('createSchedule posts schedule', async () => {
    client.post.mockResolvedValue({ data: { key: 'sc1' } });
    const payload = { interval_days: 7 } as never;
    await tanks.createSchedule('t1', payload);
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/schedules', payload);
  });

  it('getSchedules gets schedules for tank', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getSchedules('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/schedules');
  });

  it('updateSchedule puts schedule by composite key', async () => {
    client.put.mockResolvedValue({ data: { key: 'sc1' } });
    const payload = { interval_days: 14 } as never;
    await tanks.updateSchedule('t1', 'sc1', payload);
    expect(client.put).toHaveBeenCalledWith('/tanks/t1/schedules/sc1', payload);
  });

  it('deleteSchedule deletes schedule by composite key', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tanks.deleteSchedule('t1', 'sc1');
    expect(client.delete).toHaveBeenCalledWith('/tanks/t1/schedules/sc1');
  });

  it('getAllDueMaintenances gets global due overview', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getAllDueMaintenances();
    expect(client.get).toHaveBeenCalledWith('/tanks/maintenance/due');
  });
});

describe('tanks endpoints — fill events', () => {
  it('recordFillEvent posts fill event', async () => {
    client.post.mockResolvedValue({ data: { key: 'f1' } });
    const payload = { liters: 50 } as never;
    await tanks.recordFillEvent('t1', payload);
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/fills', payload);
  });

  it('getFillEvents gets paginated fills', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getFillEvents('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/fills', {
      params: { offset: 0, limit: 50 },
    });
  });

  it('getLatestFill gets latest fill', async () => {
    client.get.mockResolvedValue({ data: null });
    await expect(tanks.getLatestFill('t1')).resolves.toBeNull();
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/fills/latest');
  });

  it('getFillStats gets stats without date filters', async () => {
    client.get.mockResolvedValue({ data: { total: 0 } });
    await tanks.getFillStats('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/fills/stats', { params: {} });
  });

  it('getFillStats adds start and end date params', async () => {
    client.get.mockResolvedValue({ data: { total: 0 } });
    await tanks.getFillStats('t1', '2026-01-01', '2026-02-01');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/fills/stats', {
      params: { start_date: '2026-01-01', end_date: '2026-02-01' },
    });
  });
});

describe('tanks endpoints — relationships, sensors, HA', () => {
  it('linkFeedsFrom posts source tank key', async () => {
    client.post.mockResolvedValue({ data: undefined });
    await tanks.linkFeedsFrom('t1', 't2');
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/feeds-from', {
      source_tank_key: 't2',
    });
  });

  it('getLiveState gets live state', async () => {
    client.get.mockResolvedValue({ data: {} });
    await tanks.getLiveState('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/states/live');
  });

  it('getLiveState carries the per-sensor readings alongside the derived view', async () => {
    client.get.mockResolvedValue({ data: twoThermometersLiveState() });

    const live = await tanks.getLiveState('t1');

    expect(Object.keys(live.readings).sort()).toEqual(['s-back', 's-front']);
    expect(live.values.temperature_celsius.sensor_count).toBe(2);
    expect(live.readings['s-front'].sensor_name).toBe('Zelt vorne');
  });

  it('getSensors gets sensors for tank', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.getSensors('t1');
    expect(client.get).toHaveBeenCalledWith('/tanks/t1/sensors');
  });

  it('createSensor posts sensor for tank', async () => {
    client.post.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { entity_id: 'sensor.x' } as never;
    await tanks.createSensor('t1', payload);
    expect(client.post).toHaveBeenCalledWith('/tanks/t1/sensors', payload);
  });

  // Both of the next two asserted `/tanks/sensors/{key}` until #1339 — a path no
  // backend route has ever served. They were green from the day they were
  // written, because a mocked client can only be checked against the client:
  // the assertion restated the very string it was meant to verify. The path is
  // now the one the backend serves, and the join in
  // `tests/unit/api/test_frontend_endpoints_are_served.py` is what keeps it
  // honest — this test can only pin the reshape, not the contract.
  it('updateSensor puts to the tank-scoped sensor path', async () => {
    client.put.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { name: 'X' } as never;
    await tanks.updateSensor('t1', 'se1', payload);
    expect(client.put).toHaveBeenCalledWith('/tanks/t1/sensors/se1', payload);
  });

  it('deleteSensor deletes the tank-scoped sensor path', async () => {
    client.delete.mockResolvedValue({ data: undefined });
    await tanks.deleteSensor('t1', 'se1');
    expect(client.delete).toHaveBeenCalledWith('/tanks/t1/sensors/se1');
  });

  it('listHaEntities gets HA entity suggestions', async () => {
    client.get.mockResolvedValue({ data: [] });
    await tanks.listHaEntities();
    expect(client.get).toHaveBeenCalledWith('/tanks/ha-entities');
  });
});

import { describe, it, expect, beforeEach, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const make = () => ({
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  });
  // sites.ts uses the default (global) client only for location-types, and
  // the tenantClient for all tenant-scoped sites/locations/slots/sensors.
  return { globalClient: make(), tenantClient: make() };
});

vi.mock('@/api/client', () => ({
  __esModule: true,
  default: mocks.globalClient,
  tenantClient: mocks.tenantClient,
}));

import * as sites from '@/api/endpoints/sites';
import { twoThermometersLiveState } from '../liveStateFixture';

const globalClient = mocks.globalClient;
const tenantClient = mocks.tenantClient;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('sites endpoints — sites (tenant client)', () => {
  it('listSites gets paginated sites', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.listSites(5, 10);
    expect(tenantClient.get).toHaveBeenCalledWith('/sites', {
      params: { offset: 5, limit: 10 },
    });
  });

  it('getSite gets site by key', async () => {
    tenantClient.get.mockResolvedValue({ data: { key: 's1' } });
    await sites.getSite('s1');
    expect(tenantClient.get).toHaveBeenCalledWith('/sites/s1');
  });

  it('createSite posts payload', async () => {
    tenantClient.post.mockResolvedValue({ data: { key: 's1' } });
    const payload = { name: 'Site' } as never;
    await sites.createSite(payload);
    expect(tenantClient.post).toHaveBeenCalledWith('/sites', payload);
  });

  it('updateSite puts payload by key', async () => {
    tenantClient.put.mockResolvedValue({ data: { key: 's1' } });
    const payload = { name: 'X' } as never;
    await sites.updateSite('s1', payload);
    expect(tenantClient.put).toHaveBeenCalledWith('/sites/s1', payload);
  });

  it('deleteSite deletes by key', async () => {
    tenantClient.delete.mockResolvedValue({ data: undefined });
    await sites.deleteSite('s1');
    expect(tenantClient.delete).toHaveBeenCalledWith('/sites/s1');
  });
});

describe('sites endpoints — locations (tenant client)', () => {
  it('listLocations gets with site_key param', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.listLocations('s1');
    expect(tenantClient.get).toHaveBeenCalledWith('/locations', {
      params: { site_key: 's1' },
    });
  });

  it('getLocation gets location by key', async () => {
    tenantClient.get.mockResolvedValue({ data: { key: 'l1' } });
    await sites.getLocation('l1');
    expect(tenantClient.get).toHaveBeenCalledWith('/locations/l1');
  });

  it('createLocation posts payload', async () => {
    tenantClient.post.mockResolvedValue({ data: { key: 'l1' } });
    const payload = { name: 'Bed' } as never;
    await sites.createLocation(payload);
    expect(tenantClient.post).toHaveBeenCalledWith('/locations', payload);
  });

  it('updateLocation puts payload by key', async () => {
    tenantClient.put.mockResolvedValue({ data: { key: 'l1' } });
    const payload = { name: 'X' } as never;
    await sites.updateLocation('l1', payload);
    expect(tenantClient.put).toHaveBeenCalledWith('/locations/l1', payload);
  });

  it('deleteLocation deletes by key', async () => {
    tenantClient.delete.mockResolvedValue({ data: undefined });
    await sites.deleteLocation('l1');
    expect(tenantClient.delete).toHaveBeenCalledWith('/locations/l1');
  });

  it('listLocationChildren gets children for parent', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.listLocationChildren('l1');
    expect(tenantClient.get).toHaveBeenCalledWith('/locations/l1/children');
  });

  it('getLocationTree gets tree for site', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.getLocationTree('s1');
    expect(tenantClient.get).toHaveBeenCalledWith('/sites/s1/location-tree');
  });
});

describe('sites endpoints — location types (global client)', () => {
  it('listLocationTypes gets via global client', async () => {
    globalClient.get.mockResolvedValue({ data: [] });
    await sites.listLocationTypes();
    expect(globalClient.get).toHaveBeenCalledWith('/location-types');
    expect(tenantClient.get).not.toHaveBeenCalled();
  });
});

describe('sites endpoints — slots (tenant client)', () => {
  it('listSlots gets with location_key param', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.listSlots('l1');
    expect(tenantClient.get).toHaveBeenCalledWith('/slots', {
      params: { location_key: 'l1' },
    });
  });

  it('getSlot gets slot by key', async () => {
    tenantClient.get.mockResolvedValue({ data: { key: 'sl1' } });
    await sites.getSlot('sl1');
    expect(tenantClient.get).toHaveBeenCalledWith('/slots/sl1');
  });

  it('createSlot posts payload', async () => {
    tenantClient.post.mockResolvedValue({ data: { key: 'sl1' } });
    const payload = { location_key: 'l1' } as never;
    await sites.createSlot(payload);
    expect(tenantClient.post).toHaveBeenCalledWith('/slots', payload);
  });

  it('updateSlot puts payload by key', async () => {
    tenantClient.put.mockResolvedValue({ data: { key: 'sl1' } });
    const payload = { capacity: 4 } as never;
    await sites.updateSlot('sl1', payload);
    expect(tenantClient.put).toHaveBeenCalledWith('/slots/sl1', payload);
  });

  it('deleteSlot deletes by key', async () => {
    tenantClient.delete.mockResolvedValue({ data: undefined });
    await sites.deleteSlot('sl1');
    expect(tenantClient.delete).toHaveBeenCalledWith('/slots/sl1');
  });
});

describe('sites endpoints — site & location sensors (tenant client)', () => {
  it('getSiteSensors gets sensors for site', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.getSiteSensors('s1');
    expect(tenantClient.get).toHaveBeenCalledWith('/sites/s1/sensors');
  });

  it('createSiteSensor posts sensor for site', async () => {
    tenantClient.post.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { entity_id: 'sensor.x' } as never;
    await sites.createSiteSensor('s1', payload);
    expect(tenantClient.post).toHaveBeenCalledWith('/sites/s1/sensors', payload);
  });

  it('updateSiteSensor puts to the site-scoped sensor path', async () => {
    tenantClient.put.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { name: 'X' } as never;
    await sites.updateSiteSensor('s1', 'se1', payload);
    expect(tenantClient.put).toHaveBeenCalledWith('/sites/s1/sensors/se1', payload);
  });

  it('deleteSiteSensor deletes the site-scoped sensor path', async () => {
    tenantClient.delete.mockResolvedValue({ data: undefined });
    await sites.deleteSiteSensor('s1', 'se1');
    expect(tenantClient.delete).toHaveBeenCalledWith('/sites/s1/sensors/se1');
  });

  it('getSiteSensorsLive gets live readings for site', async () => {
    tenantClient.get.mockResolvedValue({ data: {} });
    await sites.getSiteSensorsLive('s1');
    expect(tenantClient.get).toHaveBeenCalledWith('/sites/s1/sensors/live');
  });

  it('getSiteSensorsLive returns both sensors of one metric', async () => {
    tenantClient.get.mockResolvedValue({ data: twoThermometersLiveState() });
    const live = await sites.getSiteSensorsLive('s1');
    expect(Object.keys(live.readings).sort()).toEqual(['s-back', 's-front']);
    expect(live.readings['s-front'].value).toBe(21.4);
    expect(live.readings['s-back'].value).toBe(23.9);
  });

  it('getLocationSensors gets sensors for location', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await sites.getLocationSensors('l1');
    expect(tenantClient.get).toHaveBeenCalledWith('/locations/l1/sensors');
  });

  it('createLocationSensor posts sensor for location', async () => {
    tenantClient.post.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { entity_id: 'sensor.y' } as never;
    await sites.createLocationSensor('l1', payload);
    expect(tenantClient.post).toHaveBeenCalledWith('/locations/l1/sensors', payload);
  });

  it('updateLocationSensor puts to the location-scoped sensor path', async () => {
    tenantClient.put.mockResolvedValue({ data: { key: 'se1' } });
    const payload = { is_active: false } as never;
    await sites.updateLocationSensor('l1', 'se1', payload);
    expect(tenantClient.put).toHaveBeenCalledWith('/locations/l1/sensors/se1', payload);
  });

  it('deleteLocationSensor deletes the location-scoped sensor path', async () => {
    tenantClient.delete.mockResolvedValue({ data: undefined });
    await sites.deleteLocationSensor('l1', 'se1');
    expect(tenantClient.delete).toHaveBeenCalledWith('/locations/l1/sensors/se1');
  });

  it('getLocationSensorsLive gets live readings for location', async () => {
    tenantClient.get.mockResolvedValue({ data: {} });
    await sites.getLocationSensorsLive('l1');
    expect(tenantClient.get).toHaveBeenCalledWith('/locations/l1/sensors/live');
  });

  it('getLocationSensorsLive keeps both readings and reports the collapse', async () => {
    tenantClient.get.mockResolvedValue({ data: twoThermometersLiveState() });

    const live = await sites.getLocationSensorsLive('l1');

    // The full map is the complete answer …
    expect(Object.keys(live.readings)).toHaveLength(2);
    // … and the derived view says out loud that it shows only one of them.
    const derived = live.values.temperature_celsius;
    expect(derived.value).toBe(23.9);
    expect(derived.sensor_count).toBe(2);
    expect(derived.superseded_sensor_keys).toEqual(['s-front']);
    expect(live.readings[derived.superseded_sensor_keys[0]].value).toBe(21.4);
  });

  it('getLocationSensorsLive marks a lone sensor as uncollapsed', async () => {
    const single = twoThermometersLiveState();
    delete single.readings['s-back'];
    single.values.temperature_celsius = {
      ...single.readings['s-front'],
      sensor_count: 1,
      superseded_sensor_keys: [],
    };
    tenantClient.get.mockResolvedValue({ data: single });

    const live = await sites.getLocationSensorsLive('l1');

    expect(live.values.temperature_celsius.value).toBe(21.4);
    expect(live.values.temperature_celsius.sensor_count).toBe(1);
    expect(live.values.temperature_celsius.superseded_sensor_keys).toEqual([]);
  });
});

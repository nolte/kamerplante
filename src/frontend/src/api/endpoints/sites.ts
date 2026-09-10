import client, { tenantClient } from '../client';
import type {
  Site,
  SiteCreate,
  SiteHardinessResponse,
  Location,
  LocationCreate,
  LocationTreeNode,
  LocationType,
  LiveStateResponse,
  Sensor,
  SensorCreate,
  SensorUpdate,
  Slot,
  SlotCreate,
} from '../types';

// Sites
const SITES = '/sites';

export async function listSites(offset = 0, limit = 50): Promise<Site[]> {
  const { data } = await tenantClient.get<Site[]>(SITES, { params: { offset, limit } });
  return data;
}

export async function getSite(key: string): Promise<Site> {
  const { data } = await tenantClient.get<Site>(`${SITES}/${key}`);
  return data;
}

export async function createSite(payload: SiteCreate): Promise<Site> {
  const { data } = await tenantClient.post<Site>(SITES, payload);
  return data;
}

export async function updateSite(key: string, payload: SiteCreate): Promise<Site> {
  const { data } = await tenantClient.put<Site>(`${SITES}/${key}`, payload);
  return data;
}

export async function deleteSite(key: string): Promise<void> {
  await tenantClient.delete(`${SITES}/${key}`);
}

/**
 * Derive the site's USDA hardiness zone (and legacy `climate_zone`) from its GPS
 * coordinates (REQ-039/041). Climate normals are fetched on demand server-side,
 * so this works right after coordinates are set. Requires the `grower` role and
 * returns 422 when no climate normals with a usable minimum can be obtained.
 */
export async function resolveSiteHardinessZone(
  key: string,
  force = false,
): Promise<SiteHardinessResponse> {
  const { data } = await tenantClient.post<SiteHardinessResponse>(
    `${SITES}/${key}/resolve-hardiness-zone`,
    null,
    { params: { force } },
  );
  return data;
}

// Locations
const LOCATIONS = '/locations';

export async function listLocations(siteKey: string): Promise<Location[]> {
  const { data } = await tenantClient.get<Location[]>(LOCATIONS, {
    params: { site_key: siteKey },
  });
  return data;
}

export async function getLocation(key: string): Promise<Location> {
  const { data } = await tenantClient.get<Location>(`${LOCATIONS}/${key}`);
  return data;
}

export async function createLocation(payload: LocationCreate): Promise<Location> {
  const { data } = await tenantClient.post<Location>(LOCATIONS, payload);
  return data;
}

export async function updateLocation(key: string, payload: LocationCreate): Promise<Location> {
  const { data } = await tenantClient.put<Location>(`${LOCATIONS}/${key}`, payload);
  return data;
}

export async function deleteLocation(key: string): Promise<void> {
  await tenantClient.delete(`${LOCATIONS}/${key}`);
}

export async function listLocationChildren(parentKey: string): Promise<Location[]> {
  const { data } = await tenantClient.get<Location[]>(`${LOCATIONS}/${parentKey}/children`);
  return data;
}

export async function getLocationTree(siteKey: string): Promise<LocationTreeNode[]> {
  const { data } = await tenantClient.get<LocationTreeNode[]>(`${SITES}/${siteKey}/location-tree`);
  return data;
}

// Location Types
const LOCATION_TYPES = '/location-types';

export async function listLocationTypes(): Promise<LocationType[]> {
  const { data } = await client.get<LocationType[]>(LOCATION_TYPES);
  return data;
}

// Slots
const SLOTS = '/slots';

export async function listSlots(locationKey: string): Promise<Slot[]> {
  const { data } = await tenantClient.get<Slot[]>(SLOTS, {
    params: { location_key: locationKey },
  });
  return data;
}

export async function getSlot(key: string): Promise<Slot> {
  const { data } = await tenantClient.get<Slot>(`${SLOTS}/${key}`);
  return data;
}

export async function createSlot(payload: SlotCreate): Promise<Slot> {
  const { data } = await tenantClient.post<Slot>(SLOTS, payload);
  return data;
}

export async function updateSlot(key: string, payload: SlotCreate): Promise<Slot> {
  const { data } = await tenantClient.put<Slot>(`${SLOTS}/${key}`, payload);
  return data;
}

export async function deleteSlot(key: string): Promise<void> {
  await tenantClient.delete(`${SLOTS}/${key}`);
}

// ── Site Sensors ────────────────────────────────────────────────────────

export async function getSiteSensors(siteKey: string): Promise<Sensor[]> {
  const { data } = await tenantClient.get<Sensor[]>(`${SITES}/${siteKey}/sensors`);
  return data;
}

export async function createSiteSensor(
  siteKey: string,
  payload: SensorCreate,
): Promise<Sensor> {
  const { data } = await tenantClient.post<Sensor>(
    `${SITES}/${siteKey}/sensors`,
    payload,
  );
  return data;
}

/**
 * Update a sensor attached to a site.
 *
 * Scoped by the site, like create and list: a sensor carries no `tenant_key`,
 * so its parent is the tenant anchor the backend verifies (#1339).
 */
export async function updateSiteSensor(
  siteKey: string,
  sensorKey: string,
  payload: SensorUpdate,
): Promise<Sensor> {
  const { data } = await tenantClient.put<Sensor>(
    `${SITES}/${siteKey}/sensors/${sensorKey}`,
    payload,
  );
  return data;
}

/** Delete a sensor attached to a site (see {@link updateSiteSensor}). */
export async function deleteSiteSensor(
  siteKey: string,
  sensorKey: string,
): Promise<void> {
  await tenantClient.delete(`${SITES}/${siteKey}/sensors/${sensorKey}`);
}

export async function getSiteSensorsLive(
  siteKey: string,
): Promise<LiveStateResponse> {
  const { data } = await tenantClient.get<LiveStateResponse>(
    `${SITES}/${siteKey}/sensors/live`,
  );
  return data;
}

// ── Location Sensors ────────────────────────────────────────────────────

export async function getLocationSensors(
  locationKey: string,
): Promise<Sensor[]> {
  const { data } = await tenantClient.get<Sensor[]>(
    `${LOCATIONS}/${locationKey}/sensors`,
  );
  return data;
}

export async function createLocationSensor(
  locationKey: string,
  payload: SensorCreate,
): Promise<Sensor> {
  const { data } = await tenantClient.post<Sensor>(
    `${LOCATIONS}/${locationKey}/sensors`,
    payload,
  );
  return data;
}

/**
 * Update a sensor attached to a location.
 *
 * Scoped by the location, like create and list: neither a sensor nor a location
 * carries a `tenant_key`, so the backend resolves the anchor through the
 * location's site (#1339).
 */
export async function updateLocationSensor(
  locationKey: string,
  sensorKey: string,
  payload: SensorUpdate,
): Promise<Sensor> {
  const { data } = await tenantClient.put<Sensor>(
    `${LOCATIONS}/${locationKey}/sensors/${sensorKey}`,
    payload,
  );
  return data;
}

/** Delete a sensor attached to a location (see {@link updateLocationSensor}). */
export async function deleteLocationSensor(
  locationKey: string,
  sensorKey: string,
): Promise<void> {
  await tenantClient.delete(`${LOCATIONS}/${locationKey}/sensors/${sensorKey}`);
}

export async function getLocationSensorsLive(
  locationKey: string,
): Promise<LiveStateResponse> {
  const { data } = await tenantClient.get<LiveStateResponse>(
    `${LOCATIONS}/${locationKey}/sensors/live`,
  );
  return data;
}

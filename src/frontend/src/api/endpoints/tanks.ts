import { tenantClient as client } from '../client';
import type {
  DueMaintenance,
  FillEventResult,
  LiveStateResponse,
  MaintenanceLog,
  MaintenanceLogCreate,
  MaintenanceSchedule,
  MaintenanceScheduleCreate,
  MaintenanceScheduleUpdate,
  Sensor,
  SensorCreate,
  SensorUpdate,
  Tank,
  TankAlert,
  TankCreate,
  TankFillEvent,
  TankFillEventCreate,
  TankFillEventStats,
  TankState,
  TankStateCreate,
  TankUpdate,
} from '../types';

const BASE = '/tanks';

// ── Tank CRUD ──────────────────────────────────────────────────────────

export async function listTanks(
  offset = 0,
  limit = 50,
  tankType?: string,
): Promise<Tank[]> {
  const params: Record<string, string | number> = { offset, limit };
  if (tankType) params.tank_type = tankType;
  const { data } = await client.get<Tank[]>(BASE, { params });
  return data;
}

export async function getTank(key: string): Promise<Tank> {
  const { data } = await client.get<Tank>(`${BASE}/${key}`);
  return data;
}

export async function createTank(payload: TankCreate): Promise<Tank> {
  const { data } = await client.post<Tank>(BASE, payload);
  return data;
}

export async function updateTank(
  key: string,
  payload: TankUpdate,
): Promise<Tank> {
  const { data } = await client.put<Tank>(`${BASE}/${key}`, payload);
  return data;
}

export async function deleteTank(key: string): Promise<void> {
  await client.delete(`${BASE}/${key}`);
}

// ── States ─────────────────────────────────────────────────────────────

export async function recordState(
  tankKey: string,
  payload: TankStateCreate,
): Promise<TankState> {
  const { data } = await client.post<TankState>(
    `${BASE}/${tankKey}/states`,
    payload,
  );
  return data;
}

export async function getStates(
  tankKey: string,
  offset = 0,
  limit = 50,
): Promise<TankState[]> {
  const { data } = await client.get<TankState[]>(
    `${BASE}/${tankKey}/states`,
    { params: { offset, limit } },
  );
  return data;
}

export async function getLatestState(
  tankKey: string,
): Promise<TankState | null> {
  const { data } = await client.get<TankState | null>(
    `${BASE}/${tankKey}/states/latest`,
  );
  return data;
}

// ── Alerts ─────────────────────────────────────────────────────────────

export async function getAlerts(tankKey: string): Promise<TankAlert[]> {
  const { data } = await client.get<TankAlert[]>(
    `${BASE}/${tankKey}/alerts`,
  );
  return data;
}

// ── Maintenance logs ───────────────────────────────────────────────────

export async function logMaintenance(
  tankKey: string,
  payload: MaintenanceLogCreate,
): Promise<MaintenanceLog> {
  const { data } = await client.post<MaintenanceLog>(
    `${BASE}/${tankKey}/maintenance`,
    payload,
  );
  return data;
}

export async function getMaintenanceHistory(
  tankKey: string,
  offset = 0,
  limit = 50,
): Promise<MaintenanceLog[]> {
  const { data } = await client.get<MaintenanceLog[]>(
    `${BASE}/${tankKey}/maintenance`,
    { params: { offset, limit } },
  );
  return data;
}

export async function getDueMaintenances(
  tankKey: string,
): Promise<DueMaintenance[]> {
  const { data } = await client.get<DueMaintenance[]>(
    `${BASE}/${tankKey}/maintenance/due`,
  );
  return data;
}

// ── Schedules ──────────────────────────────────────────────────────────

export async function createSchedule(
  tankKey: string,
  payload: MaintenanceScheduleCreate,
): Promise<MaintenanceSchedule> {
  const { data } = await client.post<MaintenanceSchedule>(
    `${BASE}/${tankKey}/schedules`,
    payload,
  );
  return data;
}

export async function getSchedules(
  tankKey: string,
): Promise<MaintenanceSchedule[]> {
  const { data } = await client.get<MaintenanceSchedule[]>(
    `${BASE}/${tankKey}/schedules`,
  );
  return data;
}

export async function updateSchedule(
  tankKey: string,
  scheduleKey: string,
  payload: MaintenanceScheduleUpdate,
): Promise<MaintenanceSchedule> {
  const { data } = await client.put<MaintenanceSchedule>(
    `${BASE}/${tankKey}/schedules/${scheduleKey}`,
    payload,
  );
  return data;
}

export async function deleteSchedule(
  tankKey: string,
  scheduleKey: string,
): Promise<void> {
  await client.delete(`${BASE}/${tankKey}/schedules/${scheduleKey}`);
}

// ── Global maintenance overview ────────────────────────────────────────

export async function getAllDueMaintenances(): Promise<DueMaintenance[]> {
  const { data } = await client.get<DueMaintenance[]>(
    `${BASE}/maintenance/due`,
  );
  return data;
}

// ── Fill Events ────────────────────────────────────────────────────────

export async function recordFillEvent(
  tankKey: string,
  payload: TankFillEventCreate,
): Promise<FillEventResult> {
  const { data } = await client.post<FillEventResult>(
    `${BASE}/${tankKey}/fills`,
    payload,
  );
  return data;
}

export async function getFillEvents(
  tankKey: string,
  offset = 0,
  limit = 50,
): Promise<TankFillEvent[]> {
  const { data } = await client.get<TankFillEvent[]>(
    `${BASE}/${tankKey}/fills`,
    { params: { offset, limit } },
  );
  return data;
}

export async function getLatestFill(
  tankKey: string,
): Promise<TankFillEvent | null> {
  const { data } = await client.get<TankFillEvent | null>(
    `${BASE}/${tankKey}/fills/latest`,
  );
  return data;
}

export async function getFillStats(
  tankKey: string,
  startDate?: string,
  endDate?: string,
): Promise<TankFillEventStats> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await client.get<TankFillEventStats>(
    `${BASE}/${tankKey}/fills/stats`,
    { params },
  );
  return data;
}

// ── Relationships ──────────────────────────────────────────────────────

export async function linkFeedsFrom(
  tankKey: string,
  sourceTankKey: string,
): Promise<void> {
  await client.post(`${BASE}/${tankKey}/feeds-from`, {
    source_tank_key: sourceTankKey,
  });
}

// ── Sensors & Live Query ──────────────────────────────────────────────

export async function getLiveState(
  tankKey: string,
): Promise<LiveStateResponse> {
  const { data } = await client.get<LiveStateResponse>(
    `${BASE}/${tankKey}/states/live`,
  );
  return data;
}

export async function getSensors(tankKey: string): Promise<Sensor[]> {
  const { data } = await client.get<Sensor[]>(
    `${BASE}/${tankKey}/sensors`,
  );
  return data;
}

export async function createSensor(
  tankKey: string,
  payload: SensorCreate,
): Promise<Sensor> {
  const { data } = await client.post<Sensor>(
    `${BASE}/${tankKey}/sensors`,
    payload,
  );
  return data;
}

/**
 * Update a sensor attached to a tank.
 *
 * Scoped by the tank, like create and list: a sensor carries no `tenant_key`,
 * so its parent is the tenant anchor the backend verifies. Until #1339 this
 * posted to `/tanks/sensors/{key}`, which no route has ever served — every edit
 * answered 404.
 */
export async function updateSensor(
  tankKey: string,
  sensorKey: string,
  payload: SensorUpdate,
): Promise<Sensor> {
  const { data } = await client.put<Sensor>(
    `${BASE}/${tankKey}/sensors/${sensorKey}`,
    payload,
  );
  return data;
}

/** Delete a sensor attached to a tank (see {@link updateSensor} on the scoping). */
export async function deleteSensor(
  tankKey: string,
  sensorKey: string,
): Promise<void> {
  await client.delete(`${BASE}/${tankKey}/sensors/${sensorKey}`);
}

// ── HA Entity Discovery ──────────────────────────────────────────────

export interface HAEntitySuggestion {
  entity_id: string;
  friendly_name: string;
  unit_of_measurement: string | null;
  device_class: string | null;
  state: string | null;
  suggested_metric_type: string | null;
  suggested_name: string | null;
}

export async function listHaEntities(): Promise<HAEntitySuggestion[]> {
  const { data } = await client.get<HAEntitySuggestion[]>(
    `${BASE}/ha-entities`,
  );
  return data;
}

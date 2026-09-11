import client from '../client';
import type { RecognitionStatus } from '../types';

export interface HASettingsResponse {
  ha_url: string;
  ha_access_token_masked: string;
  ha_timeout: number;
  source_ha_url: string;
  source_ha_access_token: string;
  source_ha_timeout: string;
}

export interface PlantIdentificationSettingsResponse {
  plantnet_api_key_masked: string;
  source_plantnet_api_key: string;
}

/**
 * NFR-013 §4.1 — effective object-storage configuration for the admin UI.
 *
 * Carries only non-secret fields. The S3 credentials are never returned by the
 * backend; only their *presence* is reported (`s3_*_configured`). Per AC-04 the
 * UI references no bucket/backend in user-visible data paths — this admin
 * settings surface is the sole, deliberate exception where the operator
 * configures the backend.
 */
export interface StorageSettingsResponse {
  backend: string;
  local_fs_root: string;
  local_fs_public_base_url: string;
  s3_endpoint_url: string;
  s3_region: string;
  s3_bucket: string;
  s3_use_path_style: boolean;
  s3_kms_key_id: string;
  s3_force_tls: boolean;
  s3_access_key_id_configured: boolean;
  s3_secret_access_key_configured: boolean;
  source_backend: string;
  source_local_fs_root: string;
  source_local_fs_public_base_url: string;
  source_s3_endpoint_url: string;
  source_s3_region: string;
  source_s3_bucket: string;
  source_s3_use_path_style: string;
  source_s3_kms_key_id: string;
  source_s3_force_tls: string;
}

/** Update payload — non-secret fields only (secrets come from env / ESO). */
export interface StorageSettingsUpdate {
  backend?: 'local-fs' | 's3' | null;
  local_fs_root?: string | null;
  local_fs_public_base_url?: string | null;
  s3_endpoint_url?: string | null;
  s3_region?: string | null;
  s3_bucket?: string | null;
  s3_use_path_style?: boolean | null;
  s3_kms_key_id?: string | null;
  s3_force_tls?: boolean | null;
}

/** Optional not-yet-persisted overrides for a connection test (no secrets). */
export type StorageTestRequest = StorageSettingsUpdate;

export interface StorageTestResponse {
  success: boolean;
  backend: string;
  message: string;
  writable?: boolean | null;
  bucket_reachable?: boolean | null;
}

export interface SystemSettingsResponse {
  home_assistant: HASettingsResponse;
  plant_identification: PlantIdentificationSettingsResponse;
  storage: StorageSettingsResponse;
}

export interface PlantIdentificationSettingsUpdate {
  plantnet_api_key?: string | null;
}

export interface PlantIdentificationTestRequest {
  plantnet_api_key?: string | null;
}

export interface PlantIdentificationTestResponse {
  success: boolean;
  message: string;
}

export interface HASettingsUpdate {
  ha_url?: string | null;
  ha_access_token?: string | null;
  ha_timeout?: number | null;
}

export interface HATestRequest {
  ha_url?: string | null;
  ha_access_token?: string | null;
  ha_timeout?: number | null;
}

export interface HATestResponse {
  success: boolean;
  message: string;
  ha_version?: string | null;
}

const BASE = '/admin/settings';

export async function getSystemSettings(): Promise<SystemSettingsResponse> {
  const { data } = await client.get<SystemSettingsResponse>(BASE);
  return data;
}

export async function updateHaSettings(
  body: HASettingsUpdate,
): Promise<SystemSettingsResponse> {
  const { data } = await client.put<SystemSettingsResponse>(`${BASE}/home-assistant`, body);
  return data;
}

export async function testHaConnection(
  body: HATestRequest,
): Promise<HATestResponse> {
  const { data } = await client.post<HATestResponse>(`${BASE}/home-assistant/test`, body);
  return data;
}

export async function clearHaSettings(): Promise<void> {
  await client.delete(`${BASE}/home-assistant`);
}

export async function updatePlantIdentificationSettings(
  body: PlantIdentificationSettingsUpdate,
): Promise<SystemSettingsResponse> {
  const { data } = await client.put<SystemSettingsResponse>(
    `${BASE}/plant-identification`,
    body,
  );
  return data;
}

export async function testPlantIdentificationKey(
  body: PlantIdentificationTestRequest,
): Promise<PlantIdentificationTestResponse> {
  const { data } = await client.post<PlantIdentificationTestResponse>(
    `${BASE}/plant-identification/test`,
    body,
  );
  return data;
}

export async function clearPlantIdentificationSettings(): Promise<void> {
  await client.delete(`${BASE}/plant-identification`);
}

/**
 * GET /admin/settings/storage → effective object-storage configuration
 * (NFR-013). Platform-admin-only (SEC-001): the storage-infra block is kept out
 * of the general `GET /admin/settings` payload and served here instead. Both are
 * platform-admin-only since #1385 — this used to add "which any authenticated
 * user can read", which is what #1385 fixed — and the separation still holds,
 * because two readers of one payload are how a field ends up served to the wider
 * of the two audiences.
 */
export async function getStorageSettings(): Promise<StorageSettingsResponse> {
  const { data } = await client.get<StorageSettingsResponse>(`${BASE}/storage`);
  return data;
}

/**
 * PUT /admin/settings/storage — persist the active backend + non-secret fields.
 *
 * Returns the storage block directly (SEC-001): storage is no longer embedded in
 * the general system-settings response, and this endpoint is platform-admin
 * gated, so the freshly-persisted {@link StorageSettingsResponse} is returned.
 */
export async function updateStorageSettings(
  body: StorageSettingsUpdate,
): Promise<StorageSettingsResponse> {
  const { data } = await client.put<StorageSettingsResponse>(`${BASE}/storage`, body);
  return data;
}

/** POST /admin/settings/storage/test — probe backend reachability (no secrets). */
export async function testStorageConnection(
  body: StorageTestRequest,
): Promise<StorageTestResponse> {
  const { data } = await client.post<StorageTestResponse>(`${BASE}/storage/test`, body);
  return data;
}

/** DELETE /admin/settings/storage — clear the DB override (fall back to env). */
export async function clearStorageSettings(): Promise<void> {
  await client.delete(`${BASE}/storage`);
}

/**
 * GET /admin/recognition/status — platform-admin-only, global (no tenant slug).
 *
 * Returns the read-only status of the self-hosted DINOv2 image recognition
 * (REQ-029-A): feature/adapter availability, inference-service health, species
 * coverage and the effective configuration sourced from server env/settings.
 */
export async function getRecognitionStatus(): Promise<RecognitionStatus> {
  const { data } = await client.get<RecognitionStatus>('/admin/recognition/status');
  return data;
}

/** Result of starting a reference-image acquisition run from the UI. */
export interface AcquisitionStartResponse {
  status: string;
  task_id: string | null;
}

/**
 * POST /admin/recognition/acquire — dispatch a reference-image acquisition run
 * for all species (GBIF + Wikimedia → pgvector index). Available in light + full
 * mode for any signed-in user (like the recognition status + Pl@ntNet settings).
 */
export async function startRecognitionAcquisition(): Promise<AcquisitionStartResponse> {
  const { data } = await client.post<AcquisitionStartResponse>('/admin/recognition/acquire');
  return data;
}

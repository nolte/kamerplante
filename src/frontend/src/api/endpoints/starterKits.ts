import client, { tenantClient } from '../client';
import type { StarterKit, StarterKitWithAvailability } from '../types';

const BASE = '/starter-kits';

export async function listKits(difficulty?: string): Promise<StarterKit[]> {
  const params: Record<string, string> = {};
  if (difficulty) params.difficulty = difficulty;
  const { data } = await client.get<StarterKit[]>(BASE, { params });
  return data;
}

export async function getKit(kitId: string): Promise<StarterKit> {
  const { data } = await client.get<StarterKit>(`${BASE}/${kitId}`);
  return data;
}

export async function listKitsForTenant(
  difficulty?: string,
): Promise<StarterKit[]> {
  const params: Record<string, string> = {};
  if (difficulty) params.difficulty = difficulty;
  const { data } = await tenantClient.get<StarterKit[]>(BASE, { params });
  return data;
}

export async function getKitForTenant(
  kitId: string,
): Promise<StarterKitWithAvailability> {
  const { data } = await tenantClient.get<StarterKitWithAvailability>(
    `${BASE}/${kitId}`,
  );
  return data;
}

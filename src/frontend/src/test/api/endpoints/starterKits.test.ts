import { describe, it, expect, beforeEach, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const make = () => ({
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  });
  // starterKits.ts reads global kits via the default client and
  // tenant-availability variants via the tenantClient.
  return { globalClient: make(), tenantClient: make() };
});

vi.mock('@/api/client', () => ({
  __esModule: true,
  default: mocks.globalClient,
  tenantClient: mocks.tenantClient,
}));

import * as kits from '@/api/endpoints/starterKits';

const globalClient = mocks.globalClient;
const tenantClient = mocks.tenantClient;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('starterKits endpoints — global client', () => {
  it('listKits gets without difficulty by default', async () => {
    globalClient.get.mockResolvedValue({ data: [] });
    await kits.listKits();
    expect(globalClient.get).toHaveBeenCalledWith('/starter-kits', { params: {} });
  });

  it('listKits adds difficulty param when provided', async () => {
    globalClient.get.mockResolvedValue({ data: [] });
    await kits.listKits('beginner');
    expect(globalClient.get).toHaveBeenCalledWith('/starter-kits', {
      params: { difficulty: 'beginner' },
    });
  });

  it('getKit gets kit by id', async () => {
    globalClient.get.mockResolvedValue({ data: { id: 'k1' } });
    await kits.getKit('k1');
    expect(globalClient.get).toHaveBeenCalledWith('/starter-kits/k1');
  });
});

describe('starterKits endpoints — tenant client', () => {
  it('listKitsForTenant gets without difficulty by default', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await kits.listKitsForTenant();
    expect(tenantClient.get).toHaveBeenCalledWith('/starter-kits', { params: {} });
    expect(globalClient.get).not.toHaveBeenCalled();
  });

  it('listKitsForTenant adds difficulty param when provided', async () => {
    tenantClient.get.mockResolvedValue({ data: [] });
    await kits.listKitsForTenant('expert');
    expect(tenantClient.get).toHaveBeenCalledWith('/starter-kits', {
      params: { difficulty: 'expert' },
    });
  });

  it('getKitForTenant gets kit with availability', async () => {
    tenantClient.get.mockResolvedValue({ data: { id: 'k1' } });
    await kits.getKitForTenant('k1');
    expect(tenantClient.get).toHaveBeenCalledWith('/starter-kits/k1');
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createStoreWithTenantRole } from '@/test/helpers';
import type { AiTipCard } from '@/api/types';

const getTips = vi.fn();
const refreshTips = vi.fn();

vi.mock('@/api', () => ({
  aiApi: {
    getTips: (...args: unknown[]) => getTips(...args),
    refreshTips: (...args: unknown[]) => refreshTips(...args),
  },
}));

import TipCardsPanel from '@/components/ai/TipCardsPanel';

function makeTip(overrides: Partial<AiTipCard> = {}): AiTipCard {
  return {
    key: 'tip-1',
    context_type: 'planting_run',
    context_key: 'run-1',
    tip_type: 'care',
    priority: 'medium',
    title: 'Check the EC',
    body: 'The nutrient concentration is slightly high.',
    sources: [],
    language: 'de',
    language_mismatch_warning: false,
    uses_tenant_data: true,
    confidence: 'high',
    model_name: 'gemma3:12b',
    ...overrides,
  };
}

describe('TipCardsPanel', () => {
  beforeEach(() => {
    getTips.mockReset();
    refreshTips.mockReset();
  });

  it('renders tip cards wrapped in AIResponse', async () => {
    getTips.mockResolvedValue([makeTip()]);
renderWithProviders(<TipCardsPanel contextType="planting_run" contextKey="run-1" />, {
      store: createStoreWithTenantRole('grower'),
    });

    expect(await screen.findByTestId('tip-cards-panel')).toBeTruthy();
    expect(screen.getByText('Check the EC')).toBeTruthy();
    expect(screen.getByTestId('ai-badge')).toBeTruthy();
  });

  it('renders nothing when there are no tips', async () => {
    getTips.mockResolvedValue([]);
renderWithProviders(<TipCardsPanel contextType="planting_run" contextKey="run-1" />, {
      store: createStoreWithTenantRole('grower'),
    });

    await waitFor(() => expect(getTips).toHaveBeenCalled());
    expect(screen.queryByTestId('tip-cards-panel')).toBeNull();
  });

  it('force-refreshes tips via the refresh button', async () => {
    getTips.mockResolvedValue([makeTip()]);
    refreshTips.mockResolvedValue([makeTip({ title: 'Refreshed tip' })]);
    const user = userEvent.setup();
renderWithProviders(<TipCardsPanel contextType="planting_run" contextKey="run-1" />, {
      store: createStoreWithTenantRole('grower'),
    });

    await screen.findByTestId('tip-cards-panel');
    await user.click(screen.getByTestId('tip-cards-refresh'));

    await waitFor(() => expect(refreshTips).toHaveBeenCalled());
    expect(await screen.findByText('Refreshed tip')).toBeTruthy();
  });

  it('degrades to nothing on a fetch error', async () => {
    getTips.mockRejectedValue(new Error('offline'));
renderWithProviders(<TipCardsPanel contextType="plant_instance" contextKey="p-1" />, {
      store: createStoreWithTenantRole('grower'),
    });

    await waitFor(() => expect(getTips).toHaveBeenCalled());
    expect(screen.queryByTestId('tip-cards-panel')).toBeNull();
  });

  it('offers a viewer no refresh control', async () => {
    // Regenerating tips is a write on the server since #1353
    // (`require_tenant_role(grower)`), so a viewer's click would answer 403. A
    // control that looks live and is refused is the #1339 class; it is absent.
    getTips.mockResolvedValue([makeTip({ title: 'Readable tip' })]);
    renderWithProviders(<TipCardsPanel contextType="plant_instance" contextKey="p-1" />, {
      store: createStoreWithTenantRole('viewer'),
    });

    // The panel itself is a read surface and stays — asserted first, so the
    // absence below cannot be satisfied by a page that rendered nothing.
    expect(await screen.findByText('Readable tip')).toBeTruthy();
    expect(screen.queryByTestId('tip-cards-refresh')).toBeNull();
  });

  it('keeps the readable tips when a forced refresh fails', async () => {
    // The initial load hiding the panel is deliberate (UI-NFR-012, online-only).
    // A *failed refresh* is not the same case: the panel already holds tips the
    // reader may see, and clearing them turns a failed regeneration into the loss
    // of the read surface too.
    getTips.mockResolvedValue([makeTip({ title: 'Readable tip' })]);
    refreshTips.mockRejectedValue(new Error('refused'));
    const user = userEvent.setup();
    renderWithProviders(<TipCardsPanel contextType="plant_instance" contextKey="p-1" />, {
      store: createStoreWithTenantRole('grower'),
    });

    expect(await screen.findByText('Readable tip')).toBeTruthy();
    await user.click(screen.getByTestId('tip-cards-refresh'));

    await waitFor(() => expect(refreshTips).toHaveBeenCalled());
    expect(screen.getByTestId('tip-cards-panel')).toBeTruthy();
    expect(screen.getByText('Readable tip')).toBeTruthy();
  });
});

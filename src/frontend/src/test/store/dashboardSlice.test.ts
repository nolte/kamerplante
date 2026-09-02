import { describe, it, expect, beforeEach, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';

const apiMock = vi.hoisted(() => ({
  getWidgetCatalog: vi.fn(),
  getAggregated: vi.fn(),
}));
vi.mock('@/api/endpoints/dashboard', () => ({
  getWidgetCatalog: apiMock.getWidgetCatalog,
  getAggregated: apiMock.getAggregated,
}));

import reducer, { fetchWidgetCatalog, fetchAggregated } from '@/store/slices/dashboardSlice';

function createStore() {
  return configureStore({ reducer: { dashboard: reducer } });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('dashboardSlice', () => {
  it('has the empty initial state', () => {
    const state = reducer(undefined, { type: '@@INIT' });
    expect(state).toEqual({
      catalog: [],
      catalogLoaded: false,
      aggregated: {},
      loading: false,
      aggregatedLoading: false,
      error: null,
    });
  });

  describe('fetchWidgetCatalog', () => {
    it('sets loading on pending', () => {
      const state = reducer(undefined, { type: fetchWidgetCatalog.pending.type });
      expect(state.loading).toBe(true);
      expect(state.error).toBeNull();
    });

    it('leaves the aggregate flag alone — it is a different request (#1337)', async () => {
      // The catalogue answers in ~80ms, the aggregate in ~600ms. Sharing one
      // flag reported "settled" with every widget placeholder still standing,
      // which is what the dashboard's loading announcement spoke for.
      apiMock.getWidgetCatalog.mockResolvedValue({ widgets: [] });
      const store = createStore();
      store.dispatch({ type: fetchAggregated.pending.type });

      await store.dispatch(fetchWidgetCatalog());

      expect(store.getState().dashboard.loading).toBe(false);
      expect(store.getState().dashboard.aggregatedLoading).toBe(true);
    });

    it('stores the catalog and marks it loaded on fulfilled', async () => {
      apiMock.getWidgetCatalog.mockResolvedValue({ widgets: [{ widget_key: 'plants' }] });
      const store = createStore();
      await store.dispatch(fetchWidgetCatalog());
      const state = store.getState().dashboard;
      expect(state.catalog).toEqual([{ widget_key: 'plants' }]);
      expect(state.catalogLoaded).toBe(true);
      expect(state.loading).toBe(false);
    });

    it('records the error message on rejected', async () => {
      apiMock.getWidgetCatalog.mockRejectedValue(new Error('boom'));
      const store = createStore();
      await store.dispatch(fetchWidgetCatalog());
      expect(store.getState().dashboard.error).toBe('boom');
      expect(store.getState().dashboard.loading).toBe(false);
    });

    it('falls back to a default error message when none is given', () => {
      const state = reducer(undefined, {
        type: fetchWidgetCatalog.rejected.type,
        error: {},
      });
      expect(state.error).toBe('errors.dashboardCatalogLoadFailed');
    });
  });

  describe('fetchAggregated', () => {
    it('short-circuits to an empty object for no widget keys (no API call)', async () => {
      const store = createStore();
      await store.dispatch(fetchAggregated([]));
      expect(apiMock.getAggregated).not.toHaveBeenCalled();
      expect(store.getState().dashboard.aggregated).toEqual({});
    });

    it('stores the aggregated payload on fulfilled', async () => {
      apiMock.getAggregated.mockResolvedValue({ widgets: { plants: { count: 3 } } });
      const store = createStore();
      await store.dispatch(fetchAggregated(['plants']));
      expect(apiMock.getAggregated).toHaveBeenCalledWith(['plants']);
      expect(store.getState().dashboard.aggregated).toEqual({ plants: { count: 3 } });
    });

    it('raises and clears its own loading flag around the request (#1337)', async () => {
      let release!: (v: unknown) => void;
      apiMock.getAggregated.mockReturnValue(
        new Promise((resolve) => {
          release = resolve;
        }),
      );
      const store = createStore();
      const inFlight = store.dispatch(fetchAggregated(['plants']));

      expect(store.getState().dashboard.aggregatedLoading).toBe(true);
      expect(store.getState().dashboard.loading).toBe(false);

      release({ widgets: { plants: { count: 3 } } });
      await inFlight;
      expect(store.getState().dashboard.aggregatedLoading).toBe(false);
    });

    it('clears its loading flag on rejected, without claiming the catalogue error', async () => {
      // A flag left true on failure would leave the dashboard announcing a load
      // that has already given up.
      apiMock.getAggregated.mockRejectedValue(new Error('boom'));
      const store = createStore();
      await store.dispatch(fetchAggregated(['plants']));

      expect(store.getState().dashboard.aggregatedLoading).toBe(false);
      expect(store.getState().dashboard.error).toBeNull();
    });

    it('announces a refresh too: a second fetch raises the flag again', async () => {
      apiMock.getAggregated.mockResolvedValue({ widgets: {} });
      const store = createStore();
      await store.dispatch(fetchAggregated(['plants']));
      expect(store.getState().dashboard.aggregatedLoading).toBe(false);

      store.dispatch({ type: fetchAggregated.pending.type });
      expect(store.getState().dashboard.aggregatedLoading).toBe(true);
    });
  });
});

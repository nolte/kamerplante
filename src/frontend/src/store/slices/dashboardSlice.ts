import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { DashboardWidgetCatalogEntry } from '@/api/types';
import * as api from '@/api/endpoints/dashboard';

/**
 * REQ-045 — dashboard personalization read-state: the server-authoritative
 * widget catalog (availability) and the REQ-009 aggregated payloads for the
 * user's active widgets. Kept separate from userPreferences (which owns the
 * layout itself) so both the dashboard page and the settings tab can consume
 * catalog availability.
 */

interface DashboardState {
  catalog: DashboardWidgetCatalogEntry[];
  catalogLoaded: boolean;
  aggregated: Record<string, unknown>;
  /** `fetchWidgetCatalog` only. Availability, not widget content. */
  loading: boolean;
  /**
   * `fetchAggregated` only — the request the widget placeholders are waiting
   * for, and the one the dashboard's loading announcement speaks for (#1337).
   *
   * It is a *separate* flag rather than a shared one because the two requests
   * have very different shapes: the catalogue answers in ~80ms, the aggregate
   * in ~600ms, and a layout change refetches only the aggregate. A single flag
   * therefore reported "settled" with five skeletons still on screen, and
   * reported nothing at all on a refresh.
   *
   * Starts `false`, not `true`: a dashboard with no active widgets never
   * dispatches `fetchAggregated` at all (see the guard in the thunk), and an
   * optimistic `true` would leave it announcing a load that never happens.
   */
  aggregatedLoading: boolean;
  error: string | null;
}

const initialState: DashboardState = {
  catalog: [],
  catalogLoaded: false,
  aggregated: {},
  loading: false,
  aggregatedLoading: false,
  error: null,
};

export const fetchWidgetCatalog = createAsyncThunk('dashboard/fetchWidgetCatalog', async () => {
  const res = await api.getWidgetCatalog();
  return res.widgets;
});

export const fetchAggregated = createAsyncThunk('dashboard/fetchAggregated', async (widgetKeys: string[]) => {
  if (widgetKeys.length === 0) return {};
  const res = await api.getAggregated(widgetKeys);
  return res.widgets;
});

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchWidgetCatalog.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWidgetCatalog.fulfilled, (state, action) => {
        state.loading = false;
        state.catalog = action.payload;
        state.catalogLoaded = true;
      })
      .addCase(fetchWidgetCatalog.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message ?? 'errors.dashboardCatalogLoadFailed';
      })
      .addCase(fetchAggregated.pending, (state) => {
        state.aggregatedLoading = true;
      })
      .addCase(fetchAggregated.fulfilled, (state, action) => {
        state.aggregatedLoading = false;
        state.aggregated = action.payload;
      })
      .addCase(fetchAggregated.rejected, (state) => {
        // Without this case the flag would stay true forever on a failed fetch,
        // and the announcement would claim a load that has already given up.
        // `error` is deliberately left alone: it is the catalogue's, it is the
        // only one the page surfaces, and a widget-payload failure already shows
        // up as the widgets' own empty state.
        state.aggregatedLoading = false;
      });
  },
});

export default dashboardSlice.reducer;

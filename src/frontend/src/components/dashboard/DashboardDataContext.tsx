import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

/**
 * REQ-045 — provides the REQ-009 aggregated payloads (fetched once for all the
 * user's active widget keys, N+1 avoidance) to individual widgets.
 *
 * **And it carries the page's loading signal, which is the part #1373 added.**
 * Widgets with no aggregated slice fetch their own data — `weather_forecast` via
 * `useSiteWeatherForecast`, `winter_protection` via its own selector — so they sit
 * outside `aggregatedLoading` entirely. Both are in `BEGINNER_WIDGETS`, so on a
 * default dashboard the page's single live region announced "settled" while two
 * placeholders were still standing. The page claimed to be finished while it was
 * not, which is worse than announcing nothing.
 *
 * `usePendingWidget` is how a self-fetching widget says "count me". The
 * alternative designs both lose: moving those two slices into the aggregate
 * endpoint couples their cache and refresh semantics to the REQ-009 round trip,
 * and giving each widget its own `LoadingStatus` reintroduces the multi-region
 * chatter #1337 rejected for five widgets and would reject for two.
 */

interface DashboardData {
  payloads: Record<string, unknown>;
  loading: boolean;
  /** Register/release a self-fetching widget as pending. Stable identity. */
  setWidgetPending: (widgetKey: string, pending: boolean) => void;
}

const noop = () => {};

const DashboardDataContext = createContext<DashboardData>({
  payloads: {},
  loading: false,
  setWidgetPending: noop,
});

export function DashboardDataProvider({
  value,
  children,
}: {
  value: { payloads: Record<string, unknown>; loading: boolean };
  children: ReactNode;
}) {
  const { payloads, loading } = value;
  const [pendingCount, setPendingCount] = useState(0);
  //: Which keys are currently pending, so a widget re-rendering with the same
  //: state cannot double-count itself and a widget unmounting mid-flight cannot
  //: leave the counter above zero forever — which would pin the region active and
  //: be *worse* than the defect, since a region that never settles announces
  //: nothing useful either.
  const pendingKeys = useRef(new Set<string>());

  const setWidgetPending = useCallback((widgetKey: string, pending: boolean) => {
    const keys = pendingKeys.current;
    if (pending === keys.has(widgetKey)) return;
    if (pending) keys.add(widgetKey);
    else keys.delete(widgetKey);
    setPendingCount(keys.size);
  }, []);

  const contextValue = useMemo(
    () => ({ payloads, loading: loading || pendingCount > 0, setWidgetPending }),
    [payloads, loading, pendingCount, setWidgetPending],
  );

  return <DashboardDataContext.Provider value={contextValue}>{children}</DashboardDataContext.Provider>;
}

export function useWidgetPayload(widgetKey: string): { payload: unknown; loading: boolean } {
  const { payloads, loading } = useContext(DashboardDataContext);
  return { payload: payloads[widgetKey], loading };
}

/** The page-level pending flag, for the page that owns the live region. */
export function useDashboardPending(): boolean {
  return useContext(DashboardDataContext).loading;
}

/**
 * Count a self-fetching widget into the page's loading signal (#1373).
 *
 * Call it with the widget's own loading flag; it registers on the way in and
 * releases on unmount, so a widget that disappears mid-fetch cannot pin the
 * region active.
 */
export function usePendingWidget(widgetKey: string, pending: boolean): void {
  const { setWidgetPending } = useContext(DashboardDataContext);

  // `useEffect`, not `useMemo`. Registering is a side effect, and — the half that
  // actually bites — `useMemo` never runs a cleanup, so the release on unmount
  // would simply not happen and a widget that disappeared mid-fetch would pin the
  // region active forever. A region that never settles announces nothing useful
  // either, so that failure is not the safe direction.
  useEffect(() => {
    setWidgetPending(widgetKey, pending);
    return () => setWidgetPending(widgetKey, false);
  }, [widgetKey, pending, setWidgetPending]);
}

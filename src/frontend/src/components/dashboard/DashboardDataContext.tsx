import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
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
  /**
   * The REQ-009 aggregate fetch, and ONLY that — what an aggregated widget shows a
   * placeholder for.
   *
   * **Kept separate from the page signal on purpose.** Folding the two together is
   * the obvious shortcut and it is wrong: `useWidgetPayload` hands this flag to
   * `GenericWidget` and `PlantGridWidget`, so a combined value re-skeletons every
   * aggregated widget for as long as any self-fetching one is pending. On a
   * default beginner dashboard the aggregate returns in well under a second while
   * `useSiteWeatherForecast` needs two sequential round trips, so all five
   * aggregated widgets would sit on their placeholders waiting for the weather —
   * and `PlantGridWidget` would hide its filter toolbar with them. Measured, not
   * reasoned: the first version of this file did exactly that.
   */
  aggregateLoading: boolean;
  /** Aggregate **or** any self-fetching widget. Only the page's live region reads this. */
  pageLoading: boolean;
  /** Register/release a self-fetching widget as pending. Stable identity. */
  setWidgetPending: (id: string, pending: boolean) => void;
}

const noop = () => {};

const DashboardDataContext = createContext<DashboardData>({
  payloads: {},
  aggregateLoading: false,
  pageLoading: false,
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

  const setWidgetPending = useCallback((id: string, pending: boolean) => {
    const keys = pendingKeys.current;
    if (pending === keys.has(id)) return;
    if (pending) keys.add(id);
    else keys.delete(id);
    setPendingCount(keys.size);
  }, []);

  const contextValue = useMemo(
    () => ({
      payloads,
      aggregateLoading: loading,
      pageLoading: loading || pendingCount > 0,
      setWidgetPending,
    }),
    [payloads, loading, pendingCount, setWidgetPending],
  );

  return <DashboardDataContext.Provider value={contextValue}>{children}</DashboardDataContext.Provider>;
}

export function useWidgetPayload(widgetKey: string): { payload: unknown; loading: boolean } {
  const { payloads, aggregateLoading } = useContext(DashboardDataContext);
  return { payload: payloads[widgetKey], loading: aggregateLoading };
}

/** The page-level pending flag, for the page that owns the live region. */
export function useDashboardPending(): boolean {
  return useContext(DashboardDataContext).pageLoading;
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
  // Keyed on a per-HOOK id, not on `widgetKey`. Two components registering the
  // same key would otherwise share one slot, and the first release would settle
  // the region while the second was still pending — the original defect,
  // reproduced. `dashboardLayoutOps.addWidget` appends without a duplicate check
  // and the layout arrives from user preferences, so a repeated `widget_key` is
  // representable even though today's UI has no path to it.
  const instanceId = useId();
  const id = `${widgetKey}:${instanceId}`;

  // `useEffect`, not `useMemo`. Registering is a side effect, and — the half that
  // actually bites — `useMemo` never runs a cleanup, so the release on unmount
  // would simply not happen and a widget that disappeared mid-fetch would pin the
  // region active forever. A region that never settles announces nothing useful
  // either, so that failure is not the safe direction.
  useEffect(() => {
    setWidgetPending(id, pending);
    return () => setWidgetPending(id, false);
  }, [id, pending, setWidgetPending]);
}

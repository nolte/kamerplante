import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup, act } from '@testing-library/react';
import { useState } from 'react';
import {
  DashboardDataProvider,
  useDashboardPending,
  usePendingWidget,
} from '@/components/dashboard/DashboardDataContext';

/**
 * #1373 — the dashboard has exactly one loading announcement, driven by the
 * REQ-009 aggregate fetch. Two widgets on the same page fetch their own data and
 * sat outside that flag, so the region reported "settled" while their
 * placeholders were still standing. Both are in `BEGINNER_WIDGETS`, so a default
 * beginner dashboard showed the defect on every load.
 *
 * The invariant under test is the one #1337 established and this must not break:
 * **exactly one loading announcer**, active until *every* visible placeholder is
 * gone. The tests below drive the context directly rather than the page, because
 * the page's own load path is a settled scan — and a settled scan cannot see this
 * defect, which is the measurement note both #1337 and #1373 carry.
 */

function Pending({ widgetKey, pending }: { widgetKey: string; pending: boolean }) {
  usePendingWidget(widgetKey, pending);
  return null;
}

function Region() {
  const active = useDashboardPending();
  return <span data-testid="region">{active ? 'active' : 'settled'}</span>;
}

function setup(ui: React.ReactNode, aggregateLoading = false) {
  return render(
    <DashboardDataProvider value={{ payloads: {}, loading: aggregateLoading }}>
      <Region />
      {ui}
    </DashboardDataProvider>,
  );
}

describe('the dashboard loading signal', () => {
  afterEach(() => cleanup());

  it('stays active while a self-fetching widget is still loading', () => {
    setup(<Pending widgetKey="weather_forecast" pending />);
    expect(screen.getByTestId('region')).toHaveTextContent('active');
  });

  it('settles only after the last self-fetching widget releases', () => {
    function Both() {
      const [weather, setWeather] = useState(true);
      const [winter, setWinter] = useState(true);
      return (
        <>
          <Pending widgetKey="weather_forecast" pending={weather} />
          <Pending widgetKey="winter_protection" pending={winter} />
          <button onClick={() => setWeather(false)}>weather done</button>
          <button onClick={() => setWinter(false)}>winter done</button>
        </>
      );
    }
    setup(<Both />);
    expect(screen.getByTestId('region')).toHaveTextContent('active');

    act(() => screen.getByText('weather done').click());
    expect(screen.getByTestId('region')).toHaveTextContent('active');

    act(() => screen.getByText('winter done').click());
    expect(screen.getByTestId('region')).toHaveTextContent('settled');
  });

  it('is active when only the aggregate is loading', () => {
    // The control for the other direction: the original signal must keep working.
    setup(null, true);
    expect(screen.getByTestId('region')).toHaveTextContent('active');
  });

  it('settles when nothing is pending', () => {
    // The control that matters most. A signal that is always active announces
    // nothing useful and is not an improvement over announcing too early.
    setup(<Pending widgetKey="weather_forecast" pending={false} />);
    expect(screen.getByTestId('region')).toHaveTextContent('settled');
  });

  it('releases a widget that unmounts mid-fetch', () => {
    // Without the effect cleanup the counter never returns to zero and the region
    // stays active forever — worse than the defect, because a region that never
    // settles is as uninformative as one that settles too early. An earlier draft
    // registered through `useMemo`, which runs no cleanup at all.
    function Disappearing() {
      const [mounted, setMounted] = useState(true);
      return (
        <>
          {mounted && <Pending widgetKey="weather_forecast" pending />}
          <button onClick={() => setMounted(false)}>unmount</button>
        </>
      );
    }
    setup(<Disappearing />);
    expect(screen.getByTestId('region')).toHaveTextContent('active');

    act(() => screen.getByText('unmount').click());
    expect(screen.getByTestId('region')).toHaveTextContent('settled');
  });

  it('does not double-count a widget that re-renders while pending', () => {
    // A plain counter would increment on every render and never come back down:
    // ONE release cannot undo three registrations. The registry keys on the widget
    // name for that reason, and this drives it — re-render twice, then release
    // once, and the region must settle.
    //
    // The first draft of this test ended in `expect(true).toBe(true)` after a
    // `cleanup()`, which asserts nothing at all — the tautology class this
    // repository has closed nineteen issues about.
    function Rerendering() {
      const [, bump] = useState(0);
      const [pending, setPending] = useState(true);
      return (
        <>
          <Pending widgetKey="weather_forecast" pending={pending} />
          <button onClick={() => bump((n) => n + 1)}>rerender</button>
          <button onClick={() => setPending(false)}>done</button>
        </>
      );
    }
    setup(<Rerendering />);

    act(() => screen.getByText('rerender').click());
    act(() => screen.getByText('rerender').click());
    expect(screen.getByTestId('region')).toHaveTextContent('active');

    act(() => screen.getByText('done').click());
    expect(screen.getByTestId('region')).toHaveTextContent('settled');
  });
});

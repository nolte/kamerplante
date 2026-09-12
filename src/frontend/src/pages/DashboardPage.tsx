import { useEffect, useMemo, useState, lazy, Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Skeleton from '@mui/material/Skeleton';
import { visuallyHidden } from '@mui/utils';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import SettingsIcon from '@mui/icons-material/Settings';
import DesktopWindowsIcon from '@mui/icons-material/DesktopWindows';
import TabletIcon from '@mui/icons-material/Tablet';
import SmartphoneIcon from '@mui/icons-material/Smartphone';
import DashboardCustomizeIcon from '@mui/icons-material/DashboardCustomize';
import LoadingStatus from '@/components/common/LoadingStatus';
import PageTitle from '@/components/layout/PageTitle';
import { kamiStateDashboardWelcome } from '@/assets/brand/illustrations';
import DashboardReadonlyGrid from '@/components/dashboard/DashboardReadonlyGrid';
import { DashboardDataProvider, useDashboardPending } from '@/components/dashboard/DashboardDataContext';
import WidgetConfigDialog from '@/components/dashboard/WidgetConfigDialog';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchWidgetCatalog, fetchAggregated } from '@/store/slices/dashboardSlice';
import { useDashboardLayout } from '@/hooks/useDashboardLayout';
import {
  dashboardWidgetCatalog,
  placementsForBreakpoint,
  type WidgetKey,
} from '@/config/dashboardWidgetCatalog';
import {
  moveWidget,
  resizeWidget,
  removeWidget,
  setBreakpointPlacements,
  copyPlacementsToAllBreakpoints,
  setWidgetConfig,
  sortByReadingOrder,
} from '@/lib/dashboardLayoutOps';
import {
  isPersonalizationHintDismissed,
  dismissPersonalizationHint,
} from '@/lib/dashboardLayoutStorage';
import type { DashboardLayout, DashboardWidgetInstance, WidgetPlacement } from '@/api/types';

const DashboardEditGrid = lazy(() => import('@/components/dashboard/DashboardEditGrid'));

type Breakpoint = 'lg' | 'md' | 'sm';

/**
 * The dashboard's single loading announcement, as a child of
 * `DashboardDataProvider` rather than inline (#1373).
 *
 * It has to be a child: a component cannot read a context it renders itself, and
 * the signal it needs now includes the self-fetching widgets that register
 * through `usePendingWidget`. Inline, it could only ever see `aggregatedLoading`
 * — which is exactly the defect, the region going empty while two placeholders
 * still stand.
 */
function DashboardLoadingAnnouncement() {
  const { t } = useTranslation();
  const active = useDashboardPending();
  return (
    <LoadingStatus
      active={active}
      label={t('dashboard.loading.announcement')}
      data-testid="dashboard-loading-status"
    />
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { layout, activeWidgets, isWidgetRenderable, catalogLoaded, persist, reset } =
    useDashboardLayout();
  const aggregated = useAppSelector((s) => s.dashboard.aggregated);
  // The *aggregate* flag, not the catalogue one. They are different requests
  // with different durations, and the widget placeholders wait for this one.
  const aggregatedLoading = useAppSelector((s) => s.dashboard.aggregatedLoading);

  const [editMode, setEditMode] = useState(false);
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('lg');
  const [working, setWorking] = useState<DashboardLayout | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const [hintDismissed, setHintDismissed] = useState(isPersonalizationHintDismissed());
  const [configTarget, setConfigTarget] = useState<DashboardWidgetInstance | null>(null);

  // Parallel initial load (O-001): catalog + aggregated fire independently of
  // the globally-loaded user preferences. The catalog is availability metadata
  // that does not change within a session, so it is fetched once and kept —
  // re-navigating onto the dashboard must not put the cached grid back into a
  // loading state. Same guard as DashboardSettingsTab, the other consumer.
  useEffect(() => {
    if (!catalogLoaded) void dispatch(fetchWidgetCatalog());
  }, [dispatch, catalogLoaded]);

  const activeWidgetKeys = useMemo(() => layout.widgets.map((w) => w.widget_key), [layout.widgets]);
  useEffect(() => {
    if (activeWidgetKeys.length) void dispatch(fetchAggregated(activeWidgetKeys));
  }, [dispatch, activeWidgetKeys.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  const effectiveLayout = editMode && working ? working : layout;

  const enterEdit = () => {
    setWorking(structuredClone(layout));
    setEditMode(true);
  };
  const cancelEdit = () => {
    setEditMode(false);
    setWorking(null);
  };
  const saveEdit = () => {
    if (working) persist(working);
    setEditMode(false);
    setWorking(null);
  };

  const mutate = (next: DashboardLayout, announce?: string) => {
    setWorking(next);
    if (announce) setAnnouncement(announce);
  };

  const orderedInstances = useMemo(() => {
    const placements = placementsForBreakpoint(effectiveLayout, breakpoint);
    const byId = new Map(effectiveLayout.widgets.map((w) => [w.instance_id, w]));
    return sortByReadingOrder(placements)
      .map((p) => byId.get(p.instance_id))
      .filter((w): w is DashboardWidgetInstance => Boolean(w));
  }, [effectiveLayout, breakpoint]);

  const widgetProps = (instance: DashboardWidgetInstance) => {
    const idx = orderedInstances.findIndex((w) => w.instance_id === instance.instance_id);
    const def = dashboardWidgetCatalog[instance.widget_key as WidgetKey];
    const label = t(`dashboard.widgets.${instance.widget_key}.label`);
    return {
      isFirst: idx <= 0,
      isLast: idx === orderedInstances.length - 1,
      hasConfig: def?.hasConfig ?? false,
      onMoveUp: () =>
        mutate(
          moveWidget(working ?? layout, breakpoint, instance.instance_id, 'up'),
          t('dashboard.edit.movedUp', { widget: label }),
        ),
      onMoveDown: () =>
        mutate(
          moveWidget(working ?? layout, breakpoint, instance.instance_id, 'down'),
          t('dashboard.edit.movedDown', { widget: label }),
        ),
      onGrow: () =>
        mutate(
          resizeWidget(working ?? layout, breakpoint, instance.instance_id, 1, 1),
          t('dashboard.edit.grew', { widget: label }),
        ),
      onShrink: () =>
        mutate(
          resizeWidget(working ?? layout, breakpoint, instance.instance_id, -1, -1),
          t('dashboard.edit.shrank', { widget: label }),
        ),
      onRemove: () =>
        mutate(
          removeWidget(working ?? layout, instance.instance_id),
          t('dashboard.edit.removed', { widget: label }),
        ),
      onConfigure: () => setConfigTarget(instance),
    };
  };

  const handleGridChange = (placements: WidgetPlacement[]) => {
    mutate(setBreakpointPlacements(working ?? layout, breakpoint, placements));
  };

  const handleConfigSave = (config: Record<string, unknown>) => {
    if (!configTarget) return;
    const base = working ?? layout;
    const next = setWidgetConfig(base, configTarget.instance_id, config);
    if (editMode) setWorking(next);
    else persist(next);
  };

  const dismissHint = () => {
    dismissPersonalizationHint();
    setHintDismissed(true);
  };

  const isEmpty = effectiveLayout.widgets.length === 0 || activeWidgets.length === 0;

  return (
    <Box data-testid="dashboard-page">
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <PageTitle title={t('pages.dashboard.title')} />
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          {editMode && (
            <ToggleButtonGroup
              size="small"
              exclusive
              value={breakpoint}
              onChange={(_, v) => v && setBreakpoint(v)}
              aria-label={t('dashboard.edit.breakpointSwitcher')}
            >
              <ToggleButton
                value="lg"
                aria-label={t('dashboard.edit.desktop')}
                sx={{ minWidth: 48, minHeight: 48 }}
              >
                <DesktopWindowsIcon fontSize="small" />
              </ToggleButton>
              <ToggleButton
                value="md"
                aria-label={t('dashboard.edit.tablet')}
                sx={{ minWidth: 48, minHeight: 48 }}
              >
                <TabletIcon fontSize="small" />
              </ToggleButton>
              <ToggleButton
                value="sm"
                aria-label={t('dashboard.edit.mobile')}
                sx={{ minWidth: 48, minHeight: 48 }}
              >
                <SmartphoneIcon fontSize="small" />
              </ToggleButton>
            </ToggleButtonGroup>
          )}
          {editMode && (
            <Tooltip title={t('dashboard.edit.applyToAll')}>
              <Button
                size="small"
                startIcon={<DashboardCustomizeIcon />}
                onClick={() =>
                  mutate(copyPlacementsToAllBreakpoints(working ?? layout, breakpoint))
                }
                sx={{ minHeight: 48 }}
              >
                {t('dashboard.edit.applyToAllShort')}
              </Button>
            </Tooltip>
          )}
          <Tooltip title={t('dashboard.manageWidgets')}>
            <IconButton
              aria-label={t('dashboard.manageWidgets')}
              onClick={() => navigate('/settings#dashboard')}
              sx={{ minWidth: 48, minHeight: 48 }}
              data-testid="dashboard-manage-link"
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          {editMode ? (
            <>
              <Button
                onClick={cancelEdit}
                sx={{ minHeight: 48 }}
                data-testid="dashboard-edit-cancel"
              >
                {t('common.cancel')}
              </Button>
              <Button
                variant="contained"
                onClick={saveEdit}
                sx={{ minHeight: 48 }}
                data-testid="dashboard-edit-save"
              >
                {t('common.save')}
              </Button>
            </>
          ) : (
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={enterEdit}
              sx={{ minHeight: 48 }}
              data-testid="dashboard-edit-toggle"
            >
              {t('dashboard.edit.enter')}
            </Button>
          )}
        </Stack>
      </Box>

      {!editMode && !hintDismissed && (
        <Alert
          severity="info"
          action={
            <IconButton
              aria-label={t('common.close')}
              color="inherit"
              size="small"
              onClick={dismissHint}
              sx={{ minWidth: 48, minHeight: 48 }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          }
          sx={{ mb: 2 }}
          data-testid="dashboard-coachmark"
        >
          {t('dashboard.coachmark')}
        </Alert>
      )}

      <Box aria-live="polite" role="status" sx={visuallyHidden}>
        {announcement}
      </Box>

      {isEmpty ? (
        <Box sx={{ textAlign: 'center', py: 8 }} data-testid="dashboard-empty-state">
          <Box
            component="img"
            src={kamiStateDashboardWelcome}
            alt=""
            aria-hidden="true"
            sx={{ maxHeight: 180, maxWidth: '100%', objectFit: 'contain', mb: 2, opacity: 0.85 }}
          />
          <Typography variant="h6" gutterBottom>
            {t('dashboard.empty.title')}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {t('dashboard.empty.hint')}
          </Typography>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            sx={{ justifyContent: 'center' }}
          >
            <Button
              variant="contained"
              onClick={() => navigate('/settings#dashboard')}
              sx={{ minHeight: 48 }}
            >
              {t('dashboard.empty.chooseWidgets')}
            </Button>
            <Button
              variant="outlined"
              onClick={reset}
              sx={{ minHeight: 48 }}
              data-testid="dashboard-empty-reset"
            >
              {t('dashboard.empty.restoreDefault')}
            </Button>
          </Stack>
        </Box>
      ) : (
        <DashboardDataProvider value={{ payloads: aggregated, loading: aggregatedLoading }}>
          {/*
            Issue #1337 item 1 — the dashboard's single loading announcement.

            Every other loading placeholder in this frontend pairs its `aria-busy`
            wrapper with its own `LoadingStatus` live region (#1324/#1329). That
            shape does not scale here: mid-load the grid stands with five
            aggregated placeholders at once, so a region per placeholder would be
            five concurrent polite regions all saying "loading" — worse than the
            silence it replaces. The decision taken instead:

            - **One region, owned by this page**, above the edit-mode ternary so
              the toggle cannot remount it, and inside the provider so it and the
              placeholders read one and the same `aggregatedLoading`.
            - **It speaks for the aggregate**, which is what the placeholders are
              waiting for — including on a refresh, where only the aggregate is
              refetched and a catalogue-driven region would stay silent.
            - **Empty, not unmounted, when settled** (`active`): a live region
              must exist before its content changes for the change to be
              announced, so a second load is not swallowed.
            - **A widget finishing early changes nothing.** The aggregate is one
              round trip for all widget keys, so the text is written once when
              the load starts and once when it ends.

            The page keeps a *second* status region above (the edit-mode
            move/resize announcements). Two regions are deliberate here: they
            have disjoint sources and disjoint lifetimes, and merging them into
            one node would mean one message silently overwriting the other when
            a layout edit and a refetch land together. What must be unique is the
            *loading* announcer, and this is it — no widget announces its own
            load, and no settled widget announces its empty state.

            **Known gap (#1373):** two widgets fetch their own data and are not
            represented by this flag — `weather_forecast` (bare `Skeleton`s, no
            `aria-busy`, no announcement) and `winter_protection` (a labelled
            `CircularProgress`, so named but not announced). Both are default
            beginner widgets, so on a default dashboard this region goes empty
            while their placeholders still stand. Covering them needs a way for a
            self-fetching widget to register into the page-level signal, which is
            a data-layer decision rather than a markup fix.
          */}
          <DashboardLoadingAnnouncement />
          {editMode ? (
            <Suspense fallback={<Skeleton variant="rounded" height={400} />}>
              <DashboardEditGrid
                layout={effectiveLayout}
                breakpoint={breakpoint}
                onChange={handleGridChange}
                widgetProps={widgetProps}
              />
            </Suspense>
          ) : (
            <DashboardReadonlyGrid layout={effectiveLayout} renderableKeys={isWidgetRenderable} />
          )}
        </DashboardDataProvider>
      )}

      {configTarget && (
        <WidgetConfigDialog
          open
          widgetKey={configTarget.widget_key}
          config={configTarget.config ?? {}}
          onClose={() => setConfigTarget(null)}
          onSave={handleConfigSave}
        />
      )}
    </Box>
  );
}

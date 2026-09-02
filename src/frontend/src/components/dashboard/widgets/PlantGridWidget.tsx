import { useCallback, useMemo, useState, type MouseEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import Skeleton from '@mui/material/Skeleton';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import type { TFunction } from 'i18next';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import EventIcon from '@mui/icons-material/Event';
import GridViewIcon from '@mui/icons-material/GridView';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import PlaceIcon from '@mui/icons-material/Place';
import SpaIcon from '@mui/icons-material/Spa';
import ViewAgendaIcon from '@mui/icons-material/ViewAgenda';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import { useModuleVisibility } from '@/hooks/useModuleVisibility';
import { useColumnFilters } from '@/hooks/useColumnFilters';
import { ColumnFilterBar, type ColumnFilterDef } from '@/components/common/ColumnFilterBar';
import { useWidgetPayload } from '@/components/dashboard/DashboardDataContext';
import { dashboardWidgetCatalog } from '@/config/dashboardWidgetCatalog';
import { formatDate, humanizeSlug } from '@/utils/formatting';
import type { WidgetComponentProps } from '@/components/dashboard/widgetRegistry';

/**
 * DASH-2 / issue #488 — rich, filterable plant-instance grid widget.
 *
 * Turns the ``plant_grid`` panel from #461's icon+name tile strip into a
 * first-class overview: every active plant instance is its own compact card
 * carrying glanceable status (cultivar, current growth phase, location, next
 * due date), plants with an open task/care reminder are visibly flagged, the
 * panel is filterable on phase / location / open-task, and the user can switch
 * between a *detailed* (fewer, richer cards) and a *compact* (more, denser
 * cards) format.
 *
 * Data comes from the aggregated ``plant_grid`` payload (``useWidgetPayload``),
 * enriched server-side in a single AQL round-trip (no extra fetch, no N+1) — see
 * ``ArangoPlantInstanceRepository.list_active_for_tenant``.
 */

/** Route the panel + each card's *title* deep-link into (mirrors #461). */
const PLANT_LINK_BASE = '/pflanzen/plant-instances';
/** Deep-link bases for the card's granular per-field links (FIX-02 R4). */
const SPECIES_LINK_BASE = '/stammdaten/species';
const LOCATION_LINK_BASE = '/standorte/locations';
const PHASE_LINK_BASE = '/phasen/definitionen';

/** URL-param ids owned by this widget's filters (namespaced so several dashboard
 *  widgets can coexist without clashing query params). */
const FILTER_PHASE = 'pg_phase';
const FILTER_LOCATION = 'pg_location';
const FILTER_TASK = 'pg_task';
const FILTER_IDS = [FILTER_PHASE, FILTER_LOCATION, FILTER_TASK] as const;

/** Sentinel filter token for plants missing a phase / location. */
const NONE_TOKEN = '__none__';
/** Open-task facet tokens. */
const TASK_OPEN = 'open';
const TASK_NONE = 'none';

/** localStorage key persisting the chosen card format per user/browser (#488 AC6). */
const FORMAT_STORAGE_KEY = 'kp-plant-grid-format';
type CardFormat = 'detailed' | 'compact';
const DEFAULT_FORMAT: CardFormat = 'detailed';

/** One enriched plant-instance card as delivered in the aggregated ``plant_grid`` slice. */
export interface PlantGridEntry {
  _key?: string;
  /** Human-readable business identifier (e.g. "7432") — the small secondary reference (R1). */
  instance_id?: string | null;
  /** Optional user-given label; may be empty or hold the bare number (see A1). */
  plant_name?: string | null;
  species_key?: string;
  /** Species common name (first entry), for the speaking card title (R2). */
  species_common_name?: string | null;
  /** Species scientific name, shown as a secondary hint (R2). */
  species_scientific_name?: string | null;
  cultivar_key?: string | null;
  cultivar_name?: string | null;
  phase_key?: string | null;
  /** Resolved phase-definition key targeting the phase link; null → chip without link (R5). */
  phase_definition_key?: string | null;
  phase_name?: string | null;
  location_key?: string | null;
  location_name?: string | null;
  has_open_task?: boolean;
  next_due_date?: string | null;
}

/** Per-target link-visibility flags, derived once in the widget and passed to every card. */
interface CardLinkTargets {
  plant: boolean;
  species: boolean;
  location: boolean;
  phase: boolean;
}

function readStoredFormat(): CardFormat {
  try {
    const raw = window.localStorage.getItem(FORMAT_STORAGE_KEY);
    return raw === 'compact' || raw === 'detailed' ? raw : DEFAULT_FORMAT;
  } catch {
    // jsdom / privacy modes may throw on localStorage access — fall back silently.
    return DEFAULT_FORMAT;
  }
}

function persistFormat(format: CardFormat): void {
  try {
    window.localStorage.setItem(FORMAT_STORAGE_KEY, format);
  } catch {
    // Non-fatal: the choice simply won't survive a reload.
  }
}

export default function PlantGridWidget({ widgetKey, editMode = false }: WidgetComponentProps) {
  const { t } = useTranslation();
  const { isPathVisible } = useModuleVisibility();
  const { payload, loading } = useWidgetPayload(widgetKey);
  const columnFilters = useColumnFilters(FILTER_IDS);

  // Card format is user-owned and persisted in localStorage (AC6). Keeping it in
  // localStorage (not the dashboard widget config) keeps the widget self-contained
  // and makes the switch work identically in read-only and edit mode.
  const [format, setFormat] = useState<CardFormat>(readStoredFormat);
  const handleFormatChange = useCallback((_e: MouseEvent<HTMLElement>, next: CardFormat | null) => {
    if (next) {
      setFormat(next);
      persistFormat(next);
    }
  }, []);

  const plants = useMemo<PlantGridEntry[]>(() => {
    const obj =
      payload && typeof payload === 'object' && !Array.isArray(payload)
        ? (payload as Record<string, unknown>)
        : null;
    return obj && Array.isArray(obj.plants) ? (obj.plants as PlantGridEntry[]) : [];
  }, [payload]);

  const { values } = columnFilters;

  // ── Filter facet options, derived from the plants actually present ──
  const filterDefs = useMemo<ColumnFilterDef[]>(() => {
    const phaseByToken = new Map<string, string>();
    const locationByToken = new Map<string, string>();
    for (const p of plants) {
      const phaseToken = p.phase_key || NONE_TOKEN;
      phaseByToken.set(
        phaseToken,
        phaseToken === NONE_TOKEN
          ? t('dashboard.plantGrid.filterValues.noPhase')
          : p.phase_name || humanizeSlug(p.phase_key) || phaseToken,
      );
      const locToken = p.location_key || NONE_TOKEN;
      locationByToken.set(
        locToken,
        locToken === NONE_TOKEN
          ? t('dashboard.plantGrid.filterValues.noLocation')
          : p.location_name || humanizeSlug(p.location_key) || locToken,
      );
    }
    const toOptions = (m: Map<string, string>) =>
      [...m.entries()]
        .map(([value, label]) => ({ value, label }))
        // Stable, locale-aware ordering; the "none" sentinel sinks to the bottom.
        .sort((a, b) => {
          if (a.value === NONE_TOKEN) return 1;
          if (b.value === NONE_TOKEN) return -1;
          return a.label.localeCompare(b.label);
        });
    return [
      { id: FILTER_PHASE, label: t('dashboard.plantGrid.filters.phase'), options: toOptions(phaseByToken) },
      { id: FILTER_LOCATION, label: t('dashboard.plantGrid.filters.location'), options: toOptions(locationByToken) },
      {
        id: FILTER_TASK,
        label: t('dashboard.plantGrid.filters.task'),
        options: [
          { value: TASK_OPEN, label: t('dashboard.plantGrid.filterValues.hasTask') },
          { value: TASK_NONE, label: t('dashboard.plantGrid.filterValues.noTask') },
        ],
      },
    ];
  }, [plants, t]);

  // ── Client-side filtering (the payload is already loaded in full) ──
  const filtered = useMemo<PlantGridEntry[]>(() => {
    const phases = values[FILTER_PHASE] ?? [];
    const locations = values[FILTER_LOCATION] ?? [];
    const tasks = values[FILTER_TASK] ?? [];
    if (phases.length === 0 && locations.length === 0 && tasks.length === 0) return plants;
    return plants.filter((p) => {
      const phaseToken = p.phase_key || NONE_TOKEN;
      const locToken = p.location_key || NONE_TOKEN;
      const taskToken = p.has_open_task ? TASK_OPEN : TASK_NONE;
      if (phases.length > 0 && !phases.includes(phaseToken)) return false;
      if (locations.length > 0 && !locations.includes(locToken)) return false;
      if (tasks.length > 0 && !tasks.includes(taskToken)) return false;
      return true;
    });
  }, [plants, values]);

  // Each card field links to a different section; navigation is suppressed in edit
  // mode (drag/resize owns the pointer) and whenever the target module is hidden
  // (REQ-042). Memoised so the object identity is stable for the card props.
  const linkTargets = useMemo<CardLinkTargets>(
    () => ({
      plant: !editMode && isPathVisible(PLANT_LINK_BASE),
      species: !editMode && isPathVisible(SPECIES_LINK_BASE),
      location: !editMode && isPathVisible(LOCATION_LINK_BASE),
      phase: !editMode && isPathVisible(PHASE_LINK_BASE),
    }),
    [editMode, isPathVisible],
  );
  const listPath = dashboardWidgetCatalog.plant_grid.navigateTo;
  const showListLink = !editMode && Boolean(listPath) && isPathVisible(listPath ?? '');
  const widgetLabel = t(`dashboard.widgets.${widgetKey}.label`);

  return (
    <Card sx={{ height: '100%' }} data-testid={`widget-${widgetKey}`}>
      <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
        {/* Header: icon + label + (read-only) open-list affordance. */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography
            variant="subtitle1"
            component="h3"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexGrow: 1, minWidth: 0, m: 0 }}
          >
            <GridViewIcon color="primary" fontSize="small" aria-hidden="true" sx={{ flexShrink: 0 }} />
            <Box component="span" sx={{ minWidth: 0, overflowWrap: 'break-word' }}>
              {widgetLabel}
            </Box>
          </Typography>
          {showListLink && listPath && (
            <Tooltip title={t('dashboard.nav.openListNamed', { widget: widgetLabel })}>
              <IconButton
                component={RouterLink}
                to={listPath}
                size="small"
                aria-label={t('dashboard.nav.openListNamed', { widget: widgetLabel })}
                sx={{ width: 48, height: 48, color: 'text.secondary', flexShrink: 0 }}
                data-testid={`widget-${widgetKey}-open-list`}
              >
                <ChevronRightIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>

        {/* Controls (hidden in edit mode so drag/resize + kebab own the pointer). */}
        {!editMode && !loading && plants.length > 0 && (
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: 1,
            }}
          >
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <ColumnFilterBar filters={filterDefs} state={columnFilters} />
            </Box>
            <ToggleButtonGroup
              value={format}
              exclusive
              onChange={handleFormatChange}
              size="small"
              aria-label={t('dashboard.plantGrid.format.label')}
              data-testid="plant-grid-format-switch"
            >
              <ToggleButton
                value="detailed"
                aria-label={t('dashboard.plantGrid.format.detailed')}
                sx={{ minWidth: 48, minHeight: 48 }}
                data-testid="plant-grid-format-detailed"
              >
                <Tooltip title={t('dashboard.plantGrid.format.detailed')}>
                  <ViewAgendaIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
              <ToggleButton
                value="compact"
                aria-label={t('dashboard.plantGrid.format.compact')}
                sx={{ minWidth: 48, minHeight: 48 }}
                data-testid="plant-grid-format-compact"
              >
                <Tooltip title={t('dashboard.plantGrid.format.compact')}>
                  <ViewModuleIcon fontSize="small" />
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        )}

        {/* Body */}
        <Box sx={{ flexGrow: 1, minHeight: 0 }}>
          {loading ? (
            // Busy, but deliberately unnamed — see GenericWidget / #1337. The
            // dashboard's single loading announcement is owned by DashboardPage.
            <Box
              aria-busy="true"
              data-testid={`widget-${widgetKey}-loading`}
              sx={{ display: 'grid', gap: 1, gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }}
            >
              <Skeleton variant="rounded" height={72} />
              <Skeleton variant="rounded" height={72} />
              <Skeleton variant="rounded" height={72} />
            </Box>
          ) : plants.length === 0 ? (
            // Resting content, not an announcement (#1337): this appears the
            // moment the aggregate resolves, alongside every sibling widget's
            // empty state. The grid's single loading region has already spoken
            // for that transition.
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ textAlign: 'center', py: 3 }}
              data-testid={`widget-${widgetKey}-empty`}
            >
              {t('dashboard.plantGrid.empty')}
            </Typography>
          ) : filtered.length === 0 ? (
            // This one *stays* a live region, and the difference is the trigger:
            // it is the result of the user changing a filter, not of data
            // arriving, so there is a user action for it to answer and it cannot
            // coincide with the other widgets settling.
            <Typography
              variant="body2"
              color="text.secondary"
              role="status"
              aria-live="polite"
              sx={{ textAlign: 'center', py: 3 }}
              data-testid={`widget-${widgetKey}-no-matches`}
            >
              {t('dashboard.plantGrid.noMatches')}
            </Typography>
          ) : (
            <Box
              sx={{
                display: 'grid',
                gap: 1,
                gridTemplateColumns:
                  format === 'compact'
                    ? 'repeat(auto-fill, minmax(172px, 1fr))'
                    : 'repeat(auto-fill, minmax(220px, 1fr))',
              }}
              data-testid={`widget-${widgetKey}-cards`}
            >
              {filtered.map((p, i) => (
                <PlantGridCard
                  key={p._key ?? i}
                  plant={p}
                  format={format}
                  linkTargets={linkTargets}
                  t={t}
                />
              ))}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

interface PlantGridCardProps {
  plant: PlantGridEntry;
  format: CardFormat;
  linkTargets: CardLinkTargets;
  t: TFunction;
}

interface CardLabels {
  /** Primary speaking title (R1 / A1). */
  title: string;
  /** Label for the species link row (A2), kept distinct from the title where possible. */
  speciesLabel: string;
  /**
   * True when `speciesLabel` holds the scientific (botanical) name rather than a
   * common name — used to render it in italics (botanical convention), which also
   * helps visually disambiguate the species row from the title row (R7: title/
   * subtitle hierarchy without redundancy).
   */
  speciesLabelIsScientific: boolean;
}

/**
 * Derive the card's speaking title and species-row label (R1 / R4 / A1 / A2).
 *
 * ``plant_name`` is treated as a real user label unless it is empty or merely
 * echoes the bare identifier (``instance_id`` / ``_key`` — e.g. "7432"), in which
 * case the species common name (with the cultivar when present) becomes the title;
 * the final title fallback chain is common name → ``humanizeSlug(species_key)`` →
 * "unnamed".
 *
 * The species row is always its *own* link (R4). To avoid echoing the title
 * verbatim when the common name has been promoted to the title, the species row
 * then prefers the scientific name — so the two links stay visibly distinct.
 */
function resolveCardLabels(plant: PlantGridEntry, t: TFunction): CardLabels {
  const rawName = (plant.plant_name ?? '').trim();
  const hasUserLabel = rawName !== '' && rawName !== plant.instance_id && rawName !== plant._key;
  const commonName = (plant.species_common_name ?? '').trim();
  const scientific = (plant.species_scientific_name ?? '').trim();
  const humanized = humanizeSlug(plant.species_key) || '';

  let title: string;
  let titleIsCommonName = false;
  if (hasUserLabel) {
    title = rawName;
  } else {
    const base = commonName || humanized;
    titleIsCommonName = Boolean(commonName);
    title = base
      ? plant.cultivar_name
        ? `${base} '${plant.cultivar_name}'`
        : base
      : t('dashboard.plantGrid.unnamed');
  }

  const speciesLabel = titleIsCommonName
    ? scientific || commonName
    : commonName || scientific || humanized;
  const speciesLabelIsScientific = speciesLabel === scientific && scientific !== '';

  return { title, speciesLabel, speciesLabelIsScientific };
}

/**
 * Shared touch-target sizing for every inline link/clickable chip on the card
 * (R7, UI-NFR-001 R-011/R-013): each interactive element gets its own ≥48px
 * hit height on mobile/tablet, where fingers need the room; on desktop
 * (`md+`) it may shrink to the 36px mouse-precision allowance (R-013) so the
 * compact format stays dense where a pointer — not a fingertip — is doing the
 * clicking. Applied directly to each `Link`/clickable `Chip` (not a wrapping
 * `Box`) so the enlarged hit area belongs to the interactive element itself.
 */
const touchTargetSx = {
  minHeight: { xs: 48, sm: 48, md: 36 },
  display: 'inline-flex',
  alignItems: 'center',
} as const;

function PlantGridCard({ plant, format, linkTargets, t }: PlantGridCardProps) {
  const { title, speciesLabel, speciesLabelIsScientific } = resolveCardLabels(plant, t);
  const detailed = format === 'detailed';
  const hasTask = plant.has_open_task === true;
  const reference = plant.instance_id ?? plant._key ?? '';

  // Granular per-field links (R4/R6): the card is NOT a single card-wide anchor —
  // each interactive element is its own sibling link, so no anchor is ever nested
  // inside another (valid HTML + a clean tab order).
  const linkPlant = linkTargets.plant && Boolean(plant._key);
  const linkSpecies = linkTargets.species && Boolean(plant.species_key) && Boolean(speciesLabel);
  const linkLocation = linkTargets.location && Boolean(plant.location_key);
  const linkPhase = linkTargets.phase && Boolean(plant.phase_definition_key);

  // Location label, resolved once so it can be rendered either in its own row
  // (detailed) or merged with the species row (compact — A5 density pass).
  const locationLabel = plant.location_key ? plant.location_name || humanizeSlug(plant.location_key) || '' : '';
  const hasLocation = Boolean(locationLabel);

  // The card is a `role="group"` so assistive tech announces the plant's identity
  // (and, non-visually, its open-task state — reusing `card.openTaskAria`, R7 a11y)
  // as soon as focus enters it, before the individual per-field links are reached.
  const cardAriaLabel = hasTask ? `${title} — ${t('dashboard.plantGrid.card.openTaskAria')}` : title;

  const cardSx = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'stretch',
    gap: { xs: 1, sm: 0.75, md: 0.5 },
    minHeight: 48, // ≥48px touch target (UI-NFR-001, Mobile-First)
    px: 1,
    py: 0.75,
    borderRadius: 1,
    border: 1,
    // Open-task plants get an accent border + left keyline so they stand out at a
    // glance (AC4). The colour cue is paired with a text badge below so the signal
    // is never colour-only.
    borderColor: hasTask ? 'warning.main' : 'divider',
    borderLeft: hasTask ? 4 : 1,
    borderLeftColor: hasTask ? 'warning.main' : 'divider',
    width: '100%',
    textAlign: 'left',
    bgcolor: 'background.paper',
  } as const;

  // Species row content (icon-less): its own link into the species catalog (R4),
  // shared between the detailed (own row) and compact (merged with location)
  // layouts so the link/tooltip/italic logic lives in exactly one place.
  const speciesNode = speciesLabel ? (
    <Tooltip title={speciesLabel}>
      {linkSpecies ? (
        <Link
          component={RouterLink}
          to={`${SPECIES_LINK_BASE}/${plant.species_key}`}
          variant="caption"
          underline="always"
          color="text.secondary"
          aria-label={t('dashboard.nav.openSpecies', { species: speciesLabel })}
          noWrap
          sx={{
            ...touchTargetSx,
            minWidth: 0,
            fontStyle: speciesLabelIsScientific ? 'italic' : 'normal',
          }}
          data-testid={`plant-grid-species-link-${plant._key}`}
        >
          {speciesLabel}
        </Link>
      ) : (
        <Typography
          variant="caption"
          noWrap
          sx={{ fontStyle: speciesLabelIsScientific ? 'italic' : 'normal' }}
        >
          {speciesLabel}
        </Typography>
      )}
    </Tooltip>
  ) : null;

  // Location row content, mirroring `speciesNode` above (R3/R4/A5).
  const locationNode = hasLocation ? (
    <Tooltip title={locationLabel}>
      {linkLocation ? (
        <Link
          component={RouterLink}
          to={`${LOCATION_LINK_BASE}/${plant.location_key}`}
          variant="caption"
          underline="always"
          color="text.secondary"
          aria-label={t('dashboard.nav.openLocation', { location: locationLabel })}
          noWrap
          sx={{ ...touchTargetSx, minWidth: 0 }}
          data-testid={`plant-grid-location-link-${plant._key}`}
        >
          {locationLabel}
        </Link>
      ) : (
        <Typography variant="caption" noWrap>
          {locationLabel}
        </Typography>
      )}
    </Tooltip>
  ) : null;

  return (
    <Box sx={cardSx} role="group" aria-label={cardAriaLabel} data-testid={`plant-grid-card-${plant._key}`}>
      {/* Title row — the plant's speaking name, linking to the plant detail (R1/R4).
          In compact format the bare reference number rides along on the same line
          (A5 density); in detailed format it gets its own line below (more room). */}
      <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5, minWidth: 0 }}>
        <LocalFloristIcon color="primary" fontSize="small" aria-hidden="true" sx={{ flexShrink: 0 }} />
        {linkPlant ? (
          <Link
            component={RouterLink}
            to={`${PLANT_LINK_BASE}/${plant._key}`}
            variant="body2"
            underline="always"
            color="text.primary"
            aria-label={t('dashboard.nav.openPlant', { plant: title })}
            sx={{ ...touchTargetSx, fontWeight: 600, minWidth: 0, overflowWrap: 'break-word' }}
            data-testid={`plant-grid-title-link-${plant._key}`}
          >
            {title}
          </Link>
        ) : (
          <Typography variant="body2" sx={{ fontWeight: 600, minWidth: 0, overflowWrap: 'break-word' }}>
            {title}
          </Typography>
        )}
        {!detailed && reference && (
          <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
            {t('dashboard.plantGrid.card.reference', { id: reference })}
          </Typography>
        )}
        {hasTask && (
          <NotificationsActiveIcon
            color="warning"
            fontSize="small"
            aria-hidden="true"
            sx={{ ml: 'auto', flexShrink: 0 }}
            data-testid={`plant-grid-open-task-${plant._key}`}
          />
        )}
      </Box>

      {/* Bare number as a small secondary reference — never the sole title (R1).
          Detailed format only; compact folds it into the title row above. */}
      {detailed && reference && (
        <Typography variant="caption" color="text.secondary" noWrap>
          {t('dashboard.plantGrid.card.reference', { id: reference })}
        </Typography>
      )}

      {detailed ? (
        // Detailed: species gets its own breathing-room row (A5 — more room, more rows).
        speciesNode && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', minWidth: 0 }}>
            <SpaIcon fontSize="inherit" aria-hidden="true" sx={{ flexShrink: 0 }} />
            {speciesNode}
          </Box>
        )
      ) : (
        // Compact: species + location share one row, separated by a visual "·"
        // divider, to cut the card's row count under pressure (A5). DOM order
        // (species then location) still matches the detailed layout's reading
        // order, so tab order never jumps around between formats.
        (speciesNode || locationNode) && (
          <Box
            sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.75, color: 'text.secondary', minWidth: 0 }}
          >
            {speciesNode && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
                <SpaIcon fontSize="inherit" aria-hidden="true" sx={{ flexShrink: 0 }} />
                {speciesNode}
              </Box>
            )}
            {speciesNode && locationNode && (
              <Box component="span" aria-hidden="true" sx={{ color: 'text.disabled' }}>
                &middot;
              </Box>
            )}
            {locationNode && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, minWidth: 0 }}>
                <PlaceIcon fontSize="inherit" aria-hidden="true" sx={{ flexShrink: 0 }} />
                {locationNode}
              </Box>
            )}
          </Box>
        )
      )}

      {detailed && plant.cultivar_name && (
        // Secondary content only — `noWrap` keeps narrow compact-grid cards tidy,
        // and the `Tooltip` restores the full value on hover/tap when it clips.
        <Tooltip title={plant.cultivar_name}>
          <Typography variant="caption" color="text.secondary" noWrap>
            {plant.cultivar_name}
          </Typography>
        </Tooltip>
      )}

      {/* Phase chip — links to the phase definition when resolvable, otherwise a
          plain chip (R5 graceful degradation). */}
      {plant.phase_name &&
        (linkPhase ? (
          <Chip
            component={RouterLink}
            to={`${PHASE_LINK_BASE}/${plant.phase_definition_key}`}
            clickable
            icon={<SpaIcon />}
            label={plant.phase_name}
            size="small"
            variant="outlined"
            color="primary"
            aria-label={t('dashboard.nav.openPhase', { phase: plant.phase_name })}
            sx={{ ...touchTargetSx, alignSelf: 'flex-start', maxWidth: '100%' }}
            data-testid={`plant-grid-phase-link-${plant._key}`}
          />
        ) : (
          <Chip
            icon={<SpaIcon />}
            label={plant.phase_name}
            size="small"
            variant="outlined"
            color="primary"
            aria-label={`${t('dashboard.plantGrid.card.phase')}: ${plant.phase_name}`}
            sx={{ alignSelf: 'flex-start', maxWidth: '100%' }}
          />
        ))}

      {/* Location row — detailed format only here; compact already folded it into
          the merged species/location row above (R3, both formats still covered). */}
      {detailed && locationNode && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', minWidth: 0 }}>
          <PlaceIcon fontSize="inherit" aria-hidden="true" sx={{ flexShrink: 0 }} />
          {locationNode}
        </Box>
      )}

      {/* Due date — informational only, never a link (R4). */}
      {detailed && plant.next_due_date && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', minWidth: 0 }}>
          <EventIcon fontSize="inherit" aria-hidden="true" sx={{ flexShrink: 0 }} />
          <Typography variant="caption" noWrap>
            {t('dashboard.plantGrid.card.nextDue', { date: formatDate(plant.next_due_date) })}
          </Typography>
        </Box>
      )}

      {hasTask && (
        <Chip
          label={t('dashboard.plantGrid.card.openTask')}
          size="small"
          color="warning"
          variant="outlined"
          sx={{ alignSelf: 'flex-start', mt: 0.25 }}
          data-testid={`plant-grid-open-task-chip-${plant._key}`}
        />
      )}
    </Box>
  );
}

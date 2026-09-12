import { usePendingWidget } from '@/components/dashboard/DashboardDataContext';
import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActionArea from '@mui/material/CardActionArea';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import { alpha } from '@mui/material/styles';
import AcUnitIcon from '@mui/icons-material/AcUnit';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import type { SvgIconComponent } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchHardinessOverview } from '@/store/slices/overwinteringProfilesSlice';
import SeasonOverviewPanel from './SeasonOverviewPanel';
import type {
  WinterHardinessLight,
  WinterHardinessOverviewEntry,
} from '@/api/types';

/** Human-readable primary/secondary labels derived for one red overview entry. */
interface RedEntryLabels {
  /** Speaking title — user-given name, else species/common, else raw reference. */
  title: string;
  /** Secondary species + location line; empty when nothing enriched. */
  detail: string;
}

/**
 * Derive the display labels for a red plant, mirroring the Pflanzenübersicht
 * card logic (`PlantGridWidget.resolveCardLabels`): a user-given speaking name
 * wins, falling back to the species common/scientific name, and only as a last
 * resort to the raw subject key so the entry is never titled by a bare doc key
 * (#631). The species name and location form the secondary detail line.
 */
function resolveRedEntryLabels(
  entry: WinterHardinessOverviewEntry,
  unknownLabel: string,
): RedEntryLabels {
  const rawName = (entry.plant_name ?? '').trim();
  const commonName = (entry.species_common_name ?? '').trim();
  const scientific = (entry.species_scientific_name ?? '').trim();
  const location = (entry.location_name ?? '').trim();
  const subjectKey = entry.plant_key ?? entry.planting_run_key ?? '';

  // A user label only counts when it is meaningful — not empty and not just an
  // echo of the raw key / instance id the user never typed.
  const hasUserLabel =
    rawName !== '' &&
    rawName !== entry.instance_id &&
    rawName !== subjectKey;

  const speciesName = commonName || scientific;

  let title: string;
  if (hasUserLabel) {
    title = rawName;
  } else if (speciesName) {
    title = speciesName;
  } else {
    title = subjectKey || unknownLabel;
  }

  // Secondary line: species name (when it did not already become the title) and
  // the location, so the user sees "what" and "where" at a glance.
  const detailParts: string[] = [];
  if (speciesName && speciesName !== title) {
    detailParts.push(speciesName);
  }
  if (location) {
    detailParts.push(location);
  }

  return { title, detail: detailParts.join(' · ') };
}

/** REQ-022 §Winterhärte-Ampel — traffic-light colour → MUI palette token. */
export const winterColor: Record<
  WinterHardinessLight,
  'success' | 'warning' | 'error'
> = {
  green: 'success',
  yellow: 'warning',
  red: 'error',
};

/**
 * Icon per traffic-light colour so the signal is never colour-only
 * (WCAG 1.4.1 / red-green colour-blindness — every tile carries a distinct
 * icon shape in addition to the colour and the text label below the count).
 */
const winterIcon: Record<WinterHardinessLight, SvgIconComponent> = {
  green: CheckCircleIcon,
  yellow: WarningAmberIcon,
  red: ReportProblemIcon,
};

const TILE_ORDER: WinterHardinessLight[] = ['green', 'yellow', 'red'];

/**
 * REQ-022 dashboard widget "Winterschutz-Übersicht". Aggregates all
 * overwintering profiles of the active tenant into a three-colour traffic
 * light and lists the red (must-relocate) plants with their winter action.
 */
export default function WinterProtectionWidget() {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  // Self-fetching like the weather widget, and outside the aggregate flag for the
  // same reason (#1373).
  const { overview, overviewLoading, overviewError } = useAppSelector(
    (s) => s.overwinteringProfiles,
  );

  useEffect(() => {
    dispatch(fetchHardinessOverview());
  }, [dispatch]);

  const tiles = useMemo(
    () =>
      TILE_ORDER.map((light) => ({
        light,
        count: overview ? overview[light] : 0,
      })),
    [overview],
  );

  const redPlants = useMemo(() => overview?.red_plants ?? [], [overview]);

  const total = overview?.total ?? 0;

  // Registered on the SAME expression the placeholder uses, not on the bare
  // `overviewLoading`. A re-mount with cached data re-dispatches the fetch while
  // the widget keeps rendering its content, and the bare flag would announce
  // "loading" with no placeholder standing anywhere (#1373).
  usePendingWidget('winter_protection', overviewLoading && total === 0);

  const showAllClear = total > 0 && redPlants.length === 0;

  return (
    <Card data-testid="winter-protection-widget">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <AcUnitIcon color="primary" />
          <Typography variant="h6" component="h2" id="winter-protection-title">
            {t('pages.dashboard.winterProtection.title')}
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t('pages.dashboard.winterProtection.subtitle')}
        </Typography>

        {/* REQ-047 §4.1 — per-site season state + trigger source (renders only
            when the tenant has outdoor/greenhouse sites with a season state). */}
        <SeasonOverviewPanel />

        {overviewLoading && total === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={28} aria-label={t('common.loading')} />
          </Box>
        ) : overviewError && total === 0 ? (
          <Alert severity="error" data-testid="winter-protection-error">
            {t('pages.dashboard.winterProtection.error')}
          </Alert>
        ) : total === 0 ? (
          <Typography
            variant="body2"
            color="text.secondary"
            data-testid="winter-protection-empty"
          >
            {t('pages.dashboard.winterProtection.empty')}
          </Typography>
        ) : (
          <>
            {/* Mobile-first: three equal-width tiles stacked in a single row even on
                the smallest phones — a taller, single-column stack would push the
                red action list (the most urgent content) further down the page. */}
            <Grid container spacing={1.5}>
              {tiles.map(({ light, count }) => {
                const TileIcon = winterIcon[light];
                return (
                  <Grid size={4} key={light}>
                    <CardActionArea
                      onClick={() => navigate('/ueberwinterung/profile')}
                      sx={{ borderRadius: 1 }}
                      aria-label={`${t(
                        `pages.dashboard.winterProtection.tile.${light}`,
                      )}: ${count}`}
                    >
                      <Box
                        sx={{
                          textAlign: 'center',
                          py: 1.5,
                          px: 0.5,
                          borderRadius: 1,
                          border: 1,
                          borderColor: `${winterColor[light]}.main`,
                          bgcolor: (theme) =>
                            alpha(theme.palette[winterColor[light]].main, 0.08),
                        }}
                        data-testid={`winter-tile-${light}`}
                      >
                        <TileIcon
                          fontSize="small"
                          sx={{ color: `${winterColor[light]}.main`, mb: 0.25 }}
                        />
                        <Typography
                          variant="h4"
                          sx={{ color: `${winterColor[light]}.main`, fontWeight: 600, lineHeight: 1.2 }}
                          data-testid={`winter-count-${light}`}
                        >
                          {count}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {t(`pages.dashboard.winterProtection.tile.${light}`)}
                        </Typography>
                      </Box>
                    </CardActionArea>
                  </Grid>
                );
              })}
            </Grid>

            {showAllClear && (
              <Box
                sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}
                data-testid="winter-protection-all-clear"
              >
                <CheckCircleIcon color="success" fontSize="small" />
                <Typography variant="body2" color="text.secondary">
                  {t('pages.dashboard.winterProtection.allClear')}
                </Typography>
              </Box>
            )}

            {redPlants.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <ReportProblemIcon color="error" fontSize="small" />
                  {t('pages.dashboard.winterProtection.actionRequired')}
                </Typography>
                <List dense disablePadding data-testid="winter-red-list">
                  {redPlants.map((entry) => {
                    const { title, detail } = resolveRedEntryLabels(
                      entry,
                      t('pages.dashboard.winterProtection.unknownSubject'),
                    );
                    const ratingLabel = t(
                      `enums.hardinessRating.${entry.hardiness_rating}`,
                    );
                    return (
                      <ListItem
                        key={entry.profile_key}
                        disableGutters
                        secondaryAction={
                          <Chip
                            label={t(`enums.winterAction.${entry.winter_action}`)}
                            size="small"
                            color="error"
                            variant="outlined"
                          />
                        }
                        data-testid={`winter-red-${entry.profile_key}`}
                      >
                        <ListItemText
                          primary={title}
                          secondary={
                            <>
                              {detail && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  component="span"
                                  sx={{ display: 'block' }}
                                  data-testid={`winter-red-detail-${entry.profile_key}`}
                                >
                                  {detail}
                                </Typography>
                              )}
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                component="span"
                                sx={{ display: 'block' }}
                              >
                                {ratingLabel}
                              </Typography>
                            </>
                          }
                        />
                      </ListItem>
                    );
                  })}
                </List>
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

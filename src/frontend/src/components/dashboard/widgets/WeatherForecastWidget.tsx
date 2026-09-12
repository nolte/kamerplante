import { type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Typography from '@mui/material/Typography';
import Skeleton from '@mui/material/Skeleton';
import CloudIcon from '@mui/icons-material/Cloud';
import AcUnitIcon from '@mui/icons-material/AcUnit';
import WeatherProvenanceBadge from '@/components/weather/WeatherProvenanceBadge';
import { useSiteWeatherForecast } from '@/hooks/useSiteWeatherForecast';
import { usePendingWidget } from '@/components/dashboard/DashboardDataContext';
import { formatDate, formatNumber } from '@/utils/formatting';

/** Temperatures render with a fixed single decimal so rows stay visually aligned. */
const TEMP_FORMAT = { minimumFractionDigits: 1, maximumFractionDigits: 1 };

/**
 * REQ-046 §4.2 / Issue #392 (R7) — dashboard weather-forecast widget.
 *
 * Renders the per-site daily forecast (date + min/max °C + provenance badge)
 * delivered by `GET /sites/{siteKey}/weather-forecast`, topped by a prominent
 * frost early-warning badge when the backend reports an in-horizon frost
 * (`forecast_frost_warning === true`). Falls back to the REQ-046 configure
 * empty state when no site / no source is available, and degrades gracefully to
 * a friendly hint (never a crash) when the read endpoint errors.
 */
export default function WeatherForecastWidget() {
  const { t } = useTranslation();
  const { loading, error, site, forecast, multipleSites, refetch } = useSiteWeatherForecast();
  // This widget fetches its own data, so the page's aggregate flag never saw it
  // and the single live region announced "settled" over a standing skeleton
  // (#1373). Registering here is what makes the page's claim true.
  usePendingWidget('weather_forecast', loading);

  const days = forecast?.forecasts ?? [];
  const frostActive = forecast?.forecast_frost_warning === true;

  const renderShell = (body: ReactNode) => (
    <Card sx={{ height: '100%' }} data-testid="widget-weather_forecast">
      <CardContent sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Typography
          variant="subtitle1"
          component="h3"
          sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}
        >
          <CloudIcon fontSize="small" color="primary" />
          {t('dashboard.widgets.weather_forecast.label')}
        </Typography>
        {body}
      </CardContent>
    </Card>
  );

  if (loading) {
    return renderShell(
      // `aria-busy` like the aggregated widgets: MUI's `Skeleton` renders an empty
      // `<span>` with no role and no name, so without this the placeholder is
      // SILENT in the accessibility tree rather than merely unnamed (#1373).
      <Stack aria-busy="true" spacing={1} data-testid="weather-widget-loading" sx={{ flexGrow: 1 }}>
        <Skeleton variant="rounded" height={28} />
        <Skeleton variant="rounded" height={28} />
        <Skeleton variant="rounded" height={28} />
      </Stack>,
    );
  }

  // Endpoint / network error → friendly, non-blocking hint (never a crash),
  // with a Retry action per UI-NFR-004 R-015 (network errors MUST offer retry).
  if (error) {
    return renderShell(
      <Alert
        severity="info"
        variant="outlined"
        data-testid="weather-widget-error"
        sx={{ mt: 1 }}
        action={
          <Button color="inherit" size="small" onClick={refetch} sx={{ minHeight: 48 }}>
            {t('common.retry')}
          </Button>
        }
      >
        {t('dashboard.widgets.weather_forecast.loadError')}
      </Alert>,
    );
  }

  // No site, or a site without any persisted forecast (no configured source):
  // keep the REQ-046 configure-oriented empty state.
  if (!site || days.length === 0) {
    return renderShell(
      <Box
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          gap: 1.5,
          color: 'text.secondary',
        }}
      >
        <Typography variant="body2">
          {t('dashboard.widgets.weather_forecast.emptyHint')}
        </Typography>
        <Button
          component={RouterLink}
          to="/standorte/sites"
          variant="outlined"
          data-testid="weather-widget-configure"
          sx={{ minHeight: 48 }}
        >
          {t('dashboard.widgets.weather_forecast.configureCta')}
        </Button>
      </Box>,
    );
  }

  return renderShell(
    <Stack spacing={1.5} sx={{ flexGrow: 1 }}>
      {frostActive && (
        <Alert
          severity="warning"
          icon={<AcUnitIcon fontSize="inherit" />}
          data-testid="weather-frost-warning"
        >
          <AlertTitle sx={{ mb: 0.25 }}>
            {t('dashboard.widgets.weather_forecast.frostTitle')}
          </AlertTitle>
          <Typography variant="body2">
            {t('dashboard.widgets.weather_forecast.frostDetail', {
              date: formatDate(forecast?.forecast_expected_date),
              temp: formatNumber(forecast?.forecast_min_temperature, TEMP_FORMAT),
            })}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            {t('dashboard.widgets.weather_forecast.frostExplainer')}
          </Typography>
        </Alert>
      )}

      {multipleSites && (
        <Typography variant="caption" color="text.secondary" data-testid="weather-site-name">
          {t('dashboard.widgets.weather_forecast.siteHeader', { name: site.name })}
        </Typography>
      )}

      <Stack spacing={1} data-testid="weather-forecast-rows">
        {days.map((day) => (
          <Box
            key={`${day.forecast_date}-${day.source}`}
            data-testid={`weather-forecast-row-${day.forecast_date}`}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              flexWrap: 'wrap',
              justifyContent: 'space-between',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', minWidth: 0 }}>
              <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 96 }}>
                {formatDate(day.forecast_date)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('dashboard.widgets.weather_forecast.tempRange', {
                  min: formatNumber(day.temp_min_c, TEMP_FORMAT),
                  max: formatNumber(day.temp_max_c, TEMP_FORMAT),
                })}
              </Typography>
            </Box>
            <WeatherProvenanceBadge source={day.source} dataKind={day.data_kind} />
          </Box>
        ))}
      </Stack>
    </Stack>,
  );
}

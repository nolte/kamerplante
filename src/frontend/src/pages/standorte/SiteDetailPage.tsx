import { useEffect, useMemo, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SensorsIcon from '@mui/icons-material/Sensors';
import { useForm, useWatch } from 'react-hook-form';
import MobileCard from '@/components/common/MobileCard';
import PageTitle from '@/components/layout/PageTitle';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ErrorDisplay from '@/components/common/ErrorDisplay';
import EmptyState from '@/components/common/EmptyState';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import DataTable, { type Column } from '@/components/common/DataTable';
import { useTableLocalState } from '@/hooks/useTableState';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormNumberField from '@/components/form/FormNumberField';
import FormSelectField from '@/components/form/FormSelectField';
import FormClimateZoneField from '@/components/form/FormClimateZoneField';
import FormTimezoneField from '@/components/form/FormTimezoneField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import UnsavedChangesGuard from '@/components/form/UnsavedChangesGuard';
import WaterSourceSection, { TAP_WATER_DEFAULTS, RO_WATER_DEFAULTS } from '@/components/water/WaterSourceSection';
import GpsDetectButton from './GpsDetectButton';
import HardinessZoneDetectButton from './HardinessZoneDetectButton';
import LocationTreeSection from './LocationTreeSection';
import SiteRunsSection from './SiteRunsSection';
import WeatherSourceSection from './WeatherSourceSection';
import SiteClimateSection from './SiteClimateSection';
import SensorCreateDialog from './SensorCreateDialog';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import { useSmartHomeEnabled } from '@/hooks/useSmartHomeEnabled';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchSite, clearCurrent } from '@/store/slices/sitesSlice';
import { setBreadcrumbs } from '@/store/slices/uiSlice';
import * as api from '@/api/endpoints/sites';
import type { Sensor, SiteWaterConfig } from '@/api/types';
import { buildSiteResolver, gpsToFields, gpsToPayload, isWeatherRelevantSiteType, siteTypeOptions, type SiteFormData } from './siteForm';

const DEFAULT_VALUES: SiteFormData = {
  name: '',
  type: 'indoor',
  gps_lat: '',
  gps_lon: '',
  climate_zone: '',
  total_area_m2: 0,
  timezone: 'UTC',
};

export default function SiteDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const notification = useNotification();
  const { handleError } = useApiError();
  // Issue #587: sensor UI is gated behind the smart-home toggle.
  const { isSmartHomeEnabled } = useSmartHomeEnabled();
  const { currentSite: current, loading, error } = useAppSelector((s) => s.sites);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingSensor, setDeletingSensor] = useState(false);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [sensorDialogOpen, setSensorDialogOpen] = useState(false);
  const [editSensor, setEditSensor] = useState<Sensor | undefined>(undefined);
  const [deleteSensorKey, setDeleteSensorKey] = useState<string | null>(null);
  const [waterConfig, setWaterConfig] = useState<SiteWaterConfig>({
    has_ro_system: false,
    tap_water_profile: { ...TAP_WATER_DEFAULTS },
    ro_water_profile: { ...RO_WATER_DEFAULTS },
  });
  const sensorTableState = useTableLocalState({ defaultSort: { column: 'name', direction: 'asc' } });

  const resolver = useMemo(() => buildSiteResolver(t), [t]);
  const typeOptions = useMemo(() => siteTypeOptions(t), [t]);
  const { control, handleSubmit, reset, setValue, formState: { isDirty } } = useForm<SiteFormData>({
    resolver,
    defaultValues: DEFAULT_VALUES,
  });
  // REQ-046 follow-up — the weather/frost section further down this page only
  // ever unlocks for weather-relevant sites (outdoor/greenhouse/balcony, see
  // WEATHER_RELEVANT_SITE_TYPES) with GPS coordinates; the discreet hint below
  // keeps that connection visible while editing.
  const watchedType = useWatch({ control, name: 'type' });
  const weatherEnabledForType = isWeatherRelevantSiteType(watchedType);

  const loadSensors = useCallback(async () => {
    if (!key) return;
    try {
      const s = await api.getSiteSensors(key);
      setSensors(s);
    } catch {
      // Sensors may not be available
    }
  }, [key]);

  useEffect(() => {
    if (key) {
      dispatch(fetchSite(key));
      loadSensors();
    }
    return () => { dispatch(clearCurrent()); };
  }, [key, dispatch, loadSensors]);

  useEffect(() => {
    if (current) {
      reset({
        name: current.name,
        type: current.type,
        ...gpsToFields(current.gps_coordinates),
        climate_zone: current.climate_zone,
        total_area_m2: current.total_area_m2,
        timezone: current.timezone ?? 'UTC',
      });
      const wc = current.water_config;
      setWaterConfig({
        has_ro_system: wc?.has_ro_system ?? false,
        tap_water_profile: wc?.tap_water_profile ?? { ...TAP_WATER_DEFAULTS },
        ro_water_profile: wc?.ro_water_profile ?? { ...RO_WATER_DEFAULTS },
      });
    }
  }, [current, reset]);

  // Dynamic breadcrumbs
  useEffect(() => {
    if (!current) return;
    dispatch(setBreadcrumbs([
      { label: 'nav.dashboard', path: '/dashboard' },
      { label: 'nav.sites', path: '/standorte/sites' },
      { label: current.name },
    ]));
  }, [current, dispatch]);

  // Clear dynamic breadcrumbs on unmount
  useEffect(() => () => { dispatch(setBreadcrumbs([])); }, [dispatch]);

  const onSubmit = async (data: SiteFormData) => {
    if (!key) return;
    try {
      setSaving(true);
      await api.updateSite(key, {
        name: data.name,
        type: data.type,
        gps_coordinates: gpsToPayload(data),
        climate_zone: data.climate_zone,
        total_area_m2: data.total_area_m2,
        timezone: data.timezone,
        water_config: waterConfig,
      });
      notification.success(t('common.save'));
      dispatch(fetchSite(key));
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async () => {
    if (!key) return;
    setDeleting(true);
    try {
      await api.deleteSite(key);
      notification.success(t('common.delete'));
      navigate('/standorte/sites');
    } catch (err) {
      handleError(err);
    } finally {
      setDeleting(false);
    }
    setDeleteOpen(false);
  };

  const handleDeleteSensor = async () => {
    if (deleteSensorKey && key) {
      setDeletingSensor(true);
      try {
        // Scoped by the site: a sensor has no tenant of its own, so its parent
        // is the anchor the backend verifies (#1339).
        await api.deleteSiteSensor(key, deleteSensorKey);
        notification.success(t('pages.sensors.deleted'));
        loadSensors();
      } catch (err) {
        handleError(err);
      } finally {
        setDeletingSensor(false);
      }
    }
    setDeleteSensorKey(null);
  };

  if (loading) return <LoadingSkeleton variant="form" />;
  if (error) return <ErrorDisplay error={error} onRetry={() => navigate(-1)} />;

  const PANEL_GAP = 4;

  return (
    <Box data-testid="site-detail-page">
      <UnsavedChangesGuard dirty={isDirty} />
      <PageTitle
        title={current?.name ?? t('entities.site')}
        action={
          <Button color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteOpen(true)}>
            {t('common.delete')}
          </Button>
        }
      />

      <Form onSubmit={handleSubmit(onSubmit)} sx={{ maxWidth: 1280, display: 'flex', flexDirection: 'column', gap: PANEL_GAP }}>
        <Typography variant="body2" color="text.secondary">
          {t('pages.sites.editIntro')}
        </Typography>

        <Card variant="outlined">
          <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
            <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
              {t('pages.sites.sectionBasicData')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('pages.sites.sectionBasicDataDesc')}
            </Typography>
            <FormRow>
              <FormTextField name="name" control={control} label={t('pages.sites.name')} required autoFocus />
              <FormSelectField name="type" control={control} label={t('pages.sites.type')} options={typeOptions} helperText={t('pages.sites.typeHelper')} required />
            </FormRow>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 0.5 }}>
              {t('pages.sites.gpsHelper')}
            </Typography>
            <FormRow>
              <FormNumberField name="gps_lat" control={control} label={t('pages.sites.gpsLat')} min={-90} max={90} />
              <FormNumberField name="gps_lon" control={control} label={t('pages.sites.gpsLon')} min={-180} max={180} />
            </FormRow>
            <GpsDetectButton setValue={setValue} />
            {!weatherEnabledForType && (
              <Alert severity="info" variant="outlined" icon={false} role="status" sx={{ py: 0.5, mb: 2 }} data-testid="site-weather-type-hint">
                <Typography variant="caption">
                  {t('pages.sites.weatherTypeHint', {
                    outdoorLabel: t('enums.siteType.outdoor'),
                    greenhouseLabel: t('enums.siteType.greenhouse'),
                    balconyLabel: t('enums.siteType.balcony'),
                  })}
                </Typography>
              </Alert>
            )}
            {watchedType === 'balcony' && (
              <Alert severity="info" variant="outlined" icon={false} role="status" sx={{ py: 0.5, mb: 2 }} data-testid="site-balcony-weather-hint">
                <Typography variant="caption">
                  {t('pages.sites.balconyWeatherHint')}
                </Typography>
              </Alert>
            )}
            <FormRow>
              <Box>
                <FormClimateZoneField name="climate_zone" control={control} label={t('pages.sites.climateZone')} helperText={t('pages.sites.climateZoneHelper')} />
                {/* Grouped directly under the field it fills in — placing it
                    below the whole FormRow would visually associate it with
                    the unrelated area field instead (UI-NFR-008 field grouping). */}
                {key && (
                  <HardinessZoneDetectButton
                    siteKey={key}
                    gpsPresent={current?.gps_coordinates != null}
                    onResolved={() => dispatch(fetchSite(key))}
                  />
                )}
              </Box>
              <FormNumberField name="total_area_m2" control={control} label={t('pages.sites.totalArea')} helperText={t('pages.sites.totalAreaHelper')} min={0} />
            </FormRow>
            <FormTimezoneField name="timezone" control={control} label={t('pages.sites.timezone')} helperText={t('pages.sites.timezoneHelper')} required />
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <WaterSourceSection
              value={waterConfig}
              onChange={setWaterConfig}
              warnings={current?.water_config_warnings}
            />
          </CardContent>
        </Card>

        <Typography variant="caption" color="text.secondary">* {t('common.required')}</Typography>
        <FormActions onCancel={() => navigate(-1)} loading={saving} />
      </Form>

      {/* Sensors — issue #587: only when smart home is enabled */}
      {isSmartHomeEnabled && (
      <Box sx={{ mt: 4 }} data-testid="site-sensors-section">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SensorsIcon />
            {t('pages.sensors.title')}
          </Typography>
          <Button startIcon={<AddIcon />} onClick={() => { setEditSensor(undefined); setSensorDialogOpen(true); }} data-testid="add-sensor-button">
            {t('pages.sensors.add')}
          </Button>
        </Box>
        {sensors.length === 0 ? (
          <EmptyState
            message={t('pages.sensors.noSensors')}
            actionLabel={t('pages.sensors.add')}
            onAction={() => { setEditSensor(undefined); setSensorDialogOpen(true); }}
          />
        ) : (
          <DataTable<Sensor>
            columns={[
              { id: 'name', label: t('pages.sensors.name'), render: (r) => r.name },
              { id: 'metricType', label: t('pages.sensors.metricType'), render: (r) => r.metric_type },
              { id: 'haEntityId', label: t('pages.sensors.haEntityId'), render: (r) => r.ha_entity_id || '—' },
              { id: 'active', label: t('pages.sensors.active'), render: (r) => (
                <Chip label={r.is_active ? t('common.yes') : t('common.no')} size="small" color={r.is_active ? 'success' : 'default'} />
              )},
              { id: 'actions', label: '', render: (r) => (
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); setEditSensor(r); setSensorDialogOpen(true); }}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDeleteSensorKey(r.key); }}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              )},
            ] satisfies Column<Sensor>[]}
            rows={sensors}
            getRowKey={(r) => r.key}
            tableState={sensorTableState}
            ariaLabel={t('pages.sensors.title')}
            mobileCardRenderer={(r) => (
              <MobileCard
                title={r.name}
                titleId="name"
                subtitle={r.ha_entity_id || undefined}
                subtitleId="haEntityId"
                chips={[
                  {
                    id: 'active',
                    content: (
                      <Chip
                        label={r.is_active ? t('common.yes') : t('common.no')}
                        size="small"
                        color={r.is_active ? 'success' : 'default'}
                      />
                    ),
                  },
                ]}
                fields={[
                  { id: 'metricType', label: t('pages.sensors.metricType'), value: r.metric_type },
                ]}
              />
            )}
          />
        )}
      </Box>
      )}

      {isSmartHomeEnabled && key && (
        <SensorCreateDialog
          open={sensorDialogOpen}
          onClose={() => { setSensorDialogOpen(false); setEditSensor(undefined); }}
          context={{ parentType: 'site', parentKey: key }}
          sensor={editSensor}
          onSaved={() => { setSensorDialogOpen(false); setEditSensor(undefined); loadSensors(); }}
        />
      )}

      <ConfirmDialog
        open={!!deleteSensorKey}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: sensors.find((s) => s.key === deleteSensorKey)?.name })}
        onConfirm={handleDeleteSensor}
        onCancel={() => setDeleteSensorKey(null)}
        destructive
        loading={deletingSensor}
      />

      {key && <LocationTreeSection siteKey={key} />}
      {key && <SiteRunsSection siteKey={key} />}
      {key && current && isWeatherRelevantSiteType(current.type) && (
        current.gps_coordinates != null ? (
          <>
            <WeatherSourceSection siteKey={key} />
            {/* REQ-041 — long-term climate normals (NASA POWER) for the site. */}
            <SiteClimateSection siteKey={key} />
          </>
        ) : (
          <Alert severity="info" role="status" sx={{ mt: 4 }} data-testid="weather-source-gps-hint">
            {t('pages.weatherSource.gpsRequiredHint')}
          </Alert>
        )
      )}

      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: current?.name })}
        onConfirm={onDelete}
        onCancel={() => setDeleteOpen(false)}
        destructive
        loading={deleting}
      />
    </Box>
  );
}

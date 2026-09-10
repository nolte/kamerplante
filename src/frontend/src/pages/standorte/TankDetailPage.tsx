import { useEffect, useState, useCallback } from 'react';
import { useTabUrl } from '@/hooks/useTabUrl';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import Tooltip from '@mui/material/Tooltip';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Alert from '@mui/material/Alert';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import OpacityIcon from '@mui/icons-material/Opacity';
import PlaceIcon from '@mui/icons-material/Place';
import BuildIcon from '@mui/icons-material/Build';
import IconButton from '@mui/material/IconButton';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import MobileCard from '@/components/common/MobileCard';
import EmptyState from '@/components/common/EmptyState';
import PageTitle from '@/components/layout/PageTitle';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ErrorDisplay from '@/components/common/ErrorDisplay';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import DataTable, { type Column } from '@/components/common/DataTable';
import { useTableLocalState } from '@/hooks/useTableState';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormNumberField from '@/components/form/FormNumberField';
import FormSwitchField from '@/components/form/FormSwitchField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import LocationTreeSelect from '@/components/form/LocationTreeSelect';
import HaPublishToggle from '@/components/ha/HaPublishToggle';
import UnsavedChangesGuard from '@/components/form/UnsavedChangesGuard';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import { useSmartHomeEnabled } from '@/hooks/useSmartHomeEnabled';
import { useAppDispatch } from '@/store/hooks';
import { setBreadcrumbs } from '@/store/slices/uiSlice';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import MuiLink from '@mui/material/Link';
import * as tankApi from '@/api/endpoints/tanks';
import * as sitesApi from '@/api/endpoints/sites';
import * as observationsApi from '@/api/endpoints/observations';
import SensorHistoryChart from '@/components/sensors/SensorHistoryChart';
import TankStateChart from '@/components/tanks/TankStateChart';
import type {
  Tank,
  TankState,
  TankAlert,
  TankFillEvent,
  MaintenanceLog,
  MaintenanceSchedule,
  DueMaintenance,
  Site,
  Sensor,
} from '@/api/types';
import TankStateCreateDialog from './TankStateCreateDialog';
import MaintenanceLogDialog from './MaintenanceLogDialog';
import MaintenanceScheduleDialog from './MaintenanceScheduleDialog';
import TankFillCreateDialog from './TankFillCreateDialog';
import SensorCreateDialog from './SensorCreateDialog';

/** Form container max width on md+ (UI-NFR-008 R-053). */
const FORM_MAX_WIDTH = 1280;
/** Reading-column max width for prose textareas (UI-NFR-008 R-054, ~70-80 chars). */
const READING_COL_MAX = 760;

const tankTypes = ['nutrient', 'irrigation', 'reservoir', 'recirculation', 'stock_solution'] as const;
const materials = ['plastic', 'stainless_steel', 'glass', 'ibc'] as const;

const editSchema = z.object({
  name: z.string().min(1).max(200),
  tank_type: z.enum(tankTypes),
  volume_liters: z.number().gt(0),
  material: z.enum(materials),
  location_key: z.string().nullable(),
  has_lid: z.boolean(),
  has_air_pump: z.boolean(),
  has_circulation_pump: z.boolean(),
  has_heater: z.boolean(),
  is_light_proof: z.boolean(),
  has_uv_sterilizer: z.boolean(),
  has_ozone_generator: z.boolean(),
  notes: z.string().nullable(),
});

type EditFormData = z.infer<typeof editSchema>;

const severityColor: Record<string, 'error' | 'warning' | 'info'> = {
  critical: 'error',
  high: 'error',
  medium: 'warning',
  low: 'info',
};

const sourceChipColor: Record<string, 'default' | 'primary' | 'success' | 'secondary'> = {
  manual: 'default',
  ha_auto: 'primary',
  ha_live: 'success',
  mqtt_auto: 'secondary',
};

function getFreshness(recordedAt: string | null): { color: 'success' | 'warning' | 'error'; key: string; minutes?: number } {
  if (!recordedAt) return { color: 'error', key: 'freshOffline' };
  const diffMs = Date.now() - new Date(recordedAt).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 5) return { color: 'success', key: 'freshLive' };
  if (minutes <= 60) return { color: 'warning', key: 'freshRecent', minutes };
  return { color: 'error', key: 'freshStale' };
}

function getPhStatus(ph: number | null): 'success' | 'warning' | 'error' | 'default' {
  if (ph == null) return 'default';
  if (ph >= 5.5 && ph <= 6.5) return 'success';
  if ((ph >= 5.0 && ph < 5.5) || (ph > 6.5 && ph <= 7.0)) return 'warning';
  return 'error';
}

function getEcStatus(ec: number | null): 'success' | 'warning' | 'error' | 'default' {
  if (ec == null) return 'default';
  if (ec >= 0.5 && ec <= 3.0) return 'success';
  if ((ec > 0 && ec < 0.5) || (ec > 3.0 && ec <= 4.0)) return 'warning';
  return 'error';
}

function getTempStatus(temp: number | null): 'success' | 'warning' | 'error' | 'default' {
  if (temp == null) return 'default';
  if (temp >= 18 && temp <= 22) return 'success';
  if ((temp >= 15 && temp < 18) || (temp > 22 && temp <= 26)) return 'warning';
  return 'error';
}

function getDoStatus(doVal: number | null): 'success' | 'warning' | 'error' | 'default' {
  if (doVal == null) return 'default';
  if (doVal >= 5 && doVal <= 8) return 'success';
  if ((doVal >= 3 && doVal < 5) || (doVal > 8 && doVal <= 10)) return 'warning';
  return 'error';
}

const statusBorderColor: Record<string, string> = {
  success: 'success.main',
  warning: 'warning.main',
  error: 'error.main',
  default: 'divider',
};

export default function TankDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const notification = useNotification();
  const { handleError } = useApiError();
  // Issue #587: tank sensor surfaces (HA/MQTT sensors, history charts) are gated
  // behind the smart-home toggle; the tank itself stays visible.
  const { isSmartHomeEnabled } = useSmartHomeEnabled();

  const [tank, setTank] = useState<Tank | null>(null);
  const [latestState, setLatestState] = useState<TankState | null>(null);
  const [alerts, setAlerts] = useState<TankAlert[]>([]);
  const [states, setStates] = useState<TankState[]>([]);
  const [maintenanceLogs, setMaintenanceLogs] = useState<MaintenanceLog[]>([]);
  const [dueMaintenances, setDueMaintenances] = useState<DueMaintenance[]>([]);
  const [schedules, setSchedules] = useState<MaintenanceSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useTabUrl(['details', 'states', 'maintenance', 'schedules', 'fills', 'edit']);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingSchedule, setDeletingSchedule] = useState(false);
  const [deletingSensor, setDeletingSensor] = useState(false);
  const [stateDialogOpen, setStateDialogOpen] = useState(false);
  const [maintenanceDialogOpen, setMaintenanceDialogOpen] = useState(false);
  const [fillDialogOpen, setFillDialogOpen] = useState(false);
  const [fillEvents, setFillEvents] = useState<TankFillEvent[]>([]);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [editSchedule, setEditSchedule] = useState<MaintenanceSchedule | undefined>(undefined);
  const [deleteScheduleKey, setDeleteScheduleKey] = useState<string | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteKey, setSelectedSiteKey] = useState('');
  const [siteName, setSiteName] = useState('');
  const [locationName, setLocationName] = useState('');
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [sensorDialogOpen, setSensorDialogOpen] = useState(false);
  const [editSensor, setEditSensor] = useState<Sensor | undefined>(undefined);
  const [deleteSensorKey, setDeleteSensorKey] = useState<string | null>(null);
  const [tsAvailable, setTsAvailable] = useState(false);

  const statesTableState = useTableLocalState({ defaultSort: { column: 'recordedAt', direction: 'desc' } });
  const dueTableState = useTableLocalState({ defaultSort: { column: 'nextDue', direction: 'asc' } });
  const logsTableState = useTableLocalState({ defaultSort: { column: 'performedAt', direction: 'desc' } });
  const fillsTableState = useTableLocalState({ defaultSort: { column: 'filledAt', direction: 'desc' } });
  const schedulesTableState = useTableLocalState({ defaultSort: { column: 'type', direction: 'asc' } });

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { isDirty },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      name: '',
      tank_type: 'nutrient',
      volume_liters: 50,
      material: 'plastic',
      location_key: null,
      has_lid: false,
      has_air_pump: false,
      has_circulation_pump: false,
      has_heater: false,
      is_light_proof: false,
      has_uv_sterilizer: false,
      has_ozone_generator: false,
      notes: null,
    },
  });

  const load = useCallback(async () => {
    if (!key) return;
    setLoading(true);
    try {
      const [tankData, allSites] = await Promise.all([
        tankApi.getTank(key),
        sitesApi.listSites(0, 200),
      ]);
      setTank(tankData);
      setSites(allSites);
      reset({
        name: tankData.name,
        tank_type: tankData.tank_type,
        volume_liters: tankData.volume_liters,
        material: tankData.material,
        location_key: tankData.location_key,
        has_lid: tankData.has_lid,
        has_air_pump: tankData.has_air_pump,
        has_circulation_pump: tankData.has_circulation_pump,
        has_heater: tankData.has_heater,
        is_light_proof: tankData.is_light_proof,
        has_uv_sterilizer: tankData.has_uv_sterilizer,
        has_ozone_generator: tankData.has_ozone_generator,
        notes: tankData.notes,
      });

      // Resolve location/site names for display and pre-select edit cascade
      if (tankData.location_key) {
        try {
          const loc = await sitesApi.getLocation(tankData.location_key);
          setLocationName(loc.path || loc.name);
          const site = allSites.find((s) => s.key === loc.site_key);
          setSiteName(site?.name ?? '');
          setSelectedSiteKey(loc.site_key);
        } catch {
          setLocationName('');
          setSiteName('');
          setSelectedSiteKey('');
        }
      } else {
        setLocationName('');
        setSiteName('');
        setSelectedSiteKey('');
      }

      const [ls, al, st, ml, dm, sc, fe, sn] = await Promise.all([
        tankApi.getLatestState(key),
        tankApi.getAlerts(key),
        tankApi.getStates(key),
        tankApi.getMaintenanceHistory(key),
        tankApi.getDueMaintenances(key),
        tankApi.getSchedules(key),
        tankApi.getFillEvents(key),
        tankApi.getSensors(key),
      ]);
      setLatestState(ls);
      setAlerts(al);
      setStates(st);
      setMaintenanceLogs(ml);
      setDueMaintenances(dm);
      setSchedules(sc);
      setFillEvents(fe);
      setSensors(sn);
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [key, reset]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    observationsApi.getTimeseriesStatus()
      .then((s) => setTsAvailable(s.available))
      .catch(() => setTsAvailable(false));
  }, []);

  // Dynamic breadcrumbs
  useEffect(() => {
    if (!tank) return;
    dispatch(setBreadcrumbs([
      { label: 'nav.dashboard', path: '/dashboard' },
      { label: 'nav.tanks', path: '/standorte/tanks' },
      { label: tank.name },
    ]));
  }, [tank, dispatch]);

  // Clear dynamic breadcrumbs on unmount
  useEffect(() => () => { dispatch(setBreadcrumbs([])); }, [dispatch]);

  const onSave = async (data: EditFormData) => {
    if (!key) return;
    try {
      setSaving(true);
      await tankApi.updateTank(key, { ...data, location_key: data.location_key || null });
      notification.success(t('common.saved'));
      load();
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
      await tankApi.deleteTank(key);
      notification.success(t('pages.tanks.deleted'));
      navigate('/standorte/tanks');
    } catch (err) {
      handleError(err);
    } finally {
      setDeleting(false);
    }
  };

  const onDeleteSchedule = async () => {
    if (!key || !deleteScheduleKey) return;
    setDeletingSchedule(true);
    try {
      await tankApi.deleteSchedule(key, deleteScheduleKey);
      notification.success(t('pages.tanks.scheduleDeleted'));
      setDeleteScheduleKey(null);
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setDeletingSchedule(false);
    }
  };

  const handleSiteChange = (siteKey: string) => {
    setSelectedSiteKey(siteKey);
    setValue('location_key', null, { shouldDirty: true });
  };


  const onDeleteSensor = async () => {
    if (!deleteSensorKey || !key) return;
    setDeletingSensor(true);
    try {
      // Scoped by the tank: a sensor has no tenant of its own, so its parent is
      // the anchor the backend verifies (#1339).
      await tankApi.deleteSensor(key, deleteSensorKey);
      notification.success(t('pages.tanks.sensorDeleted'));
      setDeleteSensorKey(null);
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setDeletingSensor(false);
    }
  };

  // Column definitions for data tables
  const stateColumns: Column<TankState>[] = [
    { id: 'recordedAt', label: t('pages.tanks.recordedAt'), render: (r) => r.recorded_at ? new Date(r.recorded_at).toLocaleString() : '—' },
    { id: 'ph', label: 'pH', render: (r) => r.ph ?? '—', align: 'right' },
    { id: 'ec', label: 'EC (mS/cm)', render: (r) => r.ec_ms ?? '—', align: 'right' },
    { id: 'temp', label: t('pages.tanks.waterTemp'), render: (r) => r.water_temp_celsius != null ? `${r.water_temp_celsius} °C` : '—', align: 'right' },
    { id: 'fillLevel', label: t('pages.tanks.fillLevel'), render: (r) => r.fill_level_percent != null ? `${r.fill_level_percent}%` : '—', align: 'right' },
    { id: 'tds', label: 'TDS (ppm)', render: (r) => r.tds_ppm ?? '—', align: 'right' },
  ];

  const dueColumns: Column<DueMaintenance>[] = [
    { id: 'type', label: t('pages.tanks.maintenanceType'), render: (r) => t(`enums.maintenanceType.${r.maintenance_type}`), searchValue: (r) => t(`enums.maintenanceType.${r.maintenance_type}`) },
    { id: 'nextDue', label: t('pages.tanks.nextDue'), render: (r) => new Date(r.next_due).toLocaleDateString() },
    {
      id: 'status', label: t('pages.tanks.status'), render: (r) => (
        <Chip label={t(`enums.maintenanceStatus.${r.status}`)} size="small" color={r.status === 'overdue' ? 'error' : r.status === 'due_soon' ? 'warning' : 'success'} />
      ), searchValue: (r) => t(`enums.maintenanceStatus.${r.status}`),
    },
    { id: 'priority', label: t('pages.tanks.priority'), render: (r) => t(`enums.maintenancePriority.${r.priority}`), searchValue: (r) => t(`enums.maintenancePriority.${r.priority}`) },
  ];

  const logColumns: Column<MaintenanceLog>[] = [
    { id: 'type', label: t('pages.tanks.maintenanceType'), render: (r) => t(`enums.maintenanceType.${r.maintenance_type}`), searchValue: (r) => t(`enums.maintenanceType.${r.maintenance_type}`) },
    { id: 'performedAt', label: t('pages.tanks.performedAt'), render: (r) => r.performed_at ? new Date(r.performed_at).toLocaleString() : '—' },
    { id: 'performedBy', label: t('pages.tanks.performedBy'), render: (r) => r.performed_by || '—' },
    { id: 'duration', label: t('pages.tanks.duration'), render: (r) => r.duration_minutes != null ? `${r.duration_minutes} min` : '—', align: 'right' },
    { id: 'notes', label: t('pages.tanks.notes'), render: (r) => r.notes || '—' },
  ];

  const sensorColumns: Column<Sensor>[] = [
    { id: 'name', label: t('pages.tanks.sensorColumnName'), render: (r) => r.name },
    { id: 'metric_type', label: t('pages.tanks.sensorColumnMetric'), render: (r) => r.metric_type },
    { id: 'ha_entity_id', label: t('pages.tanks.sensorColumnEntity'), render: (r) => r.ha_entity_id || '—', hideBelowBreakpoint: 'md' },
    {
      id: 'actions', label: '', sortable: false, searchable: false, render: (r: Sensor) => (
        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
          <IconButton
            size="small"
            onClick={(e) => { e.stopPropagation(); setEditSensor(r); setSensorDialogOpen(true); }}
            aria-label={t('common.edit')}
            data-testid={`sensor-edit-${r.key}`}
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            onClick={(e) => { e.stopPropagation(); setDeleteSensorKey(r.key); }}
            aria-label={t('common.delete')}
            data-testid={`sensor-delete-${r.key}`}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ), align: 'right',
    },
  ];

  const scheduleColumns: Column<MaintenanceSchedule>[] = [
    { id: 'type', label: t('pages.tanks.maintenanceType'), render: (r) => t(`enums.maintenanceType.${r.maintenance_type}`), searchValue: (r) => t(`enums.maintenanceType.${r.maintenance_type}`) },
    { id: 'intervalDays', label: t('pages.tanks.intervalDays'), render: (r) => r.interval_days, align: 'right' },
    { id: 'reminderDays', label: t('pages.tanks.reminderDays'), render: (r) => r.reminder_days_before, align: 'right' },
    { id: 'priority', label: t('pages.tanks.priority'), render: (r) => t(`enums.maintenancePriority.${r.priority}`), searchValue: (r) => t(`enums.maintenancePriority.${r.priority}`) },
    {
      id: 'active', label: t('pages.tanks.active'), render: (r) => (
        <Chip label={r.is_active ? t('common.yes') : t('common.no')} size="small" color={r.is_active ? 'success' : 'default'} />
      ), searchValue: (r) => r.is_active ? t('common.yes') : t('common.no'),
    },
    {
      id: 'actions', label: '', render: (r: MaintenanceSchedule) => (
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <IconButton
            size="small"
            onClick={(e) => { e.stopPropagation(); setEditSchedule(r); setScheduleDialogOpen(true); }}
            aria-label={t('pages.tanks.editSchedule')}
            data-testid={`schedule-edit-${r.key}`}
          >
            <EditIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            onClick={(e) => { e.stopPropagation(); setDeleteScheduleKey(r.key); }}
            aria-label={t('common.delete')}
            data-testid={`schedule-delete-${r.key}`}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ),
    },
  ];

  if (loading) return <LoadingSkeleton variant="form" />;
  if (error) return <ErrorDisplay error={error} />;
  if (!tank) return <ErrorDisplay error={t('errors.notFound')} />;

  const overdueDueCount = dueMaintenances.filter((d) => d.status === 'overdue' || d.status === 'due_soon').length;

  return (
    <Box data-testid="tank-detail-page">
      <UnsavedChangesGuard dirty={isDirty} />

      {/* Header: title + delete */}
      <PageTitle
        title={tank.name}
        action={
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => setDeleteOpen(true)}
            data-testid="tank-delete-button"
            size="small"
          >
            {t('common.delete')}
          </Button>
        }
      />

      {/* Quick-info chips under the title */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        <Chip
          icon={<OpacityIcon sx={{ fontSize: 16 }} />}
          label={`${t('pages.tanks.quickInfoType')}: ${t(`enums.tankType.${tank.tank_type}`)}`}
          size="small"
          variant="outlined"
          color="default"
        />
        <Chip
          label={`${tank.volume_liters} L`}
          size="small"
          variant="outlined"
          color="default"
        />
        {siteName && selectedSiteKey && (
          <Chip
            icon={<PlaceIcon sx={{ fontSize: 16 }} />}
            label={locationName ? `${siteName} / ${locationName}` : siteName}
            size="small"
            variant="outlined"
            color="default"
            component={RouterLink}
            to={`/standorte/sites/${selectedSiteKey}`}
            clickable
          />
        )}
        {overdueDueCount > 0 && (
          <Chip
            icon={<BuildIcon sx={{ fontSize: 16 }} />}
            label={t('pages.tanks.quickInfoDueMaint', { count: overdueDueCount })}
            size="small"
            color="warning"
            onClick={() => setTab(2)}
            sx={{ cursor: 'pointer' }}
          />
        )}
      </Box>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2 }}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        aria-label={t('pages.tanks.tabsAriaLabel')}
      >
        <Tab label={t('pages.tanks.tabDetails')} />
        <Tab label={t('pages.tanks.tabStates')} />
        <Tab label={t('pages.tanks.tabMaintenance')} />
        <Tab label={t('pages.tanks.tabSchedules')} />
        <Tab label={t('pages.tanks.tabFills')} />
        <Tab label={t('pages.tanks.tabEdit')} />
      </Tabs>

      {/* Tab 0: Details */}
      {tab === 0 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.tanks.detailsIntro')}
          </Typography>

          {alerts.length > 0 && (
            <Box sx={{ mb: 2 }}>
              {alerts.map((a, i) => (
                <Alert
                  key={i}
                  severity={severityColor[a.severity] ?? 'info'}
                  sx={{ mb: 1 }}
                >
                  {a.type === 'algae_risk' && a.factors ? (
                    <>
                      {t('tankAlerts.algae_risk_title')}
                      <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
                        <li>{t('tankAlerts.algae_factor_not_light_proof')}</li>
                        {a.factors.includes('no_lid') && (
                          <li>{t('tankAlerts.algae_factor_no_lid')}</li>
                        )}
                        {a.factors.includes('warm_water') && (
                          <li>{t('tankAlerts.algae_factor_warm_water', { temp: a.temp })}</li>
                        )}
                        {a.factors.includes('nutrient_rich') && (
                          <li>{t('tankAlerts.algae_factor_nutrient_rich')}</li>
                        )}
                      </ul>
                    </>
                  ) : (
                    t(`tankAlerts.${a.type}`, { value: a.value, limit: a.limit, limit_min: a.limit_min, limit_max: a.limit_max, defaultValue: a.message })
                  )}
                </Alert>
              ))}
            </Box>
          )}

          {/* Tank Properties Grid */}
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {t('pages.tanks.properties')}
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">{t('pages.tanks.tankType')}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{t(`enums.tankType.${tank.tank_type}`)}</Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">{t('pages.tanks.volumeLiters')}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{tank.volume_liters} L</Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">{t('pages.tanks.material')}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{t(`enums.tankMaterial.${tank.material}`)}</Typography>
                </Grid>
                <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">{t('pages.tanks.site')} / {t('pages.tanks.location')}</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {selectedSiteKey ? (
                      <>
                        <MuiLink component={RouterLink} to={`/standorte/sites/${selectedSiteKey}`} underline="hover">
                          {siteName}
                        </MuiLink>
                        {locationName && (
                          <>
                            {' / '}
                            <MuiLink component={RouterLink} to={`/standorte/locations/${tank.location_key}`} underline="hover">
                              {locationName}
                            </MuiLink>
                          </>
                        )}
                      </>
                    ) : '—'}
                  </Typography>
                </Grid>
              </Grid>
              {(() => {
                const equipChips = [
                  tank.has_lid && <Chip key="lid" label={t('pages.tanks.hasLid')} size="small" />,
                  tank.has_air_pump && <Chip key="air" label={t('pages.tanks.hasAirPump')} size="small" />,
                  tank.has_circulation_pump && <Chip key="circ" label={t('pages.tanks.hasCirculationPump')} size="small" />,
                  tank.has_heater && <Chip key="heat" label={t('pages.tanks.hasHeater')} size="small" />,
                  tank.is_light_proof && <Chip key="light" label={t('pages.tanks.isLightProof')} size="small" />,
                  tank.has_uv_sterilizer && <Chip key="uv" label={t('pages.tanks.hasUvSterilizer')} size="small" />,
                  tank.has_ozone_generator && <Chip key="ozone" label={t('pages.tanks.hasOzoneGenerator')} size="small" />,
                ].filter(Boolean);
                return equipChips.length > 0 ? (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                      {t('pages.tanks.equipment')}
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {equipChips}
                    </Box>
                  </Box>
                ) : null;
              })()}
              {tank.notes && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                    {t('pages.tanks.notes')}
                  </Typography>
                  <Typography variant="body2">{tank.notes}</Typography>
                </Box>
              )}
            </CardContent>
          </Card>

          {key && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <HaPublishToggle entityType="tank" entityKey={key} />
              </CardContent>
            </Card>
          )}

          {/* Current State — color-coded value cards */}
          {latestState && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                  <Typography variant="h6">{t('pages.tanks.latestState')}</Typography>
                  <Chip
                    label={t(`pages.tanks.source${latestState.source === 'manual' ? 'Manual' : latestState.source === 'ha_auto' ? 'HaAuto' : latestState.source === 'ha_live' ? 'HaLive' : latestState.source === 'mqtt_auto' ? 'MqttAuto' : 'Manual'}`)}
                    size="small"
                    color={sourceChipColor[latestState.source] ?? 'default'}
                  />
                  {latestState.recorded_at && (() => {
                    const freshness = getFreshness(latestState.recorded_at);
                    return (
                      <Chip
                        label={freshness.minutes != null
                          ? t(`pages.tanks.${freshness.key}`, { minutes: freshness.minutes })
                          : t(`pages.tanks.${freshness.key}`)}
                        size="small"
                        color={freshness.color}
                        variant="outlined"
                      />
                    );
                  })()}
                  {latestState.recorded_at && (
                    <Typography variant="caption" color="text.secondary">
                      {new Date(latestState.recorded_at).toLocaleString()}
                    </Typography>
                  )}
                </Box>
                <Grid container spacing={1.5}>
                  {latestState.ph != null && (() => {
                    const status = getPhStatus(latestState.ph);
                    return (
                      <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: '2px solid',
                            borderColor: statusBorderColor[status],
                            borderRadius: 1,
                            bgcolor: 'background.paper',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">pH</Typography>
                            <Tooltip title={t('pages.tanks.phTooltip')} arrow>
                              <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} tabIndex={0} />
                            </Tooltip>
                          </Box>
                          <Typography variant="h5" color={`${status}.main`} sx={{ fontWeight: 700 }}>
                            {latestState.ph}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">5.5–6.5</Typography>
                        </Box>
                      </Grid>
                    );
                  })()}
                  {latestState.ec_ms != null && (() => {
                    const status = getEcStatus(latestState.ec_ms);
                    return (
                      <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: '2px solid',
                            borderColor: statusBorderColor[status],
                            borderRadius: 1,
                            bgcolor: 'background.paper',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">EC</Typography>
                            <Tooltip title={t('pages.tanks.ecTooltip')} arrow>
                              <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} tabIndex={0} />
                            </Tooltip>
                          </Box>
                          <Typography variant="h5" color={`${status}.main`} sx={{ fontWeight: 700 }}>
                            {latestState.ec_ms}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">mS/cm</Typography>
                        </Box>
                      </Grid>
                    );
                  })()}
                  {latestState.water_temp_celsius != null && (() => {
                    const status = getTempStatus(latestState.water_temp_celsius);
                    return (
                      <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: '2px solid',
                            borderColor: statusBorderColor[status],
                            borderRadius: 1,
                            bgcolor: 'background.paper',
                          }}
                        >
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                            {t('pages.tanks.waterTempShort')}
                          </Typography>
                          <Typography variant="h5" color={`${status}.main`} sx={{ fontWeight: 700 }}>
                            {latestState.water_temp_celsius}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">°C &nbsp;(18–22)</Typography>
                        </Box>
                      </Grid>
                    );
                  })()}
                  {latestState.fill_level_percent != null && (
                    <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                      <Box
                        sx={{
                          p: 1.5,
                          border: '2px solid',
                          borderColor: 'divider',
                          borderRadius: 1,
                          bgcolor: 'background.paper',
                        }}
                      >
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                          {t('pages.tanks.fillLevel')}
                        </Typography>
                        <Typography variant="h5" sx={{ fontWeight: 700 }}>
                          {latestState.fill_level_percent}%
                        </Typography>
                        {latestState.fill_level_liters != null && (
                          <Typography variant="caption" color="text.secondary">{latestState.fill_level_liters} L</Typography>
                        )}
                      </Box>
                    </Grid>
                  )}
                  {latestState.dissolved_oxygen_mgl != null && (() => {
                    const status = getDoStatus(latestState.dissolved_oxygen_mgl);
                    return (
                      <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                        <Box
                          sx={{
                            p: 1.5,
                            border: '2px solid',
                            borderColor: statusBorderColor[status],
                            borderRadius: 1,
                            bgcolor: 'background.paper',
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">{t('pages.tanks.dissolvedOxygenShort')}</Typography>
                            <Tooltip title={t('pages.tanks.dissolvedOxygenTooltip')} arrow>
                              <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} tabIndex={0} />
                            </Tooltip>
                          </Box>
                          <Typography variant="h5" color={`${status}.main`} sx={{ fontWeight: 700 }}>
                            {latestState.dissolved_oxygen_mgl}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">mg/L &nbsp;(5–8)</Typography>
                        </Box>
                      </Grid>
                    );
                  })()}
                  {latestState.orp_mv != null && (
                    <Grid size={{ xs: 6, sm: 4, md: 3 }}>
                      <Box
                        sx={{
                          p: 1.5,
                          border: '2px solid',
                          borderColor: 'divider',
                          borderRadius: 1,
                          bgcolor: 'background.paper',
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">ORP</Typography>
                          <Tooltip title={t('pages.tanks.orpTooltip')} arrow>
                            <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.secondary', cursor: 'help' }} tabIndex={0} />
                          </Tooltip>
                        </Box>
                        <Typography variant="h5" sx={{ fontWeight: 700 }}>
                          {latestState.orp_mv}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">mV &nbsp;(300–500)</Typography>
                      </Box>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          )}

          {/* Sensor History Charts — only when smart home is enabled (issue #587)
              and sensors are configured */}
          {isSmartHomeEnabled && tsAvailable && sensors.filter((s) => s.ha_entity_id && s.is_active).length > 0 && (
            <Card variant="outlined" sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {t('pages.tanks.sensorHistory')}
                </Typography>
                {sensors
                  .filter((s) => s.ha_entity_id && s.is_active)
                  .map((s) => (
                    <SensorHistoryChart
                      key={s.key}
                      sensorKey={s.key}
                      sensorName={s.name}
                      metricType={s.metric_type}
                      unit={s.unit_of_measurement}
                    />
                  ))}
              </CardContent>
            </Card>
          )}

        </Box>
      )}

      {/* Tab 1: States */}
      {tab === 1 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.tanks.statesIntro')}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="contained"
              onClick={() => setStateDialogOpen(true)}
              data-testid="tank-record-state-button"
            >
              {t('pages.tanks.recordState')}
            </Button>
          </Box>
          {states.length >= 2 && <TankStateChart states={states} />}
          {states.length === 0 ? (
            <EmptyState
              message={t('pages.tanks.noMeasurements')}
              description={t('pages.tanks.noMeasurementsDesc')}
              actionLabel={t('pages.tanks.recordState')}
              onAction={() => setStateDialogOpen(true)}
            />
          ) : (
            <DataTable
              columns={stateColumns}
              rows={states}
              getRowKey={(r) => r.key}
              tableState={statesTableState}
              variant="simple"
              ariaLabel={t('pages.tanks.tabStates')}
              mobileCardRenderer={(r) => (
                <MobileCard
                  title={r.recorded_at ? new Date(r.recorded_at).toLocaleString() : '—'}
                  titleId="recordedAt"
                  fields={[
                    ...(r.ph != null ? [{ id: 'ph', label: t('enums.sensorMetricType.ph'), value: String(r.ph) }] : []),
                    ...(r.ec_ms != null ? [{ id: 'ec', label: t('enums.sensorMetricType.ec_ms'), value: String(r.ec_ms) }] : []),
                    ...(r.water_temp_celsius != null ? [{ id: 'temp', label: t('pages.tanks.waterTemp'), value: `${r.water_temp_celsius} °C` }] : []),
                    ...(r.fill_level_percent != null ? [{ id: 'fillLevel', label: t('pages.tanks.fillLevel'), value: `${r.fill_level_percent}%` }] : []),
                  ]}
                />
              )}
            />
          )}
        </Box>
      )}

      {/* Tab 2: Maintenance */}
      {tab === 2 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.tanks.maintenanceIntro')}
          </Typography>
          {dueMaintenances.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {t('pages.tanks.dueMaintenances')}
                </Typography>
                <DataTable
                  columns={dueColumns}
                  rows={dueMaintenances}
                  getRowKey={(r) => r.schedule_key ?? r.maintenance_type}
                  tableState={dueTableState}
                  variant="simple"
                  ariaLabel={t('pages.tanks.dueMaintenances')}
                  mobileCardRenderer={(r) => (
                    <MobileCard
                      title={t(`enums.maintenanceType.${r.maintenance_type}`)}
                      titleId="type"
                      subtitle={new Date(r.next_due).toLocaleDateString()}
                      subtitleId="nextDue"
                      chips={[
                        {
                          id: 'status',
                          content: (
                            <Chip
                              label={t(`enums.maintenanceStatus.${r.status}`)}
                              size="small"
                              color={r.status === 'overdue' ? 'error' : r.status === 'due_soon' ? 'warning' : 'success'}
                            />
                          ),
                        },
                      ]}
                      fields={[
                        { id: 'priority', label: t('pages.tanks.priority'), value: t(`enums.maintenancePriority.${r.priority}`) },
                      ]}
                    />
                  )}
                />
              </CardContent>
            </Card>
          )}
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="contained"
              onClick={() => setMaintenanceDialogOpen(true)}
              data-testid="tank-log-maintenance-button"
            >
              {t('pages.tanks.logMaintenance')}
            </Button>
          </Box>
          <Typography variant="h6" gutterBottom>
            {t('pages.tanks.maintenanceHistory')}
          </Typography>
          {maintenanceLogs.length === 0 ? (
            <EmptyState
              message={t('pages.tanks.noMaintenanceLogs')}
              description={t('pages.tanks.noMaintenanceLogsDesc')}
              actionLabel={t('pages.tanks.logMaintenance')}
              onAction={() => setMaintenanceDialogOpen(true)}
            />
          ) : (
            <DataTable
              columns={logColumns}
              rows={maintenanceLogs}
              getRowKey={(r) => r.key}
              tableState={logsTableState}
              variant="simple"
              ariaLabel={t('pages.tanks.maintenanceHistory')}
              mobileCardRenderer={(r) => (
                <MobileCard
                  title={t(`enums.maintenanceType.${r.maintenance_type}`)}
                  titleId="type"
                  subtitle={r.performed_at ? new Date(r.performed_at).toLocaleString() : undefined}
                  subtitleId="performedAt"
                  fields={[
                    ...(r.performed_by ? [{ id: 'performedBy', label: t('pages.tanks.performedBy'), value: r.performed_by }] : []),
                    ...(r.duration_minutes != null ? [{ id: 'duration', label: t('pages.tanks.duration'), value: `${r.duration_minutes} min` }] : []),
                  ]}
                />
              )}
            />
          )}
        </Box>
      )}

      {/* Tab 3: Schedules */}
      {tab === 3 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.tanks.schedulesIntro')}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="contained"
              onClick={() => { setEditSchedule(undefined); setScheduleDialogOpen(true); }}
              data-testid="tank-create-schedule-button"
            >
              {t('pages.tanks.createSchedule')}
            </Button>
          </Box>
          {schedules.length === 0 ? (
            <EmptyState
              message={t('pages.tanks.noSchedules')}
              description={t('pages.tanks.noSchedulesDesc')}
              actionLabel={t('pages.tanks.createSchedule')}
              onAction={() => { setEditSchedule(undefined); setScheduleDialogOpen(true); }}
            />
          ) : (
            <DataTable
              columns={scheduleColumns}
              rows={schedules}
              getRowKey={(r) => r.key}
              tableState={schedulesTableState}
              variant="simple"
              ariaLabel={t('pages.tanks.tabSchedules')}
              mobileCardRenderer={(r) => (
                <MobileCard
                  title={t(`enums.maintenanceType.${r.maintenance_type}`)}
                  titleId="type"
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
                    { id: 'intervalDays', label: t('pages.tanks.intervalDays'), value: String(r.interval_days) },
                    { id: 'priority', label: t('pages.tanks.priority'), value: t(`enums.maintenancePriority.${r.priority}`) },
                  ]}
                />
              )}
            />
          )}
        </Box>
      )}

      {/* Tab 4: Fills */}
      {tab === 4 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.tanks.fillsIntro')}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="contained"
              onClick={() => setFillDialogOpen(true)}
              data-testid="tank-record-fill-button"
            >
              {t('pages.tanks.recordFill')}
            </Button>
          </Box>
          {fillEvents.length === 0 ? (
            <EmptyState
              message={t('pages.tanks.noFills')}
              description={t('pages.tanks.noFillsDesc')}
              actionLabel={t('pages.tanks.recordFill')}
              onAction={() => setFillDialogOpen(true)}
            />
          ) : (
            <DataTable
              columns={[
                { id: 'filledAt', label: t('pages.tanks.filledAt'), render: (r: TankFillEvent) => r.filled_at ? new Date(r.filled_at).toLocaleString() : '—' },
                { id: 'fillType', label: t('pages.tanks.fillType'), render: (r: TankFillEvent) => t(`enums.fillType.${r.fill_type}`), searchValue: (r: TankFillEvent) => t(`enums.fillType.${r.fill_type}`) },
                { id: 'volume', label: t('pages.tanks.volumeLiters'), render: (r: TankFillEvent) => `${r.volume_liters} L`, align: 'right' as const },
                { id: 'ec', label: 'EC (mS/cm)', render: (r: TankFillEvent) => r.measured_ec_ms != null ? `${r.measured_ec_ms}` : '—', align: 'right' as const },
                { id: 'ph', label: 'pH', render: (r: TankFillEvent) => r.measured_ph ?? '—', align: 'right' as const },
                { id: 'waterSource', label: t('pages.tanks.waterSource'), render: (r: TankFillEvent) => r.water_source ? t(`enums.waterSource.${r.water_source}`) : '—' },
              ]}
              rows={fillEvents}
              getRowKey={(r: TankFillEvent) => r.key}
              tableState={fillsTableState}
              variant="simple"
              ariaLabel={t('pages.tanks.tabFills')}
              mobileCardRenderer={(r: TankFillEvent) => (
                <MobileCard
                  title={r.filled_at ? new Date(r.filled_at).toLocaleString() : '—'}
                  titleId="filledAt"
                  chips={[
                    { id: 'fillType', content: <Chip label={t(`enums.fillType.${r.fill_type}`)} size="small" /> },
                  ]}
                  fields={[
                    { id: 'volume', label: t('pages.tanks.volumeLiters'), value: `${r.volume_liters} L` },
                    ...(r.measured_ec_ms != null ? [{ id: 'ec', label: 'EC (mS/cm)', value: String(r.measured_ec_ms) }] : []),
                    ...(r.measured_ph != null ? [{ id: 'ph', label: 'pH', value: String(r.measured_ph) }] : []),
                    ...(r.water_source ? [{ id: 'waterSource', label: t('pages.tanks.waterSource'), value: t(`enums.waterSource.${r.water_source}`) }] : []),
                  ]}
                />
              )}
            />
          )}
        </Box>
      )}

      {/* Tab 5: Edit */}
      {tab === 5 && (
        <Form
          onSubmit={handleSubmit(onSave)}
          sx={{ maxWidth: { xs: '100%', md: FORM_MAX_WIDTH, xl: 1440 }, display: 'flex', flexDirection: 'column', gap: 4 }}
        >
          <Typography variant="body2" color="text.secondary">
            {t('pages.tanks.editIntro')}
          </Typography>

          {/* UI-NFR-008 R-061: Master-detail layout — left column = Identification (master,
              capped at reading width), right column = stacked compact panel (Location).
              Equipment, Notes and Sensors remain full-width below to preserve the natural
              rhythm of switch grids and the sensors DataTable (R-058). */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: `minmax(0, ${READING_COL_MAX}px) 1fr` },
              gap: 4,
              alignItems: 'start',
            }}
          >
            <Card variant="outlined">
              <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
                <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                  {t('pages.tanks.sectionIdentification')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t('pages.tanks.sectionIdentificationDesc')}
                </Typography>
                <FormTextField
                  name="name"
                  control={control}
                  label={t('pages.tanks.name')}
                  required
                  autoFocus
                />
                <FormRow>
                  <FormSelectField
                    name="tank_type"
                    control={control}
                    label={t('pages.tanks.tankType')}
                    helperText={t('pages.tanks.tankTypeHelper')}
                    required
                    options={tankTypes.map((v) => ({
                      value: v,
                      label: t(`enums.tankType.${v}`),
                    }))}
                  />
                  <FormSelectField
                    name="material"
                    control={control}
                    label={t('pages.tanks.material')}
                    helperText={t('pages.tanks.materialHelper')}
                    required
                    options={materials.map((v) => ({
                      value: v,
                      label: t(`enums.tankMaterial.${v}`),
                    }))}
                  />
                </FormRow>
                <FormNumberField
                  name="volume_liters"
                  control={control}
                  label={t('pages.tanks.volumeLiters')}
                  helperText={t('pages.tanks.volumeLitersHelper')}
                  suffix="L"
                  inputMode="decimal"
                  min={0.1}
                  required
                />
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
                <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                  {t('pages.tanks.sectionLocation')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t('pages.tanks.sectionLocationDesc')}
                </Typography>
                <TextField
                  select
                  label={t('pages.tanks.site')}
                  value={selectedSiteKey}
                  onChange={(e) => handleSiteChange(e.target.value)}
                  fullWidth
                  sx={{ mb: 2 }}
                  data-testid="form-field-site"
                >
                  <MenuItem value="">—</MenuItem>
                  {sites.map((s) => (
                    <MenuItem key={s.key} value={s.key}>{s.name}</MenuItem>
                  ))}
                </TextField>
                <LocationTreeSelect
                  name="location_key"
                  control={control}
                  siteKey={selectedSiteKey || null}
                  label={t('pages.tanks.location')}
                />
              </CardContent>
            </Card>
          </Box>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tanks.sectionEquipment')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tanks.sectionEquipmentDesc')}
              </Typography>
              <FormRow>
                <FormSwitchField
                  name="has_lid"
                  control={control}
                  label={t('pages.tanks.hasLid')}
                  helperText={t('pages.tanks.hasLidHelper')}
                />
                <FormSwitchField
                  name="has_air_pump"
                  control={control}
                  label={t('pages.tanks.hasAirPump')}
                  helperText={t('pages.tanks.hasAirPumpHelper')}
                />
              </FormRow>
              <FormRow>
                <FormSwitchField
                  name="has_circulation_pump"
                  control={control}
                  label={t('pages.tanks.hasCirculationPump')}
                  helperText={t('pages.tanks.hasCirculationPumpHelper')}
                />
                <FormSwitchField
                  name="has_heater"
                  control={control}
                  label={t('pages.tanks.hasHeater')}
                  helperText={t('pages.tanks.hasHeaterHelper')}
                />
              </FormRow>
              <FormRow>
                <FormSwitchField
                  name="is_light_proof"
                  control={control}
                  label={t('pages.tanks.isLightProof')}
                  helperText={t('pages.tanks.isLightProofHelper')}
                />
                <FormSwitchField
                  name="has_uv_sterilizer"
                  control={control}
                  label={t('pages.tanks.hasUvSterilizer')}
                  helperText={t('pages.tanks.hasUvSterilizerHelper')}
                />
              </FormRow>
              <FormSwitchField
                name="has_ozone_generator"
                control={control}
                label={t('pages.tanks.hasOzoneGenerator')}
                helperText={t('pages.tanks.hasOzoneGeneratorHelper')}
              />
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tanks.sectionNotes')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tanks.sectionNotesDesc')}
              </Typography>
              {/* UI-NFR-008 R-054: prose field capped at reading width */}
              <Box sx={{ maxWidth: READING_COL_MAX }}>
                <FormTextField
                  name="notes"
                  control={control}
                  label={t('pages.tanks.notes')}
                  multiline
                  minRows={4}
                  maxRows={14}
                />
              </Box>
            </CardContent>
          </Card>

          {/* Sensors — issue #587: only when smart home is enabled */}
          {isSmartHomeEnabled && (
          <Card variant="outlined" data-testid="tank-sensors-section">
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1, flexWrap: 'wrap', gap: 1 }}>
                <Typography variant="h6">{t('pages.tanks.sensors')}</Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => { setEditSensor(undefined); setSensorDialogOpen(true); }}
                  data-testid="tank-add-sensor-button"
                >
                  {t('pages.tanks.addSensor')}
                </Button>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: sensors.length > 0 ? 2 : 1 }}>
                {t('pages.tanks.sensorsDesc')}
              </Typography>
              <DataTable
                columns={sensorColumns}
                rows={sensors}
                getRowKey={(r) => r.key}
                variant="simple"
                ariaLabel={t('pages.tanks.sensors')}
                emptyMessage={t('pages.tanks.noSensors')}
                emptyActionLabel={t('pages.tanks.addSensor')}
                onEmptyAction={() => { setEditSensor(undefined); setSensorDialogOpen(true); }}
              />
            </CardContent>
          </Card>
          )}

          <Typography variant="caption" color="text.secondary">* {t('common.required')}</Typography>
          <FormActions
            onCancel={() => reset()}
            loading={saving}
            disabled={!isDirty}
          />
        </Form>
      )}

      <TankStateCreateDialog
        open={stateDialogOpen}
        onClose={() => setStateDialogOpen(false)}
        tankKey={key ?? ''}
        onCreated={() => {
          setStateDialogOpen(false);
          load();
        }}
      />
      <MaintenanceLogDialog
        open={maintenanceDialogOpen}
        onClose={() => setMaintenanceDialogOpen(false)}
        tankKey={key ?? ''}
        onCreated={() => {
          setMaintenanceDialogOpen(false);
          load();
        }}
      />
      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: tank.name })}
        onConfirm={onDelete}
        onCancel={() => setDeleteOpen(false)}
        destructive
        loading={deleting}
      />
      <MaintenanceScheduleDialog
        open={scheduleDialogOpen}
        onClose={() => { setScheduleDialogOpen(false); setEditSchedule(undefined); }}
        tankKey={key ?? ''}
        schedule={editSchedule}
        onSaved={() => { setScheduleDialogOpen(false); setEditSchedule(undefined); load(); }}
      />
      <TankFillCreateDialog
        open={fillDialogOpen}
        onClose={() => setFillDialogOpen(false)}
        tankKey={key ?? ''}
        onCreated={() => {
          setFillDialogOpen(false);
          load();
        }}
      />
      <ConfirmDialog
        open={!!deleteScheduleKey}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: schedules.find((s) => s.key === deleteScheduleKey)?.maintenance_type ?? '' })}
        onConfirm={onDeleteSchedule}
        onCancel={() => setDeleteScheduleKey(null)}
        destructive
        loading={deletingSchedule}
      />
      <SensorCreateDialog
        open={sensorDialogOpen}
        onClose={() => { setSensorDialogOpen(false); setEditSensor(undefined); }}
        context={{ parentType: 'tank', parentKey: key ?? '' }}
        sensor={editSensor}
        onSaved={() => { setSensorDialogOpen(false); setEditSensor(undefined); load(); }}
      />
      <ConfirmDialog
        open={!!deleteSensorKey}
        title={t('common.delete')}
        message={t('pages.tanks.deleteSensorConfirm', { name: sensors.find((s) => s.key === deleteSensorKey)?.name ?? '' })}
        onConfirm={onDeleteSensor}
        onCancel={() => setDeleteSensorKey(null)}
        destructive
        loading={deletingSensor}
      />
    </Box>
  );
}

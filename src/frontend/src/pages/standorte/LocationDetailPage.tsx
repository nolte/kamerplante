import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SensorsIcon from '@mui/icons-material/Sensors';
import GrassIcon from '@mui/icons-material/Grass';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import MobileCard from '@/components/common/MobileCard';
import PageTitle from '@/components/layout/PageTitle';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ErrorDisplay from '@/components/common/ErrorDisplay';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import DataTable, { type Column } from '@/components/common/DataTable';
import EmptyState from '@/components/common/EmptyState';
import { useTableLocalState } from '@/hooks/useTableState';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormNumberField from '@/components/form/FormNumberField';
import FormTimeField from '@/components/form/FormTimeField';
import FormSwitchField from '@/components/form/FormSwitchField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import UnsavedChangesGuard from '@/components/form/UnsavedChangesGuard';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import WaterDropIcon from '@mui/icons-material/WaterDrop';
import LocationCreateDialog from './LocationCreateDialog';
import SlotCreateDialog from './SlotCreateDialog';
import SensorCreateDialog from './SensorCreateDialog';
import WateringEventCreateDialog from './WateringEventCreateDialog';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import { useSmartHomeEnabled } from '@/hooks/useSmartHomeEnabled';
import { useAppDispatch } from '@/store/hooks';
import { setBreadcrumbs } from '@/store/slices/uiSlice';
import * as api from '@/api/endpoints/sites';
import * as tankApi from '@/api/endpoints/tanks';
import * as wateringApi from '@/api/endpoints/watering-events';
import * as runApi from '@/api/endpoints/plantingRuns';
import { listAllPlantInstances } from '@/api/endpoints/plantInstances';
import HaPublishToggle from '@/components/ha/HaPublishToggle';
import type { ChipProps } from '@mui/material/Chip';
import type { Location, PlantInstance, PlantingRun, PlantingRunStatus, Sensor, Slot, Tank, WateringEvent, WateringStats } from '@/api/types';
import { getPlantDisplayName } from '@/utils/plantDisplay';

const runStatusColor: Record<PlantingRunStatus, ChipProps['color']> = {
  planned: 'default',
  active: 'primary',
  harvesting: 'warning',
  completed: 'success',
  cancelled: 'error',
};

const timeRegex = /^\d{2}:\d{2}$/;

const schema = z.object({
  name: z.string().min(1),
  site_key: z.string(),
  area_m2: z.number().min(0),
  light_type: z.enum(['natural', 'led', 'hps', 'cmh', 'mixed']),
  irrigation_system: z.enum(['manual', 'drip', 'hydro', 'mist', 'nft', 'ebb_flow']),
  lights_on: z.string().regex(timeRegex).nullable().optional(),
  lights_off: z.string().regex(timeRegex).nullable().optional(),
  use_dynamic_sunrise: z.boolean(),
  frost_exposure: z.enum(['inherit', 'exposed', 'protected']),
});

type FormData = z.infer<typeof schema>;

const FROST_EXPOSURE_OPTIONS = ['inherit', 'exposed', 'protected'] as const;

// Maps the tri-state UI value to the nullable `frost_exposed` API field:
// inherit → null (inherit from site), exposed → true, protected → false.
function frostExposureToApi(value: FormData['frost_exposure']): boolean | null {
  if (value === 'exposed') return true;
  if (value === 'protected') return false;
  return null;
}

// Maps the persisted `frost_exposed` API value back to the tri-state UI value
// so the current setting is pre-selected when editing.
function frostExposureFromApi(value: boolean | null | undefined): FormData['frost_exposure'] {
  if (value === true) return 'exposed';
  if (value === false) return 'protected';
  return 'inherit';
}

export default function LocationDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const notification = useNotification();
  const { handleError } = useApiError();
  // Issue #587: sensor UI is gated behind the smart-home toggle.
  const { isSmartHomeEnabled } = useSmartHomeEnabled();
  const [location, setLocation] = useState<Location | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deletingSensor, setDeletingSensor] = useState(false);
  const [slotCreateOpen, setSlotCreateOpen] = useState(false);
  const [wateringEvents, setWateringEvents] = useState<WateringEvent[]>([]);
  const [wateringStats, setWateringStats] = useState<WateringStats | null>(null);
  const [wateringCreateOpen, setWateringCreateOpen] = useState(false);
  const [assignedTank, setAssignedTank] = useState<Tank | null>(null);
  const [childLocations, setChildLocations] = useState<Location[]>([]);
  const [sublocationCreateOpen, setSublocationCreateOpen] = useState(false);
  const [ancestorChain, setAncestorChain] = useState<{ key: string; name: string }[]>([]);
  const [siteName, setSiteName] = useState<string>('');
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [sensorDialogOpen, setSensorDialogOpen] = useState(false);
  const [editSensor, setEditSensor] = useState<Sensor | undefined>(undefined);
  const [deleteSensorKey, setDeleteSensorKey] = useState<string | null>(null);
  const [assignedRuns, setAssignedRuns] = useState<PlantingRun[]>([]);
  const [runPlantCounts, setRunPlantCounts] = useState<Map<string, number>>(new Map());
  const [standaloneInstances, setStandaloneInstances] = useState<PlantInstance[]>([]);
  const slotTableState = useTableLocalState({ defaultSort: { column: 'slotId', direction: 'asc' } });
  const runTableState = useTableLocalState({ defaultSort: { column: 'name', direction: 'asc' } });
  const instanceTableState = useTableLocalState({ defaultSort: { column: 'instance_id', direction: 'asc' } });
  const childTableState = useTableLocalState({ defaultSort: { column: 'name', direction: 'asc' } });
  const wateringTableState = useTableLocalState({ defaultSort: { column: 'wateredAt', direction: 'desc' } });
  const sensorTableState = useTableLocalState({ defaultSort: { column: 'name', direction: 'asc' } });

  const { control, handleSubmit, reset, formState: { isDirty } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      site_key: '',
      area_m2: 0,
      light_type: 'natural',
      irrigation_system: 'manual',
      lights_on: null,
      lights_off: null,
      use_dynamic_sunrise: false,
      frost_exposure: 'inherit',
    },
  });

  const lightType = useWatch({ control, name: 'light_type' });
  const isArtificial = lightType === 'led' || lightType === 'hps' || lightType === 'cmh';
  const isNaturalOrMixed = lightType === 'natural' || lightType === 'mixed';

  const load = async () => {
    if (!key) return;
    setLoading(true);
    try {
      const loc = await api.getLocation(key);
      setLocation(loc);
      // Build ancestor breadcrumb chain
      const ancestors: { key: string; name: string }[] = [];
      let current = loc;
      while (current.parent_location_key) {
        try {
          const parent = await api.getLocation(current.parent_location_key);
          ancestors.unshift({ key: parent.key, name: parent.name });
          current = parent;
        } catch {
          break;
        }
      }
      setAncestorChain(ancestors);
      // Fetch site name for breadcrumb
      try {
        const site = await api.getSite(loc.site_key);
        setSiteName(site.name);
      } catch {
        setSiteName('');
      }
      reset({
        name: loc.name,
        site_key: loc.site_key,
        area_m2: loc.area_m2,
        light_type: loc.light_type,
        irrigation_system: loc.irrigation_system,
        lights_on: loc.lights_on,
        lights_off: loc.lights_off,
        use_dynamic_sunrise: loc.use_dynamic_sunrise,
        frost_exposure: frostExposureFromApi(loc.frost_exposed),
      });
      const [s, children] = await Promise.all([
        api.listSlots(key),
        api.listLocationChildren(key),
      ]);
      setSlots(s);
      setChildLocations(children);
      // Load assigned tank:
      // Primary: Location.tank_key (denormalized).
      // Fallback: find tank whose location_key matches this location.
      if (loc.tank_key) {
        try {
          const t = await tankApi.getTank(loc.tank_key);
          setAssignedTank(t);
        } catch {
          setAssignedTank(null);
        }
      } else {
        try {
          const allTanks = await tankApi.listTanks(0, 200);
          const match = allTanks.find((t) => t.location_key === key);
          setAssignedTank(match ?? null);
        } catch {
          setAssignedTank(null);
        }
      }
      // Load watering events and stats
      try {
        const [we, ws] = await Promise.all([
          wateringApi.getLocationWateringEvents(key),
          wateringApi.getLocationWateringStats(key),
        ]);
        setWateringEvents(we);
        setWateringStats(ws);
      } catch {
        // Watering data may not be available
      }
      // Load sensors
      try {
        const locationSensors = await api.getLocationSensors(key);
        setSensors(locationSensors);
      } catch {
        // Sensors may not be available
      }
      // Load assigned planting runs + plant instances for this location
      try {
        const runs = await runApi.listPlantingRuns(0, 200, undefined, undefined, key);
        setAssignedRuns(runs);
        // Load plant counts per run
        const counts = new Map<string, number>();
        const runInstanceKeys = new Set<string>();
        await Promise.all(
          runs.map(async (r) => {
            try {
              const plants = await runApi.listRunPlants(r.key);
              counts.set(r.key, plants.length);
              for (const p of plants) runInstanceKeys.add(p.key);
            } catch {
              counts.set(r.key, r.actual_quantity);
            }
          }),
        );
        setRunPlantCounts(counts);
        // Load all plant instances at this location and find standalone ones
        try {
          const allInstances = await listAllPlantInstances();
          const locationInstances = allInstances.filter((i) => i.location_key === key);
          setStandaloneInstances(locationInstances.filter((i) => !runInstanceKeys.has(i.key)));
        } catch {
          setStandaloneInstances([]);
        }
      } catch {
        setAssignedRuns([]);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [key]);

  // Push dynamic breadcrumbs to global store
  useEffect(() => {
    if (!location) return;
    const crumbs: { label: string; path?: string }[] = [
      { label: 'nav.dashboard', path: '/dashboard' },
      { label: 'nav.sites', path: '/standorte/sites' },
    ];
    if (siteName) {
      crumbs.push({ label: siteName, path: `/standorte/sites/${location.site_key}` });
    }
    for (const a of ancestorChain) {
      crumbs.push({ label: a.name, path: `/standorte/locations/${a.key}` });
    }
    crumbs.push({ label: location.name });
    dispatch(setBreadcrumbs(crumbs));
  }, [location, siteName, ancestorChain, dispatch]);

  // Clear dynamic breadcrumbs on unmount
  useEffect(() => () => { dispatch(setBreadcrumbs([])); }, [dispatch]);

  const onSubmit = async (data: FormData) => {
    if (!key) return;
    try {
      setSaving(true);
      const { frost_exposure, ...rest } = data;
      await api.updateLocation(key, {
        ...rest,
        lights_on: data.lights_on || undefined,
        lights_off: data.lights_off || undefined,
        frost_exposed: frostExposureToApi(frost_exposure),
      });
      notification.success(t('common.save'));
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
      await api.deleteLocation(key);
      notification.success(t('common.delete'));
      navigate(-1);
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
        // Scoped by the location: a sensor has no tenant of its own, so its
        // parent is the anchor the backend verifies (#1339).
        await api.deleteLocationSensor(key, deleteSensorKey);
        notification.success(t('pages.sensors.deleted'));
        load();
      } catch (err) {
        handleError(err);
      } finally {
        setDeletingSensor(false);
      }
    }
    setDeleteSensorKey(null);
  };

  const slotColumns: Column<Slot>[] = [
    { id: 'slotId', label: t('pages.slots.slotId'), render: (r) => r.slot_id },
    { id: 'position', label: t('pages.slots.position'), render: (r) => `(${r.position[0]}, ${r.position[1]})` },
    { id: 'capacity', label: t('pages.slots.capacity'), render: (r) => r.capacity_plants, align: 'right' as const },
    { id: 'occupied', label: t('pages.slots.occupied'), render: (r) => (
      <Chip label={r.currently_occupied ? t('common.yes') : t('common.no')} size="small" color={r.currently_occupied ? 'warning' : 'default'} />
    )},
  ];

  if (loading) return <LoadingSkeleton variant="form" />;
  if (error) return <ErrorDisplay error={error} onRetry={() => navigate(-1)} />;

  const PANEL_GAP = 4;

  return (
    <Box data-testid="location-detail-page">
      <UnsavedChangesGuard dirty={isDirty} />

      <PageTitle
        title={location?.name ?? t('entities.location')}
        action={
          <Button color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteOpen(true)}>
            {t('common.delete')}
          </Button>
        }
      />

      <Form onSubmit={handleSubmit(onSubmit)} sx={{ maxWidth: 1280, display: 'flex', flexDirection: 'column', gap: PANEL_GAP }}>
        <Typography variant="body2" color="text.secondary">
          {t('pages.locations.editIntro')}
        </Typography>

        <Card variant="outlined">
          <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
            <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
              {t('pages.locations.sectionBasicData')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('pages.locations.sectionBasicDataDesc')}
            </Typography>
            <FormRow>
              <FormTextField name="name" control={control} label={t('pages.locations.name')} required autoFocus />
              <FormNumberField name="area_m2" control={control} label={t('pages.locations.area')} helperText={t('pages.locations.areaHelper')} min={0} />
            </FormRow>
            <FormSelectField
              name="frost_exposure"
              control={control}
              label={t('pages.locations.frostExposure')}
              helperText={t('pages.locations.frostExposureHelper')}
              options={FROST_EXPOSURE_OPTIONS.map((v) => ({
                value: v,
                label: t(`enums.frostExposure.${v}`),
              }))}
            />
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
            <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
              {t('pages.locations.sectionLightingIrrigation')}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('pages.locations.sectionLightingIrrigationDesc')}
            </Typography>
            <FormRow>
              <FormSelectField
                name="light_type"
                control={control}
                label={t('pages.locations.lightType')}
                options={['natural', 'led', 'hps', 'cmh', 'mixed'].map((v) => ({
                  value: v, label: t(`enums.lightType.${v}`),
                }))}
              />
              <FormSelectField
                name="irrigation_system"
                control={control}
                label={t('pages.locations.irrigationSystem')}
                options={['manual', 'drip', 'hydro', 'mist', 'nft', 'ebb_flow'].map((v) => ({
                  value: v, label: t(`enums.irrigationSystem.${v}`),
                }))}
              />
            </FormRow>

            {(isArtificial || isNaturalOrMixed) && (
              <Box sx={{ display: 'flex', gap: 2 }}>
                <FormTimeField
                  name="lights_on"
                  control={control}
                  label={t('pages.locations.lightsOn')}
                  helperText={t('pages.locations.lightsOnHelper')}
                />
                <FormTimeField
                  name="lights_off"
                  control={control}
                  label={t('pages.locations.lightsOff')}
                  helperText={t('pages.locations.lightsOffHelper')}
                />
              </Box>
            )}

            {isNaturalOrMixed && (
              <FormSwitchField
                name="use_dynamic_sunrise"
                control={control}
                label={t('pages.locations.useDynamicSunrise')}
              />
            )}
          </CardContent>
        </Card>

        <Typography variant="caption" color="text.secondary">* {t('common.required')}</Typography>
        <FormActions onCancel={() => navigate(-1)} loading={saving} />
      </Form>

      {/* Assigned Tank */}
      <Box sx={{ mt: 3, maxWidth: 600 }}>
        <Card variant="outlined">
          <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {t('pages.locations.assignedTank')}
            </Typography>
            {assignedTank ? (
              <Chip
                label={`${assignedTank.name} (${assignedTank.volume_liters} L)`}
                size="small"
                color="primary"
                variant="outlined"
                onClick={() => navigate(`/standorte/tanks/${assignedTank.key}`)}
              />
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t('pages.locations.noTank')}
              </Typography>
            )}
          </CardContent>
        </Card>

        {key && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <HaPublishToggle entityType="location" entityKey={key} />
            </CardContent>
          </Card>
        )}
      </Box>

      {/* Plants & Runs at this location */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <GrassIcon />
          {t('pages.locations.plantsAndRuns')}
        </Typography>
        {assignedRuns.length === 0 && standaloneInstances.length === 0 ? (
          <EmptyState message={t('pages.locations.noPlantsOrRuns')} />
        ) : (
          <>
            {assignedRuns.length > 0 && (
              <DataTable<PlantingRun>
                columns={[
                  { id: 'name', label: t('pages.plantingRuns.name'), render: (r) => r.name },
                  { id: 'status', label: t('pages.plantingRuns.status'), render: (r) => (
                    <Chip label={t(`enums.plantingRunStatus.${r.status}`)} size="small" color={runStatusColor[r.status] ?? 'default'} />
                  )},
                  { id: 'runType', label: t('pages.plantingRuns.runType'), render: (r) => t(`enums.plantingRunType.${r.run_type}`) },
                  { id: 'plants', label: t('pages.locations.plantCount'), render: (r) => (
                    <Chip
                      label={`${runPlantCounts.get(r.key) ?? r.actual_quantity} ${t('entities.plantInstances')}`}
                      size="small"
                      variant="outlined"
                    />
                  ), searchValue: (r) => String(runPlantCounts.get(r.key) ?? r.actual_quantity) },
                ]}
                rows={assignedRuns}
                getRowKey={(r) => r.key}
                onRowClick={(r) => navigate(`/durchlaeufe/planting-runs/${r.key}`)}
                tableState={runTableState}
                ariaLabel={t('pages.locations.assignedRuns')}
                mobileCardRenderer={(r) => (
                  <MobileCard
                    title={r.name}
                    titleId="name"
                    chips={[
                      {
                        id: 'status',
                        content: (
                          <Chip label={t(`enums.plantingRunStatus.${r.status}`)} size="small" color={runStatusColor[r.status] ?? 'default'} />
                        ),
                      },
                    ]}
                    fields={[
                      { id: 'runType', label: t('pages.plantingRuns.runType'), value: t(`enums.plantingRunType.${r.run_type}`) },
                      { id: 'plants', label: t('pages.locations.plantCount'), value: `${runPlantCounts.get(r.key) ?? r.actual_quantity} ${t('entities.plantInstances')}` },
                    ]}
                  />
                )}
              />
            )}
            {standaloneInstances.length > 0 && (
              <Box sx={{ mt: assignedRuns.length > 0 ? 3 : 0 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  {t('pages.locations.standalonePlants')}
                </Typography>
                <DataTable<PlantInstance>
                  columns={[
                    { id: 'instance_id', label: t('pages.plantInstances.instanceId'), render: (r) => r.instance_id },
                    { id: 'plant_name', label: t('pages.plantInstances.plantName'), render: (r) => {
                      const name = getPlantDisplayName(r);
                      return name === r.instance_id ? '—' : name;
                    }, searchValue: (r) => getPlantDisplayName(r) },
                    { id: 'current_phase', label: t('pages.plantInstances.currentPhase'), render: (r) => (
                      <Chip label={t(`enums.phaseName.${r.current_phase}`)} size="small" variant="outlined" />
                    ), searchValue: (r) => t(`enums.phaseName.${r.current_phase}`) },
                    { id: 'planted_on', label: t('pages.plantInstances.plantedOn'), render: (r) => r.planted_on ? new Date(r.planted_on).toLocaleDateString() : '—' },
                  ]}
                  rows={standaloneInstances}
                  getRowKey={(r) => r.key}
                  onRowClick={(r) => navigate(`/pflanzen/plant-instances/${r.key}`)}
                  tableState={instanceTableState}
                  ariaLabel={t('pages.locations.standalonePlants')}
                  mobileCardRenderer={(r) => {
                    const displayName = getPlantDisplayName(r);
                    return (
                      <MobileCard
                        title={displayName}
                        titleId="plant_name"
                        subtitle={displayName !== r.instance_id ? r.instance_id : undefined}
                        subtitleId="instance_id"
                        chips={
                          r.current_phase
                            ? [
                                {
                                  id: 'current_phase',
                                  content: (
                                    <Chip label={t(`enums.phaseName.${r.current_phase}`)} size="small" variant="outlined" />
                                  ),
                                },
                              ]
                            : []
                        }
                        fields={r.planted_on ? [{ id: 'planted_on', label: t('pages.plantInstances.plantedOn'), value: new Date(r.planted_on).toLocaleDateString() }] : []}
                      />
                    );
                  }}
                />
              </Box>
            )}
          </>
        )}
      </Box>

      {/* Sub-Locations */}
      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">{t('pages.locations.sublocations')}</Typography>
          <Button startIcon={<AddIcon />} onClick={() => setSublocationCreateOpen(true)} data-testid="add-sublocation-button">
            {t('pages.locations.addSublocation')}
          </Button>
        </Box>
        {childLocations.length === 0 ? (
          <EmptyState
            message={t('pages.locations.noSublocations')}
            actionLabel={t('pages.locations.addSublocation')}
            onAction={() => setSublocationCreateOpen(true)}
          />
        ) : (
          <DataTable<Location>
            columns={[
              { id: 'name', label: t('pages.locations.name'), render: (r) => r.name },
              { id: 'locationType', label: t('pages.locations.locationType'), render: (r) => r.location_type_key || '—' },
              { id: 'area', label: t('pages.locations.area'), render: (r) => `${r.area_m2} m²`, align: 'right', searchValue: (r) => String(r.area_m2) },
            ]}
            rows={childLocations}
            getRowKey={(r) => r.key}
            onRowClick={(r) => navigate(`/standorte/locations/${r.key}`)}
            tableState={childTableState}
            ariaLabel={t('pages.locations.sublocations')}
            mobileCardRenderer={(r) => (
              <MobileCard
                title={r.name}
                titleId="name"
                subtitle={r.location_type_key || undefined}
                subtitleId="locationType"
                fields={[
                  { id: 'area', label: t('pages.locations.area'), value: `${r.area_m2} m²` },
                ]}
              />
            )}
          />
        )}
      </Box>

      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">{t('pages.slots.title')}</Typography>
          <Button startIcon={<AddIcon />} onClick={() => setSlotCreateOpen(true)} data-testid="create-slot-button">
            {t('pages.slots.create')}
          </Button>
        </Box>
        {slots.length === 0 ? (
          <EmptyState
            message={t('pages.slots.noSlots')}
            actionLabel={t('pages.slots.create')}
            onAction={() => setSlotCreateOpen(true)}
          />
        ) : (
          <DataTable
            columns={slotColumns}
            rows={slots}
            getRowKey={(r) => r.key}
            onRowClick={(r) => navigate(`/standorte/slots/${r.key}`)}
            tableState={slotTableState}
            ariaLabel={t('pages.slots.title')}
            mobileCardRenderer={(r) => (
              <MobileCard
                title={r.slot_id}
                titleId="slotId"
                subtitle={`(${r.position[0]}, ${r.position[1]})`}
                subtitleId="position"
                chips={[
                  {
                    id: 'occupied',
                    content: (
                      <Chip
                        label={r.currently_occupied ? t('common.yes') : t('common.no')}
                        size="small"
                        color={r.currently_occupied ? 'warning' : 'default'}
                      />
                    ),
                  },
                ]}
                fields={[
                  { id: 'capacity', label: t('pages.slots.capacity'), value: String(r.capacity_plants) },
                ]}
              />
            )}
          />
        )}
      </Box>

      {/* Watering Events Section */}
      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <WaterDropIcon />
            {t('pages.wateringEvents.title')}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setWateringCreateOpen(true)}
            data-testid="create-watering-button"
          >
            {t('pages.wateringEvents.create')}
          </Button>
        </Box>

        {wateringStats && (
          <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
            <Card sx={{ minWidth: 150 }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Typography variant="caption" color="text.secondary">
                  {t('pages.wateringEvents.totalEvents')}
                </Typography>
                <Typography variant="h6">{wateringStats.total_events}</Typography>
              </CardContent>
            </Card>
            <Card sx={{ minWidth: 150 }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                <Typography variant="caption" color="text.secondary">
                  {t('pages.wateringEvents.totalVolume')}
                </Typography>
                <Typography variant="h6">{wateringStats.total_volume} L</Typography>
              </CardContent>
            </Card>
            {wateringStats.by_method.map((m) => (
              <Card key={m.method} sx={{ minWidth: 150 }}>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="caption" color="text.secondary">
                    {t(`enums.applicationMethod.${m.method}`)}
                  </Typography>
                  <Typography variant="h6">{m.count}× / {m.total_volume} L</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}

        <DataTable<WateringEvent>
          columns={[
            {
              id: 'wateredAt',
              label: t('pages.wateringEvents.wateredAt'),
              render: (r) => r.watered_at ? new Date(r.watered_at).toLocaleString() : '—',
              searchValue: (r) => r.watered_at ? new Date(r.watered_at).toLocaleString() : '',
            },
            {
              id: 'applicationMethod',
              label: t('pages.wateringEvents.applicationMethod'),
              render: (r) => t(`enums.applicationMethod.${r.application_method}`),
              searchValue: (r) => t(`enums.applicationMethod.${r.application_method}`),
            },
            {
              id: 'volume',
              label: t('pages.wateringEvents.volumeLiters'),
              render: (r) => `${r.volume_liters} L`,
              align: 'right',
            },
            {
              id: 'plants',
              label: t('pages.wateringEvents.plantKeys'),
              render: (r) => String(r.plant_keys.length),
              align: 'right',
            },
            {
              id: 'waterSource',
              label: t('pages.wateringEvents.waterSource'),
              render: (r) => r.water_source ? t(`enums.waterSource.${r.water_source}`) : '—',
            },
          ]}
          rows={wateringEvents}
          getRowKey={(r) => r.key}
          tableState={wateringTableState}
          ariaLabel={t('pages.wateringEvents.title')}
          mobileCardRenderer={(r) => (
            <MobileCard
              title={r.watered_at ? new Date(r.watered_at).toLocaleString() : '—'}
              titleId="wateredAt"
              chips={[
                {
                  id: 'applicationMethod',
                  content: <Chip label={t(`enums.applicationMethod.${r.application_method}`)} size="small" />,
                },
              ]}
              fields={[
                { id: 'volume', label: t('pages.wateringEvents.volumeLiters'), value: `${r.volume_liters} L` },
                { id: 'plantKeys', label: t('pages.wateringEvents.plantKeys'), value: String(r.plant_keys.length) },
                ...(r.water_source ? [{ id: 'waterSource', label: t('pages.wateringEvents.waterSource'), value: t(`enums.waterSource.${r.water_source}`) }] : []),
              ]}
            />
          )}
        />

        <WateringEventCreateDialog
          open={wateringCreateOpen}
          onClose={() => setWateringCreateOpen(false)}
          onCreated={() => {
            setWateringCreateOpen(false);
            load();
          }}
        />
      </Box>

      {/* Sensors — issue #587: only when smart home is enabled */}
      {isSmartHomeEnabled && (
      <Box sx={{ mt: 4 }} data-testid="location-sensors-section">
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
          context={{ parentType: 'location', parentKey: key }}
          sensor={editSensor}
          onSaved={() => { setSensorDialogOpen(false); setEditSensor(undefined); load(); }}
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

      {key && (
        <SlotCreateDialog
          locationKey={key}
          open={slotCreateOpen}
          onClose={() => setSlotCreateOpen(false)}
          onCreated={() => { setSlotCreateOpen(false); load(); }}
        />
      )}

      {key && location && (
        <LocationCreateDialog
          siteKey={location.site_key}
          parentLocationKey={key}
          parentLocationTypeKey={location.location_type_key}
          open={sublocationCreateOpen}
          onClose={() => setSublocationCreateOpen(false)}
          onCreated={() => { setSublocationCreateOpen(false); load(); }}
        />
      )}

      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: location?.name })}
        onConfirm={onDelete}
        onCancel={() => setDeleteOpen(false)}
        destructive
        loading={deleting}
      />
    </Box>
  );
}

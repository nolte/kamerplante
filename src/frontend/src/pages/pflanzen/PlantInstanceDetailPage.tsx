import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTabUrl } from '@/hooks/useTabUrl';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Divider from '@mui/material/Divider';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Alert from '@mui/material/Alert';
import Link from '@mui/material/Link';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Skeleton from '@mui/material/Skeleton';
import LinearProgress from '@mui/material/LinearProgress';
import CircularProgress from '@mui/material/CircularProgress';
import RemoveCircleIcon from '@mui/icons-material/RemoveCircle';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import LabelIcon from '@mui/icons-material/Label';
import ScienceIcon from '@mui/icons-material/Science';
import TodayIcon from '@mui/icons-material/Today';
import DeleteIcon from '@mui/icons-material/Delete';
import OpacityIcon from '@mui/icons-material/Opacity';
import AddIcon from '@mui/icons-material/Add';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import RepeatIcon from '@mui/icons-material/Repeat';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import EventAvailableIcon from '@mui/icons-material/EventAvailable';
import PendingIcon from '@mui/icons-material/Pending';
import axios from 'axios';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { isApiError } from '@/api/errors';
import PageTitle from '@/components/layout/PageTitle';
import PageHeaderActions from '@/components/layout/PageHeaderActions';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ErrorDisplay from '@/components/common/ErrorDisplay';
import EmptyState from '@/components/common/EmptyState';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import DataTable from '@/components/common/DataTable';
import MobileCard from '@/components/common/MobileCard';
import TaskOriginBadge from '@/components/common/TaskOriginBadge';
import Form from '@/components/form/Form';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormNumberField from '@/components/form/FormNumberField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import LocationAssignmentSection from '@/components/form/LocationAssignmentSection';
import UnsavedChangesGuard from '@/components/form/UnsavedChangesGuard';
import QrCode2Icon from '@mui/icons-material/QrCode2';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import PhaseTransitionDialog from './PhaseTransitionDialog';
import TerminationDialog from './TerminationDialog';
import PlantTagDialog from './PlantTagDialog';
import { PlantLabelDialog } from '@/components/print/PlantLabelDialog';
import PlantPhaseTimeline from './PlantPhaseTimeline';
import HarvestReadinessSection from './HarvestReadinessSection';
import { plantCanBeHarvested, harvestDateIsPredictable } from './harvestability';
import ProfilesSection from './ProfilesSection';
import OverwinteringSection from './OverwinteringSection';
import PestScanButton from '@/components/pests/PestScanButton';
import PhaseHistoryTable from '@/pages/durchlaeufe/PhaseHistoryTable';
import CareConfirmDialog from '@/pages/pflege/components/CareConfirmDialog';
import CareProfileForm from '@/pages/pflege/components/CareProfileForm';
import type { DosagePreset } from '@/pages/pflege/components/CareConfirmDialog';
import WateringLogCreateDialog from '@/pages/giessprotokoll/WateringLogCreateDialog';
import type { ChannelPreset } from '@/pages/giessprotokoll/WateringLogCreateDialog';
import DeliveryChannelAccordion from '@/pages/duengung/DeliveryChannelAccordion';
import NutrientPlanAssignDialog from '@/pages/duengung/NutrientPlanAssignDialog';
import PhaseGanttChart from '@/pages/duengung/PhaseGanttChart';
import ActivityPlanTab from '@/pages/durchlaeufe/ActivityPlanTab';
import PhaseDetailGantt from '@/pages/duengung/PhaseDetailGantt';
import { computeCurrentWeek } from '@/utils/weekCalculation';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import { useWateringVolumeSuggestion } from '@/hooks/useWateringVolumeSuggestion';
import { useTableLocalState } from '@/hooks/useTableState';
import * as plantApi from '@/api/endpoints/plantInstances';
import * as phasesApi from '@/api/endpoints/phases';
import * as speciesApi from '@/api/endpoints/species';
import * as planApi from '@/api/endpoints/nutrient-plans';
import * as fertApi from '@/api/endpoints/fertilizers';
import * as wateringLogApi from '@/api/endpoints/watering-logs';
import * as sitesApi from '@/api/endpoints/sites';
import * as careApi from '@/api/endpoints/careReminders';
import * as taskApi from '@/api/endpoints/tasks';
import * as substrateApi from '@/api/endpoints/substrates';
import type { ConfirmReminderOptions } from '@/api/endpoints/careReminders';
import type { PlantInstance, CurrentPhaseResponse, PhaseHistoryEntry, Cultivar, NutrientPlan, NutrientPlanPhaseEntry, Fertilizer, WateringLog, GrowthPhase, Species, Site, Location as SiteLocation, Slot, CareConfirmation, Substrate, SubstrateType, TaskItem } from '@/api/types';
import { getPlantDisplayName, getPlantLabel } from '@/utils/plantDisplay';
import SubstrateSelectField from '@/components/form/SubstrateSelectField';
import HaPublishToggle from '@/components/ha/HaPublishToggle';
import PlantPhotoGallery from './photos/PlantPhotoGallery';
import PlantCoverPreview from './photos/PlantCoverPreview';
import PlantDiaryTab from './diary/PlantDiaryTab';
import TaskCreateDialog from '@/pages/aufgaben/TaskCreateDialog';

const editSchema = z.object({
  plant_name: z.string().nullable(),
  cultivar_key: z.string().nullable(),
  site_key: z.string().nullable(),
  location_key: z.string().nullable(),
  slot_key: z.string().nullable(),
  substrate_key: z.string().nullable(),
  planted_on: z.string().min(1),
  container_volume_liters: z.number().min(0.1).max(500).nullable(),
});

type EditFormData = z.infer<typeof editSchema>;

/**
 * Map a data-load failure to a diagnosable ``errors.*`` i18n key, distinguishing
 * permission and not-found failures (4xx) from transport failures (network /
 * timeout) and server errors. A 422 (e.g. a pagination-cap mismatch, #614) is
 * intentionally *not* mapped to ``errors.validation`` — that key reads as "please
 * check your input", which is misleading on a read-only tab load where the user
 * has no input field to correct. It falls through to the generic
 * ``errors.loadFailed`` instead. The raw error is still logged by the caller for
 * diagnosis, so a future contract drift remains diagnosable without misdirecting
 * the end user.
 */
function resolveLoadErrorKey(error: unknown): string {
  if (isApiError(error)) {
    if (error.statusCode === 403) return 'errors.forbidden';
    if (error.statusCode === 404) return 'errors.notFound';
    if (error.statusCode >= 500) return 'errors.server';
    return 'errors.loadFailed';
  }
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED') return 'errors.networkTimeout';
    if (!error.response) return 'errors.network';
    const status = error.response.status;
    if (status === 403) return 'errors.forbidden';
    if (status === 404) return 'errors.notFound';
    if (status >= 500) return 'errors.server';
    return 'errors.loadFailed';
  }
  return 'errors.loadFailed';
}

/** Form container max width on md+ (UI-NFR-008 R-053). */
const FORM_MAX_WIDTH = 1280;
/** Reading-column max width for prose textareas (UI-NFR-008 R-054, ~70-80 chars). */
const READING_COL_MAX = 760;


export default function PlantInstanceDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const notification = useNotification();
  const { handleError } = useApiError();
  const [plant, setPlant] = useState<PlantInstance | null>(null);
  const [currentPhase, setCurrentPhase] = useState<CurrentPhaseResponse | null>(null);
  const [history, setHistory] = useState<PhaseHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [transitionOpen, setTransitionOpen] = useState(false);
  const [tagDialogOpen, setTagDialogOpen] = useState(false);
  const [labelDialogOpen, setLabelDialogOpen] = useState(false);
  // `useTabUrl` maps position to hash, so every index here is positional — the
  // `setTab(8)` calls in the info tab point at "photos" by number, not by name.
  // The diary is appended at the end (index 9) for exactly that reason:
  // inserting it earlier would silently repoint those calls at another tab.
  const [tab, setTab] = useTabUrl(['info', 'phases', 'nutrient-plan', 'watering-log', 'care', 'activity-plan', 'tasks', 'edit', 'photos', 'diary']);
  // Bumped whenever a gallery change may have altered the cover photo, so the
  // info-tab cover preview re-resolves (REQ-034 §2.3 / AC-06).
  const [coverVersion, setCoverVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [species, setSpecies] = useState<Species | null>(null);
  const [phaseSequenceKey, setPhaseSequenceKey] = useState<string | null>(null);
  const handleLifecycleLoaded = useCallback((lc: import('@/api/types').LifecycleConfig) => {
    if (lc.phase_sequence_key) {
      setPhaseSequenceKey(lc.phase_sequence_key);
    } else if (lc.species_key) {
      // Fallback: try to find phase sequence via dedicated endpoint
      import('@/api/endpoints/phaseSequences').then((api) =>
        api.getSpeciesPhaseSequence(lc.species_key).then((seq) => {
          if (seq) setPhaseSequenceKey(seq.key);
        }).catch(() => {}),
      );
    }
  }, []);
  const [cultivarList, setCultivarList] = useState<Cultivar[]>([]);

  // Watering logs state (replaces feeding events)
  const [wateringLogs, setWateringLogs] = useState<WateringLog[]>([]);
  const [wateringLogCreateOpen, setWateringLogCreateOpen] = useState(false);
  const [wateringLogChannelPreset, setWateringLogChannelPreset] = useState<ChannelPreset | undefined>(undefined);
  const wateringLogTableState = useTableLocalState({ defaultSort: { column: 'loggedAt', direction: 'desc' } });

  // Nutrient plan assignment state
  const [assignedPlan, setAssignedPlan] = useState<NutrientPlan | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [removePlanOpen, setRemovePlanOpen] = useState(false);
  const [removingPlan, setRemovingPlan] = useState(false);

  // Gantt chart state
  const [planEntries, setPlanEntries] = useState<NutrientPlanPhaseEntry[]>([]);
  const [fertilizers, setFertilizers] = useState<Fertilizer[]>([]);
  const [growthPhases, setGrowthPhases] = useState<GrowthPhase[]>([]);
  const [lifecycleKey, setLifecycleKey] = useState<string | null>(null);

  // Water mix recommended RO% per sequence_order (filled from batch endpoint)
  const [recommendedRoMap, setRecommendedRoMap] = useState<Map<number, number>>(new Map());

  // Slot picker cascade state
  const [sitesList, setSitesList] = useState<Site[]>([]);
  const [slotsList, setSlotsList] = useState<Slot[]>([]);

  // Substrate selector state
  const [substratesList, setSubstratesList] = useState<Substrate[]>([]);

  // Assigned location display (info tab)
  const [assignedSlot, setAssignedSlot] = useState<Slot | null>(null);
  const [assignedLocation, setAssignedLocation] = useState<SiteLocation | null>(null);

  // Planting run references
  const [plantRuns, setPlantRuns] = useState<plantApi.PlantRunRef[]>([]);

  // Mother instance (clonal continuation / D10) — resolved for the ancestry link
  const [motherInstance, setMotherInstance] = useState<PlantInstance | null>(null);
  // Tracks the in-flight fetch so the ancestry link can show a skeleton instead of
  // briefly flashing the raw (often UUID-like) mother_key before the readable
  // instance_id resolves.
  const [motherLoading, setMotherLoading] = useState(false);

  // Care profile state
  const [careProfile, setCareProfile] = useState<import('@/api/types').CareProfile | null>(null);

  // Watering state
  const [lastWatering, setLastWatering] = useState<CareConfirmation | null>(null);
  const [confirmingWatering, setConfirmingWatering] = useState(false);
  const [wateringDialogOpen, setWateringDialogOpen] = useState(false);
  const [nextWateringTask, setNextWateringTask] = useState<TaskItem | null>(null);
  const [plantTasks, setPlantTasks] = useState<TaskItem[]>([]);
  const [plantTasksLoading, setPlantTasksLoading] = useState(false);
  // Distinguishes "not loaded yet" from "loaded and genuinely empty" so the empty
  // state is only shown for a real ``[]`` result — never while a load is pending or
  // after a failure (#578).
  const [plantTasksLoaded, setPlantTasksLoaded] = useState(false);
  const [plantTasksError, setPlantTasksError] = useState<string | null>(null);
  // Single per-row action lock covering start/complete/skip, mirroring the task
  // queue's ``actionLoading`` so the acting row shows a spinner and its sibling
  // actions disable while a request is in flight.
  const [taskActionLoading, setTaskActionLoading] = useState<string | null>(null);
  const [taskCreateOpen, setTaskCreateOpen] = useState(false);
  const taskTableState = useTableLocalState({ defaultSort: { column: 'due_date', direction: 'asc' } });

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { isDirty },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      plant_name: null,
      cultivar_key: null,
      site_key: null,
      location_key: null,
      slot_key: null,
      substrate_key: null,
      planted_on: '',
      container_volume_liters: null,
    },
  });

  const editSiteKey = useWatch({ control, name: 'site_key' });
  const editLocationKey = useWatch({ control, name: 'location_key' });

  // `isCancelled` lets the [key]-effect abandon an in-flight load when the user
  // navigates to a sibling before it settles. Imperative refreshes (post-mutation)
  // pass the default no-op guard since they always target the current key.
  const load = async (isCancelled: () => boolean = () => false) => {
    if (!key) return;
    setLoading(true);
    try {
      const p = await plantApi.getPlantInstance(key);
      if (isCancelled()) return;
      setPlant(p);
      // Resolve the mother instance for the ancestry link (D10 clonal continuation).
      // Kicked off in the same tick as setPlant (before any further awaits) so the
      // "loading" state batches with the initial render — the raw mother_key never
      // flashes on screen before the readable instance_id (or its fallback) resolves.
      // The isCancelled guard prevents a stale mother (from a previously requested
      // sibling) from overwriting motherInstance once its response resolves late.
      if (p.mother_key) {
        setMotherLoading(true);
        plantApi.getPlantInstance(p.mother_key)
          .then((m) => { if (!isCancelled()) setMotherInstance(m); })
          .catch(() => { if (!isCancelled()) setMotherInstance(null); })
          .finally(() => { if (!isCancelled()) setMotherLoading(false); });
      } else {
        setMotherInstance(null);
        setMotherLoading(false);
      }
      let loadedSpecies: Species | null = null;
      if (p.species_key) {
        try {
          loadedSpecies = await speciesApi.getSpecies(p.species_key);
          setSpecies(loadedSpecies);
        } catch {
          setSpecies(null);
        }
        speciesApi.listCultivars(p.species_key).then(setCultivarList).catch(() => setCultivarList([]));
      }
      // Resolve site_key: prefer stored value, fall back to location → site derivation
      let resolvedSiteKey: string | null = p.site_key ?? null;
      let resolvedLocationKey: string | null = p.location_key;
      // If no location_key but slot exists, reverse-resolve from slot
      if (!resolvedLocationKey && p.slot_key) {
        try {
          const slot = await sitesApi.getSlot(p.slot_key);
          resolvedLocationKey = slot.location_key;
        } catch { /* ignore */ }
      }
      // Resolve location → site + display (also backfill site_key if not stored)
      if (resolvedLocationKey) {
        try {
          const loc = await sitesApi.getLocation(resolvedLocationKey);
          setAssignedLocation(loc);
          if (!resolvedSiteKey) resolvedSiteKey = loc.site_key;
        } catch {
          setAssignedLocation(null);
        }
        sitesApi.listSlots(resolvedLocationKey).then(setSlotsList).catch(() => setSlotsList([]));
      } else {
        setAssignedLocation(null);
      }
      // Resolve slot display
      if (p.slot_key) {
        sitesApi.getSlot(p.slot_key).then(setAssignedSlot).catch(() => setAssignedSlot(null));
      } else {
        setAssignedSlot(null);
      }
      skipLocationReset.current = true;
      skipSlotReset.current = true;
      reset({
        plant_name: p.plant_name,
        cultivar_key: p.cultivar_key,
        site_key: resolvedSiteKey,
        location_key: resolvedLocationKey,
        slot_key: p.slot_key,
        substrate_key: p.substrate_key || (p.substrate_type_override ? `_type_${p.substrate_type_override}` : null),
        planted_on: p.planted_on,
        container_volume_liters: p.container_volume_liters,
      });
      // Load planting runs for this plant
      plantApi.getPlantRuns(key).then(setPlantRuns).catch(() => setPlantRuns([]));
      try {
        const cp = await phasesApi.getCurrentPhase(key);
        setCurrentPhase(cp);
      } catch {
        // Phase control may not be configured
      }
      try {
        const h = await phasesApi.getPhaseHistory(key);
        setHistory(h);
      } catch {
        // History may be empty
      }
      // Load last watering confirmation
      try {
        const hist = await careApi.getHistory(key, 'watering');
        setLastWatering(hist.length > 0 ? hist[0] : null);
      } catch {
        setLastWatering(null);
      }
      // Load next pending watering task
      try {
        const tasks = await taskApi.listTasks(0, 50, { entity_type: 'plant_instance', entity_key: key, category: 'care_reminder', status: 'pending' });
        const wateringTask = tasks.find((t) => t.name.endsWith('— watering'));
        setNextWateringTask(wateringTask ?? null);
      } catch {
        setNextWateringTask(null);
      }
      // Load watering log history
      try {
        const wl = await wateringLogApi.getPlantWateringHistory(key);
        setWateringLogs(wl);
      } catch {
        // May not have any watering logs
      }
      // Load lifecycle growth phases for projected timeline
      try {
        const lc = await phasesApi.getLifecycleConfig(p.species_key);
        setLifecycleKey(lc.key);
        const gp = await phasesApi.listGrowthPhases(lc.key);
        setGrowthPhases(gp.sort((a, b) => a.sequence_order - b.sequence_order));
      } catch {
        setGrowthPhases([]);
      }
      // Load assigned nutrient plan + Gantt data
      // Falls back to species' default nutrient plan if no plant-specific plan assigned
      let ap = await planApi.getPlantPlan(key);
      if (!ap && loadedSpecies?.default_nutrient_plan_key) {
        try {
          ap = await planApi.fetchNutrientPlan(loadedSpecies.default_nutrient_plan_key);
        } catch {
          // Species default plan may have been deleted
        }
      }
      setAssignedPlan(ap);
      if (ap) {
        const [pe, f] = await Promise.all([
          planApi.fetchPhaseEntries(ap.key),
          fertApi.fetchFertilizers(0, 200),
        ]);
        setPlanEntries(pe);
        setFertilizers(f);
      } else {
        setPlanEntries([]);
        setFertilizers([]);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    load(() => ignore);
    return () => { ignore = true; };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load care profile when switching to Care tab
  useEffect(() => {
    if (tab === 4 && key) {
      careApi.getOrCreateProfile(key, species?.scientific_name)
        .then(setCareProfile)
        .catch(() => setCareProfile(null));
    }
  }, [tab, key, species?.scientific_name]);

  // Load every task bound to this plant instance (all categories, all statuses).
  // A dedicated ``loaded``/``error`` state pair replaces the former
  // ``plantTasks.length === 0`` guard: that guard conflated "never loaded" with
  // "genuinely empty" and swallowed every failure into the empty state, so a
  // transient error left the tab stuck on the empty CTA forever (#578).
  const loadPlantTasks = useCallback(async () => {
    if (!key) return;
    setPlantTasksLoading(true);
    setPlantTasksError(null);
    try {
      // Dedicated, pagination-free route: returns every task bound to this plant
      // instance (all categories, all statuses) sorted by due_date, matching the
      // set the active/archived split renders. The former ``listTasks(0, 500, …)``
      // 422'd because the shared list endpoint caps ``limit`` at ``le=200`` (#614).
      const tasks = await taskApi.getTasksForPlant(key);
      setPlantTasks(tasks);
      setPlantTasksLoaded(true);
    } catch (err) {
      // Surface a diagnosable, classified error instead of a blanket "load failed"
      // — and never flip ``plantTasksLoaded`` here, so the empty-state CTA stays
      // reserved for a genuine ``[]`` result and a transient failure is retryable
      // rather than masked as "no tasks" (#578).
      console.error('Failed to load plant tasks', err);
      setPlantTasksError(resolveLoadErrorKey(err));
    } finally {
      setPlantTasksLoading(false);
    }
  }, [key]);

  // Refetch whenever the Tasks tab is (re)opened — a fresh open must always reflect
  // tasks created or completed since the last visit.
  useEffect(() => {
    if (tab === 6 && key) {
      loadPlantTasks();
    }
  }, [tab, key, loadPlantTasks]);

  // Load sites + substrates when switching to Edit tab
  useEffect(() => {
    if (tab === 7) {
      sitesApi.listSites(0, 200).then(setSitesList).catch(() => setSitesList([]));
      substrateApi.listSubstrates(0, 200).then(setSubstratesList).catch(() => setSubstratesList([]));
    }
  }, [tab]);

  // Clear location when site changes (except initial load)
  const skipLocationReset = useRef(true);
  useEffect(() => {
    if (skipLocationReset.current) {
      skipLocationReset.current = false;
      return;
    }
    setValue('location_key', null);
    setSlotsList([]);
    setValue('slot_key', null, { shouldDirty: true });
  }, [editSiteKey, setValue]);

  // Load slots when location changes (except initial load)
  const skipSlotReset = useRef(true);
  useEffect(() => {
    if (skipSlotReset.current) {
      skipSlotReset.current = false;
      return;
    }
    setSlotsList([]);
    setValue('slot_key', null, { shouldDirty: true });
    if (editLocationKey) {
      sitesApi.listSlots(editLocationKey).then(setSlotsList).catch(() => setSlotsList([]));
    }
  }, [editLocationKey, setValue]);

  // Fetch recommended RO% for each phase entry when plan + site are available
  useEffect(() => {
    if (!assignedPlan?.key || !editSiteKey) {
      setRecommendedRoMap(new Map());
      return;
    }
    planApi.fetchWaterMixRecommendationsBatch(assignedPlan.key, editSiteKey)
      .then((result) => {
        const map = new Map<number, number>();
        for (const rec of result.recommendations) {
          map.set(rec.sequence_order, rec.recommendation.recommended_ro_percent);
        }
        setRecommendedRoMap(map);
      })
      .catch(() => setRecommendedRoMap(new Map()));
  }, [assignedPlan?.key, editSiteKey]);

  const handleConfirmWatering = async (options?: ConfirmReminderOptions) => {
    if (!key) return;
    try {
      setConfirmingWatering(true);
      const confirmation = await careApi.confirmReminder(key, 'watering', options);
      setLastWatering(confirmation);
      setWateringDialogOpen(false);
      notification.success(t('pages.plantInstances.wateringConfirmed'));
      // Refresh next watering task (confirming creates a new one)
      try {
        const tasks = await taskApi.listTasks(0, 50, { entity_type: 'plant_instance', entity_key: key, category: 'care_reminder', status: 'pending' });
        const wt = tasks.find((t) => t.name.endsWith('— watering'));
        setNextWateringTask(wt ?? null);
      } catch {
        setNextWateringTask(null);
      }
    } catch (err) {
      handleError(err);
    } finally {
      setConfirmingWatering(false);
    }
  };

  const [removing, setRemoving] = useState(false);
  const onRemove = async (body: import('@/api/types').RemovePlantRequest) => {
    if (!key) return;
    try {
      setRemoving(true);
      const updated = await plantApi.removePlantInstance(key, body);
      setPlant(updated);
      notification.success(t('pages.plantInstances.remove'));
      setRemoveOpen(false);
    } catch (err) {
      handleError(err);
    } finally {
      setRemoving(false);
    }
  };

  // Per-row task actions — same trio the task queue offers (start ▶ / complete ✓ /
  // skip ⏭). Each refetches the tab data afterwards so the row moves between the
  // active and archived sections and any backend-spawned follow-up (e.g. the next
  // watering reminder) shows up. Notifications reuse the queue's i18n keys.
  const handleStartTask = async (taskKey: string) => {
    try {
      setTaskActionLoading(taskKey);
      await taskApi.startTask(taskKey);
      notification.success(t('pages.tasks.taskStarted'));
      await loadPlantTasks();
    } catch (err) {
      handleError(err);
    } finally {
      setTaskActionLoading(null);
    }
  };

  const handleCompleteTask = async (taskKey: string) => {
    try {
      setTaskActionLoading(taskKey);
      await taskApi.completeTask(taskKey, {});
      notification.success(t('pages.tasks.taskCompleted'));
      await loadPlantTasks();
    } catch (err) {
      handleError(err);
    } finally {
      setTaskActionLoading(null);
    }
  };

  const handleSkipTask = async (taskKey: string) => {
    try {
      setTaskActionLoading(taskKey);
      await taskApi.skipTask(taskKey);
      notification.success(t('pages.tasks.taskSkipped'));
      await loadPlantTasks();
    } catch (err) {
      handleError(err);
    } finally {
      setTaskActionLoading(null);
    }
  };

  const onEditSubmit = async (data: EditFormData) => {
    if (!key || !plant) return;
    try {
      setSaving(true);
      const { substrate_key: rawSubstrateKey, ...payload } = data;
      // Type-only fallback keys start with '_type_' — don't send as substrate_key
      const isTypeOnly = rawSubstrateKey?.startsWith('_type_');
      const substrateKey = isTypeOnly ? null : (rawSubstrateKey || null);
      const selectedSubstrate = substrateKey ? substratesList.find((s) => s.key === substrateKey) : null;
      const typeOverride = isTypeOnly
        ? rawSubstrateKey!.replace('_type_', '') as SubstrateType
        : (selectedSubstrate?.type ?? null);
      await plantApi.updatePlantInstance(key, {
        instance_id: plant.instance_id,
        species_key: plant.species_key,
        ...payload,
        // The "—" option on every key select carries value '', so an unset
        // reference reaches here as an empty string. '' is not a key: the API
        // refuses it with 422 (min_length=1) precisely because it used to be
        // stored as a dangling reference. null is how this API says "none".
        cultivar_key: payload.cultivar_key || null,
        site_key: payload.site_key || null,
        location_key: payload.location_key || null,
        slot_key: payload.slot_key || null,
        substrate_key: substrateKey,
        substrate_type_override: typeOverride,
      });
      notification.success(t('common.save'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  const openAssignDialog = () => {
    setAssignDialogOpen(true);
  };

  const onAssignPlan = async (planKey: string) => {
    if (!key) return;
    await planApi.assignPlanToPlant(key, { plan_key: planKey, assigned_by: '' });
    notification.success(t('pages.nutrientPlans.assignPlan'));
    load();
  };

  const onRemovePlan = async () => {
    if (!key) return;
    setRemovingPlan(true);
    try {
      await planApi.removePlantPlan(key);
      notification.success(t('pages.nutrientPlans.removePlan'));
      setAssignedPlan(null);
      setRemovePlanOpen(false);
    } catch (err) {
      handleError(err);
    } finally {
      setRemovingPlan(false);
    }
  };

  // Derive actual current phase from phase history (more reliable than plant document)
  const actualPhase = useMemo(() => {
    const active = history.find((h) => h.exited_at == null);
    if (active) return { name: active.phase_name, startedAt: active.entered_at };
    // Fallback to plant document
    if (plant?.current_phase) return { name: plant.current_phase, startedAt: plant.current_phase_started_at ?? null };
    return null;
  }, [history, plant?.current_phase, plant?.current_phase_started_at]);

  const currentWeek = useMemo(() => {
    // Phase-based calculation: weeks since phase transition + plan entry's week_start
    if (actualPhase?.startedAt && planEntries.length > 0) {
      const phaseStart = new Date(actualPhase.startedAt);
      if (!isNaN(phaseStart.getTime())) {
        const now = new Date();
        now.setHours(0, 0, 0, 0);
        phaseStart.setHours(0, 0, 0, 0);
        const diffMs = now.getTime() - phaseStart.getTime();
        if (diffMs >= 0) {
          const weeksInPhase = Math.floor(diffMs / (7 * 24 * 60 * 60 * 1000)) + 1;
          const sorted = [...planEntries].sort((a, b) => a.sequence_order - b.sequence_order);
          const phaseEntry = sorted.find((e) => e.phase_name === actualPhase.name);
          if (phaseEntry) {
            return phaseEntry.week_start + weeksInPhase - 1;
          }
        }
      }
    }
    // Fallback: weeks since planting
    return plant?.planted_on ? computeCurrentWeek(plant.planted_on) : undefined;
  }, [plant?.planted_on, actualPhase, planEntries]);

  const monthName = (m: number) =>
    new Date(2024, m - 1).toLocaleString(i18n.language, { month: 'short' });

  const frostChipColor = (sensitivity: string | null): 'success' | 'warning' | 'error' | 'default' => {
    if (!sensitivity) return 'default';
    if (sensitivity === 'hardy' || sensitivity === 'very_hardy') return 'success';
    if (sensitivity === 'moderate') return 'warning';
    if (sensitivity === 'sensitive') return 'error';
    return 'default';
  };

  const assignedCultivar = useMemo(
    () => plant?.cultivar_key ? cultivarList.find((c) => c.key === plant.cultivar_key) ?? null : null,
    [plant?.cultivar_key, cultivarList],
  );

  // Current growth phase definition (from lifecycle config)
  const currentGrowthPhase = useMemo(
    () => actualPhase?.name ? growthPhases.find((g) => g.name === actualPhase.name) ?? null : null,
    [actualPhase?.name, growthPhases],
  );

  // Effective watering interval for current phase (cultivar override > phase default)
  const effectiveWateringInterval = useMemo(() => {
    if (!currentGrowthPhase) return null;
    const cultivarOverride = assignedCultivar?.phase_watering_overrides?.[currentGrowthPhase.name];
    if (cultivarOverride != null) return { value: cultivarOverride, source: 'cultivar' as const };
    if (currentGrowthPhase.watering_interval_days != null) return { value: currentGrowthPhase.watering_interval_days, source: 'phase' as const };
    return null;
  }, [currentGrowthPhase, assignedCultivar]);

  // Estimated harvest date: planted_on + sum(all growth phase durations).
  // `harvestDateIsPredictable` answers the *narrow* question — species yields
  // something at all (shared with the readiness panel below, #963) AND there is a
  // single terminal harvest to count down to. Perennials and lifecycles without a
  // harvest phase fail only the second half, which is why the two guards are
  // deliberately not the same predicate; see ./harvestability.ts.
  const estimatedHarvest = useMemo(() => {
    if (!plant?.planted_on || plant.removed_on) return null;
    if (!harvestDateIsPredictable({ species, currentPhase, growthPhases })) return null;
    const totalDays = growthPhases.reduce((sum, gp) => sum + gp.typical_duration_days, 0);
    if (totalDays === 0) return null;
    const planted = new Date(plant.planted_on);
    const harvestDate = new Date(planted.getTime() + totalDays * 86400000);
    const daysRemaining = Math.ceil((harvestDate.getTime() - Date.now()) / 86400000);
    return { date: harvestDate, daysRemaining };
  }, [plant?.planted_on, plant?.removed_on, species, growthPhases, currentPhase]);

  // Active nutrient plan phase entry for the current week (handles perennial cycle restarts)
  const activePhaseEntry = useMemo(() => {
    if (!assignedPlan || planEntries.length === 0 || currentWeek == null) return null;
    const sorted = [...planEntries].sort((a, b) => a.sequence_order - b.sequence_order);

    const currentPhaseName = actualPhase?.name;

    // 1. Direct match: phase name + week range
    const byPhase = sorted.find(
      (e) => e.phase_name === currentPhaseName && currentWeek >= e.week_start && currentWeek <= e.week_end,
    );
    if (byPhase) return byPhase;

    // 2. Direct match: week range only
    const byWeek = sorted.find((e) => currentWeek >= e.week_start && currentWeek <= e.week_end);
    if (byWeek) return byWeek;

    // 3. Cycle restart for perennial plans
    const restartSeq = assignedPlan.cycle_restart_from_sequence;
    if (restartSeq == null) return null;

    const recurring = sorted.filter((e) => e.sequence_order >= restartSeq);
    if (recurring.length === 0) return null;

    const cycleStart = recurring[0].week_start;
    const cycleEnd = recurring[recurring.length - 1].week_end;
    const cycleLen = cycleEnd - cycleStart + 1;
    if (cycleLen <= 0 || currentWeek <= cycleEnd) return null;

    const offset = (currentWeek - cycleEnd - 1) % cycleLen;
    const effectiveWeek = cycleStart + offset;

    const byPhaseCycle = recurring.find(
      (e) => e.phase_name === currentPhaseName && effectiveWeek >= e.week_start && effectiveWeek <= e.week_end,
    );
    if (byPhaseCycle) return byPhaseCycle;

    return recurring.find((e) => effectiveWeek >= e.week_start && effectiveWeek <= e.week_end) ?? null;
  }, [assignedPlan, planEntries, currentWeek, actualPhase?.name]);

  // For perennial plans: compute cycle metadata + normalized Gantt data
  const perennialCycleInfo = useMemo(() => {
    const restartSeq = assignedPlan?.cycle_restart_from_sequence;
    if (restartSeq == null || planEntries.length === 0) return null;

    const sorted = [...planEntries].sort((a, b) => a.sequence_order - b.sequence_order);
    const oneTime = sorted.filter((e) => e.sequence_order < restartSeq);
    const recurring = sorted.filter((e) => e.sequence_order >= restartSeq);
    if (recurring.length === 0) return null;

    const cycleStart = recurring[0].week_start;
    const cycleEnd = recurring[recurring.length - 1].week_end;
    const cycleLen = cycleEnd - cycleStart + 1;

    // Compute cycle number and mapped week
    let cycleNumber = 1;
    let mappedWeek: number | undefined = currentWeek;
    if (currentWeek != null) {
      if (currentWeek < cycleStart) {
        cycleNumber = 0; // still in one-time entries
        mappedWeek = undefined;
      } else if (currentWeek <= cycleEnd) {
        cycleNumber = 1;
        mappedWeek = currentWeek - cycleStart + 1;
      } else if (cycleLen > 0) {
        const pastEnd = currentWeek - cycleEnd;
        cycleNumber = Math.floor((pastEnd - 1) / cycleLen) + 2;
        const offset = (pastEnd - 1) % cycleLen;
        mappedWeek = offset + 1;
      }
    }

    return {
      oneTimeEntries: oneTime,
      recurringEntries: recurring,
      cycleStart,
      cycleEnd,
      cycleLen,
      cycleNumber,
      mappedWeek,
    };
  }, [assignedPlan, planEntries, currentWeek]);

  // Gantt data: for perennial plans show cycle view, for linear plans show everything
  // Appends a "next cycle preview" so users see fertilization resumes after dormancy
  const ganttCycleData = useMemo(() => {
    if (!perennialCycleInfo) {
      return { entries: planEntries, currentWeek };
    }

    const { recurringEntries, cycleStart, cycleLen, mappedWeek } = perennialCycleInfo;

    // Normalize entries so cycle starts at week 1
    const normalizedEntries = recurringEntries.map((e) => ({
      ...e,
      week_start: e.week_start - cycleStart + 1,
      week_end: e.week_end - cycleStart + 1,
    }));

    // Append next-cycle preview: duplicate recurring entries shifted by cycleLen
    const previewEntries = recurringEntries.map((e) => ({
      ...e,
      key: `${e.key}_preview`,
      week_start: e.week_start - cycleStart + 1 + cycleLen,
      week_end: e.week_end - cycleStart + 1 + cycleLen,
    }));

    return {
      entries: [...normalizedEntries, ...previewEntries] as typeof planEntries,
      currentWeek: mappedWeek,
    };
  }, [perennialCycleInfo, planEntries, currentWeek]);

  // Current ISO week for the seasonal calendar Gantt
  const currentIsoWeek = useMemo(() => {
    const now = new Date();
    const jan4 = new Date(now.getFullYear(), 0, 4);
    const dayOfYear = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime()) / 86400000) + 1;
    const jan4DayOfWeek = jan4.getDay() || 7;
    return Math.ceil((dayOfYear + jan4DayOfWeek - 1) / 7);
  }, []);

  // Map recurring entries to 52-week calendar year with wrapping for month-based display
  const calendarSeasonalEntries = useMemo(() => {
    if (!perennialCycleInfo) return [];
    const { recurringEntries } = perennialCycleInfo;
    if (recurringEntries.length === 0) return [];

    const cycleStart = recurringEntries[0].week_start;
    const cycleEnd = recurringEntries[recurringEntries.length - 1].week_end;
    const cycleLen = cycleEnd - cycleStart + 1;

    if (cycleLen <= 52 && cycleStart <= 52 && cycleEnd <= 52) {
      return recurringEntries;
    }

    const result: typeof recurringEntries = [];
    for (const e of recurringEntries) {
      if (e.week_end <= 52) {
        result.push(e);
      } else if (e.week_start <= 52) {
        // Crosses year boundary — keep as single entry (week_end > 52)
        result.push(e);
      } else {
        result.push({ ...e, week_start: e.week_start - 52, week_end: e.week_end - 52 });
      }
    }
    return result.sort((a, b) => a.week_start - b.week_start);
  }, [perennialCycleInfo]);

  // Resolve dosage presets from active phase entry for the confirm dialog
  const dosagePresets = useMemo((): { dosages: DosagePreset[]; targetEc?: number; targetPh?: number } | null => {
    if (!activePhaseEntry) return null;
    const dosages: DosagePreset[] = [];
    let targetEc: number | undefined;
    let targetPh: number | undefined;
    for (const channel of activePhaseEntry.delivery_channels) {
      if (!channel.enabled) continue;
      if (channel.target_ec_ms != null && targetEc == null) targetEc = channel.target_ec_ms;
      if (channel.target_ph != null && targetPh == null) targetPh = channel.target_ph;
      for (const d of channel.fertilizer_dosages) {
        if (!d.optional) {
          dosages.push({ fertilizer_key: d.fertilizer_key, ml_per_liter: d.ml_per_liter });
        }
      }
    }
    return dosages.length > 0 ? { dosages, targetEc, targetPh } : null;
  }, [activePhaseEntry]);

  // Recommended watering volume from backend (phase + species + substrate + container)
  const { suggestion: wateringVolume } = useWateringVolumeSuggestion(key);

  // Helper: format a due date as a relative label
  const formatRelativeDueDate = (dueDate: string | null): string => {
    if (!dueDate) return '—';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    const diffDays = Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return t('pages.plantInstances.taskDueDateToday');
    if (diffDays === 1) return t('pages.plantInstances.taskDueDateTomorrow');
    if (diffDays > 1) return t('pages.plantInstances.taskDueDateInDays', { count: diffDays });
    if (diffDays === -1) return t('pages.plantInstances.taskDueDateOverdueToday');
    return t('pages.plantInstances.taskDueDateOverdue', { count: Math.abs(diffDays) });
  };

  // Split tasks into active (pending/in_progress) and archived (completed/skipped/cancelled).
  // Memoised so the derived arrays keep a stable reference across renders that do not
  // change ``plantTasks`` (avoids re-sorting and re-rendering the DataTables).
  const activeTasks = useMemo(() => {
    const ACTIVE_STATUSES = new Set(['pending', 'in_progress']);
    return plantTasks
      .filter((t) => ACTIVE_STATUSES.has(t.status))
      .sort((a, b) => {
        // in_progress before pending
        const statusOrder: Record<string, number> = { in_progress: 0, pending: 1 };
        const sA = statusOrder[a.status] ?? 2;
        const sB = statusOrder[b.status] ?? 2;
        if (sA !== sB) return sA - sB;
        // then by due date ascending (null last)
        if (!a.due_date && !b.due_date) return 0;
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
      });
  }, [plantTasks]);
  const archivedTasks = useMemo(
    () => plantTasks.filter((t) => !['pending', 'in_progress'].includes(t.status)),
    [plantTasks],
  );
  // REQ-006 FreeStyle (#1082): the open machine-generated tasks bound to this
  // instance — derived work a producer (e.g. a Goose analysis pipeline) surfaced
  // for this plant. Highlighted separately so it is not lost among manual tasks.
  const openFreestyleTasks = useMemo(
    () => activeTasks.filter((t) => t.origin && t.origin !== 'user'),
    [activeTasks],
  );

  // Midnight boundary for overdue comparisons, stable within a render pass.
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  // Count overdue active tasks (due date in the past)
  const overdueCount = useMemo(
    () => activeTasks.filter((t) => t.due_date && new Date(t.due_date) < today).length,
    [activeTasks, today],
  );

  // Status chip color mapping
  const taskStatusColor = (status: string): 'success' | 'warning' | 'info' | 'error' | 'default' => {
    if (status === 'completed') return 'success';
    if (status === 'in_progress') return 'info';
    if (status === 'pending') return 'warning';
    if (status === 'cancelled' || status === 'skipped') return 'default';
    return 'default';
  };

  // Status icon mapping
  const TaskStatusIcon = ({ status }: { status: string }) => {
    if (status === 'completed') return <TaskAltIcon fontSize="small" color="success" />;
    if (status === 'in_progress') return <HourglassEmptyIcon fontSize="small" color="info" />;
    if (status === 'pending') return <PendingIcon fontSize="small" color="warning" />;
    return null;
  };

  // Per-row action trio for the active tasks table + mobile cards. Gated by status
  // exactly like the task queue (``isActionable``): start ▶ only for a pending row;
  // complete ✓ and skip ⏭ for any active (pending / in_progress) row. Archived rows
  // (completed / skipped / cancelled) are non-actionable and render no actions.
  // ``stopPropagation`` on the wrapper and each button keeps the row-click navigate
  // from firing when an action is pressed.
  const renderTaskActions = (row: TaskItem) => {
    const isActive = row.status === 'pending' || row.status === 'in_progress';
    if (!isActive) return null;
    const isPending = row.status === 'pending';
    const isLoading = taskActionLoading === row.key;
    return (
      <Box
        sx={{ display: 'flex', alignItems: 'center', gap: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        {isPending && (
          <Tooltip title={t('pages.tasks.startTask')}>
            <span>
              <IconButton
                size="small"
                onClick={(e) => { e.stopPropagation(); handleStartTask(row.key); }}
                disabled={isLoading}
                aria-label={t('pages.tasks.startTask')}
                data-testid={`task-start-${row.key}`}
                sx={{ minWidth: 40, minHeight: 40 }}
              >
                {isLoading ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon fontSize="small" />}
              </IconButton>
            </span>
          </Tooltip>
        )}
        <Tooltip title={t('pages.tasks.completeTask')}>
          <span>
            <IconButton
              size="small"
              color="success"
              onClick={(e) => { e.stopPropagation(); handleCompleteTask(row.key); }}
              disabled={isLoading}
              aria-label={t('pages.tasks.completeTask')}
              data-testid={`task-complete-${row.key}`}
              sx={{ minWidth: 40, minHeight: 40 }}
            >
              {isLoading
                ? <CircularProgress size={16} color="inherit" data-testid={`task-complete-${row.key}-spinner`} />
                : <CheckIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={t('pages.tasks.skipTask')}>
          <span>
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); handleSkipTask(row.key); }}
              disabled={isLoading}
              aria-label={t('pages.tasks.skipTask')}
              data-testid={`task-skip-${row.key}`}
              sx={{ minWidth: 40, minHeight: 40 }}
            >
              {isLoading ? <CircularProgress size={16} color="inherit" /> : <SkipNextIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
      </Box>
    );
  };

  if (loading) return <LoadingSkeleton variant="form" />;
  if (error) return <ErrorDisplay error={error} onRetry={() => navigate(-1)} />;

  return (
    <Box data-testid="plant-instance-detail-page">
      <UnsavedChangesGuard dirty={isDirty} />
      <PageTitle
        title={plant ? getPlantLabel(plant, species, assignedCultivar) : t('entities.plantInstance')}
        action={
          /* This header is the reason R-024 exists: five controls used to wrap,
             and the destructive "remove" button was the one pushed off a 393px
             viewport (UI-NFR-001 R-005/R-006). On `xs` the phase transition
             stays — the lifecycle action this page is built around — and tag,
             label and the destructive remove become a deliberate two-tap choice
             instead of something met while scrolling sideways. `PestScanButton`
             stays visible alongside it (see below), so this is two controls on
             `xs`, not one. */
          <PageHeaderActions
            /* `PestScanButton` renders its own control (camera permissions,
               capture flow) and cannot become a menu entry without being taken
               apart. It stays visible on `xs` too, which is a conscious
               deviation from "exactly one visible action" — the alternative was
               rebuilding an unrelated component inside this change. */
            extra={key ? <PestScanButton plantKey={key} /> : undefined}
            primary={{
              label: t('pages.phases.transition'),
              icon: <SwapHorizIcon />,
              disabled: !!plant?.removed_on,
              testId: 'transition-button',
              onClick: () => setTransitionOpen(true),
            }}
            secondary={[
              {
                label: t('pages.plantInstances.tag.button'),
                icon: <LabelIcon />,
                testId: 'tag-button',
                onClick: () => setTagDialogOpen(true),
              },
              {
                label: t('print.printLabelsShort'),
                icon: <QrCode2Icon />,
                tooltip: t('print.printLabels'),
                testId: 'label-button',
                onClick: () => setLabelDialogOpen(true),
              },
              {
                label: t('pages.plantInstances.remove'),
                icon: <RemoveCircleIcon />,
                color: 'error' as const,
                disabled: !!plant?.removed_on,
                testId: 'remove-button',
                onClick: () => setRemoveOpen(true),
              },
            ]}
          />
        }
      />

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3 }}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
      >
        <Tab label={t('pages.plantInstances.info')} />
        <Tab label={t('pages.plantingRuns.tabPhases')} data-testid="phases-tab" />
        <Tab label={t('entities.nutrientPlan')} />
        <Tab label={t('entities.wateringLog')} />
        <Tab label={t('nav.pflege')} />
        <Tab label={t('pages.activityPlan.tabTitle')} data-testid="activity-plan-tab" />
        <Tab label={t('pages.plantInstances.taskHistoryTab')} data-testid="tasks-tab" />
        <Tab label={t('common.edit')} data-testid="edit-tab" />
        <Tab label={t('pages.plantPhotos.tabTitle')} data-testid="photos-tab" />
        <Tab label={t('pages.plantDiary.tabTitle')} data-testid="diary-tab" />
      </Tabs>

      {tab === 0 && (
        <>
          {/* Cover photo preview (REQ-034 §2.3 / AC-06) — links to the gallery tab. */}
          {plant && key && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <Box
                component="button"
                type="button"
                onClick={() => setTab(8)}
                aria-label={t('pages.plantPhotos.tabTitle')}
                sx={{
                  p: 0,
                  border: 'none',
                  bgcolor: 'transparent',
                  cursor: 'pointer',
                  borderRadius: 1,
                  lineHeight: 0,
                }}
                data-testid="info-cover-preview"
              >
                <PlantCoverPreview key={coverVersion} plantInstanceKey={key} size={72} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {t('pages.plantPhotos.coverLabel')}
                </Typography>
                <Link
                  component="button"
                  type="button"
                  variant="body2"
                  underline="hover"
                  onClick={() => setTab(8)}
                  data-testid="info-open-gallery"
                >
                  {t('pages.plantPhotos.openGallery')}
                </Link>
              </Box>
            </Box>
          )}
          {plant && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('pages.plantInstances.infoIntro')}
            </Typography>
          )}
          {/* Compact summary bar */}
          {plant && (
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)', md: 'repeat(auto-fit, minmax(150px, 1fr))' },
                gap: { xs: 1.5, sm: 2 },
                mb: 3,
                p: 2,
                bgcolor: 'background.paper',
                borderRadius: 1,
                border: 1,
                borderColor: 'divider',
              }}
              data-testid="plant-info-card"
            >
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('pages.plantInstances.instanceId')}
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>{plant.instance_id}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('pages.plantInstances.plantedOn')}
                </Typography>
                <Typography variant="body1">
                  {new Date(plant.planted_on).toLocaleDateString(i18n.language)}
                </Typography>
              </Box>
              {estimatedHarvest && (
                <Box data-testid="estimated-harvest">
                  <Typography variant="caption" color="text.secondary">
                    {t('pages.plantInstances.estimatedHarvest')}
                  </Typography>
                  <Tooltip
                    title={t('pages.plantInstances.estimatedHarvestTooltip')}
                    arrow
                    enterTouchDelay={0}
                  >
                    <Box
                      sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}
                      tabIndex={0}
                      role="note"
                      aria-label={t('pages.plantInstances.estimatedHarvestTooltip')}
                    >
                      <EventAvailableIcon
                        sx={{
                          fontSize: 18,
                          color: estimatedHarvest.daysRemaining < 0
                            ? 'error.main'
                            : estimatedHarvest.daysRemaining <= 7
                              ? 'warning.main'
                              : 'text.secondary',
                        }}
                      />
                      <Typography
                        variant="body1"
                        color={
                          estimatedHarvest.daysRemaining < 0
                            ? 'error.main'
                            : estimatedHarvest.daysRemaining <= 7
                              // `.dark`: #ed6c02 is 3.11:1 on white, and this is
                              // the date itself, not the icon above it.
                              ? 'warning.dark'
                              : undefined
                        } sx={{ fontWeight: 500 }}>
                        {estimatedHarvest.date.toLocaleDateString(i18n.language)}
                        {' '}
                        ({estimatedHarvest.daysRemaining === 0
                          ? t('pages.plantInstances.harvestToday')
                          : estimatedHarvest.daysRemaining > 0
                            ? t('pages.plantInstances.daysRemaining', { count: estimatedHarvest.daysRemaining })
                            : t('pages.plantInstances.daysOverdue', { count: Math.abs(estimatedHarvest.daysRemaining) })
                        })
                      </Typography>
                    </Box>
                  </Tooltip>
                </Box>
              )}
              {assignedLocation && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {assignedSlot ? t('entities.slot') : t('entities.location')}
                  </Typography>
                  <Typography variant="body1">
                    <Link component={RouterLink} to={`/standorte/locations/${assignedLocation.key}`} underline="hover">
                      {assignedLocation.name}
                    </Link>
                    {assignedSlot && (
                      <>
                        {' / '}
                        <Link component={RouterLink} to={`/standorte/slots/${assignedSlot.key}`} underline="hover">
                          {assignedSlot.slot_id}
                        </Link>
                      </>
                    )}
                  </Typography>
                </Box>
              )}
              {plant.substrate_type_override && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('pages.plantInstances.substrate')}
                  </Typography>
                  <Typography variant="body1">
                    <Chip label={t(`enums.substrateType.${plant.substrate_type_override}`)} size="small" variant="outlined" />
                  </Typography>
                </Box>
              )}
              {plantRuns.length > 0 && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('entities.plantingRun')}
                  </Typography>
                  {plantRuns.map((r) => (
                    <Link
                      key={r.key}
                      component={RouterLink}
                      to={`/durchlaeufe/planting-runs/${r.key}`}
                      underline="hover"
                      sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                    >
                      {r.name}
                      <Chip label={t(`enums.plantingRunStatus.${r.status}`)} size="small" variant="outlined" />
                    </Link>
                  ))}
                </Box>
              )}
              {plant.mother_key && (
                <Box data-testid="ancestry-mother">
                  <Tooltip
                    title={t('pages.plantInstances.descendedFromTooltip')}
                    arrow
                    enterTouchDelay={0}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      tabIndex={0}
                      role="note"
                      aria-label={t('pages.plantInstances.descendedFromTooltip')}
                      sx={{ cursor: 'help', textDecoration: 'underline dotted' }}
                    >
                      {t('pages.plantInstances.descendedFrom')}
                    </Typography>
                  </Tooltip>
                  <Typography variant="body1" sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.5 }}>
                    <AccountTreeIcon fontSize="small" color="action" aria-hidden="true" sx={{ mt: '2px' }} />
                    <Link
                      component={RouterLink}
                      to={`/pflanzen/plant-instances/${plant.mother_key}`}
                      underline="hover"
                      data-testid="ancestry-mother-link"
                      sx={{ wordBreak: 'break-word' }}
                    >
                      {motherLoading
                        ? <Skeleton variant="text" width={110} data-testid="ancestry-mother-skeleton" />
                        : (motherInstance?.instance_id ?? plant.mother_key)}
                    </Link>
                  </Typography>
                </Box>
              )}
              {plant.removed_on && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('pages.plantInstances.removedOn')}
                  </Typography>
                  <Typography variant="body1" color="error">
                    {new Date(plant.removed_on).toLocaleDateString(i18n.language)}
                  </Typography>
                </Box>
              )}
              <Box data-testid="phase-info-card">
                <Typography variant="caption" color="text.secondary">
                  {t('pages.phases.current')}
                </Typography>
                <Box>
                  <Chip
                    label={plant.current_phase
                      ? t(`enums.phaseName.${plant.current_phase}`, { defaultValue: plant.current_phase })
                      : '—'}
                    color="primary"
                    size="small"
                    data-testid="current-phase"
                  />
                </Box>
              </Box>
              {currentPhase && (
                <>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t('pages.phases.daysInPhase')}
                    </Typography>
                    <Typography variant="body1">{currentPhase.days_in_phase}</Typography>
                  </Box>
                  {currentPhase.next_phase && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('pages.phases.nextPhase')}
                      </Typography>
                      <Typography variant="body1">{currentPhase.next_phase}</Typography>
                    </Box>
                  )}
                </>
              )}
            </Box>
          )}

          {/* Watering card */}
          {plant && !plant.removed_on && (
            <Card sx={{ mb: 3 }} data-testid="watering-card">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', mb: (dosagePresets || wateringVolume) ? 1.5 : 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <OpacityIcon color="primary" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {t('pages.plantInstances.lastWatered')}
                        </Typography>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {lastWatering
                            ? new Date(lastWatering.confirmed_at).toLocaleDateString(i18n.language)
                            : '—'}
                        </Typography>
                      </Box>
                    </Box>
                    {(() => {
                      // Prefer task due_date, fallback to lastWatering + interval
                      const nextDate = nextWateringTask?.due_date
                        ? new Date(nextWateringTask.due_date)
                        : lastWatering && effectiveWateringInterval
                          ? new Date(new Date(lastWatering.confirmed_at).getTime() + effectiveWateringInterval.value * 86400000)
                          : null;
                      if (!nextDate) return null;
                      const days = Math.ceil((nextDate.getTime() - Date.now()) / 86400000);
                      const daysLabel =
                        days === 0 ? t('pages.plantInstances.today')
                        : days === 1 ? t('pages.plantInstances.tomorrow')
                        : days > 1 ? t('pages.plantInstances.inDays', { count: days })
                        : t('pages.plantInstances.overdue');
                      const isOverdue = days < 0;
                      return (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <TodayIcon color={isOverdue ? 'error' : 'info'} />
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              {t('pages.plantInstances.nextWatering')}
                            </Typography>
                            <Typography variant="body1" color={isOverdue ? 'error.main' : undefined} sx={{ fontWeight: 500 }}>
                              {nextWateringTask?.due_date ? (
                                <Link
                                  component={RouterLink}
                                  to={`/aufgaben/tasks/${nextWateringTask.key}`}
                                  underline="hover"
                                >
                                  {nextDate.toLocaleDateString(i18n.language)} ({daysLabel})
                                </Link>
                              ) : (
                                <>{nextDate.toLocaleDateString(i18n.language)} ({daysLabel})</>
                              )}
                            </Typography>
                          </Box>
                        </Box>
                      );
                    })()}
                    {effectiveWateringInterval && (
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {t('pages.plantInstances.wateringInterval')}
                        </Typography>
                        <Typography variant="body1">
                          {effectiveWateringInterval.value} {t('common.days')}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  <Button
                    variant="contained"
                    color="success"
                    startIcon={<CheckCircleOutlineIcon />}
                    onClick={() => setWateringDialogOpen(true)}
                    disabled={confirmingWatering}
                    data-testid="confirm-watering-button"
                  >
                    {t('pages.plantInstances.confirmWatering')}
                  </Button>
                </Box>

                {/* Phase-specific watering hints */}
                {(dosagePresets || wateringVolume) && (
                  <>
                    <Divider />
                    <Box sx={{ mt: 1.5, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                      {/* Water targets + volume */}
                      <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
                        {activePhaseEntry && (
                          <Chip
                            label={activePhaseEntry.phase_name ? t(`enums.phaseName.${activePhaseEntry.phase_name}`, activePhaseEntry.phase_name) : ''}
                            size="small"
                            color="info"
                            variant="filled"
                          />
                        )}
                        {dosagePresets?.targetEc != null && (
                          <Tooltip title={t('pages.plantInstances.ecTooltip')} arrow enterTouchDelay={0}>
                            <Chip label={`EC ${dosagePresets.targetEc} mS/cm`} size="small" variant="outlined" />
                          </Tooltip>
                        )}
                        {dosagePresets?.targetPh != null && (
                          <Tooltip title={t('pages.plantInstances.phTooltip')} arrow enterTouchDelay={0}>
                            <Chip label={`pH ${dosagePresets.targetPh}`} size="small" variant="outlined" />
                          </Tooltip>
                        )}
                        {wateringVolume && (
                          <Chip
                            label={`${wateringVolume.liters} L`}
                            size="small"
                            variant="outlined"
                            title={wateringVolume.hint}
                          />
                        )}
                        {wateringVolume?.raw.water_only && (
                          <Tooltip title={t('pages.plantInstances.phaseRegime.waterOnlyTooltip')} arrow enterTouchDelay={0}>
                            <Box
                              component="span"
                              sx={{ display: 'inline-flex', cursor: 'help' }}
                              tabIndex={0}
                              role="note"
                              aria-label={t('pages.plantInstances.phaseRegime.waterOnlyTooltip')}
                            >
                              <Chip
                                icon={<OpacityIcon />}
                                label={t('pages.plantInstances.phaseRegime.waterOnly')}
                                size="small"
                                color="info"
                                variant="filled"
                              />
                            </Box>
                          </Tooltip>
                        )}
                      </Box>

                      {/* Fertilizer dosages */}
                      {dosagePresets && dosagePresets.dosages.length > 0 && (
                        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                          {dosagePresets.dosages.map((d) => {
                            const fert = fertilizers.find((f) => f.key === d.fertilizer_key);
                            return (
                              <Chip
                                key={d.fertilizer_key}
                                icon={<ScienceIcon />}
                                label={`${fert?.product_name ?? d.fertilizer_key}: ${d.ml_per_liter} ml/L`}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            );
                          })}
                        </Box>
                      )}

                      {/* Phase-regime + sensor helper text (REQ-003 E7) */}
                      {wateringVolume && (wateringVolume.raw.water_only || wateringVolume.raw.source === 'sensor_soil_moisture') && (
                        <Box sx={{ width: '100%' }}>
                          {wateringVolume.raw.water_only && wateringVolume.raw.regime_note && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              {wateringVolume.raw.regime_note}
                            </Typography>
                          )}
                          {wateringVolume.raw.source === 'sensor_soil_moisture' && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              {t('pages.plantInstances.phaseRegime.sensorAdjusted')}
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Current phase profile card */}
          {(currentGrowthPhase || activePhaseEntry) && (
            <Card sx={{ mb: 3 }} data-testid="phase-profile-card">
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1.5 }}>
                  {t('pages.plantInstances.phaseProfile')}
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
                  {/* Growth phase info */}
                  {currentGrowthPhase && (
                    <>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {t('pages.phases.typicalDuration')}
                        </Typography>
                        <Typography variant="body1">
                          {currentGrowthPhase.typical_duration_days} {t('pages.plantInstances.days')}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          {t('pages.phases.stressTolerance')}
                        </Typography>
                        <Typography variant="body1">
                          {t(`enums.stressTolerance.${currentGrowthPhase.stress_tolerance}`)}
                        </Typography>
                      </Box>
                    </>
                  )}

                  {/* Nutrient plan phase entry info */}
                  {activePhaseEntry && (
                    <>
                      <Box>
                        <Tooltip title={t('pages.plantInstances.npkTooltip')} arrow enterTouchDelay={0}>
                          <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help', textDecoration: 'underline dotted' }}>
                            {t('pages.nutrientPlans.npkRatio')}
                          </Typography>
                        </Tooltip>
                        <Typography variant="body1" sx={{ fontWeight: 500 }}>
                          {activePhaseEntry.npk_ratio[0]}-{activePhaseEntry.npk_ratio[1]}-{activePhaseEntry.npk_ratio[2]}
                        </Typography>
                      </Box>
                      {(activePhaseEntry.calcium_ppm != null || activePhaseEntry.magnesium_ppm != null) && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            {t('pages.plantInstances.caMgPpm')}
                          </Typography>
                          <Typography variant="body1">
                            {activePhaseEntry.calcium_ppm ?? '—'} / {activePhaseEntry.magnesium_ppm ?? '—'}
                          </Typography>
                        </Box>
                      )}
                    </>
                  )}
                </Box>

                {/* Delivery channels with target EC/pH and fertilizer dosages */}
                {activePhaseEntry && activePhaseEntry.delivery_channels.length > 0 && (
                  <>
                    <Divider sx={{ my: 1.5 }} />
                    <DeliveryChannelAccordion
                      channels={activePhaseEntry.delivery_channels}
                      fertilizers={fertilizers}
                      onLogWatering={(ch) => {
                        const volumeLiters = ch.method_params
                          ? ch.method_params.method === 'drench'
                            ? ch.method_params.volume_per_feeding_liters
                            : ch.method_params.method === 'foliar'
                              ? ch.method_params.volume_per_spray_liters
                              : null
                          : null;
                        setWateringLogChannelPreset({
                          channelId: ch.channel_id,
                          channelLabel: ch.label || ch.channel_id,
                          nutrientPlanKey: assignedPlan!.key,
                          applicationMethod: ch.application_method as 'fertigation' | 'drench' | 'foliar' | 'top_dress',
                          targetEcMs: ch.target_ec_ms,
                          targetPh: ch.target_ph,
                          fertilizers: ch.fertilizer_dosages
                            .filter((d) => !d.optional)
                            .sort((a, b) => a.mixing_order - b.mixing_order)
                            .map((d) => ({ fertilizer_key: d.fertilizer_key, ml_per_liter: d.ml_per_liter })),
                          volumeLiters,
                        });
                        setWateringLogCreateOpen(true);
                      }}
                    />
                  </>
                )}

                {/* Hint when no nutrient plan assigned */}
                {!assignedPlan && currentGrowthPhase && (
                  <>
                    <Divider sx={{ my: 1.5 }} />
                    <Alert severity="info" variant="outlined" sx={{ py: 0 }}>
                      {t('pages.plantInstances.noNutrientPlanHint')}
                    </Alert>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Harvest readiness (REQ-007 §3 "Reife-Visualisierung" / §6 DoD).
              Placed with the plant's other live-status cards — after the phase
              profile, before the static species/cultivar reference cards —
              because it answers the same question as the summary bar's
              "voraussichtliche Ernte": where is this plant in its run right now.
              Hidden once the plant is removed/harvested: readiness is a forecast
              towards an event that has already happened, mirroring the watering
              card's `!plant.removed_on` guard directly above.

              Hidden as well when the species yields nothing (#963). "Not removed
              yet" used to be the only question asked, so a *Dracaena reflexa* was
              offered a trichome/Brix observation it can never have — while the
              summary bar above already declined to predict a harvest date for it.
              Both displays now consult `plantCanBeHarvested`, so they can no
              longer contradict each other about the same plant. Only the species
              axis applies here: unlike the date estimate, a ripeness assessment
              needs no phase durations, so a crop with an incomplete lifecycle
              keeps its panel. The guard fails open on an unknown species — see
              ./harvestability.ts for why. */}
          {plant && key && !plant.removed_on && plantCanBeHarvested(species) && (
            <HarvestReadinessSection plantKey={key} />
          )}

          {/* Species & Cultivar cards */}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: assignedCultivar ? '1fr 1fr' : '1fr' }, gap: 3 }}>
            {species && (
              <Card data-testid="species-card">
                <CardContent>
                  {/* Header with name + link */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box>
                      <Typography variant="h6" sx={{ fontStyle: 'italic' }}>{species.scientific_name}</Typography>
                      {species.common_names.length > 0 && (
                        <Typography variant="body2" color="text.secondary">
                          {species.common_names.join(', ')}
                        </Typography>
                      )}
                    </Box>
                    <Link component={RouterLink} to={`/stammdaten/species/${species.key}`} underline="hover" sx={{ whiteSpace: 'nowrap', ml: 2 }}>
                      {t('pages.plantInstances.viewSpecies')}
                    </Link>
                  </Box>

                  <Divider sx={{ my: 1.5 }} />

                  {/* Properties in 2-column grid */}
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, rowGap: 0.5, columnGap: 2 }}>
                    {species.growth_habit && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.growthHabit')}: </Typography>
                        {t(`enums.growthHabit.${species.growth_habit}`)}
                      </Typography>
                    )}
                    {species.root_type && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.rootType')}: </Typography>
                        {t(`enums.rootType.${species.root_type}`)}
                      </Typography>
                    )}
                    {species.mature_height_cm && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.matureHeightCm')}: </Typography>
                        {species.mature_height_cm} cm
                      </Typography>
                    )}
                    {species.mature_width_cm && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.matureWidthCm')}: </Typography>
                        {species.mature_width_cm} cm
                      </Typography>
                    )}
                    {species.spacing_cm && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.spacingCm')}: </Typography>
                        {species.spacing_cm} cm
                      </Typography>
                    )}
                    {species.recommended_container_volume_l && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.species.recommendedContainerVolumeL')}: </Typography>
                        {species.recommended_container_volume_l} L
                      </Typography>
                    )}
                  </Box>

                  {/* Suitability + frost as compact chips */}
                  {(species.frost_sensitivity || species.indoor_suitable || species.balcony_suitable ||
                    species.container_suitable || species.greenhouse_recommended || species.support_required) && (
                    <>
                      <Divider sx={{ my: 1.5 }} />
                      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                        {species.frost_sensitivity && (
                          <Chip
                            label={`${t('pages.species.frostSensitivity')}: ${t(`enums.frostTolerance.${species.frost_sensitivity}`)}`}
                            size="small"
                            color={frostChipColor(species.frost_sensitivity)}
                          />
                        )}
                        {species.indoor_suitable && (
                          <Chip
                            label={`${t('pages.species.indoorSuitable')}: ${t(`enums.suitability.${species.indoor_suitable}`)}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {species.balcony_suitable && (
                          <Chip
                            label={`${t('pages.species.balconySuitable')}: ${t(`enums.suitability.${species.balcony_suitable}`)}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {species.container_suitable && (
                          <Chip
                            label={`${t('pages.species.containerSuitable')}: ${t(`enums.suitability.${species.container_suitable}`)}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {species.greenhouse_recommended && (
                          <Chip label={t('pages.species.greenhouseRecommended')} size="small" variant="outlined" />
                        )}
                        {species.support_required && (
                          <Chip label={t('pages.species.supportRequired')} size="small" variant="outlined" />
                        )}
                      </Box>
                    </>
                  )}

                  {/* Calendar months */}
                  {(species.harvest_months.length > 0 || species.bloom_months.length > 0 || species.direct_sow_months.length > 0) && (
                    <>
                      <Divider sx={{ my: 1.5 }} />
                      {species.harvest_months.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5, mb: 0.75 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
                            {t('pages.species.harvestMonths')}:
                          </Typography>
                          {species.harvest_months.map((m) => (
                            <Chip key={m} label={monthName(m)} size="small" />
                          ))}
                        </Box>
                      )}
                      {species.bloom_months.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5, mb: 0.75 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
                            {t('pages.species.bloomMonths')}:
                          </Typography>
                          {species.bloom_months.map((m) => (
                            <Chip key={m} label={monthName(m)} size="small" />
                          ))}
                        </Box>
                      )}
                      {species.direct_sow_months.length > 0 && (
                        <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
                          <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
                            {t('pages.species.directSowMonths')}:
                          </Typography>
                          {species.direct_sow_months.map((m) => (
                            <Chip key={m} label={monthName(m)} size="small" />
                          ))}
                        </Box>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {assignedCultivar && (
              <Card data-testid="cultivar-card">
                <CardContent>
                  {/* Header with name + link */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6">{assignedCultivar.name}</Typography>
                    <Link
                      component={RouterLink}
                      to={`/stammdaten/species/${species?.key}/cultivars/${assignedCultivar.key}`}
                      underline="hover"
                      sx={{ whiteSpace: 'nowrap', ml: 2 }}
                    >
                      {t('pages.plantInstances.viewCultivar')}
                    </Link>
                  </Box>

                  <Divider sx={{ my: 1.5 }} />

                  {/* Properties in 2-column grid */}
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, rowGap: 0.5, columnGap: 2 }}>
                    {assignedCultivar.breeder && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.cultivars.breeder')}: </Typography>
                        {assignedCultivar.breeder}{assignedCultivar.breeding_year ? ` (${assignedCultivar.breeding_year})` : ''}
                      </Typography>
                    )}
                    {assignedCultivar.days_to_maturity != null && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.cultivars.daysToMaturity')}: </Typography>
                        {assignedCultivar.days_to_maturity}
                      </Typography>
                    )}
                    {assignedCultivar.patent_status && (
                      <Typography variant="body2">
                        <Typography component="span" variant="body2" color="text.secondary">{t('pages.cultivars.patentStatus')}: </Typography>
                        {assignedCultivar.patent_status}
                      </Typography>
                    )}
                  </Box>

                  {/* Traits */}
                  {assignedCultivar.traits.length > 0 && (
                    <>
                      <Divider sx={{ my: 1.5 }} />
                      <Typography variant="caption" color="text.secondary">{t('pages.cultivars.traits')}</Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                        {assignedCultivar.traits.map((trait) => (
                          <Chip key={trait} label={t(`enums.plantTrait.${trait}`)} size="small" />
                        ))}
                      </Box>
                    </>
                  )}

                  {/* Disease resistances */}
                  {assignedCultivar.disease_resistances.length > 0 && (
                    <>
                      <Divider sx={{ my: 1.5 }} />
                      <Typography variant="caption" color="text.secondary">{t('pages.cultivars.diseaseResistances')}</Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                        {assignedCultivar.disease_resistances.map((r) => (
                          <Chip key={r} label={r} size="small" variant="outlined" />
                        ))}
                      </Box>
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </Box>
          {plant && key && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <HaPublishToggle entityType="plant" entityKey={key} />
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Tab 1: Phases */}
      {tab === 1 && plant && key && (
        <>
          <Box data-testid="phases-tab-content">
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                {t('pages.plantingRuns.phaseTimeline')}
              </Typography>
              <Button
                startIcon={<SwapHorizIcon />}
                variant="outlined"
                size="small"
                onClick={() => setTransitionOpen(true)}
                disabled={!!plant.removed_on}
              >
                {t('pages.phases.transition')}
              </Button>
            </Box>
            <PlantPhaseTimeline plant={plant} history={history} speciesName={species?.scientific_name} onLifecycleLoaded={handleLifecycleLoaded} />
            {phaseSequenceKey && (
              <Box sx={{ mt: 2, mb: 1 }}>
                <Button
                  component={RouterLink}
                  to={`/phasen/ablaeufe/${phaseSequenceKey}`}
                  variant="outlined"
                  size="small"
                  startIcon={<AccountTreeIcon />}
                >
                  {t('pages.phaseSequences.phaseSequence')}
                </Button>
              </Box>
            )}
            <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
              {t('pages.phases.history')}
            </Typography>
            <PhaseHistoryTable plantKey={key} onChanged={load} />
          </Box>
          {currentPhase?.phase_key && (
            <ProfilesSection
              phaseKey={currentPhase.phase_key}
              phaseName={currentPhase.phase}
              readOnly
            />
          )}
        </>
      )}

      {/* Tab 2: Nutrient Plan */}
      {tab === 2 && (
        <Box>
          {assignedPlan ? (
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <ScienceIcon />
                <Link component={RouterLink} to={`/duengung/plans/${assignedPlan.key}`} underline="hover">
                  {assignedPlan.name}
                </Link>
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<ScienceIcon />}
                  onClick={openAssignDialog}
                  disabled={!!plant?.removed_on}
                >
                  {t('pages.nutrientPlans.assignPlan')}
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<DeleteIcon />}
                  onClick={() => setRemovePlanOpen(true)}
                >
                  {t('pages.nutrientPlans.removePlan')}
                </Button>
              </Box>
            </Box>
          ) : (
            <Box>
              <Alert severity="info" sx={{ mb: 2 }}>
                {t('pages.nutrientPlans.noPlanAssigned')}
              </Alert>
              <Button
                variant="contained"
                startIcon={<ScienceIcon />}
                onClick={openAssignDialog}
                disabled={!!plant?.removed_on}
              >
                {t('pages.nutrientPlans.assignPlan')}
              </Button>
            </Box>
          )}

          {/* Hint when water config is missing — RO% in Gantt will be empty */}
          {assignedPlan && editSiteKey && recommendedRoMap.size === 0 && (() => {
            const selectedSite = sitesList.find((s) => s.key === editSiteKey);
            return (
              <Alert severity="info" sx={{ mt: 2 }}>
                {t('pages.nutrientPlans.waterMix.noWaterConfig', { siteName: selectedSite?.name ?? '' })}
                {selectedSite && (
                  <Link component={RouterLink} to={`/standorte/sites/${selectedSite.key}`} sx={{ ml: 0.5 }}>
                    {t('pages.nutrientPlans.waterMix.configureSite')}
                  </Link>
                )}
              </Alert>
            );
          })()}

          {/* Non-perennial: PhaseGanttChart overview + PhaseDetailGantt per group */}
          {!perennialCycleInfo && planEntries.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <PhaseGanttChart
                entries={ganttCycleData.entries}
                fertilizers={fertilizers}
                title=""
                currentWeek={ganttCycleData.currentWeek}
              />
              {(() => {
                const sorted = [...ganttCycleData.entries].sort((a, b) => a.sequence_order - b.sequence_order);
                const vegPhases = new Set(['vegetative', 'seedling', 'germination']);
                const flowerPhases = new Set(['flowering', 'flushing', 'harvest']);
                const vegEntries = sorted.filter((e) => vegPhases.has(e.phase_name));
                const flowerEntries = sorted.filter((e) => flowerPhases.has(e.phase_name));
                const cw = ganttCycleData.currentWeek;
                const phase = actualPhase?.name;
                const vegWeek = phase && vegPhases.has(phase) ? cw : undefined;
                const flowerWeek = phase && flowerPhases.has(phase) ? cw : undefined;
                return (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                    {vegEntries.length > 0 && (
                      <PhaseDetailGantt
                        entries={vegEntries}
                        fertilizers={fertilizers}
                        title={t('pages.gantt.vegetativeDetail')}
                        currentWeek={vegWeek}
                        recommendedRoMap={recommendedRoMap}
                      />
                    )}
                    {flowerEntries.length > 0 && (
                      <PhaseDetailGantt
                        entries={flowerEntries}
                        fertilizers={fertilizers}
                        title={t('pages.gantt.floweringDetail')}
                        currentWeek={flowerWeek}
                        recommendedRoMap={recommendedRoMap}
                      />
                    )}
                  </Box>
                );
              })()}
            </Box>
          )}

          {/* Perennial: Saisonaler Zyklus (matching duengung/plans detail layout) */}
          {perennialCycleInfo && calendarSeasonalEntries.length > 0 && (
            <Box sx={{ mt: 2 }}>
              {/* Seasonal cycle header */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <RepeatIcon fontSize="small" color="action" />
                <Typography variant="h6">
                  {t('pages.nutrientPlans.seasonalCycleSection')}
                </Typography>
                <Chip
                  label={`${perennialCycleInfo.cycleLen} ${t('pages.nutrientPlans.weeksPerCycle')}`}
                  size="small"
                  variant="outlined"
                />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {perennialCycleInfo.recurringEntries.map((e) => t(`enums.phaseName.${e.phase_name}`)).join(' → ')}
              </Typography>

              {/* PhaseGanttChart: 52-week calendar with month headers */}
              <PhaseGanttChart
                entries={calendarSeasonalEntries}
                fertilizers={fertilizers}
                title=""
                currentWeek={currentIsoWeek}
                totalWeeksOverride={52}
                showMonthHeaders
                compactMode
              />

            </Box>
          )}
        </Box>
      )}

      {/* Tab 3: Watering Log */}
      {tab === 3 && (
        <Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('pages.plantInstances.wateringLogIntro')}
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">{t('entities.wateringLog')}</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setWateringLogCreateOpen(true)}
              disabled={!!plant?.removed_on}
              data-testid="create-watering-log-button"
            >
              {t('pages.wateringLogs.create')}
            </Button>
          </Box>
          <DataTable<WateringLog>
            columns={[
              {
                id: 'loggedAt',
                label: t('pages.wateringLogs.loggedAt'),
                render: (r) => r.logged_at ? new Date(r.logged_at).toLocaleString() : '—',
                searchValue: (r) => r.logged_at ? new Date(r.logged_at).toLocaleString() : '',
              },
              {
                id: 'applicationMethod',
                label: t('pages.wateringLogs.applicationMethod'),
                render: (r) => t(`enums.applicationMethod.${r.application_method}`),
                searchValue: (r) => t(`enums.applicationMethod.${r.application_method}`),
              },
              {
                id: 'volume',
                label: t('pages.wateringLogs.volumeLiters'),
                render: (r) => `${r.volume_liters} L`,
                align: 'right',
              },
              {
                id: 'isSupplemental',
                label: t('pages.wateringLogs.isSupplemental'),
                render: (r) => r.is_supplemental ? (
                  <Chip label={t('common.yes')} size="small" color="info" />
                ) : null,
              },
              {
                id: 'ecAfter',
                label: t('pages.wateringLogs.ecAfter'),
                render: (r) => r.ec_after != null ? `${r.ec_after} mS/cm` : '—',
                searchValue: (r) => r.ec_after != null ? String(r.ec_after) : '',
                align: 'right',
              },
            ]}
            rows={wateringLogs}
            getRowKey={(r) => r.key}
            onRowClick={(r) => navigate(`/giessprotokoll/${r.key}`)}
            tableState={wateringLogTableState}
            ariaLabel={t('entities.wateringLog')}
            mobileCardRenderer={(r) => (
              <MobileCard
                title={r.logged_at ? new Date(r.logged_at).toLocaleString() : '—'}
                titleId="loggedAt"
                subtitle={t(`enums.applicationMethod.${r.application_method}`)}
                subtitleId="applicationMethod"
                fields={[
                  { id: 'volume', label: t('pages.wateringLogs.volumeLiters'), value: `${r.volume_liters} L` },
                  // Emitted unconditionally: as a conditional chip the column
                  // was simply absent for an ordinary watering, so "the
                  // supplemental column is empty" was unreadable rather than
                  // empty. A present-but-empty field says the same thing the
                  // desktop `<td>` says.
                  {
                    id: 'isSupplemental',
                    label: t('pages.wateringLogs.isSupplemental'),
                    value: r.is_supplemental
                      ? <Chip component="span" label={t('common.yes')} size="small" color="info" />
                      : '',
                  },
                  ...(r.ec_after != null
                    ? [{ id: 'ecAfter', label: t('pages.wateringLogs.ecAfter'), value: String(r.ec_after) }]
                    : []),
                ]}
              />
            )}
          />
        </Box>
      )}

      {/* Tab 4: Care Profile */}
      {tab === 4 && (
        <Box sx={{ maxWidth: 1280 }}>
          {careProfile ? (
            <>
              {/* Care-tab profile editing happens inline (#577): the form is always
                  editable directly on the page instead of behind a modal. The
                  care-style chip stays visible as the section header; the per-task
                  toggles inside the form already communicate the on/off state that
                  the former read-only summary duplicated. An intro line spells out
                  that edits still require an explicit save — the inline placement
                  has no modal boundary to signal that on its own. */}
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.pflege.careTabIntro')}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <Chip
                  label={t(`enums.careStyle.${careProfile.care_style}`)}
                  size="small"
                  variant="outlined"
                />
              </Box>
              <CareProfileForm
                embedded
                profile={careProfile}
                onUpdated={(updated) => setCareProfile(updated)}
              />
            </>
          ) : (
            <LoadingSkeleton variant="form" />
          )}

          {/* REQ-047 §4.3 — auto-materialised overwintering profile with the
              optional per-field override / reset-to-automatic affordances. */}
          {key && (
            <Box sx={{ mt: 3 }}>
              {/* key={key}: remount on plant change so a slow in-flight profile
                  read for the previous plant can never render here (belt-and-
                  suspenders alongside the slice-level stale-response guard). */}
              <OverwinteringSection key={key} plantKey={key} />
            </Box>
          )}
        </Box>
      )}

      {/* Tab 5: Activity Plan */}
      {tab === 5 && plant && (
        <ActivityPlanTab
          speciesKey={plant.species_key}
          plantKey={key}
          currentPhaseName={actualPhase?.name}
        />
      )}

      {/* Tab 6: Tasks */}
      {tab === 6 && (
        // `aria-busy` covers both the initial load and any silent background refetch
        // (e.g. after quick-completing a task) so assistive tech is aware content may
        // still change, even where the DOM keeps showing the previous data (UI-NFR-002
        // R-011). `showInitialSkeleton` treats "never loaded yet" as loading too — closes
        // the one-frame gap between switching to this tab and the fetch effect actually
        // flipping `plantTasksLoading`, where the populated branch would otherwise flash
        // an empty 0/0/0 summary bar before the skeleton appears.
        <Box aria-busy={plantTasksLoading}>
          {(() => {
            const showInitialSkeleton = !plantTasksLoaded && !plantTasksError;
            if (showInitialSkeleton) return <LoadingSkeleton variant="table" />;
            if (plantTasksError) return <ErrorDisplay error={plantTasksError} onRetry={loadPlantTasks} />;
            if (plantTasks.length === 0) {
              return (
                <Box>
                  <EmptyState
                    message={t('pages.plantInstances.noTasks')}
                    description={t('pages.plantInstances.noTasksDesc')}
                    actionLabel={t('pages.plantInstances.noTasksCreateCta')}
                    onAction={() => setTaskCreateOpen(true)}
                  />
                  <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => navigate('/aufgaben/queue')}
                      data-testid="empty-state-queue-link"
                    >
                      {t('pages.plantInstances.noTasksCta')}
                    </Button>
                  </Box>
                </Box>
              );
            }
            return (
            <>
              {/* Background-refetch indicator (e.g. after quick-completing a task, or
                  reopening the tab): keeps the already-loaded table visible instead of
                  swapping it out for a full skeleton on every refresh — avoids the
                  flicker a repeated full-page skeleton would cause, while still
                  satisfying UI-NFR-004 R-020 (every async action needs a visible
                  indicator) via a lightweight top progress bar rather than a second,
                  competing spinner. */}
              {plantTasksLoading && (
                <LinearProgress sx={{ mb: 1.5 }} data-testid="tasks-refetch-progress" />
              )}
              {/* Summary stats bar. The counts are an asserted outcome of
                  TC-004-092 (View 3), so the bar and each chip carry a stable
                  test id — the labels themselves are translated and the MUI
                  class names are framework-generated, neither of which is an
                  addressable hook. */}
              <Box
                data-testid="task-summary-bar"
                sx={{
                  display: 'flex',
                  gap: 1.5,
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  mb: 2,
                  p: 1.5,
                  bgcolor: 'background.paper',
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                }}
              >
                {overdueCount > 0 && (
                  <Chip
                    icon={<WarningAmberIcon />}
                    label={`${t('pages.plantInstances.taskTabSummaryOverdue')}: ${overdueCount}`}
                    size="small"
                    color="error"
                    variant="outlined"
                    data-testid="task-summary-overdue"
                  />
                )}
                <Chip
                  label={`${t('pages.plantInstances.taskTabSummaryActive')}: ${activeTasks.length}`}
                  size="small"
                  color={activeTasks.length > 0 ? 'warning' : 'default'}
                  variant="outlined"
                  data-testid="task-summary-active"
                />
                <Chip
                  label={`${t('pages.plantInstances.taskTabSummaryDone')}: ${archivedTasks.length}`}
                  size="small"
                  color="default"
                  variant="outlined"
                  data-testid="task-summary-done"
                />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => setTaskCreateOpen(true)}
                  sx={{ ml: 'auto' }}
                  data-testid="plant-task-create-button"
                >
                  {t('pages.plantInstances.noTasksCreateCta')}
                </Button>
              </Box>

              {/* REQ-006 FreeStyle (#1082): open machine-generated tasks for this
                  instance, surfaced above the manual work so derived tasks from an
                  analysis pipeline are not overlooked. */}
              {openFreestyleTasks.length > 0 && (
                <Card
                  variant="outlined"
                  sx={{ mb: 3, borderColor: 'secondary.main' }}
                  data-testid="plant-freestyle-tasks-section"
                >
                  <CardContent>
                    <Typography
                      variant="subtitle2"
                      sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 0.75 }}
                    >
                      <SmartToyIcon fontSize="small" color="secondary" />
                      {t('pages.tasks.openFreestyleTasks')}
                    </Typography>
                    <Stack spacing={1}>
                      {openFreestyleTasks.map((task) => (
                        <Box
                          key={task.key}
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            flexWrap: 'wrap',
                            justifyContent: 'space-between',
                          }}
                          data-testid={`freestyle-task-${task.key}`}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                            <TaskStatusIcon status={task.status} />
                            <Link
                              component={RouterLink}
                              to={`/aufgaben/tasks/${task.key}`}
                              underline="hover"
                              variant="body2"
                              sx={{ fontWeight: 500, minWidth: 0 }}
                            >
                              {(i18n.language === 'de' && task.name_de) ? task.name_de : task.name}
                            </Link>
                            <TaskOriginBadge origin={task.origin} testId={`freestyle-badge-${task.key}`} />
                          </Box>
                          {task.due_date && (
                            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                              {new Date(task.due_date).toLocaleDateString()}
                            </Typography>
                          )}
                        </Box>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {/* Active tasks section */}
              {activeTasks.length > 0 && (
                <Box sx={{ mb: 3 }} data-testid="plant-tasks-active-section">
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    {t('pages.plantInstances.taskTabActiveSection')}
                  </Typography>
                  <DataTable<TaskItem>
                    columns={[
                      {
                        id: 'status',
                        label: t('common.status'),
                        render: (row) => (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                            <TaskStatusIcon status={row.status} />
                            <Chip
                              size="small"
                              label={t(`enums.taskStatus.${row.status}`, { defaultValue: row.status })}
                              color={taskStatusColor(row.status)}
                              variant="filled"
                            />
                          </Box>
                        ),
                        searchValue: (row) => t(`enums.taskStatus.${row.status}`, { defaultValue: row.status }),
                      },
                      {
                        id: 'name',
                        label: t('common.name'),
                        render: (row) => (
                          <Link component={RouterLink} to={`/aufgaben/tasks/${row.key}`} underline="hover" onClick={(e) => e.stopPropagation()}>
                            {row.name}
                          </Link>
                        ),
                        searchValue: (row) => row.name,
                      },
                      {
                        id: 'category',
                        label: t('pages.tasks.category'),
                        render: (row) => (
                          <Chip
                            size="small"
                            label={t(`enums.taskCategory.${row.category}`, { defaultValue: row.category })}
                            variant="outlined"
                          />
                        ),
                        searchValue: (row) => t(`enums.taskCategory.${row.category}`, { defaultValue: row.category }),
                        hideBelowBreakpoint: 'md',
                      },
                      {
                        id: 'due_date',
                        label: t('pages.tasks.dueDate'),
                        render: (row) => {
                          const relative = formatRelativeDueDate(row.due_date);
                          const isOverdue = row.due_date && new Date(row.due_date) < today;
                          return (
                            <Typography
                              variant="body2"
                              color={isOverdue ? 'error' : 'text.primary'} sx={{ fontWeight: isOverdue ? 600 : undefined }}>
                              {relative}
                            </Typography>
                          );
                        },
                        searchValue: (row) => row.due_date ?? '',
                      },
                      {
                        id: 'priority',
                        label: t('pages.tasks.priority'),
                        render: (row) => (
                          <Chip
                            size="small"
                            label={t(`enums.taskPriority.${row.priority}`, { defaultValue: row.priority })}
                            color={row.priority === 'critical' ? 'error' : row.priority === 'high' ? 'warning' : 'default'}
                            variant="outlined"
                          />
                        ),
                        searchValue: (row) => t(`enums.taskPriority.${row.priority}`, { defaultValue: row.priority }),
                        hideBelowBreakpoint: 'md',
                      },
                      {
                        id: 'actions',
                        label: '',
                        render: (row) => renderTaskActions(row),
                        width: 132,
                      },
                    ]}
                    rows={activeTasks}
                    getRowKey={(row) => row.key}
                    onRowClick={(row) => navigate(`/aufgaben/tasks/${row.key}`)}
                    tableState={taskTableState}
                    ariaLabel={t('pages.plantInstances.taskTabActiveSection')}
                    sectionTestId="plant-tasks-active"
                    searchable
                    mobileCardRenderer={(row) => (
                      <MobileCard
                        title={row.name}
                        subtitle={formatRelativeDueDate(row.due_date)}
                        trailing={renderTaskActions(row)}
                        chips={[
                          {
                            id: 'status',
                            content: (
                              <Chip
                                size="small"
                                label={t(`enums.taskStatus.${row.status}`, { defaultValue: row.status })}
                                color={taskStatusColor(row.status)}
                                variant="filled"
                              />
                            ),
                          },
                          {
                            id: 'category',
                            content: (
                              <Chip
                                size="small"
                                label={t(`enums.taskCategory.${row.category}`, { defaultValue: row.category })}
                                variant="outlined"
                              />
                            ),
                          },
                        ]}
                        fields={[
                          { id: 'priority', label: t('pages.tasks.priority'), value: t(`enums.taskPriority.${row.priority}`, { defaultValue: row.priority }) },
                        ]}
                      />
                    )}
                  />
                </Box>
              )}

              {/* Archived tasks section */}
              {archivedTasks.length > 0 && (
                <Box data-testid="plant-tasks-done-section">
                  <Divider sx={{ mb: 2 }} />
                  <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                    {t('pages.plantInstances.taskTabDoneSection')}
                  </Typography>
                  <DataTable<TaskItem>
                    columns={[
                      {
                        id: 'status',
                        label: t('common.status'),
                        render: (row) => (
                          <Chip
                            size="small"
                            label={t(`enums.taskStatus.${row.status}`, { defaultValue: row.status })}
                            color={taskStatusColor(row.status)}
                            variant="outlined"
                          />
                        ),
                        searchValue: (row) => t(`enums.taskStatus.${row.status}`, { defaultValue: row.status }),
                      },
                      {
                        id: 'name',
                        label: t('common.name'),
                        render: (row) => (
                          <Link component={RouterLink} to={`/aufgaben/tasks/${row.key}`} underline="hover" onClick={(e) => e.stopPropagation()}>
                            {row.name}
                          </Link>
                        ),
                        searchValue: (row) => row.name,
                      },
                      {
                        id: 'category',
                        label: t('pages.tasks.category'),
                        render: (row) => (
                          <Chip
                            size="small"
                            label={t(`enums.taskCategory.${row.category}`, { defaultValue: row.category })}
                            variant="outlined"
                          />
                        ),
                        searchValue: (row) => t(`enums.taskCategory.${row.category}`, { defaultValue: row.category }),
                        hideBelowBreakpoint: 'md',
                      },
                      {
                        id: 'completed_at',
                        label: t('pages.tasks.completedAt'),
                        render: (row) => row.completed_at
                          ? new Date(row.completed_at).toLocaleDateString(i18n.language === 'de' ? 'de-DE' : 'en-US')
                          : '—',
                        searchValue: (row) => row.completed_at ?? '',
                        hideBelowBreakpoint: 'md',
                      },
                    ]}
                    rows={archivedTasks}
                    getRowKey={(row) => row.key}
                    onRowClick={(row) => navigate(`/aufgaben/tasks/${row.key}`)}
                    ariaLabel={t('pages.plantInstances.taskTabDoneSection')}
                    sectionTestId="plant-tasks-done"
                    searchable
                    mobileCardRenderer={(row) => (
                      <MobileCard
                        title={row.name}
                        subtitle={row.completed_at
                          ? new Date(row.completed_at).toLocaleDateString(i18n.language === 'de' ? 'de-DE' : 'en-US')
                          : undefined}
                        chips={[
                          {
                            id: 'status',
                            content: (
                              <Chip
                                size="small"
                                label={t(`enums.taskStatus.${row.status}`, { defaultValue: row.status })}
                                color={taskStatusColor(row.status)}
                                variant="outlined"
                              />
                            ),
                          },
                          {
                            id: 'category',
                            content: (
                              <Chip
                                size="small"
                                label={t(`enums.taskCategory.${row.category}`, { defaultValue: row.category })}
                                variant="outlined"
                              />
                            ),
                          },
                        ]}
                      />
                    )}
                  />
                </Box>
              )}
            </>
            );
          })()}
          {key && (
            <TaskCreateDialog
              open={taskCreateOpen}
              onClose={() => setTaskCreateOpen(false)}
              presetEntityKey={key}
              hideEntitySelect
              presetEntityLabel={plant ? getPlantLabel(plant, species, assignedCultivar) : null}
              onCreated={() => {
                setTaskCreateOpen(false);
                loadPlantTasks();
              }}
            />
          )}
        </Box>
      )}

      {/* Tab 7: Edit */}
      {tab === 7 && (
        <Form onSubmit={handleSubmit(onEditSubmit)} sx={{ maxWidth: FORM_MAX_WIDTH, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Typography variant="body2" color="text.secondary">
            {t('pages.plantInstances.editIntro')}
          </Typography>

          {/* UI-NFR-008 R-061: Master-detail layout — left column = General (master,
              capped at reading width), right column = compact Planting Setup panel.
              Location stays full-width below to give the LocationTreeSelect (R-057d
              dynamic-height tree) the room it needs (R-058). */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: `minmax(0, ${READING_COL_MAX}px) 1fr` },
              gap: 4,
              alignItems: 'start',
            }}
          >
            {/* Panel 1: General (master column) */}
            <Card variant="outlined">
              <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
                <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                  {t('pages.plantInstances.sectionGeneral')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t('pages.plantInstances.sectionGeneralDesc')}
                </Typography>
                <FormRow>
                  <FormTextField name="plant_name" control={control} label={t('pages.plantInstances.plantName')} helperText={t('pages.plantInstances.plantNameHelper')} autoFocus />
                  <FormSelectField
                    name="cultivar_key"
                    control={control}
                    label={t('pages.plantInstances.cultivarKey')}
                    helperText={t('pages.plantInstances.cultivarKeyHelper')}
                    options={[
                      { value: '', label: '—' },
                      ...cultivarList.map((c) => ({ value: c.key, label: c.name })),
                    ]}
                  />
                </FormRow>
              </CardContent>
            </Card>

            {/* Detail column: Planting Setup (compact, R-057) */}
            <Card variant="outlined">
              <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
                <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                  {t('pages.plantInstances.sectionSetup')}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t('pages.plantInstances.sectionSetupDesc')}
                </Typography>
                <FormRow>
                  <FormNumberField
                    name="container_volume_liters"
                    control={control}
                    label={t('pages.plantInstances.containerVolumeLiters')}
                    helperText={t('pages.plantInstances.containerVolumeLitersHelper')}
                    min={0.1}
                    max={500}
                    suffix="L"
                  />
                  <SubstrateSelectField
                    name="substrate_key"
                    control={control}
                    label={t('pages.plantInstances.substrate')}
                    helperText={t('pages.plantInstances.substrateHelper')}
                    substrates={substratesList}
                  />
                </FormRow>
                <FormTextField name="planted_on" control={control} label={t('pages.plantInstances.plantedOn')} helperText={t('pages.plantInstances.plantedOnHelper')} type="date" required />
              </CardContent>
            </Card>
          </Box>

          {/* Panel 3: Location (full-width below master-detail, R-058 — shared cascade) */}
          <LocationAssignmentSection
            control={control}
            sites={sitesList}
            slots={slotsList}
            variant="card"
          />

          <Typography variant="caption" color="text.secondary">* {t('common.required')}</Typography>
          <FormActions onCancel={() => setTab(0)} loading={saving} />
        </Form>
      )}

      {/* Tab 8: Photos (REQ-034 §2.3) */}
      {tab === 8 && key && (
        <PlantPhotoGallery
          plantInstanceKey={key}
          readOnly={!!plant?.removed_on}
          onCoverChange={() => setCoverVersion((v) => v + 1)}
          speciesKey={plant?.species_key}
          scientificName={species?.scientific_name}
        />
      )}

      {/* Tab 9: Diary (REQ-051 §6.1) */}
      {tab === 9 && key && (
        <PlantDiaryTab plantInstanceKey={key} readOnly={!!plant?.removed_on} />
      )}

      <TerminationDialog
        open={removeOpen}
        plantName={plant ? getPlantLabel(plant, species, assignedCultivar) : ''}
        onConfirm={onRemove}
        onCancel={() => setRemoveOpen(false)}
        loading={removing}
      />

      <ConfirmDialog
        open={removePlanOpen}
        title={t('pages.nutrientPlans.removePlan')}
        message={t('common.deleteConfirm', { name: assignedPlan?.name ?? '' })}
        onConfirm={onRemovePlan}
        onCancel={() => setRemovePlanOpen(false)}
        destructive
        loading={removingPlan}
      />

      {/* Assign Plan Dialog */}
      <NutrientPlanAssignDialog
        open={assignDialogOpen}
        onClose={() => setAssignDialogOpen(false)}
        onAssign={onAssignPlan}
      />

      {plant && (
        <PlantTagDialog
          open={tagDialogOpen}
          onClose={() => setTagDialogOpen(false)}
          plantKey={plant.key}
          plantName={getPlantDisplayName(plant, species, assignedCultivar)}
        />
      )}

      {plant && (
        <PlantLabelDialog
          open={labelDialogOpen}
          onClose={() => setLabelDialogOpen(false)}
          plantKeys={[plant.key]}
          plantNames={{ [plant.key]: getPlantDisplayName(plant, species, assignedCultivar) }}
        />
      )}

      {key && (
        <PhaseTransitionDialog
          plantKey={key}
          speciesKey={plant?.species_key}
          lifecycleKey={lifecycleKey}
          open={transitionOpen}
          onClose={() => setTransitionOpen(false)}
          onTransitioned={(updated) => {
            setPlant(updated);
            setTransitionOpen(false);
            load();
          }}
        />
      )}

      <CareConfirmDialog
        open={wateringDialogOpen}
        onClose={() => setWateringDialogOpen(false)}
        onConfirm={handleConfirmWatering}
        plantName={plant ? getPlantDisplayName(plant, species, assignedCultivar) : ''}
        reminderType="watering"
        loading={confirmingWatering}
        defaultDosages={dosagePresets?.dosages}
        defaultTargetEc={dosagePresets?.targetEc}
        defaultTargetPh={dosagePresets?.targetPh}
        phaseName={activePhaseEntry?.phase_name}
        defaultVolumeLiters={wateringVolume?.liters}
        volumeHint={wateringVolume?.hint}
        availableFertilizers={fertilizers}
      />

      <WateringLogCreateDialog
        open={wateringLogCreateOpen}
        onClose={() => {
          setWateringLogCreateOpen(false);
          setWateringLogChannelPreset(undefined);
        }}
        onCreated={() => {
          setWateringLogCreateOpen(false);
          setWateringLogChannelPreset(undefined);
          notification.success(t('pages.wateringLogs.logged'));
          load();
        }}
        plantKeys={key ? [key] : undefined}
        channelPreset={wateringLogChannelPreset}
        availableFertilizers={fertilizers}
      />
    </Box>
  );
}

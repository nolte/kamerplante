import { useEffect, useState, useCallback, useMemo } from 'react';
import { useTabUrl } from '@/hooks/useTabUrl';
import { useNavigate, useParams, Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Link from '@mui/material/Link';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Checkbox from '@mui/material/Checkbox';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import FormLabel from '@mui/material/FormLabel';
import FormHelperText from '@mui/material/FormHelperText';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckIcon from '@mui/icons-material/Check';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import ReplayIcon from '@mui/icons-material/Replay';
import ScheduleIcon from '@mui/icons-material/Schedule';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import AddIcon from '@mui/icons-material/Add';
import { useForm, Controller, type Control } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import PageTitle from '@/components/layout/PageTitle';
import LoadingSkeleton from '@/components/common/LoadingSkeleton';
import ErrorDisplay from '@/components/common/ErrorDisplay';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import TaskOriginBadge from '@/components/common/TaskOriginBadge';
import UnsavedChangesGuard from '@/components/form/UnsavedChangesGuard';
import FormTextField from '@/components/form/FormTextField';
import FormSelectField from '@/components/form/FormSelectField';
import FormNumberField from '@/components/form/FormNumberField';
import FormActions from '@/components/form/FormActions';
import FormRow from '@/components/form/FormRow';
import { useNotification } from '@/hooks/useNotification';
import { useApiError } from '@/hooks/useApiError';
import * as taskApi from '@/api/endpoints/tasks';
import * as plantApi from '@/api/endpoints/plantInstances';
import * as speciesApi from '@/api/endpoints/species';
import type { PlantInstance } from '@/api/types';
import type { TaskItem, TaskComment, TaskAuditEntry, ChecklistItem } from '@/api/types';
import { getPlantDisplayName } from '@/utils/plantDisplay';
import AuthImage from '@/components/common/AuthImage';
import PhotoUpload from '@/components/common/PhotoUpload';
import TaskTimer from '@/components/common/TaskTimer';

/**
 * Legacy care tasks stored instruction as "care:<type>:<id>" keys.
 * Resolve these to translated reminder-type labels; return null for normal text.
 */
function resolveCareInstruction(instruction: string, t: (key: string) => string): string | null {
  const match = instruction.match(/^care:([a-z_]+):\d+$/);
  if (!match) return null;
  const translated = t(`enums.reminderType.${match[1]}`);
  if (translated === `enums.reminderType.${match[1]}`) return match[1].replace(/_/g, ' ');
  return translated;
}

const statusColorMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
  pending: 'default',
  in_progress: 'info',
  completed: 'success',
  skipped: 'warning',
  cancelled: 'error',
  dormant: 'default',
};

const priorityColorMap: Record<string, 'default' | 'info' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
  critical: 'error',
};

const categories = [
  'maintenance', 'feeding', 'training', 'pruning', 'ausgeizen',
  'transplant', 'ipm', 'harvest', 'observation', 'care_reminder',
  'seasonal', 'phenological',
] as const;

const priorities = ['low', 'medium', 'high', 'critical'] as const;

const editSchema = z.object({
  name: z.string().min(1).max(200),
  instruction: z.string(),
  category: z.enum(categories),
  priority: z.enum(priorities),
  due_date: z.string().nullable(),
  estimated_duration_minutes: z.number().int().min(1).nullable(),
  timer_duration_seconds: z.number().int().min(1).nullable(),
  timer_label: z.string().nullable(),
  assigned_to_user_key: z.string().nullable(),
  recurrence_rule: z.string().nullable(),
});

type EditFormData = z.infer<typeof editSchema>;

const completionSchema = z.object({
  completion_notes: z.string().nullable(),
  actual_duration_minutes: z.number().int().min(1).nullable(),
  difficulty_rating: z.number().int().min(1).max(5).nullable(),
  quality_rating: z.number().int().min(1).max(5).nullable(),
});

type CompletionFormData = z.infer<typeof completionSchema>;

/** Labeled value display for the metadata grid */
function MetaItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.25 }}>
        {label}
      </Typography>
      {children}
    </Box>
  );
}

const RATING_VALUES = [1, 2, 3, 4, 5] as const;

interface RatingSelectorProps {
  name: 'difficulty_rating' | 'quality_rating';
  control: Control<CompletionFormData>;
  label: string;
  helperText: string;
  testId: string;
}

/**
 * 1-5 rating control for the completion tab (R2, FIX-05). A segmented
 * `ToggleButtonGroup` was chosen over MUI `Rating` stars: "more stars = better"
 * reads naturally for the quality rating, but is a misleading metaphor for the
 * difficulty rating (higher = harder is not "better"). The segmented selector
 * keeps both ratings visually consistent while staying semantically neutral,
 * and gives large, equally-sized ≥48px touch targets for free.
 *
 * The value stays `number 1-5 | null` (no contract change, R3): clicking the
 * already-selected button deselects it (MUI's built-in exclusive-toggle
 * behaviour), and an explicit "reset" action is offered for discoverability.
 */
function RatingSelector({ name, control, label, helperText, testId }: RatingSelectorProps) {
  const { t } = useTranslation();
  const labelId = `${testId}-label`;
  const helperId = `${testId}-helper`;

  return (
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <Box sx={{ mb: { xs: 2.5, md: 1.5 } }}>
          <FormLabel id={labelId} component="legend" sx={{ fontSize: '0.875rem', mb: 1, display: 'block' }}>
            {label}
          </FormLabel>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
              {t('pages.tasks.ratingLow')}
            </Typography>
            <ToggleButtonGroup
              exclusive
              value={field.value}
              onChange={(_, newValue) => field.onChange(newValue)}
              aria-labelledby={labelId}
              aria-describedby={helperId}
              data-testid={testId}
              sx={{ flexWrap: 'wrap' }}
            >
              {RATING_VALUES.map((v) => (
                <ToggleButton
                  key={v}
                  value={v}
                  aria-label={t('pages.tasks.ratingValueLabel', { value: v })}
                  data-testid={`${testId}-${v}`}
                  sx={{ minWidth: 48, minHeight: 48 }}
                >
                  {v}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
              {t('pages.tasks.ratingHigh')}
            </Typography>
            {field.value != null && (
              <Button
                size="small"
                onClick={() => field.onChange(null)}
                data-testid={`${testId}-clear`}
                sx={{ textTransform: 'none' }}
              >
                {t('pages.tasks.ratingClear')}
              </Button>
            )}
          </Box>
          <FormHelperText id={helperId} sx={{ mx: 0 }}>
            <Box component="span" data-testid={`${testId}-status`}>
              {field.value != null
                ? t('pages.tasks.ratingSelectedValue', { value: field.value })
                : t('pages.tasks.ratingNotRated')}
            </Box>
            {' — '}
            {helperText}
          </FormHelperText>
        </Box>
      )}
    />
  );
}

export default function TaskDetailPage() {
  const { key } = useParams<{ key: string }>();
  const { t } = useTranslation();
  const { i18n } = useTranslation();
  const notification = useNotification();
  const { handleError } = useApiError();

  const [task, setTask] = useState<TaskItem | null>(null);
  const [plantName, setPlantName] = useState<string | null>(null);
  const [plantInfo, setPlantInfo] = useState<{ plant: PlantInstance; speciesName: string; cultivarName: string | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [photoRefs, setPhotoRefs] = useState<string[]>([]);

  // Comments state
  const [comments, setComments] = useState<TaskComment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [editingCommentKey, setEditingCommentKey] = useState<string | null>(null);
  const [editCommentText, setEditCommentText] = useState('');
  const [commentLoading, setCommentLoading] = useState(false);

  // History state
  const [history, setHistory] = useState<TaskAuditEntry[]>([]);

  // Checklist add state
  const [newChecklistText, setNewChecklistText] = useState('');

  const isActionable = task?.status === 'pending' || task?.status === 'in_progress';
  const tabSlugs = useMemo(
    () => isActionable
      ? ['details', 'complete', 'comments', 'history', 'edit'] as const
      : ['details', 'comments', 'history', 'edit'] as const,
    [isActionable],
  );
  const [tab, setTab] = useTabUrl(tabSlugs);

  const {
    control: editControl,
    handleSubmit: handleEditSubmit,
    reset: resetEdit,
    formState: { isDirty },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      name: '',
      instruction: '',
      category: 'maintenance',
      priority: 'medium',
      due_date: null,
      estimated_duration_minutes: null,
      timer_duration_seconds: null,
      timer_label: null,
      assigned_to_user_key: null,
      recurrence_rule: null,
    },
  });

  const {
    control: completionControl,
    handleSubmit: handleCompletionSubmit,
    reset: resetCompletion,
  } = useForm<CompletionFormData>({
    resolver: zodResolver(completionSchema),
    defaultValues: {
      completion_notes: null,
      actual_duration_minutes: null,
      difficulty_rating: null,
      quality_rating: null,
    },
  });

  const load = useCallback(async () => {
    if (!key) return;
    setLoading(true);
    try {
      const fetched = await taskApi.getTask(key);
      setTask(fetched);
      setPhotoRefs(fetched.photo_refs ?? []);
      if (fetched.entity_type === 'plant_instance' && fetched.entity_key) {
        plantApi.getPlantInstance(fetched.entity_key)
          .then(async (p) => {
            setPlantName(getPlantDisplayName(p));
            try {
              const sp = await speciesApi.getSpecies(p.species_key);
              const speciesName = sp.common_names?.[0] || sp.scientific_name;
              let cultivarName: string | null = null;
              if (p.cultivar_key) {
                const cvList = await speciesApi.listCultivars(p.species_key);
                const cv = cvList.find((c) => c.key === p.cultivar_key);
                if (cv) cultivarName = cv.name;
              }
              setPlantInfo({ plant: p, speciesName, cultivarName });
            } catch {
              setPlantInfo(null);
            }
          })
          .catch(() => setPlantName(null));
      }
      resetEdit({
        name: fetched.name,
        instruction: fetched.instruction,
        category: fetched.category as EditFormData['category'],
        priority: fetched.priority as EditFormData['priority'],
        due_date: fetched.due_date ? fetched.due_date.split('T')[0] : null,
        estimated_duration_minutes: fetched.estimated_duration_minutes,
        timer_duration_seconds: fetched.timer_duration_seconds,
        timer_label: fetched.timer_label,
        assigned_to_user_key: fetched.assigned_to_user_key,
        recurrence_rule: fetched.recurrence_rule,
      });
      resetCompletion({
        completion_notes: fetched.completion_notes,
        actual_duration_minutes: fetched.actual_duration_minutes,
        difficulty_rating: fetched.difficulty_rating,
        quality_rating: fetched.quality_rating,
      });
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [key, resetEdit, resetCompletion]);

  const loadComments = useCallback(async () => {
    if (!key) return;
    try {
      const data = await taskApi.listTaskComments(key);
      setComments(data);
    } catch {
      // silently fail
    }
  }, [key]);

  const loadHistory = useCallback(async () => {
    if (!key) return;
    try {
      const data = await taskApi.getTaskHistory(key);
      setHistory(data);
    } catch {
      // silently fail
    }
  }, [key]);

  useEffect(() => {
    load();
  }, [load]);

  // Load comments and history when those tabs become active
  useEffect(() => {
    const commentsTabIndex = isActionable ? 2 : 1;
    const historyTabIndex = isActionable ? 3 : 2;
    if (tab === commentsTabIndex) loadComments();
    if (tab === historyTabIndex) loadHistory();
  }, [tab, isActionable, loadComments, loadHistory]);

  const onSave = async (data: EditFormData) => {
    if (!key) return;
    try {
      setSaving(true);
      await taskApi.updateTask(key, {
        name: data.name,
        instruction: data.instruction,
        category: data.category,
        priority: data.priority,
        due_date: data.due_date,
        estimated_duration_minutes: data.estimated_duration_minutes,
        timer_duration_seconds: data.timer_duration_seconds,
        timer_label: data.timer_label,
        assigned_to_user_key: data.assigned_to_user_key,
        recurrence_rule: data.recurrence_rule,
      });
      notification.success(t('common.save'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  const handleStart = async () => {
    if (!key) return;
    try {
      setActionLoading(true);
      await taskApi.startTask(key);
      notification.success(t('pages.tasks.taskStarted'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async (data: CompletionFormData) => {
    if (!key) return;
    try {
      setActionLoading(true);
      await taskApi.completeTask(key, {
        completion_notes: data.completion_notes,
        actual_duration_minutes: data.actual_duration_minutes,
        photo_refs: photoRefs.length > 0 ? photoRefs : undefined,
        difficulty_rating: data.difficulty_rating,
        quality_rating: data.quality_rating,
      });
      notification.success(t('pages.tasks.taskCompleted'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSkip = async () => {
    if (!key) return;
    try {
      setActionLoading(true);
      await taskApi.skipTask(key);
      notification.success(t('pages.tasks.taskSkipped'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const onDelete = async () => {
    if (!key) return;
    setDeleting(true);
    try {
      await taskApi.deleteTask(key);
      notification.success(t('pages.tasks.taskDeleted'));
      navigate('/aufgaben/queue');
    } catch (err) {
      handleError(err);
    } finally {
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  const handleClone = async () => {
    if (!key) return;
    try {
      setActionLoading(true);
      const cloned = await taskApi.cloneTask(key);
      notification.success(t('pages.tasks.taskCloned'));
      navigate(`/aufgaben/${cloned.key}`);
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopen = async () => {
    if (!key) return;
    try {
      setActionLoading(true);
      await taskApi.reopenTask(key);
      notification.success(t('pages.tasks.taskReopened'));
      load();
    } catch (err) {
      handleError(err);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Checklist interactions ──

  const handleChecklistToggle = async (idx: number) => {
    if (!key || !task) return;
    const updated = task.checklist.map((item, i) =>
      i === idx ? { ...item, done: !item.done } : item,
    );
    try {
      await taskApi.updateTask(key, { checklist: updated });
      setTask({ ...task, checklist: updated });
    } catch (err) {
      handleError(err);
    }
  };

  const handleChecklistAdd = async () => {
    if (!key || !task || !newChecklistText.trim()) return;
    const newItem: ChecklistItem = {
      text: newChecklistText.trim(),
      done: false,
      order: task.checklist.length,
    };
    const updated = [...task.checklist, newItem];
    try {
      await taskApi.updateTask(key, { checklist: updated });
      setTask({ ...task, checklist: updated });
      setNewChecklistText('');
    } catch (err) {
      handleError(err);
    }
  };

  // ── Comment actions ──

  const handleAddComment = async () => {
    if (!key || !newComment.trim()) return;
    try {
      setCommentLoading(true);
      await taskApi.createTaskComment(key, newComment.trim());
      setNewComment('');
      loadComments();
    } catch (err) {
      handleError(err);
    } finally {
      setCommentLoading(false);
    }
  };

  const handleUpdateComment = async (commentKey: string) => {
    if (!key || !editCommentText.trim()) return;
    try {
      setCommentLoading(true);
      await taskApi.updateTaskComment(key, commentKey, editCommentText.trim());
      setEditingCommentKey(null);
      loadComments();
    } catch (err) {
      handleError(err);
    } finally {
      setCommentLoading(false);
    }
  };

  const handleDeleteComment = async (commentKey: string) => {
    if (!key) return;
    try {
      await taskApi.deleteTaskComment(key, commentKey);
      loadComments();
    } catch (err) {
      handleError(err);
    }
  };

  const canReopen = task?.status === 'completed' || task?.status === 'skipped';

  if (loading) return <LoadingSkeleton variant="form" />;
  if (error) return <ErrorDisplay error={error} />;
  if (!task) return <ErrorDisplay error={t('errors.notFound')} />;

  const rawInstruction = (i18n.language === 'de' && task.instruction_de) ? task.instruction_de : task.instruction;
  const resolvedInstruction = rawInstruction
    ? resolveCareInstruction(rawInstruction, t) ?? rawInstruction
    : null;

  const commentsTabIndex = isActionable ? 2 : 1;
  const historyTabIndex = isActionable ? 3 : 2;
  const editTabIndex = isActionable ? 4 : 3;

  return (
    <Box data-testid="task-detail-page">
      <UnsavedChangesGuard dirty={isDirty} />

      {/* Header: Title + action buttons */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          mb: 2,
          gap: 2,
          flexWrap: 'wrap',
        }}
      >
        {/* `minWidth: 0` lets the title column shrink below its max-content
            width; without it the chip row sets the column's automatic minimum
            size and the header cannot reflow at all. */}
        <Box sx={{ minWidth: 0 }}>
          <PageTitle title={(i18n.language === 'de' && task.name_de) ? task.name_de : task.name} />
          {/* Status / category / priority. The three German labels measure
              ~340px against a 393px viewport, so the row MUST be allowed to
              wrap (UI-NFR-001 R-005/R-006). `useFlexGap` is required with
              `flexWrap`: Stack's default margin-based spacing collapses to the
              wrong side once a line breaks. */}
          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            sx={{ mt: 0.5, flexWrap: 'wrap' }}
          >
            <Chip
              label={t(`enums.taskStatus.${task.status}`)}
              size="small"
              color={statusColorMap[task.status] ?? 'default'}
            />
            <Chip
              label={t(`enums.taskCategory.${task.category}`)}
              size="small"
              variant="outlined"
            />
            <Chip
              label={t(`enums.taskPriority.${task.priority}`)}
              size="small"
              color={priorityColorMap[task.priority] ?? 'default'}
              variant="outlined"
            />
            {/* REQ-006 FreeStyle machine-generated badge (#1082) */}
            <TaskOriginBadge origin={task.origin} testId="task-detail-origin-badge" />
          </Stack>
        </Box>

        {/* The action group MUST stay shrinkable and wrap: with `flexShrink: 0`
            a flex item is sized to its max-content width, so up to five buttons
            (start / skip / reopen / clone / delete) formed one unbreakable row
            that pushed the trailing — destructive — buttons outside a 393px
            viewport. Shrinking is bounded by the group's automatic minimum size,
            so the buttons wrap onto a second line instead of overflowing
            (UI-NFR-001 R-005/R-006, UI-NFR-021 R-023). `useFlexGap` is required
            here: Stack's default margin-based spacing breaks once lines wrap. */}
        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          sx={{ flexWrap: 'wrap', justifyContent: 'flex-end' }}
        >
          {task.status === 'pending' && (
            <Button
              variant="outlined"
              size="small"
              startIcon={actionLoading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
              onClick={handleStart}
              disabled={actionLoading}
              data-testid="start-task-button"
            >
              {t('pages.tasks.startTask')}
            </Button>
          )}
          {isActionable && (
            <Button
              variant="text"
              size="small"
              startIcon={actionLoading ? <CircularProgress size={16} /> : <SkipNextIcon />}
              onClick={handleSkip}
              disabled={actionLoading}
              data-testid="skip-task-button"
            >
              {t('pages.tasks.skipTask')}
            </Button>
          )}
          {canReopen && (
            <Button
              variant="outlined"
              size="small"
              startIcon={actionLoading ? <CircularProgress size={16} /> : <ReplayIcon />}
              onClick={handleReopen}
              disabled={actionLoading}
              data-testid="reopen-task-button"
            >
              {t('pages.tasks.reopenTask')}
            </Button>
          )}
          <Button
            variant="outlined"
            size="small"
            startIcon={<ContentCopyIcon />}
            onClick={handleClone}
            disabled={actionLoading}
            data-testid="clone-task-button"
          >
            {t('pages.tasks.cloneTask')}
          </Button>
          <Button
            variant="outlined"
            size="small"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => setDeleteOpen(true)}
            data-testid="delete-task-button"
          >
            {t('common.delete')}
          </Button>
        </Stack>
      </Box>

      {/* Scrollable + mobile scroll buttons: five tabs never fit a 393px viewport,
          and a fixed tab bar would clip the trailing tabs out of reach entirely
          (UI-NFR-001 mobile-first). */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2 }}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        aria-label={t('pages.tasks.title')}
      >
        <Tab label={t('pages.tasks.tabDetails')} />
        {isActionable && <Tab label={t('pages.tasks.tabComplete')} />}
        <Tab label={t('pages.tasks.tabComments')} />
        <Tab label={t('pages.tasks.tabHistory')} />
        <Tab label={t('common.edit')} />
      </Tabs>

      {/* Tab 0: Details */}
      {tab === 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>

          {/* Metadata grid */}
          <Card variant="outlined">
            <CardContent sx={{ pb: '16px !important' }}>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(auto-fill, minmax(160px, 1fr))' },
                  gap: 2.5,
                }}
              >
                {task.entity_type === 'plant_instance' && task.entity_key && (
                  <MetaItem label={t('pages.tasks.plant')}>
                    <Tooltip
                      arrow
                      enterTouchDelay={0}
                      leaveTouchDelay={3000}
                      title={plantInfo ? (
                        <Box sx={{ p: 0.5 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {getPlantDisplayName(plantInfo.plant)}
                          </Typography>
                          <Typography variant="caption" sx={{ display: 'block' }}>
                            {t('entities.species')}: {plantInfo.speciesName}
                          </Typography>
                          {plantInfo.cultivarName && (
                            <Typography variant="caption" sx={{ display: 'block' }}>
                              {t('entities.cultivar')}: {plantInfo.cultivarName}
                            </Typography>
                          )}
                          {plantInfo.plant.current_phase && (
                            <Typography variant="caption" sx={{ display: 'block' }}>
                              {t('pages.plantInstances.currentPhase')}: {t(`enums.phaseName.${plantInfo.plant.current_phase}`, { defaultValue: plantInfo.plant.current_phase })}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            {t('pages.plantInstances.instanceId')}: {plantInfo.plant.instance_id}
                          </Typography>
                        </Box>
                      ) : ''}
                    >
                      <Link
                        component={RouterLink}
                        to={`/pflanzen/plant-instances/${task.entity_key}`}
                        underline="hover"
                        variant="body2"
                        sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, fontWeight: 500 }}
                        data-testid="plant-link"
                      >
                        <LocalFloristIcon sx={{ fontSize: 16 }} />
                        {plantName ?? task.entity_key}
                      </Link>
                    </Tooltip>
                  </MetaItem>
                )}

                {task.due_date && (
                  <MetaItem label={t('pages.tasks.dueDate')}>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CalendarTodayIcon sx={{ fontSize: 15, color: 'text.secondary' }} />
                      {new Date(task.due_date).toLocaleDateString()}
                    </Typography>
                  </MetaItem>
                )}

                {task.estimated_duration_minutes != null && (
                  <MetaItem label={t('pages.tasks.estimatedDuration')}>
                    <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <ScheduleIcon sx={{ fontSize: 15, color: 'text.secondary' }} />
                      {task.estimated_duration_minutes} min
                    </Typography>
                  </MetaItem>
                )}

                {task.actual_duration_minutes != null && (
                  <MetaItem label={t('pages.tasks.actualDuration')}>
                    <Typography variant="body2">
                      {task.actual_duration_minutes} min
                    </Typography>
                  </MetaItem>
                )}

                {task.assigned_to_user_key && (
                  <MetaItem label={t('pages.tasks.assignedTo')}>
                    <Typography variant="body2">{task.assigned_to_user_key}</Typography>
                  </MetaItem>
                )}

                {task.recurrence_rule && (
                  <MetaItem label={t('pages.tasks.recurrenceRule')}>
                    <Typography variant="body2">
                      {(() => {
                        const recurrenceLabels: Record<string, string> = {
                          'FREQ=DAILY': t('pages.tasks.recurrenceDaily'),
                          'FREQ=WEEKLY': t('pages.tasks.recurrenceWeekly'),
                          'FREQ=WEEKLY;INTERVAL=2': t('pages.tasks.recurrenceBiweekly'),
                          'FREQ=MONTHLY': t('pages.tasks.recurrenceMonthly'),
                        };
                        return recurrenceLabels[task.recurrence_rule] ?? task.recurrence_rule;
                      })()}
                    </Typography>
                  </MetaItem>
                )}

                {task.started_at && (
                  <MetaItem label={t('pages.tasks.startedAt')}>
                    <Typography variant="body2">
                      {new Date(task.started_at).toLocaleString()}
                    </Typography>
                  </MetaItem>
                )}

                {task.completed_at && (
                  <MetaItem label={t('pages.tasks.completedAt')}>
                    <Typography variant="body2">
                      {new Date(task.completed_at).toLocaleString()}
                    </Typography>
                  </MetaItem>
                )}

                {/* Task source */}
                <MetaItem label={t('pages.tasks.source')}>
                  {task.origin !== 'user' ? (
                    // REQ-006 FreeStyle (#1082): a machine producer carries its own
                    // producer id (and optional run reference), preferred over the
                    // internal-source heuristics below.
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }} data-testid="task-detail-source">
                        {task.source || t('pages.tasks.machineGenerated')}
                      </Typography>
                      {task.source_run_ref && (
                        <Typography variant="caption" color="text.secondary" data-testid="task-detail-source-run">
                          {t('pages.tasks.producerRun')}: {task.source_run_ref}
                        </Typography>
                      )}
                    </Box>
                  ) : task.activity_key ? (
                    <Link
                      component={RouterLink}
                      to={`/stammdaten/activities/${task.activity_key}`}
                      underline="hover"
                      variant="body2"
                      sx={{ fontWeight: 500 }}
                    >
                      {t('pages.tasks.sourceActivityPlan')}
                    </Link>
                  ) : task.workflow_execution_key ? (
                    <Typography variant="body2">{t('pages.tasks.sourceWorkflow')}</Typography>
                  ) : task.watering_event_key ? (
                    <Typography variant="body2">{t('pages.tasks.sourceWateringSchedule')}</Typography>
                  ) : task.category === 'care_reminder' ? (
                    <Typography variant="body2">{t('pages.tasks.sourceCareReminder')}</Typography>
                  ) : (
                    <Typography variant="body2">{t('pages.tasks.sourceManual')}</Typography>
                  )}
                </MetaItem>
              </Box>
            </CardContent>
          </Card>

          {/* Instruction callout */}
          {resolvedInstruction && (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                bgcolor: 'action.hover',
                borderLeft: '4px solid',
                borderLeftColor: 'primary.main',
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                <InfoOutlinedIcon sx={{ fontSize: 15 }} />
                {t('pages.tasks.instruction')}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {resolvedInstruction}
              </Typography>
            </Paper>
          )}

          {/* Timer */}
          {task.status === 'in_progress' && task.timer_duration_seconds != null && (
            <Card variant="outlined">
              <CardContent>
                <TaskTimer
                  durationSeconds={task.timer_duration_seconds}
                  label={task.timer_label}
                />
              </CardContent>
            </Card>
          )}

          {/* Photos */}
          {task.photo_refs && task.photo_refs.length > 0 && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  {t('pages.tasks.photos')}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {task.photo_refs.map((ref, i) => (
                    <AuthImage
                      key={ref}
                      uri={taskApi.taskPhotoUri(ref)}
                      alt={t('pages.tasks.photoAlt', { index: i + 1 })}
                      width={120}
                      height={120}
                      data-testid={`task-photo-${i}`}
                      sx={{
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: 'divider',
                      }}
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Tags */}
          {task.tags && task.tags.length > 0 && (
            <Card variant="outlined">
              <CardContent sx={{ pb: '16px !important' }}>
                <Typography variant="subtitle2" gutterBottom>
                  {t('pages.tasks.tags')}
                </Typography>
                <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
                  {task.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" variant="outlined" />
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Interactive Checklist */}
          {(task.checklist.length > 0 || isActionable) && (
            <Card variant="outlined">
              <CardContent sx={{ pb: '16px !important' }}>
                <Typography variant="subtitle2" gutterBottom>
                  {t('pages.tasks.checklist')}
                </Typography>
                <List dense disablePadding>
                  {[...task.checklist].sort((a, b) => a.order - b.order).map((item, idx) => (
                    <ListItem key={idx} disableGutters sx={{ py: 0 }}>
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <Checkbox
                          size="small"
                          checked={item.done}
                          onChange={() => handleChecklistToggle(idx)}
                          disabled={!isActionable}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={item.text}
                        slotProps={{ primary: { variant: 'body2', sx: item.done ? { textDecoration: 'line-through', color: 'text.secondary' } : {} } }}
                      />
                    </ListItem>
                  ))}
                </List>
                {isActionable && (
                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <TextField
                      size="small"
                      value={newChecklistText}
                      onChange={(e) => setNewChecklistText(e.target.value)}
                      placeholder={t('pages.tasks.addChecklistItem')}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleChecklistAdd(); } }}
                      sx={{ flex: 1 }}
                    />
                    <IconButton
                      size="small"
                      onClick={handleChecklistAdd}
                      disabled={!newChecklistText.trim()}
                    >
                      <AddIcon />
                    </IconButton>
                  </Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Completion notes */}
          {task.completion_notes && (
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderLeft: '4px solid',
                borderLeftColor: 'success.main',
              }}
            >
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                {t('pages.tasks.completionNotes')}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {task.completion_notes}
              </Typography>
            </Paper>
          )}

          {/* Ratings */}
          {(task.difficulty_rating != null || task.quality_rating != null) && (
            <Card variant="outlined">
              <CardContent sx={{ pb: '16px !important' }}>
                <Box sx={{ display: 'flex', gap: 4 }}>
                  {task.difficulty_rating != null && (
                    <MetaItem label={t('pages.tasks.difficultyRating')}>
                      <Typography variant="body2">{task.difficulty_rating} / 5</Typography>
                    </MetaItem>
                  )}
                  {task.quality_rating != null && (
                    <MetaItem label={t('pages.tasks.qualityRating')}>
                      <Typography variant="body2">{task.quality_rating} / 5</Typography>
                    </MetaItem>
                  )}
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}

      {/* Tab: Complete task (only when actionable) */}
      {tab === 1 && isActionable && (
        <Box
          component="form"
          noValidate
          onSubmit={handleCompletionSubmit(handleComplete)}
          sx={{ maxWidth: 1280, display: 'flex', flexDirection: 'column', gap: 4 }}
        >
          <Typography variant="body2" color="text.secondary">
            {t('pages.tasks.completeIntro')}
          </Typography>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionCompletion')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.sectionCompletionDesc')}
              </Typography>
              <FormTextField
                name="completion_notes"
                control={completionControl}
                label={t('pages.tasks.completionNotes')}
                helperText={t('pages.tasks.completionNotesHelper')}
                multiline
                rows={4}
                autoFocus
              />
              <FormNumberField
                name="actual_duration_minutes"
                control={completionControl}
                label={t('pages.tasks.actualDuration')}
                min={1}
                step={1}
                suffix={t('pages.tasks.minutesUnit')}
                helperText={t('pages.tasks.actualDurationHelper')}
              />
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionRatings')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.sectionRatingsDesc')}
              </Typography>
              <FormRow>
                <RatingSelector
                  name="difficulty_rating"
                  control={completionControl}
                  label={t('pages.tasks.difficultyRating')}
                  helperText={t('pages.tasks.ratingHelper')}
                  testId="task-difficulty-rating"
                />
                <RatingSelector
                  name="quality_rating"
                  control={completionControl}
                  label={t('pages.tasks.qualityRating')}
                  helperText={t('pages.tasks.ratingHelper')}
                  testId="task-quality-rating"
                />
              </FormRow>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionPhotos')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                {task.requires_photo
                  ? t('pages.tasks.sectionPhotosRequiredDesc')
                  : t('pages.tasks.sectionPhotosDesc')}
              </Typography>
              {task.requires_photo && (
                <Typography
                  variant="subtitle2"
                  color={photoRefs.length === 0 ? 'error' : 'text.primary'}
                  gutterBottom
                >
                  {t('pages.tasks.photoRequired')}
                </Typography>
              )}
              <PhotoUpload
                taskKey={key!}
                photoRefs={photoRefs}
                onChange={setPhotoRefs}
              />
            </CardContent>
          </Card>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              type="submit"
              variant="contained"
              color="success"
              startIcon={
                actionLoading ? <CircularProgress size={16} /> : <CheckIcon />
              }
              disabled={actionLoading || (task.requires_photo && photoRefs.length === 0)}
              data-testid="complete-task-submit"
            >
              {t('pages.tasks.completeTask')}
            </Button>
          </Box>
        </Box>
      )}

      {/* Tab: Comments */}
      {tab === commentsTabIndex && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              {t('pages.tasks.tabComments')} ({comments.length})
            </Typography>

            {comments.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.noComments')}
              </Typography>
            )}

            {comments.map((c) => (
              <Paper key={c.key} variant="outlined" sx={{ p: 2, mb: 1.5 }}>
                {editingCommentKey === c.key ? (
                  <Box>
                    <TextField
                      fullWidth
                      size="small"
                      multiline
                      rows={2}
                      value={editCommentText}
                      onChange={(e) => setEditCommentText(e.target.value)}
                    />
                    <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => handleUpdateComment(c.key)}
                        disabled={commentLoading || !editCommentText.trim()}
                      >
                        {t('common.save')}
                      </Button>
                      <Button size="small" onClick={() => setEditingCommentKey(null)}>
                        {t('common.cancel')}
                      </Button>
                    </Stack>
                  </Box>
                ) : (
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        {c.created_by} &mdash; {c.created_at ? new Date(c.created_at).toLocaleString() : ''}
                      </Typography>
                      <Box>
                        <IconButton
                          size="small"
                          onClick={() => {
                            setEditingCommentKey(c.key);
                            setEditCommentText(c.comment_text);
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDeleteComment(c.key)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </Box>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {c.comment_text}
                    </Typography>
                  </Box>
                )}
              </Paper>
            ))}

            <Divider sx={{ my: 2 }} />

            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                size="small"
                multiline
                rows={2}
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder={t('pages.tasks.addComment')}
              />
              <Button
                variant="contained"
                size="small"
                startIcon={commentLoading ? <CircularProgress size={16} /> : <SendIcon />}
                onClick={handleAddComment}
                disabled={commentLoading || !newComment.trim()}
                sx={{ alignSelf: 'flex-end' }}
              >
                {t('pages.tasks.send')}
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Tab: History */}
      {tab === historyTabIndex && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              {t('pages.tasks.tabHistory')} ({history.length})
            </Typography>

            {history.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {t('pages.tasks.noHistory')}
              </Typography>
            )}

            {history.map((entry) => (
              <Paper key={entry.key} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {entry.action}
                      {entry.field && (
                        <Typography component="span" variant="body2" color="text.secondary">
                          {' '}&mdash; {entry.field}
                        </Typography>
                      )}
                    </Typography>
                    {(entry.old_value || entry.new_value) && (
                      <Typography variant="caption" color="text.secondary">
                        {entry.old_value && <><s>{entry.old_value}</s> &rarr; </>}
                        {entry.new_value}
                      </Typography>
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap', ml: 2 }}>
                    {entry.changed_by} &mdash; {entry.changed_at ? new Date(entry.changed_at).toLocaleString() : ''}
                  </Typography>
                </Box>
              </Paper>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tab: Edit */}
      {tab === editTabIndex && (
        <Box
          component="form"
          // react-hook-form + zod is the single validation source of truth here.
          // Without `noValidate` the browser's own constraint validation runs
          // first (the `required` name, the `min`/`step` of the duration
          // fields): it aborts the submission *before* any `submit` event, so
          // zod never runs and no MUI helper text ever renders — the user only
          // sees a transient native bubble in the browser's locale. Same defect
          // and same fix as on HarvestBatchDetailPage/HarvestCreateDialog.
          noValidate
          onSubmit={handleEditSubmit(onSave)}
          sx={{ maxWidth: 1280, display: 'flex', flexDirection: 'column', gap: 4 }}
        >
          <Typography variant="body2" color="text.secondary">
            {t('pages.tasks.editIntro')}
          </Typography>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionTask')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.sectionTaskDesc')}
              </Typography>
              <FormTextField
                name="name"
                control={editControl}
                label={t('pages.tasks.name')}
                required
                autoFocus
              />
              <FormTextField
                name="instruction"
                control={editControl}
                label={t('pages.tasks.instruction')}
                multiline
                rows={4}
              />
              <FormSelectField
                name="category"
                control={editControl}
                label={t('pages.tasks.category')}
                options={categories.map((v) => ({
                  value: v,
                  label: t(`enums.taskCategory.${v}`),
                }))}
              />
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionScheduling')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.sectionSchedulingDesc')}
              </Typography>
              <FormRow>
                <FormTextField
                  name="due_date"
                  control={editControl}
                  label={t('pages.tasks.dueDate')}
                  type="date"
                />
                <FormSelectField
                  name="priority"
                  control={editControl}
                  label={t('pages.tasks.priority')}
                  helperText={t('pages.tasks.priorityHelper')}
                  options={priorities.map((v) => ({
                    value: v,
                    label: t(`enums.taskPriority.${v}`),
                  }))}
                />
              </FormRow>
              <FormRow>
                <FormNumberField
                  name="estimated_duration_minutes"
                  control={editControl}
                  label={t('pages.tasks.estimatedDuration')}
                  min={1}
                  step={1}
                  helperText={t('pages.tasks.estimatedDurationHelper')}
                />
                <FormNumberField
                  name="timer_duration_seconds"
                  control={editControl}
                  label={t('pages.tasks.timerDuration')}
                  min={1}
                  step={1}
                  helperText={t('pages.tasks.timerDurationHelper')}
                />
              </FormRow>
              <FormTextField
                name="timer_label"
                control={editControl}
                label={t('pages.tasks.timerLabel')}
              />
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent component="fieldset" sx={{ border: 'none', p: 0, m: 0, '&:last-child': { pb: 2 }, px: 2, pt: 2 }}>
              <Typography component="legend" variant="h6" sx={{ pt: 1.5, mb: 0.5 }}>
                {t('pages.tasks.sectionAssignment')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('pages.tasks.sectionAssignmentDesc')}
              </Typography>
              <FormTextField
                name="assigned_to_user_key"
                control={editControl}
                label={t('pages.tasks.assignedTo')}
                helperText={t('pages.tasks.assignedToHelper')}
              />
              <FormSelectField
                name="recurrence_rule"
                control={editControl}
                label={t('pages.tasks.recurrenceRule')}
                helperText={t('pages.tasks.recurrenceRuleHelper')}
                options={[
                  { value: '', label: t('pages.tasks.recurrenceNone') },
                  { value: 'FREQ=DAILY', label: t('pages.tasks.recurrenceDaily') },
                  { value: 'FREQ=WEEKLY', label: t('pages.tasks.recurrenceWeekly') },
                  { value: 'FREQ=WEEKLY;INTERVAL=2', label: t('pages.tasks.recurrenceBiweekly') },
                  { value: 'FREQ=MONTHLY', label: t('pages.tasks.recurrenceMonthly') },
                ]}
              />
            </CardContent>
          </Card>

          <Typography variant="caption" color="text.secondary">* {t('common.required')}</Typography>
          <FormActions
            onCancel={() => resetEdit()}
            loading={saving}
            disabled={!isDirty}
          />
        </Box>
      )}

      <ConfirmDialog
        open={deleteOpen}
        title={t('common.delete')}
        message={t('common.deleteConfirm', { name: task.name })}
        onConfirm={onDelete}
        onCancel={() => setDeleteOpen(false)}
        destructive
        loading={deleting}
      />
    </Box>
  );
}

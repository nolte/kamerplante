import { tenantClient as client, getActiveTenantSlug } from '../client';
import type {
  BatchResponse,
  HSTValidationResult,
  TaskPhoto,
  TaskAuditEntry,
  TaskCloneRequest,
  TaskComment,
  TaskCompleteRequest,
  TaskItem,
  TaskItemCreate,
  TaskItemUpdate,
  TaskTemplate,
  TaskTemplateCreate,
  TaskTemplateUpdate,
  WorkflowAddTaskRequest,
  WorkflowExecution,
  WorkflowInstantiateRequest,
  WorkflowPhase,
  WorkflowPhaseCreate,
  WorkflowPhaseSuggestion,
  WorkflowPhaseUpdate,
  WorkflowTargetType,
  WorkflowTemplate,
  WorkflowTemplateCreate,
  WorkflowTemplateUpdate,
} from '../types';

const BASE = '/tasks';

// -- Workflow Templates --

export async function listWorkflows(
  offset = 0,
  limit = 50,
  speciesKey?: string,
  targetEntityType?: WorkflowTargetType,
): Promise<WorkflowTemplate[]> {
  const params: Record<string, unknown> = { offset, limit };
  if (speciesKey) params.species_key = speciesKey;
  if (targetEntityType) params.target_entity_type = targetEntityType;
  const { data } = await client.get<WorkflowTemplate[]>(
    `${BASE}/workflows`,
    { params },
  );
  return data;
}

export async function createWorkflow(
  payload: WorkflowTemplateCreate,
): Promise<WorkflowTemplate> {
  const { data } = await client.post<WorkflowTemplate>(
    `${BASE}/workflows`,
    payload,
  );
  return data;
}

export async function getWorkflow(key: string): Promise<WorkflowTemplate> {
  const { data } = await client.get<WorkflowTemplate>(
    `${BASE}/workflows/${key}`,
  );
  return data;
}

export async function updateWorkflow(
  key: string,
  payload: WorkflowTemplateUpdate,
): Promise<WorkflowTemplate> {
  const { data } = await client.put<WorkflowTemplate>(
    `${BASE}/workflows/${key}`,
    payload,
  );
  return data;
}

export async function deleteWorkflow(key: string): Promise<void> {
  await client.delete(`${BASE}/workflows/${key}`);
}

export async function duplicateWorkflow(key: string, name: string): Promise<WorkflowTemplate> {
  const { data } = await client.post<WorkflowTemplate>(
    `${BASE}/workflows/${key}/duplicate`,
    null,
    { params: { name } },
  );
  return data;
}

export interface WorkflowExecutionEnriched {
  key: string;
  entity_key: string;
  entity_type: string;
  entity_name: string;
  plant_removed: boolean;
  species_name: string;
  completion_percentage: number;
  on_schedule: boolean;
  started_at: string | null;
  completed_at: string | null;
}

export async function listWorkflowExecutions(
  key: string,
): Promise<WorkflowExecutionEnriched[]> {
  const { data } = await client.get<WorkflowExecutionEnriched[]>(
    `${BASE}/workflows/${key}/executions`,
  );
  return data;
}

export async function instantiateWorkflow(
  key: string,
  payload: WorkflowInstantiateRequest,
): Promise<WorkflowExecution> {
  const { data } = await client.post<WorkflowExecution>(
    `${BASE}/workflows/${key}/instantiate`,
    payload,
  );
  return data;
}

// -- Workflow Phases --

export async function listWorkflowPhases(
  wfKey: string,
): Promise<WorkflowPhase[]> {
  const { data } = await client.get<WorkflowPhase[]>(
    `${BASE}/workflows/${wfKey}/phases`,
  );
  return data;
}

export async function createWorkflowPhase(
  wfKey: string,
  payload: WorkflowPhaseCreate,
): Promise<WorkflowPhase> {
  const { data } = await client.post<WorkflowPhase>(
    `${BASE}/workflows/${wfKey}/phases`,
    payload,
  );
  return data;
}

export async function updateWorkflowPhase(
  key: string,
  payload: WorkflowPhaseUpdate,
): Promise<WorkflowPhase> {
  const { data } = await client.put<WorkflowPhase>(
    `${BASE}/phases/${key}`,
    payload,
  );
  return data;
}

export async function deleteWorkflowPhase(key: string): Promise<void> {
  await client.delete(`${BASE}/phases/${key}`);
}

export async function reorderPhases(
  phases: { key: string; phase_order: number }[],
): Promise<WorkflowPhase[]> {
  const { data } = await client.put<WorkflowPhase[]>(
    `${BASE}/phases/reorder`,
    { phases },
  );
  return data;
}

export async function listPhaseSuggestions(): Promise<WorkflowPhaseSuggestion[]> {
  const { data } = await client.get<WorkflowPhaseSuggestion[]>(
    `${BASE}/phases/suggestions`,
  );
  return data;
}

// -- Task Templates --

export async function listTaskTemplates(
  workflowKey: string,
): Promise<TaskTemplate[]> {
  const { data } = await client.get<TaskTemplate[]>(
    `${BASE}/workflows/${workflowKey}/templates`,
  );
  return data;
}

export async function createTaskTemplate(
  payload: TaskTemplateCreate,
): Promise<TaskTemplate> {
  const { data } = await client.post<TaskTemplate>(
    `${BASE}/templates`,
    payload,
  );
  return data;
}

export async function getTaskTemplate(key: string): Promise<TaskTemplate> {
  const { data } = await client.get<TaskTemplate>(`${BASE}/templates/${key}`);
  return data;
}

export async function updateTaskTemplate(
  key: string,
  payload: TaskTemplateUpdate,
): Promise<TaskTemplate> {
  const { data } = await client.put<TaskTemplate>(
    `${BASE}/templates/${key}`,
    payload,
  );
  return data;
}

export async function deleteTaskTemplate(key: string): Promise<void> {
  await client.delete(`${BASE}/templates/${key}`);
}

// -- Tasks --

export async function listTasks(
  offset = 0,
  limit = 50,
  filters?: { status?: string; category?: string; entity_type?: string; entity_key?: string },
): Promise<TaskItem[]> {
  const params: Record<string, string | number> = { offset, limit };
  if (filters?.status) params.status = filters.status;
  if (filters?.category) params.category = filters.category;
  if (filters?.entity_type) params.entity_type = filters.entity_type;
  if (filters?.entity_key) params.entity_key = filters.entity_key;
  const { data } = await client.get<TaskItem[]>(BASE, { params });
  return data;
}

export async function createTask(payload: TaskItemCreate): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(BASE, payload);
  return data;
}

export async function getTask(key: string): Promise<TaskItem> {
  const { data } = await client.get<TaskItem>(`${BASE}/${key}`);
  return data;
}

export async function updateTask(
  key: string,
  payload: TaskItemUpdate,
): Promise<TaskItem> {
  const { data } = await client.put<TaskItem>(`${BASE}/${key}`, payload);
  return data;
}

export async function deleteTask(key: string): Promise<void> {
  await client.delete(`${BASE}/${key}`);
}

/**
 * Build the authenticated URI of a task photo attachment.
 *
 * A task stores bare attachment ids in `photo_refs` (NFR-013 §2.2 / AC-09), not
 * URIs — a stored URI carries the tenant slug, which `TenantService.update_tenant`
 * re-derives on a rename, and the shipped `migrate_photo_refs` job rewrites that
 * exact shape back to ids. The shape mirrors `_base_uri()` in
 * `app/api/v1/attachments/tenant_router.py` and `diaryPhotoUri` next door; pass
 * the result to {@link AuthImage}, which sends the Bearer header a bare
 * `<img src>` could not.
 */
export function taskPhotoUri(attachmentId: string, size?: number): string {
  const slug = getActiveTenantSlug() ?? '';
  const uri = `/api/v1/t/${slug}/attachments/${attachmentId}`;
  return size ? `${uri}/thumbnails/${size}` : uri;
}

/**
 * Upload a photo for a task and return its attachment (REQ-006).
 *
 * The photo is *not* attached to the task here: the completion form stages the
 * returned `attachment_id` values and submits them with `completeTask`, which is
 * what writes `photo_refs` and what the `requires_photo` gate reads. Until #1339
 * the backend served no route at all for this, so a task with `requires_photo`
 * could not be completed.
 */
export async function uploadTaskPhoto(
  key: string,
  file: File,
): Promise<TaskPhoto> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post<TaskPhoto>(
    `${BASE}/${key}/photos`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return data;
}

export async function startTask(key: string): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(`${BASE}/${key}/start`);
  return data;
}

export async function completeTask(
  key: string,
  payload: TaskCompleteRequest,
): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(
    `${BASE}/${key}/complete`,
    payload,
  );
  return data;
}

export async function skipTask(key: string): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(`${BASE}/${key}/skip`);
  return data;
}

// -- Specialized queries --

export async function getTaskQueue(
  plantKey?: string,
): Promise<TaskItem[]> {
  const params: Record<string, string> = {};
  if (plantKey) params.plant_key = plantKey;
  const { data } = await client.get<TaskItem[]>(`${BASE}/queue`, { params });
  return data;
}

export async function getOverdueTasks(): Promise<TaskItem[]> {
  const { data } = await client.get<TaskItem[]>(`${BASE}/overdue`);
  return data;
}

export async function generateCareReminders(): Promise<{ created: number; skipped: number }> {
  const { data } = await client.post<{ created: number; skipped: number }>(`${BASE}/generate-care-reminders`);
  return data;
}

export async function getTasksForPlant(
  plantKey: string,
  status?: string,
): Promise<TaskItem[]> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  const { data } = await client.get<TaskItem[]>(
    `${BASE}/plants/${plantKey}`,
    { params },
  );
  return data;
}

// -- HST Validation --

export async function validateHST(payload: {
  task_name: string;
  current_phase: string;
  recent_hst_tasks?: Record<string, unknown>[];
  species_name?: string;
}): Promise<HSTValidationResult> {
  const { data } = await client.post<HSTValidationResult>(
    `${BASE}/validate-hst`,
    payload,
  );
  return data;
}

// -- Clone & Reopen --

export async function cloneTask(
  key: string,
  payload: TaskCloneRequest = {},
): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(
    `${BASE}/${key}/clone`,
    payload,
  );
  return data;
}

export async function reopenTask(key: string): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(`${BASE}/${key}/reopen`, {});
  return data;
}

// -- Batch Operations --

export async function batchStatusChange(
  taskKeys: string[],
  action: 'start' | 'complete' | 'skip',
  completionNotes?: string,
): Promise<BatchResponse> {
  const { data } = await client.post<BatchResponse>(
    `${BASE}/batch/status`,
    { task_keys: taskKeys, action, completion_notes: completionNotes },
  );
  return data;
}

export async function batchDelete(taskKeys: string[]): Promise<BatchResponse> {
  const { data } = await client.post<BatchResponse>(
    `${BASE}/batch/delete`,
    { task_keys: taskKeys },
  );
  return data;
}

export async function batchAssign(
  taskKeys: string[],
  assignedToUserKey: string,
): Promise<BatchResponse> {
  const { data } = await client.post<BatchResponse>(
    `${BASE}/batch/assign`,
    { task_keys: taskKeys, assigned_to_user_key: assignedToUserKey },
  );
  return data;
}

// -- Comments --

export async function listTaskComments(
  taskKey: string,
): Promise<TaskComment[]> {
  const { data } = await client.get<TaskComment[]>(
    `${BASE}/${taskKey}/comments`,
  );
  return data;
}

export async function createTaskComment(
  taskKey: string,
  commentText: string,
): Promise<TaskComment> {
  const { data } = await client.post<TaskComment>(
    `${BASE}/${taskKey}/comments`,
    { comment_text: commentText },
  );
  return data;
}

export async function updateTaskComment(
  taskKey: string,
  commentKey: string,
  commentText: string,
): Promise<TaskComment> {
  const { data } = await client.put<TaskComment>(
    `${BASE}/${taskKey}/comments/${commentKey}`,
    { comment_text: commentText },
  );
  return data;
}

export async function deleteTaskComment(
  taskKey: string,
  commentKey: string,
): Promise<void> {
  await client.delete(`${BASE}/${taskKey}/comments/${commentKey}`);
}

// -- Audit / History --

export async function getTaskHistory(
  taskKey: string,
): Promise<TaskAuditEntry[]> {
  const { data } = await client.get<TaskAuditEntry[]>(
    `${BASE}/${taskKey}/history`,
  );
  return data;
}

// -- Workflow Executions --

export async function getWorkflowExecution(
  key: string,
): Promise<WorkflowExecution> {
  const { data } = await client.get<WorkflowExecution>(
    `${BASE}/executions/${key}`,
  );
  return data;
}

export async function addTaskToWorkflow(
  executionKey: string,
  payload: WorkflowAddTaskRequest,
): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(
    `${BASE}/executions/${executionKey}/tasks`,
    payload,
  );
  return data;
}

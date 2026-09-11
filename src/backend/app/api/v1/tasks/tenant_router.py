from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.mapping import to_response
from app.api.v1.tasks.schemas import (
    BatchAssignRequest,
    BatchDeleteRequest,
    BatchResponse,
    BatchResultItem,
    BatchStatusRequest,
    CareReminderGenerationResult,
    HSTValidateRequest,
    HSTValidationResponse,
    PhaseReorderRequest,
    TaskAuditEntryResponse,
    TaskCloneRequest,
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCommentUpdate,
    TaskCompleteRequest,
    TaskCreate,
    TaskReopenRequest,
    TaskResponse,
    TaskTemplateCreate,
    TaskTemplateResponse,
    TaskTemplateUpdate,
    TaskUpdate,
    WorkflowAddTaskRequest,
    WorkflowExecutionListItem,
    WorkflowExecutionResponse,
    WorkflowInstantiateRequest,
    WorkflowPhaseCreate,
    WorkflowPhaseResponse,
    WorkflowPhaseSuggestion,
    WorkflowPhaseUpdate,
    WorkflowTemplateCreate,
    WorkflowTemplateResponse,
    WorkflowTemplateUpdate,
)
from app.common.auth import get_current_tenant, get_current_user, require_permission
from app.common.dependencies import get_task_entity_guard, get_task_service
from app.common.enums import TaskOrigin
from app.common.exceptions import ValidationError
from app.common.openapi_responses import NOT_FOUND_RESPONSE
from app.common.pagination import PaginationParams, get_pagination
from app.core.permissions import Action, ResourceType
from app.domain.engines.recurrence_engine import RecurrenceEngine
from app.domain.models.task import Task, TaskTemplate, WorkflowPhase, WorkflowTemplate
from app.domain.models.tenant_context import TenantContext
from app.domain.models.user import User
from app.domain.services.task_entity_guard import TaskEntityGuard
from app.domain.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"], responses=NOT_FOUND_RESPONSE)


def _wf_response(wt: WorkflowTemplate) -> WorkflowTemplateResponse:
    return to_response(wt, WorkflowTemplateResponse)


def _tt_response(tt: TaskTemplate) -> TaskTemplateResponse:
    return to_response(tt, TaskTemplateResponse)


def _phase_response(p: WorkflowPhase) -> WorkflowPhaseResponse:
    return to_response(p, WorkflowPhaseResponse)


def _task_response(t: Task) -> TaskResponse:
    return to_response(t, TaskResponse)


def _we_response(we) -> WorkflowExecutionResponse:
    return to_response(we, WorkflowExecutionResponse)


_ACTIVITY_TO_TASK_CATEGORY: dict[str, str] = {
    "training_hst": "training",
    "training_lst": "training",
    "pruning": "pruning",
    "ausgeizen": "ausgeizen",
    "transplant": "transplant",
    "harvest_prep": "harvest",
    "propagation": "maintenance",
    "inspection": "observation",
    "general": "maintenance",
}


# ── Workflow Templates ──


@router.get("/workflows", response_model=list[WorkflowTemplateResponse])
def list_workflows(
    pagination: PaginationParams = Depends(get_pagination),
    species_key: str | None = Query(None, description="Filter workflow templates by species key."),
    target_entity_type: str | None = Query(None, description="Filter by target entity type."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the tenant's workflow templates with usage stats (paginated)."""
    templates, _ = service.list_workflow_templates(
        pagination.offset,
        pagination.limit,
        species_key=species_key,
        tenant_key=ctx.tenant_key,
        target_entity_type=target_entity_type,
    )
    wf_keys = [wt.key for wt in templates if wt.key]
    usage_map = service.get_workflow_usage_stats(wf_keys) if wf_keys else {}
    result = []
    for wt in templates:
        resp = _wf_response(wt)
        stats = usage_map.get(wt.key or "", {})
        resp.species_name = stats.get("species_name", "")
        resp.assigned_entity_count = stats.get("entity_count", 0)
        result.append(resp)
    return result


@router.post("/workflows", response_model=WorkflowTemplateResponse, status_code=201)
def create_workflow(
    body: WorkflowTemplateCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Create a workflow template for the tenant."""
    wt = WorkflowTemplate(**body.model_dump(), tenant_key=ctx.tenant_key)
    created = service.create_workflow_template(wt)
    return _wf_response(created)


@router.get("/workflows/{key}", response_model=WorkflowTemplateResponse)
def get_workflow(
    key: Annotated[str, Path(description="Document key of the workflow template.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return a single workflow template by key."""
    return _wf_response(service.get_workflow_template(key, tenant_key=ctx.tenant_key))


@router.put("/workflows/{key}", response_model=WorkflowTemplateResponse)
def update_workflow(
    key: Annotated[str, Path(description="Document key of the workflow template.")],
    body: WorkflowTemplateUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Update a workflow template."""
    service.get_workflow_template(key, tenant_key=ctx.tenant_key)
    data = body.model_dump(exclude_none=True)
    updated = service.update_workflow_template(key, data)
    return _wf_response(updated)


@router.delete("/workflows/{key}", status_code=204)
def delete_workflow(
    key: Annotated[str, Path(description="Document key of the workflow template.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a workflow template."""
    service.get_workflow_template(key, tenant_key=ctx.tenant_key)
    service.delete_workflow_template(key)
    return Response(status_code=204)


@router.post("/workflows/{key}/duplicate", response_model=WorkflowTemplateResponse, status_code=201)
def duplicate_workflow(
    key: Annotated[str, Path(description="Document key of the workflow template to duplicate.")],
    name: str = Query(..., min_length=1, max_length=200, description="Name for the duplicated workflow template."),
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Duplicate a workflow template under a new name."""
    service.get_workflow_template(key, tenant_key=ctx.tenant_key)
    duplicated = service.duplicate_workflow_template(key, name, tenant_key=ctx.tenant_key)
    return _wf_response(duplicated)


@router.get("/workflows/{key}/executions", response_model=list[WorkflowExecutionListItem])
def list_workflow_executions(
    key: Annotated[str, Path(description="Document key of the workflow template.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List a workflow template's executions with enriched entity info."""
    service.get_workflow_template(key, tenant_key=ctx.tenant_key)
    return service.get_executions_for_template(key)


@router.post("/workflows/{key}/instantiate", response_model=WorkflowExecutionResponse, status_code=201)
def instantiate_workflow(
    key: Annotated[str, Path(description="Document key of the workflow template.")],
    body: WorkflowInstantiateRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Instantiate a workflow template for a target entity."""
    service.get_workflow_template(key, tenant_key=ctx.tenant_key)
    execution = service.instantiate_workflow(
        key,
        entity_key=body.entity_key,
        entity_type=body.entity_type,
    )
    return _we_response(execution)


# ── Workflow Phases ──


@router.get("/workflows/{wf_key}/phases", response_model=list[WorkflowPhaseResponse])
def list_workflow_phases(
    wf_key: Annotated[str, Path(description="Document key of the workflow template.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the phases of a workflow template."""
    service.get_workflow_template(wf_key, tenant_key=ctx.tenant_key)
    return [_phase_response(p) for p in service.get_workflow_phases(wf_key)]


@router.post("/workflows/{wf_key}/phases", response_model=WorkflowPhaseResponse, status_code=201)
def create_workflow_phase(
    wf_key: Annotated[str, Path(description="Document key of the workflow template.")],
    body: WorkflowPhaseCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Create a phase within a workflow template."""
    service.get_workflow_template(wf_key, tenant_key=ctx.tenant_key)
    phase = WorkflowPhase(**body.model_dump(), workflow_template_key=wf_key)
    return _phase_response(service.create_workflow_phase(phase))


@router.get("/phases/suggestions", response_model=list[WorkflowPhaseSuggestion])
def list_phase_suggestions(
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List suggested workflow phases for building templates."""
    return service.get_phase_suggestions()


@router.put("/phases/reorder", response_model=list[WorkflowPhaseResponse])
def reorder_phases(
    body: PhaseReorderRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Reorder a workflow template's phases."""
    phases = service.reorder_workflow_phases([item.model_dump() for item in body.phases], tenant_key=ctx.tenant_key)
    return [_phase_response(p) for p in phases]


@router.put("/phases/{key}", response_model=WorkflowPhaseResponse)
def update_workflow_phase(
    key: Annotated[str, Path(description="Document key of the workflow phase.")],
    body: WorkflowPhaseUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Update a workflow phase."""
    phase = service.get_workflow_phase(key)
    service.get_workflow_template(phase.workflow_template_key, tenant_key=ctx.tenant_key)
    return _phase_response(service.update_workflow_phase(key, body.model_dump(exclude_none=True)))


@router.delete("/phases/{key}", status_code=204)
def delete_workflow_phase(
    key: Annotated[str, Path(description="Document key of the workflow phase.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a workflow phase."""
    phase = service.get_workflow_phase(key)
    service.get_workflow_template(phase.workflow_template_key, tenant_key=ctx.tenant_key)
    service.delete_workflow_phase(key)
    return Response(status_code=204)


# ── Task Templates ──


@router.get("/workflows/{wf_key}/templates", response_model=list[TaskTemplateResponse])
def list_task_templates(
    wf_key: Annotated[str, Path(description="Document key of the workflow template.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the task templates of a workflow template."""
    service.get_workflow_template(wf_key, tenant_key=ctx.tenant_key)
    templates = service.get_task_templates(wf_key)
    return [_tt_response(tt) for tt in templates]


@router.post("/templates", response_model=TaskTemplateResponse, status_code=201)
def create_task_template(
    body: TaskTemplateCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Create a task template."""
    data = body.model_dump()
    cat = data.get("category", "")
    if cat in _ACTIVITY_TO_TASK_CATEGORY:
        data["category"] = _ACTIVITY_TO_TASK_CATEGORY[cat]
    tt = TaskTemplate(**data)
    created = service.create_task_template(tt, tenant_key=ctx.tenant_key)
    return _tt_response(created)


@router.get("/templates/{key}", response_model=TaskTemplateResponse)
def get_task_template(
    key: Annotated[str, Path(description="Document key of the task template.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return a single task template by key."""
    return _tt_response(service.get_task_template_for_read(key, tenant_key=ctx.tenant_key))


@router.put("/templates/{key}", response_model=TaskTemplateResponse)
def update_task_template(
    key: Annotated[str, Path(description="Document key of the task template.")],
    body: TaskTemplateUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Update a task template."""
    data = body.model_dump(exclude_none=True)
    updated = service.update_task_template(key, data, tenant_key=ctx.tenant_key)
    return _tt_response(updated)


@router.delete("/templates/{key}", status_code=204)
def delete_task_template(
    key: Annotated[str, Path(description="Document key of the task template.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a task template."""
    service.delete_task_template(key, tenant_key=ctx.tenant_key)
    return Response(status_code=204)


# ── Tasks ──


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    pagination: PaginationParams = Depends(get_pagination),
    status: str | None = Query(default=None, description="Filter by task status."),
    category: str | None = Query(default=None, description="Filter by task category."),
    entity_type: str | None = Query(default=None, description="Filter by linked entity type."),
    entity_key: str | None = Query(default=None, description="Filter by linked entity key."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the tenant's tasks (paginated), optionally filtered."""
    filters: dict[str, str] = {}
    if status:
        filters["status"] = status
    if category:
        filters["category"] = category
    if entity_type:
        filters["entity_type"] = entity_type
    if entity_key:
        filters["entity_key"] = entity_key
    tasks, _ = service.list_tasks(pagination.offset, pagination.limit, filters or None, tenant_key=ctx.tenant_key)
    return [_task_response(t) for t in tasks]


def _resolve_task_provenance(body: TaskCreate, user: User) -> tuple[TaskOrigin, str, str | None, str | None]:
    """Server-decide a task's FreeStyle provenance from the authenticated principal.

    ``origin`` is NEVER trusted from the request body (#1000-class spoofing); it is
    derived from the caller's ``account_type`` (REQ-023 M2M):

    * **Interactive user** (``account_type == "user"``) → ``origin`` forced to
      ``USER`` and the machine-provenance fields (``source`` / ``source_run_ref`` /
      ``external_ref``) cleared. A human's task carries no producer identity, and a
      human must not be able to write into the ``(tenant, source, external_ref)``
      idempotency namespace or masquerade as a pipeline.
    * **Service account** (``account_type == "service"``) → a machine producer. The
      body's ``origin`` is honoured but constrained to a *machine* origin
      (``SYSTEM`` / ``PIPELINE``), defaulting to ``PIPELINE``; the provenance fields
      are taken from the body. A service account that omits ``origin`` therefore
      still produces a properly-marked pipeline task.

    Returns the trusted ``(origin, source, source_run_ref, external_ref)`` tuple.
    """
    if user.account_type != "service":
        return TaskOrigin.USER, "", None, None
    machine_origins = {TaskOrigin.SYSTEM.value, TaskOrigin.PIPELINE.value}
    origin = TaskOrigin(body.origin) if body.origin in machine_origins else TaskOrigin.PIPELINE
    return origin, body.source or "", body.source_run_ref, body.external_ref


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    body: TaskCreate,
    response: Response,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
    entity_guard: TaskEntityGuard = Depends(get_task_entity_guard),
):
    """Create a task for the tenant, or upsert an idempotent FreeStyle re-post.

    This single endpoint serves both interactive users and machine producers
    (REQ-006 FreeStyle tasks, #1082):

    * ``origin`` is server-decided from the principal (see
      :func:`_resolve_task_provenance`) — an interactive caller can never spoof a
      machine origin or the ``(source, external_ref)`` dedup key.
    * A producer path (``origin != user``) is one-off: a ``recurrence_rule`` that
      the shared :class:`RecurrenceEngine` recognises as an actual recurrence is
      rejected with 422, and the recurrence fields are cleared so no producer task
      can ever spawn a follow-up. Recurrence is decided by the one recurrence
      authority, not a second parallel check (R-15 / ADR-008 will consolidate).
    * A producer supplying an ``external_ref`` gets idempotent upsert semantics
      scoped to ``(tenant_key, source, external_ref)``: a re-post updates and
      returns the existing task with **200** instead of creating a duplicate
      (201).
    """
    # SEC-I01 (#1102): the binding is caller-supplied and was never checked, so a
    # task could be bound — and a `has_task` edge written — to a *foreign*
    # tenant's plant, run, location or tank. Verified before the task is built, so
    # a refusal writes neither the task nor the edge. Foreign → 404, never 403:
    # a 403 would confirm the key names a real entity somewhere.
    entity_guard.verify(body.entity_type, body.entity_key, tenant_key=ctx.tenant_key)

    origin, source, source_run_ref, external_ref = _resolve_task_provenance(body, user)

    data = body.model_dump(exclude={"origin", "source", "source_run_ref", "external_ref"})
    if origin != TaskOrigin.USER:
        rule = data.get("recurrence_rule")
        if rule and RecurrenceEngine.next_occurrence(rule, datetime.now(UTC)) is not None:
            raise ValidationError(
                "A producer-created (FreeStyle) task is one-off; a recurrence_rule is not allowed on this path."
            )
        # Belt-and-braces: clear any recurrence residue so a producer task can
        # never spawn a follow-up, even if the rule did not parse as a recurrence.
        data["recurrence_rule"] = None
        data["recurrence_end_date"] = None

    task = Task(
        **data,
        tenant_key=ctx.tenant_key,
        origin=origin,
        source=source,
        source_run_ref=source_run_ref,
        external_ref=external_ref,
    )
    created, was_created = service.create_task_idempotent(task, actor_user_key=ctx.user_key)
    if not was_created:
        response.status_code = 200
    return _task_response(created)


@router.get("/queue", response_model=list[TaskResponse])
def get_task_queue(
    plant_key: str | None = Query(default=None, description="Restrict the queue to a single plant instance."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return the prioritized task queue, optionally scoped to one plant."""
    tasks = service.get_task_queue(plant_key, tenant_key=ctx.tenant_key)
    return [_task_response(t) for t in tasks]


@router.post("/generate-care-reminders", response_model=CareReminderGenerationResult)
def generate_care_reminders_now(
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
):
    """Manually trigger care reminder generation for THIS tenant (#1204).

    The route is addressed and permission-gated per tenant, so the work must be
    bounded the same way. Until #1204 it was not: ``ctx`` was resolved, checked
    and then never threaded in, so a grower exercising a permission granted in
    tenant A wrote task rows in B, C and D, and the returned counts described
    the whole installation's volume rather than the caller's.

    ``ctx.tenant_key`` is therefore passed through. The daily Celery beat keeps
    calling the same task with no argument for the installation-wide sweep.

    Calling a ``@celery.task``-decorated function directly bypasses Celery's
    request_stack setup and crashes with ``AttributeError`` on
    ``request_stack.push``. Using ``.apply()`` runs the task eagerly in-process
    while preserving the Celery context the task body relies on.
    """
    from app.tasks.care_tasks import generate_due_care_reminders

    eager = generate_due_care_reminders.apply(kwargs={"tenant_key": ctx.tenant_key})
    return eager.result


@router.get("/overdue", response_model=list[TaskResponse])
def get_overdue_tasks(
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the tenant's overdue tasks."""
    tasks = service.get_overdue_tasks(tenant_key=ctx.tenant_key)
    return [_task_response(t) for t in tasks]


@router.get("/plants/{plant_key}", response_model=list[TaskResponse])
def get_tasks_for_plant(
    plant_key: Annotated[str, Path(description="Document key of the plant instance.")],
    status: str | None = Query(default=None, description="Filter by task status."),
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List the tasks of a plant instance, optionally filtered by status.

    A ``plant_key`` belonging to another tenant yields an empty list — the tenant
    scope is enforced in the repository query (#927).
    """
    tasks = service.get_tasks_for_plant(plant_key, status, tenant_key=ctx.tenant_key)
    return [_task_response(t) for t in tasks]


@router.post("/validate-hst", response_model=HSTValidationResponse)
def validate_hst(
    body: HSTValidateRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Validate whether a High-Stress-Training task is allowed in the current phase."""
    return service.validate_hst(body.task_name, body.current_phase, body.recent_hst_tasks, body.species_name)


@router.post("/batch/status", response_model=BatchResponse)
def batch_status_change(
    body: BatchStatusRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Apply a status change to a batch of tasks."""
    succeeded, failed = service.batch_status_change(
        body.task_keys, body.action, body.completion_notes, tenant_key=ctx.tenant_key
    )
    return BatchResponse(succeeded=succeeded, failed=[BatchResultItem(key=f["key"], error=f["error"]) for f in failed])


@router.post("/batch/delete", response_model=BatchResponse)
def batch_delete(
    body: BatchDeleteRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a batch of tasks."""
    succeeded, failed = service.batch_delete(body.task_keys, tenant_key=ctx.tenant_key)
    return BatchResponse(succeeded=succeeded, failed=[BatchResultItem(key=f["key"], error=f["error"]) for f in failed])


@router.post("/batch/assign", response_model=BatchResponse)
def batch_assign(
    body: BatchAssignRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Assign a batch of tasks to a user."""
    succeeded, failed = service.batch_assign(body.task_keys, body.assigned_to_user_key, tenant_key=ctx.tenant_key)
    return BatchResponse(succeeded=succeeded, failed=[BatchResultItem(key=f["key"], error=f["error"]) for f in failed])


@router.get("/{key}", response_model=TaskResponse)
def get_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return a single task by key."""
    return _task_response(service.get_task(key, tenant_key=ctx.tenant_key))


@router.delete("/{key}", status_code=204)
def delete_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a task."""
    # ``delete_task`` resolves the key through the tenant guard before any read
    # or delete (GHSA-h5wp-r68x-97g8), so the former separate pre-check is gone.
    service.delete_task(key, tenant_key=ctx.tenant_key)
    return Response(status_code=204)


@router.put("/{key}", response_model=TaskResponse)
def update_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    body: TaskUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Update a task."""
    task = service.get_task(key, tenant_key=ctx.tenant_key)
    previous = task.model_copy(deep=True)
    data = body.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(task, field, value)
    updated = service.update_task(key, task, previous=previous, actor_user_key=ctx.user_key)
    return _task_response(updated)


@router.post("/{key}/start", response_model=TaskResponse)
def start_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Mark a task as started."""
    return _task_response(service.start_task(key, tenant_key=ctx.tenant_key))


@router.post("/{key}/complete", response_model=TaskResponse)
def complete_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    body: TaskCompleteRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Complete a task, propagating care-reminder confirmations where applicable."""
    completed = service.complete_task(
        key,
        body.completion_notes,
        body.actual_duration_minutes,
        body.photo_refs or None,
        body.difficulty_rating,
        body.quality_rating,
        tenant_key=ctx.tenant_key,
    )
    # The care-state consequences of a completed care-reminder task are domain
    # logic and live in the service (NFR-001): confirmation + edges, the
    # watering/fertilizing log and the next watering occurrence. The guard here is
    # only a presentation-layer short-circuit so no care service is built for a
    # plain task; the service re-checks it authoritatively.
    if completed.category == "care_reminder" and completed.entity_type == "plant_instance" and completed.entity_key:
        from app.common.dependencies import get_care_reminder_service

        get_care_reminder_service().record_care_task_completion(completed, tenant_key=ctx.tenant_key)
    return _task_response(completed)


@router.post("/{key}/skip", response_model=TaskResponse)
def skip_task(
    key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Skip a task, propagating care-reminder confirmations where applicable."""
    skipped = service.skip_task(key, tenant_key=ctx.tenant_key)
    # Mirrors the completion path above: the care-state consequences of a skipped
    # care-reminder task are domain logic and live in the service (NFR-001), which
    # also owns the tenant guard on the *plant* the task points at (SEC-001). The
    # guard here is only a presentation-layer short-circuit so no care service is
    # built for a plain task; the service re-checks it authoritatively.
    if skipped.category == "care_reminder" and skipped.entity_type == "plant_instance" and skipped.entity_key:
        from app.common.dependencies import get_care_reminder_service

        get_care_reminder_service().record_care_task_skip(skipped, tenant_key=ctx.tenant_key)
    return _task_response(skipped)


@router.post("/{key}/clone", response_model=TaskResponse, status_code=201)
def clone_task(
    key: Annotated[str, Path(description="Document key of the task to clone.")],
    body: TaskCloneRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Clone a task, optionally onto another entity and with a due-date offset."""
    cloned = service.clone_task(
        key,
        due_date_offset_days=body.due_date_offset_days,
        target_entity_key=body.target_entity_key,
        target_entity_type=body.target_entity_type,
        tenant_key=ctx.tenant_key,
    )
    return _task_response(cloned)


@router.post("/{key}/reopen", response_model=TaskResponse)
def reopen_task(
    key: Annotated[str, Path(description="Document key of the task to reopen.")],
    body: TaskReopenRequest | None = None,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Reopen a completed or skipped task."""
    return _task_response(service.reopen_task(key, tenant_key=ctx.tenant_key))


@router.get("/{task_key}/comments", response_model=list[TaskCommentResponse])
def list_task_comments(
    task_key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """List a task's comments.

    The service verifies the task against ``tenant_key`` itself and scopes the
    comment query with it (#927), so the redundant pre-check is gone.
    """
    comments = service.list_comments(task_key, tenant_key=ctx.tenant_key)
    return [to_response(c, TaskCommentResponse) for c in comments]


@router.post("/{task_key}/comments", response_model=TaskCommentResponse, status_code=201)
def create_task_comment(
    task_key: Annotated[str, Path(description="Document key of the task.")],
    body: TaskCommentCreate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.CREATE)),
    service: TaskService = Depends(get_task_service),
):
    """Add a comment to a task."""
    comment = service.create_comment(task_key, body.comment_text, created_by=ctx.user_key, tenant_key=ctx.tenant_key)
    return to_response(comment, TaskCommentResponse)


@router.put("/{task_key}/comments/{comment_key}", response_model=TaskCommentResponse)
def update_task_comment(
    task_key: Annotated[str, Path(description="Document key of the task.")],
    comment_key: Annotated[str, Path(description="Document key of the comment.")],
    body: TaskCommentUpdate,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Update a task comment."""
    comment = service.update_comment(task_key, comment_key, body.comment_text, tenant_key=ctx.tenant_key)
    return to_response(comment, TaskCommentResponse)


@router.delete("/{task_key}/comments/{comment_key}", status_code=204)
def delete_task_comment(
    task_key: Annotated[str, Path(description="Document key of the task.")],
    comment_key: Annotated[str, Path(description="Document key of the comment.")],
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.DELETE)),
    service: TaskService = Depends(get_task_service),
):
    """Delete a task comment."""
    service.delete_comment(task_key, comment_key, tenant_key=ctx.tenant_key)
    return Response(status_code=204)


@router.get("/{task_key}/history", response_model=list[TaskAuditEntryResponse])
def get_task_history(
    task_key: Annotated[str, Path(description="Document key of the task.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return a task's audit history."""
    entries = service.get_task_history(task_key, tenant_key=ctx.tenant_key)
    return [to_response(e, TaskAuditEntryResponse) for e in entries]


@router.get("/executions/{key}", response_model=WorkflowExecutionResponse)
def get_workflow_execution(
    key: Annotated[str, Path(description="Document key of the workflow execution.")],
    ctx: TenantContext = Depends(get_current_tenant),
    service: TaskService = Depends(get_task_service),
):
    """Return a single workflow execution by key."""
    return _we_response(service.get_workflow_execution(key))


@router.post("/executions/{key}/tasks", response_model=TaskResponse, status_code=201)
def add_task_to_workflow(
    key: Annotated[str, Path(description="Document key of the workflow execution.")],
    body: WorkflowAddTaskRequest,
    ctx: TenantContext = Depends(require_permission(ResourceType.TASK, Action.UPDATE)),
    service: TaskService = Depends(get_task_service),
):
    """Add an ad-hoc task to a running workflow execution."""
    task = Task(**body.model_dump(), tenant_key=ctx.tenant_key)
    created = service.add_task_to_workflow_execution(key, task)
    return _task_response(created)

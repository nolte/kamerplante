from datetime import UTC, datetime, timedelta

import structlog

from app.common.enums import AttachmentCategory, TaskOrigin
from app.common.exceptions import NotFoundError, ValidationError
from app.common.tenant_guard import verify_tenant_ownership, verify_tenant_read_access
from app.domain.engines.dependency_resolver import DependencyResolver
from app.domain.engines.hst_validator import HSTValidator
from app.domain.engines.recurrence_engine import RecurrenceEngine
from app.domain.interfaces.attachment_repository import IAttachmentRepository
from app.domain.interfaces.task_repository import ITaskRepository
from app.domain.models.task import (
    ChecklistItem,
    Task,
    TaskAuditEntry,
    TaskComment,
    TaskTemplate,
    WorkflowExecution,
    WorkflowPhase,
    WorkflowTemplate,
)
from app.domain.services.notification_propagation_service import NotificationPropagationService

logger = structlog.get_logger(__name__)

# ── Update allow-lists (mass assignment, #965) ──
#
# The three ``update_*`` methods below used to loop over the caller's dict and
# ``setattr`` every entry onto the loaded model. That is mass assignment: the
# request body decided which *fields* were written, not the service — and since
# no domain model sets ``validate_assignment`` (#968), none of those writes was
# validated either. ``BaseArangoRepository.update_fields`` already states the
# obligation these sets discharge: a partial update must be built from an
# explicit allow-list, never from a raw body.
#
# Each set is the field list the corresponding request schema exposes, so no
# reachable edit is lost. What they keep out is what an editor must never move:
# identity and audit fields (``key``, ``created_at``, ``updated_at``), the
# ownership marker ``tenant_key`` and the ``is_system`` flag that guards the
# global catalog, and foreign references no route exposes (``activity_key``,
# ``phase_definition_key``) and which are therefore unverified.

#: Fields ``update_workflow_template`` may write (mirrors ``WorkflowTemplateUpdate``).
WORKFLOW_TEMPLATE_UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "description",
        "version",
        "species_compatible",
        "growth_system",
        "difficulty_level",
        "category",
        "tags",
        "target_entity_types",
    }
)

#: Fields ``update_workflow_phase`` may write (mirrors ``WorkflowPhaseUpdate``).
#: ``workflow_template_key`` is deliberately absent: a phase belongs to the
#: workflow it was created under, and re-pointing it is how it would land in
#: another tenant's workflow.
WORKFLOW_PHASE_UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "description",
        "phase_order",
        "duration_days",
        "stress_tolerance",
        "trigger_phase",
    }
)

#: Fields ``update_task_template`` may write (mirrors ``TaskTemplateUpdate``).
#: ``workflow_template_key`` is included because moving a task template between
#: the caller's own workflows is a legitimate edit — and it is exactly the field
#: :meth:`TaskService._verify_workflow_template_reference` checks, so the check
#: stays live on the update path instead of being dead code.
#:
#: **It is not reachable over HTTP, and that is left as it is (#964, #965).**
#: ``TaskTemplateUpdate`` does not declare the field, so Pydantic's
#: ``extra='ignore'`` drops it from a request body. Declaring it would make the
#: reference check genuinely reachable rather than accidentally unnecessary —
#: but it would also *widen* the write surface, and not only in theory: the SPA's
#: two inline editors (the enabled switch and the day-offset field) send
#: ``{...template, enabled: …}``, and ``TaskTemplateResponse`` carries
#: ``workflow_template_key``. Declaring the field turns that spread from
#: "silently ignored" into a re-point written on every toggle and every
#: keystroke, and any client posting a stale or partial template would move or
#: orphan it. The field therefore stays undeclared, and the guard stays live for
#: the non-HTTP callers that do reach this method.
TASK_TEMPLATE_UPDATABLE_FIELDS = frozenset(
    {
        "name",
        "instruction",
        "category",
        "trigger_type",
        "trigger_phase",
        "days_offset",
        "stress_level",
        "estimated_duration_minutes",
        "requires_photo",
        "timer_duration_seconds",
        "timer_label",
        "tools_required",
        "skill_level",
        "optimal_time_of_day",
        "workflow_template_key",
        "workflow_phase_key",
        "sequence_order",
        "default_checklist",
        "require_all_checklist_items",
    }
)


#: Fields the *activity-plan editor* may write on a task template (#992).
#: Mirrors ``app.api.v1.activity_plans.schemas.TaskTemplateUpdateRequest``, which
#: is a strictly smaller surface than the workflow editor's ``TaskTemplateUpdate``
#: above: the activity-plan tab only switches an activity on and off, re-times it
#: and re-points its trigger phase. Kept as its own set rather than folded into
#: :data:`TASK_TEMPLATE_UPDATABLE_FIELDS` for two reasons — an allow-list mirrors
#: exactly one request schema, and ``enabled`` (which only this editor exposes)
#: would otherwise silently widen the workflow editor's write surface too.
ACTIVITY_PLAN_TASK_TEMPLATE_UPDATABLE_FIELDS = frozenset(
    {
        "enabled",
        "days_offset",
        "trigger_phase",
    }
)


#: Refusal raised when a caller tries to write a *child* of a globally seeded
#: system workflow (#965 item 3, #992). Deliberately the same ``ValidationError``
#: — HTTP 422, ``VALIDATION_ERROR`` — that ``update_workflow_template`` and
#: ``delete_workflow_template`` already raise on the parent itself, rather than a
#: third convention for what is the same rule one level down. It is not the 404 a
#: foreign or unknown parent produces: that answer means "you may not even see
#: this", while a system workflow is visible to every tenant on purpose and only
#: refuses to be written into. The message names the supported way forward,
#: because duplicating is what the caller actually wants and it still works.
#:
#: Shared by both child surfaces: the tenant-scoped ``/tasks`` child routes
#: (#984) and the activity-plan template routes (#992), which were developed in
#: parallel and deliberately defined this contract identically so that the second
#: one to land collapsed into a single definition rather than leaving the project
#: with two refusal wordings for one rule.
SYSTEM_WORKFLOW_CHILD_REFUSAL = (
    "Cannot modify system workflow templates. "
    "Duplicate the workflow first to get an editable copy of its phases and task templates."
)


def _allowed(data: dict, allowed_fields: frozenset[str]) -> dict:
    """Return only the entries of ``data`` the caller is allowed to write.

    Everything else is dropped rather than rejected, mirroring how the request
    schemas already treat an unknown field (Pydantic ``extra='ignore'``): the
    body cannot widen the set of fields an update touches.
    """
    return {field: value for field, value in data.items() if field in allowed_fields}


def _refuse_system_workflow(workflow: WorkflowTemplate) -> None:
    """Stop a child write whose parent is a globally seeded system workflow.

    The one place the "system templates are read-only" rule is applied to a
    *resolved* parent, so the three child-write paths (task-template create,
    task-template re-point, phase create/update/delete) cannot drift apart. The
    two parent-level guards in :meth:`TaskService.update_workflow_template` and
    :meth:`TaskService.delete_workflow_template` keep their own wording — they
    refuse a different verb on a different object — but raise the same error.
    """
    if workflow.is_system:
        raise ValidationError(SYSTEM_WORKFLOW_CHILD_REFUSAL)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    """Anchor a naive datetime to UTC so it can be compared safely.

    Persisted task datetimes carry mixed timezone-awareness: values parsed from
    a full ISO timestamp are aware, while a date-only ``due_date`` (the common
    case for a task created via the date picker) is stored naive. Comparing the
    two raises ``TypeError`` and would abort the surrounding flow (e.g. skip the
    recurrence follow-up on completion), so naive values are anchored to UTC.
    ``None`` passes through unchanged.
    """
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class TaskService:
    def __init__(
        self,
        repo: ITaskRepository,
        hst_validator: HSTValidator,
        dependency_resolver: DependencyResolver,
        recurrence: RecurrenceEngine | None = None,
        notification_propagation: NotificationPropagationService | None = None,
        attachment_repo: IAttachmentRepository | None = None,
    ) -> None:
        self._repo = repo
        # Resolves the `photo_refs` a completion carries (#1339 review). Optional
        # only so the many existing constructions of this service keep working;
        # the DI factory always supplies it, and `_verify_photo_refs` fails
        # closed rather than waving a reference through when it is absent.
        self._attachment_repo = attachment_repo
        self._hst = hst_validator
        self._deps = dependency_resolver
        self._recurrence = recurrence or RecurrenceEngine()
        #: Optional REQ-030 §4.2 coupling: when wired, task mutations synchronously
        #: propagate into the in-app notification centre (Issue #742). Left ``None``
        #: in unit tests that don't exercise the feedback loop — every call site is
        #: guarded so the core task flow is unaffected when it is absent.
        self._notifications = notification_propagation

    # ── Workflow Templates ──

    def list_workflow_templates(
        self,
        offset: int = 0,
        limit: int = 50,
        species_key: str | None = None,
        tenant_key: str = "",
        target_entity_type: str | None = None,
    ) -> tuple[list[WorkflowTemplate], int]:
        return self._repo.get_all_workflow_templates(
            offset,
            limit,
            species_key=species_key,
            tenant_key=tenant_key,
            target_entity_type=target_entity_type,
        )

    def get_workflow_usage_stats(self, wf_keys: list[str]) -> dict[str, dict]:
        """Return species_name and assigned plant count per workflow key."""
        return self._repo.get_workflow_usage_stats(wf_keys)

    def get_workflow_template(self, key: str, tenant_key: str = "") -> WorkflowTemplate:
        wt = self._repo.get_workflow_template_or_raise(key)
        if tenant_key:
            # Read access spans the hybrid catalog: the caller's own templates
            # PLUS globally seeded system templates (empty tenant_key), so the
            # detail/instantiate/duplicate routes work for the system templates
            # the list restores. Write ownership is guarded separately below.
            verify_tenant_read_access(wt, tenant_key, "WorkflowTemplate")
        return wt

    def create_workflow_template(self, template: WorkflowTemplate) -> WorkflowTemplate:
        return self._repo.create_workflow_template(template)

    def update_workflow_template(self, key: str, data: dict) -> WorkflowTemplate:
        """Apply an allow-listed partial edit to a workflow template (#965).

        ``data`` is filtered through :data:`WORKFLOW_TEMPLATE_UPDATABLE_FIELDS`
        before anything is assigned, so the body can no longer reach
        ``tenant_key`` (handing the template to another tenant, or emptying it
        into the global catalog) or ``is_system`` (clearing the very flag the
        guard below reads).
        """
        wt = self.get_workflow_template(key)
        if wt.is_system:
            # Read access is hybrid-catalog-wide, so the router guard now admits
            # system templates; writes must stay blocked (mirrors delete below).
            raise ValidationError("Cannot modify system workflow templates.")
        for field, value in _allowed(data, WORKFLOW_TEMPLATE_UPDATABLE_FIELDS).items():
            setattr(wt, field, value)
        return self._repo.update_workflow_template(key, wt)

    def delete_workflow_template(self, key: str) -> bool:
        wt = self.get_workflow_template(key)
        if wt.is_system:
            raise ValidationError("Cannot delete system workflow templates.")
        return self._repo.delete_workflow_template(key)

    def duplicate_workflow_template(self, key: str, new_name: str, tenant_key: str = "") -> WorkflowTemplate:
        """Duplicate a workflow template including all its task templates.

        The clone is owned by ``tenant_key`` (the duplicating tenant), never by
        the source's tenant. A tenant may duplicate a global system template,
        but the copy must be a private, tenant-scoped template — leaving it with
        the source's empty tenant_key would make it globally visible to every
        tenant now that the catalog list unions global rows.

        The copy itself is :meth:`_copy_workflow_template`'s, shared with the
        copy-on-write fork of #1003. This method's own contribution is the two
        decisions that differ there: the user-chosen name, and ``auto_generated``
        cleared — an explicit duplicate is an authored workflow from that point
        on, and must not answer the generated-plan lookup.
        """
        source = self.get_workflow_template(key, tenant_key=tenant_key)
        clone, _ = self._copy_workflow_template(
            source,
            name=new_name,
            tenant_key=tenant_key,
            auto_generated=False,
        )
        return clone

    def _copy_workflow_template(
        self,
        source: WorkflowTemplate,
        *,
        name: str,
        tenant_key: str,
        auto_generated: bool,
    ) -> tuple[WorkflowTemplate, dict[str, str]]:
        """Copy a workflow with its phases and task templates, for ``tenant_key``.

        The one copier in the service, used by both flows that produce a copy of
        a shared workflow: the explicit "duplicate first" the system-workflow
        refusal points at (#984), and the automatic copy-on-write fork a tenant's
        first edit of a generated activity plan produces (#1003). They differ
        only in the two arguments above, which is why this is one function rather
        than two that drift.

        Returns the created workflow **and the source-to-copy key map of its task
        templates**. The map is what the copy-on-write caller needs and the
        duplicate caller ignores: a client that still holds the shared plan's
        keys keeps addressing the originals after the fork, and the map is how
        such a key is redirected onto the row in the copy that it stands for. It
        is also persisted per row as ``TaskTemplate.source_template_key``, so the
        redirect survives beyond this call.

        ``is_system`` is deliberately not carried over: a copy of system data is
        the caller's own editable workflow, which is the entire point of
        offering the copy.
        """
        clone = WorkflowTemplate(
            name=name,
            tenant_key=tenant_key,
            description=source.description,
            species_compatible=list(source.species_compatible),
            species_key=source.species_key,
            lifecycle_key=source.lifecycle_key,
            growth_system=source.growth_system,
            difficulty_level=source.difficulty_level,
            category=source.category,
            tags=list(source.tags),
            auto_generated=auto_generated,
            total_duration_days=source.total_duration_days,
            skill_level_filter=source.skill_level_filter,
            target_entity_types=list(source.target_entity_types),
            source_workflow_key=source.key,
        )
        created_wf = self._repo.create_workflow_template(clone)

        # Clone phases and build key mapping
        source_phases = self._repo.get_phases_for_workflow(source.key or "")
        phase_key_map: dict[str, str] = {}
        for sp in source_phases:
            old_key = sp.key
            sp.key = None
            sp.workflow_template_key = created_wf.key or ""
            sp.created_at = None
            sp.updated_at = None
            new_phase = self._repo.create_phase(sp)
            phase_key_map[old_key or ""] = new_phase.key or ""

        template_key_map: dict[str, str] = {}
        templates = self._repo.get_task_templates_for_workflow(source.key or "")
        for tt in templates:
            source_key = tt.key
            tt.key = None
            tt.source_template_key = source_key
            tt.workflow_template_key = created_wf.key or ""
            if tt.workflow_phase_key and tt.workflow_phase_key in phase_key_map:
                tt.workflow_phase_key = phase_key_map[tt.workflow_phase_key]
            tt.created_at = None
            tt.updated_at = None
            created_tt = self._repo.create_task_template(tt)
            if source_key:
                template_key_map[source_key] = created_tt.key or ""

        return created_wf, template_key_map

    # ── Workflow Phases ──

    def get_workflow_phases(self, wf_key: str) -> list[WorkflowPhase]:
        self.get_workflow_template(wf_key)
        return self._repo.get_phases_for_workflow(wf_key)

    def get_workflow_phase(self, key: str) -> WorkflowPhase:
        return self._repo.get_phase_or_raise(key)

    def create_workflow_phase(self, phase: WorkflowPhase) -> WorkflowPhase:
        _refuse_system_workflow(self.get_workflow_template(phase.workflow_template_key))
        return self._repo.create_phase(phase)

    def update_workflow_phase(self, key: str, data: dict) -> WorkflowPhase:
        """Apply an allow-listed partial edit to a workflow phase (#965).

        Same shape as :meth:`update_task_template`: the phase carries no tenant
        of its own and is anchored on ``workflow_template_key``, which the
        allow-list keeps out of reach — re-pointing it is how a phase would move
        into another tenant's workflow.
        """
        phase = self.get_workflow_phase(key)
        self._refuse_writing_into_a_system_workflow(phase.workflow_template_key)
        for field, value in _allowed(data, WORKFLOW_PHASE_UPDATABLE_FIELDS).items():
            setattr(phase, field, value)
        return self._repo.update_phase(key, phase)

    def delete_workflow_phase(self, key: str) -> bool:
        phase = self.get_workflow_phase(key)
        self._refuse_writing_into_a_system_workflow(phase.workflow_template_key)
        return self._repo.delete_phase(key)

    def _refuse_writing_into_a_system_workflow(self, workflow_template_key: str | None) -> None:
        """Refuse an edit whose *parent* workflow is a system template (#965 item 3).

        Used wherever a child is edited or removed **in place** — the phase
        routes and the two task-template routes — which reach their parent
        through the child's own ``workflow_template_key``.

        Resolution is deliberately **tenant-blind**: only ``is_system`` is
        consulted, never the caller's tenant. That keeps this a pure system-data
        guard and leaves #965 item 1 (a *foreign tenant's* child, reachable
        because ``get_task_template`` is unanchored) exactly where it was.
        Anchoring on the parent's tenant is the larger change that needs the
        orphan-ownership field and its backfill; doing it here by accident would
        settle that question in the wrong place.

        A child with no parent key is left alone: there is nothing to anchor on,
        and refusing it here would be an orphan decision bolted onto the delete
        path — orphans do have an owner now (global, decided on #965), but that
        belongs to items 1/2/4 with their own field, not to this guard.
        """
        if not workflow_template_key:
            return
        _refuse_system_workflow(self.get_workflow_template(workflow_template_key))

    def reorder_workflow_phases(self, phase_orders: list[dict], *, tenant_key: str) -> list[WorkflowPhase]:
        """Reorder a workflow's phases, verifying each against ``tenant_key`` (#965 item 1).

        ``reorder_phases`` wrote ``phase_order`` by ``_key`` with no scoping at
        all, so a caller could re-sequence another tenant's workflow — the one
        write path in the phase group the #964 sweep left open. Every phase key
        is now resolved to its parent ``WorkflowTemplate`` (the only tenant anchor
        a phase has) and verified through :meth:`get_workflow_template`, which
        answers ``NotFoundError`` for a foreign or unknown parent — the same
        tenant check the per-key phase routes already perform, and never a
        cross-tenant oracle. A system workflow's phases are refused too, matching
        the sibling edit/delete routes: re-sequencing seeded phases would move
        them for every tenant.

        ``tenant_key`` is keyword-only (#948): a route that forgets to thread it
        fails loudly rather than compiling away the isolation.
        """
        for item in phase_orders:
            phase = self.get_workflow_phase(item["key"])
            self.get_workflow_template(phase.workflow_template_key, tenant_key=tenant_key)
            self._refuse_writing_into_a_system_workflow(phase.workflow_template_key)
        return self._repo.reorder_phases(phase_orders)

    def get_phase_suggestions(self) -> list[dict]:
        return self._repo.get_phase_suggestions()

    # ── Task Templates ──

    def get_task_templates(self, wf_key: str) -> list[TaskTemplate]:
        return self._repo.get_task_templates_for_workflow(wf_key)

    def get_task_template(self, key: str) -> TaskTemplate:
        return self._repo.get_task_template_or_raise(key)

    def get_task_template_for_read(self, key: str, *, tenant_key: str) -> TaskTemplate:
        """Load a task template the caller is allowed to read (SEC-001, #965).

        The write paths (:meth:`update_task_template`/:meth:`delete_task_template`)
        grew an entity-level tenant check when ``TaskTemplate`` gained its own
        ``tenant_key``, but the single-template ``GET`` was left on the unanchored
        :meth:`get_task_template` primitive — a member of *any* tenant could fetch
        another tenant's private template by key, and the keys are ArangoDB
        auto-generated and enumerable. This mirrors the write guard exactly: the
        entity's own ``tenant_key`` is verified against the caller through
        :func:`verify_tenant_read_access`, so a foreign template answers
        ``NotFoundError`` (404, never a cross-tenant oracle) while the global
        catalogue (``tenant_key == ""``) stays readable so #324 is not re-broken.

        The bare :meth:`get_task_template` stays as the internal primitive the
        three write/enrichment methods compose with their own parent-based checks;
        this is the anchored read for the HTTP ``GET``. ``tenant_key`` is
        keyword-only (#948) so a route that forgets to thread it fails loudly.
        """
        tt = self.get_task_template(key)
        verify_tenant_read_access(tt, tenant_key, "TaskTemplate")
        return tt

    def _verify_workflow_template_reference(self, workflow_template_key: str | None, tenant_key: str) -> None:
        """Resolve a caller-supplied ``workflow_template_key`` before it is written (#965).

        ``TaskTemplate`` carries no ``tenant_key``; its parent ``WorkflowTemplate``
        does, and is therefore the anchor. The key went unchecked on both write
        paths: the repository builds a ``wf_contains`` edge from it on create,
        and ``get_task_templates_for_workflow`` filters on the *field*, so a
        foreign key attaches the caller's template to another tenant's workflow —
        an edge written across the isolation boundary, and a task that tenant's
        next instantiation will generate.

        Resolution goes through :meth:`get_workflow_template`, so an unknown key
        and a foreign tenant's key produce the identical ``NotFoundError`` (404,
        never 403 — no cross-tenant oracle). A template with **no** parent at all
        is a supported standalone state and is left alone.

        A globally seeded **system** workflow resolves — read access spans the
        hybrid catalog on purpose — but then refuses the write (#965 item 3).
        Until that was added, the "cannot modify system workflow templates" rule
        the two sibling guards enforce on the parent stopped at the parent: a
        tenant could hang a task template off "Tomato Standard", and because
        ``get_task_templates_for_workflow`` filters on the denormalised parent
        field, it surfaced for *every* tenant. The refusal is that same
        ``ValidationError`` (422), never the 404 — the caller may read this
        workflow, they may only not write into it.
        """
        if not workflow_template_key:
            return
        _refuse_system_workflow(self.get_workflow_template(workflow_template_key, tenant_key=tenant_key))

    def _verify_workflow_phase_reference(self, workflow_phase_key: str | None, tenant_key: str) -> None:
        """Resolve a caller-supplied ``workflow_phase_key`` before it is written (SEC-003).

        A task template may name the phase it belongs to. ``workflow_phase_key`` is
        in :data:`TASK_TEMPLATE_UPDATABLE_FIELDS` and settable on create, but was
        never checked — only ``workflow_template_key`` was — so a caller could store
        a reference to a **foreign** tenant's phase on their own template. It is not
        a cross-tenant write (the template stays the caller's) and leaks nothing on
        the paths traced today, but it stores an unvalidated cross-boundary
        reference a future join could dereference, exactly the class the update
        allow-list excludes ``phase_definition_key``/``activity_key`` to avoid.

        The phase's only tenant anchor is its parent ``WorkflowTemplate``, so the
        check hangs there through :meth:`get_workflow_template` — a foreign or
        unknown phase/parent answers ``NotFoundError`` (404, no cross-tenant
        oracle); a phase with no parent, or none supplied, is left alone.
        """
        if not workflow_phase_key:
            return
        phase = self.get_workflow_phase(workflow_phase_key)
        if not phase.workflow_template_key:
            return
        self.get_workflow_template(phase.workflow_template_key, tenant_key=tenant_key)

    def create_task_template(self, template: TaskTemplate, *, tenant_key: str) -> TaskTemplate:
        """Create a task template for ``tenant_key``, verifying its parent workflow (#965).

        ``tenant_key`` is required and keyword-only, following #948: a route that
        forgets to thread it does not compile away silently, it fails loudly.

        The caller's tenant is **stamped onto the entity** (#965 item 1). Since
        ``TaskTemplate`` grew its own ``tenant_key`` field, a template created here
        records its owner rather than being un-owned — a standalone template (no
        parent workflow) is now the caller's, not a globally editable orphan. The
        value comes from the auth/path context, never the request body, mirroring
        how ``Task`` and ``WorkflowTemplate`` are stamped at their construction
        sites. ``update``/``delete`` verify this field back against the caller.
        """
        self._verify_workflow_template_reference(template.workflow_template_key, tenant_key)
        self._verify_workflow_phase_reference(template.workflow_phase_key, tenant_key)
        template.tenant_key = tenant_key
        return self._repo.create_task_template(template)

    def update_task_template(self, key: str, data: dict, *, tenant_key: str) -> TaskTemplate:
        """Apply an allow-listed partial edit to a task template (#965).

        Two defects met here. ``data`` was assigned field by field with no
        allow-list, so the request body chose what got written; and
        ``workflow_template_key`` is among the fields an edit may legitimately
        move, so the update path could re-point a template into another tenant's
        workflow just as create could. The allow-list bounds *which* fields are
        written, the reference check bounds *which values* the parent field may
        take.

        Three answers, layered so the earlier one wins (#965 items 1 and 3):

        * **Foreign → 404.** The entity's own ``tenant_key`` (added for item 1) is
          verified against the caller through :func:`verify_tenant_read_access`,
          which raises ``NotFoundError`` for a template owned by another tenant —
          no cross-tenant oracle. It admits the global catalogue (``tenant_key ==
          ""``) so #324 is not re-broken. This runs *first*, so a foreign template
          is refused before it is ever classified by system-ness.
        * **System → 422.** The template's **current** parent decides whether the
          edit may happen at all: a seeded template of "Tomato Standard" is system
          data, so renaming or re-timing it is the same refusal as attaching a new
          one, only arriving by a different verb.
        * **Own → proceed.** The **target** parent is then checked as before, so a
          move can neither leave a system workflow's contents editable nor land in
          one.
        """
        tt = self.get_task_template(key)
        verify_tenant_read_access(tt, tenant_key, "TaskTemplate")
        self._refuse_writing_into_a_system_workflow(tt.workflow_template_key)
        fields = _allowed(data, TASK_TEMPLATE_UPDATABLE_FIELDS)
        if "workflow_template_key" in fields:
            self._verify_workflow_template_reference(fields["workflow_template_key"], tenant_key)
        if "workflow_phase_key" in fields:
            self._verify_workflow_phase_reference(fields["workflow_phase_key"], tenant_key)
        for field, value in fields.items():
            setattr(tt, field, value)
        return self._repo.update_task_template(key, tt)

    def delete_task_template(self, key: str, *, tenant_key: str) -> bool:
        """Remove a task template the caller owns, unless it is system data (#965 items 1, 3).

        The same three layered answers as :meth:`update_task_template`, and in the
        same order — foreign → 404, system → 422, own → proceed:

        * **Foreign → 404.** The entity's own ``tenant_key`` is verified against
          the caller (:func:`verify_tenant_read_access`); another tenant's template
          answers ``NotFoundError``, never a cross-tenant oracle. The global
          catalogue (``tenant_key == ""``) is admitted so #324 stands.
        * **System → 422.** Deleting a seeded template of a system workflow removes
          it for every tenant, the same modification the two parent-level guards
          already refuse.

        ``tenant_key`` is required and keyword-only (#948): the anchor item 1 was
        missing, so a route that forgets to thread it fails loudly rather than
        deleting across the isolation boundary.
        """
        tt = self.get_task_template(key)
        verify_tenant_read_access(tt, tenant_key, "TaskTemplate")
        self._refuse_writing_into_a_system_workflow(tt.workflow_template_key)
        return self._repo.delete_task_template(key)

    # ── Task Templates of an activity plan (tenant-anchored, #992) ──

    def _resolve_task_template_for_tenant_write(self, key: str, tenant_key: str) -> TaskTemplate:
        """Load a task template only if ``tenant_key`` may write it (#992).

        ``TaskTemplate`` carries no ``tenant_key`` of its own — ownership is not
        stored on the entity, exactly like ``Location``/``Slot``, which are
        verified through their parent site. The only anchor is the parent
        ``WorkflowTemplate`` behind ``workflow_template_key``, so the predicate
        hangs there. Hanging it on the template itself would match nothing and
        refuse every caller while looking like a working guard.

        Three answers, and the difference between them is deliberate:

        * **Foreign or unknown parent → 404.** Resolution goes through
          :meth:`get_workflow_template`, whose ``verify_tenant_read_access``
          answers ``NotFoundError`` for both, so this route cannot be used as a
          cross-tenant existence oracle.
        * **System workflow → 422.** A globally seeded workflow is visible to
          every tenant on purpose (#324: the strict direction must not hide the
          global catalogue), so it resolves — and then refuses the *write*, with
          the shared :data:`SYSTEM_WORKFLOW_CHILD_REFUSAL`. Deleting one of its
          task templates would remove it for every tenant.
        * **No parent at all → 404.** An activity plan's task templates always
          have one: ``ActivityPlanService.generate_plan`` assigns
          ``tt.workflow_template_key = wt.key`` to every template before it is
          persisted, and the seeder skips any template whose workflow it cannot
          resolve. A parentless template is therefore an unreachable state here,
          and it has no owner — so it is refused rather than left writable by
          anyone, which is what "no anchor, so no refusal" would mean on a route
          that has no tenant scoping of its own. The answer is the 404 rather
          than a 422 because "who owns this" has no answer: telling the caller
          the key exists but is unowned is the oracle the 404 avoids. The state
          is logged so it fails loudly where loudness helps — in the operator's
          log, not in an attacker's response body.

        * **A shared generated plan → the caller's private copy of it (#1003).**
          What ``ActivityPlanService`` persists is global (``tenant_key == ""``,
          ``is_system == False``), so #992 let every tenant write it — and every
          tenant write the *same* one. The write is not refused, because a
          generated plan is the user's working surface and they have no reason
          to expect it to be shared; it is redirected. See
          :meth:`_private_copy_for_a_shared_plan`.

        The caller's *own* templates pass through untouched.
        """
        template = self.get_task_template(key)
        parent_key = template.workflow_template_key
        if not parent_key:
            logger.warning(
                "task_template_without_parent_workflow",
                task_template_key=key,
                tenant_key=tenant_key,
            )
            raise NotFoundError("TaskTemplate", key)
        parent = self.get_workflow_template(parent_key, tenant_key=tenant_key)
        if parent.is_system:
            raise ValidationError(SYSTEM_WORKFLOW_CHILD_REFUSAL)
        if tenant_key and not parent.tenant_key:
            return self._private_copy_for_a_shared_plan(parent, template, tenant_key)
        return template

    def _private_copy_for_a_shared_plan(
        self,
        shared_plan: WorkflowTemplate,
        template: TaskTemplate,
        tenant_key: str,
    ) -> TaskTemplate:
        """Redirect a write on a shared generated plan onto the caller's own copy (#1003).

        The plan ``ActivityPlanService`` generates is one global object that
        every tenant growing that species reads. #992 anchored the *route* on the
        parent workflow but left that object writable by all of them, so tenant
        A switching an activity off switched it off for tenant B, silently. The
        answer taken is **copy-on-write**: the generated plan stays a shared
        template, and a tenant's first write materialises a private copy which
        that tenant works on from then on.

        Three properties this has to hold, in order of how easily they break:

        1. **Idempotence.** The copy is materialised once. Every later write
           resolves the existing copy through the same lookup the *read* path
           uses (:meth:`ITaskRepository.get_auto_generated_workflow_for_species`),
           so the plan the caller edits and the plan the caller is shown can
           never be two different objects.
        2. **Stale keys keep working.** After the fork a client still holds the
           shared plan's task-template keys, and the SPA sends them on the next
           toggle. Such a key is mapped onto the copy through
           ``source_template_key`` rather than refused, so an open tab does not
           start writing the shared object again — which would be the original
           defect, reintroduced through the back door.
        3. **The source is never written.** Nothing here touches
           ``shared_plan``; the copy is built from it and only the copy is
           returned.

        A shared workflow that is *not* a generated plan cannot be forked — the
        copy would be unreachable, because the lookup that finds it keys on
        ``auto_generated`` and ``species_key``. That state is unreachable in
        practice (``auto_generated`` is set only by ``ActivityPlanEngine``, and
        ``generate_plan`` always stamps the species), so it is refused loudly
        with the same 404 an unowned template gets rather than written through,
        which would leave the shared object mutable exactly as before.
        """
        if not (shared_plan.auto_generated and shared_plan.species_key):
            logger.warning(
                "shared_workflow_is_not_a_generated_plan",
                workflow_template_key=shared_plan.key,
                task_template_key=template.key,
                tenant_key=tenant_key,
            )
            raise NotFoundError("TaskTemplate", template.key or "")

        copy = self._repo.get_auto_generated_workflow_for_species(
            shared_plan.species_key,
            tenant_key=tenant_key,
        )
        if copy is None or copy.tenant_key != tenant_key:
            copy, template_key_map = self._copy_workflow_template(
                shared_plan,
                name=shared_plan.name,
                tenant_key=tenant_key,
                auto_generated=True,
            )
            logger.info(
                "activity_plan_forked_on_write",
                source_workflow_key=shared_plan.key,
                workflow_template_key=copy.key,
                tenant_key=tenant_key,
            )
            copied_key = template_key_map.get(template.key or "")
            if copied_key:
                return self._repo.get_task_template_or_raise(copied_key)
            raise NotFoundError("TaskTemplate", template.key or "")

        for candidate in self._repo.get_task_templates_for_workflow(copy.key or ""):
            if candidate.source_template_key == template.key:
                return candidate

        # The caller's copy exists but no longer carries this activity — they
        # deleted it from their own plan while a client still showed it. The key
        # is genuinely gone *for this tenant*, so it answers like any other key
        # they may not reach, and the shared template stays untouched.
        logger.info(
            "activity_plan_template_absent_from_private_copy",
            source_template_key=template.key,
            workflow_template_key=copy.key,
            tenant_key=tenant_key,
        )
        raise NotFoundError("TaskTemplate", template.key or "")

    def update_activity_plan_task_template(self, key: str, data: dict, *, tenant_key: str) -> TaskTemplate:
        """Apply the activity-plan editor's partial edit, anchored on the parent workflow (#992).

        ``tenant_key`` is required and keyword-only, following #948: a route that
        forgets to thread it fails loudly instead of silently authorising
        everyone — which is precisely how the previous version of this edit, made
        in the API layer straight against the repository, let any authenticated
        user retime any tenant's task template.

        The write lands on the template the resolution **returned**, not on the
        key the caller sent (#1003). The two differ whenever the caller addressed
        a shared generated plan: the resolution then hands back the equivalent
        row in that tenant's private copy, and writing ``key`` here would put the
        edit straight back onto the shared object the copy exists to protect.
        """
        template = self._resolve_task_template_for_tenant_write(key, tenant_key)
        for field, value in _allowed(data, ACTIVITY_PLAN_TASK_TEMPLATE_UPDATABLE_FIELDS).items():
            setattr(template, field, value)
        return self._repo.update_task_template(template.key or key, template)

    def delete_activity_plan_task_template(self, key: str, *, tenant_key: str) -> bool:
        """Remove a task template of an activity plan, anchored on the parent workflow (#992).

        A delete on a shared generated plan is a write like any other and forks
        the same way (#1003): the caller's private copy is materialised and the
        activity is removed **from the copy**, leaving the shared template whole
        for every other tenant. Refusing instead was the alternative considered —
        it would have been the only editor action a tenant could not perform on
        their own plan, and "remove this activity" is what an activity plan is
        for.
        """
        template = self._resolve_task_template_for_tenant_write(key, tenant_key)
        return self._repo.delete_task_template(template.key or key)

    # ── Workflow Instantiation ──

    def instantiate_workflow(
        self,
        template_key: str,
        entity_key: str,
        entity_type: str,
    ) -> WorkflowExecution:
        """Generate tasks from a workflow template for a specific entity.

        Tasks whose trigger_phase does not match the current phase are created
        with status 'dormant' for plant_instance entities and 'pending' for
        all other entity types (which have no phase concept).
        """
        wt = self.get_workflow_template(template_key)
        templates = self._repo.get_task_templates_for_workflow(template_key)

        if not templates:
            raise ValidationError(f"Workflow '{wt.name}' has no task templates.")

        execution = WorkflowExecution(
            workflow_template_key=template_key,
            entity_key=entity_key,
            entity_type=entity_type,
        )
        execution = self._repo.create_workflow_execution(execution)

        now = datetime.now(UTC)
        for tt in templates:
            checklist = [ChecklistItem(text=item.text, done=False, order=item.order) for item in tt.default_checklist]

            status = "pending"
            # recurrence-owner-ok: a workflow-template offset — it says when the FIRST task
            # of this run falls due relative to instantiation, not when the next one does.
            # Template offsets are named outside boundary 1 by the phase-0 counting
            # definition; task recurrence runs through RecurrenceEngine in
            # _create_next_recurring_task.
            due_date = now + timedelta(days=tt.days_offset) if tt.days_offset else None
            # Only plant_instance entities support phase-based dormant tasks
            if (
                entity_type == "plant_instance"
                and tt.trigger_phase
                and tt.trigger_type in ("phase_entry", "days_after_phase")
            ):
                status = "dormant"
                due_date = None

            task = Task(
                name=tt.name,
                name_de=tt.name_de,
                instruction=tt.instruction,
                instruction_de=tt.instruction_de,
                category=tt.category,
                entity_key=entity_key,
                entity_type=entity_type,
                due_date=due_date,
                status=status,
                priority="medium",
                skill_level=tt.skill_level,
                stress_level=tt.stress_level,
                estimated_duration_minutes=tt.estimated_duration_minutes,
                requires_photo=tt.requires_photo,
                timer_duration_seconds=tt.timer_duration_seconds,
                timer_label=tt.timer_label,
                checklist=checklist,
                trigger_phase=tt.trigger_phase,
                template_key=tt.key,
                workflow_execution_key=execution.key,
                activity_key=tt.activity_key,
            )
            created_task = self._repo.create_task(task)

            if tt.activity_key and created_task.key:
                self._repo.create_task_activity_edge(
                    created_task.key,
                    tt.activity_key,
                )

        return execution

    # ── Notification propagation (REQ-030 §4.2, #742) ──

    def _propagate(self, action) -> None:  # noqa: ANN001 — Callable[[NotificationPropagationService], None]
        """Run a notification-propagation ``action`` when the coupling is wired.

        Swallows and logs any propagation error so a notification-centre hiccup can
        never abort the underlying task mutation (NFR-007 graceful degradation).
        """
        if self._notifications is None:
            return
        try:
            action(self._notifications)
        except Exception:  # pragma: no cover - defensive; propagation is best-effort
            import structlog

            structlog.get_logger().warning("task_notification_propagation_failed")

    # ── Task CRUD ──

    def list_tasks(
        self,
        offset: int = 0,
        limit: int = 50,
        filters: dict | None = None,
        tenant_key: str = "",
    ) -> tuple[list[Task], int]:
        return self._repo.get_all_tasks(offset, limit, filters, tenant_key=tenant_key)

    @staticmethod
    def _require_tenant_key(tenant_key: str, method: str) -> None:
        """Reject the empty-``tenant_key`` sentinel before a tenant-scoped load.

        Mirrors ``BaseRepository._require_tenant_key`` at the service layer so a
        caller that forgets the argument fails **closed** (GHSA-h5wp-r68x-97g8).
        The ownership check used to be conditional on a truthy ``tenant_key`` with
        a ``""`` default, so an omitted argument silently skipped it and read
        across every tenant. Raising here removes that fragile invariant.
        """
        if not tenant_key:
            raise ValueError(
                f"{method} is tenant-scoped and requires a non-empty tenant_key (GHSA-h5wp-r68x-97g8 tenant isolation)."
            )

    def get_task(self, key: str, *, tenant_key: str) -> Task:
        self._require_tenant_key(tenant_key, "get_task")
        task = self._repo.get_task_or_raise(key)
        verify_tenant_ownership(task, tenant_key, "Task")
        return task

    def create_task(self, task: Task, *, actor_user_key: str = "") -> Task:
        created = self._repo.create_task(task)
        self._propagate(lambda p: p.sync_task_due_notification(created, recipient_user_key=actor_user_key))
        if created.assigned_to_user_key:
            self._propagate(lambda p: p.on_task_reassigned(created, previous_user_key=None))
        return created

    def create_task_idempotent(self, task: Task, *, actor_user_key: str = "") -> tuple[Task, bool]:
        """Create a task, or upsert the existing one for an idempotent producer re-post.

        The FreeStyle producer contract (#1082 AC-3). A machine producer
        (``origin != user``) that supplies an ``external_ref`` gets *upsert*
        semantics scoped to ``(tenant_key, source, external_ref)``: re-posting the
        same reference refreshes and returns the existing task instead of
        duplicating it. Because the lookup is anchored on the caller's own
        ``tenant_key`` and ``source`` (see
        :meth:`ITaskRepository.find_task_by_external_ref`), it is never a
        cross-tenant existence oracle and two producers cannot collide.

        Interactive tasks (``origin == user``) and producer tasks without an
        ``external_ref`` fall straight through to :meth:`create_task`, so this is a
        safe superset of the plain create path and the single POST endpoint can
        route both through it.

        Returns ``(task, created)`` where ``created`` is ``False`` for an
        idempotent hit — the endpoint maps that onto HTTP 200 (vs 201 on create).
        """
        if task.origin != TaskOrigin.USER and task.source and task.external_ref:
            existing = self._repo.find_task_by_external_ref(
                tenant_key=task.tenant_key,
                source=task.source,
                external_ref=task.external_ref,
            )
            if existing is not None and existing.key:
                refreshed = self._apply_freestyle_refresh(existing, task)
                updated = self._repo.update_task(existing.key, refreshed)
                self._propagate(lambda p: p.sync_task_due_notification(updated, recipient_user_key=actor_user_key))
                return updated, False
        return self.create_task(task, actor_user_key=actor_user_key), True

    @staticmethod
    def _apply_freestyle_refresh(existing: Task, incoming: Task) -> Task:
        """Refresh a re-posted FreeStyle task's presentation fields in place.

        A producer re-post updates what the producer authored — the free text, the
        due date, the category, the run reference — while preserving everything the
        *system* owns on the existing task: its key, its lifecycle ``status`` and
        the user's own progress (started/completed timestamps, notes, ratings), its
        ``created_at`` and its ``(source, external_ref)`` identity. That way a
        re-post never resurrects a task the user already completed or silently
        re-homes it onto another entity.
        """
        existing.name = incoming.name
        existing.name_de = incoming.name_de
        existing.instruction = incoming.instruction
        existing.instruction_de = incoming.instruction_de
        existing.category = incoming.category
        existing.priority = incoming.priority
        existing.due_date = incoming.due_date
        existing.scheduled_time = incoming.scheduled_time
        existing.tags = incoming.tags
        existing.source_run_ref = incoming.source_run_ref
        return existing

    def update_task(self, key: str, task: Task, *, previous: Task | None = None, actor_user_key: str = "") -> Task:
        """Persist a task edit and propagate it into the notification centre (#742).

        A due-date/title edit refreshes the task's ``task.due`` notification in
        place (owned by ``actor_user_key`` — the editing user threaded from the API
        context); a change of assignee additionally delivers a fresh assignment
        notification to the new member. The ``previous`` snapshot (pre-edit task)
        lets the coupling detect a reassignment.
        """
        updated = self._repo.update_task(key, task)
        self._propagate(lambda p: p.sync_task_due_notification(updated, recipient_user_key=actor_user_key))
        prev_assignee = previous.assigned_to_user_key if previous is not None else None
        if prev_assignee != updated.assigned_to_user_key:
            self._propagate(lambda p: p.on_task_reassigned(updated, previous_user_key=prev_assignee))
        return updated

    def delete_task(self, key: str, *, tenant_key: str) -> bool:
        # ``get_task`` verifies tenant ownership before anything is read or
        # deleted, so ``self._repo.delete_task`` below is only ever reached after
        # a tenant-checked load (GHSA-h5wp-r68x-97g8).
        task = self.get_task(key, tenant_key=tenant_key)
        allowed = {"pending", "skipped", "cancelled", "dormant"}
        if task.status not in allowed:
            raise ValidationError(
                f"Cannot delete task in status '{task.status}'. "
                f"Only {', '.join(sorted(allowed))} tasks can be deleted.",
            )
        deleted = self._repo.delete_task(key)
        if deleted:
            self._propagate(lambda p: p.on_task_deleted(task))
        return deleted

    def add_photo_ref(self, key: str, url: str, *, tenant_key: str) -> Task:
        task = self.get_task(key, tenant_key=tenant_key)
        task.photo_refs.append(url)
        return self._repo.update_task(key, task)

    def start_task(self, key: str, *, tenant_key: str) -> Task:
        task = self.get_task(key, tenant_key=tenant_key)
        if task.status != "pending":
            raise ValidationError(f"Cannot start task in status '{task.status}'.")
        task.status = "in_progress"
        task.started_at = datetime.now(UTC)
        return self._repo.update_task(key, task)

    def _verify_photo_refs(
        self,
        refs: list[str],
        already_attached: list[str],
        *,
        tenant_key: str,
    ) -> None:
        """Refuse a photo reference that is not this tenant's task attachment.

        ``TaskCompleteRequest.photo_refs`` is a bare ``list[str]`` and was
        forwarded verbatim, so ``['x']`` satisfied a ``requires_photo`` task and
        a foreign attachment id could be pinned onto one's own task. The diary
        sibling has resolved every reference through the attachment catalogue
        since REQ-050; this is the same rule for REQ-006.

        A reference already stored on the task is not re-checked: it passed once,
        and re-validating it would make an unrelated completion fail after a
        legitimate attachment was later erased under NFR-011 retention.

        Unknown, foreign and wrong-category all raise the **same**
        ``ValidationError`` (422): distinguishing them would confirm that an id
        exists somewhere else in the installation.

        Args:
            refs: The references the caller sent.
            already_attached: References the task already carries.
            tenant_key: Owning tenant of the task.

        Raises:
            ValidationError: If a new reference does not resolve to a
                ``TASK``-category attachment of this tenant, or if no attachment
                catalogue is configured to judge it.
        """
        known = set(already_attached)
        added = [ref for ref in dict.fromkeys(refs) if ref not in known]
        if not added:
            return

        if self._attachment_repo is None:
            # Fail closed. A service assembled without the resolver cannot judge
            # a reference, and accepting it "for now" is how a guard ends up
            # inert in production while every test still passes.
            raise ValidationError(
                "Task photo references cannot be validated: no attachment catalogue is configured.",
                details=[{"field": "photo_refs", "message": "attachment lookup unavailable"}],
            )

        for ref in added:
            attachment = self._attachment_repo.get(ref, tenant_key)
            if attachment is None or attachment.category != AttachmentCategory.TASK:
                raise ValidationError(
                    f"'{ref}' is not a task photo of this tenant.",
                    details=[{"field": "photo_refs", "message": f"unknown task attachment '{ref}'"}],
                )

    def complete_task(
        self,
        key: str,
        completion_notes: str | None = None,
        actual_minutes: int | None = None,
        photo_refs: list[str] | None = None,
        difficulty_rating: int | None = None,
        quality_rating: int | None = None,
        *,
        tenant_key: str,
    ) -> Task:
        task = self.get_task(key, tenant_key=tenant_key)
        if task.status not in ("pending", "in_progress"):
            raise ValidationError(f"Cannot complete task in status '{task.status}'.")

        if task.requires_photo and not task.photo_refs and not photo_refs:
            raise ValidationError("This task requires at least one photo before completion.")

        if photo_refs:
            self._verify_photo_refs(photo_refs, task.photo_refs, tenant_key=tenant_key)
            # Order-preserving dedup across what is already stored and what
            # arrives. The completion form seeds its list from the task's own
            # `photo_refs`, so reopening a completed task and completing it again
            # used to append every existing ref a second time — `[a, a, b]` in the
            # document and duplicate React keys in the gallery (#1339 review).
            known = set(task.photo_refs)
            task.photo_refs.extend(ref for ref in dict.fromkeys(photo_refs) if ref not in known)

        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        if completion_notes:
            task.completion_notes = completion_notes
        if actual_minutes is not None:
            task.actual_duration_minutes = actual_minutes
        if difficulty_rating is not None:
            task.difficulty_rating = difficulty_rating
        if quality_rating is not None:
            task.quality_rating = quality_rating

        updated = self._repo.update_task(key, task)

        # Reschedule dependents if late. Coerce both operands to timezone-aware
        # UTC first: a date-only due_date is stored naive and would otherwise
        # crash the comparison (and abort the recurrence spawn below).
        due_aware = _as_aware_utc(task.due_date)
        completed_aware = _as_aware_utc(task.completed_at)
        if due_aware and completed_aware and completed_aware > due_aware:
            self._reschedule_dependents(key, task)

        # Create next recurring task if applicable
        if task.recurrence_rule:
            self._create_next_recurring_task(updated)

        # Mark the task's open due notification done (badge drops, #742).
        self._propagate(lambda p: p.on_task_completed(updated))

        return updated

    def _reschedule_dependents(self, key: str, task: Task) -> None:
        # ``tenant_key`` is part of the guard, not an optional extra: the
        # repository rejects the empty sentinel since #927, and a task without a
        # tenant has no tenant-scoped sibling set to reschedule against. Such a
        # task simply has no dependents here rather than triggering a scan across
        # every tenant's tasks.
        if task.entity_key and task.entity_type and task.tenant_key:
            all_tasks = self._repo.get_tasks_for_entity(
                task.entity_type,
                task.entity_key,
                task.tenant_key,
            )
        else:
            all_tasks = []
        deps = self._repo.get_blocking_tasks(key)
        task_dicts = [
            {"key": t.key, "status": t.status, "priority": t.priority, "due_date": t.due_date} for t in all_tasks
        ]
        dep_dicts = [{"from_key": key, "to_key": d["key"]} for d in deps]
        # Anchor naive datetimes (a date-only due_date is stored without tzinfo)
        # so the resolver's completed_at/original_due comparison cannot crash.
        rescheduled = self._deps.reschedule_dependents(
            key,
            _as_aware_utc(task.completed_at),
            _as_aware_utc(task.due_date),
            task_dicts,
            dep_dicts,
        )
        for r in rescheduled:
            dep_task = self._repo.get_task_by_key(r["task_key"])
            if dep_task:
                dep_task.due_date = datetime.fromisoformat(r["new_due_date"])
                self._repo.update_task(r["task_key"], dep_task)

    def _create_next_recurring_task(self, completed_task: Task) -> Task | None:
        """Create the next instance of a recurring task after completion."""
        if not completed_task.recurrence_rule:
            return None

        # Check end date
        if completed_task.recurrence_end_date and datetime.now(UTC) >= completed_task.recurrence_end_date:
            return None

        # Compute the next due date from the recurrence rule via the shared engine.
        next_dt = self._recurrence.next_occurrence(completed_task.recurrence_rule, datetime.now(UTC))
        if next_dt is None:
            return None

        new_task = Task(
            tenant_key=completed_task.tenant_key,
            name=completed_task.name,
            name_de=completed_task.name_de,
            instruction=completed_task.instruction,
            instruction_de=completed_task.instruction_de,
            category=completed_task.category,
            entity_key=completed_task.entity_key,
            entity_type=completed_task.entity_type,
            due_date=next_dt,
            scheduled_time=completed_task.scheduled_time,
            status="pending",
            priority=completed_task.priority,
            skill_level=completed_task.skill_level,
            stress_level=completed_task.stress_level,
            estimated_duration_minutes=completed_task.estimated_duration_minutes,
            requires_photo=completed_task.requires_photo,
            timer_duration_seconds=completed_task.timer_duration_seconds,
            timer_label=completed_task.timer_label,
            tags=list(completed_task.tags),
            checklist=[
                ChecklistItem(text=item.text, done=False, order=item.order) for item in completed_task.checklist
            ],
            assigned_to_user_key=completed_task.assigned_to_user_key,
            recurrence_rule=completed_task.recurrence_rule,
            recurrence_end_date=completed_task.recurrence_end_date,
            parent_recurring_task_key=completed_task.key,
        )
        return self._repo.create_task(new_task)

    def _compute_next_recurrence(self, rule: str, after: datetime) -> datetime | None:
        """Delegate to the shared :class:`RecurrenceEngine` (kept for callers/tests).

        The recurrence algorithm now lives in one place so the generic task path
        and the fixed-interval care path share a single implementation (#510).
        """
        return self._recurrence.next_occurrence(rule, after)

    def skip_task(self, key: str, *, tenant_key: str) -> Task:
        task = self.get_task(key, tenant_key=tenant_key)
        if task.status not in ("pending", "in_progress"):
            raise ValidationError(f"Cannot skip task in status '{task.status}'.")
        task.status = "skipped"
        task.completed_at = datetime.now(UTC)
        updated = self._repo.update_task(key, task)
        self._propagate(lambda p: p.on_task_completed(updated))
        return updated

    # ── Clone ──

    def clone_task(
        self,
        key: str,
        due_date_offset_days: int | None = None,
        target_entity_key: str | None = None,
        target_entity_type: str | None = None,
        *,
        tenant_key: str,
    ) -> Task:
        source = self.get_task(key, tenant_key=tenant_key)
        due_date = None
        if due_date_offset_days is not None:
            # recurrence-owner-ok: a clone offset the caller chooses for one new task. It
            # produces a single due date and establishes no cadence — the cloned task's own
            # recurrence_rule, if it has one, is advanced by RecurrenceEngine.
            due_date = datetime.now(UTC) + timedelta(days=due_date_offset_days)

        entity_key = target_entity_key or source.entity_key
        entity_type = target_entity_type or source.entity_type

        new_task = Task(
            tenant_key=source.tenant_key,
            name=source.name,
            name_de=source.name_de,
            instruction=source.instruction,
            instruction_de=source.instruction_de,
            category=source.category,
            entity_key=entity_key,
            entity_type=entity_type,
            due_date=due_date,
            status="pending",
            priority=source.priority,
            skill_level=source.skill_level,
            stress_level=source.stress_level,
            estimated_duration_minutes=source.estimated_duration_minutes,
            requires_photo=source.requires_photo,
            timer_duration_seconds=source.timer_duration_seconds,
            timer_label=source.timer_label,
            tags=list(source.tags),
            checklist=[ChecklistItem(text=item.text, done=False, order=item.order) for item in source.checklist],
        )
        return self._repo.create_task(new_task)

    # ── Reopen ──

    def reopen_task(self, key: str, *, tenant_key: str) -> Task:
        task = self.get_task(key, tenant_key=tenant_key)
        if task.status not in ("completed", "skipped"):
            raise ValidationError(
                f"Cannot reopen task in status '{task.status}'. Only completed or skipped tasks can be reopened.",
            )
        task.reopened_from_status = task.status
        task.reopened_at = datetime.now(UTC)
        task.status = "pending"
        task.completed_at = None
        task.actual_duration_minutes = None
        task.completion_notes = None
        task.difficulty_rating = None
        task.quality_rating = None
        return self._repo.update_task(key, task)

    # ── Batch Operations ──
    #
    # Found by the #948 write-surface sweep. Every *single*-task route resolves
    # its key with ``service.get_task(key, tenant_key=ctx.tenant_key)`` first —
    # the line each router has to remember — and all three batch routes forgot
    # it, while taking their ``task_keys`` from the request body. A member of
    # tenant A could therefore complete, skip, delete or reassign another
    # tenant's tasks in bulk. ``tenant_key`` is now required and keyword-only on
    # all three, and each key is resolved through the tenant guard before
    # anything is written. A foreign key lands in ``failed`` with the same
    # "not found" text an unknown key produces, so the batch envelope is not a
    # cross-tenant oracle either.

    def batch_status_change(
        self,
        task_keys: list[str],
        action: str,
        completion_notes: str | None = None,
        *,
        tenant_key: str,
    ) -> tuple[list[str], list[dict]]:
        succeeded: list[str] = []
        failed: list[dict] = []
        for tk in task_keys:
            try:
                # Each mutating call now enforces the tenant guard itself; the
                # explicit resolve is kept so the unknown-action branch below is
                # also tenant-checked and never becomes an existence oracle.
                self.get_task(tk, tenant_key=tenant_key)
                if action == "start":
                    self.start_task(tk, tenant_key=tenant_key)
                elif action == "complete":
                    self.complete_task(tk, completion_notes=completion_notes, tenant_key=tenant_key)
                elif action == "skip":
                    self.skip_task(tk, tenant_key=tenant_key)
                else:
                    failed.append({"key": tk, "error": f"Unknown action: {action}"})
                    continue
                succeeded.append(tk)
            except (NotFoundError, ValidationError) as e:
                failed.append({"key": tk, "error": str(e)})
        return succeeded, failed

    def batch_delete(self, task_keys: list[str], *, tenant_key: str) -> tuple[list[str], list[dict]]:
        succeeded: list[str] = []
        failed: list[dict] = []
        for tk in task_keys:
            try:
                self.delete_task(tk, tenant_key=tenant_key)
                succeeded.append(tk)
            except (NotFoundError, ValidationError) as e:
                failed.append({"key": tk, "error": str(e)})
        return succeeded, failed

    def batch_assign(
        self,
        task_keys: list[str],
        assigned_to_user_key: str,
        *,
        tenant_key: str,
    ) -> tuple[list[str], list[dict]]:
        succeeded: list[str] = []
        failed: list[dict] = []
        for tk in task_keys:
            try:
                task = self.get_task(tk, tenant_key=tenant_key)
                previous_assignee = task.assigned_to_user_key
                task.assigned_to_user_key = assigned_to_user_key
                updated = self._repo.update_task(tk, task)
                if previous_assignee != assigned_to_user_key:
                    self._propagate(
                        lambda p, u=updated, prev=previous_assignee: p.on_task_reassigned(u, previous_user_key=prev)
                    )
                succeeded.append(tk)
            except (NotFoundError, ValidationError) as e:
                failed.append({"key": tk, "error": str(e)})
        return succeeded, failed

    # ── Comments ──

    def list_comments(self, task_key: str, *, tenant_key: str) -> list[TaskComment]:
        """A task's comments, scoped to ``tenant_key`` (#927).

        The task lookup verifies ownership and answers 404 for a foreign key; the
        repository applies the same tenant predicate to the comment query, so the
        isolation survives a caller that forgets the first step.
        """
        self.get_task(task_key, tenant_key=tenant_key)
        return self._repo.get_comments_for_task(task_key, tenant_key=tenant_key)

    def create_comment(self, task_key: str, text: str, created_by: str, *, tenant_key: str) -> TaskComment:
        self.get_task(task_key, tenant_key=tenant_key)  # ensure task exists and belongs to the tenant
        comment = TaskComment(
            task_key=task_key,
            comment_text=text,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        return self._repo.create_comment(comment)

    def update_comment(self, task_key: str, comment_key: str, text: str, *, tenant_key: str) -> TaskComment:
        self.get_task(task_key, tenant_key=tenant_key)  # ensure task exists and belongs to the tenant
        comment = self._repo.get_comment_or_raise(comment_key)
        if comment.task_key != task_key:
            raise ValidationError("Comment does not belong to this task.")
        comment.comment_text = text
        comment.updated_at = datetime.now(UTC)
        return self._repo.update_comment(comment_key, comment)

    def delete_comment(self, task_key: str, comment_key: str, *, tenant_key: str) -> bool:
        self.get_task(task_key, tenant_key=tenant_key)  # ensure task exists and belongs to the tenant
        comment = self._repo.get_comment_or_raise(comment_key)
        if comment.task_key != task_key:
            raise ValidationError("Comment does not belong to this task.")
        return self._repo.delete_comment(comment_key)

    # ── Audit / History ──

    def get_task_history(self, task_key: str, *, tenant_key: str) -> list[TaskAuditEntry]:
        self.get_task(task_key, tenant_key=tenant_key)  # ensure task exists and belongs to the tenant
        return self._repo.get_audit_entries_for_task(task_key)

    def _record_audit(
        self,
        task_key: str,
        action: str,
        changed_by: str = "system",
        field: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> TaskAuditEntry:
        entry = TaskAuditEntry(
            task_key=task_key,
            changed_at=datetime.now(UTC),
            changed_by=changed_by,
            action=action,
            field=field,
            old_value=old_value,
            new_value=new_value,
        )
        return self._repo.create_audit_entry(entry)

    # ── Dormant Task Activation ──

    def activate_dormant_tasks_for_phase(
        self, plant_key: str, phase_name: str, *, trigger: object = None
    ) -> list[Task]:
        """Activate dormant tasks whose trigger_phase matches the new phase.

        ``trigger`` is part of the shared post-transition callback contract
        (:meth:`PhaseService.register_on_transition`) but is irrelevant here — a
        dormant task is activated by reaching its phase regardless of whether the
        transition was automatic or manual — so it is accepted and ignored.
        """
        dormant_tasks = self._repo.get_dormant_tasks_for_phase(plant_key, phase_name)
        activated: list[Task] = []
        now = datetime.now(UTC)
        for task in dormant_tasks:
            task.status = "pending"
            if task.trigger_phase and task.trigger_phase == phase_name:
                # For phase_entry triggers: due now
                # For days_after_phase: offset from now
                tt = self._repo.get_task_template_by_key(task.template_key or "")
                if tt and tt.trigger_type == "days_after_phase" and tt.days_offset:
                    # recurrence-owner-ok: a `days_after_phase` template offset measured from the
                    # phase entry. It fires once per transition for a dormant task and advances no
                    # cadence.
                    task.due_date = now + timedelta(days=tt.days_offset)
                else:
                    task.due_date = now
            else:
                task.due_date = now
            updated = self._repo.update_task(task.key or "", task)
            activated.append(updated)
        return activated

    # ── Add Task to Workflow Execution ──

    def add_task_to_workflow_execution(self, execution_key: str, task: Task) -> Task:
        execution = self.get_workflow_execution(execution_key)
        task.workflow_execution_key = execution_key
        task.entity_key = task.entity_key or execution.entity_key
        task.entity_type = task.entity_type or execution.entity_type
        return self._repo.create_task(task)

    # ── Task Queue ──

    def get_task_queue(self, plant_key: str | None = None, *, tenant_key: str) -> list[Task]:
        """The prioritised task queue of one tenant (#927).

        Both branches are tenant-scoped: the per-plant one because ``plant_key``
        comes from a query parameter and used to select across tenants, the
        unfiltered one because it used to return the whole installation's pending
        tasks.
        """
        if plant_key:
            tasks = self._repo.get_tasks_for_plant(plant_key, "pending", tenant_key=tenant_key)
        else:
            tasks, _ = self._repo.get_pending_tasks(0, 200, tenant_key=tenant_key)

        # Deduplicate care_reminder tasks: keep only the newest per entity_key + name suffix
        tasks = self._deduplicate_care_tasks(tasks)

        task_dicts = [
            {
                "key": t.key,
                "status": t.status,
                "priority": t.priority,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in tasks
        ]
        deps: list[dict] = []
        for t in tasks:
            blocking = self._repo.get_blocking_tasks(t.key or "")
            for b in blocking:
                deps.append({"from_key": b["key"], "to_key": t.key})

        ready_dicts = self._deps.get_ready_tasks(task_dicts, deps)
        ready_keys = {d["key"] for d in ready_dicts}
        return [t for t in tasks if t.key in ready_keys]

    @staticmethod
    def _deduplicate_care_tasks(tasks: list[Task]) -> list[Task]:
        """Remove duplicate care_reminder tasks for the same plant + reminder type.

        Groups by ``(tenant_key, full task name)`` — the name (e.g.
        "CANNA-0320-X90 — watering") is unique per plant+type, and pinning the
        tenant_key ensures two tenants whose plants happen to share a display
        name + reminder type are never collapsed into one (cross-tenant dedup
        gap, #509). Within each group, prefers tasks with entity_key set (newer
        format) over those without (legacy data), then by newest due_date/created_at.
        """
        result: list[Task] = []
        care_groups: dict[tuple[str, str], list[Task]] = {}

        for task in tasks:
            if task.category == "care_reminder":
                # Group by (tenant, full name) — tenant-scoped so the read-time
                # safety net can never merge two tenants' care tasks (#509).
                care_groups.setdefault((task.tenant_key, task.name), []).append(task)
            else:
                result.append(task)

        def _as_aware(value: datetime | None) -> datetime:
            """Coerce a datetime to timezone-aware UTC for safe comparison.

            Persisted tasks can carry a mix of timezone-aware (parsed from ISO
            strings with an offset) and timezone-naive ``due_date``/``created_at``
            values. Comparing the two directly raises ``TypeError`` and would
            crash the whole task queue, so naive values are anchored to UTC and
            missing values fall back to the minimum instant.
            """
            if value is None:
                return datetime.min.replace(tzinfo=UTC)
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        for group in care_groups.values():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Prefer tasks with entity_key, then newest by due_date/created_at
                def _sort_key(t):  # noqa: E501
                    return (
                        1 if t.entity_key else 0,
                        _as_aware(t.due_date),
                        _as_aware(t.created_at),
                    )

                best = max(group, key=_sort_key)
                result.append(best)

        return result

    def get_overdue_tasks(self, *, tenant_key: str) -> list[Task]:
        """Overdue tasks of one tenant (#927)."""
        tasks = self._repo.get_overdue_tasks(tenant_key=tenant_key)
        return self._deduplicate_care_tasks(tasks)

    def get_tasks_for_plant(self, plant_key: str, status: str | None = None, *, tenant_key: str) -> list[Task]:
        """A plant's tasks, scoped to ``tenant_key`` (#927).

        ``plant_key`` is not resolved against the caller's tenant here — the
        repository's tenant predicate is what turns a foreign key into an empty
        list instead of the other tenant's task list.
        """
        return self._repo.get_tasks_for_plant(plant_key, status, tenant_key=tenant_key)

    def get_tasks_for_entity(
        self,
        entity_type: str,
        entity_key: str,
        tenant_key: str,
        status: str | None = None,
    ) -> list[Task]:
        return self._repo.get_tasks_for_entity(entity_type, entity_key, tenant_key, status)

    # ── HST Validation ──

    def validate_hst(
        self,
        task_name: str,
        current_phase: str,
        recent_hst_tasks: list[dict],
        species_name: str = "",
    ) -> dict:
        return self._hst.validate(
            task_name,
            current_phase,
            recent_hst_tasks,
            species_name,
        )

    # ── Workflow Execution ──

    def get_workflow_execution(self, key: str) -> WorkflowExecution:
        return self._repo.get_workflow_execution_or_raise(key)

    def get_executions_for_template(self, template_key: str) -> list[dict]:
        return self._repo.get_executions_for_template(template_key)

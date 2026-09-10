"""``complete_task`` resolves its ``photo_refs`` instead of trusting them (#1339).

``TaskCompleteRequest.photo_refs`` is a bare ``list[str]`` and was forwarded into
the document verbatim. Two consequences, both measured on the shipped code:

* **any string was a photo.** ``['x']`` satisfied a ``requires_photo`` task, so
  the REQ-006 §Foto-Upload-Enforcement gate — an acceptance criterion — could be
  cleared without ever uploading anything; and a *foreign* tenant's attachment id
  could be pinned onto one's own task. The diary sibling has resolved every
  reference through the attachment catalogue since REQ-050
  (``plant_diary_service._verify_photo_refs``); this is the same rule for tasks.
* **completing twice duplicated every ref.** The completion form seeds its list
  from the task's own ``photo_refs``, and the service ``extend``-ed without
  dedup, so reopening and completing again produced ``[a, a, b]`` — duplicate
  React keys in the gallery and a growing document.

Driven against a hand-written attachment catalogue rather than ``MagicMock``: a
mock answers ``get`` with another mock whose ``category`` is a mock too, which
compares unequal to everything and would make the guard look effective no matter
what it did (#1155).

No TC-ID: a service invariant, not a user-facing case.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.common.enums import AttachmentCategory
from app.common.exceptions import NotFoundError, ValidationError
from app.domain.engines.dependency_resolver import DependencyResolver
from app.domain.engines.hst_validator import HSTValidator
from app.domain.models.attachment import Attachment
from app.domain.models.task import Task
from app.domain.services.task_service import TaskService

TENANT = "tenant-a"


def _attachment(key: str, tenant_key: str, category: AttachmentCategory) -> Attachment:
    return Attachment(
        _key=key,
        tenant_key=tenant_key,
        category=category,
        mime_type="image/jpeg",
        byte_size=3,
        original_filename="p.jpg",
        storage_key=f"tenants/{tenant_key}/{category.value}/{key}.jpg",
        sha256="deadbeef",
        created_by="user-a",
    )


class FakeAttachmentRepo:
    """Answers like the real catalogue: tenant-scoped, category-bearing."""

    def __init__(self, attachments: list[Attachment]) -> None:
        self._by_key = {a.key: a for a in attachments}

    def get(self, key: str, tenant_key: str) -> Attachment | None:
        found = self._by_key.get(key)
        if found is None or found.tenant_key != tenant_key:
            return None
        return found


class FakeTaskRepo:
    def __init__(self, task: Task) -> None:
        self.task = task
        self.updated: list[Task] = []

    def get_task_or_raise(self, key: str) -> Task:
        if key != self.task.key:
            raise NotFoundError("Task", key)
        return self.task

    def update_task(self, key: str, task: Task) -> Task:
        self.updated.append(task)
        self.task = task
        return task

    # Everything `complete_task` reaches for after the write. Empty is honest
    # here: this task has no dependents and no recurrence, which is what the
    # invariants under test are about.
    def get_tasks_for_entity(self, *_args, **_kwargs) -> list:
        return []

    def get_blocking_tasks(self, *_args, **_kwargs) -> list:
        return []

    def get_task_by_key(self, key: str) -> Task | None:
        return self.task if key == self.task.key else None


def _task(**overrides) -> Task:
    values = {
        "_key": "task-1",
        "tenant_key": TENANT,
        "name": "Topping",
        "status": "pending",
        "requires_photo": False,
        "photo_refs": [],
        "due_date": datetime.now(UTC),
    }
    values.update(overrides)
    return Task(**values)


def _service(task: Task, attachments: list[Attachment]) -> tuple[TaskService, FakeTaskRepo]:
    repo = FakeTaskRepo(task)
    service = TaskService(
        repo,
        HSTValidator(),
        DependencyResolver(),
        attachment_repo=FakeAttachmentRepo(attachments),
    )
    return service, repo


class TestAReferenceMustResolve:
    def test_a_made_up_reference_is_refused(self) -> None:
        """The string that used to satisfy `requires_photo` without an upload."""
        service, repo = _service(_task(requires_photo=True), [])

        with pytest.raises(ValidationError):
            service.complete_task("task-1", None, None, ["x"], None, None, tenant_key=TENANT)

        assert repo.updated == []

    def test_a_foreign_attachment_is_refused_exactly_like_an_unknown_one(self) -> None:
        """Distinguishing them would confirm the id exists somewhere else."""
        foreign = _attachment("att-foreign", "tenant-b", AttachmentCategory.TASK)
        service, _repo = _service(_task(), [foreign])

        with pytest.raises(ValidationError) as theirs:
            service.complete_task("task-1", None, None, ["att-foreign"], None, None, tenant_key=TENANT)
        with pytest.raises(ValidationError) as missing:
            service.complete_task("task-1", None, None, ["att-nope"], None, None, tenant_key=TENANT)

        assert str(theirs.value).replace("att-foreign", "X") == str(missing.value).replace("att-nope", "X")

    def test_an_attachment_of_another_category_is_refused(self) -> None:
        """A plant gallery photo is not a task photo, however valid it is."""
        plant = _attachment("att-plant", TENANT, AttachmentCategory.PLANT)
        service, _repo = _service(_task(), [plant])

        with pytest.raises(ValidationError):
            service.complete_task("task-1", None, None, ["att-plant"], None, None, tenant_key=TENANT)

    def test_a_real_task_attachment_is_accepted(self) -> None:
        own = _attachment("att-1", TENANT, AttachmentCategory.TASK)
        service, _repo = _service(_task(requires_photo=True), [own])

        completed = service.complete_task("task-1", None, None, ["att-1"], None, None, tenant_key=TENANT)

        assert completed.photo_refs == ["att-1"]
        assert completed.status == "completed"

    def test_a_service_without_a_catalogue_fails_closed(self) -> None:
        """Accepting "for now" is how a guard ends up inert in production."""
        repo = FakeTaskRepo(_task())
        service = TaskService(repo, HSTValidator(), DependencyResolver())

        with pytest.raises(ValidationError):
            service.complete_task("task-1", None, None, ["att-1"], None, None, tenant_key=TENANT)


class TestNoDuplicates:
    def test_completing_twice_does_not_duplicate_a_ref(self) -> None:
        """The form seeds from the task's own list, so every ref came back."""
        own = _attachment("att-1", TENANT, AttachmentCategory.TASK)
        second = _attachment("att-2", TENANT, AttachmentCategory.TASK)
        service, repo = _service(_task(photo_refs=["att-1"]), [own, second])

        completed = service.complete_task("task-1", None, None, ["att-1", "att-2"], None, None, tenant_key=TENANT)

        assert completed.photo_refs == ["att-1", "att-2"]
        assert repo.task.photo_refs == ["att-1", "att-2"]

    def test_a_repeated_ref_within_one_request_is_collapsed(self) -> None:
        own = _attachment("att-1", TENANT, AttachmentCategory.TASK)
        service, _repo = _service(_task(), [own])

        completed = service.complete_task("task-1", None, None, ["att-1", "att-1"], None, None, tenant_key=TENANT)

        assert completed.photo_refs == ["att-1"]

    def test_an_already_stored_ref_is_not_re_validated(self) -> None:
        """It passed once; a later retention erasure must not block a completion."""
        service, _repo = _service(_task(photo_refs=["att-erased"]), [])

        completed = service.complete_task("task-1", None, None, ["att-erased"], None, None, tenant_key=TENANT)

        assert completed.photo_refs == ["att-erased"]

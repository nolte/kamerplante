"""Task photo upload: the missing half of a capability REQ-006 already required.

``requires_photo`` is on ``TaskTemplate`` and ``TaskItem``, ``photo_refs`` is on
``TaskItem``, ``TaskService.complete_task`` refuses a ``requires_photo`` task
that has none, ``AttachmentCategory.TASK`` is in NFR-013's category list and
``"task"`` is in its image-only MIME whitelist. Everything was built except the
route — so the enforcement had no way to be satisfied and such a task could not
be completed at all (#1339).

What is pinned here:

* the **task is resolved tenant-scoped before any byte is read**, so a foreign
  task never reaches the storage pipeline and answers the same 404 as an unknown
  one;
* the upload lands in the **TASK** category, not ``PLANT`` — the category drives
  the storage prefix and the DSGVO erasure scope, so the wrong one is a
  retention bug that nothing else would notice;
* the response exposes **only** the attachment id and tenant-scoped URIs
  (NFR-013 AC-03/AC-04);
* the route **does not write** ``task.photo_refs`` — the completion request
  does, and two writers would disagree the moment a staged photo is removed
  before submitting.

No TC-ID: route-surface invariants, not a user-facing case.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from app.api.v1.attachments.permissions import require_attachment_permission
from app.api.v1.tasks import photo_router
from app.common.enums import AttachmentCategory, TenantRole
from app.common.exceptions import ForbiddenError, InvalidFileTypeError, NotFoundError
from app.core.permissions import Action
from app.domain.models.attachment import Attachment
from app.domain.models.tenant_context import TenantContext
from tests.support.repo_scripts import load_repo_script

mounted_routes = load_repo_script("check_frontend_calls_served").collect_mounted_routes


def _ctx(role: TenantRole = TenantRole.GROWER) -> TenantContext:
    return TenantContext(tenant_key="tenant-a", tenant_slug="mein-garten", user_key="user-a", role=role)


class FakeUpload:
    def __init__(self, content_type: str | None = "image/jpeg", data: bytes = b"jpegbytes") -> None:
        self.content_type = content_type
        self.filename = "photo.jpg"
        self._data = data
        self._read = False

    async def read(self, _size: int) -> bytes:
        if self._read:
            return b""
        self._read = True
        return self._data


class FakeRequest:
    def __init__(self, content_length: int | None = None) -> None:
        self.headers = {} if content_length is None else {"content-length": str(content_length)}


class FakeTaskService:
    """Answers like the real one: a foreign or unknown key raises NotFoundError."""

    def __init__(self, owned: dict[str, str]) -> None:
        self._owned = owned
        self.lookups: list[tuple[str, str]] = []

    def get_task(self, key: str, tenant_key: str = "") -> Any:
        self.lookups.append((key, tenant_key))
        if self._owned.get(key) != tenant_key:
            raise NotFoundError("Task", key)
        return object()


class FakeAttachmentService:
    def __init__(self) -> None:
        self.uploads: list[dict] = []

    def max_upload_bytes(self) -> int:
        return 10 * 1024 * 1024

    async def upload(self, **kwargs: Any) -> Attachment:
        self.uploads.append(kwargs)
        return Attachment(
            _key="att-1",
            tenant_key=kwargs["tenant_key"],
            category=kwargs["category"],
            mime_type=kwargs["mime_type"],
            byte_size=len(kwargs["data"]),
            original_filename=kwargs["original_filename"],
            storage_key="tenants/tenant-a/task/deadbeef.jpg",
            sha256="deadbeef",
            created_by=kwargs["user_key"],
        )


@pytest.fixture
def services() -> tuple[FakeTaskService, FakeAttachmentService]:
    return FakeTaskService({"task-1": "tenant-a", "task-of-other-tenant": "tenant-b"}), FakeAttachmentService()


class TestTheRouteIsMounted:
    def test_post_tasks_key_photos_exists(self) -> None:
        """Walked with the shipped joiner, not a second copy of its logic.

        Both this file and the sensor-gate file used to carry a byte-for-byte
        copy of the ``original_router`` walk, and both copies read ``route.path``
        on a wrapper that has none — so they agreed with each other and with
        nothing FastAPI produces. One implementation, in the script the required
        join gate already drives.
        """
        from app.main import app

        mounted = mounted_routes(app)

        assert len(mounted) > 500, "the route walk collapsed — this assertion would pass vacuously"
        assert ("POST", "/api/v1/t/{}/tasks/{}/photos") in mounted


class TestTheGate:
    def test_the_route_gates_on_create_and_not_on_read(self) -> None:
        """Asserts the *action*, because the closure names are all ``_dependency``.

        Comparing ``__name__`` against ``require_attachment_permission(CREATE)``
        — which is what stood here — compares two closures that are both called
        ``_dependency``: it is equally true for ``READ``, so it could not fail.
        The action is what decides whether a viewer gets in, so the action is
        what gets driven.
        """
        dependency = inspect.signature(photo_router.upload_task_photo).parameters["ctx"].default.dependency
        read_gate = require_attachment_permission(Action.READ)

        # A viewer may READ attachments and may not CREATE them (REQ-024 §4), so
        # this pair distinguishes the two gates by behaviour.
        assert read_gate(ctx=_ctx(TenantRole.VIEWER)).role is TenantRole.VIEWER
        with pytest.raises(ForbiddenError):
            dependency(ctx=_ctx(TenantRole.VIEWER))

    def test_a_viewer_is_refused(self) -> None:
        dependency = inspect.signature(photo_router.upload_task_photo).parameters["ctx"].default.dependency

        with pytest.raises(ForbiddenError):
            dependency(ctx=_ctx(TenantRole.VIEWER))

    def test_a_grower_is_admitted(self) -> None:
        dependency = inspect.signature(photo_router.upload_task_photo).parameters["ctx"].default.dependency

        assert dependency(ctx=_ctx(TenantRole.GROWER)).role is TenantRole.GROWER


class TestTheUpload:
    @pytest.mark.asyncio
    async def test_it_stores_under_the_task_category(self, services) -> None:
        """The category drives the storage prefix and the DSGVO erasure scope."""
        tasks, attachments = services

        response = await photo_router.upload_task_photo(
            "task-1", FakeRequest(), FakeUpload(), ctx=_ctx(), task_service=tasks, attachment_service=attachments
        )

        assert attachments.uploads[0]["category"] is AttachmentCategory.TASK
        assert attachments.uploads[0]["tenant_key"] == "tenant-a"
        assert response.attachment_id == "att-1"

    @pytest.mark.asyncio
    async def test_the_response_exposes_no_storage_detail(self, services) -> None:
        tasks, attachments = services

        response = await photo_router.upload_task_photo(
            "task-1", FakeRequest(), FakeUpload(), ctx=_ctx(), task_service=tasks, attachment_service=attachments
        )

        assert response.uri == "/api/v1/t/mein-garten/attachments/att-1"
        assert "deadbeef" not in response.model_dump_json()
        assert "tenants/" not in response.model_dump_json()

    @pytest.mark.asyncio
    async def test_a_foreign_task_is_refused_before_any_byte_is_read(self, services) -> None:
        """Same 404 as an unknown key, and the storage pipeline is never entered."""
        tasks, attachments = services

        with pytest.raises(NotFoundError):
            await photo_router.upload_task_photo(
                "task-of-other-tenant",
                FakeRequest(),
                FakeUpload(),
                ctx=_ctx(),
                task_service=tasks,
                attachment_service=attachments,
            )
        with pytest.raises(NotFoundError):
            await photo_router.upload_task_photo(
                "no-such-task",
                FakeRequest(),
                FakeUpload(),
                ctx=_ctx(),
                task_service=tasks,
                attachment_service=attachments,
            )

        assert attachments.uploads == []

    @pytest.mark.asyncio
    async def test_a_body_declaring_more_than_the_limit_is_rejected_before_reading(self, services) -> None:
        from app.common.exceptions import FileTooLargeError

        tasks, attachments = services

        with pytest.raises(FileTooLargeError):
            await photo_router.upload_task_photo(
                "task-1",
                FakeRequest(content_length=999 * 1024 * 1024),
                FakeUpload(),
                ctx=_ctx(),
                task_service=tasks,
                attachment_service=attachments,
            )

        assert attachments.uploads == []

    @pytest.mark.asyncio
    async def test_a_file_without_a_content_type_is_rejected(self, services) -> None:
        tasks, attachments = services

        with pytest.raises(InvalidFileTypeError):
            await photo_router.upload_task_photo(
                "task-1",
                FakeRequest(),
                FakeUpload(content_type=None),
                ctx=_ctx(),
                task_service=tasks,
                attachment_service=attachments,
            )

        assert attachments.uploads == []

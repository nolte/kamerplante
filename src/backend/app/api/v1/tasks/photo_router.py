"""REQ-006 — task photo upload, on the NFR-013 attachment fundament (#1339).

Mounted under ``/api/v1/t/{tenant_slug}/tasks/{key}/photos``, the same shape as
the REQ-034 plant gallery (``/plant-instances/{key}/photos``) so the frontend
consumes both the same way.

**Why this exists.** REQ-006 has required task photos since v1: ``requires_photo``
is on ``TaskTemplate`` and ``TaskItem``, ``photo_refs`` is on ``TaskItem``,
completion enforces the pair (``TaskService.complete_task`` refuses a
``requires_photo`` task with no photo), ``AttachmentCategory.TASK`` is in
NFR-013's category list and ``"task"`` is in the image-only MIME whitelist. Every
part of the capability was built **except the route**: the upload button on the
task-completion form posted to ``POST /tasks/{key}/photos``, which no router had
ever served, so a ``requires_photo`` task could not be completed at all — the
enforcement had no way to be satisfied. #1339 measured the 404; this is the
missing half.

**What it deliberately does not do.** It does not write ``task.photo_refs``. The
completion form stages its photos and submits the list with
``POST /tasks/{key}/complete``, which is what writes them and what the
``requires_photo`` gate reads; appending here as well would have the two writers
disagree the moment the user removes a staged photo before submitting. The
attachment itself is persisted and tenant-owned either way, so an abandoned
upload is a listed, deletable attachment rather than a lost object.

Permissions (REQ-024 §1a — the "Attachments" matrix row, as for plant photos):
upload → ``Action.CREATE`` on ``ATTACHMENT``; a viewer is refused. The task is
loaded tenant-scoped *first*, so a foreign task key answers the same 404 as a
key that does not exist.

Responses expose only ``attachment_id`` plus stable tenant-scoped URIs — never
bucket / backend / storage-key details (NFR-013 AC-03/AC-04).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, UploadFile

from app.api.v1.attachments.permissions import require_attachment_permission
from app.api.v1.attachments.schemas import ThumbnailUris
from app.api.v1.attachments.tenant_router import _parse_content_length, _read_upload_bounded
from app.api.v1.tasks.schemas import TaskPhotoResponse
from app.common.dependencies import get_attachment_service, get_task_service
from app.common.enums import AttachmentCategory
from app.common.exceptions import FileTooLargeError, InvalidFileTypeError
from app.common.openapi_responses import CRUD_RESPONSES
from app.core.permissions import Action
from app.domain.engines.storage.thumbnail_generator import THUMBNAIL_SIZES, can_render
from app.domain.models.attachment import Attachment
from app.domain.models.tenant_context import TenantContext
from app.domain.services.attachment_service import AttachmentService
from app.domain.services.task_service import TaskService

router = APIRouter(prefix="/tasks/{key}/photos", tags=["task-photos"], responses=CRUD_RESPONSES)


def _photo_response(attachment: Attachment, tenant_slug: str) -> TaskPhotoResponse:
    attachment_id = attachment.key or ""
    uri = f"/api/v1/t/{tenant_slug}/attachments/{attachment_id}"
    thumbnail_uris: ThumbnailUris | None = None
    if can_render(attachment.mime_type):
        small, medium, large = THUMBNAIL_SIZES
        thumbnail_uris = ThumbnailUris(
            small=f"{uri}/thumbnails/{small}",
            medium=f"{uri}/thumbnails/{medium}",
            large=f"{uri}/thumbnails/{large}",
        )
    return TaskPhotoResponse(
        attachment_id=attachment_id,
        uri=uri,
        thumbnail_uris=thumbnail_uris,
        mime_type=attachment.mime_type,
        byte_size=attachment.byte_size,
        original_filename=attachment.original_filename,
    )


@router.post("", response_model=TaskPhotoResponse, status_code=201)
async def upload_task_photo(
    key: Annotated[str, Path(description="Document key of the task.")],
    request: Request,
    file: UploadFile,
    ctx: TenantContext = Depends(require_attachment_permission(Action.CREATE)),
    task_service: TaskService = Depends(get_task_service),
    attachment_service: AttachmentService = Depends(get_attachment_service),
) -> TaskPhotoResponse:
    """Upload a photo for a task and return its stable attachment URI (REQ-006).

    The task is resolved tenant-scoped before a single byte is read, so neither
    an unknown nor a foreign task ever reaches the storage pipeline — and both
    answer the same 404.
    """
    task_service.get_task(key, tenant_key=ctx.tenant_key)

    mime_type = (file.content_type or "").lower().strip()
    if not mime_type:
        raise InvalidFileTypeError("", [])

    # SEC-005 — reject an oversized upload before buffering the body.
    max_bytes = attachment_service.max_upload_bytes()
    content_length = _parse_content_length(request)
    if content_length is not None and content_length > max_bytes:
        raise FileTooLargeError(max_bytes)
    data = await _read_upload_bounded(file, max_bytes)

    attachment = await attachment_service.upload(
        tenant_key=ctx.tenant_key,
        user_key=ctx.user_key,
        data=data,
        mime_type=mime_type,
        original_filename=file.filename or "photo",
        category=AttachmentCategory.TASK,
    )
    return _photo_response(attachment, ctx.tenant_slug)

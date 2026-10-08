"""Files go straight from the browser to S3 with presigned URLs; the API never streams them."""

import uuid
from typing import Any

import anyio
from fastapi import APIRouter
from pydantic import Field

from app.common.constants import (
    ALLOWED_UPLOAD_TYPES,
    DOWNLOAD_URL_TTL_SECONDS,
    UPLOAD_MAX_BYTES,
    UPLOAD_URL_TTL_SECONDS,
)
from app.common.enums import MessageKind
from app.common.schemas import ERROR_RESPONSES, Schema
from app.core import aws
from app.core.config import get_settings
from app.core.deps import CurrentActor, Uow
from app.core.errors import NotFoundError, ValidationError
from app.modules.attachments.models import Attachment
from app.modules.attachments.repository import AttachmentRepository
from app.modules.messages.repository import MessageRepository
from app.modules.tickets.service import TicketService

router = APIRouter(prefix="/attachments", tags=["attachments"], responses=ERROR_RESPONSES)


class UploadIn(Schema):
    filename: str = Field(min_length=1, max_length=200)
    content_type: str
    size_bytes: int = Field(gt=0, le=UPLOAD_MAX_BYTES)


class UploadOut(Schema):
    id: uuid.UUID
    upload_url: str
    headers: dict[str, str]


class DownloadOut(Schema):
    url: str


def _presign(method: str, params: dict[str, Any], ttl: int) -> str:
    return str(aws.s3_public().generate_presigned_url(method, Params=params, ExpiresIn=ttl))


@router.post("", response_model=UploadOut, status_code=201)
async def create_upload(body: UploadIn, actor: CurrentActor, uow: Uow) -> UploadOut:
    if body.content_type not in ALLOWED_UPLOAD_TYPES:
        raise ValidationError("This file type is not allowed.")
    attachment_id = uuid.uuid4()
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in body.filename)[-120:]
    key = f"attachments/{actor.org_id}/{attachment_id}/{safe_name}"
    AttachmentRepository(uow.session, actor.org_id).add(
        Attachment(
            id=attachment_id,
            uploaded_by=actor.user_id,
            s3_key=key,
            filename=body.filename,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
        )
    )
    await uow.commit()
    params = {"Bucket": get_settings().files_bucket, "Key": key, "ContentType": body.content_type}
    url = await anyio.to_thread.run_sync(lambda: _presign("put_object", params, UPLOAD_URL_TTL_SECONDS))
    return UploadOut(id=attachment_id, upload_url=url, headers={"Content-Type": body.content_type})


@router.get("/{attachment_id}", response_model=DownloadOut)
async def download(attachment_id: uuid.UUID, actor: CurrentActor, uow: Uow) -> DownloadOut:
    attachment = await AttachmentRepository(uow.session, actor.org_id).get(attachment_id)
    if attachment.ticket_id is None:
        if attachment.uploaded_by != actor.user_id:
            raise NotFoundError()
    else:
        await TicketService(uow, actor).get_visible(attachment.ticket_id)  # customers: own tickets only
        if not actor.is_staff and attachment.message_id:
            message = await MessageRepository(uow.session, actor.org_id).get(attachment.message_id)
            if message.kind != MessageKind.PUBLIC_REPLY:  # files on internal notes stay internal
                raise NotFoundError()
    params = {
        "Bucket": get_settings().files_bucket,
        "Key": attachment.s3_key,
        "ResponseContentDisposition": f'attachment; filename="{attachment.filename}"',
    }
    return DownloadOut(url=await anyio.to_thread.run_sync(lambda: _presign("get_object", params, DOWNLOAD_URL_TTL_SECONDS)))

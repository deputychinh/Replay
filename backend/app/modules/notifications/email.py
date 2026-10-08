"""Email delivery (Strategy): SMTP to Mailpit locally, SES in AWS."""

from email.message import EmailMessage
from typing import Any

import aiosmtplib
import anyio

from app.core import aws
from app.core.config import get_settings
from app.db.unit_of_work import UnitOfWork


async def _send_smtp(to: str, subject: str, text: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.email_from, to, subject
    message.set_content(text)
    await aiosmtplib.send(message, hostname=settings.smtp_host, port=settings.smtp_port)


async def _send_ses(to: str, subject: str, text: str) -> None:
    settings = get_settings()
    client = aws._client("ses", None)
    await anyio.to_thread.run_sync(
        lambda: client.send_email(
            Source=settings.email_from,
            Destination={"ToAddresses": [to]},
            Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}}},
        )
    )


async def send_email(payload: dict[str, Any], _: UnitOfWork) -> None:
    send = _send_ses if get_settings().email_backend == "ses" else _send_smtp
    await send(payload["to"], payload["subject"], payload["text"])

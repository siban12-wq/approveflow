from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.clock import clock
from app.core.config import get_settings
from app.core.logging import logger
from app.models.entities import EmailOutbox


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str, db: Session | None = None) -> str: ...


class ConsoleEmailProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str, db: Session | None = None) -> str:
        logger.info("EMAIL (development sink) to=%s subject=%s", to, subject)
        if db is not None:
            db.add(
                EmailOutbox(
                    to_address=to,
                    subject=subject,
                    body=body,
                    provider="console",
                    created_at=clock.now(),
                )
            )
            db.flush()
        return "queued_console"


class SmtpEmailProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str, db: Session | None = None) -> str:
        settings = get_settings()
        try:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = settings.smtp_from
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.send_message(msg)
            status = "sent_smtp"
        except Exception as exc:  # noqa: BLE001 — record failure, do not claim delivery
            logger.warning("SMTP send failed to=%s error=%s", to, exc)
            status = f"failed_smtp:{exc.__class__.__name__}"
        if db is not None:
            db.add(
                EmailOutbox(
                    to_address=to,
                    subject=subject,
                    body=body,
                    provider=status,
                    created_at=clock.now(),
                )
            )
            db.flush()
        return status


def get_email_provider() -> EmailProvider:
    if get_settings().smtp_enabled:
        return SmtpEmailProvider()
    return ConsoleEmailProvider()

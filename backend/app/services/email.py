from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.logging import logger


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL (console) to=%s subject=%s body=%s", to, subject, body[:180])


class SmtpEmailProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str) -> None:
        # Demo default stays on the console provider. Wire SMTP only via config.
        logger.info("SMTP placeholder to=%s subject=%s", to, subject)


def get_email_provider() -> EmailProvider:
    from app.core.config import get_settings

    if get_settings().smtp_enabled:
        return SmtpEmailProvider()
    return ConsoleEmailProvider()

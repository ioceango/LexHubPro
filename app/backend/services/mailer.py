"""邮件发送：SMTP 优先，未配置时走 console（不投递）。"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Protocol, runtime_checkable

from utils.auth_crypto import mask_email
from utils.mailbox import resolve_smtp, smtp_ready

logger = logging.getLogger(__name__)

MAILER_MODE_CONSOLE = "console"
MAILER_MODE_SMTP = "smtp"


class MailerError(Exception):
    """发信失败，可映射为 503。"""


@runtime_checkable
class MailerPort(Protocol):
    provider_name: str

    async def send(self, to_email: str, subject: str, body: str) -> None:
        ...


class ConsoleMailer:
    provider_name = MAILER_MODE_CONSOLE

    async def send(self, to_email: str, subject: str, body: str) -> None:
        logger.info(
            "[BIZ] mail dispatched(console) to=%s subject=%s body_chars=%s",
            mask_email(to_email),
            subject,
            len(body or ""),
        )


class SmtpMailer:
    provider_name = MAILER_MODE_SMTP

    def __init__(self) -> None:
        cfg = resolve_smtp()
        self._host = str(cfg["host"])
        self._port = int(cfg["port"])
        self._user = str(cfg["user"])
        self._password = str(cfg["password"])
        self._from = str(cfg["from_addr"])
        self._use_tls = bool(cfg["starttls"])
        self._use_ssl = bool(cfg["ssl"])
        if not self._host:
            raise MailerError("SMTP_HOST is not configured")

    def _open_client(self):
        if self._use_ssl:
            context = ssl.create_default_context()
            return smtplib.SMTP_SSL(self._host, self._port, timeout=30, context=context)
        return smtplib.SMTP(self._host, self._port, timeout=30)

    def _send_sync(self, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._from
        message["To"] = to_email
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=False)
        message["Message-ID"] = make_msgid(domain="lexhubpro.local")
        message.set_content(body)
        with self._open_client() as client:
            client.ehlo()
            if self._use_tls:
                client.starttls()
                client.ehlo()
            if self._user:
                client.login(self._user, self._password)
            client.send_message(message)

    async def send(self, to_email: str, subject: str, body: str) -> None:
        try:
            await asyncio.to_thread(self._send_sync, to_email, subject, body)
        except Exception as exc:  # noqa: BLE001
            logger.error("[BIZ] smtp send failed type=%s to=%s", type(exc).__name__, mask_email(to_email))
            raise MailerError("验证码邮件发送失败，请稍后重试") from exc
        logger.info("[BIZ] mail dispatched(smtp) to=%s subject=%s", mask_email(to_email), subject)


def smtp_configured() -> bool:
    return smtp_ready()


def get_mailer() -> MailerPort:
    if smtp_configured():
        return SmtpMailer()
    return ConsoleMailer()

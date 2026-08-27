"""BUG-004：SMTP 发信与 console 脱敏。"""

import logging
import smtplib
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

def _reset_settings() -> None:
    from core.config import settings

    for key in list(settings.__dict__):
        if not key.startswith("_"):
            settings.__dict__.pop(key, None)


class _FakeSMTP:
    last_message = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def ehlo(self):
        return True

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = True

    def send_message(self, message):
        _FakeSMTP.last_message = message


@pytest.mark.asyncio
async def test_console_mailer_does_not_log_code_or_email(caplog):
    # BUG-004 回归
    from services.mailer import ConsoleMailer

    caplog.set_level(logging.INFO)
    await ConsoleMailer().send("alice@example.com", "验证码", "邮箱验证码：654321")
    combined = "\n".join(record.getMessage() for record in caplog.records)
    assert "654321" not in combined
    assert "alice@example.com" not in combined


@pytest.mark.asyncio
async def test_smtp_mailer_sends_when_host_configured(monkeypatch):
    # BUG-004 回归
    monkeypatch.setenv("SMTP_HOST", "mailpit")
    monkeypatch.setenv("SMTP_PORT", "1025")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setenv("SMTP_FROM", "noreply@lexhubpro.local")
    _reset_settings()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    from services.mailer import SmtpMailer, smtp_configured

    assert smtp_configured() is True
    from services.auth_accounts import require_email_verification

    assert require_email_verification() is True
    await SmtpMailer().send("user@example.com", "验证码", "邮箱验证码：111222")
    sent = _FakeSMTP.last_message
    assert sent is not None
    assert sent["To"] == "user@example.com"
    assert "111222" in sent.get_content()


class _FakeSMTP_SSL(_FakeSMTP):
    last_ssl = None

    def __init__(self, host, port, timeout=None, context=None):
        super().__init__(host, port, timeout)
        _FakeSMTP_SSL.last_ssl = self


@pytest.mark.asyncio
async def test_163_preset_uses_smtp_ssl(monkeypatch):
    # BUG-004 回归：163 走 465 SSL
    monkeypatch.setenv("SMTP_PROVIDER", "163")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("SMTP_USER", "sender@163.com")
    monkeypatch.setenv("SMTP_PASSWORD", "auth-code")
    monkeypatch.setenv("SMTP_SSL", "")
    monkeypatch.setenv("SMTP_STARTTLS", "")
    _reset_settings()
    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTP_SSL)
    from services.mailer import SmtpMailer
    from utils.mailbox import resolve_smtp

    cfg = resolve_smtp()
    assert cfg["host"] == "smtp.163.com"
    assert cfg["port"] == 465
    assert cfg["ssl"] is True
    await SmtpMailer().send("user@163.com", "验证码", "邮箱验证码：333444")
    assert _FakeSMTP_SSL.last_ssl is not None
    assert _FakeSMTP_SSL.last_ssl.logged_in is True


@pytest.mark.asyncio
async def test_gmail_preset_uses_starttls(monkeypatch):
    # BUG-004 回归：Gmail 走 587 STARTTLS
    monkeypatch.setenv("SMTP_PROVIDER", "gmail")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_SSL", "")
    monkeypatch.setenv("SMTP_STARTTLS", "")
    monkeypatch.setenv("SMTP_PORT", "")
    _reset_settings()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    from utils.mailbox import resolve_smtp

    cfg = resolve_smtp()
    assert cfg["host"] == "smtp.gmail.com"
    assert cfg["port"] == 587
    assert cfg["starttls"] is True
    from services.mailer import SmtpMailer

    _FakeSMTP.last_message = None
    await SmtpMailer().send("user@gmail.com", "验证码", "邮箱验证码：555666")
    assert _FakeSMTP.last_message is not None

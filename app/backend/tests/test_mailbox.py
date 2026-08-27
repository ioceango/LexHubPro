"""BUG-004：163 / Gmail 域名白名单。"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from utils.mailbox import is_supported_mailbox, mailbox_domain


def test_supported_mailbox_domains(monkeypatch):
    monkeypatch.setenv("AUTH_MAILBOX_ALLOW_ALL", "false")
    from core.config import settings

    settings.__dict__.pop("auth_mailbox_allow_all", None)
    assert is_supported_mailbox("a@163.com")
    assert is_supported_mailbox("a@gmail.com")
    assert is_supported_mailbox("a@126.com")
    assert not is_supported_mailbox("a@qq.com")
    assert not is_supported_mailbox("not-an-email")
    assert mailbox_domain("Name@Gmail.COM") == "gmail.com"

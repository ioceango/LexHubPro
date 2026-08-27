"""认证与存储测试公共夹具。"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_SECRET = "feat007-test-secret-key-32bytes-ok"


def reset_settings_cache() -> None:
    from core.config import settings

    for key in list(settings.__dict__):
        if not key.startswith("_"):
            settings.__dict__.pop(key, None)


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("AUTH_REQUIRE_EMAIL_VERIFICATION", "false")
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_PROVIDER", "")
    monkeypatch.setenv("AUTH_MAILBOX_ALLOW_ALL", "true")
    monkeypatch.setenv("AUTH_TENANT_ID", "default")
    from auth_providers import reset_auth_provider_cache
    from storage_providers import reset_storage_provider_cache

    reset_settings_cache()
    reset_auth_provider_cache()
    reset_storage_provider_cache()
    yield
    reset_auth_provider_cache()
    reset_storage_provider_cache()
    reset_settings_cache()


@pytest.fixture
def verify_auth_env(auth_env, monkeypatch):
    """BUG-004：强制邮箱验证（无 SMTP，验证码不真正投递）。"""
    monkeypatch.setenv("AUTH_REQUIRE_EMAIL_VERIFICATION", "true")
    reset_settings_cache()
    yield


@pytest.fixture
def mailbox_strict_env(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_MAILBOX_ALLOW_ALL", "false")
    reset_settings_cache()
    yield


@pytest.fixture
def lockout_auth_env(auth_env, monkeypatch):
    monkeypatch.setenv("AUTH_MAX_LOGIN_FAILURES", "2")
    monkeypatch.setenv("AUTH_LOCK_MINUTES", "15")
    reset_settings_cache()
    yield


# 旧夹具名，避免漏改测试
local_auth_env = auth_env

"""认证端口与自建认证安全工具回归（FEAT-005）。"""

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from auth_providers.base import AuthUser, normalize_role, normalize_status
from utils.auth_crypto import (
    bind_email_code,
    generate_email_code,
    hash_ip,
    hash_token,
    mask_email,
    validate_password_strength,
    PasswordPolicyError,
    hash_password,
    verify_password,
)
from services.auth_accounts import GENERIC_LOGIN_ERROR, GENERIC_REGISTER_MESSAGE
from services.auth_sessions import GENERIC_RESET_MESSAGE
from utils.object_key import build_object_key


def test_auth_user_admin_flag():
    admin = AuthUser(id=1, email="a@example.com", role="admin")
    user = AuthUser(id=2, email="b@example.com", role="user")
    assert admin.is_admin is True
    assert user.is_admin is False


def test_normalize_unknown_role_downgrades():
    assert normalize_role("superuser") == "user"
    assert normalize_status("unknown") == "pending_verification"


def test_password_policy_rejects_weak():
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("short")
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("allletters")
    validate_password_strength("letters12345")


def test_password_hash_is_not_reversible():
    raw = "letters12345"
    encoded = hash_password(raw)
    assert raw not in encoded
    assert verify_password(encoded, raw) is True
    assert verify_password(encoded, "wrong-password") is False


def test_token_and_ip_hash_are_digest_only():
    token = "super-secret-refresh-token"
    digest = hash_token(token)
    assert token not in digest
    assert len(digest) == 64
    assert hash_ip("127.0.0.1") != "127.0.0.1"


def test_email_mask_hides_local_part():
    masked = mask_email("alice@example.com")
    assert "alice" not in masked
    assert "@example.com" in masked


def test_anti_enumeration_messages_are_stable():
    assert "已注册" not in GENERIC_REGISTER_MESSAGE
    assert "不存在" not in GENERIC_LOGIN_ERROR
    assert "不存在" not in GENERIC_RESET_MESSAGE


def test_email_code_is_six_digits_and_user_scoped():
    # BUG-004 回归
    code = generate_email_code()
    assert len(code) == 6 and code.isdigit()
    assert hash_token(bind_email_code(1, code)) != hash_token(bind_email_code(2, code))


def test_object_key_uses_tenant_user_and_extension():
    key = build_object_key("default", "42", "合同.PDF")
    assert key.startswith("default/42/")
    assert key.endswith(".pdf")
    assert ".." not in key

"""自建认证的密码与令牌安全工具。

安全取舍说明：
- 密码用 **Argon2id**（内存硬化，抗 GPU 暴力破解），而非 SHA/PBKDF2 系列。
  Argon2 的哈希串自带随机盐与参数，无需额外存盐字段。
- 刷新令牌与一次性令牌在库中只存 **SHA-256 摘要**：这类令牌本身是高熵随机串，
  不存在被字典攻击的风险，无需慢哈希；用快哈希才能支撑按摘要的等值索引查询。
  数据库泄露时攻击者拿到摘要也无法还原可用令牌。
- 校验失败一律返回同一种错误语义，避免通过响应差异枚举账号。
"""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

logger = logging.getLogger(__name__)

# Argon2id 参数：在交互式登录可接受的延迟内提供足够成本。
# time_cost=3 / memory_cost=64MiB / parallelism=2 为常见生产基线。
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128

# 随机令牌字节数。32 字节 ≈ 256 位熵，足以抵御在线穷举。
TOKEN_BYTES = 32


class PasswordPolicyError(Exception):
    """密码不满足强度策略。"""


def validate_password_strength(password: str) -> None:
    """校验密码强度；不满足时抛 `PasswordPolicyError`。

    只做长度与字符多样性的下限约束：过度复杂的规则会促使用户使用可预测的变形，
    反而降低实际安全性。
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"密码长度至少 {MIN_PASSWORD_LENGTH} 位")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"密码长度不能超过 {MAX_PASSWORD_LENGTH} 位")
    if password.strip() != password:
        raise PasswordPolicyError("密码首尾不能包含空白字符")

    has_letter = any(char.isalpha() for char in password)
    has_digit = any(char.isdigit() for char in password)
    if not (has_letter and has_digit):
        raise PasswordPolicyError("密码需同时包含字母与数字")


def hash_password(password: str) -> str:
    """生成 Argon2id 密码哈希（内含随机盐与参数）。"""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """校验密码；任何异常都按「不匹配」处理，不向调用方泄露失败细节。"""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """判断既有哈希是否需按当前参数重算（参数升级后透明迁移）。"""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        # 无法解析的哈希视为需要重建，避免旧格式长期滞留。
        return True


def generate_email_code() -> str:
    """生成 6 位数字邮箱验证码（仅返回一次，入库只存哈希）。"""
    return f"{secrets.randbelow(1_000_000):06d}"


def bind_email_code(user_id: int, code: str) -> str:
    """把 6 位码与用户绑定后再做摘要。

    验证码空间只有 100 万，若直接哈希会撞上 `tb_one_time_token.token_hash`
    的全局唯一约束。绑定 user_id 后不同用户可持有相同数字码。
    """
    return f"{user_id}:{code}"


def generate_token() -> str:
    """生成 URL 安全的高熵随机令牌（仅返回一次，不入库）。"""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """计算令牌的 SHA-256 十六进制摘要（入库用）。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(stored_hash: str, provided_token: str) -> bool:
    """常量时间比较令牌摘要，避免时序侧信道泄露。"""
    return hmac.compare_digest(stored_hash, hash_token(provided_token))


def hash_ip(ip: Optional[str]) -> Optional[str]:
    """对来访 IP 做单向摘要，用于审计聚合但不可回溯到原始地址。"""
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def mask_email(email: Optional[str]) -> str:
    """脱敏邮箱用于日志，形如 ``a***@example.com``。

    日志中出现完整邮箱等同于泄露账号清单，因此统一走此函数。
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    visible = local[:1] if local else ""
    return f"{visible}***@{domain}"
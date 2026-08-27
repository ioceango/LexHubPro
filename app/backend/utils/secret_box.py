"""对称加密小工具：只负责加解密，不碰业务。"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from utils.config_reader import require_str


def _fernet() -> Fernet:
    secret = require_str("jwt_secret_key")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise SecretBoxError("无法解密密钥，请重新保存 API Key") from exc


def key_suffix(plain: str, length: int = 4) -> str:
    cleaned = (plain or "").strip()
    if len(cleaned) <= length:
        return cleaned
    return cleaned[-length:]


class SecretBoxError(Exception):
    """解密失败。"""

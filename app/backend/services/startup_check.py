"""启动自检：JWT 密钥与 MinIO 连通性。失败则拒绝启动。"""

import logging
from dataclasses import dataclass, field
from typing import List

from storage_providers import StorageConfigError, StorageError, get_storage_provider
from utils.config_reader import ConfigError, require_min_length

logger = logging.getLogger(__name__)

MIN_SECRET_LENGTH = 32


@dataclass
class CheckResult:
    passed: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _check_auth_config(result: CheckResult) -> None:
    try:
        require_min_length("jwt_secret_key", MIN_SECRET_LENGTH)
        result.passed.append(f"jwt_secret_key length >= {MIN_SECRET_LENGTH}")
    except ConfigError as exc:
        result.failures.append(str(exc))


async def _check_storage_config(result: CheckResult) -> None:
    try:
        provider = get_storage_provider()
    except (StorageConfigError, ConfigError) as exc:
        result.failures.append(str(exc))
        return
    checker = getattr(provider, "check_connectivity", None)
    if checker is None:
        result.passed.append("minio provider ready")
        return
    try:
        await checker()
        result.passed.append("minio connectivity ok")
    except StorageError as exc:
        result.failures.append(f"Object storage connectivity check failed: {exc}")


async def run_startup_check(strict: bool = True) -> CheckResult:
    result = CheckResult()
    _check_auth_config(result)
    await _check_storage_config(result)
    for item in result.passed:
        logger.info("[BIZ] startup check passed: %s", item)
    for item in result.failures:
        logger.error("[BIZ] startup check failed: %s", item)
    if result.failures and strict:
        raise RuntimeError("Startup self-check failed: " + "; ".join(result.failures))
    logger.info("[BIZ] startup check done ok=%s", result.ok)
    return result


async def ensure_app_ready() -> CheckResult:
    result = await run_startup_check(strict=True)
    from services.schema_bootstrap import bootstrap_admin_if_configured, ensure_app_schema

    await ensure_app_schema()
    await bootstrap_admin_if_configured()
    return result


async def ensure_local_mode_ready() -> CheckResult:
    """兼容旧入口名。"""
    return await ensure_app_ready()

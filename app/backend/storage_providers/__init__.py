"""MinIO 为唯一对象存储实现。"""

import logging
from typing import Optional

from storage_providers.base import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_PRESIGN_EXPIRES_SECONDS,
    ObjectRef,
    StorageConfigError,
    StorageError,
    StorageObjectNotFoundError,
    StorageOperationError,
    StoragePort,
)
from storage_providers.minio_provider import MinioStorageProvider

logger = logging.getLogger(__name__)

_provider_cache: Optional[StoragePort] = None


def get_storage_provider() -> StoragePort:
    global _provider_cache
    if _provider_cache is None:
        _provider_cache = MinioStorageProvider()
        logger.info("[BIZ] storage provider initialized name=minio")
    return _provider_cache


def reset_storage_provider_cache() -> None:
    global _provider_cache
    _provider_cache = None


__all__ = [
    "DEFAULT_CONTENT_TYPE",
    "DEFAULT_PRESIGN_EXPIRES_SECONDS",
    "ObjectRef",
    "StorageConfigError",
    "StorageError",
    "StorageObjectNotFoundError",
    "StorageOperationError",
    "StoragePort",
    "get_storage_provider",
    "reset_storage_provider_cache",
]

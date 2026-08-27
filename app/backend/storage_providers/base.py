"""对象存储端口定义（技术中立）。

只定义契约，不含具体实现、不读配置。平台对象存储与 S3 兼容存储各自提供适配器，
业务层只依赖 `StoragePort`，因此更换存储后端时业务代码零改动。

一条贯穿性约束：数据库只持久化 `bucket` + `object_key`，**禁止持久化签名 URL**
（签名 URL 会过期，存库必然导致后续下载失败）。
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

# 预签名下载链接默认有效期，足够完成一次下载且不至于长期泄露。
DEFAULT_PRESIGN_EXPIRES_SECONDS = 900

DEFAULT_CONTENT_TYPE = "application/octet-stream"


class StorageError(Exception):
    """存储域基础异常。"""


class StorageConfigError(StorageError):
    """存储实现所需配置缺失或非法，应在启动自检阶段暴露并终止启动。"""


class StorageObjectNotFoundError(StorageError):
    """目标对象不存在。"""


class StorageOperationError(StorageError):
    """存储操作失败（网络、权限、服务端错误）。"""


@dataclass(frozen=True)
class ObjectRef:
    """对象的持久化引用。

    仅包含可安全入库的字段；不含任何签名 URL。
    """

    bucket: str
    object_key: str
    size: int = 0
    etag: str = ""
    content_type: str = DEFAULT_CONTENT_TYPE


@runtime_checkable
class StoragePort(Protocol):
    """对象存储实现契约。

    实现方必须保证：
    1. `ensure_bucket` 与 `delete` 幂等（重复调用不报错）；
    2. 桶一律为私有，读取只能通过限时预签名 URL；
    3. `object_key` 原样透传，不做截断、转义或改写（否则下载会 404）；
    4. 失败抛出本模块定义的异常类型，不向上泄露底层 SDK 异常。
    """

    provider_name: str

    async def ensure_bucket(self, bucket: str) -> None:
        """幂等确保私有桶存在。"""
        ...

    async def upload(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> ObjectRef:
        """上传对象并返回可入库的引用。"""
        ...

    async def download(self, bucket: str, object_key: str) -> bytes:
        """读取对象字节，供审查在服务端取文件。"""
        ...

    async def get_download_url(
        self,
        bucket: str,
        object_key: str,
        expires_seconds: int = DEFAULT_PRESIGN_EXPIRES_SECONDS,
    ) -> str:
        """生成限时预签名下载链接（不得入库）。"""
        ...

    async def delete(self, bucket: str, object_key: str) -> None:
        """幂等删除对象；对象不存在时不应报错。"""
        ...

    async def exists(self, bucket: str, object_key: str) -> bool:
        """判断对象是否存在。"""
        ...
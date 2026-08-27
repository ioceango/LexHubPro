"""MinIO / S3 兼容对象存储适配器（`STORAGE_MODE=minio` 时启用）。

**为何用线程池包装同步 SDK**：`boto3` 是同步客户端，直接在事件循环里调用会阻塞
整个 FastAPI 进程。这里统一经 `run_in_executor` 派发，保证异步接口语义真实成立。

**为何桶一律私有**：合同文件属敏感数据，公开读桶等于把全部合同暴露在公网；
读取只能通过限时预签名 URL，且预签名 URL 绝不入库（会过期）。
"""

import asyncio
import functools
import logging
from typing import Optional

from storage_providers.base import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_PRESIGN_EXPIRES_SECONDS,
    ObjectRef,
    StorageConfigError,
    StorageObjectNotFoundError,
    StorageOperationError,
)
from utils.config_reader import read_bool, read_int, read_str, require_str

logger = logging.getLogger(__name__)

# 对象不存在时 S3 协议可能返回的多种错误码，统一归一化为「不存在」。
_NOT_FOUND_CODES = frozenset({"404", "NoSuchKey", "NoSuchBucket", "NotFound"})

# 预签名有效期上限：过长的链接一旦泄露等同长期公开访问。
MAX_PRESIGN_EXPIRES_SECONDS = 7 * 24 * 3600


class MinioStorageProvider:
    """基于 S3 兼容 API 的存储实现。"""

    provider_name = "minio"

    def __init__(self) -> None:
        """构造客户端。

        配置缺失时在此立即抛错而不是等到首次上传：启动自检阶段暴露问题，
        比线上第一个用户上传时才失败代价低得多。
        """
        try:
            import boto3
            from botocore.client import Config
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as exc:  # pragma: no cover - 依赖缺失属部署问题
            raise StorageConfigError(
                "STORAGE_MODE=minio requires the 'boto3' package to be installed."
            ) from exc

        self._client_error = ClientError
        self._botocore_error = BotoCoreError

        endpoint = require_str("minio_endpoint", "Example: http://minio:9000")
        access_key = require_str("minio_access_key")
        secret_key = require_str("minio_secret_key")
        self._region = read_str("minio_region", "us-east-1")
        # MinIO 默认不支持虚拟主机风格寻址，必须走 path-style，否则请求会打到错误主机。
        self._addressing_style = read_str("minio_addressing_style", "path")
        self._verify_tls = read_bool("minio_verify_tls", True)
        self._default_expires = min(
            read_int("minio_presign_expires_seconds", DEFAULT_PRESIGN_EXPIRES_SECONDS),
            MAX_PRESIGN_EXPIRES_SECONDS,
        )
        # 预签名 URL 的 host 参与签名。内部地址（minio:9000）签出来的链接浏览器打不开，
        # 必须用对外可达地址单独签。未配置时回退内部地址（同机开发可用）。
        public_endpoint = read_str("minio_public_endpoint", endpoint)

        client_kwargs = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": self._region,
            "verify": self._verify_tls,
            "config": Config(
                signature_version="s3v4",
                s3={"addressing_style": self._addressing_style},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        self._client = boto3.client("s3", endpoint_url=endpoint, **client_kwargs)
        self._signing_client = (
            self._client
            if public_endpoint == endpoint
            else boto3.client("s3", endpoint_url=public_endpoint, **client_kwargs)
        )
        # 只记录端点，绝不记录密钥。
        logger.info(
            "[BIZ] minio storage provider ready endpoint=%s public_endpoint=%s",
            endpoint,
            public_endpoint,
        )

    async def _call(self, func, *args, **kwargs):
        """把同步 SDK 调用派发到线程池，避免阻塞事件循环。"""
        loop = asyncio.get_running_loop()
        bound = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, bound)

    def _error_code(self, exc: Exception) -> str:
        """提取 S3 错误码，用于判定「对象不存在」这类可预期情况。"""
        response = getattr(exc, "response", None) or {}
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        return str(error.get("Code", ""))

    async def ensure_bucket(self, bucket: str) -> None:
        """幂等确保私有桶存在。

        先 `head_bucket` 探测再创建：直接创建在桶已存在时会因不同 S3 实现返回
        不一致的错误码，探测后创建的分支判断更可靠。
        """
        try:
            await self._call(self._client.head_bucket, Bucket=bucket)
            return
        except self._client_error as exc:
            if self._error_code(exc) not in _NOT_FOUND_CODES:
                raise StorageOperationError(f"Failed to inspect bucket '{bucket}'.") from exc
        except self._botocore_error as exc:
            raise StorageOperationError(f"Failed to reach object storage for bucket '{bucket}'.") from exc

        try:
            await self._call(self._client.create_bucket, Bucket=bucket)
            logger.info("[BIZ] minio bucket created bucket=%s", bucket)
        except self._client_error as exc:
            # 并发启动多个实例时可能同时创建，已存在即视为成功（保持幂等）。
            if self._error_code(exc) in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                return
            raise StorageOperationError(f"Failed to create bucket '{bucket}'.") from exc
        except self._botocore_error as exc:
            raise StorageOperationError(f"Failed to create bucket '{bucket}'.") from exc

    async def upload(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> ObjectRef:
        """上传对象并返回可入库的引用（不含任何 URL）。"""
        await self.ensure_bucket(bucket)
        try:
            result = await self._call(
                self._client.put_object,
                Bucket=bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type or DEFAULT_CONTENT_TYPE,
            )
        except (self._client_error, self._botocore_error) as exc:
            raise StorageOperationError(f"Failed to upload object to bucket '{bucket}'.") from exc

        logger.info("[BIZ] minio object uploaded bucket=%s size=%s", bucket, len(data))
        return ObjectRef(
            bucket=bucket,
            object_key=object_key,
            size=len(data),
            etag=str(result.get("ETag", "")).strip('"'),
            content_type=content_type or DEFAULT_CONTENT_TYPE,
        )

    async def download(self, bucket: str, object_key: str) -> bytes:
        if not await self.exists(bucket, object_key):
            raise StorageObjectNotFoundError(f"Object not found in bucket '{bucket}'.")
        try:
            result = await self._call(self._client.get_object, Bucket=bucket, Key=object_key)
            body = result["Body"]
            return body.read()
        except (self._client_error, self._botocore_error) as exc:
            raise StorageOperationError(f"Failed to download object from bucket '{bucket}'.") from exc

    async def get_download_url(
        self,
        bucket: str,
        object_key: str,
        expires_seconds: int = DEFAULT_PRESIGN_EXPIRES_SECONDS,
    ) -> str:
        """生成限时预签名下载链接。

        先确认对象存在再签名：预签名接口本身不校验对象是否存在，
        否则会返回一个必然 404 的链接，把错误推迟到用户点击时才暴露。
        """
        if not await self.exists(bucket, object_key):
            raise StorageObjectNotFoundError(f"Object not found in bucket '{bucket}'.")

        expires = min(max(expires_seconds, 1), MAX_PRESIGN_EXPIRES_SECONDS)
        try:
            return await self._call(
                self._signing_client.generate_presigned_url,
                "get_object",
                Params={"Bucket": bucket, "Key": object_key},
                ExpiresIn=expires,
            )
        except (self._client_error, self._botocore_error) as exc:
            raise StorageOperationError(f"Failed to sign download url for bucket '{bucket}'.") from exc

    async def delete(self, bucket: str, object_key: str) -> None:
        """幂等删除对象；对象不存在视为成功。"""
        try:
            await self._call(self._client.delete_object, Bucket=bucket, Key=object_key)
        except self._client_error as exc:
            if self._error_code(exc) in _NOT_FOUND_CODES:
                return
            raise StorageOperationError(f"Failed to delete object from bucket '{bucket}'.") from exc
        except self._botocore_error as exc:
            raise StorageOperationError(f"Failed to delete object from bucket '{bucket}'.") from exc

    async def exists(self, bucket: str, object_key: str) -> bool:
        """判断对象是否存在。"""
        try:
            await self._call(self._client.head_object, Bucket=bucket, Key=object_key)
            return True
        except self._client_error as exc:
            if self._error_code(exc) in _NOT_FOUND_CODES:
                return False
            raise StorageOperationError(f"Failed to inspect object in bucket '{bucket}'.") from exc
        except self._botocore_error as exc:
            raise StorageOperationError(f"Failed to inspect object in bucket '{bucket}'.") from exc

    async def check_connectivity(self) -> None:
        """连通性探测（供启动自检使用）。

        用 `list_buckets` 而非某个具体桶：既验证网络可达，也验证凭据有效，
        且不依赖桶是否已创建。
        """
        try:
            await self._call(self._client.list_buckets)
        except (self._client_error, self._botocore_error) as exc:
            raise StorageOperationError("Object storage connectivity check failed.") from exc
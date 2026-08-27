"""自托管对象存储路由（`AUTH_MODE=local` 时对外提供）。

前端不直连 MinIO：上传与换链都经本路由走 `StoragePort`，
这样预签名 host、私有桶策略与 object_key 规则集中在服务端。
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from auth_providers import AuthUser
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from schemas.storage import (
    DownloadUrlRequest,
    DownloadUrlResponse,
    UploadResponse,
)
from storage_providers import (
    DEFAULT_PRESIGN_EXPIRES_SECONDS,
    StorageError,
    StorageObjectNotFoundError,
    get_storage_provider,
)
from utils.config_reader import read_int, read_str
from utils.object_key import build_object_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/storage",
    tags=["storage"],
    dependencies=[Depends(bind_trace_id)],
)

DEFAULT_MAX_FILE_MB = 15
PDF_CONTENT_TYPE = "application/pdf"


def _bucket_name() -> str:
    return read_str("contract_bucket", "contracts") or "contracts"


def _max_file_bytes() -> int:
    megabytes = read_int("max_contract_file_mb", DEFAULT_MAX_FILE_MB)
    size = megabytes if megabytes > 0 else DEFAULT_MAX_FILE_MB
    return size * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    auth_user: AuthUser = Depends(get_current_auth_user),
) -> UploadResponse:
    """接收合同 PDF 并写入当前存储实现。"""
    filename = file.filename or "contract.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目前仅支持 PDF 格式")

    payload = await file.read()
    if len(payload) > _max_file_bytes():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件超过大小限制")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件内容为空")

    object_key = build_object_key(auth_user.tenant_id, str(auth_user.id), filename)
    bucket = _bucket_name()
    try:
        ref = await get_storage_provider().upload(bucket, object_key, payload, PDF_CONTENT_TYPE)
    except StorageError as exc:
        logger.error("[BIZ] local storage upload failed type=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="对象存储暂不可用") from exc

    return UploadResponse(
        bucket_name=ref.bucket,
        object_key=ref.object_key,
        file_size=ref.size,
        content_type=ref.content_type,
    )


@router.post("/download-url", response_model=DownloadUrlResponse)
async def create_download_url(
    payload: DownloadUrlRequest,
    _auth_user: AuthUser = Depends(get_current_auth_user),
) -> DownloadUrlResponse:
    """换取限时预签名下载链接。链接不得入库。"""
    expires = read_int("minio_presign_expires_seconds", DEFAULT_PRESIGN_EXPIRES_SECONDS)
    try:
        url = await get_storage_provider().get_download_url(
            payload.bucket_name, payload.object_key, expires
        )
    except StorageObjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在") from exc
    except StorageError as exc:
        logger.error("[BIZ] local storage sign failed type=%s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="对象存储暂不可用") from exc

    return DownloadUrlResponse(download_url=url, expires_in=expires)

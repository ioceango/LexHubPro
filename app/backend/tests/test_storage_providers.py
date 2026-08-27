"""存储端口与 MinIO 适配器回归（FEAT-005）。不连接真实 MinIO。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from storage_providers.minio_provider import MAX_PRESIGN_EXPIRES_SECONDS, MinioStorageProvider
from utils.object_key import build_object_key


def test_providers_expose_storage_port_methods():
    for method in ("ensure_bucket", "upload", "download", "get_download_url", "delete", "exists"):
        assert callable(getattr(MinioStorageProvider, method))


def test_object_key_not_a_url():
    key = build_object_key("t1", "u1", "file.pdf")
    assert not key.startswith("http")
    assert "X-Amz" not in key


@pytest.mark.asyncio
async def test_minio_presign_uses_public_endpoint(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "access")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_VERIFY_TLS", "false")
    from core.config import settings

    for key in list(settings.__dict__):
        if not key.startswith("_"):
            settings.__dict__.pop(key, None)

    fake_internal = MagicMock()
    fake_signing = MagicMock()
    fake_signing.generate_presigned_url.return_value = (
        "http://localhost:9000/contracts/u1/demo.pdf?X-Amz-Signature=abc&X-Amz-Expires=900"
    )

    with patch("boto3.client", side_effect=[fake_internal, fake_signing]):
        provider = MinioStorageProvider()

    provider.exists = lambda bucket, key: _async_true()  # type: ignore[method-assign]
    url = await provider.get_download_url("contracts", "u1/demo.pdf")
    assert url.startswith("http://localhost:9000/")
    assert "X-Amz-Signature=" in url
    fake_signing.generate_presigned_url.assert_called()
    assert provider._default_expires <= MAX_PRESIGN_EXPIRES_SECONDS


async def _async_true(*_args, **_kwargs):
    return True


@pytest.mark.asyncio
async def test_minio_delete_missing_object_is_idempotent(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "access")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_VERIFY_TLS", "false")
    from core.config import settings

    for key in list(settings.__dict__):
        if not key.startswith("_"):
            settings.__dict__.pop(key, None)

    class NotFound(Exception):
        pass

    fake_client = MagicMock()
    error = type("ClientError", (Exception,), {})()
    error.response = {"Error": {"Code": "NoSuchKey"}}
    fake_client.delete_object.side_effect = error

    with patch("boto3.client", return_value=fake_client):
        provider = MinioStorageProvider()
        provider._client_error = type(error)

    await provider.delete("contracts", "missing.pdf")

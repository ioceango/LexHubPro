"""自托管对象存储接口的请求与响应。

只返回可入库字段；下载链接是临时的，调用方不得把它写进数据库。
"""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """上传成功后的对象引用。"""

    bucket_name: str
    object_key: str
    file_size: int = 0
    content_type: str = "application/pdf"


class DownloadUrlRequest(BaseModel):
    """按对象键换取限时下载链接。"""

    bucket_name: str = Field(..., min_length=1, max_length=128)
    object_key: str = Field(..., min_length=1, max_length=512)


class DownloadUrlResponse(BaseModel):
    """限时预签名下载链接，禁止入库。"""

    download_url: str
    expires_in: int

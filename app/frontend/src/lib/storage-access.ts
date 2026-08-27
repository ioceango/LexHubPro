/**
 * 对象存储封装：上传与预签名下载只打自建 API。
 */

import { localRequest } from '@/lib/http';

const STORAGE_PREFIX = '/api/v1/storage';

export interface UploadedObject {
  bucket_name: string;
  object_key: string;
  file_size?: number;
}

export const storageApi = {
  async upload(file: File): Promise<UploadedObject> {
    const body = new FormData();
    body.append('file', file);
    return localRequest<UploadedObject>(`${STORAGE_PREFIX}/upload`, {
      method: 'POST',
      data: body,
    });
  },

  async getDownloadUrl(bucketName: string, objectKey: string): Promise<string> {
    const result = await localRequest<{ download_url: string }>(`${STORAGE_PREFIX}/download-url`, {
      method: 'POST',
      data: { bucket_name: bucketName, object_key: objectKey },
    });
    return result.download_url;
  },
};

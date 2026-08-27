/**
 * 自托管形态的统一 HTTP 封装。
 *
 * 页面禁止直接 fetch/axios。本模块负责：同源请求、Bearer、Cookie 刷新、错误解包。
 */

let accessToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

const REFRESH_PATH = '/api/v1/auth/refresh';

export const setAccessToken = (token: string | null): void => {
  accessToken = token;
};

export const getAccessToken = (): string | null => accessToken;

export class LocalHttpError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

const readDetail = async (response: Response): Promise<string> => {
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') return body.detail;
    if (typeof body?.message === 'string') return body.message;
  } catch {
    /* 响应不是 JSON 时退回状态码文案 */
  }
  return `请求失败（${response.status}）`;
};

const refreshSession = async (): Promise<boolean> => {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetch(REFRESH_PATH, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!response.ok) {
        setAccessToken(null);
        return false;
      }
      const data = (await response.json()) as { access_token?: string };
      if (!data.access_token) {
        setAccessToken(null);
        return false;
      }
      setAccessToken(data.access_token);
      return true;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
};

interface LocalRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data?: Record<string, unknown> | FormData;
  skipRefresh?: boolean;
  timeoutMs?: number;
}

export const localRequest = async <T>(path: string, options: LocalRequestOptions = {}): Promise<T> => {
  const method = options.method ?? 'GET';
  const headers = new Headers();
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  let body: BodyInit | undefined;
  if (options.data instanceof FormData) {
    body = options.data;
  } else if (options.data && method !== 'GET') {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(options.data);
  }

  const controller = options.timeoutMs ? new AbortController() : undefined;
  const timer = options.timeoutMs
    ? window.setTimeout(() => controller?.abort(), options.timeoutMs)
    : undefined;

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      credentials: 'include',
      headers,
      body,
      signal: controller?.signal,
    });
  } finally {
    if (timer) window.clearTimeout(timer);
  }

  const canRefresh = !options.skipRefresh && path !== REFRESH_PATH;
  if (response.status === 401 && canRefresh && (await refreshSession())) {
    return localRequest<T>(path, { ...options, skipRefresh: true });
  }

  if (!response.ok) {
    throw new LocalHttpError(response.status, await readDetail(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
};

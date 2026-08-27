import { localRequest } from '@/lib/http';

export interface LlmProviderView {
  provider: string;
  name: string;
  configured: boolean;
  key_suffix: string;
}

export interface LlmCatalogItem {
  id: string;
  name: string;
}

export interface LlmModelView {
  id: number;
  provider: string;
  model_id: string;
  display_name: string;
  enabled: boolean;
}

export interface LlmActiveView {
  configured: boolean;
  provider?: string | null;
  model_id?: string | null;
  display_name?: string | null;
}

export const llmApi = {
  providers: () => localRequest<LlmProviderView[]>('/api/v1/llm/providers'),
  saveKey: (provider: string, api_key: string) =>
    localRequest<{ configured: boolean; key_suffix: string }>(`/api/v1/llm/providers/${provider}/key`, {
      method: 'PUT',
      data: { api_key },
    }),
  deleteKey: (provider: string) =>
    localRequest(`/api/v1/llm/providers/${provider}/key`, { method: 'DELETE', data: {} }),
  refreshModels: (provider: string) =>
    localRequest<{ items: LlmCatalogItem[] }>(`/api/v1/llm/providers/${provider}/models/refresh`, {
      method: 'POST',
      data: {},
    }),
  models: () => localRequest<LlmModelView[]>('/api/v1/llm/models'),
  addModel: (payload: { provider: string; model_id: string; display_name?: string; enabled?: boolean }) =>
    localRequest<LlmModelView>('/api/v1/llm/models', { method: 'PUT', data: payload }),
  setEnabled: (id: number, enabled: boolean) =>
    localRequest<LlmModelView>(`/api/v1/llm/models/${id}`, { method: 'PATCH', data: { enabled } }),
  removeModel: (id: number) => localRequest(`/api/v1/llm/models/${id}`, { method: 'DELETE', data: {} }),
  active: () => localRequest<LlmActiveView>('/api/v1/llm/active'),
};

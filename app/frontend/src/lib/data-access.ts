/**
 * 业务数据访问：合同、报告、审查。只走自建 HTTP。
 */

import { localRequest } from '@/lib/http';
import type { AnalyzeResult, ContractRecord, ReportRecord } from '@/lib/review';

const DEFAULT_LIST_LIMIT = 100;

interface ListResult<T> {
  items: T[];
  total: number;
}

export interface ReportSummary {
  report_count: number;
  average_score: number | null;
  high_risk_total: number;
  medium_risk_total: number;
  low_risk_total: number;
}

export const contractsApi = {
  async create(payload: Record<string, unknown>): Promise<ContractRecord> {
    const body = { ...payload };
    delete body.status;
    return localRequest<ContractRecord>('/api/v1/contracts', { method: 'POST', data: body });
  },

  async get(id: number | string): Promise<ContractRecord> {
    return localRequest<ContractRecord>(`/api/v1/contracts/${id}`, { method: 'GET' });
  },

  async list(limit: number = DEFAULT_LIST_LIMIT): Promise<ContractRecord[]> {
    const result = await localRequest<ListResult<ContractRecord>>(
      `/api/v1/contracts?limit=${limit}&offset=0`,
      { method: 'GET' },
    );
    return result.items ?? [];
  },

  async updateStatus(
    id: number | string,
    status: string,
    extra: Record<string, unknown> = {},
  ): Promise<void> {
    await localRequest(`/api/v1/contracts/${id}/status`, {
      method: 'PATCH',
      data: {
        status,
        error_message: (extra.error_message as string | undefined) ?? null,
      },
    });
  },

  async remove(id: number | string): Promise<void> {
    await localRequest(`/api/v1/contracts/${id}`, { method: 'DELETE' });
  },
};

export const reportsApi = {
  async create(payload: Record<string, unknown>): Promise<ReportRecord> {
    return localRequest<ReportRecord>('/api/v1/reports', { method: 'POST', data: payload });
  },

  async get(id: number | string): Promise<ReportRecord> {
    return localRequest<ReportRecord>(`/api/v1/reports/${id}`, { method: 'GET' });
  },

  async list(limit: number = DEFAULT_LIST_LIMIT): Promise<ReportRecord[]> {
    const result = await localRequest<ListResult<ReportRecord>>(
      `/api/v1/reports?limit=${limit}&offset=0`,
      { method: 'GET' },
    );
    return result.items ?? [];
  },

  async summary(): Promise<ReportSummary> {
    return localRequest<ReportSummary>('/api/v1/reports/summary', { method: 'GET' });
  },

  async remove(id: number | string): Promise<void> {
    await localRequest(`/api/v1/reports/${id}`, { method: 'DELETE' });
  },
};

export const analyzeContract = async (payload: {
  contract_id: number;
  contract_type: string;
  party_role: string;
}): Promise<AnalyzeResult> => {
  return localRequest<AnalyzeResult>('/api/v1/review/analyze', {
    method: 'POST',
    data: payload,
    timeoutMs: 600_000,
  });
};

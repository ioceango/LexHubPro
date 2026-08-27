import { storageApi } from '@/lib/storage-access';

export const CONTRACT_BUCKET = 'contracts';

export type RiskLevel = 'high' | 'medium' | 'low';
export type ComplianceStatus = 'pass' | 'warn' | 'fail';

export interface KeyTerm {
  label: string;
  value: string;
}

export interface RiskClause {
  clause_title: string;
  original_text: string;
  risk_level: RiskLevel;
  risk_reason: string;
  impact: string;
  suggestion: string;
}

export interface MissingClause {
  clause_name: string;
  importance: RiskLevel;
  reason: string;
  recommended_text: string;
}

export interface ComplianceCheck {
  item: string;
  status: ComplianceStatus;
  law_reference: string;
  detail: string;
}

export interface AnalyzeResult {
  report_id?: number;
  contract_type: string;
  overall_score: number;
  risk_level: RiskLevel;
  summary: string;
  key_terms: KeyTerm[];
  risk_clauses: RiskClause[];
  missing_clauses: MissingClause[];
  compliance_checks: ComplianceCheck[];
  suggestions: string[];
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  raw_text_excerpt: string;
}

export interface ContractRecord {
  id: number;
  title: string;
  file_name: string;
  bucket_name: string;
  object_key: string;
  file_size?: number | null;
  contract_type?: string | null;
  party_role?: string | null;
  status: string;
  error_message?: string | null;
  created_at?: string | null;
}

export interface ReportRecord {
  id: number;
  contract_id: number;
  contract_title: string;
  contract_type?: string | null;
  overall_score: number;
  risk_level: string;
  summary: string;
  high_risk_count?: number | null;
  medium_risk_count?: number | null;
  low_risk_count?: number | null;
  risk_clauses?: string | null;
  missing_clauses?: string | null;
  compliance_checks?: string | null;
  key_terms?: string | null;
  suggestions?: string | null;
  raw_text_excerpt?: string | null;
  created_at?: string | null;
}

export const CONTRACT_TYPES = [
  '采购/买卖合同',
  '劳动合同',
  '房屋租赁合同',
  '服务/外包合同',
  '技术开发合同',
  '股权/投资协议',
  '借款合同',
  '保密协议(NDA)',
  '其他',
];

export const PARTY_ROLES = ['甲方', '乙方', '出租方', '承租方', '雇主', '员工', '不确定'];

export const RISK_LABEL: Record<RiskLevel, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
};

export const COMPLIANCE_LABEL: Record<ComplianceStatus, string> = {
  pass: '通过',
  warn: '需注意',
  fail: '不合规',
};

/** AI 额度耗尽：后端返回 402，重试无意义，需先充值 */
export const HTTP_QUOTA_EXHAUSTED = 402;
/** 未配置或未启用审查模型：后端返回 409，应去配置页 */
export const HTTP_MODEL_REQUIRED = 409;
/** AI 服务瞬时不可用：后端返回 503，可稍后重试 */
export const HTTP_SERVICE_UNAVAILABLE = 503;

export interface ApiErrorInfo {
  /** 可直接展示给用户的错误说明 */
  detail: string;
  /** HTTP 状态码，未知时为 0 */
  status: number;
  /** 是否值得让用户点击重试 */
  retryable: boolean;
}

export const getErrorDetail = (error: unknown): string => {
  const err = error as {
    data?: { detail?: string };
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return err?.data?.detail || err?.response?.data?.detail || err?.message || '请求失败，请稍后重试';
};

const getErrorStatus = (error: unknown): number => {
  const err = error as {
    status?: number;
    statusCode?: number;
    response?: { status?: number };
  };
  return err?.status || err?.statusCode || err?.response?.status || 0;
};

/** 解析后端错误，区分「额度耗尽」与「可重试故障」两类失败 */
export const getApiErrorInfo = (error: unknown): ApiErrorInfo => {
  const status = getErrorStatus(error);
  return {
    detail: getErrorDetail(error),
    status,
    retryable:
      status !== HTTP_QUOTA_EXHAUSTED &&
      status !== HTTP_MODEL_REQUIRED &&
      status !== 400 &&
      status !== 422,
  };
};

export const fileToDataUri = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsDataURL(file);
  });

export const normalizeRiskLevel = (value?: string | null): RiskLevel => {
  if (value === 'high' || value === 'medium' || value === 'low') return value;
  return 'medium';
};

export const normalizeComplianceStatus = (value?: string | null): ComplianceStatus => {
  if (value === 'pass' || value === 'warn' || value === 'fail') return value;
  return 'warn';
};

/** 安全解析报告中的 JSON 字符串字段 */
export const parseJsonField = <T,>(raw: string | null | undefined, fallback: T): T => {
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw);
    return (parsed ?? fallback) as T;
  } catch {
    return fallback;
  }
};

export const formatDateTime = (value?: string | null): string => {
  if (!value) return '—';
  const date = new Date(value.includes('Z') || value.includes('+') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const formatFileSize = (bytes?: number | null): string => {
  if (!bytes || bytes <= 0) return '—';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
};

/** 生成合同报告的纯文本，用于复制与导出 */
export const buildReportText = (
  report: ReportRecord,
  parts: {
    keyTerms: KeyTerm[];
    riskClauses: RiskClause[];
    missingClauses: MissingClause[];
    complianceChecks: ComplianceCheck[];
    suggestions: string[];
  },
): string => {
  const lines: string[] = [];
  lines.push(`合同审查报告 - ${report.contract_title}`);
  lines.push(`合同类型：${report.contract_type || '未识别'}`);
  lines.push(`整体安全评分：${report.overall_score}/100`);
  lines.push(`整体风险等级：${RISK_LABEL[normalizeRiskLevel(report.risk_level)]}`);
  lines.push(`审查时间：${formatDateTime(report.created_at)}`);
  lines.push('');
  lines.push('【总体结论】');
  lines.push(report.summary);

  if (parts.keyTerms.length) {
    lines.push('');
    lines.push('【关键商务条款】');
    parts.keyTerms.forEach((term) => lines.push(`- ${term.label}：${term.value}`));
  }

  if (parts.riskClauses.length) {
    lines.push('');
    lines.push('【风险条款】');
    parts.riskClauses.forEach((clause, index) => {
      lines.push(`${index + 1}. [${RISK_LABEL[normalizeRiskLevel(clause.risk_level)]}] ${clause.clause_title}`);
      if (clause.original_text) lines.push(`   原文：${clause.original_text}`);
      if (clause.risk_reason) lines.push(`   风险说明：${clause.risk_reason}`);
      if (clause.impact) lines.push(`   潜在影响：${clause.impact}`);
      if (clause.suggestion) lines.push(`   修改建议：${clause.suggestion}`);
    });
  }

  if (parts.missingClauses.length) {
    lines.push('');
    lines.push('【缺失条款】');
    parts.missingClauses.forEach((item, index) => {
      lines.push(`${index + 1}. [${RISK_LABEL[normalizeRiskLevel(item.importance)]}] ${item.clause_name}`);
      if (item.reason) lines.push(`   缺失原因说明：${item.reason}`);
      if (item.recommended_text) lines.push(`   建议补充：${item.recommended_text}`);
    });
  }

  if (parts.complianceChecks.length) {
    lines.push('');
    lines.push('【合规性检查】');
    parts.complianceChecks.forEach((check, index) => {
      lines.push(`${index + 1}. [${COMPLIANCE_LABEL[normalizeComplianceStatus(check.status)]}] ${check.item}`);
      if (check.law_reference) lines.push(`   法律依据：${check.law_reference}`);
      if (check.detail) lines.push(`   结论：${check.detail}`);
    });
  }

  if (parts.suggestions.length) {
    lines.push('');
    lines.push('【整体修改建议】');
    parts.suggestions.forEach((item, index) => lines.push(`${index + 1}. ${item}`));
  }

  lines.push('');
  lines.push('※ 本报告由 AI 生成，仅供参考，不构成正式法律意见。');
  return lines.join('\n');
};

/** 触发浏览器下载纯文本报告 */
export const downloadTextFile = (fileName: string, content: string): void => {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

/** 获取合同原文件的下载地址 */
export const resolveContractDownloadUrl = async (contract: ContractRecord): Promise<string> => {
  return storageApi.getDownloadUrl(contract.bucket_name || CONTRACT_BUCKET, contract.object_key);
};
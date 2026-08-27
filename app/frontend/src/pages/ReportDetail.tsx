import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Copy,
  Download,
  FileDown,
  Loader2,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import SiteHeader from '@/components/SiteHeader';
import { useAuth } from '@/hooks/use-auth';
import { contractsApi, reportsApi } from '@/lib/data-access';
import {
  COMPLIANCE_LABEL,
  ComplianceCheck,
  ContractRecord,
  KeyTerm,
  MissingClause,
  RISK_LABEL,
  ReportRecord,
  RiskClause,
  buildReportText,
  downloadTextFile,
  formatDateTime,
  getErrorDetail,
  normalizeComplianceStatus,
  normalizeRiskLevel,
  parseJsonField,
  resolveContractDownloadUrl,
} from '@/lib/review';
import { toast } from 'sonner';

const RISK_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const riskClasses = (level: string) => {
  const normalized = normalizeRiskLevel(level);
  if (normalized === 'high') return 'text-risk-high bg-risk-high border-risk-high';
  if (normalized === 'low') return 'text-risk-low bg-risk-low border-risk-low';
  return 'text-risk-medium bg-risk-medium border-risk-medium';
};

const ComplianceIcon = ({ status }: { status: string }) => {
  const normalized = normalizeComplianceStatus(status);
  if (normalized === 'pass') return <CheckCircle2 className="h-4 w-4 shrink-0 text-risk-low" />;
  if (normalized === 'fail') return <XCircle className="h-4 w-4 shrink-0 text-risk-high" />;
  return <AlertTriangle className="h-4 w-4 shrink-0 text-risk-medium" />;
};

const ReportDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { status, login, logout } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [report, setReport] = useState<ReportRecord | null>(null);
  const [contract, setContract] = useState<ContractRecord | null>(null);
  const [downloading, setDownloading] = useState(false);

  const loadReport = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const record = await reportsApi.get(id);
      setReport(record);
      if (record?.contract_id) {
        try {
          setContract(await contractsApi.get(record.contract_id));
        } catch {
          setContract(null);
        }
      }
    } catch (e) {
      setError(getErrorDetail(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (status === 'authenticated') {
      loadReport();
    } else if (status === 'anonymous') {
      setLoading(false);
    }
  }, [status, loadReport]);

  const riskClauses = parseJsonField<RiskClause[]>(report?.risk_clauses, []).slice().sort(
    (a, b) =>
      (RISK_ORDER[normalizeRiskLevel(a.risk_level)] ?? 1) -
      (RISK_ORDER[normalizeRiskLevel(b.risk_level)] ?? 1),
  );
  const missingClauses = parseJsonField<MissingClause[]>(report?.missing_clauses, []);
  const complianceChecks = parseJsonField<ComplianceCheck[]>(report?.compliance_checks, []);
  const keyTerms = parseJsonField<KeyTerm[]>(report?.key_terms, []);
  const suggestions = parseJsonField<string[]>(report?.suggestions, []);

  const reportText = report
    ? buildReportText(report, { keyTerms, riskClauses, missingClauses, complianceChecks, suggestions })
    : '';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(reportText);
      toast.success('报告内容已复制到剪贴板');
    } catch {
      toast.error('复制失败，请手动选择文本复制');
    }
  };

  const handleExport = () => {
    if (!report) return;
    downloadTextFile(`合同审查报告-${report.contract_title}.txt`, reportText);
    toast.success('报告已导出');
  };

  const handleDownloadOriginal = async () => {
    if (!contract) return;
    setDownloading(true);
    try {
      const url = await resolveContractDownloadUrl(contract);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      toast.error(getErrorDetail(e));
    } finally {
      setDownloading(false);
    }
  };

  const renderContent = () => {
    if (status === 'anonymous') {
      return (
        <Alert className="border-primary/30 bg-primary/[0.07]">
          <ShieldAlert className="h-4 w-4 text-primary" />
          <AlertTitle>请先登录</AlertTitle>
          <AlertDescription className="mt-2">
            审查报告仅本人可见，登录后即可查看。
            <div className="mt-4">
              <Button size="sm" onClick={login}>
                登录 / 注册
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      );
    }

    if (loading || status === 'loading') {
      return (
        <div className="space-y-5">
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-64 w-full" />
        </div>
      );
    }

    if (error || !report) {
      return (
        <Alert variant="destructive">
          <AlertTitle>无法加载审查报告</AlertTitle>
          <AlertDescription className="mt-2">
            {error || '未找到该报告，它可能已被删除。'}
            <div className="mt-4 flex gap-3">
              <Button size="sm" variant="outline" className="!bg-transparent hover:!bg-transparent" onClick={loadReport}>
                重新加载
              </Button>
              <Button size="sm" onClick={() => navigate('/history')}>
                返回历史记录
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      );
    }

    const overallLevel = normalizeRiskLevel(report.risk_level);

    return (
      <>
        {/* 概览 */}
        <section className="rounded-lg border border-border/70 bg-card p-6 sm:p-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <Badge className={`border ${riskClasses(overallLevel)}`} variant="outline">
                  整体{RISK_LABEL[overallLevel]}
                </Badge>
                {report.contract_type && (
                  <Badge variant="secondary">{report.contract_type}</Badge>
                )}
                <span className="text-xs text-muted-foreground">
                  审查时间 {formatDateTime(report.created_at)}
                </span>
              </div>
              <h1 className="mt-4 break-words text-2xl sm:text-3xl">{report.contract_title}</h1>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{report.summary}</p>

              <div className="mt-6 grid grid-cols-3 gap-4 border-t border-border/60 pt-6">
                <div>
                  <div className="font-serif text-2xl text-risk-high">{report.high_risk_count ?? 0}</div>
                  <div className="mt-1 text-xs text-muted-foreground">高风险条款</div>
                </div>
                <div>
                  <div className="font-serif text-2xl text-risk-medium">{report.medium_risk_count ?? 0}</div>
                  <div className="mt-1 text-xs text-muted-foreground">中风险条款</div>
                </div>
                <div>
                  <div className="font-serif text-2xl text-risk-low">{report.low_risk_count ?? 0}</div>
                  <div className="mt-1 text-xs text-muted-foreground">低风险条款</div>
                </div>
              </div>
            </div>

            <div className="w-full shrink-0 rounded-md border border-primary/25 bg-primary/[0.06] p-6 lg:w-64">
              <div className="text-xs tracking-wider text-muted-foreground">整体安全评分</div>
              <div className="mt-2 flex items-end gap-1">
                <span className="font-serif text-5xl text-primary">{report.overall_score}</span>
                <span className="pb-2 text-sm text-muted-foreground">/ 100</span>
              </div>
              <Progress value={report.overall_score} className="mt-4" />
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                分数越高表示合同条款对你越安全，低于 60 分建议在签署前完成修改。
              </p>
            </div>
          </div>

          <div className="mt-7 flex flex-wrap gap-3 border-t border-border/60 pt-6">
            <Button size="sm" onClick={handleCopy}>
              <Copy className="mr-2 h-4 w-4" />
              复制报告
            </Button>
            <Button size="sm" variant="outline" className="!bg-transparent hover:!bg-transparent" onClick={handleExport}>
              <FileDown className="mr-2 h-4 w-4" />
              导出报告
            </Button>
            {contract && (
              <Button
                size="sm"
                variant="outline"
                className="!bg-transparent hover:!bg-transparent"
                onClick={handleDownloadOriginal}
                disabled={downloading}
              >
                {downloading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                下载合同原件
              </Button>
            )}
          </div>
        </section>

        {/* 明细 */}
        <Tabs defaultValue="risk" className="mt-8">
          <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
            <TabsTrigger value="risk">风险条款 ({riskClauses.length})</TabsTrigger>
            <TabsTrigger value="missing">缺失条款 ({missingClauses.length})</TabsTrigger>
            <TabsTrigger value="compliance">合规检查 ({complianceChecks.length})</TabsTrigger>
            <TabsTrigger value="terms">关键条款</TabsTrigger>
          </TabsList>

          <TabsContent value="risk" className="mt-6 space-y-4">
            {riskClauses.length === 0 && (
              <p className="rounded-lg border border-border/70 bg-card p-8 text-sm text-muted-foreground">
                本次审查未识别出明确的风险条款，请结合总体结论判断。
              </p>
            )}
            {riskClauses.map((clause, index) => {
              const level = normalizeRiskLevel(clause.risk_level);
              return (
                <article key={`${clause.clause_title}-${index}`} className="rounded-lg border border-border/70 bg-card p-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge className={`border ${riskClasses(level)}`} variant="outline">
                      {RISK_LABEL[level]}
                    </Badge>
                    <h3 className="text-base">{clause.clause_title}</h3>
                  </div>

                  {clause.original_text && (
                    <blockquote className="mt-4 rounded-md bg-muted/60 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
                      {clause.original_text}
                    </blockquote>
                  )}

                  <dl className="mt-5 space-y-4 text-sm leading-relaxed">
                    {clause.risk_reason && (
                      <div>
                        <dt className="text-xs tracking-wider text-primary">风险说明</dt>
                        <dd className="mt-1.5">{clause.risk_reason}</dd>
                      </div>
                    )}
                    {clause.impact && (
                      <div>
                        <dt className="text-xs tracking-wider text-primary">潜在影响</dt>
                        <dd className="mt-1.5 text-muted-foreground">{clause.impact}</dd>
                      </div>
                    )}
                    {clause.suggestion && (
                      <div>
                        <dt className="text-xs tracking-wider text-primary">修改建议</dt>
                        <dd className="mt-1.5">{clause.suggestion}</dd>
                      </div>
                    )}
                  </dl>
                </article>
              );
            })}
          </TabsContent>

          <TabsContent value="missing" className="mt-6 space-y-4">
            {missingClauses.length === 0 && (
              <p className="rounded-lg border border-border/70 bg-card p-8 text-sm text-muted-foreground">
                未发现明显缺失的标准条款。
              </p>
            )}
            {missingClauses.map((item, index) => {
              const level = normalizeRiskLevel(item.importance);
              return (
                <article key={`${item.clause_name}-${index}`} className="rounded-lg border border-border/70 bg-card p-6">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge className={`border ${riskClasses(level)}`} variant="outline">
                      重要性：{RISK_LABEL[level]}
                    </Badge>
                    <h3 className="text-base">{item.clause_name}</h3>
                  </div>
                  {item.reason && (
                    <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{item.reason}</p>
                  )}
                  {item.recommended_text && (
                    <div className="mt-5">
                      <div className="text-xs tracking-wider text-primary">建议补充条款</div>
                      <blockquote className="mt-2 rounded-md bg-muted/60 px-4 py-3 text-sm leading-relaxed">
                        {item.recommended_text}
                      </blockquote>
                    </div>
                  )}
                </article>
              );
            })}
          </TabsContent>

          <TabsContent value="compliance" className="mt-6 space-y-3">
            {complianceChecks.length === 0 && (
              <p className="rounded-lg border border-border/70 bg-card p-8 text-sm text-muted-foreground">
                暂无合规检查结论。
              </p>
            )}
            {complianceChecks.map((check, index) => (
              <article key={`${check.item}-${index}`} className="rounded-lg border border-border/70 bg-card p-6">
                <div className="flex items-start gap-3">
                  <ComplianceIcon status={check.status} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base">{check.item}</h3>
                      <span className="text-xs text-muted-foreground">
                        {COMPLIANCE_LABEL[normalizeComplianceStatus(check.status)]}
                      </span>
                    </div>
                    {check.detail && (
                      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{check.detail}</p>
                    )}
                    {check.law_reference && (
                      <p className="mt-3 text-xs text-primary">法律依据：{check.law_reference}</p>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </TabsContent>

          <TabsContent value="terms" className="mt-6 space-y-4">
            {keyTerms.length > 0 ? (
              <div className="overflow-hidden rounded-lg border border-border/70 bg-card">
                <dl className="divide-y divide-border/60">
                  {keyTerms.map((term, index) => (
                    <div key={`${term.label}-${index}`} className="grid gap-2 px-6 py-4 sm:grid-cols-4">
                      <dt className="text-sm text-muted-foreground">{term.label}</dt>
                      <dd className="text-sm leading-relaxed sm:col-span-3">{term.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : (
              <p className="rounded-lg border border-border/70 bg-card p-8 text-sm text-muted-foreground">
                未提取到关键商务条款。
              </p>
            )}

            {suggestions.length > 0 && (
              <div className="rounded-lg border border-primary/25 bg-primary/[0.06] p-6">
                <h3 className="text-base">整体修改建议</h3>
                <ol className="mt-4 space-y-3 text-sm leading-relaxed">
                  {suggestions.map((item, index) => (
                    <li key={index} className="flex gap-3">
                      <span className="font-serif text-primary">{index + 1}</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <p className="mt-8 text-xs leading-relaxed text-muted-foreground">
          ※ 本报告由 AI 生成，仅供参考，不构成正式法律意见。重大交易请咨询执业律师。
        </p>
      </>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />
      <main className="mx-auto max-w-screen-lg px-4 py-10 sm:px-6 lg:px-8">
        <Link
          to="/history"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回审查历史
        </Link>
        <div className="mt-6">{renderContent()}</div>
      </main>
    </div>
  );
};

export default ReportDetail;
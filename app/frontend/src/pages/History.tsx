import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FilePlus2, FileText, Loader2, ShieldAlert, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import SiteHeader from '@/components/SiteHeader';
import { useAuth } from '@/hooks/use-auth';
import { contractsApi, reportsApi } from '@/lib/data-access';
import {
  ContractRecord,
  RISK_LABEL,
  ReportRecord,
  formatDateTime,
  formatFileSize,
  getErrorDetail,
  normalizeRiskLevel,
} from '@/lib/review';
import { toast } from 'sonner';

const riskClasses = (level: string) => {
  const normalized = normalizeRiskLevel(level);
  if (normalized === 'high') return 'text-risk-high bg-risk-high border-risk-high';
  if (normalized === 'low') return 'text-risk-low bg-risk-low border-risk-low';
  return 'text-risk-medium bg-risk-medium border-risk-medium';
};

const STATUS_LABEL: Record<string, string> = {
  pending: '待审查',
  reviewing: '审查中',
  completed: '已完成',
  failed: '审查失败',
  // 自托管原始词表兜底：即使映射层遗漏，也不会渲染成空白标签
  uploaded: '待审查',
  analyzing: '审查中',
};

const History = () => {
  const navigate = useNavigate();
  const { status, login, logout } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [contracts, setContracts] = useState<ContractRecord[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<ContractRecord | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [reportItems, contractItems] = await Promise.all([
        reportsApi.list(),
        contractsApi.list(),
      ]);
      setReports(reportItems);
      setContracts(contractItems);
    } catch (e) {
      setError(getErrorDetail(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === 'authenticated') {
      loadData();
    } else if (status === 'anonymous') {
      setLoading(false);
    }
  }, [status, loadData]);

  const reportByContract = new Map<number, ReportRecord>();
  reports.forEach((report) => {
    if (!reportByContract.has(report.contract_id)) {
      reportByContract.set(report.contract_id, report);
    }
  });

  const highTotal = reports.reduce((sum, item) => sum + (item.high_risk_count ?? 0), 0);
  const averageScore = reports.length
    ? Math.round(reports.reduce((sum, item) => sum + (item.overall_score ?? 0), 0) / reports.length)
    : 0;

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const relatedReports = reports.filter((item) => item.contract_id === deleteTarget.id);
      for (const item of relatedReports) {
        await reportsApi.remove(item.id);
      }
      await contractsApi.remove(deleteTarget.id);
      setReports((prev) => prev.filter((item) => item.contract_id !== deleteTarget.id));
      setContracts((prev) => prev.filter((item) => item.id !== deleteTarget.id));
      toast.success('已删除该合同及其审查报告');
      setDeleteTarget(null);
    } catch (e) {
      toast.error(getErrorDetail(e));
    } finally {
      setDeleting(false);
    }
  };

  const renderContent = () => {
    if (status === 'anonymous') {
      return (
        <Alert className="border-primary/30 bg-primary/[0.07]">
          <ShieldAlert className="h-4 w-4 text-primary" />
          <AlertTitle>请先登录查看你的审查记录</AlertTitle>
          <AlertDescription className="mt-2">
            所有合同与报告按账号隔离存储，仅本人可见。
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
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      );
    }

    if (error) {
      return (
        <Alert variant="destructive">
          <AlertTitle>加载失败</AlertTitle>
          <AlertDescription className="mt-2">
            {error}
            <div className="mt-4">
              <Button size="sm" variant="outline" className="!bg-transparent hover:!bg-transparent" onClick={loadData}>
                重新加载
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      );
    }

    if (contracts.length === 0) {
      return (
        <div className="rounded-lg border border-dashed border-border bg-card/50 p-14 text-center">
          <FileText className="mx-auto h-8 w-8 text-primary" />
          <h3 className="mt-5 text-lg">还没有审查记录</h3>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted-foreground">
            上传第一份合同，AI 会为你识别风险条款、提示缺失条款并生成完整审查报告。
          </p>
          <Button className="mt-7" onClick={() => navigate('/review')}>
            <FilePlus2 className="mr-2 h-4 w-4" />
            上传合同
          </Button>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {contracts.map((contract) => {
          const report = reportByContract.get(contract.id);
          const level = report ? normalizeRiskLevel(report.risk_level) : null;
          return (
            <article
              key={contract.id}
              className="rounded-lg border border-border/70 bg-card p-6 transition-colors duration-200 hover:border-primary/35"
            >
              <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    {level && (
                      <Badge className={`border ${riskClasses(level)}`} variant="outline">
                        {RISK_LABEL[level]}
                      </Badge>
                    )}
                    <Badge variant="secondary">{STATUS_LABEL[contract.status] ?? contract.status}</Badge>
                    {contract.contract_type && (
                      <span className="text-xs text-muted-foreground">{contract.contract_type}</span>
                    )}
                  </div>
                  <h3 className="mt-3 break-words text-lg">{contract.title}</h3>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {contract.file_name} · {formatFileSize(contract.file_size)} ·{' '}
                    {formatDateTime(contract.created_at)}
                    {contract.party_role ? ` · 立场：${contract.party_role}` : ''}
                  </p>

                  {report ? (
                    <>
                      <p className="mt-4 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                        {report.summary}
                      </p>
                      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted-foreground">
                        <span>
                          安全评分 <span className="font-serif text-base text-primary">{report.overall_score}</span>
                        </span>
                        <span className="text-risk-high">高风险 {report.high_risk_count ?? 0}</span>
                        <span className="text-risk-medium">中风险 {report.medium_risk_count ?? 0}</span>
                        <span className="text-risk-low">低风险 {report.low_risk_count ?? 0}</span>
                      </div>
                    </>
                  ) : (
                    <p className="mt-4 text-sm text-muted-foreground">
                      {contract.status === 'failed'
                        ? contract.error_message || '上次审查未完成，可重新上传该合同再试。'
                        : '尚未生成审查报告。'}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {report && (
                    <Button size="sm" onClick={() => navigate(`/report/${report.id}`)}>
                      查看报告
                    </Button>
                  )}
                  {!report && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="!bg-transparent hover:!bg-transparent"
                      onClick={() => navigate('/review')}
                    >
                      重新审查
                    </Button>
                  )}
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label="删除合同"
                    onClick={() => setDeleteTarget(contract)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    );
  };

  const showStats = status === 'authenticated' && !loading && !error && reports.length > 0;

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />

      <main className="mx-auto max-w-screen-lg px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="text-xs tracking-wider text-primary">审查历史</span>
            <h1 className="mt-3 text-3xl">我的合同与报告</h1>
          </div>
          <Button onClick={() => navigate('/review')}>
            <FilePlus2 className="mr-2 h-4 w-4" />
            上传新合同
          </Button>
        </div>

        {showStats && (
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-border/70 bg-card p-5">
              <div className="text-xs text-muted-foreground">累计审查</div>
              <div className="mt-2 font-serif text-3xl text-primary">{reports.length}</div>
            </div>
            <div className="rounded-lg border border-border/70 bg-card p-5">
              <div className="text-xs text-muted-foreground">平均安全评分</div>
              <div className="mt-2 font-serif text-3xl text-primary">{averageScore}</div>
            </div>
            <div className="rounded-lg border border-border/70 bg-card p-5">
              <div className="text-xs text-muted-foreground">累计高风险条款</div>
              <div className="mt-2 font-serif text-3xl text-risk-high">{highTotal}</div>
            </div>
          </div>
        )}

        <div className="mt-8">{renderContent()}</div>
      </main>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>删除这份合同？</AlertDialogTitle>
            <AlertDialogDescription>
              将同时删除「{deleteTarget?.title}」及其关联的审查报告，此操作无法撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>保留合同</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              删除合同
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default History;
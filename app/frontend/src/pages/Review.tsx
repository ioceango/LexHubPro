import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Loader2, RotateCw, ShieldAlert, Upload, Wallet, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import SiteHeader from '@/components/SiteHeader';
import { useAuth } from '@/hooks/use-auth';
import { analyzeContract, contractsApi } from '@/lib/data-access';
import { storageApi } from '@/lib/storage-access';
import {
  CONTRACT_BUCKET,
  CONTRACT_TYPES,
  HTTP_MODEL_REQUIRED,
  HTTP_QUOTA_EXHAUSTED,
  PARTY_ROLES,
  getApiErrorInfo,
} from '@/lib/review';
import { toast } from 'sonner';
import { llmApi } from '@/lib/user-llm';

const MAX_FILE_SIZE = 15 * 1024 * 1024;

type Stage = 'idle' | 'uploading' | 'parsing' | 'reviewing' | 'saving';

const STAGE_TEXT: Record<Stage, string> = {
  idle: '',
  uploading: '正在加密上传合同文件…',
  parsing: '正在解析合同全文条款…',
  reviewing: '法律审查模型正在逐条评估风险与合规性…',
  saving: '正在生成并保存审查报告…',
};

const STAGE_PROGRESS: Record<Stage, number> = {
  idle: 0,
  uploading: 18,
  parsing: 42,
  reviewing: 78,
  saving: 94,
};

const Review = () => {
  const navigate = useNavigate();
  const { status, login, logout } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [contractType, setContractType] = useState('');
  const [partyRole, setPartyRole] = useState('');
  const [stage, setStage] = useState<Stage>('idle');
  const [error, setError] = useState('');
  const [errorStatus, setErrorStatus] = useState(0);
  const [canRetry, setCanRetry] = useState(false);
  const [modelReady, setModelReady] = useState<boolean | null>(null);
  const [activeModelLabel, setActiveModelLabel] = useState('');

  useEffect(() => {
    if (status !== 'authenticated') {
      setModelReady(null);
      return;
    }
    llmApi
      .active()
      .then((active) => {
        setModelReady(Boolean(active.configured));
        setActiveModelLabel(active.display_name || active.model_id || '');
      })
      .catch(() => setModelReady(false));
  }, [status]);

  const busy = stage !== 'idle';
  const quotaExhausted = errorStatus === HTTP_QUOTA_EXHAUSTED;

  const clearError = () => {
    setError('');
    setErrorStatus(0);
    setCanRetry(false);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (selected.type !== 'application/pdf' && !selected.name.toLowerCase().endsWith('.pdf')) {
      setError('目前仅支持 PDF 格式的合同文件，请转换后再上传。');
      return;
    }
    if (selected.size > MAX_FILE_SIZE) {
      setError('文件超过 15MB，请压缩或拆分后再上传。');
      return;
    }
    clearError();
    setFile(selected);
    if (!title) {
      setTitle(selected.name.replace(/\.pdf$/i, ''));
    }
  };

  const resetFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async () => {
    if (status !== 'authenticated') {
      login();
      return;
    }
    if (!modelReady) {
      setError('请先配置并启用一个审查模型。');
      toast.error('请先配置并启用一个审查模型。');
      return;
    }
    if (!file) {
      setError('请先选择需要审查的合同 PDF 文件。');
      return;
    }

    const contractTitle = title.trim() || file.name.replace(/\.pdf$/i, '');
    clearError();
    let contractId: number | null = null;

    try {
      // 1. 上传原文件到私有对象存储
      setStage('uploading');
      const uploadResult = await storageApi.upload(file);

      // 2. 创建合同记录
      const contractRecord = await contractsApi.create({
        title: contractTitle,
        file_name: file.name,
        bucket_name: uploadResult.bucket_name || CONTRACT_BUCKET,
        object_key: uploadResult.object_key,
        file_size: file.size,
        contract_type: contractType,
        party_role: partyRole,
        status: 'pending',
      });
      contractId = contractRecord.id as number;

      setStage('parsing');
      setStage('reviewing');
      const result = await analyzeContract({
        contract_id: contractId,
        contract_type: contractType,
        party_role: partyRole,
      });

      setStage('saving');
      toast.success('审查完成，已生成审查报告');
      navigate(`/report/${result.report_id}`);
    } catch (e) {
      const { detail, status, retryable } = getApiErrorInfo(e);
      setError(detail);
      setErrorStatus(status);
      setCanRetry(retryable);
      toast.error(detail);
      if (status === HTTP_MODEL_REQUIRED) {
        setModelReady(false);
        navigate('/settings/models');
      }
      if (contractId) {
        try {
          await contractsApi.updateStatus(contractId, 'failed', {
            error_message: detail.slice(0, 480),
          });
        } catch {
          // 状态回写失败不影响主流程提示
        }
      }
    } finally {
      setStage('idle');
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3">
          <span className="text-xs tracking-wider text-primary">合同审查</span>
          <h1 className="text-3xl">上传合同，生成审查报告</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">
            支持 15MB、80 页以内的文字版 PDF。合同文件存放在仅你可见的私有空间。
          </p>
        </div>

        {status === 'authenticated' && modelReady === false && (
          <Alert className="mt-8 border-primary/30 bg-primary/[0.07]">
            <ShieldAlert className="h-4 w-4 text-primary" />
            <AlertTitle>请先配置审查模型</AlertTitle>
            <AlertDescription className="mt-2">
              当前没有启用的模型，无法进行合同审查。请先填写 DeepSeek 或 OpenRouter 的 API Key 并启用一个模型。
              <div className="mt-4">
                <Button size="sm" onClick={() => navigate('/settings/models')}>
                  去配置模型
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}
        {status === 'authenticated' && modelReady && activeModelLabel ? (
          <p className="mt-6 text-xs text-muted-foreground">当前审查模型：{activeModelLabel}</p>
        ) : null}

        {status === 'anonymous' && (
          <Alert className="mt-8 border-primary/30 bg-primary/[0.07]">
            <ShieldAlert className="h-4 w-4 text-primary" />
            <AlertTitle>需要登录后才能上传合同</AlertTitle>
            <AlertDescription className="mt-2">
              审查记录与合同文件按账号隔离存储，请先登录或注册。
              <div className="mt-4">
                <Button size="sm" onClick={login}>
                  登录 / 注册
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}

        <div className="mt-8 space-y-6 rounded-lg border border-border/70 bg-card p-6 sm:p-8">
          <div className="space-y-2">
            <Label>合同文件</Label>
            {file ? (
              <div className="flex items-center gap-3 rounded-md border border-primary/30 bg-primary/[0.06] px-4 py-3">
                <FileText className="h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm">{file.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={resetFile}
                  disabled={busy}
                  aria-label="移除文件"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
                className="flex w-full flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-background/50 px-6 py-12 transition-colors duration-200 hover:border-primary/50 disabled:pointer-events-none disabled:opacity-50"
              >
                <Upload className="h-6 w-6 text-primary" />
                <span className="text-sm">点击选择合同 PDF 文件</span>
                <span className="text-xs text-muted-foreground">仅支持 PDF，最大 15MB</span>
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="contract-title">合同名称</Label>
            <Input
              id="contract-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：与某供应商的年度采购框架合同"
              disabled={busy}
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>合同类型</Label>
              <Select value={contractType} onValueChange={setContractType} disabled={busy}>
                <SelectTrigger>
                  <SelectValue placeholder="选择合同类型（可留空由 AI 识别）" />
                </SelectTrigger>
                <SelectContent>
                  {CONTRACT_TYPES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>你的立场</Label>
              <Select value={partyRole} onValueChange={setPartyRole} disabled={busy}>
                <SelectTrigger>
                  <SelectValue placeholder="选择你在合同中的身份" />
                </SelectTrigger>
                <SelectContent>
                  {PARTY_ROLES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              {quotaExhausted ? <Wallet className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
              <AlertTitle>{quotaExhausted ? 'AI 服务额度已用尽' : '审查未完成'}</AlertTitle>
              <AlertDescription className="mt-2 space-y-3">
                <p className="leading-relaxed">{error}</p>
                {quotaExhausted ? (
                  <p className="text-xs opacity-80">
                    这是服务额度问题，重复重试不会成功。请在为 AI 服务补充额度后重新提交审查。
                  </p>
                ) : (
                  canRetry && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="!bg-transparent hover:!bg-transparent"
                      onClick={handleSubmit}
                      disabled={busy}
                    >
                      <RotateCw className="mr-2 h-3.5 w-3.5" />
                      重新审查
                    </Button>
                  )
                )}
              </AlertDescription>
            </Alert>
          )}

          {busy && (
            <div className="space-y-3 rounded-md border border-border/70 bg-background/60 p-4">
              <div className="flex items-center gap-2 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                {STAGE_TEXT[stage]}
              </div>
              <Progress value={STAGE_PROGRESS[stage]} />
              <p className="text-xs text-muted-foreground">
                完整审查通常需要 1-3 分钟，请勿关闭本页面。
              </p>
            </div>
          )}

          <Button
            size="lg"
            className="w-full"
            onClick={handleSubmit}
            disabled={busy || status === 'loading' || (status === 'authenticated' && modelReady === false)}
          >
            {busy ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                审查进行中…
              </>
            ) : status === 'anonymous' ? (
              '登录后开始审查'
            ) : modelReady === false ? (
              '请先配置审查模型'
            ) : (
              '开始 AI 审查'
            )}
          </Button>
        </div>
      </main>
    </div>
  );
};

export default Review;
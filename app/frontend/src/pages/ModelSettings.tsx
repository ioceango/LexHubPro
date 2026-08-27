import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import SiteHeader from '@/components/SiteHeader';
import LlmProviderCard from '@/components/LlmProviderCard';
import { useAuth } from '@/hooks/use-auth';
import { LocalHttpError } from '@/lib/http';
import { llmApi, type LlmModelView, type LlmProviderView } from '@/lib/user-llm';

const ModelSettings = () => {
  const navigate = useNavigate();
  const { status, login, logout } = useAuth();
  const [providers, setProviders] = useState<LlmProviderView[]>([]);
  const [models, setModels] = useState<LlmModelView[]>([]);
  const [error, setError] = useState('');

  const reload = async () => {
    const [nextProviders, nextModels] = await Promise.all([llmApi.providers(), llmApi.models()]);
    setProviders(nextProviders);
    setModels(nextModels);
  };

  useEffect(() => {
    if (status !== 'authenticated') return;
    reload().catch((err) => {
      setError(err instanceof LocalHttpError ? err.detail : '加载配置失败');
    });
  }, [status]);

  if (status !== 'authenticated') {
    return (
      <div className="min-h-screen bg-background">
        <SiteHeader status={status} onLogin={login} onLogout={logout} />
        <main className="mx-auto max-w-3xl px-4 py-10">
          <p className="text-sm text-muted-foreground">请先登录后再配置审查模型。</p>
          <Button className="mt-4" onClick={() => navigate('/login')}>
            去登录
          </Button>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="text-2xl">模型配置</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          填写 DeepSeek 或 OpenRouter 的 API Key，拉取模型后只能启用其中一个用于合同审查。
        </p>
        <p className="mt-2 text-xs text-muted-foreground">
          更换系统登录密钥后，已保存的 API Key 将无法解密，请重新填写。
        </p>
        {error ? <p className="mt-4 text-sm text-destructive">{error}</p> : null}
        <div className="mt-8 space-y-6">
          {providers.map((item) => (
            <LlmProviderCard
              key={item.provider}
              provider={item}
              models={models.filter((row) => row.provider === item.provider)}
              onChanged={reload}
            />
          ))}
        </div>
      </main>
    </div>
  );
};

export default ModelSettings;

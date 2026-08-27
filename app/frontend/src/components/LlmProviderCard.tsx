import { FormEvent, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import PasswordInput from '@/components/PasswordInput';
import { LocalHttpError } from '@/lib/http';
import {
  llmApi,
  type LlmCatalogItem,
  type LlmModelView,
  type LlmProviderView,
} from '@/lib/user-llm';

const CATALOG_LIMIT = 200;

const LlmProviderCard = ({
  provider,
  models,
  onChanged,
}: {
  provider: LlmProviderView;
  models: LlmModelView[];
  onChanged: () => Promise<void>;
}) => {
  const [apiKey, setApiKey] = useState('');
  const [catalog, setCatalog] = useState<LlmCatalogItem[]>([]);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);

  const visibleCatalog = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const matched = keyword
      ? catalog.filter(
          (item) =>
            item.id.toLowerCase().includes(keyword) || item.name.toLowerCase().includes(keyword),
        )
      : catalog;
    return matched.slice(0, CATALOG_LIMIT);
  }, [catalog, query]);

  const run = async (task: () => Promise<void>) => {
    setBusy(true);
    try {
      await task();
      await onChanged();
    } catch (err) {
      toast.error(err instanceof LocalHttpError ? err.detail : '操作失败');
    } finally {
      setBusy(false);
    }
  };

  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      const result = await llmApi.saveKey(provider.provider, apiKey);
      setApiKey('');
      toast.success(`已保存 ${provider.name} Key（****${result.key_suffix}）`);
    });
  };

  return (
    <section className="rounded-lg border border-border/70 bg-card p-6">
      <h2 className="text-lg">{provider.name}</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        {provider.configured ? `已保存 · ****${provider.key_suffix}` : '尚未保存 API Key'}
      </p>
      <form className="mt-4 space-y-3" onSubmit={handleSave}>
        <div className="space-y-2">
          <Label htmlFor={`key-${provider.provider}`}>API Key</Label>
          <PasswordInput
            id={`key-${provider.provider}`}
            autoComplete="off"
            value={apiKey}
            onChange={setApiKey}
            required={false}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" size="sm" disabled={busy || !apiKey.trim()}>
            保存 Key
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="!bg-transparent hover:!bg-transparent"
            disabled={busy || !provider.configured}
            onClick={() =>
              void run(async () => {
                const result = await llmApi.refreshModels(provider.provider);
                setCatalog(result.items);
                setQuery('');
                toast.success(`已拉取 ${result.items.length} 个模型`);
              })
            }
          >
            拉取模型
          </Button>
          {provider.configured ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="!bg-transparent hover:!bg-transparent"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await llmApi.deleteKey(provider.provider);
                  setCatalog([]);
                  setQuery('');
                  toast.success(`已删除 ${provider.name} Key`);
                })
              }
            >
              删除 Key
            </Button>
          ) : null}
        </div>
      </form>
      {catalog.length ? (
        <div className="mt-4 space-y-2">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索模型 id 或名称"
            aria-label={`${provider.name} 模型搜索`}
          />
          <p className="text-xs text-muted-foreground">
            共 {catalog.length} 个
            {visibleCatalog.length < catalog.length ? `，展示前 ${visibleCatalog.length} 个` : ''}
          </p>
          <div className="max-h-48 space-y-2 overflow-auto text-sm">
            {visibleCatalog.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-2">
                <span className="truncate">{item.name}</span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="shrink-0 !bg-transparent hover:!bg-transparent"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await llmApi.addModel({
                        provider: provider.provider,
                        model_id: item.id,
                        display_name: item.name,
                      });
                      toast.success('已加入我的模型');
                    })
                  }
                >
                  加入
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {models.length ? (
        <div className="mt-4 space-y-2">
          <p className="text-sm">我的模型（只能启用一个）</p>
          {models.map((row) => (
            <div key={row.id} className="flex items-center justify-between gap-2 text-sm">
              <label className="flex min-w-0 items-center gap-2">
                <input
                  type="radio"
                  name="enabled-llm"
                  checked={row.enabled}
                  disabled={busy}
                  onChange={() =>
                    void run(async () => {
                      await llmApi.setEnabled(row.id, true);
                    })
                  }
                />
                <span className="truncate">{row.display_name}</span>
              </label>
              <div className="flex shrink-0 gap-1">
                {row.enabled ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="!bg-transparent hover:!bg-transparent"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await llmApi.setEnabled(row.id, false);
                      })
                    }
                  >
                    停用
                  </Button>
                ) : null}
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      if (row.enabled) await llmApi.setEnabled(row.id, false);
                      await llmApi.removeModel(row.id);
                    })
                  }
                >
                  移除
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
};

export default LlmProviderCard;

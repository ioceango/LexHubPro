import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  FileSearch,
  FileWarning,
  Gavel,
  ListChecks,
  Lock,
  ScrollText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import SiteHeader from '@/components/SiteHeader';
import { useAuth } from '@/hooks/use-auth';
import { HERO_URL, REPORT_FEATURE_URL, RISK_FEATURE_URL } from '@/lib/assets';

const CAPABILITIES = [
  {
    icon: FileWarning,
    title: '风险条款识别',
    desc: '逐条比对合同义务分配，标注高、中、低三级风险，给出原文引用与可直接替换的修改表述。',
  },
  {
    icon: ListChecks,
    title: '缺失条款提示',
    desc: '按合同类型比对标准条款清单，提示不可抗力、争议解决、保密等缺失项并附示范文本。',
  },
  {
    icon: Gavel,
    title: '合规性检查',
    desc: '结合民法典、劳动合同法等现行法律，检查违约金上限、格式条款、个人信息处理等合规要点。',
  },
  {
    icon: ScrollText,
    title: '结构化审查报告',
    desc: '输出整体安全评分、关键商务条款摘要与整体谈判建议，支持一键复制或导出文本。',
  },
];

const STEPS = [
  { step: '01', title: '上传合同 PDF', desc: '选择合同类型与你所处的立场（甲方/乙方），文件加密存储在私有空间。' },
  { step: '02', title: 'AI 解析与审查', desc: '先做全文条款解析，再由法律审查模型逐条评估风险与合规性。' },
  { step: '03', title: '查阅审查报告', desc: '按风险等级排序查看条款问题，随时回看历史报告并导出留档。' },
];

const Index = () => {
  const navigate = useNavigate();
  const { status, login, logout } = useAuth();

  const handlePrimaryCta = () => {
    if (status === 'authenticated') {
      navigate('/review');
      return;
    }
    if (status === 'anonymous') {
      login();
      return;
    }
    navigate('/review');
  };

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border/60">
        <div className="absolute inset-0 paper-grid opacity-40" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-b from-background/40 via-background/85 to-background" aria-hidden />
        <div className="relative mx-auto grid max-w-screen-xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-5 lg:gap-8 lg:px-8 lg:py-28">
          <div className="lg:col-span-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs tracking-wide text-primary">
              <Lock className="h-3.5 w-3.5" />
              私有存储 · 数据仅本人可见
            </div>
            <h1 className="mt-6 max-w-2xl text-4xl leading-[1.15] sm:text-5xl lg:text-6xl">
              把每一份合同
              <br />
              交给<span className="text-primary">不会疲倦的法务</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground">
              上传合同 PDF，AI 在数分钟内完成全文条款解析、风险分级、缺失条款提示与合规性检查，
              输出可直接用于谈判的结构化审查报告。
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={handlePrimaryCta} disabled={status === 'loading'}>
                {status === 'anonymous' ? '登录后上传合同' : '上传合同开始审查'}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" className="!bg-transparent hover:!bg-transparent" onClick={() => navigate('/history')}>
                查看审查历史
              </Button>
            </div>
            <div className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-border/60 pt-8">
              <div>
                <div className="font-serif text-2xl text-primary">3 类</div>
                <div className="mt-1 text-xs text-muted-foreground">风险分级标注</div>
              </div>
              <div>
                <div className="font-serif text-2xl text-primary">9 类</div>
                <div className="mt-1 text-xs text-muted-foreground">常见合同覆盖</div>
              </div>
              <div>
                <div className="font-serif text-2xl text-primary">100 分</div>
                <div className="mt-1 text-xs text-muted-foreground">整体安全量化</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 lg:pt-6">
            <div className="overflow-hidden rounded-lg border border-border/70 amber-glow">
              <img
                src={HERO_URL}
                alt="法务合同智能审查场景，合同文档被逐条扫描分析"
                width={1280}
                height={854}
                fetchPriority="high"
                decoding="async"
                className="aspect-[4/3] w-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="mx-auto max-w-screen-xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 md:max-w-2xl">
          <span className="text-xs tracking-wider text-primary">核心能力</span>
          <h2>审查一份合同需要看的四件事，全部自动完成</h2>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          {CAPABILITIES.map(({ icon: Icon, title, desc }) => (
            <div
              key={title}
              className="group rounded-lg border border-border/70 bg-card p-7 transition-colors duration-300 hover:border-primary/40"
            >
              <Icon className="h-6 w-6 text-primary" />
              <h3 className="mt-5 text-lg">{title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="overflow-hidden rounded-lg border border-border/70">
            <img
              src={RISK_FEATURE_URL}
              alt="合同条款按风险等级高亮标注的特写"
              width={960}
              height={640}
              loading="lazy"
              decoding="async"
              className="aspect-[16/10] w-full object-cover"
            />
            <div className="border-t border-border/70 bg-card p-6">
              <h3 className="text-base">条款级风险定位</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                每一条风险都附带合同原文片段、不利之处说明与潜在后果，便于直接对照修改。
              </p>
            </div>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/70">
            <img
              src={REPORT_FEATURE_URL}
              alt="合同合规审查报告的评分仪表与指标面板"
              width={960}
              height={640}
              loading="lazy"
              decoding="async"
              className="aspect-[16/10] w-full object-cover"
            />
            <div className="border-t border-border/70 bg-card p-6">
              <h3 className="text-base">可量化的审查结论</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                整体安全评分与风险数量统计，让不同版本的合同修改效果一目了然。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Steps */}
      <section className="border-y border-border/60 bg-card/40">
        <div className="mx-auto max-w-screen-xl px-4 py-20 sm:px-6 lg:px-8">
          <span className="text-xs tracking-wider text-primary">使用流程</span>
          <h2 className="mt-3">三步完成一次专业审查</h2>
          <div className="mt-12 grid gap-10 md:grid-cols-3">
            {STEPS.map((item) => (
              <div key={item.step} className="border-t-2 border-primary/40 pt-6">
                <div className="font-serif text-3xl text-primary/70">{item.step}</div>
                <h3 className="mt-4 text-lg">{item.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-screen-xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="flex flex-col items-start gap-6 rounded-lg border border-primary/25 bg-primary/[0.06] p-10 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <FileSearch className="mt-1 h-8 w-8 shrink-0 text-primary" />
            <div>
              <h3 className="text-xl">现在上传一份合同试试</h3>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                支持 15MB、80 页以内的文字版 PDF 合同。审查记录仅你本人可见，可随时删除。
              </p>
            </div>
          </div>
          <Button size="lg" onClick={handlePrimaryCta} disabled={status === 'loading'}>
            开始审查
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </section>

      <footer className="border-t border-border/60 py-8">
        <div className="mx-auto max-w-screen-xl px-4 text-xs text-muted-foreground sm:px-6 lg:px-8">
          LexHubPro · AI 生成的审查结论仅供参考，不构成正式法律意见，重大交易请咨询执业律师。
        </div>
      </footer>
    </div>
  );
};

export default Index;
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { LOGO_URL } from '@/lib/assets';

interface AuthCardProps {
  title: string;
  description?: string;
  children: ReactNode;
}

/** 自建认证页共用外壳，避免每个页面复制品牌与卡片样式。 */
const AuthCard = ({ title, description, children }: AuthCardProps) => {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="absolute inset-0 paper-grid opacity-30" aria-hidden />
      <div className="relative w-full max-w-md rounded-lg border border-border/70 bg-card p-8">
        <Link to="/" className="mb-6 flex items-center gap-2.5">
          <img
            src={LOGO_URL}
            alt="LexHubPro 标识"
            width={32}
            height={32}
            decoding="async"
            className="h-8 w-8 object-contain"
          />
          <span className="font-serif text-lg font-semibold tracking-tight">
            LexHub<span className="text-primary">Pro</span>
          </span>
        </Link>
        <h1 className="text-2xl">{title}</h1>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
};

export default AuthCard;

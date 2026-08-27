import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Menu, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { AuthStatus } from '@/hooks/use-auth';
import { LOGO_URL } from '@/lib/assets';

const NAV_ITEMS = [
  { label: '首页', to: '/' },
  { label: '上传审查', to: '/review' },
  { label: '审查历史', to: '/history' },
  { label: '模型配置', to: '/settings/models' },
];

interface SiteHeaderProps {
  status: AuthStatus;
  onLogin: () => void;
  onLogout: () => void;
}

const SiteHeader = ({ status, onLogin, onLogout }: SiteHeaderProps) => {
  const location = useLocation();
  const navigate = useNavigate();

  const renderNavLink = (item: { label: string; to: string }, onNavigate?: () => void) => {
    const active = location.pathname === item.to;
    return (
      <Link
        key={item.to}
        to={item.to}
        onClick={onNavigate}
        className={`text-sm transition-colors duration-200 ${
          active ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
        }`}
      >
        {item.label}
      </Link>
    );
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-screen-xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <img
            src={LOGO_URL}
            alt="LexHubPro 标识"
            width={32}
            height={32}
            fetchPriority="high"
            decoding="async"
            className="h-8 w-8 object-contain"
          />
          <span className="font-serif text-lg font-semibold tracking-tight">
            LexHub<span className="text-primary">Pro</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-7 md:flex">{NAV_ITEMS.map((item) => renderNavLink(item))}</nav>

        <div className="ml-auto flex items-center gap-2">
          {status === 'loading' && <div className="h-8 w-20 animate-pulse rounded bg-muted" />}

          {status === 'anonymous' && (
            <Button size="sm" onClick={onLogin}>
              登录 / 注册
            </Button>
          )}

          {status === 'authenticated' && (
            <>
              <Button
                size="sm"
                className="hidden md:inline-flex"
                onClick={() => navigate('/review')}
              >
                上传合同
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="账户菜单">
                    <UserRound className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-40">
                  <DropdownMenuItem onClick={() => navigate('/profile')}>个人资料</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/settings/models')}>模型配置</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => navigate('/history')}>我的审查记录</DropdownMenuItem>
                  <DropdownMenuItem onClick={onLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden" aria-label="打开菜单">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-64">
              <div className="mt-10 flex flex-col gap-5">
                {NAV_ITEMS.map((item) => renderNavLink(item))}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
};

export default SiteHeader;
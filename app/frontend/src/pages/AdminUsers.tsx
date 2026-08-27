import { useEffect, useState } from 'react';
import SiteHeader from '@/components/SiteHeader';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { localRequest } from '@/lib/http';
import type { AuthProfile } from '@/lib/auth-provider';

interface UserList {
  items: AuthProfile[];
  total: number;
}

const AdminUsers = () => {
  const { status, user, login, logout } = useAuth();
  const [items, setItems] = useState<AuthProfile[]>([]);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const result = await localRequest<UserList>('/api/v1/admin/users?limit=50&offset=0');
      setItems(result.items);
    } catch {
      setError('无法加载用户列表');
    }
  };

  useEffect(() => {
    if (status === 'authenticated' && user?.role === 'admin') {
      void load();
    }
  }, [status, user?.role]);

  const toggleStatus = async (id: number, statusValue: string) => {
    const next = statusValue === 'disabled' ? 'active' : 'disabled';
    await localRequest(`/api/v1/admin/users/${id}/status`, {
      method: 'PATCH',
      data: { status: next },
    });
    await load();
  };

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />
      <main className="mx-auto max-w-3xl px-4 py-10">
        <h1 className="text-2xl">用户管理</h1>
        {user?.role !== 'admin' ? (
          <p className="mt-4 text-sm text-muted-foreground">需要管理员权限。</p>
        ) : (
          <div className="mt-6 space-y-3">
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border border-border/70 bg-card px-4 py-3"
              >
                <div>
                  <p className="text-sm">{item.email}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.role} · {item.status}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="!bg-transparent hover:!bg-transparent"
                  onClick={() => void toggleStatus(item.id, item.status || 'active')}
                >
                  {item.status === 'disabled' ? '启用' : '禁用'}
                </Button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminUsers;

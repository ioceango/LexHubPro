import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import PasswordInput from '@/components/PasswordInput';
import SiteHeader from '@/components/SiteHeader';
import { useAuth } from '@/hooks/use-auth';
import { authApi } from '@/lib/auth-provider';
import { LocalHttpError } from '@/lib/http';


const Profile = () => {
  const navigate = useNavigate();
  const { status, user, login, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setBusy(true);
    try {
      setMessage(await authApi.changePassword(currentPassword, newPassword));
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setError(err instanceof LocalHttpError ? err.detail : '修改失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader status={status} onLogin={login} onLogout={logout} />
      <main className="mx-auto max-w-lg px-4 py-10">
        <h1 className="text-2xl">个人资料</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {user?.email || '未登录'}
          {user?.role === 'admin' ? ' · 管理员' : ''}
        </p>
        {status === 'authenticated' ? (
          <form className="mt-8 space-y-4 rounded-lg border border-border/70 bg-card p-6" onSubmit={handleSubmit}>
            <h2 className="text-lg">修改密码</h2>
            <div className="space-y-2">
              <Label htmlFor="current">当前密码</Label>
              <PasswordInput
                id="current"
                autoComplete="current-password"
                value={currentPassword}
                onChange={setCurrentPassword}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="next">新密码</Label>
              <PasswordInput
                id="next"
                autoComplete="new-password"
                value={newPassword}
                onChange={setNewPassword}
              />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
            <Button type="submit" disabled={busy}>
              {busy ? '提交中…' : '保存'}
            </Button>
          </form>
        ) : null}
        {user?.role === 'admin' ? (
          <Button variant="outline" className="mt-6 !bg-transparent hover:!bg-transparent" onClick={() => navigate('/admin/users')}>
            用户管理
          </Button>
        ) : null}
      </main>
    </div>
  );
};

export default Profile;

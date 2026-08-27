import { FormEvent, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import AuthCard from '@/components/AuthCard';
import PasswordInput from '@/components/PasswordInput';
import { authApi } from '@/lib/auth-provider';
import { LocalHttpError } from '@/lib/http';

const ResetPassword = () => {
  const [params] = useSearchParams();
  const token = useMemo(() => params.get('token') || '', [params]);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      setMessage(await authApi.resetPassword(token, password));
    } catch (err) {
      setError(err instanceof LocalHttpError ? err.detail : '重置失败，请重新获取链接');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="重置密码" description="链接一次性有效。重置成功后请使用新密码登录。">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="password">新密码</Label>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        <Button type="submit" className="w-full" disabled={busy || !token}>
          {busy ? '提交中…' : '确认重置'}
        </Button>
      </form>
      <Link to="/login" className="mt-4 inline-block text-sm text-muted-foreground hover:text-foreground">
        返回登录
      </Link>
    </AuthCard>
  );
};

export default ResetPassword;

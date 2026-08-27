import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import AuthCard from '@/components/AuthCard';
import { authApi } from '@/lib/auth-provider';
import { LocalHttpError } from '@/lib/http';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      setMessage(await authApi.requestPasswordReset(email.trim()));
    } catch (err) {
      setError(err instanceof LocalHttpError ? err.detail : '提交失败，请稍后重试');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="忘记密码" description="如果该邮箱已注册，我们会发送一次性重置链接。">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email">邮箱</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? '提交中…' : '发送重置链接'}
        </Button>
      </form>
      <Link to="/login" className="mt-4 inline-block text-sm text-muted-foreground hover:text-foreground">
        返回登录
      </Link>
    </AuthCard>
  );
};

export default ForgotPassword;

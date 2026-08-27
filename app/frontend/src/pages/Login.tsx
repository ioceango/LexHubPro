import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import AuthCard from '@/components/AuthCard';
import PasswordInput from '@/components/PasswordInput';
import { authApi } from '@/lib/auth-provider';
import { emailFormatHint, isValidEmail, MAX_EMAIL_LENGTH } from '@/lib/email';
import { LocalHttpError } from '@/lib/http';
import { toast } from 'sonner';

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    const trimmed = email.trim();
    if (!isValidEmail(trimmed)) {
      setError(emailFormatHint);
      toast.error(emailFormatHint);
      return;
    }
    setBusy(true);
    try {
      await authApi.signIn(trimmed, password);
      toast.success('登录成功');
      navigate('/review');
    } catch (err) {
      const detail = err instanceof LocalHttpError ? err.detail : '登录失败，请稍后重试';
      setError(detail);
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="登录" description="使用注册邮箱与密码进入 LexHubPro。">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email">邮箱</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            maxLength={MAX_EMAIL_LENGTH}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">密码</Label>
          <PasswordInput id="password" value={password} onChange={setPassword} />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? '登录中…' : '登录'}
        </Button>
      </form>
      <div className="mt-4 flex justify-between text-sm text-muted-foreground">
        <Link to="/register" className="hover:text-foreground">
          注册账号
        </Link>
        <Link to="/forgot-password" className="hover:text-foreground">
          忘记密码
        </Link>
      </div>
    </AuthCard>
  );
};

export default Login;

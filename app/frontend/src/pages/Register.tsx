import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import AuthCard from '@/components/AuthCard';
import PasswordInput from '@/components/PasswordInput';
import { authApi } from '@/lib/auth-provider';
import {
  emailConstraintHint,
  emailFormatHint,
  isSupportedMailbox,
  isValidEmail,
  MAX_EMAIL_LENGTH,
} from '@/lib/email';
import { LocalHttpError } from '@/lib/http';

const Register = () => {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [awaitingCode, setAwaitingCode] = useState(false);

  const handleRegister = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    const trimmed = email.trim();
    if (!isValidEmail(trimmed)) {
      setError(emailFormatHint);
      toast.error(emailFormatHint);
      return;
    }
    if (!isSupportedMailbox(trimmed)) {
      setError(emailConstraintHint);
      toast.error(emailConstraintHint);
      return;
    }
    if (password.length < 10 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      const hint = '密码至少 10 位，需同时包含字母与数字。';
      setError(hint);
      toast.error(hint);
      return;
    }
    setBusy(true);
    try {
      const result = await authApi.signUp(trimmed, password, name.trim() || undefined);
      if (result.verification_required) {
        const failed = (result.message || '').includes('失败');
        if (failed) {
          toast.error(result.message);
          setError(result.message);
          setAwaitingCode(true);
          return;
        }
        const sent = result.message || '验证码已发送，请到邮箱查收。验证通过后才算注册成功。';
        toast.success(sent);
        setMessage(sent);
        setAwaitingCode(true);
        return;
      }
      toast.success('注册成功，请登录');
      navigate('/login');
    } catch (err) {
      const detail = err instanceof LocalHttpError ? err.detail : '注册失败，请稍后重试';
      setError(detail);
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    const trimmedCode = code.trim();
    if (!/^\d{6}$/.test(trimmedCode)) {
      const hint = '请输入 6 位数字验证码';
      setError(hint);
      toast.error(hint);
      return;
    }
    setBusy(true);
    try {
      const result = await authApi.verifyEmail({ email: email.trim(), code: trimmedCode });
      toast.success(result || '注册成功，请登录');
      navigate('/login');
    } catch (err) {
      const detail = err instanceof LocalHttpError ? err.detail : '验证失败，请重新获取验证码';
      setError(detail);
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setBusy(true);
    try {
      const result = await authApi.resendVerification(email.trim());
      toast.success(result);
      setMessage(result);
    } catch (err) {
      const detail = err instanceof LocalHttpError ? err.detail : '发送失败，请稍后重试';
      setError(detail);
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      title={awaitingCode ? '输入验证码' : '注册'}
      description={
        awaitingCode
          ? `验证码已发送到 ${email.trim()}，15 分钟内有效。`
          : '请使用 163 或 Gmail 注册。点击注册后先发验证码，校验通过才会注册成功并进入登录页。'
      }
    >
      {awaitingCode ? (
        <form className="space-y-4" onSubmit={handleVerify}>
          <div className="space-y-2">
            <Label htmlFor="code">邮箱验证码</Label>
            <Input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              required
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? '验证中…' : '完成验证'}
          </Button>
          <Button type="button" variant="outline" className="w-full !bg-transparent hover:!bg-transparent" disabled={busy} onClick={handleResend}>
            重新发送验证码
          </Button>
        </form>
      ) : (
        <form className="space-y-4" onSubmit={handleRegister}>
          <div className="space-y-2">
            <Label htmlFor="name">显示名（可选）</Label>
            <Input id="name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">邮箱</Label>
            <Input
              id="email"
              type="text"
              inputMode="email"
              autoComplete="email"
              required
              maxLength={MAX_EMAIL_LENGTH}
              title={emailConstraintHint}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">{emailConstraintHint}</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              value={password}
              onChange={setPassword}
            />
            <p className="text-xs text-muted-foreground">至少 10 位，需同时包含字母与数字。</p>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {message ? <p className="text-sm text-emerald-600">{message}</p> : null}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? '提交中…' : '注册'}
          </Button>
        </form>
      )}
      <p className="mt-4 text-sm text-muted-foreground">
        已有账号？
        <Link to="/login" className="ml-1 hover:text-foreground">
          去登录
        </Link>
      </p>
    </AuthCard>
  );
};

export default Register;

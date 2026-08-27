import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import AuthCard from '@/components/AuthCard';
import { authApi } from '@/lib/auth-provider';
import { LocalHttpError } from '@/lib/http';

const VerifyEmail = () => {
  const [params] = useSearchParams();
  const [error, setError] = useState('');
  const [message, setMessage] = useState('正在验证邮箱…');

  useEffect(() => {
    const token = params.get('token') || '';
    if (!token) {
      setError('验证链接无效');
      setMessage('');
      return;
    }
    authApi
      .verifyEmail({ token })
      .then(setMessage)
      .catch((err) => {
        setMessage('');
        setError(err instanceof LocalHttpError ? err.detail : '验证失败，请重新获取链接');
      });
  }, [params]);

  return (
    <AuthCard title="邮箱验证">
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      <Button asChild className="mt-6 w-full">
        <Link to="/login">去登录</Link>
      </Button>
    </AuthCard>
  );
};

export default VerifyEmail;

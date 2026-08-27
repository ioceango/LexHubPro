import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, beginLogin, type AuthProfile } from '@/lib/auth-provider';

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous';
export type AuthUser = AuthProfile;

/**
 * 统一的认证状态管理：loading / authenticated / anonymous 三态。
 * 仅在挂载时检查一次；认证结果返回前禁止判定未登录或触发跳转。
 */
export const useAuth = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let active = true;
    authApi
      .me()
      .then((profile) => {
        if (!active) return;
        if (profile) {
          setUser(profile);
          setStatus('authenticated');
        } else {
          setStatus('anonymous');
        }
      })
      .catch(() => {
        if (active) setStatus('anonymous');
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(() => {
    beginLogin(() => navigate('/login'));
  }, [navigate]);

  const logout = useCallback(async () => {
    try {
      await authApi.signOut();
    } finally {
      setUser(null);
      setStatus('anonymous');
      window.location.href = '/';
    }
  }, []);

  return { status, user, login, logout };
};
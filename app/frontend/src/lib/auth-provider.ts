/**
 * 自建 JWT 认证封装。页面只依赖本文件。
 */

import { getAccessToken, localRequest, setAccessToken } from '@/lib/http';

const AUTH_PREFIX = '/api/v1/auth';

export interface AuthProfile {
  id: number;
  email?: string;
  name?: string;
  role?: string;
  status?: string;
  tenant_id?: string;
}

interface TokenPair {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  user: AuthProfile;
}

interface MessageResult {
  success?: boolean;
  message: string;
}

const authPath = (suffix: string) => `${AUTH_PREFIX}${suffix}`;

export const authApi = {
  async me(): Promise<AuthProfile | null> {
    try {
      return await localRequest<AuthProfile>(authPath('/me'));
    } catch (error) {
      if ((error as { status?: number }).status === 401) return null;
      throw error;
    }
  },
  async signIn(email: string, password: string): Promise<AuthProfile> {
    const pair = await localRequest<TokenPair>(authPath('/login'), {
      method: 'POST',
      data: { email, password },
    });
    setAccessToken(pair.access_token);
    return pair.user;
  },
  async signUp(
    email: string,
    password: string,
    name?: string,
  ): Promise<{ message: string; verification_required: boolean }> {
    return localRequest<{ message: string; verification_required: boolean }>(authPath('/register'), {
      method: 'POST',
      data: { email, password, name },
    });
  },
  async signOut(): Promise<void> {
    try {
      await localRequest(authPath('/logout'), { method: 'POST', data: {} });
    } finally {
      setAccessToken(null);
    }
  },
  getAccessToken,
  async requestPasswordReset(email: string): Promise<string> {
    const result = await localRequest<MessageResult>(authPath('/password-reset/request'), {
      method: 'POST',
      data: { email },
    });
    return result.message;
  },
  async resetPassword(token: string, newPassword: string): Promise<string> {
    const result = await localRequest<MessageResult>(authPath('/password-reset/confirm'), {
      method: 'POST',
      data: { token, new_password: newPassword },
    });
    return result.message;
  },
  async verifyEmail(payload: { token?: string; email?: string; code?: string }): Promise<string> {
    const result = await localRequest<MessageResult>(authPath('/verify-email'), {
      method: 'POST',
      data: payload,
    });
    return result.message;
  },
  async resendVerification(email: string): Promise<string> {
    const result = await localRequest<MessageResult>(authPath('/verify-email/resend'), {
      method: 'POST',
      data: { email },
    });
    return result.message;
  },
  async changePassword(currentPassword: string, newPassword: string): Promise<string> {
    const result = await localRequest<MessageResult>(authPath('/password/change'), {
      method: 'POST',
      data: { current_password: currentPassword, new_password: newPassword },
    });
    return result.message;
  },
};

export const beginLogin = (goToLogin: () => void): void => {
  goToLogin();
};

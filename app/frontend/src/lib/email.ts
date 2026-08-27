/** 注册/登录共用的邮箱格式约束。注册仅允许 163 与 Gmail。 */

const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

export const MAX_EMAIL_LENGTH = 320;

export const SUPPORTED_MAILBOX_DOMAINS = [
  '163.com',
  '126.com',
  'yeah.net',
  'gmail.com',
  'googlemail.com',
] as const;

export const emailFormatHint = '请输入有效邮箱，例如 name@163.com';
export const emailConstraintHint = '请使用 163 或 Gmail 邮箱，例如 name@163.com 或 name@gmail.com';

const mailboxDomain = (value: string): string => {
  const parts = value.trim().toLowerCase().split('@');
  return parts.length === 2 ? parts[1] : '';
};

export const isValidEmail = (value: string): boolean => {
  const email = value.trim();
  if (email.length < 6 || email.length > MAX_EMAIL_LENGTH) return false;
  if (email.includes('..') || email.startsWith('.') || email.endsWith('.')) return false;
  return EMAIL_PATTERN.test(email);
};

export const isSupportedMailbox = (value: string): boolean => {
  if (!isValidEmail(value)) return false;
  return (SUPPORTED_MAILBOX_DOMAINS as readonly string[]).includes(mailboxDomain(value));
};

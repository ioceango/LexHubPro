import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/bug-fix/BUG-004-register-email-ux/test-report');
const MAILPIT = process.env.E2E_MAILPIT_URL || 'http://127.0.0.1:8025';
const PASSWORD = 'letters12345';

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

const latestCode = async (email: string): Promise<string> => {
  const list = await fetch(`${MAILPIT}/api/v1/messages`).then((res) => res.json());
  const messages = list.messages || [];
  const hit = messages.find((item: { To?: { Address?: string }[] }) =>
    JSON.stringify(item.To || []).includes(email),
  );
  expect(hit, `mailpit missing message for ${email}`).toBeTruthy();
  const id = hit.ID as string;
  const full = await fetch(`${MAILPIT}/api/v1/message/${id}`).then((res) => res.json());
  const match = String(full.Text || '').match(/(\d{6})/);
  expect(match, 'mail body missing 6-digit code').toBeTruthy();
  return match![1];
};

test.describe.configure({ mode: 'serial' });

test('BUG-004 register sends code then succeeds after verify', async ({ page }) => {
  const email = `bug004.${Date.now()}@163.com`;

  await page.goto('/register');
  await expect(page.getByRole('heading', { name: '注册' })).toBeVisible();
  await shot(page, 'S01', 'register-page');

  await page.locator('#email').fill('not-an-email');
  await page.locator('#password').fill(PASSWORD);
  await page.getByRole('button', { name: '注册' }).click();
  await expect(page.locator('p.text-destructive')).toContainText('请输入有效邮箱');
  await shot(page, 'S02', 'invalid-email');

  await page.locator('#email').fill('user@qq.com');
  await page.getByRole('button', { name: '注册' }).click();
  await expect(page.locator('p.text-destructive')).toContainText('请使用 163 或 Gmail');
  await shot(page, 'S03', 'unsupported-mailbox');

  await page.locator('#email').fill(email);
  await page.locator('#password').fill(PASSWORD);
  await page.getByRole('button', { name: '显示密码' }).click();
  await expect(page.locator('#password')).toHaveAttribute('type', 'text');
  await shot(page, 'S04', 'password-visible');
  await page.getByRole('button', { name: '隐藏密码' }).click();

  await page.getByRole('button', { name: '注册' }).click();
  await expect(page.getByRole('heading', { name: '输入验证码' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '登录' })).toHaveCount(0);
  await shot(page, 'S05', 'code-step-after-register');

  await page.locator('#code').fill('000000');
  await page.getByRole('button', { name: '完成验证' }).click();
  await expect(page.locator('p.text-destructive')).toContainText('验证码无效或已过期');
  await shot(page, 'S06', 'wrong-code');

  const code = await latestCode(email);
  await page.locator('#code').fill(code);
  await page.getByRole('button', { name: '完成验证' }).click();
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await shot(page, 'S07', 'register-success-login');
});

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/bug-fix/BUG-005-smtp-verify-code-not-sent/test-report');
const PASSWORD = 'letters12345';

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('BUG-005 register after smtp config stays on code step', async ({ page }) => {
  const email = `bug005.${Date.now()}@163.com`;
  await page.goto('/register');
  await expect(page.getByRole('heading', { name: '注册' })).toBeVisible();
  await shot(page, 'S01', 'register-page');

  await page.locator('#email').fill(email);
  await page.locator('#password').fill(PASSWORD);
  await page.getByRole('button', { name: '注册' }).click();
  await expect(page.getByRole('heading', { name: '输入验证码' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '登录' })).toHaveCount(0);
  await shot(page, 'S02', 'code-step-after-send');

  await page.getByRole('button', { name: '重新发送验证码' }).click();
  await expect(page.getByRole('heading', { name: '输入验证码' })).toBeVisible();
  await shot(page, 'S03', 'resend-still-code-step');
});

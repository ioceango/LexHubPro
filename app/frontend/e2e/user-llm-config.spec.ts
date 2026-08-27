import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/features/FEAT-008-user-llm-config/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

const fulfillJson = (page: Page, url: string, body: unknown) =>
  page.route(url, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });

test('FEAT-008 review blocked until model configured', async ({ page }) => {
  await page.goto('/review');
  await expect(page.getByRole('heading', { name: '上传合同，生成审查报告' })).toBeVisible();
  await shot(page, 'S01', 'review-requires-login-or-model');

  await page.goto('/settings/models');
  await expect(page.getByText('请先登录后再配置审查模型')).toBeVisible();
  await shot(page, 'S02', 'model-settings-login-required');

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await shot(page, 'S03', 'login-before-model-config');
});

test('FEAT-008 logged-in user without enabled model is gated', async ({ page }) => {
  await fulfillJson(page, '**/api/v1/auth/me', {
    id: 1,
    email: 'tester@gmail.com',
    name: 'Tester',
    role: 'user',
    status: 'active',
    tenant_id: 'default',
  });
  await fulfillJson(page, '**/api/v1/llm/active', { configured: false });
  await fulfillJson(page, '**/api/v1/llm/providers', [
    { provider: 'deepseek', name: 'DeepSeek', configured: false, key_suffix: '' },
    { provider: 'openrouter', name: 'OpenRouter', configured: false, key_suffix: '' },
  ]);
  await fulfillJson(page, '**/api/v1/llm/models', []);

  await page.goto('/review');
  await expect(page.getByRole('heading', { name: '请先配置审查模型' })).toBeVisible();
  await expect(page.getByRole('button', { name: '去配置模型' })).toBeVisible();
  await shot(page, 'S04', 'review-configure-model-banner');

  await page.goto('/settings/models');
  await expect(page.getByRole('heading', { name: '模型配置' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'DeepSeek' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'OpenRouter' })).toBeVisible();
  await shot(page, 'S05', 'model-settings-two-providers');
});

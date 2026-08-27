import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/bug-fix/BUG-006-review-tx-already-begun/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('BUG-006 review entry remains usable after model config', async ({ page }) => {
  await page.goto('/review');
  await expect(page.getByRole('heading', { name: '上传合同，生成审查报告' })).toBeVisible();
  await shot(page, 'S01', 'review-page');

  await page.goto('/settings/models');
  await expect(page.getByText('请先登录后再配置审查模型')).toBeVisible();
  await shot(page, 'S02', 'model-settings-login-required');
});

test('BUG-006 logged-in review with enabled model shows start button', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        email: 'tester@gmail.com',
        name: 'Tester',
        role: 'user',
        status: 'active',
        tenant_id: 'default',
      }),
    });
  });
  await page.route('**/api/v1/llm/active', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        configured: true,
        provider: 'deepseek',
        model_id: 'deepseek-chat',
        display_name: 'DeepSeek Chat',
      }),
    });
  });

  await page.goto('/review');
  await expect(page.getByText('当前审查模型：DeepSeek Chat')).toBeVisible();
  await expect(page.getByRole('button', { name: '开始 AI 审查' })).toBeVisible();
  await shot(page, 'S03', 'review-ready-with-enabled-model');
});

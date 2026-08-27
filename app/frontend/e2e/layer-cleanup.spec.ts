import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/features/FEAT-009-backend-layer-cleanup-ddl/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('FEAT-009 app still boots and scaffold routes are gone', async ({ page, request }) => {
  await page.goto('/');
  await expect(page.getByText('LexHubPro').first()).toBeVisible();
  await shot(page, 'S01', 'home');

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await shot(page, 'S02', 'login-jwt-only');

  const aihub = await request.post('/api/v1/aihub/gentxt', { data: {} });
  expect(aihub.status()).toBe(404);
  const settings = await request.get('/api/v1/admin/settings');
  expect(settings.status()).toBe(404);

  await page.goto('/logout-callback');
  await expect(page.getByRole('heading', { name: '已安全退出登录' })).toHaveCount(0);
  await shot(page, 'S03', 'oidc-callback-removed');
});

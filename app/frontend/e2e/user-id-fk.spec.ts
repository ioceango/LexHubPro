import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/bug-fix/BUG-007-contract-report-user-id-fk/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('BUG-007 contract and history entry still load after user_id fk unify', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('img', { name: 'LexHubPro 标识' }).first()).toBeVisible();
  await shot(page, 'S01', 'home-entry');

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await shot(page, 'S02', 'login-entry');

  await page.goto('/review');
  await expect(page.getByRole('heading', { name: '上传合同，生成审查报告' })).toBeVisible();
  await shot(page, 'S03', 'review-entry');

  await page.goto('/history');
  await expect(page.getByRole('heading', { name: '我的合同与报告' })).toBeVisible();
  await shot(page, 'S04', 'history-entry');
});

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/features/FEAT-013-code-review-skill/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('FEAT-013 product entry still loads after code-review skill', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('img', { name: 'LexHubPro 标识' }).first()).toBeVisible();
  await shot(page, 'S01', 'home-entry');

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await shot(page, 'S02', 'login-entry');
});

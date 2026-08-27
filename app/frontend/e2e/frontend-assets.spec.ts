import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = process.env.E2E_SCREENSHOT_DIR
  ? path.resolve(process.env.E2E_SCREENSHOT_DIR)
  : path.resolve(here, '../../../docs/features/FEAT-010-frontend-assets-mvc/test-report');

const shot = async (page: Page, id: string, title: string) => {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const file = path.join(SHOT_DIR, `${id}-${title}.png`);
  await page.screenshot({ path: file, fullPage: true });
  expect(fs.existsSync(file), `missing screenshot ${id}`).toBeTruthy();
};

test('FEAT-010 local brand images load on home and login', async ({ page }) => {
  const remoteHits: string[] = [];
  page.on('request', (req) => {
    const url = req.url();
    if (url.includes('metadl.com') || url.includes('mgx-backend-cdn')) {
      remoteHits.push(url);
    }
  });

  await page.goto('/');
  await expect(page.getByRole('img', { name: 'LexHubPro 标识' }).first()).toBeVisible();
  await expect(page.getByRole('img', { name: /法务合同智能审查/ })).toBeVisible();
  await shot(page, 'S01', 'home-local-images');

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: '登录' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'LexHubPro 标识' })).toBeVisible();
  await shot(page, 'S02', 'login-local-logo');

  expect(remoteHits, `unexpected CDN image requests: ${remoteHits.join(', ')}`).toEqual([]);
});

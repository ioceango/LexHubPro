/**
 * Record a live demo of https://alphasight.fuxingbros.com (login + PDF review).
 * Credentials via env: ONLINE_DEMO_EMAIL / ONLINE_DEMO_PASSWORD
 * Usage from repo root:
 *   ONLINE_DEMO_EMAIL=... ONLINE_DEMO_PASSWORD=... node scripts/online-demo.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../app/frontend/node_modules/playwright/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'docs', 'demo');
const pdfPath = path.join(root, 'show', '测试合同.pdf');
const email = process.env.ONLINE_DEMO_EMAIL || '';
const password = process.env.ONLINE_DEMO_PASSWORD || '';
const baseURL = 'https://alphasight.fuxingbros.com';

if (!email || !password) {
  console.error('ONLINE_DEMO_EMAIL and ONLINE_DEMO_PASSWORD are required');
  process.exit(1);
}
if (!fs.existsSync(pdfPath)) {
  console.error('missing PDF', pdfPath);
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });
const shot = async (page, name) => {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log('shot', file);
};

const browser = await chromium.launch({
  headless: true,
  args: ['--ignore-certificate-errors'],
});
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: outDir, size: { width: 1440, height: 900 } },
});
const page = await context.newPage();
page.setDefaultTimeout(30_000);

try {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.getByRole('img', { name: 'LexHubPro 标识' }).first().waitFor({ timeout: 20_000 });
  await shot(page, 'S01-home');

  await page.goto(`${baseURL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: '登录' }).waitFor();
  await shot(page, 'S02-login');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: '登录' }).click();
  await page.waitForURL(/\/(review|settings)/, { timeout: 30_000 });
  await page.getByText(/当前审查模型/).waitFor({ timeout: 30_000 });
  await shot(page, 'S03-logged-in-review');

  if (await page.getByRole('button', { name: '请先配置审查模型' }).isVisible().catch(() => false)) {
    await shot(page, 'S03b-need-model');
    throw new Error('online account has no enabled review model');
  }

  await page.locator('input[type="file"]').setInputFiles(pdfPath);
  await page.getByText('测试合同.pdf').waitFor();
  await shot(page, 'S04-file-selected');
  await page.getByRole('button', { name: '开始 AI 审查' }).click();
  await page.getByText('审查进行中').waitFor({ timeout: 20_000 });
  await shot(page, 'S05-review-in-progress');
  await page.waitForURL(/\/report\/\d+/, { timeout: 600_000, waitUntil: 'commit' });
  await page.waitForTimeout(2500);
  await shot(page, 'S06-report');
  console.log('report url', page.url());
} catch (err) {
  await shot(page, 'S99-error').catch(() => {});
  console.error(err);
  await context.close();
  await browser.close();
  process.exit(1);
}

const video = page.video();
await context.close();
await browser.close();
if (video) {
  const src = await video.path();
  const dest = path.join(outDir, 'review-flow.webm');
  fs.renameSync(src, dest);
  console.log('video', dest);
}
console.log('demo ok');

/**
 * Record live demos of model config + PDF review.
 * Reads repo-root `.env` `#demo show config` keys; env vars override.
 * Never logs secrets. Usage from repo root: `node scripts/online-demo.mjs`
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../app/frontend/node_modules/playwright/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'docs', 'demo');

const parseDotEnv = (file) => {
  const parsed = {};
  if (!fs.existsSync(file)) return parsed;
  for (const raw of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 1) continue;
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    parsed[line.slice(0, eq).trim()] = value;
  }
  return parsed;
};

const fileCfg = parseDotEnv(path.join(root, '.env'));
const pick = (envKey, fileKey) => (process.env[envKey] || fileCfg[fileKey] || '').trim();

const cfg = {
  baseURL: pick('DEMO_APP_URL', 'demo_app_url').replace(/\/+$/, ''),
  email: pick('ONLINE_DEMO_EMAIL', 'demo_account'),
  password: pick('ONLINE_DEMO_PASSWORD', 'demo_passwd'),
  openrouterKey: pick('ONLINE_DEMO_OPENROUTER_KEY', 'demo_openrouter_key'),
  modelId: pick('ONLINE_DEMO_MODEL', 'demo_openrouter_modle'),
  pdfPath: path.resolve(root, pick('ONLINE_DEMO_PDF', 'pdf_path') || 'show/测试合同.pdf'),
};

const missing = Object.entries({
  demo_app_url: cfg.baseURL,
  demo_account: cfg.email,
  demo_passwd: cfg.password,
  demo_openrouter_key: cfg.openrouterKey,
  demo_openrouter_modle: cfg.modelId,
}).filter(([, value]) => !value).map(([key]) => key);

if (missing.length) {
  console.error('missing demo config keys:', missing.join(', '));
  process.exit(1);
}
if (!fs.existsSync(cfg.pdfPath)) {
  console.error('missing PDF at pdf_path');
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });
const modelShort = cfg.modelId.split('/').pop() || cfg.modelId;
const modelFuzzy = new RegExp(modelShort.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/-/g, '[- ]'), 'i');
let enabledDisplay = modelShort;

const shot = async (page, name) => {
  const file = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log('shot', name);
};

const settle = async (page) => {
  await page.waitForTimeout(1200);
  const toast = page.locator('[data-sonner-toast]').first();
  if (await toast.isVisible().catch(() => false)) {
    await toast.waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => {});
  }
};

const login = async (page) => {
  await page.goto(`${cfg.baseURL}/login`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: '登录' }).waitFor();
  await page.locator('#email').fill(cfg.email);
  await page.locator('#password').fill(cfg.password);
  await page.getByRole('button', { name: '登录' }).click();
  try {
    await page.waitForURL(/\/(review|settings)/, { timeout: 30_000 });
  } catch {
    throw new Error('login stayed on /login — check demo_account/demo_passwd');
  }
  await settle(page);
};

const openrouterCard = (page) =>
  page.locator('section').filter({ has: page.getByRole('heading', { name: 'OpenRouter' }) });

const saveVideo = async (video, destName) => {
  if (!video) return;
  const src = await video.path();
  const dest = path.join(outDir, destName);
  if (fs.existsSync(dest)) fs.unlinkSync(dest);
  fs.renameSync(src, dest);
  console.log('video', destName);
};

const launchContext = async (browser) => {
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: outDir, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30_000);
  return { context, page };
};

const browser = await chromium.launch({
  headless: true,
  args: ['--ignore-certificate-errors'],
});

try {
  const modelSession = await launchContext(browser);
  const page = modelSession.page;
  try {
    await page.goto(cfg.baseURL, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.getByRole('img', { name: 'LexHubPro 标识' }).first().waitFor({ timeout: 20_000 });
    await shot(page, 'S01-home');

    await page.goto(`${cfg.baseURL}/login`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: '登录' }).waitFor();
    await shot(page, 'S02-login');
    await page.locator('#email').fill(cfg.email);
    await page.locator('#password').fill(cfg.password);
    await page.getByRole('button', { name: '登录' }).click();
    try {
      await page.waitForURL(/\/(review|settings)/, { timeout: 30_000 });
    } catch {
      throw new Error('login stayed on /login — check demo_account/demo_passwd');
    }
    await settle(page);

    await page.goto(`${cfg.baseURL}/settings/models`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('heading', { name: '模型配置' }).waitFor();
    await page.getByRole('heading', { name: 'OpenRouter' }).waitFor();
    await shot(page, 'M01-model-settings');

    const card = openrouterCard(page);
    await card.locator('#key-openrouter').fill(cfg.openrouterKey);
    await card.getByRole('button', { name: '保存 Key' }).click();
    await page.getByText(/已保存 OpenRouter Key/).waitFor({ timeout: 30_000 });
    await page.waitForFunction(() => {
      const el = document.querySelector('#key-openrouter');
      return el instanceof HTMLInputElement && el.value === '';
    });
    await settle(page);
    await shot(page, 'M02-key-saved');

    await card.getByRole('button', { name: '拉取模型' }).click();
    await page.getByText(/已拉取 \d+ 个模型/).waitFor({ timeout: 60_000 });
    const search = card.getByRole('textbox', { name: 'OpenRouter 模型搜索' });
    await search.waitFor();
    await search.fill(modelShort);
    await card.getByText(modelFuzzy).first().waitFor({ timeout: 15_000 });
    await shot(page, 'M03-catalog-search');

    const mineLabel = () => card.locator('label').filter({ hasText: modelFuzzy });
    if ((await mineLabel().count()) === 0) {
      await card.getByRole('button', { name: '加入' }).click();
      await page.getByText('已加入我的模型').waitFor({ timeout: 20_000 });
      await mineLabel().first().waitFor({ timeout: 15_000 });
      await settle(page);
    }
    const radio = mineLabel().first().locator('input[type="radio"]');
    if (!(await radio.isChecked())) {
      await mineLabel().first().click();
    }
    await card.getByRole('button', { name: '停用' }).waitFor({ timeout: 20_000 });
    await settle(page);
    enabledDisplay = (await mineLabel().first().innerText()).trim();
    await shot(page, 'M04-model-enabled');
    console.log('enabled model', cfg.modelId);
  } catch (err) {
    await shot(page, 'S99-error').catch(() => {});
    throw err;
  } finally {
    const video = page.video();
    await modelSession.context.close();
    await saveVideo(video, 'model-config.webm');
  }

  const reviewSession = await launchContext(browser);
  const reviewPage = reviewSession.page;
  try {
    await login(reviewPage);
    await reviewPage.goto(`${cfg.baseURL}/review`, { waitUntil: 'domcontentloaded' });
    await reviewPage.getByText(/当前审查模型/).waitFor({ timeout: 30_000 });
    const label = await reviewPage.locator('p', { hasText: '当前审查模型' }).innerText();
    console.log('review model label', label);
    if (!modelFuzzy.test(label) && !label.includes(enabledDisplay)) {
      throw new Error('review page is not using the demo OpenRouter model');
    }
    await shot(reviewPage, 'S03-logged-in-review');

    await reviewPage.locator('input[type="file"]').setInputFiles(cfg.pdfPath);
    await reviewPage.getByText('测试合同.pdf').waitFor();
    await shot(reviewPage, 'S04-file-selected');
    await reviewPage.getByRole('button', { name: '开始 AI 审查' }).click();
    await reviewPage.getByText('审查进行中').waitFor({ timeout: 20_000 });
    await shot(reviewPage, 'S05-review-in-progress');
    await reviewPage.waitForURL(/\/report\/\d+/, { timeout: 600_000, waitUntil: 'commit' });
    await reviewPage.waitForTimeout(2500);
    await shot(reviewPage, 'S06-report');
    console.log('report url', reviewPage.url());
  } catch (err) {
    await shot(reviewPage, 'S99-error').catch(() => {});
    throw err;
  } finally {
    const video = reviewPage.video();
    await reviewSession.context.close();
    await saveVideo(video, 'review-flow.webm');
  }
} catch (err) {
  console.error(err);
  await browser.close();
  process.exit(1);
}

await browser.close();
console.log('demo ok');

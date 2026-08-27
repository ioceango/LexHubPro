import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { loadRuntimeConfig } from './lib/config.ts';

async function initializeApp() {
  try {
    await loadRuntimeConfig();
  } catch {
    /* 使用 lib/config 默认值即可启动 */
  }
  createRoot(document.getElementById('root')!).render(<App />);
}

void initializeApp();

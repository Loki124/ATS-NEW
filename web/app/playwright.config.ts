import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Playwright e2e 配置
 * - baseURL: 前端开发服务器 (默认 5212, 见 src/config)
 * - webServer: 自动启 vite dev, --host 让 vite 同时监听 IPv4 (127.0.0.1)
 * - 后端需手动跑: `cd backend && node --env-file=.env src/app.js &`
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  timeout: 30_000,
  // 全局一次性登录后复用会话，避免 e2e 反复登录触发后端 /auth/login/ 限流(429) 抖动
  globalSetup: './e2e/auth.setup.ts',
  use: {
    baseURL: 'http://127.0.0.1:5212',
    // 复用 globalSetup 落盘的已登录会话（cookie + localStorage）
    storageState: path.join(__dirname, 'e2e', '.auth', 'state.json'),
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npx vite --host 127.0.0.1',
    url: 'http://127.0.0.1:5212',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});

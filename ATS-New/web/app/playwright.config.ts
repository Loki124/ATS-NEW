import { defineConfig, devices } from '@playwright/test';

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
  use: {
    baseURL: 'http://127.0.0.1:5212',
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

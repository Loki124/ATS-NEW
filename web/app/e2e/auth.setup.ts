import { chromium } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const AUTH_STATE = path.join(__dirname, '.auth', 'state.json')

/**
 * 全局一次性登录（globalSetup）—— 解决 settings e2e 反复登录触发后端 /auth/login/ 限流(429) 抖动。
 * 只登录一次，把 cookie + localStorage(accessToken/refreshToken/user) 落盘到 e2e/.auth/state.json，
 * 后续所有 spec 通过 storageState 复用，不再各自打登录接口。
 * 注意：仅用系统默认 chromium 登录一次，远低于限流阈值，稳定。
 */
async function globalSetup() {
  const browser = await chromium.launch({ args: ['--disable-dev-shm-usage', '--no-sandbox'] })
  const page = await browser.newPage()
  await page.goto('http://127.0.0.1:5212/login')
  await page.getByPlaceholder('用户名').fill('admin')
  await page.locator('input[type="password"]').first().fill('admin123')
  await page.getByRole('button', { name: /登\s*录/ }).first().click()
  await page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 15000 })
  await page.context().storageState({ path: AUTH_STATE })
  await browser.close()
}

export default globalSetup

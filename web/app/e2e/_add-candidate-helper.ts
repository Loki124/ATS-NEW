import type { Page } from '@playwright/test'

/**
 * AddCandidateModal V2 E2E - 共享 helper
 *
 * 注意: 实际登录表单的 onAccountFinish 在某些环境下不触发路由跳转
 * (可能是 n-form 的 nextTick + message 竞态), 所以 E2E 测试统一使用
 * "调用 login API + 注入 token 到 localStorage" 的方式绕过登录页。
 *
 * 这样可以:
 * 1. 不依赖登录表单的可交互细节
 * 2. 节省 ~3s 登录交互时间
 * 3. 减少 UI 改动的连带影响
 */

export async function injectAuthToken(page: Page, baseURL = 'http://127.0.0.1:5212') {
  // 1. 调用 login API 获取 token
  const resp = await page.request.post(`${baseURL}/api/v1/auth/login/`, {
    data: { username: 'admin', password: 'admin123' },
  })
  if (!resp.ok()) {
    throw new Error(`login API failed: ${resp.status()} ${await resp.text()}`)
  }
  const body = await resp.json()
  const access = body.data.access
  const refresh = body.data.refresh
  if (!access) throw new Error('login response missing access token')

  // 2. 注入到 localStorage (兼容旧 key 'token' + 新 key 'accessToken')
  await page.goto(`${baseURL}/login`)
  await page.evaluate(
    ([a, r]) => {
      localStorage.setItem('token', a)
      localStorage.setItem('accessToken', a)
      localStorage.setItem('refreshToken', r)
    },
    [access, refresh],
  )

  return { access, refresh }
}

export async function gotoCandidates(page: Page, baseURL = 'http://127.0.0.1:5212') {
  await page.goto(`${baseURL}/candidates`)
  await page.waitForLoadState('domcontentloaded')
}

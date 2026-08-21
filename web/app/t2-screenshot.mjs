/**
 * T2 Playwright 截图主理人独立核验
 */
import { chromium } from 'playwright'
import { writeFileSync } from 'fs'

const SCREENSHOTS = '/tmp/t2-screenshots'
const BASE = 'http://127.0.0.1:5212'

// 用已登录 token 直接访问（dev 通常 localStorage 已有）
// 这里用动态 login：直接打开 /login
const result = {
  loginLight: null,
  loginDark: null,
  loginBrand: null,
  errors: [],
}

try {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  // 1. Login 浅色
  console.log('[1/4] 打开 /login ...')
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: `${SCREENSHOTS}/login-light.png`, fullPage: true })
  result.loginLight = `${SCREENSHOTS}/login-light.png`
  console.log('  ✓ login-light.png')

  // 2. Login 暗色（用 theme store API）
  console.log('[2/4] 切换暗色模式 ...')
  await page.evaluate(() => {
    const w = window
    if (w.__ats?.theme) {
      w.__ats.theme.setMode('dark')
    }
  })
  await page.waitForTimeout(1000)
  await page.screenshot({ path: `${SCREENSHOTS}/login-dark.png`, fullPage: true })
  result.loginDark = `${SCREENSHOTS}/login-dark.png`
  console.log('  ✓ login-dark.png')

  // 3. Login 换品牌色（保持暗色）
  console.log('[3/4] 切换品牌色 #FF6B6B ...')
  await page.evaluate(() => {
    const w = window
    if (w.__ats?.theme) {
      w.__ats.theme.setBrand('#FF6B6B')
    }
  })
  await page.waitForTimeout(1000)
  await page.screenshot({ path: `${SCREENSHOTS}/login-brand.png`, fullPage: true })
  result.loginBrand = `${SCREENSHOTS}/login-brand.png`
  console.log('  ✓ login-brand.png')

  // 4. 检测 Login 实际渲染的关键 DOM（验证玻璃类应用）
  console.log('[4/4] 校验 DOM 关键类 ...')
  const domChecks = await page.evaluate(() => {
    const out = {}
    out.hasAppAurora = !!document.querySelector('.app-aurora')
    out.hasGlassPanel = !!document.querySelector('.glass-panel')
    out.hasGlassInput = !!document.querySelector('.glass-input')
    out.hasGradientTitle = !!document.querySelector('.gradient-title')
    out.brandVar = getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()
    out.bodyClass = document.body.className
    return out
  })
  result.domChecks = domChecks
  console.log('  DOM checks:', JSON.stringify(domChecks, null, 2))

  await browser.close()
  console.log('\n✅ 截图完成:', result)
} catch (e) {
  result.errors.push(String(e))
  console.error('❌ 错误:', e)
}

writeFileSync(`${SCREENSHOTS}/result.json`, JSON.stringify(result, null, 2))
process.exit(0)

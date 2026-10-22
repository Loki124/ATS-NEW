// 无障碍冒烟检查 —— 基于 @axe-core/playwright 跑 axe-core。
//
// 用法：
//   BASE_URL=http://localhost:5277 \
//   ROUTES=/login,/,/candidates,/positions \
//   npm run audit:a11y
//
// 默认 BASE_URL=http://localhost:5277，ROUTES 为一组代表性路由（可用 env 覆盖）。
// 默认写出 JSON 报告到 /tmp/ats-a11y-report.json（可用 A11Y_REPORT 覆盖路径）。
//
// 2026-10-21 (整改卡 E7): **按 violations 数退出**（原先恒 process.exit(0)，
// 让 R-102/R-103/R-109 三个 [R] 项永久处于"未验证"状态）。
//   - A11Y_MAX_VIOLATIONS: 允许的 violations 上限（默认 0 = 一条都不许有）→ 超出即 exit 1
//   - A11Y_MAX_ERRORS:    允许的"路由打不开/axe 报错"数（默认 0）→ 超出即 exit 1
//     （路由挂掉 = 这一条根本没检查到, 不能当通过）
//   - A11Y_ALLOW_VIOLATIONS=1: 只报告不阻断（存量基线期用; 存量清零后删掉该 env 即翻硬门禁）
//   - A11Y_VIEWPORT: 视口 WxH（默认 1440x900）→ CI 里跑 320/768/1200 三档
//   - A11Y_STORAGE_STATE: 已登录会话快照路径（默认 e2e/.auth/state.json, 存在则复用）
//     不复用的话, /candidates 这类需登录的路由会被重定向到 /login → 检的根本不是目标页。
//
// 依赖：playwright + @axe-core/playwright（均已装于 web/app/node_modules）。
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { existsSync, writeFileSync } from 'node:fs'

const BASE_URL = (process.env.BASE_URL || 'http://localhost:5277').replace(/\/$/, '')
const ROUTES = (process.env.ROUTES ||
  '/login,/,/candidates,/positions,/demands,/settings,/referral')
  .split(',').map(s => s.trim()).filter(Boolean)
const REPORT = process.env.A11Y_REPORT || '/tmp/ats-a11y-report.json'
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
const MAX_VIOLATIONS = Number(process.env.A11Y_MAX_VIOLATIONS ?? '0')
const MAX_ERRORS = Number(process.env.A11Y_MAX_ERRORS ?? '0')
const ALLOW_VIOLATIONS = process.env.A11Y_ALLOW_VIOLATIONS === '1'
const STORAGE_STATE = process.env.A11Y_STORAGE_STATE || 'e2e/.auth/state.json'
const [vpWidth, vpHeight] = (process.env.A11Y_VIEWPORT || '1440x900')
  .split('x').map(n => Number(n) || 0)
const viewport = { width: vpWidth || 1440, height: vpHeight || 900 }

const browser = await chromium.launch({ headless: true })
// @axe-core/playwright 要求页面必须来自 newContext()，不能用 browser.newPage()
const context = await browser.newContext({
  viewport,
  ...(existsSync(STORAGE_STATE) ? { storageState: STORAGE_STATE } : {}),
})
const page = await context.newPage()

const details = []
for (const route of ROUTES) {
  const url = BASE_URL + route
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
  } catch (e) {
    details.push({ route, url, error: 'goto: ' + String(e).split('\n')[0] })
    continue
  }
  // 给 SPA hydrate / 接口回填留时间
  await page.waitForTimeout(1500)
  let results
  try {
    results = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  } catch (e) {
    details.push({ route, url, error: 'axe: ' + String(e).split('\n')[0] })
    continue
  }
  details.push({
    route,
    url,
    violations: results.violations.map(v => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.length,
      helpUrl: v.helpUrl,
    })),
    passCount: results.passes.length,
    incompleteCount: results.incomplete.length,
  })
}

await browser.close()

let total = 0
const byImpact = {}
for (const r of details) {
  if (!r.violations) continue
  for (const v of r.violations) {
    total++
    byImpact[v.impact] = (byImpact[v.impact] || 0) + 1
  }
}

const summary = {
  baseUrl: BASE_URL,
  routes: ROUTES.length,
  viewport,
  totalViolations: total,
  byImpact,
  errorCount: details.filter((r) => r.error).length,
  scannedAt: new Date().toISOString(),
}
writeFileSync(REPORT, JSON.stringify({ summary, details }, null, 2))

console.log(`=== A11Y SMOKE (viewport ${viewport.width}x${viewport.height}) ===`)
console.log(`BASE_URL=${BASE_URL}  routes=${ROUTES.length}  totalViolations=${total}`)
console.log('byImpact =', JSON.stringify(byImpact))
console.log(`report -> ${REPORT}`)
for (const r of details) {
  if (r.error) { console.log(`  ⚠ ${r.route}: ${r.error}`); continue }
  if (r.violations.length) {
    console.log(`  ✗ ${r.route}: ${r.violations.length} violation(s)`)
    for (const v of r.violations.slice(0, 10)) {
      console.log(`      [${v.impact}] ${v.id} — ${v.help} (×${v.nodes})`)
    }
  } else {
    console.log(`  ✓ ${r.route}: clean (${r.passCount} passed)`)
  }
}

// 2026-10-21 (整改卡 E7): 按 violations / 路由错误数退出 (原先恒 exit 0 → 三个 [R] 项永久未验证)。
const errorCount = details.filter((r) => r.error).length
const overViolations = total > MAX_VIOLATIONS
const overErrors = errorCount > MAX_ERRORS
if (ALLOW_VIOLATIONS) {
  console.log(
    `\n[report-only] A11Y_ALLOW_VIOLATIONS=1 → 不阻断 (violations=${total}/${MAX_VIOLATIONS}, errors=${errorCount}/${MAX_ERRORS})`,
  )
  process.exit(0)
}
if (overViolations || overErrors) {
  console.error(
    `\n✗ A11Y 未达标: violations=${total} (上限 ${MAX_VIOLATIONS}), ` +
    `路由错误=${errorCount} (上限 ${MAX_ERRORS}) → exit 1`,
  )
  process.exit(1)
}
console.log(`\n✓ A11Y 达标: violations=${total} (上限 ${MAX_VIOLATIONS}), 路由错误=${errorCount}`)

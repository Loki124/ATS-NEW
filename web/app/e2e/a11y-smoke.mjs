// 无障碍冒烟检查（非阻断）—— 基于 @axe-core/playwright 跑 axe-core。
//
// 用法：
//   BASE_URL=http://localhost:5277 \
//   ROUTES=/login,/,/candidates,/positions \
//   npm run audit:a11y
//
// 默认 BASE_URL=http://localhost:5277，ROUTES 为一组代表性路由（可用 env 覆盖）。
// 默认写出 JSON 报告到 /tmp/ats-a11y-report.json（可用 A11Y_REPORT 覆盖路径）。
//
// 设计原则：非阻断。本脚本始终以 exit 0 结束，仅打印汇总 + 写报告，
// 不进 lint:ci 门禁、不阻断任何现有流程。后续若要在 CI 阻断，
// 移除末尾的 process.exit(0) 并按 violations 数退出即可。
//
// 依赖：playwright + @axe-core/playwright（均已装于 web/app/node_modules）。
import { chromium } from 'playwright'
import { AxeBuilder } from '@axe-core/playwright'
import { writeFileSync } from 'node:fs'

const BASE_URL = (process.env.BASE_URL || 'http://localhost:5277').replace(/\/$/, '')
const ROUTES = (process.env.ROUTES ||
  '/login,/,/candidates,/positions,/demands,/settings,/referral')
  .split(',').map(s => s.trim()).filter(Boolean)
const REPORT = process.env.A11Y_REPORT || '/tmp/ats-a11y-report.json'
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

const browser = await chromium.launch({ headless: true })
// @axe-core/playwright 要求页面必须来自 newContext()，不能用 browser.newPage()
const context = await browser.newContext()
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
  totalViolations: total,
  byImpact,
  scannedAt: new Date().toISOString(),
}
writeFileSync(REPORT, JSON.stringify({ summary, details }, null, 2))

console.log('=== A11Y SMOKE (non-blocking) ===')
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

// 非阻断：始终 0。需要 CI 阻断时改此处。
process.exit(0)

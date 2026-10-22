/**
 * e2e/shot.mjs — 页面截图工具（UI 改动的「自证」工具链）
 *
 * ## 为什么需要它
 * 此前 UI 改动只能靠「静态推理 + 单测」自证，结果连续三轮都出现「代码看着对、实际渲染不对」
 * （grid 行优先导致两行排成两列、图标越出高亮块、日期在「/」处折行……）。
 * 根因不是代码逻辑，而是**没有截图**。本脚本把「渲染真值」变成一条命令。
 *
 * ## 关键点 1：浏览器从哪来
 * 本机 `~/Library/Caches/ms-playwright/` 是空的（playwright 自带 chromium 未下载），
 * `chromium.launch()` 直接报 "Executable doesn't exist" → 这就是以前「起不了浏览器」的真因。
 * 解法：`channel: 'chrome'` —— 直接驱动**系统已装的 Google Chrome**，无需下载任何东西。
 *
 * ## 关键点 2：登录态从哪来
 * `admin/admin123` 已在 2026-10-08 移除（弱口令不再写死），`e2e/auth.setup.ts` 因此过期。
 * 本脚本**不猜密码、不改任何用户数据**：直接调后端 `_issue_login_token(admin)` 签发一对
 * access/refresh（与登录接口同一套逻辑），注入 localStorage 后访问。
 * 需要账号时用环境变量覆盖：SHOT_USER / SHOT_PASS（走真实登录接口）。
 *
 * ## 用法
 *   node e2e/shot.mjs <路由> [<路由> ...] [选项]
 *   node e2e/shot.mjs /campus/person /campus/rotation-resource
 *   node e2e/shot.mjs /campus/person --click="button:has-text('高级筛选')" --name=advanced
 *   node e2e/shot.mjs /campus/person --full --out=/tmp/shots
 *
 * 选项：
 *   --click=<选择器>   截图前点一下（打开弹窗/下拉等），可重复
 *   --hover=<选择器>   截图前悬停（触发浮出层）
 *   --measure=<选择器> 量几何并打印（getComputedStyle + getBoundingClientRect），可重复
 *   --wait=<毫秒>      截图前额外等待（默认 2500ms，等接口与动画）
 *   --full             整页截图（默认只截视口）
 *   --out=<目录>       输出目录（默认 web/app/e2e/__shots__）
 *   --name=<前缀>      文件名前缀（单路由时生效）
 *   --width / --height 视口尺寸（默认 1440×900）
 */
import { chromium } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'url'
import path from 'path'
import { mkdirSync } from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const BASE = process.env.SHOT_BASE || 'http://127.0.0.1:5212'
const DJANGO_DIR = path.resolve(__dirname, '../../../apps/django')
const PY = path.join(DJANGO_DIR, '.venv/bin/python')

const argv = process.argv.slice(2)
const routes = []
const clicks = []
const hovers = []
const measures = []
let wait = 2500
let fullPage = false
let outDir = path.join(__dirname, '__shots__')
let namePrefix = ''
let width = 1440
let height = 900

for (const a of argv) {
  if (a.startsWith('--click=')) clicks.push(a.slice(8))
  else if (a.startsWith('--hover=')) hovers.push(a.slice(8))
  else if (a.startsWith('--measure=')) measures.push(a.slice(10))
  else if (a.startsWith('--wait=')) wait = Number(a.slice(7))
  else if (a.startsWith('--out=')) outDir = a.slice(6)
  else if (a.startsWith('--name=')) namePrefix = a.slice(7)
  else if (a.startsWith('--width=')) width = Number(a.slice(8))
  else if (a.startsWith('--height=')) height = Number(a.slice(9))
  else if (a === '--full') fullPage = true
  else routes.push(a)
}

if (!routes.length) {
  console.error('用法: node e2e/shot.mjs <路由> [选项]   （见文件头注释）')
  process.exit(1)
}
mkdirSync(outDir, { recursive: true })

/** 签发 dev 会话（只读：只生成 token，不改任何用户数据） */
function mintSession() {
  const code = `
import json
from apps.core.models import User
from apps.accounts.views import _issue_login_token
u = User.objects.filter(username=os.environ.get('SHOT_USER', 'admin'), deleted_at__isnull=True).first()
if u is None:
    raise SystemExit('NO_USER')
print('__SHOT_SESSION__' + json.dumps(_issue_login_token(u), ensure_ascii=False))
`
  const out = execFileSync(PY, ['manage.py', 'shell'], {
    cwd: DJANGO_DIR,
    input: 'import os\n' + code,
    encoding: 'utf8',
    env: { ...process.env, SHOT_USER: process.env.SHOT_USER || 'admin' },
  })
  const line = out.split('\n').find((l) => l.includes('__SHOT_SESSION__'))
  if (!line) throw new Error('签发会话失败：未拿到 token')
  return JSON.parse(line.slice(line.indexOf('__SHOT_SESSION__') + '__SHOT_SESSION__'.length))
}

const session = mintSession()
console.log('✔ 已签发 dev 会话（admin）')

const browser = await chromium.launch({
  channel: 'chrome',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})
const context = await browser.newContext({
  viewport: { width, height },
  deviceScaleFactor: 2,
  locale: 'zh-CN',
})

// 注入会话（addInitScript 在每次页面加载前执行）
await context.addInitScript((s) => {
  localStorage.setItem('accessToken', s.access)
  localStorage.setItem('refreshToken', s.refresh)
  localStorage.setItem('user', JSON.stringify(s.user))
}, session)

const page = await context.newPage()
page.on('pageerror', (e) => console.warn('  [page error]', String(e).slice(0, 160)))

for (const route of routes) {
  const url = route.startsWith('http') ? route : `${BASE}${route}`
  await page.goto(url, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(wait)
  // ⚠️ 顺序：**先 click 后 hover** —— 典型场景是「点开折叠态 → 再 hover 某个分组浮出子菜单」，
  //    hover 早于 click 会打在还没出现的元素上（之前就是因此误判「浮出没生效」）。
  for (const sel of clicks) {
    try {
      await page.locator(sel).first().click({ timeout: 5000 })
      await page.waitForTimeout(800)
    } catch {
      console.warn(`  ! click 未命中: ${sel}`)
    }
  }
  for (const sel of hovers) {
    try {
      await page.locator(sel).first().hover({ timeout: 3000 })
      await page.waitForTimeout(600)
    } catch {
      console.warn(`  ! hover 未命中: ${sel}`)
    }
  }
  const slug =
    (namePrefix && routes.length === 1
      ? namePrefix
      : route.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_|_$/g, '')) || 'shot'
  const file = path.join(outDir, `${slug}.png`)
  await page.screenshot({ path: file, fullPage })
  console.log(`✔ ${route} → ${file}`)

  // 量几何：把「规则命中了吗 / 几何对吗」变成可打印的证据，而不是靠目测
  for (const sel of measures) {
    const measured = await page.evaluate((s) => {
      const el = document.querySelector(s)
      if (!el) return { found: false }
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return {
        found: true,
        tag: el.tagName,
        class: el.className?.toString().slice(0, 80),
        // scope id：h() 渲染的元素没有 data-v-* → scoped 规则不命中
        scopeAttrs: el.getAttributeNames().filter((n) => n.startsWith('data-v-')),
        box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        // 非继承属性优先：font-weight / color / display / align-items / gap
        style: {
          display: cs.display,
          alignItems: cs.alignItems,
          justifyContent: cs.justifyContent,
          fontWeight: cs.fontWeight,
          color: cs.color,
          padding: cs.padding,
          gap: cs.gap,
          whiteSpace: cs.whiteSpace,
        },
      }
    }, sel)
    if (!measured.found) {
      console.warn(`  ! measure 未命中: ${sel}`)
      continue
    }
    console.log(`  📐 ${sel}`)
    console.log(`     box    ${JSON.stringify(measured.box)}`)
    console.log(`     style  ${JSON.stringify(measured.style)}`)
    if (measured.scopeAttrs.length === 0) {
      console.log(
        `     ⚠️  该元素**无 data-v-* 属性** → 若其样式写在 <style scoped> 里，则规则不命中`,
      )
    }
  }
}

await browser.close()
console.log('done')

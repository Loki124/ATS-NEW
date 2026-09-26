/**
 * 系统升级检测服务（2026-09-23 新增；2026-09-26 加固）
 *
 * 机制：前端定时拉取线上 `version.json`，与构建期写入的本地版本 `APP_VERSION` 比对。
 *   - 部署了新构建后，线上 version.json 变化，但当前已加载的 bundle 仍是旧 `APP_VERSION`
 *     （编译期由 vite appVersionPlugin 生成 src/generated/appVersion.ts 写入）
 *     → 不一致 → 弹「系统已升级」确认框，由用户决定是否刷新（避免旧 bundle 静默运行）。
 *   - `version.json` 由 vite.config.ts 的 appVersionPlugin 在 dev/build 期生成（public/version.json，
 *     构建时被拷到产物根目录；Vite 跨 base 稳定，按 origin 根路径 `/version.json` 取）。
 *
 * 设计约束（对齐项目既有规范）：
 *   - 不打扰：登录页（/login）与后台标签页（visibilityState !== 'visible'）不弹确认框，
 *     且此时**不**标记「已提示」，等用户回到可见的前台页面时再提示。
 *   - 不重复打扰：每个线上版本在**本浏览器**只提示一次（localStorage 持久化一个**有界集合**），
 *     直到出现新的、尚未提示过的线上版本。
 *     → 旧实现用内存变量：页面一刷新即忘，线上版本与 bundle 失配时「每次加载都弹、
 *       点立即刷新也还弹」；且只记「上一个版本」时，多节点/负载均衡导致 version.json
 *       在 A/B 间抖动会反复弹。集合去重可同时消除这两种频弹（2026-09-26 生产缺陷根因）。
 *   - 静默失败：拉取失败（网络/404/非 JSON）不影响正常功能，下次轮询再试。
 */

import { APP_VERSION } from '@/generated/appVersion'

const PROMPTED_KEY = 'ats.promptedAppVersions'
const MAX_REMEMBERED = 8
const POLL_INTERVAL_MS = 60_000

let timer: ReturnType<typeof setInterval> | null = null
let onVisibility: (() => void) | null = null
let promptedVersions: Set<string> = readPrompted()

function readPrompted(): Set<string> {
  try {
    const raw = localStorage.getItem(PROMPTED_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? new Set(arr.filter((x) => typeof x === 'string')) : new Set()
  } catch {
    return new Set()
  }
}

function markPrompted(version: string): void {
  promptedVersions.add(version)
  try {
    // 有界：只保留最近 MAX_REMEMBERED 个（Set 保留插入顺序）
    const arr = Array.from(promptedVersions).slice(-MAX_REMEMBERED)
    promptedVersions = new Set(arr)
    localStorage.setItem(PROMPTED_KEY, JSON.stringify(arr))
  } catch {
    // 隐私模式等 localStorage 不可用 → 退化为仅内存去重
  }
}

function getLocalVersion(): string {
  return APP_VERSION
}

async function fetchRemoteVersion(): Promise<string | null> {
  // 按 origin 根路径取，跨 Vite base（dev '/'，prod '/static/'）稳定
  const url = `${location.origin}/version.json?t=${Date.now()}`
  try {
    const resp = await fetch(url, { cache: 'no-store' })
    if (!resp.ok) return null
    // 防误判：若代理/SPA fallback 把 /version.json 回成 HTML，直接放弃本次检测，
    // 避免把页面 HTML 当版本源解析出垃圾值。仅当明确是 text/html 时才拒绝，
    // 不拒绝「未声明 content-type」的正常 JSON 静态文件。
    const ct = (resp.headers.get('content-type') || '').toLowerCase()
    if (ct.includes('text/html')) return null
    const data = (await resp.json()) as { version?: string }
    const v = data && typeof data.version === 'string' ? data.version : null
    return v && v.length > 0 ? v : null
  } catch {
    return null
  }
}

/** 硬刷新：附加一次性查询参数击穿磁盘/边缘(CDN)缓存重新请求文档，确保拿到新 bundle */
function hardReload(): void {
  try {
    const url = new URL(location.href)
    url.searchParams.set('_r', String(Date.now()))
    location.replace(url.toString())
  } catch {
    location.reload()
  }
}

/** 清掉「立即刷新」留下的一次性缓存击穿参数，保持地址栏干净 */
function stripReloadParam(): void {
  try {
    const url = new URL(location.href)
    if (url.searchParams.has('_r')) {
      url.searchParams.delete('_r')
      history.replaceState(null, '', url.toString())
    }
  } catch {
    // 忽略：地址栏清理失败无副作用
  }
}
stripReloadParam()

function showUpdateDialog(remote: string): void {
  // 复用 main.ts 注入的全局离散 dialog（无需组件 tree 内 useDialog）
  const dialog = (window as any).$dialog
  if (!dialog) return
  dialog.info({
    title: '系统已升级',
    // 带上当前/最新版本号，便于用户与运维定位（也便于判断是否为「幽灵升级」）
    content: `系统已发布新版本（当前 ${getLocalVersion()} → 最新 ${remote}），建议刷新页面以使用最新功能与修复。`,
    positiveText: '立即刷新',
    negativeText: '稍后',
    showIcon: true,
    onPositiveClick: () => {
      hardReload()
    },
  })
}

/** 单次检测（可被外部手动触发，如切换系统后） */
export async function checkAppVersion(): Promise<void> {
  const remote = await fetchRemoteVersion()
  if (!remote) return
  const local = getLocalVersion()
  if (!local) return
  // 一致 / 本浏览器已就这个线上版本提示过 → 不打扰
  if (remote === local || promptedVersions.has(remote)) return
  // 登录页 / 后台标签页不打扰，且**不标记已提示**（等回到可见前台再提示）
  if (location.pathname.includes('/login') || document.visibilityState !== 'visible') return
  markPrompted(remote)
  showUpdateDialog(remote)
}

/** 启动轮询（默认 60s）。幂等：重复调用不会叠加定时器。 */
export function startAppVersionWatcher(intervalMs = POLL_INTERVAL_MS): void {
  if (timer) return
  void checkAppVersion()
  timer = setInterval(() => {
    void checkAppVersion()
  }, intervalMs)
  // 从后台切回前台时立即补一次检测（后台期间不打扰，切回后尽快提示）
  onVisibility = () => {
    if (document.visibilityState === 'visible') void checkAppVersion()
  }
  document.addEventListener('visibilitychange', onVisibility)
}

/** 停止轮询（如测试或卸载场景） */
export function stopAppVersionWatcher(): void {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (onVisibility) {
    document.removeEventListener('visibilitychange', onVisibility)
    onVisibility = null
  }
}

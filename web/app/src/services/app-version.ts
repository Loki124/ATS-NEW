/**
 * 系统升级检测服务（2026-09-23 新增）
 *
 * 机制：前端定时拉取线上 `version.json`，与构建期写入的本地版本 `APP_VERSION` 比对。
 *   - 部署了新构建后，线上 version.json 变化，但当前已加载的 bundle 仍是旧 `APP_VERSION`
 *     （编译期由 vite appVersionPlugin 生成 src/generated/appVersion.ts 写入）
 *     → 不一致 → 弹「系统已升级」确认框，由用户决定是否刷新（避免旧 bundle 静默运行）。
 *   - `version.json` 由 vite.config.ts 的 appVersionPlugin 在 dev/build 期生成（public/version.json，
 *     构建时被拷到产物根目录；Vite 跨 base 稳定，按 origin 根路径 `/version.json` 取）。
 *
 * 设计约束（对齐项目既有规范）：
 *   - 不打扰：登录页（/login）与后台标签页（visibilityState !== 'visible'）不弹确认框。
 *   - 不重复打扰：同一线上版本只提示一次（promptedVersion 记录），直到线上版本再次变更。
 *   - 静默失败：拉取失败（网络/404）不影响正常功能，下次轮询再试。
 */

import { APP_VERSION } from '@/generated/appVersion'

let timer: ReturnType<typeof setInterval> | null = null
let promptedVersion: string | null = null

function getLocalVersion(): string {
  return APP_VERSION
}

async function fetchRemoteVersion(): Promise<string | null> {
  // 按 origin 根路径取，跨 Vite base（dev '/'，prod '/static/'）稳定
  const url = `${location.origin}/version.json?t=${Date.now()}`
  try {
    const resp = await fetch(url, { cache: 'no-store' })
    if (!resp.ok) return null
    const data = (await resp.json()) as { version?: string }
    return data.version ?? null
  } catch {
    return null
  }
}

function showUpdateDialog(): void {
  // 复用 main.ts 注入的全局离散 dialog（无需组件 tree 内 useDialog）
  const dialog = (window as any).$dialog
  if (!dialog) return
  dialog.info({
    title: '系统已升级',
    content: '系统已发布新版本，建议刷新页面以使用最新功能与修复。',
    positiveText: '立即刷新',
    negativeText: '稍后',
    showIcon: true,
    onPositiveClick: () => {
      window.location.reload()
    },
    // 取消后不重复打扰：promptedVersion 已记录本次线上版本
  })
}

/** 单次检测（可被外部手动触发，如切换系统后） */
export async function checkAppVersion(): Promise<void> {
  const remote = await fetchRemoteVersion()
  if (!remote) return
  const local = getLocalVersion()
  if (!local) return
  if (remote !== local && remote !== promptedVersion) {
    promptedVersion = remote
    // 登录页 / 后台标签页不打扰
    if (location.pathname.includes('/login') || document.visibilityState !== 'visible') return
    showUpdateDialog()
  }
}

/** 启动轮询（默认 60s）。幂等：重复调用不会叠加定时器。 */
export function startAppVersionWatcher(intervalMs = 60_000): void {
  if (timer) return
  void checkAppVersion()
  timer = setInterval(() => {
    void checkAppVersion()
  }, intervalMs)
}

/** 停止轮询（如测试或卸载场景） */
export function stopAppVersionWatcher(): void {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

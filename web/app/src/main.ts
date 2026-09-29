import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios, { type AxiosResponse, type AxiosError } from 'axios'  // 2026-06-29: 全局 axios 拦截器需要
import App from './App.vue'
import router from './router'
import { naivePlugin } from './plugins/naive'
import { setupPermissionDirective } from './directives/permission'
import i18n from './locales' // 2026-09-24: vue-i18n 接入（默认 zh-CN，en-US 兜底）
import { startAppVersionWatcher } from './services/app-version'

// Naive UI —— 见 plugins/naive.ts (统一注册, 测试可复用)

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import './styles/tokens.css'
import './styles/glass.css'
import './styles/glass-modal.css' // T2.3: 模态/抽屉玻璃化扩展（n-modal-container / n-drawer 等）
import './index.css'

import { createDiscreteApi } from 'naive-ui'
// v2: 全局 toast/dialog（拦截器 + shortcuts 帮助面板共用）· 必须在 axios 拦截器之前声明
// 2026-09-23: 追加 dialog，供 app-version 升级检测在无组件上下文时弹「系统已升级」确认框
const _discrete = createDiscreteApi(['message', 'dialog'])
const _toast = _discrete.message
// 暴露全局离散 dialog，供 services/app-version.ts 在无组件上下文时调用
;(window as any).$dialog = _discrete.dialog

// G-2026-09-23 双系统 X-Recruit-Type 注入原在此处通过劫持 axios.create 全局包装实现；
// 2026-09-29 已移除该全局猴子补丁（P1-2 收尾）：X-Recruit-Type 现由 request.ts(createApi) 与
// api/auth.ts 各自请求拦截器在运行时读取 useSystemStore().current 注入，切换系统下次请求即生效。
// 仅下方全局 response 拦截器（404/500 处理）保留。

// 2026-06-29 花无缺: 全局 axios 拦截器 — 区分 401/403 (真权限) vs 404 (endpoint 缺)
// 之前 404 被 catch 走 → UI 显示 "无权限" / "加载失败" → 兵哥误以为权限问题.
// 真实根因: 后端 9 个 app 缺实现 (mou/library/scraped-resume 等), 兵哥看到的"超管没权限"全是 404.
// 全局 hook 让任何 .vue 在 catch 404 时 console.warn 出来, 真实 401/403 仍触发 logout.
axios.interceptors.response.use(
  (resp: AxiosResponse) => resp,
  (err: AxiosError) => {
    const status = err?.response?.status
    const url = err?.config?.url ?? '<unknown>'
    if (status === 404) {
      // 后端 endpoint 不存在 (开发期常见 — Plan 注释里说"待实现"但还没做)
      // ★ 2026-08-23 V3 §新 #4 收口：404 静默 + 仅 console.warn，不弹 toast（避免吓用户"接口不存在"）
      // 业务页自己跳占位（Placeholder.vue 机制）
      console.warn(
        `[API 404] 后端没实现这个 endpoint: ${url}\n` +
        `  → 这是 "后端 app 缺" 不是 "权限问题". 看报告: REPORT-2026-06-29-ats-complete.md §10`
      )
    } else if (status === 500) {
      console.error(`[API 500] 后端 bug: ${url}`, err?.response?.data)
      // ★ V3 §新 #4 改文案：从"服务异常，请稍后再试" → "服务繁忙，请稍后重试"（避免暗示系统 bug）
      _toast.error('服务繁忙，请稍后重试')
    }
    return Promise.reject(err)
  }
)

const app = createApp(App)

app.use(createPinia())
app.use(naivePlugin)
app.use(i18n) // 2026-09-24: 注册 i18n 实例（必须在 mount 前，供组件 useI18n() 使用）
// 元素级最小权限指令 v-permission (消费后端 /me 的 resource_code 列表)
setupPermissionDirective(app)
// ⚠️ 2026-09-15: app.use(router) 被有意下移到「store hydrate 之后」（见文件底部）。
//   Router 在 install 时立即触发首次导航，若此时 userStore 还没 hydrate，
//   守卫读到的 user.roles 是空数组 → 硬加载角色受限页会被误弹 /forbidden。
//   保持在这个位置之后安装，守卫首次导航就能拿到真实角色。

// 2026-06-15: 在 mount 之前从 localStorage 同步恢复 user
// 否则 router.beforeEach 跑时 userStore.user 还是 null,
// meta.roles 守卫看到 user?.roleType === undefined 误判 'user has undefined'
// → access denied 白名单页跳不进去
// 2026-06-16: 适配 Django SimpleJWT - 改用 accessToken/refreshToken 双 token
// 2026-06-17: 加 fetchMe 服务端重调 — 防止旧 Login.vue 写的 stale localStorage 永久卡死 RBAC
//   Step 1: 同步从 localStorage rehydrate, mount 前 store 不是 null, 网络挂了 UI 也能用快照
//   Step 2: 如果有 accessToken, await /api/v1/auth/me/ 用服务端数据覆盖本地
//           失败 401/403 -> logout 强制重登
//           网络抖动/5xx -> 留快照, 后续 API 401 时再被 axios 拦截器登出
import { useUserStore } from './stores/user'
import { useThemeStore } from './stores/theme'
import { useBrandStore } from './stores/brand'
const _userStore = useUserStore()
const _themeStore = useThemeStore()
const _brandStore = useBrandStore()

// v2 液态玻璃：从 localStorage 恢复主题偏好（品牌色 + 暗色模式）
// 必须在 Vue mount 之前调用，否则初始渲染用旧值会闪烁
_themeStore.init()

// 暴露测试 API（dev only）—— 给浏览器 console / 自动化测试用
// 例：window.__ats.theme.setBrand('#FF6B6B'); window.__ats.theme.setMode('dark');
if (import.meta.env.DEV) {
  ;(window as any).__ats = (window as any).__ats || {}
  ;(window as any).__ats.theme = {
    setBrand: (hex: string) => _themeStore.setBrand(hex),
    setMode: (m: 'light' | 'dark' | 'auto') => _themeStore.setMode(m),
    reset: () => _themeStore.reset(),
    get: () => ({ brand: _themeStore.brandHex, mode: _themeStore.mode }),
  }
}

// Step 1: 同步快照恢复
try {
  const _accessToken = localStorage.getItem('accessToken') || localStorage.getItem('token')
  const _refreshToken = localStorage.getItem('refreshToken')
  const _userRaw = localStorage.getItem('user')
  if (_accessToken) {
    _userStore.setAccessToken(_accessToken)
  }
  if (_refreshToken) {
    _userStore.setRefreshToken(_refreshToken)
  }
  if (_userRaw) {
    _userStore.setUser(JSON.parse(_userRaw))
  }
} catch (e) {
  console.warn('[boot] localStorage rehydrate 失败, 清掉', e)
  _userStore.logout()
}

// Step 2: 服务端契约重调 (top-level await; Vite 5 + ESM 原生支持)
//         注意: 必须在 app.mount 之前 await, 否则 router guard 首次 nav 看到的还是 stale 快照
// 2026-09-15: 改用 ensureReady() —— 与路由守卫共享同一个 in-flight hydrate promise。
//   `app.use(router)` 会在 install 时触发首次导航，守卫路径可能已经先一步发起 hydrate；
//   用 ensureReady 而非直接 fetchMe，避免重复打 /me，也保证两者拿到同一份结果。
if (_userStore.accessToken) {
  await _userStore.ensureReady()
  // G43 品牌信息同步到管理后台：系统名称 / Logo / 浏览器 title + favicon
  await _brandStore.init()
}

// 2026-06-14: 全局 error 兜底, 避免任意外部模块 TDZ / unhandled rejection 让整个 app 白屏
app.config.errorHandler = (err, _instance, info) => {
  console.error('[Vue] 全局错误:', err, '\n组件信息:', info)
}
window.addEventListener('unhandledrejection', (event) => {
  console.error('[window] unhandled promise rejection:', event.reason)
})

// 2026-09-15: 路由安装下移到 hydrate 完成之后 —— 见文件上方 app.use(naivePlugin) 处的说明。
//   `app.use(router)` 会立刻触发首次导航（守卫读 user.roles），必须在 store 就绪后执行。
//   守卫内还有 ensureReady() 门闸兜底，两层保证 F5 / 直达 URL 不再误判 /forbidden。
app.use(router)

app.mount('#app')

// 2026-09-23: 启动系统升级检测（轮询线上 version.json，不一致时弹确认框由用户刷新）。
// 放在 mount 之后：应用已就绪，且避免初始加载期打扰。
startAppVersionWatcher()

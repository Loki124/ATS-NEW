import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios, { type AxiosResponse, type AxiosError } from 'axios'  // 2026-06-29: 全局 axios 拦截器需要
import App from './App.vue'
import router from './router'
import { naivePlugin } from './plugins/naive'
import { setupPermissionDirective } from './directives/permission'

// Naive UI —— 见 plugins/naive.ts (统一注册, 测试可复用)

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import './styles/tokens.css'
import './styles/glass.css'
import './styles/glass-modal.css' // T2.3: 模态/抽屉玻璃化扩展（n-modal-container / n-drawer 等）
import './index.css'

import { createDiscreteApi } from 'naive-ui'
// v2: 全局 toast（拦截器 + shortcuts 帮助面板共用）· 必须在 axios 拦截器之前声明
const _toast = createDiscreteApi(['message']).message

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
app.use(router)
app.use(naivePlugin)
// 元素级最小权限指令 v-permission (消费后端 /me 的 resource_code 列表)
setupPermissionDirective(app)

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
if (_userStore.accessToken) {
  await _userStore.fetchMe()
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

app.mount('#app')

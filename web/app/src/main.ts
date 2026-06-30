import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios, { type AxiosResponse, type AxiosError } from 'axios'  // 2026-06-29: 全局 axios 拦截器需要
import App from './App.vue'
import router from './router'

// Naive UI —— 必须显式注册（不像 antd 那样 app.use() 自动）
// 用 create() 把常用组件包成一个 plugin 一次性注册
import {
  create,
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLoadingBarProvider,
  NButton,
  NCard,
  NInput,
  NInputNumber,
  NSelect,
  NCheckbox,
  NCheckboxGroup,
  NRadio,
  NRadioGroup,
  NSwitch,
  NForm,
  NFormItem,
  NFormItemRow,
  NDataTable,
  NPageHeader,  // 2026-06-17: 注册 naive-ui 页面头组件 (ScrapedResumeList.vue 等使用)
  NTag,
  NSpace,
  NDivider,
  NEmpty,
  NSpin,
  NAvatar,
  NBadge,
  NText,
  NH1,
  NH2,
  NH3,
  NH4,
  NH5,
  NP,
  NIcon,
  NLayout,
  NLayoutHeader,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NTabs,
  NTabPane,
  NDropdown,
  NModal,
  NDrawer,
  NDrawerContent,
  NPopconfirm,
  NPopover,
  NTooltip,
  NDescriptions,
  NDescriptionsItem,
  NTree,
  NTreeSelect,
  NUpload,
  NUploadDragger,
  NSteps,
  NStep,
  NGrid,
  NGi,
  NGridItem,
  NDatePicker,
  NTimeline,
  NTimelineItem,
  NAlert,
  NScrollbar,
  NCollapse,
  NCollapseItem,
  NBackTop,
  NCarousel,
  NCarouselItem,
  NImage,
  NInputGroup,
  NStatistic,
  NList,
  NListItem,
  NThing,
  NSkeleton,
  NResult,
  NPagination,
  NRadioButton,
} from 'naive-ui'

import 'virtual:uno.css'
import '@unocss/reset/tailwind.css'
import './styles/tokens.css'
import './index.css'

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
      console.warn(
        `[API 404] 后端没实现这个 endpoint: ${url}\n` +
        `  → 这是 "后端 app 缺" 不是 "权限问题". 看报告: REPORT-2026-06-29-ats-complete.md §10`
      )
    } else if (status === 500) {
      console.error(`[API 500] 后端 bug: ${url}`, err?.response?.data)
    }
    return Promise.reject(err)
  }
)

const app = createApp(App)

const naive = create({
  components: [
    NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, NLoadingBarProvider,
    NButton, NCard, NInput, NInputNumber, NSelect,
    NCheckbox, NCheckboxGroup, NRadio, NRadioGroup, NSwitch,
    NForm, NFormItem, NFormItemRow,
    NDataTable, NTag, NSpace, NDivider, NEmpty, NSpin,
    NAvatar, NBadge, NText,
    NH1, NH2, NH3, NH4, NH5, NP, NIcon,
    NLayout, NLayoutHeader, NLayoutSider, NLayoutContent,
    NMenu, NTabs, NTabPane, NDropdown,
    NModal, NDrawer, NDrawerContent,
    NPopconfirm, NPopover, NTooltip,
    NDescriptions, NDescriptionsItem,
    NTree, NTreeSelect,
    NUpload, NUploadDragger,
    NSteps, NStep,
    NGrid, NGi, NGridItem,
    NDatePicker,
    NTimeline, NTimelineItem,
    NAlert, NScrollbar,
    NCollapse, NCollapseItem,
    NBackTop, NCarousel, NCarouselItem,
    NImage, NInputGroup,
    NStatistic,
    NList, NListItem, NThing,
    NSkeleton, NResult,
    NPagination, NRadioButton,
  ],
})

app.use(createPinia())
app.use(router)
app.use(naive)

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
const _userStore = useUserStore()

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
}

// 2026-06-14: 全局 error 兜底, 避免任意外部模块 TDZ / unhandled rejection 让整个 app 白屏
app.config.errorHandler = (err, _instance, info) => {
  console.error('[Vue] 全局错误:', err, '\n组件信息:', info)
}
window.addEventListener('unhandledrejection', (event) => {
  console.error('[window] unhandled promise rejection:', event.reason)
})

app.mount('#app')

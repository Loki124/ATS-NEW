/**
 * 统一 HTTP 客户端（P1-2 收敛）
 *
 * 背景：api/ 下 40+ 文件各自 axios.create 独立实例并手写 token 拦截器，
 * X-Recruit-Type 原由 main.ts 全局 axios.create 包装统一注入；该包装已于 2026-09-29 移除（P1-2 收尾），
 * 现统一由本拦截器注入。
 * 现收敛为：一个共享 `api` 单例 + 一个 `createApi(opts)` 工厂（供特殊 timeout / baseURL 场景）。
 *
 * 拦截器在这里集中注入：
 *  - Authorization: 从 localStorage 的 accessToken / token 读取（幂等）
 *  - X-Recruit-Type: 运行时读取 useSystemStore().current（'social'|'campus'），切换系统后下一次请求即生效
 *
 * 行为与原各实例 + 已移除的 main.ts 包装等价；main.ts 全局 axios.create 包装作为兜底已于 2026-09-29 移除。
 */
import axios, { type AxiosInstance } from 'axios'
import { createDiscreteApi } from 'naive-ui'
import config from '../config'
import { useSystemStore } from '../stores/system'
import { useUserStore } from '../stores/user'

// 2026-10-08 (#30): 404/500 全局提示原挂在 main.ts 的「默认 axios 实例」拦截器上，
// 但全仓 40+ 业务请求都走本文件的 createApi() 实例, 默认实例从不用于业务请求 →
// 那些 404(后端缺实现)/500(后端 bug) 提示从未生效。现把处理收到本实例的响应拦截器里。
const _toast = createDiscreteApi(['message']).message

export interface CreateApiOptions {
  baseURL?: string
  timeout?: number
}

function injectAuthHeaders(cfg: any): any {
  cfg.headers = cfg.headers || {}
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`
  }
  const sys = useSystemStore()
  if (sys && sys.current) {
    cfg.headers['X-Recruit-Type'] = sys.current
  }
  return cfg
}

/**
 * P2 防御性响应归一（A2 过渡期兜底，非完整信封化）：
 * 对 2xx 且为裸 JSON 对象的响应，若其尚未带 success 字段，则补 success/message/code 元数据，
 * 使其可被「信封感知 / 容错」消费路径统一对待。
 *
 * 设计约束（A2）：
 *  - 不搬迁 payload：裸对象的根即原 payload，仅附加元数据，绝不把 payload 塞进 .data。
 *  - 不自动 reject success:false：success:false 信封由调用方按业务判定，拦截器保持透传。
 *  - 已带 success 的信封响应（成功/失败）一律 no-op，避免重复写入。
 *  - 数组 / Blob / 原始值响应不处理（仅对象）。
 *
 * 完整「裸→包信封 + payload 搬迁」须在剩余 ~26 个裸后端 ViewSet 信封化后落地，
 * 否则会击穿其对应的 FE 裸消费点（见 P1-3 收敛说明）。
 */
function normalizeEnvelopeMeta(resp: any): any {
  const d = resp?.data
  if (
    d &&
    typeof d === 'object' &&
    !Array.isArray(d) &&
    !('success' in d)
  ) {
    d.success = true
    d.message = ''
    d.code = 0
  }
  return resp
}

/**
 * P2：401 自动刷新重试（与 auth.ts 同语义，收敛到共享客户端）。
 *
 * 背景：P1-2 把 Authorization / X-Recruit-Type 注入收敛到本模块，但 401→刷新重试逻辑
 * 当时只留在 auth.ts 的独立实例上；metrics.ts 等 40+ 文件走本共享 `api`，
 * 一旦 access token 过期，PATCH/POST 等写操作直接 401 且无重试（表现为「保存模板报 401」）。
 * 现把刷新重试也收敛到本模块，所有 createApi() 实例共用同一刷新状态机（模块级 isRefreshing）。
 */
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}
function clearRefreshSubscribers() {
  refreshSubscribers = []
}

function handleAuthFailure(message: string) {
  if (isRefreshing) return
  isRefreshing = true
  clearRefreshSubscribers()
  const userStore = useUserStore()
  userStore.logout()
  if (window.location.pathname !== '/login') {
    console.warn('[auth]', message)
    window.location.href = '/login'
  }
  isRefreshing = false
}

/**
 * 响应错误拦截：命中 401 时尝试用 refresh token 换新 access 并重试原请求；
 * 无 refresh / 刷新失败 / 已是登录或刷新请求本身 → 走登出跳转。
 */
async function refreshOn401(inst: AxiosInstance, error: any): Promise<any> {
  const originalRequest = error.config as any
  const status = error.response?.status
  if (status !== 401 || !originalRequest) return Promise.reject(error)

  const reqPath = (originalRequest.url || '').split('?')[0]
  // 登录 / 刷新自身不重试，避免循环
  if (reqPath.endsWith('/auth/login/') || reqPath.endsWith('/auth/refresh/')) {
    return Promise.reject(error)
  }

  const userStore = useUserStore()
  const refreshToken = userStore.refreshToken || localStorage.getItem('refreshToken')
  if (refreshToken && !originalRequest._retry) {
    originalRequest._retry = true
    if (!isRefreshing) {
      isRefreshing = true
      try {
        const { data } = await axios.post(
          `${config.api.baseUrl}/auth/refresh/`,
          { refresh: refreshToken },
          { headers: { 'Content-Type': 'application/json' } },
        )
        const newAccess = data?.data?.access || data?.access
        userStore.setAccessToken(newAccess)
        onTokenRefreshed(newAccess)
        isRefreshing = false
        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return inst(originalRequest)
      } catch (refreshErr) {
        clearRefreshSubscribers()
        isRefreshing = false
        handleAuthFailure('登录状态已失效，请重新登录')
        return Promise.reject(refreshErr)
      }
    }
    // 已有刷新在进行：排队等结果后再重试
    return new Promise((resolve) => {
      subscribeTokenRefresh((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        resolve(inst(originalRequest))
      })
    })
  }

  handleAuthFailure('登录状态已失效，请重新登录')
  return Promise.reject(error)
}

export function createApi(opts: CreateApiOptions = {}): AxiosInstance {
  const inst = axios.create({
    baseURL: opts.baseURL ?? config.api.baseUrl,
    timeout: opts.timeout ?? 15000,
    headers: { 'Content-Type': 'application/json' },
  })
  inst.interceptors.request.use(injectAuthHeaders as any)
  // 成功态信封归一；失败态：404/500 提示 + 401 刷新重试
  inst.interceptors.response.use(normalizeEnvelopeMeta as any, (e: any) => {
    const status = e?.response?.status
    const url = e?.config?.url ?? '<unknown>'
    if (status === 404) {
      // 后端 endpoint 不存在 (开发期常见) —— 这是 "后端 app 缺" 不是 "权限问题"
      console.warn(
        `[API 404] 后端没实现这个 endpoint: ${url}\n` +
        `  → 这是 "后端 app 缺" 不是 "权限问题". 看报告: REPORT-2026-06-29-ats-complete.md §10`
      )
    } else if (status === 500) {
      console.error(`[API 500] 后端 bug: ${url}`, e?.response?.data)
      _toast.error('服务繁忙，请稍后重试')
    }
    return refreshOn401(inst, e)
  })
  return inst
}

/** 共享单例：baseURL=config.api.baseUrl, timeout=15000 */
export const api: AxiosInstance = createApi()

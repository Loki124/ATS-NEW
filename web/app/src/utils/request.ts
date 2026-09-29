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
import config from '../config'
import { useSystemStore } from '../stores/system'

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

export function createApi(opts: CreateApiOptions = {}): AxiosInstance {
  const inst = axios.create({
    baseURL: opts.baseURL ?? config.api.baseUrl,
    timeout: opts.timeout ?? 15000,
    headers: { 'Content-Type': 'application/json' },
  })
  inst.interceptors.request.use(injectAuthHeaders as any)
  return inst
}

/** 共享单例：baseURL=config.api.baseUrl, timeout=15000 */
export const api: AxiosInstance = createApi()

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

export function createApi(opts: CreateApiOptions = {}): AxiosInstance {
  const inst = axios.create({
    baseURL: opts.baseURL ?? config.api.baseUrl,
    timeout: opts.timeout ?? 15000,
    headers: { 'Content-Type': 'application/json' },
  })
  inst.interceptors.request.use(injectAuthHeaders as any)
  inst.interceptors.response.use(normalizeEnvelopeMeta as any)
  return inst
}

/** 共享单例：baseURL=config.api.baseUrl, timeout=15000 */
export const api: AxiosInstance = createApi()

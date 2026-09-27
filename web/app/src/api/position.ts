/**
 * 职位管理 API 客户端 — 真实后端端点 (apps/position)
 *
 * 全部走真实 API，无任何 mock 兜底；端点契约见 apps/position/views.py:
 *   GET    /positions/                列表(分页 {success,data,pagination})
 *   POST   /positions/                创建(返回 PositionDetailSerializer 完整数据)
 *   GET    /positions/{id}/           详情
 *   PATCH  /positions/{id}/           局部更新
 *   DELETE /positions/{id}/           软删除(perform_destroy 置 deleted_at)
 *   POST   /positions/{id}/transition/ 状态机流转 {action}
 * 关联下拉数据:
 *   GET /departments/  GET /processes/  GET /users  GET /demands/
 */

import axios from 'axios'
import config from '../config'
import { extractApiError } from './dynamic-field'

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// ===== 类型 =====

export interface PositionRow {
  id: string
  code: string
  title: string
  department: string
  departmentName: string
  demand?: string | null
  demandName?: string
  process: string
  processName?: string
  priority?: string
  state: string
  stateDisplay: string
  headcount: number
  filledCount: number
  owner?: string
  ownerName?: string
  hiringManager?: string | number
  hiringManagerName?: string
  salaryMin?: string | number | null
  salaryMax?: string | number | null
  location?: string
  createdAt: string
  description?: string
}

export interface PositionPayload {
  title: string
  department: string
  process: string
  priority?: string
  headcount: number
  owner: string | number
  hiringManager: string | number
  demand?: string | null
  salaryMin?: number | null
  salaryMax?: number | null
  location?: string
  description?: string
}

interface ApiListResponse {
  success?: boolean
  data?: unknown[] | { list?: unknown[] }
}

function extractList<T>(raw: unknown): T[] {
  if (!raw) return []
  const r = raw as ApiListResponse
  if (Array.isArray(r?.data)) return r.data as T[]
  if (r?.data && Array.isArray((r.data as { list?: unknown[] }).list)) {
    return (r.data as { list: unknown[] }).list as T[]
  }
  return []
}

function extractOne<T>(raw: unknown): T | null {
  const r = raw as { data?: T }
  return r?.data ?? null
}

// ===== 职位 CRUD =====

export async function listPositions(params?: Record<string, unknown>): Promise<PositionRow[]> {
  try {
    const { data } = await api.get('/positions/', { params: { pageSize: 200, ...params } })
    return extractList<PositionRow>(data)
  } catch {
    return []
  }
}

export async function createPosition(payload: PositionPayload): Promise<PositionRow> {
  const { data } = await api.post('/positions/', payload)
  return extractOne<PositionRow>(data) as PositionRow
}

export async function updatePosition(id: string, payload: Partial<PositionPayload>): Promise<PositionRow> {
  const { data } = await api.patch(`/positions/${id}/`, payload)
  return extractOne<PositionRow>(data) as PositionRow
}

export async function deletePosition(id: string): Promise<void> {
  await api.delete(`/positions/${id}/`)
}

export async function transitionPosition(id: string, action: string): Promise<PositionRow> {
  const { data } = await api.post(`/positions/${id}/transition/`, { action })
  return extractOne<PositionRow>(data) as PositionRow
}

// ===== 关联下拉数据 =====

export interface Option { label: string; value: string | number }

export async function listDepartments(): Promise<Option[]> {
  try {
    const { data } = await api.get('/departments/', { params: { pageSize: 200 } })
    return extractList<{ id: string; name: string }>(data).map((d) => ({ label: d.name, value: d.id }))
  } catch {
    return []
  }
}

export async function listProcesses(): Promise<Option[]> {
  try {
    const { data } = await api.get('/processes/', { params: { pageSize: 200 } })
    return extractList<{ id: string; name: string }>(data).map((p) => ({ label: p.name, value: p.id }))
  } catch {
    return []
  }
}

export async function listDemands(): Promise<Option[]> {
  try {
    const { data } = await api.get('/demands/', { params: { pageSize: 200 } })
    return extractList<{ id: string; code: string; title: string }>(data).map((d) => ({
      label: `${d.code} - ${d.title}`,
      value: d.id,
    }))
  } catch {
    return []
  }
}

export async function listUsers(): Promise<Option[]> {
  try {
    const { data } = await api.get('/users', { params: { pageSize: 200 } })
    return extractList<{ id: string | number; realName?: string; username?: string }>(data).map((u) => ({
      label: u.realName || u.username || String(u.id),
      value: u.id,
    }))
  } catch {
    return []
  }
}

export { extractApiError }
export default { listPositions, createPosition, updatePosition, deletePosition, transitionPosition, listDepartments, listProcesses, listDemands, listUsers, extractApiError }

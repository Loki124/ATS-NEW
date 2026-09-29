/**
 * 校招专属功能（校园大使 + 宣讲会）API。
 * 后端挂 /api/v1/campus-recruit/，camelCase 自动转换。
 *
 * 响应契约（与 campusControl.ts 同源）：
 *  - 列表（GET 集合）→ 信封 { success, data:[...], pagination }
 *  - 新建/更新（POST/PUT 单对象）→ 裸 camelCase 对象
 *  - restore（POST 单对象）→ 信封 { success, id }
 *  - 配置端点（GET/PUT）→ 信封 { success, data }，data 为自由 JSON 配置 dict
 *  - 删除 → 204（无响应体）
 *
 * 隔离：所有请求经 main.ts 全局拦截器自动注入 X-Recruit-Type: campus，
 * 后端 ScopeQuerysetMixin 据此按 recruit_type='campus' 硬分区（读侧过滤 + 写侧权威注入）。
 */
import { api } from '../utils/request'

import config from '../config'

/* ============================ 领域类型 ============================ */
export type AmbassadorStatus = 'active' | 'pending' | 'inactive'
export type SessionType = 'offline' | 'online' | 'hybrid'
export type SessionStatus = 'planned' | 'ongoing' | 'ended' | 'cancelled'

export const AMBASSADOR_STATUS_LABELS: Record<AmbassadorStatus, string> = {
  active: '已激活',
  pending: '待审核',
  inactive: '已停用',
}

export const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  offline: '线下',
  online: '线上',
  hybrid: '线上线下结合',
}

export const SESSION_STATUS_LABELS: Record<SessionStatus, string> = {
  planned: '已排期',
  ongoing: '进行中',
  ended: '已结束',
  cancelled: '已取消',
}

/** 校园大使。 */
export interface CampusAmbassador {
  id: string
  school: string
  name: string
  region: string
  status: AmbassadorStatus
  phone: string
  note: string
  recruitType: string
  createdAt?: string
  updatedAt?: string
}

/** 宣讲会。startTime/endTime 为 ISO 字符串（null = 未排期）。 */
export interface CampusSession {
  id: string
  title: string
  school: string
  sessionType: SessionType
  startTime: string | null
  endTime: string | null
  venue: string
  onlineLink: string
  capacity: number | null
  status: SessionStatus
  note: string
  recruitType: string
  createdAt?: string
  updatedAt?: string
}

export interface AmbassadorInput {
  school: string
  name: string
  region?: string
  status?: AmbassadorStatus
  phone?: string
  note?: string
}

export interface SessionInput {
  title: string
  school?: string
  sessionType?: SessionType
  startTime?: string | null
  endTime?: string | null
  venue?: string
  onlineLink?: string
  capacity?: number | null
  status?: SessionStatus
  note?: string
}

export interface Pagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface PageResult<T> {
  rows: T[]
  pagination: Pagination
}

/* ============================ 工具 ============================ */
const listData = <T>(r: any): T[] => (r?.data?.data ?? []) as T[]

/* ============================ 校园大使 ============================ */
export const listAmbassadors = (params: { page?: number; pageSize?: number; search?: string } = {}) =>
  api
    .get('/campus-recruit/ambassadors/', { params: { page_size: 200, ...params } })
    .then((r) => ({ rows: listData<CampusAmbassador>(r), pagination: r.data.pagination as Pagination }))

export const createAmbassador = (payload: AmbassadorInput) =>
  api.post('/campus-recruit/ambassadors/', payload).then((r) => r.data as CampusAmbassador)

export const updateAmbassador = (id: string, payload: Partial<AmbassadorInput>) =>
  api.put(`/campus-recruit/ambassadors/${id}/`, payload).then((r) => r.data as CampusAmbassador)

export const deleteAmbassador = (id: string) =>
  api.delete(`/campus-recruit/ambassadors/${id}/`).then((r) => r.data)

export const restoreAmbassador = (id: string) =>
  api.post(`/campus-recruit/ambassadors/${id}/restore/`).then((r) => r.data as { success: boolean; id: string })

/* ============================ 宣讲会 ============================ */
export const listSessions = (params: { page?: number; pageSize?: number; search?: string } = {}) =>
  api
    .get('/campus-recruit/sessions/', { params: { page_size: 200, ...params } })
    .then((r) => ({ rows: listData<CampusSession>(r), pagination: r.data.pagination as Pagination }))

export const createSession = (payload: SessionInput) =>
  api.post('/campus-recruit/sessions/', payload).then((r) => r.data as CampusSession)

export const updateSession = (id: string, payload: Partial<SessionInput>) =>
  api.put(`/campus-recruit/sessions/${id}/`, payload).then((r) => r.data as CampusSession)

export const deleteSession = (id: string) => api.delete(`/campus-recruit/sessions/${id}/`).then((r) => r.data)

export const restoreSession = (id: string) =>
  api.post(`/campus-recruit/sessions/${id}/restore/`).then((r) => r.data as { success: boolean; id: string })

/* ============================ 模块启用开关配置 ============================ */
export interface ModuleConfig {
  enabled: boolean
  [key: string]: any
}

export const getAmbassadorConfig = () =>
  api.get('/campus-recruit/ambassadors/config/').then((r) => (r.data.data ?? {}) as ModuleConfig)

export const putAmbassadorConfig = (cfg: ModuleConfig) =>
  api.put('/campus-recruit/ambassadors/config/', cfg).then((r) => (r.data.data ?? {}) as ModuleConfig)

export const getSessionConfig = () =>
  api.get('/campus-recruit/sessions/config/').then((r) => (r.data.data ?? {}) as ModuleConfig)

export const putSessionConfig = (cfg: ModuleConfig) =>
  api.put('/campus-recruit/sessions/config/', cfg).then((r) => (r.data.data ?? {}) as ModuleConfig)

export default {
  listAmbassadors, createAmbassador, updateAmbassador, deleteAmbassador, restoreAmbassador,
  listSessions, createSession, updateSession, deleteSession, restoreSession,
  getAmbassadorConfig, putAmbassadorConfig, getSessionConfig, putSessionConfig,
}

import { api } from '../utils/request'

import config from '../config'

export interface IntegrationItem {
  id: string
  type: string
  typeDisplay: string
  name: string
  provider: string
  config: Record<string, any>
  fieldMapping: Record<string, any>
  isActive: boolean
  lastSyncAt: string | null
  createdAt: string
  updatedAt: string
}

export interface SyncLogItem {
  id: string
  config: string
  configName: string
  configProvider: string
  syncType: string
  status: string
  totalCount: number
  successCount: number
  failedCount: number
  errorMessage: string
  endpoint: string
  method: string
  direction: string
  durationMs: number | null
  createdAt: string
}

export async function listIntegrations(params?: Record<string, any>) {
  const { data } = await api.get('/integrations/', { params })
  return data
}
export async function createIntegration(payload: Record<string, any>) {
  const { data } = await api.post('/integrations/', payload)
  return data
}
export async function updateIntegration(id: string, payload: Record<string, any>) {
  const { data } = await api.put(`/integrations/${id}/`, payload)
  return data
}
export async function deleteIntegration(id: string) {
  await api.delete(`/integrations/${id}/`)
}
export async function testIntegration(id: string) {
  const { data } = await api.post(`/integrations/${id}/test/`)
  return data
}
export async function listSyncLogs(params?: Record<string, any>) {
  const { data } = await api.get('/integrations/sync-logs/', { params })
  return data
}

export interface BackgroundCheckOrderEventItem {
  id: string
  order: string
  orderNumber: string
  fromStatus: number | null
  toStatus: number
  fromStatusDisplay: string
  toStatusDisplay: string
  riskLevel: number | null
  reportUrl: string
  completionTime: string | null
  source: string
  isLegalTransition: boolean
  rawPayload: Record<string, any> | null
  createdAt: string
}

export interface BackgroundCheckOrderItem {
  id: string
  config: string
  configName: string
  configProvider: string
  orderNumber: string
  candidateId: string
  candidateName: string
  channel: string
  channelDisplay: string
  remark: string
  isSupplementary: boolean
  parentOrderId: string
  bgSuggestions: Array<{ interviewer: string; interviewerName: string; suggestion: string; answer?: string }>
  status: number
  statusDisplay: string
  statusName: string
  riskLevel: number | null
  riskLevelDisplay: string
  reportUrl: string
  completionTime: string | null
  latestPayload: Record<string, any> | null
  createdAt: string
  updatedAt: string
  events?: BackgroundCheckOrderEventItem[]
}

export async function listBackgroundCheckOrders(params?: Record<string, any>) {
  const { data } = await api.get('/background-check/orders/', { params })
  return data
}

export async function cancelBackgroundCheckOrder(id: string) {
  const { data } = await api.post(`/background-check/orders/${id}/cancel/`)
  return data
}

// ===== 候选人管理「发起背调」(供应商集成系统) =====
export interface BackgroundCheckSupplier {
  id: string
  name: string
  provider: string
  isSystemIntegrated?: boolean
  /** 来自 IntegrationConfig.bg_metadata（配置缺失则为 null，前端优雅降级不渲染） */
  deliveryRank?: number | null
  deliveryTag?: string | null
  usageRank?: number | null
  usageTag?: string | null
}

/** 背调人信息（弹窗两分支共享） */
export interface BgCandidate {
  id: string
  name: string
  phone: string
  idCardNo?: string
  email?: string
  position?: string
  expectedOnboardingDate?: string | null
}

/** 套餐/检查项（标准化形态） */
export interface BgPackage {
  token: string
  name: string
  workdays: number | null
  features: string[]
}

/** 背调建议（按面试官聚合） */
export interface BgSuggestion {
  interviewer: string
  interviewerName: string
  interviewId: string
  suggestion: string
  submittedAt: string
}

export async function listBackgroundCheckSuppliers(mode?: 'self_order' | 'system_order'): Promise<BackgroundCheckSupplier[]> {
  const { data } = await api.get('/background-check/orders/suppliers/', { params: mode ? { mode } : {} })
  const body = (data || {}) as any
  return body.data ?? []
}

export async function getBackgroundCheckProducts(configId: string): Promise<{ success: boolean; message?: string; data: { source: string; packages: BgPackage[] } }> {
  const { data } = await api.get('/background-check/orders/products/', { params: { config_id: configId } })
  const body = (data || {}) as any
  const d = body.data ?? {}
  return { success: !!body.success, message: body.message, data: { source: d.source ?? '', packages: d.packages ?? [] } }
}

export async function createBackgroundCheckOrder(payload: {
  candidate_id: string
  candidate_name?: string
  phone?: string
  config_id: string
  items: string[]
  channel?: string
  remark?: string
  parent_order_id?: string
  bg_suggestions?: any[]
  has_existing_report?: boolean
  /** 下单分支：冗余存选中套餐名 */
  package_name?: string
  /** 下单分支：背调结果（一般空） */
  bg_result?: string
  /** 下单分支：是否可以联系候选人 */
  contactable?: boolean | null
  /** 背调人信息快照 */
  subject_snapshot?: Record<string, any>
  /** 预计入职日期（透传供应商 expect_entry_time） */
  expected_onboarding_date?: string
}): Promise<{ success: boolean; message?: string; data?: any }> {
  const { data } = await api.post('/background-check/orders/create-order/', payload)
  const body = (data || {}) as any
  return { success: !!body.success, message: body.message, data: body.data }
}

/** 已有报告上传 / 自主背调（步骤式弹窗「已有报告」分支） */
export async function uploadBackgroundCheckReport(payload: {
  candidate_id: string
  candidate_name?: string
  phone?: string
  report_url: string
  remark?: string
  answers?: Array<{ interviewer: string; answer: string }>
  bg_suggestions?: any[]
  parent_order_id?: string
  /** 图2 套餐名称 */
  package_name?: string
  /** 图2 背调供应商 */
  bg_provider?: string
  /** 图2 背调时间（ISO） */
  bg_time?: string
  /** 图2 背调结果（BGResult） */
  bg_result?: string
  /** 背调人信息快照 */
  subject_snapshot?: Record<string, any>
}): Promise<{ success: boolean; message?: string; data?: any }> {
  const { data } = await api.post('/background-check/orders/upload-report/', payload)
  const body = (data || {}) as any
  return { success: !!body.success, message: body.message, data: body.data }
}

/** 通用文件上传：POST /api/v1/media/upload/（multipart，字段名 file） */
export async function uploadMedia(file: File): Promise<{ id: string; name: string; url: string; size: number; contentType: string }> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/media/upload/', form, {
    headers: { 'Content-Type': undefined as unknown as string },
  })
  const body = (data || {}) as any
  const d = body.data ?? {}
  return {
    id: d.id ?? '',
    name: d.name ?? '',
    url: d.url ?? '',
    size: d.size ?? 0,
    contentType: d.contentType ?? d.content_type ?? '',
  }
}

/** 聚合某候选人来自各面试官的背调建议 */
export async function getBackgroundCheckSuggestions(candidateId: string): Promise<BgSuggestion[]> {
  const { data } = await api.get('/background-check/orders/bg-suggestions/', { params: { candidate_id: candidateId } })
  const body = (data || {}) as any
  return body.data ?? []
}

export default api

import axios from 'axios'
import config from '../config'

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

export default api

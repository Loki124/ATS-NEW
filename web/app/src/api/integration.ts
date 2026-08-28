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

export default api

/**
 * metrics.ts — 指标库 API 客户端（规则引擎指标层）
 *
 * 后端端点（baseURL = config.api.baseUrl = '/api/v1'，路径从 /metrics/... 起算）：
 *   GET|POST      /metrics/atomic-metrics/      原子指标 CRUD
 *   DELETE        /metrics/atomic-metrics/{id}/ （被引用时返回 400 + error）
 *   GET|POST      /metrics/derived-metrics/     派生指标 CRUD
 *   GET|POST      /metrics/templates/           指标模板 CRUD
 *   POST          /metrics/rules/execute/       一次性执行（不落库）
 *   GET           /metrics/operators/           运算符目录（复用 rule_engine 11 种）
 *   GET           /metrics/derived-funcs/       派生计算函数目录
 *   GET           /metrics/sample-data/         示例候选人数据
 *
 * 响应信封：{ success, data, pagination }；字段为 camelCase（drf-camel-case）。
 */
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

/** 解标准信封：裸数组/对象与 {success,data} 两种形态都兼容 */
function unwrap<T>(res: any): T {
  const body = res?.data
  if (body && typeof body === 'object' && 'success' in body && 'data' in body) {
    return body.data as T
  }
  return body as T
}

// ===== 类型 =====

export type MetricDataType = 'number' | 'string' | 'boolean' | 'date'

export interface AtomicMetric {
  id: string
  name: string
  sourcePath: string
  dataType: MetricDataType
  unit?: string
  description?: string
  status?: string
  templateCount?: number
}

export interface DerivedMetric {
  id: string
  name: string
  calcFunc: string
  basePath: string
  params?: Record<string, any>
  dataType: MetricDataType
  unit?: string
  description?: string
  status?: string
  templateCount?: number
}

export interface MetricTemplate {
  id: string
  name: string
  atomicMetric?: string | null
  derivedMetric?: string | null
  metricName?: string
  metricPath?: string
  metricKind?: 'atomic' | 'derived'
  dataType?: MetricDataType
  unit?: string
  operators: string[]
  status?: string
  description?: string
}

export interface OptionItem {
  value: string
  label: string
}

export interface DerivedFuncItem {
  name: string
  label: string
  description?: string
  paramsHint?: string
}

export interface ExecuteStep {
  index: number
  pass: boolean
  templateName: string
  operator: string
  operatorLabel: string
  actual: any
  expected: any
  detail: string
  error?: string
}

export interface ExecuteResult {
  pass: boolean
  logic: string
  steps: ExecuteStep[]
  summary: string
}

export interface ExecutePayload {
  conditions: {
    templateId: string
    operator: string
    value?: any
    meta?: Record<string, any>
  }[]
  logic?: 'AND' | 'OR'
  data: Record<string, any>
}

// ===== 端点 =====

export async function listAtomicMetrics(): Promise<AtomicMetric[]> {
  const res = await api.get('/metrics/atomic-metrics/')
  return unwrap<AtomicMetric[]>(res) ?? []
}

export async function createAtomicMetric(payload: Partial<AtomicMetric>): Promise<AtomicMetric> {
  const res = await api.post('/metrics/atomic-metrics/', payload)
  return unwrap<AtomicMetric>(res)
}

export async function deleteAtomicMetric(id: string): Promise<void> {
  await api.delete(`/metrics/atomic-metrics/${id}/`)
}

export async function listDerivedMetrics(): Promise<DerivedMetric[]> {
  const res = await api.get('/metrics/derived-metrics/')
  return unwrap<DerivedMetric[]>(res) ?? []
}

export async function createDerivedMetric(payload: Partial<DerivedMetric>): Promise<DerivedMetric> {
  const res = await api.post('/metrics/derived-metrics/', payload)
  return unwrap<DerivedMetric>(res)
}

export async function deleteDerivedMetric(id: string): Promise<void> {
  await api.delete(`/metrics/derived-metrics/${id}/`)
}

export async function listMetricTemplates(): Promise<MetricTemplate[]> {
  const res = await api.get('/metrics/templates/')
  return unwrap<MetricTemplate[]>(res) ?? []
}

export async function createMetricTemplate(payload: Partial<MetricTemplate>): Promise<MetricTemplate> {
  const res = await api.post('/metrics/templates/', payload)
  return unwrap<MetricTemplate>(res)
}

export async function deleteMetricTemplate(id: string): Promise<void> {
  await api.delete(`/metrics/templates/${id}/`)
}

export async function listOperators(): Promise<OptionItem[]> {
  const res = await api.get('/metrics/operators/')
  return unwrap<OptionItem[]>(res) ?? []
}

export async function listDerivedFuncs(): Promise<DerivedFuncItem[]> {
  const res = await api.get('/metrics/derived-funcs/')
  return unwrap<DerivedFuncItem[]>(res) ?? []
}

export async function getSampleData(): Promise<Record<string, any>> {
  const res = await api.get('/metrics/sample-data/')
  return unwrap<Record<string, any>>(res) ?? {}
}

/** 一次性执行规则（不落库），返回分步结果 */
export async function executeRule(payload: ExecutePayload): Promise<ExecuteResult> {
  const res = await api.post('/metrics/rules/execute/', payload)
  return unwrap<ExecuteResult>(res)
}

/** 真实候选人数据快照（供规则按 source_path 取值） */
export async function getCandidateSnapshot(candidateId: string): Promise<Record<string, any>> {
  const res = await api.get(`/metrics/candidates/${candidateId}/snapshot/`)
  return unwrap<Record<string, any>>(res) ?? {}
}

export interface CandidateFieldPath {
  path: string
  label: string
  dataType: string
  source: 'model' | 'dynamic'
}

/** 可引用的字段路径清单（配置原子指标时下拉选择，避免手填路径出错） */
export async function listCandidateFields(): Promise<CandidateFieldPath[]> {
  const res = await api.get('/metrics/candidate-fields/')
  return unwrap<CandidateFieldPath[]>(res) ?? []
}

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
import { api } from '../utils/request'

import config from '../config'

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

/** 派生函数的单个参数声明（前端据此渲染类型化输入，取代自由 JSON 文本） */
export interface ParamField {
  key: string
  label: string
  type: 'number' | 'string' | 'select' | 'boolean' | 'tags'
  options?: { value: string; label: string }[]
  default?: any
  required?: boolean
}

export interface DerivedFuncItem {
  name: string
  label: string
  description?: string
  paramsHint?: string
  /** 期望 base_path 解析出的 items 形状：list_periods / list_edu / date */
  inputKind?: string
  /** 计算结果类型：number / string / boolean / date */
  outputType?: string
  /** 结果单位（仅展示） */
  unit?: string
  /** 参数声明，驱动类型化参数输入 */
  paramSchema?: ParamField[]
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

// ===== 持久化规则 =====

export type MetricRuleScene = 'TALENT_POOL' | 'FILTER' | 'SCORING' | 'MANUAL'

export interface MetricRule {
  id: string
  name: string
  description?: string
  scene: MetricRuleScene
  conditions: {
    templateId: string
    operator: string
    value?: any
    meta?: Record<string, any>
  }[]
  logic: 'AND' | 'OR'
  /** T4：动作类型。VETO=必须满足(不满足即拒) / DEDUCT=优先考虑(仅记录不阻断) / BONUS=加分项 */
  actionType?: 'VETO' | 'DEDUCT' | 'BONUS'
  status?: string
  enabled: boolean
  conditionCount?: number
  createdAt?: string
}

/** 规则动作类型选项（供前端单选渲染） */
export const ACTION_TYPE_OPTIONS: { value: 'VETO' | 'DEDUCT' | 'BONUS'; labelKey: string }[] = [
  { value: 'VETO', labelKey: 'metrics.rule.action.veto' },
  { value: 'DEDUCT', labelKey: 'metrics.rule.action.deduct' },
  { value: 'BONUS', labelKey: 'metrics.rule.action.bonus' },
]

export async function listMetricRules(): Promise<MetricRule[]> {
  const res = await api.get('/metrics/rules/')
  return unwrap<MetricRule[]>(res) ?? []
}

export async function createMetricRule(payload: Partial<MetricRule>): Promise<MetricRule> {
  const res = await api.post('/metrics/rules/', payload)
  return unwrap<MetricRule>(res)
}

export async function updateMetricRule(id: string, payload: Partial<MetricRule>): Promise<MetricRule> {
  const res = await api.patch(`/metrics/rules/${id}/`, payload)
  return unwrap<MetricRule>(res)
}

export async function deleteMetricRule(id: string): Promise<void> {
  await api.delete(`/metrics/rules/${id}/`)
}

export async function getMetricRule(id: string): Promise<MetricRule> {
  const res = await api.get(`/metrics/rules/${id}/`)
  return unwrap<MetricRule>(res)
}

/** 启用/停用切换（幂等） */
export async function toggleMetricRule(id: string): Promise<{ id: string; enabled: boolean }> {
  const res = await api.post(`/metrics/rules/${id}/toggle/`)
  return unwrap<{ id: string; enabled: boolean }>(res)
}

/** 按已保存规则对真实候选人执行 */
export async function runMetricRule(id: string, candidateId: string): Promise<ExecuteResult> {
  const res = await api.post(`/metrics/rules/${id}/run/`, { candidateId })
  return unwrap<ExecuteResult>(res)
}

export interface SceneFilterResult {
  scene: string
  passedIds: string[]
  rejected: { candidateId: string; reason: string }[]
  /** 实际扫描条数 */
  scanned?: number
  /** 在库候选人总数 */
  total?: number
  /** 是否因同步上限被截断 —— true 时应改走异步拿全量结果 */
  truncated?: boolean
}

export interface FilterTaskStatus {
  status: 'pending' | 'running' | 'done' | 'not_found'
  progress?: number
  total?: number
  scene?: string
  passedIds?: string[]
  rejected?: { candidateId: string; reason: string }[]
}

/** 全量异步筛选（候选人超过同步扫描上限时使用） */
export async function filterBySceneAsync(
  scene: string,
  candidateIds?: string[],
): Promise<{ taskId: string }> {
  const res = await api.post('/metrics/rules/filter-async/', { scene, candidateIds })
  return unwrap<{ taskId: string }>(res)
}

export async function getFilterTaskStatus(taskId: string): Promise<FilterTaskStatus> {
  const res = await api.get('/metrics/rules/filter-status/', { params: { taskId } })
  return unwrap<FilterTaskStatus>(res)
}

/**
 * 按场景规则批量筛选候选人。
 * 不传 candidateIds 时后端自动扫描在库候选人（上限保护），返回 passedIds，
 * 前端再带 ids= 请求列表 —— 保证分页与总数正确。
 */
export async function filterByScene(
  scene: string,
  candidateIds?: string[],
): Promise<SceneFilterResult> {
  const res = await api.post('/metrics/rules/filter/', { scene, candidateIds })
  return unwrap<SceneFilterResult>(res)
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

/** 编辑（PATCH 部分更新）已存在的指标 */
export async function updateAtomicMetric(id: string, payload: Partial<AtomicMetric>): Promise<AtomicMetric> {
  const res = await api.patch(`/metrics/atomic-metrics/${id}/`, payload)
  return unwrap<AtomicMetric>(res)
}

export async function updateDerivedMetric(id: string, payload: Partial<DerivedMetric>): Promise<DerivedMetric> {
  const res = await api.patch(`/metrics/derived-metrics/${id}/`, payload)
  return unwrap<DerivedMetric>(res)
}

export async function updateMetricTemplate(id: string, payload: Partial<MetricTemplate>): Promise<MetricTemplate> {
  const res = await api.patch(`/metrics/templates/${id}/`, payload)
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

/** 指标定义（统一视图：原子指标 + 派生指标合并）。列与产品截图一致。 */
export interface MetricDefinition {
  id: string
  /** atomic=原子（对象路径） / derived=派生（参数化 Handler） */
  kind: 'atomic' | 'derived'
  name: string
  /** object_path=对象路径 / parametric_handler=参数化 Handler */
  valueMode: 'object_path' | 'parametric_handler'
  /** 原子=source_path，派生=base_path */
  dataSource: string
  /** 派生指标的参数（原子指标为空对象） */
  params: Record<string, any>
  /** 返回类型（指标数据类型）：number / string / boolean / date */
  returnType: string
  /** 是否枚举型（下拉 / 列表字段） */
  isEnum?: boolean
  /** 依据字段类型计算的能力白名单：支持的运算符取值列表 */
  supportedOperators: string[]
  status?: string
  description?: string
  calcFunc?: string
  /** 派生函数是否带参数（参数化 Handler） */
  isParametric?: boolean
  /** 是否由动态字段自动生成 */
  autoGenerated?: boolean
}

/** 统一「指标定义」列表（原子 + 派生合并，含取值方式与运算符白名单） */
export async function listMetricDefinitions(): Promise<MetricDefinition[]> {
  const res = await api.get('/metrics/definitions/')
  return unwrap<MetricDefinition[]>(res) ?? []
}

/** 可引用的字段路径清单（配置原子指标时下拉选择，避免手填路径出错） */
export async function listCandidateFields(): Promise<CandidateFieldPath[]> {
  const res = await api.get('/metrics/candidate-fields/')
  return unwrap<CandidateFieldPath[]>(res) ?? []
}

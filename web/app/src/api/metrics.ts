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

export interface MetricTemplateParamConfig {
  min?: number | null
  max?: number | null
  step?: number | null
  prefix?: string
  suffix?: string
  allOption?: boolean
}

export interface MetricTemplateValueSegment {
  min: number | null
  max: number | null
  step?: number | null
  label?: string
}

export interface MetricTemplateValueDomain {
  segments?: MetricTemplateValueSegment[]
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
  /** PRD 指标模板配置：参数范围/步长/显示 */
  paramConfig?: MetricTemplateParamConfig
  /** PRD 指标模板配置：值域分段 */
  valueDomain?: MetricTemplateValueDomain
  /** 枚举型指标的允许取值列表 */
  paramEnums?: string[]
  /** 是否允许为空 */
  paramAllowNull?: boolean
  status?: string
  description?: string
  /** LIFE-1：当前版本号（语义变更自增，永不复用） */
  version?: number
  /** LIFE-1：版本历史条数（= version_count 属性） */
  versionCount?: number
}

/** LIFE-1：指标模板版本快照（只读，不可经 API 增删改） */
export interface TemplateVersion {
  id: string
  templateId: string
  version: number
  snapshot: Record<string, any>
  changedFields: string[]
  changeKind: 'create' | 'update' | 'rollback' | 'import'
  changeNote: string
  createdAt: string
  createdBy?: string | null
}

export interface OptionItem {
  value: string
  label: string
}

// ===== LIFE-2：指标模板禁用/删除前的受影响规则清单（事前披露 + 确认闸门） =====

/** 进入条件（ORM 路径）引用项 */
export interface AffectedEntryCondition {
  ruleId: string
  ruleName: string
  ruleStatus: string
  expression: string
  itemId: string
  operator: string
  value: any
  processId: string
  processName: string
  stageId: string
  stageName: string
}

/** 自动跳过/归档（JSON 路径）引用项 */
export interface AffectedStageRule {
  ruleType: 'skip' | 'archive'
  stageRuleId: string
  ruleId: string
  ruleName: string
  ruleEnabled: boolean
  itemId: number
  operator: string
  value: any
  processId: string
  processName: string
  stageId: string
  stageName: string
}

/** 受影响规则清单总结构 */
export interface TemplateAffectedRules {
  templateId: string
  templateName: string
  templateStatus: string
  total: number
  entryConditions: AffectedEntryCondition[]
  stageRules: AffectedStageRule[]
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
  /** 关联需求（FK，允许为空） */
  demandId?: string | null
  /** 关联职位（FK，允许为空） */
  positionId?: string | null
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

export async function listDerivedMetrics(): Promise<DerivedMetric[]> {
  const res = await api.get('/metrics/derived-metrics/')
  return unwrap<DerivedMetric[]>(res) ?? []
}

/** 更新派生指标（如修改 params.recent_n 切换「全部平均 / 最近N段平均」） */
export async function updateDerivedMetric(id: string, payload: Partial<DerivedMetric>): Promise<DerivedMetric> {
  const res = await api.patch(`/metrics/derived-metrics/${id}/`, payload)
  return unwrap<DerivedMetric>(res)
}

export async function listMetricTemplates(): Promise<MetricTemplate[]> {
  const res = await api.get('/metrics/templates/')
  return unwrap<MetricTemplate[]>(res) ?? []
}

export async function createMetricTemplate(payload: Partial<MetricTemplate>): Promise<MetricTemplate> {
  const res = await api.post('/metrics/templates/', payload)
  return unwrap<MetricTemplate>(res)
}

/** 编辑（PATCH 部分更新）已存在的指标模板 */
export async function updateMetricTemplate(id: string, payload: Partial<MetricTemplate>): Promise<MetricTemplate> {
  const res = await api.patch(`/metrics/templates/${id}/`, payload)
  return unwrap<MetricTemplate>(res)
}

export async function deleteMetricTemplate(id: string): Promise<void> {
  await api.delete(`/metrics/templates/${id}/`)
}

/**
 * LIFE-2：禁用/删除前枚举引用某指标模板的全部规则（进入条件 ORM + 跳过/归档 JSON）。
 * 后端经 drf-camel-case 返回 camelCase；此处按 camelCase 字段名接收。
 */
export async function getTemplateAffectedRules(id: string): Promise<TemplateAffectedRules> {
  const res = await api.get(`/metrics/templates/${id}/affected-rules/`)
  return unwrap<TemplateAffectedRules>(res)
}

/**
 * LIFE-1：拉取某指标模板的版本历史（倒序快照列表）。
 * 后端经 drf-camel-case 返回 camelCase；此处按 camelCase 字段名接收。
 */
export async function listTemplateVersions(templateId: string): Promise<TemplateVersion[]> {
  const res = await api.get(`/metrics/templates/${templateId}/versions/`)
  return unwrap<TemplateVersion[]>(res) ?? []
}

/**
 * LIFE-1：将某指标模板回滚到指定历史版本（POST，body {version_no}）。
 * 成功后模板 version+1 并追加一条 kind='rollback' 快照；缺失版本 -> 404、引用指标失效 -> 400。
 */
export async function rollbackTemplateVersion(templateId: string, versionNo: number): Promise<MetricTemplate> {
  const res = await api.post(`/metrics/templates/${templateId}/versions/rollback/`, {
    version_no: versionNo,
  })
  return unwrap<MetricTemplate>(res)
}

export async function listOperators(): Promise<OptionItem[]> {
  const res = await api.get('/metrics/operators/')
  return unwrap<OptionItem[]>(res) ?? []
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
  /** 出参单位（如 岁 / 月 / 元） */
  unit?: string
  /** 是否枚举型（下拉 / 列表字段） */
  isEnum?: boolean
  /** 入参类型：discrete=离散 / continuous=连续（PRD 指标定义列） */
  paramType?: 'discrete' | 'continuous'
  /** 依据字段类型计算的能力白名单：支持的运算符取值列表 */
  supportedOperators: string[]
  /** 枚举型指标的出参候选值（isEnum 为 true 时非空） */
  enumValues?: string[]
  description?: string
  calcFunc?: string
  /** 派生函数是否带参数（参数化 Handler） */
  isParametric?: boolean
  /** 派生函数的参数声明（前端据此渲染类型化参数编辑，如 recent_n） */
  paramSchema?: ParamField[]
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

// ===== 指标模板导入 / 导出 =====

export type TemplateImportMode = 'skip' | 'update' | 'error'

export interface TemplateImportResult {
  /** 新建条数 */
  created: number
  /** 更新条数 */
  updated: number
  /** 跳过条数 */
  skipped: number
  /** 失败条数 */
  failed: number
  /** 错误明细（人话） */
  errors: string[]
  /** 失败错误报告（xlsx，base64）；仅在存在解析/校验错误时有值 */
  errorFile?: string | null
}

/**
 * 导入失败专用错误：携带后端返回的错误报告（errors + errorFile），
 * 便于调用方在 catch 中展示明细并下载错误报告。
 */
export class TemplateImportError extends Error {
  report: TemplateImportResult
  constructor(report: TemplateImportResult) {
    super((report.errors || []).join('；') || '导入失败')
    this.name = 'TemplateImportError'
    this.report = report
  }
}

/** 导出全部指标模板为 xlsx / csv（文件流，前端负责触发下载）。 */
export async function exportMetricTemplates(format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
  const res = await api.get('/metrics/templates/export/', {
    params: { file_format: format },
    responseType: 'blob',
  })
  return res.data as Blob
}

/** 下载指标模板导入模板（含表头 + 示例 + 填写说明）。 */
export async function downloadTemplateTemplate(format: 'xlsx' | 'csv' = 'xlsx'): Promise<Blob> {
  const res = await api.get('/metrics/templates/template/', {
    params: { file_format: format },
    responseType: 'blob',
  })
  return res.data as Blob
}

/**
 * 批量导入指标模板（multipart/form-data：file + mode）。
 *
 * 成功（2xx）：后端返回 {success, data:{created,updated,skipped,failed,errors}}。
 * 失败（4xx，含解析/校验错误）：后端返回 {success:false, data:{errors, errorFile}}，
 * 抛出 TemplateImportError 并携带 report，调用方据此展示明细 / 下载错误报告。
 */
export async function importMetricTemplates(
  file: File,
  mode: TemplateImportMode = 'skip',
): Promise<TemplateImportResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('mode', mode)
  try {
    const res = await api.post('/metrics/templates/import/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const body = res.data
    const data = (body && typeof body === 'object' && 'data' in body ? body.data : body) as TemplateImportResult
    return data
  } catch (err: any) {
    const r = err?.response?.data
    if (r && r.data) {
      throw new TemplateImportError(r.data as TemplateImportResult)
    }
    throw err
  }
}

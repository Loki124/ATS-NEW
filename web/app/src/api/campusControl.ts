/**
 * 校招管控（人员比例管控系统）v2.4 API。
 * 后端挂 /api/v1/campus/，camelCase 自动转换。
 *
 * 响应契约：
 *  - 列表（GET 集合）→ 信封 { success, data:[...], pagination }
 *  - 新建/更新（POST/PUT 单对象）→ 裸 camelCase 对象
 *  - @action（ratio/plan/validate/batch）→ 信封 { success, data }（或 400 { success:false, detail }）
 *  - 删除 → 204
 *  - Decimal 字段（target）序列化为字符串，本封装统一转 number
 *
 * v2.4：
 *  - 取消上下限（lo/hi）配置，以 target 为管控上限。
 *  - 管控人数（年度 annualTarget + 12 个月度 monthlyTargets）承载于规则（ControlRule）上，
 *    不再有独立的 ControlHeadcount 表；人数规划的目标数据直接来自规则。
 *  - 适用范围（bu/position/level，全空 = 全局）是每条规则的独立属性；
 *    看板/规划展示全量（每条按自身适用范围计算）。
 *  - 规则新增 year 维度键（unique_together 含 year）。
 */
import { api } from '../utils/request'

/* ============================ 领域常量 ============================ */
export const DEPTS = ['能电BG', '三到BG', '综合BG', '醒电BG']
export const SCHOOLS = ['985', '211', '双一流', '其他']
export const MAJORS = ['工学', '其他']
export const SEXES = ['男', '女']
export const DIMS = ['院校标签', '专业标签', '性别'] as const
export const STRENGTH = ['硬约束', '软约束'] as const  // v2.9：原「仅提示」已合并至「软约束」（后端处理一致）
export const STATUS = ['在职', '在途Offer', '在途待入职', '候选池'] as const
export const POSITIONS = ['技术研发', '产品', '设计', '运营', '职能', '销售']
export const LEVELS = ['L1', 'L2', 'L3', 'L4', 'L5']
export const ALL_MONTHS = Array.from({ length: 12 }, (_, i) => `${i + 1}月`)
export const MONTHS = ALL_MONTHS

export type Dim = (typeof DIMS)[number]
export type Strength = (typeof STRENGTH)[number]

/* ============================ 类型定义 ============================ */
/** 适用范围（bu/position/level 全空 = 全局）。 */
export interface ScopeFilter {
  bu: string
  position: string
  level: string
}

export interface ControlDimension {
  id: string
  name: string
  code: string
  isActive: boolean
  createdAt?: string
  updatedAt?: string
}

export interface ControlIndicator {
  id: string
  dimension: string
  dimensionName: string
  name: string
  isActive: boolean
  createdAt?: string
  updatedAt?: string
}

/** 管控规则：自带适用范围、占比 target（管控上限）、以及该指标在该适用范围下的管控人数。 */
export interface ControlRule {
  id: string
  code: string // 规则编号（G + 4 位，自动补号）
  isActive: boolean // 是否启用
  bu: string
  position: string
  level: string
  dimension: string
  dimensionName: string
  indicator: string
  indicatorName: string
  year: number
  target: number // 0~1，占比管控上限
  strength: Strength
  annualTarget: number // 年度管控人数
  monthlyTargets: number[] // 12 个月度管控人数
  rolloverEnabled: boolean // v2.10：是否启用本月浮动目标（roll-over）
  createdByName?: string
  createdAt?: string
  updatedByName?: string
  updatedAt?: string
}

export interface Person {
  id: string
  code: string
  name: string
  bu: string
  school: string
  sex: string
  major: string
  month: string
  status: string
  expectedEntryDate: string | null
  actualEntryDate: string | null
  position: string
  level: string
  counted: boolean
}

export interface RatioRow {
  dimension: string
  indicator: string
  bu: string
  position: string
  level: string
  // —— 保留：占比视角（既有断言依赖） ——
  actual: number
  denom: number
  ratio: number
  target: number
  status: '正常' | '高于上限'
  strength: Strength
  // —— 新增：人数达成视角 ——
  annualTarget: number
  annualAchieved: number
  annualInProgress: number
  annualRate: number | null
  monthTarget: number
  monthAchieved: number
  monthInProgress: number
  monthRate: number | null
  // —— v2.10：本月浮动 4 字段（rolloverEnabled=False 时 monthRollover=0、monthAvailableTarget==monthTarget）——
  monthRollBase?: number
  monthRollActual?: number
  monthRollover: number
  monthAvailableTarget: number
}

export interface RatioResult {
  total: number
  rows: RatioRow[]
}

export interface ValidationCheck {
  dimension: string
  indicator: string
  bu: string
  position: string
  level: string
  strength: Strength
  ratio: number
  ratioStatus: '正常' | '高于上限'
  monthActual: number
  monthTarget: number
  countStatus: '本月达标' | '缺口未达成' | '未设目标'
}

export interface ValidationResult {
  verdict: '阻断提交' | '允许提交但需关注' | '通过'
  verdictLevel: 'block' | 'warn' | 'pass'
  checks: ValidationCheck[]
}

/* ============================ 工具 ============================ */
const num = (v: unknown): number => (v == null ? 0 : Number(v))
const listData = <T>(r: any): T[] => (r?.data?.data ?? []) as T[]

/* ============================ 维度 ============================ */
export const listDimensions = () =>
  api.get('/campus/dimensions/', { params: { page_size: 200 } }).then((r) => listData<ControlDimension>(r))
export const createDimension = (payload: { name: string; code?: string; isActive?: boolean }) =>
  api.post('/campus/dimensions/', payload).then((r) => (r.data?.data ?? r.data) as ControlDimension)
export const updateDimension = (id: string, payload: Partial<ControlDimension>) =>
  api.put(`/campus/dimensions/${id}/`, payload).then((r) => (r.data?.data ?? r.data) as ControlDimension)
export const deleteDimension = (id: string) => api.delete(`/campus/dimensions/${id}/`).then((r) => r.data)
export const restoreDimension = (id: string) => api.post(`/campus/dimensions/${id}/restore/`).then((r) => r.data)

/* ============================ 指标 ============================ */
export const listIndicators = (dimension?: string) =>
  api
    .get('/campus/indicators/', { params: { page_size: 200, ...(dimension ? { dimension } : {}) } })
    .then((r) => listData<ControlIndicator>(r))
export const createIndicator = (payload: { dimension: string; name: string; isActive?: boolean }) =>
  api.post('/campus/indicators/', payload).then((r) => (r.data?.data ?? r.data) as ControlIndicator)
export const updateIndicator = (id: string, payload: Partial<ControlIndicator>) =>
  api.put(`/campus/indicators/${id}/`, payload).then((r) => (r.data?.data ?? r.data) as ControlIndicator)
export const deleteIndicator = (id: string) => api.delete(`/campus/indicators/${id}/`).then((r) => r.data)
export const restoreIndicator = (id: string) => api.post(`/campus/indicators/${id}/restore/`).then((r) => r.data)

/* ============================ 规则 ============================ */
export interface RuleInput {
  bu: string
  position: string
  level: string
  dimension: string
  indicator: string
  year: number
  target: number // 0~1，占比管控上限
  strength: Strength
  annualTarget: number // 年度管控人数
  monthlyTargets: number[] // 12 个月度管控人数
  /** v2.10：是否启用本月浮动目标（roll-over）；缺省按 False 处理（v2.4 行为零回归） */
  rolloverEnabled?: boolean
}

const ruleToNum = (x: any): ControlRule => ({
  ...x,
  target: num(x.target),
  annualTarget: num(x.annualTarget),
  monthlyTargets: Array.isArray(x.monthlyTargets) && x.monthlyTargets.length === 12
    ? x.monthlyTargets.map((v: any) => Number(v))
    : Array(12).fill(0),
  // v2.10：浮动目标开关；后端 BooleanField 默认 False，转 boolean 统一前端口径
  rolloverEnabled: Boolean(x.rolloverEnabled),
})

/** 全部规则（每条自带适用范围 + 管控人数）。 */
export const listRules = () =>
  api.get('/campus/rules/', { params: { page_size: 200 } }).then((r) => listData<ControlRule>(r).map(ruleToNum))

export const createRule = (payload: RuleInput) =>
  api.post('/campus/rules/', payload).then((r) => ruleToNum(r.data?.data ?? r.data))
export const updateRule = (id: string, payload: Partial<RuleInput>) =>
  api.put(`/campus/rules/${id}/`, payload).then((r) => ruleToNum(r.data?.data ?? r.data))
export const deleteRule = (id: string) => api.delete(`/campus/rules/${id}/`).then((r) => r.data)

/** 复制规则：克隆出一条「未启用」副本（后端校验唯一键含 is_active，已存在未启用副本则 409）。 */
export const copyRule = (id: string) =>
  api.post(`/campus/rules/${id}/copy/`, {}).then((r) => ruleToNum(r.data))

/** 启用 / 停用规则（后端 toggle 端点：冲突启用返回 409，缺参返回 400）。 */
export const toggleRule = (id: string, isActive: boolean) =>
  api.post(`/campus/rules/${id}/toggle/`, { is_active: isActive }).then((r) => ruleToNum(r.data))

export interface RuleDraft {
  indicator: string
  target: number // 0~1
  strength: Strength
  monthlyTargets?: number[] // 12 个月度管控人数；未传时后端按年度目标均分
}

/** 批量保存某 (适用范围, 维度) 的全部规则，硬校验 100% 加和（保留供可选使用）。 */
export const batchSaveRules = (scope: ScopeFilter, dimension: string, rules: RuleDraft[]) =>
  api
    .post('/campus/rules/batch/', { bu: scope.bu ?? '', position: scope.position ?? '', level: scope.level ?? '', dimension, rules })
    .then((r) => r.data as { success: boolean; data: { saved: number } })

export interface BatchConfigPayload {
  bu: string
  position: string
  level: string
  dimension: string
  year: number
  totalTarget: number
  rules: RuleDraft[]
}

/** 批量配置规则 + 人数目标（v2.9 扁平模型）：每条规则独占「适用范围·维度·指标·年度」组合，target 恒为 1.0，不再校验占比之和=100%。 */
export const batchConfigRules = (payload: BatchConfigPayload) =>
  api
    .post('/campus/rules/with-targets/', payload)
    .then((r) => r.data as { success: boolean; data: { saved: number; totalTarget: number; year: number } })

/** 维度规则集编辑面：单条指标项。
 *  - target/strength：必填（占比管控上限 + 控制强度）
 *  - annualTarget/monthlyTargets：成对可选；都不传时由后端从旧规则继承以避免误清人数目标
 *    （与 set_rules 端点契约对齐）。
 */
export interface DimRuleSetItem {
  indicator: string
  target: number // 0~1
  strength: Strength
  /** 年度管控人数（整数 ≥ 0）。与 monthlyTargets 同传或同不传。 */
  annualTarget?: number
  /** 12 个月度管控人数，长度 12 的非负整数数组且 sum = annualTarget。 */
  monthlyTargets?: number[]
}

/**
 * 维度规则集保存（PUT /dimensions/{id}/rules/）。
 * 原子替换该 (适用范围, 维度, 年度) 下全部规则（v2.9 扁平模型：每条规则 target 恒为 1.0，不再校验占比之和=100%）；
 * 保留既有年度/月度人数目标（仅更新 target/strength）。对应「维度规则集编辑面」保存动作。
 */
export const saveDimensionRuleSet = (
  dimensionId: string,
  payload: {
    bu: string; position: string; level: string; year: number; rules: DimRuleSetItem[];
    /** 维度年度管控人数（各指标 annualTarget 加和须 == 此值，后端硬拦校验）。 */
    totalTarget: number;
    /** 编辑态「重定位」时传入原适用范围，后端据此删除旧 scope 规则集。未提供则按普通原子替换处理。 */
    original?: { bu: string; position: string; level: string; year: number };
  },
) => api.put(`/campus/dimensions/${dimensionId}/rules/`, payload).then((r) => r.data as { success: boolean; data: { saved: number } })

/* ============================ 规则导入 / 导出 ============================ */
/** 导出全部规则为 xlsx（浏览器直接下载）。 */
export const exportRules = () =>
  api
    .get('/campus/rules/export/', { responseType: 'blob' })
    .then((r) => triggerDownload(r.data, 'campus_rules_export.xlsx'))

/** 下载规则导入模板 xlsx。 */
export const downloadRuleTemplate = () =>
  api
    .get('/campus/rules/template/', { responseType: 'blob' })
    .then((r) => triggerDownload(r.data, 'campus_rules_template.xlsx'))

export interface RuleImportResult {
  success: boolean
  data: { groups: number; savedRules: number; errors: string[]; errorFile?: string | null }
}
/** 导入规则 xlsx 文件，返回成功/失败明细。
 * 业务校验错误（400）会被后端显式返回，这里设置 validateStatus 让 4xx 也进入 then 分支，
 * 便于前端展示详细的 errors 列表，而不是只弹一个 "Request failed with status code 400"。
 */
export const importRules = (file: File): Promise<RuleImportResult> => {
  const fd = new FormData()
  fd.append('file', file)
  return api
    .post('/campus/rules/import/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      validateStatus: (status) => status < 500,
    })
    .then((r) => r.data as RuleImportResult)
}

export function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

/* ============================ 指标导入 / 导出 ============================ */
export interface IndicatorImportResult {
  success: boolean
  data: {
    created: number
    updated: number
    skipped: number
    failed: number
    errors: string[]
    errorFile?: string | null
  }
}

/** 导出全部指标为 xlsx / csv（含完整字段：维度、指标名称、是否启用）。 */
export const exportIndicators = (format: 'xlsx' | 'csv' = 'xlsx') =>
  api
    .get('/campus/indicators/export/', {
      params: { file_format: format },
      responseType: 'blob',
    })
    .then((r) => triggerDownload(r.data, `campus_indicators_export.${format}`))

/** 下载指标导入模板 xlsx / csv。 */
export const downloadIndicatorTemplate = (format: 'xlsx' | 'csv' = 'xlsx') =>
  api
    .get('/campus/indicators/template/', {
      params: { file_format: format },
      responseType: 'blob',
    })
    .then((r) => triggerDownload(r.data, `campus_indicators_template.${format}`))

/**
 * 批量导入指标文件（xlsx / csv），mode=skip|update|error 控制重复项处理。
 * 业务校验错误（400）由后端显式返回，validateStatus 让 4xx 进入 then 分支便于展示明细。
 */
export const importIndicators = (
  file: File,
  mode: 'skip' | 'update' | 'error' = 'skip',
): Promise<IndicatorImportResult> => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('mode', mode)
  return api
    .post('/campus/indicators/import/', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      validateStatus: (status) => status < 500,
    })
    .then((r) => r.data as IndicatorImportResult)
}

/* ============================ 实时看板（全量，每条按自身适用范围） ============================ */
export const getRatio = () =>
  api.get('/campus/rules/ratio/').then((r) => r.data.data as RatioResult)

/* ============================ 录入校验 ============================ */
export const validateDraft = (
  year: number,
  draft: { bu: string; position?: string; level?: string; school: string; sex: string; major: string; month?: string },
) =>
  api
    .post('/campus/rules/validate/', draft, { params: { year } })
    .then((r) => r.data.data as ValidationResult)

/* ============================ 人员主数据 ============================ */
export interface ListPersonsParams {
  staffed?: boolean
  status?: string
  bu?: string
  position?: string
  level?: string
  school?: string
  sex?: string
  major?: string
  month?: string
  year?: number
  search?: string
}
export const listPersons = (params?: ListPersonsParams) => {
  const q: Record<string, unknown> = { page_size: 200 }
  if (params?.staffed) q.staffed = '1'
  if (params?.status) q.status = params.status
  if (params?.bu) q.bu = params.bu
  if (params?.position) q.position = params.position
  if (params?.level) q.level = params.level
  if (params?.school) q.school = params.school
  if (params?.sex) q.sex = params.sex
  if (params?.major) q.major = params.major
  if (params?.month) q.month = params.month
  if (params?.year) q.year = params.year
  if (params?.search) q.search = params.search
  return api.get('/campus/persons/', { params: q }).then((r) => listData<Person>(r))
}
export const upsertPerson = (p: Partial<Person> & { code: string; name: string; bu: string; school: string; sex: string; major: string; month: string; status: string }) => {
  const payload = {
    code: p.code, name: p.name, bu: p.bu, school: p.school, sex: p.sex, major: p.major,
    month: p.month, status: p.status,
    expected_entry_date: p.expectedEntryDate || null,
    actual_entry_date: p.actualEntryDate || null,
    position: p.position ?? '', level: p.level ?? '', counted: p.counted ?? true,
  }
  if (p.id) return api.put(`/campus/persons/${p.id}/`, payload).then((r) => (r.data?.data ?? r.data) as Person)
  return api.post(`/campus/persons/`, payload).then((r) => (r.data?.data ?? r.data) as Person)
}
export const deletePerson = (id: string) => api.delete(`/campus/persons/${id}/`).then((r) => r.data)
export const restorePerson = (id: string) => api.post(`/campus/persons/${id}/restore/`).then((r) => r.data)

export default {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, createRule, updateRule, deleteRule, copyRule, toggleRule, batchSaveRules, batchConfigRules,
  saveDimensionRuleSet,
  getRatio, validateDraft,
  listPersons, upsertPerson, deletePerson,
  exportRules, downloadRuleTemplate, importRules,
  exportIndicators, downloadIndicatorTemplate, importIndicators,
}

/**
 * 校招管控（人员比例管控系统）v2.2 API。
 * 后端挂 /api/v1/campus/，camelCase 自动转换。
 *
 * 响应契约：
 *  - 列表（GET 集合）→ 信封 { success, data:[...], pagination }
 *  - 新建/更新（POST/PUT 单对象）→ 裸 camelCase 对象
 *  - @action（ratio/plan/validate/batch）→ 信封 { success, data }（或 400 { success:false, detail }）
 *  - 删除 → 204
 *  - Decimal 字段（target/lo/hi）序列化为字符串，本封装统一转 number
 *
 * v2.2：适用范围（bu/position/level，全空 = 全局）是每条规则/目标的独立属性；
 *       看板/规划展示全量（每条按自身适用范围计算），不再有全局适用范围筛选。
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

/* ============================ 领域常量 ============================ */
export const DEPTS = ['能电BG', '三到BG', '综合BG', '醒电BG']
export const SCHOOLS = ['985', '211', '双一流', '其他']
export const MAJORS = ['工学', '其他']
export const SEXES = ['男', '女']
export const DIMS = ['院校标签', '专业标签', '性别'] as const
export const STRENGTH = ['硬约束', '软约束', '仅提示'] as const
export const STATUS = ['已入职', '已Offer', '候选池'] as const
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

export interface ControlRule {
  id: string
  bu: string
  position: string
  level: string
  dimension: string
  dimensionName: string
  indicator: string
  indicatorName: string
  target: number // 0~1
  lo: number
  hi: number
  strength: Strength
  createdByName?: string
  createdAt?: string
  updatedByName?: string
  updatedAt?: string
}

export interface ControlHeadcount {
  id: string
  bu: string
  position: string
  level: string
  indicator: string
  indicatorName: string
  dimensionName: string
  year: number
  annualTarget: number
  monthlyTargets: number[] // 长度 12
  createdAt?: string
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
  actual: number
  denom: number
  ratio: number
  target: number
  lo: number
  hi: number
  status: '正常' | '低于下限' | '高于上限'
  strength: Strength
}

export interface SumCheck {
  dimension: string
  bu: string
  position: string
  level: string
  sum: number
  ok: boolean
}

export interface RatioResult {
  total: number
  rows: RatioRow[]
  sumChecks: SumCheck[]
}

export interface PlanRow {
  dimension: string
  indicator: string
  bu: string
  position: string
  level: string
  strength: Strength
  onjob: number
  annualTarget: number
  annualGap: number
  monthTarget: number
  monthActual: number
  gap: number
  status: '本月达标' | '缺口未达成' | '未设目标'
}

export interface Kpi {
  total: number
  ruleCount: number
  warnCount: number
  hardViolationCount: number
  monthGap: number
}

export interface PlanResult {
  rows: PlanRow[]
  kpi: Kpi
  year: number
}

export interface ValidationCheck {
  dimension: string
  indicator: string
  bu: string
  position: string
  level: string
  strength: Strength
  ratio: number
  ratioStatus: '正常' | '低于下限' | '高于上限'
  monthActual: number
  monthTarget: number
  countStatus: '本月达标' | '缺口未达成' | '未设目标'
}

export interface ValidationResult {
  verdict: '❌ 阻断提交' | '⚠️ 允许提交但需关注' | '✅ 通过'
  checks: ValidationCheck[]
}

/* ============================ 工具 ============================ */
const num = (v: unknown): number => (v == null ? 0 : Number(v))
const listData = <T>(r: any): T[] => (r?.data?.data ?? []) as T[]

/* ============================ 维度 ============================ */
export const listDimensions = () =>
  api.get('/campus/dimensions/', { params: { page_size: 200 } }).then((r) => listData<ControlDimension>(r))
export const createDimension = (payload: { name: string; code?: string; isActive?: boolean }) =>
  api.post('/campus/dimensions/', payload).then((r) => r.data as ControlDimension)
export const updateDimension = (id: string, payload: Partial<ControlDimension>) =>
  api.put(`/campus/dimensions/${id}/`, payload).then((r) => r.data as ControlDimension)
export const deleteDimension = (id: string) => api.delete(`/campus/dimensions/${id}/`).then((r) => r.data)

/* ============================ 指标 ============================ */
export const listIndicators = (dimension?: string) =>
  api
    .get('/campus/indicators/', { params: { page_size: 200, ...(dimension ? { dimension } : {}) } })
    .then((r) => listData<ControlIndicator>(r))
export const createIndicator = (payload: { dimension: string; name: string; isActive?: boolean }) =>
  api.post('/campus/indicators/', payload).then((r) => r.data as ControlIndicator)
export const updateIndicator = (id: string, payload: Partial<ControlIndicator>) =>
  api.put(`/campus/indicators/${id}/`, payload).then((r) => r.data as ControlIndicator)
export const deleteIndicator = (id: string) => api.delete(`/campus/indicators/${id}/`).then((r) => r.data)

/* ============================ 规则 ============================ */
export interface RuleInput {
  bu: string
  position: string
  level: string
  dimension: string
  indicator: string
  target: number // 0~1
  lo: number
  hi: number
  strength: Strength
}

const ruleToNum = (x: any): ControlRule => ({ ...x, target: num(x.target), lo: num(x.lo), hi: num(x.hi) })

/** 全部规则（每条自带适用范围）。 */
export const listRules = () =>
  api.get('/campus/rules/', { params: { page_size: 200 } }).then((r) => listData<ControlRule>(r).map(ruleToNum))

export const createRule = (payload: RuleInput) =>
  api.post('/campus/rules/', payload).then((r) => ruleToNum(r.data))
export const updateRule = (id: string, payload: Partial<RuleInput>) =>
  api.put(`/campus/rules/${id}/`, payload).then((r) => ruleToNum(r.data))
export const deleteRule = (id: string) => api.delete(`/campus/rules/${id}/`).then((r) => r.data)

export interface RuleDraft {
  indicator: string
  target: number // 0~1
  lo: number
  hi: number
  strength: Strength
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

/** 批量配置规则 + 人数目标：先按维度设定总人数，再选多个指标占比加和=100%；每指标 annual=round(totalTarget×target)。 */
export const batchConfigRules = (payload: BatchConfigPayload) =>
  api
    .post('/campus/rules/with-targets/', payload)
    .then((r) => r.data as { success: boolean; data: { saved: number; totalTarget: number; year: number } })

/* ============================ 实时看板（全量，每条按自身适用范围） ============================ */
export const getRatio = () =>
  api.get('/campus/rules/ratio/').then((r) => r.data.data as RatioResult)

/* ============================ 人数规划（全量） ============================ */
export const getPlan = (year: number, month: string) =>
  api.get('/campus/rules/plan/', { params: { year, month } }).then((r) => r.data.data as PlanResult)

/* ============================ 录入校验 ============================ */
export const validateDraft = (
  year: number,
  draft: { bu: string; position?: string; level?: string; school: string; sex: string; major: string; month?: string },
) =>
  api
    .post('/campus/rules/validate/', draft, { params: { year } })
    .then((r) => r.data.data as ValidationResult)

/* ============================ 人数目标 ============================ */
export const listHeadcounts = (year: number) =>
  api.get('/campus/headcounts/', { params: { page_size: 200, year } }).then((r) =>
    listData<ControlHeadcount>(r).map((x) => ({
      ...x,
      monthlyTargets: Array.isArray(x.monthlyTargets) && x.monthlyTargets.length === 12 ? x.monthlyTargets : Array(12).fill(0),
    })),
  )
export const upsertHeadcount = (
  h: Partial<ControlHeadcount> & { bu: string; position: string; level: string; indicator: string; year: number; annualTarget: number; monthlyTargets: number[] },
) => {
  const payload = {
    bu: h.bu ?? '', position: h.position ?? '', level: h.level ?? '',
    indicator: h.indicator,
    year: h.year,
    annualTarget: Number(h.annualTarget),
    monthlyTargets: h.monthlyTargets.map((v) => Number(v)),
  }
  if (h.id) return api.put(`/campus/headcounts/${h.id}/`, payload).then((r) => r.data as ControlHeadcount)
  return api.post('/campus/headcounts/', payload).then((r) => r.data as ControlHeadcount)
}
export const deleteHeadcount = (id: string) => api.delete(`/campus/headcounts/${id}/`).then((r) => r.data)

/* ============================ 人员主数据 ============================ */
export const listPersons = () =>
  api.get('/campus/persons/', { params: { page_size: 200 } }).then((r) => listData<Person>(r))
export const upsertPerson = (p: Partial<Person> & { code: string; name: string; bu: string; school: string; sex: string; major: string; month: string; status: string }) => {
  const payload = {
    code: p.code, name: p.name, bu: p.bu, school: p.school, sex: p.sex, major: p.major,
    month: p.month, status: p.status, position: p.position ?? '', level: p.level ?? '', counted: p.counted ?? true,
  }
  if (p.id) return api.put(`/campus/persons/${p.id}/`, payload).then((r) => r.data as Person)
  return api.post('/campus/persons/', payload).then((r) => r.data as Person)
}
export const deletePerson = (id: string) => api.delete(`/campus/persons/${id}/`).then((r) => r.data)

export default {
  listDimensions, createDimension, updateDimension, deleteDimension,
  listIndicators, createIndicator, updateIndicator, deleteIndicator,
  listRules, createRule, updateRule, deleteRule, batchSaveRules, batchConfigRules,
  getRatio, getPlan, validateDraft,
  listHeadcounts, upsertHeadcount, deleteHeadcount,
  listPersons, upsertPerson, deletePerson,
}

/**
 * 校招管控（人员比例管控系统）API。
 * 后端 /api/v1/campus/ 返回 { success, data } 信封。
 * 列表接口走 StandardResultsSetPagination：{ success, data:[...], pagination }。
 * 说明：占比 target/lo/hi 后端以小数(0~1)存储；本封装按后端契约收发明文小数，
 *      百分比↔小数的换算放在前端组件层处理（PRD §6）。
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

/* ============================ 领域常量（与 PRD §1 对齐） ============================ */
export const DEPTS = ['能电BG', '三到BG', '综合BG', '醒电BG']
export const SCHOOLS = ['985', '211', '双一流', '其他']
export const MAJORS = ['工学', '其他']
export const SEXES = ['男', '女']
export const MONTHS = ['8月', '9月', '10月']
export const DIMS = ['院校标签', '专业标签', '性别'] as const
export const STRENGTH = ['硬约束', '软约束', '仅提示'] as const
export const STATUS = ['已入职', '已Offer', '候选池'] as const

export type Dim = (typeof DIMS)[number]
export type Strength = (typeof STRENGTH)[number]

/** dim -> 合法 group 集合（新增/编辑规则时分组选项联动）。 */
export const GROUP_CHOICES: Record<Dim, string[]> = {
  院校标签: SCHOOLS,
  专业标签: MAJORS,
  性别: DEPTS.flatMap((bu) => SEXES.map((s) => `${bu}-${s}`)),
}

/* ============================ 类型定义 ============================ */
export interface Rule {
  id: string
  dim: Dim
  group: string
  target: number // 0~1 小数
  lo: number
  hi: number
  strength: Strength
  whole: number
  monthTarget: number
  createdByName?: string
  createdAt?: string
  updatedByName?: string
  updatedAt?: string
}

export interface RatioRow {
  dim: Dim
  group: string
  actual: number
  denom: number
  ratio: number // 0~1 小数
  target: number
  lo: number
  hi: number
  status: '正常' | '低于下限' | '高于上限'
  strength: Strength
}

export interface PlanRow {
  dim: Dim
  group: string
  strength: Strength
  onjob: number
  whole: number
  wholeGap: number
  monthTarget: number
  monthActual: number
  gap: number
  status: '本月达标' | '缺口未达成' | '未设目标'
}

export interface Kpi {
  total: number
  groupCount: number
  warnCount: number
  hardViolationCount: number
  monthGap: number
}

export interface ValidationCheck {
  dim: Dim
  group: string
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
  counted: boolean
}

export interface ImportResult {
  created: string[]
  createdCount: number
  errors: { row: number; errors: any }[]
}

/* ============================ 规则配置 F1 ============================ */
/** 列表（page_size=200 覆盖全部种子规则）。返回 Rule[]。 */
export const getRules = () =>
  api
    .get<{ success: boolean; data: Rule[] }>('/campus/rules/', { params: { page_size: 200 } })
    .then((r) => (r.data.data ?? []) as Rule[])

/** 新建/编辑规则。payload 用后端小数契约。 */
export const upsertRule = (rule: Partial<Rule> & { dim: Dim; group: string }) => {
  const payload = {
    dim: rule.dim,
    group: rule.group,
    target: Number(rule.target),
    lo: Number(rule.lo),
    hi: Number(rule.hi),
    strength: rule.strength,
    whole: Number(rule.whole ?? 0),
    monthTarget: Number(rule.monthTarget ?? 0),
  }
  if (rule.id) {
    return api.put<{ success: boolean; data: Rule }>(`/campus/rules/${rule.id}/`, payload).then((r) => r.data.data)
  }
  return api.post<{ success: boolean; data: Rule }>('/campus/rules/', payload).then((r) => r.data.data)
}

export const deleteRule = (id: string) =>
  api.delete(`/campus/rules/${id}/`).then((r) => r.data)

/* ============================ 实时看板 F3 ============================ */
/** compute_ratio。返回 { total, rows }。 */
export const getRatio = () =>
  api
    .get<{ success: boolean; data: { total: number; rows: RatioRow[] } }>('/campus/rules/ratio/')
    .then((r) => r.data.data)

/* ============================ 人数规划 F4 ============================ */
/** compute_count + kpi。返回 { rows, kpi }。 */
export const getPlan = (month: string) =>
  api
    .get<{ success: boolean; data: { rows: PlanRow[]; kpi: Kpi } }>('/campus/rules/plan/', {
      params: { month },
    })
    .then((r) => r.data.data)

/* ============================ 录入校验 F5 ============================ */
/** simulate（服务端重算作为管控依据）。 */
export const validateDraft = (draft: { bu: string; school: string; sex: string; major: string; month?: string }) =>
  api
    .post<{ success: boolean; data: ValidationResult }>('/campus/rules/validate/', draft)
    .then((r) => r.data.data)

/* ============================ 人员主数据 F2 ============================ */
export const getPersons = () =>
  api
    .get<{ success: boolean; data: Person[] }>('/campus/persons/', { params: { page_size: 200 } })
    .then((r) => (r.data.data ?? []) as Person[])

export const upsertPerson = (p: Partial<Person> & { code: string; name: string; bu: string; school: string; sex: string; major: string; month: string; status: string }) => {
  const payload = {
    code: p.code,
    name: p.name,
    bu: p.bu,
    school: p.school,
    sex: p.sex,
    major: p.major,
    month: p.month,
    status: p.status,
    counted: p.counted ?? true,
  }
  if (p.id) {
    return api.put<{ success: boolean; data: Person }>(`/campus/persons/${p.id}/`, payload).then((r) => r.data.data)
  }
  return api.post<{ success: boolean; data: Person }>('/campus/persons/', payload).then((r) => r.data.data)
}

export const deletePerson = (id: string) =>
  api.delete(`/campus/persons/${id}/`).then((r) => r.data)

/** 批量导入人员。 */
export const importPersons = (rows: Partial<Person>[]) =>
  api
    .post<{ success: boolean; data: ImportResult }>('/campus/persons/import/', { rows })
    .then((r) => r.data.data)

export default {
  getRules,
  upsertRule,
  deleteRule,
  getRatio,
  getPlan,
  validateDraft,
  getPersons,
  upsertPerson,
  deletePerson,
  importPersons,
}

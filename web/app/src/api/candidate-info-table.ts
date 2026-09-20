// 候选人信息表：真实数据表格 + 列显隐配置落库 + 搜索筛选 + 前端 CSV 导出
// 数据来源：GET /api/v1/candidates/（camelCase 渲染）
// 列配置落库端点：GET/POST/PUT /api/v1/standard-resume/candidate-info-table/（CandidateTableConfigView）
//
// 2026-09-12 扩展：候选人信息登记表设置（权限 / 使用范围 / 标准简历样式 / 场景联动），
// 复用同一 key='candidate_info_table' 配置端点，结构见 CandidateInfoTableConfig。

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

export const CANDIDATE_TABLE_CONFIG_API = '/standard-resume/candidate-info-table/'

// 真实候选人记录（对齐后端 CandidateListSerializer 的 camelCase 字段）
export interface CandidateRow {
  id: string
  name?: string
  phone?: string
  email?: string
  gender?: string
  age?: number
  currentState?: string
  stateDisplay?: string
  sourceChannel?: string
  sourceChannelName?: string
  referralType?: string
  currentCompany?: string
  currentPosition?: string
  applicationCount?: number
  createdAt?: string
  tags?: string[]
  blacklisted?: boolean
}

// 列配置
export interface CandidateTableColumn {
  key: string
  label: string
  visible: boolean
  order: number
}

export interface CandidateTableColumnConfig {
  columns: CandidateTableColumn[]
}

export function defaultColumnConfig(): CandidateTableColumnConfig {
  return { columns: [] }
}

// 默认列集（无配置时回退）—— 覆盖 CandidateRow 主要展示字段
export const DEFAULT_TABLE_COLUMNS: CandidateTableColumn[] = [
  { key: 'name', label: '姓名', visible: true, order: 0 },
  { key: 'gender', label: '性别', visible: true, order: 1 },
  { key: 'age', label: '年龄', visible: true, order: 2 },
  { key: 'phone', label: '手机号', visible: true, order: 3 },
  { key: 'currentCompany', label: '当前公司', visible: true, order: 4 },
  { key: 'currentPosition', label: '当前职位', visible: true, order: 5 },
  { key: 'sourceChannelName', label: '来源渠道', visible: true, order: 6 },
  { key: 'stateDisplay', label: '状态', visible: true, order: 7 },
  { key: 'applicationCount', label: '投递次数', visible: false, order: 8 },
  { key: 'createdAt', label: '创建时间', visible: true, order: 9 },
]

// 列配置读写
export async function fetchColumnConfig(): Promise<CandidateTableColumnConfig> {
  const r = await api.get(CANDIDATE_TABLE_CONFIG_API)
  const data = (r.data?.data ?? {}) as Partial<CandidateTableColumnConfig>
  return { columns: Array.isArray(data.columns) ? data.columns : [] }
}

export async function saveColumnConfig(cfg: CandidateTableColumnConfig): Promise<CandidateTableColumnConfig> {
  const r = await api.put(CANDIDATE_TABLE_CONFIG_API, cfg)
  const data = (r.data?.data ?? {}) as Partial<CandidateTableColumnConfig>
  return { columns: Array.isArray(data.columns) ? data.columns : [] }
}

export async function resetColumnConfig(): Promise<CandidateTableColumnConfig> {
  return saveColumnConfig(defaultColumnConfig())
}

// 按列配置解析出最终可见列（按 order 升序，仅 visible）
export function resolveVisibleColumns(columns: CandidateTableColumn[]): CandidateTableColumn[] {
  return [...columns]
    .filter((c) => c.visible)
    .sort((a, b) => a.order - b.order)
}

// 真实数据拉取——注意后端参数名：page_size / state / keyword（非 pageSize / candidateStatus）
export async function listCandidatesForTable(params: {
  page?: number
  pageSize?: number
  state?: string
  keyword?: string
} = {}): Promise<{ data: CandidateRow[]; total: number }> {
  const { page = 1, pageSize = 20, state, keyword } = params
  const query: Record<string, unknown> = { page, page_size: pageSize }
  if (state) query.state = state
  if (keyword) query.keyword = keyword
  const res = await api.get('/candidates/', { params: query })
  const body = res.data || {}
  return {
    data: Array.isArray(body.data) ? (body.data as CandidateRow[]) : [],
    total: body.pagination?.total ?? 0,
  }
}

// 前端本地生成 CSV（后端无导出端点）—— 带 BOM 防 Excel 中文乱码
export function buildCsv(
  rows: CandidateRow[],
  columns: { key: string; label: string }[],
): string {
  const header = columns.map((c) => c.label).join(',')
  const escape = (v: unknown): string => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = rows.map((row) =>
    columns.map((c) => escape((row as unknown as Record<string, unknown>)[c.key])).join(','),
  )
  return '﻿' + [header, ...lines].join('\r\n')
}

export function exportTableToCsv(
  rows: CandidateRow[],
  columns: { key: string; label: string }[],
  filename = '候选人信息表',
): void {
  const csv = buildCsv(rows, columns)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/* ============ 候选人信息登记表设置（权限 / 使用范围 / 样式 / 场景联动） ============ */

export type ScopeMode = 'global' | 'department'
export type ResumeStyle = 'standard' | 'custom'

export interface CandidateInfoTableScene {
  key: string
  label: string
  formId: number | null
  style: ResumeStyle
}

export interface CandidateInfoTableConfig {
  permissionScope: ScopeMode
  usageScope: ScopeMode
  resumeStyle: ResumeStyle
  scenes: CandidateInfoTableScene[]
}

// 后端无配置时的默认结构（与后端 CandidateTableConfigView 默认值对齐）
export function defaultCandidateInfoTableConfig(): CandidateInfoTableConfig {
  return {
    permissionScope: 'global',
    usageScope: 'global',
    resumeStyle: 'standard',
    scenes: [
      { key: 'interview_accept', label: '接受面试时', formId: null, style: 'standard' },
      { key: 'interview_signin', label: '面试签到时', formId: null, style: 'standard' },
      { key: 'offer_accept', label: '接受Offer时', formId: null, style: 'standard' },
    ],
  }
}

function unwrap<T>(r: { data: { success: boolean; data: T } }): T {
  return r.data.data
}

export async function getCandidateInfoTableConfig(): Promise<CandidateInfoTableConfig> {
  const r = await api.get(CANDIDATE_TABLE_CONFIG_API)
  const data = (r.data?.data ?? {}) as Partial<CandidateInfoTableConfig>
  const def = defaultCandidateInfoTableConfig()
  // 缺省场景用默认补齐，保证前端始终有完整场景列表
  return {
    permissionScope: data.permissionScope ?? def.permissionScope,
    usageScope: data.usageScope ?? def.usageScope,
    resumeStyle: data.resumeStyle ?? def.resumeStyle,
    scenes: data.scenes?.length ? data.scenes : def.scenes,
  }
}

export async function saveCandidateInfoTableConfig(
  cfg: CandidateInfoTableConfig,
): Promise<CandidateInfoTableConfig> {
  const r = await api.put(CANDIDATE_TABLE_CONFIG_API, cfg)
  return unwrap<CandidateInfoTableConfig>(r)
}

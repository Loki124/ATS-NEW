/**
 * rule-engine.ts — 统一规则引擎 API 客户端 (Phase 4 后端)
 *
 * 后端端点: GET /api/v1/rule-engine/rules/?category=&trigger_type=&enabled=&source_app=
 *           GET /api/v1/rule-engine/triggers/
 *           GET /api/v1/rule-engine/operators/
 *
 * ⚠️ 路径约定: axios 实例 baseURL 已是 config.api.baseUrl = '/api/v1',
 *    调用路径必须从 '/rule-engine/...' 起算, 不能重复 '/api/v1' 前缀
 *    (否则最终请求是 '/api/v1/api/v1/rule-engine/rules/' → Django 404)。
 *
 * 严格只读: 聚合视图 (Phase 1+), 源数据由各业务模块 (automation / mou / campus_control / ...)
 *           在源表维护, 本端点仅做 DB 读 + 映射。
 *
 * 响应格式: { success, data: [...], pagination: { total, ... } } — 标准信封
 * 字段命名: drf-camel-case 输出 camelCase (category / sourceApp / triggerType / legacyModel /
 *           conditionsSummary / actionsSummary / ...), FE 类型严格按 camelCase 写
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

// ===== 类型定义 =====

export type RuleCategory = 'TCA' | 'BUSINESS_EVENT' | 'CONSTRAINT' | 'SET_PERMISSION'

export interface UnifiedRule {
  id: string
  name: string
  category: RuleCategory
  sourceApp: string
  triggerType: string
  legacyModel?: string
  legacyId?: string
  triggerTiming?: string
  scopeJson?: any
  priority?: string
  priorityRank?: number
  status?: string
  enabled?: boolean
  conditionExpression?: string
  conditionLogic?: string
  configJson?: any
  conditionsSummary?: any
  actionsSummary?: any
}

export interface UnifiedRuleListResponse {
  success: boolean
  data: UnifiedRule[]
  pagination: { total: number; page: number; pageSize: number }
}

export interface TriggerOption {
  value: string
  label: string
}

export interface OperatorOption {
  value: string
  label: string
}

// ===== 端点 =====

export interface ListRulesParams {
  page?: number
  pageSize?: number
  category?: RuleCategory
  triggerType?: string
  enabled?: boolean
  sourceApp?: string
}

export async function listRules(params: ListRulesParams = {}): Promise<UnifiedRuleListResponse> {
  const res = await api.get('/rule-engine/rules/', { params })
  return res.data
}

export async function listTriggers(): Promise<TriggerOption[]> {
  const res = await api.get('/rule-engine/triggers/')
  return Array.isArray(res.data) ? res.data : (res.data?.data || [])
}

export async function listOperators(): Promise<OperatorOption[]> {
  const res = await api.get('/rule-engine/operators/')
  return Array.isArray(res.data) ? res.data : (res.data?.data || [])
}
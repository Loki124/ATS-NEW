import type { ApiEnvelope } from '../utils/envelope'
// 重复候选人管理 API
// 后端端点（挂载 /api/v1/duplicate-rules/）：
//   GET         catalog/            查重项字段目录（强 / 中 / 弱）
//   GET         config/             读取「合并规则 + 重复申请管理」配置
//   PUT         config/             局部保存配置
//   GET         rules/              规则列表
//   POST        rules/              新建规则
//   GET/PUT/DEL rules/<pk>/         规则详情 / 更新 / 软删除
//   POST        rules/<pk>/toggle/  启用 / 停用
//   POST        rules/reset/        恢复系统默认
//
// ⚠️ 后端全局启用 CamelCaseJSONRenderer / CamelCaseJSONParser：
//    出入参一律 camelCase（含自由 JSON dict 的键），本文件类型定义即按 camelCase 声明。
import { api } from '../utils/request'

import config from '../config'

// ===== 查重项 =====
export type DuplicateStrength = 'STRONG' | 'MEDIUM' | 'WEAK'

/** 查重项取值强度（服务端 catalog 决定，前端不自行判定） */
export interface DuplicateFieldItem {
  key: string
  label: string
  hint: string
}

export interface DuplicateFieldGroup {
  strength: DuplicateStrength
  label: string
  items: DuplicateFieldItem[]
}

// ===== 规则 =====
export type DuplicateConditionLogic = 'ALL' | 'ANY'

export interface DuplicateRuleItem {
  key: string
  strength: DuplicateStrength
}

export interface DuplicateRule {
  id: number
  name: string
  scope: string
  isSystem: boolean
  conditionLogic: DuplicateConditionLogic
  anyCount: number
  items: DuplicateRuleItem[]
  isEnabled: boolean
  orderIndex: number
  /** 只读展示列：全部 / 任意 N 项 */
  conditionText: string
  /** 只读展示列：查重项中文名数组 */
  itemsText: string[]
  createdAt?: string
  updatedAt?: string
}

export interface DuplicateRulePayload {
  name: string
  scope?: string
  conditionLogic: DuplicateConditionLogic
  anyCount?: number
  items: DuplicateRuleItem[]
  isEnabled?: boolean
  orderIndex?: number
}

// ===== 配置 =====
export interface MergeStrategyOption {
  value: string
  label: string
}

export interface MergeStrategy {
  key: string
  label: string
  value: string
  options: MergeStrategyOption[]
}

export interface MergeConfig {
  enabled: boolean
  cancelUnacceptedHeadhunter: boolean
  strategies: MergeStrategy[]
}

export interface ApplicationConfig {
  enabled: boolean
  windowMonths: number
  windowOptions: { value: number; label: string }[]
}

export interface DuplicateConfig {
  merge: MergeConfig
  application: ApplicationConfig
}

function unwrap<T>(r: { data: ApiEnvelope<T> }): T {
  return r.data.data
}

// ===== API =====

/** 查重项字段目录（强 / 中 / 弱三档） */
export async function getDuplicateCatalog(): Promise<{ groups: DuplicateFieldGroup[] }> {
  const r = await api.get('/duplicate-rules/catalog/')
  return unwrap<{ groups: DuplicateFieldGroup[] }>(r)
}

/** 读取全局配置（后端缺失字段会用默认值补齐） */
export async function getDuplicateConfig(): Promise<DuplicateConfig> {
  const r = await api.get('/duplicate-rules/config/')
  return unwrap<DuplicateConfig>(r)
}

/** 局部保存配置：无需提交的键保持服务端现值 */
export async function updateDuplicateConfig(
  partial: Partial<DuplicateConfig>,
): Promise<DuplicateConfig> {
  const r = await api.put('/duplicate-rules/config/', partial)
  return unwrap<DuplicateConfig>(r)
}

/** 规则列表（首次调用会惰性种入系统内置规则） */
export async function listDuplicateRules(scope?: string): Promise<DuplicateRule[]> {
  const r = await api.get('/duplicate-rules/rules/', { params: scope ? { scope } : undefined })
  return unwrap<DuplicateRule[]>(r)
}

export async function createDuplicateRule(
  payload: DuplicateRulePayload,
): Promise<DuplicateRule> {
  const r = await api.post('/duplicate-rules/rules/', payload)
  return unwrap<DuplicateRule>(r)
}

export async function updateDuplicateRule(
  id: number,
  payload: Partial<DuplicateRulePayload>,
): Promise<DuplicateRule> {
  const r = await api.put(`/duplicate-rules/rules/${id}/`, payload)
  return unwrap<DuplicateRule>(r)
}

/** 软删除（系统内置规则后端会拒绝） */
export async function deleteDuplicateRule(id: number): Promise<void> {
  await api.delete(`/duplicate-rules/rules/${id}/`)
}

/** 启用 / 停用；不传 isEnabled 时后端翻转当前状态 */
export async function toggleDuplicateRule(
  id: number,
  isEnabled?: boolean,
): Promise<DuplicateRule> {
  const r = await api.post(
    `/duplicate-rules/rules/${id}/toggle/`,
    isEnabled === undefined ? {} : { isEnabled },
  )
  return unwrap<DuplicateRule>(r)
}

/** 恢复系统默认：软删自定义规则 + 系统规则复位 */
export async function resetDuplicateRules(): Promise<DuplicateRule[]> {
  const r = await api.post('/duplicate-rules/rules/reset/', {})
  return unwrap<DuplicateRule[]>(r)
}

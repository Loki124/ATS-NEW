/**
 * dynamicStrategy.ts — 动态策略（Dynamic Strategy）API 客户端
 *
 * 后端端点（base: /api/v1）:
 *   GET    /dynamic-strategies/                      列表
 *   POST   /dynamic-strategies/                      创建
 *   GET    /dynamic-strategies/{strategy_code}/      详情
 *   PUT    /dynamic-strategies/{strategy_code}/      更新
 *   DELETE /dynamic-strategies/{strategy_code}/      删除
 *   GET    /dynamic-strategies/options/              模块/动作/预设包选项
 *
 * 响应格式: { success: boolean, data: ... }（见 utils/envelope.ApiEnvelope）
 *
 * 类型风格对齐 role-v2.ts / permission-resource.ts：复用本仓共享 `api` 单例，
 * 通过 ApiEnvelope<...> 收口响应，导出函数式 API。
 */
import { api } from '../utils/request'
import type { ApiEnvelope } from '../utils/envelope'
import type { ActionDictItem, ActionPreset, WriteMode, PermConditionGroup } from '@/api/data-permission'

// ===== 类型定义 =====

/** 单个模块的操作权限配置（写范围）：与 ModuleActionCard 的 write 子结构对齐。 */
export interface StrategyModuleConfig {
  /** 写范围模式：none=不限制 / all=全部可写 / owner=仅负责人 / scope=自定义范围 */
  mode: WriteMode
  /** 组间组合表达式（scope 模式生效） */
  expr: string
  /** 自定义条件组（scope 模式生效） */
  groups: PermConditionGroup[]
  /** 允许的写动作 key 集合（来自 options.actions，DB 可配置） */
  actions: string[]
}

/** 动态策略实体（创建/列表/详情共用） */
export interface DynamicStrategy {
  id?: number | string
  strategy_code: string
  strategy_name: string
  /** 1=启用 / 0=停用 */
  status: number
  description?: string | null
  /** 受限制的业务模块（module key 列表）：demand/process/position/candidate/talent */
  governed_functions: string[]
  /** 本策略授予的功能资源码 */
  granted_resource_codes: string[]
  /** module_key -> 操作权限配置（mode/actions/groups/expr） */
  module_config: Record<string, StrategyModuleConfig>
  created_at?: string
  updated_at?: string
}

/** options 接口：模块清单 + 可配置动作字典 + 动作预设包 */
export interface StrategyOptions {
  modules: Array<{ key: string; label: string }>
  actions: ActionDictItem[]
  presets: ActionPreset[]
}

// ===== API =====

/** 策略列表 */
export async function listStrategies(params?: Record<string, unknown>): Promise<DynamicStrategy[]> {
  const { data } = await api.get<ApiEnvelope<DynamicStrategy[]>>('/dynamic-strategies/', { params })
  return data.data ?? []
}

/** 策略详情 */
export async function getStrategy(code: string): Promise<DynamicStrategy> {
  const { data } = await api.get<ApiEnvelope<DynamicStrategy>>(`/dynamic-strategies/${code}/`)
  return data.data
}

/** 创建策略 */
export async function createStrategy(payload: Partial<DynamicStrategy>): Promise<DynamicStrategy> {
  const { data } = await api.post<ApiEnvelope<DynamicStrategy>>('/dynamic-strategies/', payload)
  return data.data
}

/** 更新策略 */
export async function updateStrategy(
  code: string,
  payload: Partial<DynamicStrategy>,
): Promise<DynamicStrategy> {
  const { data } = await api.put<ApiEnvelope<DynamicStrategy>>(`/dynamic-strategies/${code}/`, payload)
  return data.data
}

/** 删除策略 */
export async function deleteStrategy(code: string): Promise<void> {
  await api.delete<ApiEnvelope<void>>(`/dynamic-strategies/${code}/`)
}

/** 策略配置选项：模块清单 + 动作字典 + 预设包 */
export async function getStrategyOptions(): Promise<StrategyOptions> {
  const { data } = await api.get<ApiEnvelope<StrategyOptions>>('/dynamic-strategies/options/')
  return data.data ?? { modules: [], actions: [], presets: [] }
}

export default api

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
import type { ApiEnvelope, ApiEnvelopePaged } from '../utils/envelope'
import type {
  ActionDictItem, ActionPreset, WriteMode, PermConditionGroup,
  DimensionMeta, AttributeField,
} from '@/api/data-permission'

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

/**
 * 动态策略实体（创建/列表/详情共用）。
 * ⚠️ 字段名与 API 响应一致走 camelCase（本项目 REST 框架 CamelCaseJSONRenderer 出参；
 *   前端直接消费 camelCase，不再手桥；与 DepartmentManagement 等列表页同约定）。
 */
export interface DynamicStrategy {
  id?: number | string
  strategyCode: string
  strategyName: string
  /** 1=启用 / 0=停用 */
  status: number
  description?: string | null
  /** 受限制的业务模块（module key 列表）：demand/process/position/candidate/talent */
  governedFunctions: string[]
  /** 本策略授予的功能资源码 */
  grantedResourceCodes: string[]
  /** module_key -> 操作权限配置（mode/actions/groups/expr） */
  moduleConfig: Record<string, StrategyModuleConfig>
  createdAt?: string
  updatedAt?: string
}

/**
 * 「受限功能」候选资源：后端按策略模块分组下发，已过滤
 * strategy_governed=True + BUTTON + status=1。
 */
export interface StrategyGovernedResource {
  /** 资源码（形如 recruit:demand:xxx:button:create），勾选后写入 grantedResourceCodes */
  resourceCode: string
  /** 资源中文名，复选框展示文案 */
  resourceName: string
  /** 子模块 code（资源码第 3 段），用于 UI 分组；无子模块时缺省 */
  subModule?: string
}

/** options 接口：模块 × 维度 × 属性字段矩阵 + 可配置动作字典 + 动作预设包 + 受管控资源 */
export interface StrategyOptions {
  /** 每模块含维度/属性字段（供「配置写范围」弹窗 RuleConfigModal 取下拉） */
  modules: StrategyModuleOption[]
  actions: ActionDictItem[]
  presets: ActionPreset[]
  /**
   * 策略模块 key → 该模块下「受策略管控」的资源列表（受限功能候选）。
   * 后端契约：{ [策略模块key]: StrategyGovernedResource[] }；
   * 旧版本无此键（缺省 undefined），取值处须用 `?? []` 兜底。
   */
  governedResources?: Record<string, StrategyGovernedResource[]>
}

/** options.modules 单项：与 data-permission 的 ModuleOption 同构（角色无关矩阵） */
export interface StrategyModuleOption {
  /** 后端 matrix 以 moduleKey 为键（兼容旧 key 字段） */
  moduleKey?: string
  key?: string
  label: string
  dimensions: DimensionMeta[]
  attributeFields: AttributeField[]
}

/** 列表响应：信封内的数据数组 + 分页总条数 */
export interface StrategyListResult {
  items: DynamicStrategy[]
  total: number
}

// ===== API =====

/** 策略列表（服务端分页；返回 {items,total} 供 remotePagination） */
export async function listStrategies(params?: Record<string, unknown>): Promise<StrategyListResult> {
  const { data } = await api.get<ApiEnvelopePaged<DynamicStrategy>>('/dynamic-strategies/', { params })
  return { items: data.data ?? [], total: data.pagination?.total ?? 0 }
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

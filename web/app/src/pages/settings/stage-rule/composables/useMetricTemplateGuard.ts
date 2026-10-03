/**
 * 指标模板失效守卫（EXP-5 / EXP-3 共享纯函数工具）。
 * 不依赖任何组件，仅依赖 types，可被任意 composable / modal 直接引入。
 *
 * 背景：规则里的 METRIC 条件项通过 `field`（模板 id）引用指标模板；
 * 当模板被禁用 / 软删后，后端目录 GET /api/v1/expressions/fields 会把它从
 * METRIC source 的 fields 中剔除。此时该条件项即「引用失效」，必须拦截，
 * 防止「引用失效」的静默假绿。
 *
 * 关键约定：catalog 为 null（目录加载失败）→ fail-open，不判失效、不拦截，
 * 避免误伤正常编辑。仅当 catalog 已加载且该 METRIC 项的 field 不在目录中时才判失效。
 */

import type { FieldCatalog, FieldDef, ConditionItem } from '../types'

/** 失效指标模板红字提示文案（复用为 EXP-5 红字与 itemError 的统一出口） */
export const METRIC_STALE_MESSAGE = '引用的指标模板已失效（禁用/删除），请移除或重新选择'

/**
 * 从目录取 METRIC 数据源下的字段列表（即指标模板映射）。
 * catalog 缺失 / 无 METRIC source → 返回空数组。
 */
export function getMetricFields(catalog: FieldCatalog | null): FieldDef[] {
  return catalog?.sources?.find((s) => s.source === 'METRIC')?.fields || []
}

/**
 * 判断某条件项是否为「引用失效的指标模板」：
 * - 仅对 condition_type === 'METRIC' 生效；
 * - catalog 为 null（目录加载失败）→ fail-open：返回 false（不判失效、不拦截）；
 * - 否则，当其 field（模板 id）不在 METRIC fields 中时返回 true。
 */
export function isMetricFieldMissing(item: ConditionItem, catalog: FieldCatalog | null): boolean {
  if (item.condition_type !== 'METRIC') return false
  if (!catalog) return false // 目录未加载 -> fail-open，不判失效
  const fields = getMetricFields(catalog)
  return !fields.some((f) => f.field === item.field)
}

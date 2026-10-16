/**
 * metricsListFilter.ts — 指标工作区「列表筛选 / 空态细分 / 分页切片」纯逻辑。
 *
 * 从 composables/useMetricsWorkspace.ts 抽出的无状态部分：
 *   - filteredDefinitions（kind + module + 关键词过滤）
 *   - defEmptyKind（空态细分 first / search / filter）
 *   - filteredTemplates（status + 关键词过滤）
 *   - pagedDefinitions / pagedTemplates（分页切片，越界回退）
 *
 * 约定（重构铁律）：
 *   - 全部为纯函数，不依赖任何组件级 reactive state；
 *   - **不接受 i18n 的 t**：需要文案的判定一律由调用方把「已解析好的文案函数」注入，
 *     单测传 identity mock（(type) => `X:${type}`）即可，无需真实字典/接口；
 *   - 行为与拆分前逐字一致，重构不改判定规则。
 */
import type { MetricDefinition, MetricTemplate, OptionItem } from '@/api/metrics'
import * as MF from './metricsFormat'

/**
 * 关键词匹配要命中中文文案（出参类型 / 参数类型 / 指标类型），故这三个文案函数由调用方注入。
 * 类型签名与 metricsFormat 的 label 函数一致，composable 侧用 `MF.xxx(t, x)` 的薄包装传入。
 */
export interface DefinitionKeywordLabels {
  returnTypeLabel: (type?: string) => string
  paramTypeLabel: (type?: string) => string
  kindLabel: (row: MetricDefinition) => string
}

export type DefKindFilter = 'all' | 'atomic' | 'derived'
export type DefModuleFilter = 'all' | 'candidate' | 'demand' | 'position' | 'derived' | 'other'
export type TplStatusFilter = 'all' | 'enabled' | 'disabled'
export type EmptyKind = 'first' | 'search' | 'filter'

export interface DefinitionFilter {
  keyword: string
  kind: DefKindFilter
  module: DefModuleFilter
}

export interface TemplateFilter {
  keyword: string
  status: TplStatusFilter
}

/**
 * 指标定义过滤：kind 与 module 先做等值筛，关键词命中范围为
 * name / dataSource / 出参类型 / 参数类型 / 指标类型 / 取值方式 / 支持运算符 的 join。
 * 关键词与被匹配文本均 lowerCase 后做 includes。
 */
export function filterDefinitions(
  definitions: MetricDefinition[],
  filter: DefinitionFilter,
  labels: DefinitionKeywordLabels,
  operatorCatalog: OptionItem[],
): MetricDefinition[] {
  const kw = filter.keyword.trim().toLowerCase()
  const opLabel = (o: string) => MF.findOperatorLabel(operatorCatalog, o)
  return definitions.filter((d) => {
    if (filter.kind !== 'all' && d.kind !== filter.kind) return false
    if (filter.module !== 'all' && MF.sourceModuleKey(d) !== filter.module) return false
    if (kw) {
      const hay = [
        d.name,
        d.dataSource,
        labels.returnTypeLabel(d.returnType),
        labels.paramTypeLabel(d.paramType),
        labels.kindLabel(d),
        d.valueMode,
        (d.supportedOperators || []).map((o) => opLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
}

/**
 * M-3 空态细分：
 *   - 库里一条都没有 → first（首用引导）
 *   - 有数据但搜了关键词 → search（搜索无果）
 *   - 有数据且仅靠 kind/module 筛掉 → filter（筛选无果）
 */
export function definitionEmptyKind(totalCount: number, filter: DefinitionFilter): EmptyKind {
  if (totalCount === 0) return 'first'
  if (filter.keyword.trim()) return 'search'
  if (filter.kind !== 'all' || filter.module !== 'all') return 'filter'
  return 'first'
}

/** 指标模板过滤：status 等值筛 + 关键词（name / metricName / 支持运算符）。 */
export function filterTemplates(
  templates: MetricTemplate[],
  filter: TemplateFilter,
  operatorCatalog: OptionItem[],
): MetricTemplate[] {
  const kw = filter.keyword.trim().toLowerCase()
  const opLabel = (o: string) => MF.findOperatorLabel(operatorCatalog, o)
  return templates.filter((tpl) => {
    if (filter.status !== 'all' && tpl.status !== filter.status) return false
    if (kw) {
      const hay = [
        tpl.name,
        tpl.metricName,
        (tpl.operators || []).map((o) => opLabel(o)).join(' '),
      ].join(' ').toLowerCase()
      if (!hay.includes(kw)) return false
    }
    return true
  })
}

/**
 * 分页切片：起始位置对最后一页做钳制，
 * 保证删除末页数据后当前页码越界时不会切出空白页。
 */
export function pageSlice<T>(list: T[], page: number, pageSize: number): T[] {
  const maxStart = Math.max(0, list.length - pageSize)
  const start = Math.min((page - 1) * pageSize, maxStart)
  return list.slice(start, start + pageSize)
}

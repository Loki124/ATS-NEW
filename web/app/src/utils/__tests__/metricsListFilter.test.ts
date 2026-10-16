/**
 * metricsListFilter.test.ts — 列表筛选 / 空态细分 / 分页切片 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉到本模块的业务判定：
 *   - filterDefinitions：kind/module 等值筛 + 关键词多字段命中
 *   - definitionEmptyKind：first / search / filter 三态细分
 *   - filterTemplates：status 等值筛 + 关键词
 *   - pageSlice：越界页码钳制
 *
 * 用 identity-mock `t = (k) => k` 断言「选键逻辑」，不依赖具体字典文案。
 */
import { describe, it, expect } from 'vitest'
import {
  filterDefinitions,
  definitionEmptyKind,
  filterTemplates,
  pageSlice,
  type DefinitionFilter,
  type TemplateFilter,
} from '../metricsListFilter'
import type { MetricDefinition, MetricTemplate, OptionItem } from '@/api/metrics'

// 纯函数不接 i18n 的 t，改注入「已解析好的文案函数」；identity mock 让断言只关心选键逻辑。
const RT = ((type?: string) => `RT:${type}`) as any
const PT = ((type?: string) => `PT:${type}`) as any
const KL = ((r: MetricDefinition) => `KL:${r.kind}`) as any
const labels = { returnTypeLabel: RT, paramTypeLabel: PT, kindLabel: KL }
const catalog: OptionItem[] = [
  { value: 'GTE', label: '大于等于' },
  { value: 'LTE', label: '小于等于' },
  { value: 'IN', label: '属于' },
]

function def(p: Partial<MetricDefinition>): MetricDefinition {
  return { id: 'x', kind: 'atomic', name: '', dataSource: '', ...p } as MetricDefinition
}
function tpl(p: Partial<MetricTemplate>): MetricTemplate {
  return { id: 't1', name: '', status: 'enabled', ...p } as MetricTemplate
}
const base: DefinitionFilter = { keyword: '', kind: 'all', module: 'all' }
const baseTpl: TemplateFilter = { keyword: '', status: 'all' }

describe('filterDefinitions', () => {
  it('kind=all 时全量返回', () => {
    const list = [def({ id: '1' }), def({ id: '2', kind: 'derived' })]
    expect(filterDefinitions(list, base,
      labels,
      catalog,
    )).toHaveLength(2)
  })

  it('kind 等值筛只保留该类', () => {
    const list = [def({ id: '1', kind: 'atomic' }), def({ id: '2', kind: 'derived' })]
    expect(filterDefinitions(list, { ...base, kind: 'derived' },
      labels,
      catalog,
    ).map((d) => d.id)).toEqual(['2'])
  })

  it('module 等值筛按 dataSource 前缀判定', () => {
    const list = [
      def({ id: 'a', dataSource: 'candidate.age' }),
      def({ id: 'b', dataSource: 'demand.count' }),
    ]
    expect(filterDefinitions(list, { ...base, module: 'demand' },
      labels,
      catalog,
    ).map((d) => d.id)).toEqual(['b'])
  })

  it('kind 与 module 条件为 AND 关系', () => {
    const list = [
      def({ id: 'a', kind: 'atomic', dataSource: 'demand.count' }),
      def({ id: 'b', kind: 'derived', dataSource: 'demand.count' }),
    ]
    const r = filterDefinitions(list, { ...base, kind: 'atomic', module: 'demand' },
      labels,
      catalog,
    )
    expect(r.map((d) => d.id)).toEqual(['a'])
  })

  it('关键词命中 name', () => {
    const list = [def({ id: 'a', name: '面试轮次' }), def({ id: 'b', name: '到岗天数' })]
    expect(filterDefinitions(list, { ...base, keyword: '面试' },
      labels,
      catalog,
    ).map((d) => d.id)).toEqual(['a'])
  })

  it('关键词命中 dataSource', () => {
    const list = [def({ id: 'a', dataSource: 'candidate.age' }), def({ id: 'b', dataSource: 'demand.count' })]
    expect(filterDefinitions(list, { ...base, keyword: 'candidate' },
      labels,
      catalog,
    ).map((d) => d.id)).toEqual(['a'])
  })

  it('关键词大小写不敏感', () => {
    const list = [def({ id: 'a', name: 'InterviewCount' })]
    expect(filterDefinitions(list, { ...base, keyword: 'interviewcount' },
      labels,
      catalog,
    )).toHaveLength(1)
  })

  it('关键词命中运算符中文标签（需 operatorCatalog）', () => {
    const list = [def({ id: 'a', supportedOperators: ['GTE'] }), def({ id: 'b', supportedOperators: ['IN'] })]
    const r = filterDefinitions(list, { ...base, keyword: '大于等于' },
      labels,
      catalog,
    )
    expect(r.map((d) => d.id)).toEqual(['a'])
  })

  it('关键词空白 trim 后视为不过滤', () => {
    const list = [def({ id: 'a' }), def({ id: 'b' })]
    expect(filterDefinitions(list, { ...base, keyword: '   ' },
      labels,
      catalog,
    )).toHaveLength(2)
  })

  it('无任何命中返回空数组', () => {
    expect(filterDefinitions([def({ id: 'a', name: 'x' })], { ...base, keyword: 'zzz' },
      labels,
      catalog,
    )).toEqual([])
  })

  it('supportedOperators 为空数组时不影响其它条件', () => {
    const list = [def({ id: 'a', name: '命中', supportedOperators: [] })]
    expect(filterDefinitions(list, { ...base, keyword: '命中' },
      labels,
      catalog,
    )).toHaveLength(1)
  })
})

describe('definitionEmptyKind', () => {
  it('库为空 → first', () => {
    expect(definitionEmptyKind(0, base)).toBe('first')
  })

  it('有数据 + 有关键词 → search', () => {
    expect(definitionEmptyKind(5, { ...base, keyword: 'x' })).toBe('search')
  })

  it('有数据 + kind 非 all → filter', () => {
    expect(definitionEmptyKind(5, { ...base, kind: 'atomic' })).toBe('filter')
  })

  it('有数据 + module 非 all → filter', () => {
    expect(definitionEmptyKind(5, { ...base, module: 'demand' })).toBe('filter')
  })

  it('有数据 + 空白关键词 + 无筛选 → first', () => {
    expect(definitionEmptyKind(5, { ...base, keyword: '  ' })).toBe('first')
  })

  it('关键词优先于筛选（同时存在时判 search）', () => {
    expect(definitionEmptyKind(5, { ...base, keyword: 'k', kind: 'atomic' })).toBe('search')
  })
})

describe('filterTemplates', () => {
  it('status=all 全量返回', () => {
    const list = [tpl({ id: 'a' }), tpl({ id: 'b', status: 'disabled' })]
    expect(filterTemplates(list, baseTpl,
      catalog,
    )).toHaveLength(2)
  })

  it('status 等值筛', () => {
    const list = [tpl({ id: 'a' }), tpl({ id: 'b', status: 'disabled' })]
    expect(filterTemplates(list, { ...baseTpl, status: 'disabled' },
      catalog,
    ).map((x) => x.id)).toEqual(['b'])
  })

  it('关键词命中 name', () => {
    const list = [tpl({ id: 'a', name: '高级岗模板' }), tpl({ id: 'b', name: '初级岗模板' })]
    expect(filterTemplates(list, { ...baseTpl, keyword: '高级' },
      catalog,
    ).map((x) => x.id)).toEqual(['a'])
  })

  it('关键词命中 metricName', () => {
    const list = [tpl({ id: 'a', name: 'x', metricName: '面试轮次' }), tpl({ id: 'b', name: 'y', metricName: '薪资' })]
    expect(filterTemplates(list, { ...baseTpl, keyword: '面试' },
      catalog,
    ).map((x) => x.id)).toEqual(['a'])
  })

  it('关键词命中运算符标签', () => {
    const list = [tpl({ id: 'a', operators: ['IN'] }), tpl({ id: 'b', operators: ['GTE'] })]
    expect(filterTemplates(list, { ...baseTpl, keyword: '大于等于' },
      catalog,
    ).map((x) => x.id)).toEqual(['b'])
  })

  it('status 与关键词为 AND 关系', () => {
    const list = [
      tpl({ id: 'a', name: '目标', status: 'disabled' }),
      tpl({ id: 'b', name: '目标', status: 'enabled' }),
    ]
    expect(filterTemplates(list, { keyword: '目标', status: 'disabled' },
      catalog,
    ).map((x) => x.id)).toEqual(['a'])
  })
})

describe('pageSlice', () => {
  const list = Array.from({ length: 25 }, (_, i) => i + 1)

  it('首页取前 N 条', () => {
    expect(pageSlice(list, 1, 10)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  })

  it('第二页取第 11-20 条', () => {
    expect(pageSlice(list, 2, 10)).toEqual([11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
  })

  it('末页不足 pageSize 时按 maxStart 起点补满（保留原实现的满页策略）', () => {
    // maxStart = 25 - 10 = 15 → slice(15, 25)，与前页有重叠但保证分页条稳定
    expect(pageSlice(list, 3, 10)).toEqual([16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
  })

  it('页码越界钳制到 maxStart，不返回空数组', () => {
    expect(pageSlice(list, 99, 10)).toEqual([16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
  })

  it('空列表返回空数组', () => {
    expect(pageSlice([], 1, 10)).toEqual([])
  })

  it('页码为 0 或负数时起始为负 → 返回空数组（不越界读）', () => {
    expect(pageSlice(list, 0, 10)).toEqual([])
    expect(pageSlice(list, -5, 10)).toEqual([])
  })

  it('条数少于 pageSize 时整表返回', () => {
    expect(pageSlice([1, 2, 3], 1, 20)).toEqual([1, 2, 3])
  })
})

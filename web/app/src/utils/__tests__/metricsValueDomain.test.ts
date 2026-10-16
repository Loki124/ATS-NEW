/**
 * metricsValueDomain.test.ts — 值域分段枚举与校验 单测。
 *
 * 覆盖从 useMetricsWorkspace.ts 下沉的业务规则：
 *   - computeDateDomain：日期型分段枚举（含单边区间、步进、截断上限）
 *   - buildDomainItems：数值型分段枚举（含开放上界、步长兜底）
 *   - dateSegmentIssues：日期型逐条校验 + 重叠检测
 *   - numericSegmentIssues：数值型逐条校验 + 重叠检测
 *   - domainErrorText / domainSummaryTagText：聚合文案
 */
import { describe, it, expect } from 'vitest'
import {
  computeDateDomain,
  buildDomainItems,
  dateSegmentIssues,
  numericSegmentIssues,
  domainErrorText,
  domainSummaryTagText,
  DATE_ENUM_LIMIT,
  DATE_ENUM_HARD_LIMIT,
  calcUnitFor,
} from '../metricsValueDomain'

// 纯函数不接 i18n 的 t，改注入「已解析好的文案函数」；identity mock 让断言只关心选键逻辑。
const labels = {
  domainCount: (n: number) => `COUNT(${n})`,
  domainCountTruncated: (total: number, shown: number) => `TRUNC(${total}/${shown})`,
  domainStepRequired: () => 'STEP_REQ',
  domainStepPositiveInt: () => 'STEP_POS_INT',
  domainBoundRequired: () => 'BOUND_REQ',
  domainRelativeRequired: () => 'REL_REQ',
  domainFromBeforeTo: () => 'FROM_BEFORE_TO',
  domainOverlap: () => 'OVERLAP',
  domainMaxGtMin: () => 'MAX_GT_MIN',
  domainStepPositive: () => 'STEP_POS',
  domainStepInteger: () => 'STEP_INT',
  domainSegmentOverlap: () => 'SEG_OVERLAP',
}
const abs = (date: string) => ({ type: 'absolute', date, n: null, unit: '日' })

describe('computeDateDomain', () => {
  it('双边区间按步进枚举（含端点）', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('2024-01-01'), to: abs('2024-01-03'), step: 1, stepUnit: '日' }],
      granularity: '日',
    })
    expect(r.total).toBe(3)
    expect(r.items.map((i) => i.text)).toEqual(['2024-01-01', '2024-01-02', '2024-01-03'])
  })

  it('只有 from → 产出「起」边界项', () => {
    const r = computeDateDomain({ segments: [{ from: abs('2024-01-01'), to: null, step: 1 }], granularity: '日', })
    expect(r.total).toBe(1)
    expect(r.items[0].text).toBe('2024-01-01起')
  })

  it('只有 to → 产出「及以前」边界项', () => {
    const r = computeDateDomain({ segments: [{ from: null, to: abs('2024-01-01'), step: 1 }], granularity: '日', })
    expect(r.total).toBe(1)
    expect(r.items[0].text).toBe('2024-01-01及以前')
  })

  it('双边皆空 → 该段跳过', () => {
    expect(computeDateDomain({ segments: [{ from: null, to: null, step: 1 }], granularity: '日', }).total).toBe(0)
  })

  it('from > to 的段跳过', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('2024-03-01'), to: abs('2024-01-01'), step: 1, stepUnit: '日' }],
      granularity: '日',
    })
    expect(r.total).toBe(0)
  })

  it('step <= 0 兜底为 1', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('2024-01-01'), to: abs('2024-01-03'), step: 0, stepUnit: '日' }],
      granularity: '日',
    })
    expect(r.total).toBe(3)
  })

  it('按年粒度步进', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('2020-01-01'), to: abs('2022-01-01'), step: 1, stepUnit: '年' }],
      granularity: '年',
    })
    expect(r.items.map((i) => i.text)).toEqual(['2020', '2021', '2022'])
  })

  it('items 受 DATE_ENUM_LIMIT 截断但 total 统计真实总数', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('2024-01-01'), to: abs('2030-01-01'), step: 1, stepUnit: '日' }],
      granularity: '日',
    })
    expect(r.items).toHaveLength(DATE_ENUM_LIMIT)
    expect(r.total).toBeGreaterThan(DATE_ENUM_LIMIT)
  })

  it('total 触达硬上限即停止枚举', () => {
    const r = computeDateDomain({
      segments: [{ from: abs('1900-01-01'), to: abs('2024-01-01'), step: 1, stepUnit: '日' }],
      granularity: '日',
    })
    expect(r.total).toBeLessThanOrEqual(DATE_ENUM_HARD_LIMIT)
  })

  it('空 segments 返回空结果', () => {
    expect(computeDateDomain({ segments: [], granularity: '日', })).toEqual({ items: [], total: 0 })
  })
})

describe('buildDomainItems', () => {
  it('闭区间按步长枚举', () => {
    expect(buildDomainItems({ segments: [{ min: 1, max: 3, step: 1 }], unit: '岁', isDiscrete: true }))
      .toEqual([{ text: '1岁', value: '1' }, { text: '2岁', value: '2' }, { text: '3岁', value: '3' }])
  })

  it('max 为空 → 开放上界项', () => {
    expect(buildDomainItems({ segments: [{ min: 5, max: null, step: 1 }], unit: '岁', isDiscrete: true }))
      .toEqual([{ text: '5岁以上', value: '5+' }])
  })

  it('max <= min 的段跳过', () => {
    expect(buildDomainItems({ segments: [{ min: 3, max: 3, step: 1 }], unit: '岁', isDiscrete: true })).toEqual([])
  })

  it('离散型 step<=0 兜底为 1', () => {
    expect(buildDomainItems({ segments: [{ min: 1, max: 3, step: null }], unit: '', isDiscrete: true })).toHaveLength(3)
  })

  it('连续型 step<=0 兜底为 0.5', () => {
    expect(buildDomainItems({ segments: [{ min: 1, max: 2, step: 0 }], unit: '', isDiscrete: false }))
      .toEqual([{ text: '1', value: '1' }, { text: '1.5', value: '1.5' }, { text: '2', value: '2' }])
  })

  it('min 非有限数 → 跳过', () => {
    expect(buildDomainItems({ segments: [{ min: 'abc', max: 3, step: 1 }], unit: '', isDiscrete: true })).toEqual([])
  })

  it('多段结果顺序拼接', () => {
    const r = buildDomainItems({
      segments: [{ min: 1, max: 2, step: 1 }, { min: 10, max: 11, step: 1 }], unit: '段', isDiscrete: true,
    })
    expect(r.map((i) => i.value)).toEqual(['1', '2', '10', '11'])
  })

  it('空 segments 返回空数组', () => {
    expect(buildDomainItems({ segments: [], unit: '', isDiscrete: true })).toEqual([])
  })
})

describe('dateSegmentIssues', () => {
  const seg = (p: any) => ({ from: abs('2024-01-01'), to: abs('2024-01-05'), step: 1, ...p })

  it('合法分段无错误', () => {
    expect(dateSegmentIssues([seg({})],
    labels,
    )).toEqual([null])
  })

  it('step 缺失 → 必填', () => {
    expect(dateSegmentIssues([seg({ step: null })],
    labels,
    )[0]).toBe('STEP_REQ')
  })

  it('step 为 0 / 负数 / 小数 → 正整数', () => {
    expect(dateSegmentIssues([seg({ step: 0 })],
    labels,
    )[0]).toBe('STEP_POS_INT')
    expect(dateSegmentIssues([seg({ step: -1 })],
    labels,
    )[0]).toBe('STEP_POS_INT')
    expect(dateSegmentIssues([seg({ step: 1.5 })],
    labels,
    )[0]).toBe('STEP_POS_INT')
  })

  it('双边皆空 → 边界必填', () => {
    expect(dateSegmentIssues([seg({ from: null, to: null })],
    labels,
    )[0]).toBe('BOUND_REQ')
  })

  it('相对边界缺 n → 相对量必填', () => {
    expect(dateSegmentIssues([seg({ from: { type: 'relative', date: null, n: null, unit: '日' } })],
    labels,
    )[0])
      .toBe('REL_REQ')
  })

  it('from >= to → 顺序错误', () => {
    expect(dateSegmentIssues([seg({ from: abs('2024-02-01'), to: abs('2024-01-01') })],
    labels,
    )[0])
      .toBe('FROM_BEFORE_TO')
    expect(dateSegmentIssues([seg({ from: abs('2024-01-01'), to: abs('2024-01-01') })],
    labels,
    )[0])
      .toBe('FROM_BEFORE_TO')
  })

  it('相邻区间重叠 → 后一段标重叠', () => {
    const r = dateSegmentIssues([
      seg({ from: abs('2024-01-01'), to: abs('2024-01-10') }),
      seg({ from: abs('2024-01-05'), to: abs('2024-01-20') }),
    ],
    labels,
    )
    expect(r[0]).toBeNull()
    expect(r[1]).toBe('OVERLAP')
  })

  it('区间不相邻 → 均可通过', () => {
    const r = dateSegmentIssues([
      seg({ from: abs('2024-01-01'), to: abs('2024-01-10') }),
      seg({ from: abs('2024-01-11'), to: abs('2024-01-20') }),
    ],
    labels,
    )
    expect(r).toEqual([null, null])
  })

  it('已有错误优先，不被重叠覆盖', () => {
    const r = dateSegmentIssues([
      seg({ from: abs('2024-01-01'), to: abs('2024-01-10') }),
      seg({ from: abs('2024-01-05'), to: abs('2024-01-20'), step: null }),
    ],
    labels,
    )
    expect(r[1]).toBe('STEP_REQ')
  })

  it('结果长度与分段数一致', () => {
    expect(dateSegmentIssues([seg({}), seg({}), seg({})],
    labels,
    )).toHaveLength(3)
  })
})

describe('numericSegmentIssues', () => {
  it('合法分段无错误', () => {
    expect(numericSegmentIssues([{ min: 1, max: 3, step: 1 }], true,
    labels,
    )).toEqual([null])
  })

  it('max <= min → 上界须大于下界', () => {
    expect(numericSegmentIssues([{ min: 3, max: 3, step: 1 }], true,
    labels,
    )[0]).toBe('MAX_GT_MIN')
  })

  it('单边区间不校验上下界', () => {
    expect(numericSegmentIssues([{ min: 3, max: null, step: 1 }], true,
    labels,
    )).toEqual([null])
  })

  it('step 缺失 → 必填', () => {
    expect(numericSegmentIssues([{ min: 1, max: 3, step: '' }], true,
    labels,
    )[0]).toBe('STEP_REQ')
  })

  it('step <= 0 → 正数', () => {
    expect(numericSegmentIssues([{ min: 1, max: 3, step: -1 }], true,
    labels,
    )[0]).toBe('STEP_POS')
  })

  it('连续型允许小数 step', () => {
    expect(numericSegmentIssues([{ min: 1, max: 3, step: 0.5 }], false,
    labels,
    )).toEqual([null])
  })

  it('离散型 step 必须为整数', () => {
    expect(numericSegmentIssues([{ min: 1, max: 3, step: 0.5 }], true,
    labels,
    )[0]).toBe('STEP_INT')
  })

  it('区间重叠 → 后一段标记', () => {
    const r = numericSegmentIssues([
      { min: 1, max: 10, step: 1 },
      { min: 5, max: 20, step: 1 },
    ], true,
    labels,
    )
    expect(r[1]).toBe('SEG_OVERLAP')
  })

  it('输入顺序乱时按 min 排序后再判重叠', () => {
    const r = numericSegmentIssues([
      { min: 50, max: 60, step: 1 },
      { min: 1, max: 55, step: 1 },
    ], true,
    labels,
    )
    expect(r[0]).toBe('SEG_OVERLAP')
  })
})

describe('domainErrorText', () => {
  it('无错误 → 空串', () => {
    expect(domainErrorText([null, null])).toBe('')
  })

  it('带段号聚合，多段以；分隔', () => {
    expect(domainErrorText([null, 'E1', 'E2'])).toBe('段2：E1；段3：E2')
  })
})

describe('domainSummaryTagText', () => {
  it('非日期型用候选数', () => {
    expect(domainSummaryTagText(false, 3, 0, labels)).toBe('COUNT(3)')
  })

  it('日期型未截断时用真实总数', () => {
    expect(domainSummaryTagText(true, 5, 5, labels)).toBe('COUNT(5)')
  })

  it('日期型截断时走截断文案', () => {
    expect(domainSummaryTagText(true, 40, 500, labels)).toBe('TRUNC(500/40)')
  })
})

describe('calcUnitFor', () => {
  it('月 / 年 有换算枚举值', () => {
    expect(calcUnitFor('月')).toBe('month')
    expect(calcUnitFor('年')).toBe('year')
  })

  it('日无换算 → 空串', () => {
    expect(calcUnitFor('日')).toBe('')
  })
})

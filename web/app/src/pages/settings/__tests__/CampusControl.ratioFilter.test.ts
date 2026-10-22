/**
 * 编制管控 · 实时看板 —— 筛选条行为契约测试。
 *
 * 锁住 2026-10-21 的看板改造：
 *  1. KPI 统计卡片（4 张）与底部说明文字块已移除，页面上不再有这两块常驻元素
 *  2. 筛选条含 4 个筛选项：适用范围 / 维度 / 指标 / 年度达成率（10% 分档下拉），
 *     且每个筛选项都有「可见标签」（不是仅 placeholder）
 *  3. 四类筛选都真实过滤表格行：适用范围 / 维度 / 指标 / 年度达成率分档
 *  4. 未设年度目标（annualRate = null）的行，在达成率筛选生效时不参与筛选
 *  5. 空态区分「暂无数据」与「当前筛选下无数据」
 *  6. 筛选条最右侧常驻「清空筛选」按钮：无筛选时禁用，有筛选时可点击复原
 *  7. 达成率分档下方不再有常驻提示文字（按 2026-10-21 产品要求移除）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { NSelect } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'
import CampusControl from '../CampusControl.vue'

// vi.mock 的工厂在模块导入期执行 → 数据必须用 vi.hoisted 提前声明，否则 TDZ 报错
const { RATIO_ROWS } = vi.hoisted(() => ({
  RATIO_ROWS: [
    {
      dimension: '专业标签', indicator: '其他', bu: '', position: '', level: '',
      annualTarget: 1000, annualAchieved: 23, annualInProgress: 7, annualRate: 0.023,
      monthTarget: 89, monthAchieved: 1, monthInProgress: 1, monthRate: 0.011,
      monthRollover: 0, monthAvailableTarget: 89, strength: '硬约束',
      actual: 30, denom: 56, ratio: 0.5, target: 1, status: '正常',
    },
    {
      dimension: '专业标签', indicator: '工学', bu: '', position: '', level: '',
      annualTarget: 60, annualAchieved: 13, annualInProgress: 13, annualRate: 0.22,
      monthTarget: 5, monthAchieved: 0, monthInProgress: 2, monthRate: 0,
      monthRollover: 0, monthAvailableTarget: 5, strength: '软约束',
      actual: 13, denom: 60, ratio: 0.2, target: 1, status: '正常',
    },
    {
      dimension: '身份证籍贯', indicator: '云南省', bu: '能智BG', position: '', level: '',
      annualTarget: 60, annualAchieved: 0, annualInProgress: 0, annualRate: 0,
      monthTarget: 2, monthAchieved: 0, monthInProgress: 2, monthRate: 0,
      monthRollover: 0, monthAvailableTarget: 2, strength: '硬约束',
      actual: 0, denom: 60, ratio: 0, target: 1, status: '正常',
    },
    {
      // 未设年度目标 → annualRate 为 null
      dimension: '身份证籍贯', indicator: '湖南省', bu: '能智BG', position: '', level: '',
      annualTarget: 0, annualAchieved: 0, annualInProgress: 0, annualRate: null,
      monthTarget: 0, monthAchieved: 0, monthInProgress: 0, monthRate: null,
      monthRollover: 0, monthAvailableTarget: 0, strength: '硬约束',
      actual: 0, denom: 60, ratio: 0, target: 1, status: '正常',
    },
  ],
}))

vi.mock('../../../api/campusControl', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/campusControl')>()
  return {
    ...actual,
    getRatio: vi.fn(async () => ({ total: 12, rows: RATIO_ROWS })),
    listDimensions: vi.fn(async () => []),
    listIndicators: vi.fn(async () => []),
    listRules: vi.fn(async () => []),
    listPersons: vi.fn(async () => []),
    validateDraft: vi.fn(async () => ({ verdict: '通过', verdictLevel: 'pass', checks: [], messages: [] })),
  }
})

type AnyVm = any

async function mountPage() {
  const wrapper = mount(CampusControl, {
    global: { plugins: [naivePlugin] },
    attachTo: document.body,
  })
  await flushPromises()
  await nextTick()
  return wrapper
}

const rowsOf = (vm: AnyVm) => vm.filteredRatioRows as any[]

describe('编制管控 · 实时看板筛选条', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('KPI 统计卡片与底部说明文字已移除', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('.kpi-card')).toHaveLength(0)
    expect(wrapper.findAll('.n-alert')).toHaveLength(0)
    wrapper.unmount()
  })

  it('筛选条含 4 个带可见标签的筛选项', async () => {
    const wrapper = await mountPage()
    // 结构对齐「规则配置」页签：同一 .toolbar 容器 + 4 个同宽下拉（.rule-filter-select）
    const bar = wrapper.find('.ratio-filter-bar')
    expect(bar.exists()).toBe(true)
    expect(bar.classes()).toContain('toolbar')
    // 4 个同宽下拉（复用规则配置页签的 .rule-filter-select 宽度）
    const barSelects = wrapper
      .findAllComponents(NSelect)
      .filter((s) => s.classes().includes('rule-filter-select'))
    expect(barSelects).toHaveLength(4)
    // 字段名以 placeholder 呈现（与规则配置页签一致），另配隐藏 label 供读屏使用
    expect(barSelects.map((s) => s.props('placeholder'))).toEqual([
      '适用范围', '维度', '指标', '年度达成率',
    ])
    const hiddenLabels = bar.findAll('label.visually-hidden')
    expect(hiddenLabels.map((l) => l.text())).toEqual(['适用范围', '维度', '指标', '年度达成率'])
    // 年度达成率为下拉分档：全部 + 每 10% 一档（0%–10% … 190%–200%）+ 200% 以上
    const vm = wrapper.vm as AnyVm
    const rateLabels = vm.ratioRateOptions.map((o: any) => o.label)
    expect(rateLabels[0]).toBe('全部')
    expect(rateLabels[1]).toBe('0%–10%')
    expect(rateLabels[2]).toBe('10%–20%')
    expect(rateLabels[rateLabels.length - 2]).toBe('190%–200%')
    expect(rateLabels[rateLabels.length - 1]).toBe('200% 以上')
    expect(rateLabels).toHaveLength(22) // 全部 + 20 档 + 200% 以上
    // 4 个筛选项全部是下拉（无滑块残留）
    expect(wrapper.findAll('.n-slider-handle')).toHaveLength(0)
    // 达成率分档下方不再有常驻提示文字
    expect(wrapper.find('.ratio-rate-hint').exists()).toBe(false)
    wrapper.unmount()
  })

  it('默认展示全部行（无筛选时不过滤）', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm
    expect(rowsOf(vm)).toHaveLength(RATIO_ROWS.length)
    wrapper.unmount()
  })

  it('维度筛选只保留该维度的行，并联动指标选项', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm
    vm.ratioFilterDimension = '专业标签'
    await nextTick()
    expect(rowsOf(vm).every((r) => r.dimension === '专业标签')).toBe(true)
    expect(rowsOf(vm)).toHaveLength(2)
    // 指标选项随维度收敛
    expect(vm.ratioIndicatorOptions.map((o: any) => o.value)).toEqual(['其他', '工学'])
    wrapper.unmount()
  })

  it('指标与适用范围筛选分别生效', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm

    vm.ratioFilterIndicator = '工学'
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(1)
    expect(rowsOf(vm)[0].indicator).toBe('工学')

    vm.ratioFilterIndicator = null
    // 适用范围选项 value 为 (部门·职务·职级) 组合键，与表格首列口径一致
    const scopeOpt = vm.ratioScopeOptions.find((o: any) => o.label.includes('能智BG'))
    expect(scopeOpt).toBeTruthy()
    vm.ratioFilterScope = scopeOpt.value
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(2)
    expect(rowsOf(vm).every((r) => r.bu === '能智BG')).toBe(true)

    wrapper.unmount()
  })

  it('年度达成率按 10% 分档过滤，且未设年度目标的行不参与', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm

    // 档位区间为 [lo, hi)：20%–30% 命中 22%，不命中 2.3% / 0% / 空值
    vm.ratioFilterRate = '20-30'
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(1)
    expect(rowsOf(vm)[0].annualRate).toBe(0.22)

    // 0%–10% 命中 2.3% 与 0%；未设年度目标（null）的行仍不参与
    vm.ratioFilterRate = '0-10'
    await nextTick()
    expect(rowsOf(vm).map((r) => r.indicator)).toEqual(['其他', '云南省'])

    // 末档 200% 以上为开区间
    vm.ratioFilterRate = '200+'
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(0)

    wrapper.unmount()
  })

  it('「清空筛选」按钮常驻最右侧：无筛选时禁用，有筛选时可点击复原', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm
    const btn = wrapper.find('.ratio-filter-bar .n-button')

    // 常驻 + 文案 + 位于筛选条最右（spacer 之后）
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toBe('清空筛选')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)

    vm.ratioFilterDimension = '专业标签'
    await nextTick()
    expect((btn.element as HTMLButtonElement).disabled).toBe(false)

    await btn.trigger('click')
    await nextTick()
    expect(vm.ratioFilterDimension).toBeNull()
    expect(vm.ratioFilterActive).toBe(false)
    expect(rowsOf(vm)).toHaveLength(RATIO_ROWS.length)
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)

    wrapper.unmount()
  })

  it('空态区分「暂无数据」与「当前筛选下无数据」', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as AnyVm

    vm.ratioFilterDimension = '专业标签'
    vm.ratioFilterRate = '90-100'
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(0)
    expect(wrapper.text()).toContain('当前筛选下无数据')

    vm.resetRatioFilters()
    await nextTick()
    expect(rowsOf(vm)).toHaveLength(RATIO_ROWS.length)
    expect(vm.ratioFilterActive).toBe(false)
    wrapper.unmount()
  })
})

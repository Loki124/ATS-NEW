/**
 * 轮岗资源 · 「统计概览」面板回归测试（2026-10-22）
 *
 * 锁四件事：
 * ① **数据源**：真实接口优先；真实为空 → 兜底示例数据（仓库既有 `useCampusMock` 约定）；
 * ② **版式三段式**：顶部总体概览条 + 指标视图切换 + 明细表；
 * ③ **列结构**：7 个列分组 / 22 个叶子列；视图切换只渲染该主题的列组（不再横跨全表）；
 * ④ **数值口径**：比率按百分比展示、分母为 0 显示「—」（不是 0%）；BG 跨行合并。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { NDataTable } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'
import { buildMockResourceStats } from '../../../mocks/campusStats'

/** 接口桩：默认返回空（触发示例兜底），用例内可覆盖。 */
const apiMock = vi.hoisted(() => ({
  fetchStatsOverview: vi.fn(async (): Promise<any> => ({
    rows: [],
    totals: null,
    unassignedDemand: 0,
  })),
}))

vi.mock('../../../api/campusRotation', () => ({
  fetchStatsOverview: apiMock.fetchStatsOverview,
}))

import ResourceStatsOverview from '../ResourceStatsOverview.vue'

/** 一行真实数据（够断言用）。 */
function realRow(over: Record<string, any> = {}) {
  return {
    bgGroup: '能电BG',
    bgTotal: 12,
    buName: '能良出行',
    demand: 100,
    fixed: 40,
    lost: 5,
    fillRate: 0.4,
    onboard: 90,
    offboard: 10,
    active: 80,
    retainRate: 0.888,
    offCS: 1,
    offAnchor: 2,
    offOther: 3,
    onCS: 4,
    onAnchor: 5,
    onOther: 6,
    male: 10,
    female: 8,
    intendMale: 12,
    intendFemale: 9,
    femaleRatio: 0.428,
    bgSpan: 1,
    ...over,
  }
}

async function mountPanel() {
  const w = mount(ResourceStatsOverview, {
    global: { plugins: [createPinia(), naivePlugin], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

describe('统计概览 · 数据源', () => {
  beforeEach(() => {
    apiMock.fetchStatsOverview.mockReset()
    apiMock.fetchStatsOverview.mockResolvedValue({ rows: [], totals: null, unassignedDemand: 0 })
  })

  it('① 真实接口有数据时渲染真实数据（不落示例兜底）', async () => {
    const rows = [realRow()]
    apiMock.fetchStatsOverview.mockResolvedValue({
      rows: [realRow({ bgGroup: '整体', buName: '整体', bgTotal: null }), ...rows],
      totals: realRow({ bgGroup: '整体', buName: '整体', bgTotal: null, demand: 100 }),
      unassignedDemand: 0,
    })
    const w = await mountPanel()
    const body = w.findAll('.n-data-table-tbody').map((t) => t.text()).join('|')
    expect(body).toContain('能良出行')
    // 整体行不进表（概览条承担），表里只有明细行
    expect(body).not.toContain('整体')
  }, 20000)

  it('② 真实数据为空 → 兜底示例数据（36 行明细）', async () => {
    const w = await mountPanel()
    const bodyRows = w.findAll('.n-data-table-tbody tr')
    const mock = buildMockResourceStats()
    expect(bodyRows.length).toBe(mock.length - 1) // 减去「整体」行
    expect(w.find('.n-data-table-tbody').text()).toContain('能良出行')
  }, 20000)

  it('③ 概览条取「整体」汇总值（真实模式）', async () => {
    apiMock.fetchStatsOverview.mockResolvedValue({
      rows: [
        realRow({ bgGroup: '整体', buName: '整体', bgTotal: null, demand: 986, fillRate: 0.348 }),
        realRow(),
      ],
      totals: realRow({ bgGroup: '整体', buName: '整体', bgTotal: null, demand: 986, fillRate: 0.348 }),
      unassignedDemand: 7,
    })
    const w = await mountPanel()
    const kpi = w.find('.kpi').text()
    expect(kpi).toContain('986')
    expect(kpi).toContain('34.8%')
    // 未归属需求要提示出来（不静默丢弃）
    expect(kpi).toContain('7 人校招需求未能归属')
  }, 20000)
})

describe('统计概览 · 版式', () => {
  beforeEach(() => {
    apiMock.fetchStatsOverview.mockReset()
    apiMock.fetchStatsOverview.mockResolvedValue({ rows: [], totals: null, unassignedDemand: 0 })
  })

  it('① 顶部总体概览条 6 个指标位', async () => {
    const w = await mountPanel()
    expect(w.findAll('.kpi__cell')).toHaveLength(6)
    const labels = w.findAll('.kpi__label').map((n) => n.text())
    expect(labels).toEqual(['业务需求', '满足率', '入职', '留存率', '在职', '女生比'])
  }, 20000)

  it('② 指标视图切换：5 个视图，默认「全部指标」', async () => {
    const w = await mountPanel()
    const switches = w.findAll('.n-radio-button').map((n) => n.text())
    expect(switches).toEqual(['全部指标', '需求与定岗', '入离职', '轮岗分布', '性别与意向'])
    expect(w.find('.n-radio-button--checked').text()).toBe('全部指标')
  }, 20000)

  it('③ 全部指标视图：7 个列分组 + 21 个叶子列（两行表头）', async () => {
    const w = await mountPanel()
    const headRows = w.findAll('.n-data-table-thead tr')
    expect(headRows.length).toBe(2)
    const groupTitles = headRows[0].findAll('th').map((th) => th.text())
    for (const g of ['组织', '26年需求', '26届入离职情况', '26届离职分布(轮岗部门)', '26届在职分布(当前)', '性别分布(当前)', '意向BU']) {
      expect(groupTitles.join('|')).toContain(g)
    }
    // 叶子列 21 = 组织2 + 需求4 + 入离职4 + 分布6 + 性别与意向5
    // （原表「26年需求」组里两列同名的「满足率」已收敛为一列）
    const leafCount = headRows[1].findAll('th').length
    expect(leafCount).toBe(21)
  }, 20000)

  it('④ 切到「需求与定岗」只渲染组织 + 需求两组列（不再横跨全表）', async () => {
    const w = await mountPanel()
    const allScrollX = w.findComponent(NDataTable).props('scrollX') as number
    const labels = w.findAll('.n-radio-button').map((n) => n.text())
    const idx = labels.findIndex((t) => t === '需求与定岗')
    const input = w.findAll('.n-radio-button input')[idx]
    ;(input.element as HTMLInputElement).checked = true
    await input.trigger('change')
    await flushPromises()
    const head = w.find('.n-data-table-thead').text()
    expect(head).toContain('组织')
    expect(head).toContain('26年需求')
    expect(head).not.toContain('26届在职分布')
    // scroll-x 随视图收窄：组织(290) + 需求(356) = 646，远小于「全部指标」的 1882
    const scrollX = w.findComponent(NDataTable).props('scrollX') as number
    expect(scrollX).toBe(646)
    expect(scrollX).toBeLessThan(allScrollX)
  }, 20000)
})

describe('统计概览 · 数值与合并', () => {
  beforeEach(() => {
    apiMock.fetchStatsOverview.mockReset()
    apiMock.fetchStatsOverview.mockResolvedValue({ rows: [], totals: null, unassignedDemand: 0 })
  })

  it('① 比率按百分比展示，且带量度条（transform scaleX）', async () => {
    const w = await mountPanel()
    // 整体行的三个比率在**概览条**里（表体只放明细行）
    const kpi = w.find('.kpi').text()
    expect(kpi).toContain('34.8%') // 满足率 343/986
    expect(kpi).toContain('88.5%') // 留存率 814/920
    expect(kpi).toContain('33.9%') // 女生比 276/814
    // 表体里也有比率（明细行）
    expect(w.find('.n-data-table-tbody').text()).toMatch(/\d+\.\d%/)
    // 量度条存在，且用 transform 表达长度（不动画 width）
    const fills = w.findAll('.stats-rate__fill')
    expect(fills.length).toBeGreaterThan(0)
    const style = fills[0].attributes('style') ?? ''
    expect(style).toContain('scaleX')
  }, 20000)

  it('② 分母为 0 的比率显示「—」（不是 0%），且不画条', async () => {
    const w = await mountPanel()
    const text = w.find('.n-data-table-tbody').text()
    expect(text).toContain('—')
    // 「招才人力」业务需求=0 → 满足率「—」
    const noneCells = w.findAll('.stats-rate__value--none')
    expect(noneCells.length).toBeGreaterThan(0)
  }, 20000)

  it('③ BG 跨行合并：td[rowspan] 真实存在（能电BG 覆盖 8 行）', async () => {
    const w = await mountPanel()
    const spanned = w.findAll('td[rowspan]')
    expect(spanned.length).toBeGreaterThan(0)
    const spans = spanned.map((td) => Number(td.attributes('rowspan'))).sort((a, b) => b - a)
    expect(spans).toContain(8) // 能电BG 组：7 个 BU + 1 个 BG汇总
    expect(spans).toContain(2) // 能战BG 组
  }, 20000)

  it('④ 真实模式下的比率与合并同样成立', async () => {
    apiMock.fetchStatsOverview.mockResolvedValue({
      rows: [
        realRow({ bgGroup: '整体', buName: '整体', bgTotal: null }),
        realRow({ bgSpan: 2 }),
        realRow({ bgGroup: '', buName: 'BU2', bgSpan: 0 }),
      ],
      totals: realRow({ bgGroup: '整体', buName: '整体', bgTotal: null }),
      unassignedDemand: 0,
    })
    const w = await mountPanel()
    expect(w.findAll('td[rowspan]').length).toBeGreaterThan(0)
    expect(w.find('.n-data-table-tbody').text()).toContain('40.0%')
  }, 20000)
})

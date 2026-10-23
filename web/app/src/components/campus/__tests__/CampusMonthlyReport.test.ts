/**
 * 月报提交与评分页（CampusMonthlyReport）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 提交视图加载完成 → 渲染「我的月报」列表（月份 / 状态 / 综合分）
 *  2. 「提交月报」→ 确认框写明后果 → 调用 submit 端点
 *  3. 评分视图：打开评分弹窗 → 5 子项实时汇总业务导师分 / 成长导师分 / 综合分（逆向清单 A7）
 *  4. 保存评分 → 调用 score 端点
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusMonthlyReport from '../../../pages/campus/CampusMonthlyReport.vue'

const apiGet = vi.fn()
const apiPost = vi.fn()

vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: (...args: any[]) => apiPost(...args),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

/** 月报行（草稿状态 → 可提交）。 */
const draftReport = {
  id: 'r1',
  person: 'p1',
  personName: '员工16',
  classRoomName: '2610 班',
  ym: '2026-07',
  submittedAt: null,
  status: 'draft',
  businessScore: 0,
  growthScore: 0,
  finalScore: 0,
  comment: '本月完成客服轮岗',
}

/** 待评分月报（已提交）。 */
const submittedReport = {
  ...draftReport,
  id: 'r2',
  status: 'submitted',
  submittedAt: '2026-08-01 10:00:00',
}

const getCall = (fragment: string) => apiGet.mock.calls.find((c: any[]) => String(c[0]).includes(fragment))

describe('CampusMonthlyReport 行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiGet.mockResolvedValue({ data: { data: [draftReport] } })
    apiPost.mockResolvedValue({ data: { data: draftReport } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusMonthlyReport, {
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('① 提交视图加载完成 → 渲染我的月报列表（月份 / 状态）', async () => {
    const wrapper = await mountPage()
    expect(getCall('/campus-assessment/monthly-reports/')).toBeTruthy()
    const tbody = wrapper.find('.n-data-table-tbody')
    expect(tbody.exists()).toBe(true)
    expect(tbody.text()).toContain('2026-07')
    expect(tbody.text()).toContain('员工16')
    expect(tbody.text()).toContain('待提交')
  }, 20000)

  it('② 「提交月报」→ 确认框写明后果 → 调用 submit 端点', async () => {
    const wrapper = await mountPage()
    const rowBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '上报月报')
    expect(rowBtn).toBeTruthy()
    await rowBtn!.trigger('click')
    await flushPromises()

    // 确认框必须写明后果（R-106 / R-204）
    expect(wrapper.text()).toContain('进入待评分状态')

    const buttons = wrapper.findAll('button').filter((b) => b.text() === '上报月报')
    await buttons[buttons.length - 1].trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/campus-assessment/monthly-reports/r1/submit/', {})
  }, 20000)

  it('③ 评分弹窗实时汇总业务导师分 / 成长导师分 / 综合分', async () => {
    apiGet.mockImplementation(async (_url: string, cfg: any) => {
      // 评分视图带 status=submitted 查询参数（参数在 config.params，不在 url 里）
      if (cfg?.params?.status === 'submitted') return { data: { data: [submittedReport] } }
      return { data: { data: [draftReport] } }
    })
    const wrapper = await mountPage()
    const tab = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '月报评分')
    expect(tab).toBeTruthy()
    await tab!.trigger('click')
    await flushPromises()

    const scoreBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '月报评分')
    expect(scoreBtn).toBeTruthy()
    await scoreBtn!.trigger('click')
    await flushPromises()

    // 5 个子项 + 角色选择
    expect(wrapper.text()).toContain('案例')
    expect(wrapper.text()).toContain('可执行')

    // 直接驱动表单状态，验证实时汇总（A7：综合 = 业务×0.7 + 成长×0.3）
    const vm = wrapper.vm as any
    vm.scoreForm.sub.case = 20
    vm.scoreForm.sub.insight = 18
    await flushPromises()

    const values = wrapper.findAll('.score-value').map((n) => n.text())
    expect(values[0]).toBe('38') // 业务导师分 = 20 + 18
    expect(values[1]).toBe('0') // 成长导师分未评
    expect(values[2]).toBe('26.6') // 38 × 0.7

    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存评分')
    expect(saveBtn).toBeTruthy()
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/campus-assessment/monthly-reports/r2/score/', {
      role: 'business',
      case: 20,
      insight: 18,
      problem: 0,
      clarity: 0,
      executable: 0,
      comment: '',
    })
  }, 20000)
})

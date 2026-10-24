/**
 * 考勤管理页（CampusAttendance）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 每日打卡排名加载完成 → 渲染排名行（含「与第1名差距」列）
 *  2. 无打卡记录 → 渲染空态（与「暂无数据」文案不同）
 *  3. 切到「月度汇总」页签 → 调用 attendance-monthly 端点
 *  4. R-202：每个视图恰好 1 个实心主操作（导出），其余按钮非 primary
 *  5. 导出：本地生成 CSV（不依赖后端导出接口）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusAttendance from '../../../pages/campus/CampusAttendance.vue'

const apiGet = vi.fn()

vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

/** 每日打卡排名行（契约 §2.2 daily-ranking/）。 */
const dailyRow = {
  id: 'ar1',
  person: 'p1',
  personName: '员工16',
  classRoomName: '2610 班',
  punchTime: '08:52',
  status: '正常',
  gapToFirst: 0,
}

/** 月度考勤汇总行。 */
const monthlyRow = {
  id: 'am1',
  person: 'p1',
  personName: '员工16',
  classRoomName: '2610 班',
  dept: '客服部',
  ym: '2026-07',
  attendDays: 21,
  lateCount: 1,
  leaveDays: 0,
  status: '正常',
}

/** 找出指定 URL 的 GET 调用。 */
const getCall = (fragment: string) => apiGet.mock.calls.find((c: any[]) => String(c[0]).includes(fragment))

describe('CampusAttendance 行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiGet.mockResolvedValue({ data: { data: [dailyRow] } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusAttendance, {
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('① 每日打卡排名加载完成 → 渲染排名行与「与第1名差距」列', async () => {
    const wrapper = await mountPage()
    expect(getCall('/campus-assessment/attendance-records/daily-ranking/')).toBeTruthy()
    const tbody = wrapper.find('.n-data-table-tbody')
    expect(tbody.exists()).toBe(true)
    expect(tbody.text()).toContain('员工16')
    expect(tbody.text()).toContain('08:52')
    // 「与第1名差距」列头存在
    expect(wrapper.find('.n-data-table-thead').text()).toContain('与第1名差距')
  }, 20000)

  it('② 无打卡记录 → 渲染空态（区别于「暂无数据」）', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('没有打卡记录')
  }, 20000)

  it('③ 切到「月度汇总」页签 → 调用月度汇总端点并渲染出勤数据', async () => {
    apiGet.mockImplementation(async (url: string) => {
      if (String(url).includes('attendance-monthly')) return { data: { data: [monthlyRow] } }
      return { data: { data: [dailyRow] } }
    })
    const wrapper = await mountPage()
    const tab = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '月度汇总')
    expect(tab).toBeTruthy()
    await tab!.trigger('click')
    await flushPromises()

    expect(getCall('/campus-assessment/attendance-monthly/')).toBeTruthy()
    const tbody = wrapper.find('.n-data-table-tbody')
    expect(tbody.text()).toContain('客服部')
    expect(tbody.text()).toContain('21')
  }, 20000)

  it('④ R-202：每个视图恰好 1 个实心主操作，其余按钮降级为默认/ghost', async () => {
    const wrapper = await mountPage()

    // 每日打卡排名视图（naive 的 show:lazy 页签同时只渲染当前页签）
    const dailyPane = wrapper.find('.n-tab-pane')
    expect(dailyPane.exists()).toBe(true)
    const dailyPrimary = dailyPane
      .findAll('button')
      .filter((b) => b.classes().includes('n-button--primary-type'))
    expect(dailyPrimary.length).toBe(1)
    expect(dailyPrimary[0].text()).toContain('导出打卡记录')

    const tab = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '月度汇总')
    await tab!.trigger('click')
    await flushPromises()

    const monthlyPane = wrapper.find('.n-tab-pane')
    const monthlyPrimary = monthlyPane
      .findAll('button')
      .filter((b) => b.classes().includes('n-button--primary-type'))
    expect(monthlyPrimary.length).toBe(1)
    expect(monthlyPrimary[0].text()).toContain('导出月度汇总')
  }, 20000)

  it('⑤ 点「导出打卡记录」→ 本地生成 CSV（含当前视图数据）', async () => {
    const blobs: any[] = []
    const origCreate = URL.createObjectURL
    const origRevoke = URL.revokeObjectURL
    ;(URL as any).createObjectURL = (b: any) => {
      blobs.push(b)
      return 'blob:mock'
    }
    ;(URL as any).revokeObjectURL = () => {}
    try {
      const wrapper = await mountPage()
      const btn = wrapper.findAll('button').find((b) => b.text().includes('导出打卡记录'))
      expect(btn).toBeTruthy()
      await btn!.trigger('click')
      await flushPromises()

      expect(blobs.length).toBe(1)
      const csv = await blobs[0].text()
      expect(csv).toContain('员工16')
      expect(csv).toContain('打卡时间')
    } finally {
      ;(URL as any).createObjectURL = origCreate
      ;(URL as any).revokeObjectURL = origRevoke
    }
  }, 20000)
})

/**
 * 考勤管理页（CampusAttendance）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 每日打卡排名加载完成 → 渲染排名行（含「与第1名差距」列）
 *  2. 无打卡记录 → 渲染空态（与「暂无数据」文案不同）
 *  3. 切到「月度汇总」页签 → 调用 attendance-monthly 端点
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
})

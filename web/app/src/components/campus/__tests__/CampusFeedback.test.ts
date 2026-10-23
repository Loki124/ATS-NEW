/**
 * 反馈记录页（CampusFeedback）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 4 张统计卡渲染（总数 / 处理中 / 已解决·已闭环 / 含证据记录）
 *  2. 列表加载完成 → 渲染记录行；搜索框把关键词映射到 kw 查询参数
 *  3. 「办结记录」→ 调用 resolve 端点
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusFeedback from '../../../pages/campus/CampusFeedback.vue'

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

/** 反馈记录行（契约 §2.1 FeedbackRecord）。 */
const feedbackRow = {
  id: 'f1',
  date: '2026-07-12',
  person: 'p1',
  personName: '员工16',
  reporterName: '张老师',
  category: 'issue',
  type: '迟到',
  content: '本月迟到 2 次，未提前报备',
  handling: '班主任已沟通',
  status: '处理中',
  attachments: ['聊天记录截图'],
  handlerName: '',
  handledAt: null,
}

/** 概览统计（stats/overview/）。 */
const stats = {
  feedbackTotal: 49,
  feedbackPending: 12,
  feedbackResolved: 37,
  feedbackWithEvidence: 8,
  attendDays: 0,
  lateCount: 0,
  leaveDays: 0,
}

const getCall = (fragment: string) => apiGet.mock.calls.find((c: any[]) => String(c[0]).includes(fragment))

describe('CampusFeedback 行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiGet.mockImplementation(async (url: string) => {
      if (String(url).includes('stats/overview')) return { data: { data: stats } }
      return { data: { data: [feedbackRow] } }
    })
    apiPost.mockResolvedValue({ data: { data: { ...feedbackRow, status: '已解决' } } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusFeedback, {
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('① 4 张统计卡渲染统计数值', async () => {
    const wrapper = await mountPage()
    expect(getCall('/campus-assessment/stats/overview/')).toBeTruthy()
    const cards = wrapper.findAll('.stat-card')
    expect(cards.length).toBe(4)
    const text = wrapper.find('.stat-row').text()
    expect(text).toContain('反馈总数')
    expect(text).toContain('处理中')
    expect(text).toContain('已解决·已闭环')
    expect(text).toContain('含证据记录')
    expect(text).toContain('49')
    expect(text).toContain('12')
  }, 20000)

  it('② 列表渲染反馈记录行，搜索关键词映射到 kw 参数', async () => {
    const wrapper = await mountPage()
    const tbody = wrapper.find('.n-data-table-tbody')
    expect(tbody.exists()).toBe(true)
    expect(tbody.text()).toContain('员工16')
    expect(tbody.text()).toContain('迟到')
    expect(tbody.text()).toContain('处理中')

    const input = wrapper.find('input')
    expect(input.exists()).toBe(true)
    await input.setValue('迟到')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索记录')
    expect(searchBtn).toBeTruthy()
    await searchBtn!.trigger('click')
    await flushPromises()

    const calls = apiGet.mock.calls.filter((c: any[]) => String(c[0]).includes('feedback-records'))
    expect(calls.length).toBeGreaterThan(1)
    expect(calls[calls.length - 1][1]?.params?.kw).toBe('迟到')
  }, 20000)

  it('③ 「办结记录」→ 调用 resolve 端点', async () => {
    const wrapper = await mountPage()
    const resolveBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '办结记录')
    expect(resolveBtn).toBeTruthy()
    await resolveBtn!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/campus-assessment/feedback-records/f1/resolve/', {})
  }, 20000)
})

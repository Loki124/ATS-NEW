/**
 * 校招生活动竞技页（CampusActivity）· 行为契约测试。
 *
 * 锁住：
 *  1. 两个页签（活动列表 / 我的成绩）
 *  2. 活动列表列（名称 / 类型 / 日期 / 状态 / 奖励）与行内容
 *  3. 活动评分录入：提交载荷（活动 / 校招生 / 得分 / 奖励）
 *  4. 我的成绩表列（我的成绩 / 排名 / 奖励）
 *  5. 空态二分
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusActivity from '../../../pages/campus/CampusActivity.vue'

const { notifyCreate } = vi.hoisted(() => ({ notifyCreate: vi.fn() }))

const apiGet = vi.fn()
const apiPost = vi.fn()
const apiPut = vi.fn()
const apiDelete = vi.fn()

vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: (...args: any[]) => apiPost(...args),
    put: (...args: any[]) => apiPut(...args),
    delete: (...args: any[]) => apiDelete(...args),
  },
}))

vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  const stub = () => ({ info: vi.fn(), success: vi.fn(), warning: vi.fn(), error: vi.fn(), loading: vi.fn() })
  return {
    ...actual,
    useDialog: () => ({ ...stub(), create: vi.fn() }),
    useMessage: stub,
    useNotification: () => ({ create: notifyCreate }),
  }
})

const activity = {
  id: 'a1',
  name: '青说演说家',
  type: '演讲赛',
  date: '2026-10-18',
  status: '进行中',
  reward: '+3 分',
  rule: '限时 5 分钟演讲',
  enabled: true,
}

const activityScore = {
  id: 'as1',
  activity: 'a1',
  activityName: '青说演说家',
  person: 'p1',
  personName: '张一鸣',
  score: 88,
  reward: '+3 分',
  rank: 2,
}

describe('CampusActivity 活动页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/activity-scores/')) return Promise.resolve({ data: { data: [activityScore] } })
      if (url.includes('/activities/')) return Promise.resolve({ data: { data: [activity] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: activity } })
    apiPut.mockResolvedValue({ data: { data: activity } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusActivity, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 两个页签 = 活动列表 / 我的成绩', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['活动列表', '我的成绩'])
  }, 20000)

  it('② 活动列表列齐全，行内容按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('活动名称')
    expect(heads).toContain('类型')
    expect(heads).toContain('日期')
    expect(heads).toContain('状态')
    expect(heads).toContain('奖励')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('青说演说家')
    expect(body).toContain('演讲赛')
    expect(body).toContain('2026-10-18')
    expect(body).toContain('进行中')
    expect(body).toContain('+3 分')
  }, 20000)

  it('③ 录入活动成绩 → POST /campus-learning/activity-scores/', async () => {
    const wrapper = await mountPage()
    const vm0 = wrapper.vm as any
    vm0.activeTab = 'mine'
    await flushPromises()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('录入成绩'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.scoreForm.activity = 'a1'
    vm.scoreForm.person = 'p1'
    vm.scoreForm.score = 92
    vm.scoreForm.reward = '+3 分'
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存成绩'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-learning/activity-scores/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ activity: 'a1', person: 'p1', score: 92, reward: '+3 分' })
  }, 20000)

  it('④ 我的成绩表列 = 活动 / 校招生 / 我的成绩 / 排名 / 奖励', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'mine'
    await vm.loadScores()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('我的成绩')
    expect(heads).toContain('排名')
    expect(heads).toContain('奖励')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('张一鸣')
    expect(body).toContain('88')
    expect(body).toContain('2')
  }, 20000)

  it('⑤ 空态二分：无数据 = 暂无数据；筛选无结果 = 没有符合筛选条件的活动', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('暂无数据')

    const vm = wrapper.vm as any
    vm.activitySearch = '不存在的活动'
    await vm.loadActivities()
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合筛选条件的活动')
  }, 20000)
})

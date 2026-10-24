/**
 * 校招内定岗跟踪与定岗安排页（CampusPlacementTrack）· 行为契约测试。
 *
 * 锁住：
 *  1. 四个页签（花名册 / 目标 / 数据 / 考核）
 *  2. 花名册列（姓名 / 届数 / 校招批次 / 定岗部门 / 岗位 / 定岗日期 / 目标 / 最近考核 / 状态）
 *  3. 新增目标：提交载荷（record / name / metric / targetValue / weight）
 *  4. 目标表列（目标名称 / 衡量指标 / 目标值 / 权重 / 截止日期 / 状态）
 *  5. 空态二分
 *  6. 【R-105】草稿：恢复上次未提交的目标 + 提供「清空」出口；提交成功后立即清除
 *  7. 【R-221】校验提示就近落在字段旁（图标 + 文字双通道），不再只靠全局 toast
 *  8. 【R-203】写入失败三段式（人话标题 + 数据安全说明 + 折叠详情 + 复制）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusPlacementTrack from '../../../pages/campus/CampusPlacementTrack.vue'

const { notifyCreate, msg } = vi.hoisted(() => ({
  notifyCreate: vi.fn(),
  msg: {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  },
}))

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
  return {
    ...actual,
    useDialog: () => ({ ...msg, create: vi.fn() }),
    useMessage: () => msg,
    // 与真实 API 同形：create 返回带 destroy 的通知实例
    useNotification: () => ({
      create: (...args: any[]) => {
        notifyCreate(...args)
        return { destroy: vi.fn() }
      },
    }),
  }
})

const record = {
  id: 'r1',
  person: 'p1',
  personName: '张一鸣',
  className: '2610 班',
  batch: '2026秋招',
  dept: '直播业务部',
  positionName: '直播运营',
  placeDate: '2026-09-01',
  trackYears: 1,
  latestPerf: 'A',
  status: '跟踪中',
}

const goal = {
  id: 'g1',
  record: 'r1',
  name: '出勤率达标',
  metric: '出勤率',
  targetValue: '≥ 95%',
  weight: 40,
  dueDate: '2026-12-31',
  status: '进行中',
}

const metric = {
  id: 'm1',
  record: 'r1',
  ym: '2026-09',
  metric: '出勤率',
  actualValue: '96%',
  remark: '全勤',
}

const assessment = {
  id: 'as1',
  record: 'r1',
  period: '2026 年第三季度',
  score: 88,
  perfLevel: 'A',
  assessedAt: '2026-10-01',
  comment: '表现稳定',
}

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusPlacementTrack 定岗跟踪页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    msg.info.mockReset()
    msg.success.mockReset()
    msg.warning.mockReset()
    msg.error.mockReset()
    localStorage.clear()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/placement-records/')) return Promise.resolve({ data: { data: [record] } })
      if (url.includes('/placement-goals/')) return Promise.resolve({ data: { data: [goal] } })
      if (url.includes('/placement-metrics/')) return Promise.resolve({ data: { data: [metric] } })
      if (url.includes('/placement-assessments/')) return Promise.resolve({ data: { data: [assessment] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: goal } })
    apiPut.mockResolvedValue({ data: { data: goal } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPlacementTrack, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 四个页签 = 花名册 / 目标 / 数据 / 考核', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['花名册', '目标', '数据', '考核'])
  }, 20000)

  it('② 花名册列齐全，行内容按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('姓名')
    expect(heads).toContain('届数')
    expect(heads).toContain('校招批次')
    expect(heads).toContain('定岗部门')
    expect(heads).toContain('岗位')
    expect(heads).toContain('定岗日期')
    expect(heads).toContain('目标')
    expect(heads).toContain('最近考核')
    expect(heads).toContain('状态')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('张一鸣')
    expect(body).toContain('26 届')
    expect(body).toContain('2026秋招')
    expect(body).toContain('直播业务部')
    expect(body).toContain('2026-09-01')
    expect(body).toContain('跟踪中')
  }, 20000)

  it('③ 新增目标：选记录 + 填目标 → POST /campus-placement/placement-goals/', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    vm.goalRecord = 'r1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增目标'))!.trigger('click')
    await flushPromises()

    const nameInput = formItem(wrapper, '目标名称')?.find('input')
    await nameInput!.setValue('直播时长达标')
    const metricInput = formItem(wrapper, '衡量指标')?.find('input')
    await metricInput!.setValue('月直播时长')
    const valueInput = formItem(wrapper, '目标值')?.find('input')
    await valueInput!.setValue('≥ 60 小时')
    vm.goalForm.weight = 30
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存目标'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-placement/placement-goals/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({
      record: 'r1',
      name: '直播时长达标',
      metric: '月直播时长',
      targetValue: '≥ 60 小时',
      weight: 30,
    })
  }, 20000)

  it('④ 目标表列 = 目标名称 / 衡量指标 / 目标值 / 权重 / 截止日期 / 状态', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    await vm.loadGoals()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('目标名称')
    expect(heads).toContain('衡量指标')
    expect(heads).toContain('目标值')
    expect(heads).toContain('权重')
    expect(heads).toContain('截止日期')
    expect(heads).toContain('状态')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('出勤率达标')
    expect(body).toContain('≥ 95%')
    expect(body).toContain('40%')
  }, 20000)

  it('⑤ 数据与考核页签各自渲染对应列', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'metric'
    await vm.loadMetrics()
    await flushPromises()
    let heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('月份')
    expect(heads).toContain('完成值')
    expect(wrapper.find('.n-data-table-tbody').text()).toContain('96%')

    vm.activeTab = 'assessment'
    await vm.loadAssessments()
    await flushPromises()
    heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('考核周期')
    expect(heads).toContain('绩效等级')
    expect(heads).toContain('评语')
  }, 20000)

  it('⑥ 空态二分：无数据 = 暂无数据；筛选无结果 = 没有符合筛选条件的定岗记录', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('暂无数据')

    const vm = wrapper.vm as any
    vm.rosterSearch = '不存在的人'
    await vm.loadRecords()
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合筛选条件的定岗记录')
  }, 20000)

  it('⑦【R-105】草稿：恢复上次未提交的目标内容，并提供「清空」出口', async () => {
    localStorage.setItem(
      'draft:campus-placement-track-goal',
      JSON.stringify({
        _ts: Date.now(),
        _data: {
          name: '直播时长达标',
          metric: '月直播时长',
          targetValue: '≥ 60 小时',
          weight: 30,
          dueDateTs: null,
          status: '未开始',
        },
      }),
    )

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    vm.goalRecord = 'r1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增目标'))!.trigger('click')
    await flushPromises()

    expect(vm.goalForm.name).toBe('直播时长达标')
    expect(vm.goalForm.metric).toBe('月直播时长')
    expect(vm.goalForm.weight).toBe(30)

    // 「已恢复」提示带「清空」出口
    expect(notifyCreate).toHaveBeenCalled()
    const opts = notifyCreate.mock.calls[0][0]
    expect(opts.title).toBe('已恢复上次填写的内容')
    expect(opts.action).toBeTruthy()

    // 点「清空」→ 草稿被清掉
    const vnode = opts.action()
    await vnode.props.onClick()
    expect(localStorage.getItem('draft:campus-placement-track-goal')).toBeNull()
  }, 20000)

  it('⑧【R-105】提交成功后立即清除草稿', async () => {
    localStorage.setItem(
      'draft:campus-placement-track-goal',
      JSON.stringify({
        _ts: Date.now(),
        _data: { name: '直播时长达标', metric: '月直播时长', targetValue: '≥ 60 小时', weight: 30, dueDateTs: null, status: '未开始' },
      }),
    )

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    vm.goalRecord = 'r1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增目标'))!.trigger('click')
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存目标'))!.trigger('click')
    await flushPromises()

    expect(apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-placement/placement-goals/'))).toBeTruthy()
    expect(localStorage.getItem('draft:campus-placement-track-goal')).toBeNull()
  }, 20000)

  it('⑨【R-221】校验提示就近落在字段旁（图标 + 文字双通道），不发写请求', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    vm.goalRecord = 'r1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增目标'))!.trigger('click')
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存目标'))!.trigger('click')
    await flushPromises()

    const feedback = wrapper.find('.n-form-item-feedback')
    expect(feedback.exists()).toBe(true)
    expect(feedback.text()).toContain('请填写目标名称')
    // 图标 + 文字双通道（不只靠颜色）
    expect(feedback.find('.n-icon').exists()).toBe(true)
    // 校验没过 → 不发写请求
    expect(apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-placement/placement-goals/'))).toBeUndefined()
  }, 20000)

  it('⑩【R-203】写入失败三段式：人话标题 + 数据安全说明 + 折叠详情可复制', async () => {
    apiPost.mockRejectedValue({ response: { status: 500, data: { detail: '定岗目标服务不可用' } } })

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'goal'
    vm.goalRecord = 'r1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增目标'))!.trigger('click')
    await flushPromises()

    vm.goalForm.name = '直播时长达标'
    vm.goalForm.metric = '月直播时长'
    vm.goalForm.targetValue = '≥ 60 小时'
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存目标'))!.trigger('click')
    await flushPromises()

    const state = wrapper.find('.error-state')
    expect(state.exists()).toBe(true)
    // ① 人话描述（不得以「抱歉」开头，不得直接甩原始报文）
    expect(state.find('.error-state-title').text()).toBe('创建定岗目标没有成功')
    expect(state.find('.error-state-title').text()).not.toContain('抱歉')
    // ② 你的数据是否安全
    expect(state.find('.error-state-desc').text()).toContain('你填写的内容仍保留在表单里')
    // ③ 技术详情折叠在 <details> 里 + 一键复制
    const details = state.find('details')
    expect(details.exists()).toBe(true)
    expect(details.text()).toContain('HTTP 500')
    expect(details.text()).toContain('定岗目标服务不可用')
    expect(state.findAll('button').some((b) => b.text().includes('复制错误信息'))).toBe(true)
  }, 20000)
})

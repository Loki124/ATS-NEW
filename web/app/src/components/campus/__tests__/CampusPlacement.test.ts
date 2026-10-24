/**
 * 校招内定岗双选页（CampusPlacement）· 行为契约测试。
 *
 * 锁住六步撮合状态机的**前端如实表述**（AGENTS.md R-203 / 逆向清单 §4.3）：
 *  1. 六个页签（岗位池 / 需求审核 / 志愿推送 / 人才市场 / 双选进度 / 绩效展示）
 *  2. 岗位池卡片：用人部门 / 需求数量 / 负责BP / 提交人 / 状态徽标
 *  3. 需求审核：驳回必须填原因（body 带 action=reject + note）
 *  4. 启动撮合：确认框必须写明「校招生不可再修改志愿」
 *  5. 录取：确认框必须写明「后续填报的志愿会被自动释放」
 *  6. 放弃：确认框必须写明「下一志愿自动推送」
 *  7. R-105 草稿：恢复上次填写的内容 + 「清空」出口
 *  8. R-221 字段级校验：错误就地显示（图标 + 文字），不发请求
 *  9. R-203 写入失败：三段式（人话标题 + 数据安全 + 折叠详情 + 恢复动作）
 * 10. R-204 文案：按钮不含禁用词「提交」，裸「取消」按语义改写
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusPlacement from '../../../pages/campus/CampusPlacement.vue'

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

const demand = {
  id: 'd1',
  name: '直播运营管培生',
  dept: '直播业务部',
  businessDept: '三到BG',
  headcount: 5,
  submitter: 'u1',
  submitterName: '李四',
  needStatus: '待审核',
  needDesc: '负责直播间运营',
  bizIntro: '直播业务介绍',
  deptIntro: '',
  assessReq: '',
  needTime: '2026 年 9 月到岗',
  workLocation: '杭州',
  bp: 'u2',
  bpName: '王五',
  scopeType: 'all',
  scopeBatch: '',
  scopeIntentDepts: [],
  openEnabled: false,
  openStart: null,
  openEnd: null,
  openBatchNo: '',
}

const flow = { id: 'f1', batch: '2026秋招', started: false, startTime: null, wishLimit: 2 }

const applications = [
  {
    id: 'ap1',
    person: 'p1',
    personName: '张一鸣',
    className: '2610 班',
    avgScore: 88.5,
    position: 'd1',
    positionName: '直播运营管培生',
    businessDept: '三到BG',
    order: 1,
    channel: '志愿',
    status: '推送中',
    pushedAt: '2026-10-22T08:00:00Z',
    pushedBy: 'u2',
    decision: null,
    decidedAt: null,
  },
  {
    id: 'ap2',
    person: 'p2',
    personName: '李四',
    className: '2611 班',
    avgScore: 76,
    position: 'd1',
    positionName: '直播运营管培生',
    businessDept: '三到BG',
    order: 1,
    channel: '志愿',
    status: '人才市场',
    pushedAt: '2026-10-20T08:00:00Z',
    pushedBy: 'u2',
    decision: null,
    decidedAt: null,
  },
]

const person = {
  id: 'p1',
  code: 'C00000001',
  name: '张一鸣',
  employeeId: '0008740',
  bu: '三到BG',
  school: '211',
  sex: '男',
  major: '工学',
  month: '8月',
  status: '在职',
  expectedEntryDate: null,
  actualEntryDate: null,
  position: '',
  level: '',
  headTeacher: null,
  headTeacherName: '',
  classRoom: null,
  classRoomName: '2610 班',
  mentor: null,
  mentorName: '',
  schoolName: '',
  education: '本科',
  phone: '',
  counted: true,
}

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusPlacement 定岗双选页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    localStorage.clear()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/position-demands/')) return Promise.resolve({ data: { data: [demand] } })
      if (url.includes('/selection-flows/')) return Promise.resolve({ data: { data: [flow] } })
      if (url.includes('/applications/')) return Promise.resolve({ data: { data: applications } })
      if (url.includes('/campus/persons/')) return Promise.resolve({ data: { data: [person] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: demand } })
    apiPut.mockResolvedValue({ data: { data: demand } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusPlacement, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 六个页签 = 岗位池 / 需求审核 / 志愿推送 / 人才市场 / 双选进度 / 绩效展示', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['岗位池', '需求审核', '志愿推送', '人才市场', '双选进度', '绩效展示'])
  }, 20000)

  it('② 岗位池卡片展示 用人部门 / 需求数量 / 负责BP / 提交人 / 状态徽标', async () => {
    const wrapper = await mountPage()
    const card = wrapper.find('.demand-card')
    expect(card.exists()).toBe(true)
    const text = card.text()
    expect(text).toContain('直播运营管培生')
    expect(text).toContain('直播业务部')
    expect(text).toContain('5 人')
    expect(text).toContain('王五')
    expect(text).toContain('李四')
    expect(text).toContain('待审核')
  }, 20000)

  it('③ 需求审核：驳回必须填原因 → POST review { action: reject, note }', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'review'
    await flushPromises()

    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('驳回需求'))!.trigger('click')
    await flushPromises()

    // 未填原因 → 拦住不发请求
    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('驳回需求'))!.trigger('click')
    await flushPromises()
    expect(apiPost.mock.calls.find((c) => String(c[0]).includes('/review/'))).toBeUndefined()

    // 填原因 → 提交
    const note = formItem(wrapper, '驳回原因')?.find('textarea')
    await note!.setValue('需求描述不完整')
    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('驳回需求'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/position-demands/d1/review/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ action: 'reject', note: '需求描述不完整' })
  }, 20000)

  it('④ 启动撮合：确认框写明「校招生不可再修改志愿」→ 确认后 POST start', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'push'
    vm.pushBatch = '2026秋招'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('启动撮合'))!.trigger('click')
    await flushPromises()

    const confirmBody = wrapper.find('.confirm-body').text()
    expect(confirmBody).toContain('校招生不可再修改志愿')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('启动撮合'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/selection-flows/f1/start/'))
    expect(call).toBeTruthy()
  }, 20000)

  it('⑤ 录取：确认框写明「后续填报的志愿会被自动释放」→ POST accept', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'push'
    vm.pushBatch = '2026秋招'
    await vm.loadPushApplications()
    await flushPromises()

    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '录取')!.trigger('click')
    await flushPromises()

    const confirmBody = wrapper.find('.confirm-body').text()
    expect(confirmBody).toContain('后续填报的志愿会被自动释放')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('确认录取'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/applications/ap1/accept/'))
    expect(call).toBeTruthy()
  }, 20000)

  it('⑥ 放弃：确认框写明「下一志愿自动推送」→ POST reject', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'push'
    vm.pushBatch = '2026秋招'
    await vm.loadPushApplications()
    await flushPromises()

    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '放弃')!.trigger('click')
    await flushPromises()

    expect(wrapper.find('.confirm-body').text()).toContain('下一志愿')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('确认放弃'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/applications/ap1/reject/'))
    expect(call).toBeTruthy()
  }, 20000)

  it('⑦ 人才市场：未被选择的校招生出现在列表里，带「采纳」操作', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'market'
    await vm.loadMarketApplications()
    await flushPromises()

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('李四')
    expect(wrapper.findAll('.n-data-table-tbody button').some((b) => b.text() === '采纳')).toBe(true)
  }, 20000)

  it('⑧ 双选进度：按校招生聚合志愿，展示双选阶段 / 填报志愿数 / 定岗结果', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'progress'
    await vm.loadProgressApplications()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('双选阶段')
    expect(heads).toContain('填报志愿')
    expect(heads).toContain('定岗结果')
    expect(heads).toContain('本人确认')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('张一鸣')
    expect(body).toContain('推送中')
  }, 20000)

  it('⑨ R-105 草稿：打开需求申请弹窗恢复上次填写的内容，并给出「清空」出口', async () => {
    localStorage.setItem(
      'draft:campus-placement-demand',
      JSON.stringify({
        _ts: Date.now(),
        _data: {
          name: '草稿岗位',
          dept: '直播业务部',
          businessDept: '三到BG',
          headcount: 3,
          needTime: '',
          workLocation: '',
          bpName: '',
          scopeType: 'all',
          scopeBatch: '',
          openEnabled: false,
          openStartTs: null,
          openEndTs: null,
          needDesc: '草稿需求描述',
          bizIntro: '',
        },
      }),
    )
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('申请发布需求'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    expect(vm.demandForm.name).toBe('草稿岗位')
    expect(vm.demandForm.needDesc).toBe('草稿需求描述')

    const created = notifyCreate.mock.calls.at(-1)
    expect(created?.[0].content).toBe('已恢复上次填写的内容')
    const actionVNode = created?.[0].action()
    expect(actionVNode.children.default()).toBe('清空')

    await actionVNode.props.onClick()
    await flushPromises()
    expect(vm.demandForm.name).toBe('')
    expect(vm.demandForm.needDesc).toBe('')
    expect(localStorage.getItem('draft:campus-placement-demand')).toBe(null)
  }, 20000)

  it('⑩ R-221 字段级校验：岗位名称为空 → 错误就地显示在名称字段旁（图标 + 文字），且不发请求', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('申请发布需求'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.demandForm.name = ''
    vm.demandForm.dept = '直播业务部'
    vm.demandForm.businessDept = '三到BG'
    vm.demandForm.needDesc = '负责直播间运营'
    await flushPromises()

    // happy-dom 无法模拟真实焦点（连裸 input 都拿不到 activeElement），
    // 这里断言「页面确实向第一个出错控件请求了焦点」。
    const focusSpy = vi.spyOn(vm.demandNameRef, 'focus')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存需求'))!.trigger('click')
    await flushPromises()

    const nameItem = formItem(wrapper, '岗位名称')
    expect(nameItem!.text()).toContain('请填写岗位名称')
    expect(nameItem!.find('.field-error .n-icon').exists()).toBe(true)

    // 焦点被送到第一个出错字段
    expect(focusSpy).toHaveBeenCalled()

    expect(apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-placement/position-demands/'))).toBeUndefined()
  }, 20000)

  it('⑪ R-203 写入失败：弹窗内三段式（人话标题 + 数据安全 + 折叠详情 + 恢复动作）', async () => {
    apiPost.mockRejectedValue({ response: { status: 500, data: { detail: '服务端原始报文' } } })
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('申请发布需求'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.demandForm.name = '直播运营管培生'
    vm.demandForm.dept = '直播业务部'
    vm.demandForm.businessDept = '三到BG'
    vm.demandForm.needDesc = '负责直播间运营'
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存需求'))!.trigger('click')
    await flushPromises()

    expect(vm.demandWriteError.title).toBe('保存需求没有成功')
    expect(vm.demandWriteError.safe).toContain('没有丢失')
    expect(vm.demandWriteError.detail).toContain('HTTP 500')
    expect(vm.demandWriteError.detail).toContain('服务端原始报文')

    const box = wrapper.find('.error-state')
    expect(box.exists()).toBe(true)
    expect(box.text()).toContain('保存需求没有成功')
    expect(box.find('.error-state-detail').exists()).toBe(true)
    expect(box.findAll('button').some((b) => b.text().includes('复制错误信息'))).toBe(true)
    expect(box.findAll('button').some((b) => b.text().includes('重新保存需求'))).toBe(true)
  }, 20000)

  it('⑫ R-204 文案：按钮不含禁用词「提交」，裸「取消」按语义改写', async () => {
    const wrapper = await mountPage()

    // 工具栏入口：动词 + 宾语，且不含「提交」
    const applyBtn = wrapper.findAll('.toolbar button').find((b) => b.text().includes('申请发布需求'))
    expect(applyBtn).toBeTruthy()
    expect(wrapper.text()).not.toContain('提交')

    // 需求申请弹窗：裸「取消」→ 取消办理
    await applyBtn!.trigger('click')
    await flushPromises()
    const demandFooter = wrapper.findAll('.modal-footer button').map((b) => b.text())
    expect(demandFooter).toContain('取消办理')
    expect(demandFooter).not.toContain('取消')

    // 驳回弹窗：裸「取消」→ 取消驳回
    const vm = wrapper.vm as any
    vm.activeTab = 'review'
    await flushPromises()
    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('驳回需求'))!.trigger('click')
    await flushPromises()
    const rejectFooter = wrapper.findAll('.modal-footer button').map((b) => b.text())
    expect(rejectFooter).toContain('取消驳回')
  }, 20000)
})

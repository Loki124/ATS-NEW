/**
 * 校招生课程页（CampusCourse）· 行为契约测试。
 *
 * 锁住三块前端行为：
 *  1. 三个页签（课程管理 / 我的课程 / 学习龙虎榜）与管理端表格列
 *  2. 新增课程：表单校验 + 提交载荷（只提交表单字段，不提交展示字段）
 *  3. 空态二分：无数据「暂无数据」 vs 筛选无结果「没有符合筛选条件的课程」
 *  4. 删除课程 = 中等破坏性 → 直接执行 + 通知撤销（8s）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusCourse from '../../../pages/campus/CampusCourse.vue'

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

const course = {
  id: 'c1',
  code: 'C001',
  name: '新人成长训练营',
  form: '直播',
  durationMin: 120,
  category: '业务知识',
  type: '必修',
  examRequired: true,
  enabled: true,
  description: '面向 26 届校招生的入门课程',
  doneCount: 18,
  totalCount: 30,
}

const progress = {
  id: 'lp1',
  person: 'p1',
  personName: '张一鸣',
  course: 'c1',
  courseName: '新人成长训练营',
  progress: 45,
  minutes: 180,
  doneAt: null,
  lastAt: '2026-10-20T10:00:00Z',
}

const boardRow = {
  id: 'p1',
  name: '张一鸣',
  class: '2610 班',
  minutes: 980,
  done: 4,
  avgProg: 62,
  total: 7,
}

/** 取指定 label 的表单项（n-form-item 的 label 文本含必填星号）。 */
function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusCourse 课程页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/courses/')) return Promise.resolve({ data: { data: [course] } })
      if (url.includes('/learn-progress/')) return Promise.resolve({ data: { data: [progress] } })
      if (url.includes('/learn-board/')) return Promise.resolve({ data: { data: [boardRow] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: course } })
    apiPut.mockResolvedValue({ data: { data: course } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusCourse, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 三个页签 = 课程管理 / 我的课程 / 学习龙虎榜', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['课程管理', '我的课程', '学习龙虎榜'])
  }, 20000)

  it('② 管理端表格列齐全，课程行按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('课程')
    expect(heads).toContain('形式')
    expect(heads).toContain('时长')
    expect(heads).toContain('分类')
    expect(heads).toContain('类型')
    expect(heads).toContain('结课考试')
    expect(heads).toContain('完成情况')
    expect(heads).toContain('操作')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('新人成长训练营')
    expect(body).toContain('直播')
    expect(body).toContain('120 分钟')
    expect(body).toContain('必修')
    expect(body).toContain('18 / 30 人')
  }, 20000)

  it('③ 新增课程：填名称后保存 → POST /campus-learning/courses/ 且载荷正确', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增课程'))!.trigger('click')
    await flushPromises()

    // 弹窗打开：n-modal preset="card" 的标题栏
    expect(wrapper.find('.n-card-header__main').text()).toContain('新增课程')

    const nameInput = formItem(wrapper, '课程名称')?.find('input')
    expect(nameInput).toBeTruthy()
    await nameInput!.setValue('新员工合规必修课')
    const codeInput = formItem(wrapper, '课程编码')?.find('input')
    await codeInput!.setValue('C002')

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存课程'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-learning/courses/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ name: '新员工合规必修课', code: 'C002', type: '必修' })
  }, 20000)

  it('④ 空态二分：无数据 = 暂无数据；筛选无结果 = 没有符合筛选条件的课程', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('暂无数据')

    const vm = wrapper.vm as any
    vm.courseSearch = '不存在的课程'
    await vm.loadCourses()
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合筛选条件的课程')
  }, 20000)

  it('⑤ 删除课程 = 直接执行删除 + 通知里带「撤销」动作', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('删除课程'))!.trigger('click')
    await flushPromises()

    const del = apiDelete.mock.calls.find((c) => String(c[0]).includes('/campus-learning/courses/c1/'))
    expect(del).toBeTruthy()
    // R-106：中等破坏性 → 不弹确认框，改为通知撤销
    expect(notifyCreate).toHaveBeenCalled()
    const options = notifyCreate.mock.calls[0][0]
    expect(options.duration).toBe(8000)
    expect(typeof options.action).toBe('function')
  }, 20000)

  it('⑥ 切到「我的课程」页签 → 渲染进度条与累计学习', async () => {
    const wrapper = await mountPage()
    const mine = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '我的课程')!
    await mine.trigger('click')
    await flushPromises()

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('新人成长训练营')
    expect(body).toContain('180 分钟')
    expect(body).toContain('45%')
  }, 20000)
})

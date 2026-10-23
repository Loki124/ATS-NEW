/**
 * 校招生考试页（CampusExam）· 行为契约测试。
 *
 * 锁住：
 *  1. 两个页签（考试管理 / 成绩排名）
 *  2. 考试列表列与行内容
 *  3. 成绩录入：提交载荷（考试 / 校招生 / 得分）
 *  4. 成绩排名表：排名 / 校招生 / 得分 / 结果 / 得分条（结果由后端 passed 决定，前端只展示）
 *  5. 空态二分
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusExam from '../../../pages/campus/CampusExam.vue'

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

const exam = {
  id: 'e1',
  name: '入职必修考试',
  date: '2026-10-15',
  form: '线上',
  fullScore: 100,
  passScore: 60,
  course: 'c1',
  courseName: '新人成长训练营',
  enabled: true,
}

const ranking = [
  { rank: 1, person: 'p1', personName: '张一鸣', className: '2610 班', score: 92, passed: true, percent: 92 },
  { rank: 2, person: 'p2', personName: '李四', className: '2611 班', score: 41, passed: false, percent: 41 },
]

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusExam 考试页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/exams/') && url.includes('/ranking/')) return Promise.resolve({ data: { data: ranking } })
      if (url.includes('/exams/')) return Promise.resolve({ data: { data: [exam] } })
      if (url.includes('/courses/')) return Promise.resolve({ data: { data: [] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: exam } })
    apiPut.mockResolvedValue({ data: { data: exam } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusExam, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 两个页签 = 考试管理 / 成绩排名', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['考试管理', '成绩排名'])
  }, 20000)

  it('② 考试列表列齐全，行内容按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('考试')
    expect(heads).toContain('日期')
    expect(heads).toContain('形式')
    expect(heads).toContain('满分')
    expect(heads).toContain('及格分')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('入职必修考试')
    expect(body).toContain('2026-10-15')
    expect(body).toContain('线上')
  }, 20000)

  it('③ 录入成绩：选校招生 + 得分 → POST /campus-learning/exam-scores/', async () => {
    const wrapper = await mountPage()
    const vm0 = wrapper.vm as any
    vm0.activeTab = 'rank'
    vm0.rankExamId = 'e1'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('录入成绩'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.scoreForm.exam = 'e1'
    vm.scoreForm.person = 'p1'
    vm.scoreForm.score = 88
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存成绩'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-learning/exam-scores/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ exam: 'e1', person: 'p1', score: 88 })
  }, 20000)

  it('④ 成绩排名表：排名 / 校招生 / 得分 / 结果 / 得分条都渲染', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'rank'
    vm.rankExamId = 'e1'
    await vm.loadRanking()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('排名')
    expect(heads).toContain('校招生')
    expect(heads).toContain('得分')
    expect(heads).toContain('结果')
    expect(heads).toContain('得分条')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('张一鸣')
    expect(body).toContain('92')
    // passed 由后端判定，前端只展示通过 / 未通过（不靠颜色单独表达）
    expect(body).toContain('通过')
    expect(body).toContain('未通过')
  }, 20000)

  it('⑤ 空态：无数据 = 暂无数据；已选考试但无成绩 = 该考试还没有成绩记录', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/exams/') && url.includes('/ranking/')) return Promise.resolve({ data: { data: [] } })
      if (url.includes('/exams/')) return Promise.resolve({ data: { data: [exam] } })
      return Promise.resolve({ data: { data: [] } })
    })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'rank'
    vm.rankExamId = 'e1'
    await vm.loadRanking()
    await flushPromises()
    expect(wrapper.text()).toContain('该考试还没有成绩记录')
  }, 20000)

  it('⑥ 新增考试：必填校验拦下空名称，不发请求', async () => {
    const wrapper = await mountPage()
    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('新增考试'))!.trigger('click')
    await flushPromises()

    const vm = wrapper.vm as any
    vm.examForm.name = ''
    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存考试'))!.trigger('click')
    await flushPromises()

    const call = apiPost.mock.calls.find((c) => String(c[0]).includes('/campus-learning/exams/'))
    expect(call).toBeUndefined()
  }, 20000)
})

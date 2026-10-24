/**
 * 月报提交与评分页（CampusMonthlyReport）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 提交视图加载完成 → 渲染「我的月报」列表（月份 / 状态 / 综合分）
 *  2. 「提交月报」→ 确认框写明后果 → 调用 submit 端点
 *  3. 评分视图：打开评分弹窗 → 5 子项实时汇总业务导师分 / 成长导师分 / 综合分（逆向清单 A7）
 *  4. 保存评分 → 调用 score 端点
 *  5. 草稿自动保存（R-105）：写月报 / 评分各自落盘 → 重开恢复 + 「清空」出口 → 提交成功后清除
 *  6. 字段级校验（R-221）：必填为空时字段旁出现「图标 + 文字」反馈，不发请求
 *  7. 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠可复制详情
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

/** 等待草稿 debounce（useFormDraft 固定 800ms）落盘。 */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** 草稿 localStorage 键（useFormDraft 约定 `draft:<命名空间>`）。 */
const CREATE_DRAFT_KEY = 'draft:campus-monthly-report-create'
const SCORE_DRAFT_KEY = 'draft:campus-monthly-report-score'

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
    localStorage.removeItem(CREATE_DRAFT_KEY)
    localStorage.removeItem(SCORE_DRAFT_KEY)
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
      // 评分视图带 pending=1 查询参数（参数在 config.params，不在 url 里）。
      // ⚠️ 口径：契约 §2.2「评分落库即置 scored」⇒ **不能**用 status 表达「待评分」
      //    （只评一侧的月报状态也是 scored），后端改用 ?pending=1（缺任一角色评分即待评分）。
      if (cfg?.params?.pending === '1') return { data: { data: [submittedReport] } }
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

  it('④ 写月报草稿（R-105）：填写后落盘 → 重开恢复 + 「清空」出口 → 提交成功后清除', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    vm.openCreate()
    await flushPromises()
    vm.createForm.comment = '本月完成客服轮岗，遇到一个客诉已闭环'
    await sleep(1000)

    const raw = localStorage.getItem(CREATE_DRAFT_KEY)
    expect(raw).toBeTruthy()
    expect(JSON.parse(raw!)._data.comment).toContain('客服轮岗')

    // 重新打开 → 恢复提示 + 内容回填
    vm.openCreate()
    await flushPromises()
    expect(vm.createForm.comment).toContain('客服轮岗')
    expect(wrapper.text()).toContain('已恢复上次填写的内容')
    expect(wrapper.findAll('button').some((b) => b.text() === '清空草稿')).toBe(true)

    // 提交成功 → 草稿立即清除
    await vm.submitCreate()
    await flushPromises()
    expect(apiPost).toHaveBeenCalled()
    expect(localStorage.getItem(CREATE_DRAFT_KEY)).toBeNull()
  }, 20000)

  it('⑤ 评分草稿按月报 id 分桶（R-105）：只恢复同一份月报的草稿', async () => {
    const other = { ...submittedReport, id: 'r3', personName: '员工17' }
    apiGet.mockImplementation(async (_url: string, cfg: any) => {
      if (cfg?.params?.pending === '1') return { data: { data: [submittedReport, other] } }
      return { data: { data: [draftReport] } }
    })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    // 给 r2 打分并写评语 → 落盘
    vm.openScore(submittedReport)
    await flushPromises()
    vm.scoreForm.comment = '本月表现良好'
    await sleep(1000)
    expect(localStorage.getItem(SCORE_DRAFT_KEY)).toBeTruthy()

    // 重新打开 r2 → 恢复评语
    vm.openScore(submittedReport)
    await flushPromises()
    expect(vm.scoreForm.comment).toBe('本月表现良好')
    expect(wrapper.text()).toContain('已恢复上次填写的内容')

    // 打开别的月报 → 不灌入 r2 的草稿
    vm.openScore(other)
    await flushPromises()
    expect(vm.scoreForm.comment).toBe('')
  }, 20000)

  it('⑥ 字段级校验（R-221）：汇报内容为空时字段旁出现反馈，不发写请求', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    vm.openCreate()
    await flushPromises()
    vm.createForm.comment = ''
    await vm.submitCreate()
    await flushPromises()

    expect(apiPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('请填写汇报内容')
    expect(wrapper.find('.n-form-item-feedback--error').exists()).toBe(true)
    expect(wrapper.find('.field-error').exists()).toBe(true)
  }, 20000)

  it('⑦ 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠可复制详情', async () => {
    apiPost.mockRejectedValue({ response: { status: 500, data: { detail: '服务器开小差了' } } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    vm.openCreate()
    await flushPromises()
    vm.createForm.comment = '本月完成客服轮岗'
    await vm.submitCreate()
    await flushPromises()

    // ① 人话描述 ② 数据是否安全
    expect(wrapper.text()).toContain('保存月报草稿没有成功')
    expect(wrapper.text()).toContain('你填写的内容仍保留在表单里')
    // ③ 技术报文折叠在「详情」里，展开后可复制
    const detailHeader = wrapper
      .findAll('.n-collapse-item__header-main')
      .find((h) => h.text().includes('详情'))
    expect(detailHeader).toBeTruthy()
    await detailHeader!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('HTTP 500 · 服务器开小差了')
    expect(wrapper.findAll('button').some((b) => b.text() === '复制错误信息')).toBe(true)
  }, 20000)

  it('⑧ 工具栏筛选控件的可访问名与可见标签一致（R-218）', async () => {
    const wrapper = await mountPage()
    const select = wrapper.find('.n-select')
    expect(select.exists()).toBe(true)
    expect(select.attributes('aria-label')).toBe('月份')
  }, 20000)
})

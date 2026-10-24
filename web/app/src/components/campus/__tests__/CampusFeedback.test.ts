/**
 * 反馈记录页（CampusFeedback）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 4 张统计卡渲染（总数 / 处理中 / 已解决·已闭环 / 含证据记录）
 *  2. 列表加载完成 → 渲染记录行；搜索框把关键词映射到 kw 查询参数
 *  3. 「办结记录」→ 调用 resolve 端点
 *  4. R-105 草稿：打开新增弹窗恢复上次填写内容，并提供「清空」出口
 *  5. R-221 字段级校验：缺必填项 → 就地标错 + 提示还差几项，不发写请求
 *  6. R-203 写入失败三段式：标题 + 数据安全说明 + 折叠技术详情（可复制）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusFeedback from '../../../pages/campus/CampusFeedback.vue'

const { notifyCreate } = vi.hoisted(() => ({ notifyCreate: vi.fn() }))

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

/** 草稿在 localStorage 里的键（useFormDraft 统一加 `draft:` 前缀）。 */
const DRAFT_KEY = 'draft:campus-feedback-create'

/** 造一份未过期草稿（_ts + _data，格式与 useFormDraft 的写入一致）。 */
function seedDraft(data: Record<string, unknown>) {
  localStorage.setItem(DRAFT_KEY, JSON.stringify({ _ts: Date.now(), _data: data }))
}

describe('CampusFeedback 行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    notifyCreate.mockReset()
    localStorage.clear()
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

  /** 打开「新增反馈记录」弹窗。 */
  const openCreateModal = async (wrapper: any) => {
    const btn = wrapper.findAll('.toolbar button').find((b: any) => b.text().includes('新增记录'))
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
  }

  /** 弹窗底部的「保存记录」按钮。 */
  const saveBtn = (wrapper: any) =>
    wrapper.findAll('button').find((b: any) => b.text().includes('保存记录'))

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

  it('④ R-105 草稿：打开新增弹窗 → 恢复上次填写的内容，并提供「清空」出口', async () => {
    seedDraft({
      person: 'p1',
      dateTs: 1758604800000,
      category: 'issue',
      type: '迟到',
      content: '本月迟到 2 次，未提前报备',
      handling: '班主任已沟通',
      evidence: '',
    })
    const wrapper = await mountPage()
    await openCreateModal(wrapper)

    // 草稿内容已回填到表单
    const vm = wrapper.vm as any
    expect(vm.formState.type).toBe('迟到')
    expect(vm.formState.content).toContain('本月迟到 2 次')

    // 提示「已恢复上次填写的内容」，并带「清空」出口
    expect(notifyCreate).toHaveBeenCalled()
    const opts = notifyCreate.mock.calls[0][0]
    expect(opts.content).toBe('已恢复上次填写的内容')
    expect(typeof opts.action).toBe('function')

    // 点「清空」→ 草稿被清掉，表单回到空白
    const vnode: any = opts.action()
    vnode.props.onClick()
    expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    expect(vm.formState.type).toBe('')
  }, 20000)

  it('⑤ R-221 字段级校验：缺必填项 → 字段旁标错 + 提示还差几项，不发写请求', async () => {
    const wrapper = await mountPage()
    await openCreateModal(wrapper)

    const btn = saveBtn(wrapper)
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()

    // 校验没过 → 不发写请求
    expect(apiPost).not.toHaveBeenCalled()

    // 错误就地显示在字段旁（图标 + 文字双通道）
    const feedbackText = wrapper
      .findAll('.n-form-item-feedback')
      .map((n: any) => n.text())
      .join('|')
    expect(feedbackText).toContain('请选择校招生')
    expect(feedbackText).toContain('请填写反馈类型')
    expect(feedbackText).toContain('请填写反馈描述')

    // 顶部给出「还有 N 项未填写」，不再静默
    expect(wrapper.find('.form-hint').text()).toContain('还有 3 项未填写')
  }, 20000)

  it('⑥ R-203 写入失败：三段式提示（标题 + 数据安全说明 + 折叠技术详情）', async () => {
    apiPost.mockRejectedValue({ response: { status: 500, data: { detail: '服务端原始报文' } } })
    const wrapper = await mountPage()
    await openCreateModal(wrapper)

    const vm = wrapper.vm as any
    vm.formState.person = 'p1'
    vm.formState.type = '迟到'
    vm.formState.content = '本月迟到 2 次，未提前报备'
    await flushPromises()

    const btn = saveBtn(wrapper)
    await btn!.trigger('click')
    await flushPromises()

    const box = wrapper.find('.write-error-wrap')
    expect(box.exists()).toBe(true)
    // ① 人话描述发生了什么
    expect(box.text()).toContain('保存反馈记录没有成功')
    // ② 用户数据是否安全
    expect(box.text()).toContain('你填写的内容仍保留在表单里')
    // ③ 技术详情折叠 + 可复制
    expect(box.find('.error-code').text()).toContain('HTTP 500 · 服务端原始报文')
    const btns = box.findAll('button').map((b: any) => b.text()).join('|')
    expect(btns).toContain('复制错误信息')
  }, 20000)
})

/**
 * 校招生考核页（CampusAssessment）行为契约测试。
 *
 * 锁住的前端行为：
 *  1. 月度数据加载态 → 有数据渲染（表格出现校招生与总分）
 *  2. 月度数据空态渲染（区分「暂无数据」文案）
 *  3. 「加减分」→ 弹窗填原因 → 调用 adjust 端点
 *  4. 「核对通过」→ 确认框 → 调用 check 端点
 *  5. 草稿自动保存（R-105）：模板表单填写后落盘 → 重开恢复 → 提交成功后清除
 *  6. 字段级校验（R-221）：必填为空时字段旁出现「图标 + 文字」反馈，不发请求
 *  7. 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠可复制详情
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusAssessment from '../../../pages/campus/CampusAssessment.vue'

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

/** 等待草稿 debounce（useFormDraft 固定 800ms）落盘。 */
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** 考核模板草稿的 localStorage 键（useFormDraft 约定 `draft:<命名空间>`）。 */
const TEMPLATE_DRAFT_KEY = 'draft:campus-assessment-template'

/** 月度考核行（字段与后端 camelCase 出参对齐）。 */
const monthlyRow = {
  id: 'ma1',
  person: 'p1',
  personName: '员工16',
  classRoom: 'cr1',
  classRoomName: '2610 班',
  dept: '客服部',
  ym: '2026-07',
  kpi: 90,
  exam: 80,
  adjust: 0,
  total: 86,
  status: 'draft',
  note: '',
}

/** 找出指定 URL 的最近一次 GET 调用参数。 */
const getCall = (fragment: string) => apiGet.mock.calls.find((c: any[]) => String(c[0]).includes(fragment))

describe('CampusAssessment 月度数据行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    apiGet.mockResolvedValue({ data: { data: [monthlyRow] } })
    apiPost.mockResolvedValue({ data: { data: monthlyRow } })
    localStorage.removeItem(TEMPLATE_DRAFT_KEY)
  })

  const mountPage = async () => {
    const wrapper = mount(CampusAssessment, {
      global: { stubs: { teleport: true } },
    })
    await flushPromises()
    return wrapper
  }

  it('① 加载完成后渲染月度数据表格（校招生 / 总分 / 状态）', async () => {
    const wrapper = await mountPage()
    // 列表端点被调用（契约 §2.2 monthly-assessments/）
    expect(getCall('/campus-assessment/monthly-assessments/')).toBeTruthy()
    const tbody = wrapper.find('.n-data-table-tbody')
    expect(tbody.exists()).toBe(true)
    expect(tbody.text()).toContain('员工16')
    expect(tbody.text()).toContain('86')
    expect(tbody.text()).toContain('待核对')
  }, 20000)

  it('② 无数据时渲染空态（未筛选=暂无数据；带筛选=无匹配结果）', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    // 默认带月份筛选 → 「筛选无结果」文案
    expect(wrapper.text()).toContain('没有符合筛选条件的月度数据')

    // 清掉筛选 → 「暂无数据」文案（两种空态文案区分开）
    const vm = wrapper.vm as any
    vm.monthlyYm = ''
    await vm.loadMonthly()
    await flushPromises()
    expect(wrapper.text()).toContain('暂无月度考核数据')
  }, 20000)

  it('③ 「加减分」→ 弹窗填写原因 → 调用 adjust 端点', async () => {
    const wrapper = await mountPage()
    const adjustBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '加减分')
    expect(adjustBtn).toBeTruthy()
    await adjustBtn!.trigger('click')
    await flushPromises()

    const textarea = wrapper.find('textarea')
    expect(textarea.exists()).toBe(true)
    await textarea.setValue('创新提案')
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存分值')
    expect(saveBtn).toBeTruthy()
    await saveBtn!.trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/campus-assessment/monthly-assessments/ma1/adjust/', {
      adjust: 0,
      reason: '创新提案',
    })
  }, 20000)

  it('④ 「核对通过」→ 确认框写明后果 → 调用 check 端点', async () => {
    const wrapper = await mountPage()
    const checkBtn = wrapper.findAll('.n-data-table-tbody button').find((b) => b.text() === '核对通过')
    expect(checkBtn).toBeTruthy()
    await checkBtn!.trigger('click')
    await flushPromises()

    // 确认框必须写明后果（R-106）
    expect(wrapper.text()).toContain('将被锁定')

    // 行内按钮与确认框按钮同名 → 取最后一个（确认框里的）
    const buttons = wrapper.findAll('button').filter((b) => b.text() === '核对通过')
    await buttons[buttons.length - 1].trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith('/campus-assessment/monthly-assessments/ma1/check/')
  }, 20000)

  it('⑤ 排名页签：列头同时给出「实际值」与「折算得分」及权重说明', async () => {
    const rankRow = {
      rank: 1,
      person: 'p1',
      personName: '员工16',
      classRoomName: '2610 班',
      actual: { kpi: 90, learn: 80, force: 85, add: 3 },
      score: { kpi: 45, learn: 24, force: 17, add: 3 },
      comp: 89,
    }
    apiGet.mockImplementation(async (url: string) => {
      if (String(url).includes('ranking/composite')) return { data: { data: [rankRow] } }
      return { data: { data: [monthlyRow] } }
    })
    const wrapper = await mountPage()
    const tab = wrapper.findAll('.n-tabs-tab').find((t) => t.text() === '排名')
    expect(tab).toBeTruthy()
    await tab!.trigger('click')
    await flushPromises()

    const rankCall = getCall('/campus-assessment/ranking/composite/')
    expect(rankCall).toBeTruthy()
    expect(rankCall![1]?.params?.dim).toBe('comp')

    // 列头由 h() 渲染（不带 data-v）→ 样式放在非 scoped 块，这里验证结构确实渲染出来
    const head = wrapper.find('.n-data-table-thead')
    expect(head.text()).toContain('KPI 实际值')
    expect(head.text()).toContain('权重 50%')
    expect(head.find('.ca-col-title').exists()).toBe(true)
    expect(wrapper.find('.n-data-table-tbody').text()).toContain('员工16')
  }, 20000)

  it('⑥ 草稿自动保存（R-105）：模板表单填写后落盘 → 重开恢复 + 给「清空」出口 → 提交成功后清除', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    // 打开「新增模板」→ 填写名称 → 等 debounce 落盘
    vm.openTemplateCreate()
    await flushPromises()
    vm.templateForm.name = '客服部第1阶段月度考核'
    await sleep(1000)

    const raw = localStorage.getItem(TEMPLATE_DRAFT_KEY)
    expect(raw).toBeTruthy()
    expect(JSON.parse(raw!)._data.name).toBe('客服部第1阶段月度考核')

    // 重新打开 → 恢复提示出现 + 内容回填
    vm.openTemplateCreate()
    await flushPromises()
    expect(vm.templateForm.name).toBe('客服部第1阶段月度考核')
    expect(wrapper.text()).toContain('已恢复上次填写的内容')
    expect(wrapper.findAll('button').some((b) => b.text() === '清空草稿')).toBe(true)

    // 提交成功 → 草稿立即清除
    vm.templateForm.items = [{ name: '业务考核', weight: 100, target: '' }]
    await vm.submitTemplate()
    await flushPromises()
    expect(apiPost).toHaveBeenCalled()
    expect(localStorage.getItem(TEMPLATE_DRAFT_KEY)).toBeNull()
  }, 20000)

  it('⑦ 字段级校验（R-221）：必填为空时字段旁出现反馈，不发写请求', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    vm.openTemplateCreate()
    await flushPromises()
    await vm.submitTemplate()
    await flushPromises()

    expect(apiPost).not.toHaveBeenCalled()
    // 反馈在字段旁（不是全局 toast）
    expect(wrapper.text()).toContain('请填写模板名称')
    expect(wrapper.find('.n-form-item-feedback--error').exists()).toBe(true)
    expect(wrapper.find('.field-error').exists()).toBe(true)
  }, 20000)

  it('⑧ 写入失败三段式（R-203）：标题 + 数据安全说明 + 折叠可复制详情', async () => {
    apiPost.mockRejectedValue({ response: { status: 500, data: { detail: '服务器开小差了' } } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any

    vm.openTemplateCreate()
    await flushPromises()
    vm.templateForm.name = '客服部第1阶段月度考核'
    vm.templateForm.items = [{ name: '业务考核', weight: 100, target: '' }]
    await vm.submitTemplate()
    await flushPromises()

    // ① 人话描述 ② 数据是否安全
    expect(wrapper.text()).toContain('保存考核模板没有成功')
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
})

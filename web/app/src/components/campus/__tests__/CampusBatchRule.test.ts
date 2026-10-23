/**
 * 校招生批次规则页（CampusBatchRule）· 行为契约测试。
 *
 * 锁住：
 *  1. 三个页签（命名规则 / 批次定义 / 区间时间轴）
 *  2. 命名模板变量按钮：点击变量追加到模板；保存 → PUT /campus/batch-naming/
 *  3. 实时预览 → GET /campus/batch-rules/preview/ 且带 snake_case 参数
 *  4. 批次定义列（批次号 / 批次名称 / 区间起始 / 区间结束 / 命中人数 / 状态）
 *  5. 区间时间轴：按月份铺开区间条，区间重叠 → 给出冲突提示
 *  6. 重算批次号两步走：先 POST recalc（**不带 apply**）出变更预览，确认后才 POST recalc { apply: true } 落库
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusBatchRule from '../../../pages/campus/CampusBatchRule.vue'

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

const ruleA = {
  id: 'b1',
  code: '202609',
  name: '2026 年 9 月批次',
  startDate: '2026-09-01',
  endDate: '2026-09-30',
  enabled: true,
  sort: 1,
}

const ruleB = {
  id: 'b2',
  code: '202610',
  name: '2026 年 10 月批次',
  startDate: '2026-10-01',
  endDate: '2026-10-31',
  enabled: true,
  sort: 2,
}

const naming = {
  template: '{YY}{MM}{SEQ}',
  seqWidth: 2,
  seqStart: 1,
  cycle: 'month',
  dateField: 'entryDate',
  autoApply: true,
}

const preview = {
  samples: ['260901', '260902'],
  rules: [{ code: '202609', name: '2026 年 9 月批次', count: 42 }],
  unmatched: 3,
  noBatch: 5,
}

const recalcResult = {
  changes: [{ person: 'p1', personName: '张一鸣', oldBatch: '202608', newBatch: '202609' }],
}

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusBatchRule 批次规则页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/batch-naming/')) return Promise.resolve({ data: { data: naming } })
      if (url.includes('/batch-rules/preview/')) return Promise.resolve({ data: { data: preview } })
      if (url.includes('/batch-rules/')) return Promise.resolve({ data: { data: [ruleA, ruleB] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockImplementation((url: string) => {
      if (String(url).includes('/batch-rules/recalc/')) return Promise.resolve({ data: { data: recalcResult } })
      return Promise.resolve({ data: { data: ruleA } })
    })
    apiPut.mockResolvedValue({ data: { data: naming } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusBatchRule, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 三个页签 = 命名规则 / 批次定义 / 区间时间轴', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['命名规则', '批次定义', '区间时间轴'])
  }, 20000)

  it('② 命名规则：变量按钮追加到模板 → 保存 → PUT /campus/batch-naming/', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.namingForm.template = '{YY}'

    const varButton = wrapper.findAll('.var-row button').find((b) => b.text().includes('{SEQ}'))!
    await varButton.trigger('click')
    await flushPromises()
    expect(vm.namingForm.template).toBe('{YY}{SEQ}')

    await wrapper.findAll('.form-actions button').find((b) => b.text().includes('保存规则'))!.trigger('click')
    await flushPromises()

    const call = apiPut.mock.calls.find((c) => String(c[0]).includes('/campus/batch-naming/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ template: '{YY}{SEQ}', seqWidth: 2, seqStart: 1, cycle: 'month', dateField: 'entryDate' })
  }, 20000)

  it('③ 实时预览：GET /campus/batch-rules/preview/ 且参数为 snake_case', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.namingForm.seqWidth = 3
    await vm.previewNaming()
    await flushPromises()

    const call = apiGet.mock.calls.filter((c) => String(c[0]).includes('/batch-rules/preview/')).pop()
    expect(call).toBeTruthy()
    expect(call![1]?.params).toMatchObject({
      template: '{YY}{MM}{SEQ}',
      seq_width: 3,
      seq_start: 1,
      cycle: 'month',
      date_field: 'entryDate',
    })
    // 预览样例展示到界面上
    expect(wrapper.text()).toContain('260901')
  }, 20000)

  it('④ 批次定义列齐全，命中人数取自 preview 的命中统计', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'rules'
    await vm.loadRules()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('批次号')
    expect(heads).toContain('批次名称')
    expect(heads).toContain('区间起始')
    expect(heads).toContain('区间结束')
    expect(heads).toContain('命中人数')
    expect(heads).toContain('状态')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('202609')
    expect(body).toContain('2026 年 9 月批次')
    expect(body).toContain('42')
  }, 20000)

  it('⑤ 区间时间轴：按月份铺开区间条，区间重叠给出冲突提示', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/batch-naming/')) return Promise.resolve({ data: { data: naming } })
      if (url.includes('/batch-rules/preview/')) return Promise.resolve({ data: { data: preview } })
      if (url.includes('/batch-rules/')) {
        // 两条区间故意重叠（9/1 - 10/15 与 9/15 - 10/31）
        return Promise.resolve({
          data: {
            data: [
              { ...ruleA, endDate: '2026-10-15' },
              { ...ruleB, startDate: '2026-09-15' },
            ],
          },
        })
      }
      return Promise.resolve({ data: { data: [] } })
    })

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'timeline'
    await vm.loadRules()
    await flushPromises()

    expect(wrapper.findAll('.timeline-bar').length).toBe(2)
    expect(wrapper.findAll('.timeline-tick').length).toBeGreaterThan(0)
    expect(wrapper.find('.issue-box').text()).toContain('区间重叠')
  }, 20000)

  it('⑥ 重算批次号两步走：先出变更预览，确认后才落库', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'rules'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('重算批次号'))!.trigger('click')
    await flushPromises()

    // 第一步：只预览，不带 apply
    const previewCall = apiPost.mock.calls.find((c) => String(c[0]).includes('/batch-rules/recalc/'))
    expect(previewCall).toBeTruthy()
    expect(previewCall![1]?.apply).toBeUndefined()

    // 预览弹窗展示「原批次 → 新批次」
    const list = wrapper.find('.recalc-list').text()
    expect(list).toContain('202608')
    expect(list).toContain('202609')

    // 第二步：确认后才带 apply: true 落库
    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('确认重算'))!.trigger('click')
    await flushPromises()

    const applyCall = apiPost.mock.calls.filter((c) => String(c[0]).includes('/batch-rules/recalc/')).pop()
    expect(applyCall![1]).toMatchObject({ apply: true })
  }, 20000)
})

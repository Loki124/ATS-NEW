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
 *  7. 【R-109】区间条用 --c-info-deep 阶（白字 8.72:1），不再用 --c-info 主色作实底（3.68:1，不达 AA）
 *  8. 【R-105】命名规则草稿：恢复上次未提交的内容 + 提供「清空」出口
 *  9. 【R-221】校验提示就近落在字段旁（图标 + 文字双通道），不再只靠全局 toast
 * 10. 【R-203】写入失败三段式（人话标题 + 数据安全说明 + 折叠详情 + 复制）
 * 11. 【R-106】按规则回写批次 → Toast 撤销（8s）+ 回滚
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import CampusBatchRule from '../../../pages/campus/CampusBatchRule.vue'

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
const apiPatch = vi.fn()
const apiDelete = vi.fn()

vi.mock('../../../utils/request', () => ({
  api: {
    get: (...args: any[]) => apiGet(...args),
    post: (...args: any[]) => apiPost(...args),
    put: (...args: any[]) => apiPut(...args),
    patch: (...args: any[]) => apiPatch(...args),
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

/* ── 对比度工具（WCAG 2.1 相对亮度）── */
function relLuminance(hex: string): number {
  const v = hex.replace('#', '')
  const ch = [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16) / 255)
  const lin = ch.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
}
function contrastRatio(a: string, b: string): number {
  const la = relLuminance(a)
  const lb = relLuminance(b)
  const [hi, lo] = la > lb ? [la, lb] : [lb, la]
  return (hi + 0.05) / (lo + 0.05)
}

const TOKENS_CSS = readFileSync(resolve(__dirname, '../../../styles/tokens.css'), 'utf8')
const PAGE_SRC = readFileSync(resolve(__dirname, '../../../pages/campus/CampusBatchRule.vue'), 'utf8')
/** 取令牌文件里某个变量的全部取值（浅色 + 暗色各一次）。 */
function tokenValues(name: string): string[] {
  return [...TOKENS_CSS.matchAll(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`, 'g'))].map((m) => m[1])
}

describe('CampusBatchRule 批次规则页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiPatch.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    msg.info.mockReset()
    msg.success.mockReset()
    msg.warning.mockReset()
    msg.error.mockReset()
    localStorage.clear()
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
    apiPatch.mockResolvedValue({ data: { data: { success: true } } })
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

  it('⑦【R-109】区间条用 --c-info-deep 阶：白字对比度 ≥ 4.5:1（旧的 --c-info 主色只有 3.68:1）', async () => {
    // 7.1 源码契约：区间条实底走 deep 阶 + on-deep 前景色，不再用主色作实底
    const barRule = PAGE_SRC.slice(PAGE_SRC.indexOf('.timeline-bar {'), PAGE_SRC.indexOf('.timeline-bar--off'))
    expect(barRule).toContain('background: var(--c-info-deep);')
    expect(barRule).toContain('color: var(--on-c-info-deep);')
    expect(barRule).not.toContain('var(--c-info);')

    // 7.2 令牌实配：浅色 + 暗色两套 deep 阶都达到 AA 4.5:1
    const deeps = tokenValues('c-info-deep')
    const onDeeps = tokenValues('on-c-info-deep')
    expect(deeps.length).toBeGreaterThan(0)
    deeps.forEach((bg, i) => {
      expect(contrastRatio(bg, onDeeps[i])).toBeGreaterThanOrEqual(4.5)
    })

    // 7.3 反证：旧写法（主色 #3B82F6 作实底 + 白字）确实不达标
    const mainColor = tokenValues('c-info')[0]
    expect(contrastRatio(mainColor, '#FFFFFF')).toBeLessThan(4.5)
  }, 20000)

  it('⑧【R-105】草稿：恢复上次未提交的命名规则，并提供「清空」出口', async () => {
    localStorage.setItem(
      'draft:campus-batch-rule-naming',
      JSON.stringify({
        _ts: Date.now(),
        _data: {
          template: '{YY}{MM}{N}',
          seqWidth: 3,
          seqStart: 2,
          cycle: 'month',
          dateField: 'entryDate',
          autoApply: false,
        },
      }),
    )

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    expect(vm.namingForm.template).toBe('{YY}{MM}{N}')
    expect(vm.namingForm.seqWidth).toBe(3)
    expect(vm.namingForm.autoApply).toBe(false)

    // 「已恢复」提示带「清空」出口
    expect(notifyCreate).toHaveBeenCalled()
    const opts = notifyCreate.mock.calls[0][0]
    expect(opts.title).toBe('已恢复上次填写的内容')
    expect(opts.action).toBeTruthy()

    // 点「清空」→ 草稿被清掉
    const vnode = opts.action()
    await vnode.props.onClick()
    expect(localStorage.getItem('draft:campus-batch-rule-naming')).toBeNull()
  }, 20000)

  it('⑨【R-105】提交成功后立即清除草稿', async () => {
    localStorage.setItem(
      'draft:campus-batch-rule-naming',
      JSON.stringify({ _ts: Date.now(), _data: { template: '{YY}', seqWidth: 2, seqStart: 1, cycle: 'month', dateField: 'entryDate', autoApply: true } }),
    )
    const wrapper = await mountPage()
    await flushPromises()

    await wrapper.findAll('.form-actions button').find((b) => b.text().includes('保存规则'))!.trigger('click')
    await flushPromises()

    expect(apiPut.mock.calls.find((c) => String(c[0]).includes('/campus/batch-naming/'))).toBeTruthy()
    expect(localStorage.getItem('draft:campus-batch-rule-naming')).toBeNull()
  }, 20000)

  it('⑩【R-221】校验提示就近落在字段旁（图标 + 文字双通道），不发写请求', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.namingForm.template = ''
    await flushPromises()

    await wrapper.findAll('.form-actions button').find((b) => b.text().includes('保存规则'))!.trigger('click')
    await flushPromises()

    const feedback = wrapper.find('.n-form-item-feedback')
    expect(feedback.exists()).toBe(true)
    expect(feedback.text()).toContain('请填写命名模板')
    // 图标 + 文字双通道（不只靠颜色）
    expect(feedback.find('.n-icon').exists()).toBe(true)
    // 校验没过 → 不发写请求
    expect(apiPut.mock.calls.find((c) => String(c[0]).includes('/campus/batch-naming/'))).toBeUndefined()
  }, 20000)

  it('⑪【R-203】写入失败三段式：人话标题 + 数据安全说明 + 折叠详情可复制', async () => {
    apiPut.mockRejectedValue({ response: { status: 500, data: { detail: '批次命名服务不可用' } } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.namingForm.template = '{YY}{MM}{SEQ}'
    await flushPromises()

    await wrapper.findAll('.form-actions button').find((b) => b.text().includes('保存规则'))!.trigger('click')
    await flushPromises()

    const state = wrapper.find('.error-state')
    expect(state.exists()).toBe(true)
    // ① 人话描述（不得以「抱歉」开头，不得直接甩原始报文）
    expect(state.find('.error-state-title').text()).toBe('保存命名规则没有成功')
    expect(state.find('.error-state-title').text()).not.toContain('抱歉')
    // ② 你的数据是否安全
    expect(state.find('.error-state-desc').text()).toContain('你填写的内容仍保留在表单里')
    // ③ 技术详情折叠在 <details> 里 + 一键复制
    const details = state.find('details')
    expect(details.exists()).toBe(true)
    expect(details.text()).toContain('HTTP 500')
    expect(details.text()).toContain('批次命名服务不可用')
    expect(state.findAll('button').some((b) => b.text().includes('复制错误信息'))).toBe(true)
  }, 20000)

  it('⑫【R-106】按规则回写批次 → Toast 撤销（8s），撤销会回滚已回写的批次', async () => {
    apiPost.mockImplementation((url: string) => {
      if (String(url).includes('/batch-rules/apply/')) {
        return Promise.resolve({
          data: {
            data: {
              filled: 1,
              skipped: 0,
              unmatched: 0,
              details: [{ person_id: 'p1', code: 'C93000001', name: '张三', batch: '202609' }],
            },
          },
        })
      }
      return Promise.resolve({ data: { data: ruleA } })
    })

    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'rules'
    await flushPromises()

    await wrapper.findAll('.toolbar button').find((b) => b.text().includes('按规则回写批次'))!.trigger('click')
    await flushPromises()

    expect(notifyCreate).toHaveBeenCalled()
    const opts = notifyCreate.mock.calls[0][0]
    expect(opts.duration).toBe(8000)
    expect(opts.content).toContain('已按规则回写 1 人')
    expect(opts.action).toBeTruthy()

    // 点「撤销」→ 逐个把被回写人员的批次清回空值
    const vnode = opts.action()
    await vnode.props.onClick()
    await flushPromises()
    expect(apiPatch).toHaveBeenCalledWith('/campus/persons/p1/', { batch: '' })
  }, 20000)
})

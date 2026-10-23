/**
 * 校招生交易和结算页（CampusSettlement）· 行为契约测试。
 *
 * 锁住：
 *  1. 三个页签（收入统计 / 结算账单 / 定价管理）
 *  2. 收入统计列（月份 / 校招生 / 输出部门 / 阶段 / 出勤 / 计价规则 / 单价 / 金额 / 状态）
 *  3. 定价管理：编辑「排名分档 → 结算单价 / 底价 / 交易价允许区间」→ PUT 整个 tiers
 *  4. 结算账单：确认账单是高影响操作 → 必须先出确认框，框内写明「锁定，不可再修改」
 *  5. 空态二分
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CampusSettlement from '../../../pages/campus/CampusSettlement.vue'

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

const revenue = {
  id: 'rv1',
  person: 'p1',
  personName: '张一鸣',
  ym: '2026-09',
  outputDept: '直播业务部',
  stage: '定岗后',
  attendDays: 22,
  rule: '按出勤计价',
  unitPrice: 1200,
  amount: 26400,
  status: '已确认',
}

const bill = {
  id: 'b1',
  billNo: 'B202609001',
  businessDept: '直播业务部',
  period: '2026-09',
  personCount: 12,
  amount: 316800,
  status: '待确认',
  confirmedAt: null,
}

const scheme = {
  id: 's1',
  name: '2026 秋季定价方案',
  type: 'FIXED',
  batch: '2026秋招',
  selFlowBatch: '2026秋招',
  tiers: [{ rank: '1-10', price: 1200, floor: 1000, min: 1000, max: 1500 }],
  isDefault: true,
  enabled: true,
}

function formItem(wrapper: any, label: string) {
  return wrapper
    .findAll('.n-form-item')
    .find((n: any) => n.find('.n-form-item-label').exists() && n.find('.n-form-item-label').text().replace(/\*/g, '').trim() === label)
}

describe('CampusSettlement 结算页行为契约', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiPut.mockReset()
    apiDelete.mockReset()
    notifyCreate.mockReset()
    apiGet.mockImplementation((url: string) => {
      if (url.includes('/revenue-records/')) return Promise.resolve({ data: { data: [revenue] } })
      if (url.includes('/price-schemes/')) return Promise.resolve({ data: { data: [scheme] } })
      if (url.includes('/bills/')) return Promise.resolve({ data: { data: [bill] } })
      return Promise.resolve({ data: { data: [] } })
    })
    apiPost.mockResolvedValue({ data: { data: revenue } })
    apiPut.mockResolvedValue({ data: { data: revenue } })
    apiDelete.mockResolvedValue({ data: { success: true } })
  })

  const mountPage = async () => {
    const wrapper = mount(CampusSettlement, { global: { stubs: { teleport: true } } })
    await flushPromises()
    return wrapper
  }

  it('① 三个页签 = 收入统计 / 结算账单 / 定价管理', async () => {
    const wrapper = await mountPage()
    const tabs = wrapper.findAll('.n-tabs-tab').map((t) => t.text())
    expect(tabs).toEqual(['收入统计', '结算账单', '定价管理'])
  }, 20000)

  it('② 收入统计列齐全，台账行按接口字段渲染', async () => {
    const wrapper = await mountPage()
    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('月份')
    expect(heads).toContain('校招生')
    expect(heads).toContain('输出部门')
    expect(heads).toContain('阶段')
    expect(heads).toContain('出勤')
    expect(heads).toContain('计价规则')
    expect(heads).toContain('单价')
    expect(heads).toContain('金额')
    expect(heads).toContain('状态')

    const body = wrapper.find('.n-data-table-tbody').text()
    expect(body).toContain('2026-09')
    expect(body).toContain('张一鸣')
    expect(body).toContain('直播业务部')
    expect(body).toContain('22')
    expect(body).toContain('已确认')
  }, 20000)

  it('③ 定价管理：编辑分档 → PUT price-schemes 带整份 tiers', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'price'
    await vm.loadSchemes()
    await flushPromises()

    const heads = wrapper.findAll('.n-data-table-thead th').map((th) => th.text()).join('|')
    expect(heads).toContain('排名区间')
    expect(heads).toContain('结算单价')
    expect(heads).toContain('底价')
    expect(heads).toContain('交易价允许区间')

    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('编辑分档'))!.trigger('click')
    await flushPromises()

    const rankInput = formItem(wrapper, '排名区间')?.find('input')
    await rankInput!.setValue('1-5')
    vm.tierForm.price = 1500
    vm.tierForm.floor = 1200
    vm.tierForm.min = 1200
    vm.tierForm.max = 1800
    await flushPromises()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('保存分档'))!.trigger('click')
    await flushPromises()

    const call = apiPut.mock.calls.find((c) => String(c[0]).includes('/campus-placement/price-schemes/s1/'))
    expect(call).toBeTruthy()
    const tiers = call![1].tiers
    expect(Array.isArray(tiers)).toBe(true)
    expect(tiers[0]).toMatchObject({ rank: '1-5', price: 1500, floor: 1200, min: 1200, max: 1800 })
  }, 20000)

  it('④ 确认账单：先出确认框（写明锁定不可再修改）→ 确认后 PUT bills', async () => {
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'bill'
    await vm.loadBills()
    await flushPromises()

    await wrapper.findAll('.n-data-table-tbody button').find((b) => b.text().includes('确认账单'))!.trigger('click')
    await flushPromises()

    const confirmBody = wrapper.find('.confirm-body').text()
    expect(confirmBody).toContain('B202609001')
    expect(confirmBody).toContain('锁定')
    // 尚未确认 → 不应已发请求
    expect(apiPut.mock.calls.find((c) => String(c[0]).includes('/campus-placement/bills/'))).toBeUndefined()

    await wrapper.findAll('.modal-footer button').find((b) => b.text().includes('确认账单'))!.trigger('click')
    await flushPromises()

    const call = apiPut.mock.calls.find((c) => String(c[0]).includes('/campus-placement/bills/b1/'))
    expect(call).toBeTruthy()
    expect(call![1]).toMatchObject({ status: '已确认' })
  }, 20000)

  it('⑤ 空态二分：无数据 = 暂无数据；筛选无结果 = 没有符合筛选条件的账单', async () => {
    apiGet.mockResolvedValue({ data: { data: [] } })
    const wrapper = await mountPage()
    const vm = wrapper.vm as any
    vm.activeTab = 'bill'
    await vm.loadBills()
    await flushPromises()
    expect(wrapper.text()).toContain('暂无数据')

    vm.billStatus = '已确认'
    await vm.loadBills()
    await flushPromises()
    expect(wrapper.text()).toContain('没有符合筛选条件的账单')
  }, 20000)
})

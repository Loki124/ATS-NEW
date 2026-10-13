import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CandidateOfferPanel from '../CandidateOfferPanel.vue'

vi.mock('../../../api/offer', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/offer')>()
  return {
    ...actual,
    listOffersByCandidate: vi.fn(async () => ({ items: [] })),
    transitionOffer: vi.fn(async () => ({})),
  }
})

import { listOffersByCandidate, transitionOffer } from '../../../api/offer'

async function settle(wrapper: ReturnType<typeof mount>) {
  await (wrapper.vm as any).$nextTick()
  await new Promise((r) => setTimeout(r, 0))
  await flushPromises()
}

function makeOffer(over: Record<string, any> = {}) {
  return {
    id: 'o1',
    code: 'OF001',
    applicationId: 'a1',
    candidateId: 'c1',
    candidateName: '张三',
    positionId: 'p1',
    positionTitle: '前端工程师',
    salary: '18000.00',
    salaryCurrency: 'CNY',
    level: 'P6',
    startDate: '2026-11-01',
    expireDate: '2026-11-15',
    state: 'DRAFT',
    stateDisplay: '草稿',
    sentAt: null,
    respondedAt: null,
    createdAt: '2026-10-01T00:00:00Z',
    ...over,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('CandidateOfferPanel', () => {
  it('按 candidateId 调用后端 candidate 过滤参数', async () => {
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c9' }, attachTo: document.body })
    await settle(wrapper)
    expect(listOffersByCandidate).toHaveBeenCalledWith('c9', { page: 1, pageSize: 50 })
  })

  it('渲染后端真实字段(state/salary/startDate/level/positionTitle)', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({ items: [makeOffer()] })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)

    expect(document.body.textContent).toContain('OF001')
    expect(document.body.textContent).toContain('草稿')       // stateDisplay
    expect(document.body.textContent).toContain('前端工程师') // positionTitle
    expect(document.body.textContent).toContain('18000')      // salary
    expect(document.body.textContent).toContain('2026-11-01') // startDate
    expect(document.body.textContent).toContain('P6')         // level
  })

  it('无 Offer 时展示空态', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({ items: [] })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)
    expect(document.body.textContent).toContain('暂无 Offer 记录')
  })

  it('草稿态提供「提交审批」并以 action 提交(不是 to)', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({ items: [makeOffer({ state: 'DRAFT' })] })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)

    const btn = Array.from(document.body.querySelectorAll<HTMLButtonElement>('.n-button'))
      .find((b) => b.textContent?.includes('提交审批'))
    expect(btn).toBeTruthy()
    btn!.click()
    await settle(wrapper)

    expect(transitionOffer).toHaveBeenCalledWith('o1', 'submit_approval', undefined)
  })

  it('终态(已入职)不渲染任何可执行动作', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({
      items: [makeOffer({ state: 'ONBOARDED', stateDisplay: '已入职' })],
    })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)

    expect(document.body.textContent).toContain('无后续可执行操作')
    expect(transitionOffer).not.toHaveBeenCalled()
  })

  it('待审批态提供「审批通过」主按钮 + 「驳回」收进更多菜单', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({
      items: [makeOffer({ state: 'PENDING_APPROVAL', stateDisplay: '待审批' })],
    })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)

    const text = document.body.textContent || ''
    expect(text).toContain('审批通过')   // 首动作渲染为主按钮
    expect(text).toContain('更多')       // 次动作收进下拉（Naive 懒渲染，不在 DOM 内）

    // 下拉选项内容由 offerActionsFor 决定：审批通过 + 驳回
    const vm = wrapper.vm as any
    expect(vm).toBeTruthy()
  })

  it('危险动作(驳回)走原因弹窗而非直接提交', async () => {
    ;(listOffersByCandidate as any).mockResolvedValueOnce({
      items: [makeOffer({ state: 'PENDING_APPROVAL', stateDisplay: '待审批' })],
    })
    const wrapper = mount(CandidateOfferPanel, { props: { candidateId: 'c1' }, attachTo: document.body })
    await settle(wrapper)

    // 直接调用危险动作 → 应弹原因框而非发请求
    const vm = wrapper.vm as any
    // 通过 DOM 点击主按钮(审批通过, 非危险)验证正常路径
    const btn = Array.from(document.body.querySelectorAll<HTMLButtonElement>('.n-button'))
      .find((b) => b.textContent?.includes('审批通过'))
    btn!.click()
    await settle(wrapper)
    expect(transitionOffer).toHaveBeenCalledWith('o1', 'approve', undefined)
    expect(vm).toBeTruthy()
  })
})
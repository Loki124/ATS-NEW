import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step2Assign from '../Step2Assign.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'
import PositionChips from '@/components/common/PositionChips.vue'

// 与 AddCandidateModal.test.ts 一致: 测试环境 mock vue-i18n (否则 useI18n 报 app.use 错误)
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (k: string) => k }) }))
// 2026-09-27: mock 真实 /positions/ 端点, 验证 Step2 用的是真实数据而非硬编码 mock
vi.mock('@/api/dashboard', () => ({
  fetchPositions: vi.fn(async () => [
    { id: 'pos-1', title: '前端工程师' },
    { id: 'pos-2', title: '后端工程师' },
  ]),
}))

const baseResume = { id: 'd1', file_name: 'r1.pdf', job_id: 'j1', status: 'clean' as const, progress: 100, procPhase: null, edited: {}, parsed: { name: '张三', age: 28, edu: '本科' } as any }

describe('Step2Assign', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders apply mode toggle when multiple resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(true)
  })

  it('hides apply mode toggle for single resume', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(false)
  })

  it('renders 3 direction options', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.dopt')).toHaveLength(3)
  })

  it('renders submit choices', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.sc-opt')).toHaveLength(2)
  })

  it('emits back event when back button clicked', async () => {
    const wrapper = mount(Step2Assign)
    // i18n mock 下按钮文案为 key, 用 key 后缀定位(原 '上一步' 文案依赖真实 i18n)
    const backBtn = wrapper.findAll('button').find((b) => b.text().includes('Step2Assign.s18'))!
    await backBtn.trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })

  // ===== 2026-09-27: 替换硬编码 mock, 接真实 /positions/ =====
  async function mountStep2WithPosition() {
    const store = useAddCandidateStore()
    store.applyMode = 'all'
    store.dirAll = 'position'
    const wrapper = mount(Step2Assign, { global: { stubs: { DirectionPicker: true } } })
    await flushPromises()
    return { wrapper, store }
  }

  it('从 /positions/ 拉取真实职位并渲染为选项(非 8 条硬编码 mock)', async () => {
    const { wrapper } = await mountStep2WithPosition()
    const chips = wrapper.findComponent(PositionChips)
    expect(chips.exists()).toBe(true)
    expect(chips.props('items')).toEqual([
      { id: 'pos-1', label: '前端工程师' },
      { id: 'pos-2', label: '后端工程师' },
    ])
  })

  it('选中职位后 store.posAll 存的是 position id(uuid), 而非标题', async () => {
    const { wrapper, store } = await mountStep2WithPosition()
    const chips = wrapper.findComponent(PositionChips)
    await chips.findAll('.pos-item')[0].trigger('click')
    expect(store.posAll).toBe('pos-1')
  })
})

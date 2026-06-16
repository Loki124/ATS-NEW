import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NMessageProvider } from 'naive-ui'
import { nextTick } from 'vue'
import type { RecruitmentProcess, ProcessStageLink } from '../../../api/recruitment-process'

vi.mock('../../../api/recruitment-process', () => ({
  getProcess: vi.fn(),
  listProcessLinks: vi.fn(),
}))

import { getProcess, listProcessLinks } from '../../../api/recruitment-process'
import ProcessDetailModal from '../ProcessDetailModal.vue'

const mockedGetProcess = vi.mocked(getProcess)
const mockedListProcessLinks = vi.mocked(listProcessLinks)

// Match the REAL RecruitmentProcess type:
//   id, code, name, description?, status, applicableDepartments?, applicableMode,
//   validateResumeScore, failPrompt?, createdAt, updatedAt, _count?, updater?, links?
const PROCESS: RecruitmentProcess = {
  id: 'p1',
  code: 'P001',
  name: '一级总及以上流程',
  description: 'test',
  status: 'ACTIVE',
  applicableDepartments: ['技术部', '产品部'],
  applicableMode: 'ALL',
  validateResumeScore: true,
  failPrompt: '请先完成初评',
  createdAt: '2026-06-01T00:00:00Z',
  updatedAt: '2026-06-10T00:00:00Z',
}

// getProcess returns RecruitmentProcess & { stages, autoRules }; cast to that
const PROCESS_FULL = { ...PROCESS, stages: [], autoRules: [] } as any

// Match the REAL ProcessStageLink type: condition is EntryCondition | null (object)
const STAGE_LINKS: ProcessStageLink[] = [
  {
    id: 'l1', processId: 'p1', stageId: 'st1', orderIndex: 1,
    isStart: true, isEnd: false, status: 'ACTIVE',
    stage: { id: 'st1', code: 'F001', name: '初评', stageType: 'FILTER', features: ['invite'], isSystem: true, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: { id: 'c1', stageId: 'st1', processId: 'p1', matchType: 'ALL', conditionType: 'CANDIDATE', items: [] },
  },
  {
    id: 'l2', processId: 'p1', stageId: 'st2', orderIndex: 2,
    isStart: false, isEnd: false, status: 'ACTIVE',
    stage: { id: 'st2', code: 'F002', name: 'HRBP评估', stageType: 'FILTER', features: [], isSystem: false, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: null,
  },
  {
    id: 'l3', processId: 'p1', stageId: 'st3', orderIndex: 3,
    isStart: false, isEnd: true, status: 'ACTIVE',
    stage: { id: 'st3', code: 'F003', name: '正式录用', stageType: 'ONBOARDING', features: [], isSystem: true, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: null,
  },
]

function factory(props: any) {
  // NMessageProvider must wrap the component as a parent (not a plugin) so
  // useMessage() resolves inside the child component's setup.
  // n-modal teleports its body to document.body, so we attach to body to
  // let @vue/test-utils see the teleported content.
  const Wrapper = defineComponent({
    setup(_, { slots }) {
      return () => h(NMessageProvider, null, { default: () => slots.default?.() })
    },
  })
  return mount(Wrapper, {
    props,
    slots: { default: () => h(ProcessDetailModal, props) },
    attachTo: document.body,
  })
}

describe('ProcessDetailModal.vue', () => {
  let wrapper: any

  beforeEach(() => {
    mockedGetProcess.mockReset()
    mockedListProcessLinks.mockReset()
    // Clean up any previous body content (teleported modals)
    document.body.innerHTML = ''
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    document.body.innerHTML = ''
  })

  it('renders 3 cards in vertical single-column list', async () => {
    mockedGetProcess.mockResolvedValue(PROCESS_FULL)
    mockedListProcessLinks.mockResolvedValue(STAGE_LINKS)

    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()

    // n-modal teleports to document.body, so query the body directly
    expect(document.querySelectorAll('.stage-card')).toHaveLength(3)
  })

  it('shows system built-in badge on first and last stage', async () => {
    mockedGetProcess.mockResolvedValue(PROCESS_FULL)
    mockedListProcessLinks.mockResolvedValue(STAGE_LINKS)

    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()

    const badges = document.querySelectorAll('.stage-card__system-badge')
    expect(badges).toHaveLength(2) // first and last
  })

  it('emits goEdit when click 前往编辑', async () => {
    mockedGetProcess.mockResolvedValue(PROCESS_FULL)
    mockedListProcessLinks.mockResolvedValue(STAGE_LINKS)

    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()

    const btn = document.querySelector('[data-testid="btn-go-edit"]') as HTMLElement
    expect(btn).toBeTruthy()
    btn.click()
    await flushPromises()
    // The inner ProcessDetailModal emits goEdit; check via findComponent
    const inner = wrapper.findComponent(ProcessDetailModal)
    expect(inner.exists()).toBe(true)
    expect(inner.emitted('goEdit')).toBeTruthy()
  })
})

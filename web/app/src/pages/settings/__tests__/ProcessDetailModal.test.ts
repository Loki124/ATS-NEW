import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NMessageProvider, NDialogProvider } from 'naive-ui'
import { nextTick } from 'vue'
import type { RecruitmentProcess, ProcessStageLink } from '../../../api/recruitment-process'
import { naivePlugin } from '../../../plugins/naive'

// API mock — vi.mock hoists; 路径深度 3 层 (__tests__ → settings → pages → src)
const mockGetProcess = vi.fn()
const mockListProcessLinks = vi.fn()
const mockUpdateProcess = vi.fn()
const mockListStages = vi.fn()
const mockReorderProcessLinks = vi.fn()
const mockAddProcessLink = vi.fn()
const mockDeleteProcessLink = vi.fn()
const mockUpdateProcessLink = vi.fn()

vi.mock('../../../api/recruitment-process', () => ({
  getProcess: (...args: any[]) => mockGetProcess(...args),
  listProcessLinks: (...args: any[]) => mockListProcessLinks(...args),
  updateProcess: (...args: any[]) => mockUpdateProcess(...args),
  listStages: (...args: any[]) => mockListStages(...args),
  reorderProcessLinks: (...args: any[]) => mockReorderProcessLinks(...args),
  addProcessLink: (...args: any[]) => mockAddProcessLink(...args),
  deleteProcessLink: (...args: any[]) => mockDeleteProcessLink(...args),
  updateProcessLink: (...args: any[]) => mockUpdateProcessLink(...args),
  listProcesses: vi.fn(),
  createProcess: vi.fn(),
  deleteProcess: vi.fn(),
  copyProcess: vi.fn(),
  updateProcessStatus: vi.fn(),
  upsertStageRule: vi.fn(),
  upsertEntryCondition: vi.fn(),
  listStageRules: vi.fn(),
  listEntryConditions: vi.fn(),
  evaluateCandidateForStage: vi.fn(),
  checkApplicationStageTransition: vi.fn(),
  listRounds: vi.fn(),
  createRound: vi.fn(),
  updateRound: vi.fn(),
  updateRoundStatus: vi.fn(),
}))

import ProcessDetailModal from '../ProcessDetailModal.vue'

// 复用现有 PROCESS 形态 (status='ACTIVE', 匹配 recruitment-process.ts:36 类型)
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
const PROCESS_FULL = { ...PROCESS, stages: [], autoRules: [] } as any

// 复用现有 STAGE_LINKS (3 条, 含 isSystem / isStart / isEnd)
const STAGE_LINKS: ProcessStageLink[] = [
  {
    id: 'l1', processId: 'p1', stageId: 'st1', order: 1,
    status: 'ACTIVE',
    stage: { id: 'st1', code: 'F001', name: '初评', stageType: 'SCREEN', features: ['invite'], isSystem: true, isStart: true, isEnd: false, status: 'ENABLED', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    stageRule: null,
    entryCondition: { id: 'c1', stageId: 'st1', processId: 'p1', matchType: 'ALL', conditionType: 'CANDIDATE', items: [] },
  },
  {
    id: 'l2', processId: 'p1', stageId: 'st2', order: 2,
    status: 'ACTIVE',
    stage: { id: 'st2', code: 'F002', name: 'HRBP评估', stageType: 'SCREEN', features: [], isSystem: false, isStart: false, isEnd: false, status: 'ENABLED', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    stageRule: null,
    entryCondition: null,
  },
  {
    id: 'l3', processId: 'p1', stageId: 'st3', order: 3,
    status: 'ACTIVE',
    stage: { id: 'st3', code: 'F003', name: '正式录用', stageType: 'OFFER', features: [], isSystem: true, isStart: false, isEnd: true, status: 'ENABLED', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    stageRule: null,
    entryCondition: null,
  },
]

// factory: NMessageProvider + NDialogProvider 包 + attachTo document.body (n-modal teleport 逃出 wrapper)
function factory(props: any) {
  const Wrapper = defineComponent({
    setup(_, { slots }) {
      return () => h(NDialogProvider, null, {
        default: () => h(NMessageProvider, null, { default: () => slots.default?.() }),
      })
    },
  })
  const w = mount(Wrapper, {
    props,
    slots: { default: () => h(ProcessDetailModal, props) },
    attachTo: document.body,
  })
  // 注册全部 naive-ui 组件, 模拟生产 app.use(naivePlugin)
  w.vm.$.appContext.app.use(naivePlugin)
  return w
}

describe('ProcessDetailModal.vue', () => {
  let wrapper: any

  beforeEach(() => {
    mockGetProcess.mockReset()
    mockListProcessLinks.mockReset()
    mockUpdateProcess.mockReset()
    mockListStages.mockReset()
    mockReorderProcessLinks.mockReset()
    mockAddProcessLink.mockReset()
    mockDeleteProcessLink.mockReset()
    mockUpdateProcessLink.mockReset()
    mockGetProcess.mockResolvedValue(PROCESS_FULL)
    mockListProcessLinks.mockResolvedValue(STAGE_LINKS)
    mockListStages.mockResolvedValue([])
    mockUpdateProcess.mockResolvedValue(PROCESS_FULL)
    mockReorderProcessLinks.mockResolvedValue({ success: true })
    mockAddProcessLink.mockResolvedValue({ id: 'new-link' })
    mockDeleteProcessLink.mockResolvedValue({ success: true })
    mockUpdateProcessLink.mockResolvedValue({ success: true })
    document.body.innerHTML = ''
  })

  afterEach(() => {
    if (wrapper) { wrapper.unmount(); wrapper = null }
    document.body.innerHTML = ''
  })

  // --- 旧契约 1 (保留) ---
  it('renders 3 cards in vertical single-column list', async () => {
    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()
    expect(document.querySelectorAll('.stage-card')).toHaveLength(3)
  })

  // --- 旧契约 2 (保留) ---
  it('shows system built-in badge on first and last stage', async () => {
    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()
    expect(document.querySelectorAll('.stage-card__system-badge')).toHaveLength(2)
  })

  // --- 契约 3 (统一后不再有 view→edit 切换; enterEdit 已移除) 见下方契约 4 ---

  // --- 契约 4 ---
  it('enterEdit switches mode to edit and populates editForm', async () => {
    wrapper = factory({ show: true, processId: 'p1', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    // 用 defaultMode: 'edit' 直接进 edit 态, editForm.name 应等于 PROCESS.name
    const nameInput = document.querySelector('input[placeholder="流程名称"]') as HTMLInputElement
    expect(nameInput).toBeTruthy()
    expect(nameInput.value).toBe('一级总及以上流程')
  })

  // --- 新契约 5 ---
  it('cancelEdit with dirty state opens popconfirm', async () => {
    wrapper = factory({ show: true, processId: 'p1', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    // 改 name
    const nameInput = document.querySelector('input[placeholder="流程名称"]') as HTMLInputElement
    nameInput.value = '一级总及以上流程-改'
    nameInput.dispatchEvent(new Event('input'))
    await flushPromises()
    // 点取消
    const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === '取消') as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()
    await nextTick()
    await new Promise(r => setTimeout(r, 50))
    // 关闭确认 dialog 应出现 (n-dialog 渲染 .n-dialog 容器)
    expect(document.querySelectorAll('.n-dialog').length).toBeGreaterThan(0)
  })

  // --- 新契约 6 ---
  it('save calls updateProcess and emits saved', async () => {
    wrapper = factory({ show: true, processId: 'p1', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    // 直接进 edit 态, 不修改任何字段, 点保存
    const saveBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === '保存') as HTMLElement
    expect(saveBtn).toBeTruthy()
    saveBtn.click()
    await flushPromises()
    expect(mockUpdateProcess).toHaveBeenCalledTimes(1)
    const inner = wrapper.findComponent(ProcessDetailModal)
    expect(inner.emitted('saved')).toBeTruthy()
  })

  // --- 新契约 7 ---
  it('handle 409 from updateProcess opens conflict modal', async () => {
    mockUpdateProcess.mockRejectedValueOnce({
      response: { status: 409, data: { updatedBy: 'admin', updatedAt: '2026-07-02 10:30:00' } },
    })
    wrapper = factory({ show: true, processId: 'p1', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    const saveBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === '保存') as HTMLElement
    saveBtn.click()
    await flushPromises()
    expect(document.body.textContent).toContain('修改冲突')
  })

  // --- 新契约 9: 新建流程 (processId='') ---
  it('create mode (processId="") opens edit form with empty fields, no getProcess call', async () => {
    wrapper = factory({ show: true, processId: '', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    // 不应调用 getProcess / listProcessLinks
    expect(mockGetProcess).not.toHaveBeenCalled()
    expect(mockListProcessLinks).not.toHaveBeenCalled()
    // edit mode 应打开, 流程名称输入框 placeholder 可见
    const nameInput = document.querySelector('input[placeholder="流程名称"]') as HTMLInputElement
    expect(nameInput).toBeTruthy()
    expect(nameInput.value).toBe('')
    // 取消 / 创建 按钮可见
    const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === '取消') as HTMLElement
    expect(cancelBtn).toBeTruthy()
    const createBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === '创建') as HTMLElement
    expect(createBtn).toBeTruthy()
  })

  // --- 新契约 8 ---
  it('closing modal with dirty state in edit mode shows popconfirm', async () => {
    wrapper = factory({ show: true, processId: 'p1', defaultMode: 'edit' })
    await flushPromises()
    await nextTick()
    // 修改字段
    const nameInput = document.querySelector('input[placeholder="流程名称"]') as HTMLInputElement
    nameInput.value = '一级总及以上流程-改'
    nameInput.dispatchEvent(new Event('input'))
    await flushPromises()
    // 关 modal
    const closeBtn = document.querySelector('.n-base-close') as HTMLElement
    expect(closeBtn).toBeTruthy()
    closeBtn.click()
    await flushPromises()
    await nextTick()
    await new Promise(r => setTimeout(r, 50))
    // 弹关闭确认 dialog (关闭被拦截)
    expect(document.querySelectorAll('.n-dialog').length).toBeGreaterThan(0)
  })
})
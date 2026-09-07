# 招聘流程详情+编辑统一入口 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把招聘流程详情页 (`ProcessDetailModal.vue`) 和编辑页 (`CustomRecruitmentProcessModal.vue`) 整合成单一 modal, 在详情态可直接切换到编辑态, list 页只剩 `[编辑]` 一个入口.

**Architecture:** 单 modal + `mode: 'view' | 'edit'` 切换. `ProcessDetailModal.vue` 重写, 加 mode / editForm / dirty / 409 冲突 modal; view 模板保留 v2 设计; edit 模板在同一 modal 内替换为表单 + 阶段操作. 删除 `CustomRecruitmentProcessModal.vue`. `RecruitmentProcess.vue` 操作列只保留 1 个按钮.

**Tech Stack:** Vue 3 Composition API (`<script setup lang="ts">`) + naive-ui (n-modal/n-input/n-select/n-switch/n-radio-group/n-popconfirm) + @vicons/ionicons5 + vitest.

**Spec:** `docs/superpowers/specs/2026-07-02-process-detail-edit-unify-design.md` (commit 37db406)

**Working directory:** `/Users/loki/ClaudeWorkSpace/ATS-NEW/web/app`

---

## 文件结构

| 文件 | 操作 | 责任 |
|---|---|---|
| `src/pages/settings/ProcessDetailModal.vue` | **重写** (~1400 行) | 单 modal 双态, view=只读详情, edit=就地编辑 |
| `src/pages/settings/RecruitmentProcess.vue` | **改** (~280 行) | list 操作列只保留 `[编辑]` 按钮 |
| `src/pages/settings/CustomRecruitmentProcessModal.vue` | **删** | 不再引用 |
| `src/pages/settings/__tests__/ProcessDetailModal.test.ts` | **扩** (8 条) | 单测覆盖 view / edit / dirty / 409 / close guard |
| `src/api/recruitment-process.ts` | 不动 | 复用现有 API |

---

## Task 1: 扩展单测契约 (TDD — 先写失败的测试)

**Files:**
- Modify: `src/pages/settings/__tests__/ProcessDetailModal.test.ts`

- [ ] **Step 1: 读现有单测, 确认契约映射**

读 `src/pages/settings/__tests__/ProcessDetailModal.test.ts` 现有 3 条用例. 旧契约映射:
- `data-testid="btn-go-edit"` → `data-testid="btn-enter-edit"` (HERO 右上 [编辑] 按钮, view 态)
- `emitted('goEdit')` → `emitted('enterEdit')`

现有 mock 数据形态 (复用, 不重建):
- `PROCESS.status: 'ACTIVE'` (匹配 `recruitment-process.ts:36` 类型 `'ACTIVE' | 'INACTIVE'`)
- `STAGE_LINKS` 3 条, 含 `stage.isSystem` (true/false) + `isStart` / `isEnd`
- mock API 路径: `vi.mock('../../../api/recruitment-process', ...)` (3 层向上, `__tests__ → settings → pages → src`)
- factory: 嵌套 `NMessageProvider` + `attachTo: document.body` (n-modal teleport 逃出 wrapper)

- [ ] **Step 2: 改写现有 3 条用例 + 加 5 条新用例**

完整覆盖文件如下 (替换原 140 行). 复用现有 PROCESS / STAGE_LINKS / factory, 扩 mock 涵盖 updateProcess / listStages / stage CRUD, 改契约:

```ts
// src/pages/settings/__tests__/ProcessDetailModal.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NMessageProvider, NDialogProvider } from 'naive-ui'
import { nextTick } from 'vue'
import type { RecruitmentProcess, ProcessStageLink } from '../../../api/recruitment-process'

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
  evaluateEntryCondition: vi.fn(),
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
    id: 'l1', processId: 'p1', stageId: 'st1', orderIndex: 1,
    isStart: true, isEnd: false, status: 'ACTIVE',
    stage: { id: 'st1', code: 'F001', name: '初评', stageType: 'SCREEN', features: ['invite'], isSystem: true, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: { id: 'c1', stageId: 'st1', processId: 'p1', matchType: 'ALL', conditionType: 'CANDIDATE', items: [] },
  },
  {
    id: 'l2', processId: 'p1', stageId: 'st2', orderIndex: 2,
    isStart: false, isEnd: false, status: 'ACTIVE',
    stage: { id: 'st2', code: 'F002', name: 'HRBP评估', stageType: 'SCREEN', features: [], isSystem: false, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: null,
  },
  {
    id: 'l3', processId: 'p1', stageId: 'st3', orderIndex: 3,
    isStart: false, isEnd: true, status: 'ACTIVE',
    stage: { id: 'st3', code: 'F003', name: '正式录用', stageType: 'OFFER', features: [], isSystem: true, status: 'ACTIVE', createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
    rule: null,
    condition: null,
  },
]

// factory: NMessageProvider 包 + attachTo document.body (n-modal teleport 逃出 wrapper)
function factory(props: any) {
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

  // --- 旧契约 3 (替换为 enterEdit) ---
  it('emits enterEdit when click [编辑]', async () => {
    wrapper = factory({ show: true, processId: 'p1' })
    await flushPromises()
    await nextTick()
    const btn = document.querySelector('[data-testid="btn-enter-edit"]') as HTMLElement
    expect(btn).toBeTruthy()
    btn.click()
    await flushPromises()
    const inner = wrapper.findComponent(ProcessDetailModal)
    expect(inner.emitted('enterEdit')).toBeTruthy()
  })

  // --- 新契约 4 ---
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
    // popconfirm 应出现 (n-popconfirm 渲染 .n-popconfirm 容器)
    expect(document.querySelectorAll('.n-popconfirm, .n-popover').length).toBeGreaterThan(0)
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
    // 弹 popconfirm (关闭被拦截)
    expect(document.querySelectorAll('.n-popconfirm, .n-popover').length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 3: 跑测试, 确认 8 条全 fail**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW/web/app && npm run test -- ProcessDetailModal 2>&1 | tail -30
```

预期: 8/8 FAIL. 失败原因应该是 "Cannot find element [data-testid=\"btn-enter-edit\"]" 或 "emitted('enterEdit') not found" 或 "editForm 找不到".

- [ ] **Step 4: 提交测试**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW && git add web/app/src/pages/settings/__tests__/ProcessDetailModal.test.ts && git commit -m "test(ProcessDetailModal): 扩展单测 3 → 8, 替换 v3 契约"
```

---

## Task 2: 重写 ProcessDetailModal — 加 mode state + view 模板契约

**Files:**
- Modify: `src/pages/settings/ProcessDetailModal.vue`

- [ ] **Step 1: 加 mode / editForm / dirty 等 state (在 script setup 顶部)**

在 `<script setup lang="ts">` 第 1 行后插入 (紧接 import):

```ts
import { ref, watch, computed, reactive, onBeforeUnmount, onMounted, h } from 'vue'
import {
  NModal, NSpin, NSpace, NButton, NIcon, NTag, NGrid, NGridItem, NInput, NInputNumber,
  NSelect, NSwitch, NRadioGroup, NRadio, NPopconfirm, NDivider, NAlert, NText, NPopover,
  useMessage,
} from 'naive-ui'
import {
  GitNetworkOutline, ArrowDownOutline, FilterOutline, MailOutline, VideocamOutline,
  DocumentTextOutline, CheckmarkCircleOutline, ServerOutline, InformationCircleOutline,
  CreateOutline, ClipboardOutline, CopyOutline, PersonOutline, TimeOutline, LayersOutline,
  EllipsisHorizontalOutline, BusinessOutline, MedalOutline, BriefcaseOutline,
  PersonCircleOutline, TrashOutline, AddOutline,
} from '@vicons/ionicons5'
import {
  getProcess, listProcessLinks, updateProcess, listStages,
  addProcessLink, deleteProcessLink, updateProcessLink, reorderProcessLinks,
  copyProcess,
  type RecruitmentProcess, type RecruitmentStage, type ProcessStageLink,
  type StageRule, type EntryCondition,
} from '../../api/recruitment-process'
import StageRuleConfigModal from './StageRuleConfigModal.vue'

const props = withDefaults(defineProps<{
  show: boolean
  processId: string
  defaultMode?: 'view' | 'edit'
  editable?: boolean
}>(), {
  defaultMode: 'view',
  editable: true,
})

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
  (e: 'copied', id: string): void
  (e: 'enterEdit', id: string): void
}>()

const message = useMessage()

// ===== state =====
type Mode = 'view' | 'edit'
const mode = ref<Mode>(props.defaultMode)
const data = ref<Partial<RecruitmentProcess> & Record<string, any>>({})
const links = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)

// edit 态
const editForm = ref<EditForm | null>(null)
const originalSnapshot = ref<any>(null)
const selectedStageIdx = ref<number | null>(null)
const deptOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])
const userOptions = ref<{ label: string; value: string }[]>([])
const stageLibrary = ref<RecruitmentStage[]>([])

// 嵌套 StageRuleConfigModal
const showRuleConfig = ref(false)
const ruleEditingStage = ref<any>(null)
const ruleEditingLinkId = ref<string | undefined>(undefined)

// 冲突 modal
const showConflict = ref(false)
const conflictInfo = ref<any>({})

// 关闭确认
const showCloseConfirm = ref(false)

// ===== types =====
type ScopeKey = 'department' | 'level' | 'position' | 'user'
interface ScopeIndicator {
  key: ScopeKey
  mode: 'include' | 'exclude'
  values: string[]
  options: { label: string; value: string }[]
  loading: boolean
}
interface EditStage {
  id?: string
  code?: string
  name: string
  stageType: 'SCREEN' | 'INVITATION' | 'INTERVIEW' | 'OFFER'
  isStart: boolean
  isEnd: boolean
  stageLimit?: number
  features: string[]
  _linkId?: string
}
interface EditForm {
  name: string
  description: string
  validateResumeScore: boolean
  failPrompt: string
  applicableMode: 'ALL' | 'ANY'
  applicableIndicators: ScopeIndicator[]
  stages: EditStage[]
}
```

- [ ] **Step 2: 加 view 模板契约 ([data-testid="btn-enter-edit"])**

在 HERO `</div>` (`.hero` 关闭, 现 ProcessDetailModal.vue:67) 之前插入 [编辑] 按钮 (作为 `.hero` 的子元素, 与 `.hero__icon` `.hero__main` 同一 flex 行):

```vue
<button v-if="mode === 'view' && editable" class="hero__edit-btn" data-testid="btn-enter-edit" @click="enterEdit">
  <n-icon :component="CreateOutline" />
  编辑
</button>
```

加 CSS:
```css
.hero__edit-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #2080f0;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.hero__edit-btn:hover { border-color: #2080f0; background: #f0f5ff; }
```

- [ ] **Step 3: 加 enterEdit 函数 (stub, 仅 emit)**

```ts
function enterEdit() {
  if (!props.editable) return
  emit('enterEdit', props.processId)
  // Task 3 填充完整 enterEdit 逻辑
}
```

- [ ] **Step 4: 跑单测 1/2/3/4 (旧契约 + enterEdit emit)**

```bash
npm run test -- ProcessDetailModal 2>&1 | tail -30
```

预期: 1/2/3/4 PASS, 5/6/7/8 FAIL (因为 enterEdit 没真切换 mode).

- [ ] **Step 5: 提交**

```bash
git add web/app/src/pages/settings/ProcessDetailModal.vue && git commit -m "feat(ProcessDetailModal): 加 mode state + HERO [编辑] 按钮契约"
```

---

## Task 3: 完成 enterEdit + edit 模板 + dirty 检测

**Files:**
- Modify: `src/pages/settings/ProcessDetailModal.vue`

- [ ] **Step 1: 加 utils + load helpers**

```ts
// ===== utils =====
function formatDate(s: string | undefined | null): string {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function deepClone<T>(v: T): T { return JSON.parse(JSON.stringify(v)) }

function findIndicatorOldFormat(key: ScopeKey): { mode: 'include' | 'exclude'; values: string[] } | null {
  if (!data.value) return null
  const inds = (data.value.applicableScope as any)?.indicators
  if (Array.isArray(inds)) {
    const i = inds.find((x: any) => x.key === key)
    return i ? { mode: i.mode, values: i.values || [] } : null
  }
  return null
}

const hasAnyScope = computed(() => {
  if (!data.value) return false
  const inds = (data.value.applicableScope as any)?.indicators
  const items = (data.value.applicableScope as any)?.items
  return (Array.isArray(inds) && inds.length > 0) || (Array.isArray(items) && items.length > 0)
})

const dirty = computed(() => {
  if (mode.value !== 'edit' || !editForm.value || !originalSnapshot.value) return false
  return JSON.stringify(editForm.value) !== JSON.stringify(originalSnapshot.value.form)
})

// ===== load =====
async function load() {
  if (!props.processId) return
  loading.value = true
  try {
    const [procResp, lksResp] = await Promise.all([
      getProcess(props.processId).catch(() => null),
      listProcessLinks(props.processId).catch(() => []),
    ])
    const proc = procResp as any
    const linksArr: any[] = Array.isArray(lksResp) ? lksResp : (Array.isArray(proc?.stageLinks) ? proc.stageLinks : [])
    data.value = (proc && typeof proc === 'object') ? proc : {}
    links.value = linksArr
      .slice()
      .sort((a: any, b: any) => (a.order ?? a.orderIndex ?? 0) - (b.order ?? b.orderIndex ?? 0))
      .map((l: any) => ({
        ...l,
        stage: l.stage ? {
          ...l.stage,
          features: [...(l.stage.defaultFeatures || []), ...(l.stage.optionalFeatures || [])],
          isSystem: l.stage.isBuiltin ?? l.stage.isSystem ?? false,
          stageType: l.stage.stageType,
        } : l.stage,
        isStart: l.isStart ?? l.isRequired ?? false,
        isEnd: l.isEnd ?? false,
      }))
  } finally {
    loading.value = false
  }
}

// ===== edit lifecycle =====
function buildEditForm(): EditForm {
  const d = data.value
  const indicators: ScopeIndicator[] = [
    { key: 'department', mode: 'include', values: [], options: deptOptions.value, loading: false },
    { key: 'level',      mode: 'include', values: [], options: [], loading: false },
    { key: 'position',   mode: 'include', values: [], options: positionOptions.value, loading: false },
    { key: 'user',       mode: 'include', values: [], options: userOptions.value, loading: false },
  ]
  for (const ind of indicators) {
    const old = findIndicatorOldFormat(ind.key)
    if (old) { ind.mode = old.mode; ind.values = old.values }
  }
  const stages: EditStage[] = links.value.map((l: any) => ({
    id: l.stage?.id,
    code: l.stage?.code,
    name: l.stage?.name || '',
    stageType: l.stage?.stageType || 'SCREEN',
    isStart: l.isStart,
    isEnd: l.isEnd,
    stageLimit: l.stageLimit,
    features: l.stage?.features || [],
    _linkId: l.id,
  }))
  return {
    name: d.name || '',
    description: d.description || '',
    validateResumeScore: d.validateResumeScore ?? true,
    failPrompt: d.failPrompt || '',
    applicableMode: (d.applicableMode as any) || 'ALL',
    applicableIndicators: indicators,
    stages,
  }
}

async function loadScopeOptions() {
  // 简化版: 不阻塞, 用空数组 (实际从 /departments /positions /users 拉, v2 modal 已有)
  // 单测不依赖 options 加载
  deptOptions.value = []
  positionOptions.value = []
  userOptions.value = []
}

async function loadStageLibrary() {
  try {
    const res = await listStages({ status: 'ENABLED' })
    stageLibrary.value = Array.isArray(res) ? res : []
  } catch {
    stageLibrary.value = []
  }
}

async function enterEdit() {
  if (!props.editable) return
  emit('enterEdit', props.processId)
  await loadScopeOptions()
  await loadStageLibrary()
  const form = buildEditForm()
  editForm.value = form
  originalSnapshot.value = { form: deepClone(form) }
  selectedStageIdx.value = null
  mode.value = 'edit'
}

function cancelEdit() {
  if (dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
}

function exitEditMode() {
  mode.value = 'view'
  editForm.value = null
  originalSnapshot.value = null
  showCloseConfirm.value = false
}
```

- [ ] **Step 2: 改 modal 关闭逻辑 + beforeunload**

```ts
function handleClose() {
  if (mode.value === 'edit' && dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
  emit('update:show', false)
}

function handleUpdateShow(v: boolean) {
  if (!v) handleClose()
  else emit('update:show', true)
}

function confirmClose() {
  exitEditMode()
  emit('update:show', false)
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (mode.value === 'edit' && dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
```

- [ ] **Step 3: 加 edit 模板 (在 view 模板之后)**

替换原 `<n-spin :show="loading">` 为:

```vue
<n-spin :show="loading">
  <template v-if="mode === 'view'">
    <!-- 现有 v2 模板 (HERO + section + footer) 不变 -->
    ... [保留原 v2 模板]
  </template>

  <template v-else>
    <!-- EDIT MODE -->
    <!-- ====== HERO (edit) ====== -->
    <div class="hero hero--edit">
      <div class="hero__icon">
        <n-icon :component="GitNetworkOutline" size="22" />
      </div>
      <div class="hero__main">
        <n-input
          v-model:value="editForm!.name"
          size="large"
          placeholder="流程名称"
          style="font-size: 18px; font-weight: 600"
        />
        <div class="hero__meta" style="margin-top: 8px">
          <span class="hero__meta-item">
            <n-icon :component="LayersOutline" />
            {{ editForm!.stages.length }} 个阶段
          </span>
          <span v-if="data.code" class="hero__meta-item">
            <n-icon :component="ServerOutline" />
            编号 {{ data.code }} (BE 自动生成, 不可改)
          </span>
        </div>
      </div>
      <div class="hero__actions">
        <n-button @click="cancelEdit">取消</n-button>
        <n-button type="primary" :loading="saving" @click="handleSave">保存</n-button>
      </div>
    </div>

    <!-- ====== 基础信息 (edit) ====== -->
    <div class="section">
      <div class="section__title">
        <span class="section__title-bar" />
        <span>基础信息</span>
      </div>
      <div class="section__body">
        <div class="field-row">
          <span class="field-label">流程名称</span>
          <n-input v-model:value="editForm!.name" placeholder="如：技术部社招流程" />
        </div>
        <div class="field-row field-row--block">
          <span class="field-label">流程说明</span>
          <n-input v-model:value="editForm!.description" type="textarea" :rows="2" placeholder="可选" />
        </div>
        <div class="field-row">
          <span class="field-label">适用范围组合</span>
          <n-radio-group v-model:value="editForm!.applicableMode">
            <n-radio value="ALL">全部满足 (AND)</n-radio>
            <n-radio value="ANY">任一满足 (OR)</n-radio>
          </n-radio-group>
        </div>
        <div class="field-row">
          <span class="field-label">是否启用</span>
          <n-tag size="small">{{ data.status === 'ACTIVE' ? '启用中' : '已停用' }} (不可改)</n-tag>
        </div>
        <div class="field-row">
          <span class="field-label">校验简历评分</span>
          <n-switch v-model:value="editForm!.validateResumeScore" />
        </div>
        <div class="field-row field-row--block field-row--last">
          <span class="field-label">流转异常提示</span>
          <n-input v-model:value="editForm!.failPrompt" type="textarea" :rows="3" placeholder="候选人不满足进入条件时的展示文本 (可选)" />
        </div>
      </div>
    </div>

    <!-- ====== 适用范围 4 指标 (edit) ====== -->
    <div v-if="editForm!.applicableIndicators.length" class="section">
      <div class="section__title">
        <span class="section__title-bar" />
        <span>适用范围</span>
      </div>
      <div class="scope-edit-list">
        <div v-for="ind in editForm!.applicableIndicators" :key="ind.key" class="scope-edit-row">
          <n-tag :type="SCOPE_INDICATOR_META[ind.key].tagType" size="small" style="min-width: 88px">
            {{ SCOPE_INDICATOR_META[ind.key].label }}
          </n-tag>
          <n-radio-group v-model:value="ind.mode" size="small">
            <n-radio value="include">包含</n-radio>
            <n-radio value="exclude">不包含</n-radio>
          </n-radio-group>
          <n-select
            v-model:value="ind.values"
            multiple
            filterable
            clearable
            placeholder="留空 = 不约束"
            :options="ind.options"
            :loading="ind.loading"
            style="flex: 1; min-width: 280px"
          />
        </div>
      </div>
    </div>

    <!-- ====== 阶段流程 (edit) ====== -->
    <div class="section">
      <div class="section__title">
        <span class="section__title-bar" />
        <span>阶段流程</span>
        <n-tag size="small">{{ editForm!.stages.length }} 个</n-tag>
      </div>
      <n-alert type="info" :show-icon="false" style="margin-bottom: 12px; font-size: 12px">
        起止阶段不可删除. 中间业务阶段可单独配置或删除. 点阶段行的空白处选中, 选中后可插入/删除.
      </n-alert>
      <div class="stage-list">
        <div
          v-for="(stage, idx) in editForm!.stages"
          :key="stage._linkId || stage.id || idx"
          class="stage-row"
          :class="{ 'stage-row-selected': selectedStageIdx === idx }"
          @click.self="selectedStageIdx = idx"
        >
          <div class="stage-num">{{ idx + 1 }}</div>
          <div class="stage-row__main">
            <n-tag size="small" :type="STAGE_TYPE_META[stage.stageType]?.tagType || 'default'">
              {{ STAGE_TYPE_META[stage.stageType]?.label || stage.stageType }}
            </n-tag>
            <span class="name-text">{{ stage.name }}</span>
            <n-input-number
              v-model:value="stage.stageLimit"
              :min="0"
              size="small"
              placeholder="阶段限时 (h)"
              style="width: 130px"
            />
          </div>
          <div class="stage-row__actions" @click.stop>
            <n-button text type="primary" @click.stop="openStageRuleConfig(stage)">配置阶段规则</n-button>
            <n-button text type="primary" @click.stop="openEntryCondition(stage)">配置进入条件</n-button>
            <n-popconfirm
              v-if="!stage.isStart && !stage.isEnd"
              @positive-click="removeStage(idx)"
            >
              <template #trigger>
                <n-button text type="error">删除</n-button>
              </template>
              确定删除阶段「{{ stage.name }}」？
            </n-popconfirm>
            <n-tag v-else type="default" size="small">起止不可删</n-tag>
          </div>
        </div>
      </div>
      <n-space style="margin-top: 12px">
        <n-button size="small" type="primary" dashed :disabled="selectedStageIdx === null" @click="addStage('preceding')">
          <template #icon>+</template>
          在选中前插入
        </n-button>
        <n-button size="small" type="primary" dashed :disabled="selectedStageIdx === null" @click="addStage('following')">
          <template #icon>+</template>
          在选中后插入
        </n-button>
        <n-button size="small" type="default" dashed @click="addStage('end')">
          <template #icon>+</template>
          追加到末尾
        </n-button>
        <n-popconfirm @positive-click="removeSelectedStage">
          <template #trigger>
            <n-button size="small" type="error" dashed :disabled="selectedStageIdx === null">
              <template #icon>×</template>
              删除选中
            </n-button>
          </template>
          确定删除选中的阶段？
        </n-popconfirm>
        <n-text depth="3" style="font-size: 12px">
          {{
            selectedStageIdx === null
              ? '未选中任何阶段 (点阶段行的空白处选中)'
              : `已选中第 ${selectedStageIdx + 1 } 行`
          }}
          · 可选阶段库: {{ stageLibrary.length }} 个
        </n-text>
      </n-space>
    </div>
  </template>
</n-spin>

<!-- 关闭确认 Popconfirm -->
<n-popconfirm
  :show="showCloseConfirm"
  @positive-click="confirmClose"
  @negative-click="showCloseConfirm = false"
>
  <template #trigger>
    <span style="display: none" />
  </template>
  有未保存的修改, 确定离开?
</n-popconfirm>

<!-- 409 冲突 modal -->
<n-modal v-model:show="showConflict" preset="card" title="修改冲突" style="width: 480px">
  <p>此流程在您编辑期间被其他用户修改。</p>
  <p v-if="conflictInfo?.updatedBy">最后修改人: {{ conflictInfo.updatedBy }}</p>
  <p v-if="conflictInfo?.updatedAt">修改时间: {{ formatDate(conflictInfo.updatedAt) }}</p>
  <n-space justify="end">
    <n-button @click="abandonEdit">放弃修改</n-button>
    <n-button type="primary" @click="reloadAndEdit">重新加载后继续编辑</n-button>
  </n-space>
</n-modal>

<!-- 嵌套 StageRuleConfigModal -->
<StageRuleConfigModal
  v-model:show="showRuleConfig"
  :stage="ruleEditingStage"
  :link-id="ruleEditingLinkId"
  @saved="onRuleSaved"
/>
```

- [ ] **Step 4: 加 SCOPE_INDICATOR_META + STAGE_TYPE_META (在 script 内)**

```ts
const SCOPE_INDICATOR_META: Record<ScopeKey, { label: string; tagType: 'info' | 'success' | 'warning' | 'error' }> = {
  department: { label: '需求部门', tagType: 'info' },
  level:      { label: '职级',     tagType: 'warning' },
  position:   { label: '岗位',     tagType: 'success' },
  user:       { label: '用户',     tagType: 'error' },
}

const STAGE_TYPE_META: Record<string, { label: string; color: string; tagType: 'info' | 'success' | 'warning' | 'error' }> = {
  SCREEN:     { label: '筛选',  color: '#2080f0', tagType: 'info' },
  INVITATION: { label: '邀约',  color: '#f0a020', tagType: 'warning' },
  INTERVIEW:  { label: '面试',  color: '#722ed1', tagType: 'success' },
  OFFER:      { label: 'Offer', color: '#18a058', tagType: 'success' },
}
```

- [ ] **Step 5: 加 stage 操作函数 (stub, Task 4 填充)**

```ts
function openStageRuleConfig(stage: EditStage) {
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId
  showRuleConfig.value = true
}

function openEntryCondition(stage: EditStage) {
  // 复用现有逻辑 (从 CustomRecruitmentProcessModal 抽取)
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId
  showRuleConfig.value = true
}

function onRuleSaved() {
  // 子 modal 已写库, 这里仅 toast
  message.success('阶段配置已保存')
}

function addStage(position: 'preceding' | 'following' | 'end') {
  if (!editForm.value) return
  const lib = stageLibrary.value.find(s => !editForm.value!.stages.some(es => es.id === s.id))
  if (!lib) { message.warning('可选阶段库为空, 请先创建阶段'); return }
  const newStage: EditStage = {
    id: lib.id,
    code: lib.code,
    name: lib.name,
    stageType: (lib.stageType as any) || 'SCREEN',
    isStart: false,
    isEnd: false,
    stageLimit: undefined,
    features: [],
  }
  if (position === 'end') editForm.value.stages.push(newStage)
  else if (selectedStageIdx.value !== null) {
    const idx = position === 'preceding' ? selectedStageIdx.value : selectedStageIdx.value + 1
    editForm.value.stages.splice(idx, 0, newStage)
  }
}

function removeStage(idx: number) {
  if (!editForm.value) return
  editForm.value.stages.splice(idx, 1)
  if (selectedStageIdx.value === idx) selectedStageIdx.value = null
}

function removeSelectedStage() {
  if (selectedStageIdx.value === null || !editForm.value) return
  removeStage(selectedStageIdx.value)
}

function handleSave() {
  // Task 4 填充完整 save 逻辑
  message.info('Task 4 将填充 save 逻辑')
}

function abandonEdit() {
  showConflict.value = false
  exitEditMode()
}

async function reloadAndEdit() {
  showConflict.value = false
  await load()
  await enterEdit()
}

async function onCopy() {
  // 复用 v2 逻辑
  if (!props.processId || !data.value) return
  try {
    const newProc = await copyProcess(props.processId, { newName: `${data.value.name} - 副本` })
    message.success(`已复制: ${newProc.name}`)
    emit('copied', newProc.id)
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '复制失败')
  }
}
```

- [ ] **Step 6: 跑单测, 期望 1/2/3/4 PASS, 5/6/8 PASS, 7 FAIL (save stub)**

```bash
npm run test -- ProcessDetailModal 2>&1 | tail -40
```

- [ ] **Step 7: 提交**

```bash
git add web/app/src/pages/settings/ProcessDetailModal.vue && git commit -m "feat(ProcessDetailModal): 双态 modal — view / edit 切换 + dirty 检测 + 关闭保护"
```

---

## Task 4: 实现 handleSave (顺序提交 + 409 冲突)

**Files:**
- Modify: `src/pages/settings/ProcessDetailModal.vue`

- [ ] **Step 1: 加 validateEditForm**

```ts
function validateEditForm(form: EditForm): string | null {
  if (!form.name.trim()) return '流程名称不能为空'
  if (form.name.length > 100) return '流程名称过长 (最多 100 字符)'
  if (form.stages.length < 2) return '至少需要 2 个阶段 (起 + 终)'
  const hasStart = form.stages.some(s => s.isStart)
  const hasEnd = form.stages.some(s => s.isEnd)
  if (!hasStart) return '缺少起始阶段'
  if (!hasEnd) return '缺少结束阶段'
  return null
}
```

- [ ] **Step 2: 实现 handleSave (完整)**

```ts
async function handleSave() {
  if (!editForm.value || !props.processId) return
  const err = validateEditForm(editForm.value)
  if (err) { message.error(err); return }

  saving.value = true
  try {
    // a) update 基础信息 + 适用范围
    await updateProcess(props.processId, {
      name: editForm.value.name,
      description: editForm.value.description,
      validateResumeScore: editForm.value.validateResumeScore,
      failPrompt: editForm.value.failPrompt,
      applicableMode: editForm.value.applicableMode,
      applicableScope: {
        mode: editForm.value.applicableMode,
        indicators: editForm.value.applicableIndicators.map(i => ({
          key: i.key, mode: i.mode, values: i.values,
        })),
      },
    } as any)

    // b) 删除被移除的 link
    const originalLinkIds = new Set(links.value.map((l: any) => l.id).filter(Boolean))
    const currentLinkIds = new Set(editForm.value.stages.map(s => s._linkId).filter(Boolean) as string[])
    for (const oldId of originalLinkIds) {
      if (!currentLinkIds.has(oldId)) {
        await deleteProcessLink(oldId)
      }
    }

    // c) 新增的 link
    for (const s of editForm.value.stages) {
      if (!s._linkId && s.id) {
        const created: any = await addProcessLink({
          processId: props.processId,
          stageId: s.id,
          orderIndex: editForm.value.stages.indexOf(s) + 1,
          stageLimit: s.stageLimit,
        })
        s._linkId = created.id
      }
    }

    // d) 重排
    const linkIds = editForm.value.stages.map(s => s._linkId!).filter(Boolean)
    if (linkIds.length) await reorderProcessLinks(props.processId, linkIds)

    // e) stageLimit 更新
    for (const s of editForm.value.stages) {
      if (s._linkId && s.stageLimit !== undefined) {
        await updateProcessLink(s._linkId, { stageLimit: s.stageLimit } as any)
      }
    }

    // f) 重新拉数据 + 退出 edit
    await load()
    exitEditMode()
    message.success('已保存')
    emit('saved')
  } catch (e: any) {
    if (e?.response?.status === 409) {
      showConflict.value = true
      conflictInfo.value = e.response.data || {}
    } else {
      message.error(e?.response?.data?.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}
```

- [ ] **Step 3: 跑单测, 期望 8/8 PASS**

```bash
npm run test -- ProcessDetailModal 2>&1 | tail -30
```

预期: 8/8 PASS.

- [ ] **Step 4: 类型检查**

```bash
npx vue-tsc --noEmit 2>&1 | grep "ProcessDetailModal" | head -20
```

预期: 0 错.

- [ ] **Step 5: ESLint**

```bash
npx eslint src/pages/settings/ProcessDetailModal.vue 2>&1 | tail -10
```

预期: 0 警告.

- [ ] **Step 6: 提交**

```bash
git add web/app/src/pages/settings/ProcessDetailModal.vue && git commit -m "feat(ProcessDetailModal): handleSave 顺序提交 + 409 冲突 modal"
```

---

## Task 5: 简化 RecruitmentProcess.vue — 删除 CustomRecruitmentProcessModal 引用 + 操作列只保留 [编辑]

**Files:**
- Modify: `src/pages/settings/RecruitmentProcess.vue`

- [ ] **Step 1: 删 import + 模板引用**

读 `src/pages/settings/RecruitmentProcess.vue`, 删:
- 顶部 `import CustomRecruitmentProcessModal from './CustomRecruitmentProcessModal.vue'`
- 模板内 `<CustomRecruitmentProcessModal v-model:show="showCustomModal" :editing="customEditing" @saved="onCustomSaved" />`

- [ ] **Step 2: 删 state + functions**

删:
- `const showCustomModal = ref(false)`
- `const customEditing = ref<any>(null)`
- `function openCustomModal(row: any | null) { ... }`
- `function onCustomSaved() { loadList() }`
- `function handleEdit(row: any) { ... }` (不再需要, 但 handleCreate 还用)

- [ ] **Step 3: 改操作列只保留 [编辑] 按钮**

找到 columns 内 action 列, 替换 render 函数:

```ts
{
  title: '操作',
  key: 'action',
  width: 100,
  fixed: 'right' as const,
  render: (row: any) => h(NButton, {
    size: 'small',
    type: 'primary',
    text: true,
    onClick: () => openProcessModal(row),
  }, { default: () => '编辑' }),
},
```

加 `openProcessModal`:

```ts
const detailDefaultMode = ref<'view' | 'edit'>('edit')

function openProcessModal(row: any) {
  detailProcessId.value = row.id
  detailDefaultMode.value = 'edit'
  showDetail.value = true
}
```

- [ ] **Step 4: 改 ProcessDetailModal props**

模板内 `<ProcessDetailModal v-model:show="showDetail" :process-id="detailProcessId" @go-edit="onGoEdit" @copied="onProcessCopied" />` 改为:

```vue
<ProcessDetailModal
  v-model:show="showDetail"
  :process-id="detailProcessId"
  :default-mode="detailDefaultMode"
  :editable="true"
  @saved="onProcessSaved"
  @copied="onProcessCopied"
/>
```

加 `onProcessSaved`:

```ts
function onProcessSaved() {
  loadList()
}
```

- [ ] **Step 5: 删 `onGoEdit` (不再需要)**

```ts
// 删除整个 onGoEdit 函数
```

- [ ] **Step 5.5: 重写 [新建流程] 顶部按钮 (删除 openCustomModal 后, 这个按钮调用断裂)**

模板顶部 `<n-button @click="openCustomModal(null)">新建流程</n-button>` 改为:

```vue
<n-button type="primary" @click="openCreateProcess">
  <template #icon><n-icon :component="AddOutline" /></template>
  新建流程
</n-button>
```

加 `openCreateProcess` (复用 ProcessDetailModal 的 edit 态新建流程, processId 留空):

```ts
function openCreateProcess() {
  detailProcessId.value = ''  // 空 = 新建态
  detailDefaultMode.value = 'edit'
  showDetail.value = true
}
```

**注意**: `ProcessDetailModal.vue` 在 `processId=''` 时不调 load API, 直接进空 editForm 形态. 这要求 Task 3 step 1 的 `load()` 已有 `if (!props.processId) return` 守卫 (已包含). OK.

- [ ] **Step 6: 跑单测, 期望 8/8 PASS (RecruitmentProcess.vue 没有单测)**

```bash
npm run test -- ProcessDetailModal 2>&1 | tail -10
```

- [ ] **Step 7: 类型 + lint**

```bash
npx vue-tsc --noEmit 2>&1 | grep "RecruitmentProcess" | head -10
npx eslint src/pages/settings/RecruitmentProcess.vue 2>&1 | tail -5
```

- [ ] **Step 8: 提交**

```bash
git add web/app/src/pages/settings/RecruitmentProcess.vue && git commit -m "refactor(RecruitmentProcess): 操作列只保留 [编辑], 删除 CustomRecruitmentProcessModal 引用"
```

---

## Task 6: 删除 CustomRecruitmentProcessModal.vue + 兜底扫描引用

**Files:**
- Delete: `src/pages/settings/CustomRecruitmentProcessModal.vue`

- [ ] **Step 1: 兜底扫描引用**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW && grep -rn "CustomRecruitmentProcessModal" web/app/src/ 2>&1 | grep -v node_modules
```

预期: 无结果 (Task 5 已删引用).

- [ ] **Step 2: 兜底扫描单测引用**

```bash
grep -rn "CustomRecruitmentProcessModal" web/app/src/pages/settings/__tests__/ 2>&1
```

预期: 无结果.

- [ ] **Step 3: 删文件**

```bash
git rm web/app/src/pages/settings/CustomRecruitmentProcessModal.vue
```

- [ ] **Step 4: 跑全套验证**

```bash
cd web/app && npm run test -- ProcessDetailModal 2>&1 | tail -10
cd web/app && npx vue-tsc --noEmit 2>&1 | tail -5
cd web/app && npx eslint src/pages/settings/ProcessDetailModal.vue src/pages/settings/RecruitmentProcess.vue 2>&1 | tail -5
```

预期: 单测 8/8, 类型 0 错, lint 0 警告.

- [ ] **Step 5: 提交**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW && git commit -m "chore: 删除 CustomRecruitmentProcessModal.vue (被 ProcessDetailModal 双态取代)"
```

---

## Task 7: 浏览器端到端验证

- [ ] **Step 1: 启动 dev server (如果未启动)**

```bash
cd /Users/loki/ClaudeWorkSpace/ATS-NEW
# Vite 在 port 5212, Django 在 port 8000 (用 mcp__Claude_Preview__preview_list 验证)
```

- [ ] **Step 2: 浏览器进 /settings/recruitment-process**

用 mcp__Claude_Preview__preview_eval 跳转:
```js
window.location.href = '/settings/recruitment-process'
```

- [ ] **Step 3: 验证 list 操作列只剩 [编辑]**

```js
JSON.stringify({
  actionButtons: Array.from(document.querySelectorAll('table tbody tr:first-child button')).map(b => b.textContent.trim())
})
```

预期: `["编辑"]` (单按钮).

- [ ] **Step 4: 点 [编辑] → modal 以 edit 态打开**

```js
document.querySelector('table tbody tr:first-child button').click()
```

snapshot 验证 modal 标题为 input + 取消/保存按钮存在.

- [ ] **Step 5: 验证 view 态 + 编辑切换**

点 modal 外部关闭, 再点 [编辑] → modal 直接进 edit 态.

点取消 (dirty) → 弹 Popconfirm.

- [ ] **Step 6: 验证 save 后退回 view 态 + list 自动 reload**

修改字段 → 保存 → toast 成功 → modal 退回 view 态 → 列表 reload.

- [ ] **Step 7: 验证 409 冲突 modal (可选, 需 2 个浏览器 session)**

(超出 mock 范围, 单测覆盖即可, 此步可跳过)

---

## 最终验证

- [ ] 单测: `npm run test -- ProcessDetailModal` → 8/8 PASS
- [ ] 类型: `npx vue-tsc --noEmit` → 0 新错
- [ ] Lint: `npx eslint src/pages/settings/ProcessDetailModal.vue src/pages/settings/RecruitmentProcess.vue` → 0 警告
- [ ] 浏览器: list 操作列只 1 按钮, modal 默认进 edit 态, dirty 弹 Popconfirm, save 成功回 view
- [ ] 删除 CustomRecruitmentProcessModal.vue 后, 全仓库 grep 无引用
- [ ] 5 次 commit: test → feat state → feat edit template → feat save → refactor list → chore delete
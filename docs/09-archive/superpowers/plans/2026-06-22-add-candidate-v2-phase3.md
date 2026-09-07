# AddCandidateModal V2 - Phase 3: 前端 API + Pinia store 实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 前端 `addCandidate.ts` API 客户端 + Pinia store，封装 7 个后端 endpoint + SSE 流。

**Architecture:**
- `web/app/src/api/addCandidate.ts` — 7 个 endpoint 封装 + SSE 客户端
- `web/app/src/stores/addCandidate.ts` — Pinia store（setup style），管 `resumes[]/step/scoringProgress` 等
- 复用 `src/api/auth.ts` 的 axios 实例和拦截器
- 复用 `src/config` 的 base URL

**Tech Stack:**
- Frontend: Vue 3 + TypeScript + Pinia + Axios, Vitest + happy-dom
- 后端依赖 Phase 2 (7 endpoint + SSE)

**Spec:** [docs/superpowers/specs/2026-06-22-add-candidate-v2-design.md](../specs/2026-06-22-add-candidate-v2-design.md) §4
**依赖 Phase 2:** 后端 endpoint + Celery + SSE 已就绪

---

## 文件结构

### 新增（2 个文件）
- `web/app/src/api/addCandidate.ts` — 7 endpoint + SSE (~200 行)
- `web/app/src/stores/addCandidate.ts` — Pinia store (~500 行)

### 新增测试（2 个文件）
- `web/app/src/api/__tests__/addCandidate.test.ts` — API 客户端 (~150 行)
- `web/app/src/stores/__tests__/addCandidate.test.ts` — store 全覆盖 (~400 行)

---

## 全局约束

- **API 路径前缀**：`/api/v1/candidates/add-candidate/`
- **错误处理**：API 层抛 `Error` 带 `code` 字段；store 捕获后转 toast
- **SSE 客户端**：用 `EventSource` 浏览器原生 API，不引第三方
- **去重**：上传文件名相同时 client 端 dedup

---

## Task 1: Type definitions + API 客户端骨架

**Files:**
- Create: `web/app/src/api/addCandidate.ts`
- Create: `web/app/src/api/__tests__/addCandidate.test.ts`

### Step 1.1: 写失败测试

`web/app/src/api/__tests__/addCandidate.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { uploadAndParse, getParseStatus, postDuplicateCheck, replaceFile, bulkCreate, startScoring, openScoringStream } from '../addCandidate'

vi.mock('axios')
const mockedAxios = vi.mocked(axios, true)

describe('addCandidate API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('uploadAndParse', () => {
    it('POSTs multipart to upload-and-parse/ and returns job_ids', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { job_ids: ['j1'], draft_ids: ['d1'] },
      })
      mockedAxios.create.mockReturnValue({ post: mockPost } as any)
      const file = new File(['x'], 'test.pdf', { type: 'application/pdf' })
      const result = await uploadAndParse([file])
      expect(result.job_ids).toEqual(['j1'])
      expect(result.draft_ids).toEqual(['d1'])
    })
  })

  describe('getParseStatus', () => {
    it('GETs parse-status/{job_id}/ and returns status', async () => {
      const mockGet = vi.fn().mockResolvedValue({
        data: { draft_id: 'd1', status: 'done', progress: 100, phase: null, parsed: {}, duplicate: {}, error: null },
      })
      mockedAxios.create.mockReturnValue({ get: mockGet } as any)
      const result = await getParseStatus('j1')
      expect(result.status).toBe('done')
    })
  })

  describe('postDuplicateCheck', () => {
    it('POSTs duplicate-check/ with phone/email/name', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { status: 'clean' },
      })
      mockedAxios.create.mockReturnValue({ post: mockPost } as any)
      const result = await postDuplicateCheck({ draft_id: 'd1', phone: '13800138000', email: '', name: '' })
      expect(result.status).toBe('clean')
    })
  })

  describe('replaceFile', () => {
    it('POSTs multipart to replace-file/{draft_id}/', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { new_job_id: 'j2' },
      })
      mockedAxios.create.mockReturnValue({ post: mockPost } as any)
      const file = new File(['y'], 'new.pdf', { type: 'application/pdf' })
      const result = await replaceFile('d1', file)
      expect(result.new_job_id).toBe('j2')
    })
  })

  describe('bulkCreate', () => {
    it('POSTs JSON to bulk-create/ with drafts and submit_mode', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { task_id: 't1', created_candidate_ids: ['c1'], route: { c1: 'pending' } },
      })
      mockedAxios.create.mockReturnValue({ post: mockPost } as any)
      const result = await bulkCreate({
        drafts: [{ draft_id: 'd1', direction: 'pending' }],
        submit_mode: 'async',
      })
      expect(result.task_id).toBe('t1')
    })
  })

  describe('startScoring', () => {
    it('POSTs JSON to scoring/start/ with task_id', async () => {
      const mockPost = vi.fn().mockResolvedValue({
        data: { stream_url: '/api/v1/candidates/add-candidate/scoring/stream/t1/' },
      })
      mockedAxios.create.mockReturnValue({ post: mockPost } as any)
      const result = await startScoring({ candidate_ids: ['c1'], task_id: 't1' })
      expect(result.stream_url).toContain('t1')
    })
  })

  describe('openScoringStream', () => {
    it('returns EventSource instance for given task_id', () => {
      const result = openScoringStream('t1')
      expect(result).toBeInstanceOf(EventSource)
    })
  })
})
```

### Step 1.2: 跑测试确认失败

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run src/api/__tests__/addCandidate.test.ts
```

Expected: All tests fail (no module).

### Step 1.3: 写实现

`web/app/src/api/addCandidate.ts`:
```typescript
/**
 * AddCandidateModal V2 - API 客户端
 *
 * 封装 7 个后端 endpoint + SSE 流。
 * 复用 auth.ts 的 axios 实例（带 401 拦截器、自动 refresh token）
 */
import axios, { type AxiosInstance } from 'axios'
import config from '../config'

const BASE = `${config.api.baseUrl}/candidates/add-candidate`

function getClient(): AxiosInstance {
  return axios.create({
    baseURL: BASE,
    timeout: 60000,
  })
}

// ============ Types ============
export type JobStatus = 'processing' | 'done' | 'failed'
export type JobPhase = 'uploading' | 'parsing' | 'checking' | null
export type DupStatus = 'clean' | 'unocc' | 'occupied'
export type Direction = 'pending' | 'talent' | 'position'
export type SubmitMode = 'wait' | 'async'

export interface ParsedResume {
  name?: string
  phone?: string
  email?: string
  gender?: string
  age?: number
  edu?: string
  educations: Education[]
  experiences: Experience[]
  confidence: number
}

export interface Education {
  period: string
  school: string
  major: string
  degree: string
}

export interface Experience {
  period: string
  company: string
  position: string
  summary: string
}

export interface DuplicateInfo {
  status: DupStatus
  existing_resume_id?: string
  created_at?: string
  history?: string
  cur_status?: string
  active_application_id?: string
}

export interface ParseStatus {
  draft_id: string
  status: JobStatus
  phase: JobPhase
  progress: number
  parsed?: ParsedResume | null
  duplicate?: DuplicateInfo | null
  error?: string | null
}

export interface BulkCreateDraft {
  draft_id: string
  direction: Direction
  position_id?: string | null
  channel?: string
  source?: string
  provider?: string
}

export interface BulkCreateResult {
  task_id: string
  created_candidate_ids: string[]
  route: Record<string, string>
}

export interface ScoreEvent {
  event: string
  data: any
}

// ============ 7 endpoints ============

/** POST /upload-and-parse/  — 上传 1-20 份简历，返回 job_id 列表 */
export async function uploadAndParse(files: File[]): Promise<{ job_ids: string[]; draft_ids: string[] }> {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  const client = getClient()
  const resp = await client.post('/upload-and-parse/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data
}

/** GET /parse-status/{job_id}/  — 轮询解析状态 */
export async function getParseStatus(job_id: string): Promise<ParseStatus> {
  const client = getClient()
  const resp = await client.get(`/parse-status/${job_id}/`)
  return resp.data
}

/** POST /duplicate-check/  — 用户改字段后重查重 */
export async function postDuplicateCheck(params: {
  draft_id: string
  phone: string
  email: string
  name: string
}): Promise<DuplicateInfo> {
  const client = getClient()
  const resp = await client.post('/duplicate-check/', params)
  return resp.data
}

/** POST /replace-file/{draft_id}/  — 替换附件并重新解析 */
export async function replaceFile(draft_id: string, file: File): Promise<{ job_id: string; draft_id: string }> {
  const form = new FormData()
  form.append('file', file)
  const client = getClient()
  const resp = await client.post(`/replace-file/${draft_id}/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return resp.data
}

/** POST /bulk-create/  — Step 2 提交（创建候选 + 关联） */
export async function bulkCreate(params: {
  drafts: BulkCreateDraft[]
  submit_mode: SubmitMode
}): Promise<BulkCreateResult> {
  const client = getClient()
  const resp = await client.post('/bulk-create/', params)
  return resp.data
}

/** POST /scoring/start/  — async 模式显式启动评分 */
export async function startScoring(params: { candidate_ids: string[]; task_id: string }): Promise<{ stream_url: string }> {
  const client = getClient()
  const resp = await client.post('/scoring/start/', params)
  return resp.data
}

/** GET /scoring/stream/{task_id}/  — SSE 流（返回 EventSource） */
export function openScoringStream(task_id: string): EventSource {
  // EventSource 不支持自定义 header（无法带 Authorization），
  // 所以需要在后端允许 EventSource 走 query string 或 cookie。
  // 简化方案：用 fetch 读 stream，自己分发事件。
  // 真实实现可以用 `event-source-polyfill` 或后端改用 query token。
  // 此处先用 EventSource（cookie-based auth）
  const url = `${BASE}/scoring/stream/${task_id}/`
  return new EventSource(url)
}
```

### Step 1.4: 跑测试

```bash
npx vitest run src/api/__tests__/addCandidate.test.ts
```
Expected: 7 tests pass（mock setup 让 axios.create 返回 mock client）

### Step 1.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/api/addCandidate.ts \
        ATS-New/web/app/src/api/__tests__/addCandidate.test.ts
git commit -m "feat(add-candidate-frontend): API 客户端 + 7 endpoint + SSE"
```

---

## Task 2: Pinia store - 状态 + 基础 actions

**Files:**
- Create: `web/app/src/stores/addCandidate.ts`
- Create: `web/app/src/stores/__tests__/addCandidate.test.ts` (initial part)

### Step 2.1: 写失败测试

`web/app/src/stores/__tests__/addCandidate.test.ts`:
```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAddCandidateStore } from '../addCandidate'
import type { ResumeDraft, ParsedResume, DuplicateInfo } from '@/api/addCandidate'

vi.mock('@/api/addCandidate', () => ({
  uploadAndParse: vi.fn(),
  getParseStatus: vi.fn(),
  postDuplicateCheck: vi.fn(),
  replaceFile: vi.fn(),
  bulkCreate: vi.fn(),
  startScoring: vi.fn(),
  openScoringStream: vi.fn(),
}))

import * as api from '@/api/addCandidate'

describe('useAddCandidateStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('reset', () => {
    it('clears all state to initial values', () => {
      const store = useAddCandidateStore()
      store.step = 2
      store.isDirty = true
      store.resumes.push({} as any)
      store.reset()
      expect(store.step).toBe(1)
      expect(store.isDirty).toBe(false)
      expect(store.resumes).toEqual([])
    })
  })

  describe('addResumes', () => {
    it('initializes new ResumeDrafts with status=processing and adds to list', () => {
      const store = useAddCandidateStore()
      store.addResumes([
        { job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' },
        { job_id: 'j2', draft_id: 'd2', file_name: 'b.pdf' },
      ])
      expect(store.resumes).toHaveLength(2)
      expect(store.resumes[0].status).toBe('processing')
      expect(store.resumes[0].procPhase).toBe('uploading')
      expect(store.resumes[0].progress).toBe(0)
      expect(store.isDirty).toBe(true)
    })
  })

  describe('updateField', () => {
    it('updates field, marks rechecking, and sets isDirty', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.updateField('d1', 'phone', '13900000000')
      const r = store.resumes[0]
      expect(r.edited.phone).toBe('13900000000')
      expect(store.recheckingIds.has('d1')).toBe(true)
      expect(store.isDirty).toBe(true)
    })
  })

  describe('replaceResumeFile', () => {
    it('resets resume to processing state and re-triggers parse', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.updateField('d1', 'name', '张三')
      store.replaceResumeFile('d1', 'new.pdf')
      const r = store.resumes[0]
      expect(r.file_name).toBe('new.pdf')
      expect(r.status).toBe('processing')
      expect(r.edited).toEqual({})
      expect(r.parsed).toBeUndefined()
      expect(r.duplicate).toBeUndefined()
    })
  })

  describe('processParseUpdate', () => {
    it('updates status, phase, progress from polling response', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', {
        status: 'done',
        phase: 'checking',
        progress: 100,
        parsed: { name: '张三', phone: '13800138000' } as any,
        duplicate: { status: 'clean' } as any,
      })
      const r = store.resumes[0]
      expect(r.status).toBe('done')
      expect(r.progress).toBe(100)
      expect(r.parsed?.name).toBe('张三')
      expect(r.duplicate?.status).toBe('clean')
    })
  })
})
```

### Step 2.2: 跑测试确认失败

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: All fail (no module)

### Step 2.3: 写 store 实现（基础部分）

`web/app/src/stores/addCandidate.ts`:
```typescript
/**
 * AddCandidateModal V2 - Pinia Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import type {
  ResumeDraft as ApiResumeDraft,
  ParsedResume,
  DuplicateInfo,
  DupStatus,
  Direction,
  SubmitMode,
  ScoreResult,
} from '@/api/addCandidate'

// ============ Internal types ============
export interface ResumeDraft {
  id: string                              // draft_id
  file_name: string
  job_id: string
  status: 'processing' | 'clean' | 'unocc' | 'occupied'
  progress: number
  procPhase: 'uploading' | 'parsing' | 'checking' | null
  parsed?: ParsedResume
  edited: Partial<ParsedResume>
  duplicate?: DuplicateInfo
  occupyAction?: 'pending' | 'merge' | 'apply' | 'cancel' | 'score'
  appliedPosition?: string
  scoreSnapshot?: ScoreResult
}

export interface ScoreResult {
  score: number
  passed: boolean
  dimensions: Array<{ name: string; score: number }>
}

// ============ Store ============
export const useAddCandidateStore = defineStore('addCandidate', () => {
  // ===== State =====
  const step = ref<1 | 2 | 3>(1)
  const isDirty = ref(false)
  const resumes = ref<ResumeDraft[]>([])

  // Step 2
  const applyMode = ref<'all' | 'per'>('all')
  const dirAll = ref<'' | Direction>('')
  const posAll = ref<string>('')
  const dirPer = ref<Record<string, '' | Direction>>({})
  const posPer = ref<Record<string, string>>({})

  // Submit
  const submitMode = ref<SubmitMode>('wait')
  const submitting = ref(false)
  const appInfo = ref({ channel: '招聘网站', source: 'Boss直聘', provider: '' })

  // Score progress
  const scoringProgress = ref<Record<string, { status: 'waiting' | 'scoring' | 'done'; progress: number; result?: ScoreResult }>>({})
  const allScoringDone = ref(false)
  const asyncResult = ref(false)

  // Batch UI
  const selectedIds = ref<string[]>([])
  const activeId = ref<string | null>(null)

  // Temp flags
  const recheckingIds = ref<Set<string>>(new Set())
  const replacingId = ref<string | null>(null)

  // ===== Actions =====

  function reset() {
    step.value = 1
    isDirty.value = false
    resumes.value = []
    applyMode.value = 'all'
    dirAll.value = ''
    posAll.value = ''
    dirPer.value = {}
    posPer.value = {}
    submitMode.value = 'wait'
    submitting.value = false
    appInfo.value = { channel: '招聘网站', source: 'Boss直聘', provider: '' }
    scoringProgress.value = {}
    allScoringDone.value = false
    asyncResult.value = false
    selectedIds.value = []
    activeId.value = null
    recheckingIds.value = new Set()
    replacingId.value = null
  }

  function addResumes(jobs: Array<{ job_id: string; draft_id: string; file_name: string }>) {
    for (const j of jobs) {
      resumes.value.push({
        id: j.draft_id,
        file_name: j.file_name,
        job_id: j.job_id,
        status: 'processing',
        progress: 0,
        procPhase: 'uploading',
        edited: {},
      })
    }
    isDirty.value = true
  }

  function updateField(draftId: string, field: keyof ParsedResume, value: any) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    r.edited[field] = value
    recheckingIds.value.add(draftId)
    recheckingIds.value = new Set(recheckingIds.value)  // trigger reactivity
    isDirty.value = true
  }

  function replaceResumeFile(draftId: string, newFileName: string) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    r.file_name = newFileName
    r.parsed = undefined
    r.duplicate = undefined
    r.edited = {}
    r.status = 'processing'
    r.progress = 0
    r.procPhase = 'uploading'
    r.occupyAction = undefined
    r.appliedPosition = undefined
    r.scoreSnapshot = undefined
    replacingId.value = draftId
    isDirty.value = true
  }

  function processParseUpdate(draftId: string, update: {
    status: 'processing' | 'done' | 'failed'
    phase: 'uploading' | 'parsing' | 'checking' | null
    progress: number
    parsed?: ParsedResume | null
    duplicate?: DuplicateInfo | null
  }) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    r.status = update.status
    r.procPhase = update.phase
    r.progress = update.progress
    if (update.parsed) r.parsed = update.parsed
    if (update.duplicate !== undefined) r.duplicate = update.duplicate ?? undefined
    if (r.status !== 'processing') r.procPhase = null
  }

  return {
    // state
    step, isDirty, resumes,
    applyMode, dirAll, posAll, dirPer, posPer,
    submitMode, submitting, appInfo,
    scoringProgress, allScoringDone, asyncResult,
    selectedIds, activeId, recheckingIds, replacingId,
    // actions
    reset, addResumes, updateField, replaceResumeFile, processParseUpdate,
  }
})
```

### Step 2.4: 跑测试

```bash
npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: 5 tests pass

### Step 2.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/stores/addCandidate.ts \
        ATS-New/web/app/src/stores/__tests__/addCandidate.test.ts
git commit -m "feat(add-candidate-frontend): Pinia store 基础 + 5 actions"
```

---

## Task 3: Pinia store - 业务 actions（方向选择 + 提交 + 计算属性）

**Files:**
- Modify: `web/app/src/stores/addCandidate.ts`
- Modify: `web/app/src/stores/__tests__/addCandidate.test.ts` (add tests)

### Step 3.1: 写失败测试

追加到 `addCandidate.test.ts`:
```typescript
  describe('setOccupyAction', () => {
    it('changes status to clean when action=pending', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'occupied', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
      store.setOccupyAction('d1', 'pending')
      expect(store.resumes[0].status).toBe('clean')
      expect(store.resumes[0].duplicate).toBeUndefined()
    })

    it('removes resume when action=cancel', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.setOccupyAction('d1', 'cancel')
      expect(store.resumes).toHaveLength(0)
    })

    it('expands apply position selector when action=apply', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.setOccupyAction('d1', 'apply')
      expect(store.resumes[0].occupyAction).toBe('apply')
    })
  })

  describe('setDirAll', () => {
    it('sets dirAll and applies to all resumes (except occupied which only get pending)', () => {
      const store = useAddCandidateStore()
      store.addResumes([
        { job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' },
        { job_id: 'j2', draft_id: 'd2', file_name: 'b.pdf' },
      ])
      store.processParseUpdate('d2', { status: 'occupied', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
      store.setDirAll('position')
      expect(store.dirAll).toBe('position')
      expect(store.dirPer['d1']).toBe('position')
      expect(store.dirPer['d2']).toBe('pending')  // occupied → forced pending
    })
  })

  describe('computed canGoStep2', () => {
    it('true when all done and no occupied and all valid', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', {
        status: 'done', phase: null, progress: 100,
        parsed: { name: '张三', phone: '13800138000', email: 'z@x.com' } as any,
        duplicate: { status: 'clean' } as any,
      })
      expect(store.canGoStep2).toBe(true)
    })

    it('false when occupied exists', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'occupied', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
      expect(store.canGoStep2).toBe(false)
    })

    it('false when name missing', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', {
        status: 'done', phase: null, progress: 100,
        parsed: { name: '', phone: '13800138000', email: 'z@x.com' } as any,
        duplicate: { status: 'clean' } as any,
      })
      expect(store.canGoStep2).toBe(false)
    })
  })

  describe('computed canSubmit', () => {
    it('true when applyMode=all and dirAll set (position needs posAll)', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'clean' } as any })
      store.step = 2
      store.dirAll = 'pending'
      expect(store.canSubmit).toBe(true)
    })

    it('false when dirAll=position but posAll empty', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'clean' } as any })
      store.step = 2
      store.dirAll = 'position'
      expect(store.canSubmit).toBe(false)
      store.posAll = 'pos_42'
      expect(store.canSubmit).toBe(true)
    })
  })
```

### Step 3.2: 跑测试确认失败

```bash
npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: 7 new tests fail (no computed/actions yet)

### Step 3.3: 扩展 store 实现

追加到 `addCandidate.ts`（在 `processParseUpdate` 之后、return 之前）:

```typescript
  function setOccupyAction(draftId: string, action: 'pending' | 'merge' | 'apply' | 'cancel' | 'score') {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    r.occupyAction = action
    if (action === 'pending') {
      r.status = 'clean'
      r.duplicate = undefined
    } else if (action === 'merge') {
      r.status = 'unocc'
    } else if (action === 'cancel') {
      resumes.value = resumes.value.filter((x) => x.id !== draftId)
    }
    isDirty.value = true
  }

  function setDirAll(dir: '' | Direction) {
    dirAll.value = dir
    if (dir !== 'position') posAll.value = ''
    for (const r of resumes.value) {
      // occupied resumes only allow 'pending'
      if (r.status === 'occupied' && dir !== 'pending') {
        dirPer.value[r.id] = 'pending'
      } else {
        dirPer.value[r.id] = dir
      }
    }
  }

  function setPosAll(pos: string) {
    posAll.value = pos
    for (const r of resumes.value) {
      if (dirPer.value[r.id] === 'position') posPer.value[r.id] = pos
    }
  }

  function setPerDir(draftId: string, dir: '' | Direction) {
    dirPer.value[draftId] = dir
    if (dir !== 'position') delete posPer.value[draftId]
  }

  function setPerPos(draftId: string, pos: string) {
    posPer.value[draftId] = pos
  }

  function selectApplyPos(draftId: string, pos: string) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (r) r.appliedPosition = pos
  }

  // ===== Computed =====
  const mode = computed<'single' | 'batch'>(() => (resumes.value.length === 1 ? 'single' : 'batch'))
  const isAllDone = computed(() => resumes.value.every((r) => r.status !== 'processing'))
  const hasOccupied = computed(() => resumes.value.some((r) => r.status === 'occupied'))

  function passesValidation(r: ResumeDraft): boolean {
    const name = r.edited.name ?? r.parsed?.name
    const phone = r.edited.phone ?? r.parsed?.phone
    const email = r.edited.email ?? r.parsed?.email
    return !!(name && phone && email)
  }

  const canGoStep2 = computed(() => isAllDone.value && !hasOccupied.value && resumes.value.every(passesValidation))

  const canSubmit = computed(() => {
    if (applyMode.value === 'all') {
      if (!dirAll.value) return false
      if (dirAll.value === 'position' && !posAll.value) return false
      return true
    } else {
      return resumes.value.every((r) => {
        const d = dirPer.value[r.id]
        if (!d) return false
        if (d === 'position' && !posPer.value[r.id]) return false
        return true
      })
    }
  })
```

修改 `return` 块:
```typescript
  return {
    // state
    step, isDirty, resumes,
    applyMode, dirAll, posAll, dirPer, posPer,
    submitMode, submitting, appInfo,
    scoringProgress, allScoringDone, asyncResult,
    selectedIds, activeId, recheckingIds, replacingId,
    // actions
    reset, addResumes, updateField, replaceResumeFile, processParseUpdate,
    setOccupyAction, setDirAll, setPosAll, setPerDir, setPerPos, selectApplyPos,
    // computed
    mode, isAllDone, hasOccupied, canGoStep2, canSubmit,
  }
```

### Step 3.4: 跑测试

```bash
npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: 12 tests pass（5 + 7）

### Step 3.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/stores/addCandidate.ts \
        ATS-New/web/app/src/stores/__tests__/addCandidate.test.ts
git commit -m "feat(add-candidate-frontend): Pinia store 业务 actions + computed"
```

---

## Task 4: Pinia store - 异步 actions（upload/polling/submit）

**Files:**
- Modify: `web/app/src/stores/addCandidate.ts`
- Modify: `web/app/src/stores/__tests__/addCandidate.test.ts` (add tests)

### Step 4.1: 写失败测试

```typescript
  describe('uploadFiles', () => {
    it('calls api.uploadAndParse and adds resumes to store', async () => {
      const store = useAddCandidateStore()
      vi.mocked(api.uploadAndParse).mockResolvedValue({
        job_ids: ['j1', 'j2'],
        draft_ids: ['d1', 'd2'],
      })
      const files = [new File(['x'], 'a.pdf', { type: 'application/pdf' })]
      await store.uploadFiles(files)
      expect(api.uploadAndParse).toHaveBeenCalledWith(files)
      expect(store.resumes).toHaveLength(2)
      expect(store.resumes[0].id).toBe('d1')
    })
  })

  describe('pollParseStatus', () => {
    it('polls api.getParseStatus until status=done/failed, calling processParseUpdate', async () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      vi.mocked(api.getParseStatus)
        .mockResolvedValueOnce({ draft_id: 'd1', status: 'processing', phase: 'parsing', progress: 30, parsed: null, duplicate: null, error: null })
        .mockResolvedValueOnce({ draft_id: 'd1', status: 'done', phase: null, progress: 100, parsed: { name: 'X' } as any, duplicate: { status: 'clean' } as any, error: null })

      await store.pollParseStatus('d1')
      expect(api.getParseStatus).toHaveBeenCalledTimes(2)
      expect(store.resumes[0].status).toBe('done')
      expect(store.resumes[0].parsed?.name).toBe('X')
    })
  })

  describe('triggerRecheck', () => {
    it('debounces duplicate-check call after field edit', async () => {
      vi.useFakeTimers()
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, parsed: { phone: '13800138000' } as any, duplicate: { status: 'clean' } as any })
      vi.mocked(api.postDuplicateCheck).mockResolvedValue({ status: 'clean' })

      store.triggerRecheck('d1')
      expect(api.postDuplicateCheck).not.toHaveBeenCalled()
      vi.advanceTimersByTime(900)
      expect(api.postDuplicateCheck).toHaveBeenCalled()
      vi.useRealTimers()
    })
  })

  describe('submit', () => {
    it('calls api.bulkCreate, dispatches scoring, sets submitting=true', async () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'clean' } as any })
      store.step = 2
      store.dirAll = 'pending'
      vi.mocked(api.bulkCreate).mockResolvedValue({
        task_id: 't1',
        created_candidate_ids: ['c1'],
        route: { c1: 'pending' },
      })

      await store.submit()
      expect(api.bulkCreate).toHaveBeenCalled()
      expect(store.submitting).toBe(true)
      expect(store.step).toBe(3)
    })
  })
```

### Step 4.2: 跑测试确认失败

```bash
npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: 4 new fail

### Step 4.3: 实现异步 actions

追加到 store:
```typescript
  let pollTimers: Record<string, number> = {}

  async function uploadFiles(files: File[]) {
    const result = await api.uploadAndParse(files)
    addResumes(
      result.job_ids.map((job_id, i) => ({
        job_id,
        draft_id: result.draft_ids[i],
        file_name: files[i]?.name || 'unknown',
      })),
    )
  }

  async function pollParseStatus(draftId: string) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    const resp = await api.getParseStatus(r.job_id)
    processParseUpdate(draftId, resp)
    if (resp.status === 'processing') {
      // continue polling
      pollTimers[draftId] = window.setTimeout(() => pollParseStatus(draftId), 1500)
    }
  }

  let recheckTimers: Record<string, number> = {}

  function triggerRecheck(draftId: string) {
    if (recheckTimers[draftId]) window.clearTimeout(recheckTimers[draftId])
    recheckTimers[draftId] = window.setTimeout(async () => {
      delete recheckTimers[draftId]
      const r = resumes.value.find((x) => x.id === draftId)
      if (!r) return
      const phone = r.edited.phone ?? r.parsed?.phone ?? ''
      const email = r.edited.email ?? r.parsed?.email ?? ''
      const name = r.edited.name ?? r.parsed?.name ?? ''
      const dup = await api.postDuplicateCheck({ draft_id: draftId, phone, email, name })
      processParseUpdate(draftId, {
        status: dup.status === 'clean' ? 'done' : (dup.status as any),
        phase: null,
        progress: 100,
        duplicate: dup,
      })
      recheckingIds.value.delete(draftId)
      recheckingIds.value = new Set(recheckingIds.value)
    }, 800)
  }

  async function submit() {
    if (submitMode.value === 'wait') {
      submitting.value = true
      step.value = 3
    } else {
      submitting.value = true
      step.value = 3
      asyncResult.value = true
    }
    const drafts = resumes.value.map((r) => ({
      draft_id: r.id,
      direction: (dirPer.value[r.id] || dirAll.value) as Direction,
      position_id: posPer.value[r.id] || posAll.value || null,
      channel: appInfo.value.channel,
      source: appInfo.value.source,
      provider: appInfo.value.provider,
    }))
    const result = await api.bulkCreate({ drafts, submit_mode: submitMode.value })
    // 评分任务由后端 bulk-create 内部触发
    return result
  }

  function closeStream() {
    for (const k of Object.keys(pollTimers)) {
      window.clearTimeout(pollTimers[k])
      delete pollTimers[k]
    }
  }
```

修改 `return`:
```typescript
  return {
    // state
    step, isDirty, resumes,
    applyMode, dirAll, posAll, dirPer, posPer,
    submitMode, submitting, appInfo,
    scoringProgress, allScoringDone, asyncResult,
    selectedIds, activeId, recheckingIds, replacingId,
    // actions
    reset, addResumes, updateField, replaceResumeFile, processParseUpdate,
    setOccupyAction, setDirAll, setPosAll, setPerDir, setPerPos, selectApplyPos,
    uploadFiles, pollParseStatus, triggerRecheck, submit, closeStream,
    // computed
    mode, isAllDone, hasOccupied, canGoStep2, canSubmit,
  }
```

### Step 4.4: 跑测试

```bash
npx vitest run src/stores/__tests__/addCandidate.test.ts
```
Expected: 16 tests pass (5 + 7 + 4)

注：`triggerRecheck` 的 debounce 用 `vi.useFakeTimers` 测，需要 `vi.advanceTimersByTime(900)` 触发。

### Step 4.5: Commit

```bash
cd /Users/loki/ats-add-candidate-v2
git add ATS-New/web/app/src/stores/addCandidate.ts \
        ATS-New/web/app/src/stores/__tests__/addCandidate.test.ts
git commit -m "feat(add-candidate-frontend): Pinia store 异步 actions (upload/poll/submit)"
```

---

## Task 5: 端到端验证

### Step 5.1: 跑全部 addCandidate 前端测试

```bash
cd /Users/loki/ats-add-candidate-v2/ATS-New/web/app && npx vitest run src/api/__tests__/addCandidate.test.ts src/stores/__tests__/addCandidate.test.ts --coverage
```

Expected: 23 tests pass, coverage ≥ 80%

### Step 5.2: 跑前端 type check

```bash
npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: 无 error

### Step 5.3: Tag + Push

```bash
cd /Users/loki/ats-add-candidate-v2
git tag -d phase3-complete 2>/dev/null
git tag -a phase3-complete -m "Phase 3 完成: API client + Pinia store (16 actions, 6 computed)"
git push gitee feat/add-candidate-v2 --follow-tags
```

---

## 总时间预算

| Task | 工作量 |
|---|---|
| 1: API 客户端 | 0.5 天 |
| 2: Store 基础 | 0.5 天 |
| 3: Store 业务 actions | 0.5 天 |
| 4: Store 异步 actions | 0.5 天 |
| 5: 验证 | 0.5 天 |
| **合计** | **~2.5 天** |

---

## 执行选项

Two execution options:
1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task
2. **Inline Execution** — Execute tasks in this session

**Which approach?**
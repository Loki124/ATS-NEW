/**
 * AddCandidateModal V2 - Pinia Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import type {
  ParsedResume,
  DuplicateInfo,
  DupStatus,
  Direction,
  SubmitMode,
} from '@/api/addCandidate'
import * as api from '@/api/addCandidate'
// 2026-06-28 花无缺: ScoreResult 和 ResumeDraft 都是 store 内部定义的 (line 21 + 34),
//                  不从 @/api/addCandidate 导入 (api 文件没导出这两个).
//                  TS2305 build fail 修法: 从 import block 里删.
//                  ApiResumeDraft alias 也跟着删 (没用了).

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
    r.procPhase = update.phase
    r.progress = update.progress
    if (update.parsed) r.parsed = update.parsed
    if (update.duplicate !== undefined) r.duplicate = update.duplicate ?? undefined
    // 解析任务完成时, 业务 status 由 duplicate 决定 (而不是任务的 'done' 状态)
    if (update.status === 'done') {
      const dupStatus = update.duplicate?.status
      r.status = dupStatus ? dupStatus : 'clean'
    } else if (update.status === 'failed') {
      // 2026-06-28 花无缺: TS2322 修法 — 任务级 'failed' 业务状态 fallback 到 'clean'
      //                     (跟 done + 无 dupStatus 行为一致, 用户看到 "待处理" 而不是 "处理中")
      r.status = 'clean'
    } else {
      // 'processing'
      r.status = update.status
    }
    if (r.status !== 'processing') r.procPhase = null
  }

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

  // ===== Async actions =====

  // poll timers keyed by draft_id (so we can cancel individually)
  const pollTimers: Record<string, number> = {}
  // recheck timers keyed by draft_id (debounced)
  const recheckTimers: Record<string, number> = {}

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

  async function pollParseStatus(draftId: string, overrideJobId?: string) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    const jobId = overrideJobId || r.job_id
    if (overrideJobId) r.job_id = overrideJobId
    const resp = await api.getParseStatus(jobId)
    processParseUpdate(draftId, {
      status: resp.status as 'processing' | 'done' | 'failed',
      phase: resp.phase,
      progress: resp.progress,
      parsed: resp.parsed ?? undefined,
      duplicate: resp.duplicate ?? undefined,
    })
    if (resp.status === 'processing') {
      // continue polling — store timer so closeStream() can cancel,
      // but wait for the next poll to finish before resolving so callers
      // can `await` until the draft reaches a terminal status.
      await new Promise<void>((resolve) => {
        pollTimers[draftId] = window.setTimeout(async () => {
          delete pollTimers[draftId]
          await pollParseStatus(draftId)
          resolve()
        }, 1500)
      })
    } else {
      // terminal: clear any tracked timer
      if (pollTimers[draftId]) {
        window.clearTimeout(pollTimers[draftId])
        delete pollTimers[draftId]
      }
    }
  }

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
    for (const k of Object.keys(recheckTimers)) {
      window.clearTimeout(recheckTimers[k])
      delete recheckTimers[k]
    }
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
})

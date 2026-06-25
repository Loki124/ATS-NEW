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

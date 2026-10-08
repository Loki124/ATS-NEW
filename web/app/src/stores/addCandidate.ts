/**
 * AddCandidateModal V2 - Pinia Store
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { Ref } from 'vue'
import type {
  ParsedResume,
  DuplicateInfo,
  DupStatus,
  Direction,
  SubmitMode,
  ScoringStreamHandle,
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
  parseError?: string | null
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
  // 2026-10-08: 录入模式 — 'upload'(默认, 上传简历解析) | 'manual'(无文件手动填写)
  const entryMode = ref<'upload' | 'manual'>('upload')

  // poll attempts keyed by draft_id — 防止后端异常时前端无限轮询（兜底）
  const pollAttempts: Record<string, number> = {}
  // 2026-09-26: 解析轮询上限。1.5s 一次 × 120 = 180s，覆盖首次模型加载（YOLOv10+Qwen3 进程内加载）实际首跑约 60-90s；
  // 原 40(≈60s) 过短会导致后端已完成(如 84.9s)但前端已放弃轮询而误报"解析超时"。
  // 仍保留兜底：超过上限仍 processing 才停轮询并标记超时（多为 Celery worker 未运行等真实异常）。
  const POLL_MAX_ATTEMPTS = 120
  const POLL_INTERVAL_MS = 1500

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
    entryMode.value = 'upload'
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
        parseError: null,
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
    r.parseError = null
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
      // 解析成功 → 清除历史解析错误
      r.parseError = null
    } else if (update.status === 'failed') {
      // 2026-09-25: 解析任务真正失败 → 置为 clean 并标记面向用户的错误，
      // 避免此前「永远 processing」的卡死；用户可重新上传或手动补全信息。
      r.status = 'clean'
      r.parseError = '简历解析失败，请检查文件格式后重新上传，或手动补全候选人信息'
    } else {
      // 'processing'
      r.status = update.status
      // 重新进入处理中 → 清除历史解析错误
      r.parseError = null
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
// 评分 SSE 流句柄（submit 时打开，closeStream 时关闭）
let scoringStreamHandle: ScoringStreamHandle | null = null

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

  // 2026-10-08: 手动填写模式 — 无文件建草稿。复用整条 V2 管线（Step1 编辑/Step2 去向/bulk-create）。
  async function addManualResume(data: {
    name: string
    phone: string
    email: string
    gender?: string
    age?: number | null
    file_name?: string
  }) {
    const resp = await api.manualCreate(data)
    resumes.value.push({
      id: resp.draft_id,
      job_id: resp.job_id,
      file_name: data.file_name || '(手动录入)',
      status: resp.status,
      progress: 100,
      procPhase: null,
      parsed: resp.parsed,
      edited: {},
      duplicate: resp.duplicate,
      parseError: null,
    })
    isDirty.value = true
  }

  async function pollParseStatus(draftId: string, overrideJobId?: string) {
    const r = resumes.value.find((x) => x.id === draftId)
    if (!r) return
    const jobId = overrideJobId || r.job_id
    if (overrideJobId) {
      r.job_id = overrideJobId
      // 新 job → 重置轮询计数与超时错误，重新开始兜底计时
      pollAttempts[draftId] = 0
      r.parseError = null
    }
    if (pollAttempts[draftId] === undefined) pollAttempts[draftId] = 0

    const resp = await api.getParseStatus(jobId)
    processParseUpdate(draftId, {
      status: resp.status as 'processing' | 'done' | 'failed',
      phase: resp.phase,
      progress: resp.progress,
      parsed: resp.parsed ?? undefined,
      duplicate: resp.duplicate ?? undefined,
    })
    if (resp.status === 'processing') {
      pollAttempts[draftId] += 1
      // 兜底：超过最大轮询次数（约 180s）仍 processing，停止轮询并标记解析超时，
      // 避免后端异常（如 Celery worker 未运行）时前端无限轮询卡死。
      if (pollAttempts[draftId] >= POLL_MAX_ATTEMPTS) {
        if (pollTimers[draftId]) {
          window.clearTimeout(pollTimers[draftId])
          delete pollTimers[draftId]
        }
        // 兜底：超过约 180s 仍在 processing（多为后端 Celery worker 未运行等异常），
        // 停止轮询、标记超时错误并置为 clean，避免前端无限轮询 + 弹窗卡死。
        r.parseError = '简历解析超时，请确认解析服务已启动后重新上传简历'
        r.procPhase = null
        r.status = 'clean'
        return
      }
      // continue polling — store timer so closeStream() can cancel,
      // but wait for the next poll to finish before resolving so callers
      // can `await` until the draft reaches a terminal status.
      await new Promise<void>((resolve) => {
        pollTimers[draftId] = window.setTimeout(async () => {
          delete pollTimers[draftId]
          await pollParseStatus(draftId)
          resolve()
        }, POLL_INTERVAL_MS)
      })
    } else {
      // terminal: clear any tracked timer and reset attempt counter
      pollAttempts[draftId] = 0
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
    submitting.value = true
    step.value = 3
    if (submitMode.value === 'async') asyncResult.value = true

    const drafts = resumes.value.map((r) => {
      // 2026-10-08: 合并手动编辑覆盖解析值（修复「手动字段被自动清理」——提交时从未发送 edited）。
      // 无编辑时 merged === parsed（与旧行为一致）；手动模式下 parsed 即手动录入值。
      const merged = { ...(r.parsed || {}), ...(r.edited || {}) }
      return {
        draft_id: r.id,
        direction: (dirPer.value[r.id] || dirAll.value) as Direction,
        position_id: posPer.value[r.id] || posAll.value || null,
        channel: appInfo.value.channel,
        source: appInfo.value.source,
        provider: appInfo.value.provider,
        name: merged.name || '',
        phone: merged.phone || '',
        email: merged.email || '',
        parsed_data: merged,
      }
    })
    const result = await api.bulkCreate({ drafts, submit_mode: submitMode.value })

    // 2026-09-27: 接上评分 SSE 流（真正的半成品）。后端 bulk_create 已触发
    // score_batch_task 并返回 task_id；此处订阅进度回填 scoringProgress / allScoringDone。
    const taskId: string | undefined = result?.task_id
    const candIds: string[] = result?.created_candidate_ids || []
    if (taskId) {
      // created_candidate_ids 与 resumes 同序 → 下标对齐建 candidate_id ↔ draft_id 映射
      const candToDraft: Record<string, string> = {}
      resumes.value.forEach((r, i) => {
        if (candIds[i]) candToDraft[candIds[i]] = r.id
      })
      // 初始化每条简历的评分进度（overlay 用 r.id 作键）
      for (const r of resumes.value) {
        scoringProgress.value[r.id] = { status: 'waiting', progress: 0 }
      }
      scoringStreamHandle = api.openScoringStream(taskId, (event, data) => {
        if (event === 'scoring-done' || event === 'scoring-failed') {
          const draftId = (data?.candidate_id && candToDraft[data.candidate_id]) || data?.candidate_id || ''
          if (draftId) {
            scoringProgress.value[draftId] = {
              status: 'done',
              progress: 100,
              result:
                event === 'scoring-failed'
                  ? { score: 0, passed: false, dimensions: [] }
                  : {
                      score: data.score,
                      passed: data.passed,
                      dimensions: data.dimensions || [],
                    },
            }
          }
        } else if (event === 'task-complete') {
          allScoringDone.value = true
        } else if (event === 'stream-end' || event === 'error') {
          // 连接关闭/异常：兜底标记完成，避免浮层永久卡死（如 Celery/Redis 不可用）
          if (!allScoringDone.value) {
            for (const r of resumes.value) {
              const cur = scoringProgress.value[r.id]
              if (!cur || cur.status !== 'done') {
                scoringProgress.value[r.id] = {
                  status: 'done',
                  progress: 100,
                  result: { score: 0, passed: false, dimensions: [] },
                }
              }
            }
            allScoringDone.value = true
          }
        }
        scoringProgress.value = { ...scoringProgress.value }
      })
    } else {
      // 后端未返回 task_id（极端降级）→ 直接标记完成，避免卡死
      allScoringDone.value = true
    }

    return result
  }

  function closeStream() {
    for (const k of Object.keys(pollTimers)) {
      window.clearTimeout(pollTimers[k])
      delete pollTimers[k]
    }
    for (const k of Object.keys(pollAttempts)) {
      delete pollAttempts[k]
    }
    for (const k of Object.keys(recheckTimers)) {
      window.clearTimeout(recheckTimers[k])
      delete recheckTimers[k]
    }
    // 关闭评分 SSE 流（submit 时打开），避免连接泄漏
    if (scoringStreamHandle) {
      try { scoringStreamHandle.close() } catch { /* ignore */ }
      scoringStreamHandle = null
    }
  }

  // ===== Computed =====
  const mode = computed<'single' | 'batch'>(() => (resumes.value.length === 1 ? 'single' : 'batch'))
  const isAllDone = computed(() => resumes.value.every((r) => r.status !== 'processing'))
  const hasOccupied = computed(() => resumes.value.some((r) => r.status === 'occupied'))
  // 2026-06-29 花无缺: ScoringOverlay.vue 用 (i < store._overallStep) 驱动 4 个子步骤高亮.
  //   不在 store 里的私有状态, 用 allScoringDone + scoringProgress 推算:
  //   - allScoringDone=true → _overallStep=4 (全部 ok)
  //   - 否则看 scores: all 'done' → 3, all 'scoring' → 1, 混合 → 2
  //
  // 注意: 不是 computed 而是普通 ref, 这样测试可以 store._overallStep = 2 强制设值.
  //   生产代码不应该这么写, 但 _overallStep 已经被 UI 直接依赖,
  //   强 setter 比强制 computed 更直接 (computed 时测试需要绕过 TS readonly 检查).
  const _overallStep = ref(1)
  function recalcOverallStep() {
    if (allScoringDone.value) {
      _overallStep.value = 4
      return
    }
    const entries = Object.values(scoringProgress.value)
    if (entries.length === 0) {
      _overallStep.value = 1
      return
    }
    const doneCnt = entries.filter((e) => e.status === 'done').length
    const scoringCnt = entries.filter((e) => e.status === 'scoring').length
    if (doneCnt === entries.length) _overallStep.value = 3
    else if (scoringCnt === entries.length) _overallStep.value = 1
    else _overallStep.value = 2
  }
  // 任务进度更新后自动重算
  watch(() => [allScoringDone.value, scoringProgress.value], recalcOverallStep, { deep: true })

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
    step, isDirty, resumes, entryMode,
    applyMode, dirAll, posAll, dirPer, posPer,
    submitMode, submitting, appInfo,
    scoringProgress, allScoringDone, asyncResult, _overallStep,
    selectedIds, activeId, recheckingIds, replacingId,
    // actions
    reset, addResumes, updateField, replaceResumeFile, processParseUpdate,
    setOccupyAction, setDirAll, setPosAll, setPerDir, setPerPos, selectApplyPos,
    uploadFiles, addManualResume, pollParseStatus, triggerRecheck, submit, closeStream,
    // computed
    mode, isAllDone, hasOccupied, canGoStep2, canSubmit,
  }
})

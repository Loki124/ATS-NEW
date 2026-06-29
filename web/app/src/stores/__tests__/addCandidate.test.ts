import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAddCandidateStore } from '../addCandidate'
import type { ResumeDraft } from '../addCandidate'
// 2026-06-29 花无缺: ResumeDraft 定义在 stores/addCandidate (line 21), 不在 api.
//   旧代码 import from '@/api/addCandidate', TS2305 fail. 改成从 '../addCandidate' 直接 import.
import type { ParsedResume, DuplicateInfo } from '@/api/addCandidate'

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
      // status='done' + duplicate.status='clean' -> 业务 status 为 'clean'
      expect(r.status).toBe('clean')
      expect(r.progress).toBe(100)
      expect(r.parsed?.name).toBe('张三')
      expect(r.duplicate?.status).toBe('clean')
    })
  })

  describe('setOccupyAction', () => {
    it('changes status to clean when action=pending', () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      // 2026-06-29 花无缺: processParseUpdate 的 status 是任务级 (done|processing|failed),
      //   业务 status (clean|unocc|occupied) 通过 duplicate.status 传. 旧 test 用 'occupied'
      //   直接当 task status, TS2322 fail. 改成 task status='done' + duplicate.status='occupied'.
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
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
      // 2026-06-29 花无缺: 同上, 业务 status 走 duplicate.status, 不用 task status
      store.processParseUpdate('d2', { status: 'done', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
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
      // 2026-06-29: status 是 task-level, 业务走 duplicate.status
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'occupied' } as any })
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

  describe('uploadFiles', () => {
    it('calls api.uploadAndParse and adds resumes to store', async () => {
      const store = useAddCandidateStore()
      vi.mocked(api.uploadAndParse).mockResolvedValue({
        job_ids: ['j1', 'j2'],
        draft_ids: ['d1', 'd2'],
      })
      const files = [
        new File(['x'], 'a.pdf', { type: 'application/pdf' }),
        new File(['y'], 'b.pdf', { type: 'application/pdf' }),
      ]
      await store.uploadFiles(files)
      expect(api.uploadAndParse).toHaveBeenCalledWith(files)
      expect(store.resumes).toHaveLength(2)
      expect(store.resumes[0].id).toBe('d1')
      expect(store.resumes[0].file_name).toBe('a.pdf')
      expect(store.resumes[1].id).toBe('d2')
      expect(store.resumes[1].file_name).toBe('b.pdf')
    })
  })

  describe('pollParseStatus', () => {
    it('polls api.getParseStatus until status=done/failed, calling processParseUpdate', async () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      vi.mocked(api.getParseStatus)
        .mockResolvedValueOnce({
          draft_id: 'd1',
          status: 'processing',
          phase: 'parsing',
          progress: 30,
          parsed: null,
          duplicate: null,
          error: null,
        })
        .mockResolvedValueOnce({
          draft_id: 'd1',
          status: 'done',
          phase: null,
          progress: 100,
          parsed: { name: 'X' } as any,
          duplicate: { status: 'clean' } as any,
          error: null,
        })

      await store.pollParseStatus('d1')
      expect(api.getParseStatus).toHaveBeenCalledTimes(2)
      // status='done' + duplicate.status='clean' -> 业务 status 为 'clean'
      expect(store.resumes[0].status).toBe('clean')
      expect(store.resumes[0].parsed?.name).toBe('X')
      // cleanup any pending poll timers
      store.closeStream()
    })
  })

  describe('triggerRecheck', () => {
    it('debounces duplicate-check call after field edit', async () => {
      vi.useFakeTimers()
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', {
        status: 'done',
        phase: null,
        progress: 100,
        parsed: { phone: '13800138000' } as any,
        duplicate: { status: 'clean' } as any,
      })
      vi.mocked(api.postDuplicateCheck).mockResolvedValue({ status: 'clean' } as any)

      store.triggerRecheck('d1')
      expect(api.postDuplicateCheck).not.toHaveBeenCalled()
      // advance past the 800ms debounce; the setTimeout callback is async so we
      // must flush timers + microtasks to let the awaited api call resolve
      await vi.advanceTimersByTimeAsync(900)
      expect(api.postDuplicateCheck).toHaveBeenCalled()
      vi.useRealTimers()
    })
  })

  describe('submit', () => {
    it('calls api.bulkCreate, sets submitting=true and step=3', async () => {
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

    it('sets asyncResult=true when submitMode=async', async () => {
      const store = useAddCandidateStore()
      store.addResumes([{ job_id: 'j1', draft_id: 'd1', file_name: 'a.pdf' }])
      store.processParseUpdate('d1', { status: 'done', phase: null, progress: 100, duplicate: { status: 'clean' } as any })
      store.step = 2
      store.dirAll = 'pending'
      store.submitMode = 'async'
      vi.mocked(api.bulkCreate).mockResolvedValue({
        task_id: 't1',
        created_candidate_ids: ['c1'],
        route: { c1: 'pending' },
      })

      await store.submit()
      expect(store.asyncResult).toBe(true)
      expect(store.step).toBe(3)
    })
  })
})

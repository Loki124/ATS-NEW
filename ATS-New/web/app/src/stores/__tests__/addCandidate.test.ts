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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { uploadAndParse, getParseStatus, postDuplicateCheck, replaceFile, bulkCreate, startScoring, openScoringStream } from '../addCandidate'

// happy-dom 15.x 不暴露 EventSource 全局；注入一个最小 stub
// 让 `new EventSource(url)` 在测试环境可用，满足 `instanceof EventSource` 断言
if (typeof (globalThis as any).EventSource === 'undefined') {
  class EventSourceStub {
    url: string
    constructor(url: string) {
      this.url = url
    }
    close() {}
  }
  ;(globalThis as any).EventSource = EventSourceStub
}

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

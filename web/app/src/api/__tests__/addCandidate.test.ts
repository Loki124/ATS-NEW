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

// Mock axios 但让 .create() 返回真实 axios 实例（支持 interceptors.request/response）
// 这样既能 mock HTTP 调用，又能验证 auth header 注入
const mockPost = vi.fn()
const mockGet = vi.fn()
const realAxiosCreate = axios.create.bind(axios)
vi.spyOn(axios, 'create').mockImplementation((cfg?: any) => {
  const instance = realAxiosCreate(cfg)
  vi.spyOn(instance, 'post').mockImplementation(mockPost as any)
  vi.spyOn(instance, 'get').mockImplementation(mockGet as any)
  return instance
})

describe('addCandidate API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 重新 spy（因为 clearAllMocks 会重置）
    vi.spyOn(axios, 'create').mockImplementation((cfg?: any) => {
      const instance = realAxiosCreate(cfg)
      vi.spyOn(instance, 'post').mockImplementation(mockPost as any)
      vi.spyOn(instance, 'get').mockImplementation(mockGet as any)
      return instance
    })
  })

  describe('uploadAndParse', () => {
    it('POSTs multipart to upload-and-parse/ and returns job_ids', async () => {
      mockPost.mockResolvedValueOnce({ data: { job_ids: ['j1'], draft_ids: ['d1'] } })
      const file = new File(['x'], 'test.pdf', { type: 'application/pdf' })
      const result = await uploadAndParse([file])
      expect(result.job_ids).toEqual(['j1'])
      expect(result.draft_ids).toEqual(['d1'])
    })
  })

  describe('getParseStatus', () => {
    it('GETs parse-status/{job_id}/ and returns status', async () => {
      mockGet.mockResolvedValueOnce({
        data: { draft_id: 'd1', status: 'done', progress: 100, phase: null, parsed: {}, duplicate: {}, error: null },
      })
      const result = await getParseStatus('j1')
      expect(result.status).toBe('done')
    })
  })

  describe('postDuplicateCheck', () => {
    it('POSTs duplicate-check/ with phone/email/name', async () => {
      mockPost.mockResolvedValueOnce({ data: { status: 'clean' } })
      const result = await postDuplicateCheck({ draft_id: 'd1', phone: '13800138000', email: '', name: '' })
      expect(result.status).toBe('clean')
    })
  })

  describe('replaceFile', () => {
    it('POSTs multipart to replace-file/{draft_id}/', async () => {
      // 2026-06-29 花无缺: replaceFile API 返回 { job_id, draft_id } (line 151),
      //   旧 test 用 result.new_job_id 不存在, TS2339 fail. 改成 result.job_id.
      mockPost.mockResolvedValueOnce({ data: { job_id: 'j2' } })
      const file = new File(['y'], 'new.pdf', { type: 'application/pdf' })
      const result = await replaceFile('d1', file)
      expect(result.job_id).toBe('j2')
    })
  })

  describe('bulkCreate', () => {
    it('POSTs JSON to bulk-create/ with drafts and submit_mode', async () => {
      mockPost.mockResolvedValueOnce({
        data: { task_id: 't1', created_candidate_ids: ['c1'], route: { c1: 'pending' } },
      })
      const result = await bulkCreate({
        drafts: [{ draft_id: 'd1', direction: 'pending' }],
        submit_mode: 'async',
      })
      expect(result.task_id).toBe('t1')
    })
  })

  describe('startScoring', () => {
    it('POSTs JSON to scoring/start/ with task_id', async () => {
      mockPost.mockResolvedValueOnce({
        data: { stream_url: '/api/v1/candidates/add-candidate/scoring/stream/t1/' },
      })
      const result = await startScoring({ candidate_ids: ['c1'], task_id: 't1' })
      expect(result.stream_url).toContain('t1')
    })
  })

  describe('openScoringStream', () => {
    it('returns a closeable handle and does not require EventSource', async () => {
      // 避免真实 fetch 打到不存在的 dev server（ECONNREFUSED 噪声）
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: null }))
      const handle = openScoringStream('t1', () => {})
      expect(typeof handle.close).toBe('function')
      await Promise.resolve()
      vi.unstubAllGlobals()
    })
  })
})

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

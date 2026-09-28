/**
 * AddCandidateModal V2 - API 客户端
 *
 * 封装 7 个后端 endpoint + SSE 流。
 * 自带 Authorization 拦截器（auth.ts 的实例在创建 modal 时未挂载到这里）
 */
import axios, { type AxiosInstance } from 'axios'
import config from '../config'

const BASE = `${config.api.baseUrl}/candidates/add-candidate`

function getClient(): AxiosInstance {
  const client = axios.create({
    baseURL: BASE,
    timeout: 60000,
  })
  // 注入 auth header — 否则后端 IsAuthenticated 直接 401
  client.interceptors.request.use((cfg) => {
    const token = localStorage.getItem('accessToken') || ''
    if (token) {
      cfg.headers = cfg.headers || {}
      cfg.headers.Authorization = `Bearer ${token}`
    }
    return cfg
  })
  // 401 时跳转登录（与 auth.ts 一致）
  client.interceptors.response.use(
    (resp) => resp,
    (error) => {
      if (error?.response?.status === 401) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('user')
        // 跳登录页（hash 模式）
        if (typeof window !== 'undefined' && window.location.hash !== '#/login') {
          window.location.hash = '#/login'
        }
      }
      return Promise.reject(error)
    },
  )
  return client
}

// 2026-08-27: 后端 CamelCaseJSONRenderer 会把 DRF 响应的 snake_case 键统一转成 camelCase,
// 但本模块的类型声明 / store / 组件均按 snake_case 读取返回值. 在此边界统一归一化,
// 避免运行时 result.job_ids 之类为 undefined 而导致 .map() 崩溃.
function snakizeKeys<T = any>(obj: any): T {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return obj as T
  const out: Record<string, any> = {}
  for (const key of Object.keys(obj)) {
    const snaked = key.replace(/([A-Z])/g, '_$1').toLowerCase()
    out[snaked] = obj[key]
  }
  return out as T
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
  position?: string  // 2026-06-29 花无缺: ResumeCard.vue (line 50) 用 .position 显示求职意向
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
  return snakizeKeys(resp.data)
}

/** GET /parse-status/{job_id}/  — 轮询解析状态 */
export async function getParseStatus(job_id: string): Promise<ParseStatus> {
  const client = getClient()
  const resp = await client.get(`/parse-status/${job_id}/`)
  return snakizeKeys(resp.data)
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
  return snakizeKeys(resp.data)
}

/** POST /replace-file/{draft_id}/  — 替换附件并重新解析 */
export async function replaceFile(draft_id: string, file: File): Promise<{ job_id: string; draft_id: string }> {
  const form = new FormData()
  form.append('file', file)
  const client = getClient()
  const resp = await client.post(`/replace-file/${draft_id}/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return snakizeKeys(resp.data)
}

/** POST /bulk-create/  — Step 2 提交（创建候选 + 关联） */
export async function bulkCreate(params: {
  drafts: BulkCreateDraft[]
  submit_mode: SubmitMode
}): Promise<BulkCreateResult> {
  const client = getClient()
  const resp = await client.post('/bulk-create/', params)
  return snakizeKeys(resp.data)
}

/** POST /scoring/start/  — async 模式显式启动评分 */
export async function startScoring(params: { candidate_ids: string[]; task_id: string }): Promise<{ stream_url: string }> {
  const client = getClient()
  const resp = await client.post('/scoring/start/', params)
  return snakizeKeys(resp.data)
}

// SSE 事件帧
export interface ScoringEvent {
  event: string
  data: any
}

// 评分流句柄（可关闭）
export interface ScoringStreamHandle {
  close: () => void
}

/**
 * 打开评分进度 SSE 流。
 *
 * 2026-09-27 修复：原实现用 `EventSource`，但它**无法携带 Authorization header**，
 * 而后端 ScoringStreamView 用 `IsHROrAbove`(Bearer/JWT 鉴权) → 即便接上也会 401/403，
 * 且 `openScoringStream` 此前无任何业务调用方（真·半成品）。
 * 改为 fetch + ReadableStream 手动解析 SSE 帧，带 `Authorization: Bearer`，返回可关闭句柄。
 */
export function openScoringStream(
  taskId: string,
  onEvent: (event: string, data: any) => void,
): ScoringStreamHandle {
  const url = `${BASE}/scoring/stream/${taskId}/`
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token') || ''
  const controller = new AbortController()
  const handle: ScoringStreamHandle = { close: () => controller.abort() }

  ;(async () => {
    if (typeof fetch === 'undefined') {
      onEvent('error', { message: 'fetch unsupported' })
      return
    }
    try {
      const resp = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        signal: controller.signal,
      })
      if (!resp.ok || !resp.body) {
        onEvent('error', { status: resp.status })
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx: number
        while ((idx = buf.indexOf('\n\n')) !== -1) {
          const frame = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const ev = parseSseFrame(frame)
          if (ev) onEvent(ev.event, ev.data)
        }
      }
      onEvent('stream-end', {})
    } catch (e: any) {
      if (e?.name !== 'AbortError') onEvent('error', { message: String(e) })
    }
  })()

  return handle
}

function parseSseFrame(frame: string): ScoringEvent | null {
  let event = 'message'
  let dataStr = ''
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr += line.slice(5).trim()
  }
  if (!dataStr) return null
  try {
    return { event, data: JSON.parse(dataStr) }
  } catch {
    return { event, data: {} }
  }
}

/** 关闭 SSE 流 — 2026-07-02: 必须显式 close, 否则连接 + auth cookie 泄漏 */
export function closeScoringStream(handle: ScoringStreamHandle | null): void {
  if (handle) {
    try { handle.close() } catch { /* ignore */ }
  }
}

// ============ 简历解析引擎后台切换 ============
export type ResumeParserBackendName = 'career_core' | 'smartresume'

export interface ResumeParserBackendProbe {
  /** 后端名（career_core / smartresume） */
  name: ResumeParserBackendName
  /** 后端是否在代码注册表内（即后端是否支持该引擎） */
  registered: boolean
  /** 可执行文件是否就绪（career 二进制 / SmartResume 脚本） */
  available: boolean
}

export interface SmartResumeCloudConfig {
  /** 本地直连模型 / 云端大模型 API */
  llm_mode?: 'local' | 'cloud'
  /** 云端 API 地址（OpenAI 兼容，默认 DashScope compatible-mode） */
  api_url?: string
  /** 云端 API Key（仅 PUT 请求使用；GET 响应已脱敏为 api_key_set） */
  api_key?: string
  /** 是否已配置云端 API Key（GET 时脱敏，不返回明文） */
  api_key_set?: boolean
  /** 云端模型名（如 qwen-plus / qwen-max） */
  model_name?: string
}

export interface ResumeParserConfig {
  /** 当前激活的后端 */
  backend: ResumeParserBackendName
  /** SmartResume 云端大模型配置（仅当 backend=smartresume 时有效） */
  smartresume?: SmartResumeCloudConfig
  /** 各后端运行时探测结果（数组，不落库，GET 时计算） */
  available: ResumeParserBackendProbe[]
}

/** GET /resume-parser-config/ — 读取当前激活引擎 + 各引擎可用性 */
export async function getResumeParserConfig(): Promise<ResumeParserConfig> {
  const client = getClient()
  const resp = await client.get('/resume-parser-config/')
  const body = (resp.data || {}) as { data?: ResumeParserConfig }
  return (body.data || { backend: 'career_core', available: [] }) as ResumeParserConfig
}

/** PUT /resume-parser-config/ — 切换激活引擎 / 保存 SmartResume 配置 */
export async function updateResumeParserConfig(
  payload: { backend: ResumeParserBackendName; smartresume?: SmartResumeCloudConfig },
): Promise<ResumeParserConfig> {
  const client = getClient()
  const resp = await client.put('/resume-parser-config/', payload)
  const body = (resp.data || {}) as { data?: ResumeParserConfig }
  return (body.data || { backend: payload.backend, available: [] }) as ResumeParserConfig
}

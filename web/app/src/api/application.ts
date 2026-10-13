import type { ApiEnvelope } from '../utils/envelope'
import { api } from '../utils/request'

// 申请（候选人↔流程↔阶段）列表 API
// 后端端点：GET /api/v1/applications/
// 关键查询参数：process(流程id) / stage(当前阶段 RecruitmentStage id) / candidate / position / state / keyword
// 用于前端"流程-阶段"管道视图：按流程+阶段聚合候选人数量，以及点击阶段卡片后取候选人 id 白名单。

export interface ApplicationListItem {
  id: string
  code?: string
  // list 视图下 candidate 为 PK(string)；detail 视图下为嵌套对象 {id,...}。统一用 extractCandidateId 抽取。
  candidate: string | { id: string; [k: string]: any } | null
  candidateName?: string
  process?: string
  currentStage?: string
  [k: string]: any
}

export interface ApplicationListResult {
  data: ApplicationListItem[]
  pagination: { total: number; page: number; pageSize: number }
}

/**
 * 从 application.candidate 抽取候选人 id（兼容 PK 字符串与嵌套对象两种形态）。
 */
export function extractCandidateId(candidate: ApplicationListItem['candidate']): string | null {
  if (!candidate) return null
  if (typeof candidate === 'string') return candidate
  return candidate.id ?? null
}

/**
 * 申请列表（支持 process + stage 过滤）。
 * 兼容两种后端信封：
 *   - 自定义分页：{ data: [...], pagination: { total } }
 *   - DRF 默认分页：{ count, results: [...] }
 *   - 裸数组兜底
 */
export async function listApplications(params: {
  processId?: string
  stageId?: string
  candidateId?: string
  positionId?: string
  state?: string
  keyword?: string
  page?: number
  pageSize?: number
} = {}): Promise<ApplicationListResult> {
  const query: Record<string, any> = {}
  if (params.processId) query.process = params.processId
  if (params.stageId) query.stage = params.stageId
  if (params.candidateId) query.candidate = params.candidateId
  if (params.positionId) query.position = params.positionId
  if (params.state) query.state = params.state
  if (params.keyword) query.keyword = params.keyword
  if (params.page != null) query.page = params.page
  if (params.pageSize != null) query.pageSize = params.pageSize

  const resp = await api.get('/applications/', { params: query })
  const body = (resp as any)?.data ?? resp
  let data: ApplicationListItem[] = []
  let total = 0
  if (Array.isArray(body)) {
    data = body
    total = body.length
  } else if (Array.isArray(body?.data)) {
    data = body.data
    total = body?.pagination?.total ?? body?.count ?? data.length
  } else if (Array.isArray(body?.results)) {
    data = body.results
    total = body?.count ?? data.length
  }
  return {
    data,
    pagination: {
      total,
      page: params.page ?? 1,
      pageSize: params.pageSize ?? data.length,
    },
  }
}

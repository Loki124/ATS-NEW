/**
 * 候选人 API (PRD G9 批量操作 / G10 阶段进入 / G13 批量筛选)
 */
import { api } from '../utils/request'

export interface Candidate {
  id: string
  name: string
  gender?: string
  age?: number
  phone?: string
  email?: string
  highestEducation?: string
  firstEducation?: string
  currentCompany?: string
  currentPosition?: string
  workYears?: number
  source?: string
  candidateStatus?: string
  archiveReason?: string
  createdAt: string
  updatedAt: string
}

// 列表
/**
 * 候选人列表。
 * ids: 逗号分隔的 ID 白名单 —— 供指标库「按规则筛选」结果集回传
 *      （规则含派生指标无法 SQL 化，先由 metrics 算得 passedIds 再收敛结果集）。
 */
export async function listCandidates(params: {
  page?: number
  pageSize?: number
  candidateStatus?: string
  keyword?: string
  ids?: string
} = {}) {
  const { data } = await api.get('/candidates/', { params })
  return data
}

// 详情
export async function getCandidate(id: string) {
  const { data } = await api.get(`/candidates/${id}/`)
  // 裸容错: 后端信封化后 data={success,data:payload}; 过渡期裸返回则回落 data 本身
  return data?.data ?? data
}

// 局部更新候选人 (PATCH /candidates/<id>/, 用于编辑简历中映射到模型列的字段)
export async function updateCandidate(id: string, payload: Record<string, any>) {
  const { data } = await api.patch(`/candidates/${id}/`, payload)
  // 裸容错: 同 getCandidate, 兼容后端裸返回与信封
  return data?.data ?? data
}

// G9 批量推荐
export async function batchRecommend(payload: { candidateIds: string[]; positionId: string; comment?: string }) {
  const { data } = await api.post('/candidates/batch/recommend/', payload)
  return data
}

// G9 批量归档
export async function batchArchive(payload: { candidateIds: string[]; reason?: string }) {
  const { data } = await api.post('/candidates/batch/archive/', payload)
  return data
}

// G9 批量分配
export async function batchAssign(payload: { candidateIds: string[]; recruiterId: string }) {
  const { data } = await api.post('/candidates/batch/assign/', payload)
  return data
}

// G9 批量导出
export async function batchExport(payload: { candidateIds?: string[]; filter?: any } = {}) {
  const { data } = await api.post('/candidates/batch/export/', payload, { responseType: 'blob' })
  return data
}

// G13 批量筛选
export async function batchScreen(payload: { candidateIds: string[]; result: 'PASS' | 'FAIL'; comment?: string }) {
  const { data } = await api.post('/candidates/batch/screen/', payload)
  return data
}

// G11 倒序推荐
export async function recommendReverse(payload: { positionId: string; candidateIds?: string[] }) {
  const { data } = await api.post('/candidates/recommend-reverse/', payload)
  return data
}

// G11 倒序推荐 (按 lastActiveAt + score 综合分)
export interface RecommendationParams {
  positionId?: string
  keyword?: string
  sortBy?: 'score' | 'lastActiveAt' | 'composite'
  limit?: number
}
export async function fetchRecommendations(params: RecommendationParams = {}) {
  const { data } = await api.get('/candidates/recommendations/', { params })
  return data
}

// G44 候选人 11 状态详细字段
export type StatusValue = 'PENDING' | 'PASS' | 'FAIL'
export interface CandidateStatusDetail {
  evaluated?: StatusValue
  hrbpFiltered?: StatusValue
  managerFiltered?: StatusValue
  seniorManagerFiltered?: StatusValue
  invited?: StatusValue
  jointInterview?: StatusValue
  comprehensiveInterview?: StatusValue
  offerNegotiation?: StatusValue
  backgroundCheck?: StatusValue
  pendingOnboarding?: StatusValue
  onboarded?: StatusValue
  [key: string]: StatusValue | undefined
}
export interface StatusSchemaItem {
  order: number
  label: string
  terminal: boolean
}
export type StatusSchema = Record<string, StatusSchemaItem>

export async function fetchStatusSchema(): Promise<StatusSchema> {
  const { data } = await api.get('/candidates/status-details/schema/')
  return data.data
}

export async function updateCandidateStatusDetail(id: string, key: string, value: StatusValue) {
  const { data } = await api.put(`/candidates/${id}/status-details/`, { key, value })
  return data
}

export default api

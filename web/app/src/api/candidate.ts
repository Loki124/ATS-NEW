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

// 操作历史（时间倒序；支持 action / date_from / date_to 筛选，分页）
export async function getCandidateHistories(
  id: string,
  params: { page?: number; pageSize?: number; action?: string; date_from?: string; date_to?: string } = {},
) {
  const { data } = await api.get(`/candidates/${id}/histories/`, { params })
  return data?.data ?? data
}

// 操作历史哈希链完整性校验（不可篡改检测）
export async function verifyCandidateHistories(id: string) {
  const { data } = await api.get(`/candidates/${id}/histories/verify/`)
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

// ============================================================
// 候选人详情页操作：淘汰 / 放入人才库 / 推荐其他职位 / 关注 / 转发
//
// 端点契约见 apps/candidate/views.py：
//   POST /candidates/<id>/transition/          状态机（淘汰 mark_process_failed、
//                                              入库 move_to_talent_pool）
//   POST /candidates/batch/recommend/           推荐到其他职位
//   GET|POST|DELETE /candidates/<id>/follow/    个人级关注
//   GET|POST /candidates/<id>/forward/         转发给内部同事
// ============================================================

/** FSM 动作名 → i18n 文案由页面负责，这里只透传后端枚举 */
export type CandidateTransitionAction =
  | 'enter_process'
  | 'send_offer'
  | 'mark_onboarded'
  | 'withdraw'
  | 'move_to_talent_pool'
  | 'mark_process_failed'
  | 'pause_process'
  | 'resume_process'

/**
 * 候选人状态机流转（淘汰 / 放入人才库 均走此端点）。
 * 后端按 FSM action 分派动作粒度权限：
 *   mark_process_failed → 'eliminate'、move_to_talent_pool → 'talent_pool_add'
 * 并强制「仅锁定人可操作」（ensure_operable），非锁定人会收到 FORBIDDEN_SCOPE。
 */
export async function transitionCandidate(
  id: string,
  action: CandidateTransitionAction,
  extra: Record<string, any> = {},
) {
  const { data } = await api.post(`/candidates/${id}/transition/`, { action, ...extra })
  return data?.data ?? data
}

/** 推荐到其他职位（单人在详情页复用批量端点，传单元素数组） */
export async function recommendCandidateToPosition(
  candidateId: string,
  positionId: string,
  comment?: string,
) {
  const { data } = await api.post('/candidates/batch/recommend/', {
    candidateIds: [candidateId],
    positionId,
    comment,
  })
  // 批量端点逐条返回成败，前端据 results[0] 判定，不靠 HTTP 200 假成功
  const results = data?.data?.results ?? []
  const first = results[0]
  if (!first || first.success !== true) {
    const err: any = new Error(first?.error || 'RECOMMEND_FAILED')
    err.code = first?.error || 'RECOMMEND_FAILED'
    throw err
  }
  return first
}

// ---------- 关注（个人级） ----------

/** 查询当前登录用户是否关注该候选人（详情页按钮态回显） */
export async function getCandidateFollowState(id: string): Promise<boolean> {
  const { data } = await api.get(`/candidates/${id}/follow/`)
  return data?.data?.isFollowed ?? false
}

/** 关注候选人（幂等，复合唯一约束保证重复调用安全） */
export async function followCandidate(id: string) {
  const { data } = await api.post(`/candidates/${id}/follow/`)
  return data?.data ?? data
}

/** 取消关注 */
export async function unfollowCandidate(id: string) {
  const { data } = await api.delete(`/candidates/${id}/follow/`)
  return data?.data ?? data
}

// ---------- 转发给内部同事 ----------

export interface ForwardRow {
  id: string
  fromUserId: string
  fromUserName: string
  toUserId: string
  toUserName: string
  note: string
  createdAt?: string
}

/** 该候选人的转发记录（谁转给了谁） */
export async function listCandidateForwards(id: string): Promise<ForwardRow[]> {
  const { data } = await api.get(`/candidates/${id}/forward/`)
  return data?.data?.results ?? []
}

/**
 * 转发候选人给一位或多位内部同事。
 * 逐条返回成败（USER_NOT_FOUND / FORBIDDEN_SCOPE / FORBIDDEN_SELF），
 * 部分失败不静默吞掉，交由前端提示。
 */
export async function forwardCandidate(id: string, toUserIds: string[], note?: string) {
  const { data } = await api.post(`/candidates/${id}/forward/`, {
    toUserIds,
    note,
  })
  return data?.data ?? data
}

export default api

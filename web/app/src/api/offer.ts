/**
 * Offer API 客户端 — 与后端真实契约对齐 (2026-10-14)
 *
 * ⚠️ 本文件此前是「假契约」，与后端完全对不上，导致 Offer 页表格全空 + 操作必 400。
 *    本次按后端实际实现重写。对齐依据（apps/offer/models.py + serializers.py + views.py）：
 *
 *   1. 状态字段是 `state`（不是 offerStatus），另有 `stateDisplay` 中文名。
 *      OfferState 共 11 态：DRAFT / PENDING_APPROVAL / REJECTED / PENDING_SEND / SENT /
 *                           NEGOTIATING / ACCEPTED / REJECTED_BY_CANDIDATE / WITHDRAWN /
 *                           PENDING_ONBOARDING / ONBOARDED
 *      ⚠️ 后端**没有** APPROVED：审批通过后进入 PENDING_SEND（待发出）。
 *      此前前端发 to:'APPROVED' 必然 400。
 *
 *   2. 流转 POST `offers/{id}/transition/`，入参是 `{action, reason}`（**不是** `{to, reason}`），
 *      action 取值 8 个：submit_approval / approve / reject / send / accept /
 *                       negotiate / candidate_reject / onboarded
 *
 *   3. 列表 GET `offers/` 支持 filterset：state / candidate / position / level
 *      → 按候选人查 Offer 用 `candidate`，这是并入候选人详情页的基础。
 *
 *   4. OfferListSerializer 真实字段（camelCase 渲染）：
 *      id, code, applicationId, candidateId, candidateName, positionId, positionTitle,
 *      salary, salaryCurrency, level, startDate, expireDate, state, stateDisplay,
 *      sentAt, respondedAt, createdAt
 *      此前前端用的 jobTitle/jobLevel/offerStatus/expectedJoinDate/baseSalaryTrial/
 *      baseSalaryFormal/demandId **后端一个都不返回** → 已移除并换成本表字段。
 *
 *   5. 后端 offer router **只有** offer-list / offer-detail / offer-transition。
 *      此前前端调用的 /offer-templates/、render-from-offer/、status-history/、
 *      background-checks/（背调）**后端无对应路由** → 相关函数与常量已删除。
 *      需要模板生成/背调时应先补后端接口，本次范围不含。
 */
import { api } from '../utils/request'

export type TagType = 'default' | 'primary' | 'success' | 'info' | 'warning' | 'error'

/** 后端 OfferState 全量 11 态（顺序与 models.OfferState 一致） */
export const OFFER_STATE = {
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  REJECTED: 'REJECTED',
  PENDING_SEND: 'PENDING_SEND',
  SENT: 'SENT',
  NEGOTIATING: 'NEGOTIATING',
  ACCEPTED: 'ACCEPTED',
  REJECTED_BY_CANDIDATE: 'REJECTED_BY_CANDIDATE',
  WITHDRAWN: 'WITHDRAWN',
  PENDING_ONBOARDING: 'PENDING_ONBOARDING',
  ONBOARDED: 'ONBOARDED',
} as const

export type OfferStateValue = (typeof OFFER_STATE)[keyof typeof OFFER_STATE]

/** 状态中文名（对齐后端 TextChoices 的 .label；优先用后端返回的 stateDisplay） */
export const OFFER_STATE_LABEL: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_APPROVAL: '待审批',
  REJECTED: '已驳回',
  PENDING_SEND: '待发出',
  SENT: '已发出',
  NEGOTIATING: '谈判中',
  ACCEPTED: '已接受',
  REJECTED_BY_CANDIDATE: '候选人已拒绝',
  WITHDRAWN: '已撤回',
  PENDING_ONBOARDING: '待入职',
  ONBOARDED: '已入职',
}

export const OFFER_STATE_COLOR: Record<string, TagType> = {
  DRAFT: 'default',
  PENDING_APPROVAL: 'warning',
  REJECTED: 'error',
  PENDING_SEND: 'info',
  SENT: 'primary',
  NEGOTIATING: 'warning',
  ACCEPTED: 'success',
  REJECTED_BY_CANDIDATE: 'error',
  WITHDRAWN: 'default',
  PENDING_ONBOARDING: 'info',
  ONBOARDED: 'success',
}

/** 可执行流转动作（后端 OfferTransitionSerializer.ACTION_CHOICES） */
export const OFFER_ACTION = {
  SUBMIT_APPROVAL: 'submit_approval',
  APPROVE: 'approve',
  REJECT: 'reject',
  SEND: 'send',
  ACCEPT: 'accept',
  NEGOTIATE: 'negotiate',
  CANDIDATE_REJECT: 'candidate_reject',
  ONBOARDED: 'onboarded',
} as const

export type OfferActionValue = (typeof OFFER_ACTION)[keyof typeof OFFER_ACTION]

export const OFFER_ACTION_LABEL: Record<string, string> = {
  submit_approval: '提交审批',
  approve: '审批通过',
  reject: '驳回',
  send: '发送',
  accept: '候选人接受',
  negotiate: '进入谈判',
  candidate_reject: '候选人拒绝',
  onboarded: '确认入职',
}

/** 危险动作：需要填写原因并二次确认 */
const DANGEROUS_ACTIONS = new Set<string>([OFFER_ACTION.REJECT, OFFER_ACTION.CANDIDATE_REJECT])

/**
 * 各状态下允许的动作 —— 严格对齐后端 models.Offer 的 @transition source。
 *
 * ⚠️ 真实性说明（勿臆造动作）：后端仅存在 9 个 @transition，其中
 *    `set_onboarding_date`(ACCEPTED→PENDING_ONBOARDING) 需要 date 入参，
 *    且**未**列入 OfferTransitionSerializer.ACTION_CHOICES，故无法经 HTTP 触发。
 *    因此 ACCEPTED / NEGOTIATING / REJECTED / REJECTED_BY_CANDIDATE / WITHDRAWN
 *    在当前后端下确无可执行动作（终态），此处如实留空，不做假动作。
 */
export const OFFER_STATE_ACTIONS: Record<string, string[]> = {
  [OFFER_STATE.DRAFT]: [OFFER_ACTION.SUBMIT_APPROVAL],
  [OFFER_STATE.PENDING_APPROVAL]: [OFFER_ACTION.APPROVE, OFFER_ACTION.REJECT],
  [OFFER_STATE.PENDING_SEND]: [OFFER_ACTION.SEND],
  [OFFER_STATE.SENT]: [OFFER_ACTION.ACCEPT, OFFER_ACTION.NEGOTIATE, OFFER_ACTION.CANDIDATE_REJECT],
  [OFFER_STATE.NEGOTIATING]: [],
  [OFFER_STATE.ACCEPTED]: [],
  [OFFER_STATE.PENDING_ONBOARDING]: [OFFER_ACTION.ONBOARDED],
  [OFFER_STATE.ONBOARDED]: [],
  [OFFER_STATE.REJECTED]: [],
  [OFFER_STATE.REJECTED_BY_CANDIDATE]: [],
  [OFFER_STATE.WITHDRAWN]: [],
}

/** 展示用状态名：优先后端 stateDisplay → 本地枚举 → 原值 → '—' */
export function offerStateLabel(offer: { state?: string; stateDisplay?: string }): string {
  return offer.stateDisplay || OFFER_STATE_LABEL[offer.state || ''] || offer.state || '—'
}

/** 状态标签配色 */
export function offerStateColor(state?: string): TagType {
  return (state && OFFER_STATE_COLOR[state]) || 'default'
}

/** 该状态下可执行的动作 */
export function offerActionsFor(state?: string): string[] {
  if (!state) return []
  return OFFER_STATE_ACTIONS[state] || []
}

/** 该动作是否必须填原因（危险动作） */
export function isDangerousAction(action: string): boolean {
  return DANGEROUS_ACTIONS.has(action)
}

/** 字段严格对齐后端 OfferListSerializer（camelCase 渲染器输出） */
export interface Offer {
  id: string
  code: string
  applicationId: string
  candidateId: string
  candidateName: string
  positionId: string
  positionTitle: string
  /** 薪资（后端 DecimalField，序列化为字符串） */
  salary?: string | number | null
  salaryCurrency: string
  /** 职级（后端 level） */
  level: string
  /** 预计入职日期（后端 start_date） */
  startDate?: string | null
  expireDate?: string | null
  /** 后端 FSM 状态（不是 offerStatus） */
  state: string
  stateDisplay?: string
  sentAt?: string | null
  respondedAt?: string | null
  createdAt: string
}

/** 列表查询（后端 filterset_fields: state / candidate / position / level） */
export async function listOffers(params: {
  page?: number
  pageSize?: number
  state?: string
  candidate?: string
  position?: string
  level?: string
} = {}) {
  const { data } = await api.get('/offers/', { params })
  return data?.data ?? data
}

/** 按候选人查其 Offer（候选人详情页 Offer 页签用） */
export async function listOffersByCandidate(candidateId: string, params: { page?: number; pageSize?: number } = {}) {
  return listOffers({ ...params, candidate: candidateId })
}

export async function getOffer(id: string) {
  const { data } = await api.get(`/offers/${id}/`)
  return data?.data ?? data
}

/**
 * 状态流转。
 * ⚠️ 入参必须是 `{action, reason}`（后端 OfferTransitionSerializer.action），
 *    action 取 OFFER_ACTION 常量值（如 'approve'，不是 'APPROVED'）。
 */
export async function transitionOffer(id: string, action: string, reason?: string) {
  const { data } = await api.post(`/offers/${id}/transition/`, { action, reason: reason || '' })
  return data?.data ?? data
}

export default api
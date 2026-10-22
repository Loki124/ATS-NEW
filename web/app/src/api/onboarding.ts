/**
 * Onboarding API 客户端 — 与后端真实契约对齐 (2026-10-21)
 *
 * ⚠️ 本文件此前是「假契约」：状态 8 态（NOT_STARTED…）、字段 jobTitle / expectedJoinDate /
 *    onboardingStatus / onboardedAt 后端一个都不返回，transition 发 `{to, reason}` 必 400。
 *    本次按后端真实实现重写。对齐依据（apps/onboarding/models.py + serializers.py + views.py）：
 *
 *   1. 状态字段是 `state`（+ stateDisplay 中文名）。OnboardingState 共 7 态：
 *      PENDING 待入职 / PREPARING 入职准备中 / DELAYED 已延期 / COMPLETED 已完成 /
 *      PROBATION 试用中 / REGULARIZED 已转正 / RESIGNED_DURING_PROBATION 试用期离职
 *
 *   2. 流转 POST `onboardings/{id}/transition/`，入参是 `{action, new_date?, result?}`
 *      （**不是** `{to, reason}`）。action 取值 6 个：start_preparing / complete /
 *      delay / resume / enter_probation / regularize。其中 delay 必须带 new_date，
 *      regularize 可带 result（默认 PASS）。
 *
 *   3. 列表 GET `onboardings/` 支持 filterset：state / candidate / position
 *      → 按候选人查入职用 `candidate`，这是并入候选人详情页的基础。
 *
 *   4. 真实字段（CamelCase 渲染）：id, offer, candidate, candidateName, position,
 *      positionTitle, startDate, actualStartDate, probationEndDate, state,
 *      stateDisplay, regularizationResult, regularizationAt, createdAt；
 *      Detail 视图另含 todoList / todoCompleted / updatedAt。
 */
import { api } from '../utils/request'

export type TagType = 'default' | 'primary' | 'success' | 'info' | 'warning' | 'error'

/** 后端 OnboardingState 全量 7 态（顺序与 models.OnboardingState 一致） */
export const ONBOARDING_STATE = {
  PENDING: 'PENDING',
  PREPARING: 'PREPARING',
  DELAYED: 'DELAYED',
  COMPLETED: 'COMPLETED',
  PROBATION: 'PROBATION',
  REGULARIZED: 'REGULARIZED',
  RESIGNED_DURING_PROBATION: 'RESIGNED_DURING_PROBATION',
} as const

export type OnboardingStateValue = (typeof ONBOARDING_STATE)[keyof typeof ONBOARDING_STATE]

/** 状态中文名（对齐后端 TextChoices 的 .label；优先用后端返回的 stateDisplay） */
export const ONBOARDING_STATE_LABEL: Record<string, string> = {
  PENDING: '待入职',
  PREPARING: '入职准备中',
  DELAYED: '已延期',
  COMPLETED: '已完成',
  PROBATION: '试用中',
  REGULARIZED: '已转正',
  RESIGNED_DURING_PROBATION: '试用期离职',
}

export const ONBOARDING_STATE_COLOR: Record<string, TagType> = {
  PENDING: 'primary',
  PREPARING: 'warning',
  DELAYED: 'error',
  COMPLETED: 'info',
  PROBATION: 'warning',
  REGULARIZED: 'success',
  RESIGNED_DURING_PROBATION: 'default',
}

/** 可执行流转动作（后端 OnboardingTransitionSerializer.ACTION_CHOICES） */
export const ONBOARDING_ACTION = {
  START_PREPARING: 'start_preparing',
  COMPLETE: 'complete',
  DELAY: 'delay',
  RESUME: 'resume',
  ENTER_PROBATION: 'enter_probation',
  REGULARIZE: 'regularize',
} as const

export type OnboardingActionValue = (typeof ONBOARDING_ACTION)[keyof typeof ONBOARDING_ACTION]

export const ONBOARDING_ACTION_LABEL: Record<string, string> = {
  start_preparing: '开始准备',
  complete: '完成准备',
  delay: '延期',
  resume: '恢复准备',
  enter_probation: '进入试用期',
  regularize: '转正',
}

/**
 * 各状态下允许的动作 —— 严格对齐后端 models.Onboarding 的 @transition source。
 *
 *  - start_preparing: PENDING → PREPARING
 *  - complete:        PREPARING → COMPLETED
 *  - delay:           PREPARING → DELAYED / DELAYED → DELAYED（需 new_date）
 *  - resume:          DELAYED → PREPARING
 *  - enter_probation: COMPLETED → PROBATION
 *  - regularize:      PROBATION → REGULARIZED（可带 result，默认 PASS）
 *
 * REGULARIZED / RESIGNED_DURING_PROBATION 为终态，确无可执行动作，如实留空。
 */
export const ONBOARDING_STATE_ACTIONS: Record<string, string[]> = {
  [ONBOARDING_STATE.PENDING]: [ONBOARDING_ACTION.START_PREPARING],
  [ONBOARDING_STATE.PREPARING]: [ONBOARDING_ACTION.COMPLETE, ONBOARDING_ACTION.DELAY],
  [ONBOARDING_STATE.DELAYED]: [ONBOARDING_ACTION.DELAY, ONBOARDING_ACTION.RESUME],
  [ONBOARDING_STATE.COMPLETED]: [ONBOARDING_ACTION.ENTER_PROBATION],
  [ONBOARDING_STATE.PROBATION]: [ONBOARDING_ACTION.REGULARIZE],
  [ONBOARDING_STATE.REGULARIZED]: [],
  [ONBOARDING_STATE.RESIGNED_DURING_PROBATION]: [],
}

/** 展示用状态名：优先后端 stateDisplay → 本地枚举 → 原值 → '—' */
export function onboardingStateLabel(o: { state?: string; stateDisplay?: string }): string {
  return o.stateDisplay || ONBOARDING_STATE_LABEL[o.state || ''] || o.state || '—'
}

/** 状态标签配色 */
export function onboardingStateColor(state?: string): TagType {
  return (state && ONBOARDING_STATE_COLOR[state]) || 'default'
}

/** 该状态下可执行的动作 */
export function onboardingActionsFor(state?: string): string[] {
  if (!state) return []
  return ONBOARDING_STATE_ACTIONS[state] || []
}

/** 该动作是否需要额外参数（日期 / 结果） */
export function isParamAction(action: string): boolean {
  return action === ONBOARDING_ACTION.DELAY || action === ONBOARDING_ACTION.REGULARIZE
}

/** 字段严格对齐后端 OnboardingListSerializer / DetailSerializer（CamelCase 渲染器输出） */
export interface Onboarding {
  id: string
  offer?: string
  candidate?: string
  candidateName?: string
  position?: string
  positionTitle?: string
  /** 入职日期（后端 start_date，DateField） */
  startDate?: string | null
  /** 实际入职日期（后端 actual_start_date） */
  actualStartDate?: string | null
  /** 试用期结束日期（后端 probation_end_date） */
  probationEndDate?: string | null
  /** 后端 FSM 状态（不是 onboardingStatus） */
  state: string
  stateDisplay?: string
  /** 转正结果（后端 regularization_result） */
  regularizationResult?: string
  /** 转正时间（后端 regularization_at） */
  regularizationAt?: string | null
  createdAt: string
  /** 入职待办清单（Detail 视图；数组，元素可为字符串或 {text,done}） */
  todoList?: Array<string | { text: string; done?: boolean }>
  todoCompleted?: Record<string, boolean>
  updatedAt?: string
}

/** 列表查询（后端 filterset_fields: state / candidate / position） */
export async function listOnboardings(params: {
  page?: number
  pageSize?: number
  state?: string
  candidate?: string
  position?: string
} = {}) {
  const { data } = await api.get('/onboardings/', { params })
  return data?.data ?? data
}

/** 按候选人查其入职记录（候选人详情页 Onboarding 页签用） */
export async function listOnboardingsByCandidate(
  candidateId: string,
  params: { page?: number; pageSize?: number } = {},
) {
  return listOnboardings({ ...params, candidate: candidateId })
}

/**
 * 状态流转。
 * ⚠️ 入参必须是 `{action, new_date?, result?}`（后端 OnboardingTransitionSerializer.action），
 *    action 取 ONBOARDING_ACTION 常量值；delay 需 newDate，regularize 可选 result。
 */
export async function transitionOnboarding(
  id: string,
  action: string,
  payload?: { newDate?: string; result?: string },
) {
  // ⚠️ body 只能有后端 OnboardingTransitionSerializer 认的字段（action/new_date/result）。
  //    历史上硬编码 `reason: payload?.reason || ''` → 后端不认 → 静默丢弃。
  const body: Record<string, unknown> = { action }
  if (action === ONBOARDING_ACTION.DELAY && payload?.newDate) body.new_date = payload.newDate
  if (action === ONBOARDING_ACTION.REGULARIZE && payload?.result) body.result = payload.result
  const { data } = await api.post(`onboardings/${id}/transition/`, body)
  return data?.data ?? data
}

export default api

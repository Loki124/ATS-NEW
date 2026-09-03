import axios from 'axios';
import config from '../config';
import type { TagType } from './offer';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export const INTERVIEW_STATUS = {
  SCHEDULED: 'SCHEDULED',
  CONFIRMED: 'CONFIRMED',
  COMPLETED: 'COMPLETED',
  CANCELLED: 'CANCELLED',
} as const;

export const INTERVIEW_FEEDBACK_STATUS = {
  PENDING: 'PENDING',
  COMPLETED: 'COMPLETED',
} as const;

export const INTERVIEW_STATUS_LABEL: Record<string, string> = {
  SCHEDULED: '已安排',
  CONFIRMED: '已确认',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
};

export const FEEDBACK_STATUS_LABEL: Record<string, string> = {
  PENDING: '待反馈',
  COMPLETED: '已反馈',
};

export const FEEDBACK_STATUS_COLOR: Record<string, TagType> = {
  PENDING: 'warning',
  COMPLETED: 'success',
};

export interface Interview {
  id: string;
  applicationId: string;
  roundName?: string;
  interviewType: string;
  interviewDate: string;
  duration: number;
  location?: string;
  meetingLink?: string;
  interviewerNames?: string;
  arrangerName: string;
  interviewStatus: string;
  feedbackStatus: string;
  createdAt: string;
}

export async function listInterviews(params: { page?: number; pageSize?: number; feedbackStatus?: string; interviewStatus?: string } = {}) {
  const { data } = await api.get('/interviews/', { params });
  return data;
}

export async function submitFeedback(interviewId: string, payload: { result: 'PASS' | 'FAIL'; reason?: string; [key: string]: any }) {
  const { data } = await api.post(`interviews/${interviewId}/feedback/`, payload);
  return data;
}

export async function cancelInterview(interviewId: string, reason?: string) {
  const { data } = await api.delete(`interviews/${interviewId}/`, { data: { reason } });
  return data;
}

// G19 - 获取候选人历史面试反馈 (供前端预览)
export interface InterviewHistoryItem {
  id: string;
  result: string;
  reason?: string;
  interviewerName: string;
  feedbackAt?: string;
  roundName: string;
}

export interface InterviewHistory {
  total: number;
  passCount: number;
  failCount: number;
  previousFeedback: string;
  feedbacks: InterviewHistoryItem[];
}

export async function getInterviewHistory(candidateId: string): Promise<InterviewHistory> {
  const { data } = await api.get(`/interviews/history/${candidateId}/`);
  return data.data;
}

// ============================================================================
// 面试评价 (InterviewEvaluation) — /api/v1/interviews/evaluations/
// ============================================================================
//
// 枚举对齐说明（D1 决策·v2）：前端 modal 用 3 档（PASS / FAIL / PENDING）
// 与 2026-09-03 stitch design 一致；后端 model 用 5 档
// (STRONGLY_RECOMMEND / RECOMMEND / NEUTRAL / NOT_RECOMMEND / STRONGLY_NOT_RECOMMEND)。
// 空表无历史数据兼容压力 → 前端 mapping 层做翻译，后端不动。
//
//   PASS    → RECOMMEND
//   FAIL    → NOT_RECOMMEND
//   PENDING → NEUTRAL
// STRONGLY_RECOMMEND / STRONGLY_NOT_RECOMMEND 仅后端使用（view 态反向映射回 3 档）

export type EvalFinalResult = 'PASS' | 'FAIL' | 'PENDING'

export const EVALUATION_REC_TO_BACKEND: Record<EvalFinalResult, string> = {
  PASS: 'RECOMMEND',
  FAIL: 'NOT_RECOMMEND',
  PENDING: 'NEUTRAL',
}

export const EVALUATION_REC_FROM_BACKEND: Record<string, EvalFinalResult> = {
  STRONGLY_RECOMMEND: 'PASS',
  RECOMMEND: 'PASS',
  NEUTRAL: 'PENDING',
  NOT_RECOMMEND: 'FAIL',
  STRONGLY_NOT_RECOMMEND: 'FAIL',
}

/** 评价 meta 载荷（v2 commit 2fxxxx：走 metaJson 字段，不再塞 scores） */
export interface EvaluationMeta {
  compliances: Record<string, { compliance: 'PASS' | 'PARTIAL' | 'FAIL' | null; reason: string }>
  suggestedLevel: string
  suggestedSalary: string
  /** v2 设计稿新增字段：modal 内 3 档 radio，冗余存一份方便 view 态还原 */
  finalResult: EvalFinalResult
}

/** scores JSON 里旧版元数据 key（v1 commit af10812 临时方案：__ 前缀避免污染真实分数）
 *  v2 已迁出到 metaJson 字段，仅作读取兼容（历史数据兜底） */
export const EVAL_META_KEY = '__meta'

/** 把 meta 塞进 scores JSON（**v2 已废弃**，仅作写入兼容回退，新数据请走 metaJson 字段） */
export function packEvalScores(values: Record<string, number>, meta: EvaluationMeta): Record<string, any> {
  return { ...values, [EVAL_META_KEY]: JSON.stringify(meta) }
}

/** 从 scores JSON 还原 meta（缺失或解析失败返回 null）—— 历史数据兼容 */
export function unpackEvalMeta(scores: Record<string, any> | null | undefined): EvaluationMeta | null {
  if (!scores) return null
  const raw = scores[EVAL_META_KEY]
  if (typeof raw !== 'string') return null
  try { return JSON.parse(raw) as EvaluationMeta } catch { return null }
}

/** 把 meta 从 scores JSON 里剥离（前端 view 态展示用） */
export function stripEvalMeta(scores: Record<string, any> | null | undefined): Record<string, number> {
  if (!scores) return {}
  const out: Record<string, number> = {}
  for (const [k, v] of Object.entries(scores)) {
    if (k === EVAL_META_KEY) continue
    if (typeof v === 'number') out[k] = v
  }
  return out
}

export interface InterviewEvaluationApi {
  id: string
  interview: string
  interviewer: string
  interviewerName: string
  scores: Record<string, number>
  overallScore: number | null
  /** 后端枚举 5 档：STRONGLY_RECOMMEND / RECOMMEND / NEUTRAL / NOT_RECOMMEND / STRONGLY_NOT_RECOMMEND */
  recommendation: string
  comment: string
  /** v2 (commit 2fxxxx)：评价 meta 独立字段（4 维符合性 + 建议职级/薪资 + 3 档 finalResult） */
  metaJson?: EvaluationMeta | null
  submittedAt: string
}

/** 列表响应沿用 {success, data: [...], pagination} 范式 → 返回 data 数组 */
export async function listEvaluations(
  params: { interview?: string; interviewer?: string; recommendation?: string; page?: number; pageSize?: number } = {},
): Promise<InterviewEvaluationApi[]> {
  const { data } = await api.get('/interviews/evaluations/', { params })
  return (data?.data ?? []) as InterviewEvaluationApi[]
}

/** GET 单条 / DRF 默认返回 {id, ...} 单对象 → 直接返回 */
export async function getEvaluation(id: string): Promise<InterviewEvaluationApi> {
  const { data } = await api.get(`/interviews/evaluations/${id}/`)
  return (data?.data ?? data) as InterviewEvaluationApi
}

/** 创建评价 — 必须附带 interviewer（当前用户 id），后端 serializer 未 auto-fill
 *  v2 (commit 2fxxxx)：meta 字段直接走 metaJson 字段，不再塞 scores['__meta']
 *      兼容旧客户端：旧数据读时 fallback 到 scores['__meta'] */
export async function createEvaluation(payload: {
  interview: string
  interviewer: string
  scores: Record<string, any>
  overallScore: number
  /** 已转为后端 5 档字符串 */
  recommendation: string
  comment: string
  /** v2：评价 meta（独立字段，避免污染 scores 真实分数 key） */
  metaJson?: EvaluationMeta
}): Promise<InterviewEvaluationApi> {
  const { data } = await api.post('/interviews/evaluations/', payload)
  return (data?.data ?? data) as InterviewEvaluationApi
}

/** 部分更新评价 */
export async function updateEvaluation(
  id: string,
  payload: Partial<{
    scores: Record<string, number>
    overallScore: number
    recommendation: string
    comment: string
  }>,
): Promise<InterviewEvaluationApi> {
  const { data } = await api.patch(`/interviews/evaluations/${id}/`, payload)
  return (data?.data ?? data) as InterviewEvaluationApi
}

export default api;

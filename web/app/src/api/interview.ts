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
// 枚举对齐说明（D1 决策）：前端 modal 用 4 档（PASS / MANAGER / DISCUSS / FAIL）
// 与截图 / 设计稿一致；后端 model 用 5 档
// (STRONGLY_RECOMMEND / RECOMMEND / NEUTRAL / NOT_RECOMMEND / STRONGLY_NOT_RECOMMEND)。
// 空表无历史数据兼容压力 → 前端 mapping 层做翻译，后端不动。
//
//   PASS    → RECOMMEND
//   MANAGER → NEUTRAL
//   DISCUSS → NEUTRAL
//   FAIL    → NOT_RECOMMEND
// STRONGLY_RECOMMEND / STRONGLY_NOT_RECOMMEND 仅后端使用（view 态反向映射回 4 档）

export const EVALUATION_REC_TO_BACKEND: Record<string, string> = {
  PASS: 'RECOMMEND',
  MANAGER: 'NEUTRAL',
  DISCUSS: 'NEUTRAL',
  FAIL: 'NOT_RECOMMEND',
}

export const EVALUATION_REC_FROM_BACKEND: Record<string, 'PASS' | 'MANAGER' | 'DISCUSS' | 'FAIL'> = {
  STRONGLY_RECOMMEND: 'PASS',
  RECOMMEND: 'PASS',
  NEUTRAL: 'DISCUSS',
  NOT_RECOMMEND: 'FAIL',
  STRONGLY_NOT_RECOMMEND: 'FAIL',
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

/** 创建评价 — 必须附带 interviewer（当前用户 id），后端 serializer 未 auto-fill */
export async function createEvaluation(payload: {
  interview: string
  interviewer: string
  scores: Record<string, number>
  overallScore: number
  /** 已转为后端 5 档字符串 */
  recommendation: string
  comment: string
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

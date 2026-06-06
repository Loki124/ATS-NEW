import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
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

export const FEEDBACK_STATUS_COLOR: Record<string, string> = {
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
  const { data } = await api.get('/api/interviews', { params });
  return data;
}

export async function submitFeedback(interviewId: string, payload: { result: 'PASS' | 'FAIL'; reason?: string; [key: string]: any }) {
  const { data } = await api.post(`/api/interviews/${interviewId}/feedback`, payload);
  return data;
}

export async function cancelInterview(interviewId: string, reason?: string) {
  const { data } = await api.delete(`/api/interviews/${interviewId}`, { data: { reason } });
  return data;
}

export default api;

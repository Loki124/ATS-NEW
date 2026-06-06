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

export const ONBOARDING_STATUS = {
  NOT_STARTED: 'NOT_STARTED',
  PENDING_CONFIRM: 'PENDING_CONFIRM',
  CONFIRMED: 'CONFIRMED',
  PENDING_ONBOARD: 'PENDING_ONBOARD',
  ONBOARDING: 'ONBOARDING',
  ONBOARDED: 'ONBOARDED',
  PENDING_REJECT: 'PENDING_REJECT',
  CANCELLED: 'CANCELLED',
} as const;

export const ONBOARDING_STATUS_LABEL: Record<string, string> = {
  NOT_STARTED: '未开始',
  PENDING_CONFIRM: '待确认',
  CONFIRMED: '已确认',
  PENDING_ONBOARD: '待入职',
  ONBOARDING: '入职中',
  ONBOARDED: '已入职',
  PENDING_REJECT: '待拒绝',
  CANCELLED: '已取消',
};

export const ONBOARDING_STATUS_COLOR: Record<string, string> = {
  NOT_STARTED: 'default',
  PENDING_CONFIRM: 'warning',
  CONFIRMED: 'info',
  PENDING_ONBOARD: 'primary',
  ONBOARDING: 'warning',
  ONBOARDED: 'success',
  PENDING_REJECT: 'error',
  CANCELLED: 'default',
};

export interface Onboarding {
  id: string;
  applicationId: string;
  jobTitle?: string;
  jobLevel?: string;
  expectedJoinDate: string;
  onboardingStatus: string;
  onboardedAt?: string;
  cancelReason?: string;
}

export async function listOnboardings(params: { page?: number; pageSize?: number; onboardingStatus?: string } = {}) {
  const { data } = await api.get('/onboardings', { params });
  return data;
}

export async function transitionOnboarding(id: string, to: string, reason?: string) {
  const { data } = await api.post(`onboardings/${id}/transition`, { to, reason });
  return data;
}

export default api;

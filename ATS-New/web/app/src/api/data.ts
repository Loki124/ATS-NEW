// G35 - 数据中心 前端 API 客户端 (KPI + 导出 + 订阅)

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

export interface DashboardKpi {
  totalCandidates: number;
  activeDemands: number;
  openPositions: number;
  ongoingInterviews: number;
  sentOffers: number;
  pendingOnboardings: number;
  generatedAt: string;
}

export interface DataSubscription {
  id: string;
  userId: string;
  userName: string;
  resource: string; // Candidate / Demand / Position / Offer / Interview / Onboarding
  metric: string;   // 'all' / 'count_by_status' / 'count_by_dept' / 'export_csv'
  filters?: string | null;
  channel: string;  // EMAIL / SYSTEM / WECOM / SMS
  schedule: string; // DAILY / WEEKLY / MONTHLY / ON_DEMAND
  scheduleTime?: string | null;
  recipients?: string | null;
  isActive: boolean;
  lastRunAt?: string | null;
  nextRunAt?: string | null;
  runCount: number;
  createdAt: string;
  updatedAt: string;
}

export const getKpi = () =>
  api.get('/data/kpi').then((r) => r.data.data);

export const exportResource = (resource: string, format: 'csv' | 'json' = 'csv', fields?: string[]) =>
  api.get(`/data/export/${resource}`, {
    params: { format, fields: fields?.join(',') },
    responseType: 'blob',
  }).then((r) => r.data);

export const listSubscriptions = () =>
  api.get('/data/subscriptions').then((r) => r.data.data);

export const createSubscription = (body: Partial<DataSubscription>) =>
  api.post('/data/subscriptions', body).then((r) => r.data.data);

export const deleteSubscription = (id: string) =>
  api.delete(`/data/subscriptions/${id}`).then((r) => r.data);

export const RESOURCE_OPTIONS = [
  { label: '候选人 Candidate', value: 'Candidate' },
  { label: '需求 Demand', value: 'Demand' },
  { label: '职位 Position', value: 'Position' },
  { label: 'Offer', value: 'Offer' },
  { label: '面试 Interview', value: 'Interview' },
  { label: '入职 Onboarding', value: 'Onboarding' },
];

export const CHANNEL_OPTIONS = [
  { label: '系统消息', value: 'SYSTEM' },
  { label: '邮件 EMAIL', value: 'EMAIL' },
  { label: '企业微信', value: 'WECOM' },
  { label: '短信 SMS', value: 'SMS' },
];

export const SCHEDULE_OPTIONS = [
  { label: '每日 DAILY', value: 'DAILY' },
  { label: '每周 WEEKLY', value: 'WEEKLY' },
  { label: '每月 MONTHLY', value: 'MONTHLY' },
  { label: '按需 ON_DEMAND', value: 'ON_DEMAND' },
];

export default api;

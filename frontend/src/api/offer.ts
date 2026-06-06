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

export const OFFER_STATUS = {
  NOT_CREATED: 'NOT_CREATED',
  DRAFT: 'DRAFT',
  PENDING_APPROVAL: 'PENDING_APPROVAL',
  APPROVED: 'APPROVED',
  SENT: 'SENT',
  ACCEPTED: 'ACCEPTED',
  REJECTED: 'REJECTED',
  WITHDRAWN: 'WITHDRAWN',
  EXPIRED: 'EXPIRED',
} as const;

export const OFFER_STATUS_LABEL: Record<string, string> = {
  NOT_CREATED: '未创建',
  DRAFT: '草稿',
  PENDING_APPROVAL: '待审批',
  APPROVED: '已审批',
  SENT: '已发送',
  ACCEPTED: '已接受',
  REJECTED: '已拒绝',
  WITHDRAWN: '已撤销',
  EXPIRED: '已过期',
};

export const OFFER_STATUS_COLOR: Record<string, string> = {
  NOT_CREATED: 'default',
  DRAFT: 'info',
  PENDING_APPROVAL: 'warning',
  APPROVED: 'success',
  SENT: 'primary',
  ACCEPTED: 'success',
  REJECTED: 'error',
  WITHDRAWN: 'default',
  EXPIRED: 'warning',
};

export const OFFER_TEMPLATE_KEY = {
  GENERAL: 'GENERAL',
  WITH_COMMISSION: 'WITH_COMMISSION',
  INTERN: 'INTERN',
  MEIZHOU: 'MEIZHOU',
} as const;

export const OFFER_TEMPLATE_LABEL: Record<string, string> = {
  GENERAL: '通用模板',
  WITH_COMMISSION: '含提成',
  INTERN: '实习生',
  MEIZHOU: '梅州版',
};

export interface Offer {
  id: string;
  applicationId: string;
  demandId?: string;
  jobTitle?: string;
  jobLevel?: string;
  expectedJoinDate: string;
  offerStatus: string;
  baseSalaryTrial?: number;
  baseSalaryFormal?: number;
  sentAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface OfferTemplate {
  key: string;
  name: string;
  description: string;
  applicableTypes: string[];
  variables: string[];
}

export async function listOffers(params: { page?: number; pageSize?: number; offerStatus?: string; demandId?: string } = {}) {
  const { data } = await api.get('/api/offers', { params });
  return data;
}

export async function getOffer(id: string) {
  const { data } = await api.get(`/api/offers/${id}`);
  return data;
}

export async function getOfferHistory(id: string) {
  const { data } = await api.get(`/api/offers/${id}/status-history`);
  return data;
}

export async function transitionOffer(id: string, to: string, reason?: string) {
  const { data } = await api.post(`/api/offers/${id}/transition`, { to, reason });
  return data;
}

export async function listOfferTemplates() {
  const { data } = await api.get('/api/offer-templates');
  return data;
}

export async function renderOffer(offerId: string, templateKey: string, format: 'html' | 'pdf' = 'html') {
  const { data } = await api.post('/api/offer-templates/render-from-offer', { offerId, templateKey, format });
  return data;
}

export default api;

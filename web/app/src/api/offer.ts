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

export type TagType = 'default' | 'primary' | 'success' | 'info' | 'warning' | 'error';

export const OFFER_STATUS_COLOR: Record<string, TagType> = {
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
  const { data } = await api.get('/offers', { params });
  return data;
}

export async function getOffer(id: string) {
  const { data } = await api.get(`offers/${id}`);
  return data;
}

export async function getOfferHistory(id: string) {
  const { data } = await api.get(`offers/${id}/status-history`);
  return data;
}

export async function transitionOffer(id: string, to: string, reason?: string) {
  const { data } = await api.post(`offers/${id}/transition`, { to, reason });
  return data;
}

export async function listOfferTemplates() {
  const { data } = await api.get('/offer-templates');
  return data;
}

export async function renderOffer(offerId: string, templateKey: string, format: 'html' | 'pdf' = 'html') {
  const { data } = await api.post('/offer-templates/render-from-offer', { offerId, templateKey, format });
  return data;
}

// G26 - 手动背调 4 等级

export const BG_CHECK_LEVEL = {
  PASS: 'PASS',
  WARN: 'WARN',
  INCONCLUSIVE: 'INCONCLUSIVE',
  FAIL: 'FAIL',
} as const;

export const BG_CHECK_LEVEL_LABEL: Record<string, string> = {
  PASS: '通过',
  WARN: '有保留通过',
  INCONCLUSIVE: '资料不足',
  FAIL: '不通过',
};

export const BG_CHECK_LEVEL_COLOR: Record<string, TagType> = {
  PASS: 'success',
  WARN: 'warning',
  INCONCLUSIVE: 'info',
  FAIL: 'error',
};

export interface BackgroundCheck {
  id: string;
  offerId: string;
  checkType: string;
  result?: string;
  level?: string;
  score?: number;
  risks?: Array<{ category?: string; severity?: string; description?: string }>;
  supplier?: string;
  note?: string;
  orderedAt?: string;
  authorizedAt?: string;
  completedAt?: string;
  reportPath?: string;
  reportUrl?: string;
  reportSize?: number;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export async function listBackgroundChecks(offerId: string): Promise<BackgroundCheck[]> {
  const { data } = await api.get(`/offers/${offerId}/background-checks`);
  return data.data;
}

export async function createBackgroundCheck(offerId: string, payload: { checkType: string; supplier?: string; note?: string }): Promise<BackgroundCheck> {
  const { data } = await api.post(`/offers/${offerId}/background-checks`, payload);
  return data.data;
}

export async function completeBackgroundCheck(
  offerId: string,
  bid: string,
  payload: { level: 'PASS' | 'WARN' | 'INCONCLUSIVE' | 'FAIL'; risks?: any[]; reportPath?: string; reportUrl?: string; reportSize?: number },
): Promise<BackgroundCheck> {
  const { data } = await api.put(`/offers/${offerId}/background-checks/${bid}/complete`, payload);
  return data.data;
}

export async function downloadBackgroundCheckReport(offerId: string, bid: string): Promise<Blob> {
  const { data } = await api.get(`/offers/${offerId}/background-checks/${bid}/report`, { responseType: 'blob' });
  return data;
}

export default api;

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

export const INVITATION_STATUS = {
  PENDING_ASSIGN: 'PENDING_ASSIGN',
  PENDING_CLAIM: 'PENDING_CLAIM',
  PENDING_INVITE: 'PENDING_INVITE',
  INVITING: 'INVITING',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
  TERMINATED: 'TERMINATED',
  INTERVENED: 'INTERVENED',
} as const;

export const INVITATION_STATUS_LABEL: Record<string, string> = {
  PENDING_ASSIGN: '待分配',
  PENDING_CLAIM: '待领取',
  PENDING_INVITE: '待邀约',
  INVITING: '邀约中',
  SUCCESS: '已成功',
  FAILED: '已失败',
  TERMINATED: '已终止',
  INTERVENED: '被干预',
};

export const INVITATION_STATUS_COLOR: Record<string, string> = {
  PENDING_ASSIGN: 'default',
  PENDING_CLAIM: 'warning',
  PENDING_INVITE: 'info',
  INVITING: 'primary',
  SUCCESS: 'success',
  FAILED: 'error',
  TERMINATED: 'default',
  INTERVENED: 'warning',
};

export interface Invitation {
  id: string;
  applicationId: string;
  candidateId: string;
  positionId: string;
  ownerId: string;
  ownerName: string;
  inviterId?: string;
  inviterName?: string;
  assignType: string;
  assignedAt?: string;
  invitationStatus: string;
  claimedAt?: string;
  claimedById?: string;
  claimedByName?: string;
  contactAttempts: number;
  lastContactAt?: string;
  interventionCount: number;
  lastInterventionBy?: string;
  resultStatus?: string;
  resultReason?: string;
  resultAt?: string;
  timeoutAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ListParams {
  page?: number;
  pageSize?: number;
  status?: string;
  positionId?: string;
  ownerId?: string;
  claimedById?: string;
  expired?: boolean;
}

export async function listInvitations(params: ListParams = {}) {
  const { data } = await api.get('/invitations', { params });
  return data;
}

export async function getClaimPool() {
  const { data } = await api.get('/invitations/claimable');
  return data;
}

export async function getInvitation(id: string) {
  const { data } = await api.get(`invitations/${id}`);
  return data;
}

export async function enterPool(id: string, reason?: string) {
  const { data } = await api.post(`invitations/${id}/enter-pool`, { reason });
  return data;
}

export async function claim(id: string) {
  const { data } = await api.post(`invitations/${id}/claim`);
  return data;
}

export async function markContacted(id: string, note?: string) {
  const { data } = await api.post(`invitations/${id}/contact`, { note });
  return data;
}

export async function markResult(id: string, success: boolean, reason?: string) {
  const { data } = await api.post(`invitations/${id}/result`, { success, reason });
  return data;
}

export async function intervene(id: string, reason?: string) {
  const { data } = await api.post(`invitations/${id}/intervene`, { reason });
  return data;
}

export async function terminate(id: string, reason?: string) {
  const { data } = await api.post(`invitations/${id}/terminate`, { reason });
  return data;
}

export async function processExpired() {
  const { data } = await api.post('/invitations/process-expired');
  return data;
}

export default api;

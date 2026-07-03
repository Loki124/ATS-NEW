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

export const INVITATION_STATUS_COLOR: Record<string, TagType> = {
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
  const { data } = await api.get('/invitations/', { params });
  return data;
}

export async function getClaimPool() {
  const { data } = await api.get('/invitations/claimable/');
  return data;
}

export async function getInvitation(id: string) {
  const { data } = await api.get(`invitations/${id}`);
  return data;
}

export async function enterPool(id: string, reason?: string) {
  // 2026-06-29 花无缺: 后端 InvitationViewSet 实际只有 /transition (统一 action 路由),
  //   FE 调独立的 /enter-pool /claim /contact /result /intervene /terminate 全部 404.
  //   全部改用 /transition + action body (后端 state machine 走同一入口)
  const { data } = await api.post(`invitations/${id}/transition`, { action: 'enter_pool', reason })
  return data
}

export async function claim(id: string) {
  const { data } = await api.post(`invitations/${id}/transition`, { action: 'claim' })
  return data
}

export async function markContacted(id: string, note?: string) {
  // /contact → /transition + 'contact' action
  const { data } = await api.post(`invitations/${id}/transition`, { action: 'contact', note })
  return data
}

export async function markResult(id: string, success: boolean, reason?: string) {
  // /result → /transition + 'success' or 'fail' action
  const { data } = await api.post(`invitations/${id}/transition`, {
    action: success ? 'success' : 'fail',
    reason,
  })
  return data
}

export async function intervene(id: string, reason?: string) {
  const { data } = await api.post(`invitations/${id}/transition`, { action: 'intervene', reason })
  return data
}

export async function terminate(id: string, reason?: string) {
  const { data } = await api.post(`invitations/${id}/transition`, { action: 'terminate', reason })
  return data
}

export async function processExpired() {
  const { data } = await api.post('/invitations/process-expired/');
  return data;
}

export default api;

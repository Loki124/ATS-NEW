import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截器：自动加 Bearer token
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// ===== 类型定义 =====

export interface ReferralCode {
  id: string;
  code: string;
  userId: string;
  status: 'ACTIVE' | 'INVALID' | string;
  invalidReason?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReferralRecord {
  id: string;
  candidateName: string;
  candidatePhone?: string;
  candidateEmail?: string;
  positionId?: string;
  positionTitle?: string;
  referralCodeId: string;
  referralCode: string;
  referralUserId: string;
  referralUserName: string;
  status: string;
  currentStage: string;
  appliedAt?: string;
  onboardedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ReferralRecordSummary {
  recommendValidCount: number;
  onboardedCount: number;
  probationPassedCount: number;
  rewardToConfirmTotal: number;
  rewardConfirmedTotal: number;
  rewardIssuedTotal: number;
}

export interface ReferralReward {
  id: string;
  recordId: string;
  candidateName: string;
  amount: number;
  currency: string;
  status: string;
  triggeredAt: string;
  confirmedAt?: string;
  issuedAt?: string;
}

export interface ReferralRule {
  id: string;
  name: string;
  ruleType: 'REWARD' | 'RESTRICTION' | string;
  positionLevel?: string;
  triggerStage?: string;
  conditions: any;
  amount?: string;
  description?: string;
  status: string;
  createdAt: string;
}

export interface ExpertConfig {
  id: string;
  userId: string;
  teamId: string;
  expertId: string;
  expertName?: string;
  referralCodeId?: string;
  isPrimary: boolean;
}

export interface PaginatedResult<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

// ===== API 方法 =====

export const getMyCode = () =>
  api.get<{ success: boolean; data: ReferralCode }>('/referral/codes/me').then((r) => r.data.data);

export const getMyRecords = (page = 1, pageSize = 20) =>
  api
    .get<{ success: boolean; data: PaginatedResult<ReferralRecord> }>('/referral/records/me', {
      params: { page, pageSize },
    })
    .then((r) => r.data.data);

export const getMyRecordSummary = () =>
  api
    .get<{ success: boolean; data: ReferralRecordSummary }>('/referral/records/me/summary')
    .then((r) => r.data.data);

export const getMyRewards = (page = 1, pageSize = 20) =>
  api
    .get<{ success: boolean; data: PaginatedResult<ReferralReward> }>('/referral/rewards/me', {
      params: { page, pageSize },
    })
    .then((r) => r.data.data);

export const getRules = () =>
  api
    .get<{ success: boolean; data: ReferralRule[] }>('/referral/rules')
    .then((r) => r.data.data);

export const getMyExpertConfigs = () =>
  api
    .get<{ success: boolean; data: ExpertConfig[] }>('/referral/expert-configs/me')
    .then((r) => r.data.data);

// ===== 新增推荐（内部员工手动添加）=====
export const addReferral = (payload: {
  candidate: { name: string; phone?: string; email?: string }
  candidateId: string
  positionId: string
}) =>
  api
    .post<{ success: boolean; data: { id: string } }>('/referral/records', {
      candidateId: payload.candidateId,
      positionId: payload.positionId,
      // resumeId 不传（前端流程里没真实简历文件，createReferral 内部允许 null）
      referralType: 'REFERRER_HELP',
    })
    .then((r) => r.data)

// ===== 奖励确认/拒绝/发放（管理员）=====
export const confirmReward = (rewardId: string) =>
  api.post<{ success: boolean }>(`/referral/rewards/${rewardId}/confirm`).then((r) => r.data)

export const rejectReward = (rewardId: string, reason?: string) =>
  api.post<{ success: boolean }>(`/referral/rewards/${rewardId}/reject`, { reason }).then((r) => r.data)

export const issueReward = (rewardId: string) =>
  api.post<{ success: boolean }>(`/referral/rewards/${rewardId}/issue`).then((r) => r.data)

export default {
  getMyCode,
  getMyRecords,
  getMyRecordSummary,
  getMyRewards,
  getRules,
  getMyExpertConfigs,
  addReferral,
  confirmReward,
  rejectReward,
  issueReward,
};

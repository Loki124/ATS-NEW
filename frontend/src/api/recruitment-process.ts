/**
 * 招聘流程管理 API 客户端 - PRD G38 (P0)
 */

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

// ===== 类型定义 =====
export interface RecruitmentProcess {
  id: string;
  code: string;
  name: string;
  description?: string;
  status: 'ACTIVE' | 'INACTIVE';
  // 适用范围
  applicableDepartments?: string[];
  applicablePositionLevels?: string[];
  applicableUserIds?: string[];
  applicableJobs?: string[];
  applicableMode: 'ALL' | 'ANY';
  // 简历评分开关
  validateResumeScore: boolean;
  // 流转异常提示
  failPrompt?: string;
  createdAt: string;
  updatedAt: string;
  _count?: { links: number; stageRules: number };
  updater?: { id: string; realName?: string; username: string };
  links?: ProcessStageLink[];
}

export interface RecruitmentStage {
  id: string;
  code: string;
  name: string;
  stageType: 'FILTER' | 'INVITATION' | 'INTERVIEW' | 'OFFER' | 'ONBOARDING';
  features: string[];
  isSystem: boolean;
  description?: string;
  status: 'ACTIVE' | 'INACTIVE';
  createdAt: string;
  updatedAt: string;
  _count?: { links: number };
}

/// 流程-阶段 link（每个流程包含哪些阶段 + 顺序 + 规则）
export interface ProcessStageLink {
  id: string;
  processId: string;
  stageId: string;
  orderIndex: number;
  customName?: string;
  isStart: boolean;
  isEnd: boolean;
  stageLimit?: number;
  status: 'ACTIVE' | 'INACTIVE';
  stage: RecruitmentStage;
  rule?: StageRule | null;
  condition?: EntryCondition | null;
}

export interface StageRule {
  id: string;
  stageId: string;
  processId: string;
  autoAdvanceType: 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS';
  autoAdvanceTiming: 'NONE' | 'IMMEDIATE' | 'DELAYED';
  autoAdvanceDays?: number;
  defaultHandlerType: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM';
  defaultHandlerFields?: string[];
  defaultHandlerUserIds?: string[];
  timeLimit?: number;
  timeLimitScope: 'NEW_ONLY' | 'ALL';
  interviewRoundIds?: string[];
}

export interface EntryCondition {
  id: string;
  stageId: string;
  processId: string;
  matchType: 'ALL' | 'ANY';
  conditionType: 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED';
  prompt?: string;
  items: ConditionItem[];
}

export interface ConditionItem {
  id?: string;
  parentId?: string | null;
  relationToParent?: 'AND' | 'OR' | null;
  field: string;
  operator: string;
  value?: any;
  refStageId?: string;
  refDictId?: string;
  orderIndex?: number;
}

export interface InterviewRound {
  id: string;
  code: string;
  name: string;
  description?: string;
  evaluationFormName?: string;
  isUniversal: boolean;
  status: 'ACTIVE' | 'INACTIVE';
  createdBy?: string;
}

export interface AutoArchiveRule {
  id: string;
  processId: string;
  ruleType: 'INVITE_FAIL' | 'OFFER_FAIL' | 'EVAL_FAIL' | 'TIMEOUT_UNASSIGNED';
  enabled: boolean;
  config: any;
}

// ===== API =====
export const listProcesses = (params?: { status?: string; keyword?: string }) =>
  api.get<{ success: boolean; data: RecruitmentProcess[] }>('/recruitment-processes', { params }).then((r) => r.data.data);

export const getProcess = (id: string) =>
  api.get<{ success: boolean; data: RecruitmentProcess & { stages: RecruitmentStage[]; autoRules: AutoArchiveRule[] } }>(`/recruitment-processes/${id}`).then((r) => r.data.data);

export const createProcess = (payload: { name: string; description?: string; createdBy?: string; validateResumeScore?: boolean; failPrompt?: string; applicableMode?: 'ALL' | 'ANY' }) =>
  api.post<{ success: boolean; data: RecruitmentProcess }>('/recruitment-processes', payload).then((r) => r.data.data);

export const updateProcess = (id: string, payload: Partial<RecruitmentProcess>) =>
  api.put<{ success: boolean; data: RecruitmentProcess }>(`/recruitment-processes/${id}`, payload).then((r) => r.data.data);

export const deleteProcess = (id: string) =>
  api.delete<{ success: boolean }>(`/recruitment-processes/${id}`).then((r) => r.data);

export const copyProcess = (id: string, payload: { newName?: string; createdBy?: string }) =>
  api.post<{ success: boolean; data: RecruitmentProcess }>(`/recruitment-processes/${id}/copy`, payload).then((r) => r.data.data);

export const updateProcessStatus = (id: string, status: 'ACTIVE' | 'INACTIVE') =>
  api.put<{ success: boolean; data: RecruitmentProcess }>(`/recruitment-processes/${id}/status`, { status }).then((r) => r.data.data);

// ===== 阶段 =====
export const listStages = (params?: { stageType?: string; status?: string; keyword?: string }) =>
  api.get<{ success: boolean; data: RecruitmentStage[] }>('/recruitment-stages', { params }).then((r) => r.data.data);

export const createStage = (payload: { name: string; stageType: string; features?: string[]; description?: string; stageLimit?: number }) =>
  api.post<{ success: boolean; data: RecruitmentStage }>('/recruitment-stages', payload).then((r) => r.data.data);

export const updateStage = (id: string, payload: Partial<RecruitmentStage>) =>
  api.put<{ success: boolean; data: RecruitmentStage }>(`/recruitment-stages/${id}`, payload).then((r) => r.data.data);

export const deleteStage = (id: string) =>
  api.delete<{ success: boolean }>(`/recruitment-stages/${id}`).then((r) => r.data);

export const updateStageStatus = (id: string, status: 'ACTIVE' | 'INACTIVE') =>
  api.put<{ success: boolean; data: RecruitmentStage }>(`/recruitment-stages/${id}/status`, { status }).then((r) => r.data.data);

// ===== 流程-阶段 link =====
export const listProcessLinks = (processId: string) =>
  api.get<{ success: boolean; data: ProcessStageLink[] }>('/recruitment-process-stage-links', { params: { processId } }).then((r) => r.data.data);

export const addProcessLink = (payload: { processId: string; stageId: string; orderIndex?: number; customName?: string; stageLimit?: number }) =>
  api.post<{ success: boolean; data: ProcessStageLink }>('/recruitment-process-stage-links', payload).then((r) => r.data.data);

export const updateProcessLink = (id: string, payload: Partial<ProcessStageLink>) =>
  api.put<{ success: boolean; data: ProcessStageLink }>(`/recruitment-process-stage-links/${id}`, payload).then((r) => r.data.data);

export const deleteProcessLink = (id: string) =>
  api.delete<{ success: boolean }>(`/recruitment-process-stage-links/${id}`).then((r) => r.data);

export const reorderProcessLinks = (processId: string, orderedLinkIds: string[]) =>
  api.put<{ success: boolean }>('/recruitment-process-stage-links/reorder', { processId, orderedLinkIds }).then((r) => r.data);

// ===== 阶段规则 + 进入条件 =====
export const upsertStageRule = (stageId: string, payload: Partial<StageRule> & { processId?: string }) =>
  api.post<{ success: boolean; data: StageRule }>('/recruitment-rules/stage-rules', { stageId, ...payload }).then((r) => r.data.data);

export const upsertEntryCondition = (stageId: string, payload: {
  matchType: 'ALL' | 'ANY';
  conditionType: 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED';
  prompt?: string;
  items: ConditionItem[];
}) =>
  api.post<{ success: boolean; data: EntryCondition }>('/recruitment-rules/entry-conditions', { stageId, ...payload }).then((r) => r.data.data);

export const evaluateEntryCondition = (stageId: string, context: { candidate: any; stageStatuses?: any }) =>
  api.post<{ success: boolean; data: { passed: boolean; failedItems: any[]; prompt: string | null } }>(`/recruitment-rules/entry-conditions/${stageId}/evaluate`, context).then((r) => r.data.data);

// ===== 面试轮次 =====
export const listRounds = (params?: { status?: string; keyword?: string }) =>
  api.get<{ success: boolean; data: InterviewRound[] }>('/recruitment-rounds', { params }).then((r) => r.data.data);

export const createRound = (payload: { name: string; description?: string; evaluationFormName?: string; isUniversal?: boolean; createdBy?: string }) =>
  api.post<{ success: boolean; data: InterviewRound }>('/recruitment-rounds', payload).then((r) => r.data.data);

export const updateRound = (id: string, payload: Partial<InterviewRound>) =>
  api.put<{ success: boolean; data: InterviewRound }>(`/recruitment-rounds/${id}`, payload).then((r) => r.data.data);

export const updateRoundStatus = (id: string, status: 'ACTIVE' | 'INACTIVE') =>
  api.put<{ success: boolean; data: InterviewRound }>(`/recruitment-rounds/${id}/status`, { status }).then((r) => r.data.data);

// Auto-archive rules (G38 #8 配套, 暂未实现后端)
export const listAutoArchiveRules = (params: { processId?: string } = {}) =>
  api.get<{ success: boolean; data: AutoArchiveRule[] }>('/recruitment-rules/auto-archive-rules', { params }).then((r) => r.data.data)

export const upsertAutoArchiveRule = (rule: Partial<AutoArchiveRule>) =>
  api.post<{ success: boolean; data: AutoArchiveRule }>('/recruitment-rules/auto-archive-rules', rule).then((r) => r.data.data)

export default {
  listProcesses, getProcess, createProcess, updateProcess, deleteProcess, copyProcess, updateProcessStatus,
  listStages, createStage, updateStage, deleteStage, updateStageStatus,
  listProcessLinks, addProcessLink, updateProcessLink, deleteProcessLink, reorderProcessLinks,
  upsertStageRule, upsertEntryCondition, evaluateEntryCondition,
  listRounds, createRound, updateRound, updateRoundStatus,
};

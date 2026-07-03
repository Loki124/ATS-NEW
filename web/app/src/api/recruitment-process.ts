/**
 * 招聘流程管理 API 客户端 - PRD G38 (P0)
 *
 * 2026-06-17: BE 启用 drf-camel-case, 请求/响应 snake_case ↔ camelCase 自动转换;
 *             FE 直接发 camelCase (stageType / orderIndex 等), 无需手动桥接.
 * 2026-06-17: URL 对齐 BE 实际路由 (config/urls.py):
 *             /recruitment-processes        → /processes
 *             /recruitment-stages           → /stages
 *             /recruitment-process-stage-links → /process-stage-links
 *             /recruitment-rules/entry-conditions → /entry-condition-rules (BE 已挂载)
 *             /recruitment-rules/{stage-rules,candidates,applications,auto-archive-rules},
 *             /recruitment-rounds  ← BE 尚未挂载, 命中即 404 (G38 BE 60%, 待续).
 */

import axios from 'axios';
import config from '../config';

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
  // 2026-06-17: 新 4 指标 (含值 + 包含/不包含 + 多值), BE 存到 applicable_scope JSONField
  applicableScope?: { mode: 'ALL' | 'ANY'; indicators: { key: 'department' | 'level' | 'position' | 'user'; mode: 'include' | 'exclude'; values: string[] }[] };
  // 简历评分开关
  validateResumeScore: boolean;
  // 流转异常提示
  failPrompt?: string;
  createdAt: string;
  updatedAt: string;
  _count?: { links: number; stageRules: number };
  updater?: { id: string; realName?: string; username: string };
  // 2026-07-02: BE getProcess 返回的元信息 (创建人/修改人)
  creator?: { id: string; realName?: string; username: string };
  links?: ProcessStageLink[];
}

export interface RecruitmentStage {
  id: string;
  code: string;
  name: string;
  // 2026-06-29 花无缺: BE (apps/process/models.py:23-28) StageType = SCREEN/INVITATION/INTERVIEW/OFFER.
  //   旧 FE 定义用 'FILTER' + 多了 'ONBOARDING' (BE 没有), 跟 BE 不同步, POST/PUT 走 400.
  //   改成跟 BE 一致. 前端 'src/pages/settings/RecruitmentStage.vue' 已经用 SCREEN (form.stageType 默认 'SCREEN', FALLBACK_STAGE_TYPE 第 1 个 value=SCREEN),
  //   本次对齐是 FE 落后 -> 跟上 BE.
  stageType: 'SCREEN' | 'INVITATION' | 'INTERVIEW' | 'OFFER';
  features: string[];
  isSystem: boolean;
  // 2026-07-03 BR-001: 起止阶段标记, 后端 RecruitmentStage 加了 is_start/is_end 列;
  // 全局有且仅有 1 个起始 (=初评) 和 1 个结束 (=正式录用), 由 seed 设置, serializer 强制互斥唯一.
  isStart: boolean;
  isEnd: boolean;
  description?: string;
  // 2026-07-03: BE StageStatus = ENABLED/DISABLED (apps/process/models.py),
  //   旧 'ACTIVE'|'INACTIVE' 跟 BE 不一致 → status 列恒显示「停用」.
  status: 'ENABLED' | 'DISABLED';
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
  // 2026-07-03 BR-001: isStart/isEnd 已从 link 移到 stage 自身, 此处删除
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
  api.get<{ success: boolean; data: RecruitmentProcess[] }>('/processes/', { params }).then((r) => r.data.data);

// 2026-07-02: BE 部分接口已不再包 {success, data} 包裹, 直接返 root object;
// normalize 函数兼容两种形态
const unwrap = (resp: any) => {
  // axios response: r.data 是 response body
  const body = resp?.data ?? resp
  // 包裹形态: {success, data, code, message, errors}
  if (body && typeof body === 'object' && 'success' in body && 'data' in body) {
    return body.data
  }
  return body
}

export const getProcess = (id: string) =>
  api.get(`/processes/${id}/`).then((r) => unwrap(r)) as unknown as Promise<RecruitmentProcess & { stages: RecruitmentStage[]; autoRules: AutoArchiveRule[] }>;

// 2026-06-17: 加上 applicableScope (4 指标数组). 旧的 applicableDepartments/Levels/UserIds/Jobs 字段保留兼容.
export const createProcess = (payload: { name: string; description?: string; createdBy?: string; validateResumeScore?: boolean; failPrompt?: string; applicableMode?: 'ALL' | 'ANY'; applicableDepartments?: string[]; applicablePositionLevels?: string[]; applicableUserIds?: string[]; applicableJobs?: string[]; applicableScope?: { mode: 'ALL' | 'ANY'; indicators: { key: 'department' | 'level' | 'position' | 'user'; mode: 'include' | 'exclude'; values: string[] }[] } }) =>
  api.post<{ success: boolean; data: RecruitmentProcess }>('/processes/', payload).then((r) => r.data.data);

export const updateProcess = (id: string, payload: Partial<RecruitmentProcess>) =>
  api.put<{ success: boolean; data: RecruitmentProcess }>(`/processes/${id}/`, payload).then((r) => r.data.data);

export const deleteProcess = (id: string) =>
  api.delete<{ success: boolean }>(`/processes/${id}/`).then((r) => r.data);

export const copyProcess = (id: string, payload: { newName?: string; createdBy?: string }) =>
  api.post<{ success: boolean; data: RecruitmentProcess }>(`/processes/${id}/copy/`, payload).then((r) => r.data.data);

export const updateProcessStatus = (id: string, status: 'ACTIVE' | 'INACTIVE') =>
  api.put<{ success: boolean; data: RecruitmentProcess }>(`/processes/${id}/status/`, { status }).then((r) => r.data.data);

// ===== 阶段 =====
export const listStages = (params?: { stageType?: string; status?: string; keyword?: string }) =>
  api.get<{ success: boolean; data: RecruitmentStage[] }>('/stages/', { params }).then((r) => r.data.data);

export const createStage = (payload: { name: string; stageType: string; features?: string[]; description?: string; stageLimit?: number }) =>
  api.post<{ success: boolean; data: RecruitmentStage }>('/stages/', payload).then((r) => r.data.data);

export const updateStage = (id: string, payload: Partial<RecruitmentStage>) =>
  api.put<{ success: boolean; data: RecruitmentStage }>(`/stages/${id}/`, payload).then((r) => r.data.data);

export const deleteStage = (id: string) =>
  api.delete<{ success: boolean }>(`/stages/${id}/`).then((r) => r.data);

// 2026-07-03: BE expose POST /stages/{id}/disable/ 和 /enable/ (@action),
//   旧 PUT /stages/{id}/status/ 路径不存在 → 404.
export const disableStage = (id: string) =>
  api.post<{ success: boolean; data: RecruitmentStage }>(`/stages/${id}/disable/`, {}).then((r) => r.data.data);

export const enableStage = (id: string) =>
  api.post<{ success: boolean; data: RecruitmentStage }>(`/stages/${id}/enable/`, {}).then((r) => r.data.data);

// ===== 流程-阶段 link =====
export const listProcessLinks = (processId: string) =>
  api.get('/process-stage-links/', { params: { processId } }).then((r) => unwrap(r)) as unknown as Promise<ProcessStageLink[]>;

export const addProcessLink = (payload: { processId: string; stageId: string; orderIndex?: number; customName?: string; stageLimit?: number }) =>
  api.post<{ success: boolean; data: ProcessStageLink }>('/process-stage-links/', payload).then((r) => r.data.data);

export const updateProcessLink = (id: string, payload: Partial<ProcessStageLink>) =>
  api.put<{ success: boolean; data: ProcessStageLink }>(`/process-stage-links/${id}/`, payload).then((r) => r.data.data);

export const deleteProcessLink = (id: string) =>
  api.delete<{ success: boolean }>(`/process-stage-links/${id}/`).then((r) => r.data);

export const reorderProcessLinks = (processId: string, orderedLinkIds: string[]) =>
  api.put<{ success: boolean }>('/process-stage-links/reorder/', { processId, orderedLinkIds }).then((r) => r.data);

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

// 列表查询 (G38 #7 阶段规则 / #5 进入条件)
export const listStageRules = (params: { linkId: string }) =>
  api.get<{ success: boolean; data: StageRule[] }>('/recruitment-rules/stage-rules', { params }).then((r) => r.data.data)

export const listEntryConditions = (params: { linkId: string }) =>
  api.get<{ success: boolean; data: EntryCondition[] }>('/recruitment-rules/entry-conditions', { params }).then((r) => r.data.data)

// 候选人上下文评估 (G10 + G1.5) - 替代 raw fetch
export const evaluateCandidateForStage = (candidateId: string, entryConditionId: string, applicationId?: string) =>
  api.post<{ success: boolean; data: { passed: boolean; failedItems: any[]; prompt: string | null } }>(
    '/recruitment-rules/candidates/' + candidateId + '/evaluate',
    { entryConditionId, applicationId }
  ).then((r) => r.data.data)

export const checkApplicationStageTransition = (applicationId: string, entryConditionId?: string) =>
  api.post<{ success: boolean; data: { allowed: boolean; reason?: string; prompt?: string } }>(
    '/recruitment-rules/applications/' + applicationId + '/check-stage-transition',
    { entryConditionId }
  ).then((r) => r.data.data)

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
  listStages, createStage, updateStage, deleteStage, disableStage, enableStage,
  listProcessLinks, addProcessLink, updateProcessLink, deleteProcessLink, reorderProcessLinks,
  upsertStageRule, upsertEntryCondition, evaluateEntryCondition, listStageRules, listEntryConditions,
  evaluateCandidateForStage, checkApplicationStageTransition,
  listRounds, createRound, updateRound, updateRoundStatus,
};

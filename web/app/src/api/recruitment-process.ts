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
  // 2026-08-17: BE 用 is_builtin, 旧 FE 字段 isSystem 已废弃. reference_count 替代 _count.links.
  isBuiltin?: boolean;
  // 兼容旧代码 / 测试数据
  isSystem?: boolean;
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
  // 2026-08-17: 功能项. BE 输出 defaultFeatures + optionalFeatures, 同时用 features 映射 defaultFeatures.
  features?: string[];
  defaultFeatures?: string[];
  optionalFeatures?: string[];
  referenceCount?: number;
  _count?: { links: number };
}

/// 流程-阶段 link（每个流程包含哪些阶段 + 顺序 + 规则）
export interface ProcessStageLink {
  id: string;
  processId: string;
  stageId: string;
  // 2026-07-03: 改 orderIndex → order 对齐 BE ProcessStageLinkSerializer.fields
  //   (apps/django/apps/process/serializers.py:213). FE 之前发 'orderIndex' 经
  //   drf-camel-case 转 'order_index', BE 收到未知字段静默丢弃, 落到 model default order=0.
  order: number;
  customName?: string;
  // 2026-07-03 BR-001: isStart/isEnd 已从 link 移到 stage 自身, 此处删除
  stageLimit?: number;
  status: 'ACTIVE' | 'INACTIVE';
  stage: RecruitmentStage;
  // 2026-07-08: BE StageRule/EntryCondition 嵌套在 ProcessStageLink 下, 旧字段名 rule/condition 已废弃.
  //   BE StageRuleSerializer.Meta.fields 含 stageRule (OneToOne nested), 同理 entryCondition.
  stageRule?: StageRule | null;
  entryCondition?: EntryCondition | null;
}

export interface StageRule {
  id: string;
  link?: string;
  stageId?: string;
  processId?: string;
  autoAdvanceType: 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS';
  autoAdvanceTiming: 'NONE' | 'IMMEDIATE' | 'DELAYED';
  autoAdvanceDays?: number;
  // 2026-09-02: 计划中字段 (BE 暂未落地，UI 显示恒为「未开启」——保持类型可选避免 UI 报错)
  autoSkipNPlusTwo?: boolean;
  defaultHandlerType: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM';
  defaultHandlerFields?: string[];
  defaultHandlerUserIds?: string[];
  timeLimit?: number;
  timeLimitScope: 'NEW_ONLY' | 'ALL';
  interviewRoundIds?: string[];
  // 2026-07-08: BE StageRule 新增字段 (apps/process/models.py:260 StageRule model):
  //   inherit_prior_consensus / is_grab_mode / grab_threshold / interview_format
  inheritPriorConsensus?: boolean;
  isGrabMode?: boolean;
  grabThreshold?: number;
  interviewFormat?: string;
  interviewRounds?: number;
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

export const getProcessLink = (linkId: string) =>
  api.get(`/process-stage-links/${linkId}/`).then((r) => unwrap(r)) as unknown as Promise<ProcessStageLink>;

// 2026-07-03: 字段名 orderIndex? → order?, 跟 BE ProcessStageLinkSerializer 字段对齐.
//   BE 收到 'order_index' (drf-camel-case 转换) 是未知字段, ModelSerializer 静默丢弃, 落地 order=0.
//   配套: 上面 ProcessStageLink 类型同步改 orderIndex → order.
export const addProcessLink = (payload: { processId: string; stageId: string; order?: number; customName?: string; stageLimit?: number }) =>
  api.post<{ success: boolean; data: ProcessStageLink }>('/process-stage-links/', payload).then((r) => r.data.data);

export const updateProcessLink = (id: string, payload: Partial<ProcessStageLink>) =>
  api.put<{ success: boolean; data: ProcessStageLink }>(`/process-stage-links/${id}/`, payload).then((r) => r.data.data);

export const deleteProcessLink = (id: string) =>
  api.delete<{ success: boolean }>(`/process-stage-links/${id}/`).then((r) => r.data);

// 2026-07-03: BE @action(detail=False, methods=['post'], url_path='reorder') (views.py:333)
//   旧 FE 调 PUT /process-stage-links/reorder/ → 405 Method Not Allowed
//   Body: { "process_id": "...", "order": [{"link_id": "...", "order": 1}, ...] }
export const reorderProcessLinks = (processId: string, orderedLinkIds: string[]) =>
  api.post<{ success: boolean }>('/process-stage-links/reorder/', {
    process_id: processId,
    order: orderedLinkIds.map((linkId, idx) => ({ link_id: linkId, order: idx + 1 })),
  }).then((r) => r.data);

// ===== 阶段规则 + 进入条件 =====
// 2026-07-03: 桥接到真 BE 端点
//   - StageRule: BE ModelViewSet @ /api/v1/stage-rules/ (StageRuleViewSet, models.py:260)
//     FE 之前调 /recruitment-rules/stage-rules (stub urls_stubs.py:113, 不入库) → 假数据.
//     字段名靠 drf-camel-case 双向翻译: autoAdvanceType → auto_advance_type (✓)
//   - EntryCondition: BE 没有专用 model. JSON-encode 进 ProcessStageLink.entry_rule_expression
//     (serializer.py: ProcessStageLinkSerializer.validate, JSON-encode if entry_condition 提供).
//     写入走 PATCH /api/v1/process-stage-links/{id}/, 入参 { entry_condition: {...} }.
// 2026-07-03: BE StageRule 是 OneToOne (ProcessStageLink ↔ StageRule),
//   重复 POST 同 link 会 400 "已存在". 正确做法: 先 GET ?link=X 查现有 rule,
//   有则 PUT /stage-rules/{id}/, 无则 POST. (FE 之前走 stub 不知道这个, 现在需要做.)
export const upsertStageRule = async (linkId: string, payload: Partial<StageRule> & { processId?: string }) => {
  const list = await api.get<{ success: boolean; data: any[] }>('/stage-rules/', { params: { link: linkId } })
    .then((r) => unwrap(r) as any[]);
  const existing = Array.isArray(list) ? list.find((r) => r.link === linkId) : null
  if (existing?.id) {
    // 2026-07-03: BE StageRuleSerializer.Meta.fields 包含 'link' (OneToOne FK, 非 nullable),
    //   PUT 走 full validation, 不传 link → 400 "该字段是必填项". 即便 instance 上 link 已有,
    //   DRF 仍要入参里再传一次. POST 分支 { link: linkId, ...payload } 是正确的, PUT 分支之前漏了.
    return api.put<{ success: boolean; data: StageRule }>(`/stage-rules/${existing.id}/`, { link: linkId, ...payload })
      .then((r) => unwrap(r) as StageRule)
  }
  return api.post<{ success: boolean; data: StageRule }>('/stage-rules/', { link: linkId, ...payload })
    .then((r) => unwrap(r) as StageRule)
}

// FE StageRule 接口没有 link 字段, 但 BE StageRuleSerializer 要求 (OneToOne FK).
// 调用方需显式传 linkId (从 ProcessStageLink.id 拿). 新建规则时 link 可为全新空 link,
// 但通常先 addProcessLink 拿到 linkId, 再 upsertStageRule.

// 列表查询 (G38 #7 阶段规则 / #5 进入条件)
// 2026-07-08: 改用真实 endpoint /stage-rules/?link=X (跟 upsertStageRule 一致).
//   之前 /recruitment-rules/stage-rules 是 stub, GET 永远返空 list → modal 重打开看不到已配置.
export const listStageRules = (params: { linkId: string }) =>
  api.get<{ success: boolean; data: StageRule[] }>('/stage-rules/', { params: { link: params.linkId } })
    .then((r) => unwrap(r) as StageRule[])

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

/* ============================================================================
 * 阶段配置规则 — 进入条件规则（EntryConditionRuleViewSet）
 * 2026-09-07: 切换至新 viewset，根治旧 PATCH entry_condition 丢数据 bug（R6）。
 * 旧 upsertEntryCondition / listEntryConditions 已标记 @deprecated（见下方）。
 * ========================================================================== */
export const listEntryConditionRules = (params: { linkId: string }) =>
  api
    .get<{ success: boolean; data: any[] }>('/entry-condition-rules/', { params: { link: params.linkId } })
    .then((r) => unwrap(r) as any[])

export const createEntryConditionRule = (payload: Record<string, any>) =>
  api.post<{ success: boolean; data: any }>('/entry-condition-rules/', payload).then((r) => unwrap(r) as any)

export const updateEntryConditionRule = (id: string, payload: Record<string, any>) =>
  api.put<{ success: boolean; data: any }>(`/entry-condition-rules/${id}/`, payload).then((r) => unwrap(r) as any)

export const deleteEntryConditionRule = (id: string) =>
  api.delete<{ success: boolean; data: any }>(`/entry-condition-rules/${id}/`).then((r) => unwrap(r) as any)

export const toggleEntryConditionRule = (id: string) =>
  api.post<{ success: boolean; data: any }>(`/entry-condition-rules/${id}/toggle/`).then((r) => unwrap(r) as any)

export const reorderEntryConditionRules = (ruleOrders: { id: string; rule_seq: number }[]) =>
  api.post<{ success: boolean; data: any }>('/entry-condition-rules/reorder/', { rules: ruleOrders }).then((r) => unwrap(r) as any)

export const evaluateEntryConditionRule = (payload: Record<string, any>) =>
  api.post<{ success: boolean; data: any }>('/entry-condition-rules/evaluate/', payload).then((r) => unwrap(r) as any)

/* 字段字典：后端 GET /api/v1/expressions/fields 实现中，前端先 mock 兜底。
 * 后端就绪后移除 mock 分支即可（字段名已对齐后端真实解析映射）。 */
export const listEntryConditionFields = async (): Promise<any> => {
  try {
    return await api.get<{ success: boolean; data: any }>('/expressions/fields').then((r) => unwrap(r) as any)
  } catch {
    // 临时 mock 兜底（见 stage-rule/constants.ts AR_FIELD_CATALOG）
    return AR_FIELD_CATALOG_FALLBACK
  }
}

export const validateExpressionApi = (expression: string, maxId: number) =>
  api
    .post<{ success: boolean; data: { valid: boolean; error?: string } }>('/expressions/validate', {
      expression,
      max_id: maxId,
    })
    .then((r) => r.data.data)

/* 临时 mock 字段字典（与 stage-rule/constants.ts 同源，避免循环依赖直接内联最小结构） */
const AR_FIELD_CATALOG_FALLBACK = {
  sources: [
    {
      source: 'DEMAND',
      label: '需求中',
      fields: [
        { field: 'DEMAND_LEVEL', label: '需求职级', operators: ['EQ', 'NEQ', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY'] },
        { field: 'HIRING_MANAGER', label: '用人经理', operators: ['EQ', 'NEQ', 'IN'], auto_filter_inactive_users: true },
        { field: 'DEPARTMENT', label: '需求部门', operators: ['EQ', 'IN', 'NOT_IN'] },
      ],
    },
    {
      source: 'CANDIDATE',
      label: '候选人中',
      fields: [
        { field: 'AGE', label: '年龄', operators: ['EQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'] },
        { field: 'GENDER', label: '性别', operators: ['EQ', 'NEQ', 'IN'] },
        { field: 'HIGHEST_EDU', label: '最高学历', operators: ['EQ', 'NEQ', 'IN', 'NOT_IN'] },
        { field: 'WORK_YEARS', label: '工作年限', operators: ['EQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'] },
        { field: 'CURRENT_CITY', label: '当前城市', operators: ['EQ', 'IN', 'NOT_IN'] },
        { field: 'EXPECTED_CITY', label: '期望城市', operators: ['EQ', 'IN', 'NOT_IN'] },
      ],
    },
    {
      source: 'STAGE_STATUS',
      label: '阶段状态',
      fields: [
        { field: 'stage_name', label: '阶段名称', operators: ['EQ', 'NEQ', 'IN'] },
        { field: 'stage_statuses', label: '阶段状态', operators: ['IN', 'NOT_IN'], is_array: true },
      ],
    },
  ],
  operators: {
    EQ: '等于', NEQ: '不等于', GT: '大于', GTE: '大于等于', LT: '小于', LTE: '小于等于',
    BETWEEN: '区间', IN: '属于', NOT_IN: '不属于', IS_EMPTY: '为空', IS_NOT_EMPTY: '不为空',
  },
}

/* ============================================================================
 * @deprecated 旧进入条件 API（走 PATCH /process-stage-links/{id}/ entry_condition JSON）
 *   已被 EntryConditionRuleViewSet 全套替代，待旧数据迁移完成后删除（spec commit 9）。
 *   保留仅为旧引用兼容，新代码请勿调用。
 * ========================================================================== */
/**
 * @deprecated 2026-09-07 起废弃：进入条件已切到 EntryConditionRuleViewSet。
 * 用 listEntryConditionRules / createEntryConditionRule / updateEntryConditionRule / deleteEntryConditionRule 代替。
 */
export const upsertEntryCondition = (
  linkId: string,
  payload: {
    matchType: 'ALL' | 'ANY'
    conditionType: 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED'
    prompt?: string
    items: ConditionItem[]
  },
) =>
  api.patch<{ success: boolean; data: ProcessStageLink }>(`/process-stage-links/${linkId}/`, {
    entry_condition: payload,
  }).then((r) => unwrap(r) as ProcessStageLink)

/**
 * @deprecated 2026-09-07 起废弃：改用 listEntryConditionRules（走 viewset）。
 */
export const listEntryConditions = async (params: { linkId: string }): Promise<EntryCondition[]> => {
  const link = (await getProcessLink(params.linkId)) as any
  return link?.entryCondition ? [link.entryCondition] : []
}

export default {
  listProcesses, getProcess, createProcess, updateProcess, deleteProcess, copyProcess, updateProcessStatus,
  listStages, createStage, updateStage, deleteStage, disableStage, enableStage,
  listProcessLinks, addProcessLink, updateProcessLink, deleteProcessLink, reorderProcessLinks,
  upsertStageRule, listStageRules,
  evaluateCandidateForStage, checkApplicationStageTransition,
  listRounds, createRound, updateRound, updateRoundStatus,
  // 2026-09-07 新增：进入条件规则 viewset 全套
  listEntryConditionRules, createEntryConditionRule, updateEntryConditionRule, deleteEntryConditionRule,
  toggleEntryConditionRule, reorderEntryConditionRules, evaluateEntryConditionRule,
  listEntryConditionFields, validateExpressionApi,
};

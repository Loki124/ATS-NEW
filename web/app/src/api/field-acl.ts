import type { ApiEnvelope } from '../utils/envelope'
// G8/G43 - 字段级 ACL 前端 API 客户端
// 模式跟 src/api/referral.ts 一致: 自管 axios 实例, 不依赖不存在的 base 文件
import { api } from '../utils/request'

// ===== 类型定义 =====

/**
 * 字段可见性三态 —— **只用后端代码枚举**，与 `apps/field_acl/models.py` 的
 * `FieldPermission.choices` 严格一一对应（READ / MASK / NONE）。
 *
 * 🔴 为什么废弃旧的 `FieldAclAction`（'VIEW'|'MASK'|'HIDE'）：那套词汇只存在于
 * 后端 `permission_to_action` 的过渡映射里，模型与脱敏引擎从不使用它。
 * 两套词汇并存时，管理员能选出一个后端根本不认的值，表现为"保存了但没生效" ——
 * 静默失败，且极难排查。**本文件禁止再出现 VIEW / HIDE 字面量。**
 *
 * 过渡期说明：后端 `GET /field-acl/matrix` 同时返回 `permission`（权威）与
 * `action`（旧词汇），旧前端读 `action`、新前端读 `permission`，下批删 `action`。
 */
export type PermissionCode = 'READ' | 'MASK' | 'NONE';

/**
 * 用户可见文案（唯一真源，禁止在组件内内联中文）。
 * 口径见 AGENTS.md R-204「动词+宾语」与设计文档 §6.1 枚举与文案口径表。
 */
export const PERMISSION_TEXT: Record<PermissionCode, string> = {
  READ: '可读',
  MASK: '脱敏可见',
  NONE: '不可见',
};

/**
 * 从严顺序（对齐后端 `enforcement._SEVERITY` 与 `FieldAclService._get_field_permission`：
 * 命中多条规则时 NONE > MASK > READ）。
 * 用于前端展示"该角色在多个来源下最终生效的严格值"，避免用户困惑于
 * "我配了 READ 为什么还是脱敏"——那是列级数据权限从严叠加的结果。
 */
export const PERMISSION_SEVERITY: Record<PermissionCode, number> = {
  READ: 0,
  MASK: 1,
  NONE: 2,
};

/** 从严归约：多个来源（角色规则 / 默认清单）合成最终生效值。 */
export function strictestPermission(codes: PermissionCode[]): PermissionCode {
  if (codes.length === 0) return 'READ';
  return codes.reduce((a, b) => (PERMISSION_SEVERITY[b] > PERMISSION_SEVERITY[a] ? b : a));
}

export interface FieldAclRule {
  id: string;
  resource: string;
  field: string;
  /**
   * 权威值：后端代码枚举 READ/MASK/NONE。
   *
   * P2-1（2026-10-14）起 rules 列表与 matrix 同口径双返回；此前本字段缺失，
   * 前端只能读旧词汇 `action`，GET→PUT 往返必 400（PUT 只认代码枚举）。
   */
  permission: PermissionCode;
  /** 旧前端词汇，仅为过渡保留；新代码请读 `permission`（见类型注释）。 */
  action?: string;
  roleId?: string | null;
  roleCode?: string | null;
  maskPattern?: string | null;
  priority: number;
  description?: string | null;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

/** matrix 单个格子：permission 为权威值，action 为过渡字段（下批删）。 */
export interface FieldAclMatrixCell {
  permission: PermissionCode;
  action?: string;
}

export type FieldAclMatrix = {
  [resource: string]: {
    [field: string]: { [roleCode: string]: FieldAclMatrixCell | PermissionCode };
  };
};

/** 后端下发的可配实体目录（`GET /field-acl/catalog`）。
 * 字段清单由后端给，前端**不自建** —— 自建就会与
 * `FieldAclService.DEFAULT_SENSITIVE_FIELDS` 漂移，出现"能选但永不命中"的死字段。
 */
export interface AclEntityMeta {
  label: string;
  fields: string[];
  /** 该实体下未配规则时默认脱敏的字段全集（用于打「默认脱敏」标记）。 */
  defaultMasked: string[];
}

export type AclCatalog = Record<string, AclEntityMeta>;

/** 批量影响预览/ 落库的请求体。 */
export interface AclBatchBody {
  mode: 'by_role' | 'by_entity';
  roleCode?: string;
  entity?: string;
  items: Array<{ field: string; permission: PermissionCode }>;
}

export interface AclBatchResult {
  dryRun: boolean;
  affectedRoles: number;
  affectedFields: number;
  affectedEntities: number;
  willCreate: number;
  willUpdate: number;
  created?: number;
}

/** 写接口返回的单条规则。 */
export interface FieldAclRuleWriteResult {
  id: string;
  entity: string;
  field: string;
  roleCode: string;
  permission: PermissionCode;
}

export interface FieldAclAudit {
  id: string;
  userId: string;
  userName: string;
  resource: string;
  field: string;
  action: string;
  result: 'ALLOW' | 'MASKED' | 'HIDDEN';
  targetId?: string | null;
  ip?: string | null;
  ua?: string | null;
  createdAt: string;
}

// ===== API =====

export const fetchAclMatrix = () =>
  api.get<ApiEnvelope<FieldAclMatrix>>('/field-acl/matrix/').then(r => r.data.data);

/** 可配实体与字段清单（后端唯一真源）。 */
export const fetchAclCatalog = () =>
  api.get<ApiEnvelope<AclCatalog>>('/field-acl/catalog/').then(r => r.data.data);

export const listAclRules = (params?: { resource?: string; roleCode?: string }) =>
  api.get<ApiEnvelope<FieldAclRule[]>>('/field-acl/rules/', { params }).then(r => r.data.data);

/** upsert 单条 ACL（PUT幂等）；命中已有三元组则更新，否则新建。
 *
 * ⚠️ 用 `PUT /field-acl/rules`（三元组定位），不是 `POST /rules/{id}`：
 * ACL 的唯一键是 (entity, field, role_code)，没有单条 pk 语义。
 * 后端路由 `url_path='rules'` 上挂了 GET/PUT/DELETE 三个方法
 * （必须同一个 @action，见 field_acl/views.py 的注释：DRF 命中首条即止）。
 */
export const upsertAclRule = (rule: {
  entity: string; field: string; roleCode: string; permission: PermissionCode;
}) =>
  api.put<ApiEnvelope<FieldAclRuleWriteResult>>('/field-acl/rules/', rule)
    .then(r => r.data.data);

/** 删除单条 ACL（按三元组定位，无需先查id）。
 *
 * ⚠️ DELETE 带 body 必须用 `api.request({ method:'DELETE', data })` ——
 * `api.delete(url, { data })` 的第二参是 config，语义不同易踩坑。
 * 幂等：删不存在的规则返回 200 + deleted:0，故「撤销」流程可无脑重放。
 */
export const deleteAclRule = (rule: { entity: string; field: string; roleCode: string }) =>
  api.request({
    url: '/field-acl/rules/', method: 'DELETE', data: rule,
  }).then(r => r.data.data);

/** 批量影响预览（dryRun=true 不落库，前端批量操作前必须先调）。
 * 「影响范围」数字只能来自后端，前端自行推算会漏掉列级叠加与跨实体影响。
 */
export const previewAclBatch = (body: AclBatchBody) =>
  api.post<ApiEnvelope<AclBatchResult>>('/field-acl/rules/batch/', { ...body, dryRun: true })
    .then(r => r.data.data);

export const applyAclBatch = (body: AclBatchBody) =>
  api.post<ApiEnvelope<AclBatchResult>>('/field-acl/rules/batch/', { ...body, dryRun: false })
    .then(r => r.data.data);

export const queryAclAudit = (params?: { userId?: string; resource?: string; field?: string; limit?: number }) =>
  api.get<ApiEnvelope<FieldAclAudit[]>>('/field-acl/audit/', { params }).then(r => r.data.data);

export default api;
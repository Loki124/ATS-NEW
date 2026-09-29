/**
 * management-unit.ts — V2 管理单元 API 客户端 (T19, 方案 A 增强 2026-09-15)
 *
 * 后端端点: GET/POST/PUT/DELETE /api/v1/management-units/
 *           GET /api/v1/management-units/tree/          (按 parent_id 嵌套树)
 *           POST /api/v1/management-units/{id}/sync-data-rules/  (同步到 DataPermissionRule)
 * 响应格式: { success: boolean, data: ManagementUnit | ManagementUnit[] | TreeNode[] }
 *
 * 管理单元: 数据权限范围的载体 (组织维度)
 * - org_scope JSON 字段 (具体哪些组织 ID / path)
 * - include_children 1/0 (是否包含子级, 对应 DEPT_AND_SUB 数据范围)
 * - parent_id (方案 A: 树形层级)
 * - personnel_scope JSON 谓词 (方案 A: 人员范围动态条件)
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export interface ManagementUnit {
  id: string;
  systemCode: string;
  unitName: string;
  unitType: string;
  parentId?: string | number | null;
  code?: string | null;
  description?: string | null;
  displayOrder?: number;
  orgScope?: Array<{ deptId: string; includeChildren: boolean }> | Record<string, any> | null;
  personnelScope?: Record<string, any> | null;
  dataRange?: Record<string, any> | null;
  orgScopes?: Record<string, Array<{ deptId: string; includeChildren: boolean }>> | null;
  dataRanges?: Record<string, any> | null;
  /** 单元级人员数据范围（public 应用回退源） */
  personDataRange?: Record<string, any> | null;
  /** 按应用人员数据范围 {app_code: range}, 缺省回退 unit 级 personDataRange */
  personDataRanges?: Record<string, any> | null;
  /** 按应用组织范围是否启用 {app_code: bool}, 缺省启用 */
  orgScopeEnabled?: Record<string, boolean> | null;
  /** 按应用人员范围是否启用 {app_code: bool}, 缺省启用 */
  personScopeEnabled?: Record<string, boolean> | null;
  includeChildren: number;
  status: number;
  createdAt?: string;
  updatedAt?: string;
}

/** tree 端点返回节点 (camelCase, 含 children 嵌套) */
export interface ManagementUnitTreeNode {
  id: string;
  unitName: string;
  unitType: string;
  parentId: string | number | null;
  status: number;
  code?: string | null;
  description?: string | null;
  displayOrder?: number;
  orgScope?: Record<string, any> | null;
  personnelScope?: Record<string, any> | null;
  dataRange?: Record<string, any> | null;
  personDataRange?: Record<string, any> | null;
  children: ManagementUnitTreeNode[];
}

/** sync-data-rules 返回 */
export interface SyncDataRulesResult {
  ruleId: string | null;
  effectiveUnitIds: number[];
  ruleIds?: string[];
  syncedUserCount?: number;
  dimensionValue?: string;
  scopePayload?: Record<string, any>;
}

// ===== API =====

export async function listManagementUnits(params?: { unitType?: string; status?: number }) {
  const { data } = await api.get<{ success: boolean; data: ManagementUnit[] }>(
    '/management-units/',
    { params },
  );
  return data.data ?? [];
}

export async function treeManagementUnits() {
  const { data } = await api.get<{ success: boolean; data: ManagementUnitTreeNode[] }>(
    '/management-units/tree/',
  );
  return data.data ?? [];
}

export async function createManagementUnit(payload: Partial<ManagementUnit>) {
  const { data } = await api.post<{ success: boolean; data: ManagementUnit }>(
    '/management-units/',
    payload,
  );
  return data.data;
}

export async function updateManagementUnit(id: string, payload: Partial<ManagementUnit>) {
  // 使用 PATCH(部分更新): serializer 中 unit_name 为必填, PUT 会拒绝仅传部分字段的调用
  // (如按应用保存 orgScopes/dataRanges、批量停用仅传 {status:0}), 改为 PATCH 后这些调用均生效.
  const { data } = await api.patch<{ success: boolean; data: ManagementUnit }>(
    `/management-units/${id}/`,
    payload,
  );
  return data.data;
}

export async function deleteManagementUnit(id: string) {
  const { data } = await api.delete<{ success: boolean; message?: string }>(`/management-units/${id}/`);
  return data;
}

export async function syncManagementUnitRules(id: string) {
  const { data } = await api.post<{ success: boolean; data: SyncDataRulesResult }>(
    `/management-units/${id}/sync-data-rules/`,
  );
  return data.data;
}

export interface ManagementUnitMember {
  id: string;
  unitId: string;
  memberType: 'DEPT' | 'USER' | 'PERSON';
  departmentId: string | null;
  userId: number | null;
  personId: string | null;
  appCode?: string | null;
  includeChildren: number;
  remark: string | null;
  status: number;
  createdAt: string;
  updatedAt: string;
  departmentName?: string;
  userName?: string;
  personName?: string;
}

export function listManagementUnitMembers(unitId: string | number) {
  return api.get<{success:boolean;data:ManagementUnitMember[]}>(`/management-units/${unitId}/members/`).then(r => r.data.data ?? []);
}

export function addManagementUnitMember(unitId: string | number, payload: Partial<ManagementUnitMember> & { memberType: 'DEPT'|'USER'|'PERSON' }) {
  return api.post<{success:boolean;data:ManagementUnitMember}>(`/management-units/${unitId}/members/`, payload).then(r => r.data.data);
}

export function removeManagementUnitMember(unitId: string | number, memberId: string) {
  return api.delete<{success:boolean;data:null}>(`/management-units/${unitId}/members/${memberId}/`).then(r => r.data);
}

export function updateManagementUnitMember(unitId: string | number, memberId: string, payload: { includeChildren?: number; remark?: string }) {
  return api.put<{success:boolean;data:ManagementUnitMember}>(`/management-units/${unitId}/members/${memberId}/`, payload).then(r => r.data.data);
}

export interface ResolvedPerson {
  id: number | string;
  name: string;
  email: string;
  departmentId: string | null;
  departmentName: string;
}

/** 需求 E：基于 person_data_range 部门条件解析出实际相关人员(系统用户)列表，纯只读 */
export function listResolvedPersons(unitId: string | number, appCode?: string | null) {
  const qs = appCode ? `?app_code=${encodeURIComponent(appCode)}` : '';
  return api.get<{success:boolean;data:ResolvedPerson[];message?:string}>(`/management-units/${unitId}/resolved-persons/${qs}`).then(r => r.data);
}

export default api;

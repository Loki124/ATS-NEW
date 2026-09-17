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
  const { data } = await api.put<{ success: boolean; data: ManagementUnit }>(
    `/management-units/${id}/`,
    payload,
  );
  return data.data;
}

export async function deleteManagementUnit(id: string) {
  const { data } = await api.delete<{ success: boolean }>(`/management-units/${id}/`);
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

export default api;

// 数据权限管理前端 API 客户端（统一行级 + 列级，按 角色/部门/用户 维度）
// 模式与 src/api/field-acl.ts 一致: 自管 axios 实例, 不依赖不存在的 base 文件

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

// ===== 类型定义（与后端 DataPermissionRule  camelCase 契约对应）=====

export type DimensionType = 'ROLE' | 'DEPARTMENT' | 'USER';
export type RuleLevel = 'ROW' | 'COLUMN';
export type RowScopeType = 'ALL' | 'DEPT' | 'DEPT_AND_SUB' | 'SELF' | 'CUSTOM';
export type ColumnPermission = 'READ' | 'MASK' | 'NONE';

export interface DataPermissionRule {
  id: string;
  dimensionType: DimensionType;
  dimensionValue: string;
  level: RuleLevel;
  scopeType?: RowScopeType | null;
  scopePayload?: Record<string, unknown> | null;
  entity?: string | null;
  field?: string | null;
  permission?: ColumnPermission | null;
  priority: number;
  status: number; // 1 启用 / 0 停用
  remark?: string | null;
  createdBy?: number | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface OptionItem {
  value: string;
  label: string;
}

export interface DataPermissionOptions {
  dimension_types: OptionItem[];
  levels: OptionItem[];
  row_scopes: OptionItem[];
  column_permissions: OptionItem[];
}

// ===== API =====

export const listRules = (params?: {
  dimensionType?: string;
  dimensionValue?: string;
  level?: string;
}) =>
  api.get<{ success: boolean; data: DataPermissionRule[] }>('/data-permissions/', { params })
    .then(r => r.data.data ?? []);

export const createRule = (rule: Partial<DataPermissionRule>) =>
  api.post<{ success: boolean; data: DataPermissionRule }>('/data-permissions/', rule)
    .then(r => r.data.data);

export const updateRule = (id: string, rule: Partial<DataPermissionRule>) =>
  api.patch<{ success: boolean; data: DataPermissionRule }>(`/data-permissions/${id}/`, rule)
    .then(r => r.data.data);

export const deleteRule = (id: string) =>
  api.delete<{ success: boolean }>(`/data-permissions/${id}/`).then(r => r.data);

export const fetchOptions = () =>
  api.get<{ success: boolean; data: DataPermissionOptions }>('/data-permissions/options/')
    .then(r => r.data.data);

// 维度候选值（角色 / 部门 / 用户）—— 复用现有端点，加载失败不影响主流程
const unwrap = (r: any): any[] => {
  const d = r?.data?.data ?? r?.data ?? [];
  return Array.isArray(d) ? d : [];
};

export const listRoles = () =>
  api.get('/roles/').then(r => unwrap(r).map((x: any) => ({
    value: String(x.roleCode ?? x.role_code ?? x.code ?? x.id),
    label: x.roleName ?? x.role_name ?? x.name ?? x.roleCode ?? x.code ?? String(x.id),
  }))).catch(() => []);

export const listDepartments = () =>
  api.get('/departments/').then(r => unwrap(r).map((x: any) => ({
    value: String(x.id),
    label: x.name ?? x.deptName ?? x.departmentName ?? String(x.id),
  }))).catch(() => []);

export const listUsers = () =>
  api.get('/users/').then(r => unwrap(r).map((x: any) => ({
    value: String(x.id),
    label: x.realName ?? x.fullName ?? x.username ?? x.employeeId ?? String(x.id),
  }))).catch(() => []);

export default api;

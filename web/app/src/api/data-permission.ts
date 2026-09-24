/**
 * data-permission.ts — 角色数据权限（数据权限向导）API 客户端
 *
 * 后端端点:
 *   GET    /api/v1/roles/{id}/data-permissions/          读取某角色 5 模块配置
 *   POST   /api/v1/roles/{id}/data-permissions/          一次性保存 5 模块
 *   GET    /api/v1/roles/{id}/data-permissions/options/  模块×维度矩阵 + 维度值选项
 *
 * 响应格式: { success: boolean, data: ... }
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

export type DataPermMode = 'none' | 'all' | 'scope';
export type Operator = 'in' | 'not_in';

export interface PermValue {
  id: string | number;
  label: string;
  stale?: boolean;
}

export interface PermCondition {
  id: string;
  dimension: string;
  operator: Operator;
  values: PermValue[];
}

export interface PermConditionGroup {
  id: string;
  expr: string;
  conditions: PermCondition[];
}

export interface ModulePerm {
  moduleKey: string;
  mode: DataPermMode;
  expr: string;
  groups: PermConditionGroup[];
  featureGranted: boolean;
}

export interface RoleDataPermPayload {
  roleId: string;
  modules: ModulePerm[];
}

export interface DimensionMeta {
  key: string;
  label: string;
  valueType: string;
  options: PermValue[];
}

export interface ModuleOption {
  moduleKey: string;
  label: string;
  dimensions: DimensionMeta[];
}

// ===== API =====

export async function getRoleDataPerm(roleId: string): Promise<{ modules: ModulePerm[]; roleCode: string }> {
  const res = await api.get(`/roles/${roleId}/data-permissions/`);
  const data = res.data?.data || { roleId, roleCode: '', modules: [] };
  return { modules: data.modules || [], roleCode: data.roleCode || '' };
}

export async function saveRoleDataPerm(
  roleId: string,
  payload: RoleDataPermPayload,
): Promise<{ modules: ModulePerm[] }> {
  const res = await api.post(`/roles/${roleId}/data-permissions/`, payload);
  const data = res.data?.data || { modules: [] };
  return { modules: data.modules || [] };
}

export async function getRoleDataPermOptions(roleId: string): Promise<ModuleOption[]> {
  const res = await api.get(`/roles/${roleId}/data-permissions/options/`);
  const data = res.data?.data || { modules: [] };
  return data.modules || [];
}

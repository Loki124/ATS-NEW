/**
 * user-role-v2.ts — V2 用户角色授权 API 客户端 (T19)
 *
 * 后端端点: GET/POST/PUT/DELETE /api/v1/user-roles/
 *           GET /api/v1/user-roles/suggest-scope/?user_id=X&role_code=Y
 * 响应格式: { success: boolean, data: UserRoleV2 | UserRoleV2[] | SuggestScopeResult }
 *
 * V2 vs V1:
 * - role_code 字符串 (替代 FK, 跨系统灵活)
 * - management_unit_ids JSON 字段 (数据权限范围载体)
 * - valid_from / valid_to (角色有效期)
 * - suggest-scope action: 根据用户角色推荐管理单元
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

export interface UserRoleV2 {
  id: string;
  userId: number | string;
  roleCode: string;
  systemCode: string;
  managementUnitIds?: number[] | null;
  validFrom?: string | null;
  validTo?: string | null;
  grantedById?: number | null;
  grantedAt?: string;
  updatedAt?: string;
}

export interface SuggestScopeResult {
  suggestedUnitIds: number[];
  derivedFrom: string;
  rationale: string;
}

// ===== API =====

export async function listUserRoles(params?: { userId?: number | string; roleCode?: string; systemCode?: string }) {
  const { data } = await api.get<{ success: boolean; data: UserRoleV2[] }>('/user-roles/', { params });
  return data.data ?? [];
}

export async function createUserRole(payload: Partial<UserRoleV2>) {
  const { data } = await api.post<{ success: boolean; data: UserRoleV2 }>('/user-roles/', payload);
  return data.data;
}

export async function updateUserRole(id: string, payload: Partial<UserRoleV2>) {
  const { data } = await api.put<{ success: boolean; data: UserRoleV2 }>(`/user-roles/${id}/`, payload);
  return data.data;
}

export async function deleteUserRole(id: string) {
  const { data } = await api.delete<{ success: boolean }>(`/user-roles/${id}/`);
  return data;
}

/**
 * 根据用户+角色推荐数据范围 (管理单元)
 * 后端基于 scope_resolver.resolve_scope(user) 返回 L2 (角色 ALL) 或 L4 (兜底) 的建议
 */
export async function suggestScope(userId: number | string, roleCode: string) {
  const { data } = await api.get<{ success: boolean; data: SuggestScopeResult }>(
    '/user-roles/suggest-scope/',
    { params: { user_id: userId, role_code: roleCode } },
  );
  return data.data;
}

export default api;
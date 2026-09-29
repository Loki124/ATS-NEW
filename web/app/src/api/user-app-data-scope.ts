/**
 * user-app-data-scope.ts — V2 用户-角色-应用 数据范围 API 客户端 (方案 A 2026-09-15)
 *
 * 后端端点: GET/POST /api/v1/user-app-data-scopes/
 *           DELETE /api/v1/user-app-data-scopes/{id}/
 * 响应格式: { success: boolean, data: UserAppDataScope | UserAppDataScope[] }
 *
 * 设计: 按 (user_id, role_code, app_code) 维度承载管理单元数据范围,
 *       对齐北森「按应用管理单元」。scope_resolver L1 在传入 app_code 时优先读取本表,
 *       缺失则回退 UserRoleV2.management_unit_ids 全局兜底。
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export interface UserAppDataScope {
  id: string;
  userId: number | string;
  roleCode: string;
  systemCode: string;
  appCode: string;
  managementUnitIds?: number[] | null;
  grantedById?: number | null;
  grantedAt?: string;
  updatedAt?: string;
}

// ===== API =====

export async function listUserAppDataScopes(params?: {
  userId?: number | string;
  roleCode?: string;
  appCode?: string;
}) {
  const { data } = await api.get<{ success: boolean; data: UserAppDataScope[] }>(
    '/user-app-data-scopes/',
    { params },
  );
  return data.data ?? [];
}

/**
 * 按 (user_id, role_code, app_code) upsert。
 * 后端 ModelViewSet.create 内部 get_or_create + 更新 management_unit_ids。
 */
export async function upsertUserAppDataScope(payload: {
  userId: number | string;
  roleCode: string;
  appCode: string;
  systemCode?: string;
  managementUnitIds?: number[] | null;
}) {
  const { data } = await api.post<{ success: boolean; data: UserAppDataScope }>(
    '/user-app-data-scopes/',
    payload,
  );
  return data.data;
}

export async function deleteUserAppDataScopeById(id: string) {
  const { data } = await api.delete<{ success: boolean }>(`/user-app-data-scopes/${id}/`);
  return data;
}

export default api;

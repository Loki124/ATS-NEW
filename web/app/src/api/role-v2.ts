import type { ApiEnvelope } from '../utils/envelope'
/**
 * role-v2.ts — V2 角色 (RoleV2) API 客户端 (T19)
 *
 * 后端端点: GET/POST/PUT/DELETE /api/v1/roles/
 *           POST /api/v1/roles/clone-from-template/
 * 响应格式: { success: boolean, data: RoleV2 | RoleV2[] }
 *
 * V2 vs V1:
 * - V2 roles 表 db_table='roles', 无 parent_role_id (扁平结构)
 * - permission_codes 是 SerializerMethodField (从 role_permission 表聚合)
 * - 通过 template_code 复用模板
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export type DataScopeType = 'SELF' | 'DEPT' | 'DEPT_AND_SUB' | 'ALL';

export interface RoleV2 {
  id: string;
  systemCode: string;
  roleCode: string;
  roleName: string;
  templateCode?: string | null;
  defaultDataScopeType?: DataScopeType | null;
  description?: string | null;
  isSystem: number;
  status: number;
  permissionCodes: string[];
  createdAt?: string;
  updatedAt?: string;
}

// ===== API =====

export async function listRoles(params?: { status?: number; isSystem?: number; search?: string }) {
  const { data } = await api.get<ApiEnvelope<RoleV2[]>>('/roles/', { params });
  return data.data ?? [];
}

export async function createRole(payload: Partial<RoleV2>) {
  const { data } = await api.post<ApiEnvelope<RoleV2>>('/roles/', payload);
  return data.data;
}

export async function updateRole(id: string, payload: Partial<RoleV2>) {
  const { data } = await api.put<ApiEnvelope<RoleV2>>(`/roles/${id}/`, payload);
  return data.data;
}

export async function deleteRole(id: string) {
  const { data } = await api.delete<ApiEnvelope<void>>(`/roles/${id}/`);
  return data;
}

/**
 * 从模板克隆新角色
 * body: { template_code, role_code, role_name, custom_permissions?: {add, remove} }
 */
export async function cloneFromTemplate(payload: {
  templateCode: string;
  roleCode: string;
  roleName: string;
  customPermissions?: { add?: string[]; remove?: string[] };
}) {
  const { data } = await api.post<ApiEnvelope<RoleV2>>(
    '/roles/clone-from-template/',
    payload,
  );
  return data.data;
}

/**
 * 同步角色已勾选的资源码 (role_permission 表整组替换).
 *
 * T29 fix: PUT /roles/{id}/ 的 permissionCodes 是 SerializerMethodField (read-only),
 * DRF 会静默丢弃, 用户以为保存成功实际数据丢失. 此处显式走 sync-resources action.
 */
export async function syncRolePermissions(roleId: string, codes: string[]) {
  const { data } = await api.post<ApiEnvelope<RoleV2>>(
    `/roles/${roleId}/sync-resources/`,
    { resourceCodes: codes },
  );
  return data.data;
}

export default api;
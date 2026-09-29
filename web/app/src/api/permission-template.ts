/**
 * permission-template.ts — V2 权限模板 API 客户端 (T19)
 *
 * 后端端点: GET /api/v1/permissions/templates/
 * 响应格式: { success: boolean, data: PermissionTemplate[] }
 *
 * V2 设计: PermissionTemplate 是 permission_codes JSONField 列表的快照,
 *   用于快速复制到 RoleV2 (roles/clone-from-template/).
 *   列表通过 read-only 暴露, 写操作走 RoleV2.clone_from_template action.
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export interface PermissionTemplate {
  id: string;
  systemCode: string;
  templateCode: string;
  templateName: string;
  description?: string | null;
  isSystem: number;
  permissionCodes: string[];
  status: number;
}

// ===== API =====

export async function listTemplates(params?: { isSystem?: number }) {
  const { data } = await api.get<{ success: boolean; data: PermissionTemplate[] }>(
    '/permissions/templates/',
    { params },
  );
  return data.data ?? [];
}

export default api;
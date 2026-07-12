/**
 * permission-resource.ts — V2 权限资源 API 客户端 (T19)
 *
 * 后端端点: GET/POST /api/v1/permissions/resources/
 *           GET/PUT/DELETE /api/v1/permissions/resources/{id}/
 * 响应格式: { success: boolean, data: PermissionResource | results: PermissionResource[] }
 *
 * 字段命名: drf-camel-case 出 camelCase (resourceCode / resourceName / systemCode),
 *   FE 类型严格按 camelCase 写, 后端 snake_case 通过中间件自动桥接
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

export type ResourceType = 'MENU' | 'BUTTON' | 'FIELD' | 'API';

export interface PermissionResource {
  id: string;
  systemCode: string;
  resourceCode: string;
  resourceName: string;
  resourceType: ResourceType;
  parentCode?: string | null;
  module?: string | null;
  sortOrder?: number;
  status: number;
}

// ===== API =====

/**
 * 资源列表 (ReadOnlyModelViewSet, 后端过滤 status=1 默认)
 * 后端 pagination_class=None, 直接返数组, 但为兼容 interceptor 留出 results 兜底
 */
export async function listResources(params?: { module?: string; resourceType?: string; search?: string }) {
  const { data } = await api.get<{ success: boolean; data: PermissionResource[] | { results: PermissionResource[] } }>(
    '/permissions/resources/',
    { params },
  );
  const payload = data.data;
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

export async function createResource(payload: Partial<PermissionResource>) {
  const { data } = await api.post<{ success: boolean; data: PermissionResource }>(
    '/permissions/resources/',
    payload,
  );
  return data.data;
}

export async function updateResource(id: string, payload: Partial<PermissionResource>) {
  const { data } = await api.put<{ success: boolean; data: PermissionResource }>(
    `/permissions/resources/${id}/`,
    payload,
  );
  return data.data;
}

export async function deleteResource(id: string) {
  const { data } = await api.delete<{ success: boolean }>(`/permissions/resources/${id}/`);
  return data;
}

export default api;
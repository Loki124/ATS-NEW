/**
 * management-unit.ts — V2 管理单元 API 客户端 (T19)
 *
 * 后端端点: GET/POST/PUT/DELETE /api/v1/management-units/
 * 响应格式: { success: boolean, data: ManagementUnit | ManagementUnit[] }
 *
 * 管理单元: 数据权限范围的载体 (组织维度)
 * - org_scope JSON 字段 (具体哪些组织 ID / path)
 * - include_children 1/0 (是否包含子级, 对应 DEPT_AND_SUB 数据范围)
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
  orgScope?: Record<string, any> | null;
  includeChildren: number;
  status: number;
  createdAt?: string;
  updatedAt?: string;
}

// ===== API =====

export async function listManagementUnits(params?: { unitType?: string; status?: number }) {
  const { data } = await api.get<{ success: boolean; data: ManagementUnit[] }>(
    '/management-units/',
    { params },
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

export default api;
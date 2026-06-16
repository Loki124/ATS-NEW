// G8/G43 - 字段级 ACL 前端 API 客户端
// 模式跟 src/api/referral.ts 一致: 自管 axios 实例, 不依赖不存在的 base 文件

import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// ===== 类型定义 =====

export type FieldAclAction = 'VIEW' | 'MASK' | 'HIDE';

export interface FieldAclRule {
  id: string;
  resource: string;
  field: string;
  action: FieldAclAction;
  roleId?: string | null;
  roleCode?: string | null;
  maskPattern?: string | null;
  priority: number;
  description?: string | null;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export type FieldAclMatrix = {
  [resource: string]: {
    [field: string]: { [roleCode: string]: FieldAclAction };
  };
};

export interface FieldAclAudit {
  id: string;
  userId: string;
  userName: string;
  resource: string;
  field: string;
  action: FieldAclAction;
  result: 'ALLOW' | 'MASKED' | 'HIDDEN';
  targetId?: string | null;
  ip?: string | null;
  ua?: string | null;
  createdAt: string;
}

// ===== API =====

export const fetchAclMatrix = () =>
  api.get<{ success: boolean; data: FieldAclMatrix }>('/field-acl/matrix').then(r => r.data.data);

export const listAclRules = (params?: { resource?: string; roleCode?: string }) =>
  api.get<{ success: boolean; data: FieldAclRule[] }>('/field-acl/rules', { params }).then(r => r.data.data);

export const upsertAclRule = (rule: Partial<FieldAclRule>) =>
  api.post<{ success: boolean; data: FieldAclRule }>('/field-acl/rules', rule).then(r => r.data.data);

export const deleteAclRule = (id: string) =>
  api.delete<{ success: boolean }>(`/field-acl/rules/${id}`).then(r => r.data);

export const queryAclAudit = (params?: { userId?: string; resource?: string; field?: string; limit?: number }) =>
  api.get<{ success: boolean; data: FieldAclAudit[] }>('/field-acl/audit', { params }).then(r => r.data.data);

export default api;

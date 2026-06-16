// G42 - 动态字段定义 前端 API 客户端

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

export type FieldType = 'TEXT' | 'NUMBER' | 'DATE' | 'SELECT' | 'MULTISELECT' | 'BOOLEAN';

export interface FieldOption {
  id?: string;
  value: string;
  label: string;
  orderIndex?: number;
  isActive?: boolean;
}

export interface FieldDefinition {
  id: string;
  resource: string;
  fieldKey: string;
  label: string;
  fieldType: FieldType;
  isRequired: boolean;
  isVisible: boolean;
  placeholder?: string | null;
  helpText?: string | null;
  defaultValue?: string | null;
  validation?: string | null;
  orderIndex: number;
  groupName?: string | null;
  status?: string;
  options?: FieldOption[];
  createdAt?: string;
  updatedAt?: string;
}

export const listFields = (resource: string) =>
  api.get(`/dynamic-fields/${resource}/fields`).then((r) => r.data.data);

export const getField = (resource: string, key: string) =>
  api.get(`/dynamic-fields/${resource}/fields/${key}`).then((r) => r.data.data);

export const upsertField = (resource: string, body: Partial<FieldDefinition>) =>
  api.post(`/dynamic-fields/${resource}/fields`, body).then((r) => r.data.data);

export const deleteField = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/fields/${id}`).then((r) => r.data);

export const reorderFields = (resource: string, orderedIds: string[]) =>
  api.put(`/dynamic-fields/${resource}/fields/reorder`, { orderedIds }).then((r) => r.data);

export const validateValue = (resource: string, id: string, value: any) =>
  api.post(`/dynamic-fields/${resource}/fields/${id}/validate`, { value }).then((r) => r.data.data);

export const FIELD_TYPE_OPTIONS: { label: string; value: FieldType }[] = [
  { label: '文本', value: 'TEXT' },
  { label: '数字', value: 'NUMBER' },
  { label: '日期', value: 'DATE' },
  { label: '下拉单选', value: 'SELECT' },
  { label: '下拉多选', value: 'MULTISELECT' },
  { label: '布尔', value: 'BOOLEAN' },
];

export const RESOURCE_OPTIONS: { label: string; value: string }[] = [
  { label: '候选人 Candidate', value: 'Candidate' },
  { label: '需求 Demand', value: 'Demand' },
  { label: '职位 Position', value: 'Position' },
];

export default api;

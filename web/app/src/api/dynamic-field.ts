// G42 - 动态字段定义 前端 API 客户端

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
  api.get(`/dynamic-fields/${resource}/fields/`).then((r) => r.data.data);

/** detail 端点统一按 id (nanoid) 寻址, 与后端 `get_object()` 契约一致 */
export const getField = (resource: string, id: string) =>
  api.get(`/dynamic-fields/${resource}/fields/${id}/`).then((r) => r.data.data);

/**
 * 新建 / 编辑字段定义。
 *
 * 2026-08-04 修复: 原实现无论新建还是编辑都 POST 到 list 端点, 编辑时携带的
 * fieldKey 与已有记录相同 → 撞后端 unique_together → IntegrityError → HTTP 500。
 * 现按 `body.id` 是否存在区分:
 *   - 无 id → POST  /dynamic-fields/{resource}/fields/        (新建, 201)
 *   - 有 id → PUT   /dynamic-fields/{resource}/fields/{id}/   (编辑, 200)
 */
export const upsertField = (resource: string, body: Partial<FieldDefinition>) =>
  (body.id
    ? api.put(`/dynamic-fields/${resource}/fields/${body.id}/`, body)
    : api.post(`/dynamic-fields/${resource}/fields/`, body)
  ).then((r) => r.data.data);

export const deleteField = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/fields/${id}/`).then((r) => r.data);

/** 后端 reorder 端点只挂了 POST, 这里必须用 POST, 否则 405 */
export const reorderFields = (resource: string, orderedIds: string[]) =>
  api.post(`/dynamic-fields/${resource}/fields/reorder/`, { orderedIds }).then((r) => r.data);

/**
 * 单值校验。
 *
 * 注意: 后端 `apps/dynamic_field/urls.py` 目前**未挂载** `<id>/validate/` 路由,
 * 调用会得到 404。当前无调用方, 待后端补齐该端点后方可使用。
 */
export const validateValue = (resource: string, id: string, value: any) =>
  api.post(`/dynamic-fields/${resource}/fields/${id}/validate/`, { value }).then((r) => r.data.data);

/**
 * 从后端错误响应里提取可读文案。
 *
 * 后端 `custom_exception_handler` 对 DRF 校验错误统一返回
 * `{ success, code, message: '请求处理失败', errors: { fieldKey: ['...'] } }`,
 * 只读 `message` 会永远显示泛化文案, 因此优先展开 `errors` 里的字段级提示。
 */
export function extractApiError(e: any, fallback = '请求失败'): string {
  const data = e?.response?.data;
  const errors = data?.errors;

  if (errors) {
    if (typeof errors === 'string') return errors;
    const flattened = Object.values(errors)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter((v): v is string => typeof v === 'string' && v.length > 0);
    if (flattened.length) return flattened.join('; ');
  }

  return data?.message || data?.detail || e?.message || fallback;
}

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

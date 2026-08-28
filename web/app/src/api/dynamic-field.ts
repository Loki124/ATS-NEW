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
 *
 * 2026-08-28 兜底: DRF ModelSerializer 自动注入的 UniqueTogetherValidator 默认文案
 * 是「字段 X, Y, Z 必须能构成唯一集合。」, 对用户不友好。即便后端已通过
 * ControlRuleSerializer.get_validators 替换为业务文案, 这里再做一道模式归一:
 * 万一后端再加新表 unique_together 漏改文案, 前端也能屏蔽抽象错误, 转友好提示。
 */
const UNIQUE_TOGETHER_ABSTRACT_PATTERN = /必须能构成唯一集合|make a unique set/i
const UNIQUE_TOGETHER_FRIENDLY = (
  '已存在同名记录（重复键）。请先停用或删除同名的旧记录后再新建，'
  + '或调整其中任意一个关键字段（适用范围 / 维度 / 指标 / 生效年度 / 启用状态）以避免冲突。'
)

function _walk(node: unknown, visit: (v: unknown) => void): void {
  if (node == null) return
  if (typeof node === 'string') { visit(node); return }
  if (Array.isArray(node)) { node.forEach((it) => _walk(it, visit)); return }
  if (typeof node === 'object') {
    Object.values(node as Record<string, unknown>).forEach((v) => _walk(v, visit))
  }
}

function _flattenStrings(node: unknown): string {
  const out: string[] = []
  _walk(node, (v) => out.push(String(v)))
  return out.join(' ')
}

export function extractApiError(e: any, fallback = '请求失败'): string {
  const data = e?.response?.data;
  const errors = data?.errors;

  if (errors) {
    // 优先吞掉「必须能构成唯一集合」这类抽象 DRF 模板, 转业务友好文案。
    // 深度遍历 errors 任何层级的字符串字段, 命中即整体替换, 避免误过嵌套报文。
    if (UNIQUE_TOGETHER_ABSTRACT_PATTERN.test(_flattenStrings(errors))) {
      return UNIQUE_TOGETHER_FRIENDLY
    }

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

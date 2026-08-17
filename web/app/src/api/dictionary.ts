/**
 * 数据字典 API 客户端  (PR #69 — 阶段类型数据字典化)
 *
 * 后端 apps/dictionary (DictionaryType / DictionaryItem):
 *   - GET /api/v1/dictionary-items/?type_code=<code>
 *       返回该类型下所有「启用」字典项, 按 sort_order 升序.
 *   - 响应包 { success, data:[...], pagination:{...} } (StandardResultsSetPagination).
 *   - 全局 camelCase 渲染: sort_order→sortOrder, type.code→typeCode, is_active→isActive.
 *
 * 设计: 字典项是枚举的 single source of truth.
 *   阶段类型字典 code = 'recruitment_stage_type', 业务字段 stage_type 存的是 item.key
 *   (如 'SCREEN'), 展示名用 item.value (如 '筛选').
 */
import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

/** 字典项 (驼峰键, 与后端 DictionaryItemSerializer 对齐). */
export interface DictionaryItem {
  id: string;
  type: string;
  /** 所属字典类型 code (type.code). */
  typeCode: string;
  /** 字典项编码 — 业务字段实际存储的值 (如 stage_type='SCREEN'). */
  key: string;
  /** 展示名 (如 '筛选'). */
  value: string;
  sortOrder: number;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

/** naive-ui n-select 用的 option. value=业务存储值(key), label=展示名(value). */
export interface DictionaryOption {
  label: string;
  value: string;
  sortOrder?: number;
}

/** 阶段类型字典 code. */
export const STAGE_TYPE_DICT_CODE = 'recruitment_stage_type';

/**
 * 取某类型下所有启用字典项 (按 sortOrder 升序).
 * 兼容 {success,data} 包裹或裸数组两种响应形态.
 */
export async function listDictionaryItems(typeCode: string): Promise<DictionaryItem[]> {
  const resp = await api.get<{ success: boolean; data: DictionaryItem[] }>('/dictionary-items/', {
    params: { type_code: typeCode, page_size: 200 },
  });
  const body = resp.data;
  const items: DictionaryItem[] = Array.isArray(body)
    ? body
    : body && typeof body === 'object' && 'data' in body && Array.isArray((body as any).data)
      ? (body as any).data
      : [];
  return items.slice().sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0));
}

/** 字典类型 (驼峰键, 与后端 DictionaryTypeSerializer 对齐). */
export interface DictionaryType {
  id: string;
  code: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
}

/** 取所有字典类型 (按名称排序). 兼容 {success,data} 包裹或裸数组. */
export async function listDictionaryTypes(): Promise<DictionaryType[]> {
  const resp = await api.get<{ success: boolean; data: DictionaryType[] }>('/dictionary-types/', {
    params: { page_size: 200 },
  });
  const body = resp.data;
  const types: DictionaryType[] = Array.isArray(body)
    ? body
    : body && typeof body === 'object' && 'data' in body && Array.isArray((body as any).data)
      ? (body as any).data
      : [];
  return types.slice().sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
}

/** 字典项 → n-select options (value=key, label=value). */
export function toOptions(items: DictionaryItem[]): DictionaryOption[] {
  return items.map((it) => ({ label: it.value, value: it.key, sortOrder: it.sortOrder }));
}

/** 直接拉「阶段类型」可选列表. */
export async function listStageTypeOptions(): Promise<DictionaryOption[]> {
  const items = await listDictionaryItems(STAGE_TYPE_DICT_CODE);
  return toOptions(items);
}

/**
 * 新建字典类型. POST /dictionary-types/
 * 返回包兼容 {success,data} 或直接对象, 取 resp.data.data ?? resp.data.
 */
export async function createDictionaryType(payload: {
  code: string;
  name: string;
  description?: string;
}): Promise<DictionaryType> {
  const resp = await api.post<{ success: boolean; data: DictionaryType }>('/dictionary-types/', payload);
  const body = resp.data as any;
  return body?.data ?? body;
}

/**
 * 更新字典类型 (按 code). PUT /dictionary-types/<code>/
 * code 为 URL lookup, body 只含可改字段 (name / description).
 */
export async function updateDictionaryType(
  code: string,
  payload: { name: string; description?: string },
): Promise<DictionaryType> {
  const resp = await api.put<{ success: boolean; data: DictionaryType }>(
    `/dictionary-types/${code}/`,
    payload,
  );
  const body = resp.data as any;
  return body?.data ?? body;
}

/** 删除字典类型 (软删). DELETE /dictionary-types/<code>/ */
export async function deleteDictionaryType(code: string): Promise<void> {
  const resp = await api.delete(`/dictionary-types/${code}/`);
  const body = resp.data as any;
  return body?.data ?? body;
}

/**
 * 新建字典项. POST /dictionary-items/
 * type 传字典类型 id (由前端在选中类型下创建时填入).
 */
export async function createDictionaryItem(payload: {
  type: string;
  key: string;
  value: string;
  sortOrder?: number;
  isActive?: boolean;
}): Promise<DictionaryItem> {
  const resp = await api.post<{ success: boolean; data: DictionaryItem }>('/dictionary-items/', payload);
  const body = resp.data as any;
  return body?.data ?? body;
}

/**
 * 更新字典项 (按 id). PUT /dictionary-items/<id>/
 * 仅传需要修改的字段; type 不可改 (创建时固定).
 */
export async function updateDictionaryItem(
  id: string,
  payload: { key?: string; value?: string; sortOrder?: number; isActive?: boolean },
): Promise<DictionaryItem> {
  const resp = await api.put<{ success: boolean; data: DictionaryItem }>(
    `/dictionary-items/${id}/`,
    payload,
  );
  const body = resp.data as any;
  return body?.data ?? body;
}

/** 删除字典项 (软删). DELETE /dictionary-items/<id>/ */
export async function deleteDictionaryItem(id: string): Promise<void> {
  const resp = await api.delete(`/dictionary-items/${id}/`);
  const body = resp.data as any;
  return body?.data ?? body;
}

export default {
  listDictionaryItems,
  listDictionaryTypes,
  toOptions,
  listStageTypeOptions,
  STAGE_TYPE_DICT_CODE,
  createDictionaryType,
  updateDictionaryType,
  deleteDictionaryType,
  createDictionaryItem,
  updateDictionaryItem,
  deleteDictionaryItem,
};

/**
 * 数据字典 API 客户端 (终稿 PRD — 树形 / 系统自定义差异化 / 草稿批量提交)
 *
 * 后端 apps/dictionary:
 *   - GET  /api/v1/dictionary-types/?q=<搜索>&type=system|custom   列表(搜索/筛选)
 *   - GET  /api/v1/dictionary-types/<code>/                       详情(含 items 扁平树)
 *   - POST /api/v1/dictionary-types/<code>/submit/                 批量提交草稿
 *   - POST /api/v1/dictionary-types/                              新建字典类型
 *   - PUT  /api/v1/dictionary-types/<code>/                       更新(含 is_enabled)
 *   - DELETE /api/v1/dictionary-types/<code>/                     删除(仅自定义)
 * 响应: 列表走 { success, data:[...], pagination }, 单对象直出 camelCase。
 * submit 端点成功/失败均返回裸体: 成功 {detail, dictNumber, code};
 *   失败 {detail:'校验失败', headErrors:{...}, itemErrors:{'0':{...}}}。
 *
 * 设计: 字典项是枚举 single source of truth; 阶段类型 code='recruitment_stage_type'。
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

/** 字典类型(列表/详情, 驼峰键)。 */
export interface DictionaryType {
  id: string;
  code: string;
  name: string;
  englishName: string;
  description: string;
  dictNumber: string;
  isSystem: boolean;
  isEnabled: boolean;
  createdByName: string;
  createdAt: string;
  updatedByName: string;
  updatedAt: string;
}

/** 字典项(扁平, 含 parentId, 供前端构建树)。 */
export interface DictionaryItem {
  id: string;
  parentId: string | null;
  key: string;
  value: string;
  englishName: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
}

export interface DictionaryDetail extends DictionaryType {
  items: DictionaryItem[];
}

/** 列表查询参数。 */
export interface DictionaryTypeQuery {
  q?: string;
  type?: 'system' | 'custom' | 'all';
}

/** naive-ui n-select 用的 option。 */
export interface DictionaryOption {
  label: string;
  value: string;
  sortOrder?: number;
}

export const STAGE_TYPE_DICT_CODE = 'recruitment_stage_type';

/**
 * --- 阶段类型枚举读取 (PR #69 single source of truth) ---
 * RecruitmentStage.vue 依赖 listStageTypeOptions(); 此处保留兼容实现,
 * 与新版树形/草稿 API 共存 (字段名互不冲突)。
 */

/** 阶段类型读取用的扁平项 (仅取枚举所需字段)。 */
export interface DictionaryItemLite {
  key: string;
  value: string;
  sortOrder: number;
  isActive: boolean;
}

/** 取某类型下所有字典项 (按 sortOrder 升序)。兼容包裹或裸数组。 */
export async function listDictionaryItems(typeCode: string): Promise<DictionaryItemLite[]> {
  const resp = await api.get('/dictionary-items/', {
    params: { type_code: typeCode, page_size: 200 },
  });
  const body = resp.data;
  const items: any[] = Array.isArray(body)
    ? body
    : body && typeof body === 'object' && 'data' in body && Array.isArray((body as any).data)
      ? (body as any).data
      : [];
  return items
    .slice()
    .sort((a: any, b: any) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0))
    .map((it: any) => ({
      key: it.key,
      value: it.value,
      sortOrder: it.sortOrder,
      isActive: it.isActive,
    }));
}

/** 字典项 → n-select options (value=key, label=value)。 */
export function toOptions(items: DictionaryItemLite[]): DictionaryOption[] {
  return items.map((it) => ({ label: it.value, value: it.key, sortOrder: it.sortOrder }));
}

/** 直接拉「阶段类型」可选列表。 */
export async function listStageTypeOptions(): Promise<DictionaryOption[]> {
  const items = await listDictionaryItems(STAGE_TYPE_DICT_CODE);
  return toOptions(items);
}

/** 取字典类型列表(支持搜索 q 与类型筛选 type)。兼容包裹或裸数组。 */
export async function listDictionaryTypes(
  params: DictionaryTypeQuery = {},
): Promise<DictionaryType[]> {
  const query: Record<string, any> = { page_size: 200 };
  if (params.q) query.q = params.q;
  if (params.type && params.type !== 'all') query.type = params.type;
  const resp = await api.get('/dictionary-types/', { params: query });
  const body = resp.data;
  if (Array.isArray(body)) return body;
  if (body && typeof body === 'object' && Array.isArray((body as any).data)) {
    return (body as any).data;
  }
  return [];
}

/** 取某字典类型详情(含元素扁平列表, 已含 parentId)。 */
export async function getDictionaryDetail(code: string): Promise<DictionaryDetail> {
  const resp = await api.get<DictionaryDetail>(`/dictionary-types/${code}/`);
  return resp.data as any;
}

/** 提交草稿: 头部修改 + 元素增改/停用, 事务一次性落库。 */
export async function submitDictionaryDraft(
  code: string,
  payload: { head: Record<string, any>; items: Record<string, any>[] },
): Promise<any> {
  const resp = await api.post(`/dictionary-types/${code}/submit/`, payload);
  return resp.data;
}

/** 新建字典类型。 */
export async function createDictionaryType(payload: {
  code: string;
  name: string;
  englishName?: string;
  description?: string;
}): Promise<DictionaryType> {
  const resp = await api.post('/dictionary-types/', payload);
  const body = resp.data as any;
  return body?.data ?? body;
}

/** 更新字典类型(按 code, 可含 is_enabled)。用 PATCH 部分更新,
 *  允许只传 is_enabled 切换启用/停用, 不触发 name 必填校验。 */
export async function updateDictionaryType(
  code: string,
  payload: { name?: string; englishName?: string; description?: string; isEnabled?: boolean },
): Promise<DictionaryType> {
  const resp = await api.patch(`/dictionary-types/${code}/`, payload);
  const body = resp.data as any;
  return body?.data ?? body;
}

/** 删除字典类型(软删, 仅自定义)。 */
export async function deleteDictionaryType(code: string): Promise<void> {
  await api.delete(`/dictionary-types/${code}/`);
}

export default {
  listDictionaryTypes,
  getDictionaryDetail,
  submitDictionaryDraft,
  createDictionaryType,
  updateDictionaryType,
  deleteDictionaryType,
  STAGE_TYPE_DICT_CODE,
  listDictionaryItems,
  toOptions,
  listStageTypeOptions,
};

/**
 * job-title.ts — 职务（JobTitle）API 薄封装（2026-10-14 org-mgmt T5）。
 *
 * 后端 apps/position_title（DRF ViewSet，路由 basename: position-title）：
 *   - GET    /position-titles/            列表（search=name，is_enabled 筛选，分页）
 *   - POST   /position-titles/            新建
 *   - GET    /position-titles/{id}/       详情
 *   - PUT    /position-titles/{id}/       更新
 *   - PATCH  /position-titles/{id}/       部分更新（启停只传 isEnabled）
 *   - DELETE /position-titles/{id}/       软删
 * 响应信封 {success, data, message, code, pagination?}；JSON 出参已由
 * djangorestframework-camel-case 全局渲染为 camelCase（isEnabled/status/jobFamily...）。
 *
 * 职位族 / 职位类 / 职位子类三级枚举走既有 apps/dictionary（DictionaryItem），
 * 此处经 /dictionary-items/ 拉取并保留 id / parentId（dictionary.ts 的
 * listDictionaryItems 会剥离这两个字段，无法满足前端级联与 id→名称反查）。
 */
import api from './auth';

/** 字典项（含 id / parentId，供三级级联下拉与反查展示名）。 */
export interface PositionDictionaryItem {
  id: string;
  parentId: string | null;
  key: string;
  value: string;
  sortOrder: number;
  isActive: boolean;
}

/** 职务实体（列表行为 camelCase）。 */
export interface JobTitle {
  id: string;
  name: string;
  /** 职位族：字典项对象 {id, value} 或字典项 id（前端两种形态均兼容）。 */
  jobFamily?: any;
  jobCategory?: any;
  jobSubcategory?: any;
  isKeyPosition?: boolean;
  responsibility?: string;
  isManagement?: boolean;
  jobLevelTier?: string | null;
  sortOrder?: number;
  isEnabled?: boolean;
  /** 后端派生只读字段（ACTIVE / INACTIVE）。 */
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

/** 新建 / 更新入参（camelCase，由 CamelCaseJSONParser 归一为 snake_case 落库）。 */
export interface JobTitlePayload {
  name: string;
  jobFamily: string | null;
  jobCategory: string | null;
  jobSubcategory: string | null;
  isKeyPosition: boolean;
  responsibility: string;
  isManagement: boolean;
  jobLevelTier: string | null;
  sortOrder: number;
}

/** 列表查询参数。 */
export interface JobTitleQuery {
  search?: string;
  /** 启用状态筛选：true=启用 / false=停用 / undefined=全部。 */
  isEnabled?: boolean;
  pageSize?: number;
}

/** 拉取某字典类型下的全部字典项（按 sortOrder 升序，保留 id / parentId）。 */
export async function listPositionDictionaryItems(
  typeCode: string,
): Promise<PositionDictionaryItem[]> {
  const resp = await api.get('/dictionary-items/', {
    params: { type_code: typeCode, page_size: 200 },
  });
  const body: any = resp.data;
  const items: any[] = Array.isArray(body)
    ? body
    : body && typeof body === 'object' && Array.isArray(body.data)
      ? body.data
      : [];
  return items
    .map((it: any) => {
      const rawParent = it.parentId ?? it.parent_id ?? null;
      return {
        id: String(it.id),
        parentId: rawParent == null ? null : String(rawParent),
        key: String(it.key ?? ''),
        value: String(it.value ?? ''),
        sortOrder: Number(it.sortOrder ?? it.sort_order ?? 0),
        isActive: (it.isActive ?? it.is_active) !== false,
      };
    })
    .sort((a: PositionDictionaryItem, b: PositionDictionaryItem) => a.sortOrder - b.sortOrder);
}

/** 职务列表（信封 data 数组；分页由前端 useTablePagination 本地切片）。 */
export async function listJobTitles(query: JobTitleQuery = {}): Promise<JobTitle[]> {
  const params: Record<string, any> = { page_size: query.pageSize ?? 1000 };
  if (query.search) params.search = query.search;
  if (query.isEnabled !== undefined) {
    params.is_enabled = query.isEnabled ? 'true' : 'false';
  }
  const resp = await api.get('/position-titles/', { params });
  const body: any = resp.data;
  if (Array.isArray(body)) return body as JobTitle[];
  if (body && typeof body === 'object' && Array.isArray(body.data)) {
    return body.data as JobTitle[];
  }
  return [];
}

/** 新建职务。 */
export async function createJobTitle(payload: JobTitlePayload): Promise<JobTitle | null> {
  const resp = await api.post('/position-titles/', payload);
  const body: any = resp.data;
  return (body?.data ?? body ?? null) as JobTitle | null;
}

/** 更新职务（全量 PUT）。 */
export async function updateJobTitle(
  id: string,
  payload: JobTitlePayload,
): Promise<JobTitle | null> {
  const resp = await api.put(`/position-titles/${id}/`, payload);
  const body: any = resp.data;
  return (body?.data ?? body ?? null) as JobTitle | null;
}

/** 启停切换（PATCH 部分更新，仅切 is_enabled，软停不物理删除）。 */
export async function setJobTitleEnabled(id: string, isEnabled: boolean): Promise<void> {
  await api.patch(`/position-titles/${id}/`, { isEnabled });
}

export default {
  listPositionDictionaryItems,
  listJobTitles,
  createJobTitle,
  updateJobTitle,
  setJobTitleEnabled,
};

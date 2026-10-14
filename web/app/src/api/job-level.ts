/**
 * job-level.ts — 职级（JobLevel）域 API 薄封装（2026-10-14 org-mgmt T6）。
 *
 * 后端 apps/job_level（DRF ViewSet）：
 *   - GET/POST     /job-levels/                       职级 CRUD
 *   - PUT/PATCH    /job-levels/{id}/                  更新 / 启停（isEnabled）
 *   - GET/POST     /job-level-categories/             类别 CRUD（含 jobLevelCount）
 *   - PUT/PATCH    /job-level-categories/{id}/        类别更新 / 启停
 *   - GET/PUT      /job-level-grade-settings/current/ 职等上限单例读写（maxGrade）
 *   - GET/PUT      /job-level-sequences/current/      职级序列单例读写（managementEnabled）
 * 响应信封 {success, data, ...}；JSON 出参已由 djangorestframework-camel-case
 * 全局渲染为 camelCase（isEnabled/status/jobLevelCount/maxGrade/managementEnabled）。
 */
import api from './auth';

/** 职级类别。 */
export interface JobLevelCategory {
  id: string;
  name: string;
  sortOrder?: number;
  isEnabled?: boolean;
  /** 后端派生只读字段（ACTIVE / INACTIVE）。 */
  status?: string;
  /** 该类别下启用中的职级数量（SerializerMethodField）。 */
  jobLevelCount?: number;
}

/** 职级实体。 */
export interface JobLevel {
  id: string;
  name: string;
  /** 类别：类别对象 {id, name} 或类别 id（前端两种形态均兼容）。 */
  category?: any;
  /** 类别展示名（后端 category_name 经 camel-case 透出；回显兜底用）。 */
  categoryName?: string;
  grade?: number;
  sortOrder?: number;
  remark?: string;
  isEnabled?: boolean;
  status?: string;
  createdAt?: string;
  updatedAt?: string;
}

/** 新建 / 更新入参（camelCase）。 */
export interface JobLevelPayload {
  name: string;
  category: string | null;
  grade: number;
  sortOrder: number;
  remark: string;
}

/** 列表查询参数。 */
export interface JobLevelQuery {
  search?: string;
  isEnabled?: boolean;
  pageSize?: number;
}

/** 职等上限单例。 */
export interface JobLevelGradeSetting {
  maxGrade: number;
}

/** 职级序列单例。 */
export interface JobLevelSequenceSetting {
  managementEnabled: boolean;
}

/** 解析信封中的 data 数组。 */
function readList(body: any): any[] {
  if (Array.isArray(body)) return body;
  if (body && typeof body === 'object' && Array.isArray(body.data)) return body.data;
  return [];
}

/** 解析信封中的单对象（兼容包裹与裸体）。 */
function readObject(body: any): any {
  if (body && typeof body === 'object' && 'data' in body) return body.data;
  return body ?? null;
}

/** 职级列表。 */
export async function listJobLevels(query: JobLevelQuery = {}): Promise<JobLevel[]> {
  const params: Record<string, any> = { page_size: query.pageSize ?? 1000 };
  if (query.search) params.search = query.search;
  if (query.isEnabled !== undefined) {
    params.is_enabled = query.isEnabled ? 'true' : 'false';
  }
  const resp = await api.get('/job-levels/', { params });
  return readList(resp.data) as JobLevel[];
}

/** 新建职级。 */
export async function createJobLevel(payload: JobLevelPayload): Promise<JobLevel | null> {
  const resp = await api.post('/job-levels/', payload);
  return readObject(resp.data) as JobLevel | null;
}

/** 更新职级（全量 PUT）。 */
export async function updateJobLevel(id: string, payload: JobLevelPayload): Promise<JobLevel | null> {
  const resp = await api.put(`/job-levels/${id}/`, payload);
  return readObject(resp.data) as JobLevel | null;
}

/** 启停切换（PATCH 部分更新，软停不物理删除）。 */
export async function setJobLevelEnabled(id: string, isEnabled: boolean): Promise<void> {
  await api.patch(`/job-levels/${id}/`, { isEnabled });
}

/** 职级类别列表（含 jobLevelCount；isEnabled 传 false 可只看停用项）。 */
export async function listJobLevelCategories(
  params: { isEnabled?: boolean; pageSize?: number } = {},
): Promise<JobLevelCategory[]> {
  const query: Record<string, any> = { page_size: params.pageSize ?? 500 };
  if (params.isEnabled !== undefined) {
    query.is_enabled = params.isEnabled ? 'true' : 'false';
  }
  const resp = await api.get('/job-level-categories/', { params: query });
  return readList(resp.data) as JobLevelCategory[];
}

/** 新建职级类别。 */
export async function createJobLevelCategory(payload: {
  name: string;
  sortOrder?: number;
}): Promise<JobLevelCategory | null> {
  const resp = await api.post('/job-level-categories/', payload);
  return readObject(resp.data) as JobLevelCategory | null;
}

/** 更新职级类别名称 / 顺序（PUT）。 */
export async function updateJobLevelCategory(
  id: string,
  payload: { name?: string; sortOrder?: number },
): Promise<JobLevelCategory | null> {
  const resp = await api.put(`/job-level-categories/${id}/`, payload);
  return readObject(resp.data) as JobLevelCategory | null;
}

/** 类别启停切换（PATCH 部分更新，软停不物理删除）。 */
export async function setJobLevelCategoryEnabled(
  id: string,
  isEnabled: boolean,
): Promise<JobLevelCategory | null> {
  const resp = await api.patch(`/job-level-categories/${id}/`, { isEnabled });
  return readObject(resp.data) as JobLevelCategory | null;
}

/** 读取职等上限单例（缺省 40）。 */
export async function getJobLevelGradeSetting(): Promise<JobLevelGradeSetting> {
  const resp = await api.get('/job-level-grade-settings/current/');
  const body = readObject(resp.data);
  const raw = body?.maxGrade ?? body?.max_grade;
  const maxGrade = Number(raw);
  return { maxGrade: Number.isFinite(maxGrade) && maxGrade > 0 ? maxGrade : 40 };
}

/** 保存职等上限单例。 */
export async function updateJobLevelGradeSetting(
  maxGrade: number,
): Promise<JobLevelGradeSetting> {
  const resp = await api.put('/job-level-grade-settings/current/', { maxGrade });
  const body = readObject(resp.data);
  const raw = body?.maxGrade ?? body?.max_grade;
  const saved = Number(raw);
  return { maxGrade: Number.isFinite(saved) && saved > 0 ? saved : maxGrade };
}

/** 读取职级序列单例（管理序列开关）。 */
export async function getJobLevelSequenceSetting(): Promise<JobLevelSequenceSetting> {
  const resp = await api.get('/job-level-sequences/current/');
  const body = readObject(resp.data);
  const raw = body?.managementEnabled ?? body?.management_enabled;
  return { managementEnabled: raw === true };
}

/** 保存职级序列单例。 */
export async function updateJobLevelSequenceSetting(
  managementEnabled: boolean,
): Promise<JobLevelSequenceSetting> {
  const resp = await api.put('/job-level-sequences/current/', { managementEnabled });
  const body = readObject(resp.data);
  const raw = body?.managementEnabled ?? body?.management_enabled;
  return { managementEnabled: raw === undefined ? managementEnabled : raw === true };
}

export default {
  listJobLevels,
  createJobLevel,
  updateJobLevel,
  setJobLevelEnabled,
  listJobLevelCategories,
  createJobLevelCategory,
  updateJobLevelCategory,
  setJobLevelCategoryEnabled,
  getJobLevelGradeSetting,
  updateJobLevelGradeSetting,
  getJobLevelSequenceSetting,
  updateJobLevelSequenceSetting,
};

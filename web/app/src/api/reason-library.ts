/**
 * Reason Library API 客户端 (T-14)
 *
 * 后端端点 (挂载 /api/v1/reason-library/, 见 apps/django/apps/reason_library/urls.py):
 *   GET    /tags/                       列表 (filter: type/enabled/search, 默认分页)
 *   POST   /tags/                       新建 (custom only; system 由 seed 灌入)
 *   GET    /tags/{id}/                  详情 (含 ref_count)
 *   PATCH  /tags/{id}/                  更新 (system 不可改 — 40302)
 *   DELETE /tags/{id}/                  软删 (system 或被引用 — 40301/40901)
 *   POST   /tags/import/                multipart CSV 导入 (T10)
 *   GET    /rules/                      列表 (含 is_system/enabled/scene 过滤)
 *   POST   /rules/                      创建空规则 (头部, 三步内容走 wizard/save)
 *   GET    /rules/{id}/                 详情 (完整嵌套树)
 *   PATCH  /rules/{id}/                 头部更新 (可选 If-Match)
 *   DELETE /rules/{id}/                 删除 (system 或被引用 → 40310/40910)
 *   POST   /rules/{id}/snapshot/        复制为 custom 副本 (name + "(副本)")
 *   POST   /rules/{id}/wizard/save/     三步原子保存 (可选 If-Match)
 *   POST   /rules/import/               JSON 完整草稿导入
 *   GET    /scenes/                     读场景配置 (当前哪条规则占用)
 *   PUT    /scenes/                     写场景配置 (冲突 → 409 RULE_SCENE_CONFLICT)
 *   GET    /active/?scene=xxx           业务态查询 (Q3: 显式引用 > 系统预置, 多条取最新)
 *
 * 响应格式: { code, data: T|null, message } (见 types/reason-library.ts ApiResponse)
 * 字段命名: camelCase (DB snake_case 经 djangorestframework-camel-case 自动转换)
 *
 * ⚠️ 路径约定 (与 rule-engine.ts 一致): baseURL 已是 config.api.baseUrl = '/api/v1',
 *    调用路径必须从 '/reason-library/...' 起算, 不能重复 '/api/v1' 前缀。
 */

/**
 * 并发保护开关 (可选乐观锁)
 * - false (当前默认): 单人维护场景。请求不携带 If-Match / expected_updated_at,
 *   后端收到的请求无这些字段时直接跳过校验 → 不会出现"数据已被他人修改"误报。
 * - true: 多人协作时开启。请求携带 If-Match, 后端比对 updated_at, 冲突返回
 *   412 OPTIMISTIC_LOCK_FAILED, UI 提示"数据已被他人修改, 请刷新后重试"。
 * 未来启用多人: 仅需把此常量改为 true, 后端无需任何改动。
 */
export const ENABLE_OPTIMISTIC_LOCK = false

import axios from 'axios'
import config from '../config'
import type {
  ApiResponse,
  PaginatedData,
  ReasonTag,
  ReasonTagPayload,
  RuleListQuery,
  RuleCategory,
  SceneConfigPayload,
  SceneKey,
  SceneRule,
  SceneRuleListItem,
  SceneRuleUpdatePayload,
  TagImportResult,
  TagListQuery,
  WizardPayload,
  WizardSavePayload,
} from '../types/reason-library'
import { BIZ_CODE } from '../types/reason-library'

// ==================== axios 实例 ====================

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// ==================== 解包 ====================

/** 解 { code, data, message } → data; 后端失败抛 BizException 形式 Error */
function unwrap<T>(resp: { data: ApiResponse<T> }): T {
  const body = resp.data
  if (body && typeof body === 'object' && 'code' in body) {
    if (body.code === BIZ_CODE.SUCCESS || body.code === 0) {
      return (body.data ?? (null as unknown)) as T
    }
    // 业务错误 → 抛错, 上层 catch 后用 extractApiError 拿 message
    const err: any = new Error(body.message || `业务错误 code=${body.code}`)
    err.code = body.code
    err.response = { data: body }
    throw err
  }
  return (body as any) as T
}

/** 解分页: 后端 DRF 默认分页 {count, next, previous, results}; 这里有些接口可能直接 {items,total,page,pageSize}
 *  (由后端 PaginatedResponseRenderer 统一, 见 settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS']) */
function unwrapList<T>(resp: { data: ApiResponse<any> }): PaginatedData<T> {
  const body = resp.data
  if (body?.code === 0 || body?.code === BIZ_CODE.SUCCESS) {
    const data = body.data
    if (!data) return { items: [], total: 0, page: 1, pageSize: 20 }
    if (Array.isArray(data)) {
      return { items: data as T[], total: data.length, page: 1, pageSize: data.length }
    }
    // DRF 标准分页: { count, next, previous, results }
    if ('results' in data) {
      return {
        items: (data.results ?? []) as T[],
        total: Number(data.count ?? 0),
        page: 1,
        pageSize: (data.results ?? []).length,
      }
    }
    // 自定义 { items, total, page, pageSize }
    if ('items' in data) {
      return {
        items: (data.items ?? []) as T[],
        total: Number(data.total ?? 0),
        page: Number(data.page ?? 1),
        pageSize: Number(data.pageSize ?? 20),
      }
    }
  }
  return { items: [], total: 0, page: 1, pageSize: 20 }
}

// ==================== 错误码常量再导出 ====================

export { BIZ_CODE }

// ==================== Tag CRUD ====================

export function listTags(params?: TagListQuery): Promise<PaginatedData<ReasonTag>> {
  // 后端 StandardResultsSetPagination 只认 page_size; 前端统一用 pageSize 字段名
  const { pageSize, ...rest } = params ?? {}
  return api
    .get<ApiResponse<any>>('/reason-library/tags/', { params: { ...rest, page_size: pageSize } })
    .then((r) => unwrapList<ReasonTag>(r))
}

export function getTag(id: string): Promise<ReasonTag> {
  return api
    .get<ApiResponse<ReasonTag>>(`/reason-library/tags/${id}/`)
    .then((r) => unwrap<ReasonTag>(r))
}

export function createTag(payload: ReasonTagPayload): Promise<ReasonTag> {
  return api
    .post<ApiResponse<ReasonTag>>('/reason-library/tags/', payload)
    .then((r) => unwrap<ReasonTag>(r))
}

export function updateTag(id: string, payload: Partial<ReasonTagPayload>): Promise<ReasonTag> {
  return api
    .patch<ApiResponse<ReasonTag>>(`/reason-library/tags/${id}/`, payload)
    .then((r) => unwrap<ReasonTag>(r))
}

export function deleteTag(id: string): Promise<void> {
  return api
    .delete<ApiResponse<null>>(`/reason-library/tags/${id}/`)
    .then((r) => {
      unwrap<null>(r)
    })
}

export function importTags(file: File): Promise<TagImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<ApiResponse<TagImportResult>>('/reason-library/tags/import/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => unwrap<TagImportResult>(r))
}

// ==================== Rule CRUD ====================

export function listRules(params?: RuleListQuery): Promise<PaginatedData<SceneRuleListItem>> {
  const { pageSize, ...rest } = params ?? {}
  return api
    .get<ApiResponse<any>>('/reason-library/rules/', { params: { ...rest, page_size: pageSize } })
    .then((r) => unwrapList<SceneRuleListItem>(r))
}

export function getRule(id: string): Promise<SceneRule> {
  return api
    .get<ApiResponse<SceneRule>>(`/reason-library/rules/${id}/`)
    .then((r) => unwrap<SceneRule>(r))
}

export function createRule(payload: { name: string; description?: string }): Promise<SceneRule> {
  return api
    .post<ApiResponse<SceneRule>>('/reason-library/rules/', payload)
    .then((r) => unwrap<SceneRule>(r))
}

export function updateRule(
  id: string,
  payload: Partial<SceneRuleUpdatePayload>,
): Promise<SceneRule> {
  const headers: Record<string, string> = {}
  const { ifMatch, ...body } = payload
  if (ENABLE_OPTIMISTIC_LOCK && ifMatch) headers['If-Match'] = ifMatch
  return api
    .patch<ApiResponse<SceneRule>>(`/reason-library/rules/${id}/`, body, { headers })
    .then((r) => unwrap<SceneRule>(r))
}

export function deleteRule(id: string): Promise<void> {
  return api
    .delete<ApiResponse<null>>(`/reason-library/rules/${id}/`)
    .then((r) => {
      unwrap<null>(r)
    })
}

export function snapshotRule(id: string): Promise<SceneRule> {
  return api
    .post<ApiResponse<SceneRule>>(`/reason-library/rules/${id}/snapshot/`, {})
    .then((r) => unwrap<SceneRule>(r))
}

/**
 * 将前端 WizardPayload 转为后端 WizardSaveSerializer 期望的字段 (T-BF-02 BugFix):
 * - 为每个分类生成 client_id = existingId ?? crypto.randomUUID()
 *   (后端 client_id 是前端临时引用 — 新分类必填, 已存在分类沿用前端的 id)
 * - parentId → parent_client_id (映射在 client_id 分配完成后做)
 * - tags: ReasonTag[] → tag_ids: string[] (只提取 id)
 */
export function toWizardSavePayload(rule: WizardPayload): WizardSavePayload {
  // 第一遍: 给每个分类分配 client_id (已有 id 复用, 否则生成新 UUID)
  //   关键: 用 index 作为新分类的内部 key, 避免两个新建分类都使用 id='' 时
  //         Map key 冲突导致 client_id 重复。
  //   同时建立 id -> client_id 索引, 让 parentId 引用能查到对应 client_id。
  const idToClientId = new Map<string, string>()
  const newCatCidByIndex = new Map<number, string>()
  rule.categories.forEach((cat, idx) => {
    if (cat.id) {
      idToClientId.set(cat.id, cat.id)
    } else {
      const cid = crypto.randomUUID()
      newCatCidByIndex.set(idx, cid)
    }
  })

  // 末级分类集合: 标签只允许挂在末级 (Item4 修订); 非末级输出空 tag_ids,
  // 避免历史脏数据 (绑定挂非末级) 在保存时被再次写入 → 修复『已在当前规则中使用』误报。
  const idSet = new Set(rule.categories.map((c) => c.id))
  const leafIds = new Set(
    rule.categories.filter((c) => !rule.categories.some((x) => x.parentId === c.id)).map((c) => c.id),
  )
  void idSet
  const categories = rule.categories.map((cat, idx) => {
    const client_id = cat.id ? idToClientId.get(cat.id)! : newCatCidByIndex.get(idx)!
    const parent_client_id = cat.parentId ? idToClientId.get(cat.parentId) : undefined
    const isLeaf = leafIds.has(cat.id)
    return {
      id: cat.id || undefined,
      client_id,
      parent_client_id,
      name: cat.name,
      order: cat.order,
      allow_custom: cat.allowCustom,
      tag_ids: isLeaf ? (cat.tags || []).map((t) => t.id) : [],
    }
  })

  return {
    name: rule.name,
    description: rule.description,
    enabled: rule.enabled,
    scenes: rule.scenes,
    recruit_types: rule.recruitTypes && rule.recruitTypes.length ? rule.recruitTypes : ['social'],
    max_selectable_tags: rule.maxSelectableTags ?? 5,
    categories,
  }
}

/**
 * 三步原子保存 (T06 / T12):
 * - body = WizardSavePayload (经 toWizardSavePayload 转换)
 * - 并发保护: 由 ENABLE_OPTIMISTIC_LOCK 开关控制, 默认关闭 (单人场景)
 */
export function wizardSave(ruleId: string, payload: WizardPayload): Promise<SceneRule> {
  const headers: Record<string, string> = {}
  const body = toWizardSavePayload(payload)
  if (ENABLE_OPTIMISTIC_LOCK && payload.updatedAt) {
    headers['If-Match'] = payload.updatedAt
    body.expected_updated_at = payload.updatedAt
  }
  return api
    .post<ApiResponse<SceneRule>>(`/reason-library/rules/${ruleId}/wizard/save/`, body, { headers })
    .then((r) => unwrap<SceneRule>(r))
}

/** 通用 CSV 下载 (带鉴权): 触发浏览器保存文件。 */
export async function downloadCsv(path: string, filename: string): Promise<void> {
  const resp = await api.get(path, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([resp.data]))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

/** 导出全部原因标签 CSV。 */
export function exportTags(): Promise<void> {
  return downloadCsv('/reason-library/tags/export/', 'reason-tags-export.csv')
}

/** 下载导入模板 CSV。 */
export function downloadImportTemplate(): Promise<void> {
  return downloadCsv('/reason-library/tags/import-template/', 'reason-tags-import-template.csv')
}

export function importRule(file: File): Promise<SceneRule> {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<ApiResponse<SceneRule>>('/reason-library/rules/import/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => unwrap<SceneRule>(r))
}

// ==================== Scene Config ====================

/** 读场景配置: 返回 { scenes: { [scene]: ruleId|null } } — null 表示该场景未覆盖, 业务态走系统预置 */
export function getSceneConfig(): Promise<SceneConfigPayload> {
  return api
    .get<ApiResponse<SceneConfigPayload>>('/reason-library/scenes/')
    .then((r) => unwrap<SceneConfigPayload>(r))
}

/** 写场景配置: 部分提交 { sceneKey: ruleId } — 冲突时后端返 409 RULE_SCENE_CONFLICT */
export function putSceneConfig(
  payload: Partial<Record<SceneKey, string | null>>,
): Promise<SceneConfigPayload> {
  return api
    .put<ApiResponse<SceneConfigPayload>>('/reason-library/scenes/', payload)
    .then((r) => unwrap<SceneConfigPayload>(r))
}

// ==================== 业务态 Active Query ====================

/**
 * 业务态查询 (Q3 / Q-A5):
 * - 优先级: 显式引用 > 系统预置
 * - 多条显式引用取最新 updatedAt
 * - 缓存不按 user.role 区分 (Q-A5)
 * 返回规则完整 SceneRule (含 categories 树)
 */
export function getActiveRule(scene: SceneKey): Promise<SceneRule | null> {
  return api
    .get<ApiResponse<SceneRule | null>>('/reason-library/active/', { params: { scene } })
    .then((r) => {
      const body = r.data
      if (body?.code === 0 || body?.code === BIZ_CODE.SUCCESS) {
        return (body.data ?? null) as SceneRule | null
      }
      const err: any = new Error(body?.message || `Active 查询失败`)
      err.code = body?.code
      throw err
    })
}

// ==================== 工具: 把后端错误信息提取为字符串 (UI 弹 toast) ====================

export function extractReasonApiError(e: any, fallback = '请求失败'): string {
  const data = e?.response?.data
  if (data?.errors) {
    if (typeof data.errors === 'string') return data.errors
    const flat = Object.values(data.errors)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter((v): v is string => typeof v === 'string' && v.length > 0)
    if (flat.length) return flat.join('; ')
  }
  return data?.message || e?.message || fallback
}

// ==================== 类型再导出 (供组件就近 import) ====================

export type {
  ApiResponse,
  PaginatedData,
  ReasonTag,
  ReasonTagPayload,
  SceneRule,
  SceneRuleListItem,
  SceneRuleUpdatePayload,
  RuleCategory,
  SceneKey,
  SceneConfigPayload,
  TagImportResult,
  TagListQuery,
  RuleListQuery,
  WizardPayload,
  WizardSavePayload,
}

// ==================== 默认导出 (便于整批 import) ====================

export default {
  // tag
  listTags,
  getTag,
  createTag,
  updateTag,
  deleteTag,
  importTags,
  // rule
  listRules,
  getRule,
  createRule,
  updateRule,
  deleteRule,
  snapshotRule,
  wizardSave,
  importRule,
  // scene
  getSceneConfig,
  putSceneConfig,
  // active
  getActiveRule,
  // helpers
  extractReasonApiError,
  toWizardSavePayload,
}

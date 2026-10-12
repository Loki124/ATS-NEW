/**
 * permission-resource.ts — V2 权限资源 API 客户端 (T19)
 *
 * 后端端点: GET /api/v1/permissions/resources/  （ReadOnlyModelViewSet，仅只读）
 * 响应格式: { success, data, pagination? } —— ⚠️ 后端 per P1 audit (a0de2af3) 已恢复
 * 服务端分页 (StandardResultsSetPagination: page_size=20, page_size_query_param=
 * 'page_size', max_page_size=200, page_query_param='page')，list 单次请求只返回一页，
 * 分页信息在响应体的 pagination 字段（total / has_next 等）。
 *
 * 字段命名: drf-camel-case 出 camelCase (resourceCode / resourceName / systemCode),
 *   FE 类型严格按 camelCase 写, 后端 snake_case 通过中间件自动桥接
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export type ResourceType = 'MENU' | 'BUTTON' | 'FIELD' | 'API';

export interface PermissionResource {
  id: string;
  systemCode: string;
  resourceCode: string;
  resourceName: string;
  resourceType: ResourceType;
  parentCode?: string | null;
  module?: string | null;
  sortOrder?: number;
  status: number;
}

/** 服务端分页信封（StandardResultsSetPagination → success_response） */
interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

type ListResponse = {
  success: boolean;
  data: PermissionResource[] | { results: PermissionResource[] };
  pagination?: PaginationMeta;
};

/** 从信封里取出当页数组（兼容非分页数组 / 旧 results 形态） */
function extractItems(payload: ListResponse['data']): PermissionResource[] {
  if (Array.isArray(payload)) return payload;
  return payload?.results ?? [];
}

// ===== API =====

/**
 * 资源列表（**单页**）。后端默认 status=1，支持 module / resourceType / search 过滤。
 * 一般业务请改用 fetchAllResources —— 除非明确只要第一页。
 */
export async function listResources(params?: { module?: string; resourceType?: string; search?: string; page?: number; pageSize?: number }) {
  const { data } = await api.get<ListResponse>(
    '/permissions/resources/',
    {
      params: params
        ? { ...params, ...(params.pageSize ? { page_size: params.pageSize } : {}) }
        : undefined,
    },
  );
  return extractItems(data.data);
}

/**
 * 拉取**全部**符合条件的资源（自动跟随服务端分页翻页直到取完）。
 *
 * 背景: 后端已恢复服务端分页（单页 20 条），资源管理列表的前端筛选/分页、
 * 角色编辑弹窗的权限勾选都需要完整集合 —— 只取第一页会把 185 条资源
 * 静默截断成 20 条（2026-10-10 线上反馈的回归）。
 *
 * 每页按 max_page_size(200) 取，185 条一次即完成；未来增长到多页也自动翻完。
 *
 * @param params     可选服务端筛选（module / resourceType / search）
 * @param maxPages   防失控上限，默认 50 页（≈ 10000 条），超出即止并返回已取部分
 */
export async function fetchAllResources(
  params?: { module?: string; resourceType?: string; search?: string },
  maxPages = 50,
): Promise<PermissionResource[]> {
  const PAGE_SIZE = 200 // 对齐后端 StandardResultsSetPagination.max_page_size
  const all: PermissionResource[] = []
  for (let page = 1; page <= maxPages; page++) {
    const { data } = await api.get<ListResponse>('/permissions/resources/', {
      params: { ...params, page, page_size: PAGE_SIZE },
    })
    all.push(...extractItems(data.data))
    if (!data.pagination?.has_next) break
  }
  return all
}

export default api;
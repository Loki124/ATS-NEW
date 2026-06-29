/**
 * 数据字典 API 客户端
 *
 * 2026-06-29 花无缺: 后端 apps/data_dict app 还没实现 (P0-1),
 *   FE listDict() 直接 return 空数组, 调用方 (RecruitmentStage.vue) catch 后用 FALLBACK_*
 *   所以这个 stub 留接口签名即可, 真接入等 BE 落地.
 */
import config from '../config'

export interface DictItem {
  label: string
  value: string
  sort?: number
}

export async function listDict(_type: string): Promise<DictItem[]> {
  // 2026-06-29 P0-1: BE dict app not implemented. Return empty so caller falls back.
  // TODO(fe-yzy): 接入后端 /api/v1/data-dict/by-type/{type}/ 当 BE 上线.
  void config
  return []
}

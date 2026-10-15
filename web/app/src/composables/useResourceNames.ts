/**
 * useResourceNames.ts — 权限资源「英文码 → 中文名」共享映射（模块级单例）
 *
 * 背景：权限码形如 `recruit:candidate:view` 是英文，直接透给用户不可读。
 *   后端 /api/v1/permissions/resources/ 同时返回 resourceCode(英文) 与 resourceName(中文)，
 *   本 composable 把全量资源拉一次缓存，供「模板管理」「从模板克隆」等多处复用，
 *   避免每个组件各自拉取 / 各自硬编码映射表。
 *
 * 模块级单例：首次 ensureLoaded 后结果常驻，后续调用直接命中缓存（含跨组件共享）。
 */
import { ref } from 'vue'
import { fetchAllResources, type PermissionResource } from '@/api/permission-resource'
import { resourceModuleLabel, UNGROUPED_MODULE } from '@/utils/permissionModules'

let cache: PermissionResource[] | null = null
let loadingPromise: Promise<PermissionResource[]> | null = null

/** 取中文名；未知码回退为原始 code（不隐藏未知值，便于排查 seed 缺口）。 */
export function nameOf(code: string): string {
  return cache?.find((r) => r.resourceCode === code)?.resourceName ?? code
}

/** 取资源所属模块 code（permission_resources.module）；未知返回 null。 */
export function moduleOf(code: string): string | null {
  return cache?.find((r) => r.resourceCode === code)?.module ?? null
}

export interface GroupedCode {
  module: string
  moduleLabel: string
  items: { code: string; name: string }[]
}

/**
 * 把权限码数组按「功能模块」分组（依赖已加载的缓存）。
 * 每组内按中文名排序；无模块归属的归入「其他」。供抽屉 / 克隆选择器展示中文权限码。
 */
export function groupPermissionCodesByModule(codes: string[]): GroupedCode[] {
  const groups: Record<string, GroupedCode> = {}
  for (const code of codes) {
    const mod = moduleOf(code) ?? UNGROUPED_MODULE
    const label = resourceModuleLabel(mod === UNGROUPED_MODULE ? null : mod, '其他')
    if (!groups[mod]) groups[mod] = { module: mod, moduleLabel: label, items: [] }
    groups[mod].items.push({ code, name: nameOf(code) })
  }
  const result = Object.values(groups)
  for (const g of result) g.items.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
  return result.sort((a, b) => a.moduleLabel.localeCompare(b.moduleLabel, 'zh'))
}

export function useResourceNames() {
  const resources = ref<PermissionResource[]>(cache ?? [])
  const loading = ref(false)

  /** 确保全量资源已加载（幂等：已缓存/加载中直接复用）。 */
  async function ensureLoaded(): Promise<PermissionResource[]> {
    if (cache) {
      resources.value = cache
      return cache
    }
    if (loadingPromise) {
      const r = await loadingPromise
      resources.value = r
      return r
    }
    loading.value = true
    loadingPromise = fetchAllResources()
    try {
      cache = await loadingPromise
      resources.value = cache
      return cache
    } finally {
      loading.value = false
    }
  }

  return { resources, loading, ensureLoaded, nameOf, moduleOf, groupPermissionCodesByModule }
}

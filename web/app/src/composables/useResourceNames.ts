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
import { resourceModuleLabel, buildSubModuleIndex, UNGROUPED_MODULE } from '@/utils/permissionModules'

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

// ===== 两级分组：功能模块 → 子模块（权限码明细弹窗用）=====

/** 未归入任何子模块的权限码分组 key（与身份编辑弹窗同约定） */
export const LOOSE_SUB_KEY = '__loose__'

export interface SubGroupedCode {
  /** 子模块 code；`''` = 该模块无子模块时的模块级分组；`__loose__` = 模块有子模块但本码未归类 */
  code: string
  /** 子模块中文名；模块级分组（该模块整体无子模块）时为空串，由 UI 决定是否显示标题 */
  label: string
  items: { code: string; name: string }[]
}

export interface ModuleCodeTree {
  module: string
  moduleLabel: string
  /** 本模块权限码总数 */
  total: number
  subModules: SubGroupedCode[]
}

/**
 * 把权限码按「功能模块 → 子模块」两级分组（依赖已加载的缓存）。
 *
 * 为什么需要下钻到子模块：「系统设置」一个模块下就有 40 个二级分栏、115 条权限码，
 * 只按模块分组会平铺成一长列，完全读不出归属；下钻后每个子模块独立成块。
 *
 * 子模块判定与资源管理列表 / 身份编辑弹窗**同源**（buildSubModuleIndex）：
 * 形如 `recruit:settings:account:menu:view` 的资源，第 3 段 `account` 即子模块。
 *
 * 排序：模块按中文名；模块内子模块按中文名；子模块内权限码按中文名。
 * 未归类分组恒排在本模块最后，且仅在该模块确实存在子模块时才显示「其他」标题。
 */
export function groupPermissionCodesBySubModule(codes: string[]): ModuleCodeTree[] {
  const index = buildSubModuleIndex(cache ?? [])
  const modules = new Map<string, { label: string; buckets: Map<string, SubGroupedCode> }>()

  for (const code of codes) {
    const mod = moduleOf(code) ?? UNGROUPED_MODULE
    let node = modules.get(mod)
    if (!node) {
      node = {
        label: resourceModuleLabel(mod === UNGROUPED_MODULE ? null : mod, '其他'),
        buckets: new Map(),
      }
      modules.set(mod, node)
    }
    const parts = code.split(':')
    const subCode = parts.length >= 4 ? parts[2] : ''
    const subLabel = subCode ? index[mod]?.[subCode] : undefined
    const key = subLabel ? subCode : LOOSE_SUB_KEY
    let bucket = node.buckets.get(key)
    if (!bucket) {
      bucket = { code: key, label: subLabel ?? '', items: [] }
      node.buckets.set(key, bucket)
    }
    bucket.items.push({ code, name: nameOf(code) })
  }

  const result: ModuleCodeTree[] = []
  for (const [mod, node] of modules) {
    const hasSub = [...node.buckets.values()].some((b) => b.label !== '')
    const subModules = [...node.buckets.values()]
    for (const b of subModules) {
      b.items.sort((x, y) => x.name.localeCompare(y.name, 'zh'))
      // 整个模块都没子模块（如候选人管理）→ 不显示子模块标题，直接平铺；
      // 有子模块时，散项统一落到「其他」。
      if (!b.label) b.label = hasSub ? '其他' : ''
    }
    subModules.sort((a, b) => {
      if (a.code === LOOSE_SUB_KEY) return 1
      if (b.code === LOOSE_SUB_KEY) return -1
      return a.label.localeCompare(b.label, 'zh')
    })
    result.push({
      module: mod,
      moduleLabel: node.label,
      total: subModules.reduce((n, b) => n + b.items.length, 0),
      subModules,
    })
  }
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

  return {
    resources, loading, ensureLoaded, nameOf, moduleOf,
    groupPermissionCodesByModule, groupPermissionCodesBySubModule,
  }
}

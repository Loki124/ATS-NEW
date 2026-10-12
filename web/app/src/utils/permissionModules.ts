/**
 * permissionModules.ts — 权限资源「模块」代码 → 中文显示名（单一数据源）
 *
 * 背景：permission_resources.module 存的是英文代码（application / mgmt_unit / …），
 *   直接透给用户不可读。原先映射表是 RoleEditModal.vue 的组件私有常量，资源管理列表
 *   （ResourcesTab.vue）用不到，导致模块筛选与表格列显示裸代码。
 *   故抽到此处共享，角色编辑弹窗与资源管理列表共用同一份定义。
 *
 * 取值与后端 seed 一一对应：apps/core/management/commands/seed_v2_init.py
 *   的资源四元组 (code, 中文名, type, module)，module 列共 15 个取值。
 *   新增模块时需同步 seed 与本表。
 *
 * 注：暂为中文硬编码（沿用 RoleEditModal 既有做法）。若后续要支持多语言展示，
 *   应迁至 locales 语言包按模块 code 做 key，此处退化为默认值兜底。
 */

/** 模块代码 → 中文名。未收录的 code 回退为原 code（不隐藏未知值，便于排查）。 */
export const RESOURCE_MODULE_LABELS: Record<string, string> = {
  candidate: '候选人管理',
  offer: 'Offer 管理',
  interview: '面试管理',
  demand: '招聘需求',
  position: '岗位管理',
  application: '申请管理',
  onboarding: '入职管理',
  referral: '内推管理',
  invitation: '邀约管理',
  talent_pool: '人才库',
  // mou 是 seed 里的「MOU菜单 / 创建MOU / 审批MOU」，与 mgmt_unit（管理单元）是两个模块，
  // 早期版本曾把两者都写成「管理单元」，会导致筛选后看不出区别，故按 seed 校正。
  mou: 'MOU',
  mgmt_unit: '管理单元',
  role: '身份管理',
  user_role: '用户授权',
  settings: '系统设置',
}

/** 未归类资源的占位 module 值（沿用 RoleEditModal 的约定） */
export const UNGROUPED_MODULE = '__ungrouped__'

/**
 * 取模块中文名。
 * @param module 模块代码；空值 / 未归类占位值交由调用方传入的 fallback 处理
 * @param fallback 空值或未收录时的兜底文案，缺省回退为原始 code
 */
export function resourceModuleLabel(module?: string | null, fallback?: string): string {
  if (!module || module === UNGROUPED_MODULE) {
    return fallback ?? module ?? ''
  }
  return RESOURCE_MODULE_LABELS[module] ?? fallback ?? module
}

// ===== 子模块（settings 这类模块内部的二级/三级分栏）=====

/**
 * 子模块代码 → 中文名。由数据推导，不硬编码 —— 新增子模块无需改前端。
 *
 * 数据来源：形如 `recruit:settings:account:menu:view` 的「菜单型」资源，
 * 其 code 第 3 段是子模块代码，resource_name 形如「个人信息管理菜单」，
 * 去掉「菜单」后缀即子模块中文名。
 */
export type SubModuleIndex = Record<string, Record<string, string>>

/** 去掉菜单名后缀：「个人信息管理菜单」→「个人信息管理」 */
function stripMenuSuffix(name?: string | null): string {
  if (!name) return ''
  return name.replace(/菜单$/, '').trim()
}

/**
 * 从全量资源列表构建「模块 → 子模块代码 → 中文名」索引。
 *
 * 判定子模块的依据是「该 code 的第 4 段是 menu」：
 *   recruit:settings:account:menu:view  → sub = account（settings 的子模块）
 *   recruit:candidate:menu:view         → 第 4 段不存在，不是子模块
 * 这样避免了「4 段时第 3 段到底是子模块还是动作」的歧义，无需硬编码动作词表。
 */
export function buildSubModuleIndex(resources: Array<{ resourceCode: string; resourceName: string }>): SubModuleIndex {
  const index: SubModuleIndex = {}
  for (const r of resources) {
    const parts = r.resourceCode.split(':')
    if (parts.length < 5 || parts[3] !== 'menu') continue
    const module = parts[1]
    const sub = parts[2]
    const label = stripMenuSuffix(r.resourceName)
    if (!label) continue
    index[module] = index[module] ?? {}
    // 同子模块存在多条菜单时保留首个，不互相覆盖
    if (!index[module][sub]) index[module][sub] = label
  }
  return index
}

/**
 * 从资源编码取子模块代码（第 3 段）。
 * @returns 子模块代码；该资源不属于任何子模块时返回 null（如 `recruit:candidate:list`）
 */
export function parseSubModuleCode(resourceCode: string): string | null {
  const parts = resourceCode.split(':')
  if (parts.length < 4) return null
  // 3 段无子模块；4 段时第 3 段可能是子模块，也可能是顶级动作（menu/list/…），
  // 交由调用方用索引校验，这里原样返回第 3 段。
  return parts[2] || null
}

/**
 * 取子模块中文名。
 * @param resourceCode 资源编码
 * @param index buildSubModuleIndex 的产物
 * @returns 中文名；无子模块或未收录时返回 null，由调用方决定兜底展示
 */
export function resourceSubModuleLabel(
  resourceCode: string,
  index: SubModuleIndex,
): string | null {
  const parts = resourceCode.split(':')
  if (parts.length < 4) return null
  const module = parts[1]
  const sub = parts[2]
  // 索引里不存在 ⇒ 第 3 段是动作而非子模块（如 candidate:list）
  return index[module]?.[sub] ?? null
}

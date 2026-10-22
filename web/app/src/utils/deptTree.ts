/**
 * 部门树筛选 · 纯逻辑层（2026-10-22 新增）
 *
 * 组件 `components/common/DeptTreeFilter.vue` 的全部树构建与勾选语义都在这里，
 * 不依赖 Vue / naive-ui —— 这样能用普通单测锁住「勾选传播 / 父子联动」这些
 * 最容易出错的规则（勾错了不会报错，只会**筛不出数据**）。
 *
 * ## 一、树的构建口径
 *
 * - 可见集合：`includeInactive=false`（默认）只显示启用部门；
 *   `includeInactive=true` 时把停用部门也放进树（带「停用」标记，仍可勾选 ——
 *   停用部门下仍可能挂着历史数据，筛它正是「展示历史停用部门」的意义）。
 * - 层级：按**真实** parentId 层级；父部门不可见时，子部门**上提到最近的可见祖先**
 *   （不是直接甩到根层 —— 否则「能电BG > 能食电器」这类两级结构会被拆散）。
 * - 「自动选中全部子部门」展开的是**可见树**的后代（所见即所得）：
 *   停用部门在 `includeInactive=false` 时不可见 → 不计入展开结果。
 *
 * ## 二、勾选语义
 *
 * `checked` = 复选框呈**实心勾**的节点；`indeterminate` = 呈**半选（横杠）**的节点。
 *
 * - 「自动选中全部子部门」ON：勾一个节点 = 同时勾上它的全部可见后代
 *   （等价于「选中该部门及其所有下级」）；取消同理。
 * - OFF：只勾自己，不动后代；但祖先仍按子树的完整度回算
 *   （孩子勾了但孩子子树没全勾 → 祖先显示半选，而不是实心勾）。
 * - 向上回算规则：
 *   · 某节点的所有孩子**连同其子树**都全选 → 该节点实心勾；
 *   · 只要有孩子被勾（哪怕只是半选）→ 该节点半选；
 *   · 否则 → 该节点未选。
 * - 对外暴露的「已选部门」= `checked` 集合（半选**不算**选中，
 *   否则「选了子部门却连父部门一起筛进去」会出现用户没预期的结果）。
 *
 * ## 三、与既有 `buildDeptTree`（utils/campus.ts）的区别
 *
 * `buildDeptTree` 服务于**单选**表单（回显完整路径），停用祖先的后代会被提到根层；
 * 本模块服务于**多选筛选**（要按子树展开勾选），故另起一套口径，不复用它。
 */
/**
 * 部门是否启用。
 * ⚠️ 唯一真源放这里（通用工具层），`utils/campus.ts` 的 `isDeptActive`
 *    改为引用本函数 —— 两处各写一份谓词是「口径漂移」的典型来源。
 */
export function isDeptEnabled(d: any): boolean {
  return d?.status === 'ACTIVE' || d?.isActive === true || d?.is_active === true
}

/** 兼容部门数据源（store 的 Department 与接口返回的驼峰字段都能吃） */
export interface DeptLike {
  id: string
  name: string
  parentId?: string | null
  status?: string
  isActive?: boolean
  is_active?: boolean
}

/** 树节点（naive-ui n-tree 的 data 结构，额外带 inactive 标记） */
export interface DeptTreeNode {
  key: string
  label: string
  name: string
  /** 该部门已停用（仅 includeInactive=true 时才会出现在树里） */
  inactive: boolean
  children?: DeptTreeNode[]
}

/** 树的索引（勾选算法要按父/子关系回算，故单独建索引，不在渲染时反复遍历） */
export interface DeptTreeIndex {
  /** 树的根节点 */
  nodes: DeptTreeNode[]
  /** key → 直属子节点 key 列表 */
  childrenMap: Map<string, string[]>
  /** key → 父节点 key（根节点为 null） */
  parentMap: Map<string, string | null>
  /** key → 部门名称 */
  nameMap: Map<string, string>
  /** key → 是否停用 */
  inactiveMap: Map<string, boolean>
}

/** 勾选状态 */
export interface DeptSelection {
  /** 实心勾的节点 */
  checked: string[]
  /** 半选（横杠）的节点 */
  indeterminate: string[]
}

export interface BuildDeptTreeOptions {
  /** 是否把停用部门也放进树（「展示历史停用部门」开关） */
  includeInactive?: boolean
}

/**
 * 构建部门筛选树。
 * @param list 部门列表（任意字段命名：parentId / parent_id 都能吃）
 */
export function buildDeptFilterTree(
  list: DeptLike[] | any[],
  options: BuildDeptTreeOptions = {},
): DeptTreeIndex {
  const includeInactive = options.includeInactive === true

  // 归一化：id / parent 一律转字符串，避免数字 id 与字符串 id 互不相等
  const all: { id: string; name: string; parentId: string | null; enabled: boolean }[] = []
  for (const raw of list || []) {
    if (!raw || raw.id === null || raw.id === undefined) continue
    const parentRaw = raw.parentId ?? raw.parent_id ?? null
    all.push({
      id: String(raw.id),
      name: String(raw.name ?? raw.id),
      parentId: parentRaw === null || parentRaw === undefined ? null : String(parentRaw),
      enabled: isDeptEnabled(raw),
    })
  }
  const byId = new Map(all.map((d) => [d.id, d]))

  const visible = includeInactive ? all : all.filter((d) => d.enabled)
  const visibleIds = new Set(visible.map((d) => d.id))

  /** 最近的**可见**祖先（父不可见时继续上溯；都没有则 null → 挂根层） */
  const visibleParentOf = (id: string): string | null => {
    const seen = new Set<string>()
    let cur = byId.get(id)
    while (cur && cur.parentId && !seen.has(cur.id)) {
      seen.add(cur.id)
      const parent = byId.get(cur.parentId)
      if (!parent) return null
      if (visibleIds.has(parent.id)) return parent.id
      cur = parent
    }
    return null
  }

  const childrenMap = new Map<string, string[]>()
  /** key → 父节点 key（根节点为 null） */
  const parentMap = new Map<string, string | null>()
  const nameMap = new Map<string, string>()
  const inactiveMap = new Map<string, boolean>()

  for (const d of visible) {
    const parent = visibleParentOf(d.id)
    parentMap.set(d.id, parent)
    nameMap.set(d.id, d.name)
    inactiveMap.set(d.id, !d.enabled)
    if (!childrenMap.has(d.id)) childrenMap.set(d.id, [])
  }
  for (const d of visible) {
    const parent = parentMap.get(d.id) ?? null
    if (parent) {
      const siblings = childrenMap.get(parent)
      if (siblings) siblings.push(d.id)
    }
  }

  // 组装 n-tree 的 data 结构（根 → 子）
  const nodeByKey = new Map<string, DeptTreeNode>()
  for (const d of visible) {
    nodeByKey.set(d.id, {
      key: d.id,
      label: d.name,
      name: d.name,
      inactive: !d.enabled,
      children: [],
    })
  }
  const nodes: DeptTreeNode[] = []
  for (const d of visible) {
    const node = nodeByKey.get(d.id)!
    const parent = parentMap.get(d.id) ?? null
    if (parent && nodeByKey.has(parent)) nodeByKey.get(parent)!.children!.push(node)
    else nodes.push(node)
  }

  return { nodes, childrenMap, parentMap, nameMap, inactiveMap }
}

/** 取某节点的**全部可见后代** key */
export function collectDeptDescendants(index: DeptTreeIndex, key: string): string[] {
  const out: string[] = []
  const walk = (k: string) => {
    for (const child of index.childrenMap.get(k) ?? []) {
      out.push(child)
      walk(child)
    }
  }
  walk(key)
  return out
}

/** 子树是否「整体全选」（自身在 checked 且全部后代都在 checked） */
function isSubtreeFullyChecked(index: DeptTreeIndex, checked: Set<string>, key: string): boolean {
  if (!checked.has(key)) return false
  for (const d of collectDeptDescendants(index, key)) {
    if (!checked.has(d)) return false
  }
  return true
}

/** 子树内是否有任何被勾（自身或后代） */
function hasSelectedInSubtree(index: DeptTreeIndex, checked: Set<string>, key: string): boolean {
  if (checked.has(key)) return true
  for (const d of collectDeptDescendants(index, key)) {
    if (checked.has(d)) return true
  }
  return false
}

/**
 * 回算受影响节点的所有祖先的勾选状态。
 *
 * 规则：
 *  · 祖先的所有孩子**连同其子树**都全选 → 祖先实心勾；
 *  · 只要有孩子被勾（含半选）→ 祖先半选；
 *  · 否则 → 祖先未选。
 */
function recomputeAncestors(
  index: DeptTreeIndex,
  checked: Set<string>,
  indeterminate: Set<string>,
  changedKey: string,
) {
  let cur = index.parentMap.get(changedKey) ?? null
  const guard = new Set<string>()
  while (cur && !guard.has(cur)) {
    guard.add(cur)
    const childKeys = index.childrenMap.get(cur) ?? []
    const allFull =
      childKeys.length > 0 && childKeys.every((c) => isSubtreeFullyChecked(index, checked, c))
    const anyActive = childKeys.some(
      (c) =>
        checked.has(c) ||
        indeterminate.has(c) ||
        hasSelectedInSubtree(index, checked, c),
    )
    if (allFull) {
      checked.add(cur)
      indeterminate.delete(cur)
    } else {
      checked.delete(cur)
      if (anyActive) indeterminate.add(cur)
      else indeterminate.delete(cur)
    }
    cur = index.parentMap.get(cur) ?? null
  }
}

/**
 * 勾选/取消一个节点，返回新的勾选集合（实心勾）。
 *
 * @param autoSelectChildren 「自动选中全部子部门」：ON 时连带勾上全部可见后代
 */
export function toggleDeptNode(
  index: DeptTreeIndex,
  selected: string[],
  key: string,
  next: boolean,
  autoSelectChildren: boolean,
): string[] {
  const checked = new Set(selected)
  const indeterminate = new Set<string>()
  const descendants = autoSelectChildren ? collectDeptDescendants(index, key) : []

  if (next) {
    checked.add(key)
    descendants.forEach((d) => checked.add(d))
  } else {
    checked.delete(key)
    descendants.forEach((d) => checked.delete(d))
  }
  // 半选集合按新状态重算（受影响的是 key 及其祖先）
  for (const k of [key, ...descendants]) indeterminate.delete(k)
  recomputeAncestors(index, checked, indeterminate, key)
  return [...checked]
}

/**
 * 由「勾选集合」推导完整的显示状态（实心勾 + 半选）。
 * 用于外部直接改 v-model（例如清空、外部塞值）后刷新界面。
 */
export function computeDeptSelection(index: DeptTreeIndex, selected: string[]): DeptSelection {
  const checked = new Set(selected)
  const indeterminate = new Set<string>()
  for (const node of index.nodes) {
    walkUp(index, checked, indeterminate, node.key)
  }
  return { checked: [...checked], indeterminate: [...indeterminate] }
}

/** 自底向上回算一棵子树内的勾选状态 */
function walkUp(
  index: DeptTreeIndex,
  checked: Set<string>,
  indeterminate: Set<string>,
  key: string,
) {
  const childKeys = index.childrenMap.get(key) ?? []
  for (const c of childKeys) walkUp(index, checked, indeterminate, c)
  const allFull =
    childKeys.length > 0 && childKeys.every((c) => isSubtreeFullyChecked(index, checked, c))
  const anyActive = childKeys.some(
    (c) => checked.has(c) || indeterminate.has(c) || hasSelectedInSubtree(index, checked, c),
  )
  if (allFull) {
    checked.add(key)
    indeterminate.delete(key)
  } else if (anyActive) {
    checked.delete(key)
    indeterminate.add(key)
  } else if (checked.has(key)) {
    // 自身被勾但子树没全勾（如「自动选中全部子部门」关闭时）：保持实心勾
    indeterminate.delete(key)
  }
}

/**
 * 取「顶层已选」：自身已选、且没有任何**已选**祖先的节点。
 * 用于触发器上的摘要文案 —— 勾了 集团总部 + 它的孩子时，只显示「集团总部」。
 */
export function topLevelDeptKeys(index: DeptTreeIndex, selected: string[]): string[] {
  const set = new Set(selected)
  return selected.filter((key) => {
    let cur = index.parentMap.get(key) ?? null
    const guard = new Set<string>()
    while (cur && !guard.has(cur)) {
      guard.add(cur)
      if (set.has(cur)) return false
      cur = index.parentMap.get(cur) ?? null
    }
    return true
  })
}

/**
 * 触发器上的摘要文案：
 *   未选 → 空串（由调用方显示 placeholder）
 *   选 1 个 → 「能电BG」
 *   选多个 → 「能电BG 等 3 项」
 */
export function deptSelectionSummary(index: DeptTreeIndex, selected: string[]): string {
  const tops = topLevelDeptKeys(index, selected)
  if (!tops.length) return ''
  const names = tops.map((k) => index.nameMap.get(k) ?? k)
  if (names.length === 1) return names[0]
  return `${names[0]} 等 ${names.length} 项`
}

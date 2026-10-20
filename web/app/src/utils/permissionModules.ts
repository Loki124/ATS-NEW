/**
 * permissionModules.ts — 权限资源「模块」代码 → 中文显示名（单一数据源）
 *
 * 背景：permission_resources.module 存的是英文代码（application / mgmt_unit / …），
 *   直接透给用户不可读。原先映射表是 RoleEditModal.vue 的组件私有常量，资源管理列表
 *   （ResourcesTab.vue）用不到，导致模块筛选与表格列显示裸代码。
 *   故抽到此处共享，角色编辑弹窗与资源管理列表共用同一份定义。
 *
 * 取值与后端 seed 一一对应：apps/core/management/commands/seed_v2_init.py
 *   的资源四元组 (code, 中文名, type, module)。seed 当前共 18 个 module 取值，
 *   本表须与之**全量对齐**；新增模块时必须同步 seed 与本表，否则该模块下资源
 *   在「资源管理」页会被渲染成「—」（误判为「没有模块」）。
 *
 * 注：暂为中文硬编码（沿用 RoleEditModal 既有做法）。若后续要支持多语言展示，
 *   应迁至 locales 语言包按模块 code 做 key，此处退化为默认值兜底。
 */

/** 模块代码 → 中文名。未收录的 code 回退为原 code（不隐藏未知值，便于排查）。 */
export const RESOURCE_MODULE_LABELS: Record<string, string> = {
  candidate: '候选人管理',
  interview: '面试管理',
  demand: '招聘需求',
  position: '职位管理',
  application: '申请管理',
  onboarding: '入职管理',
  referral: '内推管理',
  invitation: '邀约管理',
  talent_pool: '人才库',
  // mou 是 MOU 协议码族（已随 0030 整族停用，仅停用态资源仍以此模块显示）。
  mou: 'MOU',
  // 2026-10-20（0042）：管理单元码族已迁至 recruit:settings:mgmt_unit:*、module
  // 同步为 settings —— 新数据在「模块」筛选里归入「系统设置」、子模块列显示「管理单元」，
  // 与侧边栏「设置中心 → 权限管理 → 管理单元」一致。本条标签仅作历史兜底
  // （未跑 0042 的旧库仍可能读到 module=mgmt_unit），不影响新数据。
  mgmt_unit: '管理单元',
  role: '身份管理',
  // user_role 模块已随 0038 迁移为 settings:users:role_grant（用户身份配置），标签移除
  settings: '系统设置',
  // ↓ 2026-10-19 补齐：下列 4 个模块此前漏收进前端映射表，导致对应资源在
  //   ResourcesTab 模块列显示「—」（误判为无模块）。真值均来自 seed 资源名。
  channel: '渠道管理',
  notification: '通知中心',
  user_app_data_scope: '应用数据范围',
  campus: '校园招聘',
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

// ===== 功能权限树（按编码结构：第 2 段=模块 → 中间段逐层 → 末级权限项）=====
//
// 资源码结构：`recruit:{module}:{中间段…}:{type}:{action}`
//   - 第 1 段恒为 `recruit`（系统编码），跳过；
//   - 第 2 段 = 模块（用 RESOURCE_MODULE_LABELS 中文名）；
//   - 中间段 = 第 3 段…直到「类型段」之前，逐层作为分组节点；
//   - 类型段：MENU 型资源为 `menu`（动作恒 `view`），其余为 BUTTON/字段等，
//     其**末段**为动作（list/create/edit/…）。
// 为忠实「按编码结构」且零遗漏：每个资源都落为一个叶子，分组节点是纯容器，
// 故「既是分组又是叶子」的情况（如某菜单型资源与其按钮同挂一个分组）天然成立。

export interface PermLeaf {
  resourceCode: string
  resourceName: string
  resourceType: string
  /** 末段原始动作码（view/list/create/edit/…），用于叶子小标签 */
  action: string
  isMenu: boolean
}

export interface PermNode {
  /** 路径唯一键（各段以 / 连接），用于展开状态与递归 key */
  key: string
  /** 原始码段（无中文时兜底展示） */
  segment: string
  /** 展示名：模块取中文映射；中间分组取同名 MENU 资源「去菜单后缀」名；否则原始码段 */
  label: string
  /** 仅叶子节点有值 */
  leaf?: PermLeaf
  children: PermNode[]
}

/** 组内排序：分组（含子节点）排在叶子之前，同类型按中文名/key 稳定排序 */
function sortPermNodes(nodes: PermNode[]): void {
  nodes.sort((a, b) => {
    const ag = a.children.length > 0 ? 0 : 1
    const bg = b.children.length > 0 ? 0 : 1
    if (ag !== bg) return ag - bg
    return a.label.localeCompare(b.label, 'zh') || a.key.localeCompare(b.key)
  })
  for (const n of nodes) sortPermNodes(n.children)
}

/**
 * 由全量资源构建「模块 → 中间段逐层 → 末级权限项」的多层树。
 * 数据驱动、无需硬编码子模块清单；新增任意深度的中间段都自动成层。
 *
 * @param resources 权限资源（resourceCode / resourceName / resourceType）
 * @returns 顶层即模块节点数组（depth 0）
 */
export function buildPermissionTree(
  resources: Array<{ resourceCode: string; resourceName: string; resourceType?: string }>,
): PermNode[] {
  const root: PermNode = { key: '', segment: '', label: '', children: [] }

  // 第一遍：按编码结构插入叶子
  for (const r of resources) {
    const segs = (r.resourceCode || '').split(':')
    if (segs[0] === 'recruit') segs.shift()
    if (!segs.length) continue
    const secondLast = segs[segs.length - 2]
    let groupPath: string[]
    let leaf: PermLeaf
    if (secondLast === 'menu') {
      // MENU 型：groupPath 去掉末尾 menu:view；动作恒为 view
      groupPath = segs.slice(0, segs.length - 2)
      leaf = {
        resourceCode: r.resourceCode,
        resourceName: r.resourceName,
        resourceType: r.resourceType ?? 'MENU',
        action: 'view',
        isMenu: true,
      }
    } else {
      // 其余：groupPath 去掉末段动作，末段即动作
      groupPath = segs.slice(0, segs.length - 1)
      leaf = {
        resourceCode: r.resourceCode,
        resourceName: r.resourceName,
        resourceType: r.resourceType ?? '',
        action: segs[segs.length - 1],
        isMenu: false,
      }
    }
    let cur = root
    for (let i = 0; i < groupPath.length; i++) {
      const seg = groupPath[i]
      const key = groupPath.slice(0, i + 1).join('/')
      let child = cur.children.find((c) => c.key === key)
      if (!child) {
        const isModule = i === 0
        child = {
          key,
          segment: seg,
          label: isModule ? RESOURCE_MODULE_LABELS[seg] ?? seg : seg,
          children: [],
        }
        cur.children.push(child)
      }
      cur = child
    }
    cur.children.push({
      key: cur.key ? `${cur.key}/${r.resourceCode}` : r.resourceCode,
      segment: leaf.action,
      label: r.resourceName,
      leaf,
      children: [],
    })
  }

  // 第二遍：用 MENU 叶子的「去菜单后缀名」反哺父分组中文名（数据驱动，无需硬编码）
  for (const r of resources) {
    const segs = (r.resourceCode || '').split(':')
    if (segs[0] === 'recruit') segs.shift()
    if (segs.length < 3) continue
    if (segs[segs.length - 2] !== 'menu') continue
    const groupPath = segs.slice(0, segs.length - 2)
    const label = stripMenuSuffix(r.resourceName)
    if (!label) continue
    let cur = root
    let ok = true
    for (let i = 0; i < groupPath.length; i++) {
      const key = groupPath.slice(0, i + 1).join('/')
      const child = cur.children.find((c) => c.key === key)
      if (!child) {
        ok = false
        break
      }
      cur = child
    }
    if (ok) cur.label = label
  }

  sortPermNodes(root.children)
  return root.children
}

/** 收集节点（含子树）下所有叶子资源码 */
export function collectNodeCodes(node: PermNode): string[] {
  const out: string[] = []
  if (node.leaf) out.push(node.leaf.resourceCode)
  for (const c of node.children) out.push(...collectNodeCodes(c))
  return out
}

/** 收集节点（含子树）下所有「分组节点」的 key（用于展开全部） */
export function collectGroupKeys(node: PermNode, includeSelf = false): string[] {
  const out: string[] = []
  if (includeSelf && node.children.length) out.push(node.key)
  for (const c of node.children) {
    if (c.children.length) out.push(c.key)
    out.push(...collectGroupKeys(c, false))
  }
  return out
}

export function nodeAllChecked(node: PermNode, selected: ReadonlySet<string>): boolean {
  const codes = collectNodeCodes(node)
  return codes.length > 0 && codes.every((c) => selected.has(c))
}

export function nodeIndeterminate(node: PermNode, selected: ReadonlySet<string>): boolean {
  const codes = collectNodeCodes(node)
  const some = codes.some((c) => selected.has(c))
  return some && !nodeAllChecked(node, selected)
}

export function nodeSelectedCount(node: PermNode, selected: ReadonlySet<string>): number {
  return collectNodeCodes(node).filter((c) => selected.has(c)).length
}

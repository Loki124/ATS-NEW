/**
 * 部门树路径回归测试（2026-10-21 「归属部门回显 undefined/产品中心」修复）
 *
 * 真实故障：新建直播间 / 客服部门 / 轮岗安排 的「归属部门」下拉选中后，
 * 输入框回显成「undefined/产品中心」——多级部门（父级存在）的路径全脏。
 *
 * 根因：`utils/campus.ts` 的 `buildDeptTree` 在向上回溯祖先时走了 `nodeById`，
 * 而树节点对象只有 `key / label / name / children`、**没有 `id` 与 `parentId`**，
 * 于是第二轮起 `nameById.get(String(cur.id))` 落空 → 兜底成字符串 "undefined"，
 * 路径变成 "undefined/产品中心"。
 *
 * 锁两条契约：
 * 1. label = 完整路径（根→当前），任一层级不得出现 "undefined"；
 * 2. 停用部门不可选（不进树），但其**启用后代**仍挂在根层且路径显示祖先真实名称。
 */
import { describe, it, expect } from 'vitest'
import { buildDeptTree } from '../campus'

/** root(0) → grp(1) → bu(2) → deep(3)，另有停用节点与同���子节点 */
const DEPTS = [
  { id: 'root', name: '集团总部', code: 'ROOT', parentId: null, status: 'ACTIVE' },
  { id: 'grp', name: '能良', code: 'GRP', parentId: 'root', status: 'ACTIVE' },
  { id: 'bu', name: '能智BG', code: 'BU', parentId: 'grp', status: 'ACTIVE' },
  { id: 'deep', name: '产品中心', code: 'DEEP', parentId: 'bu', status: 'ACTIVE' },
  { id: 'other', name: '运营中心', code: 'OTH', parentId: 'bu', status: 'ACTIVE' },
  { id: 'off', name: '已停用BU', code: 'OFF', parentId: 'root', status: 'INACTIVE' },
  { id: 'offChild', name: '停用BU下的子部门', code: 'OFFC', parentId: 'off', status: 'ACTIVE' },
]

/** 在树里找节点的 label（深度优先） */
function findLabel(nodes: any[], key: string): string | undefined {
  for (const n of nodes) {
    if (n.key === key) return n.label
    if (n.children) {
      const hit = findLabel(n.children, key)
      if (hit !== undefined) return hit
    }
  }
  return undefined
}

/** 收集整棵树的所有 label */
function allLabels(nodes: any[]): string[] {
  const out: string[] = []
  for (const n of nodes) {
    out.push(n.label)
    if (n.children) out.push(...allLabels(n.children))
  }
  return out
}

describe('buildDeptTree 部门路径', () => {
  it('多级部门的 label 是完整路径，不含 undefined', () => {
    const tree = buildDeptTree(DEPTS as any)
    expect(findLabel(tree, 'deep')).toBe('集团总部/能良/能智BG/产品中心')
    expect(findLabel(tree, 'bu')).toBe('集团总部/能良/能智BG')
    expect(findLabel(tree, 'grp')).toBe('集团总部/能良')
    expect(findLabel(tree, 'root')).toBe('集团总部')
  })

  it('整棵树没有任何 label 含 "undefined"', () => {
    const tree = buildDeptTree(DEPTS as any)
    const dirty = allLabels(tree).filter((l) => String(l).includes('undefined'))
    expect(dirty).toEqual([])
  })

  it('同名兄弟节点靠完整路径区分', () => {
    const tree = buildDeptTree(DEPTS as any)
    expect(findLabel(tree, 'deep')).not.toBe(findLabel(tree, 'other'))
  })

  it('停用部门不可选（不进树）', () => {
    const tree = buildDeptTree(DEPTS as any)
    expect(findLabel(tree, 'off')).toBeUndefined()
  })

  it('停用祖先的启用后代仍可选，且路径显示祖先真实名称', () => {
    const tree = buildDeptTree(DEPTS as any)
    // 父不可选 → 子节点提到根层，但路径保留祖先名
    expect(findLabel(tree, 'offChild')).toBe('集团总部/已停用BU/停用BU下的子部门')
    expect(findLabel(tree, 'offChild')).not.toContain('undefined')
  })
})

/**
 * 真实数据快照（dev 库 departments 表，2026-10-21 取样 8 行）。
 * 字段名按前端实际收到的形态：isActive（后端 is_active 经 camelize）+ parentId（parent_id）。
 * 这组数据正是故障现场：产品中心 的父级为「集团总部」，修复前回显成「undefined/产品中心」。
 */
const REAL_DEPTS = [
  { id: 'dMCxP', name: '集团总部', parentId: null, isActive: true },
  { id: 'CyCd3', name: '能良', parentId: 'dMCxP', isActive: true },
  { id: 'HAxdC', name: '能智BG', parentId: 'CyCd3', isActive: true },
  { id: 'J4_Mb', name: '产品中心', parentId: 'dMCxP', isActive: true },
  { id: 'Qd_gq', name: '运营中心', parentId: 'J4_Mb', isActive: true },
  { id: 'msx5F', name: '技术中心', parentId: 'dMCxP', isActive: true },
  { id: 'h1U_se', name: '醒市', parentId: 'dMCxP', isActive: true },
  { id: 'VERIFY_DEPT', name: '验收部门', parentId: null, isActive: true },
]

describe('buildDeptTree 真实部门数据（dev 库快照）', () => {
  it('产品中心的完整路径是「集团总部/产品中心」，不再是 undefined/产品中心', () => {
    const tree = buildDeptTree(REAL_DEPTS as any)
    expect(findLabel(tree, 'J4_Mb')).toBe('集团总部/产品中心')
  })

  it('运营中心（三级）路径完整', () => {
    const tree = buildDeptTree(REAL_DEPTS as any)
    expect(findLabel(tree, 'Qd_gq')).toBe('集团总部/产品中心/运营中心')
  })

  it('能智BG 路径完整', () => {
    const tree = buildDeptTree(REAL_DEPTS as any)
    expect(findLabel(tree, 'HAxdC')).toBe('集团总部/能良/能智BG')
  })

  it('全树无 undefined 文案', () => {
    const tree = buildDeptTree(REAL_DEPTS as any)
    expect(allLabels(tree).filter((l) => String(l).includes('undefined'))).toEqual([])
  })
})

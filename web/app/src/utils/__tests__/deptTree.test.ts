/**
 * 部门树筛选 · 勾选传播规则（2026-10-22）
 *
 * 这些规则错起来**不报错**，只是「筛不出数据」或「多筛出数据」，
 * 所以必须用单测锁死：
 *  1. 停用部门默认不进树；开关打开后进树并带「停用」标记；
 *  2. 父部门不可见时，启用后代上提到**最近的可见祖先**（不是甩到根层）；
 *  3. 「自动选中全部子部门」ON → 勾父即勾满后代；OFF → 只勾自己；
 *  4. 向上回算：孩子全选 → 父实心勾；孩子部分选 → 父半选；
 *  5. 取消勾选会级联撤销；
 *  6. 摘要只列「顶层已选」（勾了父就不重复列它的孩子）。
 */
import { describe, it, expect } from 'vitest'
import {
  buildDeptFilterTree,
  computeDeptSelection,
  deptSelectionSummary,
  toggleDeptNode,
  topLevelDeptKeys,
} from '../deptTree'

/**
 * 集团总部
 * ├─ 能电BG
 * │  ├─ 能食电器
 * │  │  └─ 经营者管理部
 * │  └─ 经营管理部
 * └─ 能战BG（停用）
 *    └─ 清醒电器（启用，父停用）
 */
const DEPTS = [
  { id: 'root', name: '集团总部', parentId: null, status: 'ACTIVE' },
  { id: 'bg-dian', name: '能电BG', parentId: 'root', status: 'ACTIVE' },
  { id: 'dept-shi', name: '能食电器', parentId: 'bg-dian', status: 'ACTIVE' },
  { id: 'dept-jing', name: '经营者管理部', parentId: 'dept-shi', status: 'ACTIVE' },
  { id: 'dept-jing', name: '经营管理部', parentId: 'bg-dian', status: 'ACTIVE' },
  { id: 'bg-zhan', name: '能战BG', parentId: 'root', status: 'INACTIVE' },
  { id: 'dept-xing', name: '清醒电器', parentId: 'bg-zhan', status: 'ACTIVE' },
]

const keysOf = (nodes: any[]): string[] => {
  const out: string[] = []
  const walk = (list: any[]) => {
    for (const n of list) {
      out.push(n.key)
      if (n.children?.length) walk(n.children)
    }
  }
  walk(nodes)
  return out
}

describe('buildDeptFilterTree 树的构建', () => {
  it('① 默认只显示启用部门（停用部门不进树）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const keys = keysOf(t.nodes)
    expect(keys).not.toContain('bg-zhan')
    expect(keys).toContain('bg-dian')
  })

  it('② 「展示历史停用部门」打开 → 停用部门进树且标记为停用', () => {
    const t = buildDeptFilterTree(DEPTS as any, { includeInactive: true })
    expect(keysOf(t.nodes)).toContain('bg-zhan')
    expect(t.inactiveMap.get('bg-zhan')).toBe(true)
    expect(t.inactiveMap.get('bg-dian')).toBe(false)
  })

  it('③ 父部门不可见 → 启用后代上提到最近的可见祖先（不是根层）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    // 清醒电器的父「能战BG」停用不可见 → 上提到「集团总部」
    expect(t.parentMap.get('dept-xing')).toBe('root')
    // 能战BG 可见时 → 清醒电器挂回能战BG
    const t2 = buildDeptFilterTree(DEPTS as any, { includeInactive: true })
    expect(t2.parentMap.get('dept-xing')).toBe('bg-zhan')
  })

  it('④ 部门 id 数字/字符串混用不影响层级', () => {
    const t = buildDeptFilterTree([
      { id: 1, name: 'A', parentId: null, status: 'ACTIVE' },
      { id: 2, name: 'B', parentId: 1, status: 'ACTIVE' },
    ] as any)
    expect(t.parentMap.get('2')).toBe('1')
  })
})

describe('勾选传播', () => {
  it('⑤ 「自动选中全部子部门」ON → 勾父即勾满全部可见后代', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'bg-dian', true, true)
    expect(checked).toContain('bg-dian')
    expect(checked).toContain('dept-shi')
    expect(checked).toContain('dept-jing')
    expect(checked).toContain('dept-jing')
  })

  it('⑥ 「自动选中全部子部门」OFF → 只勾自己，后代不动', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'bg-dian', true, false)
    expect(checked).toEqual(['bg-dian'])
  })

  it('⑦ 孩子全选 → 父自动实心勾（向上回算）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    let checked = toggleDeptNode(t, [], 'dept-shi', true, true)
    checked = toggleDeptNode(t, checked, 'dept-jing', true, true)
    const state = computeDeptSelection(t, checked)
    expect(state.checked).toContain('bg-dian')
    expect(state.indeterminate).not.toContain('bg-dian')
  })

  it('⑧ 孩子部分选 → 父显示半选（不实心勾）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'dept-shi', true, true)
    const state = computeDeptSelection(t, checked)
    expect(state.checked).toContain('dept-shi')
    expect(state.checked).not.toContain('bg-dian')
    expect(state.indeterminate).toContain('bg-dian')
  })

  it('⑨ 取消勾选会级联撤销后代', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const on = toggleDeptNode(t, [], 'bg-dian', true, true)
    const off = toggleDeptNode(t, on, 'bg-dian', false, true)
    expect(off).not.toContain('dept-shi')
    expect(off).not.toContain('dept-jing')
    expect(off).not.toContain('dept-jing')
    expect(off).not.toContain('bg-dian')
  })

  it('⑩ 半选节点不计入「已选」（避免把父部门一起筛进去）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'dept-shi', true, true)
    const state = computeDeptSelection(t, checked)
    expect(state.checked).toContain('dept-shi')
    expect(state.checked).not.toContain('bg-dian')
  })
})

describe('摘要文案', () => {
  it('⑪ 选 1 个 → 显示部门名', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    expect(deptSelectionSummary(t, ['dept-shi'])).toBe('能食电器')
  })

  it('⑫ 勾了父 + 孩子 → 只列顶层已选，不重复列孩子', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'bg-dian', true, true)
    expect(topLevelDeptKeys(t, checked)).toEqual(['bg-dian'])
    expect(deptSelectionSummary(t, checked)).toBe('能电BG')
  })

  it('⑬ 多个不相干的部门 → 「第一个 等 N 项」', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    const checked = toggleDeptNode(t, [], 'dept-shi', true, true)
    // 清醒电器挂在「集团总部」下，与「能食电器」不同支 → 两个顶层已选
    const next = toggleDeptNode(t, checked, 'dept-xing', true, true)
    expect(topLevelDeptKeys(t, next).sort()).toEqual(['dept-shi', 'dept-xing'])
    expect(deptSelectionSummary(t, next)).toBe('能食电器 等 2 项')
  })

  it('⑬-2 兄弟节点全选 → 父部门自动补进已选（级联语义：父也算选中）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    let checked = toggleDeptNode(t, [], 'dept-shi', true, true)
    checked = toggleDeptNode(t, checked, 'dept-jing', true, true)
    // 能电BG 的两个孩子都被覆盖 → 父部门实心勾，且计入已选
    const state = computeDeptSelection(t, checked)
    expect(state.checked).toContain('bg-dian')
    expect(deptSelectionSummary(t, checked)).toBe('能电BG')
  })

  it('⑭ 未选 → 空串（由调用方显示占位符）', () => {
    const t = buildDeptFilterTree(DEPTS as any)
    expect(deptSelectionSummary(t, [])).toBe('')
  })
})

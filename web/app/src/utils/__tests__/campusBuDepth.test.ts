/**
 * BU（二级部门）层级口径回归测试（2026-10-21 BU 400 修复）
 *
 * 锁住一条**跨栈**契约的前端侧：BU 下拉选项 = 0 基层级 depth==2 的部门。
 *
 * 起因（真实故障）：后端 `is_bu_depth` 历史上按「parent 存在且 parent.parent 为空」
 * 实现 = 0 基第 1 级（事业群），与本文件的 `buOptions`（取 `level === 2`）差一级，
 * 后果是「下拉里选得出的 BU 一提交就被后端 400 拒绝」。
 *
 * 口径真源：根=0、事业群=1、BU=2、三级部门=3
 * （PRD《校招生管理需求规格与实施方案》§6.1 + 后端 `apps/core/dept_depth.py`）。
 *
 * 后端侧同一契约的锁在 `apps/django/apps/core/tests/test_dept_depth.py` ——
 * 那边把本文件的 level 算法复刻到 Python 并逐节点比对，两侧都钉在同一个数字 2 上。
 */
import { describe, it, expect } from 'vitest'
import { buOptions, deptLevelMap } from '../campus'

/** 构造一棵 0 基层级的部门树：root(0) -> grp(1) -> bu(2) -> deep(3) */
const DEPTS = [
  { id: 'root', name: '集团总部', code: 'ROOT', parentId: null, status: 'ACTIVE' },
  { id: 'grp', name: '能良', code: 'GRP', parentId: 'root', status: 'ACTIVE' },
  { id: 'bu', name: '能智BG', code: 'BU', parentId: 'grp', status: 'ACTIVE' },
  { id: 'deep', name: '运营中心', code: 'DEEP', parentId: 'bu', status: 'ACTIVE' },
  { id: 'bu2', name: '产品中心BU', code: 'BU2', parentId: 'root', status: 'ACTIVE' },
  { id: 'bu2child', name: '产品中心-子', code: 'BU2C', parentId: 'bu2', status: 'ACTIVE' },
  { id: 'off', name: '已停用BU', code: 'OFF', parentId: 'root', status: 'INACTIVE' },
]

describe('campus 部门层级口径（BU = 0 基 depth 2）', () => {
  it('deptLevelMap 采用 0 基编号：根=0、其子=1、孙=2', () => {
    const map = deptLevelMap(DEPTS as any)
    expect(map.root).toBe(0)
    expect(map.grp).toBe(1)
    expect(map.bu).toBe(2)
    expect(map.deep).toBe(3)
  })

  it('buOptions 只返回 depth==2 的节点（不含事业群、不含三级部门）', () => {
    const map = deptLevelMap(DEPTS as any)
    const opts = buOptions(DEPTS as any, map)
    const values = opts.map((o) => o.value)

    expect(values).toContain('bu')
    expect(values).toContain('bu2child')
    // 事业群（depth 1）不是 BU
    expect(values).not.toContain('grp')
    expect(values).not.toContain('bu2')
    // 三级部门（depth 3）不是 BU
    expect(values).not.toContain('deep')
    // 根不是 BU
    expect(values).not.toContain('root')
  })

  it('停用部门不出现在 BU 下拉里', () => {
    const map = deptLevelMap(DEPTS as any)
    const values = buOptions(DEPTS as any, map).map((o) => o.value)
    expect(values).not.toContain('off')
  })

  it('BU 下拉 label 为完整路径，便于同名 BU 区分', () => {
    const map = deptLevelMap(DEPTS as any)
    const opts = buOptions(DEPTS as any, map)
    const bu = opts.find((o) => o.value === 'bu')
    expect(bu?.label).toBe('集团总部/能良/能智BG')
  })
})

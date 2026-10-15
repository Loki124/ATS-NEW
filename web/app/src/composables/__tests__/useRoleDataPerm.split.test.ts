/**
 * 读 / 写拆分（2026-10-15）逻辑层单测。
 *
 * 覆盖拆分后新增的三处行为契约：
 *   1. `writeBadge` 徽标语义 —— 尤其是「配了范围却 0 动作」必须是 error（fail-closed 只读），
 *      不能因为 actions.length===0 与「未配置」数值相同就显示成绿色（颜色撒谎）；
 *   2. `readDirty` / `writeDirty` 分别标脏 —— 只改一边不在另一边亮圆点，
 *      且 `readDirty || writeDirty === isDirty`（两个页签合起来不漏报）；
 *   3. `validate()` 的 `errorKinds` 归因 —— 读范围报错归 read、写范围报错归 write，
 *      保存前预校验靠它把用户送到正确的页签。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'

const h0 = vi.hoisted(() => ({
  getRoleDataPerm: vi.fn(),
  getRoleDataPermOptions: vi.fn(),
  saveRoleDataPerm: vi.fn(),
}))

vi.mock('@/api/data-permission', () => ({
  getRoleDataPerm: h0.getRoleDataPerm,
  getRoleDataPermOptions: h0.getRoleDataPermOptions,
  saveRoleDataPerm: h0.saveRoleDataPerm,
}))

import { useRoleDataPerm, writeBadge } from '@/composables/useRoleDataPerm'
import type { ModulePerm, WritePerm } from '@/api/data-permission'

const write = (over: Partial<WritePerm> = {}): WritePerm => ({
  mode: 'none',
  expr: '',
  groups: [],
  actions: [],
  ...over,
})

/** 读侧带 1 组 1 条的合法 scope 模块（保证 readDirty 基线为 false） */
const scopeRead = () => ({
  mode: 'scope' as const,
  expr: '',
  groups: [{
    id: 'g1',
    expr: '',
    conditions: [{ id: 'c1', kind: 'relationship' as const, dimension: 'dept', operator: 'in', values: [{ id: 'd1', label: '技术部' }] }],
  }],
})

const module = (over: Partial<ModulePerm> = {}): ModulePerm => ({
  moduleKey: 'demand',
  featureGranted: true,
  ...scopeRead(),
  write: write(),
  ...over,
} as ModulePerm)

/** 深拷贝两份基线分别喂 saved / draft（同一引用会导致两边同时变，脏检查恒 false） */
function setup(modules: ModulePerm[]) {
  const roleId = ref('role-1')
  const dp = useRoleDataPerm(roleId)
  dp.saved.value = JSON.parse(JSON.stringify(modules))
  dp.draft.value = JSON.parse(JSON.stringify(modules))
  return dp
}

beforeEach(() => {
  h0.getRoleDataPerm.mockReset()
  h0.getRoleDataPermOptions.mockReset().mockResolvedValue({ modules: [], actionRegistry: [], presetPackages: [] })
  h0.saveRoleDataPerm.mockReset()
})

describe('writeBadge 徽标语义（读/写两处 UI 共用的单一判定）', () => {
  it('未配置（none）→ 中性「未配置」', () => {
    expect(writeBadge(write({ mode: 'none' }))).toEqual({
      tone: 'default', key: 'dataperm.write.badge.none', n: 0,
    })
  })

  it('write 缺省（undefined）同样视为未配置', () => {
    expect(writeBadge(undefined).key).toBe('dataperm.write.badge.none')
  })

  it('全部可写（all）→ 成功色', () => {
    expect(writeBadge(write({ mode: 'all' }))).toEqual({
      tone: 'success', key: 'dataperm.write.badge.all', n: 0,
    })
  })

  it('配了范围却 0 动作 → error（fail-closed 只读，不可因 length===0 显示成绿）', () => {
    const badge = writeBadge(write({ mode: 'owner', actions: [] }))
    expect(badge.tone).toBe('error')
    expect(badge.key).toBe('dataperm.write.badge.zero')
    // 与「未配置」必须可区分：同 tone 会让两种截然不同的状态看起来一样
    expect(badge.tone).not.toBe(writeBadge(write({ mode: 'none' })).tone)
  })

  it('已授权 n 项 → 中性 + 带出 n', () => {
    expect(writeBadge(write({ mode: 'owner', actions: ['view', 'edit'] }))).toEqual({
      tone: 'default', key: 'dataperm.write.badge.active', n: 2,
    })
  })
})

describe('readDirty / writeDirty 分别标脏', () => {
  it('初始（saved 与 draft 一致）三项全为 false', () => {
    const dp = setup([module()])
    expect(dp.isDirty.value).toBe(false)
    expect(dp.readDirty.value).toBe(false)
    expect(dp.writeDirty.value).toBe(false)
  })

  it('只改写动作 → 仅 writeDirty 翻 true，读侧不亮圆点', () => {
    const dp = setup([module()])
    dp.setWriteActions('demand', ['view', 'edit'])
    expect(dp.writeDirty.value).toBe(true)
    expect(dp.readDirty.value).toBe(false)
    expect(dp.isDirty.value).toBe(true)
  })

  it('只改读范围 → 仅 readDirty 翻 true', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'all')
    expect(dp.readDirty.value).toBe(true)
    expect(dp.writeDirty.value).toBe(false)
  })

  it('readDirty || writeDirty 恒等于 isDirty（两页签圆点合起来不漏报）', () => {
    const dp = setup([module(), module({ moduleKey: 'process', mode: 'all', groups: [] })])
    dp.setWriteActions('demand', ['view'])
    expect(dp.readDirty.value || dp.writeDirty.value).toBe(dp.isDirty.value)
    dp.setGroups('process', [])
    expect(dp.readDirty.value || dp.writeDirty.value).toBe(dp.isDirty.value)
  })

  it('write mode=all 时清空 groups 不产生假脏（与 submit 收敛口径一致）', () => {
    const dp = setup([module({ write: write({ mode: 'scope', expr: '1', groups: [{ id: 'g', expr: '', conditions: [] }], actions: ['view'] }) })])
    expect(dp.writeDirty.value).toBe(false)
    dp.setWriteMode('demand', 'all')
    expect(dp.writeDirty.value).toBe(true)
    dp.setWriteActions('demand', ['view'])
    expect(dp.writeDirty.value).toBe(true)
  })
})

describe('validate() 的 errorKinds 归因（决定预校验跳哪个页签）', () => {
  it('写范围配了却 0 动作 → 归因 write', () => {
    const dp = setup([module({ mode: 'all', groups: [], write: write({ mode: 'owner', actions: [] }) })])
    const bad = dp.validate()
    expect(bad).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('write')
    expect(dp.errors.value.demand).toContain('未勾选任何动作')
  })

  it('写范围 scope 但无条件 → 归因 write', () => {
    const dp = setup([module({ mode: 'all', groups: [], write: write({ mode: 'scope', actions: ['view'] }) })])
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('write')
    expect(dp.errors.value.demand).toContain('至少配置 1 条')
  })

  it('读范围 scope 但无条件组 → 归因 read', () => {
    const dp = setup([module({ mode: 'scope', groups: [] })])
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('read')
  })

  it('读范围组间表达式非法 → 归因 read', () => {
    const dp = setup([module({ mode: 'scope', expr: '9' })])
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('read')
  })

  it('同一模块读写都合法 → bad 为空且 errorKinds 清空', () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view', 'edit'] }) })])
    expect(dp.validate()).toEqual([])
    expect(dp.errorKinds.value).toEqual({})
  })

  it('写错误优先于读错误（同模块只报第一条，与原行为一致）', () => {
    // 读侧也非法（scope 无条件组），但写侧先命中 → 归因 write
    const dp = setup([module({ mode: 'scope', groups: [], write: write({ mode: 'owner', actions: [] }) })])
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('write')
  })
})

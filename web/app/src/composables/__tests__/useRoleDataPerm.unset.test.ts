/**
 * 「未配置」（unset）显式态逻辑层单测 —— 卡 1.2。
 *
 * 测的是本仓 god composable 的标准手法：**把纯逻辑经由 draft/saved 直接驱动，
 * 不 mount 组件**。理由是 ModulePermCard 只做渲染，而真正会出事的地方全在
 * 状态转移与 payload 序列化上（组件测不到）。
 *
 * 覆盖三条契约：
 *   1. setMode 切到 'unset' 时**清空 groups 与 expr**（产品已拍板：切走即清）——
 *      否则管理员切走再切回会看到一条"还在的旧规则"，而后端其实已把行删了；
 *   2. submit **原样下发 'unset'**（不是不下发）。工单原方案说 unset 模块
 *      不下发，但后端 upsert_modules 对未提及的模块是"不动"——不下发等于
 *      管理员点保存后什么都没发生且返回 200（静默失效）；
 *   3. unset 在 validate() 中**不报错**（它是合法态，不是半个 scope），
 *      且不会被「无权限二次确认」误伤（那属RoleEditModal，只验语义不进列表）。
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

import { useRoleDataPerm, MODULE_KEYS, newGroup } from '@/composables/useRoleDataPerm'
import type { ModulePerm, WritePerm } from '@/api/data-permission'

const write = (over: Partial<WritePerm> = {}): WritePerm => ({
  mode: 'none',
  expr: '',
  groups: [],
  actions: [],
  ...over,
})

/** 带 1 组 1 条条件的合法 scope 模块（readDirty 基线为 false） */
const scopeRead = () => ({
  mode: 'scope' as const,
  expr: '',
  groups: [{
    id: 'g1',
    expr: '',
    conditions: [{
      id: 'c1', kind: 'relationship' as const, dimension: 'dept',
      operator: 'in', values: [{ id: 'd1', label: '技术部' }],
    }],
  }],
})

const module = (over: Partial<ModulePerm> = {}): ModulePerm => ({
  moduleKey: 'demand',
  featureGranted: true,
  ...scopeRead(),
  write: write(),
  ...over,
} as ModulePerm)

/** 深拷贝两份基线分别喂 saved / draft（同引用会让两边同时变，脏检查恒 false） */
function setup(modules: ModulePerm[]) {
  const roleId = ref('role-1')
  const dp = useRoleDataPerm(roleId)
  dp.saved.value = JSON.parse(JSON.stringify(modules))
  dp.draft.value = JSON.parse(JSON.stringify(modules))
  return dp
}

beforeEach(() => {
  h0.getRoleDataPerm.mockReset()
  h0.getRoleDataPermOptions.mockReset()
    .mockResolvedValue({ modules: [], actionRegistry: [], presetPackages: [] })
  h0.saveRoleDataPerm.mockReset()
    .mockResolvedValue({ modules: [], writeNormalized: [] })
})

describe("setMode 切到 'unset'（卡 1.2：切走即清）", () => {
  it('清空 groups', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    expect(dp.draft.value[0].groups).toEqual([])
  })

  it('清空 expr', () => {
    const dp = setup([module({ ...scopeRead(), expr: '1' })])
    dp.setMode('demand', 'unset')
    expect(dp.draft.value[0].expr).toBe('')
  })

  it('mode 落为 unset', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    expect(dp.draft.value[0].mode).toBe('unset')
  })

  it('清空后 readDirty 为true（确实改了东西，不能静默保存成什么都没发生）', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    expect(dp.readDirty.value).toBe(true)
  })

  it('从 unset 切回 scope 时不复活旧规则（组内容为新建的空组）', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    dp.setMode('demand', 'scope')
    const g = dp.draft.value[0].groups
    expect(g).toHaveLength(1)
    // 旧条件（技术部 in）不得复活：管理员看到"还在的旧规则"会以为系统没清干净。
    // newGroup() 会预置一条**未填值**的默认条件（dept/in/values:[]），
    // 这不是残留 —— 判据是它没有被填上旧值。
    expect(g[0].conditions).toHaveLength(1)
    expect(g[0].conditions[0].values).toEqual([])
  })

  it('已是 unset 时再切 unset 不产生额外变更（幂等）', () => {
    const dp = setup([module({ mode: 'unset', expr: '', groups: [] })])
    expect(dp.readDirty.value).toBe(false)
    dp.setMode('demand', 'unset')
    expect(dp.readDirty.value).toBe(false)
  })

  it('不写侧：切 unset 不影响 write 配置', () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view'] }) })])
    dp.setMode('demand', 'unset')
    const w = dp.draft.value[0].write
    expect(w?.mode).toBe('owner')
    expect(w?.actions).toEqual(['view'])
  })
})

describe("submit 下发 'unset'（卡 1.2：显式下发，不是省略）", () => {
  it('payload 里该模块的 mode 确实是 unset（省略下发=静默失效）', async () => {
    const dp = setup([module({ moduleKey: 'demand', mode: 'unset', expr: '', groups: [] })])
    dp.setMode('demand', 'all') // 让 isDirty 成立，submit 不会被前置拦截
    dp.setMode('demand', 'unset')
    await dp.submit()

    expect(h0.saveRoleDataPerm).toHaveBeenCalled()
    const payload = h0.saveRoleDataPerm.mock.calls[0][1]
    const dm = payload.modules.find((m: any) => m.moduleKey === 'demand')
    expect(dm.mode).toBe('unset')
  })

  it('unset 模块照常出现在 payload 里（不因"未配置"被过滤掉）', async () => {
    const all = MODULE_KEYS.map((k) => module({
      moduleKey: k, mode: 'unset', expr: '', groups: [],
    }))
    const dp = setup(all)
    dp.setMode('demand', 'all')
    dp.setMode('demand', 'unset')
    await dp.submit()

    const payload = h0.saveRoleDataPerm.mock.calls[0][1]
    expect(payload.modules).toHaveLength(MODULE_KEYS.length)
    expect(payload.modules.map((m: any) => m.moduleKey).sort())
      .toEqual([...MODULE_KEYS].sort())
  })

  it('unset 时 expr/groups 一并收敛为空（不留幽灵规则）', async () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    await dp.submit()
    const dm = h0.saveRoleDataPerm.mock.calls[0][1]
      .modules.find((m: any) => m.moduleKey === 'demand')
    expect(dm.expr).toBe('')
    expect(dm.groups).toEqual([])
  })

  it('unset 时 write 段仍整段下发（P0-1：漏传会静默抹掉操作权限）', async () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view'] }) })])
    dp.setMode('demand', 'unset')
    await dp.submit()
    const dm = h0.saveRoleDataPerm.mock.calls[0][1]
      .modules.find((m: any) => m.moduleKey === 'demand')
    expect(dm.write).toEqual({ mode: 'owner', expr: '', groups: [], actions: ['view'] })
  })
})

describe("validate() 对 'unset' 的处理", () => {
  it('unset 是合法态，不报任何错', () => {
    const dp = setup([module({ mode: 'unset', expr: '', groups: [] })])
    expect(dp.validate()).toEqual([])
  })

  it('unset 不被要求"至少配置 1 条条件"（那是 scope 的约束）', () => {
    const dp = setup([module({ mode: 'unset', expr: '', groups: [] })])
    dp.validate()
    expect(dp.errors.value.demand).toBeUndefined()
  })

  it('unset 也不进「无权限二次确认」（语义正确：未配置 != 无权限）', () => {
    const dp = setup([module({ mode: 'unset', expr: '', groups: [] })])
    // RoleEditModal 里确认名单为 filter(m => m.mode === 'none')；
    // 这里锁住"unset 不等于 none"这条不变式。
    const noneList = dp.draft.value.filter((m) => m.mode === 'none')
    expect(noneList).toHaveLength(0)
  })

  it('unset 仍受写范围校验约束（配了写范围却不勾动作照样拦）', () => {
    const dp = setup([module({
      mode: 'unset', expr: '', groups: [],
      write: write({ mode: 'owner', actions: [] }),
    })])
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errorKinds.value.demand).toBe('write')
  })
})

describe('newGroup 与 unset 交互的边界', () => {
  it('切到 unset 后 groups 为空数组而非 undefined（serialize 不崩）', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset')
    expect(Array.isArray(dp.draft.value[0].groups)).toBe(true)
    expect(dp.draft.value[0].groups).toHaveLength(0)
  })

  it('newGroup() 产出可用的组（预置一条未填值的默认条件）', () => {
    const g = newGroup()
    // newGroup() 预置一条默认条件（方便直接选维度/运算符），但**值必须为空**：
    // 若它自带已填值，切回 scope 就等于凭空多出一条范围，权限会突然被放大。
    expect(g.conditions).toHaveLength(1)
    expect(g.conditions[0].values).toEqual([])
    expect(g.id).toBeTruthy()
  })
})

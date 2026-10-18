/**
 * 配置卡「同排紧凑版」逻辑层单测（2026-10-18 兵哥原型）。
 *
 * 背景：ModulePermCard 按原型重构成两行结构（标题行 + 虚线规则框），
 * 渲染只认三个新纯逻辑的产出，故按本仓标准手法直接单测 composable，不 mount 组件：
 *   1. previewTags / previewGroupText —— 规则框标签链的数据源。
 *      与 previewOf 的差异只是「拆不拆括号」：逐组一个标签、组间默认 OR；
 *      🔴 组间自定义表达式（如「1 且 2」）必须整句单标签 —— 扁平标签 + UI 的「或」
 *      连接词会把「且」渲染成「或」，属放大权限的安全语义错误。
 *   2. resetModule —— 卡内「重置」：只还原本模块读范围（mode/expr/groups/templateDrifts），
 *      不碰 write 半边（写范围归操作权限页签的卡管），并清掉该模块的校验错误。
 *   3. moduleReadDirty —— 模块粒度脏检查，驱动「重置」显隐；
 *      只反映本卡：改别的模块不算本卡脏（否则每张卡都亮重置，逼管理员全量放弃）。
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

import {
  useRoleDataPerm, previewTags, previewGroupText, previewOf,
} from '@/composables/useRoleDataPerm'
import type { ModulePerm, WritePerm } from '@/api/data-permission'

const write = (over: Partial<WritePerm> = {}): WritePerm => ({
  mode: 'none',
  expr: '',
  groups: [],
  actions: [],
  ...over,
})

/** 部门 ∈ [技术部] 的关系条件（renderCondition 输出「部门 属于 [技术部]」） */
const deptCond = (label = '技术部') => ({
  id: 'c1',
  kind: 'relationship' as const,
  dimension: 'dept',
  operator: 'in',
  values: [{ id: 'd1', label }],
})

/** 带 1 组 1 条条件的合法 scope 模块 */
const scopeRead = () => ({
  mode: 'scope' as const,
  expr: '',
  groups: [{ id: 'g1', expr: '', conditions: [deptCond()] }],
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

describe('previewTags：规则框标签链（2026-10-18 原型 .tag-list）', () => {
  it('每组一个标签，组间默认 OR（与 previewOf 拆括号后同源）', () => {
    const m = module({
      groups: [
        { id: 'g1', expr: '', conditions: [deptCond('技术部')] },
        { id: 'g2', expr: '', conditions: [deptCond('产品部')] },
      ],
    })
    expect(previewTags(m)).toEqual(['部门 属于 [技术部]', '部门 属于 [产品部]'])
    // 与整句预览同口径：只是拆掉括号与「或」连接词
    expect(previewOf(m)).toBe('（部门 属于 [技术部]） 或 （部门 属于 [产品部]）')
  })

  it('组内多条件按且(AND) 合并进同一个标签', () => {
    const m = module({
      groups: [{
        id: 'g1',
        expr: '',
        conditions: [deptCond('技术部'), deptCond('北京')],
      }],
    })
    expect(previewTags(m)).toEqual(['部门 属于 [技术部] 且 部门 属于 [北京]'])
  })

  it('🔴 组间自定义表达式（且）不拆标签链：整句单标签，防「或」连接词拆错逻辑', () => {
    const m = module({
      expr: '1 and 2',
      groups: [
        { id: 'g1', expr: '', conditions: [deptCond('技术部')] },
        { id: 'g2', expr: '', conditions: [deptCond('产品部')] },
      ],
    })
    // 扁平化会得到两个标签 + UI 的「或」=> 把 AND 读成 OR（权限被放大），必须整句
    expect(previewTags(m)).toEqual(['（部门 属于 [技术部]） 且 （部门 属于 [产品部]）'])
  })

  it('空条件组被过滤（不留空标签）', () => {
    const m = module({
      groups: [
        { id: 'g1', expr: '', conditions: [deptCond()] },
        { id: 'g2', expr: '', conditions: [] },
      ],
    })
    expect(previewTags(m)).toEqual(['部门 属于 [技术部]'])
  })

  it('非 scope 模式返回空数组（none/all/unset 不渲染规则框）', () => {
    expect(previewTags(module({ mode: 'none' }))).toEqual([])
    expect(previewTags(module({ mode: 'all' }))).toEqual([])
    expect(previewTags(module({ mode: 'unset' }))).toEqual([])
  })

  it('previewGroupText 与 previewOf 的组内渲染逐字一致（抽函数不漂移）', () => {
    const g = { id: 'g1', expr: '1 and 2', conditions: [deptCond('技术部'), deptCond('北京')] }
    expect(previewGroupText(g)).toBe('部门 属于 [技术部] 且 部门 属于 [北京]')
    expect(previewOf(module({ groups: [g] }))).toBe(`（${previewGroupText(g)}）`)
  })
})

describe('resetModule：卡内「重置」只还原本模块读范围', () => {
  it('还原 mode / expr / groups，readDirty 归 false', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'all')
    expect(dp.readDirty.value).toBe(true)

    dp.resetModule('demand')
    expect(dp.draft.value[0].mode).toBe('scope')
    expect(dp.draft.value[0].groups).toHaveLength(1)
    expect(dp.draft.value[0].groups[0].conditions[0].values[0].label).toBe('技术部')
    expect(dp.readDirty.value).toBe(false)
  })

  it('🔴 不碰 write 半边：读卡重置不得静默撤销操作权限页签的改动', () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view'] }) })])
    dp.setWriteMode('demand', 'all')
    dp.setWriteActions('demand', ['view', 'edit'])
    expect(dp.writeDirty.value).toBe(true)

    dp.resetModule('demand')
    // 读范围已还原，写范围保持在途编辑
    expect(dp.readDirty.value).toBe(false)
    expect(dp.writeDirty.value).toBe(true)
    expect(dp.draft.value[0].write?.mode).toBe('all')
    expect(dp.draft.value[0].write?.actions).toEqual(['view', 'edit'])
  })

  it('还原后 saved 与 draft 不共享引用（再改 draft 不污染 saved）', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'unset') // 切走即清
    dp.resetModule('demand')
    dp.draft.value[0].groups[0].conditions[0].values[0].label = '产品部'
    expect(dp.saved.value[0].groups[0].conditions[0].values[0].label).toBe('技术部')
  })

  it('清掉该模块的校验错误（不清会出现「按钮已重置、红字仍在」的罗生门）', () => {
    const dp = setup([module()])
    dp.setGroups('demand', [{ id: 'g1', expr: '', conditions: [] }]) // scope 0 条件 → 校验必挂
    expect(dp.validate()).toEqual(['demand'])
    expect(dp.errors.value.demand).toBeTruthy()

    dp.resetModule('demand')
    expect(dp.errors.value.demand).toBeUndefined()
    expect(dp.errorKinds.value.demand).toBeUndefined()
  })

  it('恢复随草稿展示的 templateDrifts（升级未保存时还原，不留"无漂移"假象）', () => {
    const drift = {
      state: 'outdated' as const,
      templateCode: 'tpl-1',
      templateName: '模板A',
      snapshotVersion: 1,
      latestVersion: 2,
      groupIndex: 0,
    }
    const dp = setup([module({ templateDrifts: [drift] })])
    // 模拟升级：父组件本地摘掉漂移标记（onUpgradeTemplate 的同款动作）
    dp.draft.value[0].templateDrifts = []
    expect(dp.draft.value[0].templateDrifts).toHaveLength(0)

    dp.resetModule('demand')
    expect(dp.draft.value[0].templateDrifts).toHaveLength(1)
    expect(dp.draft.value[0].templateDrifts?.[0].state).toBe('outdated')
  })

  it('只影响目标模块：别的模块的在途编辑原样保留', () => {
    const mods = [
      module({ moduleKey: 'demand' }),
      module({ moduleKey: 'process' }),
    ]
    const dp = setup(mods)
    dp.setMode('demand', 'all')
    dp.setMode('process', 'none')

    dp.resetModule('demand')
    expect(dp.draft.value[0].mode).toBe('scope')
    expect(dp.draft.value[1].mode).toBe('none') // process 的在途改动不动
    expect(dp.readDirty.value).toBe(true) // 全局仍脏（process 未保存）
  })

  it('不存在的 key 静默返回（不抛错，不制造半还原态）', () => {
    const dp = setup([module()])
    expect(() => dp.resetModule('nope')).not.toThrow()
    expect(dp.draft.value[0].mode).toBe('scope')
  })
})

describe('moduleReadDirty：模块粒度脏检查（驱动「重置」显隐）', () => {
  it('干净基线为 false', () => {
    const dp = setup([module({ moduleKey: 'demand' }), module({ moduleKey: 'process' })])
    expect(dp.moduleReadDirty('demand')).toBe(false)
    expect(dp.moduleReadDirty('process')).toBe(false)
  })

  it('只反映本卡：改了 process 不算 demand 脏', () => {
    const dp = setup([module({ moduleKey: 'demand' }), module({ moduleKey: 'process' })])
    dp.setMode('process', 'none')
    expect(dp.moduleReadDirty('demand')).toBe(false)
    expect(dp.moduleReadDirty('process')).toBe(true)
  })

  it('改本卡即脏，resetModule 后复归干净', () => {
    const dp = setup([module()])
    dp.setMode('demand', 'all')
    expect(dp.moduleReadDirty('demand')).toBe(true)
    dp.resetModule('demand')
    expect(dp.moduleReadDirty('demand')).toBe(false)
  })

  it('只改写范围不算读范围脏（两个页签各算各的）', () => {
    const dp = setup([module()])
    dp.setWriteMode('demand', 'all')
    expect(dp.moduleReadDirty('demand')).toBe(false)
    expect(dp.writeDirty.value).toBe(true)
  })
})

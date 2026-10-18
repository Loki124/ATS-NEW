/**
 * T08 提交链 UI 串联 —— 逻辑层回归钉（2026-10-15）。
 *
 * 两条核心契约（与 docs/ARCH 批次2/3「T08 提交链」对齐）：
 *   1. 段2（数据/操作权限）提交失败**绝不**污染段1（角色元数据 + 功能权限已落库态）
 *      以及管理员在段2 的未保存草稿 —— 失败可重试，且重试时仍持有改动。
 *   2. 写范围 round-trip 一致：submit 成功后 draft/saved 被回写为后端 res.modules，
 *      （所见即所存，无假脏）；writeNormalized 哨兵按后端回传同步（正常恒为 []）。
 *
 * 说明：段1/段2 失败定位到出错页签 + 可重试的 UI 行为，已由
 *       RoleEditModal.vue 的 prevalidateDataPerm()（errorKinds 归因跳 tab + scrollIntoView
 *       + 不关闭弹窗）覆盖，本文件只在逻辑层把"失败不污染 / 往返一致"钉死，防止回归。
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

import { useRoleDataPerm } from '@/composables/useRoleDataPerm'
import type { ModulePerm, WritePerm } from '@/api/data-permission'

const write = (over: Partial<WritePerm> = {}): WritePerm => ({
  mode: 'none',
  expr: '',
  groups: [],
  actions: [],
  ...over,
})

/** 读侧带 1 组 1 条的合法 scope 模块（保证读维度合法，报错只可能来自写维度） */
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

describe('T08-1 段2 失败不影响段1（草稿与已落库态不被污染）', () => {
  it('预校验失败（写范围配了却 0 动作）→ submit 返回 false，saved/draft 原样保留且不发请求', async () => {
    // 段1 已落库，段2 草稿里写范围 mode=owner 但没勾动作 → fail-closed 校验拒绝
    const dp = setup([module({ write: write({ mode: 'owner', actions: [] }) })])
    const savedSnap = JSON.stringify(dp.saved.value)
    const draftSnap = JSON.stringify(dp.draft.value)
    const ok = await dp.submit()
    expect(ok).toBe(false)
    expect(h0.saveRoleDataPerm).not.toHaveBeenCalled() // 段2 根本没真正发保存请求
    expect(JSON.stringify(dp.saved.value)).toBe(savedSnap) // 段1 已落库状态不被波及
    expect(JSON.stringify(dp.draft.value)).toBe(draftSnap) // 管理员段2 的改动也还在，可重试
  })

  it('写范围 scope 但无条件组 → 同样预校验拒绝且不触碰草稿', async () => {
    const dp = setup([module({ mode: 'all', groups: [], write: write({ mode: 'scope', actions: ['view'] }) })])
    const draftSnap = JSON.stringify(dp.draft.value)
    const ok = await dp.submit()
    expect(ok).toBe(false)
    expect(h0.saveRoleDataPerm).not.toHaveBeenCalled()
    expect(JSON.stringify(dp.draft.value)).toBe(draftSnap)
  })

  it('后端拒绝（5xx/网络）→ submit 抛错，但本地 saved/draft 不回退不污染（段1 已落库状态保留）', async () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view'] }) })])
    const savedSnap = JSON.stringify(dp.saved.value)
    const draftSnap = JSON.stringify(dp.draft.value)
    h0.saveRoleDataPerm.mockRejectedValue(new Error('网络抖动'))
    // 关键回归点：保存失败不能把草稿/已存一起抹掉，管理员重试时仍持有未保存的改动
    await expect(dp.submit()).rejects.toThrow('网络抖动')
    expect(JSON.stringify(dp.saved.value)).toBe(savedSnap)
    expect(JSON.stringify(dp.draft.value)).toBe(draftSnap)
  })
})

describe('T08-2 写范围往返一致（submit 成功回写 res.modules + writeNormalized 哨兵）', () => {
  it('保存成功 → draft/saved 被回写为后端 res.modules（所见即所存，无假脏），写范围 round-trip 相等', async () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view', 'edit'] }) })])
    const echoed = [module({ write: write({ mode: 'owner', actions: ['view', 'edit'] }) })]
    h0.saveRoleDataPerm.mockResolvedValue({ modules: echoed, writeNormalized: [] })
    const ok = await dp.submit()
    expect(ok).toBe(true)
    // 后端落库态成为新干净基线，且草稿与基线完全一致（无假脏圆点）
    expect(dp.draft.value).toEqual(dp.saved.value)
    // 写范围逐字段 round-trip：前端提交的写授权 = 后端持久化后回传的写授权
    expect(dp.saved.value[0].write).toEqual({ mode: 'owner', expr: '', groups: [], actions: ['view', 'edit'] })
    expect(dp.draft.value[0].write).toEqual(dp.saved.value[0].write)
    expect(dp.writeNormalized.value).toEqual([]) // 正常前端恒为 []，不被误置成脏标记
  })

  it('后端回传 writeNormalized 非空 → 哨兵同步到 writeNormalized.value（序列化回归告警通道）', async () => {
    const dp = setup([module({ write: write({ mode: 'owner', actions: ['view'] }) })])
    h0.saveRoleDataPerm.mockResolvedValue({
      modules: [module({ write: write({ mode: 'owner', actions: ['view'] }) })],
      writeNormalized: ['demand'],
    })
    const ok = await dp.submit()
    expect(ok).toBe(true)
    // 哨兵透传：一旦后端报告"某模块 payload 缺 write 键且沿用了原值"，前端必须知道
    expect(dp.writeNormalized.value).toEqual(['demand'])
  })
})

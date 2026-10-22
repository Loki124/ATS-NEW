/**
 * 校招生管理 · 轮岗资源页签化回归测试（2026-10-21 兵哥指令）
 *
 * 轮岗资源由三个并列菜单（轮岗资源 / 客服部门 / 资源汇总）收敛为单入口页签
 * （BU汇总 / 直播间 / 客服部门），锁三件事防止回退：
 * 1. 只有一个入口路由 /campus/rotation-resource；
 * 2. 旧三路径重定向到新入口，且带上对应页签（深链不丢语义、不 404）；
 * 3. 权限码映射：新入口与旧路径同属 recruit:campus:resource:menu:view（合并后不丢授权）。
 */
import { describe, expect, it } from 'vitest'

import router from '../index'
import { permissionForPath } from '../../utils/permissionMenu'

/** 把嵌套路由表拍平（campus 路由挂在 '/' 父路由的 children 内）。 */
function flatten(routes: any[], out: any[] = []): any[] {
  for (const r of routes) {
    out.push(r)
    if (r.children) flatten(r.children, out)
  }
  return out
}

const ROUTES = flatten((router.options.routes ?? []) as any[])
const byPath = (p: string) => ROUTES.find((r) => r.path === p)

describe('轮岗资源页签化路由', () => {
  it('轮岗资源只有一个入口路由，指向 RotationResource 页面', () => {
    const rr = byPath('campus/rotation-resource')
    expect(rr).toBeTruthy()
    expect(rr!.name).toBe('CampusRotationResource')
  })

  it('旧三路径重定向到新入口并带上对应页签', () => {
    // ⚠️ 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」一个页签 →
    //   两条旧深链都落到 tab=resource。
    expect(byPath('campus/live-room')!.redirect).toEqual({
      path: '/campus/rotation-resource',
      query: { tab: 'resource' },
    })
    expect(byPath('campus/service-dept')!.redirect).toEqual({
      path: '/campus/rotation-resource',
      query: { tab: 'resource' },
    })
    expect(byPath('campus/resource-summary')!.redirect).toEqual({
      path: '/campus/rotation-resource',
      query: { tab: 'bu' },
    })
  })

  it('旧路径不再是独立页面组件（避免同一份数据两套入口）', () => {
    for (const p of ['campus/live-room', 'campus/service-dept', 'campus/resource-summary']) {
      expect(byPath(p)!.component).toBeUndefined()
    }
  })

  it('新入口与旧路径权限码一致（合并后不丢授权）', () => {
    const code = 'recruit:campus:resource:menu:view'
    expect(permissionForPath('/campus/rotation-resource')).toBe(code)
    expect(permissionForPath('/campus/live-room')).toBe(code)
    expect(permissionForPath('/campus/service-dept')).toBe(code)
    expect(permissionForPath('/campus/resource-summary')).toBe(code)
  })

  it('轮岗安排 / 班级管理 / 校招生档案路由未被误改', () => {
    expect(byPath('campus/rotation-arrangement')?.name).toBe('CampusRotationArrangement')
    expect(byPath('campus/class-room')?.name).toBe('CampusClassRoom')
    expect(byPath('campus/person')?.name).toBe('CampusPersonManagement')
  })
})

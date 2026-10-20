/**
 * permissionMenu 单元测试 — 菜单/路由资源码映射与递归裁剪（G4）。
 *
 * 重点锁两件事：
 * 1. 最长前缀优先：/settings/company/brand 不能被 /settings/company 抢走码；
 * 2. fail-open：未登记路径恒保留；分组在 children 被裁空时才整体移除。
 */
import { describe, expect, it } from 'vitest'

import {
  MENU_PERMISSION_RULES,
  filterMenuByPermission,
  isPathGuarded,
  permissionForPath,
} from './permissionMenu'

const allowAll = () => true
const denyAll = () => false

describe('permissionForPath', () => {
  it('按最长前缀命中，避免父路径抢子路径的码', () => {
    expect(permissionForPath('/settings/company/brand')).toBe('recruit:settings:company_brand:menu:view')
    expect(permissionForPath('/settings/company')).toBe('recruit:settings:company:menu:view')
  })

  it('子路径继承父路径的码', () => {
    expect(permissionForPath('/candidates/123')).toBe('recruit:candidate:menu:view')
  })

  it('未登记路径返回 undefined（视为公共入口）', () => {
    expect(permissionForPath('/dashboard')).toBeUndefined()
    expect(permissionForPath('/some/unknown')).toBeUndefined()
    expect(isPathGuarded('/dashboard')).toBe(false)
    // 对照组取「当前确已登记」的路径：原写 /offers，该路由已随 Offer 并入候选人
    // 管理（7eb66448）删除、登记一并移除，继续断言 true 会让门禁常红。
    expect(isPathGuarded('/candidates')).toBe(true)
  })

  it('码表不重复且非空', () => {
    expect(MENU_PERMISSION_RULES.length).toBeGreaterThan(20)
    MENU_PERMISSION_RULES.forEach((r) => {
      expect(r.code).toMatch(/^recruit:/)
      expect(r.prefix.startsWith('/')).toBe(true)
    })
  })
})

describe('filterMenuByPermission', () => {
  const menu = [
    {
      key: 'g-basic',
      type: 'group' as const,
      label: '基本信息',
      children: [
        { key: '/settings/company/brand', label: '品牌信息' },
        { key: '/settings/dictionary', label: '数据字典' },
      ],
    },
    { key: '/dashboard', label: '工作台' },
  ]

  it('canAccess 全放行时菜单原样保留', () => {
    expect(filterMenuByPermission(menu, allowAll)).toHaveLength(2)
  })

  it('裁掉无权叶子项，分组在还剩子项时保留', () => {
    const canAccess = (code?: string) => code !== 'recruit:settings:dictionary:menu:view'
    const out = filterMenuByPermission(menu, canAccess)
    expect(out).toHaveLength(2)
    expect((out[0].children ?? [])).toHaveLength(1)
  })

  it('分组子项全被裁掉时分组整体移除', () => {
    const canAccess = (code?: string) =>
      code !== 'recruit:settings:company_brand:menu:view'
        && code !== 'recruit:settings:dictionary:menu:view'
    const out = filterMenuByPermission(menu, canAccess)
    expect(out).toHaveLength(1)
    expect(out[0].key).toBe('/dashboard')
  })

  it('未登记路径的菜单项恒保留（fail-open）', () => {
    const out = filterMenuByPermission([{ key: '/dashboard', label: '工作台' }], denyAll)
    expect(out).toHaveLength(1)
  })
})

/**
 * 设置菜单结构护栏（2026-10-21：用户管理迁入「权限管理」+ 用户组管理下线）。
 *
 * 锁住三条结构契约：
 *  1. 「用户管理」(`/settings/users/all`) 归属「权限管理」分组 (g-permission)，且**排第一位**；
 *  2. 不存在独立的「用户管理」分组 (g-user) —— 用户组管理下线后原分组已空，整体删除；
 *  3. 不存在「用户组管理」菜单项 / 路由（功能整体下线）。
 *
 * 读的是组件真实渲染给 n-menu 的 options（不是源码文本），故菜单树真变了本测试即红。
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { NMenu } from 'naive-ui'
import SettingsLayout from '../SettingsLayout.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/settings/users/all' }),
}))

// 菜单裁剪依赖 canAccess；本测试只关心结构，放行全部（fail-open 与真源一致）
vi.mock('../../../composables/usePermission', () => ({
  usePermission: () => ({ canAccess: () => true }),
}))

/** 递归收集菜单树里的所有 key */
function collectKeys(nodes: any[]): string[] {
  const out: string[] = []
  for (const n of nodes ?? []) {
    if (n?.key != null) out.push(String(n.key))
    if (n?.children?.length) out.push(...collectKeys(n.children))
  }
  return out
}

/** 按 key 递归查找菜单节点（g-permission 嵌在「基本信息」分组内，非顶层） */
function findNode(nodes: any[], key: string): any | undefined {
  for (const n of nodes ?? []) {
    if (String(n?.key) === key) return n
    if (n?.children?.length) {
      const hit = findNode(n.children, key)
      if (hit) return hit
    }
  }
  return undefined
}

function mountMenu(): any[] {
  const wrapper = mount(SettingsLayout, {
    global: { stubs: { 'router-view': true } },
  })
  const menu = wrapper.findComponent(NMenu)
  expect(menu.exists(), 'SettingsLayout 应渲染出 n-menu').toBe(true)
  return menu.props('options') as any[]
}

describe('设置菜单结构（用户管理归入权限管理 / 用户组管理下线）', () => {
  it('用户管理是「权限管理」分组的第一个子项', () => {
    const options = mountMenu()
    const gPermission = findNode(options, 'g-permission')
    expect(gPermission, '应存在「权限管理」分组 g-permission').toBeTruthy()
    const children = gPermission.children ?? []
    expect(children.length).toBeGreaterThan(0)
    expect(children[0].key).toBe('/settings/users/all')
  })

  it('「权限管理」分组内不再有用户组管理，其余子项保持', () => {
    const options = mountMenu()
    const gPermission = findNode(options, 'g-permission')
    expect(gPermission).toBeTruthy()
    const keys = collectKeys(gPermission.children ?? [])
    expect(keys).toContain('/settings/users/all')
    expect(keys).toContain('/settings/permissions')
    expect(keys).not.toContain('/settings/user-groups')
  })

  it('不存在独立的「用户管理」分组（原 g-user 已随用户组管理下线整体删除）', () => {
    const options = mountMenu()
    const allKeys = collectKeys(options)
    expect(allKeys).not.toContain('g-user')
    expect(allKeys).not.toContain('/settings/user-groups')
  })
})

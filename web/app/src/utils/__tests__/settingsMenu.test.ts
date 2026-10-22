/**
 * settingsMenu.test.ts — 设置侧栏折叠态菜单变换单测
 *
 * 背景：naive-ui 的折叠态浮出（hover 弹二级菜单）**只对根级子菜单生效**
 *   （Submenu.render: `this.root ? h(NDropdown, …) : h('div', …)`，root = level === 0）。
 *   设置菜单是「分组 → 子菜单 → 叶子」三层，父项都在 level 1 → 折叠态全成死路。
 *   本模块负责把分组打平，让父项回到根级。
 */
import { describe, it, expect } from 'vitest'
import type { MenuOption } from 'naive-ui'
import { buildCollapsedMenuOptions, countRootExpandable } from '../settingsMenu'

const GROUPED: MenuOption[] = [
  {
    key: 'g-basic',
    type: 'group',
    label: '基本信息',
    children: [
      { key: '/settings/account', label: '个人信息' },
      { key: 'g-company', label: '公司信息管理', children: [{ key: '/settings/company', label: '公司信息' }] },
    ],
  },
  {
    key: 'g-process',
    type: 'group',
    label: '过程管理',
    children: [
      { key: 'g-candidate', label: '候选人信息', children: [{ key: '/settings/candidate-dynamic-fields', label: '动态字段' }] },
      { key: '/settings/interview-management', label: '面试管理' },
    ],
  },
]

describe('buildCollapsedMenuOptions', () => {
  it('分组被打平：所有条目都提升到根级（不再有 type:group）', () => {
    const out = buildCollapsedMenuOptions(GROUPED)
    expect(out.every((o) => o.type !== 'group')).toBe(true)
    expect(out.map((o) => String(o.key))).toEqual([
      '/settings/account',
      'g-company',
      'settings-divider-g-process',
      'g-candidate',
      '/settings/interview-management',
    ])
  })

  it('可展开父项全部位于根级 → naive 的浮出载体（NDropdown）才会挂上', () => {
    const out = buildCollapsedMenuOptions(GROUPED)
    // 每个有 children 的条目都必须在根级（不能藏在别人的 children 里）
    for (const o of out) {
      if ((o.children?.length ?? 0) > 0) {
        expect(o.type).not.toBe('group')
      }
    }
    expect(countRootExpandable(out)).toBe(2)
    // 父项的子项本身仍是叶子（浮出后直接是可选条目）
    const company = out.find((o) => o.key === 'g-company')
    expect(company?.children?.[0]?.key).toBe('/settings/company')
  })

  it('组与组之间插入分隔线（折叠态看不到组标题，靠分隔线保留视觉分组）', () => {
    const out = buildCollapsedMenuOptions(GROUPED)
    const dividers = out.filter((o) => o.type === 'divider')
    expect(dividers.length).toBe(1) // 2 个分组 → 1 条分隔线（第一组前不加）
    expect(String(dividers[0].key)).toBe('settings-divider-g-process')
  })

  it('空分组被跳过，不留空壳', () => {
    const out = buildCollapsedMenuOptions([
      { key: 'g-empty', type: 'group', label: '空组', children: [] },
      { key: '/settings/x', label: 'X' },
    ])
    expect(out.map((o) => String(o.key))).toEqual(['/settings/x'])
  })

  it('非分组条目原样保留（根级叶子不被改动）', () => {
    const out = buildCollapsedMenuOptions([{ key: '/settings/root', label: '根级' }])
    expect(out).toHaveLength(1)
    expect(out[0].key).toBe('/settings/root')
  })

  it('空输入返回空数组', () => {
    expect(buildCollapsedMenuOptions([])).toEqual([])
  })
})

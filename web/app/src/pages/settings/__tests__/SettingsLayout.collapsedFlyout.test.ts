/**
 * 设置侧栏折叠态 · 悬浮浮出二级菜单 —— 回归护栏
 * （2026-10-21 兵哥指令：「把系统设置模块的菜单也按照悬浮展示子菜单的形式处理」）
 *
 * 锁住三条契约：
 *  1. **展开态分组结构不变**（基本信息/过程管理… 是设置页的主要导航线索，不能丢）；
 *  2. **折叠态分组被打平**：所有可展开父项回到根级
 *     —— naive 的浮出载体 NDropdown 只挂在 root(level 0) 子菜单上（Submenu.render），
 *        父项不在根级 = 折叠态 hover 不出、点击也是死路；
 *  3. **折叠态 hover 父项图标真的会弹出二级菜单**（行为级验证，不是只看结构）。
 *
 * 读的是组件真实渲染给 n-menu 的 options（不是源码文本），菜单树真变了本测试即红。
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { NMenu } from 'naive-ui'
import SettingsLayout from '../SettingsLayout.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/settings/company/address' }),
}))

// 菜单裁剪依赖 canAccess；本测试只关心结构，放行全部（fail-open 与真源一致）
vi.mock('../../../composables/usePermission', () => ({
  usePermission: () => ({ canAccess: () => true }),
}))

/** 折叠设置侧栏（点 header 里的折叠按钮） */
async function collapseSider() {
  const wrapper = mount(SettingsLayout, {
    global: { stubs: { 'router-view': true } },
    attachTo: document.body,
  })
  await wrapper.find('.collapse-btn').trigger('click')
  await flushPromises()
  return wrapper
}

function menuOptions(wrapper: any): any[] {
  const menu = wrapper.findComponent(NMenu)
  expect(menu.exists(), 'SettingsLayout 应渲染出 n-menu').toBe(true)
  return menu.props('options') as any[]
}

describe('设置侧栏折叠态 · 悬浮浮出', () => {
  it('① 展开态保留分组结构（分组标题是设置页主要导航线索）', () => {
    const wrapper = mount(SettingsLayout, {
      global: { stubs: { 'router-view': true } },
    })
    const options = menuOptions(wrapper)
    expect(options.some((o) => o.type === 'group')).toBe(true)
    // 分组内仍有二级子菜单（展开态是就地展开，不是浮出）
    const gBasic = options.find((o) => o.key === 'g-basic')
    expect(gBasic?.children?.length).toBeGreaterThan(0)
    wrapper.unmount()
  })

  it('② 折叠态分组被打平，可展开父项全部回到根级', async () => {
    const wrapper = await collapseSider()
    const options = menuOptions(wrapper)
    // 不再有分组
    expect(options.every((o) => o.type !== 'group')).toBe(true)
    // 每个有 children 的条目都在根级（不在任何人的 children 里）
    const nested = options.filter((o) => (o.children?.length ?? 0) > 0)
    expect(nested.length).toBeGreaterThan(0)
    for (const o of nested) expect(o.type).not.toBe('group')
    // 关键父项仍在（「公司信息管理」「权限管理」…）
    const keys = options.map((o) => String(o.key))
    expect(keys).toContain('g-company')
    expect(keys).toContain('g-permission')
    wrapper.unmount()
  })

  it('③ 折叠态 hover 父项图标 → 真的浮出二级菜单（行为级）', async () => {
    const wrapper = await collapseSider()
    const options = menuOptions(wrapper)
    // 找「公司信息管理」在根级可展开项中的序号
    const expandableIdx = options
      .filter((o) => (o.children?.length ?? 0) > 0)
      .findIndex((o) => o.key === 'g-company')
    expect(expandableIdx).toBeGreaterThanOrEqual(0)

    const submenus = wrapper.findAll('.n-submenu')
    expect(submenus.length, '折叠态的可展开父项应渲染为 .n-submenu').toBeGreaterThan(0)

    // naive 的 popover hover 触发有 100ms 延迟（Popover.mjs delay 默认 100）→ 用假时钟推进
    vi.useFakeTimers()
    await submenus[expandableIdx].trigger('mouseenter')
    vi.advanceTimersByTime(200)
    await flushPromises()
    vi.useRealTimers()

    const panel = document.body.querySelector('.n-dropdown-menu')
    expect(panel, 'hover 后应浮出下拉面板').toBeTruthy()
    const text = panel?.textContent ?? ''
    // 浮出内容 = 该父项的子项（公司信息 / 办公地址 / 会议室 / 简历邮箱 / 品牌）
    expect(text).toContain('公司信息')

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})

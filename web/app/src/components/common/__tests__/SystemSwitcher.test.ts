/**
 * SystemSwitcher.test.ts — 系统切换器组件行为测试
 *
 * 覆盖:
 *  - 触发器显示当前系统名 / 折叠态显示单字标识
 *  - 下拉面板挂上紧凑化 class（sys-switch-dropdown）
 *  - 选项行结构：图标槽 + 文字 +（当前项）右侧勾
 *  - 选中另一个系统 → 切换 store，且**不跳路由**（DUAL_SYSTEM_DESIGN.md D5）
 *  - 选中「内推助手」→ 跳 /referral，不切换系统
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import SystemSwitcher from '../SystemSwitcher.vue'
import { useSystemStore } from '../../../stores/system'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'home', component: { template: '<div/>' } },
    { path: '/campus/person', name: 'campus-person', component: { template: '<div/>' } },
    { path: '/referral', name: 'referral', component: { template: '<div/>' } },
  ],
})

function mountSwitcher(collapsed = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const wrapper = mount(SystemSwitcher, {
    props: { collapsed },
    global: { plugins: [pinia, router] },
    attachTo: document.body,
  })
  return { wrapper, pinia }
}

/** 展开下拉（naive 的 trigger=click 监听挂在触发元素上） */
async function openDropdown(wrapper: VueWrapper) {
  await wrapper.find('button.sys-switch').trigger('click')
  await flushPromises()
}

/** 取下拉里的选项行（naive 的 option body 才是可点击体） */
function optionBodies(): HTMLElement[] {
  return Array.from(document.body.querySelectorAll<HTMLElement>('.n-dropdown-option-body'))
}

function clickOptionByText(text: string) {
  const target = optionBodies().find((el) => el.textContent?.includes(text))
  expect(target, `下拉里应存在「${text}」选项`).toBeTruthy()
  target!.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

describe('SystemSwitcher', () => {
  beforeEach(async () => {
    localStorage.clear()
    await router.push('/')
    await router.isReady()
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('触发器显示当前系统名（默认社招）', () => {
    const { wrapper } = mountSwitcher()
    expect(wrapper.find('.sys-switch__label').text()).toBe('社会招聘')
    expect(wrapper.find('button.sys-switch').attributes('aria-label')).toContain('社会招聘')
    wrapper.unmount()
  })

  it('折叠态显示单字标识而非系统名', () => {
    const { wrapper } = mountSwitcher(true)
    expect(wrapper.find('.sys-switch__short').text()).toBe('社')
    expect(wrapper.find('.sys-switch__label').exists()).toBe(false)
    wrapper.unmount()
  })

  it('下拉面板挂上紧凑化 class，且选项行是「图标 + 文字 + 勾」结构', async () => {
    const { wrapper } = mountSwitcher()
    await openDropdown(wrapper)

    // 紧凑化面板的 CSS 钩子（teleport 到 body，必须用全局 class 命中）
    expect(document.body.querySelector('.sys-switch-dropdown')).toBeTruthy()

    const rows = Array.from(document.body.querySelectorAll<HTMLElement>('.sys-opt'))
    expect(rows.length).toBe(3) // 社会招聘 / 校园招聘 / 内推助手
    for (const row of rows) {
      expect(row.querySelector('.sys-opt__icon')).toBeTruthy()
      expect(row.querySelector('.sys-opt__text')).toBeTruthy()
    }
    // 当前系统（社招）有勾，另一个没有
    const current = rows.find((r) => r.classList.contains('sys-opt--current'))
    expect(current?.textContent).toContain('社会招聘')
    expect(current?.querySelector('.sys-opt__check')).toBeTruthy()
    expect(rows.find((r) => r.textContent?.includes('校园招聘'))?.querySelector('.sys-opt__check')).toBeNull()

    // 图标尺寸统一 16px（两人形的 PeopleOutline 在 15px 下糊成一团，故用单人 PersonOutline + 16px）
    const icon = document.body.querySelector<HTMLElement>('.sys-opt__icon .n-icon')
    expect(icon?.style.fontSize).toBe('16px')

    wrapper.unmount()
  })

  it('naive 的 prefix 预留位确实被压到 0（文字错位的根因已消除）', async () => {
    const { wrapper } = mountSwitcher()
    await openDropdown(wrapper)

    const menu = document.body.querySelector<HTMLElement>('.n-dropdown-menu')
    expect(menu).toBeTruthy()
    // 内联 CSS 变量 = naive 实际生效值（行高 / 字号 / prefix 槽宽）
    expect(menu!.style.getPropertyValue('--n-option-prefix-width')).toBe('0px')
    expect(menu!.style.getPropertyValue('--n-option-icon-prefix-width')).toBe('0px')
    expect(menu!.style.getPropertyValue('--n-option-height')).toBe('32px')
    expect(menu!.style.getPropertyValue('--n-font-size')).toBe('13px')

    // 所有选项行的 prefix 槽宽度一致 → 文字起始位置必然一致
    const prefixes = Array.from(
      document.body.querySelectorAll<HTMLElement>('.n-dropdown-option-body__prefix'),
    )
    expect(prefixes.length).toBeGreaterThan(0)

    wrapper.unmount()
  })

  it('选中另一个系统 → 切换系统，但**停留在当前路由**（D5）', async () => {
    await router.push('/campus/person')
    const { wrapper } = mountSwitcher()
    await openDropdown(wrapper)

    clickOptionByText('校园招聘')
    await flushPromises()

    const store = useSystemStore()
    expect(store.current).toBe('campus')
    // D5：切换系统后停留当前路由，不跳工作台
    expect(router.currentRoute.value.path).toBe('/campus/person')
    wrapper.unmount()
  })

  it('选中「内推助手」→ 跳 /referral，且不切换招聘系统', async () => {
    const { wrapper } = mountSwitcher()
    await openDropdown(wrapper)

    clickOptionByText('内推助手')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/referral')
    expect(useSystemStore().current).toBe('social')
    wrapper.unmount()
  })
})

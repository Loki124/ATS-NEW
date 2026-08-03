import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { naivePlugin } from '../../../../plugins/naive'
import PermissionManagement from '../../PermissionManagement.vue'

// API mock — resources/templates/roles/user-roles/mgmt-units 都返回数组 (子组件直接 .forEach)
vi.mock('@/api/permission-resource', () => ({
  listResources: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/permission-template', () => ({
  listTemplates: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/role-v2', () => ({
  listRoles: vi.fn().mockResolvedValue([]),
  cloneFromTemplate: vi.fn(),
}))
vi.mock('@/api/user-role-v2', () => ({
  listUserRoles: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/management-unit', () => ({
  listMgmtUnits: vi.fn().mockResolvedValue([]),
}))

function factory() {
  const Wrapper = defineComponent({
    setup(_, { slots }) {
      return () =>
        h(NConfigProvider, null, {
          default: () =>
            h(NMessageProvider, null, {
              default: () => slots.default?.(),
            }),
        })
    },
  })
  const w = mount(Wrapper, {
    slots: { default: () => h(PermissionManagement) },
    attachTo: document.body,
  })
  w.vm.$.appContext.app.use(naivePlugin)
  return w
}

describe('PermissionManagement', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('renders 4 tabs', async () => {
    const wrapper = factory()
    await flushPromises()
    expect(wrapper.findAll('.n-tabs-tab').length).toBe(4)
  })

  it('default tab is resources', async () => {
    // R10 (2026-08-03 寇豆码): 原断言是 `wrapper.vm.activeTab || 'resources'`。
    //   wrapper 挂的是外层 Wrapper 组件, 它身上根本没有 activeTab, 所以永远走
    //   `|| 'resources'` 分支 —— 恒真断言, 测不出任何东西, 同时 vue-tsc 报 TS2339。
    //   改成读真实渲染结果: naive-ui 会给选中的 tab 加 .n-tabs-tab--active。
    const wrapper = factory()
    await flushPromises()
    const activeTab = wrapper.find('.n-tabs-tab--active')
    expect(activeTab.exists()).toBe(true)
    expect(activeTab.text()).toContain('资源管理')
  })
})

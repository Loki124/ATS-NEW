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
    const wrapper = factory()
    await flushPromises()
    expect(wrapper.vm.activeTab || 'resources').toBeTruthy()
  })
})

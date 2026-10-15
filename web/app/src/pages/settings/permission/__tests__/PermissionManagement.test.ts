import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { naivePlugin } from '../../../../plugins/naive'
import PermissionManagement from '../../PermissionManagement.vue'

// API mock — roles/templates 返回数组 (子组件直接消费)
// 2026-09-18 重构: 原 4-tab 拆解后本页只挂 RolesTab。
// 2026-10-15: 模板管理入口与弹窗下线，模板基础信息并入「查看权限码」弹窗。
vi.mock('@/api/permission-template', () => ({
  listTemplates: vi.fn().mockResolvedValue([]),
}))
vi.mock('@/api/role-v2', () => ({
  listRoles: vi.fn().mockResolvedValue([]),
  cloneFromTemplate: vi.fn(),
}))

function factory() {
  // 权限 v2：RolesTab 引入 useUserStore（动作管理入口仅超管可见）→ 需要 Pinia。
  // setActivePinia 供 setup 期调用；app.use 供组件内注入（与下方 naivePlugin 同款模式）。
  const pinia = createPinia()
  setActivePinia(pinia)
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
  w.vm.$.appContext.app.use(pinia)
  return w
}

describe('PermissionManagement (身份管理)', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('renders page title 身份管理', async () => {
    const wrapper = factory()
    await flushPromises()
    expect(wrapper.find('.page-title').text()).toBe('身份管理')
  })

  it('no longer renders tabs (去 tab 化)', async () => {
    const wrapper = factory()
    await flushPromises()
    expect(wrapper.findAll('.n-tabs-tab').length).toBe(0)
  })

  it('不再渲染「模板管理」按钮（模板信息已并入查看权限码弹窗）', async () => {
    const wrapper = factory()
    await flushPromises()
    const btn = wrapper.findAll('button').find((b) => b.text().includes('模板管理'))
    expect(btn).toBeFalsy()
    expect(document.body.querySelector('.templates-modal')).toBeFalsy()
  })
})

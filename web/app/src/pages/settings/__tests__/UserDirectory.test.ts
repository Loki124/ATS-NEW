import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'

// 2026-09-19 整合重构测试：内部/外部/全部用户合并为单一「用户管理」页
//   - 无 n-tabs、无 KPI 卡片
//   - 工具条对齐校招管控：.toolbar + .rule-filter-search + 2×.rule-filter-select + .spacer + 右对齐「新建用户」
//   - 列表带 pagination（pageSize 20 + 共 N 条 前缀）
//   - 表单含「用户类型」字段
//   - 写操作以 HTTP 2xx 判定成功（request() 返回 {ok,status,data}）

vi.mock('../../../stores/user', () => ({
  useUserStore: () => ({ accessToken: 'test-token' }),
}))

vi.mock('../../../stores/department', () => ({
  useDepartmentStore: () => ({
    loading: false,
    departments: [],
    getById: () => null,
    loadDepartments: vi.fn(),
  }),
}))

const MOCK_USERS = Array.from({ length: 12 }, (_, i) => ({
  id: `u-${i + 1}`,
  username: `user-${String(i + 1).padStart(2, '0')}`,
  realName: `用户${i + 1}`,
  status: i % 3 === 0 ? 'INACTIVE' : 'ACTIVE',
  roleType: 'HR',
  userType: i % 2 === 0 ? 'INTERNAL' : 'EXTERNAL',
  createdAt: '2026-09-19T00:00:00Z',
}))

const MOCK_ROLES = [
  { id: 'r1', name: 'HR', code: 'HR', roleType: 'SYSTEM' },
  { id: 'r2', name: 'Manager', code: 'MANAGER', roleType: 'BUSINESS' },
]

function factory() {
  const Wrapper = defineComponent({
    setup(_, { slots }) {
      return () =>
        h(NConfigProvider, null, {
          default: () => h(NMessageProvider, null, { default: () => slots.default?.() }),
        })
    },
  })
  const w = mount(Wrapper, {
    slots: { default: () => h(UserDirectory) },
    attachTo: document.body,
  })
  try {
    w.vm.$.appContext.app.use(naivePlugin)
  } catch {
    /* 已注册则忽略 */
  }
  return w
}

// 模拟 fetch：request() 内部走 response.text() + JSON.parse，并依赖 response.ok 判定写操作
function setupFetch() {
  global.fetch = vi.fn(async (url: string) => {
    let payload: any
    if (url.includes('/api/v1/users/') && !url.includes('/roles/')) {
      payload = { success: true, data: MOCK_USERS }
    } else if (url.includes('/api/v1/permissions/roles/')) {
      payload = { success: true, data: MOCK_ROLES }
    } else if (url.includes('/permissions/users/') && url.includes('/roles/')) {
      payload = { success: true, data: MOCK_ROLES }
    } else {
      payload = { success: true, data: [] }
    }
    return { ok: true, status: 200, text: async () => JSON.stringify(payload) } as any
  }) as any
}

import UserDirectory from '../UserDirectory.vue'

describe('UserDirectory (整合后用户管理)', () => {
  let wrapper: any

  beforeEach(() => {
    setupFetch()
    document.body.innerHTML = ''
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('renders page title 用户管理', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(wrapper.find('.page-title').text()).toBe('用户管理')
  })

  it('no longer renders tabs (内部/外部/全部合并)', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelectorAll('.n-tabs-tab').length).toBe(0)
  })

  it('KPI stat cards removed', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelector('.kpi-row')).toBeFalsy()
    expect(document.querySelector('.kpi-card')).toBeFalsy()
  })

  it('toolbar has search + 2 selects + spacer + 新建用户 button at right', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const toolbar = document.querySelector('.toolbar')
    expect(toolbar).toBeTruthy()
    // 搜索框（.rule-filter-search 内原生 input）
    expect(toolbar!.querySelector('.rule-filter-search input')).toBeTruthy()
    // 两个筛选项 .rule-filter-select
    expect(toolbar!.querySelectorAll('.rule-filter-select').length).toBe(2)
    // .spacer 存在，用于把按钮推到最右
    expect(toolbar!.querySelector('.spacer')).toBeTruthy()
    // 新建用户 按钮
    const newBtn = Array.from(toolbar!.querySelectorAll('.n-button')).find((b) =>
      (b.textContent || '').includes('新建用户')
    )
    expect(newBtn).toBeTruthy()
    // 新建用户 按钮是 toolbar 的最后一个子元素（最右侧）
    const children = Array.from(toolbar!.children)
    expect(children[children.length - 1].contains(newBtn!)).toBe(true)
  })

  it('renders pagination with 共 N 条 prefix', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelector('.n-data-table')).toBeTruthy()
    const pag = document.querySelector('.n-pagination')
    expect(pag).toBeTruthy()
    expect(pag!.textContent || '').toContain('共 12 条')
  })

  it('user type column distinguishes internal/external', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const bodyText = document.querySelector('.n-data-table')?.textContent || ''
    expect(bodyText).toContain('内部')
    expect(bodyText).toContain('外部')
  })

  it('search box filters the table client-side', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const input = document.querySelector('.rule-filter-search input') as HTMLInputElement
    expect(input).toBeTruthy()
    // 初始展示 = 第一页（pageSize 20），12 条数据 → 12 行
    const initialRows = document.querySelectorAll('.n-data-table-tbody .n-data-table-tr').length
    expect(initialRows).toBe(12)
    // 输入唯一子串 user-07 → 仅 1 行
    await wrapper.find('.rule-filter-search input').setValue('user-07')
    await flushPromises()
    await nextTick()
    const filteredRows = document.querySelectorAll('.n-data-table-tbody .n-data-table-tr').length
    expect(filteredRows).toBe(1)
  })

  // 2026-09-19 整合重构后：独立的「角色」弹窗已合并进编辑弹窗
  // （loadUserRoles 在点击「编辑」时调用，角色配置以编辑表单字段呈现，见 UserDirectory.vue:158/745-746）。
  // 此处验证当前真实的角色配置路径，而非已删除的旧 UX。
  it('edit modal opens and contains role config field (loadUserRoles path)', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    // 操作列中的「编辑」按钮
    const editBtn = Array.from(document.querySelectorAll('.n-data-table .n-button')).find((b) =>
      (b.textContent || '').trim() === '编辑'
    ) as HTMLButtonElement | undefined
    expect(editBtn).toBeTruthy()
    await editBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()
    const modal = document.querySelector('.n-modal')
    expect(modal).toBeTruthy()
    // 角色配置作为编辑表单字段呈现（loadUserRoles 已填入当前用户角色）
    expect(modal!.textContent || '').toContain('角色配置')
  })
})

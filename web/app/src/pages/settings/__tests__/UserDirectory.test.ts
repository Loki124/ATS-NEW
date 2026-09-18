import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, nextTick } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'

// 2026-09-19 整合重构测试：内部/外部/全部用户合并为单一「用户管理」页
//   - 无 n-tabs、无 KPI 卡片
//   - 搜索框 + 用户类型/状态 筛选项 + 右侧「新建用户」按钮
//   - 列表带 pagination 分页器
//   - 表单含「用户类型」字段

vi.mock('../../../stores/user', () => ({
  useUserStore: () => ({ accessToken: 'test-token' }),
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

import UserDirectory from '../UserDirectory.vue'

function setupFetch() {
  global.fetch = vi.fn(async (url: string) => {
    if (url.includes('/api/v1/users/')) {
      return { json: async () => ({ success: true, data: MOCK_USERS }) } as any
    }
    if (url.includes('/api/v1/permissions/roles/')) {
      return { json: async () => ({ success: true, data: MOCK_ROLES }) } as any
    }
    return { json: async () => ({ success: true, data: [] }) } as any
  }) as any
}

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

  it('filter row has search box + 2 selects + 新建用户 button at right', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const filterRow = document.querySelector('.filter-row')
    expect(filterRow).toBeTruthy()
    // 搜索框（n-input 内含原生 input）
    expect(filterRow!.querySelector('.filter-search input')).toBeTruthy()
    // 两个筛选项 n-select
    expect(filterRow!.querySelectorAll('.filter-select').length).toBe(2)
    // 新建用户 按钮
    const newBtn = Array.from(filterRow!.querySelectorAll('.n-button')).find((b) =>
      (b.textContent || '').includes('新建用户')
    )
    expect(newBtn).toBeTruthy()
    // 新建用户 按钮是 filter-row 的最后一个子元素（最右侧）
    const children = Array.from(filterRow!.children)
    expect(children[children.length - 1].contains(newBtn!)).toBe(true)
  })

  it('renders pagination component under data table', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelector('.n-data-table')).toBeTruthy()
    expect(document.querySelector('.n-pagination')).toBeTruthy()
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
    const input = document.querySelector('.filter-search input') as HTMLInputElement
    expect(input).toBeTruthy()
    // 初始展示 = 第一页（pageSize 10），12 条数据 → 10 行
    const initialRows = document.querySelectorAll('.n-data-table-tbody .n-data-table-tr').length
    expect(initialRows).toBe(10)
    // 输入唯一子串 user-07 → 仅 1 行
    await wrapper.find('.filter-search input').setValue('user-07')
    await flushPromises()
    await nextTick()
    const filteredRows = document.querySelectorAll('.n-data-table-tbody .n-data-table-tr').length
    expect(filteredRows).toBe(1)
  })
})

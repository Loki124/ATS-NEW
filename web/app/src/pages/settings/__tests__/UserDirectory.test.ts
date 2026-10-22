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
  // 2026-10-18 兵哥：三态（PENDING 待激活 / ACTIVE 已激活 / DISABLED 已停用），
  // 与后端 User.activation_status 同源同值；三态各占 1/3 以便筛选断言。
  status: (['PENDING', 'ACTIVE', 'DISABLED'] as const)[i % 3],
  roleType: 'HR',
  userType: i % 2 === 0 ? 'INTERNAL' : 'EXTERNAL',
  createdAt: '2026-09-19T00:00:00Z',
  // 拥有身份：首个用户 3 个（验证折叠为 +1），第二个 1 个（不折叠），其余无身份（走 '-' 占位）
  roleNames: i === 0 ? ['超级管理员', '面试官', 'HRBP'] : i === 1 ? ['面试官'] : [],
  // 管理单元范围：首个用户 3 个（验证折叠为 +1），第二个 1 个（不折叠），其余无授权
  managementUnitNames:
    i === 0 ? ['华东大区', '华南大区', '华北大区'] : i === 1 ? ['华东大区'] : [],
}))

// 2026-10-21 管理单元授权：管理单元树（GET /api/v1/management-units/tree/）
const MOCK_MGMT_UNITS = [
  { id: 11, unitName: '华东大区', status: 1, children: [] },
  { id: 12, unitName: '华南大区', status: 1, children: [] },
]

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
    } else if (url.includes('/management-units/tree/')) {
      payload = { success: true, data: MOCK_MGMT_UNITS }
    } else if (url.includes('/permissions/users/') && url.includes('/roles/')) {
      // 身份项携带 managementUnitIds（用户级统一口径：后端给每条身份下发同一份并集）
      payload = {
        success: true,
        data: MOCK_ROLES.map((r, i) => ({ ...r, managementUnitIds: i === 0 ? [11] : [] })),
      }
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
  }, 20000)

  it('no longer renders tabs (内部/外部/全部合并)', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelectorAll('.n-tabs-tab').length).toBe(0)
  }, 20000)

  it('KPI stat cards removed', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelector('.kpi-row')).toBeFalsy()
    expect(document.querySelector('.kpi-card')).toBeFalsy()
  }, 20000)

  it('toolbar has search + 4 selects + spacer + 新建用户 button at right', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const toolbar = document.querySelector('.toolbar')
    expect(toolbar).toBeTruthy()
    // 搜索框（.rule-filter-search 内原生 input）
    expect(toolbar!.querySelector('.rule-filter-search input')).toBeTruthy()
    // 四个筛选项 .rule-filter-select：用户类型 / 状态 / 直属上级 / 身份（需求5）
    expect(toolbar!.querySelectorAll('.rule-filter-select').length).toBe(4)
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
  }, 20000)

  it('renders pagination with 共 N 条 prefix', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    expect(document.querySelector('.n-data-table')).toBeTruthy()
    const pag = document.querySelector('.n-pagination')
    expect(pag).toBeTruthy()
    expect(pag!.textContent || '').toContain('共 12 条')
  }, 20000)

  it('user type column distinguishes internal/external', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const bodyText = document.querySelector('.n-data-table')?.textContent || ''
    expect(bodyText).toContain('内部')
    expect(bodyText).toContain('外部')
  }, 20000)

  it('拥有身份 column caps at 2 names and folds the rest as +N', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const groups = document.querySelectorAll('.role-tags')
    // 12 个用户里只有 2 个有身份（3 个 / 1 个），其余走 '-' 占位
    expect(groups.length).toBe(2)
    const [three, one] = Array.from(groups)
    // 3 个身份：只渲染前 2 个 + 「+1」，第 3 个不进 DOM（完整列表仅在 tooltip 内）
    expect(three.querySelectorAll('.n-tag').length).toBe(2)
    expect(three.querySelector('.role-more')?.textContent).toBe('+1')
    expect(three.textContent).not.toContain('HRBP')
    // 1 个身份：不折叠，无 +N
    expect(one.querySelectorAll('.n-tag').length).toBe(1)
    expect(one.querySelector('.role-more')).toBeFalsy()
  }, 20000)

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
  }, 20000)

  // 2026-09-19 整合重构后：独立的「角色」弹窗已合并进编辑弹窗
  // （loadUserRoles 在点击「编辑」时调用，身份配置以编辑表单字段呈现，见 UserDirectory.vue:158/745-746）。
  // 此处验证当前真实的身份配置路径，而非已删除的旧 UX。
  it('edit modal opens and contains identity config field (loadUserRoles path)', async () => {
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
    // 身份配置作为编辑表单字段呈现（loadUserRoles 已填入当前用户身份）
    expect(modal!.textContent || '').toContain('身份配置')
  }, 20000)

  // 2026-10-21 管理单元授权配置
  it('edit modal contains 管理单元授权 field', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const editBtn = Array.from(document.querySelectorAll('.n-data-table .n-button')).find((b) =>
      (b.textContent || '').trim() === '编辑'
    ) as HTMLButtonElement | undefined
    await editBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()
    const modal = document.querySelector('.n-modal')
    expect(modal!.textContent || '').toContain('管理单元授权')
    // 授权范围说明（未授权时的生效口径）
    expect(modal!.textContent || '').toContain('未授权时按身份默认数据范围生效')
  }, 20000)

  it('saves management unit scope together with identity config', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const editBtn = Array.from(document.querySelectorAll('.n-data-table .n-button')).find((b) =>
      (b.textContent || '').trim() === '编辑'
    ) as HTMLButtonElement | undefined
    await editBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()
    const saveBtn = Array.from(document.querySelectorAll('.n-modal .n-button')).find((b) =>
      (b.textContent || '').trim() === '保存用户'
    ) as HTMLButtonElement | undefined
    expect(saveBtn).toBeTruthy()
    await saveBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()
    const calls = (global.fetch as any).mock.calls as any[]
    const post = calls.find(
      ([url, opts]: any) =>
        url.includes('/permissions/users/') && url.includes('/roles/') && opts?.method === 'POST'
    )
    expect(post).toBeTruthy()
    const body = JSON.parse(post![1].body)
    // 管理单元授权范围随身份配置一并提交（回显值 11 → 数字）
    expect(body.managementUnitIds).toEqual([11])
  }, 20000)

  it('管理单元范围 column caps at 2 names and folds the rest as +N', async () => {    wrapper = factory()
    await flushPromises()
    await nextTick()
    const groups = document.querySelectorAll('.mgmt-tags')
    expect(groups.length).toBe(2)
    const [three, one] = Array.from(groups)
    expect(three.querySelectorAll('.n-tag').length).toBe(2)
    expect(three.querySelector('.role-more')?.textContent).toBe('+1')
    expect(three.textContent).not.toContain('华北大区')
    expect(one.querySelectorAll('.n-tag').length).toBe(1)
    expect(one.querySelector('.role-more')).toBeFalsy()
  }, 20000)

  // 2026-10-21：身份配置 与 管理单元授权 改为同一行（同一个 n-grid 的两列）
  it('身份配置 与 管理单元授权 位于同一行（同一 n-grid 的两个列）', async () => {
    wrapper = factory()
    await flushPromises()
    await nextTick()
    const editBtn = Array.from(document.querySelectorAll('.n-data-table .n-button')).find((b) =>
      (b.textContent || '').trim() === '编辑'
    ) as HTMLButtonElement | undefined
    await editBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()

    const modal = document.querySelector('.n-modal')!
    const labels = Array.from(modal.querySelectorAll('.n-form-item-label'))
    const roleItem = labels
      .find((el) => (el.textContent || '').trim() === '身份配置')
      ?.closest('.n-form-item') as HTMLElement
    const unitItem = labels
      .find((el) => (el.textContent || '').trim() === '管理单元授权')
      ?.closest('.n-form-item') as HTMLElement
    expect(roleItem).toBeTruthy()
    expect(unitItem).toBeTruthy()

    // 关键断言：两个表单项归属**同一个** n-grid → 同一行
    const roleGrid = roleItem.closest('.n-grid')!
    const unitGrid = unitItem.closest('.n-grid')!
    expect(unitGrid).toBe(roleGrid)

    // 该栅格只有两格，且两项各占一格。
    // naive-ui 的 n-grid-item 渲染为**无 class 的 div**，列宽靠内联 grid-column 表达：
    // 单列 = `span 1 / span 1`，整行 = `span 2 / span 2`。
    expect(roleGrid.children.length).toBe(2)
    const roleCell = roleItem.parentElement as HTMLElement
    const unitCell = unitItem.parentElement as HTMLElement
    expect(roleCell).not.toBe(unitCell)
    expect(roleCell.style.gridColumn).toContain('span 1')
    expect(unitCell.style.gridColumn).toContain('span 1')
  }, 20000)

  // 回归：授权范围加载失败时不得把已有范围清空。
  // 提交时省略 managementUnitIds → 后端按「缺省 = 不动已有范围」处理。
  it('omits managementUnitIds when the scope could not be loaded', async () => {
    const originalFetch = global.fetch
    global.fetch = vi.fn(async (url: string) => {
      let payload: any
      if (url.includes('/api/v1/users/') && !url.includes('/roles/')) {
        payload = { success: true, data: MOCK_USERS }
      } else if (url.includes('/api/v1/permissions/roles/')) {
        payload = { success: true, data: MOCK_ROLES }
      } else if (url.includes('/management-units/tree/')) {
        payload = { success: true, data: MOCK_MGMT_UNITS }
      } else if (url.includes('/permissions/users/') && url.includes('/roles/')) {
        // 身份+范围加载失败（HTTP 500）
        return { ok: false, status: 500, text: async () => JSON.stringify({ success: false }) } as any
      } else {
        payload = { success: true, data: [] }
      }
      return { ok: true, status: 200, text: async () => JSON.stringify(payload) } as any
    }) as any

    wrapper = factory()
    await flushPromises()
    await nextTick()
    const editBtn = Array.from(document.querySelectorAll('.n-data-table .n-button')).find((b) =>
      (b.textContent || '').trim() === '编辑'
    ) as HTMLButtonElement | undefined
    await editBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()
    const saveBtn = Array.from(document.querySelectorAll('.n-modal .n-button')).find((b) =>
      (b.textContent || '').trim() === '保存用户'
    ) as HTMLButtonElement | undefined
    await saveBtn!.click()
    await flushPromises()
    await nextTick()
    await flushPromises()

    const calls = (global.fetch as any).mock.calls as any[]
    const post = calls.find(
      ([url, opts]: any) =>
        url.includes('/permissions/users/') && url.includes('/roles/') && opts?.method === 'POST'
    )
    expect(post).toBeTruthy()
    const body = JSON.parse(post![1].body)
    expect(body.managementUnitIds).toBeUndefined()
    global.fetch = originalFetch
  }, 20000)

  // 授权范围挂在「用户 × 身份」上：没有身份时必须拦下并提示，而不是静默丢弃
  it('blocks submit when management units are set without any identity', async () => {    wrapper = factory()
    await flushPromises()
    await nextTick()
    const newBtn = Array.from(document.querySelectorAll('.toolbar .n-button')).find((b) =>
      (b.textContent || '').includes('新建用户')
    ) as HTMLButtonElement | undefined
    await newBtn!.click()
    await flushPromises()
    await nextTick()
    // 模拟管理员选了管理单元但没选身份
    const vm = wrapper.findComponent(UserDirectory).vm as any
    vm.formState.managementUnitIds = ['11']
    await nextTick()
    const saveBtn = Array.from(document.querySelectorAll('.n-modal .n-button')).find((b) =>
      (b.textContent || '').trim() === '保存用户'
    ) as HTMLButtonElement | undefined
    await saveBtn!.click()
    await flushPromises()
    await nextTick()
    const calls = (global.fetch as any).mock.calls as any[]
    const posted = calls.some(
      ([url, opts]: any) =>
        url.includes('/permissions/users/') && url.includes('/roles/') && opts?.method === 'POST'
    )
    expect(posted).toBe(false)
  }, 20000)
})

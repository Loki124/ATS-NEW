/**
 * 身份编辑弹窗「读 / 写拆分」（2026-10-15）DOM 级回归。
 *
 * 背景：操作权限原先寄生在 ModulePermCard 的「段② 谁能改」里，与读范围混在同一张卡，
 * 5 模块 × 13 动作 = 65 个勾选框重复堆叠。现已拆为独立页签：
 *   页签 3「数据权限」= 看得见什么（ModulePermCard，只留读范围，不掺任何操作权限信息）
 *   页签 4「操作权限」= 能对看得见的数据做哪些操作（ModuleActionCard，未配置默认折叠）
 *
 * 本文件锁定拆分后的对外契约：
 *   - 四个页签齐备且「操作权限」与「数据权限」并列
 *   - 数据权限页签**不含任何操作权限信息与跳转入口**（2026-10-16 兵哥拍板整条移除）
 *   - 操作权限页签默认只展开已配置（mode!=='none'）的卡，未配置的收成一行摘要
 *   - 切到操作权限页签渲染出 5 张卡（含 ap-card-* 定位锚点）
 *   - 动作墙按 常规/危险 两组渲染，预设包按钮可见
 *
 * 🔴 查询必须走 document：NModal 默认 teleport 到 body，wrapper.findAll 只能看到
 *    Wrapper 那一层（挂在 attachTo 的容器里），摸不到弹窗内容。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { naivePlugin } from '../../../../plugins/naive'
import RoleEditModal from '../RoleEditModal.vue'

const h0 = vi.hoisted(() => ({
  fetchAllResources: vi.fn(),
  getRoleDataPerm: vi.fn(),
  getRoleDataPermOptions: vi.fn(),
  saveRoleDataPerm: vi.fn(),
  previewBindTemplate: vi.fn(),
}))

vi.mock('@/api/permission-resource', () => ({
  fetchAllResources: h0.fetchAllResources,
}))

vi.mock('@/api/data-permission', () => ({
  getRoleDataPerm: h0.getRoleDataPerm,
  getRoleDataPermOptions: h0.getRoleDataPermOptions,
  saveRoleDataPerm: h0.saveRoleDataPerm,
  previewBindTemplate: h0.previewBindTemplate,
}))

vi.mock('@/api/role-v2', () => ({
  listRoles: vi.fn(),
  createRole: vi.fn(),
  updateRole: vi.fn(),
  syncRolePermissions: vi.fn(),
  cloneFromTemplate: vi.fn(),
}))

const RESOURCES = [
  { resourceCode: 'recruit:demand:list', resourceName: '需求列表', module: 'demand' },
  { resourceCode: 'recruit:candidate:list', resourceName: '候选人列表', module: 'candidate' },
]

/** 5 模块的读/写配置基线（写侧刻意覆盖四种 mode：none / all / owner / scope） */
const MODULES = [
  {
    moduleKey: 'demand', mode: 'scope', expr: '', featureGranted: true,
    groups: [{
      id: 'g1', expr: '',
      conditions: [{ id: 'c1', kind: 'relationship', dimension: 'dept', operator: 'in', values: [{ id: 'd1', label: '技术部' }] }],
    }],
    write: { mode: 'owner', expr: '', groups: [], actions: ['view', 'edit'] },
  },
  { moduleKey: 'process', mode: 'all', expr: '', featureGranted: true, groups: [], write: { mode: 'none', expr: '', groups: [], actions: [] } },
  { moduleKey: 'position', mode: 'all', expr: '', featureGranted: true, groups: [], write: { mode: 'all', expr: '', groups: [], actions: [] } },
  { moduleKey: 'candidate', mode: 'all', expr: '', featureGranted: true, groups: [], write: { mode: 'scope', expr: '', groups: [], actions: ['view'] } },
  { moduleKey: 'talent', mode: 'all', expr: '', featureGranted: true, groups: [], write: { mode: 'none', expr: '', groups: [], actions: [] } },
]

const OPTIONS = {
  modules: ['demand', 'process', 'position', 'candidate', 'talent'].map((k) => ({
    moduleKey: k,
    label: k,
    dimensions: [{ key: 'dept', label: '部门', valueType: 'department', options: [] }],
    attributeFields: [],
  })),
  actionRegistry: [
    { key: 'view', label: '查看', category: 'read', destructive: false, enabled: true, is_system: true, sort_order: 10 },
    { key: 'edit', label: '编辑', category: 'write', destructive: false, enabled: true, is_system: true, sort_order: 110 },
    { key: 'create', label: '创建', category: 'write', destructive: false, enabled: true, is_system: true, sort_order: 120 },
    { key: 'merge', label: '合并', category: 'write', destructive: true, enabled: true, is_system: true, sort_order: 310 },
    { key: 'delete', label: '删除', category: 'write', destructive: true, enabled: true, is_system: true, sort_order: 320 },
  ],
  presetPackages: [
    { key: 'owner_full', label: '负责人全量', actionKeys: ['view', 'edit', 'merge'], module: null },
  ],
}

const ROLE = {
  id: 'role-1',
  roleCode: 'CUSTOM_HR',
  roleName: '自定义HR',
  templateCode: '',
  defaultDataScopeType: null,
  description: '',
  status: 1,
  permissionCodes: ['recruit:demand:list'],
}

const $all = (sel: string): HTMLElement[] => Array.from(document.querySelectorAll<HTMLElement>(sel))
const $one = (sel: string): HTMLElement | null => document.querySelector<HTMLElement>(sel)
const text = (el: Element | null): string => (el?.textContent ?? '').trim()

function factory(role: Record<string, unknown> | null = ROLE) {
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
    slots: { default: () => h(RoleEditModal as any, { show: true, role }) },
    attachTo: document.body,
  })
  w.vm.$.appContext.app.use(naivePlugin)
  w.vm.$.appContext.app.use(pinia)
  return w
}

/** 按页签文案定位并点击（比下标更抗顺序调整） */
async function gotoTab(label: string) {
  const tabs = $all('.n-tabs-tab')
  const tab = tabs.find((t) => text(t).includes(label))
  expect(tab, `找不到页签「${label}」；实际页签：${tabs.map(text).join(' | ')}`).toBeTruthy()
  tab!.click()
  await flushPromises()
}

beforeEach(() => {
  document.body.innerHTML = ''
  h0.fetchAllResources.mockReset().mockResolvedValue(RESOURCES)
  h0.getRoleDataPerm.mockReset().mockResolvedValue({ modules: MODULES })
  h0.getRoleDataPermOptions.mockReset().mockResolvedValue(OPTIONS)
  h0.saveRoleDataPerm.mockReset().mockResolvedValue({ modules: [] })
  h0.previewBindTemplate.mockReset().mockResolvedValue({ groups: [] })
})

describe('RoleEditModal 读/写拆分', () => {
  it('四个页签齐备，「数据权限」紧随「基础信息」（2026-10-18 兵哥调整）', async () => {
    factory()
    await flushPromises()
    const tabs = $all('.n-tabs-tab').map(text)
    expect(tabs).toHaveLength(4)
    expect(tabs[0]).toContain('基础信息')
    expect(tabs[1]).toContain('数据权限')
    expect(tabs[2]).toContain('功能权限')
    expect(tabs[3]).toContain('操作权限')
  })

  it('操作权限内容默认不渲染（show:lazy），切到该页签才出现', async () => {
    factory()
    await flushPromises()
    expect($all('.action-card')).toHaveLength(0)
    await gotoTab('操作权限')
    expect($all('.action-card')).toHaveLength(5)
  })

  it('数据权限页签不再出现任何操作权限摘要条/ 入口（2026-10-16 兵哥拍板）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')

    // 读/写拆分后曾在此加「操作权限 + 徽标 + 去配置」摘要条，现已整条移除：
    // 操作权限有独立页签，本页复述状态只会诱导「两处都能配」的错觉。
    expect($all('.action-summary')).toHaveLength(0)
    expect($all('.as-label')).toHaveLength(0)
    expect($all('.as-badge')).toHaveLength(0)
    expect($all('.as-goto')).toHaveLength(0)
    // 页面上不得残留指向操作权限的跳转入口
    const doc = document.body.textContent || ''
    expect(doc).not.toContain('去配置')
    // 但读范围自身的配置入口仍在（不能连累）
    expect($all('.module-card').length).toBe(5)
    expect($all('.module-card .summary-actions').length).toBeGreaterThan(0)
  })

  it('切到操作权限页签渲染出 5 张操作权限卡（带定位锚点）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')
    expect($all('.action-card')).toHaveLength(0)

    await gotoTab('操作权限')

    expect($all('.action-card')).toHaveLength(5)
    expect(document.getElementById('ap-card-demand')).toBeTruthy()
  })

  it('操作权限页签默认只展开已配置（mode!==none）的卡', async () => {
    factory()
    await flushPromises()
    await gotoTab('操作权限')

    const cards = $all('.action-card')
    expect(cards).toHaveLength(5)
    // demand(owner) / position(all) / candidate(scope) 激活 → 展开；process / talent 未配置 → 收起
    expect(cards.filter((c) => c.classList.contains('open'))).toHaveLength(3)
    // 收起的卡仍有一行摘要：模块名 + 徽标 + 展开入口
    expect(text(cards[1].querySelector('.ac-title'))).toBe('process')
    expect(text(cards[1].querySelector('.ac-badge'))).toBe('未配置')
    expect(text(cards[1].querySelector('.ac-toggle'))).toBe('展开')
    // 收起态不渲染动作墙（避免 65 个勾选框一上来全铺开）
    expect(cards[1].querySelectorAll('.action-check')).toHaveLength(0)
  })

  it('展开的操作权限卡含写模式四选一 + 动作墙两组 + 预设包', async () => {
    factory()
    await flushPromises()
    await gotoTab('操作权限')

    const demand = $all('.action-card')[0]
    // 写模式四选一
    expect(demand.querySelectorAll('.ac-mode-group .n-radio-button')).toHaveLength(4)
    // 动作墙按 常规/危险 分组（真源是后端 destructive 标记 + category，不按动作名硬编码）
    const groups = Array.from(demand.querySelectorAll('.action-group'))
    expect(groups).toHaveLength(2)
    expect(text(groups[0].querySelector('.group-name'))).toBe('常规操作')
    expect(text(groups[1].querySelector('.group-name'))).toContain('危险操作')
    // 回归（HEAD 预存 bug）：种子把合并/删除标为 category='write' + destructive=true，
    // 只按 category 分组会让危险组空转 → 必须落到危险组且带红色警示标记
    const checksOf = (g: Element) => Array.from(g.querySelectorAll('.action-check')).map((c) => text(c))
    expect(checksOf(groups[0])).toEqual(['编辑', '创建'])
    expect(checksOf(groups[1])).toEqual(['合并', '删除'])
    // 危险组有红色警示标记（颜色 + 文字双通道）
    expect(text(groups[1].querySelector('.destructive-tag'))).toBe('高危')
    // 预设包以可见按钮呈现（不藏在下拉里）
    expect(demand.querySelector('.preset-row')).toBeTruthy()
    expect(text(demand.querySelector('.preset-row button'))).toBe('负责人全量')
  })

  it('owner 模式已勾选动作在动作墙中回显', async () => {
    factory()
    await flushPromises()
    await gotoTab('操作权限')

    const demand = $all('.action-card')[0]
    // fixture: actions = ['view','edit']；view 属 read 类别不进写范围动作墙，故仅 edit 被勾
    expect(demand.querySelectorAll('.action-check.n-checkbox--checked')).toHaveLength(1)
    expect(text(demand.querySelector('.action-check.n-checkbox--checked'))).toBe('编辑')
  })

  it('动作管理入口随操作权限页签出现（仅当前登录超管可见）', async () => {
    factory()
    await flushPromises()
    await gotoTab('操作权限')
    // 默认 store 无角色 → 非超管 → 不渲染（后端 IsSuperAdmin 双保险）
    expect($all('button').some((b) => text(b).includes('动作与预设包管理'))).toBe(false)
  })
})

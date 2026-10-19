/**
 * 身份编辑弹窗「读 / 写拆分」（2026-10-15）DOM 级回归。
 *
 * 背景：操作权限原先寄生在 ModulePermCard 的「段② 谁能改」里，与读范围混在同一张卡，
 * 5 模块 × 13 动作 = 65 个勾选框重复堆叠。拆分后：
 *   页签 2「数据权限」= 看得见什么（ModulePermCard，只留读范围，不掺任何操作权限信息）
 *   页签 3「功能权限」= 资源勾选
 *
 * ⚠️ 2026-10-19：「操作权限」页签（ModuleActionCard + 动作字典管理入口）已从本弹窗移除，
 *   操作权限（写范围 / 动作授权）的配置整体迁入独立的「动态策略」页（SettingsLayout.s69）。
 *   本弹窗的 useRoleDataPerm.submit() 仍保存读 + 写 两半草稿，移除 UI 页签不改变存储的写数据。
 *
 * 本文件锁定对外契约：
 *   - 三个页签齐备（基础信息 / 数据权限 / 功能权限），「数据权限」紧随「基础信息」
 *   - 数据权限页签**不含任何操作权限信息与跳转入口**（2026-10-16 兵哥拍板整条移除）
 *
 * 🔴 查询必须走 document：NModal 默认 teleport 到 body，wrapper.findAll 只能看到
 *    Wrapper 那一层（挂在 attachTo 的容器里），摸不到弹窗内容。
 *
 * 2026-10-18 兵哥权限模型简化（追加锁定）：
 *   - 基础信息页签只剩 roleCode/roleName/description/status 四项
 *     （「来源模板」「默认数据范围」移除：模板仅创建时引用，数据范围仅数据权限页签配置）
 *   - 数据权限卡无 ⓘ icon + hover 提示（与功能权限解耦），标题列宽统一（min-width:5em）
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import fs from 'node:fs'
import path from 'node:path'
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
  it('三个页签齐备，「数据权限」紧随「基础信息」（2026-10-18 兵哥调整 / 2026-10-19 移除操作权限页签）', async () => {
    factory()
    await flushPromises()
    const tabs = $all('.n-tabs-tab').map(text)
    expect(tabs).toHaveLength(3)
    expect(tabs[0]).toContain('基础信息')
    expect(tabs[1]).toContain('数据权限')
    expect(tabs[2]).toContain('功能权限')
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

  it('数据权限卡为「同排紧凑版」两行结构：分段选择器 + 虚线规则框 + 标签链（2026-10-18 兵哥原型）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')

    const demand = $one('#dp-card-demand .module-card')
    expect(demand).toBeTruthy()
    // 第一行：分段选择器三选一，scope 卡选中「指定范围」（ARIA radiogroup）
    const segs = demand!.querySelectorAll('.mc-segment')
    expect(segs).toHaveLength(3)
    expect(text(segs[0])).toBe('无权限')
    expect(text(segs[1])).toBe('全部')
    expect(text(segs[2])).toBe('指定范围')
    expect(segs[2].classList.contains('active')).toBe(true)
    expect(segs[2].getAttribute('aria-checked')).toBe('true')
    // 第二行：虚线规则框（仅 scope 展开）+ 条件标签链 + 修改配置（文案对齐原型）
    expect(demand!.querySelector('.mc-rule-container')).toBeTruthy()
    expect(text(demand!.querySelector('.mc-tag'))).toBe('部门 属于 [技术部]')
    expect(text(demand!.querySelector('.summary-actions button'))).toBe('修改配置')
    // 干净基线不出现「重置」（不常驻多半禁用的按钮）
    expect(demand!.querySelector('.mc-btn-reset')).toBeNull()

    // 切到「全部」：规则框收起，本卡变脏 → 「重置」出现（模块粒度脏检查）
    ;(segs[1] as HTMLElement).click()
    await flushPromises()
    expect($one('#dp-card-demand .mc-rule-container')).toBeNull()
    const resetBtn = $one('#dp-card-demand .mc-btn-reset')
    expect(resetBtn).toBeTruthy()
    expect(text(resetBtn)).toBe('重置')

    // 点重置：只还原本卡读范围（规则框回来、重置消失），不影响其它卡
    resetBtn!.click()
    await flushPromises()
    expect($one('#dp-card-demand .mc-rule-container')).toBeTruthy()
    expect($one('#dp-card-demand .mc-btn-reset')).toBeNull()
  })

  it('none/all 模式的卡不展开规则框（与原型"仅指定范围展示"一致）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')

    // fixture：process/position/candidate/talent 均为 mode='all'
    const processCard = $one('#dp-card-process .module-card')
    expect(processCard!.querySelector('.mc-rule-container')).toBeNull()
    const segs = processCard!.querySelectorAll('.mc-segment')
    expect(text(segs[1])).toBe('全部')
    expect(segs[1].classList.contains('active')).toBe(true)
  })

  it('none/all 模式第二行显示固定描述（2026-10-18 兵哥：各卡二行结构齐整）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')

    // all 模式（fixture: process 卡）→ 固定文案，且不给「修改配置」按钮（无可配内容）
    const processCard = $one('#dp-card-process .module-card')
    expect(text(processCard!.querySelector('.mc-mode-desc'))).toBe('可查看当前模块的全部数据')
    expect(processCard!.querySelector('.summary-actions')).toBeNull()

    // 切到「无权限」（demand 卡点第一段）→ 固定文案切换，规则框仍不展开
    const segs = $one('#dp-card-demand .module-card')!.querySelectorAll('.mc-segment')
    ;(segs[0] as HTMLElement).click()
    await flushPromises()
    const demandCard = $one('#dp-card-demand .module-card')
    expect(text(demandCard!.querySelector('.mc-mode-desc'))).toBe('无当前模块数据权限')
    expect(demandCard!.querySelector('.mc-rule-container')).toBeNull()
  })

  it('基础信息页签只剩四项：无「来源模板」「默认数据范围」（2026-10-18 兵哥调整）', async () => {
    factory()
    await flushPromises()
    // 首个页签（基础信息）默认激活，四个字段一项不多一项不少
    // （required 字段的 label 带 * 后缀，剥离后比对字段名本身）
    const labels = $all('.basic-form .n-form-item-label')
      .map(text)
      .map((s) => s.replace(/\s*\*$/, ''))
    expect(labels).toEqual(['身份编码', '身份名称', '描述', '状态'])
    // 已删字段的残留锚点与说明文字不得复现
    expect($all('.scope-note')).toHaveLength(0)
    const doc = document.body.textContent || ''
    expect(doc).not.toContain('来源模板')
    expect(doc).not.toContain('默认数据范围')
  })

  it('数据权限卡不再有 ⓘ 图标 + hover 提示，标题列宽统一（2026-10-18 兵哥调整）', async () => {
    factory()
    await flushPromises()
    await gotoTab('数据权限')

    // ① 模块级 icon + hover 提示整条移除（与功能权限解耦，各模块单独提示内容全部撤掉）
    expect($all('.hint-btn')).toHaveLength(0)
    expect($all('.module-card .mc-tip')).toHaveLength(0)
    // ② 每张卡都有标题元素（5 模块）
    expect($all('.module-card .mc-title')).toHaveLength(5)
    // ③ 标题列宽统一（.mc-title min-width:5em）→ 各卡分段选择器左边缘对齐。
    //    vitest 默认 css:false，scoped 样式不注入 DOM，改源码级正则守护规则存在性与数值
    //    （范式同 styles/__tests__/table-alignment-rules.test.ts）。
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../../../components/role/ModulePermCard.vue'),
      'utf8',
    )
    expect(src).toMatch(/\.mc-title\s*\{[^}]*min-width:\s*5em/)
  })
})

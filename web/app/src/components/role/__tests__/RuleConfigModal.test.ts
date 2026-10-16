/**
 * 规则弹窗「简历锁定人 · 为空/不为空」DOM 级回归（兵哥 2026-10-15：「选不了」）。
 *
 * 病根：`unifiedOperatorValue` 把 is_empty/is_not_empty 折叠成 'in'，受控下拉
 * 的 :value 重算后与用户所选不符，n-select 把选择秒弹回「包含」。
 * 本文件锁定修复后的对外行为：
 *   - operator=is_empty 回显「为空」而非「包含」；
 *   - 选「不为空」后下拉**保持**不为空（不弹回）；
 *   - 无值运算符下业务值 / 取值来源两个控件消失（设计文档 §4）；
 *   - 选回「包含」控件恢复（可逆，不卡死）；
 *   - 存量 operator=in 行为不变（向后兼容锚点）。
 *
 * 🔴 查询必须走 document：NModal 默认 teleport 到 body，wrapper 的 DOM 查询
 *    只能看到 attachTo 容器那一层（同 RoleEditModal.test.ts 的教训）。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NConfigProvider, NMessageProvider, NSelect } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'
import RuleConfigModal from '../RuleConfigModal.vue'

const h0 = vi.hoisted(() => ({
  listScopeTemplates: vi.fn(),
  previewBindTemplate: vi.fn(),
  getRoleDataPerm: vi.fn(),
  getRoleDataPermOptions: vi.fn(),
  saveRoleDataPerm: vi.fn(),
}))

// useRoleDataPerm（被弹窗 import）在模块层 import 这三个取数函数；
// 弹窗自身只用 listScopeTemplates / previewBindTemplate。全部 mock 掉，
// 避免任何真实 HTTP。
vi.mock('@/api/data-permission', () => ({
  listScopeTemplates: h0.listScopeTemplates,
  previewBindTemplate: h0.previewBindTemplate,
  getRoleDataPerm: h0.getRoleDataPerm,
  getRoleDataPermOptions: h0.getRoleDataPermOptions,
  saveRoleDataPerm: h0.saveRoleDataPerm,
}))

/** 候选人模块维度矩阵（形态与后端 options_payload 的 lock_owner meta 一致） */
const DIMENSIONS = [
  {
    key: 'lock_owner', label: '简历锁定人', valueType: 'user',
    contextKeys: ['currentUser.id'],
    operators: [
      { value: 'in', label: '包含' },
      { value: 'not_in', label: '不包含' },
      { value: 'is_empty', label: '为空' },
      { value: 'is_not_empty', label: '不为空' },
    ],
    options: [{ id: 'u1', label: '张三' }, { id: 'u2', label: '李四' }],
  },
  {
    key: 'creator', label: '创建人', valueType: 'user',
    contextKeys: ['currentUser.id'],
    operators: [
      { value: 'in', label: '包含' },
      { value: 'not_in', label: '不包含' },
    ],
    options: [{ id: 'u1', label: '张三' }],
  },
]

const groupsWith = (operator: string) => [{
  id: 'g1',
  expr: '',
  conditions: [{ id: 'c1', kind: 'relationship' as const, dimension: 'lock_owner', operator, values: [] }],
}]

function factory(operator: string) {
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
    slots: {
      default: () =>
        h(RuleConfigModal as any, {
          show: true,
          moduleName: '候选人管理',
          moduleKey: 'candidate',
          dimensions: DIMENSIONS,
          attributeFields: [],
          groups: groupsWith(operator),
          interExpr: '',
        }),
    },
    attachTo: document.body,
  })
  w.vm.$.appContext.app.use(naivePlugin)
  return w
}

const $one = (sel: string): HTMLElement | null => document.querySelector<HTMLElement>(sel)
const text = (el: Element | null): string => (el?.textContent ?? '').trim()

/** 条件行里的运算符下拉（.cond-verb 挂在 n-select 根元素上） */
function verbSelect(w: ReturnType<typeof factory>) {
  return w.findAllComponents(NSelect).find((s) => s.element.classList.contains('cond-verb'))
}

beforeEach(() => {
  document.body.innerHTML = ''
  h0.listScopeTemplates.mockReset().mockResolvedValue([])
  h0.previewBindTemplate.mockReset().mockResolvedValue({ groups: [] })
  h0.getRoleDataPerm.mockReset()
  h0.getRoleDataPermOptions.mockReset()
  h0.saveRoleDataPerm.mockReset()
})

describe('RuleConfigModal 简历锁定人无值运算符', () => {
  it('operator=is_empty 回显「为空」，不被折叠成「包含」', async () => {
    factory('is_empty')
    await flushPromises()
    const verb = text($one('.cond-verb'))
    expect(verb).toContain('为空')
    expect(verb).not.toContain('不为空')
    expect(verb).not.toContain('包含')
  })

  it('operator=is_not_empty 回显「不为空」', async () => {
    factory('is_not_empty')
    await flushPromises()
    const verb = text($one('.cond-verb'))
    expect(verb).toContain('不为空')
    expect(verb).not.toContain('包含')
  })

  it('无值运算符下业务值/取值来源控件消失，预览句为「简历锁定人 为空」', async () => {
    factory('is_empty')
    await flushPromises()
    expect($one('.cond-src')).toBeNull()
    expect($one('.cond-val')).toBeNull()
    expect(text($one('.preview-text'))).toBe('（简历锁定人 为空）')
  })

  it('选「不为空」后下拉保持不为空（修复前会秒弹回「包含」）', async () => {
    const w = factory('is_empty')
    await flushPromises()
    const sel = verbSelect(w)
    expect(sel, '找不到运算符下拉 .cond-verb').toBeTruthy()
    await sel!.vm.$emit('update:value', 'is_not_empty')
    await flushPromises()
    const verb = text($one('.cond-verb'))
    expect(verb).toContain('不为空')
    expect(verb).not.toContain('包含')
    expect($one('.cond-val')).toBeNull()
  })

  it('选回「包含」业务值控件恢复（可逆，不卡死）', async () => {
    const w = factory('is_empty')
    await flushPromises()
    const sel = verbSelect(w)
    await sel!.vm.$emit('update:value', 'in')
    await flushPromises()
    expect(text($one('.cond-verb'))).toContain('包含')
    expect($one('.cond-val')).toBeTruthy()
  })

  it('存量 operator=in 行为不变：包含 + 业务值/取值来源俱在（向后兼容锚点）', async () => {
    factory('in')
    await flushPromises()
    expect(text($one('.cond-verb'))).toContain('包含')
    expect($one('.cond-val')).toBeTruthy()
    // lock_owner 的 contextKeys 含 currentUser.id → 支持动态取值
    expect($one('.cond-src')).toBeTruthy()
  })
})

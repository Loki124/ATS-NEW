/**
 * StrategyModuleConfigModal 表达式能力回归（兵哥 2026-10-20 截图反馈：
 * 「条件组内多条条件之间、条件组与条件组之间无法设置且/或关系」）。
 *
 * 锁定修复后的对外行为（与角色数据权限弹窗 RuleConfigModal 同一交互范式）：
 *   1. 每个条件组渲染「组内表达式」输入 + 一个「组间组合」输入
 *      （静态「或 (OR)」分隔符已移除 —— 自定义组间关系下它是错的）；
 *   2. 非法表达式 → 状态图标 error 态 + 点「确定应用」被拦
 *      （message.warning，无 apply emit）—— 非法表达式绝不能被保存；
 *   3. 合法自定义（组内 `1 or 2`、组间 `1 and 2`）→ apply payload 原样带回两级表达式，
 *      预览句按真实表达式渲染且/或；
 *   4. initialExpr/initialGroups 打开时正确回填（往返编辑不丢）。
 *
 * ⚠️ 非法表达式用例用「同层混用 and/or」（`1 and 2 or 3`）而非 `1 and`：
 *    共享校验器 validateExpr（useRoleDataPerm）对「运算符后缺运算数」类错误
 *    （如 `1 and`）存在漏判（parseOr 的 `!left.andSeen && err` 守卫会把
 *    and 之后的错误吞掉），该共享函数不在本 BugFix 文件清单内、已按纪律
 *    上报主理人另行处理；后端 validate_expr 对两类错误均正确拒绝
 *    （见 test_dynamic_strategy_expr_guard.py），安全闭环不依赖前端漏判。
 *
 * 🔴 查询必须走 document：NModal 默认 teleport 到 body，wrapper 的 DOM 查询
 *    只能看到 attachTo 容器那一层（同 RuleConfigModal.test.ts 的教训）。
 * 🔴 naive-ui 在本文件级覆写 mock：useMessage 返回**共享** stub，才能断言
 *    warning 被调用（setup.ts 全局 mock 每次调用返新对象，无从断言）；
 *    其余导出仍走 importOriginal 展开，真实组件行为不变。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { NConfigProvider, NMessageProvider, NInput } from 'naive-ui'
import { naivePlugin } from '../../../plugins/naive'
import StrategyModuleConfigModal from '../StrategyModuleConfigModal.vue'
import type { PermConditionGroup } from '@/api/data-permission'

const h0 = vi.hoisted(() => ({
  message: { info: vi.fn(), success: vi.fn(), warning: vi.fn(), error: vi.fn(), loading: vi.fn() },
  getRoleDataPerm: vi.fn(),
  getRoleDataPermOptions: vi.fn(),
  saveRoleDataPerm: vi.fn(),
  listScopeTemplates: vi.fn(),
  previewBindTemplate: vi.fn(),
}))

// useRoleDataPerm（被弹窗 import）在模块层 import 这些取数函数；全部 mock 掉，
// 避免任何真实 HTTP。useMessage 覆写为共享 stub 供断言。
vi.mock('@/api/data-permission', () => ({
  getRoleDataPerm: h0.getRoleDataPerm,
  getRoleDataPermOptions: h0.getRoleDataPermOptions,
  saveRoleDataPerm: h0.saveRoleDataPerm,
  listScopeTemplates: h0.listScopeTemplates,
  previewBindTemplate: h0.previewBindTemplate,
}))

vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  return {
    ...actual,
    useMessage: () => h0.message,
    useDialog: () => ({ ...h0.message, create: vi.fn() }),
    useNotification: () => ({ create: vi.fn() }),
  }
})

/** 单维度（部门）矩阵：形态与后端 options_payload 的 dept meta 一致 */
const DIMENSIONS = [
  {
    key: 'dept', label: '部门', valueType: 'department',
    contextKeys: ['currentUser.deptSubtree'],
    options: [{ id: 'd1', label: '研发部' }, { id: 'd2', label: '销售部' }],
  },
]

/** 造一条关系维度条件（静态、部门维度） */
function cond(id: string) {
  return {
    id, kind: 'relationship' as const,
    dimension: 'dept', operator: 'in:exact', relation: 'exact' as const,
    values: [], valueSource: 'static' as const,
  }
}

/** 造数据工厂：nGroups 组 × nConds 条件；intraExpr 覆写第 1 组组内表达式 */
function makeGroups(nGroups = 2, nConds = 2, intraExpr = ''): PermConditionGroup[] {
  return Array.from({ length: nGroups }, (_, gi) => ({
    id: `g${gi + 1}`,
    expr: gi === 0 ? intraExpr : '',
    conditions: Array.from({ length: nConds }, (_, ci) => cond(`g${gi + 1}c${ci + 1}`)),
  }))
}

function factory(groups: PermConditionGroup[], expr: string) {
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
        h(StrategyModuleConfigModal as any, {
          show: true,
          moduleKey: 'candidate',
          moduleName: '候选人管理',
          dimensions: DIMENSIONS,
          attributeFields: [],
          initialGroups: groups,
          initialExpr: expr,
        }),
    },
    attachTo: document.body,
    // 首渲染前注册全量 naive 组件（n-modal teleport 内容与 n-tag 等均走全局解析）
    global: { plugins: [naivePlugin] },
  })
  return w
}

/** 弹窗内全部表达式输入框（DOM 顺序 = 各组组内 → 组间） */
function exprInputs(w: ReturnType<typeof factory>) {
  return w.findAllComponents(NInput)
}

/** 弹窗组件实例（teleport 到 body，事件记录仍在实例上） */
function modalOf(w: ReturnType<typeof factory>) {
  return w.findComponent(StrategyModuleConfigModal as any)
}

/** 按按钮文案点击（n-modal teleport 到 body，按钮只在 document 里） */
async function clickByText(label: string) {
  const btn = [...document.querySelectorAll('button')].find(
    (b) => (b.textContent ?? '').trim() === label,
  )
  expect(btn, `找不到按钮「${label}」`).toBeTruthy()
  btn!.click()
  await flushPromises()
}

beforeEach(() => {
  document.body.innerHTML = ''
  h0.message.warning.mockReset()
  h0.getRoleDataPerm.mockReset()
  h0.getRoleDataPermOptions.mockReset()
  h0.saveRoleDataPerm.mockReset()
  h0.listScopeTemplates.mockReset()
  h0.previewBindTemplate.mockReset()
})

describe('StrategyModuleConfigModal 组内/组间表达式（且/或）能力', () => {
  it('渲染每个条件组的「组内表达式」输入与一个「组间组合」输入', async () => {
    factory(makeGroups(2), '')
    await flushPromises()
    // 2 组 → 2 个组内表达式行；组间组合行恒 1 个（inter-block 内）
    expect(document.querySelectorAll('.group-block .group-inner-row').length).toBe(2)
    expect(document.querySelectorAll('.group-block .group-inner-row .n-input').length).toBe(2)
    expect(document.querySelectorAll('.inter-block .group-inner-row').length).toBe(1)
    expect(document.querySelectorAll('.inter-block .n-input').length).toBe(1)
    // 标签文案（真实 zh-CN 文案，由 setup.ts 的 t() 提供）
    const labelText = (sel: string) => (document.querySelector(sel)?.textContent ?? '').trim()
    expect(labelText('.group-block .inner-label')).toContain('组内表达式')
    expect(labelText('.inter-block .inner-label')).toContain('组间组合')
    // 静态组间分隔符「或 (OR)」已移除：自定义组间关系下它会误导（把「且」显示成「或」）
    expect(document.querySelector('.group-sep')).toBeNull()
  })

  it('组内非法表达式（1 and 2 or 3 同层混用）→ 状态图标 error 态 + 确定应用被拦（warning，无 apply emit）', async () => {
    // 3 条条件：编号 1..3 俱在，唯一非法点即同层混用 and/or
    const w = factory(makeGroups(1, 3, '1 and 2 or 3'), '')
    await flushPromises()
    const inputs = exprInputs(w)
    expect(inputs.length).toBe(2) // 1 组 × 组内 + 组间
    await inputs[0].vm.$emit('update:value', '1 and 2 or 3')
    await flushPromises()
    // 状态图标转 error 态
    expect(document.querySelector('.group-block .expr-status.bad')).toBeTruthy()
    expect(document.querySelector('.group-block .expr-status.ok')).toBeNull()
    // 点「确定应用」被拦：warning 已提示，且没有 apply / 关闭 emit
    await clickByText('确定应用')
    expect(h0.message.warning).toHaveBeenCalledTimes(1)
    const modal = modalOf(w)
    expect(modal.emitted('apply')).toBeUndefined()
    expect(modal.emitted('update:show')).toBeUndefined()
  })

  it('组间非法表达式（1 and 2 or 3 同层混用）同样被拦', async () => {
    // 3 组：编号 1..3 俱在，唯一非法点即同层混用 and/or
    const w = factory(makeGroups(3, 2), '')
    await flushPromises()
    const inputs = exprInputs(w)
    expect(inputs.length).toBe(4) // 3 组 × 组内 + 组间
    await inputs[3].vm.$emit('update:value', '1 and 2 or 3')
    await flushPromises()
    expect(document.querySelector('.inter-block .expr-status.bad')).toBeTruthy()
    await clickByText('确定应用')
    expect(h0.message.warning).toHaveBeenCalledTimes(1)
    const modal = modalOf(w)
    expect(modal.emitted('apply')).toBeUndefined()
  })

  it('合法自定义（组内 1 or 2、组间 1 and 2）→ apply payload 带回表达式，预览按真实关系渲染', async () => {
    const w = factory(makeGroups(2), '')
    await flushPromises()
    const inputs = exprInputs(w)
    await inputs[0].vm.$emit('update:value', '1 or 2')
    await inputs[2].vm.$emit('update:value', '1 and 2')
    await flushPromises()
    // 状态图标回合法态
    expect(document.querySelector('.group-block .expr-status.ok')).toBeTruthy()
    expect(document.querySelector('.inter-block .expr-status.ok')).toBeTruthy()
    // 预览句按真实表达式渲染：组内「或」+ 组间「且」（不再是写死的且/或）
    const preview = document.querySelector('.preview-text')?.textContent ?? ''
    expect(preview).toContain('或')
    expect(preview).toContain('且')
    await clickByText('确定应用')
    const events = modalOf(w).emitted('apply')
    expect(events).toBeTruthy()
    const payload = events![0][0] as { groups: PermConditionGroup[]; expr: string }
    expect(payload.expr).toBe('1 and 2')
    expect(payload.groups[0].expr).toBe('1 or 2')
    expect(payload.groups[1].expr).toBe('')
  })

  it('initialExpr/initialGroups 打开时正确回填（往返不丢）', async () => {
    const w = factory(makeGroups(2, 2, '1 or 2'), '1 and 2')
    await flushPromises()
    const inputs = exprInputs(w)
    expect(inputs[0].props('value')).toBe('1 or 2')
    expect(inputs[2].props('value')).toBe('1 and 2')
    // 直接应用：表达式原样往返（不再被抹空）
    await clickByText('确定应用')
    const payload = modalOf(w).emitted('apply')![0][0] as { groups: PermConditionGroup[]; expr: string }
    expect(payload.expr).toBe('1 and 2')
    expect(payload.groups[0].expr).toBe('1 or 2')
  })

  it('留空表达式合法（默认 且/或）：apply 放行且 expr 为空串', async () => {
    const w = factory(makeGroups(2), '')
    await flushPromises()
    const inputs = exprInputs(w)
    expect(inputs[0].props('value')).toBe('')
    expect(inputs[2].props('value')).toBe('')
    await clickByText('确定应用')
    const payload = modalOf(w).emitted('apply')![0][0] as { groups: PermConditionGroup[]; expr: string }
    expect(payload.expr).toBe('')
    expect(payload.groups[0].expr).toBe('')
  })
})

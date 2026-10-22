/**
 * 部门树筛选组件（组件库）· 交互契约（2026-10-22）
 *
 * 锁四件事：
 *  1. 触发器：未选显示占位符，选中显示部门摘要；
 *  2. 面板：两个策略开关（自动选中全部子部门 / 展示历史停用部门）齐备且文案正确；
 *  3. 勾选 → 回传已选部门 id 列表（v-model），且「自动选中」开关能改变勾选范围；
 *  4. 「展示历史停用部门」打开后，停用部门出现在树里。
 *
 * 勾选传播的细规则在 `utils/__tests__/deptTree.test.ts`（纯函数层），
 * 本文件只锁组件的接线（渲染 / 事件 / 开关联动），不重复测算法。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import DeptTreeFilter from '../DeptTreeFilter.vue'

const DEPTS = [
  { id: 'root', name: '集团总部', parentId: null, status: 'ACTIVE' },
  { id: 'bg-dian', name: '能电BG', parentId: 'root', status: 'ACTIVE' },
  { id: 'dept-shi', name: '能食电器', parentId: 'bg-dian', status: 'ACTIVE' },
  { id: 'dept-jing', name: '经营管理部', parentId: 'bg-dian', status: 'ACTIVE' },
  { id: 'bg-zhan', name: '能战BG', parentId: 'root', status: 'INACTIVE' },
]

const mountFilter = (props: Record<string, any> = {}) => {
  const wrapper = mount(DeptTreeFilter, {
    props: { departments: DEPTS as any, ...props },
    global: { plugins: [createPinia()], stubs: { teleport: true } },
  })
  return wrapper
}

/** 打开浮层面板（n-popover 内容在 show 时渲染） */
const openPanel = async (wrapper: ReturnType<typeof mountFilter>) => {
  await wrapper.find('.dept-filter__trigger').trigger('click')
  await flushPromises()
  return wrapper
}

describe('部门树筛选组件（组件库）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('① 触发器：未选时显示占位符', async () => {
    const w = mountFilter({ placeholder: '全部归属部门' })
    expect(w.find('.dept-filter__value').text()).toBe('全部归属部门')
    expect(w.find('.dept-filter__value').classes()).toContain('is-placeholder')
  })

  it('② 触发器：选中后显示部门摘要', async () => {
    const w = mountFilter({ modelValue: ['dept-shi'] })
    expect(w.find('.dept-filter__value').text()).toBe('能食电器')
  })

  it('③ 面板：两个策略开关齐备且文案正确', async () => {
    const w = await openPanel(mountFilter())
    const text = w.find('.dept-filter__panel').text()
    expect(text).toContain('自动选中全部子部门')
    expect(text).toContain('展示历史停用部门')
    expect(w.findAll('.n-switch').length).toBe(2)
  })

  it('④ 勾选部门 → 回传已选部门 id 列表', async () => {
    const w = await openPanel(mountFilter())
    // 树节点上的复选框（n-tree checkable → .n-tree-node-checkbox > .n-checkbox）
    const boxes = w.findAll('.n-tree-node-checkbox .n-checkbox')
    expect(boxes.length).toBeGreaterThan(0)
    await boxes[0].trigger('click')
    await flushPromises()
    const emitted = w.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const last = emitted![emitted!.length - 1][0] as string[]
    expect(last.length).toBeGreaterThan(0)
    expect(last.every((k) => typeof k === 'string')).toBe(true)
  })

  it('⑤ 「自动选中全部子部门」默认开启：勾父即带上后代', async () => {
    const w = await openPanel(mountFilter())
    const vm = w.vm as any
    // 直接驱动勾选逻辑（避免依赖 n-tree 内部 DOM 细节）
    vm.onCheck(['bg-dian'])
    await flushPromises()
    const emitted = w.emitted('update:modelValue')!
    const last = emitted[emitted.length - 1][0] as string[]
    expect(last).toContain('bg-dian')
    expect(last).toContain('dept-shi')
    expect(last).toContain('dept-jing')
  })

  it('⑥ 关掉「自动选中全部子部门」→ 勾父只带上自己', async () => {
    const w = await openPanel(mountFilter())
    const vm = w.vm as any
    vm.autoSelect = false
    await flushPromises()
    vm.onCheck(['bg-dian'])
    await flushPromises()
    const emitted = w.emitted('update:modelValue')!
    const last = emitted[emitted.length - 1][0] as string[]
    expect(last).toEqual(['bg-dian'])
  })

  it('⑦ 「展示历史停用部门」打开后，停用部门出现在树里', async () => {
    const w = await openPanel(mountFilter())
    expect(w.find('.dept-filter__tree').text()).not.toContain('能战BG')
    const vm = w.vm as any
    vm.showInactive = true
    await flushPromises()
    expect(w.find('.dept-filter__tree').text()).toContain('能战BG')
  })

  it('⑧ 清空 → 回传空列表', async () => {
    const w = await openPanel(mountFilter({ modelValue: ['dept-shi'] }))
    const btn = w.findAll('button').find((b) => b.text() === '清空')
    expect(btn).toBeTruthy()
    await btn!.trigger('click')
    await flushPromises()
    const emitted = w.emitted('update:modelValue')!
    expect(emitted[emitted.length - 1][0]).toEqual([])
  })
})

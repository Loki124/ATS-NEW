import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ReasonRuleWizard from '../ReasonRuleWizard.vue'

vi.mock('../../../api/reason-library', () => ({
  getRule: vi.fn(async () => ({
    id: 'r1',
    name: 'Rule A',
    enabled: true,
    isSystem: false,
    isPresetDefault: false,
    categories: [{ id: 'c1', name: 'Cat', level: 1, order: 0, parentId: '', allowCustom: false, tags: [], color: '' }],
    sceneAssignments: [],
    scenes: [],
    version: 1,
  })),
  listTags: vi.fn(async () => ({ items: [] })),
  getSceneConfig: vi.fn(async () => ({ items: [] })),
  wizardSave: vi.fn(async () => ({ id: 'r1', name: 'Rule A', enabled: false })),
  createRule: vi.fn(async () => ({ id: 'new' })),
  discardDraftRule: vi.fn(async () => ({})),
  extractReasonApiError: vi.fn((_e: unknown, fb: string) => fb),
}))

import * as api from '../../../api/reason-library'

afterEach(() => {
  document.body.innerHTML = ''
})

beforeEach(() => {
  vi.clearAllMocks()
})

async function settle(wrapper: ReturnType<typeof mount>) {
  await (wrapper.vm as any).$nextTick()
  await new Promise((r) => setTimeout(r, 0))
  await flushPromises()
}

function clickConfirm() {
  const btn = Array.from(document.body.querySelectorAll<HTMLButtonElement>('.n-button')).find((b) =>
    b.textContent?.includes('确认停用'),
  )
  if (!btn) throw new Error('confirm button not found')
  btn.click()
}

describe('ReasonRuleWizard 停用二次风险确认', () => {
  it('保存时把启用中的规则关为停用 → 先弹确认, 确认后才真正保存', async () => {
    const wrapper = mount(ReasonRuleWizard, {
      props: { show: true, ruleId: 'r1' },
      attachTo: document.body,
    })
    await settle(wrapper)
    expect((wrapper.vm as any).wizard?.enabled).toBe(true)

    // 模拟在向导内把规则关为停用
    const vm1 = wrapper.vm as any
    vm1.wizard.enabled = false
    await settle(wrapper)

    await (wrapper.vm as any).onSave()
    await settle(wrapper)

    // 未直接保存, 而是弹出二次风险确认
    expect(api.wizardSave).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('停用风险确认')

    // 勾选「已知晓」→ 点击「确认停用」
    const checkbox = document.body.querySelector<HTMLElement>('.n-checkbox')!
    checkbox.click()
    await settle(wrapper)
    clickConfirm()
    await settle(wrapper)

    expect(api.wizardSave).toHaveBeenCalledTimes(1)
    const savedPayload = (api.wizardSave as any).mock.calls[0][1]
    expect(savedPayload.enabled).toBe(false)
  })

  it('保持启用直接保存, 不弹确认', async () => {
    const wrapper = mount(ReasonRuleWizard, {
      props: { show: true, ruleId: 'r1' },
      attachTo: document.body,
    })
    await settle(wrapper)
    await (wrapper.vm as any).onSave()
    await settle(wrapper)

    expect(api.wizardSave).toHaveBeenCalledTimes(1)
    expect(document.body.textContent).not.toContain('停用风险确认')
  })

  it('系统预置规则关为停用 → 不弹确认 (后端会拒, 走正常保存链路报错)', async () => {
    ;(api.getRule as any).mockImplementationOnce(async () => ({
      id: 'r2',
      name: 'Sys Rule',
      enabled: true,
      isSystem: true,
      isPresetDefault: false,
      categories: [{ id: 'c1', name: 'Cat', level: 1, order: 0, parentId: '', allowCustom: false, tags: [], color: '' }],
      sceneAssignments: [],
      scenes: [],
      version: 1,
    }))
    const wrapper = mount(ReasonRuleWizard, {
      props: { show: true, ruleId: 'r2' },
      attachTo: document.body,
    })
    await settle(wrapper)
    const vm3 = wrapper.vm as any
    vm3.wizard.enabled = false
    await settle(wrapper)
    await (wrapper.vm as any).onSave()
    await settle(wrapper)

    expect(document.body.textContent).not.toContain('停用风险确认')
    expect(api.wizardSave).toHaveBeenCalledTimes(1)
  })
})

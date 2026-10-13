import { describe, it, expect, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import RiskConfirmModal from '../RiskConfirmModal.vue'

const baseProps = {
  show: true,
  title: '停用风险确认',
  riskContent: 'RISK-CONTENT',
  confirmText: '确认停用',
  cancelText: '取消',
  acknowledgeText: '我已知晓',
}

async function settle(wrapper: ReturnType<typeof mount>) {
  await wrapper.vm.$nextTick()
  await new Promise((r) => setTimeout(r, 0))
  await flushPromises()
}

function factory(props = {}) {
  return mount(RiskConfirmModal, {
    props: { ...baseProps, ...props },
    attachTo: document.body,
  })
}

function buttonByText(text: string): HTMLButtonElement {
  const btns = Array.from(document.body.querySelectorAll<HTMLButtonElement>('.n-button'))
  const btn = btns.find((b) => b.textContent?.includes(text))
  if (!btn) throw new Error(`button "${text}" not found in body`)
  return btn
}

function isDisabled(btn: HTMLButtonElement): boolean {
  return btn.hasAttribute('disabled') || btn.classList.contains('n-button--disabled')
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('RiskConfirmModal.vue', () => {
  it('renders title, risk content and acknowledge text when open', async () => {
    const wrapper = factory()
    await settle(wrapper)
    expect(document.body.textContent).toContain('停用风险确认')
    expect(document.body.textContent).toContain('RISK-CONTENT')
    expect(document.body.textContent).toContain('我已知晓')
  })

  it('keeps confirm disabled until acknowledge checkbox is checked', async () => {
    const wrapper = factory()
    await settle(wrapper)

    const confirm = buttonByText('确认停用')
    expect(isDisabled(confirm)).toBe(true)

    const checkbox = document.body.querySelector<HTMLElement>('.n-checkbox')!
    expect(checkbox).toBeTruthy()
    checkbox.click()
    await settle(wrapper)

    const confirmAfter = buttonByText('确认停用')
    expect(isDisabled(confirmAfter)).toBe(false)
  })

  it('emits confirm only after acknowledge + positive click', async () => {
    const wrapper = factory()
    await settle(wrapper)

    // 未勾选时点击确认: 不应 emit confirm
    buttonByText('确认停用').click()
    await settle(wrapper)
    expect(wrapper.emitted('confirm')).toBeFalsy()

    const checkbox = document.body.querySelector<HTMLElement>('.n-checkbox')!
    checkbox.click()
    await settle(wrapper)

    buttonByText('确认停用').click()
    await settle(wrapper)

    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('cancel')).toBeFalsy()
  })

  it('emits cancel on negative click', async () => {
    const wrapper = factory()
    await settle(wrapper)
    buttonByText('取消').click()
    await settle(wrapper)
    expect(wrapper.emitted('cancel')).toBeTruthy()
    expect(wrapper.emitted('confirm')).toBeFalsy()
  })

  it('resets acknowledged when reopened', async () => {
    const wrapper = factory()
    await settle(wrapper)

    const checkbox = document.body.querySelector<HTMLElement>('.n-checkbox')!
    checkbox.click()
    await settle(wrapper)
    expect(isDisabled(buttonByText('确认停用'))).toBe(false)

    // 关闭再打开 -> 勾选状态应被重置
    await wrapper.setProps({ show: false })
    await settle(wrapper)
    await wrapper.setProps({ show: true })
    await settle(wrapper)

    expect(isDisabled(buttonByText('确认停用'))).toBe(true)
  })

  it('disables confirm while loading', async () => {
    const wrapper = factory({ loading: true })
    await settle(wrapper)
    expect(isDisabled(buttonByText('确认停用'))).toBe(true)
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScheduleDayDrawer from '../ScheduleDayDrawer.vue'

const ITEMS = [
  { id: 'i1', date: '2026-06-12', time: '10:00', candidateName: '张三', position: '产品经理' },
]

describe('ScheduleDayDrawer.vue', () => {
  it('shows empty state when no items', () => {
    const w = mount(ScheduleDayDrawer, {
      props: { show: true, date: '2026-06-12', items: [] },
      attachTo: document.body,
    })
    // n-drawer teleports content to body, so check document.body
    expect(document.body.textContent).toContain('无日程')
  })

  it('renders list of items', () => {
    const w = mount(ScheduleDayDrawer, {
      props: { show: true, date: '2026-06-12', items: ITEMS },
      attachTo: document.body,
    })
    // n-drawer teleports content to body, so check document.body
    expect(document.body.textContent).toContain('张三')
    expect(document.body.textContent).toContain('10:00')
  })
})

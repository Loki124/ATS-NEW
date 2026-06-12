import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WeeklySchedule from '../WeeklySchedule.vue'

const ITEMS = [
  { id: 'i1', date: '2026-06-12', time: '10:00', candidateName: '张三', position: '产品经理' },
  { id: 'i2', date: '2026-06-12', time: '14:00', candidateName: '李四', position: '设计师' },
  { id: 'i3', date: '2026-06-15', time: '09:00', candidateName: '王五', position: '前端' },
]

describe('WeeklySchedule.vue', () => {
  it('renders in week mode by default', () => {
    const w = mount(WeeklySchedule, { props: { interviews: ITEMS } })
    expect(w.find('.weekly-schedule__grid').exists()).toBe(true)
    expect(w.find('.weekly-schedule__col').exists()).toBe(true)
  })

  it('switches to month mode on toggle', async () => {
    const w = mount(WeeklySchedule, { props: { interviews: ITEMS } })
    await w.find('[data-testid="mode-month"]').trigger('click')
    expect(w.find('.month-grid').exists()).toBe(true)
  })

  it('emits openDrawer on date cell click', async () => {
    const w = mount(WeeklySchedule, { props: { interviews: ITEMS } })
    // 切到 month 模式,然后点有 item 的 cell
    await w.find('[data-testid="mode-month"]').trigger('click')
    const cells = w.findAll('.month-grid__cell')
    const cell = cells.find((c) => c.text().includes('12'))
    expect(cell).toBeTruthy()
    await cell!.trigger('click')
    expect(w.emitted('openDrawer')).toBeTruthy()
  })
})

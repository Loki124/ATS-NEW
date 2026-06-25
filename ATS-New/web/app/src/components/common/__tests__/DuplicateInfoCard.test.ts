import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DuplicateInfoCard from '../DuplicateInfoCard.vue'

const info = {
  existing_resume_id: 'RES-2024-08521',
  created_at: '2024-08-15',
  history: '高级前端工程师（2024-08）· 已归档',
  cur_status: '未占用 · 可安全合并',
  active_application_id: undefined as string | undefined,
}

describe('DuplicateInfoCard', () => {
  it('renders all info rows when status=unocc', () => {
    const wrapper = mount(DuplicateInfoCard, { props: { info, status: 'unocc' } })
    expect(wrapper.text()).toContain('RES-2024-08521')
    expect(wrapper.text()).toContain('2024-08-15')
    expect(wrapper.text()).toContain('高级前端工程师')
    expect(wrapper.text()).toContain('未占用')
  })

  it('renders status with red color when occupied', () => {
    const wrapper = mount(DuplicateInfoCard, {
      props: { info: { ...info, cur_status: '已占用 · 面试中' }, status: 'occupied' },
    })
    // The status row is the 4th .dup-row (last one) — its .dup-value has inline color style
    const rows = wrapper.findAll('.dup-row')
    const statusValueEl = rows[rows.length - 1]!.find('.dup-value')
    expect(statusValueEl.attributes('style')).toContain('color:')
  })
})
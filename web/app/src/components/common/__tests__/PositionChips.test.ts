import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PositionChips from '../PositionChips.vue'

// 2026-09-27: 契约改为 {id,label}; 选中值(modelValue)为 id
const items = [
  { id: 'p1', label: '高级前端工程师' },
  { id: 'p2', label: '资深前端工程师' },
  { id: 'p3', label: '前端架构师' },
  { id: 'p4', label: '产品经理' },
]

describe('PositionChips', () => {
  it('renders all positions as chips', () => {
    const wrapper = mount(PositionChips, { props: { items, modelValue: [] } })
    expect(wrapper.findAll('.pos-item')).toHaveLength(items.length)
  })

  it('emits update:modelValue with single id selection', async () => {
    const wrapper = mount(PositionChips, { props: { items, modelValue: [] } })
    await wrapper.findAll('.pos-item')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['p1']])
  })

  it('highlights selected positions by id', () => {
    const wrapper = mount(PositionChips, { props: { items, modelValue: ['p3'] } })
    const els = wrapper.findAll('.pos-item')
    expect(els[2].classes()).toContain('sel')
  })
})

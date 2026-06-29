import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PositionChips from '../PositionChips.vue'

const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', '产品经理']

describe('PositionChips', () => {
  it('renders all positions as chips', () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: [] } })
    expect(wrapper.findAll('.pos-item')).toHaveLength(positions.length)
  })

  it('emits update:modelValue with single selection', async () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: [] } })
    await wrapper.findAll('.pos-item')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['高级前端工程师']])
  })

  it('highlights selected positions', () => {
    const wrapper = mount(PositionChips, { props: { positions, modelValue: ['前端架构师'] } })
    const items = wrapper.findAll('.pos-item')
    expect(items[2].classes()).toContain('sel')
  })
})

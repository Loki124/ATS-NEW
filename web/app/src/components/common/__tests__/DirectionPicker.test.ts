import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DirectionPicker from '../DirectionPicker.vue'

describe('DirectionPicker', () => {
  it('renders 3 options', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: false } })
    expect(wrapper.findAll('.dopt')).toHaveLength(3)
  })

  it('emits update:modelValue when option clicked', async () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: false } })
    await wrapper.findAll('.dopt')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['pending'])
  })

  it('disables talent and position options when hasOccupied=true', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: '', hasOccupied: true } })
    const opts = wrapper.findAll('.dopt')
    expect(opts[1].classes()).toContain('off')  // talent
    expect(opts[2].classes()).toContain('off')  // position
    expect(opts[0].classes()).not.toContain('off')  // pending
  })

  it('highlights currently selected option', () => {
    const wrapper = mount(DirectionPicker, { props: { modelValue: 'position', hasOccupied: false } })
    const opts = wrapper.findAll('.dopt')
    expect(opts[2].classes()).toContain('sel')
  })
})
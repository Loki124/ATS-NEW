import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ApplyPositionSelector from '../ApplyPositionSelector.vue'

const positions = ['高级前端工程师', '资深前端工程师', '前端架构师', '产品经理']

describe('ApplyPositionSelector', () => {
  it('renders all position options', () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '' } })
    const items = wrapper.findAll('.apply-pos-item')
    expect(items).toHaveLength(positions.length)
  })

  it('emits update:modelValue with selected position', async () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '' } })
    await wrapper.findAll('.apply-pos-item')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['高级前端工程师'])
  })

  it('highlights currently selected position', () => {
    const wrapper = mount(ApplyPositionSelector, { props: { positions, modelValue: '前端架构师' } })
    const items = wrapper.findAll('.apply-pos-item')
    expect(items[2].classes()).toContain('sel')
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusTag from '../StatusTag.vue'

describe('StatusTag', () => {
  it.each([
    ['clean', '无重复', 'g'],
    ['unocc', '未占用', 'y'],
    ['occupied', '已占用', 'r'],
    ['processing', '处理中', 'b'],
  ])('renders %s status with label %s and color %s', (status, label, color) => {
    const wrapper = mount(StatusTag, { props: { status } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.find('.tag').classes()).toContain(`tag-${color}`)
  })

  it('renders null status as fallback', () => {
    const wrapper = mount(StatusTag, { props: { status: 'unknown' as any } })
    expect(wrapper.text()).toContain('未知')
  })
})
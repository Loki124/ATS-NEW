import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CheckBanner, { type Status } from '../CheckBanner.vue'

describe('CheckBanner', () => {
  const cases: Array<[Status, string]> = [
    ['clean', '系统中未发现重复简历'],
    ['unocc', '系统中已有同名简历'],
    ['occupied', '该候选人在系统中已被占用'],
    ['processing', '简历正在处理中'],
  ]
  it.each(cases)('renders %s banner with appropriate text', (status, text) => {
    const wrapper = mount(CheckBanner, { props: { status } })
    expect(wrapper.text()).toContain(text)
    expect(wrapper.find('.cb').classes()).toContain(status)
  })
})
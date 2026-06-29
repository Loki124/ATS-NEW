import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusTag, { type Status } from '../StatusTag.vue'

describe('StatusTag', () => {
  const cases: Array<[Status, string, string]> = [
    ['clean', '无重复', 'g'],
    ['unocc', '未占用', 'y'],
    ['occupied', '已占用', 'r'],
    ['processing', '处理中', 'b'],
  ]
  it.each(cases)('renders %s status with label %s and color %s', (status, label, color) => {
    const wrapper = mount(StatusTag, { props: { status } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.find('.tag').classes()).toContain(`tag-${color}`)
  })

  it('renders unknown status as fallback', () => {
    // 2026-06-29 花无缺: 旧测试 'unknown' 不在 Status union, TS2322 fail.
    //   改成 unknown-status fallback 测试, 用 'unknown' 走 fallback 路径.
    //   Vue prop 严格类型用 'unknown' 也可以 (StatusTag 内部 config[status] || fallback)
    const wrapper = mount(StatusTag, { props: { status: 'unknown' as any } })
    expect(wrapper.text()).toContain('未知')
  })
})
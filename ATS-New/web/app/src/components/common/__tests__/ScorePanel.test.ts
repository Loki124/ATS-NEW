import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScorePanel from '../ScorePanel.vue'

const score = {
  score: 78,
  passed: true,
  dimensions: [
    { name: '技术匹配', score: 82 },
    { name: '经验匹配', score: 75 },
    { name: '学历匹配', score: 90 },
    { name: '综合素质', score: 65 },
  ],
}

describe('ScorePanel', () => {
  it('renders overall score', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    expect(wrapper.text()).toContain('78')
  })

  it('renders pass tag when passed=true', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    expect(wrapper.text()).toContain('通过')
  })

  it('renders fail tag when passed=false', () => {
    const wrapper = mount(ScorePanel, { props: { score: { ...score, passed: false } } })
    expect(wrapper.text()).toContain('未通过')
  })

  it('renders 4 dimension bars', () => {
    const wrapper = mount(ScorePanel, { props: { score } })
    const dims = wrapper.findAll('.sc-dim')
    expect(dims).toHaveLength(4)
  })
})

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ResumeCard from '../ResumeCard.vue'
import type { ResumeDraft } from '@/stores/addCandidate'

const baseResume: ResumeDraft = {
  id: 'd1',
  file_name: 'zhangsan.pdf',
  job_id: 'j1',
  status: 'clean',
  progress: 100,
  procPhase: null,
  edited: {},
  parsed: { name: '张三', phone: '138****8888', email: 'z@x.com', gender: '男', age: 28 } as any,
  duplicate: { status: 'clean' } as any,
}

describe('ResumeCard', () => {
  it('renders name, file, gender, age, phone from parsed', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('zhangsan.pdf')
    expect(wrapper.text()).toContain('138****8888')
  })

  it('shows status tag for status=clean', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    expect(wrapper.text()).toContain('无重复')
  })

  it('emits toggle when header clicked', async () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: false, selected: false } })
    await wrapper.find('.c-header').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })

  it('applies expanded class when active=true', () => {
    const wrapper = mount(ResumeCard, { props: { resume: baseResume, active: true, selected: false } })
    expect(wrapper.find('.card-item').classes()).toContain('expanded')
  })

  it('shows progress bar when status=processing', () => {
    const wrapper = mount(ResumeCard, {
      props: { resume: { ...baseResume, status: 'processing', progress: 50, procPhase: 'parsing' }, active: false, selected: false },
    })
    expect(wrapper.find('.pbar').exists()).toBe(true)
  })
})

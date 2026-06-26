import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step1Single from '../Step1Single.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = {
  id: 'd1',
  file_name: 'zhangsan.pdf',
  job_id: 'j1',
  status: 'clean' as const,
  progress: 100,
  procPhase: null,
  edited: {},
  parsed: { name: '张三', phone: '138****8888', email: 'z@x.com', gender: '男', age: 28, edu: '本科', educations: [], experiences: [] } as any,
  duplicate: { status: 'clean' } as any,
}

describe('Step1Single', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders resume name and file in header', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('zhangsan.pdf')
  })

  it('renders basic info section with input fields', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.findAll('input').length).toBeGreaterThanOrEqual(3)
  })

  it('shows check banner in right panel', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume]
    const wrapper = mount(Step1Single)
    expect(wrapper.text()).toContain('系统中未发现重复简历')
  })

  it('shows occupied actions when status=occupied', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ ...baseResume, status: 'occupied', duplicate: { status: 'occupied' } as any }]
    const wrapper = mount(Step1Single)
    expect(wrapper.find('.occ-actions').exists()).toBe(true)
  })
})

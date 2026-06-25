import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step2Assign from '../Step2Assign.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = { id: 'd1', file_name: 'r1.pdf', job_id: 'j1', status: 'clean' as const, progress: 100, procPhase: null, edited: {}, parsed: { name: '张三', age: 28, edu: '本科' } as any }

describe('Step2Assign', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders apply mode toggle when multiple resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(true)
  })

  it('hides apply mode toggle for single resume', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume] as any
    const wrapper = mount(Step2Assign)
    expect(wrapper.find('.apply-mode').exists()).toBe(false)
  })

  it('renders 3 direction options', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.dopt')).toHaveLength(3)
  })

  it('renders submit choices', () => {
    const wrapper = mount(Step2Assign)
    expect(wrapper.findAll('.sc-opt')).toHaveLength(2)
  })

  it('emits back event when back button clicked', async () => {
    const wrapper = mount(Step2Assign)
    const backBtn = wrapper.findAll('button').find(b => b.text().includes('上一步'))!
    await backBtn.trigger('click')
    expect(wrapper.emitted('back')).toBeTruthy()
  })
})
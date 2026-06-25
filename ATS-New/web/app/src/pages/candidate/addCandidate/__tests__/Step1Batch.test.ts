import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Step1Batch from '../Step1Batch.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const baseResume = { id: 'd1', file_name: 'r1.pdf', job_id: 'j1', status: 'clean' as const, progress: 100, procPhase: null, edited: {}, parsed: { name: '张三' } as any }

describe('Step1Batch', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows upload zone when no resumes', () => {
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.upload-zone').exists()).toBe(true)
  })

  it('shows status summary when resumes exist', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.text()).toContain('2 份无重复')
  })

  it('renders one ResumeCard per resume', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume, { ...baseResume, id: 'd2' }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.findAll('.card-item')).toHaveLength(2)
  })

  it('shows bulk action bar when items selected', () => {
    const store = useAddCandidateStore()
    store.resumes = [baseResume] as any
    store.selectedIds = ['d1']
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.bulk-bar').exists()).toBe(true)
  })

  it('shows warning for occupied resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ ...baseResume, status: 'occupied', duplicate: { status: 'occupied' } as any }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.nbar.error').exists()).toBe(true)
  })
})
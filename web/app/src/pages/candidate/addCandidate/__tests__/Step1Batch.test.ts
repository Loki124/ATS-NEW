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

  it('renders the 3 step-explanation bullets with correct labels', () => {
    const wrapper = mount(Step1Batch)
    const text = wrapper.text()
    // i18n 提取曾把这三个 label 整体错位一格（s13/s14/s15），导致第二条变成「：可直接进入下一步：…」且第三条「需处理」丢失
    expect(text).toContain('无重复：可直接进入下一步')
    expect(text).toContain('未占用：系统有记录但可合并')
    expect(text).toContain('需处理：已被占用，需选择处理方式')
  })

  it('shows warning for occupied resumes', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ ...baseResume, status: 'occupied', duplicate: { status: 'occupied' } as any }] as any
    const wrapper = mount(Step1Batch)
    expect(wrapper.find('.nbar.error').exists()).toBe(true)
  })
})
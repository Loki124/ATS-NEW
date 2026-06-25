import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import AsyncResult from '../AsyncResult.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('AsyncResult', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders success message with resume count', () => {
    const store = useAddCandidateStore()
    store.resumes = [{}, {}, {}] as any
    const wrapper = mount(AsyncResult)
    expect(wrapper.text()).toContain('提交成功')
    expect(wrapper.text()).toContain('3')
  })

  it('emits close event when 关闭 button clicked', async () => {
    const store = useAddCandidateStore()
    const wrapper = mount(AsyncResult)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('renders pass and fail routes explanation', () => {
    const store = useAddCandidateStore()
    const wrapper = mount(AsyncResult)
    expect(wrapper.text()).toContain('评分通过的候选人')
    expect(wrapper.text()).toContain('评分未通过的候选人')
  })
})

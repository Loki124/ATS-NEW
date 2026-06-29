import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ScoringOverlay from '../ScoringOverlay.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('ScoringOverlay', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders overall step progress', () => {
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.find('.sub-progress').exists()).toBe(true)
  })

  it('shows scoring list when overallStep >= 2', () => {
    const store = useAddCandidateStore()
    store.resumes = [{ id: 'd1' }] as any
    store._overallStep = 2
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.find('.scoring-list').exists()).toBe(true)
  })

  it('renders close button when allScoringDone=true', () => {
    const store = useAddCandidateStore()
    store.allScoringDone = true
    const wrapper = mount(ScoringOverlay)
    expect(wrapper.text()).toContain('关闭')
  })
})
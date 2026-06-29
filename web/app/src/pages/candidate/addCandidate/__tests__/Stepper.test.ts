import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import Stepper from '../Stepper.vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

describe('Stepper', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders 2 step items', () => {
    const store = useAddCandidateStore()
    const wrapper = mount(Stepper)
    expect(wrapper.findAll('.step-item')).toHaveLength(2)
  })

  it('marks step 1 as on when step=1', () => {
    const store = useAddCandidateStore()
    store.step = 1
    const wrapper = mount(Stepper)
    const dots = wrapper.findAll('.sdot')
    expect(dots[0].classes()).toContain('on')
    expect(dots[1].classes()).not.toContain('on')
  })

  it('marks step 2 as on and step 1 as ok when step=2', () => {
    const store = useAddCandidateStore()
    store.step = 2
    const wrapper = mount(Stepper)
    const dots = wrapper.findAll('.sdot')
    expect(dots[0].classes()).toContain('ok')
    expect(dots[1].classes()).toContain('on')
  })
})

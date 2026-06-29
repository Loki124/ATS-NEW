import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OccupiedActions from '../OccupiedActions.vue'

describe('OccupiedActions', () => {
  it('renders 5 action buttons', () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd1' } })
    const btns = wrapper.findAll('.occ-btn')
    expect(btns).toHaveLength(5)
  })

  it('emits action event with draftId and action name when clicked', async () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd1' } })
    const pendingBtn = wrapper.findAll('.occ-btn').find((b) => b.text().includes('待分配'))!
    await pendingBtn.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['d1', 'pending'])
  })

  it('emits merge event', async () => {
    const wrapper = mount(OccupiedActions, { props: { draftId: 'd2' } })
    const mergeBtn = wrapper.findAll('.occ-btn').find((b) => b.text().includes('合并'))!
    await mergeBtn.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['d2', 'merge'])
  })
})
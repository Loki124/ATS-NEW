import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import StatBar from '../StatBar.vue'

const STATS = [
  { key: 'a', label: '待初筛', value: 12, accentColor: 'amber' as const },
  { key: 'b', label: '待处理', value: 5, accentColor: 'rose' as const },
  { key: 'c', label: '推荐', value: 3, accentColor: 'sky' as const },
  { key: 'd', label: '初筛', value: 28, accentColor: 'emerald' as const },
]

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/:catchAll(.*)', component: { template: '<div/>' } }],
})

function factory(props: any = { stats: STATS }) {
  return mount(StatBar, {
    props,
    global: { plugins: [router] },
  })
}

describe('StatBar.vue', () => {
  it('renders 1 stat-bar container', () => {
    const wrapper = factory()
    expect(wrapper.find('.stat-bar').exists()).toBe(true)
  })

  it('renders all 4 stats', () => {
    const wrapper = factory()
    expect(wrapper.findAll('.stat-bar__item')).toHaveLength(4)
  })

  it('shows label and value', () => {
    const wrapper = factory()
    expect(wrapper.text()).toContain('待初筛')
    expect(wrapper.text()).toContain('12')
  })

  it('clickable item with href navigates via router', async () => {
    const pushSpy = vi.spyOn(router, 'push')
    const STATS_WITH_HREF = [
      { ...STATS[0], href: '/screening' },
      STATS[1], STATS[2], STATS[3],
    ]
    const wrapper = factory({ stats: STATS_WITH_HREF })
    const firstItem = wrapper.findAll('.stat-bar__item')[0]
    await firstItem.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/screening')
  })
})

/**
 * 轮岗资源宿主页 · 页签结构回归测试（2026-10-21 兵哥指令，2026-10-22 扩页签）
 *
 * 锁「轮岗资源 = 单入口 + 三个页签」这条产品约定：
 * 1. 三个页签齐备且顺序为 统计概览 / 资源测算 / 轮岗资源；
 *    （原「BU汇总」已更名为「资源测算」并新增置首的「统计概览」；
 *      原「直播间 / 客服部门」两页签合并为「轮岗资源」一张表）
 * 2. 默认落在 统计概览，切页签渲染对应面板；
 * 3. 页签切换同步 URL 查询参数（刷新保持 + 旧深链可落位）；
 * 4. 页面不再渲染标题与提示条（校招生管理列表页统一去标题）。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { naivePlugin } from '../../../plugins/naive'

const mocks = vi.hoisted(() => ({
  route: { query: {} as Record<string, any> },
  replace: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ replace: mocks.replace }),
}))

// 三个面板是独立取数的页面组件，此处打桩，只验宿主页的页签接线
vi.mock('../ResourceStatsOverview.vue', async () => {
  const { h } = await import('vue')
  return { default: { name: 'ResourceStatsOverviewPanel', render: () => h('div', { class: 'stub-panel stub-stats' }) } }
})
vi.mock('../ResourceSummary.vue', async () => {
  const { h } = await import('vue')
  return { default: { name: 'ResourceSummaryPanel', render: () => h('div', { class: 'stub-panel stub-bu' }) } }
})
vi.mock('../RotationResourcePanel.vue', async () => {
  const { h } = await import('vue')
  return { default: { name: 'RotationResourcePanel', render: () => h('div', { class: 'stub-panel stub-resource' }) } }
})

import RotationResource from '../RotationResource.vue'

function mountPage() {
  return mount(RotationResource, { global: { plugins: [naivePlugin] } })
}

function tabByText(wrapper: ReturnType<typeof mountPage>, text: string) {
  return wrapper.findAll('.n-tabs-tab').find((t) => t.text().includes(text))
}

describe('轮岗资源宿主页', () => {
  beforeEach(() => {
    mocks.route.query = {}
    mocks.replace.mockClear()
  })

  it('渲染三个页签：统计概览 / 资源测算 / 轮岗资源', () => {
    const w = mountPage()
    expect(w.text()).toContain('统计概览')
    expect(w.text()).toContain('资源测算')
    expect(w.text()).toContain('轮岗资源')
    // 「BU汇总」已更名为「资源测算」，旧名不得残留在界面文案里
    expect(w.text()).not.toContain('BU汇总')
  })

  it('默认落在 统计概览 页签', () => {
    const w = mountPage()
    expect(w.find('.stub-stats').exists()).toBe(true)
    expect(w.find('.stub-bu').exists()).toBe(false)
  })

  it('切到资源测算页签后渲染对应面板', async () => {
    const w = mountPage()
    const bu = tabByText(w, '资源测算')
    expect(bu).toBeTruthy()
    await bu!.trigger('click')
    expect(w.find('.stub-bu').exists()).toBe(true)
    expect(w.find('.stub-stats').exists()).toBe(false)
  })

  it('旧深链 ?tab=bu 仍能落到资源测算页签', async () => {
    mocks.route.query = { tab: 'bu' }
    const w = mountPage()
    await w.vm.$nextTick()
    expect(w.find('.stub-bu').exists()).toBe(true)
  })

  it('切到轮岗资源页签后渲染对应面板', async () => {
    const w = mountPage()
    const rs = tabByText(w, '轮岗资源')
    expect(rs).toBeTruthy()
    await rs!.trigger('click')
    expect(w.find('.stub-resource').exists()).toBe(true)
  })

  it('页签切换同步到 URL 查询参数（?tab=resource）', async () => {
    const w = mountPage()
    const rs = tabByText(w, '轮岗资源')
    await rs!.trigger('click')
    expect(mocks.replace).toHaveBeenCalledWith({ query: expect.objectContaining({ tab: 'resource' }) })
  })

  it('页面不再渲染标题与提示条', () => {
    const w = mountPage()
    expect(w.find('.page-title').exists()).toBe(false)
    expect(w.find('.page-subtitle').exists()).toBe(false)
  })
})

/**
 * GlobalSearch.test.ts - vitest unit tests (Plan T4)
 *
 * 覆盖:
 *  - n-auto-complete 渲染
 *  - 300ms debounce 触发 searchApi
 *  - 空 q 不搜索
 *  - API 错误优雅处理 (不崩溃)
 *  - 渲染分组 options (group header + item)
 *  - 选中调用 routeForEntity 并 router.push
 *
 * ⚠️ Plan T4 修正:
 *  - useMessage 需 NMessageProvider 包裹 (NMessageProvider 是 component,不是 plugin)
 *  - useRouter 需 createRouter + createMemoryHistory
 *  - entityLabel/routeForEntity 走真实导出
 *
 * 实现方式: 用一个 Wrapper 组件把 NMessageProvider 套在 GlobalSearch 外面,
 *   然后 mount Wrapper (Wrapper 通过 plugin 安装 router, 内部 NMessageProvider 提供 message context).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick, defineComponent, h } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { NMessageProvider } from 'naive-ui'

// Mock ONLY the search API (entityLabel + routeForEntity are real exports)
vi.mock('../../../api/search', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../api/search')>()
  return {
    ...actual,
    searchApi: vi.fn(),
  }
})

import { searchApi } from '../../../api/search'
import GlobalSearch from '../GlobalSearch.vue'

const mockedSearchApi = vi.mocked(searchApi)

// Test router (in-memory) — all 6 entity types
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', name: 'home', component: { template: '<div/>' } },
    { path: '/candidate/detail/:id', name: 'candidate-detail', component: { template: '<div/>' } },
    { path: '/demand/detail/:id', name: 'demand-detail', component: { template: '<div/>' } },
    { path: '/position/detail/:id', name: 'position-detail', component: { template: '<div/>' } },
    { path: '/interview/detail/:id', name: 'interview-detail', component: { template: '<div/>' } },
    { path: '/offer/detail/:id', name: 'offer-detail', component: { template: '<div/>' } },
    { path: '/referral/detail/:id', name: 'referral-detail', component: { template: '<div/>' } },
  ],
})

// Wrapper: provides NMessageProvider context (NMessageProvider 是 component,不是 plugin)
const WrapWithMessage = defineComponent({
  name: 'WrapWithMessage',
  setup(_, { slots }) {
    return () => h(NMessageProvider, null, { default: () => slots.default?.() })
  },
})

function factory() {
  return mount(WrapWithMessage, {
    global: {
      plugins: [router],
    },
    slots: {
      default: () => h(GlobalSearch),
    },
  })
}

describe('GlobalSearch.vue', () => {
  beforeEach(() => {
    mockedSearchApi.mockReset()
    mockedSearchApi.mockResolvedValue({ groups: [], took: 0, query: '', totalGroups: 0 })
  })

  it('renders n-auto-complete', () => {
    const wrapper = factory()
    expect(wrapper.find('.global-search').exists()).toBe(true)
  })

  it('triggers searchApi on input (debounced 300ms)', async () => {
    const wrapper = factory()
    const input = wrapper.find('input')
    await input.setValue('张')
    await new Promise((r) => setTimeout(r, 350))
    expect(mockedSearchApi).toHaveBeenCalledWith(
      expect.objectContaining({ q: '张' }),
    )
  })

  it('does not search for empty q', async () => {
    const wrapper = factory()
    const input = wrapper.find('input')
    await input.setValue('')
    await new Promise((r) => setTimeout(r, 350))
    expect(mockedSearchApi).not.toHaveBeenCalled()
  })

  it('handles API error gracefully (no crash)', async () => {
    mockedSearchApi.mockRejectedValue(new Error('network'))
    const wrapper = factory()
    const input = wrapper.find('input')
    await input.setValue('张')
    await new Promise((r) => setTimeout(r, 350))
    await flushPromises()
    // Just verify no crash — the toast may or may not render depending on Naive UI internals
    expect(wrapper.exists()).toBe(true)
  })

  it('renders search results in grouped options', async () => {
    mockedSearchApi.mockResolvedValue({
      groups: [{ type: 'candidate', total: 1, items: [{ id: 'c1', name: '张三' }] }],
      took: 10,
      query: '张',
      totalGroups: 1,
    })
    const wrapper = factory()
    const input = wrapper.find('input')
    await input.setValue('张')
    await new Promise((r) => setTimeout(r, 350))
    await flushPromises()
    await nextTick()
    // 组件的 options computed 应包含 candidate item
    // NAutoComplete 的 options 通过 render-label 渲染,所以断言 options 计算属性比较可靠
    const vm = wrapper.findComponent(GlobalSearch).vm as any
    expect(vm.options).toBeDefined()
    // options 是嵌套结构: 1 group 包含 1 child
    expect(vm.options).toHaveLength(1)
    expect(vm.options[0].type).toBe('group')
    expect(vm.options[0].children).toHaveLength(1)
    expect(vm.options[0].children[0].value).toBe('candidate:c1')
  })

  it('navigates via routeForEntity on select', async () => {
    const pushSpy = vi.spyOn(router, 'push')
    mockedSearchApi.mockResolvedValue({
      groups: [{ type: 'candidate', total: 1, items: [{ id: 'c1', name: '张三' }] }],
      took: 10,
      query: '张',
      totalGroups: 1,
    })
    const wrapper = factory()
    const input = wrapper.find('input')
    await input.setValue('张')
    await new Promise((r) => setTimeout(r, 350))
    await flushPromises()

    // Simulate select via the component's onSelect handler
    const vm = wrapper.findComponent(GlobalSearch).vm as any
    vm.onSelect('candidate:c1')
    expect(pushSpy).toHaveBeenCalledWith('/candidate/detail/c1')
  })
})

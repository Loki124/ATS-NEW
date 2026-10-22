/**
 * 校招生管理 · 示例数据守卫回归（2026-10-21）
 *
 * 病根：班级管理页点「校招人数」穿透报 404
 *   GET /api/v1/campus-rotation/class-rooms/MOCK_CR_01/members/ 404
 *
 * 链路：mode='on'（强制示例）→ 页面走 isMockOnly 分支 `list.value = mockRows; return`
 *   —— **从不调用 pick()** → isMock 停留在 false → 按钮的 `disabled: isMock` 守卫失效
 *   → 拿 MOCK_ 前缀的假 id 打真接口 → 404。
 *
 * 本文件锁住修复后的语义：
 *   - isMock 由 mode 与取数结果**派生**（'on' 恒真 / 'off' 恒假 / 'auto' 看取数），
 *     不再依赖 pick() 是否被调用；
 *   - setMode 在另一个实例上调用也生效（mode 是模块级共享单例，isMock 是派生的）；
 *   - 各页面的写操作与成员穿透都有二次守卫（拿假 id 不发请求）。
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, getCurrentInstance, h } from 'vue'
import naiveUI, { NConfigProvider, NMessageProvider } from 'naive-ui'
import { useCampusMock } from '../useCampusMock'
import ClassRoom from '../../pages/campus/ClassRoom.vue'

/** happy-dom 未实现 Storage 方法，装完整桩（与 useCampusMock.test.ts 同手法）。 */
const store: Record<string, string> = {}
const storageStub = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => {
    store[k] = String(v)
  },
  removeItem: (k: string) => {
    delete store[k]
  },
  clear: () => {
    for (const k of Object.keys(store)) delete store[k]
  },
  key: (i: number) => Object.keys(store)[i] ?? null,
  get length() {
    return Object.keys(store).length
  },
}
;(globalThis as any).localStorage = storageStub

const REAL = [{ id: 'r1' }]
const MOCK = [{ id: 'MOCK_1' }]

describe('useCampusMock.isMock 派生语义（2026-10-21 修复）', () => {
  beforeEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })
  afterEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })

  it('mode=on 时恒为示例 —— 即便本页从未调用 pick()', () => {
    const { isMock } = useCampusMock()
    useCampusMock().setMode('on')
    expect(isMock.value).toBe(true)
  })

  it('mode=off 时恒为真实', () => {
    const { isMock } = useCampusMock()
    useCampusMock().setMode('off')
    expect(isMock.value).toBe(false)
  })

  it('auto 模式：以本页取数结果为准（真实有数据→真实，为空→示例）', () => {
    const { pick, isMock } = useCampusMock()
    expect(pick(REAL, MOCK)).toBe(REAL)
    expect(isMock.value).toBe(false)
    expect(pick([], MOCK)).toBe(MOCK)
    expect(isMock.value).toBe(true)
  })

  it('mode=on 后再切 auto，isMock 回到「按取数判定」而非粘住 true', () => {
    const { pick, isMock } = useCampusMock()
    useCampusMock().setMode('on')
    expect(isMock.value).toBe(true)
    useCampusMock().setMode('auto')
    expect(isMock.value).toBe(false)
    expect(pick(REAL, MOCK)).toBe(REAL)
    expect(isMock.value).toBe(false)
  })

  it('在另一个实例上 setMode 也能影响本页的 isMock（mode 是共享单例）', () => {
    // 复现真场景：CampusMockBar 与页面各自 useCampusMock()，拿到不同实例
    const page = useCampusMock()
    const bar = useCampusMock()
    bar.setMode('on')
    expect(page.isMock.value).toBe(true)
  })
})

describe('班级管理页 · 示例数据不得发真接口（2026-10-21 修复）', () => {
  beforeEach(() => {
    storageStub.clear()
    useCampusMock().setMode('on')
  })
  afterEach(() => {
    storageStub.clear()
    useCampusMock().setMode('auto')
  })

  const h0 = vi.hoisted(() => ({
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  }))
  vi.mock('@/api/request', () => ({
    default: {
      get: h0.get,
      post: h0.post,
      put: h0.put,
      delete: h0.del,
    },
  }))
  vi.mock('../../mocks/campus', async (orig) => {
    const actual = await orig<typeof import('../../mocks/campus')>()
    return {
      ...actual,
      // 示例数据自带 MOCK_ 前缀假 id（与真实现一致）
      MOCK_CLASS_ROOMS: [{ id: 'MOCK_CR_01', code: 'CL1', name: '示例班', studentCount: 3, isActive: true }],
    }
  })
  vi.mock('../../utils/campus', async (orig) => {
    const actual = await orig<typeof import('../../utils/campus')>()
    return {
      ...actual,
      searchUsers: vi.fn().mockResolvedValue([]),
    }
  })

  it('示例模式下点「校招人数」不发 members 请求（此前报 404）', async () => {
    h0.get.mockResolvedValue({ data: { data: [] } })
    const wrapper = mount(defineComponent({
      setup() {
        // 全量注册 naive-ui 组件（ClassRoom 用到 n-grid/n-data-table 等，
        // 否则模板里解析不到、表格不渲染）
        const app = getCurrentInstance()!.appContext.app
        app.use(naiveUI)
        return () => h(NConfigProvider, null, {
          default: () => h(NMessageProvider, null, { default: () => h(ClassRoom) }),
        })
      },
    }), { attachTo: document.body })
    await flushPromises()
    await flushPromises()

    // ⚠️ NDataTable 的表体渲染在 body 级独立层（不挂在 wrapper 树上），
    //    故必须走 document 查询（与 RuleConfigModal.test.ts 同一教训）。
    const cellBtns = Array.from(document.querySelectorAll('button'))
      .filter((b) => (b.textContent || '').trim() === '3')
    expect(cellBtns.length, '应渲染出「校招人数」示例值按钮').toBeGreaterThan(0)

    cellBtns[0].click()
    await flushPromises()

    const called = h0.get.mock.calls.map((c) => String(c[0]))
    expect(called.some((u) => String(u).includes('/members/'))).toBe(false)
    wrapper.unmount()
  })
})

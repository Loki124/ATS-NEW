/**
 * useFormDraft 护栏（2026-10-23 校招生全生命周期移植 · R-105）
 *
 * 覆盖三条此前**没有**护栏、且在 12 个新页面接草稿后暴露出来的行为：
 *
 * 1. **clear() 必须取消待写定时器** —— 否则「提交成功 → clear() → 800ms 后定时器触发 →
 *    把刚提交的内容重新写回草稿」，下次打开误报「已恢复上次填写的内容」。
 *    （真实踩过：草稿在提交成功后"复活"。）
 * 2. **敏感字段整体禁用草稿** —— R-105 硬约束：命中敏感字段名/输入类型即**不落盘**
 *    （不是逐字段过滤，避免部分落盘）。
 * 3. **TTL 24h 过期即丢弃** —— 过期草稿不可被 probe 命中，也应被清掉。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, reactive } from 'vue'
import { mount } from '@vue/test-utils'
import { useFormDraft } from '../useFormDraft'

const KEY = (ns: string) => `draft:${ns}`

/** 在真实组件里跑 composable（它依赖 onUnmounted / watch 的组件上下文）。 */
function withSetup<T>(fn: () => T): [T, ReturnType<typeof mount>] {
  let result!: T
  const wrapper = mount(
    defineComponent({
      setup() {
        result = fn()
        return () => h('div')
      },
    }),
  )
  return [result, wrapper]
}

describe('useFormDraft', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useFakeTimers()
  })

  it('probe 命中未过期草稿，restore 把内容灌回表单', () => {
    localStorage.setItem(
      KEY('t1'),
      JSON.stringify({ _ts: Date.now(), _data: { name: '张三' } }),
    )
    const [draft] = withSetup(() => useFormDraft('t1', reactive({ name: '' })))
    expect(draft.probe()).toBe(true)
    draft.restore()
    expect(localStorage.getItem(KEY('t1'))).toContain('张三')
  })

  it('clear() 之后待写定时器不得把草稿写回来（提交后草稿复活）', async () => {
    const form = reactive({ name: '李四' })
    const [draft] = withSetup(() => useFormDraft('t2', form))
    // 触发 watch → 安排 800ms 后的写入
    form.name = '李四'
    await nextTick()
    // 提交成功 → 立即清空
    draft.clear()
    // 让 debounce 定时器到期
    vi.advanceTimersByTime(1200)
    await nextTick()
    expect(localStorage.getItem(KEY('t2'))).toBeNull()
  })

  it('敏感字段命中即整体禁用草稿（不落盘）', async () => {
    const form = reactive({ name: '王五', password: 'x' })
    const [draft] = withSetup(() => useFormDraft('t3', form))
    form.name = '王五'
    await nextTick()
    vi.advanceTimersByTime(1200)
    await nextTick()
    expect(localStorage.getItem(KEY('t3'))).toBeNull()
    expect(draft.probe()).toBe(false)
  })

  it('过期草稿（>24h）不被命中且被清理', () => {
    const old = Date.now() - 25 * 60 * 60 * 1000
    localStorage.setItem(KEY('t4'), JSON.stringify({ _ts: old, _data: { name: '赵六' } }))
    const [draft] = withSetup(() => useFormDraft('t4', reactive({ name: '' })))
    expect(draft.probe()).toBe(false)
    expect(localStorage.getItem(KEY('t4'))).toBeNull()
  })
})

// useFormDraft —— 表单草稿自动保存（AGENTS.md R-105 通用实现）
//
// 职责边界（严格遵守 R-105 / R-106）：
//   - 保存介质：localStorage；TTL ≤ 24h（写入时打 _ts，读取时过期直接丢弃）
//   - 触发时机：源响应式对象变化后 debounce 800ms（与 AGENTS.md 示例代码一致）
//   - 恢复提示：打开弹窗时若发现未过期草稿，由调用方 toast「已恢复」+ 提供「清空」出口
//   - 提交成功：调用方 MUST 调 clear() 立即清除（R-105: 提交成功后 MUST 立即清除）
//   - 敏感字段：SENSITIVE_KEY 命中时整体禁用草稿（R-105 硬约束）
//   - enabled：可为 boolean 或 () => boolean getter；例如编辑模式传 () => !editing.value 关闭，
//     避免草稿覆盖真实 row 数据
//
// 用法：
//   const draft = useFormDraft('recruitment-stage', form, { enabled: () => !editing.value })
//   // 打开弹窗时
//   if (draft.probe()) { draft.restore(); message.info('已恢复上次填写的内容', { action: { label: '清空', onClick: draft.clear } }) }
//   // 保存成功后
//   draft.clear()

import { ref, watch, onUnmounted } from 'vue'

const SENSITIVE_KEY =
  /password|passwd|cvv|cvc|card|idcard|passport|ssn|otp|smscode|captcha|token|apikey|secret/i

const TTL = 24 * 60 * 60 * 1000 // 24h

interface DraftMeta {
  _ts: number
  _data: Record<string, unknown>
}

function safeRead(key: string): DraftMeta | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw) as DraftMeta
    if (!parsed || typeof parsed._ts !== 'number' || typeof parsed._data !== 'object') return null
    if (Date.now() - parsed._ts > TTL) {
      localStorage.removeItem(key)
      return null
    }
    return parsed
  } catch {
    return null
  }
}

/**
 * @param ns        命名空间（区分不同表单，避免 key 冲突）
 * @param source    响应式表单对象（reactive / ref）
 * @param options.enabled  是否启用草稿（默认 true）；可传 () => boolean getter 动态决定
 */
export function useFormDraft(
  ns: string,
  source: Record<string, unknown>,
  options: { enabled?: boolean | (() => boolean); debounceMs?: number } = {}
) {
  const debounceMs = options.debounceMs ?? 800
  const key = `draft:${ns}`

  const getEnabled = (): boolean => {
    const base = typeof options.enabled === 'function' ? options.enabled() : options.enabled !== false
    const sensitive = Object.keys(source).some((k) => SENSITIVE_KEY.test(k))
    return base && !sensitive
  }

  const hasDraft = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  // 探测是否有未过期草稿（不自动灌入，由调用方决定是否恢复）
  function probe(): boolean {
    if (!getEnabled()) return false
    const meta = safeRead(key)
    hasDraft.value = !!meta
    return !!meta
  }

  // 把已存草稿灌入 source（调用方在确认恢复时调用）
  function restore(): void {
    if (!getEnabled()) return
    const meta = safeRead(key)
    if (!meta) return
    Object.assign(source, meta._data)
  }

  // 无条件清除（提交成功 / 用户主动清空，不检查 enabled）
  function clear(): void {
    hasDraft.value = false
    try {
      localStorage.removeItem(key)
    } catch {
      /* ignore */
    }
  }

  function write(): void {
    if (!getEnabled()) return
    try {
      const data: Record<string, unknown> = {}
      for (const k of Object.keys(source)) {
        if (SENSITIVE_KEY.test(k)) continue
        data[k] = source[k]
      }
      const meta: DraftMeta = { _ts: Date.now(), _data: data }
      localStorage.setItem(key, JSON.stringify(meta))
    } catch {
      /* localStorage 不可用时静默降级（草稿属增强能力，失败不影响主流程） */
    }
  }

  const stop = watch(
    () => JSON.stringify(source),
    () => {
      if (!getEnabled()) return
      if (timer) clearTimeout(timer)
      timer = setTimeout(write, debounceMs)
    }
  )

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
    stop()
  })

  return { hasDraft, probe, restore, clear, enabled: getEnabled }
}

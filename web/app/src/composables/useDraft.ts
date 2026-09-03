import { ref, watch, onBeforeUnmount, type Reactive } from 'vue'

/**
 * useDraft —— R-105 草稿自动保存（预计填写 > 1 分钟的表单）
 *
 * 设计要点（对齐 AGENTS.md R-105）：
 * 1. 介质为 localStorage，TTL 默认 24h；过期自动清除。
 * 2. 敏感字段（密码/令牌/证件号等）一旦命中，整体禁用草稿——不逐字段过滤，避免部分落盘。
 * 3. 提交成功后由调用方调用 clear() 立即清除草稿。
 * 4. 恢复时返回 boolean；调用方负责提示「已恢复上次填写的内容」并提供「清空」出口。
 *    严禁弹二次确认框（R-106：草稿已存在时弹窗即违规）。
 *
 * 用法：
 *   const form = reactive({ title: '', body: '' })
 *   const { restored, restore, clear } = useDraft(form, { key: 'announcement-edit' })
 *   // 打开表单时：
 *   if (restore()) message.info('已恢复上次填写的内容', { action: { label: '清空', onClick: clear } })
 *   // 提交成功后：clear()
 */
export const SENSITIVE_KEY =
  /password|passwd|pwd|cvv|cvc|card|cardnumber|idcard|id_card|passport|ssn|otp|smscode|sms_code|captcha|token|apikey|api_key|secret|securityanswer|currentpassword|newpassword|confirmpassword/i

export interface UseDraftOptions {
  /** 草稿唯一键，建议带业务语义，如 'announcement-edit' */
  key: string
  /** 存活时长(ms)，默认 24h */
  ttl?: number
  /** 防抖保存间隔(ms)，默认 800 */
  debounce?: number
  /**
   * 判定表单是否为「空/未填写」。命中时整体禁用草稿保存，
   * 避免打开空白表单时把默认值写成草稿、下次打开误报「已恢复」。
   * 例：isEmpty: (v) => !v.title && !v.body
   */
  isEmpty?: (v: T) => boolean
}

export function useDraft<T extends Record<string, unknown>>(
  form: T | Reactive<T>,
  options: UseDraftOptions,
) {
  const { key, ttl = 24 * 60 * 60 * 1000, debounce = 800 } = options
  const storageKey = `draft:${key}`
  const restored = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  function hasSensitive(v: Record<string, unknown>): boolean {
    return Object.keys(v ?? {}).some((k) => SENSITIVE_KEY.test(k))
  }

  function save() {
    const v = form as Record<string, unknown>
    if (hasSensitive(v)) return // 含敏感字段 → 整体禁用草稿
    if (options.isEmpty?.(v as T)) return // 空表单 → 不落盘，避免误恢复
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({ v: { ...v }, exp: Date.now() + ttl }),
      )
    } catch {
      /* 配额/隐私模式异常静默忽略，不阻断用户输入 */
    }
  }

  function clear() {
    try {
      localStorage.removeItem(storageKey)
    } catch {
      /* ignore */
    }
    restored.value = false
  }

  function restore(): boolean {
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return false
      const parsed = JSON.parse(raw) as { v?: Record<string, unknown>; exp?: number }
      if (!parsed?.v || Date.now() > (parsed.exp ?? 0)) {
        localStorage.removeItem(storageKey)
        return false
      }
      Object.assign(form as Record<string, unknown>, parsed.v)
      restored.value = true
      return true
    } catch {
      return false
    }
  }

  watch(
    () => form,
    () => {
      const v = form as Record<string, unknown>
      if (hasSensitive(v)) return
      if (timer) clearTimeout(timer)
      timer = setTimeout(save, debounce)
    },
    { deep: true },
  )

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return { restored, restore, save, clear, hasSensitive }
}

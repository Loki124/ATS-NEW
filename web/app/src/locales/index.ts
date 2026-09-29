/**
 * vue-i18n 正式接入 (2026-09-24)
 *
 * 旧 stub（zh-CN.ts / en-US.ts）只导出扁平 dot-key 字典（如 'reasonLibrary.title'）
 * 与占位 t()。这里把它们转成 vue-i18n 需要的嵌套 messages，建立真正的 i18n 实例。
 *
 * - 默认语言 zh-CN（契合 R-222「用户可见文案优先中文」）
 * - en-US 作为兜底/可切换语言（reasonLibrary 命名空间已双语，其余缺失键回退 zh-CN）
 * - legacy:false → Composition API：`useI18n()` 取 t，模板可用 `$t`
 */
import { createI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import { REASON_LIBRARY_ZH, DATA_PERM_ZH, APP_UI_ZH } from './zh-CN'
import { REASON_LIBRARY_EN, DATA_PERM_EN, APP_UI_EN } from './en-US'
import { LANGUAGE_ZH, LANGUAGE_EN } from './language'
import { METRICS_ZH, METRICS_EN } from './metrics'
import { RESUME_PARSER_ZH, RESUME_PARSER_EN } from './resumeParser'

/** 扁平 dot-key 字典 -> vue-i18n 嵌套对象 */
function toNested(flat: Record<string, string>): Record<string, any> {
  const root: Record<string, any> = {}
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split('.')
    let node = root
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof node[parts[i]] !== 'object' || node[parts[i]] === null) {
        node[parts[i]] = {}
      }
      node = node[parts[i]]
    }
    node[parts[parts.length - 1]] = value
  }
  return root
}

const messages = {
  'zh-CN': toNested({ ...REASON_LIBRARY_ZH, ...DATA_PERM_ZH, ...APP_UI_ZH, ...LANGUAGE_ZH, ...METRICS_ZH, ...RESUME_PARSER_ZH }),
  'en-US': toNested({ ...REASON_LIBRARY_EN, ...DATA_PERM_EN, ...APP_UI_EN, ...LANGUAGE_EN, ...METRICS_EN, ...RESUME_PARSER_EN }),
}

export type AppLocale = 'zh-CN' | 'en-US'

/** 系统支持的语言清单（选项原生名按惯例用母语书写，便于跨语言识别） */
export const SUPPORTED_LOCALES: { code: AppLocale; native: string }[] = [
  { code: 'zh-CN', native: '简体中文' },
  { code: 'en-US', native: 'English' },
]

const LOCALE_STORAGE_KEY = 'ats-locale'

/** 启动时从 localStorage 恢复用户语言偏好；非法/缺失时回落中文 */
function readInitialLocale(): AppLocale {
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (saved === 'zh-CN' || saved === 'en-US') return saved
  } catch {
    /* localStorage 不可用时静默回落 */
  }
  return 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  locale: readInitialLocale(),
  fallbackLocale: 'zh-CN',
  messages,
})

/**
 * 全局当前语言（可写 computed，单一真相源）。
 * 组件订阅此值即可响应式跟随切换；直接赋值即切换并持久化。
 */
export const currentLocale = computed<AppLocale>({
  get: () => i18n.global.locale.value as AppLocale,
  set: (code) => {
    i18n.global.locale.value = code
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, code)
    } catch {
      /* 持久化失败时不影响本次会话内切换 */
    }
  },
})

export default i18n

/**
 * 同步 <html lang> 属性（P0-2）：保证无障碍 / 屏幕阅读器 / SEO 正确。
 * 启动即按已恢复的语言设置一次，之后随 currentLocale 变化持续同步。
 */
function syncHtmlLang(code: AppLocale) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
}
syncHtmlLang(readInitialLocale())
watch(currentLocale, syncHtmlLang)

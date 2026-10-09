/**
 * vue-i18n 正式接入 (2026-09-24)
 *
 * 旧 stub（zh-CN.ts / en-US.ts）只导出扁平 dot-key 字典（如 'reasonLibrary.title'）
 * 与占位 t()。这里把它们转成 vue-i18n 需要的嵌套 messages，建立真正的 i18n 实例。
 *
 * - 默认语言 zh-CN（契合 R-222「用户可见文案优先中文」）
 * - en-US 作为兜底/可切换语言（reasonLibrary 命名空间已双语，其余缺失键回退 zh-CN）
 * - legacy:false → Composition API：`useI18n()` 取 t，模板可用 `$t`
 *
 * ## 2026-10-09 (#39) 按域异步加载
 * 大字典（REASON_LIBRARY_* / DATA_PERM_* / APP_UI_*）已拆分到 `./domains/<locale>.<CONST>.ts`：
 * - 启动只加载「当前语言」对应分片（默认 zh-CN），把原 ~260KB/语言的字典移出主包（异步 chunk）。
 * - 切换到另一语言时再懒加载该语言分片（见底部 watch），绝大多数用户（默认中文）不会下载 en-US。
 * - language.ts 极小，保持静态导入。
 */
import { createI18n } from 'vue-i18n'
import { computed, watch } from 'vue'
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
  messages: {}, // 初始为空，运行时异步加载（#39）：见 loadLocale / ensureLocaleLoaded
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

const _loaded = new Set<AppLocale>()

/**
 * 异步加载某语言的字典分片并注册到 i18n（幂等）。
 * 分片 = 3 个大数据域（reasonLibrary / dataPerm / appUi）+ 2 个小域（metrics / resumeParser，已静态可用）。
 */
export async function loadLocale(code: AppLocale): Promise<void> {
  if (_loaded.has(code)) return
  const [reason, dataPerm, appUi]: any[] = await Promise.all([
    code === 'zh-CN'
      ? import('./domains/zh-CN.REASON_LIBRARY_ZH')
      : import('./domains/en-US.REASON_LIBRARY_EN'),
    code === 'zh-CN'
      ? import('./domains/zh-CN.DATA_PERM_ZH')
      : import('./domains/en-US.DATA_PERM_EN'),
    code === 'zh-CN'
      ? import('./domains/zh-CN.APP_UI_ZH')
      : import('./domains/en-US.APP_UI_EN'),
  ])
  const flat: Record<string, string> = {
    ...(code === 'zh-CN' ? LANGUAGE_ZH : LANGUAGE_EN),
    ...(code === 'zh-CN' ? METRICS_ZH : METRICS_EN),
    ...(code === 'zh-CN' ? RESUME_PARSER_ZH : RESUME_PARSER_EN),
    ...(code === 'zh-CN' ? reason.REASON_LIBRARY_ZH : reason.REASON_LIBRARY_EN),
    ...(code === 'zh-CN' ? dataPerm.DATA_PERM_ZH : dataPerm.DATA_PERM_EN),
    ...(code === 'zh-CN' ? appUi.APP_UI_ZH : appUi.APP_UI_EN),
  }
  i18n.global.setLocaleMessage(code, toNested(flat))
  _loaded.add(code)
}

/** 启动期加载当前语言字典（main.ts 在 mount 前 await，避免首屏闪烁） */
export async function ensureLocaleLoaded(): Promise<void> {
  await loadLocale(currentLocale.value)
}

export default i18n

/**
 * 同步 <html lang> 属性（P0-2）：保证无障碍 / 屏幕阅读器 / SEO 正确。
 * 切换语言时一并懒加载对应分片（首次切换到 en-US 才真正下载该语言字典）。
 */
function syncHtmlLang(code: AppLocale) {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', code)
  }
}
syncHtmlLang(readInitialLocale())
watch(currentLocale, (code) => {
  void loadLocale(code) // 懒加载分片（已加载则幂等跳过）
  syncHtmlLang(code)
})

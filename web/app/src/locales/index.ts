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
import { REASON_LIBRARY_ZH, DATA_PERM_ZH } from './zh-CN'
import { REASON_LIBRARY_EN } from './en-US'

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
  'zh-CN': toNested({ ...REASON_LIBRARY_ZH, ...DATA_PERM_ZH }),
  'en-US': toNested({ ...REASON_LIBRARY_EN }),
}

export const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages,
})

export default i18n

// 全局 vitest setup
//
// 全局 mock 两处「测试环境缺失运行时实例」的报错:
//   1) vue-i18n: 测试环境没有真实 i18n 实例, 任意组件调用 useI18n() 都会抛
//      "Need to install with app.use function"。这里用真实 zh-CN 文案构建一个
//      与 vue-i18n 同形的 t(), 让 t('components.common.UploadZone.s1') 返回真实中文,
//      既修复组件挂载, 又保留既有测试对「中文可见文案」的断言语义(而非退化为断言 key)。
//      证据: 全仓组件均 const { t } = useI18n() (仅解构 t); 无测试文件 import createI18n。
//   2) naive-ui: useDialog/useMessage/useNotification 需要外层 <n-*provider> 注入,
//      测试中缺失会抛 "No outer <n-dialog-provider /> founded"。这里用 stub 覆盖这三个
//      composable, 同时保留 naive-ui 全部真实组件(通过 importOriginal 展开)。
import { vi } from 'vitest'
import { REASON_LIBRARY_ZH, DATA_PERM_ZH, APP_UI_ZH } from '@/locales/zh-CN'
import { LANGUAGE_ZH } from '@/locales/language'
import { METRICS_ZH } from '@/locales/metrics'
import { RESUME_PARSER_ZH } from '@/locales/resumeParser'

type Dict = Record<string, any>

/** 扁平 dot-key 字典 -> 嵌套对象 (同 src/locales/index.ts 的 toNested) */
function toNested(flat: Record<string, string>): Dict {
  const root: Dict = {}
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split('.')
    let node = root
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof node[parts[i]] !== 'object' || node[parts[i]] === null) node[parts[i]] = {}
      node = node[parts[i]]
    }
    node[parts[parts.length - 1]] = value
  }
  return root
}

const zhMessages: Dict = toNested({
  ...REASON_LIBRARY_ZH,
  ...DATA_PERM_ZH,
  ...APP_UI_ZH,
  ...LANGUAGE_ZH,
  ...METRICS_ZH,
  ...RESUME_PARSER_ZH,
})

function resolve(obj: Dict, key: string): string | undefined {
  let node: Dict | string | undefined = obj
  for (const k of key.split('.')) {
    if (node && typeof node === 'object') node = (node as Dict)[k]
    else return undefined
  }
  return typeof node === 'string' ? node : undefined
}

function interpolate(str: string, named?: Record<string, unknown>): string {
  if (!named) return str
  return str.replace(/\{(\w+)\}/g, (_, n: string) =>
    named[n] !== undefined ? String(named[n]) : `{${n}}`,
  )
}

/** 与 vue-i18n 同形的 t(): 命中返真实中文, 缺失(理论不该发生)回退 key, 不抛错 */
function makeT() {
  return (key: string, named?: Record<string, unknown>): string => {
    const val = resolve(zhMessages, key)
    if (typeof val === 'string') return interpolate(val, named)
    return key
  }
}

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: makeT(), locale: 'zh-CN', rt: (k: string) => k, tm: () => ({}), te: () => true }),
}))

vi.mock('naive-ui', async (importOriginal) => {
  const actual = await importOriginal<typeof import('naive-ui')>()
  const notifyStub = () => ({ info: vi.fn(), success: vi.fn(), warning: vi.fn(), error: vi.fn(), loading: vi.fn() })
  return {
    ...actual,
    useDialog: () => ({ ...notifyStub(), create: vi.fn() }),
    useMessage: notifyStub,
    useNotification: () => ({ create: vi.fn() }),
  }
})

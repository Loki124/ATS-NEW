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

/**
 * localStorage 兜底（2026-10-21）。
 *
 * 背景：Node ≥ 22 内置了一个**空的** `globalThis.localStorage`（原型只有 Object.prototype，
 *   没有 getItem/setItem/removeItem/clear/key），而 vitest 的 happy-dom 环境
 *   **不会覆盖已经存在的全局** → 于是测试里 `localStorage.getItem()` 直接抛
 *   "localStorage.getItem is not a function"。
 *
 * 实测：本地 Node v25 下 9 个用例假红（`src/utils/__tests__/request.test.ts` 8 个 +
 *   `src/api/__tests__/addCandidate.test.ts` 1 个）；CI 用 Node 20，没有这个内置全局
 *   → happy-dom 的实现正常注入 → CI 是绿的。于是出现「本地红、CI 绿」，
 *   且失败原因与被测代码毫无关系。
 *
 * 仓库里其实早有同源的记录：`src/router/__tests__/router.test.ts` 顶部注释写着
 * 「happy-dom 测试环境可能不提供 localStorage … 直接调 localStorage.getItem 会抛
 * "not a function"」—— 当时只在那一个文件里做了 stub 兜底，其余文件没兜。
 *
 * 修法：**只在 localStorage 不可用时**注入一个内存实现（DOM Storage 接口齐全），
 *   可用时保持原样 —— 不改变 happy-dom / Node 自带实现的行为。
 */
function ensureLocalStorage() {
  const g = globalThis as any
  const ls = g.localStorage
  const REQUIRED = ['getItem', 'setItem', 'removeItem', 'clear', 'key']
  const usable = !!ls && REQUIRED.every((fn) => typeof ls[fn] === 'function')
  if (usable) return

  const store = new Map<string, string>()
  g.localStorage = {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => {
      store.set(k, String(v))
    },
    removeItem: (k: string) => {
      store.delete(k)
    },
    clear: () => {
      store.clear()
    },
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size
    },
  }
}

ensureLocalStorage()

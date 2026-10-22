/**
 * 数据列表页标准结构护栏（2026-10-21「权限管理模块数据列表标准化」）。
 *
 * 依据 `docs/04-ui/SETTINGS_PAGE_STRUCTURE.md` §2.2 与 `AGENTS.md` R-215，
 * 设置中心的数据列表页（表格 + 筛选工具条 + 分页器）必须满足：
 *
 *   ① 滚动容器用 `.data-body`（**不能**用 `.page-body`）
 *      —— `.page-body` 被 SettingsLayout 的 `:deep(.page-body){overflow-y:auto!important}`
 *      强制成整页滚动容器，页面写 `overflow:hidden` 也会被覆盖 → 与表格体内部滚动
 *      叠成**双滚动条**，且标题/工具条随整页滚走。规范称此为「致命陷阱」。
 *   ② 模型 B：`.page-header` 是 `.page-container` 的直接子元素
 *      —— 间距由外壳 `.settings-scroll :deep(.page-container)` 的 gap 独家提供（单一来源）。
 *   ③ 列表外壳用**全局** `.glass-panel.panel-shell`
 *      —— 私有副本（`.permission-shell` / `.resources-shell` 等）会造成内衬/高度链分叉。
 *   ④ `n-data-table` 必须带 `flex-height`，否则表高为 0 或被内容撑开。
 *
 * 本护栏覆盖「权限管理」分组下除**字段权限**外的全部数据列表页
 * （字段权限是表单/详情页，按用户要求本轮不动，走 `.page-body` 轨道）。
 *
 * 读源码而非运行时 DOM：这些页面的表格数据依赖后端接口，运行时断言成本高；
 * 而本回归的根因就是「容器类名写错」，静态判定更直接、更早失败。
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const SETTINGS_DIR = join(__dirname, '..')

/** 权限管理分组下需符合数据列表标准的所有页（字段权限除外） */
const DATA_LIST_PAGES = [
  'UserDirectory.vue',
  'PermissionManagement.vue',
  'PermissionResources.vue',
  'MouManagement.vue',
  'DynamicStrategy.vue',
]

function read(file: string): string {
  return readFileSync(join(SETTINGS_DIR, file), 'utf8')
}

describe('数据列表页标准结构（.data-body + 模型 B + 全局 .panel-shell）', () => {
  it.each(DATA_LIST_PAGES)('%s 不用 .page-body 作滚动容器', (file) => {
    const src = read(file)
    // 模板里不得出现 class="page-body"
    expect(src).not.toMatch(/class="page-body"/)
    // scoped 样式里不得有 .page-body 规则（写了也会被全局 !important 覆盖，等于假实现）
    expect(src).not.toMatch(/^\s*\.page-body\b/m)
  })

  it.each(DATA_LIST_PAGES)('%s 使用 .data-body 作滚动容器', (file) => {
    expect(read(file)).toMatch(/class="data-body"/)
  })

  it.each(DATA_LIST_PAGES)('%s 的 .data-body 自身不滚（overflow: hidden）', (file) => {
    const src = read(file)
    const block = src.match(/\.data-body\s*\{([^}]*)\}/)
    expect(block, `${file} 应有 .data-body 规则`).toBeTruthy()
    expect(block![1]).toMatch(/overflow(-y)?:\s*hidden/)
  })

  it.each(DATA_LIST_PAGES)('%s 的页头是 .page-container 的直接子元素（模型 B）', (file) => {
    const src = read(file)
    const container = src.match(/<div class="page-container[^"]*">([\s\S]*?)<\/div>\s*<\/template>/)
    expect(container, `${file} 应有 .page-container 根节点`).toBeTruthy()
    // .page-container 之后紧跟 .page-header（中间不夹 .data-body）；注释可有可无
    const head = container![1]
    expect(head).toMatch(/^\s*(?:<!--[\s\S]*?-->\s*)?<div class="page-header">/)
  })

  it.each(DATA_LIST_PAGES)('%s 的列表外壳用全局 .glass-panel.panel-shell', (file) => {
    const src = read(file)
    expect(src).toMatch(/class="glass-panel panel-shell"/)
    // 私有外壳副本会造成内衬/高度链分叉
    expect(src).not.toMatch(/class="glass-panel (permission-shell|resources-shell)"/)
  })

  it.each(DATA_LIST_PAGES)('%s 的表格带 flex-height（否则表高塌陷）', (file) => {
    expect(read(file)).toMatch(/flex-height/)
  })
})

describe('字段权限（本次豁免，表单/详情页轨道）', () => {
  it('FieldAclSettings.vue 仍走 .page-body 轨道（用户明确排除）', () => {
    const src = readFileSync(join(SETTINGS_DIR, 'FieldAclSettings.vue'), 'utf8')
    expect(src).toMatch(/class="page-body"/)
  })
})

/**
 * 筛选项行与数据列表之间的间距 —— 单一来源护栏。
 *
 * 间距基准由 `glass.css` 的全局 `.toolbar { margin-bottom: var(--space-2) }`（8px）独家提供，
 * 与其余数据列表页一致（DepartmentManagement / UserDirectory / MouManagement …）。
 *
 * ⚠️ 历史坑：身份管理（RolesTab）与资源管理（ResourcesTab）在 toolbar 与 table-wrap 之间
 * 还有一层带 `gap: var(--space-2)` 的 flex 包装（.roles-tab / .resources-tab），
 * 于是「全局 toolbar 的 margin-bottom 8px + 包装层 gap 8px」= **16px**，
 * 与其他页的 8px 不一致 —— 用户肉眼可见的「筛选项与数据列表间距不一致」。
 * 这两层包装上的 gap 已移除，间距回归单一来源。
 */
describe('筛选行与数据列表的间距（单一来源）', () => {
  /** 介于 .toolbar 与 .table-wrap 之间的中间包装层 */
  const INTERMEDIATE_WRAPPERS: Record<string, string> = {
    'permission/RolesTab.vue': '.roles-tab',
    'permission/ResourcesTab.vue': '.resources-tab',
  }

  const GLASS_CSS = join(SETTINGS_DIR, '../../styles/glass.css')

  it('全局 .toolbar 提供 8px 的 margin-bottom（间距基准）', () => {
    const css = readFileSync(GLASS_CSS, 'utf8')
    const block = css.match(/\.toolbar\s*\{([^}]*)\}/)
    expect(block, 'glass.css 应有全局 .toolbar 规则').toBeTruthy()
    expect(block![1]).toMatch(/margin-bottom:\s*var\(--space-2\)/)
  })

  it.each(Object.entries(INTERMEDIATE_WRAPPERS))(
    '%s 的中间包装层不额外加 gap（否则与全局 margin-bottom 叠成 16px）',
    (file, selector) => {
      const src = read(file)
      const cls = selector.replace('.', '')
      const block = src.match(new RegExp(`\\${selector}\\s*\\{([^}]*)\\}`))
      expect(block, `${file} 应有 ${selector} 规则`).toBeTruthy()
      expect(block![1]).not.toMatch(/gap\s*:/)
    },
  )
})


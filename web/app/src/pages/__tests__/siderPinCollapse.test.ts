/**
 * 左侧竖排导航栏「固定 / 折叠」双态 —— 回归护栏（2026-10-21 兵哥指令）
 *
 * 需求：侧栏要能**固定**（常驻展开并占位）与**折叠**（只展示菜单 icon）两种持久状态。
 *
 * 这套逻辑横跨 4 个文件、5 处必须同步的约束（任一处漂移都会出「侧栏与主区错位 / 宽度对不上」）：
 *   1. `pages/Layout.vue` —— 状态、宽度、类名、header 偏移、切换把手
 *   2. `pages/Layout.vue` 的样式 —— 固定态 grid 两列 + 把手定位
 *   3. `stores/user.ts` —— 偏好持久化（要能跟账号走，不能只存本地）
 *   4. `locales/domains/*` —— 中英文案对称（locale:audit 只查对称性，查不到「文案缺失」）
 *
 * 按仓库既有先例（`pages/__tests__/campusPersonMenu.test.ts`、
 * `styles/__tests__/table-alignment-rules.test.ts`）采用**源码扫描式**断言：
 * 不依赖运行时渲染，CI 上零成本、失败信息直指字面量漂移。
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

const read = (p: string) => fs.readFileSync(path.resolve(__dirname, p), 'utf8')
const LAYOUT = read('../Layout.vue')
const USER_STORE = read('../../stores/user.ts')
const ZH = read('../../locales/domains/zh-CN.APP_UI_ZH.ts')
const EN = read('../../locales/domains/en-US.APP_UI_EN.ts')

describe('侧栏固定 / 折叠双态', () => {
  it('① 侧栏宽度随固定态切换（64px ↔ 240px），不是写死 64', () => {
    expect(LAYOUT).toMatch(/:width="siderWidth"/)
    expect(LAYOUT).toMatch(/SIDER_WIDTH_EXPANDED = 240/)
    expect(LAYOUT).toMatch(/SIDER_WIDTH_COLLAPSED = 64/)
    // 旧的写死宽度不能再出现
    expect(LAYOUT).not.toMatch(/:width="64"/)
  })

  it('② 固定态在文档流内占位 240px（grid 第 1 列随状态变化）', () => {
    expect(LAYOUT).toMatch(/app-layout--pinned:not\(.app-layout--top\)/)
    expect(LAYOUT).toMatch(/grid-template-columns: 240px calc\(100vw - 240px\) !important/)
    // 固定态的 sider 不能再是浮层（position: fixed）
    expect(LAYOUT).toMatch(/\.app-sider\.app-sider--pinned \{[\s\S]*?position: relative !important/)
  })

  it('③ 折叠态由「固定」决定，hover 不再整体展开（让位给原生二级菜单浮出）', () => {
    // 菜单只在固定态展开 → 折叠态下 naive 的 Submenu 才会启用原生 dropdown（VS Code 式浮出）
    expect(LAYOUT).toMatch(/const effectiveExpanded = computed\(\(\) => siderPinned\.value\)/)
    // ⚠️ 原「悬停整个侧栏就整体展开」（peek）必须下线：它会把菜单置为展开态，
    //    正好顶掉原生浮出 → 折叠态永远看不到二级菜单（兵哥反馈）。
    expect(LAYOUT).not.toMatch(/hoverExpanded/)
    expect(LAYOUT).not.toMatch(/\.app-sider\.app-sider--floating \{/)
    expect(LAYOUT).not.toMatch(/'app-sider--floating'/)
    expect(LAYOUT).not.toMatch(/@mouseenter="hoverExpanded = true"/)
    expect(LAYOUT).toMatch(/app-sider--pinned': siderPinned/)
  })

  it('③b 折叠态点分组图标 → 固定侧栏并展开该组（naive 折叠态点击不展开分组）', () => {
    expect(LAYOUT).toMatch(/function openGroup\(key: string\)/)
    expect(LAYOUT).toMatch(/setUiSettings\(\{ siderPinned: true \}\)/)
    expect(LAYOUT).toMatch(/expandedKeys\.value = \[\.\.\.expandedKeys\.value, key\]/)
    // 只有折叠态才接管分组点击；展开态由 naive 自己的 toggleExpand 处理
    expect(LAYOUT).toMatch(/!effectiveExpanded\.value\) \{\s*openGroup\(key\)/)
  })

  it('④ 固定态下 header 偏移跟随（主区不被压住）', () => {
    expect(LAYOUT).toMatch(/const offset = siderPinned\.value \? SIDER_WIDTH_EXPANDED : SIDER_WIDTH_COLLAPSED/)
    expect(LAYOUT).toMatch(/left: `\$\{offset\}px`/)
    expect(LAYOUT).toMatch(/width: `calc\(100vw - \$\{offset\}px\)`/)
  })

  it('⑤ 切换控件在侧栏内部、可点（原生 button + aria-label，且不是被主区盖住的悬浮把手）', () => {
    expect(LAYOUT).toMatch(/class="sider-toggle"/)
    expect(LAYOUT).toMatch(/type="button"/)
    expect(LAYOUT).toMatch(/:aria-label="siderPinned \? t\('pages\.Layout\.sider\.collapse'\) : t\('pages\.Layout\.sider\.pin'\)"/)
    expect(LAYOUT).toMatch(/@click\.stop="toggleSiderPinned"/)
    // ⚠️ 悬浮在右缘的把手会被主区面板盖住 → 点不到（兵哥实测）；
    //    切换控件必须是侧栏内部的一行，不能是 position:absolute 浮在外面的把手。
    expect(LAYOUT).not.toMatch(/class="sider-handle"/)
    expect(LAYOUT).not.toMatch(/\.sider-handle \{/)
  })

  it('⑤b 切换按钮与「设置」同一行、且只显示图标不带文字', () => {
    // 同一行：外层 .sider-footer-row 同时包住 .sider-footer（设置）与 .sider-toggle
    expect(LAYOUT).toMatch(/class="sider-footer-row"/)
    expect(LAYOUT).toMatch(/sider-footer-row[\s\S]*?class="sider-footer"[\s\S]*?class="sider-toggle"/)
    // 只显示图标：切换按钮内不得有文字标签
    expect(LAYOUT).not.toMatch(/sider-toggle-label/)
    // 文字语义保留在 title / aria-label 里（可访问性不丢）
    expect(LAYOUT).toMatch(/:title="siderPinned \? t\('pages\.Layout\.sider\.collapse'\) : t\('pages\.Layout\.sider\.pin'\)"/)
  })

  it('⑤c 「设置」不能被绝对定位 —— 绝对定位会把它拽出 flex 流，图标被挤到行首（兵哥截图）', () => {
    // 贴底必须作用在**整行** .sider-footer-row 上，而不是行内的 .sider-footer
    expect(LAYOUT).toMatch(/\.app-sider \.sider-footer-row \{[\s\S]*?position: absolute/)
    expect(LAYOUT).not.toMatch(/\.app-sider :deep\(\.sider-footer\) \{[\s\S]*?position: absolute/)
  })

  it('⑥ 偏好跟账号走（setUiSettings 同步全部键，不再只同步 menuLayout）', () => {
    expect(USER_STORE).toMatch(/if \(persist && Object\.keys\(data\)\.length\)/)
    expect(USER_STORE).not.toMatch(/if \(persist && data\.menuLayout\)/)
    // /me 水合不再回写（否则每次登录多打一次 PATCH）
    expect(USER_STORE).toMatch(/setUiSettings\(userData\.uiSettings, false\)/)
    // Layout 读取的键名与 store 写入的一致
    expect(LAYOUT).toMatch(/userStore\.uiSettings\?\.siderPinned === true/)
    expect(LAYOUT).toMatch(/setUiSettings\(\{ siderPinned: !siderPinned\.value \}\)/)
  })

  it('⑦ 中英文案对称（locale:audit 查不出「文案缺失」）', () => {
    expect(ZH).toMatch(/'pages\.Layout\.sider\.pin': "固定侧边栏"/)
    expect(ZH).toMatch(/'pages\.Layout\.sider\.collapse': "折叠侧边栏（仅显示图标）"/)
    expect(EN).toMatch(/'pages\.Layout\.sider\.pin': "Pin sidebar"/)
    expect(EN).toMatch(/'pages\.Layout\.sider\.collapse': "Collapse sidebar \(icons only\)"/)
  })
})

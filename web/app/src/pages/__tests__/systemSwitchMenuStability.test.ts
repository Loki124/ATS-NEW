/**
 * 系统切换（社招 ↔ 校招）——「样式优化 + 消除页面波动」回归护栏（2026-10-21 兵哥指令）
 *
 * 兵哥反馈：系统切换「不好用，而且导致页面波动」，配图里能看到三个问题：
 *   a) 浮层面板过大、圆角 + 阴影过重 → 大面积遮挡下方菜单
 *   b) 「社会招聘」与「✓校园招聘」两行文字不对齐
 *   c) 切换系统后侧栏菜单整组增删 → 条目逐个跳出，画面抖动
 *
 * 这套改动横跨 3 处必须同步的约束（任一处漂移都会复发）：
 *   1. `utils/systemSwitcher.ts` —— 选项行结构（图标槽 / 文字 / 勾）+ 紧凑化主题
 *   2. `components/common/SystemSwitcher.vue` —— 触发器 + 下拉挂载 + 不跳路由（D5）
 *   3. `pages/Layout.vue` —— 菜单随系统重建 + 淡入动画（消化抖动）
 *
 * 按仓库既有先例采用**源码扫描式**断言：CI 零成本、失败信息直指字面量漂移。
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { SYSTEM_ICONS } from '../../utils/systemSwitcher'

const read = (p: string) => fs.readFileSync(path.resolve(__dirname, p), 'utf8')
const LAYOUT = read('../Layout.vue')
const SWITCHER = read('../../components/common/SystemSwitcher.vue')
const SWITCH_UTIL = read('../../utils/systemSwitcher.ts')
const GLASS = read('../../styles/glass.css')
const TOKENS = read('../../styles/tokens.css')

/** 从 CSS 文本里取某个间距令牌的 px 值（用于几何断言，不写死数值） */
function tokenPx(css: string, name: string): number {
  const m = css.match(new RegExp(`${name}:\\s*(\\d+)px`))
  return m ? Number(m[1]) : Number.NaN
}

describe('系统切换器 · 样式与稳定性', () => {
  it('① 选项行整行自绘：图标槽 → 文字 →（当前项）右侧勾', () => {
    expect(SWITCH_UTIL).toMatch(/sys-opt__icon/)
    expect(SWITCH_UTIL).toMatch(/sys-opt__text/)
    expect(SWITCH_UTIL).toMatch(/sys-opt__check/)
    // 回归护栏：不得再用 naive 的 icon 字段 + 空 span 占位（那正是文字错位的根因）
    expect(SWITCH_UTIL).not.toMatch(/display:inline-block;width:14px/)
    for (const opt of ['icon: () =>']) {
      expect(SWITCH_UTIL).not.toContain(opt)
    }
  })

  it('② naive 的 prefix 预留位归零（文字起始位置不再被图标槽挤偏）', () => {
    expect(SWITCH_UTIL).toMatch(/optionPrefixWidthMedium: '0px'/)
    expect(SWITCH_UTIL).toMatch(/optionIconPrefixWidthMedium: '0px'/)
  })

  it('③ 面板紧凑化：行高 / 字号在组件侧，圆角 / 阴影 / 内边距在 glass.css 统一收', () => {
    expect(SWITCH_UTIL).toMatch(/optionHeightMedium: '32px'/)
    expect(SWITCH_UTIL).toMatch(/fontSizeMedium: '13px'/)
    // 面板视觉必须落在 glass.css 的「紧凑型变体」（L2/L3 用 !important 锁了标准值）
    expect(GLASS).toMatch(/\.n-dropdown-menu\.sys-switch-dropdown \{/)
    expect(GLASS).toMatch(/box-shadow: var\(--shadow-float\) !important/)
    expect(GLASS).toMatch(/border-radius: var\(--radius-sm\) !important/)
    // 轻投影令牌必须真实存在（浅色 + 暗色各一份），否则浮层会退化成 naive 默认重投影
    expect(TOKENS).toMatch(/--shadow-float:\s*0 4px 16px rgba\(15, 23, 42/)
    expect(TOKENS).toMatch(/--shadow-float:\s*0 4px 16px rgba\(0, 0, 0/)
  })

  it('④ 下拉面板挂紧凑化 class（teleport 到 body，只能用全局 class 命中）', () => {
    expect(SWITCHER).toMatch(/menu-props/)
    expect(SWITCHER).toMatch(/sys-switch-dropdown/)
    // 行结构样式必须是非 scoped 的全局块（scoped 打不中 teleport 内容）
    expect(SWITCHER).toMatch(/<style>\s*\/\* === 选项行/)
    // 面板级视觉不得在组件里硬编码（规范 §5：禁止组件硬编码圆角 / 选项内边距）
    expect(SWITCHER).not.toMatch(/border-radius: var\(--radius-sm\);\s*\n\s*box-shadow/)
  })

  it('⑤ 触发器有系统图标 + 无障碍标注（折叠态单字按钮同样可理解）', () => {
    expect(SWITCHER).toMatch(/sys-switch__icon/)
    expect(SWITCHER).toMatch(/:aria-label="switchAriaLabel"/)
    expect(SWITCHER).toMatch(/:title="switchAriaLabel"/)
    // 折叠态视觉 32px，命中区用伪元素扩到 44×44（R-102）
    expect(SWITCHER).toMatch(/\.sys-switch--collapsed::after \{[\s\S]*?inset: -6px/)
  })

  it('⑥ 切换系统**不跳路由**（DUAL_SYSTEM_DESIGN.md D5：停留当前路由）', () => {
    const switchBranch = SWITCHER.slice(SWITCHER.indexOf('systemStore.switchTo'), SWITCHER.indexOf('</script>'))
    expect(switchBranch).not.toMatch(/router\.push/)
    expect(SWITCHER).not.toMatch(/router\.push\('\/dashboard'\)/)
    expect(SWITCHER).not.toMatch(/router\.push\("\/dashboard"\)/)
  })

  it('⑦ 侧栏菜单随系统重建 + 淡入，消化「整组增删」造成的抖动', () => {
    expect(LAYOUT).toMatch(/:key="`sider-menu-\$\{systemStore\.current\}`"/)
    expect(LAYOUT).toMatch(/:key="`top-menu-\$\{systemStore\.current\}`"/)
    expect(LAYOUT).toMatch(/sider-menu--switching/)
    expect(LAYOUT).toMatch(/@keyframes sider-menu-switch-in/)
    // 只动 opacity / transform（R-206）
    const anim = LAYOUT.slice(LAYOUT.indexOf('@keyframes sider-menu-switch-in'))
    expect(anim.slice(0, 320)).toMatch(/opacity/)
    expect(anim.slice(0, 320)).toMatch(/transform/)
    expect(anim.slice(0, 320)).not.toMatch(/width:|height:|margin/)
    // 尊重 prefers-reduced-motion（R-206）
    expect(LAYOUT).toMatch(/@media \(prefers-reduced-motion: reduce\)/)
  })

  it('⑧ 首次挂载不播切换动画（只有真正切换过一次才淡入）', () => {
    expect(LAYOUT).toMatch(/const systemSwitched = ref\(false\)/)
    expect(LAYOUT).toMatch(/watch\(\s*\(\) => systemStore\.current/)
  })

  it('⑨ 行内容必须落在 hover 高亮块内侧（2026-10-22 兵哥反馈「hover 时样式很奇怪」）', () => {
    // naive 的行高亮层是 `.n-dropdown-option-body::before { inset: 0 var(--space-1) }`
    // → 在行内容盒内缩 4px；而行内容盒已被 `.n-dropdown-option { padding: 0 var(--space-3) }`
    //    从面板边缘内缩 8px → 内容盒左右各有 4px 在高亮块**外面**。
    // 自绘行（prefix 宽度已压到 0）若不补内边距，图标就落进那 4px 的沟里 →
    // hover 时图标看起来「跑到高亮块外面」，高亮块左边缘还会在图标旁形成一条竖线。
    const glassInsetToken = GLASS.match(
      /\.n-dropdown-option-body::before[\s\S]*?inset:\s*0\s+var\((--space-\d+)\)/,
    )?.[1]
    expect(glassInsetToken, 'glass.css 的行高亮层应使用间距令牌表达 inset').toBeTruthy()
    const highlightInset = tokenPx(TOKENS, glassInsetToken!)
    const rowPadding = tokenPx(TOKENS, '--space-2')
    expect(highlightInset).toBeGreaterThan(0)
    expect(rowPadding).toBeGreaterThanOrEqual(highlightInset)

    const sysOptRule = SWITCHER.match(/\.sys-opt \{([\s\S]*?)\n\}/)
    expect(sysOptRule, '应存在 .sys-opt 行样式').toBeTruthy()
    expect(sysOptRule![1]).toMatch(/padding:\s*0\s+var\(--space-2\)/)
  })

  it('⑩ 社招图标不得用 PeopleOutline（两个交叠人形，16px 下糊成一团像被裁了一半）', () => {
    expect(SYSTEM_ICONS.social).toBeTruthy()
    expect((SYSTEM_ICONS.social as unknown as { name?: string }).name).not.toBe('PeopleOutline')
    expect((SYSTEM_ICONS.social as unknown as { name?: string }).name).toBe('PersonOutline')
  })

  it('⑪ 折叠态焦点环内描边（外扩 2px 的方框会压在下方浮层左上角）', () => {
    expect(SWITCHER).toMatch(/\.sys-switch--collapsed:focus-visible \{[\s\S]*?outline-offset: -2px/)
  })
})

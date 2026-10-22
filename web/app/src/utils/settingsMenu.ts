/**
 * settingsMenu.ts — 设置模块侧栏菜单的结构变换
 *
 * 背景（2026-10-21 兵哥指令：「把系统设置模块的菜单也按照悬浮展示子菜单的形式处理」）：
 *   设置侧栏折叠到 64px 后，naive-ui 的折叠态浮出（hover 弹出二级菜单）**不生效**，
 *   「公司信息管理 / 组织管理 / 权限管理 / 候选人信息 …」这些图标全是死路：
 *   ① hover 不出二级菜单；
 *   ② 点击也没反应（父项 key 不是路由，handleMenuClick 只处理 '/' 开头的 key）。
 *
 * 根因在 naive-ui 源码，不是样式问题：
 *   - `menu/src/utils.mjs` `itemRenderer`：`root: level === 0`
 *   - `menu/src/Submenu.mjs` render：`this.root ? h(NDropdown, …) : h('div', …)`
 *     —— **只有根级子菜单才包 NDropdown（浮出载体）**，非根级子菜单走普通 div 分支。
 *   设置菜单的结构是「分组(type:'group') → 子菜单 → 叶子」三层，
 *   所有可展开父项都在 level 1 → `root === false` → 永远拿不到浮出载体。
 *   （主侧栏没有分组层，父项都在 level 0，所以它的浮出是好的。）
 *
 * 修法：**折叠态把分组打平**，组内条目提升为根级 → 父项回到 level 0 → 原生浮出即可用。
 * 展开态保持原分组结构不变（分组标题是设置页的主要导航线索，不能丢）。
 */
import type { MenuOption } from 'naive-ui'

/**
 * 折叠态菜单：分组打平 + 组间插入分隔线。
 *
 * @param options 已按权限裁剪的菜单树（分组结构）
 * @returns 全部条目位于根级的菜单树（可展开父项得以触发 naive 原生 hover 浮出）
 */
export function buildCollapsedMenuOptions(options: MenuOption[]): MenuOption[] {
  const out: MenuOption[] = []
  let groupIndex = 0
  for (const opt of options) {
    if (opt.type === 'group') {
      const children = (opt.children ?? []) as MenuOption[]
      // 空分组直接跳过（权限裁剪后可能已空），不留空壳
      if (!children.length) continue
      // 组与组之间补一条分隔线：折叠态看不到组标题了，用分隔线保留视觉分组
      if (groupIndex > 0) {
        out.push({ type: 'divider', key: `settings-divider-${String(opt.key ?? groupIndex)}` })
      }
      out.push(...children)
      groupIndex += 1
      continue
    }
    out.push(opt)
  }
  return out
}

/**
 * 折叠态下菜单里「可展开父项」是否都已提升到根级。
 *
 * 供护栏测试断言用：只要有一个父项不在根级，它的图标在折叠态就是死路
 * （naive 的浮出载体 NDropdown 只挂在 root 子菜单上）。
 */
export function countRootExpandable(options: MenuOption[]): number {
  return options.filter((o) => o.type !== 'group' && (o.children?.length ?? 0) > 0).length
}

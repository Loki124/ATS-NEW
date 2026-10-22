import { h, type Component } from 'vue'
import { NIcon, type DropdownOption, type DropdownDividerOption } from 'naive-ui'
import {
  CheckmarkOutline,
  PersonOutline,
  SchoolOutline,
  ShareSocialOutline,
} from '@vicons/ionicons5'
import { RECRUIT_SYSTEMS, type RecruitSystemKey } from '../stores/system'

/**
 * 系统切换器（社会招聘 / 校园招聘）下拉的**纯逻辑层**
 *
 * 为什么要单独抽出来：
 *  - 选项的 DOM 结构需要断言（「图标槽 / 文字 / 勾」三段固定宽度），
 *    挂在 .vue 里只能靠脆弱的 DOM 快照；抽成纯函数后可直接单测。
 *  - naive-ui 的 option 结构有坑，见 buildSystemSwitcherOptions 的注释。
 */

/**
 * 各招聘系统的语义图标：社招 = 单人，校招 = 学校
 *
 * ⚠️ 社招**不用** `PeopleOutline` —— 那个图标是两个交叠的人形（两个头 + 两条身体路径），
 * 在 16px 下糊成一团，看着像「图标被裁了一半」（兵哥 2026-10-22 反馈）。
 * 单人 `PersonOutline` 在 16px 下轮廓清晰。
 */
export const SYSTEM_ICONS: Record<RecruitSystemKey, Component> = {
  social: PersonOutline,
  campus: SchoolOutline,
}

/** 「内推助手」是功能入口（路由跳转），不是招聘系统 */
export const REFERRAL_ICON = ShareSocialOutline
export const REFERRAL_KEY = '/referral'

export type SystemSwitcherOption = DropdownOption | DropdownDividerOption

/**
 * 构造系统切换下拉的选项列表。
 *
 * ⚠️ 为什么**不**用 naive-ui 的 `icon` prop：
 *   naive 的 option body 结构固定为 [prefix 槽][label][suffix 槽]，prefix 宽度由
 *   「整个菜单里是否存在任一带 icon 的项」决定（有 → 36px，无 → 14px）。
 *   早前用「空 span 占位」补齐当前项的图标位时，「社会招聘」与「✓校园招聘」两行
 *   文字起始位置对不齐（兵哥 2026-10-21 反馈），且勾选态挤在图标槽里、右侧无对齐位。
 *   现在改为**整行自绘**（图标槽 + 文字 + 右侧勾），并把 naive 的 prefix 宽度压到 0，
 *   文字永远左对齐、勾永远靠右，且与 naive 内部结构解耦。
 *
 * @param current 当前生效的招聘系统（决定哪一项打勾）
 */
export function buildSystemSwitcherOptions(current: RecruitSystemKey): SystemSwitcherOption[] {
  const list: SystemSwitcherOption[] = RECRUIT_SYSTEMS.map((s) => ({
    key: s.key,
    label: () =>
      h('div', { class: ['sys-opt', { 'sys-opt--current': s.key === current }] }, [
        h('span', { class: 'sys-opt__icon' }, [
          h(NIcon, { size: 16 }, { default: () => h(SYSTEM_ICONS[s.key]) }),
        ]),
        h('span', { class: 'sys-opt__text' }, s.label),
        s.key === current
          ? h('span', { class: 'sys-opt__check' }, [
              h(NIcon, { size: 15 }, { default: () => h(CheckmarkOutline) }),
            ])
          : null,
      ]),
  }))

  // 分隔线把「招聘系统」与「功能入口」分开，避免误点
  list.push({ type: 'divider', key: 'div-referral' })
  list.push({
    key: REFERRAL_KEY,
    label: () =>
      h('div', { class: 'sys-opt' }, [
        h('span', { class: 'sys-opt__icon' }, [
          h(NIcon, { size: 16 }, { default: () => h(REFERRAL_ICON) }),
        ]),
        h('span', { class: 'sys-opt__text' }, '内推助手'),
      ]),
  })
  return list
}

/**
 * 下拉面板的紧凑化设置（2026-10-21 兵哥反馈：浮层过大、阴影过重、遮挡下方菜单）
 *
 * ⚠️ 这里只放「naive 内联 CSS 变量、且 glass.css 没有 !important 锁死」的那几项：
 *   行高（--n-option-height）、字号（--n-font-size）、prefix 槽宽（--n-option-prefix-width）。
 *   圆角 / 阴影 / 面板内边距由 glass.css §下拉弹窗规范 的**紧凑型变体**
 *   （`.n-dropdown-menu.sys-switch-dropdown`）统一负责 —— L2/L3 用 !important 锁了标准值，
 *   组件内覆盖会被压掉，且「下拉视觉单一真源」要求变体也落在那一节。
 */
export const SYSTEM_SWITCHER_THEME_OVERRIDES = {
  // 行高 34→32、字号 14→13：面板整体更矮，遮挡面积小一圈
  optionHeightMedium: '32px',
  fontSizeMedium: '13px',
  // prefix 槽归零：图标/文字/勾全部自绘，杜绝 naive 预留位导致的文字错位
  optionPrefixWidthMedium: '0px',
  optionIconPrefixWidthMedium: '0px',
}

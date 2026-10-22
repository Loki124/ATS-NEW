/**
 * systemSwitcher.test.ts — 系统切换器纯逻辑层单测
 *
 * 覆盖:
 *  - 选项构成与顺序（2 个系统 + 分隔线 + 内推助手）
 *  - 选项行三段结构：图标槽 → 文字 →（当前项）右侧勾
 *  - **回归护栏**：选项不得使用 naive-ui 的 `icon` 字段
 *    （naive 会据此给 prefix 槽留 14/36px 预留位，导致两行文字起始位置对不齐）
 *  - 紧凑化主题覆盖（行高/字号/内边距/prefix 宽度/轻投影）
 */
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import type { VNode } from 'vue'
import {
  buildSystemSwitcherOptions,
  SYSTEM_ICONS,
  SYSTEM_SWITCHER_THEME_OVERRIDES,
  REFERRAL_KEY,
} from '../systemSwitcher'
import { RECRUIT_SYSTEMS } from '../../stores/system'

/** 取某个选项 label 渲染出的 VNode */
function labelOf(option: unknown): VNode {
  const label = (option as { label?: () => VNode }).label
  expect(typeof label).toBe('function')
  return (label as () => VNode)()
}

/** 取选项行 VNode 的三个子节点 */
function rowParts(vnode: VNode) {
  const children = vnode.children as VNode[]
  return {
    icon: children[0],
    text: children[1],
    check: children[2] ?? null,
  }
}

describe('buildSystemSwitcherOptions', () => {
  it('选项构成固定：2 个系统 + 1 分隔线 + 内推助手', () => {
    const list = buildSystemSwitcherOptions('social')
    expect(list).toHaveLength(4)
    expect(list[0].key).toBe('social')
    expect(list[1].key).toBe('campus')
    expect(list[2].type).toBe('divider')
    expect(list[3].key).toBe(REFERRAL_KEY)
  })

  it('每个系统项的行结构是 [图标槽, 文字, 勾?]，顺序固定', () => {
    const list = buildSystemSwitcherOptions('social')
    for (const opt of list.slice(0, 2)) {
      const vnode = labelOf(opt)
      expect(vnode.props?.class).toContain('sys-opt')
      const parts = rowParts(vnode)
      expect(parts.icon?.props?.class).toBe('sys-opt__icon')
      expect(parts.text?.props?.class).toBe('sys-opt__text')
    }
  })

  it('当前系统打勾（勾在右侧独立槽位），非当前系统不打勾', () => {
    const list = buildSystemSwitcherOptions('campus')
    const social = rowParts(labelOf(list[0]))
    const campus = rowParts(labelOf(list[1]))
    expect(social.check).toBeNull()
    expect(campus.check?.props?.class).toBe('sys-opt__check')
    // 当前项整行加 current 修饰类（品牌色 + 加粗）；class 在建 vnode 时已被 Vue 归一化成字符串
    expect(labelOf(list[1]).props?.class).toContain('sys-opt--current')
    expect(labelOf(list[0]).props?.class).not.toContain('sys-opt--current')
  })

  it('文字内容取自 RECRUIT_SYSTEMS（社招/校招），与勾的位置无关', () => {
    const list = buildSystemSwitcherOptions('social')
    expect(rowParts(labelOf(list[0])).text?.children).toBe(RECRUIT_SYSTEMS[0].label)
    expect(rowParts(labelOf(list[1])).text?.children).toBe(RECRUIT_SYSTEMS[1].label)
  })

  it('内推助手行结构一致（图标 + 文字，无勾）', () => {
    const list = buildSystemSwitcherOptions('social')
    const vnode = labelOf(list[3])
    const parts = rowParts(vnode)
    expect(parts.icon?.props?.class).toBe('sys-opt__icon')
    expect(parts.text?.children).toBe('内推助手')
    expect(parts.check).toBeNull()
  })

  it('回归护栏：选项不得使用 naive 的 icon 字段（会挤偏文字）', () => {
    for (const opt of buildSystemSwitcherOptions('campus')) {
      expect((opt as { icon?: unknown }).icon).toBeUndefined()
    }
  })
})

describe('SYSTEM_ICONS', () => {
  it('社招 / 校招 各有独立图标', () => {
    expect(SYSTEM_ICONS.social).toBeTruthy()
    expect(SYSTEM_ICONS.campus).toBeTruthy()
    expect(SYSTEM_ICONS.social).not.toBe(SYSTEM_ICONS.campus)
  })
})

describe('SYSTEM_SWITCHER_THEME_OVERRIDES', () => {
  it('只包含「naive 内联变量」且未被 glass.css !important 锁死的项', () => {
    // 行高 / 字号 / prefix 槽宽走内联 CSS 变量 → 组件侧可生效
    expect(SYSTEM_SWITCHER_THEME_OVERRIDES.optionHeightMedium).toBe('32px')
    expect(SYSTEM_SWITCHER_THEME_OVERRIDES.fontSizeMedium).toBe('13px')
    expect(SYSTEM_SWITCHER_THEME_OVERRIDES.optionPrefixWidthMedium).toBe('0px')
    expect(SYSTEM_SWITCHER_THEME_OVERRIDES.optionIconPrefixWidthMedium).toBe('0px')
    // 圆角 / 阴影 / 内边距由 glass.css 的紧凑变体统一负责（组件侧写了也会被 !important 压掉）
    expect(Object.keys(SYSTEM_SWITCHER_THEME_OVERRIDES).sort()).toEqual([
      'fontSizeMedium',
      'optionHeightMedium',
      'optionIconPrefixWidthMedium',
      'optionPrefixWidthMedium',
    ])
  })

  it('紧凑变体的视觉值落在 glass.css（下拉视觉单一真源）', () => {
    const GLASS = fs.readFileSync(
      path.resolve(__dirname, '../../styles/glass.css'),
      'utf8',
    )
    expect(GLASS).toMatch(/\.n-dropdown-menu\.sys-switch-dropdown \{/)
    expect(GLASS).toMatch(/border-radius: var\(--radius-sm\) !important/)
    expect(GLASS).toMatch(/box-shadow: var\(--shadow-float\) !important/)
    expect(GLASS).toMatch(/padding: var\(--space-1\) 0 !important/)
  })

  it('轻投影令牌必须真实存在（浅色 + 暗色各一份），否则浮层会退化成 naive 默认重投影', () => {
    const TOKENS = fs.readFileSync(
      path.resolve(__dirname, '../../styles/tokens.css'),
      'utf8',
    )
    expect(TOKENS).toMatch(/--shadow-float:\s*0 4px 16px rgba\(15, 23, 42/)
    expect(TOKENS).toMatch(/--shadow-float:\s*0 4px 16px rgba\(0, 0, 0/)
  })
})

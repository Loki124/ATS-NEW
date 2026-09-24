/**
 * 语言切换入口的专属 i18n 字典（2026-09-24）
 *
 * 独立成文件的原因：zh-CN.ts / en-US.ts 当前被并行会话 WIP 占用（工作树脏改），
 * 为避免把未提交的他人改动一并提交，语言切换这一个 key 单独成模块，由 index.ts 合并。
 *
 * 语言选项的中文/英文「原生名」（简体中文 / English）在 LanguageSwitcher.vue 内硬编码
 * （按惯例语言名用其母语书写，便于用户无论当前 UI 语言都能识别），此处仅放可本地化的
 * 无障碍标签（aria-label）。
 */

export const LANGUAGE_ZH: Record<string, string> = {
  'components.common.LanguageSwitcher.s1': '语言',
}

export const LANGUAGE_EN: Record<string, string> = {
  'components.common.LanguageSwitcher.s1': 'Language',
}

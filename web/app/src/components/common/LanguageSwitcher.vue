<template>
  <n-dropdown
    trigger="click"
    placement="bottom-end"
    :options="options"
    :show-arrow="true"
    @select="onSelect"
  >
    <button class="lang-trigger" type="button" :aria-label="ariaLabel">
      <NIcon :size="20" aria-hidden="true"><LanguageOutline /></NIcon>
    </button>
  </n-dropdown>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { NIcon } from 'naive-ui'
import { LanguageOutline, CheckmarkOutline as Check } from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import { currentLocale, SUPPORTED_LOCALES, type AppLocale } from '../../locales'

/**
 * LanguageSwitcher — 页面右上角语言切换入口。
 *
 * 触发器：玻璃化方形图标按钮（地球图标），置于 Layout 头部右集群最右侧。
 * 浮层：n-dropdown 下拉菜单，placement="bottom-end" 保证在视口右上角展开；
 *      桌面端与移动端均右对齐触发器，超出时 Naive UI 自动翻转。
 * 选项：母语书写的语言名（简体中文 / English），当前项带品牌色勾选。
 * 关闭：点击外部区域或选择语言后自动关闭。
 */
const { t } = useI18n()
const ariaLabel = computed(() => t('components.common.LanguageSwitcher.s1'))

const options = computed(() =>
  SUPPORTED_LOCALES.map((l) => ({
    key: l.code,
    label: () =>
      h(
        'span',
        { style: 'display:inline-flex;align-items:center;justify-content:space-between;gap:12px;width:100%' },
        [
          h('span', { style: 'font-weight:' + (l.code === currentLocale.value ? '500' : '400') }, l.native),
          l.code === currentLocale.value
            ? h(NIcon, { size: 14, style: 'color:var(--brand)' }, { default: () => h(Check) })
            : h('span', { style: 'display:inline-block;width:14px' }),
        ],
      ),
  })),
)

function onSelect(key: string) {
  if (key === currentLocale.value) return
  currentLocale.value = key as AppLocale
}
</script>

<style scoped>
.lang-trigger {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.lang-trigger:hover,
.lang-trigger:focus-visible {
  color: var(--brand);
  background: var(--brand-tint);
}
.lang-trigger:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
</style>

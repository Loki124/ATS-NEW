<template>
  <n-dropdown
    trigger="click"
    :options="options"
    :show-arrow="true"
    @select="onSelect"
  >
    <button class="lang-switch" type="button" :aria-label="ariaLabel">
      <NIcon :size="18" aria-hidden="true"><LanguageOutline /></NIcon>
      <span class="lang-switch__label">{{ currentNative }}</span>
      <NIcon :size="12" class="lang-switch__chevron" aria-hidden="true"><ChevronDown /></NIcon>
    </button>
  </n-dropdown>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { NIcon } from 'naive-ui'
import { LanguageOutline, ChevronDownOutline as ChevronDown, CheckmarkOutline as Check } from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import { currentLocale, SUPPORTED_LOCALES, type AppLocale } from '../../locales'

/**
 * LanguageSwitcher — 顶栏语言切换入口（简体中文 / English）。
 *
 * 位置：Layout 头部右集群（通知与用户头像之间），side 与 top 布局通用。
 * 状态：currentLocale（locales/index.ts 的可写 computed，localStorage 持久化）。
 * 切换即更新 vue-i18n 全局 locale，全站文案响应式跟随；naive-ui 内置英文默认不受影响。
 */
const { t } = useI18n()

const currentNative = computed(
  () => SUPPORTED_LOCALES.find((l) => l.code === currentLocale.value)?.native ?? '简体中文',
)
const ariaLabel = computed(() => t('components.common.LanguageSwitcher.s1'))

const options = computed(() =>
  SUPPORTED_LOCALES.map((l) => ({
    key: l.code,
    label: l.native,
    icon: () =>
      l.code === currentLocale.value
        ? h(NIcon, { size: 14, style: 'color:var(--brand)' }, { default: () => h(Check) })
        : h('span', { style: 'display:inline-block;width:14px' }),
  })),
)

function onSelect(key: string) {
  if (key === currentLocale.value) return
  currentLocale.value = key as AppLocale
}
</script>

<style scoped>
.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border-hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-13);
  line-height: 1;
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.lang-switch:hover,
.lang-switch:focus-visible {
  color: var(--brand);
  background: var(--brand-tint);
}
.lang-switch:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
.lang-switch__label {
  white-space: nowrap;
  font-weight: 500;
}
.lang-switch__chevron {
  flex-shrink: 0;
  opacity: 0.7;
}
</style>

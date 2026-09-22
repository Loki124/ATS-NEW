<template>
  <n-dropdown
    trigger="click"
    :options="options"
    :show-arrow="true"
    @select="onSelect"
  >
    <!-- 折叠态（侧栏 64px）：仅显示当前系统单字 + 切换角标，纵向紧凑 -->
    <button
      v-if="collapsed"
      class="sys-switch sys-switch--collapsed"
      type="button"
      :aria-label="`当前系统：${systemStore.label}，点击切换系统`"
    >
      <span class="sys-switch__short">{{ systemStore.meta.short }}</span>
      <NIcon :size="12" class="sys-switch__chevron" aria-hidden="true"><ChevronDown /></NIcon>
    </button>

    <!-- 展开态 / 顶部横排：当前系统名 + chevron，横向 pill -->
    <button
      v-else
      class="sys-switch"
      type="button"
      :aria-label="`当前系统：${systemStore.label}，点击切换系统`"
    >
      <span class="sys-switch__label">{{ systemStore.label }}</span>
      <NIcon :size="14" class="sys-switch__chevron" aria-hidden="true"><ChevronDown /></NIcon>
    </button>
  </n-dropdown>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { NDropdown, NIcon, useMessage } from 'naive-ui'
import { ChevronDownOutline as ChevronDown, CheckmarkOutline as Check } from '@vicons/ionicons5'
import { useSystemStore, RECRUIT_SYSTEMS, type RecruitSystemKey } from '../../stores/system'

/**
 * SystemSwitcher — 「社会招聘 / 校园招聘」双系统切换入口
 *
 * 位置：Layout 品牌 logo 右侧（side 折叠态独占一行；展开态 / top 横排在 logo 文本右侧）。
 * 状态：useSystemStore（localStorage 持久化）；Phase 1 仅切换前端上下文，
 * 数据隔离待后端 recruit_type 维度落地后接入（见 docs/02-architecture/DUAL_SYSTEM_DESIGN.md）。
 */
defineProps<{ collapsed?: boolean }>()

const systemStore = useSystemStore()
const message = useMessage()

const options = computed(() =>
  RECRUIT_SYSTEMS.map((s) => ({
    key: s.key,
    label: s.label,
    icon: () =>
      s.key === systemStore.current
        ? h(NIcon, { size: 14, style: 'color:var(--brand)' }, { default: () => h(Check) })
        : h('span', { style: 'display:inline-block;width:14px' }),
  })),
)

function onSelect(key: RecruitSystemKey) {
  if (key === systemStore.current) return
  systemStore.switchTo(key)
  const target = RECRUIT_SYSTEMS.find((s) => s.key === key)
  message.success(`已切换到「${target?.label}」系统`)
}
</script>

<style scoped>
.sys-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 8px;
  border: 1px solid var(--border-hairline);
  border-radius: 999px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  line-height: 1;
  cursor: pointer;
  user-select: none;
  transition: background var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}
.sys-switch:hover,
.sys-switch:focus-visible {
  color: var(--brand);
  background: var(--brand-tint);
}
.sys-switch:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
.sys-switch__label {
  white-space: nowrap;
  font-weight: 500;
}
.sys-switch__chevron {
  flex-shrink: 0;
  opacity: 0.7;
}

/* 侧栏折叠态：64px 宽度内居中，纵向单字 + chevron */
.sys-switch--collapsed {
  width: 32px;
  height: 32px;
  padding: 0;
  flex-direction: column;
  justify-content: center;
  gap: 0;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
}
.sys-switch--collapsed .sys-switch__short {
  font-weight: 600;
}
</style>

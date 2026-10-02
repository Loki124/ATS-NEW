<template>
  <n-popover :to="'body'" trigger="hover" placement="bottom">
    <template #trigger>
      <span class="ws-op-badge">
        <span class="ws-op-dot" />
        {{ t('metrics.operator.count', { n: value.length }) }}
      </span>
    </template>
    <div class="ws-op-pop">
      <div class="ws-op-pop-title">{{ t('metrics.operator.popoverTitle') }}</div>
      <div class="ws-op-pop-chips">
        <n-tag v-for="op in value" :key="op" size="small" type="info">
          {{ operatorLabel(op) }}
        </n-tag>
      </div>
    </div>
  </n-popover>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { NPopover, NTag } from 'naive-ui'
import type { OptionItem } from '@/api/metrics'

const props = defineProps<{
  /** 运算符 code 列表（如 ['gt', 'lt']） */
  value: string[]
  /** 运算符目录（来自 operatorCatalog），用于把 code 转中文 label */
  catalog?: OptionItem[]
}>()

const { t } = useI18n()

/** code -> 中文 label，找不到则回退原始 code */
function operatorLabel(op: string): string {
  return props.catalog?.find((o) => o.value === op)?.label ?? op
}
</script>

<style scoped>
.ws-op-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-12);
  line-height: 1;
  color: var(--ink-soft);
  cursor: default;
  white-space: nowrap;
}
.ws-op-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
}
.ws-op-pop {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 280px;
}
.ws-op-pop-title {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink-strong);
}
.ws-op-pop-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>

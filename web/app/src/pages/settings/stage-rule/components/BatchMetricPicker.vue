<!--
  批量添加指标条件入口（EXP-3）。
  - 点击触发一个多选面板，列出目录中 METRIC 的所有字段（指标模板），显示 label；
  - 用户勾选若干模板后点「添加」，向当前规则逐条追加对应 METRIC 条件项；
  - catalog 无 METRIC 字段（含加载失败 / 未配置）时面板提示空态，按钮禁用由调用方控制。
  面板内容经 naive-ui 的 NPopover 默认 teleport 到 body，故样式使用非 scoped 块并以
  `bmp-` 前缀收口，避免污染其他组件。
-->
<template>
  <n-popover
    v-model:show="show"
    trigger="click"
    placement="bottom-start"
    :show-arrow="false"
    :disabled="disabled"
  >
    <template #trigger>
      <span class="bmp-trigger" :class="{ 'bmp-trigger--disabled': disabled }">
        <n-icon :component="ListOutline" />
        <span>{{ t('pages.settings.stage-rule.components.BatchMetricPicker.s1') }}</span>
      </span>
    </template>
    <div class="bmp-panel">
      <div class="bmp-panel__title">{{ t('pages.settings.stage-rule.components.BatchMetricPicker.s2') }}</div>
      <div v-if="fields.length" class="bmp-panel__list">
        <label v-for="f in fields" :key="f.field" class="bmp-opt">
          <input v-model="selected" type="checkbox" :value="f.field" />
          <span class="bmp-opt__label">{{ f.label }}</span>
        </label>
      </div>
      <div v-else class="bmp-panel__empty">{{ t('pages.settings.stage-rule.components.BatchMetricPicker.s5') }}</div>
      <div class="bmp-panel__actions">
        <n-button size="tiny" @click="close">{{ t('pages.settings.stage-rule.components.BatchMetricPicker.s3') }}</n-button>
        <n-button size="tiny" type="primary" :disabled="!selected.length" @click="confirm">{{ t('pages.settings.stage-rule.components.BatchMetricPicker.s4') }}</n-button>
      </div>
    </div>
  </n-popover>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { NPopover, NButton, NIcon } from 'naive-ui'
import { ListOutline } from '@vicons/ionicons5'
import { getMetricFields } from '../composables/useMetricTemplateGuard'
import type { FieldCatalog, FieldDef } from '../types'

const props = defineProps<{
  catalog: FieldCatalog | null
  /** 外部容量上限（如当前组/规则已到最大条件数）时禁用入口 */
  disabled?: boolean
}>()
const emit = defineEmits<{
  (e: 'add', fields: FieldDef[]): void
}>()
const { t } = useI18n()

const show = ref(false)
const selected = ref<string[]>([])

const fields = computed(() => getMetricFields(props.catalog))

function close() {
  show.value = false
  selected.value = []
}
function confirm() {
  if (!selected.value.length) return
  const picked = fields.value.filter((f) => selected.value.includes(f.field))
  emit('add', picked)
  close()
}
</script>

<!-- NPopover 默认 teleport 到 body，面板内部样式需非 scoped，并以 bmp- 前缀收口 -->
<style>
.bmp-trigger {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--fs-12);
  color: var(--ink-faint);
  cursor: pointer;
  user-select: none;
  transition: color var(--duration-fast) var(--ease-out);
}
.bmp-trigger:hover:not(.bmp-trigger--disabled) {
  color: var(--brand);
}
.bmp-trigger--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.bmp-trigger .n-icon {
  font-size: 14px;
}

.bmp-panel {
  width: 264px;
}
.bmp-panel__title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
}
.bmp-panel__list {
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
}
.bmp-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-13);
  color: var(--ink-soft);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
}
.bmp-opt:hover {
  background: var(--g1);
}
.bmp-opt input {
  flex-shrink: 0;
  cursor: pointer;
}
.bmp-opt__label {
  line-height: 1.3;
}
.bmp-panel__empty {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  padding: 8px 0;
  margin-bottom: 10px;
}
.bmp-panel__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

<template>
  <n-modal
    :show="visible"
    preset="card"
    class="stopped-rules-modal"
    title="已停用规则"
    :closable="false"
    style="width: 640px; max-width: 95vw; max-height: 86vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="sr-body">
      <p class="field-hint">以下为已停用的自动归档规则，重新启用后将恢复生效。</p>
      <RuleTable :columns="columns" :rows="rules">
        <template #actions="{ row }">
          <div class="action-btns">
            <a @click="emit('reenable', row)">重新启用</a>
          </div>
        </template>
      </RuleTable>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">关闭</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NModal, NButton } from 'naive-ui'
import RuleTable from '../components/RuleTable.vue'
import type { ArchiveRule } from '../types'

const emit = defineEmits<{
  (e: 'reenable', rule: ArchiveRule): void
  (e: 'close'): void
}>()

const visible = ref(false)
const saving = ref(false)
const rules = ref<ArchiveRule[]>([])

const columns = [
  { key: 'name', title: '规则名', width: '34%' },
  { key: 'expression', title: '执行条件', width: '40%' },
  { key: 'effective_scope', title: '生效方式', width: '16%' },
]

function open(list: ArchiveRule[]) {
  rules.value = list
  visible.value = true
}
defineExpose({ open })

function onRequestClose() {
  if (saving.value) return
  visible.value = false
  emit('close')
}
</script>

<style scoped>
.sr-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.field-hint {
  color: var(--ink-soft);
  font-size: var(--fs-12);
  margin: 0;
  line-height: 1.5;
}
.action-btns {
  display: flex;
  gap: 10px;
}
.action-btns a {
  color: var(--brand);
  text-decoration: none;
  cursor: pointer;
  font-size: var(--fs-12);
}
.action-btns a:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}
.modal-footer {
  padding: var(--space-3) 0;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>

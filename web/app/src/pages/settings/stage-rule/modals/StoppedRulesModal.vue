<template>
  <n-modal
    :show="visible"
    preset="card"
    class="stopped-rules-modal"
    :title="t('pages.settings.stage-rule.modals.StoppedRulesModal.s3')"
    :closable="false"
    style="width: 640px; max-width: 95vw; max-height: 86vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="sr-body">
      <p class="field-hint">{{ t('pages.settings.stage-rule.modals.StoppedRulesModal.s1') }}</p>
      <RuleTable :columns="columns" :rows="rules">
        <template #actions="{ row }">
          <div class="action-btns">
            <a @click="emit('reenable', row)">{{ t('pages.settings.stage-rule.modals.StoppedRulesModal.s2') }}</a>
          </div>
        </template>
      </RuleTable>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">{{ t('pages.settings.stage-rule.modals.StoppedRulesModal.s4') }}</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref } from 'vue'
import { NModal, NButton } from 'naive-ui'
import RuleTable from '../components/RuleTable.vue'
const { t } = useI18n()

export interface StoppedItem {
  id: string
  name: string
  expression: string
  kindLabel: string
  rule: any
}

const emit = defineEmits<{
  (e: 'reenable', item: StoppedItem): void
  (e: 'close'): void
}>()

const visible = ref(false)
const saving = ref(false)
const rules = ref<StoppedItem[]>([])

const columns = [
  { key: 'name', title: t('pages.settings.stage-rule.modals.StoppedRulesModal.s5'), width: '24%' },
  { key: 'kindLabel', title: t('pages.settings.stage-rule.modals.StoppedRulesModal.s6'), width: '16%' },
  { key: 'expression', title: t('pages.settings.stage-rule.modals.StoppedRulesModal.s7'), width: '44%' },
]

function open(list: StoppedItem[]) {
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

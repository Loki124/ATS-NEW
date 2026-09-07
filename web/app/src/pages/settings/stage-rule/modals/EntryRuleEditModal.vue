<template>
  <n-modal
    :show="visible"
    preset="card"
    class="entry-rule-edit-modal"
    :title="isNew ? '新建进入条件规则' : '编辑进入条件规则'"
    :closable="false"
    style="width: 720px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="er-body">
      <div class="er-field">
        <label class="field-label">规则名 <span class="required-mark">*</span></label>
        <n-input
          v-model:value="draft.rule_name"
          size="small"
          placeholder="请输入规则名"
          :maxlength="30"
          show-count
          :class="{ 'input-error': !!nameError }"
        />
        <p v-if="nameError" class="error-msg">{{ nameError }}</p>
      </div>

      <div class="er-field">
        <label class="field-label">条件项 <span class="required-mark">*</span></label>
        <div class="cond-list">
          <div v-for="(it, idx) in draft.items" :key="idx" class="cond-row">
            <span class="cond-seq">{{ idx + 1 }}</span>
            <ConditionPicker :model-value="it" :catalog="catalog" @update:model-value="onItemUpdate(idx, $event)" />
            <button class="cond-del" type="button" :disabled="draft.items.length <= 1" @click="removeItem(idx)">
              <n-icon :component="TrashOutline" />
            </button>
          </div>
        </div>
        <button class="btn-outline-primary" type="button" :disabled="!canAddItem" @click="addItem()">
          <n-icon :component="AddOutline" /> 添加条件
        </button>
        <p v-if="!canAddItem" class="field-hint">最多 {{ AR_MAX_CONDITIONS }} 个条件项</p>
      </div>

      <div class="er-field">
        <label class="field-label">
          组内表达式
          <n-popover trigger="hover" placement="top">
            <template #trigger>
              <n-icon class="help-icon" :component="HelpCircleOutline" />
            </template>
            <ul class="help-list">
              <li v-for="(h, i) in EXPRESSION_HELP" :key="i">{{ h }}</li>
            </ul>
          </n-popover>
        </label>
        <n-input v-model:value="draft.expression" size="small" placeholder="如 1 and 2" :class="{ 'input-error': exprInvalid }" />
        <p v-if="exprInvalid" class="error-msg">{{ exprError?.error }}</p>
      </div>

      <div class="er-field">
        <label class="field-label">整体未满足提示</label>
        <n-input
          v-model:value="draft.reject_message"
          type="textarea"
          size="small"
          placeholder="候选人不满足该条件时的提示文案"
          :maxlength="500"
          show-count
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">取消</n-button>
        <n-button size="small" type="primary" :disabled="hasError || saving" :loading="saving" @click="onSave">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NModal, NInput, NButton, NIcon, NPopover } from 'naive-ui'
import { TrashOutline, AddOutline, HelpCircleOutline } from '@vicons/ionicons5'
import ConditionPicker from '../components/ConditionPicker.vue'
import { useEntryRuleEditor } from '../composables/useEntryRuleEditor'
import { AR_MAX_CONDITIONS, EXPRESSION_HELP } from '../constants'
import type { ConditionItem, EntryConditionRule, FieldCatalog } from '../types'

const props = defineProps<{ catalog: FieldCatalog | null }>()
const emit = defineEmits<{
  (e: 'save', rule: EntryConditionRule): void
  (e: 'close'): void
}>()

const { visible, isNew, draft, canAddItem, exprError, nameError, hasError, open, close, addItem, removeItem, renumber } = useEntryRuleEditor()
const saving = ref(false)

const exprInvalid = computed(() => !!exprError && !exprError.empty)

function onItemUpdate(idx: number, item: ConditionItem) {
  draft.items[idx] = item
  renumber()
}

defineExpose({ open })

function onRequestClose() {
  if (saving.value) return
  close()
  emit('close')
}

function onSave() {
  if (hasError) return
  saving.value = true
  try {
    emit('save', closeCommit())
    close()
    emit('close')
  } finally {
    saving.value = false
  }
}

/** 提交前深拷贝 draft（useEntryRuleEditor.commit 内部已 clone，这里复用） */
function closeCommit(): EntryConditionRule {
  return {
    id: draft.id,
    rule_name: draft.rule_name,
    rule_seq: draft.rule_seq,
    status: draft.status,
    expression: draft.expression,
    reject_message: draft.reject_message,
    items: draft.items.map((it) => ({ ...it })),
  }
}
</script>

<style scoped>
.er-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.field-label {
  display: block;
  font-size: var(--fs-13);
  color: var(--ink);
  margin-bottom: 6px;
  font-weight: 500;
}
.required-mark {
  color: var(--c-error);
  margin-left: 2px;
}
.help-icon {
  color: var(--ink-faint);
  font-size: 14px;
  cursor: help;
  margin-left: 4px;
  vertical-align: middle;
}
.cond-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.cond-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.cond-seq {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--brand-a12);
  color: var(--brand);
  font-size: var(--fs-12);
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cond-del {
  background: transparent;
  border: none;
  color: var(--ink-faint);
  cursor: pointer;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.cond-del:hover:not(:disabled) {
  color: var(--c-error);
}
.cond-del:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.input-error :deep(.n-input__input-el),
.input-error :deep(.n-input__textarea-el) {
  border-color: var(--c-error) !important;
  background: var(--c-error-soft);
}
.error-msg {
  color: var(--c-error);
  font-size: var(--fs-12);
  margin: 4px 0 0;
}
.field-hint {
  color: var(--ink-soft);
  font-size: var(--fs-12);
  margin: 6px 0 0;
}
.help-list {
  margin: 0;
  padding-left: 18px;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.6;
}
.btn-outline-primary {
  background: transparent;
  border: 1px dashed var(--brand);
  color: var(--brand);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  margin-top: 6px;
}
.btn-outline-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-outline-primary:hover:not(:disabled) {
  background: var(--brand-a12);
  border-style: solid;
}
.modal-footer {
  padding: var(--space-3) 0;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.modal-footer :deep(.n-button) {
  min-width: 88px;
}
</style>

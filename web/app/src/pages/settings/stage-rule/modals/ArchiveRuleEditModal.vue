<template>
  <n-modal
    :show="visible"
    preset="card"
    class="archive-rule-edit-modal"
    :title="isNew ? '新建自动归档规则' : '编辑自动归档规则'"
    :closable="false"
    style="width: 720px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="er-body">
      <div class="er-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s1') }} <span class="required-mark">*</span></label>
        <n-input v-model:value="draft.name" size="small" :placeholder="t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s9')" :maxlength="50" show-count :class="{ 'input-error': !draft.name.trim() }" />
      </div>

      <div class="er-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s2') }} <span class="required-mark">*</span></label>
        <div class="cond-list">
          <div v-for="(it, idx) in draft.items" :key="idx" class="cond-row">
            <span class="cond-seq">{{ idx + 1 }}</span>
            <ConditionPicker :model-value="it" :catalog="catalog" @update:model-value="onItemUpdate(idx, $event)" />
            <button class="cond-del" type="button" :disabled="draft.items.length <= 1" @click="removeItem(idx)">
              <n-icon :component="TrashOutline" />
            </button>
          </div>
        </div>
        <button class="btn-outline-primary" type="button" :disabled="draft.items.length >= 10" @click="addItem()">
          <n-icon :component="AddOutline" /> 添加条件
        </button>
        <n-input v-model:value="draft.expression" size="small" :placeholder="t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s10')" :class="{ 'input-error': exprInvalid }" style="margin-top: 8px" />
        <p v-if="exprInvalid" class="error-msg">{{ exprErr }}</p>
      </div>

      <div class="er-field">
        <label class="field-label">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s3') }}</label>
        <div class="exec-grid">
          <div class="flow-field">
            <label class="field-label">锁定时长 (天) <span class="required-mark">*</span></label>
            <n-input-number v-model:value="draft.lock_days" size="small" :min="1" :max="365" />
          </div>
          <div class="flow-field">
            <label class="field-label">加时规则 (天)</label>
            <n-input-number v-model:value="draft.extend_days" size="small" :min="0" :max="365" />
          </div>
        </div>
        <div class="scope-row">
          <label class="field-label">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s4') }}</label>
          <n-radio-group :value="draft.effective_scope" @update:value="(v: any) => (draft.effective_scope = v)">
            <n-space>
              <n-radio value="ALL">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s5') }}</n-radio>
              <n-radio value="NEW_ONLY">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s6') }}</n-radio>
            </n-space>
          </n-radio-group>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s7') }}</n-button>
        <n-button size="small" type="primary" :disabled="!canSave || saving" :loading="saving" @click="onSave">{{ t('pages.settings.stage-rule.modals.ArchiveRuleEditModal.s8') }}</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { NModal, NInput, NButton, NIcon, NRadioGroup, NRadio, NSpace, NInputNumber } from 'naive-ui'
import { TrashOutline, AddOutline } from '@vicons/ionicons5'
import ConditionPicker from '../components/ConditionPicker.vue'
import { useExpressionValidator } from '../composables/useExpressionValidator'
import type { ConditionItem, FieldCatalog, ArchiveRule } from '../types'
const { t } = useI18n()

const props = defineProps<{ catalog: FieldCatalog | null }>()
const emit = defineEmits<{
  (e: 'save', rule: ArchiveRule): void
  (e: 'close'): void
}>()

const { clientValidate } = useExpressionValidator()
const saving = ref(false)

const visible = ref(false)
const isNew = ref(false)
const draft = ref<ArchiveRule>(blank())

function blank(): ArchiveRule {
  return {
    id: `archive-${Date.now()}`,
    name: '',
    enabled: true,
    scope: 'NEW_ONLY',
    expression: '',
    items: [emptyItem(1)],
    lock_days: 30,
    extend_days: 0,
    effective_scope: 'ALL',
  }
}
function emptyItem(seq: number): ConditionItem {
  return { item_seq: seq, condition_type: 'DEMAND', field: 'DEMAND_LEVEL', operator: 'EQ', value: null }
}

const exprInfo = computed(() => clientValidate(draft.value.expression, draft.value.items.length))
const exprInvalid = computed(() => !!exprInfo.value && !exprInfo.value.empty && !exprInfo.value.valid)
const exprErr = computed(() => exprInfo.value?.error || '')
const canSave = computed(
  () =>
    draft.value.name.trim() !== '' &&
    !exprInvalid.value &&
    (draft.value.lock_days ?? 0) > 0 &&
    draft.value.items.every((it) => it.field && it.operator && valueOk(it)),
)

function valueOk(it: ConditionItem): boolean {
  const noValue = it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY'
  if (noValue) return true
  if (it.value == null) return false
  if (Array.isArray(it.value)) return it.value.length > 0
  return String(it.value) !== ''
}

function open(rule?: ArchiveRule) {
  isNew.value = !rule
  draft.value = rule ? { ...rule, items: rule.items.map((it) => ({ ...it })) } : blank()
  visible.value = true
}
defineExpose({ open })

function onItemUpdate(idx: number, item: ConditionItem) {
  draft.value.items[idx] = item
  draft.value.items.forEach((it, i) => (it.item_seq = i + 1))
}
function addItem() {
  draft.value.items.push(emptyItem(draft.value.items.length + 1))
}
function removeItem(idx: number) {
  if (draft.value.items.length <= 1) return
  draft.value.items.splice(idx, 1)
  draft.value.items.forEach((it, i) => (it.item_seq = i + 1))
}

function onRequestClose() {
  if (saving.value) return
  visible.value = false
  emit('close')
}
function onSave() {
  if (!canSave.value) return
  saving.value = true
  try {
    emit('save', { ...draft.value, items: draft.value.items.map((it) => ({ ...it })) })
    visible.value = false
    emit('close')
  } finally {
    saving.value = false
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
.exec-grid {
  display: flex;
  gap: var(--space-4);
}
.exec-grid .flow-field {
  flex: 1;
}
.scope-row {
  margin-top: var(--space-3);
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
/* 原型 .btn-outline.primary：实线品牌描边 + 白底，hover 实心品牌底 + 白字 */
.btn-outline-primary {
  background: var(--surface);
  border: 1px solid var(--brand);
  color: var(--brand);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
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
  background: var(--brand);
  border-color: var(--brand);
  color: var(--on-brand);
  box-shadow: var(--shadow-sm);
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
@media (max-width: 600px) {
  .exec-grid {
    flex-direction: column;
    gap: var(--space-3);
  }
}
</style>

<template>
  <n-modal
    :show="visible"
    preset="card"
    class="skip-rule-edit-modal"
    :title="isNew ? '新建自动跳过规则' : '编辑自动跳过规则'"
    :closable="false"
    style="width: 720px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="er-body">
      <div class="er-field">
        <label class="field-label">规则名称 <span class="required-mark">*</span></label>
        <n-input v-model:value="draft.name" size="small" placeholder="请输入规则名称" :maxlength="50" show-count :class="{ 'input-error': !draft.name.trim() }" />
      </div>

      <div class="er-field">
        <label class="field-label">条件设置 <span class="required-mark">*</span></label>
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
        <n-input v-model:value="draft.expression" size="small" placeholder="执行条件表达式，如 1 and 2" :class="{ 'input-error': exprInvalid }" style="margin-top: 8px" />
        <p v-if="exprInvalid" class="error-msg">{{ exprErr }}</p>
      </div>

      <div class="er-field">
        <label class="field-label">执行设置</label>
        <n-radio-group :value="draft.action" @update:value="(v: any) => (draft.action = v)">
          <n-space>
            <n-radio value="SKIP">跳过本阶段</n-radio>
            <n-radio value="APPROVE">直接通过</n-radio>
            <n-radio value="REJECT">直接拒绝</n-radio>
          </n-space>
        </n-radio-group>
        <div class="scope-row">
          <label class="field-label">生效范围</label>
          <n-radio-group :value="draft.scope" @update:value="(v: any) => (draft.scope = v)">
            <n-space>
              <n-radio value="NEW_ONLY">仅新进入</n-radio>
              <n-radio value="ALL">全部</n-radio>
            </n-space>
          </n-radio-group>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">取消</n-button>
        <n-button size="small" type="primary" :disabled="!canSave || saving" :loading="saving" @click="onSave">保存</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NModal, NInput, NButton, NIcon, NRadioGroup, NRadio, NSpace } from 'naive-ui'
import { TrashOutline, AddOutline } from '@vicons/ionicons5'
import ConditionPicker from '../components/ConditionPicker.vue'
import { useExpressionValidator } from '../composables/useExpressionValidator'
import type { ConditionItem, FieldCatalog, SkipRule, SkipAction } from '../types'

const props = defineProps<{ catalog: FieldCatalog | null }>()
const emit = defineEmits<{
  (e: 'save', rule: SkipRule): void
  (e: 'close'): void
}>()

const { clientValidate } = useExpressionValidator()
const saving = ref(false)

const visible = ref(false)
const isNew = ref(false)
const draft = ref<SkipRule>(blank())

function blank(): SkipRule {
  return {
    id: `skip-${Date.now()}`,
    name: '',
    enabled: true,
    scope: 'NEW_ONLY',
    expression: '',
    items: [emptyItem(1)],
    action: 'SKIP' as SkipAction,
  }
}
function emptyItem(seq: number): ConditionItem {
  return { item_seq: seq, condition_type: 'DEMAND', field: 'DEMAND_LEVEL', operator: 'EQ', value: null }
}

const exprInfo = computed(() => clientValidate(draft.value.expression, draft.value.items.length))
const exprInvalid = computed(() => !!exprInfo.value && !exprInfo.value.empty && !exprInfo.value.valid)
const exprErr = computed(() => exprInfo.value?.error || '')
const canSave = computed(() => draft.value.name.trim() !== '' && !exprInvalid.value && draft.value.items.every((it) => it.field && it.operator && valueOk(it)))

function valueOk(it: ConditionItem): boolean {
  const noValue = it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY'
  if (noValue) return true
  if (it.value == null) return false
  if (Array.isArray(it.value)) return it.value.length > 0
  return String(it.value) !== ''
}

function open(rule?: SkipRule) {
  isNew.value = !rule
  draft.value = rule
    ? { ...rule, items: rule.items.map((it) => ({ ...it })) }
    : blank()
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
.btn-outline-primary {
  background: transparent;
  border: 1px dashed var(--brand);
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

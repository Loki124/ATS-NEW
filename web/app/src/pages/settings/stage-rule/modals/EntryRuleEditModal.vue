<!--
  进入条件编辑弹窗（嵌套条件组 UI，对齐 HTML 原型）。
  - 每条规则 = 多个 ConditionGroup（条件组），每个组独立 innerExpression + innerPrompt
  - 整条规则 = 条件组表达式 + 整体未满足提示
  - 保存时拍平为后端 EntryConditionRule（items[] + expression + reject_message）
-->
<template>
  <n-modal
    :show="visible"
    preset="card"
    class="entry-rule-edit-modal"
    :title="isNew ? t('pages.settings.stage-rule.modals.EntryRuleEditModal.s21') : t('pages.settings.stage-rule.modals.EntryRuleEditModal.s34')"
    :closable="false"
    style="width: 760px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
  >
    <div class="er-body">
      <!-- 条件组容器 -->
      <div class="er-field">
        <label class="field-label">
          {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s25') }} <span class="required-mark">*</span>
        </label>
        <div id="entryGroupsContainer">
          <div
            v-for="(group, gi) in draft.groups"
            :key="gi"
            class="group-block"
          >
            <!-- group header: 条件组 N + 添加条件 + 删除组 -->
            <div class="group-header">
              <span class="group-title">
                <n-icon :component="ReorderFourOutline" />
                {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s26') }} {{ gi + 1 }}
              </span>
              <div class="group-actions">
                <a @click="addItem(group)"><n-icon :component="AddOutline" /> {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s1') }}</a>
                <a v-if="canRemoveGroup()" class="danger" @click="removeGroup(gi)">
                  <n-icon :component="TrashOutline" /> {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s27') }}
                </a>
              </div>
            </div>

            <!-- group 内的条件项列表 -->
            <div class="cond-list">
              <div
                v-for="(it, ci) in group.conditions"
                :key="ci"
                class="cond-row"
              >
                <span class="cond-seq">{{ ci + 1 }}</span>
                <ConditionPicker :model-value="it" :catalog="catalog" @update:model-value="onItemUpdate(group, ci, $event)" />
                <button
                  class="cond-del"
                  type="button"
                  :disabled="!canRemoveItemInGroup(group)"
                  @click="removeItem(group, ci)"
                >
                  <n-icon :component="TrashOutline" />
                </button>
              </div>
            </div>

            <!-- 组内表达式 + 组内未满足提示 -->
            <div class="group-inner-row">
              <label class="inner-label">
                {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s22') }}
                <span class="op-expr-help" @click.stop="toggleExprHelp(gi)">
                  <n-icon :component="HelpCircleOutline" />
                  <span v-if="exprHelpOpen === gi" class="op-expr-popover">
                    <strong>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s2') }}<em>(1 or 2) and (3 or 4)</em></strong>
                    <ol>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s3') }}</li>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s4') }}</li>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s5') }}</li>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s6') }}</li>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s7') }}</li>
                      <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s8') }}</li>
                    </ol>
                  </span>
                </span>
              </label>
              <n-input
                v-model:value="group.innerExpression"
                size="small"
                :placeholder="t('pages.settings.stage-rule.modals.EntryRuleEditModal.s23')"
                :class="{ 'input-error': innerExprError(group).empty === false && !innerExprError(group).valid }"
              />
              <p v-if="innerExprError(group).empty === false && !innerExprError(group).valid" class="error-msg">
                {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s28') }}{{ innerExprError(group).error }}
              </p>
            </div>
            <div class="group-inner-row">
              <label class="inner-label">{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s9') }}</label>
              <n-input
                v-model:value="group.innerPrompt"
                size="small"
                :placeholder="t('pages.settings.stage-rule.modals.EntryRuleEditModal.s19')"
              />
            </div>
          </div>
        </div>

        <!-- 添加条件组按钮 -->
        <a class="add-link" :class="{ 'add-link--disabled': !canAddGroup }" @click="addGroup()">
          <n-icon :component="AddOutline" /> {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s29') }}
        </a>
        <p v-if="!canAddGroup" class="field-hint">{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s30') }} {{ AR_MAX_GROUPS }} {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s31') }}</p>
      </div>

      <!-- 条件组表达式（整条规则） -->
      <div class="er-field">
        <label class="field-label">
          {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s32') }} <span class="required-mark">*</span>
          <span class="op-expr-help" @click.stop="toggleExprHelp(-1)">
            <n-icon :component="HelpCircleOutline" />
            <span v-if="exprHelpOpen === -1" class="op-expr-popover">
              <strong>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s10') }}<em>(1 or 2) and (3 or 4)</em></strong>
              <ol>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s11') }}</li>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s12') }}</li>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s13') }}</li>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s14') }}</li>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s15') }}</li>
                <li>{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s16') }}</li>
              </ol>
            </span>
          </span>
        </label>
        <n-input
          v-model:value="draft.groupExpression"
          size="small"
          :placeholder="t('pages.settings.stage-rule.modals.EntryRuleEditModal.s24')"
          :class="{ 'input-error': !groupError.empty && !groupError.valid }"
        />
        <p v-if="!groupError.empty && !groupError.valid" class="error-msg">
          {{ groupError.error }}
        </p>
      </div>

      <!-- 整体未满足提示 -->
      <div class="er-field">
        <label class="field-label">
          {{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s33') }} <span class="required-mark">*</span>
        </label>
        <n-input
          v-model:value="draft.overallPrompt"
          type="textarea"
          size="small"
          :placeholder="t('pages.settings.stage-rule.modals.EntryRuleEditModal.s20')"
          :maxlength="500"
          show-count
          :autosize="{ minRows: 2, maxRows: 4 }"
        />
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s17') }}</n-button>
        <n-button size="small" type="primary" :disabled="hasError || saving" :loading="saving" @click="onSave">{{ t('pages.settings.stage-rule.modals.EntryRuleEditModal.s18') }}</n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { NModal, NInput, NButton, NIcon } from 'naive-ui'
import {
  AddOutline, TrashOutline, HelpCircleOutline, ReorderFourOutline,
} from '@vicons/ionicons5'
import ConditionPicker from '../components/ConditionPicker.vue'
import { useEntryRuleEditor } from '../composables/useEntryRuleEditor'
import { AR_MAX_GROUPS } from '../constants'
import type { ConditionItem, EntryConditionRule, FieldCatalog, ConditionGroup } from '../types'
const { t } = useI18n()

const props = defineProps<{ catalog: FieldCatalog | null }>()
const emit = defineEmits<{
  (e: 'save', rule: EntryConditionRule): void
  (e: 'close'): void
}>()

const {
  visible, isNew, draft,
  groupError, itemError, innerExprError, hasError,
  canAddGroup, canRemoveGroup, canRemoveItemInGroup,
  open, close, addGroup, removeGroup, addItem, removeItem,
  commit,
} = useEntryRuleEditor()
const saving = ref(false)
const exprHelpOpen = ref<number | null>(null)

function onItemUpdate(g: ConditionGroup, idx: number, item: ConditionItem) {
  g.conditions[idx] = item
}

function toggleExprHelp(gi: number) {
  exprHelpOpen.value = exprHelpOpen.value === gi ? null : gi
}

defineExpose({ open })

function onRequestClose() {
  if (saving.value) return
  close()
  emit('close')
}

function onSave() {
  if (hasError.value) return
  saving.value = true
  try {
    emit('save', commit())
    close()
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
.help-icon,
.op-expr-help {
  position: relative;
  display: inline-flex;
  align-items: center;
  color: var(--ink-faint);
  font-size: 12px;
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-out);
  margin-left: 4px;
  vertical-align: middle;
}
.op-expr-help:hover { color: var(--brand); }
.op-expr-popover {
  position: absolute;
  bottom: calc(100% + 10px);
  left: -10px;
  width: 340px;
  background: var(--ink);
  color: var(--g6);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-elevated);  /* 原 var(--shadow-elev) 未定义，阴影被丢弃 */
  padding: 11px 13px;
  z-index: 30;
  font-size: var(--fs-12);
  line-height: 1.65;
  text-align: left;
  font-weight: 400;
  cursor: default;
  animation: erFadeIn 0.15s ease-out;
}
.op-expr-popover::before {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 18px;
  width: 8px;
  height: 8px;
  background: var(--ink);
  transform: rotate(45deg);
  border-radius: 1px;
}
.op-expr-popover strong { color: var(--surface); }
.op-expr-popover em { font-style: normal; color: var(--brand); }
.op-expr-popover ol { margin: 2px 0 0; padding-left: 16px; color: var(--g6); }
.op-expr-popover li { margin-bottom: 1px; padding-left: 2px; }
@keyframes erFadeIn { from { opacity: 0; } to { opacity: 1; } }

/* ===== 条件组容器（HTML 原型 .group-block） ===== */
.group-block {
  background: var(--g1);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  margin-bottom: var(--space-3);
  border: 1px solid var(--g2);
}
.group-block:last-child { margin-bottom: 0; }
.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.group-title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.group-actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}
.group-actions a {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  text-decoration: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  transition: color var(--duration-fast) var(--ease-out);
}
.group-actions a:hover { color: var(--brand); }
.group-actions a.danger:hover { color: var(--c-error); }

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

.group-inner-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-top: 8px;
}
.group-inner-row + .group-inner-row { margin-top: 6px; }
.inner-label {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  white-space: nowrap;
  min-width: 88px;
}
.group-inner-row :deep(.n-input) {
  flex: 1;
}

/* ===== 添加条件组链接 ===== */
.add-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--brand);
  font-size: var(--fs-12);
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  margin-top: 10px;
  transition: color var(--duration-fast) var(--ease-out);
}
.add-link:hover { color: var(--brand-hover); }
.add-link--disabled {
  color: var(--ink-faint);
  cursor: not-allowed;
  pointer-events: none;
}

/* ===== 错误 / 提示 ===== */
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

/* ===== Footer ===== */
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
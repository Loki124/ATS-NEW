<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ resourceLabel }}表单设置</h1>
        <p class="page-subtitle">
          配置{{ resourceLabel }}表单包含的字段与必填规则，右侧实时预览填写效果。
          字段来源于动态字段配置的「{{ resource }}」资源；可拖拽分组与字段调整展示顺序。
        </p>
      </div>
      <div class="page-header-actions">
        <n-button quaternary size="small" :loading="loading" @click="loadFields">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新字段
        </n-button>
        <n-button tertiary size="small" :disabled="loading" @click="onReset">
          <template #icon><n-icon :component="ReloadOutline" /></template>
          重置默认
        </n-button>
      </div>
    </div>

    <div class="page-body">
      <div class="sr-grid">
        <!-- 左：配置（按分组 + 双层拖拽） -->
        <section class="glass-card sr-config">
          <header class="sr-panel-head">
            <h2 class="sr-panel-title">{{ resourceLabel }}字段</h2>
            <span class="sr-save-hint" :class="{ saved, saving }">
              {{ saving ? '保存中…' : saved ? '已自动保存' : '未保存' }}
            </span>
          </header>

          <n-spin :show="loading">
            <div class="sr-config-body">
              <n-alert
                v-if="error"
                type="error"
                :bordered="false"
                class="sr-alert"
              >
                <template #header>
                  <span>加载字段失败</span>
                  <n-button size="tiny" tertiary class="sr-alert-retry" @click="loadFields">重试</n-button>
                </template>
                {{ error }}
              </n-alert>

              <n-empty
                v-else-if="!allFields.length && !loading"
                :description="`暂无可选字段，请先在「${resourceLabel}字段管理」中配置 ${resource} 资源字段`"
                class="sr-empty"
              />

              <template v-else>
                <VueDraggable
                  v-model="groupBuckets"
                  handle=".group-drag-handle"
                  :animation="180"
                  ghost-class="sr-ghost"
                  class="sr-groups"
                  @end="onGroupDragEnd"
                >
                  <section
                    v-for="grp in groupBuckets"
                    :key="grp.key"
                    class="sr-group"
                  >
                    <header class="sr-group-head">
                      <n-icon
                        v-if="groupBuckets.length > 1"
                        class="sr-drag-handle group-drag-handle"
                        :component="ReorderThreeOutline"
                        size="18"
                      />
                      <span v-else class="sr-drag-handle-placeholder" />
                      <h3 class="sr-group-title">
                        {{ grp.group?.name || '未分组' }}
                      </h3>
                      <n-tag size="small" :bordered="false" class="sr-group-count">
                        {{ grp.fields.length }} 字段
                      </n-tag>
                    </header>

                    <VueDraggable
                      v-if="grp.fields.length"
                      v-model="grp.fields"
                      handle=".field-drag-handle"
                      :animation="160"
                      ghost-class="sr-ghost"
                      class="sr-fields"
                      @end="(evt: SortableEvent) => onFieldDragEnd(grp, evt)"
                    >
                      <div
                        v-for="m in grp.fields"
                        :key="m.field.id || m.field.fieldKey"
                        class="sr-field-row"
                        :class="{ 'sr-field-row--dimmed': m.field.isVisible === false }"
                      >
                        <n-icon
                          class="sr-drag-handle field-drag-handle"
                          :component="MenuOutline"
                          size="16"
                          :title="m.field.isVisible === false
                            ? '该字段在动态字段定义层为隐藏，仍可拖拽调整顺序'
                            : '拖拽调整顺序'"
                        />
                        <div class="sr-field-meta">
                          <span class="sr-field-label">{{ m.field.label }}</span>
                          <span v-if="m.field.isVisible === false" class="sr-tag-hidden">定义层隐藏</span>
                          <span class="sr-type-tag">{{ fieldTypeLabel(m.field.fieldType) }}</span>
                        </div>
                        <div class="sr-field-toggles">
                          <n-switch
                            :value="m.enabled"
                            size="small"
                            @update:value="setEnabled(m.field.fieldKey, $event)"
                          />
                          <span class="sr-toggle-label">显示</span>
                          <n-switch
                            :value="m.required"
                            size="small"
                            :disabled="!m.enabled"
                            @update:value="setRequired(m.field.fieldKey, $event)"
                          />
                          <span class="sr-toggle-label" :class="{ disabled: !m.enabled }">必填</span>
                        </div>
                      </div>
                    </VueDraggable>
                    <div v-else class="sr-group-empty">
                      <n-empty size="small" description="暂无字段" />
                    </div>
                  </section>
                </VueDraggable>
              </template>
            </div>
          </n-spin>
        </section>

        <!-- 右：预览（按分组 + 启用字段） -->
        <section class="glass-card sr-preview">
          <header class="sr-panel-head">
            <h2 class="sr-panel-title">表单预览</h2>
            <span class="sr-preview-count">{{ enabledFields.length }} 个字段</span>
          </header>

          <div class="sr-preview-body">
            <n-empty
              v-if="!enabledFields.length"
              description="左侧开启字段后，这里实时展示填写效果"
              class="sr-empty"
            />
            <div v-else class="sr-form">
              <div
                v-for="grp in previewGroups"
                :key="grp.key"
                class="sr-form-group"
              >
                <div class="sr-form-group-title">
                  {{ grp.group?.name || '未分组' }}
                  <span class="sr-form-group-count">{{ grp.fields.length }}</span>
                </div>
                <div class="sr-form-grid">
                  <div
                    v-for="m in grp.fields"
                    :key="m.field.fieldKey"
                    class="sr-form-item"
                    :class="{ 'sr-form-item--full': isFullWidth(m.field) }"
                  >
                    <label class="sr-form-label">
                      {{ m.field.label }}
                      <span v-if="m.required" class="sr-req">*</span>
                    </label>

                    <!-- BOOLEAN -->
                    <n-switch v-if="m.field.fieldType === 'BOOLEAN'" disabled />
                    <!-- 单选类 -->
                    <n-select
                      v-else-if="isSingleChoice(m.field.fieldType)"
                      disabled
                      :options="selectOptions(m.field)"
                      placeholder="请选择"
                    />
                    <!-- 多选类 -->
                    <n-select
                      v-else-if="isMultiChoice(m.field.fieldType)"
                      multiple
                      disabled
                      :options="selectOptions(m.field)"
                      placeholder="请选择"
                    />
                    <!-- 附件 -->
                    <div v-else-if="m.field.fieldType === 'ATTACHMENT'" class="sr-attachment">
                      <AttachmentUploader :model-value="[]" :disabled="true" />
                    </div>
                    <!-- 组合字段 -->
                    <div v-else-if="m.field.fieldType === 'COMPOSITE'" class="sr-composite">
                      <CompositeFieldCard :field="m.field" :model-value="{}" mode="display" />
                    </div>
                    <!-- 多行文本 -->
                    <n-input
                      v-else-if="m.field.fieldType === 'MULTILINE_TEXT'"
                      type="textarea"
                      disabled
                      :rows="3"
                      :placeholder="m.field.placeholder || ('请输入' + m.field.label)"
                    />
                    <!-- 行政区划 -->
                    <RegionCascader
                      v-else-if="isRegionType(m.field.fieldType)"
                      :level="(m.field.regionLevel || 'DISTRICT') as RegionLevelValue"
                      :with-country="!!m.field.withCountry"
                      :value="null"
                      :disabled="true"
                    />
                    <!-- 日期型 -->
                    <NDatePicker
                      v-else-if="isDateFieldType(m.field.fieldType)"
                      disabled
                      :type="(datePickerType(m.field.fieldType, m.field.dateFormat) as any)"
                      clearable
                    />
                    <!-- 富文本 -->
                    <RichTextEditor
                      v-else-if="m.field.fieldType === 'RICH_TEXT'"
                      :model-value="''"
                      :disabled="true"
                    />
                    <!-- 数字类: 值 + 单位 -->
                    <n-space v-else-if="m.field.fieldType === 'NUMBER'" align="center" :size="8">
                      <n-input
                        disabled
                        :placeholder="m.field.placeholder || ('请输入' + m.field.label)"
                      />
                      <n-text v-if="(m.field.validation as FieldValidation | null)?.unit" depth="3">
                        {{ (m.field.validation as FieldValidation | null)?.unit }}
                      </n-text>
                    </n-space>
                    <!-- URL: 链接 (预览只读) -->
                    <n-a
                      v-else-if="m.field.fieldType === 'URL'"
                      :href="undefined"
                      target="_blank"
                      class="sr-url-preview"
                    >
                      {{ m.field.placeholder || 'https://example.com' }}
                    </n-a>
                    <!-- 默认：文本/电话/邮箱/证件 等 -->
                    <n-input
                      v-else
                      disabled
                      :placeholder="m.field.placeholder || ('请输入' + m.field.label)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted, watch } from 'vue'
import { NButton, NIcon, NSwitch, NSpin, NAlert, NEmpty, NInput, NSelect, NDatePicker, NTag, NText, NSpace, NA, useMessage } from 'naive-ui'
import RichTextEditor from '@/components/RichTextEditor.vue'
import {
  RefreshOutline,
  ReloadOutline,
  ReorderThreeOutline,
  MenuOutline,
} from '@vicons/ionicons5'
import { VueDraggable } from 'vue-draggable-plus'
import type { SortableEvent } from 'sortablejs'
import {
  listFields,
  listGroups,
  updateFieldOrder,
  updateGroupOrder,
  extractApiError,
  type FieldDefinition,
  type FieldGroup,
  type FieldType,
  type FieldValidation,
  type RegionLevelValue,
  FIELD_TYPE_LABEL,
  isDateFieldType, datePickerType,
  isRegionFieldType,
} from '../../api/dynamic-field'
import {
  fetchFormConfig,
  saveFormConfig,
  resetFormConfig,
  defaultFormConfig,
  mergeFields,
  groupFieldsByGroup,
  UNGROUPED_GROUP_CODE,
  type FormConfig,
  type FormFieldConfig,
  type MergedResumeField,
  type FieldGroupBucket,
} from '../../api/form-config';
import RegionCascader from '../../components/RegionCascader.vue';
import AttachmentUploader from '@/components/AttachmentUploader.vue';
import CompositeFieldCard from '@/components/CompositeFieldCard.vue';

const props = defineProps<{
  /** 动态字段资源：'Demand' 招聘需求 / 'Position' 职位信息 */
  resource: 'Demand' | 'Position'
}>()

const { t } = useI18n()

const resourceLabel = computed(() => (props.resource === 'Demand' ? '招聘需求' : '职位信息'))

const message = useMessage()

const allFields = ref<FieldDefinition[]>([])
const allGroups = ref<FieldGroup[]>([])
const loading = ref(false)
const error = ref('')
const saved = ref(true)
const saving = ref(false)
const ready = ref(false)
const dirty = ref(false)
const config = ref<FormConfig>(defaultFormConfig())

const groupBuckets = ref<FieldGroupBucket[]>([])
const fieldReorderRunning = ref(false)
const groupReorderRunning = ref(false)
const lastReorderError = ref('')

function fieldTypeLabel(t: FieldType): string {
  return FIELD_TYPE_LABEL[t] ?? t
}

function isSingleChoice(t: FieldType): boolean {
  return t === 'SELECT' || t === 'LIST_SINGLE' || t === 'PERSON' || t === 'DEPARTMENT'
}
function isMultiChoice(t: FieldType): boolean {
  return t === 'MULTISELECT' || t === 'LIST_MULTI'
}
function isRegionType(t: FieldType): boolean {
  return isRegionFieldType(t)
}
function selectOptions(field: FieldDefinition) {
  return (field.options || []).map((o) => ({ label: o.label, value: o.value }))
}

function isFullWidth(field: FieldDefinition): boolean {
  return field.fieldType === 'TEXT'
    || field.fieldType === 'ATTACHMENT'
    || field.fieldType === 'ADDRESS'
    || field.fieldType === 'REGION'
    || field.fieldType === 'RICH_TEXT'
}

function ensureCoverage() {
  const existing = new Map(config.value.fields.map((f) => [f.fieldKey, f]))
  config.value.fields = allFields.value.map((f) => {
    const c = existing.get(f.fieldKey)
    return c ?? { fieldKey: f.fieldKey, enabled: f.isVisible, required: f.isRequired }
  })
}

async function loadFields() {
  loading.value = true
  error.value = ''
  try {
    const fields = await listFields(props.resource)
    allFields.value = fields
    ensureCoverage()
    try {
      allGroups.value = await listGroups(props.resource)
    } catch {
      allGroups.value = []
    }
  } catch (e: any) {
    error.value = e?.message || '请求动态字段失败，请检查网络或登录状态'
  } finally {
    loading.value = false
  }
}

function findEntry(key: string): FormFieldConfig | undefined {
  return config.value.fields.find((f) => f.fieldKey === key)
}
function setEnabled(key: string, v: boolean) {
  const e = findEntry(key)
  if (!e) return
  e.enabled = v
  if (!v) e.required = false
  dirty.value = true
}
function setRequired(key: string, v: boolean) {
  const e = findEntry(key)
  if (!e) return
  e.required = v
  dirty.value = true
}

async function onReset() {
  const cfg = await resetFormConfig(props.resource)
  config.value = cfg
  ensureCoverage()
  dirty.value = false
}

watch(
  config,
  async (v) => {
    if (!ready.value || !dirty.value) return
    saving.value = true
    saved.value = false
    try {
      await saveFormConfig(props.resource, v)
      saved.value = true
    } catch (e: any) {
      saved.value = false
      message.error('保存失败：' + extractApiError(e))
    } finally {
      saving.value = false
    }
  },
  { deep: true },
)

const merged = computed<MergedResumeField[]>(() => mergeFields(allFields.value, config.value))
const enabledFields = computed(() => merged.value.filter((m) => m.enabled))

watch(
  [merged, () => config.value.groupOrder, allGroups],
  ([m, go, groups]) => {
    const next = groupFieldsByGroup(m, go, groups as FieldGroup[])
    if (groupBuckets.value.length === 0) {
      groupBuckets.value = next
      return
    }
    const byKey = new Map(groupBuckets.value.map((b) => [b.key, b]))
    const rebuilt: FieldGroupBucket[] = []
    for (const nb of next) {
      const existing = byKey.get(nb.key)
      if (existing) {
        existing.fields = nb.fields
        existing.group = nb.group
        rebuilt.push(existing)
        byKey.delete(nb.key)
      } else {
        rebuilt.push(nb)
      }
    }
    groupBuckets.value = rebuilt
  },
  { immediate: true, deep: true },
)

const previewGroups = computed(() =>
  groupBuckets.value
    .map((g) => ({
      key: g.key,
      group: g.group,
      fields: g.fields.filter((f) => f.enabled),
    }))
    .filter((g) => g.fields.length > 0),
)

async function onGroupDragEnd() {
  if (groupBuckets.value.length <= 1) return

  const ordered = groupBuckets.value.filter((g) => g.key !== UNGROUPED_GROUP_CODE)
  if (!ordered.length) return

  const beforeOrder = new Map(allGroups.value.map((g) => [g.id, g.orderIndex]))
  const beforeGroupOrder = [...(config.value.groupOrder ?? [])]

  config.value.groupOrder = ordered.map((g) => g.key)
  dirty.value = true

  const step = 10
  const updates: Array<{ id: string; orderIndex: number; moduleId: string }> = []
  ordered.forEach((g, i) => {
    if (!g.group?.id) return
    const moduleId = g.group.moduleId || g.group.module?.id || ''
    updates.push({ id: g.group.id, orderIndex: (i + 1) * step, moduleId })
  })
  if (!updates.length) return

  const byId = new Map(allGroups.value.map((g) => [g.id, g]))
  for (const u of updates) {
    const g = byId.get(u.id)
    if (g) g.orderIndex = u.orderIndex
  }

  groupReorderRunning.value = true
  lastReorderError.value = ''
  try {
    const results = await Promise.allSettled(
      updates.map((u) => updateGroupOrder(props.resource, u.id, u.orderIndex, u.moduleId)),
    )
    const failed = results.filter((r) => r.status === 'rejected') as PromiseRejectedResult[]
    if (failed.length) {
      for (const [id, oldOrder] of beforeOrder.entries()) {
        const g = byId.get(id)
        if (g) g.orderIndex = oldOrder
      }
      config.value.groupOrder = beforeGroupOrder
      const firstReason = failed[0]?.reason
      lastReorderError.value = `分组排序保存失败 (${failed.length}/${updates.length}), 已回滚`
      console.error('[FormSettings] group reorder failed', failed)
      message.error(lastReorderError.value + (firstReason ? `: ${extractApiError(firstReason)}` : ''))
    }
  } catch (e: any) {
    for (const [id, oldOrder] of beforeOrder.entries()) {
      const g = byId.get(id)
      if (g) g.orderIndex = oldOrder
    }
    config.value.groupOrder = beforeGroupOrder
    lastReorderError.value = e?.message || '分组排序保存异常'
    message.error(lastReorderError.value)
  } finally {
    groupReorderRunning.value = false
  }
}

async function onFieldDragEnd(grp: FieldGroupBucket, evt: SortableEvent) {
  if (evt.oldIndex === evt.newIndex) return
  if (!grp.fields.length) return

  const groupIndex = groupBuckets.value.findIndex((g) => g.key === grp.key)
  if (groupIndex < 0) return

  const newMergedOrder: MergedResumeField[] = []
  for (const g of groupBuckets.value) {
    for (const m of g.fields) newMergedOrder.push(m)
  }

  const step = 10
  const updates: Array<{ id: string; orderIndex: number }> = []
  for (let i = 0; i < newMergedOrder.length; i++) {
    const m = newMergedOrder[i]
    if (!m.field.id) continue
    updates.push({ id: m.field.id, orderIndex: (i + 1) * step })
  }
  if (!updates.length) return

  const beforeOrder = new Map(allFields.value.map((f) => [f.id, f.orderIndex]))
  const byId = new Map(allFields.value.map((f) => [f.id, f]))
  for (const u of updates) {
    const f = byId.get(u.id)
    if (f) f.orderIndex = u.orderIndex
  }

  fieldReorderRunning.value = true
  lastReorderError.value = ''
  try {
    const results = await Promise.allSettled(
      updates.map((u) => updateFieldOrder(props.resource, u.id, u.orderIndex)),
    )
    const failed = results.filter((r) => r.status === 'rejected') as PromiseRejectedResult[]
    if (failed.length) {
      for (const [id, oldOrder] of beforeOrder.entries()) {
        const f = byId.get(id)
        if (f) f.orderIndex = oldOrder
      }
      const firstReason = failed[0]?.reason
      lastReorderError.value = `字段排序保存失败 (${failed.length}/${updates.length}), 已回滚`
      console.error('[FormSettings] field reorder failed', failed)
      message.error(lastReorderError.value + (firstReason ? `: ${extractApiError(firstReason)}` : ''))
    }
  } catch (e: any) {
    for (const [id, oldOrder] of beforeOrder.entries()) {
      const f = byId.get(id)
      if (f) f.orderIndex = oldOrder
    }
    lastReorderError.value = e?.message || '字段排序保存异常'
    message.error(lastReorderError.value)
  } finally {
    fieldReorderRunning.value = false
  }
}

onMounted(async () => {
  await loadFields()
  await loadConfigIntoState()
})

async function loadConfigIntoState() {
  try {
    const cfg = await fetchFormConfig(props.resource)
    config.value = cfg
    ensureCoverage()
  } catch {
    // 拉取失败：保留默认配置，页面仍可编辑（变更后会写回后端）
  } finally {
    ready.value = true
  }
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sr-grid {
  display: grid;
  grid-template-columns: minmax(360px, 460px) 1fr;
  gap: var(--space-4);
  align-items: start;
}
@media (min-width: 1024px) {
  .sr-grid {
    height: 100%;
    align-items: stretch;
  }
  .sr-config,
  .sr-preview {
    overflow-y: auto;
    height: 100%;
    min-height: 0;
  }
}
@media (max-width: 1024px) {
  .sr-grid { grid-template-columns: 1fr; }
}

.sr-config,
.sr-preview { padding: var(--space-4); }

.sr-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.sr-panel-title {
  margin: 0;
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
}
.sr-save-hint {
  font-size: var(--text-meta);
  color: var(--c-warning);
}
.sr-save-hint.saved { color: var(--c-success); }
.sr-save-hint.saving { color: var(--c-info); }

.sr-config-body { min-height: 120px; }

.sr-alert { margin-bottom: var(--space-3); }
.sr-alert-retry { margin-left: var(--space-3); vertical-align: middle; }
.sr-empty { padding: var(--space-12) 0; }

/* === 分组（玻璃卡片嵌套 + 双层拖拽） === */
.sr-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.sr-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
}
.sr-group-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm, 4px);
  background: var(--g1);
  transition: background var(--duration-base, .2s) var(--ease-out, ease);
}
.sr-group:hover .sr-group-head { background: var(--brand-soft); }
.sr-group-title {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: var(--text-meta);
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sr-group-count {
  flex-shrink: 0;
  background: var(--c-info-soft);
  color: var(--c-info);
}
.sr-group-empty {
  padding: var(--space-3) 0;
}

.sr-drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  color: var(--ink-faint);
  cursor: grab;
  border-radius: var(--radius-sm, 4px);
  transition: background var(--duration-base, .2s) var(--ease-out, ease),
              color var(--duration-base, .2s) var(--ease-out, ease);
}
.sr-drag-handle:hover {
  background: var(--brand-tint);
  color: var(--brand);
}
.sr-drag-handle:active { cursor: grabbing; }
.sr-drag-handle-placeholder {
  display: inline-block;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}
.group-drag-handle { }
.field-drag-handle { }

.sr-ghost {
  opacity: 0.4;
  background: var(--brand-soft);
  border: 1px dashed var(--brand);
  border-radius: var(--radius-md);
}

/* === 字段行 === */
.sr-fields {
  display: flex;
  flex-direction: column;
}
.sr-field-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-hairline);
}
.sr-field-row:last-child { border-bottom: none; }
.sr-field-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}
.sr-field-label {
  font-size: var(--text-small);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sr-type-tag {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--c-info-soft);
  color: var(--c-info);
  font-size: var(--text-meta);
  white-space: nowrap;
}
.sr-field-toggles {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}
.sr-toggle-label {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.sr-toggle-label.disabled { color: var(--ink-faint); }

.sr-field-row--dimmed .sr-field-label,
.sr-field-row--dimmed .sr-type-tag,
.sr-field-row--dimmed .sr-toggle-label {
  opacity: 0.55;
}
.sr-tag-hidden {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0 var(--space-2);
  font-size: var(--text-meta, 12px);
  line-height: 18px;
  color: var(--ink-faint);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm, 4px);
}

/* === 预览面板 === */
.sr-preview-count { font-size: var(--text-meta); color: var(--ink-faint); }
.sr-form { display: flex; flex-direction: column; gap: var(--space-4); }
.sr-form-group { display: flex; flex-direction: column; gap: var(--space-2); }
.sr-form-group-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-meta);
  font-weight: 600;
  color: var(--ink-soft);
  letter-spacing: 0.02em;
}
.sr-form-group-count {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--g1);
  color: var(--ink-faint);
  font-size: var(--text-meta);
  font-weight: 400;
}
.sr-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  column-gap: var(--space-4);
  row-gap: var(--space-3);
  align-items: start;
}
@media (max-width: 720px) {
  .sr-form-grid { grid-template-columns: 1fr; }
}
.sr-form-item { display: flex; flex-direction: column; gap: var(--space-1); }
.sr-form-item--full { grid-column: 1 / -1; }
.sr-form-label { font-size: var(--text-small); color: var(--ink-soft); }
.sr-req { color: var(--c-error); margin-left: 2px; }
.sr-attachment {
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  text-align: center;
  color: var(--ink-faint);
  font-size: var(--text-small);
}
.sr-composite {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}
</style>

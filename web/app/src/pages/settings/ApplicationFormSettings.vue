<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="sr-title-row">
          <h1 class="page-title">申请表和登记表设置</h1>
          <n-tag :bordered="false" type="primary" size="small" round>社招</n-tag>
        </div>
        <p class="page-subtitle">
          配置候选人投递「申请表」与入职「登记表」包含的多套表单、字段与必填规则，右侧实时预览候选人填写效果。
          字段来源于动态字段模块的「Candidate」资源。
        </p>
      </div>
      <div class="page-header-actions">
        <n-button type="primary" size="small" :loading="creating" @click="onAddForm">
          <template #icon><n-icon :component="AddOutline" /></template>
          添加申请表
        </n-button>
      </div>
    </div>

    <div class="page-body">
      <div class="sr-grid">
        <!-- 左：表单列表 -->
        <section class="glass-card sr-list">
          <header class="sr-panel-head">
            <h2 class="sr-panel-title">表单列表</h2>
            <span class="sr-count">{{ forms.length }} 套</span>
          </header>

          <n-spin :show="loading">
            <n-empty
              v-if="!loading && !forms.length"
              description="暂无表单，点击右上角「添加申请表」创建第一套"
              class="sr-empty"
            />
            <div v-else class="sr-list-body">
              <button
                v-for="f in forms"
                :key="f.id"
                type="button"
                class="sr-form-card"
                :class="{ active: selectedId === f.id }"
                @click="selectForm(f.id)"
              >
                <div class="sr-form-card-top">
                  <span class="sr-form-card-name">{{ f.name }}</span>
                  <n-tag
                    :bordered="false"
                    size="tiny"
                    :type="f.formType === 'application' ? 'info' : 'default'"
                  >
                    {{ f.formType === 'application' ? '申请表' : '登记表' }}
                  </n-tag>
                </div>
                <div class="sr-form-card-meta">
                  {{ f.fields.filter((x) => x.enabled).length }} 个字段启用
                  <span v-if="f.departments.length">· {{ f.departments.length }} 个部门</span>
                </div>
                <div class="sr-form-card-actions" @click.stop>
                  <n-button size="tiny" tertiary @click="startEdit(f.id)">编辑</n-button>
                  <n-button
                    size="tiny"
                    tertiary
                    type="error"
                    :loading="deletingId === f.id"
                    @click="onDelete(f)"
                  >
                    删除
                  </n-button>
                </div>
              </button>
            </div>
          </n-spin>
        </section>

        <!-- 右：预览 / 编辑 -->
        <section class="glass-card sr-preview">
          <div class="sr-preview-scroll">
            <template v-if="!selected && !editing">
              <n-empty description="从左侧选择一套表单查看预览，或新建表单" class="sr-empty" />
            </template>

            <template v-else-if="!editing">
              <header class="sr-panel-head">
                <div>
                  <h2 class="sr-panel-title">{{ selected.name }}</h2>
                  <span class="sr-preview-sub">
                    {{ selected.formType === 'application' ? '申请表' : '登记表' }}
                    <span v-if="selected.departments.length">· 适用 {{ selected.departments.join('、') }}</span>
                  </span>
                </div>
                <n-button size="small" tertiary @click="startEdit(selected.id)">
                  <template #icon><n-icon :component="CreateOutline" /></template>
                  编辑
                </n-button>
              </header>

              <div class="sr-preview-body">
                <div v-if="!enabledFields.length" class="sr-preview-empty">
                  该表单尚未开启任何字段
                </div>
                <div v-for="grp in groupedEnabled" :key="grp.name" class="sr-form-group">
                  <div class="sr-form-group-title">{{ grp.name }}</div>
                  <div class="sr-form-grid">
                    <div
                      v-for="m in grp.items"
                      :key="m.field.fieldKey"
                      class="sr-form-item"
                      :class="{ 'sr-form-item--full': isFullWidth(m.field) }"
                    >
                      <label class="sr-form-label">
                        {{ m.label }}
                        <span v-if="m.required" class="sr-req">*</span>
                      </label>
                      <n-switch v-if="m.fieldType === 'BOOLEAN'" disabled />
                      <n-select
                        v-else-if="isSingleChoice(m.fieldType)"
                        disabled
                        :options="selectOptions(m)"
                        placeholder="请选择"
                      />
                      <n-select
                        v-else-if="isMultiChoice(m.fieldType)"
                        multiple
                        disabled
                        :options="selectOptions(m)"
                        placeholder="请选择"
                      />
                      <div v-else-if="m.fieldType === 'ATTACHMENT'" class="sr-attachment">
                        点击上传附件
                      </div>
                      <n-input
                        v-else-if="m.fieldType === 'MULTILINE_TEXT'"
                        type="textarea"
                        disabled
                        :rows="3"
                        :placeholder="m.placeholder || ('请输入' + m.label)"
                      />
                      <n-input
                        v-else
                        disabled
                        :placeholder="m.placeholder || ('请输入' + m.label)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <template v-else>
              <header class="sr-panel-head">
                <h2 class="sr-panel-title">{{ draft.id ? '编辑表单' : '新建表单' }}</h2>
                <span class="sr-save-hint" :class="{ saved, saving }">
                  {{ saving ? '保存中…' : saved ? '已保存' : '未保存' }}
                </span>
              </header>

              <n-spin :show="saving">
                <div class="sr-edit-body">
                  <div class="sr-edit-row">
                    <label class="sr-edit-label">表单名称</label>
                    <n-input
                      v-model:value="draft.name"
                      placeholder="如：猎头更新简历登记表"
                      :maxlength="128"
                    />
                  </div>

                  <div class="sr-edit-row">
                    <label class="sr-edit-label">表单类型</label>
                    <n-radio-group v-model:value="draft.formType">
                      <n-radio value="registration">登记表</n-radio>
                      <n-radio value="application">申请表</n-radio>
                    </n-radio-group>
                  </div>

                  <div class="sr-edit-row">
                    <label class="sr-edit-label">应用部门</label>
                    <n-select
                      v-model:value="draft.departments"
                      multiple
                      filterable
                      tag
                      placeholder="选择或输入部门"
                      :options="deptOptions"
                    >
                      <template #empty>可直接输入部门名称后按回车添加</template>
                    </n-select>
                  </div>

                  <div class="sr-edit-row">
                    <label class="sr-edit-label">填写模式</label>
                    <n-radio-group v-model:value="draft.mode">
                      <n-radio value="default">默认</n-radio>
                      <n-radio value="step">分步</n-radio>
                    </n-radio-group>
                  </div>

                  <div class="sr-edit-fields">
                    <div class="sr-edit-fields-head">字段配置（按分组）</div>
                    <div
                      v-for="grp in groupedAllFields"
                      :key="grp.name"
                      class="sr-edit-group"
                    >
                      <div class="sr-form-group-title">{{ grp.name }}</div>
                      <div
                        v-for="item in grp.items"
                        :key="item.fieldKey"
                        class="sr-field-row"
                      >
                        <div class="sr-field-meta">
                          <span class="sr-field-label">{{ item.label }}</span>
                          <span class="sr-type-tag">{{ fieldTypeLabel(item.fieldType) }}</span>
                        </div>
                        <div class="sr-field-toggles">
                          <n-switch
                            :value="item.enabled"
                            size="small"
                            @update:value="onFieldEnabledChange(item.fieldKey, item.group, $event)"
                          />
                          <span class="sr-toggle-label">显示</span>
                          <n-switch
                            :value="item.required"
                            size="small"
                            :disabled="!item.enabled"
                            @update:value="onFieldRequiredChange(item.fieldKey, item.group, $event)"
                          />
                          <span class="sr-toggle-label" :class="{ disabled: !item.enabled }">必填</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </n-spin>
            </template>
          </div>

          <template v-if="editing">
            <div class="sr-edit-actions">
              <n-button tertiary @click="cancelEdit">取消</n-button>
              <n-button type="primary" :loading="saving" @click="saveEdit">
                保存表单
              </n-button>
            </div>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NButton, NIcon, NSpin, NEmpty, NInput, NSelect, NSwitch, NTag, NRadio, NRadioGroup,
} from 'naive-ui'
import { useMessage, useDialog } from 'naive-ui'
import { AddOutline, CreateOutline } from '@vicons/ionicons5'
import {
  listFields,
  FIELD_TYPE_LABEL,
  type FieldDefinition,
  type FieldType,
} from '../../api/dynamic-field'
import {
  listRegistrationForms,
  createRegistrationForm,
  updateRegistrationForm,
  deleteRegistrationForm,
  type RegistrationForm,
  type RegistrationFormField,
  type RegistrationFormType,
} from '../../api/application-form'

const message = useMessage()
const dialog = useDialog()

const forms = ref<RegistrationForm[]>([])
const allFields = ref<FieldDefinition[]>([])
const loading = ref(false)
const creating = ref(false)
const deletingId = ref<number | null>(null)
const selectedId = ref<number | null>(null)
const editing = ref(false)

const draft = ref<RegistrationForm>(emptyDraft())
const saved = ref(true)
const saving = ref(false)

const deptOptions = ref<{ label: string; value: string }[]>([])

function emptyDraft(): RegistrationForm {
  return {
    id: 0,
    name: '',
    formType: 'registration',
    departments: [],
    mode: 'default',
    fields: [],
    orderIndex: 0,
    isActive: true,
  }
}

function fieldTypeLabel(t: FieldType): string {
  return FIELD_TYPE_LABEL[t] ?? t
}
function isSingleChoice(t: FieldType): boolean {
  return t === 'SELECT' || t === 'LIST_SINGLE'
}
function isMultiChoice(t: FieldType): boolean {
  return t === 'MULTISELECT' || t === 'LIST_MULTI'
}
function isFullWidth(field: FieldDefinition): boolean {
  return field.fieldType === 'TEXT' || field.fieldType === 'ATTACHMENT'
}
function selectOptions(field: FieldDefinition) {
  return (field.options || []).map((o) => ({ label: o.label, value: o.value }))
}

interface MergedField {
  fieldKey: string
  label: string
  fieldType: FieldType
  placeholder?: string
  options: { label: string; value: string }[]
  enabled: boolean
  required: boolean
  group: string
}

function mergeFormFields(form: RegistrationForm | null): MergedField[] {
  const map = new Map((form?.fields || []).map((f) => [f.fieldKey, f]))
  return [...allFields.value]
    .sort((a, b) => a.orderIndex - b.orderIndex)
    .map((field) => {
      const c = map.get(field.fieldKey)
      return {
        fieldKey: field.fieldKey,
        label: field.label,
        fieldType: field.fieldType,
        placeholder: field.placeholder || undefined,
        options: field.options || [],
        enabled: c ? c.enabled : field.isVisible,
        required: c ? c.required : field.isRequired,
        group: c?.group || field.groupName || '基础信息',
      }
    })
}

const selected = computed(
  () => forms.value.find((f) => f.id === selectedId.value) || null,
)

const enabledFields = computed(() => {
  if (!selected.value) return []
  return mergeFormFields(selected.value).filter((m) => m.enabled)
})

const groupedEnabled = computed(() => {
  const items = enabledFields.value.map((m) => ({
    field: allFields.value.find((f) => f.fieldKey === m.fieldKey)!,
    label: m.label,
    fieldType: m.fieldType,
    placeholder: m.placeholder,
    required: m.required,
    group: m.group,
  }))
  return groupBy(items)
})

const groupedAllFields = computed(() => {
  if (!editing.value || !draft.value) return []
  const merged = mergeFormFields(draft.value)
  return groupBy(
    merged.map((m) => ({
      fieldKey: m.fieldKey,
      label: m.label,
      fieldType: m.fieldType,
      enabled: m.enabled,
      required: m.required,
      group: m.group,
    })),
  )
})

function groupBy(
  items: Array<{ group: string; [k: string]: unknown }>,
): Array<{ name: string; items: any[] }> {
  const groups: Record<string, any[]> = {}
  for (const it of items) {
    ;(groups[it.group] ||= []).push(it)
  }
  return Object.entries(groups).map(([name, its]) => ({ name, items: its }))
}

function selectForm(id: number) {
  selectedId.value = id
  editing.value = false
}

function startEdit(id: number) {
  const f = forms.value.find((x) => x.id === id)
  if (!f) return
  draft.value = JSON.parse(JSON.stringify(f))
  selectedId.value = id
  editing.value = true
  saved.value = true
}

function onAddForm() {
  draft.value = emptyDraft()
  draft.value.fields = mergeFormFields(null).map((m) => ({
    fieldKey: m.fieldKey,
    enabled: m.enabled,
    required: m.required,
    group: m.group,
  }))
  selectedId.value = null
  editing.value = true
  saved.value = true
}

function getOrCreateDraftField(fieldKey: string, group: string): RegistrationFormField {
  let f = draft.value.fields.find((x) => x.fieldKey === fieldKey)
  if (!f) {
    f = { fieldKey, enabled: true, required: false, group }
    draft.value.fields.push(f)
  }
  return f
}

function onFieldEnabledChange(fieldKey: string, group: string, enabled: boolean) {
  const f = getOrCreateDraftField(fieldKey, group)
  f.enabled = enabled
  if (!enabled) f.required = false
  saved.value = false
}
function onFieldRequiredChange(fieldKey: string, group: string, required: boolean) {
  const f = getOrCreateDraftField(fieldKey, group)
  f.required = required
  saved.value = false
}

function cancelEdit() {
  editing.value = false
  draft.value = emptyDraft()
  if (selectedId.value) selectForm(selectedId.value)
}

async function saveEdit() {
  if (!draft.value.name.trim()) {
    message.warning('请填写表单名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: draft.value.name.trim(),
      formType: draft.value.formType as RegistrationFormType,
      departments: draft.value.departments,
      mode: draft.value.mode,
      fields: draft.value.fields as RegistrationFormField[],
      isActive: draft.value.isActive,
    }
    if (draft.value.id) {
      const updated = await updateRegistrationForm(draft.value.id, payload)
      const idx = forms.value.findIndex((f) => f.id === updated.id)
      if (idx >= 0) forms.value[idx] = updated
      else forms.value.push(updated)
      message.success('表单已保存')
    } else {
      const created = await createRegistrationForm(payload)
      forms.value.push(created)
      selectedId.value = created.id
      message.success('表单已创建')
    }
    saved.value = true
    editing.value = false
  } catch (e: any) {
    message.error(`保存失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    saving.value = false
  }
}

function onDelete(f: RegistrationForm) {
  dialog.warning({
    title: '删除表单',
    content: `确定删除「${f.name}」？删除后可通过数据库恢复，操作不可在界面撤销。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      deletingId.value = f.id
      try {
        await deleteRegistrationForm(f.id)
        forms.value = forms.value.filter((x) => x.id !== f.id)
        if (selectedId.value === f.id) {
          selectedId.value = null
          editing.value = false
        }
        message.success('已删除')
      } catch (e: any) {
        message.error(`删除失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
      } finally {
        deletingId.value = null
      }
    },
  })
}

async function load() {
  loading.value = true
  try {
    const [fl, fr] = await Promise.all([
      listFields('Candidate'),
      listRegistrationForms(),
    ])
    allFields.value = fl
    forms.value = fr
    if (!selectedId.value && fr.length) selectForm(fr[0].id)
  } catch (e: any) {
    message.error(`加载失败：${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: var(--space-6);
  box-sizing: border-box;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sr-title-row { display: flex; align-items: center; gap: var(--space-2); }
.page-subtitle { margin: var(--space-2) 0 0; max-width: 720px; }

.sr-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
  align-items: start;
}
@media (min-width: 1024px) {
  .sr-grid {
    grid-template-columns: minmax(300px, 360px) 1fr;
    height: 100%;
    align-items: stretch;
  }
}
@media (max-width: 1024px) {
  .sr-grid { grid-template-columns: 1fr; }
}

.sr-list, .sr-preview {
  padding: var(--space-4);
  min-height: 0;
}
@media (min-width: 1024px) {
  .sr-list, .sr-preview {
    overflow-y: auto;
    height: 100%;
  }
}

.sr-preview {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}
.sr-preview-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
}

.sr-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.sr-panel-title { margin: 0; font-size: var(--fs-16); font-weight: 600; color: var(--ink); }
.sr-count, .sr-preview-sub { font-size: var(--text-meta); color: var(--ink-faint); }
.sr-preview-sub { display: block; margin-top: 2px; }

.sr-save-hint { font-size: var(--text-meta); color: var(--c-warning); }
.sr-save-hint.saved { color: var(--c-success); }
.sr-save-hint.saving { color: var(--c-info); }

.sr-empty { padding: var(--space-12) 0; }

.sr-list-body { display: flex; flex-direction: column; gap: var(--space-2); }
.sr-form-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  text-align: left;
  padding: var(--space-3);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  background: var(--glass-bg-card);
  color: var(--ink);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}
.sr-form-card:hover { border-color: var(--brand); }
.sr-form-card.active {
  border-color: var(--brand);
  background: var(--brand-tint);
  box-shadow: 0 0 0 1px var(--brand) inset;
}
.sr-form-card-top { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }
.sr-form-card-name { font-size: var(--text-small); font-weight: 600; color: var(--ink); }
.sr-form-card-meta { font-size: var(--text-meta); color: var(--ink-faint); }
.sr-form-card-actions { display: flex; gap: var(--space-1); margin-top: var(--space-1); }

.sr-preview-body { display: flex; flex-direction: column; gap: var(--space-4); }
.sr-preview-empty {
  padding: var(--space-8);
  text-align: center;
  color: var(--ink-faint);
  font-size: var(--text-small);
  border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-lg);
}
.sr-form-group-title {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  margin-bottom: var(--space-2);
  letter-spacing: 0.02em;
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

.sr-edit-body { display: flex; flex-direction: column; gap: var(--space-4); }
.sr-edit-row { display: grid; grid-template-columns: 96px 1fr; align-items: center; gap: var(--space-3); }
.sr-edit-label { font-size: var(--text-small); color: var(--ink-soft); }
.sr-edit-fields {
  border-top: 1px solid var(--border-hairline);
  padding-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.sr-edit-fields-head { font-size: var(--text-meta); color: var(--ink-faint); }
.sr-edit-group { display: flex; flex-direction: column; gap: var(--space-1); }

.sr-field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-hairline);
}
.sr-field-meta { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
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
.sr-field-toggles { display: flex; align-items: center; gap: var(--space-2); flex-shrink: 0; }
.sr-toggle-label { font-size: var(--text-meta); color: var(--ink-soft); }
.sr-toggle-label.disabled { color: var(--ink-faint); }

.sr-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  flex-shrink: 0;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-hairline);
  background: var(--glass-bg-card);
}
</style>

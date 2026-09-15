<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">标准简历设置</h1>
        <p class="page-subtitle">
          配置候选人标准简历包含的字段与必填规则，右侧实时预览候选人填写效果。
          字段来源于动态字段模块的「Candidate」资源。
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
        <!-- 左：配置 -->
        <section class="glass-card sr-config">
        <header class="sr-panel-head">
          <h2 class="sr-panel-title">简历字段</h2>
          <span class="sr-save-hint" :class="{ saved, saving }">{{ saving ? '保存中…' : saved ? '已自动保存' : '未保存' }}</span>
        </header>

        <n-spin :show="loading">
          <div class="sr-config-body">
            <n-alert
              v-if="error"
              type="error"
              title="加载字段失败"
              :bordered="false"
              class="sr-alert"
            >
              {{ error }}
              <template #action>
                <n-button size="small" tertiary @click="loadFields">重试</n-button>
              </template>
            </n-alert>

            <n-empty
              v-else-if="!allFields.length && !loading"
              description="暂无可选字段，请先在「动态字段」中配置 Candidate 资源字段"
              class="sr-empty"
            />

            <template v-else>
              <div v-for="m in merged" :key="m.field.fieldKey" class="sr-field-row">
                <div class="sr-field-meta">
                  <span class="sr-field-label">{{ m.field.label }}</span>
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

              <div class="sr-stages">
                <div class="sr-stages-head">必填阶段规则</div>
                <p class="sr-stages-desc">勾选的阶段将强制校验上述「必填」字段。</p>
                <div class="sr-stage-chips">
                  <button
                    v-for="s in stages"
                    :key="s.key"
                    type="button"
                    class="sr-stage-chip"
                    :class="{ active: config.requiredStages.includes(s.key) }"
                    @click="toggleStage(s.key)"
                  >
                    {{ s.label }}
                  </button>
                </div>
              </div>
            </template>
          </div>
        </n-spin>
      </section>

      <!-- 右：预览 -->
      <section class="glass-card sr-preview">
        <header class="sr-panel-head">
          <h2 class="sr-panel-title">标准简历预览</h2>
          <span class="sr-preview-count">{{ enabledFields.length }} 个字段</span>
        </header>

        <div class="sr-preview-body">
          <n-empty
            v-if="!enabledFields.length"
            description="左侧开启字段后，这里实时展示候选人填写效果"
            class="sr-empty"
          />
          <div v-else class="sr-form">
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
                    点击上传附件
                  </div>
                  <!-- 多行文本 -->
                  <n-input
                    v-else-if="m.field.fieldType === 'MULTILINE_TEXT'"
                    type="textarea"
                    disabled
                    :rows="3"
                    :placeholder="m.field.placeholder || ('请输入' + m.field.label)"
                  />
                  <!-- 行政区划级联型 (省/省市/省市区) -->
                  <RegionCascader
                    v-else-if="isRegionType(m.field.fieldType)"
                    :field-type="(m.field.fieldType as any)"
                    :with-country="!!m.field.withCountry"
                    :value="null"
                    :disabled="true"
                  />
                  <!-- 日期型 (单点/范围; 精度 年/年月/年月日 → picker type 映射) -->
                  <NDatePicker
                    v-else-if="isDateFieldType(m.field.fieldType)"
                    disabled
                    :type="(datePickerType(m.field.fieldType, m.field.dateFormat) as any)"
                    clearable
                  />
                  <!-- 文本/数字/证件 等 -->
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
import { ref, computed, onMounted, watch } from 'vue'
import { NButton, NIcon, NSwitch, NSpin, NAlert, NEmpty, NInput, NSelect, NDatePicker } from 'naive-ui'
import { RefreshOutline, ReloadOutline } from '@vicons/ionicons5'
import {
  listFields,
  type FieldDefinition,
  type FieldType,
  FIELD_TYPE_LABEL,
  isDateFieldType, datePickerType,
} from '../../api/dynamic-field'
import {
  STANDARD_RESUME_STAGES as stages,
  defaultConfig,
  fetchConfig,
  saveConfig,
  resetConfig,
  mergeFields,
  type StandardResumeConfig,
  type StandardResumeFieldConfig,
  type MergedResumeField,
} from '../../api/standard-resume';
import RegionCascader from '../../components/RegionCascader.vue';

const allFields = ref<FieldDefinition[]>([])
const loading = ref(false)
const error = ref('')
const saved = ref(true)
const saving = ref(false)
const ready = ref(false) // 初始加载完成前不触发自动保存，避免把默认值写回后端
const dirty = ref(false) // 仅用户显式编辑后才允许自动保存（避免加载即把全量字段写回后端）
const config = ref<StandardResumeConfig>(defaultConfig())

function fieldTypeLabel(t: FieldType): string {
  return FIELD_TYPE_LABEL[t] ?? t
}

function isSingleChoice(t: FieldType): boolean {
  return t === 'SELECT' || t === 'LIST_SINGLE'
}
function isMultiChoice(t: FieldType): boolean {
  return t === 'MULTISELECT' || t === 'LIST_MULTI'
}
// 2026-09-15 行政区划级联型(省/省市/省市区)
function isRegionType(t: FieldType): boolean {
  return t === 'REGION_PROVINCE' || t === 'REGION_PROVINCE_CITY' || t === 'REGION_PROVINCE_CITY_DISTRICT'
}
function selectOptions(field: FieldDefinition) {
  return (field.options || []).map((o) => ({ label: o.label, value: o.value }))
}

// 多行文本（TEXT）与附件块独占整宽一行；其余字段每行两列
function isFullWidth(field: FieldDefinition): boolean {
  return field.fieldType === 'TEXT'
    || field.fieldType === 'ATTACHMENT'
    || field.fieldType === 'ADDRESS'
    || field.fieldType === 'REGION_PROVINCE'
    || field.fieldType === 'REGION_PROVINCE_CITY'
    || field.fieldType === 'REGION_PROVINCE_CITY_DISTRICT'
}

// 用全部动态字段给 config 补齐/裁剪条目，保证每个字段都有配置项
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
    const fields = await listFields('Candidate')
    allFields.value = fields
    ensureCoverage()
  } catch (e: any) {
    error.value = e?.message || '请求动态字段失败，请检查网络或登录状态'
  } finally {
    loading.value = false
  }
}

function findEntry(key: string): StandardResumeFieldConfig | undefined {
  return config.value.fields.find((f) => f.fieldKey === key)
}
function setEnabled(key: string, v: boolean) {
  const e = findEntry(key)
  if (!e) return
  e.enabled = v
  if (!v) e.required = false // 不显示则不允许必填
  dirty.value = true
}
function setRequired(key: string, v: boolean) {
  const e = findEntry(key)
  if (!e) return
  e.required = v
  dirty.value = true
}
function toggleStage(key: string) {
  const arr = config.value.requiredStages
  const i = arr.indexOf(key)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(key)
  dirty.value = true
}

async function onReset() {
  const cfg = await resetConfig()
  config.value = cfg
  ensureCoverage()
  dirty.value = false // reset 已通过 API 落库，避免 watch 重复写回
}

// 配置变更即自动持久化到后端
watch(
  config,
  async (v) => {
    if (!ready.value || !dirty.value) return
    saving.value = true
    saved.value = false
    try {
      await saveConfig(v)
      saved.value = true
    } catch {
      saved.value = false // 保存失败保留本地修改，下次变更重试
    } finally {
      saving.value = false
    }
  },
  { deep: true },
)

const merged = computed<MergedResumeField[]>(() => mergeFields(allFields.value, config.value))
const enabledFields = computed(() => merged.value.filter((m) => m.enabled))
const groupedEnabled = computed(() => {
  const groups: Record<string, MergedResumeField[]> = {}
  for (const m of enabledFields.value) {
    const g = m.field.groupName || '基础信息'
    ;(groups[g] ||= []).push(m)
  }
  return Object.entries(groups).map(([name, items]) => ({ name, items }))
})

onMounted(async () => {
  await loadFields()
  await loadConfigIntoState()
})

// 拉取后端标准简历配置填入 state 并确保字段覆盖
async function loadConfigIntoState() {
  try {
    const cfg = await fetchConfig()
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
  grid-template-columns: minmax(320px, 380px) 1fr;
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

.sr-empty { padding: var(--space-12) 0; }

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

.sr-stages { margin-top: var(--space-4); padding-top: var(--space-3); border-top: 1px solid var(--border-hairline); }
.sr-stages-head { font-size: var(--text-small); font-weight: 600; color: var(--ink); margin-bottom: var(--space-1); }
.sr-stages-desc { font-size: var(--text-meta); color: var(--ink-soft); margin: 0 0 var(--space-3); }
.sr-stage-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.sr-stage-chip {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline);
  background: transparent;
  color: var(--ink-soft);
  font-size: var(--text-small);
  cursor: pointer;
  transition: background var(--duration-base) var(--ease-out), color var(--duration-base) var(--ease-out), border-color var(--duration-base) var(--ease-out);
}
.sr-stage-chip:hover { border-color: var(--brand-tint); color: var(--brand); }
.sr-stage-chip.active {
  background: var(--brand-soft);
  color: var(--brand);
  border-color: var(--brand-soft);
}

.sr-preview-count { font-size: var(--text-meta); color: var(--ink-faint); }

.sr-form { display: flex; flex-direction: column; gap: var(--space-4); }
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
</style>

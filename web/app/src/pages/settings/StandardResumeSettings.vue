<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">标准简历设置</h1>
        <p class="page-subtitle">
          配置候选人标准简历包含的字段与必填规则，右侧实时预览候选人填写效果。
          字段来源于动态字段模块的「Candidate」资源；可拖拽模块与字段调整展示顺序。
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
        <!-- 左：配置（按模块分组 + 拖拽） -->
        <section class="glass-card sr-config">
          <header class="sr-panel-head">
            <h2 class="sr-panel-title">简历字段</h2>
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
                description="暂无可选字段，请先在「动态字段」中配置 Candidate 资源字段"
                class="sr-empty"
              />

              <template v-else>
                <!-- 模块级拖拽：每个 module 一个 <section> -->
                <VueDraggable
                  v-model="moduleGroups"
                  item-key="key"
                  handle=".module-drag-handle"
                  :animation="180"
                  ghost-class="sr-ghost"
                  class="sr-modules"
                  @end="onModuleDragEnd"
                >
                  <template #item="{ element: grp }">
                    <section class="sr-module">
                      <header class="sr-module-head">
                        <n-icon
                          v-if="moduleGroups.length > 1"
                          class="sr-drag-handle module-drag-handle"
                          :component="ReorderThreeOutline"
                          size="18"
                        />
                        <span v-else class="sr-drag-handle-placeholder" />
                        <h3 class="sr-module-title">
                          {{ grp.module?.name || '未分组' }}
                        </h3>
                        <n-tag size="small" :bordered="false" class="sr-module-count">
                          {{ grp.fields.length }} 字段
                        </n-tag>
                      </header>

                      <!-- 字段级拖拽：每行一个字段 -->
                      <VueDraggable
                        v-model="grp.fields"
                        :item-key="(m: MergedResumeField) => m.field.id"
                        handle=".field-drag-handle"
                        :animation="160"
                        ghost-class="sr-ghost"
                        class="sr-fields"
                        @end="(evt: SortableEvent) => onFieldDragEnd(grp, evt)"
                      >
                        <template #item="{ element: m }">
                          <div class="sr-field-row">
                            <n-icon
                              v-if="m.field.isVisible !== false"
                              class="sr-drag-handle field-drag-handle"
                              :component="MenuOutline"
                              size="16"
                            />
                            <span v-else class="sr-drag-handle-placeholder" />
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
                        </template>
                      </VueDraggable>
                    </section>
                  </template>
                </VueDraggable>

                <!-- 必填阶段规则（保持原结构） -->
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

        <!-- 右：预览（按模块分组 + 启用字段） -->
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
              <div
                v-for="grp in previewGroups"
                :key="grp.key"
                class="sr-form-group"
              >
                <div class="sr-form-group-title">
                  {{ grp.module?.name || '未分组' }}
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
                    <!-- 默认：文本/数字/证件 等 -->
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
import { NButton, NIcon, NSwitch, NSpin, NAlert, NEmpty, NInput, NSelect, NDatePicker, NTag, useMessage } from 'naive-ui'
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
  updateFieldOrder,
  extractApiError,
  type FieldDefinition,
  type FieldType,
  type RegionLevelValue,
  FIELD_TYPE_LABEL,
  isDateFieldType, datePickerType,
  isRegionFieldType,
} from '../../api/dynamic-field'
import {
  STANDARD_RESUME_STAGES as stages,
  defaultConfig,
  fetchConfig,
  saveConfig,
  resetConfig,
  mergeFields,
  groupFieldsByModule,
  UNGROUPED_MODULE_CODE,
  type StandardResumeConfig,
  type StandardResumeFieldConfig,
  type MergedResumeField,
  type ModuleGroup,
} from '../../api/standard-resume';
import RegionCascader from '../../components/RegionCascader.vue';
import AttachmentUploader from '@/components/AttachmentUploader.vue';
import CompositeFieldCard from '@/components/CompositeFieldCard.vue';

const message = useMessage()

const allFields = ref<FieldDefinition[]>([])
const loading = ref(false)
const error = ref('')
const saved = ref(true)
const saving = ref(false)
const ready = ref(false) // 初始加载完成前不触发自动保存，避免把默认值写回后端
const dirty = ref(false) // 仅用户显式编辑后才允许自动保存（避免加载即把全量字段写回后端）
const config = ref<StandardResumeConfig>(defaultConfig())

// 拖拽专用：本地可变副本；用 moduleGroups 渲染 + 拖拽，拖拽结束再回写 config
const moduleGroups = ref<ModuleGroup[]>([])
// 字段排序保存中（避免重复触发 + 显示进度）
const fieldReorderRunning = ref(false)
const lastReorderError = ref('')

function fieldTypeLabel(t: FieldType): string {
  return FIELD_TYPE_LABEL[t] ?? t
}

function isSingleChoice(t: FieldType): boolean {
  return t === 'SELECT' || t === 'LIST_SINGLE'
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

// 多行文本（TEXT）与附件块独占整宽一行；其余字段每行两列
function isFullWidth(field: FieldDefinition): boolean {
  return field.fieldType === 'TEXT'
    || field.fieldType === 'ATTACHMENT'
    || field.fieldType === 'ADDRESS'
    || field.fieldType === 'REGION'
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

// 用 moduleGroups 渲染左侧；watch merged / config.moduleOrder 同步过来。
// 注意: moduleGroups 是本地可变副本 (拖拽会改它), 拖拽结束才把顺序回写到 config.moduleOrder。
watch(
  [merged, () => config.value.moduleOrder],
  ([m, mo]) => {
    const next = groupFieldsByModule(m, mo)
    // 保留用户已编辑的 group.fields (本地拖拽态), 其它按 next 重建
    if (moduleGroups.value.length === 0) {
      moduleGroups.value = next
      return
    }
    // 把 next 的 key 顺序应用到现有 moduleGroups, 缺失的追加到末尾
    const byKey = new Map(moduleGroups.value.map((g) => [g.key, g]))
    const rebuilt: ModuleGroup[] = []
    for (const g of next) {
      const existing = byKey.get(g.key)
      if (existing) {
        // 字段可能变了 (新增/删除), 用 next.fields 替换
        existing.fields = g.fields
        rebuilt.push(existing)
        byKey.delete(g.key)
      } else {
        rebuilt.push(g)
      }
    }
    // 残留的 group (后端顺序里已消失的模块) 跳过 — 对应字段也没了
    moduleGroups.value = rebuilt
  },
  { immediate: true, deep: true },
)

// 预览侧: 按当前拖拽后的顺序 + 仅启用的字段分组, 与左侧保持一致
const previewGroups = computed(() =>
  moduleGroups.value
    .map((g) => ({
      key: g.key,
      module: g.module,
      fields: g.fields.filter((f) => f.enabled),
    }))
    .filter((g) => g.fields.length > 0),
)

// 模块拖拽结束: 把新顺序回写到 config.moduleOrder, 触发自动保存。
function onModuleDragEnd() {
  if (moduleGroups.value.length <= 1) return
  config.value.moduleOrder = moduleGroups.value.map((g) =>
    g.module?.code ?? UNGROUPED_MODULE_CODE,
  )
  dirty.value = true
}

// 字段拖拽结束: 把组内新字段顺序展开为全局 merged 顺序,
// 然后批量 PATCH DynamicField.order_index (步长 10 方便再插)。
async function onFieldDragEnd(grp: ModuleGroup, _evt: SortableEvent) {
  // 仅当真正改动时才写后端 (Sortable 会在无变化时也触发 end, 跳过)
  if (!grp.fields.length) return

  // 1) 立即把新顺序应用到本地 merged 数组 (驱动预览/UI 重排)
  // 找到该组在 moduleGroups 里的索引位置, 把组内字段按新顺序展开回 merged
  const groupIndex = moduleGroups.value.findIndex((g) => g.key === grp.key)
  if (groupIndex < 0) return

  // 2) 重新组装 merged 数组: 取所有 group, 按 groupIndex 顺序, group 内按 grp.fields 新顺序
  const newMergedOrder: MergedResumeField[] = []
  for (const g of moduleGroups.value) {
    for (const m of g.fields) newMergedOrder.push(m)
  }

  // 3) 计算每个字段的新 order_index, 步长 10 (10, 20, 30, ...)
  const step = 10
  const updates: Array<{ id: string; orderIndex: number }> = []
  for (let i = 0; i < newMergedOrder.length; i++) {
    const m = newMergedOrder[i]
    if (!m.field.id) continue
    updates.push({ id: m.field.id, orderIndex: (i + 1) * step })
  }
  if (!updates.length) return

  // 4) 先 snapshot 原 orderIndex (必须在改 allFields 之前做)
  const beforeOrder = new Map(allFields.value.map((f) => [f.id, f.orderIndex]))
  const byId = new Map(allFields.value.map((f) => [f.id, f]))
  for (const u of updates) {
    const f = byId.get(u.id)
    if (f) f.orderIndex = u.orderIndex
  }
  // 强制触发 merged / moduleGroups 重新分组 (使用新 orderIndex)
  // 注意: allFields 是 ref, 改 .orderIndex 后, 因为 reactive proxy, watch([merged,...]) 会重跑

  // 5) 批量 PATCH 写回后端; 部分失败回滚
  fieldReorderRunning.value = true
  lastReorderError.value = ''
  try {
    const results = await Promise.allSettled(
      updates.map((u) => updateFieldOrder('Candidate', u.id, u.orderIndex)),
    )
    const failed = results.filter((r) => r.status === 'rejected') as PromiseRejectedResult[]
    if (failed.length) {
      // 回滚本地 orderIndex
      for (const [id, oldOrder] of beforeOrder.entries()) {
        const f = byId.get(id)
        if (f) f.orderIndex = oldOrder
      }
      const firstReason = failed[0]?.reason
      lastReorderError.value = `字段排序保存失败 (${failed.length}/${updates.length}), 已回滚`
      // eslint-disable-next-line no-console
      console.error('[StandardResumeSettings] field reorder failed', failed)
      message.error(lastReorderError.value + (firstReason ? `: ${extractApiError(firstReason)}` : ''))
    }
  } catch (e: any) {
    // 整批异常时整体回滚
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

/* === 模块分组（玻璃卡片嵌套 + 拖拽手柄） === */
.sr-modules {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.sr-module {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
}
.sr-module-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
}
.sr-module-title {
  margin: 0;
  flex: 1;
  min-width: 0;
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sr-module-count {
  flex-shrink: 0;
  background: var(--c-info-soft);
  color: var(--c-info);
}

/* 拖拽手柄（模块 + 字段共用样式 + 区分父级选择器） */
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
.module-drag-handle { /* 模块级: 稍大, 突出 */ }
.field-drag-handle { /* 字段级: 稍小 */ }

/* Sortable.js 拖拽 ghost 态 (拖动中的临时占位元素) */
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

/* === 阶段规则 === */
.sr-stages {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-hairline);
}
.sr-stages-head {
  font-size: var(--text-small);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-1);
}
.sr-stages-desc {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  margin: 0 0 var(--space-3);
}
.sr-stage-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.sr-stage-chip {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline);
  background: transparent;
  color: var(--ink-soft);
  font-size: var(--text-small);
  cursor: pointer;
  transition: background var(--duration-base, .2s) var(--ease-out, ease),
              color var(--duration-base, .2s) var(--ease-out, ease),
              border-color var(--duration-base, .2s) var(--ease-out, ease);
}
.sr-stage-chip:hover { border-color: var(--brand-tint); color: var(--brand); }
.sr-stage-chip.active {
  background: var(--brand-soft);
  color: var(--brand);
  border-color: var(--brand-soft);
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

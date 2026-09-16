<template>
  <div class="composite-field-card">
    <div class="cfc-head">
      <n-icon size="16" class="cfc-icon"><LayersOutline /></n-icon>
      <span class="cfc-title">{{ field.label || '组合字段' }}</span>
    </div>
    <div class="cfc-grid">
      <div v-for="sub in field.subFields || []" :key="sub.key" class="cfc-cell">
        <div class="cfc-cell-label">
          {{ sub.label || sub.key }}
          <span v-if="sub.required" class="cfc-req">*</span>
        </div>
        <!-- 附件子字段：内嵌上传器 -->
        <AttachmentUploader
          v-if="sub.type === 'ATTACHMENT'"
          :model-value="asAttachments(modelValue[sub.key])"
          :multiple="true"
          :disabled="mode === 'display'"
          @update:model-value="(v) => setSub(sub.key, v)"
        />
        <!-- 文本/多行 -->
        <n-input
          v-else-if="sub.type === 'TEXT' || sub.type === 'MULTILINE_TEXT'"
          :value="asString(modelValue[sub.key])"
          :type="sub.type === 'MULTILINE_TEXT' ? 'textarea' : 'text'"
          :disabled="mode === 'display'"
          :placeholder="mode === 'display' ? '—' : '请输入'"
          @update:value="(v) => setSub(sub.key, v)"
        />
        <!-- 数字 -->
        <n-input-number
          v-else-if="sub.type === 'NUMBER'"
          :value="asNumber(modelValue[sub.key])"
          :disabled="mode === 'display'"
          @update:value="(v) => setSub(sub.key, v)"
        />
        <!-- 日期 -->
        <n-date-picker
          v-else-if="sub.type === 'DATE'"
          :value="asTimestamp(modelValue[sub.key])"
          type="date"
          :disabled="mode === 'display'"
          @update:value="(v) => setSub(sub.key, v ? formatDate(v) : '')"
        />
        <!-- 手机号 / 邮箱 -->
        <n-input
          v-else
          :value="asString(modelValue[sub.key])"
          :type="sub.type === 'EMAIL' ? 'email' : 'tel'"
          :disabled="mode === 'display'"
          :placeholder="mode === 'display' ? '—' : '请输入'"
          @update:value="(v) => setSub(sub.key, v)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NIcon, NInput, NInputNumber, NDatePicker } from 'naive-ui'
import { LayersOutline } from '@vicons/ionicons5'
import AttachmentUploader from '@/components/AttachmentUploader.vue'
import { type SubField, type AttachmentItem } from '@/api/dynamic-field'

const props = withDefaults(defineProps<{
  field: { label?: string; subFields?: SubField[] | null }
  modelValue: Record<string, unknown>
  mode?: 'edit' | 'display'
}>(), { modelValue: () => ({}), mode: 'edit' })

const emit = defineEmits<{
  (e: 'update:modelValue', v: Record<string, unknown>): void
}>()

function setSub(key: string, val: unknown) {
  emit('update:modelValue', { ...props.modelValue, [key]: val })
}
function asString(v: unknown): string {
  return v == null ? '' : String(v)
}
function asNumber(v: unknown): number | null {
  if (v == null || v === '') return null
  const n = Number(v)
  return Number.isNaN(n) ? null : n
}
function asAttachments(v: unknown): AttachmentItem[] {
  return Array.isArray(v) ? (v as AttachmentItem[]) : []
}
function asTimestamp(v: unknown): number | null {
  if (!v) return null
  const t = new Date(String(v)).getTime()
  return Number.isNaN(t) ? null : t
}
function formatDate(ts: number): string {
  const d = new Date(ts)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
</script>

<style scoped>
.composite-field-card {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-card);
  padding: 12px 14px;
}
.cfc-head { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.cfc-icon { color: var(--brand); }
.cfc-title { font-weight: 600; font-size: var(--fs-14); color: var(--ink); }
.cfc-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 16px; }
.cfc-cell { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.cfc-cell-label { font-size: var(--fs-13); color: var(--ink-soft); }
.cfc-req { color: var(--error); margin-left: 2px; }
@media (max-width: 640px) {
  .cfc-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>

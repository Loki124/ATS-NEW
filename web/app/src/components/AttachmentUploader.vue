<template>
  <div class="attachment-uploader">
    <div v-if="modelValue.length" class="au-list">
      <div v-for="it in modelValue" :key="it.id || it.url" class="au-item">
        <img v-if="isImage(it)" :src="it.url" class="au-thumb" alt="" />
        <div v-else class="au-file-icon">
          <n-icon size="20"><DocumentOutline /></n-icon>
        </div>
        <a :href="it.url" target="_blank" rel="noopener" class="au-name" :title="it.name">{{ it.name }}</a>
        <n-button v-if="!disabled" text type="error" size="tiny" @click="removeItem(it)">{{ t('components.AttachmentUploader.s1') }}</n-button>
      </div>
    </div>
    <label v-if="!disabled" class="au-add">
      <input type="file" :multiple="multiple" :accept="accept" class="au-input" @change="onPick" />
      <n-icon size="16"><AddOutline /></n-icon>
      <span>{{ multiple ? '添加附件' : '上传附件' }}</span>
    </label>
    <n-text v-if="uploading" depth="3" class="au-uploading">{{ t('components.AttachmentUploader.s2') }}</n-text>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref } from 'vue'
import { NIcon, NButton, NText, NImage, useMessage } from 'naive-ui'
import { AddOutline, DocumentOutline } from '@vicons/ionicons5'
import config from '@/config'
import { type AttachmentItem } from '@/api/dynamic-field'
const { t } = useI18n()

const props = withDefaults(defineProps<{
  modelValue: AttachmentItem[]
  multiple?: boolean
  disabled?: boolean
}>(), { multiple: true, disabled: false })

const emit = defineEmits<{
  (e: 'update:modelValue', v: AttachmentItem[]): void
}>()

const message = useMessage()
const uploading = ref(false)
const accept = '.pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar'

function isImage(it: AttachmentItem): boolean {
  return /\.(png|jpe?g|gif|webp|bmp)$/i.test(it.url || it.name || '')
}

function removeItem(it: AttachmentItem) {
  emit('update:modelValue', props.modelValue.filter((x) => (x.id || x.url) !== (it.id || it.url)))
}

async function uploadOne(file: File): Promise<AttachmentItem> {
  const form = new FormData()
  form.append('file', file)
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token') || ''
  const resp = await fetch(`${config.api.baseUrl}/media/upload/`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const data = await resp.json()
  if (!resp.ok || !data?.success) {
    throw new Error(data?.message || `上传失败 (HTTP ${resp.status})`)
  }
  return {
    id: data.data.id,
    name: data.data.name,
    url: data.data.url,
    size: data.data.size,
    content_type: data.data.content_type,
  }
}

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  uploading.value = true
  try {
    const uploaded: AttachmentItem[] = []
    for (const f of files) {
      uploaded.push(await uploadOne(f))
    }
    emit('update:modelValue', [...props.modelValue, ...uploaded])
    message.success(`已上传 ${uploaded.length} 个文件`)
  } catch (err: any) {
    message.error('上传失败: ' + (err?.message || err))
  } finally {
    uploading.value = false
    input.value = ''
  }
}
</script>

<style scoped>
.attachment-uploader { display: flex; flex-direction: column; gap: 8px; }
.au-list { display: flex; flex-wrap: wrap; gap: 8px; }
.au-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px; border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm); background: var(--glass-bg-card);
  max-width: 240px;
}
.au-thumb { width: 32px; height: 32px; object-fit: cover; border-radius: 4px; }
.au-file-icon { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; color: var(--ink-soft); }
.au-name { font-size: var(--fs-13); color: var(--ink); text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.au-name:hover { text-decoration: underline; }
.au-add {
  display: inline-flex; align-items: center; gap: 4px; cursor: pointer;
  padding: 6px 12px; border: 1px dashed var(--border-hairline);
  border-radius: var(--radius-sm); color: var(--ink-soft); font-size: var(--fs-13);
  width: fit-content;
}
.au-add:hover { border-color: var(--brand); color: var(--brand); }
.au-input { display: none; }
.au-uploading { font-size: var(--fs-12); }
</style>

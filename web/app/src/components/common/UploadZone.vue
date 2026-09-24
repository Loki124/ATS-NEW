<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { NIcon } from 'naive-ui'
import { CloudUploadOutline as Upload, DocumentTextOutline as FileText, FolderOpenOutline as FolderOpen } from '@vicons/ionicons5'
const { t } = useI18n()
const emit = defineEmits<{ (e: 'upload', files: File[]): void }>()

function handleClick() {
  emit('upload', [])  // parent handles file picker
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).classList.add('dragover')
}

function handleDragLeave(e: DragEvent) {
  ;(e.currentTarget as HTMLElement).classList.remove('dragover')
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  ;(e.currentTarget as HTMLElement).classList.remove('dragover')
  const files = Array.from(e.dataTransfer?.files || [])
  emit('upload', files)
}
</script>

<template>
  <div
    class="upload-zone"
    @click="handleClick"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <div class="up-icon"><NIcon :size="28" aria-hidden="true"><Upload /></NIcon></div>
    <div class="up-text">{{ t('components.common.UploadZone.s1') }}</div>
    <div class="up-hint">{{ t('components.common.UploadZone.s2') }}</div>
    <div class="up-quick">
      <span @click.stop="emit('upload', [])"><NIcon :size="14" style="vertical-align:-2px;margin-right:4px" aria-hidden="true"><FileText /></NIcon>{{ t('components.common.UploadZone.s3') }}</span>
      <span @click.stop="emit('upload', [])"><NIcon :size="14" style="vertical-align:-2px;margin-right:4px" aria-hidden="true"><FolderOpen /></NIcon>{{ t('components.common.UploadZone.s4') }}</span>
    </div>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--g4);
  border-radius: 12px;
  padding: var(--space-8) 20px;
  text-align: center;
  cursor: pointer;
  transition: 0.15s;
  background: var(--g1);
}
.upload-zone:hover, .upload-zone.dragover { border-color: var(--brand); background: var(--brand-a12); }
.upload-zone.dragover { box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }
.up-icon { font-size: var(--fs-36); margin-bottom: var(--space-2); transition: 0.2s; }
.upload-zone.dragover .up-icon { transform: scale(1.1); }
.up-text { font-size: var(--fs-13); font-weight: 500; color: var(--g7); }
.up-hint { font-size: 11px; color: var(--g5); margin-top: var(--space-1); }
.up-quick { display: flex; gap: var(--space-2); justify-content: center; margin-top: var(--space-3); }
.up-quick span {
  font-size: 11px;
  padding: var(--space-1) 10px;
  background: var(--glass-bg-card);
  border: 1px solid var(--g3);
  border-radius: 20px;
  color: var(--g6);
  cursor: pointer;
}
.up-quick span:hover { border-color: var(--brand); color: var(--brand); }
</style>
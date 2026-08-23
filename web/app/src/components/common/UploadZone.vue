<script setup lang="ts">
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
    <div class="up-icon">📁</div>
    <div class="up-text">点击上传或拖拽简历文件到此处</div>
    <div class="up-hint">支持 PDF / Word / TXT，单文件不超过 10MB，支持批量上传</div>
    <div class="up-quick">
      <span @click.stop="emit('upload', [])">📄 选择文件</span>
      <span @click.stop="emit('upload', [])">📂 从人才库导入</span>
    </div>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--g4);
  border-radius: 12px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: 0.15s;
  background: var(--g1);
}
.upload-zone:hover, .upload-zone.dragover { border-color: var(--p); background: var(--pl); }
.upload-zone.dragover { box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }
.up-icon { font-size: 36px; margin-bottom: 8px; transition: 0.2s; }
.upload-zone.dragover .up-icon { transform: scale(1.1); }
.up-text { font-size: 13px; font-weight: 500; color: var(--g7); }
.up-hint { font-size: 11px; color: var(--g5); margin-top: 4px; }
.up-quick { display: flex; gap: 8px; justify-content: center; margin-top: 12px; }
.up-quick span {
  font-size: 11px;
  padding: 4px 10px;
  background: var(--glass-bg-card);
  border: 1px solid var(--g3);
  border-radius: 20px;
  color: var(--g6);
  cursor: pointer;
}
.up-quick span:hover { border-color: var(--p); color: var(--p); }
</style>
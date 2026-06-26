<script setup lang="ts">
import type { ResumeDraft } from '@/stores/addCandidate'
import StatusTag from './StatusTag.vue'
import CheckBanner from './CheckBanner.vue'

const props = defineProps<{
  resume: ResumeDraft
  active: boolean
  selected: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'select'): void
  (e: 'replace'): void
}>()

function getStatusClass(s: string) {
  if (s === 'clean') return 'clean'
  if (s === 'unocc') return 'unocc'
  if (s === 'occupied') return 'occ'
  return ''
}

function progressColor(p: string | null) {
  if (p === 'uploading') return 'bl'
  if (p === 'parsing') return 'ye'
  if (p === 'checking') return 'pu'
  return 'bl'
}
</script>

<template>
  <div :class="['card-item', getStatusClass(resume.status), { expanded: active, selected }]">
    <div class="c-header" @click="emit('toggle')">
      <div v-if="resume.status !== 'processing'" :class="['c-chk', { checked: selected }]" @click.stop="emit('select')"></div>
      <div v-else style="width:16px;flex-shrink:0;"></div>
      <div class="c-avatar">{{ resume.parsed?.name?.charAt(0) || resume.file_name.charAt(0) }}</div>
      <div class="c-info">
        <div class="c-name">
          {{ resume.parsed?.name || resume.file_name }}
          <span class="c-file">{{ resume.file_name }}</span>
          <StatusTag :status="resume.status" />
        </div>
        <div class="c-basic">
          <span v-if="resume.parsed?.gender">{{ resume.parsed.gender }}</span>
          <span v-if="resume.parsed?.age">{{ resume.parsed.age }}岁</span>
          <span v-if="resume.parsed?.phone">{{ resume.parsed.phone }}</span>
          <span v-if="resume.parsed?.edu">{{ resume.parsed.edu }}</span>
          <span v-if="resume.parsed?.position">{{ resume.parsed.position }}</span>
        </div>
        <div v-if="resume.status === 'processing'" class="pbar">
          <div :class="['pfill', progressColor(resume.procPhase)]" :style="{ width: `${resume.progress}%` }"></div>
        </div>
      </div>
      <button v-if="resume.status !== 'processing'" class="replace-file-btn" @click.stop="emit('replace')">更换</button>
      <div class="c-expand">▾</div>
    </div>

    <div v-if="active" class="c-body">
      <CheckBanner v-if="resume.duplicate" :status="resume.duplicate.status" />
      <!-- Phase 5 场景组件会在这里插入更多内容 -->
      <slot name="body" />
    </div>
  </div>
</template>

<style scoped>
.card-item {
  border: 1px solid var(--g3);
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  transition: 0.15s;
}
.card-item:hover { border-color: var(--p); }
.card-item.selected { border-color: var(--p); box-shadow: 0 0 0 1px rgba(79, 70, 229, 0.15); }
.card-item.occ { border-left: 3px solid var(--d); }
.card-item.unocc { border-left: 3px solid var(--w); }
.card-item.clean { border-left: 3px solid var(--s); }

.c-header { display: flex; align-items: center; gap: 10px; padding: 12px 14px; cursor: pointer; }
.c-chk {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 2px solid var(--g4);
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.c-chk.checked { background: var(--p); border-color: var(--p); }
.c-chk.checked::after { content: '✓'; color: #fff; font-size: 10px; }

.c-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--g2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--g5);
  flex-shrink: 0;
  font-weight: 600;
}
.c-info { flex: 1; min-width: 0; }
.c-name { font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.c-file { font-size: 10px; color: var(--g5); font-weight: 400; }
.c-basic { font-size: 11px; color: var(--g6); display: flex; gap: 10px; flex-wrap: wrap; margin-top: 2px; }
.c-expand { font-size: 16px; color: var(--g5); transition: 0.2s; flex-shrink: 0; }
.card-item.expanded .c-expand { transform: rotate(180deg); }

.pbar { height: 3px; background: var(--g3); border-radius: 2px; overflow: hidden; margin-top: 4px; }
.pfill { height: 100%; border-radius: 2px; transition: width 0.3s; }
.pfill.bl { background: var(--b); }
.pfill.ye { background: #F59E0B; }
.pfill.pu { background: #8B5CF6; }

.replace-file-btn {
  padding: 4px 8px;
  font-size: 11px;
  border: 1px solid var(--g3);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.c-body { padding: 0 14px 14px; border-top: 1px solid var(--g3); }
</style>

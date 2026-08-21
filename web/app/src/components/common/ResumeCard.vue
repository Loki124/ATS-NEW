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
  if (p === 'uploading') return 'info'
  if (p === 'parsing') return 'warning'
  if (p === 'checking') return 'brand'
  return 'info'
}
</script>

<template>
  <div :class="['card-item', getStatusClass(resume.status), { expanded: active, selected }]">
    <div class="c-header" @click="emit('toggle')">
      <div v-if="resume.status !== 'processing'" :class="['c-chk', { checked: selected }]" @click.stop="emit('select')"></div>
      <div v-else class="c-chk-spacer"></div>
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
          <div :class="['pfill', `pfill-${progressColor(resume.procPhase)}`]" :style="{ width: `${resume.progress}%` }"></div>
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
/* === ResumeCard · 玻璃卡片 + 状态左边框（DESIGN.md §4 玻璃卡片）=== */
.card-item {
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-card);
}
.card-item:hover {
  border-color: var(--brand);
  box-shadow: var(--shadow-card), 0 0 0 1px var(--brand-tint);
}
.card-item.selected {
  border-color: var(--brand);
  box-shadow: var(--shadow-card), 0 0 0 1px var(--brand-soft);
}
/* 状态左边框（DESIGN.md §4 语义状态） */
.card-item.occ   { border-left: 3px solid var(--c-error); }
.card-item.unocc { border-left: 3px solid var(--c-warning); }
.card-item.clean { border-left: 3px solid var(--c-success); }

.c-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  cursor: pointer;
}
.c-chk-spacer {
  width: 16px;
  flex-shrink: 0;
}
.c-chk {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 2px solid var(--ink-faint);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: all var(--duration-fast) var(--ease-out);
}
.c-chk.checked {
  background: var(--brand);
  border-color: var(--brand);
}
.c-chk.checked::after {
  content: '✓';
  color: #fff;
  font-size: 10px;
}

.c-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-h4);
  color: var(--brand);
  flex-shrink: 0;
  font-weight: 600;
}
.c-info {
  flex: 1;
  min-width: 0;
}
.c-name {
  font-weight: 600;
  font-size: var(--text-small);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  color: var(--ink);
}
.c-file {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  font-weight: 400;
}
.c-basic {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-top: 2px;
}
.c-expand {
  font-size: var(--text-h4);
  color: var(--ink-faint);
  transition: transform var(--duration-base) var(--ease-out);
  flex-shrink: 0;
}
.card-item.expanded .c-expand {
  transform: rotate(180deg);
}

.pbar {
  height: 3px;
  background: var(--glass-bg-input);
  border-radius: var(--radius-pill);
  overflow: hidden;
  margin-top: var(--space-1);
}
.pfill {
  height: 100%;
  border-radius: var(--radius-pill);
  transition: width var(--duration-base) var(--ease-out);
}
.pfill-info    { background: var(--c-info); }
.pfill-warning { background: var(--c-warning); }
.pfill-brand   { background: var(--brand); }

.replace-file-btn {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-meta);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  background: var(--glass-bg-input);
  color: var(--ink-soft);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.replace-file-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.c-body {
  padding: 0 var(--space-3) var(--space-3);
  border-top: 1px solid var(--border-hairline);
}
</style>
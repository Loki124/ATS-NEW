<script setup lang="ts">
import { computed } from 'vue'
import { useAddCandidateStore } from '@/stores/addCandidate'

const store = useAddCandidateStore()

const stepClass = computed(() => (s: 1 | 2) => {
  if (store.step === s) return 'on'
  if (store.step > s) return 'ok'
  return ''
})
</script>

<template>
  <div class="stepper">
    <div class="step-item">
      <div :class="['sdot', stepClass(1)]">{{ store.step > 1 ? '✓' : '1' }}</div>
      <span :class="['slabel', stepClass(1) ? stepClass(1) : '']">上传解析 & 查重</span>
    </div>
    <div :class="['sline', store.step > 1 ? 'ok' : '']"></div>
    <div class="step-item">
      <div :class="['sdot', stepClass(2)]">{{ store.step >= 2 ? (store.step > 2 ? '✓' : '2') : '2' }}</div>
      <span class="slabel">选择去向 & 提交</span>
    </div>
  </div>
</template>

<style scoped>
.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--g3);
  flex-shrink: 0;
  gap: 0;
}
.step-item { display: flex; align-items: center; gap: 2px; }
.sdot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  transition: 0.2s;
  border: 2px solid var(--g4);
  background: var(--glass-bg-card); /* v2.8 T2.8.1: #fff → var(--glass-bg-card) */
  color: var(--g5);
}
.sdot.on { border-color: var(--p); background: var(--p); color: #fff; }
.sdot.ok { border-color: var(--s); background: var(--s); color: #fff; }
.sdot.warn { border-color: var(--w); background: var(--w); color: #fff; }
.slabel {
  font-size: 11px;
  color: var(--g5);
  font-weight: 500;
  margin-left: 6px;
}
.sdot.on + .slabel { color: var(--p); }
.sdot.ok + .slabel { color: var(--s); }
.sdot.warn + .slabel { color: var(--w); }
.sline {
  width: 56px;
  height: 2px;
  background: var(--g3);
  margin: 0 6px;
  transition: 0.2s;
}
.sline.ok { background: var(--s); }
.sline.on { background: linear-gradient(to right, var(--s), var(--p)); }

@media (max-width: 768px) {
  .stepper { padding: 10px 12px; }
  .sline { width: 32px; }
  .slabel { font-size: 10px; margin-left: 4px; }
}
</style>

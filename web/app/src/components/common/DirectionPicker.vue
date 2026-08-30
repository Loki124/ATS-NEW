<script setup lang="ts">
import type { Direction } from '@/api/addCandidate'

const props = defineProps<{ modelValue: '' | Direction; hasOccupied: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: Direction): void }>()

const options: Array<{ value: Direction; icon: string; label: string; hint: string }> = [
  { value: 'pending', icon: '📥', label: '待分配', hint: '无需评分，直接进入' },
  { value: 'talent', icon: '📁', label: '人才库', hint: '无需评分，直接进入' },
  { value: 'position', icon: '🎯', label: '职位', hint: '需人岗匹配评分' },
]

function select(opt: Direction) {
  if (props.hasOccupied && opt !== 'pending') return
  emit('update:modelValue', opt)
}
</script>

<template>
  <div class="dir-opts">
    <div
      v-for="opt in options"
      :key="opt.value"
      :class="['dopt', { sel: modelValue === opt.value, off: hasOccupied && opt.value !== 'pending' }]"
      @click="select(opt.value)"
    >
      <div class="dicon">{{ opt.icon }}</div>
      <div class="dinfo">
        <div class="dlabel">{{ opt.label }}</div>
        <div class="dhint">{{ opt.hint }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dir-opts { display: flex; flex-direction: column; gap: 6px; }
.dopt {
  padding: 10px 14px;
  border: 2px solid var(--g3);
  border-radius: 12px;
  cursor: pointer;
  transition: 0.15s;
  background: var(--glass-bg-card);
  display: flex;
  align-items: center;
  gap: 10px;
}
.dopt:hover:not(.off) { border-color: var(--p); }
.dopt.sel { border-color: var(--p); background: var(--pl); }
.dopt.off { opacity: 0.4; cursor: not-allowed; background: var(--g1); }
.dicon { font-size: var(--fs-20); flex-shrink: 0; }
.dinfo { flex: 1; }
.dlabel { font-weight: 600; font-size: var(--fs-12); }
.dhint { font-size: var(--fs-10); color: var(--g5); }
</style>
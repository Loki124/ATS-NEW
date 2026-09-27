<script setup lang="ts">
// 2026-09-27: 改为 {id,label} 契约 —— 选中值(modelValue)是职位 id(uuid),
// 展示用 label。后端 bulk-create 按 position_id 查 Position, 必须传 id 而非标题。
const props = defineProps<{ items: { id: string; label: string }[]; modelValue: string[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string[]): void }>()

function toggle(id: string) {
  if (props.modelValue.includes(id)) {
    emit('update:modelValue', props.modelValue.filter((p) => p !== id))
  } else {
    emit('update:modelValue', [...props.modelValue, id])
  }
}
</script>

<template>
  <div class="pos-list">
    <div
      v-for="p in items"
      :key="p.id"
      :class="['pos-item', { sel: modelValue.includes(p.id) }]"
      @click="toggle(p.id)"
    >
      {{ p.label }}
    </div>
  </div>
</template>

<style scoped>
.pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.pos-item {
  padding: 6px var(--space-3);
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 11px;
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.pos-item:hover { border-color: var(--brand); }
.pos-item.sel { border-color: var(--brand); background: var(--brand-a12); color: var(--brand); font-weight: 500; }
</style>

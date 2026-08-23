<script setup lang="ts">
const props = defineProps<{ positions: string[]; modelValue: string[] }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string[]): void }>()

function toggle(pos: string) {
  if (props.modelValue.includes(pos)) {
    emit('update:modelValue', props.modelValue.filter((p) => p !== pos))
  } else {
    emit('update:modelValue', [...props.modelValue, pos])
  }
}
</script>

<template>
  <div class="pos-list">
    <div
      v-for="p in positions"
      :key="p"
      :class="['pos-item', { sel: modelValue.includes(p) }]"
      @click="toggle(p)"
    >
      {{ p }}
    </div>
  </div>
</template>

<style scoped>
.pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.pos-item {
  padding: 6px 12px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 11px;
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.pos-item:hover { border-color: var(--p); }
.pos-item.sel { border-color: var(--p); background: var(--pl); color: var(--p); font-weight: 500; }
</style>

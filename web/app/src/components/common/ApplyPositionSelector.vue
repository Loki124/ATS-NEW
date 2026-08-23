<script setup lang="ts">
const props = defineProps<{ positions: string[]; modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', val: string): void }>()

function select(pos: string) {
  emit('update:modelValue', pos)
}
</script>

<template>
  <div class="apply-pos">
    <div class="apply-pos-title">选择目标职位</div>
    <div class="apply-pos-list">
      <div
        v-for="p in positions"
        :key="p"
        :class="['apply-pos-item', { sel: modelValue === p }]"
        @click="select(p)"
      >
        {{ p }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.apply-pos {
  margin-top: 8px;
  padding: 10px 12px;
  background: var(--bl);
  border: 1px solid #BFDBFE;
  border-radius: 8px;
}
.apply-pos-title { font-size: 11px; font-weight: 600; color: #1E40AF; margin-bottom: 6px; }
.apply-pos-list { display: flex; flex-wrap: wrap; gap: 6px; }
.apply-pos-item {
  padding: 4px 10px;
  border: 1px solid var(--g3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 10px;
  background: var(--glass-bg-card);
  transition: 0.15s;
}
.apply-pos-item:hover { border-color: var(--p); }
.apply-pos-item.sel { border-color: var(--p); background: var(--pl); color: var(--p); font-weight: 500; }
</style>

<!--
  简易可拖拽列表（仅支持垂直拖拽排序）
  - 使用 HTML5 Drag and Drop API
  - v-model 双向绑定，change 事件在排序变化时触发
-->
<template>
  <div>
    <div
      v-for="(item, index) in items"
      :key="getKey(item)"
      :draggable="true"
      @dragstart="onDragStart($event, index)"
      @dragover.prevent="onDragOver($event, index)"
      @dragenter.prevent="onDragEnter(index)"
      @dragleave="onDragLeave(index)"
      @drop.prevent="onDrop($event, index)"
      @dragend="onDragEnd"
      :class="['draggable-item', { 'drag-over': dragOverIndex === index, 'dragging': dragIndex === index }]"
    >
      <slot :element="item" :index="index" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue: any[]
  itemKey?: string  // 用作 :key 的字段名，默认 'id'
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: any[]): void
}>()

const items = ref<any[]>([...props.modelValue])
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

watch(() => props.modelValue, (v) => {
  items.value = [...v]
}, { deep: true })

function getKey(item: any) {
  return props.itemKey ? item[props.itemKey] : item.id
}

function onDragStart(e: DragEvent, index: number) {
  dragIndex.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragOver(_e: DragEvent, index: number) {
  // 允许 drop
}

function onDragEnter(index: number) {
  dragOverIndex.value = index
}

function onDragLeave(index: number) {
  if (dragOverIndex.value === index) {
    dragOverIndex.value = null
  }
}

function onDrop(_e: DragEvent, index: number) {
  const from = dragIndex.value
  if (from === null || from === index) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  const newList = [...items.value]
  const [moved] = newList.splice(from, 1)
  newList.splice(index, 0, moved)
  items.value = newList
  emit('update:modelValue', newList)
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}
</script>

<style scoped>
.draggable-item {
  transition: all 0.2s;
  border-radius: 6px;
}
.draggable-item.dragging {
  opacity: 0.4;
}
.draggable-item.drag-over {
  background: #e6f7ff;
  box-shadow: 0 0 0 2px #1890ff inset;
}
</style>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="modalTitle"
    class="perm-code-modal"
    :bordered="false"
    style="width: 720px; max-width: 92vw"
    :mask-closable="true"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="pc-body">
      <template v-if="groups.length">
        <section v-for="g in groups" :key="g.module" class="pc-group">
          <header class="pc-group-head">
            <span class="pc-group-title">{{ g.moduleLabel }}</span>
            <span class="pc-group-count">{{ g.items.length }}</span>
          </header>
          <ul class="pc-list">
            <li v-for="it in g.items" :key="it.code" class="pc-item">
              <span class="pc-name">{{ it.name }}</span>
              <code class="pc-code" :title="it.code">{{ it.code }}</code>
            </li>
          </ul>
        </section>
      </template>
      <n-empty v-else description="该模板暂无权限码" />
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NModal, NEmpty } from 'naive-ui'
import { useResourceNames, groupPermissionCodesByModule, type GroupedCode } from '@/composables/useResourceNames'

const props = defineProps<{
  show: boolean
  /** 展示标题用的模板名（可选）。 */
  title?: string
  /** 待展示的权限码（英文码数组）。 */
  codes: string[]
}>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

// 复用资源名映射单例：打开时确保中文名就绪（缓存未命中按英文码兜底），
// 就绪后强制重算分组，避免先渲染成裸英文码。
const { ensureLoaded } = useResourceNames()
const groups = ref<GroupedCode[]>([])

const modalTitle = computed(() => (props.title ? `权限码明细 · ${props.title}` : '权限码明细'))

watch(
  [() => props.show, () => props.codes],
  async ([shown]) => {
    if (shown) {
      await ensureLoaded().catch(() => {})
      groups.value = groupPermissionCodesByModule(props.codes ?? [])
    }
  },
  { immediate: true },
)
</script>

<style scoped>
/* 居中模态内的权限码明细：按功能模块分组，中文名为主、英文码作副文本 */
.pc-body {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.pc-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.pc-group-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.pc-group-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  padding: 3px 10px;
  border-left: 3px solid var(--brand);
  background: var(--g1);
  border-radius: 4px;
}
.pc-group-count {
  font-size: 12px;
  line-height: 1;
  color: var(--ink-faint);
  background: var(--g1);
  border-radius: 999px;
  padding: 3px 8px;
}
.pc-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.pc-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 5px 8px;
  border-radius: 4px;
  transition: background var(--dur-fast, 120ms) ease;
}
.pc-item:hover {
  background: var(--g1);
}
.pc-name {
  color: var(--ink);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pc-code {
  flex: none;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-faint);
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

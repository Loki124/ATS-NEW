<template>
  <n-drawer
    :show="show"
    :width="460"
    placement="right"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-drawer-content :title="drawerTitle" :native-scrollbar="false">
      <template v-if="groups.length">
        <div v-for="g in groups" :key="g.module" class="code-group">
          <div class="code-group-title">{{ g.moduleLabel }}</div>
          <div v-for="it in g.items" :key="it.code" class="code-item">
            <span class="code-name">{{ it.name }}</span>
            <span class="code-raw" :title="it.code">{{ it.code }}</span>
          </div>
        </div>
      </template>
      <n-empty v-else description="该模板暂无权限码" />
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NDrawer, NDrawerContent, NEmpty } from 'naive-ui'
import { useResourceNames, groupPermissionCodesByModule, type GroupedCode } from '@/composables/useResourceNames'

const props = defineProps<{
  show: boolean
  /** 展示标题用的模板名（可选）。 */
  title?: string
  /** 待展示的权限码（英文码数组）。 */
  codes: string[]
}>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

// 复用资源名映射单例，确保中文名就绪后再分组渲染（缓存未就绪时按英文码兜底，
// 打开抽屉时触发一次 ensureLoaded，落库后强制重算）。
const { ensureLoaded } = useResourceNames()
const groups = ref<GroupedCode[]>([])

const drawerTitle = computed(() => (props.title ? `权限码明细 · ${props.title}` : '权限码明细'))

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
/* 按功能模块分组展示中文名，英文 code 作副文本/悬浮提示 */
.code-group { margin-bottom: var(--space-3); }
.code-group-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink, #1e293b);
  padding: 4px 8px;
  border-left: 3px solid var(--brand, #4f46e5);
  background: var(--surface-2, #f1f5f9);
  border-radius: 4px;
  margin-bottom: 6px;
}
.code-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 4px 8px;
}
.code-name { color: var(--ink, #1e293b); }
.code-raw {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--ink-soft, #94a3b8);
  max-width: 52%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

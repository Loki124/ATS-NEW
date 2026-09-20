<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.sceneEditor.title')"
    style="max-width: 520px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="scene-intro">
      <n-icon :component="InformationCircleOutline" color="var(--brand)" :size="14" />
      <span>{{ t('reasonLibrary.wizard.sceneEditor.subtitle') }}</span>
    </div>

    <div class="scene-grid">
      <label
        v-for="scene in SCENE_OPTIONS"
        :key="scene"
        class="scene-card"
        :class="{
          checked: localScenes.includes(scene),
          disabled: isConflict(scene),
        }"
      >
        <input
          type="checkbox"
          :checked="localScenes.includes(scene)"
          :disabled="isConflict(scene) && !localScenes.includes(scene)"
          @change="(e: any) => toggle(scene, e.target.checked)"
        />
        <span class="name">{{ scene }}</span>
        <n-tooltip v-if="isConflict(scene) && !localScenes.includes(scene)" placement="top">
          <template #trigger>
            <n-icon :component="WarningOutline" :size="14" color="var(--c-warning)" />
          </template>
          <span>{{ t('reasonLibrary.wizard.sceneEditor.conflict') }}<br />{{ allScenesUsage[scene]?.ruleName }}</span>
        </n-tooltip>
      </label>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">{{ t('reasonLibrary.common.cancel') }}</n-button>
        <n-button type="primary" @click="confirm">{{ t('reasonLibrary.common.confirm') }}</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * SceneEditorModal (T-19)
 * - 6 个场景多选 (与 SCENE_OPTIONS 对齐)
 * - 已被其他规则占用的场景: 显示 conflict tooltip, 未选时 disabled
 * - 已选场景不 disabled (允许取消本规则的引用)
 * - v-model:scenes 双向同步到父组件的 wizard.scenes
 */
import { ref, watch } from 'vue'
import { NModal, NButton, NSpace, NIcon, NTooltip } from 'naive-ui'
import { InformationCircleOutline, WarningOutline } from '@vicons/ionicons5'
import type { SceneKey } from '../../../types/reason-library'
import { SCENE_OPTIONS } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'

const props = defineProps<{
  show: boolean
  scenes: SceneKey[]
  allScenesUsage?: Partial<Record<SceneKey, { ruleId: string; ruleName: string }>>
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:scenes', v: SceneKey[]): void
}>()

const localScenes = ref<SceneKey[]>([])

watch(
  () => [props.show, props.scenes] as const,
  ([show, scenes]) => {
    if (show) localScenes.value = [...(scenes ?? [])]
  },
  { immediate: true },
)

function isConflict(scene: SceneKey): boolean {
  const usage = props.allScenesUsage?.[scene]
  // conflict 表示已被其他规则占用; 但本地已选的 (本规则在用) 不算冲突
  return !!usage && !localScenes.value.includes(scene)
}

function toggle(scene: SceneKey, checked: boolean) {
  const next = checked
    ? [...new Set([...localScenes.value, scene])]
    : localScenes.value.filter((s) => s !== scene)
  localScenes.value = next
}

function confirm() {
  emit('update:scenes', [...localScenes.value])
  emit('update:show', false)
}
</script>

<style scoped>
.scene-intro {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2) var(--space-3);
  background: var(--brand-soft);
  border-radius: var(--radius-md);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.6;
  margin-bottom: var(--space-3);
}

.scene-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.scene-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  background: #fff;
}
.scene-card:hover:not(.disabled) { border-color: var(--brand); background: var(--brand-tint); }
.scene-card.checked { border-color: var(--brand); background: var(--brand-soft); }
.scene-card.disabled { background: var(--g1); cursor: not-allowed; opacity: .7; }

.scene-card input {
  accent-color: var(--brand);
  width: 16px;
  height: 16px;
  cursor: pointer;
}
.scene-card input:disabled { cursor: not-allowed; }

.scene-card .name {
  flex: 1;
  font-size: var(--fs-13);
  color: var(--ink);
}
</style>

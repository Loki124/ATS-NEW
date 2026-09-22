<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.configRule')"
    style="max-width: 560px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="cfg-intro">
      <n-icon :component="InformationCircleOutline" color="var(--brand)" :size="14" />
      <span>{{ t('reasonLibrary.wizard.configRule.subtitle') }}</span>
    </div>

    <!-- 维度一: 入口(应用场景) -->
    <div class="cfg-section">
      <div class="cfg-section-title">{{ t('reasonLibrary.wizard.configRule.entry') }}</div>
      <div class="scene-grid">
        <label
          v-for="scene in SCENE_OPTIONS"
          :key="scene"
          class="scene-card"
          :class="{
            checked: localScenes.includes(scene),
            disabled: isSceneConflict(scene),
          }"
        >
          <input
            type="checkbox"
            :checked="localScenes.includes(scene)"
            :disabled="isSceneConflict(scene) && !localScenes.includes(scene)"
            @change="(e: any) => toggleScene(scene, e.target.checked)"
          />
          <span class="name">{{ scene }}</span>
          <n-tooltip
            v-if="isSceneConflict(scene) && !localScenes.includes(scene)"
            placement="top"
          >
            <template #trigger>
              <n-icon :component="WarningOutline" :size="14" color="var(--c-warning)" />
            </template>
            <span>{{ conflictText(scene) }}</span>
          </n-tooltip>
        </label>
      </div>
    </div>

    <!-- 维度二: 类型(社会招聘/校园招聘) -->
    <div class="cfg-section">
      <div class="cfg-section-title">{{ t('reasonLibrary.wizard.configRule.type') }}</div>
      <n-space :size="10">
        <label
          v-for="opt in RECRUIT_TYPE_OPTIONS"
          :key="opt.value"
          class="type-chip"
          :class="{
            checked: localTypes.includes(opt.value),
            disabled: isTypeConflict(opt.value),
          }"
        >
          <input
            type="checkbox"
            :checked="localTypes.includes(opt.value)"
            :disabled="isTypeConflict(opt.value) && !localTypes.includes(opt.value)"
            @change="(e: any) => toggleType(opt.value, e.target.checked)"
          />
          <span>{{ opt.label }}</span>
        </label>
      </n-space>
    </div>

    <!-- 可选标签上限 -->
    <div class="cfg-section">
      <div class="cfg-section-title">{{ t('reasonLibrary.wizard.configRule.maxTags') }}</div>
      <n-input-number
        v-model:value="localMax"
        :min="0"
        :max="100"
        style="width: 160px"
        clearable
        :placeholder="t('reasonLibrary.wizard.maxSelectableTagsPlaceholder')"
      />
      <p class="cfg-hint">{{ t('reasonLibrary.wizard.maxSelectableTagsHint') }}</p>
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
 * RuleConfigModal (2026-09-22 重构自 SceneEditorModal)
 * 将「应用场景(入口)」「招聘类型」「可选标签上限」三个配置合并为单一「配置规则」弹窗。
 *
 * 冲突模型: 规则应用范围 = 所选场景(入口) × 所选类型 的笛卡尔积。
 * 某个 (scene, type) 组合若已被「其他规则」占用, 则对应场景卡 / 类型芯片禁用并提示,
 * 后端 UNIQUE(scene, recruit_type) + 保存前 _check_scene_conflicts 仍保留为权威兜底。
 *
 * allScenesUsage key 形如 `${scene}|${recruitType}` → { ruleId, ruleName }。
 */
import { ref, watch } from 'vue'
import { NModal, NButton, NSpace, NIcon, NTooltip, NInputNumber } from 'naive-ui'
import { InformationCircleOutline, WarningOutline } from '@vicons/ionicons5'
import type { RecruitType, SceneKey } from '../../../types/reason-library'
import { SCENE_OPTIONS, RECRUIT_TYPE_OPTIONS } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'

const props = defineProps<{
  show: boolean
  ruleId: string
  scenes: SceneKey[]
  recruitTypes: RecruitType[]
  maxSelectableTags: number
  allScenesUsage?: Record<string, { ruleId: string; ruleName: string }>
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:scenes', v: SceneKey[]): void
  (e: 'update:recruitTypes', v: RecruitType[]): void
  (e: 'update:maxSelectableTags', v: number): void
}>()

const localScenes = ref<SceneKey[]>([])
const localTypes = ref<RecruitType[]>([])
const localMax = ref(5)

watch(
  () => [props.show, props.scenes, props.recruitTypes, props.maxSelectableTags] as const,
  ([show]) => {
    if (show) {
      localScenes.value = [...(props.scenes ?? [])]
      localTypes.value = [...(props.recruitTypes ?? [])]
      localMax.value = props.maxSelectableTags ?? 5
    }
  },
  { immediate: true },
)

function keyOf(scene: SceneKey, rt: RecruitType): string {
  return `${scene}|${rt}`
}

/** (scene, type) 是否已被「其他规则」占用 — 排除当前规则自身 */
function isPairConflict(scene: SceneKey, rt: RecruitType): boolean {
  const u = props.allScenesUsage?.[keyOf(scene, rt)]
  if (!u) return false
  // 新建规则 (ruleId 为空) 时, 任何已有占用都算冲突
  return props.ruleId ? u.ruleId !== props.ruleId : true
}

/** 场景卡禁用: 当前所选类型中, 该场景与「每一个」类型的组合都被占用 → 选它必冲突 */
function isSceneConflict(scene: SceneKey): boolean {
  if (!localTypes.value.length) return false
  return localTypes.value.every((rt) => isPairConflict(scene, rt))
}

/** 类型芯片禁用: 当前所选场景中, 该类型与「每一个」场景的组合都被占用 → 选它必冲突 */
function isTypeConflict(rt: RecruitType): boolean {
  if (!localScenes.value.length) return false
  return localScenes.value.every((s) => isPairConflict(s, rt))
}

function conflictText(scene: SceneKey): string {
  const taken = localTypes.value
    .filter((rt) => isPairConflict(scene, rt))
    .map((rt) => RECRUIT_TYPE_OPTIONS.find((o) => o.value === rt)?.label ?? rt)
  const names = taken
    .map((label) => props.allScenesUsage?.[keyOf(scene, (RECRUIT_TYPE_OPTIONS.find((o) => o.label === label)?.value) as RecruitType)]?.ruleName)
    .filter(Boolean)
  const who = [...new Set(names)].join('、')
  return `${scene} (${taken.join('/')}) 已被${who || '其他规则'}占用, 需先解除引用`
}

function toggleScene(scene: SceneKey, checked: boolean) {
  localScenes.value = checked
    ? [...new Set([...localScenes.value, scene])]
    : localScenes.value.filter((s) => s !== scene)
}

function toggleType(rt: RecruitType, checked: boolean) {
  localTypes.value = checked
    ? [...new Set([...localTypes.value, rt])]
    : localTypes.value.filter((r) => r !== rt)
}

function confirm() {
  emit('update:scenes', [...localScenes.value])
  emit('update:recruitTypes', [...localTypes.value])
  emit('update:maxSelectableTags', Math.max(0, localMax.value ?? 0))
  emit('update:show', false)
}
</script>

<style scoped>
.cfg-intro {
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

.cfg-section { margin-bottom: var(--space-4); }
.cfg-section-title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-2);
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
.scene-card input,
.type-chip input {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--border-hairline, #c4c8d4);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out);
}
.scene-card input:checked,
.type-chip input:checked { background: var(--brand); border-color: var(--brand); }
.scene-card input:checked::after,
.type-chip input:checked::after {
  content: '';
  position: absolute;
  left: 5px; top: 1.5px;
  width: 4px; height: 9px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.scene-card input:disabled,
.type-chip input:disabled { cursor: not-allowed; opacity: .5; }
.scene-card .name { flex: 1; font-size: var(--fs-13); color: var(--ink); }

.type-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border-hairline);
  border-radius: 999px;
  cursor: pointer;
  font-size: var(--fs-13);
  color: var(--ink);
  background: #fff;
  transition: all var(--duration-fast) var(--ease-out);
}
.type-chip:hover:not(.disabled) { border-color: var(--brand); background: var(--brand-tint); }
.type-chip.checked { border-color: var(--brand); background: var(--brand-soft); color: var(--brand-ink); }
.type-chip.disabled { background: var(--g1); cursor: not-allowed; opacity: .7; }

.cfg-hint {
  margin: 6px 0 0;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.5;
}
</style>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.configRuleLabel')"
    style="max-width: 560px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <!-- 维度整合: 校园招聘 / 社会招聘 并排两张独立卡片, 每张卡内列出全部应用场景 -->
    <div class="cfg-section">
      <div class="cfg-section-title">{{ t('reasonLibrary.wizard.configRule.entryWithType') }}</div>
      <p v-if="presetDefault" class="cfg-locked-note">
        {{ t('reasonLibrary.wizard.configRule.presetDefaultCoverNote') }}
      </p>
      <div class="recruit-grid">
        <div
          v-for="opt in RECRUIT_TYPE_OPTIONS"
          :key="opt.value"
          class="recruit-card"
          :class="[`type-${opt.value}`, { active: cardHasAny(opt.value) || presetDefault, disabled: cardBlocked(opt.value) && !presetDefault }]"
        >
          <div class="card-head">
            <span class="card-title">{{ opt.label }}</span>
            <span class="card-badge">{{ presetDefault ? SCENE_OPTIONS.length : cardSelectedCount(opt.value) }} / {{ SCENE_OPTIONS.length }}</span>
            <n-tooltip v-if="cardBlocked(opt.value)" placement="top">
              <template #trigger>
                <n-icon :component="WarningOutline" :size="14" color="var(--c-warning)" />
              </template>
              <span>{{ cardBlockedText(opt.value) }}</span>
            </n-tooltip>
          </div>
          <div class="scene-list">
            <label
              v-for="scene in SCENE_OPTIONS"
              :key="scene"
              class="scene-check"
              :class="{
                checked: presetDefault || isPairSelected(scene, opt.value),
                disabled: presetDefault || (isPairConflict(scene, opt.value) && !isPairSelected(scene, opt.value)),
              }"
            >
              <input
                type="checkbox"
                :checked="presetDefault || isPairSelected(scene, opt.value)"
                :disabled="presetDefault || (isPairConflict(scene, opt.value) && !isPairSelected(scene, opt.value))"
                @change="(e: any) => togglePair(scene, opt.value, e.target.checked)"
              />
              <span class="scene-label">{{ scene }}</span>
              <n-tooltip v-if="!presetDefault && isPairConflict(scene, opt.value)" placement="top">
                <template #trigger>
                  <n-icon :component="WarningOutline" :size="13" color="var(--c-error)" />
                </template>
                <span>{{ conflictTextFor(scene, opt.value) }}</span>
              </n-tooltip>
            </label>
          </div>
        </div>
      </div>
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
 * 将「应用场景(入口)」「招聘类型」「可选标签上限」合并为单一「配置规则」弹窗。
 *
 * 2026-09-23 交互反转 (v2): 改为「校园招聘 / 社会招聘」两张并排独立卡片,
 * 每张卡内完整列出全部 6 个应用场景供直接多选。两类入口各自独立、操作路径更短,
 * 选择状态互不干扰 (key = `${scene}|${recruitType}`, 卡片仅固定 recruitType 维度)。
 *
 * 规则应用范围 = 显式 (场景,类型) 成对集合 (SceneRecruitPair[]), 支持子集
 * (如「场景A仅校招、场景B仅社招」), 由后端 RuleSceneAssignment 逐行存储, UNIQUE 兜底。
 *
 * 冲突模型: 某 (scene, type) 若已被「其他规则」占用, 该组合复选框禁用并 tooltip 提示;
 * 后端 UNIQUE(scene, recruit_type) + _check_scene_conflicts 仍为权威兜底。
 * allScenesUsage key 形如 `${scene}|${recruitType}` → { ruleId, ruleName }。
 */
import { ref, watch } from 'vue'
import { NModal, NButton, NSpace, NIcon, NTooltip, NInputNumber, useMessage } from 'naive-ui'
import { WarningOutline } from '@vicons/ionicons5'
import type { RecruitType, SceneKey, SceneRecruitPair } from '../../../types/reason-library'
import { SCENE_OPTIONS, RECRUIT_TYPE_OPTIONS } from '../../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  ruleId: string
  /** 显式 (场景,类型) 成对 — 权威数据源 */
  scenePairs?: SceneRecruitPair[]
  /** 兼容旧调用: 无 scenePairs 时按 scenes×recruitTypes 笛卡尔积初始化 */
  scenes?: SceneKey[]
  recruitTypes?: RecruitType[]
  maxSelectableTags: number
  allScenesUsage?: Record<string, { ruleId: string; ruleName: string }>
  /** 是否「预置默认规则」: 覆盖全部场景×类型且不可调整, 弹窗内覆盖区只读锁定 */
  presetDefault?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:scenePairs', v: SceneRecruitPair[]): void
  (e: 'update:scenes', v: SceneKey[]): void
  (e: 'update:recruitTypes', v: RecruitType[]): void
  (e: 'update:maxSelectableTags', v: number): void
}>()

const message = useMessage()

/** 已选 (场景,类型) 成对, key = `${scene}|${rt}` */
const selectedPairs = ref<Set<string>>(new Set())
const localMax = ref(5)

function keyOf(scene: SceneKey, rt: RecruitType): string {
  return `${scene}|${rt}`
}

watch(
  () => [props.show, props.scenePairs, props.scenes, props.recruitTypes, props.maxSelectableTags] as const,
  ([show]) => {
    if (show) {
      const base: SceneRecruitPair[] = (props.scenePairs && props.scenePairs.length)
        ? props.scenePairs
        : [...(props.scenes ?? []).flatMap((s) =>
            (props.recruitTypes && props.recruitTypes.length
              ? props.recruitTypes
              : (['social'] as RecruitType[])
            ).map((rt) => ({ scene: s, recruitType: rt })),
          )]
      selectedPairs.value = new Set(base.map((p) => keyOf(p.scene, p.recruitType)))
      localMax.value = props.maxSelectableTags ?? 5
    }
  },
  { immediate: true },
)

/** (scene, type) 是否已被「其他规则」占用 — 排除当前规则自身 */
function isPairConflict(scene: SceneKey, rt: RecruitType): boolean {
  const u = props.allScenesUsage?.[keyOf(scene, rt)]
  if (!u) return false
  return props.ruleId ? u.ruleId !== props.ruleId : true
}

function isPairSelected(scene: SceneKey, rt: RecruitType): boolean {
  return selectedPairs.value.has(keyOf(scene, rt))
}

/** 该招聘类型卡片是否至少选中了一个场景 (用于卡片高亮) */
function cardHasAny(rt: RecruitType): boolean {
  return SCENE_OPTIONS.some((s) => isPairSelected(s, rt))
}

/** 该招聘类型卡片已选场景数 */
function cardSelectedCount(rt: RecruitType): number {
  return SCENE_OPTIONS.filter((s) => isPairSelected(s, rt)).length
}

/** 该招聘类型的全部场景都被其他规则占用且当前未选 → 整卡禁用 */
function cardBlocked(rt: RecruitType): boolean {
  return SCENE_OPTIONS.every((s) => isPairConflict(s, rt)) && !cardHasAny(rt)
}

function conflictTextFor(scene: SceneKey, rt: RecruitType): string {
  const u = props.allScenesUsage?.[keyOf(scene, rt)]
  const label = RECRUIT_TYPE_OPTIONS.find((o) => o.value === rt)?.label ?? rt
  return `${scene}（${label}）已被${u?.ruleName || '其他规则'}占用，需先解除引用`
}

function cardBlockedText(rt: RecruitType): string {
  const names = [
    ...new Set(
      SCENE_OPTIONS
        .filter((s) => isPairConflict(s, rt))
        .map((s) => props.allScenesUsage?.[keyOf(s, rt)]?.ruleName)
        .filter(Boolean),
    ),
  ].join('、')
  const label = RECRUIT_TYPE_OPTIONS.find((o) => o.value === rt)?.label ?? rt
  return `${label} 的全部场景已被${names || '其他规则'}占用，请从其他规则解除引用后再选`
}

function togglePair(scene: SceneKey, rt: RecruitType, checked: boolean) {
  const key = keyOf(scene, rt)
  if (checked) {
    if (isPairConflict(scene, rt)) {
      const label = RECRUIT_TYPE_OPTIONS.find((o) => o.value === rt)?.label ?? rt
      const rule = props.allScenesUsage?.[key]?.ruleName || '其他规则'
      message.warning(
        t('reasonLibrary.wizard.configRule.pairBlockedToast', { type: label, scene, rule }),
      )
      return
    }
    const next = new Set(selectedPairs.value)
    next.add(key)
    selectedPairs.value = next
  } else {
    const next = new Set(selectedPairs.value)
    next.delete(key)
    selectedPairs.value = next
  }
}

function confirm() {
  // 可选标签上限始终可改 (包括预置默认规则)
  emit('update:maxSelectableTags', Math.max(0, localMax.value ?? 0))
  // 预置默认规则: 应用范围(场景×类型)锁定、不可调整, 不回传覆盖数据,
  // 避免父组件据此改写「覆盖全部」的语义。
  if (!props.presetDefault) {
    const pairs: SceneRecruitPair[] = Array.from(selectedPairs.value).map((k) => {
      const [scene, rt] = k.split('|') as [SceneKey, RecruitType]
      return { scene, recruitType: rt }
    })
    const scenes = [...new Set(pairs.map((p) => p.scene))]
    const recruitTypes = [...new Set(pairs.map((p) => p.recruitType))]
    emit('update:scenePairs', pairs)
    emit('update:scenes', scenes)
    emit('update:recruitTypes', recruitTypes)
  }
  emit('update:show', false)
}
</script>

<style scoped>
.cfg-section { margin-bottom: var(--space-4); }
.cfg-section:last-child { margin-bottom: 0; }

/* 预置默认规则: 应用范围锁定提示条 */
.cfg-locked-note {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: var(--space-2) var(--space-3);
  font-size: var(--fs-12);
  line-height: 1.6;
  color: var(--brand-ink, var(--brand));
  background: var(--brand-soft, rgba(32, 128, 240, 0.1));
  border: 1px solid var(--brand-tint, rgba(32, 128, 240, 0.2));
  border-radius: var(--radius-md);
}
.cfg-section-title {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: var(--space-2);
}

/* 两张招聘类型卡片并排, 窄屏自动堆叠 */
.recruit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}
@media (max-width: 480px) {
  .recruit-grid { grid-template-columns: 1fr; }
}

/* 每张卡片以自身 accent 变量驱动, 形成视觉区分 */
.recruit-card {
  --accent: var(--brand);
  --accent-soft: var(--brand-soft);
  --accent-tint: var(--brand-tint);
  --accent-ink: var(--brand-ink);
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border-hairline);
  border-top: 3px solid var(--accent);
  border-radius: var(--radius-md);
  background: #fff;
  transition: all var(--duration-fast) var(--ease-out);
}
.recruit-card.type-social {
  --accent: #2080f0;
  --accent-soft: rgba(32, 128, 240, 0.12);
  --accent-tint: rgba(32, 128, 240, 0.06);
  --accent-ink: #2080f0;
}
.recruit-card.type-campus {
  --accent: #18a058;
  --accent-soft: rgba(24, 160, 88, 0.12);
  --accent-tint: rgba(24, 160, 88, 0.06);
  --accent-ink: #18a058;
}
.recruit-card:hover:not(.disabled) { background: var(--accent-tint); }
.recruit-card.active { border-color: var(--accent); background: var(--accent-soft); }
.recruit-card.disabled { background: var(--g1); cursor: not-allowed; opacity: .7; }

.card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border-hairline);
}
.card-title {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-13);
  font-weight: 700;
  color: var(--accent-ink);
}
.card-badge {
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--accent-ink);
  background: var(--accent-soft);
  border-radius: 999px;
  padding: 1px 8px;
}

.scene-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.scene-check {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--fs-12);
  color: var(--ink);
  background: #fff;
  transition: all var(--duration-fast) var(--ease-out);
}
.scene-check:hover:not(.disabled) { border-color: var(--accent); background: var(--accent-tint); }
.scene-check.checked { border-color: var(--accent); background: var(--accent-soft); color: var(--accent-ink); }
.scene-check.disabled { background: var(--g1); cursor: not-allowed; opacity: .7; }
.scene-label { flex: 1; min-width: 0; line-height: 1.4; }

/* 复选框自定义 (暗色安全): appearance:none + 主题变量 bg/border, 不依赖浏览器默认渲染 */
.recruit-card input[type='checkbox'] {
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
.recruit-card input[type='checkbox']:checked { background: var(--accent); border-color: var(--accent); }
.recruit-card input[type='checkbox']:checked::after {
  content: '';
  position: absolute;
  left: 5px; top: 1.5px;
  width: 4px; height: 9px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.recruit-card input[type='checkbox']:disabled { cursor: not-allowed; opacity: .5; }
</style>

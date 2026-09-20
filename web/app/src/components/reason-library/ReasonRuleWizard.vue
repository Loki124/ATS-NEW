<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.title')"
    style="max-width: 920px; width: 92vw;"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="onShowChange"
  >
    <!-- 头部信息 -->
    <div v-if="wizard" class="wizard-head glass-card">
      <div class="wizard-title-row">
        <h4 class="wizard-title">{{ wizard.name || t('reasonLibrary.wizard.title') }}</h4>
        <n-tag v-if="wizard.isSystem" size="small" type="warning" bordered>
          {{ t('reasonLibrary.rules.col.systemBadge') }}
        </n-tag>
        <div class="wizard-meta">
          <span class="meta-label">{{ t('reasonLibrary.wizard.scenes') }}：</span>
          <n-space size="4" v-if="wizard.scenes.length">
            <n-tag v-for="s in wizard.scenes" :key="s" size="small" type="info" bordered>{{ s }}</n-tag>
          </n-space>
          <span v-else class="rl-empty-tag">{{ t('reasonLibrary.rules.col.emptyScenes') }}</span>
          <n-button size="tiny" @click="openSceneEditor" style="margin-left: 8px;">
            <template #icon><n-icon :component="PencilOutline" /></template>
            {{ t('reasonLibrary.wizard.editScenes') }}
          </n-button>
        </div>
      </div>

      <!-- 步骤指示 -->
      <div class="wizard-steps">
        <div
          v-for="(s, i) in steps"
          :key="s.key"
          class="step"
          :class="{ on: step === i + 1, done: step > i + 1 }"
          @click="gotoStep(i + 1)"
        >
          <span class="num">{{ i + 1 }}</span>
          <span class="label">{{ s.label }}</span>
        </div>
      </div>
    </div>

    <!-- Body: 三步切换 -->
    <div v-if="wizard" class="wizard-body">
      <Step1Categories
        v-show="step === 1"
        v-model:categories="wizard.categories"
        :is-super-admin="isSuperAdmin"
      />
      <Step2Assignments
        v-show="step === 2"
        v-model:categories="wizard.categories"
        :available-tags="allTags"
      />
      <Step3Preview
        v-show="step === 3"
        :wizard="wizard"
        :all-tags="allTags"
      />
    </div>

    <!-- Footer -->
    <template #footer>
      <n-space justify="space-between" align="center">
        <n-button @click="onCancel">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          {{ t('reasonLibrary.wizard.actions.cancel') }}
        </n-button>
        <n-space>
          <n-button v-if="step > 1" @click="gotoStep(step - 1)">
            <template #icon><n-icon :component="ChevronBackOutline" /></template>
            {{ t('reasonLibrary.wizard.actions.prev') }}
          </n-button>
          <n-button v-if="step < 3" type="primary" @click="gotoStep(step + 1)">
            {{ nextLabel }}
            <template #icon><n-icon :component="ChevronForwardOutline" /></template>
          </n-button>
          <n-button v-else type="primary" :loading="saving" @click="onSave">
            <template #icon><n-icon :component="CheckmarkOutline" /></template>
            {{ t('reasonLibrary.wizard.actions.save') }}
          </n-button>
        </n-space>
      </n-space>
    </template>

    <!-- 子弹窗 -->
    <SceneEditorModal
      v-model:show="sceneEditorShow"
      v-model:scenes="wizard!.scenes"
      :all-scenes-usage="sceneUsage"
    />
  </n-modal>
</template>

<script setup lang="ts">
/**
 * ReasonRuleWizard (T-18) — 三步向导
 *
 * - 大尺寸弹窗 (max-width: 920px), 内部 n-modal-content 自带滚动
 * - 头部: 规则名 + 系统预置 + 应用场景 tag + 编辑按钮
 * - n-steps: 1) 分类树 (Step1)  2) 标签分配 (Step2)  3) 预览 (Step3)
 * - 三步共享同一份 WizardPayload (v-model:categories 双向)
 *
 * 数据流:
 *   - show=true + ruleId=null → createRule() 创建空规则 → 进入 wizard (id 已生成)
 *   - show=true + ruleId=<id>  → getRule 拉详情 → 灌入 wizard
 *   - 保存 → wizardSave(id, payload, ifMatch=updatedAt)
 */
import { ref, computed, watch } from 'vue'
import {
  NModal, NButton, NSpace, NTag, NIcon, useMessage, useDialog,
} from 'naive-ui'
import {
  ChevronBackOutline, ChevronForwardOutline, ArrowBackOutline,
  CheckmarkOutline, PencilOutline,
} from '@vicons/ionicons5'
import {
  createRule, getRule, wizardSave, extractReasonApiError, listTags,
} from '../../api/reason-library'
import type {
  ReasonTag, RuleCategory, SceneKey, SceneRule, WizardPayload,
} from '../../types/reason-library'
import { BIZ_CODE } from '../../types/reason-library'
import { t } from '../../locales/zh-CN'
import Step1Categories from './wizard/Step1Categories.vue'
import Step2Assignments from './wizard/Step2Assignments.vue'
import Step3Preview from './wizard/Step3Preview.vue'
import SceneEditorModal from './wizard/SceneEditorModal.vue'

const props = defineProps<{
  show: boolean
  ruleId: string | null
  isSuperAdmin?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved', rule: SceneRule): void
}>()

const message = useMessage()
const dialog = useDialog()

// ============= 内部状态 =============
const wizard = ref<WizardPayload | null>(null)
const step = ref(1)
const saving = ref(false)
const loading = ref(false)

// 标签池 (Step2/Step3 用) — 与 wizard 解耦, 仅读
const allTags = ref<ReasonTag[]>([])

// 场景占用情况 (SceneEditor 用: 哪些 scene 被其他规则占用)
const sceneUsage = ref<Partial<Record<SceneKey, { ruleId: string; ruleName: string }>>>({})

// 步骤定义
const steps = [
  { key: 'cat', label: t('reasonLibrary.wizard.step1.label') },
  { key: 'tag', label: t('reasonLibrary.wizard.step2.label') },
  { key: 'prev', label: t('reasonLibrary.wizard.step3.label') },
]

const nextLabel = computed(() =>
  step.value === 1
    ? t('reasonLibrary.wizard.actions.nextStep1')
    : step.value === 2
      ? t('reasonLibrary.wizard.actions.nextStep2')
      : t('reasonLibrary.wizard.actions.next'),
)

const sceneEditorShow = ref(false)

// ============= 加载逻辑 =============
watch(
  () => [props.show, props.ruleId] as const,
  async ([show, ruleId]) => {
    if (!show) return
    step.value = 1
    loading.value = true
    try {
      // 1. 加载标签池 (后台一次性拉满)
      const tagRes = await listTags({ page: 1, pageSize: 500 })
      allTags.value = tagRes.items ?? []
      // 2. 编辑: 拉详情; 新建: 创建空规则
      if (ruleId) {
        const rule = await getRule(ruleId)
        wizard.value = toWizard(rule)
      } else {
        const newRule = await createRule({ name: '新建规则' })
        wizard.value = toWizard(newRule)
      }
    } catch (e: any) {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
      emit('update:show', false)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

/** SceneRule → WizardPayload */
function toWizard(rule: SceneRule): WizardPayload {
  return {
    id: rule.id,
    name: rule.name,
    description: rule.description,
    enabled: rule.enabled,
    isSystem: rule.isSystem,
    scenes: [...(rule.scenes ?? [])],
    categories: deepCloneCategories(rule.categories ?? []),
    updatedAt: rule.updatedAt,
  }
}

function deepCloneCategories(cats: RuleCategory[]): RuleCategory[] {
  return cats.map((c) => ({
    id: c.id,
    parentId: c.parentId,
    name: c.name,
    level: c.level,
    order: c.order,
    allowCustom: c.allowCustom,
    tags: (c.tags ?? []).map((t) => ({ ...t })),
  }))
}

// ============= 切换步骤 =============
function gotoStep(n: number) {
  if (n < 1 || n > 3) return
  // Step1 → Step2: 校验至少 1 个末级分类
  if (step.value === 1 && n === 2) {
    if (!wizard.value) return
    const cats = wizard.value.categories
    if (cats.length === 0) {
      message.warning(t('reasonLibrary.wizard.emptyCategory'))
      return
    }
    const leafCount = countLeaf(cats)
    if (leafCount === 0) {
      message.warning(t('reasonLibrary.wizard.intro.step2'))
      return
    }
  }
  step.value = n
}

function openSceneEditor() {
  sceneEditorShow.value = true
}

function countLeaf(cats: RuleCategory[]): number {
  const childMap = new Map<string, RuleCategory[]>()
  cats.forEach((c) => {
    const pid = c.parentId || ''
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(c)
  })
  return cats.filter((c) => !childMap.get(c.id)?.length).length
}

// ============= 保存 =============
async function onSave() {
  if (!wizard.value) return
  if (!wizard.value.name.trim()) {
    message.warning(t('reasonLibrary.tags.modal.nameRequired'))
    gotoStep(1)
    return
  }
  if (wizard.value.categories.length === 0) {
    message.warning(t('reasonLibrary.wizard.emptyCategory'))
    gotoStep(1)
    return
  }
  saving.value = true
  try {
    const payload: WizardPayload = JSON.parse(JSON.stringify(wizard.value))
    // wizardSave 内部会自动调用 toWizardSavePayload 把 WizardPayload
    // (含 categories[*].tags + parentId) 转为后端 WizardSaveSerializer
    // 期望的 snake_case + tag_ids + parent_client_id 形态 (T-BF-02 BugFix)
    const result = await wizardSave(payload.id, payload, payload.updatedAt)
    message.success(t('reasonLibrary.common.success'))
    emit('saved', result)
  } catch (e: any) {
    if (e?.code === BIZ_CODE.OPTIMISTIC_LOCK_FAILED) {
      message.error(t('reasonLibrary.errors.OPTIMISTIC_LOCK_FAILED'))
    } else if (e?.code === BIZ_CODE.RULE_SCENE_CONFLICT) {
      message.error(t('reasonLibrary.errors.RULE_SCENE_CONFLICT'))
    } else if (e?.code === BIZ_CODE.CATEGORY_LEVEL_EXCEED) {
      message.error(t('reasonLibrary.errors.CATEGORY_LEVEL_EXCEED'))
    } else {
      message.error(extractReasonApiError(e, t('reasonLibrary.common.failed')))
    }
  } finally {
    saving.value = false
  }
}

// ============= 退出/关闭 =============
function onCancel() {
  dialog.warning({
    title: t('reasonLibrary.wizard.actions.cancel'),
    content: t('reasonLibrary.common.unsaved'),
    positiveText: t('reasonLibrary.common.confirm'),
    negativeText: t('reasonLibrary.common.cancel'),
    onPositiveClick: () => emit('update:show', false),
  })
}

function onShowChange(v: boolean) {
  if (!v) {
    wizard.value = null
    step.value = 1
  }
  emit('update:show', v)
}
</script>

<style scoped>
.wizard-head {
  background: var(--glass-bg-card);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
}
.wizard-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}
.wizard-title {
  margin: 0;
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
}
.wizard-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
.meta-label { font-weight: 500; }
.rl-empty-tag {
  font-size: var(--fs-11);
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--g1);
  color: var(--ink-faint);
}

/* 步骤指示 */
.wizard-steps {
  display: flex;
  align-items: center;
  gap: 0;
}
.step {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: 1;
  font-size: var(--fs-12);
  color: var(--ink-faint);
  cursor: pointer;
  position: relative;
  user-select: none;
  transition: color var(--duration-fast) var(--ease-out);
}
.step:not(:last-child)::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-hairline);
  margin: 0 12px;
}
.step.done:not(:last-child)::after { background: var(--c-success-soft); }
.step .num {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--g1);
  color: var(--ink-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-12);
  font-weight: 600;
  flex-shrink: 0;
  transition: all var(--duration-base) var(--ease-out);
}
.step.on .num {
  background: var(--brand);
  color: #fff;
}
.step.on {
  color: var(--brand);
  font-weight: 600;
}
.step.done .num {
  background: var(--c-success-soft);
  color: var(--c-success-deep);
}
.step.done { color: var(--c-success-deep); }

.wizard-body {
  min-height: 320px;
  max-height: 56vh;
  overflow-y: auto;
  padding: 4px 4px 4px 0;
}
</style>

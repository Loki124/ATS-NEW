<template>
  <n-modal
    class="rrw-modal"
    :show="show"
    preset="card"
    :closable="false"
    style="max-width: 920px; width: 92vw;"
    :mask-closable="false"
    :bordered="false"
    :close-on-esc="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="onShowChange"
  >
    <!-- 标题行: 规则名称 + 系统/预置标签 + 应用场景 + 配置规则按钮；移除右侧关闭按钮 -->
    <template #header>
      <div class="wizard-titlebar">
        <div class="wizard-title-left">
          <span class="wizard-title">{{ wizard?.name || t('reasonLibrary.wizard.title') }}</span>
          <n-tag v-if="wizard?.code" size="tiny" type="default" bordered class="wizard-code-tag">
            {{ wizard.code }}
          </n-tag>
          <n-tag v-if="wizard?.version != null" size="tiny" type="default" bordered class="wizard-version-tag">
            v{{ wizard.version }}
          </n-tag>
          <n-tag v-if="wizard?.isSystem" size="small" type="warning" bordered>
            {{ t('reasonLibrary.rules.col.systemBadge') }}
          </n-tag>
          <n-space v-if="wizard?.isPresetDefault" :size="4">
            <n-tag size="small" type="primary" bordered>{{ t('reasonLibrary.rules.col.presetDefaultScope') }}</n-tag>
          </n-space>
          <n-space v-else-if="wizard?.scenes?.length" :size="4">
            <n-tag v-for="s in wizard.scenes" :key="s" size="small" type="info" bordered>{{ s }}</n-tag>
          </n-space>
          <span v-else class="rl-empty-tag">{{ t('reasonLibrary.rules.col.emptyScenes') }}</span>
        </div>
        <n-space :size="6">
          <n-button v-if="ruleId" size="tiny" @click="openVersionHistory">
            <template #icon><n-icon :component="TimeOutline" /></template>
            {{ t('reasonLibrary.wizard.history') }}
          </n-button>
          <n-button size="tiny" @click="openRuleConfig">
            <template #icon><n-icon :component="SettingsOutline" /></template>
            {{ t('reasonLibrary.wizard.configRuleLabel') }}
          </n-button>
        </n-space>
      </div>
    </template>
    <n-spin :show="loading" :description="t('reasonLibrary.common.loading')">
      <!-- 步骤指示（置于标题栏下方, 不随内容滚动） -->
      <div v-if="wizard" class="wizard-steps">
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

      <!-- Body: 三步切换 -->
      <div v-if="wizard" class="wizard-body">
        <Step1Categories
          v-show="step === 1"
          v-model:categories="wizard.categories"
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
          @update:color="onCategoryColorChange"
          @update:modal-title="onModalTitleChange"
        />
      </div>
    </n-spin>

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

    <!-- 统一「配置规则」弹窗: 入口(场景) + 类型 + 可选标签上限 -->
    <RuleConfigModal
      v-if="wizard"
      v-model:show="ruleConfigShow"
      v-model:name="wizard.name"
      v-model:enabled="wizard.enabled"
      v-model:scene-pairs="wizard.scenePairs"
      v-model:scenes="wizard.scenes"
      v-model:recruit-types="wizard.recruitTypes"
      v-model:max-selectable-tags="wizard.maxSelectableTags"
      :rule-id="ruleId || ''"
      :all-scenes-usage="sceneUsage"
      :preset-default="wizard?.isPresetDefault ?? false"
    />

    <!-- 规则历史版本列表 + 回滚 -->
    <RuleVersionHistoryModal
      v-if="ruleId"
      v-model:show="versionHistoryShow"
      :rule-id="ruleId"
      :current-version="wizard?.version"
      @rollbacked="onVersionRollbacked"
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
 *   - 保存 → wizardSave(id, payload)
 */
import { ref, computed, watch } from 'vue'
import {
  NModal, NButton, NSpace, NTag, NIcon, useMessage, useDialog, NSpin,
} from 'naive-ui'
import {
  ChevronBackOutline, ChevronForwardOutline, ArrowBackOutline,
  CheckmarkOutline, SettingsOutline, TimeOutline,
} from '@vicons/ionicons5'
import {
  createRule, getRule, wizardSave, deleteRule, extractReasonApiError, listTags, getSceneConfig,
} from '../../api/reason-library'
import type {
  ReasonTag, RuleCategory, RecruitType, SceneRecruitPair, SceneRule, WizardPayload,
} from '../../types/reason-library'
import { BIZ_CODE } from '../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
import Step1Categories from './wizard/Step1Categories.vue'
import Step2Assignments from './wizard/Step2Assignments.vue'
import Step3Preview from './wizard/Step3Preview.vue'
import RuleConfigModal from './wizard/RuleConfigModal.vue'
import RuleVersionHistoryModal from './wizard/RuleVersionHistoryModal.vue'

const props = defineProps<{
  show: boolean
  ruleId: string | null
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

// 场景(入口)+类型 占用情况 — key 为 `${scene}|${recruitType}`, 供 RuleConfigModal 禁用「已被其他规则占用」的组合
const sceneUsage = ref<Record<string, { ruleId: string; ruleName: string }>>({})

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

// 统一「配置规则」弹窗状态
const ruleConfigShow = ref(false)

function openRuleConfig() {
  ruleConfigShow.value = true
}

// 历史版本弹窗状态
const versionHistoryShow = ref(false)

function openVersionHistory() {
  versionHistoryShow.value = true
}

/** 历史版本回滚成功: 用返回的最新规则原地重建向导草稿 (分类树/场景/名称/状态) */
async function onVersionRollbacked(rule: SceneRule) {
  // 重新拉一次场景占用, 回滚可能改变了 (场景,类型) 组合 → RuleConfigModal 禁用判断需最新
  try {
    const cfg = await getSceneConfig()
    const usage: Record<string, { ruleId: string; ruleName: string }> = {}
    for (const it of cfg.items) {
      if (it.ruleId) usage[`${it.scene}|${it.recruitType}`] = { ruleId: it.ruleId, ruleName: it.ruleName ?? '' }
    }
    sceneUsage.value = usage
  } catch {
    // 占用刷新失败不阻断回滚结果展示
  }
  wizard.value = toWizard(rule)
  message.success(t('reasonLibrary.wizard.history.rollbackApplied'))
}

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
      // 1.5 加载场景占用情况 — 供 RuleConfigModal 禁用「已被其他规则占用」的 (场景,类型) 组合,
      //    避免用户误选后在保存时触发后端 RULE_SCENE_CONFLICT(409)。
      //    key 形如 `${scene}|${recruitType}`。
      try {
        const cfg = await getSceneConfig()
        const usage: Record<string, { ruleId: string; ruleName: string }> = {}
        for (const it of cfg.items) {
          if (it.ruleId) usage[`${it.scene}|${it.recruitType}`] = { ruleId: it.ruleId, ruleName: it.ruleName ?? '' }
        }
        sceneUsage.value = usage
      } catch {
        sceneUsage.value = {}
      }
      // 2. 编辑: 拉详情; 新建: 仅在内存构造草稿, 不预建规则
      //    (修复「打开向导又取消 → 残留『新建规则』垃圾数据」)
      if (ruleId) {
        const rule = await getRule(ruleId)
        wizard.value = toWizard(rule)
      } else {
        wizard.value = emptyWizardPayload()
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
  // 详情接口以 camelCase 返回 sceneAssignments: [{scene, recruitType}]
  const sa = (rule as any).sceneAssignments ?? []
  // 应用范围以「显式 (场景,类型) 成对」为权威 (取代 scenes×recruitTypes 笛卡尔积)
  const scenePairs: SceneRecruitPair[] = sa.map((a: any) => ({
    scene: a.scene,
    recruitType: a.recruitType,
  }))
  const pairScenes = [...new Set(scenePairs.map((p) => p.scene))]
  const pairTypes = [...new Set(scenePairs.map((p) => p.recruitType))]
  return {
    id: rule.id,
    code: (rule as any).code,
    version: (rule as any).version,
    name: rule.name,
    description: rule.description,
    enabled: rule.enabled,
    isSystem: rule.isSystem,
    isPresetDefault: !!(rule as any).isPresetDefault,
    scenes: pairScenes.length ? pairScenes : [...(rule.scenes ?? [])],
    recruitTypes: pairTypes.length ? pairTypes : ['social'],
    scenePairs,
    maxSelectableTags: rule.maxSelectableTags ?? 5,
    modalTitle: (rule as any).modalTitle ?? '',
    categories: deepCloneCategories(rule.categories ?? [], allTags.value),
    updatedAt: rule.updatedAt,
  }
}

/** 新建规则的内存草稿 (不落库, 保存时才真正 createRule) */
function emptyWizardPayload(): WizardPayload {
  return {
    id: '',
    name: '',
    description: '',
    enabled: true,
    isSystem: false,
    isPresetDefault: false,
    scenes: [],
    recruitTypes: ['social'],
    scenePairs: [],
    maxSelectableTags: 5,
    modalTitle: '',
    categories: [],
    updatedAt: undefined,
  }
}

/**
 * 深拷贝分类树 (用于向导草稿)。
 * ⚠️ 关键: 后端序列化仅下发 tagIds (camelCase), 不返回完整 tags 对象。
 * 必须从已加载的标签池 allTags 按 id 重建 tags, 否则编辑已有规则时
 * 所有已分配标签会被静默清空 (→ Step2 显示"0 条"、Step3 预览整棵树塌缩)。
 */
function deepCloneCategories(cats: RuleCategory[], allTags: ReasonTag[]): RuleCategory[] {
  const tagById = new Map(allTags.map((t) => [t.id, t]))
  return cats.map((c) => {
    const rawIds = c.tagIds && c.tagIds.length ? c.tagIds : (c.tags ?? []).map((t) => t.id)
    const tags = rawIds
      .map((id) => tagById.get(id))
      .filter((t): t is ReasonTag => !!t)
    return {
      id: c.id,
      parentId: c.parentId,
      name: c.name,
      level: c.level,
      order: c.order,
      allowCustom: c.allowCustom,
      color: c.color || '',
      tags,
    }
  })
}

// ============= 区块颜色回写 (Step3 模块三) =============
/** Step3 调色板/自定义色变更 → 写入 wizard.categories[i].color (空串=未自定义/继承) */
function onCategoryColorChange(payload: { catId: string; color: string }) {
  const w = wizard.value
  if (!w) return
  const cat = w.categories.find((c) => c.id === payload.catId)
  if (cat) cat.color = payload.color || ''
}

/** 模拟弹窗标题变更: 写入 wizard.modalTitle (保存时随规则落库 modal_title) */
function onModalTitleChange(v: string) {
  const w = wizard.value
  if (!w) return
  w.modalTitle = v ?? ''
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
    let result: SceneRule
    if (payload.id) {
      // 编辑: 直接原子保存 (单人场景无乐观锁)
      result = await wizardSave(payload.id, payload)
    } else {
      // 新建: 先建规则头, 再原子保存 (创建与保存合一)
      // 若保存失败, 回滚刚建的规则头, 避免留下『新建规则』垃圾数据
      const created = await createRule({ name: payload.name, description: payload.description })
      try {
        result = await wizardSave(created.id, payload)
      } catch (saveErr) {
        await deleteRule(created.id).catch(() => {})
        throw saveErr
      }
    }
    message.success(t('reasonLibrary.common.success'))
    emit('saved', result)
  } catch (e: any) {
    if (e?.code === BIZ_CODE.OPTIMISTIC_LOCK_FAILED) {
      // 仅在 ENABLE_OPTIMISTIC_LOCK=true (多人协作) 时才可能抛出
      message.error(t('reasonLibrary.errors.OPTIMISTIC_LOCK_FAILED'))
    } else if (e?.code === BIZ_CODE.RULE_SCENE_CONFLICT) {
      message.error(t('reasonLibrary.errors.RULE_SCENE_CONFLICT'))
    } else if (e?.code === BIZ_CODE.CATEGORY_LEVEL_EXCEED) {
      message.error(t('reasonLibrary.errors.CATEGORY_LEVEL_EXCEED'))
    } else if (e?.code === BIZ_CODE.TAG_ALREADY_ASSIGNED) {
      // Item4: 同一标签不可跨分类重复 — 后端 40902 拦截
      message.error(t('reasonLibrary.wizard.tagPicker.assignedElsewhere'))
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
    onPositiveClick: () => {
      // 确认退出时同步重置内部状态: 不再只依赖 onShowChange(它仅在 n-modal
      // 内部交互触发 mask/esc 时回调, 而这里 emit 后父组件更新 show 的链路
      // 任何一环异常——如 dev HMR 半更新导致旧闭包 emit 失联——都会让向导
      // 残留旧编辑状态。先清空内容再请求关闭, 保证『确定退出』必然生效。
      wizard.value = null
      step.value = 1
      emit('update:show', false)
    },
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
.wizard-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.wizard-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.wizard-title {
  margin: 0;
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
}
.wizard-code-tag {
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.wizard-version-tag {
  font-family: var(--font-mono, monospace);
  font-weight: 600;
}
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
  margin-bottom: var(--space-3);
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
  /* 需求: 大屏使用固定「最大高度上限」, 高度不再随步骤内容伸缩 → 消除切换抖动。
     单一确定值 (非 min/max 区间), 配合 n-modal 垂直居中避免上下跳动。
     padding 归零: 消除步骤区上/右/下 4px 留白 (原先 4px 4px 4px 0)。 */
  height: min(640px, 72vh);
  overflow-y: auto;
  padding: 0;
}
/* 小屏 (视口高度 < 760px): 弹窗撑满高度, 内容在 body 内滚动 */
@media (max-height: 760px) {
  .wizard-body {
    height: calc(100vh - 200px);
  }
}
</style>

<!-- 非 scoped: 向导主弹窗容器背景改为不透明白, 去除 0.96 半透底透出遮罩的灰感 (scoped :deep 无法命中组件根 n-modal; !important 压过 naive 的 background 简写) -->
<style>
.rrw-modal .n-card,
.n-card.n-card--content-soft-segmented.n-card--footer-soft-segmented {
  background-color: var(--surface) !important;
}
</style>

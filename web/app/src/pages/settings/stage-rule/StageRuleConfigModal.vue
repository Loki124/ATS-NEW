<template>
  <n-modal
    :show="show"
    class="stage-rule-config-modal"
    preset="card"
    :title="undefined"
    :closable="false"
    style="width: 840px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v: boolean) => !v && onRequestClose()"
    @after-leave="resetTransient"
  >
    <template #header>
      <div class="hero">
        <div class="hero__icon">
          <n-icon :component="SettingsOutline" size="20" />
        </div>
        <h2 class="hero__title">
          {{ t('pages.settings.stage-rule.StageRuleConfigModal.s3') }}
          <small class="hero__object">—— {{ stage?.name || t('pages.settings.stage-rule.StageRuleConfigModal.s10') }}</small>
        </h2>
        <span class="hero__tip" :aria-label="t('pages.settings.stage-rule.StageRuleConfigModal.s1')">
          <n-icon :component="FlashOutline" size="12" /> {{ t('pages.settings.stage-rule.StageRuleConfigModal.s1') }}
        </span>
        <button class="hero__close" type="button" :aria-label="t('pages.settings.stage-rule.StageRuleConfigModal.s2')" :disabled="saving" @click="onRequestClose">
          <n-icon :component="CloseOutline" size="20" />
        </button>
      </div>
    </template>

    <n-spin :show="loading">
      <div class="rule-config-body">
        <div v-if="loadError" class="load-error">
          <n-alert type="error" :title="loadError">
            <n-button size="small" :disabled="saving" @click="reload">{{ t('pages.settings.stage-rule.StageRuleConfigModal.s4') }}</n-button>
          </n-alert>
        </div>
        <div v-else class="rule-config-flat">
          <EntryConditionCard
            :rules="entryRules"
            :module-on="entryEnabled"
            @update:module-on="(v: boolean) => (entryEnabled = v)"
            @configure="onEntryConfigure"
            @edit="(r: EntryConditionRule) => entryModal?.open(r)"
            @toggle="toggleEntry"
            @remove="removeEntry"
          />
          <DefaultHandlerCard
            :form="form"
            :demand-person-fields="demandPersonFields"
            :position-person-fields="positionPersonFields"
            :user-options="handlerUserOptions"
            @update:default-handler-type="(v: any) => (form.defaultHandlerType = v)"
            @update:default-handler-fields="(v: string[]) => (form.defaultHandlerFields = v)"
            @update:default-handler-user-ids="(v: string[]) => (form.defaultHandlerUserIds = v)"
          />
          <!-- 仅面试型阶段（stageType=INTERVIEW）渲染面试配置；轮次数据由真实数据源 listRounds 提供 -->
          <InterviewConfigCard v-if="isInterviewStage" :form="form" :rounds="interviewRounds" />
          <AutomationCard
            :form="form"
            :skip-rules="skipRules"
            :archive-rules="archiveRules"
            @update:skip-enabled="(v: boolean) => (form.skipEnabled = v)"
            @update:archive-enabled="(v: boolean) => (form.archiveEnabled = v)"
            @update:auto-eval-n2="(v: boolean) => (form.autoEvalN2 = v)"
            @update:auto-eval-prev-aa="(v: boolean) => (form.autoEvalPrevAa = v)"
            @update:auto-advance-type="(v: any) => (form.autoAdvanceType = v)"
            @update:auto-advance-timing="(v: any) => (form.autoAdvanceTiming = v)"
            @update:auto-advance-days="(v: number | null) => (form.autoAdvanceDays = v)"
            @add-skip="skipModal?.open()"
            @add-archive="archiveModal?.open()"
            @edit-skip="(r: SkipRule) => skipModal?.open(r)"
            @edit-archive="(r: ArchiveRule) => archiveModal?.open(r)"
            @remove-skip="removeSkip"
            @remove-archive="removeArchive"
            @show-stopped="showStopped"
          />
        </div>
      </div>
    </n-spin>

    <template #footer>
      <div class="modal-footer">
        <n-button size="small" :disabled="saving" @click="onRequestClose">{{ t('pages.settings.stage-rule.StageRuleConfigModal.s5') }}</n-button>
        <n-button size="small" type="primary" :loading="saving" :disabled="loading" @click="handleSubmit">{{ t('pages.settings.stage-rule.StageRuleConfigModal.s6') }}</n-button>
      </div>
    </template>

    <!-- 二级 / 三级弹窗 -->
    <EntryRuleEditModal ref="entryModal" :catalog="activeCatalog" @save="onEntrySave" @close="onSubClose" />
    <SkipRuleEditModal ref="skipModal" :catalog="activeCatalog" @save="onSkipSave" @close="onSubClose" />
    <ArchiveRuleEditModal ref="archiveModal" :catalog="activeCatalog" @save="onArchiveSave" @close="onSubClose" />
    <StoppedRulesModal ref="stoppedModal" @reenable="onReenable" @close="onSubClose" />
  </n-modal>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, watch } from 'vue'
import { NModal, NIcon, NSpin, NButton, NAlert, useMessage } from 'naive-ui'
import { SettingsOutline, FlashOutline, CloseOutline } from '@vicons/ionicons5'
import EntryConditionCard from './cards/EntryConditionCard.vue'
import DefaultHandlerCard from './cards/DefaultHandlerCard.vue'
import InterviewConfigCard from './cards/InterviewConfigCard.vue'
import AutomationCard from './cards/AutomationCard.vue'
import EntryRuleEditModal from './modals/EntryRuleEditModal.vue'
import SkipRuleEditModal from './modals/SkipRuleEditModal.vue'
import ArchiveRuleEditModal from './modals/ArchiveRuleEditModal.vue'
import StoppedRulesModal from './modals/StoppedRulesModal.vue'
import { useStageRuleForm } from './composables/useStageRuleForm'
import { listRounds } from '../../../api/recruitment-process'
import { listFields } from '../../../api/dynamic-field'
import { listUsers } from '../../../api/users'
import type { EntryConditionRule, SkipRule, ArchiveRule } from './types'
const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    show: boolean
    stage: any | null
    linkId: string | null
    initialTab?: string
  }>(),
  { initialTab: 'auto' },
)

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const { form, entryRules, skipRules, archiveRules, catalog, loading, saving, loadError, load, save, reset } = useStageRuleForm()

const entryEnabled = ref(true)
const entryModal = ref<InstanceType<typeof EntryRuleEditModal>>()
const skipModal = ref<InstanceType<typeof SkipRuleEditModal>>()
const archiveModal = ref<InstanceType<typeof ArchiveRuleEditModal>>()
const stoppedModal = ref<InstanceType<typeof StoppedRulesModal>>()

/** 面试配置模块仅对「面试型」阶段渲染（判断标准与 ProcessStageRules.vue 一致：stageType === 'INTERVIEW'） */
const isInterviewStage = computed(() => (props.stage as any)?.stageType === 'INTERVIEW')

/** 面试轮次真实数据源（GET 面试轮次列表，同「面试轮次管理」页 listRounds）。
 * 每次打开弹窗重新拉取，保证配置内容随数据源实时更新；拉取失败给空列表（子组件渲染空态）。 */
const interviewRounds = ref<any[]>([])
async function loadRounds() {
  try {
    interviewRounds.value = await listRounds()
  } catch {
    interviewRounds.value = []
  }
}

/** 默认处理人真实数据源（严禁 mock/硬编码，与面试轮次同策略：每次打开弹窗重新拉取，失败降级空列表）。
 *  - 需求/职位资源下「人员(PERSON)」型动态字段（GET /dynamic-fields/{resource}/fields/，同动态字段设置页 listFields）
 *  - 系统真实用户列表（GET /users，同选人场景 listUsers；自带失败降级空数组） */
const demandPersonFields = ref<any[]>([])
const positionPersonFields = ref<any[]>([])
const handlerUserOptions = ref<any[]>([])
async function loadHandlerData() {
  const pickPerson = (list: any) => (Array.isArray(list) ? list : []).filter((f: any) => f?.fieldType === 'PERSON')
  const [demand, position, users] = await Promise.all([
    listFields('Demand').catch(() => []),
    listFields('Position').catch(() => []),
    listUsers(),
  ])
  demandPersonFields.value = pickPerson(demand)
  positionPersonFields.value = pickPerson(position)
  handlerUserOptions.value = Array.isArray(users) ? users : []
}

/** 字段字典来自真实后端 GET /api/v1/expressions/fields。
 * 直接透传 catalog（含加载中 / 失败时的 null）：
 * - 加载完成 → 真实目录，EXP-5 失效模板守卫据此判定；
 * - 为 null（加载中或失败）→ fail-open，不拦截（避免误伤正常编辑）。 */
const activeCatalog = computed(() => catalog.value)

watch(
  () => props.show,
  (v) => {
    if (v && props.linkId) {
      entryEnabled.value = true
      void load(props.linkId)
      void loadRounds()
      void loadHandlerData()
    }
  },
)

function reload() {
  if (props.linkId) void load(props.linkId)
}

function onRequestClose() {
  if (saving.value) return
  emit('update:show', false)
}

function resetTransient() {
  saving.value = false
  reset()
}

// ===== 进入条件规则 =====
function onEntrySave(rule: EntryConditionRule) {
  const idx = entryRules.value.findIndex((r) => r.id && rule.id && r.id === rule.id)
  if (idx >= 0) entryRules.value[idx] = rule
  else entryRules.value.push(rule)
}
function toggleEntry(rule: EntryConditionRule) {
  const r = entryRules.value.find((x) => x.id === rule.id)
  if (r) r.status = r.status === 'ENABLED' ? 'DISABLED' : 'ENABLED'
}
function removeEntry(rule: EntryConditionRule) {
  entryRules.value = entryRules.value.filter((x) => x.id !== rule.id)
}

// ===== 自动跳过规则 =====
function onSkipSave(rule: SkipRule) {
  const idx = skipRules.value.findIndex((r) => r.id === rule.id)
  if (idx >= 0) skipRules.value[idx] = rule
  else skipRules.value.push(rule)
  form.skipEnabled = true
}
function removeSkip(rule: SkipRule) {
  // P0-2：停用 = 软禁用，移出主表、仅出现在「已停用规则」弹窗（不删除）
  const r = skipRules.value.find((x) => x.id === rule.id)
  if (r) r.enabled = false
}

// ===== 自动归档规则 =====
function onArchiveSave(rule: ArchiveRule) {
  const idx = archiveRules.value.findIndex((r) => r.id === rule.id)
  if (idx >= 0) archiveRules.value[idx] = rule
  else archiveRules.value.push(rule)
  form.archiveEnabled = true
}
function removeArchive(rule: ArchiveRule) {
  // P0-2：停用 = 软禁用，移出主表、仅出现在「已停用规则」弹窗（不删除）
  const r = archiveRules.value.find((x) => x.id === rule.id)
  if (r) r.enabled = false
}
function showStopped() {
  // P0-2：同时收纳「自动跳过 / 自动归档」中被停用的规则
  const disabled = [
    ...skipRules.value.filter((r) => !r.enabled).map((r) => ({ id: r.id, name: r.name, expression: r.expression, kindLabel: t('pages.settings.stage-rule.StageRuleConfigModal.s11'), rule: r })),
    ...archiveRules.value.filter((r) => !r.enabled).map((r) => ({ id: r.id, name: r.name, expression: r.expression, kindLabel: t('pages.settings.stage-rule.StageRuleConfigModal.s12'), rule: r })),
  ]
  stoppedModal.value?.open(disabled)
}
function onReenable(payload: { rule: SkipRule | ArchiveRule }) {
  // P0-2：重新启用停用规则（跳过 / 归档通用）
  payload.rule.enabled = true
  message.success(t('pages.settings.stage-rule.StageRuleConfigModal.s7'))
}

// ===== 进入条件规则（P0-4：仅允许一条，规则配置直接打开已存在的那条）=====
function onEntryConfigure() {
  const existing = entryRules.value.find((r) => r.id) || entryRules.value[0]
  entryModal.value?.open(existing)
}

function onSubClose() {
  // 子弹窗关闭无需特殊处理（其自身控制 visible）
}

async function handleSubmit() {
  if (!props.linkId) {
    message.error(t('pages.settings.stage-rule.StageRuleConfigModal.s8'))
    return
  }
  try {
    const ok = await save(props.linkId)
    if (ok) {
      message.success(t('pages.settings.stage-rule.StageRuleConfigModal.s9'))
      emit('saved')
      emit('update:show', false)
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || e?.message || t('pages.settings.stage-rule.StageRuleConfigModal.s13'))
  }
}
</script>

<!-- 全局覆盖（n-modal 渲染到 body，scoped 不穿透，故非 scoped） -->
<style>
/* 容器浮起：HTML 原型 box-shadow 0 20px 60px rgba(0,0,0,0.18) → --shadow-2xl */
.stage-rule-config-modal .n-card {
  box-shadow: var(--shadow-2xl);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.stage-rule-config-modal .n-card-header {
  padding: 0;
  border-bottom: none;
}
/* footer：原型 border-top 1px + bg #fafbfc（→ --g1） */
.stage-rule-config-modal .n-card__footer {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-hairline);
  background: var(--g1);
}
.stage-rule-config-modal .n-card__content {
  padding: 0;
}

/* ===== 卡片公共样式（必须非 scoped）=====
 * Card1-4 是子组件，Vue scoped 只命中子组件根节点，内部 .card-title / .flow-block /
 * .block-header 拿不到父 scope id → 父 scoped 样式对它们全部落空（P0-1 根因）。
 * 故这些「子卡片内部」的样式统一放在此全局块，用 .stage-rule-config-modal 前缀收口。 */
.stage-rule-config-modal .config-card {
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  border-radius: 12px;  /* 原型 config-card radius 12 */
  padding: 14px 16px 16px;  /* 原型 14 16 16 */
}
.stage-rule-config-modal .card-title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 12px;  /* 原型 12px */
  letter-spacing: -0.01em;
}
.stage-rule-config-modal .card-title .n-icon {
  color: var(--brand);
  font-size: 14px;
  flex-shrink: 0;
}
/* 默认处理人 / 流程自动化 模块标题行内容靠左（无右侧操作，覆盖全局 space-between） */
.stage-rule-config-modal .card-title.card-title--left {
  justify-content: flex-start;
}
.stage-rule-config-modal .card-title .title-actions {
  gap: var(--space-3);
}
.stage-rule-config-modal .title-desc {
  font-weight: 400;
  font-size: 11.5px;  /* 原型辅助说明 11.5px */
  color: var(--ink-faint);  /* 原型 #86909c 接近 --ink-faint #64748B */
  margin-left: 2px;
}

/* ===== Flow Condition Row（P0-1 收口：基类非 scoped）=====
 * DefaultHandlerCard / AutomationCard / InterviewConfigCard 都用 .flow-condition-row。
 * AutomationCard / InterviewConfigCard 在各自 scoped 里定义了 display:flex；
 * DefaultHandlerCard 只定义了 .flow-condition-row--3（flex-wrap + .flow-field），
 * 漏了基类 → 父级非 flex 容器 → 三下拉纵向堆叠（用户截图实证）。
 * 基类统一收口到全局块，确保三卡片都拿到 flex 行布局。
 *
 * 关键：此处只设 display + gap，**不设 align-items**。
 * AutomationCard 要 flex-end（表单行基线），InterviewConfigCard 要 flex-start
 * （面试轮次 + 形式顶对齐）；全局 .flow-condition-row 与各卡片 scoped .flow-condition-row
 * 选择器特异度都是 (0,2,0)，source-order 决胜。在全局块里写 align-items 会按打包顺序
 * 静默覆盖 InterviewConfigCard 的 flex-start（特异度陷阱，与 P0-1 同根）。
 * 故 align-items 留给各卡片 scoped 自管；DefaultHandlerCard 的 .flow-condition-row--3
 * 也补上 align-items: flex-end。 */
.stage-rule-config-modal .flow-condition-row {
  display: flex;
  gap: var(--space-4);
}

/* ===== Flow Block ===== */
.stage-rule-config-modal .flow-block {
  background: var(--surface);
  border-radius: 10px;  /* 原型 flow-block radius 10 */
  padding: 10px 14px;  /* 原型 10 14 */
  margin-bottom: 12px;
  box-shadow: 0 0 0 1px var(--border-hairline), 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow var(--duration-fast) var(--ease-out);
}
.stage-rule-config-modal .flow-block:last-child {
  margin-bottom: 0;
}
.stage-rule-config-modal .flow-block:hover {
  box-shadow: 0 0 0 1px var(--border-hairline), 0 2px 8px rgba(15, 23, 42, 0.04);
}
.stage-rule-config-modal .block-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.stage-rule-config-modal .block-header .n-icon {
  color: var(--brand);
  font-size: 12px;
  flex-shrink: 0;
}
.stage-rule-config-modal .block-desc {
  font-weight: 400;
  font-size: 11.5px;
  color: var(--ink-faint);
  margin-left: 2px;
  line-height: 1.4;
}
.stage-rule-config-modal .block-header--secondary {
  font-size: 13.5px;
  font-weight: 650;
}
.stage-rule-config-modal .block-header--split {
  justify-content: space-between;
  align-items: center;
}
.stage-rule-config-modal .block-header__main {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}
</style>

<style scoped>
.rule-config-body {
  min-height: 280px;
}
.rule-config-flat {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}
.load-error {
  padding: var(--space-4);
}

/* ===== HERO ===== */
.hero {
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-hairline);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.hero__icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--g1);
  flex-shrink: 0;
  box-shadow: var(--shadow-xs);
}
.hero__title {
  margin: 0;
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  flex: 1 1 auto;
  min-width: 0;
}
.hero__object {
  font-weight: 400;
  font-size: var(--fs-12);
  color: var(--ink-faint);
  margin-left: 2px;
}
.hero__tip {
  font-size: var(--fs-12);
  color: var(--brand);
  background: var(--brand-a12);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-weight: 500;
  flex-shrink: 0;
}
.hero__close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--ink-faint);
  font-size: var(--fs-18);
  padding: var(--space-1);
  line-height: 1;
  border-radius: var(--radius-sm);
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.hero__close:hover {
  background: var(--overlay-scrim-weak);
  color: var(--ink);
}

/* ===== Section Card 容器（主壳自身元素，scoped 可命中）=====
 * 注意：.config-card / .card-title / .flow-block / .block-header 等「子卡片内部」样式
 * 已迁移到本文件顶部的非 scoped 块（P0-1 修复），此处不再重复定义。 */
.rule-config-flat {
  display: flex;
  flex-direction: column;
  gap: 12px;  /* 原型卡片间距 12px */
  padding: 14px 20px;  /* 原型主体 padding 16 20 */
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* ===== Footer ===== */
.modal-footer {
  padding: 0;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
.modal-footer :deep(.n-button) {
  min-width: 88px;
}

@media (max-width: 600px) {
  .hero {
    padding: var(--space-4) var(--space-3);
  }
  .config-card {
    padding: 10px 10px 12px;
  }
}
</style>

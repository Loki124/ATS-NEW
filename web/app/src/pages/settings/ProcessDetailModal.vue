<!--
  流程详情 / 编辑 Modal — V8 风格统一重构 (2026-09-07)
  v3 重构要点:
  - 编辑态与展示态合并为「单一模板」，复用同一套组件（stage-card / config-item / EntryConditionCard），
    不再为 edit / view 分别设计视觉方案（满足「编辑态=展示态」硬约束）。
  - 视觉语言对齐编辑流程_详情页（V8）: sticky 顶栏 + 锚点导航 + 分区白卡 + stage-card/config-item 网格。
  - 顶栏(顶部概览条)常驻，含标题/状态/元信息/锚点导航/取消·保存；下方三段式分区(基础信息/适用范围/流程阶段)。
  - mode 仅作内部 dirty 判定用，模板不再按 mode 分叉。

  单测契约保留 (8 条不变量):
  - .stage-card = 每 link 一个根容器
  - .stage-card__system-badge = 首末 2 个 (来自 editForm.stages[].isSystem)
  - input[placeholder="流程名称"] = editForm.name
  - dirty 取消 / 关闭 → .n-dialog
  - 保存 → updateProcess + saved
  - 409 → 修改冲突 modal
  - 新建 (processId='') → 空表单, 取消/创建按钮
  (旧契约 btn-enter-edit / enterEdit 已移除: 统一后不再有 view→edit 切换)
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    class="process-detail-modal"
    style="width: 880px; max-width: 95vw; max-height: 90vh"
    :mask-closable="true"
    :title="isCreateMode ? '新建流程' : '编辑流程'"
    :bordered="false"
    :segmented="{ content: true, footer: true }"
    @update:show="handleUpdateShow"
  >
    <n-scrollbar style="height: 100%">
      <n-spin :show="loading">
        <div v-if="loadError" class="dp-load-error">
          <n-empty description="加载流程详情失败">
            <template #extra>
              <n-button type="primary" @click="handleRetryLoad">重新加载</n-button>
            </template>
          </n-empty>
        </div>
        <div v-else-if="editForm" class="dp-wrap">
          <!-- ====== 顶部概览条 (统一 edit/display, V8 sticky topbar) ====== -->
          <div class="dp-topbar">
            <div class="dp-topbar-inner">
              <div class="dp-logo">
                <n-icon :component="GitNetworkOutline" size="20" />
              </div>
              <div class="dp-title-block">
                <div class="dp-title">
                  <span>{{ editForm.name || data.name || (isCreateMode ? '新建流程' : '流程详情') }}</span>
                  <n-tag
                    v-if="(data.status as any) === 'ACTIVE' || (data.status as any) === 'ENABLED'"
                    type="success" size="small" round
                  >启用中</n-tag>
                  <n-tag v-else-if="data.status" type="default" size="small" round>
                    {{ data.status === 'INACTIVE' ? '已停用' : data.status }}
                  </n-tag>
                </div>
                <div class="dp-meta">
                  <span><n-icon :component="LayersOutline" /> {{ editForm.stages.length }} 个阶段</span>
                  <span v-if="data.code"><n-icon :component="ServerOutline" /> 编号 {{ data.code }} (不可改)</span>
                </div>
              </div>
              <nav class="dp-tabs" aria-label="页面导航">
                <button type="button" class="dp-tab" @click="scrollToSection('sec-basic')">基础信息</button>
                <button type="button" class="dp-tab" @click="scrollToSection('sec-scope')">适用范围</button>
                <button type="button" class="dp-tab" @click="scrollToSection('sec-stages')">流程阶段</button>
              </nav>
              <div class="dp-actions">
                <n-button @click="cancelEdit">取消</n-button>
                <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">
                  {{ isCreateMode ? '创建' : '保存' }}
                </n-button>
              </div>
            </div>
          </div>

          <!-- ====== 基础信息 ====== -->
          <section class="dp-section" id="sec-basic">
            <div class="dp-section-title"><h3>基础信息</h3></div>
            <div class="dp-card">
              <div class="dp-form-grid">
                <div class="dp-field span-full">
                  <label class="dp-flabel">流程名称</label>
                  <n-input v-model:value="editForm.name" placeholder="流程名称" />
                </div>
                <div class="dp-field">
                  <span class="dp-flabel">适用范围组合</span>
                  <n-radio-group v-model:value="editForm.applicableMode" size="small">
                    <n-radio value="ALL">全部满足</n-radio>
                    <n-radio value="ANY">任一满足</n-radio>
                  </n-radio-group>
                </div>
                <div class="dp-field">
                  <span class="dp-flabel">校验简历评分</span>
                  <n-switch v-model:value="editForm.validateResumeScore" />
                </div>
                <div class="dp-field span-full">
                  <label class="dp-flabel">流程说明</label>
                  <n-input v-model:value="editForm.description" type="textarea" :rows="3" placeholder="可选" />
                </div>
                <div class="dp-field span-full">
                  <label class="dp-flabel">流转异常提示</label>
                  <n-input v-model:value="editForm.failPrompt" type="textarea" :rows="3" placeholder="候选人不满足进入条件时的展示文本 (可选)" />
                </div>
              </div>
            </div>
          </section>

          <!-- ====== 适用范围 ====== -->
          <section class="dp-section" id="sec-scope">
            <div class="dp-section-title">
              <h3>适用范围</h3><span class="hint">基于条件规则判断适用范围</span>
            </div>
            <div v-if="editForm.applicableIndicators.length" class="scope-card-list">
              <n-grid :cols="2" :x-gap="12" :y-gap="12" responsive="screen" :item-responsive="true">
                <n-grid-item v-for="ind in editForm.applicableIndicators" :key="ind.key">
                  <div class="scope-card" :class="getScopeEditCardClass(ind)">
                    <div class="scope-card__head">
                      <n-icon :component="SCOPE_KEY_ICONS[ind.key]" />
                      <span class="scope-card__name">{{ SCOPE_INDICATOR_META[ind.key].label }}</span>
                    </div>
                    <div class="scope-card__mode">
                      <n-radio-group v-model:value="ind.mode" size="small">
                        <n-radio value="include">包含</n-radio>
                        <n-radio value="exclude">不包含</n-radio>
                      </n-radio-group>
                      <span v-if="ind.values.length" class="scope-card__count">{{ ind.values.length }} 项</span>
                      <span v-else class="scope-card__count">不限</span>
                    </div>
                    <div class="scope-card__values">
                      <n-select
                        v-model:value="ind.values"
                        multiple filterable clearable
                        placeholder="留空 = 不约束"
                        :options="scopeOptionsFor(ind.key)"
                        :loading="!scopeOptionsLoaded"
                        class="scope-card__select"
                      />
                    </div>
                  </div>
                </n-grid-item>
              </n-grid>
            </div>
          </section>

          <!-- ====== 阶段流程 ====== -->
          <section class="dp-section" id="sec-stages">
            <div class="dp-section-title">
              <h3>流程阶段</h3><span class="warn">第一个和最后一个阶段为系统内置固定阶段，不可取消或调整位置</span>
            </div>
            <n-alert type="info" :show-icon="false" style="margin-bottom: var(--space-3); font-size: 12px">
              起止阶段不可删除. 中间业务阶段可单独配置或删除. 点「配置阶段规则」编辑阶段规则与进入条件.
            </n-alert>
            <div class="stage-list">
              <div
                v-for="(stage, idx) in editForm.stages"
                :key="stage._linkId || stage.id || idx"
                class="stage-card"
                :class="[
                  `stage-card--${(stage.stageType || 'SCREEN').toLowerCase()}`,
                  { 'stage-card--selected': selectedStageIdx === idx },
                ]"
              >
                <!-- 阶段 header: 序号 + 名称 + 类型/系统/起止 tag + 操作 -->
                <div class="stage-header">
                  <div class="header-left">
                    <span class="stage-no">{{ idx + 1 }}</span>
                    <span class="stage-name">{{ stage.name }}</span>
                    <n-tag size="small" type="default">
                      <template #icon><n-icon :component="stageTypeIcon(stage.stageType)" /></template>
                      {{ stageTypeLabel(stage.stageType) }}
                    </n-tag>
                    <n-tag
                      v-if="stage.isSystem"
                      class="stage-card__system-badge"
                      type="info" size="small" round
                    >
                      <template #icon><n-icon :component="InformationCircleOutline" /></template>
                      系统内置
                    </n-tag>
                    <n-tag v-if="stage.isStart" type="success" size="small" round>起始</n-tag>
                    <n-tag v-if="stage.isEnd" type="warning" size="small" round>结束</n-tag>
                  </div>
                  <div class="header-right">
                    <n-button size="small" type="primary" @click.stop="openStageRuleConfig(stage)">
                      <template #icon><n-icon :component="OptionsOutline" /></template>配置阶段规则
                    </n-button>
                    <n-button v-if="!stage.isStart" size="small" @click.stop="addStageAt(idx, 'preceding')">
                      <template #icon><n-icon :component="AddOutline" /></template>添加前序阶段
                    </n-button>
                    <n-popconfirm v-if="!stage.isStart && !stage.isEnd" @positive-click="removeStage(idx)">
                      <template #trigger>
                        <n-button size="small" type="error">删除当前阶段</n-button>
                      </template>
                      确定删除阶段「{{ stage.name }}」？
                    </n-popconfirm>
                  </div>
                </div>

                <!-- 卡内 config 网格: 进入条件 / 包含功能 / 阶段自动化 / 默认处理人 -->
                <div class="config-grid">
                  <div class="config-item span-2">
                    <div class="item-title"><span>进入条件</span></div>
                    <div class="item-body">
                      <EntryConditionCard :entry-condition="stage._condition" />
                    </div>
                  </div>

                  <div class="config-item">
                    <div class="item-title"><span>包含功能</span></div>
                    <div class="item-body">
                      <template v-if="stage.features?.length">
                        <div class="feature-tags">
                          <span v-for="f in stage.features" :key="f" class="feature-tag">{{ featureLabel(f) }}</span>
                        </div>
                      </template>
                      <div v-else class="feature-empty">
                        <n-icon :component="ExtensionPuzzleOutline" /><span>未启用包含功能</span>
                      </div>
                    </div>
                  </div>

                  <div class="config-item">
                    <div class="item-title"><span>阶段自动化</span></div>
                    <div class="item-body">
                      <div class="auto-grid">
                        <div class="auto-item">
                          <span class="label">自动流转</span>
                          <span class="value">
                            <span class="status-dot" :class="{ off: !(stage._rule && stage._rule.autoAdvanceType && stage._rule.autoAdvanceType !== 'NONE') }"></span>
                            {{ stage._rule && stage._rule.autoAdvanceType && stage._rule.autoAdvanceType !== 'NONE'
                              ? (AUTO_ADVANCE_LABEL[stage._rule.autoAdvanceType] || stage._rule.autoAdvanceType)
                                + (stage._rule.autoAdvanceTiming === 'IMMEDIATE' ? ' · 立即执行'
                                  : stage._rule.autoAdvanceTiming === 'DELAYED' && stage._rule.autoAdvanceDays ? ` · 延迟 ${stage._rule.autoAdvanceDays} 天` : '')
                              : '未开启' }}
                          </span>
                        </div>
                        <div class="auto-item">
                          <span class="label">自动跳过</span>
                          <span class="value">
                            <span class="status-dot" :class="{ off: !stage._rule?.autoSkipNPlusTwo }"></span>
                            {{ stage._rule?.autoSkipNPlusTwo ? '已开启' : '未开启' }}
                          </span>
                        </div>
                        <div class="auto-item">
                          <span class="label">阶段限时</span>
                          <span class="value">
                            <span class="status-dot" :class="{ off: !stage._rule?.timeLimit }"></span>
                            {{ stage._rule?.timeLimit ? `${stage._rule.timeLimit} 天` : '未开启' }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="config-item span-2 handler-row">
                    <div class="item-title"><span>默认处理人</span></div>
                    <div class="item-body">
                      <template v-if="stage._rule?.defaultHandlerType">
                        <span class="handler-tag">{{ HANDLER_TYPE_LABEL[stage._rule.defaultHandlerType] || stage._rule.defaultHandlerType }}</span>
                        <span v-for="(f, fi) in (stage._rule.defaultHandlerFields || [])" :key="'f' + fi" class="handler-tag">{{ f }}</span>
                        <span v-for="(u, ui) in (stage._rule.defaultHandlerUserIds || [])" :key="'u' + ui" class="handler-tag">{{ u }}</span>
                      </template>
                      <span v-else class="handler-none">无默认处理人</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <n-button
              v-if="!editForm.stages.length || !editForm.stages[editForm.stages.length - 1]?.isEnd"
              style="margin-top: 12px" size="small" type="primary" block
              @click="addStageAt(editForm.stages.length, 'following')"
            >
              <template #icon><n-icon :component="AddOutline" /></template>追加到末尾
            </n-button>
          </section>
        </div>
      </n-spin>
    </n-scrollbar>

    <template #footer>
      <n-space justify="end">
        <n-button @click="handleClose">关闭</n-button>
        <n-button
          v-if="!isCreateMode"
          type="default"
          :loading="copying"
          data-testid="btn-copy-process"
          @click="onCopy"
        >
          <template #icon><n-icon :component="CopyOutline" /></template>
          复制此流程
        </n-button>
      </n-space>
    </template>
  </n-modal>

  <!-- 关闭确认 dialog (n-modal preset="dialog" 自带 teleport + 居中, 不依赖 trigger) -->
  <n-modal
    :show="showCloseConfirm"
    preset="dialog"
    title="有未保存的修改"
    content="确定离开? 当前编辑内容将丢失。"
    positive-text="确定离开"
    negative-text="继续编辑"
    @positive-click="confirmClose"
    @negative-click="showCloseConfirm = false"
    @close="showCloseConfirm = false"
  />

  <!-- 409 冲突 modal -->
  <n-modal
    v-model:show="showConflict"
    preset="card"
    title="修改冲突"
    style="width: 480px; max-width: 90vw"
  >
    <p>此流程在您编辑期间被其他用户修改。</p>
    <p v-if="conflictInfo?.updatedBy">最后修改人: {{ conflictInfo.updatedBy }}</p>
    <p v-if="conflictInfo?.updatedAt">修改时间: {{ formatDate(conflictInfo.updatedAt) }}</p>
    <n-space justify="end">
      <n-button @click="abandonEdit">放弃修改</n-button>
      <n-button type="primary" class="gradient-btn" @click="reloadAndEdit">重新加载后继续编辑</n-button>
    </n-space>
  </n-modal>

  <!-- 阶段选择 Picker: 点 "添加前序阶段" / "追加到末尾" 触发 -->
  <n-modal
    v-model:show="showStagePicker"
    preset="card"
    class="stage-picker-modal"
    title="选择要添加的阶段"
    style="width: 600px; max-width: 95vw; max-height: 90vh"
  >
    <n-input
      v-model:value="stagePickerKeyword"
      placeholder="搜索阶段名称 / 编号"
      clearable
      style="margin-bottom: 12px"
    >
      <template #prefix>
        <n-icon :component="SearchOutline" />
      </template>
    </n-input>

    <div v-if="stagePickerCandidates.length === 0" class="picker-empty">
      <n-empty description="没有可添加的阶段 (本流程已用完所有阶段,或阶段库为空)。请先在「阶段模板库」中创建更多阶段。" />
    </div>
    <div v-else class="picker-list">
      <div
        v-for="s in stagePickerCandidates"
        :key="s.id"
        class="picker-item"
        :class="{ 'picker-item--start': s.isStart, 'picker-item--end': s.isEnd }"
        @click="confirmStagePick(s)"
      >
        <div
          class="picker-item__dot"
          :style="{ background: stageTypeColor(s.stageType) }"
        />
        <div class="picker-item__main">
          <div class="picker-item__name">
            {{ s.name }}
            <n-tag
              v-if="s.isStart"
              size="tiny"
              type="success"
              round
              style="margin-left: 6px"
            >起始</n-tag>
            <n-tag
              v-if="s.isEnd"
              size="tiny"
              type="warning"
              round
              style="margin-left: 6px"
            >结束</n-tag>
          </div>
          <div class="picker-item__code">{{ s.code }} · {{ stageTypeLabel(s.stageType) }}</div>
        </div>
        <div class="picker-item__hint">
          <span v-if="s.isStart && stagePickerInsertIdx > 0">将插入到开头</span>
          <span v-else-if="s.isEnd">将插入到末尾</span>
          <span v-else>将插入到第 {{ stagePickerInsertIdx + 1 }} 行{{ stagePickerInsertPosition === 'preceding' ? '之前' : '之后' }}</span>
        </div>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-text depth="3" style="font-size: 12px">
          同一阶段在同一流程中只能被使用一次
        </n-text>
        <n-button @click="showStagePicker = false">取消</n-button>
      </n-space>
    </template>
  </n-modal>

  <!-- 嵌套 StageRuleConfigModal -->
  <StageRuleConfigModal
    v-model:show="showRuleConfig"
    :stage="ruleEditingStage"
    :link-id="ruleEditingLinkId"
    @saved="onRuleSaved"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onBeforeUnmount, reactive, type Ref } from 'vue'
import {
  NSpace, NTag, NSpin, NModal, NButton, NIcon, NScrollbar,
  NGrid, NGridItem, NInput, NRadio, NRadioGroup, NSelect, NSwitch,
  NAlert, NInputNumber, NPopconfirm, NText, NEmpty, useMessage,
} from 'naive-ui'
import { useUndo } from '../../composables/useUndo'
import {
  GitNetworkOutline,
  ServerOutline,
  LayersOutline,
  InformationCircleOutline,
  CopyOutline,
  CreateOutline,
  FilterOutline,
  MailOutline,
  VideocamOutline,
  DocumentTextOutline,
  CheckmarkCircleOutline,
  BusinessOutline,
  MedalOutline,
  BriefcaseOutline,
  PersonCircleOutline,
  AddOutline,
  SearchOutline,
  OptionsOutline,
  ExtensionPuzzleOutline,
} from '@vicons/ionicons5'
import EntryConditionCard from './EntryConditionCard.vue'
import {
  getProcess,
  listProcessLinks,
  copyProcess,
  updateProcess,
  createProcess,
  listStages,
  addProcessLink,
  deleteProcessLink,
  updateProcessLink,
  reorderProcessLinks,
  type RecruitmentProcess,
  type ProcessStageLink,
  type StageRule,
  type EntryCondition,
} from '../../api/recruitment-process'
import StageRuleConfigModal from './StageRuleConfigModal.vue'
// D1: 适用范围选项真实数据源 (departments / positions / users)
import api from '../../api/auth'
import { listUsers } from '../../api/users'

const props = withDefaults(defineProps<{
  show: boolean
  processId: string
  defaultMode?: 'view' | 'edit'
  editable?: boolean
}>(), {
  defaultMode: 'view',
  editable: true,
})

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'copied', newProcessId: string): void
  (e: 'saved', processId: string): void
}>()

const message = useMessage()
const { undoable } = useUndo()
const loading = ref(false)
const copying = ref(false)
const saving = ref(false)
// E1: 加载错误态 (加载失败时渲染错误块 + 重试, 而非仅 toast)
const loadError = ref<string | null>(null)
// D1: 适用范围选项是否已加载 (控制 select loading 态)
const scopeOptionsLoaded = ref(false)
const data = ref<Partial<RecruitmentProcess> & Record<string, any>>({})
const links = ref<ProcessStageLink[]>([])

// ===== mode state (内部仅用于 dirty 判定; 模板不再按 mode 分叉) =====
type Mode = 'view' | 'edit'
const mode = ref<Mode>(props.defaultMode)

// ===== create mode =====
const isCreateMode = computed(() => !props.processId)

// ===== edit state =====
type ScopeKey = 'department' | 'level' | 'position' | 'user'

interface ScopeIndicator {
  key: ScopeKey
  mode: 'include' | 'exclude'
  values: string[]
  options: { label: string; value: string }[]
  loading: boolean
}

interface EditStage {
  id?: string
  code?: string
  name: string
  stageType: string
  isStart?: boolean
  isEnd?: boolean
  isSystem?: boolean
  stageLimit?: number
  features?: string[]
  _linkId?: string
  _rule?: StageRule
  _condition?: EntryCondition
}

interface EditForm {
  name: string
  description: string
  validateResumeScore: boolean
  failPrompt: string
  applicableMode: 'ALL' | 'ANY'
  applicableIndicators: ScopeIndicator[]
  stages: EditStage[]
}

interface EditSnapshot {
  form: EditForm
}

const editForm = ref<EditForm | null>(null)
const originalSnapshot = ref<EditSnapshot | null>(null)
const selectedStageIdx = ref<number | null>(null)
const showCloseConfirm = ref(false)
const showConflict = ref(false)

const conflictInfo = ref<{ updatedBy?: string; updatedAt?: string } | null>(null)
const showRuleConfig = ref(false)
const ruleEditingStage = ref<EditStage | null>(null)
const ruleEditingLinkId = ref<string | null>(null)

// scope options
const deptOptions = ref<{ label: string; value: string }[]>([])
const positionOptions = ref<{ label: string; value: string }[]>([])
const userOptions = ref<{ label: string; value: string }[]>([])

// stage library (含 isStart/isEnd 字段, Picker 用)
const stageLibrary = ref<{ id: string; code: string; name: string; stageType: string; isStart?: boolean; isEnd?: boolean; status?: string }[]>([])

// ===== 元数据映射 =====
const STAGE_TYPE_META: Record<string, { label: string; color: string; tagType: 'info' | 'warning' | 'success' | 'primary' | 'default'; icon: any }> = {
  SCREEN:     { label: '筛选',  color: 'var(--c-info)',    tagType: 'info',    icon: FilterOutline },
  INVITATION: { label: '邀约',  color: 'var(--c-warning)', tagType: 'warning', icon: MailOutline },
  INTERVIEW:  { label: '面试',  color: 'var(--c-purple)',  tagType: 'primary', icon: VideocamOutline },
  OFFER:      { label: 'Offer', color: 'var(--c-success)', tagType: 'success', icon: DocumentTextOutline },
  ONBOARDING: { label: '入职',  color: 'var(--c-cyan)',    tagType: 'info',    icon: CheckmarkCircleOutline },
}

const SCOPE_INDICATOR_LABEL: Record<string, string> = {
  department: '部门',
  level: '职级',
  position: '岗位',
  user: '用户',
}

const SCOPE_KEY_ICONS: Record<string, any> = {
  department: BusinessOutline,
  level: MedalOutline,
  position: BriefcaseOutline,
  user: PersonCircleOutline,
}

const CONDITION_TYPE_LABEL: Record<string, string> = {
  STAGE_STATUS: '基于阶段状态',
  CANDIDATE: '基于候选人',
  MIXED: '混合',
}

const FEATURE_LABEL: Record<string, string> = {
  INVITE_FILTER: '邀请筛选',
  INVITE_UPDATE_INFO: '邀请更新简历',
  TRANSFER_STAGE: '转移阶段',
  ARCHIVE: '归档',
  ARRANGE_INTERVIEW: '安排面试',
  INVITE_INTERVIEW: '邀请面试',
  SEND_OFFER: '发送 Offer',
  START_BACKGROUND_CHECK: '发起背调',
  START_ONBOARDING: '发起入职',
}

const AUTO_ADVANCE_LABEL: Record<string, string> = {
  NONE: '关闭',
  MEET_NEXT: '满足下一阶段条件',
  IGNORE_NEXT: '忽略下一阶段条件',
  MEET_NEXT_OR_N2: '满足下一阶段或 N+2',
  N1_ALL_PASS: '当前阶段全员通过',
}

const HANDLER_TYPE_LABEL: Record<string, string> = {
  FROM_DEMAND: '来自需求方',
  FROM_POSITION: '来自岗位负责人',
  CUSTOM: '自定义',
}

// ===== edit-mode meta =====
const SCOPE_INDICATOR_META: Record<ScopeKey, { label: string; tagType: 'info' | 'success' | 'warning' | 'error' }> = {
  department: { label: '需求部门', tagType: 'info' },
  level:      { label: '职级',     tagType: 'warning' },
  position:   { label: '岗位',     tagType: 'success' },
  user:       { label: '用户',     tagType: 'error' },
}

async function load() {
  if (!props.processId) return
  loadError.value = null
  loading.value = true
  try {
    // 2026-07-02: BE 部分接口不再返 {success,data} 包裹, api client 已 unwrap
    const [procResp, lksResp] = await Promise.all([
      getProcess(props.processId).catch(() => null),
      listProcessLinks(props.processId).catch(() => []),
    ])
    const proc = procResp as any
    const linksFromProc = Array.isArray(proc?.stageLinks) ? proc.stageLinks : null
    const linksArr: any[] = Array.isArray(lksResp) ? lksResp : (linksFromProc || [])
    // 兜底：旧 API 仍可能返单个对象（无 stageLinks）
    const procObj = (proc && typeof proc === 'object') ? proc : {}
    data.value = procObj
    // 适配 BE 新形态: stageLinks / order / defaultFeatures+optionalFeatures / isBuiltin
    links.value = linksArr
      .slice()
    // 2026-07-03: 字段对齐 FE 'order' (recruitment-process.ts:87) — 之前 a.orderIndex 是 undefined, 排序静默坏.
      .sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0))
      .map((l: any) => ({
        ...l,
        stage: l.stage ? {
          ...l.stage,
          features: [
            ...(l.stage.defaultFeatures || []),
            ...(l.stage.optionalFeatures || []),
          ],
          isSystem: l.stage.isBuiltin ?? l.stage.isSystem ?? false,
          stageType: l.stage.stageType,
        } : l.stage,
        isStart: l.stage?.isStart ?? false,
        isEnd: l.stage?.isEnd ?? false,
      }))
  } catch (e: any) {
    // E1: 渲染错误态而非仅 toast (R-104 异步四态)
    loadError.value = e?.response?.data?.message || '加载流程详情失败'
    message.error(loadError.value)
  } finally {
    loading.value = false
  }
}

// 统一入口: 打开即进 edit 态 (编辑态=展示态, 单一模板)。每次打开重置并构建 editForm。
watch(
  () => [props.show, props.processId],
  async ([s]) => {
    if (!s) return
    mode.value = 'edit'
    // 新建流程 (processId='')：不调 getProcess / listProcessLinks, 直接进空表单 edit 态
    if (isCreateMode.value) {
      await enterCreateMode()
      return
    }
    await load()
    await initEditFormFromSnapshot()
  },
  { immediate: true },
)

// ===== utils =====
function formatDate(s: string | undefined | null): string {
  if (!s) return '-'
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

function deepClone<T>(v: T): T { return JSON.parse(JSON.stringify(v)) }

// ===== dirty detection =====
// C2/D8: 比较时剔除 _rule / _condition — 二者经独立通道(stageRule modal)保存,
//   不纳入 dirty 判定, 否则"规则已保存但关闭仍弹未保存"的假 positive + 无意义重存循环.
function _stripRuntime(form: EditForm): string {
  const clone: any = deepClone(form)
  for (const s of clone.stages) {
    delete s._rule
    delete s._condition
  }
  return JSON.stringify(clone)
}
const dirty = computed(() => {
  if (mode.value !== 'edit' || !editForm.value || !originalSnapshot.value) return false
  return _stripRuntime(editForm.value) !== _stripRuntime(originalSnapshot.value.form)
})

// ===== build edit form from current data =====
function buildEmptyEditForm(): EditForm {
  const indicators: ScopeIndicator[] = [
    { key: 'department', mode: 'include', values: [], options: deptOptions.value, loading: false },
    { key: 'level',      mode: 'include', values: [], options: [], loading: false },
    { key: 'position',   mode: 'include', values: [], options: positionOptions.value, loading: false },
    { key: 'user',       mode: 'include', values: [], options: userOptions.value, loading: false },
  ]

  // 创建流程时, 默认自动添加系统起止 (初评 + 正式录用)。
  // 这两个 stage 是全局唯一且写死的, 每个新建流程都必须以初评开头、正式录用结尾。
  // 业务阶段由用户在编辑过程中插入。
  const startStage = stageLibrary.value.find(s => s.isStart)
  const endStage = stageLibrary.value.find(s => s.isEnd)
  const stages: EditStage[] = []
  if (startStage) stages.push(_mkStageFromLib(startStage))
  if (endStage) stages.push(_mkStageFromLib(endStage))

  return {
    name: '',
    description: '',
    validateResumeScore: false,
    failPrompt: '',
    applicableMode: 'ALL',
    applicableIndicators: indicators,
    stages,
  }
}

function buildEditForm(): EditForm {
  if (isCreateMode.value) return buildEmptyEditForm()
  const d = data.value
  const indicators: ScopeIndicator[] = [
    { key: 'department', mode: 'include', values: [], options: deptOptions.value, loading: false },
    { key: 'level',      mode: 'include', values: [], options: [], loading: false },
    { key: 'position',   mode: 'include', values: [], options: positionOptions.value, loading: false },
    { key: 'user',       mode: 'include', values: [], options: userOptions.value, loading: false },
  ]
  for (const ind of indicators) {
    // D3: 使用统一读取器 findIndicator (兼容 indicators / items / 旧 applicableDepartments 三态),
    //   避免仅读旧格式导致打开即清空适用范围 (D2 数据丢失).
    const found = findIndicator(ind.key)
    if (found) {
      ind.mode = (found.mode as 'include' | 'exclude') || 'include'
      ind.values = found.values || []
    }
  }
  const stages: EditStage[] = links.value.map((l: any) => ({
    id: l.stage?.id,
    code: l.stage?.code,
    name: l.stage?.name || '',
    stageType: l.stage?.stageType || 'SCREEN',
    isStart: l.stage?.isStart,
    isEnd: l.stage?.isEnd,
    isSystem: l.stage?.isSystem ?? l.stage?.isBuiltin ?? false,
    stageLimit: l.stageLimit,
    features: l.stage?.features || [],
    _linkId: l.id,
    _rule: l.stageRule || undefined,
    _condition: l.entryCondition || undefined,
  }))
  return {
    name: d.name || '',
    description: d.description || '',
    validateResumeScore: d.validateResumeScore ?? true,
    failPrompt: d.failPrompt || '',
    applicableMode: (d.applicableMode as 'ALL' | 'ANY') || 'ALL',
    applicableIndicators: indicators,
    stages,
  }
}

// D1: 真实拉取适用范围选项 (departments / positions / users). 非阻塞 + 逐项 fail-safe,
//   任一接口失败不影响编辑态其余功能 (测试未 mock 这些接口, 必须静默失败).
async function loadScopeOptions() {
  scopeOptionsLoaded.value = false
  const [deptRes, posRes, userRes] = await Promise.allSettled([
    api.get('/departments/'),
    api.get('/positions', { params: { status: 'ACTIVE' } }),
    listUsers(),
  ])
  if (deptRes.status === 'fulfilled') {
    deptOptions.value = extractList(deptRes.value).map((d: any) => ({ label: d.name, value: String(d.id) }))
  }
  if (posRes.status === 'fulfilled') {
    positionOptions.value = extractList(posRes.value).map((p: any) => ({ label: p.name || p.title, value: String(p.id) }))
  }
  if (userRes.status === 'fulfilled') {
    userOptions.value = extractList(userRes.value).map((u: any) => ({ label: u.realName || u.username, value: String(u.id) }))
  }
  scopeOptionsLoaded.value = true
}

// 兼容 {success,data:[...]} 与 [...] 两种返回形态
function extractList(resp: any): any[] {
  if (Array.isArray(resp)) return resp
  if (resp && Array.isArray(resp.data)) return resp.data
  if (resp && resp.data && Array.isArray(resp.data.data)) return resp.data.data
  return []
}

async function loadStageLibrary() {
  try {
    // BE 不接受 ?status=ACTIVE (BE 只识别 ENABLED/DISABLED, listStages 默认就是 ACTIVE)。
    // 流程编辑器需要看所有阶段的 stageType 颜色等信息, 不过滤状态, 让用户能用任何 stage
    // (同一 stage 可被多个流程复用)。
    const res = await listStages()
    stageLibrary.value = Array.isArray(res) ? res : []
  } catch {
    stageLibrary.value = []
  }
}

// ===== edit lifecycle =====
// 共享: 初始化 editForm + snapshot + 加载选项 + 切到 edit 模式
async function initEditFormFromSnapshot() {
  loadScopeOptions() // 非阻塞, 选项到位后响应式回填
  await loadStageLibrary()
  const form = buildEditForm()
  editForm.value = form
  originalSnapshot.value = { form: deepClone(form) }
  selectedStageIdx.value = null
  mode.value = 'edit'
}

async function enterEdit() {
  if (!props.editable) return
  await initEditFormFromSnapshot()
}

// 新建流程 (processId='')：跳过 getProcess / listProcessLinks, 直接进空表单
async function enterCreateMode() {
  if (!props.editable) return
  // 把默认 mode 强制为 edit, 不论 defaultMode 传什么
  loadError.value = null
  mode.value = 'edit'
  await initEditFormFromSnapshot()
}

function cancelEdit() {
  if (dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
  emit('update:show', false)
}

// C5: 退出编辑态时一并清理所有子弹窗 / 临时态, 避免"孤儿弹窗"(关闭主弹窗后子弹窗残留).
function exitEditMode() {
  mode.value = 'view'
  editForm.value = null
  originalSnapshot.value = null
  showCloseConfirm.value = false
  showConflict.value = false
  showRuleConfig.value = false
  ruleEditingStage.value = null
  ruleEditingLinkId.value = null
  showStagePicker.value = false
  stagePickerKeyword.value = ''
  loadError.value = null
  scopeOptionsLoaded.value = false
  selectedStageIdx.value = null
}

// ===== close guard =====
function handleClose() {
  if (mode.value === 'edit' && dirty.value) {
    showCloseConfirm.value = true
    return
  }
  exitEditMode()
  emit('update:show', false)
}

function handleUpdateShow(v: boolean) {
  if (!v) handleClose()
  else emit('update:show', true)
}

function confirmClose() {
  exitEditMode()
  emit('update:show', false)
}

// E1: 错误态重试入口 (模板错误块按钮调用)
async function handleRetryLoad() {
  loadError.value = null
  if (isCreateMode.value) {
    await enterCreateMode()
  } else {
    await load()
    await initEditFormFromSnapshot()
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (mode.value === 'edit' && dirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))

// ===== stage ops =====
function openStageRuleConfig(stage: EditStage) {
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId ?? null
  showRuleConfig.value = true
}

function openEntryCondition(stage: EditStage) {
  // 进入条件与阶段规则同走 StageRuleConfigModal
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId ?? null
  showRuleConfig.value = true
}

async function onRuleSaved() {
  // 2026-07-03: 重新拉取这条 link (含 stage_rule + entry_condition 反序列化),
  //   更新对应的 editForm.stages[idx]._rule / _condition, 模板即时反映。
  const linkId = ruleEditingLinkId.value
  if (!linkId || !editForm.value) {
    message.success('阶段配置已保存')
    return
  }
  try {
    const all = await listProcessLinks(props.processId)
    const updated = Array.isArray(all) ? all.find((l: any) => l.id === linkId) : null
    if (!updated) {
      message.success('阶段配置已保存')
      return
    }
    const idx = editForm.value.stages.findIndex((s: EditStage) => s._linkId === linkId)
    if (idx < 0) {
      message.success('阶段配置已保存')
      return
    }
    editForm.value.stages[idx]._rule = updated.stageRule || undefined
    editForm.value.stages[idx]._condition = updated.entryCondition || undefined
    message.success('阶段配置已保存')
  } catch (e: any) {
    message.success('阶段配置已保存 (但本地状态刷新失败，请重新打开查看)')
  }
}

function addStage(position: 'preceding' | 'following' | 'end') {
  if (!editForm.value) return
  if (position === 'end') {
    return addStageAt(editForm.value.stages.length, 'following')
  }
  return addStageAt(
    position === 'preceding'
      ? 0
      : editForm.value.stages.length - 1,
    position,
  )
}

function addStageAt(idx: number, position: 'preceding' | 'following') {
  // 弹窗让用户选 stage; 同流程已用 stage 自动排除, 跨流程可复用。
  openStagePickerAt(idx, position)
}

function _mkStageFromLib(lib: any): EditStage {
  return {
    id: lib.id,
    code: lib.code,
    name: lib.name,
    stageType: lib.stageType || 'SCREEN',
    isStart: !!lib.isStart,
    isEnd: !!lib.isEnd,
    isSystem: !!lib.isSystem,
    stageLimit: undefined,
    features: [],
  }
}

// ===== Stage Picker =====
const showStagePicker = ref(false)
const stagePickerKeyword = ref('')
const stagePickerInsertIdx = ref(0)
const stagePickerInsertPosition = ref<'preceding' | 'following'>('preceding')

const stagePickerCandidates = computed(() => {
  if (!editForm.value) return []
  const usedStageIds = new Set(editForm.value.stages.map(es => es.id))
  const kw = stagePickerKeyword.value.trim().toLowerCase()
  return stageLibrary.value
    .filter(s => !usedStageIds.has(s.id))
    .filter(s => !kw || s.name.toLowerCase().includes(kw) || s.code.toLowerCase().includes(kw))
    .sort((a, b) => {
      // 起止阶段优先 (强制落到首/尾, 显眼), 再按 code 排序
      const ax = a.isStart ? 0 : a.isEnd ? 2 : 1
      const bx = b.isStart ? 0 : b.isEnd ? 2 : 1
      if (ax !== bx) return ax - bx
      return (a.code || '').localeCompare(b.code || '')
    })
})

function openStagePickerAt(idx: number, position: 'preceding' | 'following') {
  if (!editForm.value) return
  stagePickerInsertIdx.value = idx
  stagePickerInsertPosition.value = position
  stagePickerKeyword.value = ''
  showStagePicker.value = true
}

function confirmStagePick(lib: any) {
  if (!editForm.value) return
  if (!lib?.id) return
  const stages = editForm.value.stages
  const newStage = _mkStageFromLib(lib)

  // 起止阶段: 强制放到首/尾, 忽略用户选的 idx
  if (lib.isStart) {
    if (!stages.length || stages[0]?.isStart) {
      message.warning('此流程已存在起始阶段, 不能再添加')
      showStagePicker.value = false
      return
    }
    stages.unshift(newStage)
    message.success(`已添加起始阶段「${newStage.name}」到流程开头`)
    showStagePicker.value = false
    return
  }
  if (lib.isEnd) {
    if (stages.length && stages[stages.length - 1]?.isEnd) {
      message.warning('此流程已存在结束阶段, 不能再添加')
      showStagePicker.value = false
      return
    }
    stages.push(newStage)
    message.success(`已添加结束阶段「${newStage.name}」到流程末尾`)
    showStagePicker.value = false
    return
  }

  const insertIdx = stagePickerInsertPosition.value === 'preceding'
    ? stagePickerInsertIdx.value
    : stagePickerInsertIdx.value + 1
  stages.splice(insertIdx, 0, newStage)
  // 2026-07-03: 防御性 normalize, 防止用户在中间插入后系统起止被挤到非首/尾位置.
  _normalizeStartEnd(stages)
  message.success(`已添加阶段「${newStage.name}」到第 ${insertIdx + 1} 位`)
  showStagePicker.value = false
}

// 2026-07-03: 强制保证系统起止位置不变量 — 起始必须在位置 0, 结束必须在位置 N-1.
function _normalizeStartEnd(stages: EditStage[]) {
  if (!Array.isArray(stages) || stages.length < 2) return
  const startIdx = stages.findIndex(s => s.isStart)
  if (startIdx > 0) {
    const [start] = stages.splice(startIdx, 1)
    stages.unshift(start)
  }
  const endIdx = stages.findIndex(s => s.isEnd)
  const lastIdx = stages.length - 1
  if (endIdx >= 0 && endIdx < lastIdx) {
    const [end] = stages.splice(endIdx, 1)
    stages.push(end)
  }
}

function removeStage(idx: number) {
  if (!editForm.value) return
  const removed = editForm.value.stages[idx]
  editForm.value.stages.splice(idx, 1)
  if (selectedStageIdx.value === idx) selectedStageIdx.value = null
  else if (selectedStageIdx.value !== null && selectedStageIdx.value > idx) {
    selectedStageIdx.value -= 1
  }
  // R-106：编辑态移除阶段属本地可逆操作 → 直接执行 + Toast 撤销（真实重新插入）
  undoable(`已移除阶段「${removed?.name ?? ''}」`, () => {
    editForm.value?.stages.splice(idx, 0, removed)
  })
}

function removeSelectedStage() {
  if (selectedStageIdx.value === null || !editForm.value) return
  removeStage(selectedStageIdx.value)
}

// ===== 409 conflict =====
function abandonEdit() {
  showConflict.value = false
  exitEditMode()
}

async function reloadAndEdit() {
  showConflict.value = false
  await load()
  await enterEdit()
}

// ===== validate + handleSave =====
function validateEditForm(form: EditForm): string | null {
  if (!form.name || !form.name.trim()) return '流程名称不能为空'
  if (form.name.length > 100) return '流程名称不能超过 100 字符'
  if (!Array.isArray(form.stages) || form.stages.length < 2) return '至少需要 2 个阶段 (含起止)'
  if (!form.stages.some(s => s.isStart)) return '缺少起始阶段'
  if (!form.stages.some(s => s.isEnd)) return '缺少结束阶段'
  return null
}

async function handleSave() {
  if (!editForm.value) return
  const form = editForm.value

  // 2026-07-03: 防御性 normalize, 保证起止位置不变量 (即便 Form 状态因 race condition 被破坏).
  _normalizeStartEnd(form.stages)

  // 2. validate
  const err = validateEditForm(form)
  if (err) {
    message.error(err)
    return
  }

  saving.value = true
  try {
    // 3a. applicableScope payload (used in both create + update)
    const applicableScope = {
      mode: form.applicableMode,
      indicators: form.applicableIndicators.map((ind: ScopeIndicator) => ({
        key: ind.key,
        mode: ind.mode,
        values: ind.values || [],
      })),
    }

    // ===== 新建流程路径 =====
    let currentProcessId = props.processId
    if (isCreateMode.value) {
      const created = await createProcess({
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        failPrompt: form.failPrompt,
        applicableMode: form.applicableMode,
        applicableScope: applicableScope as any,
      })
      currentProcessId = created?.id
      if (!currentProcessId) {
        message.error('创建失败: 未返回流程 ID')
        return
      }
    } else {
      // ===== 更新流程路径 =====
      await updateProcess(props.processId, {
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        failPrompt: form.failPrompt,
        applicableMode: form.applicableMode,
        applicableScope: applicableScope as any,
      })

      // 3b. delete removed links (sequential)
      const originalLinkIds = new Set(
        (links.value || []).map((l: any) => l.id).filter(Boolean),
      )
      const currentLinkIds = new Set(
        form.stages.map(s => s._linkId).filter(Boolean) as string[],
      )
      const toDelete = [...originalLinkIds].filter(id => !currentLinkIds.has(id))
      for (const oldId of toDelete) {
        await deleteProcessLink(oldId)
      }
    }

    // 3c. add new links (sequential — needed for stageLimit update below)
    for (let i = 0; i < form.stages.length; i++) {
      const s = form.stages[i]
      if (!s._linkId && s.id) {
        const created = await addProcessLink({
          processId: currentProcessId,
          stageId: s.id,
          stageLimit: s.stageLimit,
          order: i + 1,
        })
        if (created?.id) s._linkId = created.id
      }
    }

    // 3d. reorder links
    const linkIds = form.stages
      .map(s => s._linkId)
      .filter(Boolean) as string[]
    if (linkIds.length) {
      await reorderProcessLinks(currentProcessId, linkIds)
    }

    // 3e. update stageLimit on existing links
    for (const s of form.stages) {
      if (s._linkId && s.stageLimit !== undefined && s.stageLimit !== null) {
        await updateProcessLink(s._linkId, { stageLimit: s.stageLimit })
      }
    }

    // 3f. 刷新 data + links: create 模式也要 (虽然 data 为空, 但 load() 用 currentProcessId)
    if (!isCreateMode.value) {
      await load()
    } else {
      data.value = { id: currentProcessId, name: form.name }
      links.value = []
    }

    // 3g. success path
    exitEditMode()
    message.success(isCreateMode.value ? '已创建' : '已保存')
    emit('saved', currentProcessId)
  } catch (e: any) {
    // 409 conflict path
    if (e?.response?.status === 409) {
      showConflict.value = true
      conflictInfo.value = e.response.data || {}
    } else {
      message.error(e?.response?.data?.message || (isCreateMode.value ? '创建失败' : '保存失败'))
    }
  } finally {
    saving.value = false
  }
}

async function onCopy() {
  if (!props.processId || !data.value) return
  copying.value = true
  try {
    const newProc = await copyProcess(props.processId, {
      newName: `${data.value.name} - 副本`,
    })
    message.success(`已复制: ${newProc.name}`)
    emit('copied', newProc.id)
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '复制失败')
  } finally {
    copying.value = false
  }
}

// ===== 适用范围工具函数 =====
const hasAnyScope = computed(() => {
  if (!data.value) return false
  const inds = (data.value.applicableScope as any)?.indicators
  const items = (data.value.applicableScope as any)?.items
  const hasOldFields = Array.isArray(data.value.applicableDepartments) && data.value.applicableDepartments.length > 0
  return (Array.isArray(inds) && inds.length > 0) ||
         (Array.isArray(items) && items.length > 0) ||
         hasOldFields
})

function findIndicator(key: string): any | null {
  if (!data.value) return null
  // 旧形态: { mode, indicators: [{key, mode, values}] }
  const inds = data.value.applicableScope?.indicators
  if (Array.isArray(inds)) {
    return inds.find((i: any) => i.key === key) || null
  }
  // 新形态: { items: [{op, field, value}], expression } — 按 field 前缀映射
  const items = (data.value.applicableScope as any)?.items as any[] | undefined
  if (Array.isArray(items) && items.length) {
    const FIELD_TO_KEY: Record<string, string> = {
      recruitment_type: 'department',
      position_category: 'position',
      job_level: 'level',
      position_level: 'level',
      recruiter: 'user',
      owner: 'user',
      recruiter_id: 'user',
    }
    const filtered = items
      .filter((it) => FIELD_TO_KEY[it.field] === key)
      .map((it) => (Array.isArray(it.value) ? it.value : [it.value]))
      .flat()
      .filter(Boolean)
    if (filtered.length) {
      return { key, mode: 'include', values: filtered }
    }
  }
  // fallback: 旧字段
  if (key === 'department' && Array.isArray(data.value.applicableDepartments)) {
    return { key, mode: 'include', values: data.value.applicableDepartments }
  }
  return null
}

function getScopeMode(key: string): 'include' | 'exclude' | null {
  return (findIndicator(key)?.mode as 'include' | 'exclude') || null
}

function getScopeModeLabel(key: string): string {
  const mode = getScopeMode(key)
  if (mode === 'include') return '包含'
  if (mode === 'exclude') return '不包含'
  return '不限'
}

function getScopeValues(key: string): string[] {
  return (findIndicator(key)?.values as string[]) || []
}

function getScopeValueCount(key: string): number {
  return getScopeValues(key).length
}

function getScopeCardClass(key: string): string {
  const mode = getScopeMode(key)
  if (mode === 'exclude') return 'scope-card--exclude'
  if (mode === 'include') return 'scope-card--include'
  return 'scope-card--neutral'
}

// D1: 适用范围选项实时取自响应式 deptOptions/positionOptions/userOptions (loadScopeOptions 填充),
//   保证选项到位后 select 自动回填, 编辑态可正常选择.
function scopeOptionsFor(key: ScopeKey): { label: string; value: string }[] {
  switch (key) {
    case 'department': return deptOptions.value
    case 'position': return positionOptions.value
    case 'user': return userOptions.value
    case 'level': return [] // 职级暂无独立接口
    default: return []
  }
}

// ===== Edit-mode scope card class (driven by indicator.mode + values) =====
function getScopeEditCardClass(ind: ScopeIndicator): string {
  if (ind.mode === 'exclude') return 'scope-card--exclude'
  if (ind.values?.length) return 'scope-card--include'
  return 'scope-card--neutral'
}

// ===== 格式化辅助函数 =====
function stageTypeLabel(t?: string): string {
  return STAGE_TYPE_META[t || '']?.label || t || '-'
}

function stageTypeColor(t?: string): string {
  return STAGE_TYPE_META[t || '']?.color || 'var(--n-400)'
}

function stageTypeTagType(t?: string): 'info' | 'warning' | 'success' | 'primary' | 'default' {
  return STAGE_TYPE_META[t || '']?.tagType || 'default'
}

function stageTypeIcon(t?: string) {
  return STAGE_TYPE_META[t || '']?.icon || InformationCircleOutline
}

function featureLabel(f: string): string {
  return FEATURE_LABEL[f] || f
}

// 锚点导航：滚动到对应 section（与 sticky topbar 配合）
function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
/* ===== 顶部概览条 (V8 dp-topbar, sticky) ===== */
.dp-wrap {
  max-width: 920px;
  margin: 0 auto;
  padding: 0 4px 24px;
}

.dp-topbar {
  position: sticky;
  top: 0;
  z-index: 90;
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border-bottom: 1px solid var(--g2);
  margin: 0 -20px 12px;
}
.dp-topbar-inner {
  max-width: 920px;
  margin: 0 auto;
  padding: 11px var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.dp-logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand), color-mix(in srgb, var(--brand) 70%, white));
  color: var(--on-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.dp-title-block { flex: 1; min-width: 0; }
.dp-title {
  font-size: var(--fs-16);
  font-weight: 600;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.dp-title > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dp-meta {
  margin-top: 3px;
  display: flex;
  gap: var(--space-3);
  font-size: var(--fs-12);
  color: var(--n-450);
  flex-wrap: wrap;
}
.dp-meta :deep(.n-icon) {
  font-size: var(--fs-13);
  margin-right: 4px;
  color: var(--n-350);
}
.dp-tabs {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}
.dp-tab {
  font: inherit;
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink-soft);
  padding: 6px var(--space-2);
  border-radius: 7px;
  cursor: pointer;
  text-decoration: none;
  background: transparent;
  border: 1px solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
}
.dp-tab:hover {
  background: color-mix(in srgb, var(--brand) 10%, white);
  color: var(--brand);
}
.dp-tab:focus-visible {
  outline: none;
  border-color: var(--brand);
  color: var(--brand);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 25%, transparent);
}
.dp-actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* ===== 分区标题 (紫色竖条, V8 dp-section-title) ===== */
.dp-section {
  scroll-margin-top: 76px;
  margin-top: var(--space-4);
}
.dp-section-title {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin: var(--space-4) 0 var(--space-2);
}
.dp-section-title::before {
  content: '';
  width: 4px;
  height: 14px;
  border-radius: 2px;
  background: var(--brand);
  align-self: center;
}
.dp-section-title h3 {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
}
.dp-section-title .hint { font-size: var(--fs-12); color: var(--n-450); }
.dp-section-title .warn { font-size: var(--fs-12); color: var(--brand-warm-deep); }

/* ===== 通用白卡 (V8 dp-card) ===== */
.dp-card {
  background: var(--surface);
  border: 1px solid var(--g2);
  border-radius: var(--radius-md);
  padding: 4px var(--space-4);
}

/* 基础信息: 标题在上、控件在下的字段网格 */
.dp-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-3) var(--space-4);
  padding: var(--space-3) 0 var(--space-4);
}
.dp-field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
.dp-field.span-full { grid-column: 1 / -1; }
.dp-flabel {
  font-size: var(--fs-13);
  color: var(--ink-soft);
  font-weight: 500;
}

/* ===== 适用范围编辑器 ===== */
.scope-card-list { width: 100%; }
.scope-card {
  border: 1px solid var(--g2);
  border-radius: var(--radius-md);
  padding: 12px var(--space-3);
  background: var(--glass-bg-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  transition: all var(--duration-fast) var(--ease-out);
}
.scope-card:hover { box-shadow: 0 2px 8px var(--overlay-scrim-weak); }
.scope-card--include { border-color: var(--c-info-bg); }
.scope-card--exclude { border-color: var(--c-error-bg); }
.scope-card--neutral { border-color: var(--g2); }
.scope-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
}
.scope-card__head :deep(.n-icon) {
  font-size: var(--fs-14);
  color: var(--brand);
}
.scope-card--exclude .scope-card__head :deep(.n-icon) { color: var(--c-error); }
.scope-card__name { flex: 1; }
.scope-card__mode {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 11px;
}
.scope-card__mode :deep(.n-radio-group) { flex: 1 1 auto; min-width: 0; }
.scope-card__count {
  color: var(--n-400);
  flex-shrink: 0;
  white-space: nowrap;
  margin-left: auto;
}
.scope-card__values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  flex: 1;
  align-items: flex-start;
}

/* ===== 阶段列表 (V8 stage-list) ===== */
.stage-list { display: flex; flex-direction: column; gap: var(--space-3); }

/* 阶段卡片 (保留 .stage-card 类名 — 单测契约依赖) */
.stage-card {
  position: relative;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--space-4);
  transition: box-shadow var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.stage-card:last-child { margin-bottom: 0; }
.stage-card:hover {
  box-shadow: var(--shadow-panel);
  border-color: var(--glass-border-strong);
}

/* 阶段 header */
.stage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--glass-border);
  margin-bottom: var(--space-2);
}
.header-left { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.header-right { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

.stage-no {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--brand) 12%, white);
  color: var(--brand);
  font-size: var(--fs-13);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stage-name {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
  margin-right: var(--space-1);
}
/* 保留 .stage-card__system-badge 类名 — 单测契约依赖 (首末 2 个) */
.stage-card__system-badge { margin-left: 2px; }

/* 卡内 config 网格 */
.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}
.config-item {
  background: var(--g1);
  border: 1px solid var(--g2);
  border-radius: 10px;
  padding: var(--space-2) var(--space-3);
  min-width: 0;
}
.config-item.span-2 { grid-column: 1 / -1; }
.config-item .item-title {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--n-450);
  letter-spacing: .4px;
  margin-bottom: 6px;
}
.config-item .item-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.config-item.handler-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
}
.config-item.handler-row .item-title { flex: 0 0 auto; margin-bottom: 0; }
.config-item.handler-row .item-body {
  flex: 1;
  min-width: 0;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.handler-tag {
  background: var(--g1);
  color: var(--ink);
  font-size: var(--fs-12);
  font-weight: 500;
  padding: 1px var(--space-2);
  line-height: 22px;
  border-radius: 6px;
}
.handler-none { font-size: var(--fs-12); color: var(--n-450); }

/* 功能 tag */
.feature-tags { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.feature-tag {
  display: inline-flex;
  align-items: center;
  background: color-mix(in srgb, var(--brand) 10%, white);
  color: var(--brand);
  font-size: var(--fs-12);
  padding: 2px var(--space-2);
  border-radius: 3px;
  line-height: 1.5;
  white-space: nowrap;
}
.feature-empty {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-12);
  color: var(--n-450);
  min-height: 40px;
}
.feature-empty :deep(.n-icon) { font-size: var(--fs-13); color: var(--n-350); }

/* 自动化子网格 */
.auto-grid { display: flex; flex-direction: column; gap: 5px; width: 100%; }
.auto-item { display: flex; align-items: center; gap: 6px; min-width: 0; }
.auto-item .label {
  flex: 0 0 64px;
  font-size: var(--fs-12);
  font-weight: 500;
  color: var(--n-450);
}
.auto-item .value {
  flex: 1;
  min-width: 0;
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-success);
  flex-shrink: 0;
}
.status-dot.off { background: var(--g4); }

/* ===== 空状态 ===== */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  color: var(--n-400);
  padding: var(--space-8) 0;
}

/* 加载错误态 (E1) */
.dp-load-error {
  padding: var(--space-8) 0;
  text-align: center;
}

/* ===== Stage Picker ===== */
.picker-empty { padding: var(--space-6) 0; }
.picker-list { display: flex; flex-direction: column; gap: var(--space-2); }
.picker-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--g2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-out);
}
.picker-item:hover { border-color: var(--brand); }
.picker-item--start { border-left: 3px solid var(--c-success); }
.picker-item--end { border-left: 3px solid var(--c-warning); }
.picker-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.picker-item__main { flex: 1; min-width: 0; }
.picker-item__name { font-size: var(--fs-14); font-weight: 600; color: var(--ink); }
.picker-item__code { font-size: var(--fs-12); color: var(--n-450); }
.picker-item__hint { font-size: var(--fs-12); color: var(--n-350); white-space: nowrap; }

/* 响应式 */
@media (max-width: 640px) {
  .dp-form-grid { grid-template-columns: 1fr; gap: var(--space-3); }
  .config-grid { grid-template-columns: 1fr; }
  .dp-topbar-inner { flex-wrap: wrap; gap: var(--space-2); }
  .dp-tabs { order: 3; width: 100%; }
}
</style>

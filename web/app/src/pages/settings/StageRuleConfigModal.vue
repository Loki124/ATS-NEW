<!--
  Plan K #7: 配置阶段规则 Modal
  原型 3:
    - 自动化流转条件 (select: 满足下阶段进入条件)
    - 执行时机 (select)
    - 默认处理人 (table: 数据来源/取值字段/处理规则, 多行)
    - 阶段限时 (table: 规则名/条件/动作, 启停用)
    - 面试轮次 (复选: 联合面试/综合面试)
    - 面试形式 (复选: 现场面试/电话面试/视频面试/AI面试)
    - 取消 / 提交 按钮
-->
<template>
  <n-modal
    :show="show"
    class="stage-rule-config-modal"
    preset="card"
    :title="undefined"
    style="width: 760px; max-width: 95vw; max-height: 90vh"
    :mask-closable="!saving"
    :on-mask-click="onRequestClose"
    @update:show="(v) => emit('update:show', v)"
    @after-leave="resetTransient"
  >
    <n-spin :show="loading">
      <div class="rule-config-body">
        <!-- HERO HEADER -->
        <div class="hero">
          <div class="hero__icon">
            <n-icon :component="SettingsOutline" size="22" />
          </div>
          <div class="hero__main">
            <div class="hero__title">
              <span>配置阶段规则</span>
              <span class="hero__stage-chip">—— {{ stage?.name || '未命名' }}</span>
            </div>
            <div class="hero__subtitle">
              为本阶段配置自动化、默认处理人、限时与进入条件
            </div>
          </div>
          <span class="hero__tip" aria-label="即时生效">
            <n-icon :component="FlashOutline" size="12" /> 即时生效
          </span>
          <button
            class="hero__close"
            type="button"
            aria-label="关闭"
            :disabled="saving"
            @click="onRequestClose"
          >
            <n-icon :component="CloseOutline" size="20" />
          </button>
        </div>

        <!-- 分区锚点导航：配置项较多时快速定位（sticky 吸顶，随内容区滚动） -->
        <nav class="section-nav" aria-label="配置项分区">
          <button
            v-for="s in visibleSections"
            :key="s.key"
            type="button"
            class="section-nav__item"
            :class="{ 'section-nav__item--active': activeSection === s.key }"
            @click="scrollToSection(s.key)"
          >
            {{ s.label }}
          </button>
        </nav>

        <div class="rule-config-flat">
          <!-- ============ Card 1: 流程自动化 (完全参照原型) ============ -->
          <div class="config-card">
            <div class="card-title">
              <n-icon :component="GitNetworkOutline" /> 流程自动化
              <span class="title-desc">· 配置阶段的自动评估、流转、跳过与归档规则</span>
            </div>

            <!-- Block 1: 自动评估 -->
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="ConstructOutline" /> 自动评估
                <span class="block-desc">· 当前阶段的自动化评估规则</span>
              </div>
              <div class="option-grid">
                <label class="opt-item">
                  <n-checkbox v-model:checked="form.grabModeEnabled" />
                  <span>N+2 推荐免筛选</span>
                </label>
                <label class="opt-item">
                  <n-checkbox v-model:checked="form.inheritPriorConsensus" />
                  <span>引用前序双 A 的一致意见</span>
                </label>
              </div>
            </div>

            <!-- Block 2: 自动流转 (双列内联 + 自动流转条件) -->
            <div class="flow-block">
              <div class="block-header block-header--secondary">
                <n-icon :component="ArrowForwardOutline" /> 自动流转
                <span class="block-desc">· 满足自动流转条件时，在到达执行时机后自动流转到下阶段</span>
              </div>
              <div class="flow-condition-row">
                <div class="flow-field">
                  <label class="field-label">自动流转条件</label>
                  <n-select
                    v-model:value="form.autoAdvanceType"
                    :options="autoAdvanceOptions"
                    size="small"
                  />
                </div>
                <div class="flow-field">
                  <label class="field-label">执行时机</label>
                  <n-select
                    v-model:value="form.autoAdvanceTiming"
                    :options="timingOptions"
                    size="small"
                  />
                </div>
              </div>
              <div v-if="form.autoAdvanceTiming === 'DELAYED'" class="flow-condition-row">
                <div class="flow-field">
                  <label class="field-label">延迟天数 (1-15 工作日)</label>
                  <n-input-number v-model:value="form.autoAdvanceDays" :min="1" :max="15" size="small" />
                </div>
              </div>
            </div>

            <!-- Block 3: 自动跳过 (开关 + 规则表) -->
            <div class="flow-block">
              <div class="block-header block-header--split">
                <div class="block-header__main">
                  <n-icon :component="PlaySkipForwardOutline" /> 自动跳过
                  <span class="block-desc">· 满足规则时不再停留，直接判断是否满足下阶段进入条件</span>
                </div>
                <label class="switch-pill" :class="{ 'switch-pill--on': form.skipEnabled }">
                  <input
                    type="checkbox"
                    class="switch-pill__input"
                    :checked="form.skipEnabled"
                    :disabled="saving"
                    @change="form.skipEnabled = ($event.target as HTMLInputElement).checked"
                  >
                  <span class="switch-pill__track"><span class="switch-pill__dot"></span></span>
                  <span class="switch-pill__label">{{ form.skipEnabled ? '开启' : '关闭' }}</span>
                </label>
              </div>
              <div class="rule-content" :class="{ 'rule-content--hidden': !form.skipEnabled }">
                <div class="rule-table-wrap">
                  <table class="rule-table">
                    <thead>
                      <tr>
                        <th style="width: 70px;">规则名称</th>
                        <th>执行条件</th>
                        <th>执行动作</th>
                        <th style="width: 100px;">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="form.skipRules.length === 0">
                        <td colspan="4" class="rule-table__empty">暂无规则，点击下方添加</td>
                      </tr>
                      <tr v-for="(rule, idx) in form.skipRules" :key="rule._key">
                        <td><strong>跳过{{ idx + 1 }}</strong></td>
                        <td>
                          <n-input v-model:value="rule.condition" size="small" placeholder="如：候选人已接受其他 offer" />
                        </td>
                        <td>
                          <n-input v-model:value="rule.action" size="small" placeholder="如：跳过本阶段" />
                        </td>
                        <td>
                          <div class="action-btns">
                            <a class="danger" @click="removeSkipRule(idx)">
                              <n-icon :component="TrashOutline" size="12" /> 删除
                            </a>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="actions-row">
                  <button class="btn-outline-primary" type="button" @click="addSkipRule">
                    <n-icon :component="AddOutline" size="12" /> 添加规则
                  </button>
                </div>
              </div>
            </div>

            <!-- Block 4: 自动归档 (开关 + 规则表，复用 time-limit 数据) -->
            <div class="flow-block">
              <div class="block-header block-header--split">
                <div class="block-header__main">
                  <n-icon :component="HourglassOutline" /> 自动归档
                  <span class="block-desc">· 限定阶段总时长，超时自动归档候选人到公共人才库</span>
                </div>
                <label class="switch-pill" :class="{ 'switch-pill--on': form.timeLimitEnabled }">
                  <input
                    type="checkbox"
                    class="switch-pill__input"
                    :checked="form.timeLimitEnabled"
                    :disabled="saving"
                    @change="form.timeLimitEnabled = ($event.target as HTMLInputElement).checked"
                  >
                  <span class="switch-pill__track"><span class="switch-pill__dot"></span></span>
                  <span class="switch-pill__label">{{ form.timeLimitEnabled ? '开启' : '关闭' }}</span>
                </label>
              </div>
              <div class="rule-content" :class="{ 'rule-content--hidden': !form.timeLimitEnabled }">
                <div class="rule-table-wrap">
                  <table class="rule-table">
                    <thead>
                      <tr>
                        <th style="width: 70px;">规则名称</th>
                        <th>执行条件</th>
                        <th>执行动作</th>
                        <th style="width: 100px;">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="form.timeLimitRules.length === 0">
                        <td colspan="4" class="rule-table__empty">暂无规则，点击下方添加</td>
                      </tr>
                      <tr v-for="(rule, idx) in form.timeLimitRules" :key="rule._key">
                        <td><strong>{{ rule.name || `归档${idx + 1}` }}</strong></td>
                        <td>
                          <n-input v-model:value="rule.condition" size="small" placeholder="如：候选人性别为空" />
                        </td>
                        <td>
                          <n-input v-model:value="rule.action" size="small" placeholder="如：锁定时长30天" />
                        </td>
                        <td>
                          <div class="action-btns">
                            <a class="danger" @click="removeTimeLimitRule(idx)">
                              <n-icon :component="TrashOutline" size="12" /> 删除
                            </a>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="actions-row">
                  <button class="btn-outline-primary" type="button" @click="addTimeLimitRule">
                    <n-icon :component="AddOutline" size="12" /> 添加规则
                  </button>
                  <n-divider vertical />
                  <n-text depth="3" style="font-size: 12px">插入预置:</n-text>
                  <n-button size="small" quaternary @click="insertPreset('PRESIDENT')">总裁级 (90 天)</n-button>
                  <n-button size="small" quaternary @click="insertPreset('DIRECTOR')">总监级 (60 天)</n-button>
                  <n-button size="small" quaternary @click="insertPreset('OTHER')">其他级别 (30 天)</n-button>
                </div>
              </div>
            </div>
          </div>

          <!-- ============ Card 2: 默认处理人 (完全参照原型 3 字段内联) ============ -->
          <div class="config-card">
            <div class="card-title">
              <n-icon :component="PersonOutline" /> 默认处理人
              <span class="title-desc">· 进入本阶段时自动为默认处理人添加待办任务</span>
            </div>
            <div class="flow-condition-row flow-condition-row--3">
              <div class="flow-field">
                <label class="field-label">
                  数据来源 <span class="required-mark">*</span>
                </label>
                <n-select
                  v-model:value="primaryHandler.dataSource"
                  :options="dataSourceOptions"
                  size="small"
                  @update:value="onPrimaryDataSourceChange"
                />
              </div>
              <div class="flow-field">
                <label class="field-label">
                  取值字段 <span class="required-mark">*</span>
                </label>
                <n-select
                  v-model:value="primaryHandler.field"
                  :options="fieldOptionsBySource[primaryHandler.dataSource] || []"
                  :disabled="primaryHandler.dataSource === 'NONE'"
                  placeholder="无需选择"
                  size="small"
                />
              </div>
              <div class="flow-field">
                <label class="field-label">处理规则</label>
                <n-select
                  v-model:value="primaryHandler.strategy"
                  :options="strategyOptions"
                  :disabled="primaryHandler.dataSource === 'NONE'"
                  size="small"
                />
              </div>
            </div>
          </div>

          <!-- ============ Card 3 (项目扩展): 面试轮次 + 形式 (仅 INTERVIEW 阶段) ============ -->
          <div v-if="isInterviewType" class="config-card">
            <div class="card-title">
              <n-icon :component="BriefcaseOutline" /> 面试配置
              <span class="title-desc">· 面试轮次与形式（仅面试/邀约阶段）</span>
            </div>
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="LayersOutline" /> 面试轮次 (可多选)
              </div>
              <div class="option-grid">
                <label v-for="opt in interviewRoundOptions" :key="opt.value" class="opt-item">
                  <n-checkbox
                    :checked="form.interviewRounds.includes(opt.value)"
                    @update:checked="(v: boolean) => onInterviewToggle('rounds', opt.value, v)"
                  />
                  <span>{{ opt.label }}</span>
                </label>
              </div>
            </div>
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="VideocamOutline" /> 面试形式 (可多选)
              </div>
              <div class="option-grid">
                <label v-for="opt in interviewFormOptions" :key="opt.value" class="opt-item">
                  <n-checkbox
                    :checked="form.interviewForms.includes(opt.value)"
                    @update:checked="(v: boolean) => onInterviewToggle('forms', opt.value, v)"
                  />
                  <span>{{ opt.label }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- ============ Card 4 (项目扩展): 进入条件 ============ -->
          <div class="config-card">
            <div class="card-title">
              <n-icon :component="LockClosedOutline" /> 进入条件
              <span class="title-desc">· 候选人进入此阶段需满足的判定条件</span>
            </div>
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="GitCompareOutline" /> 判定方式
              </div>
              <n-radio-group v-model:value="condForm.matchType" name="matchType">
                <n-space>
                  <n-radio value="ALL">全部满足 (AND)</n-radio>
                  <n-radio value="ANY">任意满足 (OR)</n-radio>
                </n-space>
              </n-radio-group>
            </div>
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="CodeSlashOutline" /> 条件表达式 (可选)
              </div>
              <n-input
                v-model:value="condForm.expression"
                placeholder="如: (1 AND 2) OR (3 AND 4)"
                :status="exprValidation && !exprValidation.valid ? 'error' : undefined"
                @blur="onExprBlur"
              />
              <div v-if="exprValidation && !exprValidation.valid" class="field-error-hint">
                {{ exprValidation.error }}
              </div>
              <div v-else class="field-hint" style="margin-top: 6px;">留空则用上面条件树自动生成</div>
            </div>
            <div class="flow-block">
              <div class="block-header">
                <n-icon :component="ChatboxOutline" /> 未满足条件时提示内容 (选填)
              </div>
              <n-input
                v-model:value="condForm.prompt"
                type="textarea"
                :rows="3"
                placeholder="如: 请先完成 HRBP 评估"
              />
              <div class="field-hint" style="margin-top: 6px;">选填。填写后会在候选人未满足进入条件时展示该提示。</div>
            </div>
          </div>
        </div>
      </div>
    </n-spin>

    <template #footer>
      <div class="modal-footer">
        <n-button :disabled="saving" @click="onRequestClose">取消</n-button>
        <n-button
          type="primary"
          class="gradient-btn"
          :loading="saving"
          :disabled="saving || hasExprError"
          @click="handleSubmit"
        >
          保存
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, h, onMounted } from 'vue'
import {
  NModal, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect,
  NCheckbox, NCheckboxGroup, NButton, NSpace, NAlert, NSpin, NTag, NPopconfirm,
  NRadio, NRadioGroup, NDataTable, NIcon, useMessage,
} from 'naive-ui'
import {
  upsertStageRule, upsertEntryCondition, listStageRules, listEntryConditions,
  type ConditionItem,
} from '../../api/recruitment-process'
import { validateExpression } from '../../utils/condition-expression'
import { default as axios } from 'axios'
import config from '../../config'
import { SettingsOutline, CloseOutline, FlashOutline, AddOutline, TrashOutline,
  OptionsOutline, GitNetworkOutline, PersonOutline, TimerOutline,
  BriefcaseOutline, LockClosedOutline,
  ConstructOutline, ArrowForwardOutline, PlaySkipForwardOutline, HourglassOutline,
  LayersOutline, VideocamOutline, GitCompareOutline, CodeSlashOutline,
  ChatboxOutline } from '@vicons/ionicons5'

// 嵌套条件项（3 级树） - 扩展 ConditionItem 增加 children 字段
interface ConditionItemTree extends ConditionItem {
  children?: ConditionItemTree[]
}

const props = defineProps<{
  show: boolean
  stage: any | null
  linkId: string | null
  // 2026-06-17: 让父级可以选择默认 tab ('auto' / 'handler' / 'timelimit' / 'interview' / 'condition')
  initialTab?: 'auto' | 'handler' | 'timelimit' | 'interview' | 'condition'
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const loading = ref(false)
const saving = ref(false)

/**
 * 分区锚点导航（与模板 data-section 一一对应）
 * 2026-08-31: 原 activeTab 只在 handleSubmit 里做分支判定，但本弹窗是**扁平表单**，
 *   没有 tab 切换 UI → activeTab 恒为 'auto' → 进入条件分支永不触发（见 handleSubmit 注释）。
 *   这里把 initialTab 重新解释为「初始定位到哪个分区」，prop 契约不变。
 */
const SECTIONS = [
  { key: 'auto', label: '自动处理' },
  { key: 'flow', label: '流转条件' },
  { key: 'handler', label: '默认处理人' },
  { key: 'timelimit', label: '阶段限时' },
  { key: 'interview', label: '面试配置' },
  { key: 'condition', label: '进入条件' },
] as const
type SectionKey = typeof SECTIONS[number]['key']
const activeSection = ref<SectionKey>((props.initialTab as SectionKey) || 'auto')

const isInterviewType = computed(() => {
  return props.stage?.stageType === 'INTERVIEW' || props.stage?.stageType === 'INVITATION'
})

const visibleSections = computed(() =>
  SECTIONS.filter((s) => s.key !== 'interview' || isInterviewType.value),
)

/** 弹窗内容被 teleport 到 <body>，scoped 拿不到，只能按 modal class 定位唯一滚动容器 */
function getScrollHost(): HTMLElement | null {
  return document.querySelector('.stage-rule-config-modal .n-card-content')
}

function scrollToSection(key: SectionKey) {
  activeSection.value = key
  const el = getScrollHost()?.querySelector<HTMLElement>(`[data-section="${key}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 表单 state
const form = reactive({
  // 2026-06-17: 4 个总开关 (按截图"自动处理规则" + 阶段限时"是否开启")
  autoAdvanceEnabled: true,
  grabModeEnabled: false,            // N+2 推荐免筛选
  inheritPriorConsensus: false,      // 引用前序双 A 的一致意见
  timeLimitEnabled: false,
  // 2026-09-03: 自动跳过开关 + 规则 (原型新增模块，UI-only 不写入后端)
  skipEnabled: false,
  skipRules: [] as Array<{
    _key: string
    condition: string
    action: string
    enabled: boolean
  }>,
  // 自动化
  autoAdvanceType: 'NONE' as 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS',
  autoAdvanceTiming: 'NONE' as 'NONE' | 'IMMEDIATE' | 'DELAYED',
  autoAdvanceDays: undefined as number | undefined,
  // 默认处理人 (多行)
  handlerRules: [] as Array<{
    _key: string
    dataSource: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM'
    field: string
    strategy: 'NONE' | 'ROUND_ROBIN' | 'IN_ORDER'
    enabled: boolean
  }>,
  // 阶段限时 (多行) - 自动归档 block 用，复用 time-limit 接口
  timeLimitRules: [] as Array<{
    _key: string
    name: string
    condition: string
    action: string
    enabled: boolean
  }>,
  // 阶段限时 (按职级的小时数, 预置按钮使用)
  timeLimitHoursByLevel: {} as Record<string, number>,
  // 面试
  interviewRounds: [] as string[],
  interviewForms: [] as string[],
})

// 进入条件 (单独 form)
const condForm = reactive({
  matchType: 'ALL' as 'ALL' | 'ANY',
  conditionType: 'MIXED' as 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED',
  prompt: '',
  expression: '', // Plan L: 可选手写表达式
  items: [] as ConditionItemTree[],
})

/**
 * Plan L #3b: 表达式实时校验
 *  - 空 → 合法 (留空 = 全部满足)
 *  - 非空 → 校验括号、数字范围、AND/OR 平衡
 */
const exprValidation = computed(() => {
  if (!condForm.expression) return null
  return validateExpression(condForm.expression, condForm.items?.length || 0)
})

function onExprBlur() {
  if (!condForm.expression) return
  const r = validateExpression(condForm.expression, condForm.items?.length || 0)
  if (!r.valid) {
    message.warning(`表达式校验失败: ${r.error}`)
  }
}

/** 表达式非法 → 禁用提交，避免把错误配置写库（此前只在 blur 提示，提交路径无校验） */
const hasExprError = computed(() => !!exprValidation.value && !exprValidation.value.valid)

/** 统一关闭入口：保存中禁止关闭，避免提交到一半被关掉留下半截状态 */
function onRequestClose() {
  if (saving.value) return
  emit('update:show', false)
}

/** 关闭动画结束后复位瞬时状态；DOM 此时可能已被移除，取不到容器是正常情况 */
function resetTransient() {
  saving.value = false
  activeSection.value = 'auto'
  getScrollHost()?.scrollTo({ top: 0 })
}

const autoAdvanceOptions = [
  { label: '不自动流转', value: 'NONE' },
  { label: '满足下阶段进入条件时 (推荐)', value: 'MEET_NEXT' },
  { label: '无视下阶段进入条件', value: 'IGNORE_NEXT' },
  { label: '满足下阶段条件或 N+2 推荐', value: 'MEET_NEXT_OR_N2' },
  { label: 'N+1 全部通过', value: 'N1_ALL_PASS' },
]

/**
 * 执行时机改为下拉单选（参照原型交互），值复用 NONE/IMMEDIATE/DELAYED，
 * DELAYED 模式下额外由 autoAdvanceDays 控制天数。
 */
const timingOptions = [
  { label: '立即执行 (默认)', value: 'IMMEDIATE' },
  { label: '不执行', value: 'NONE' },
  { label: '延迟 N 个工作日执行', value: 'DELAYED' },
]

const dataSourceOptions = [
  { label: '需求中', value: 'FROM_DEMAND' },
  { label: '职位中', value: 'FROM_POSITION' },
  { label: '指定人员', value: 'CUSTOM' },
  { label: '无默认处理人', value: 'NONE' },
]

/**
 * 默认处理人 · 三字段内联（参照原型）
 *  - 第一行作为「主配置」直接绑到本 state；
 *  - 提交时若 form.handlerRules 为空，把这一行同步写回 handlerRules[0] 落库。
 *  - 这样既保留原多行表数据结构（向后兼容已存在的 StageRule 数据），又给用户最简单的单行交互。
 */
const primaryHandler = reactive<{
  dataSource: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM' | 'NONE'
  field: string
  strategy: 'NONE' | 'ROUND_ROBIN' | 'IN_ORDER'
}>({
  dataSource: 'FROM_DEMAND',
  field: '',
  strategy: 'NONE',
})

function onPrimaryDataSourceChange(v: typeof primaryHandler.dataSource) {
  // 数据来源变更 → 取值字段与处理规则必须重置（原型交互铁律）
  primaryHandler.field = ''
  if (v === 'NONE') {
    primaryHandler.strategy = 'NONE'
  }
}

const fieldOptionsBySource: Record<string, any[]> = {
  FROM_DEMAND: [
    { label: 'HRBP', value: 'HRBP' },
    { label: '用人经理', value: 'MANAGER' },
    { label: '用人经理上级', value: 'MANAGER_SUPER' },
  ],
  FROM_POSITION: [
    { label: '职位负责人', value: 'POSITION_OWNER' },
    { label: '职位协助人', value: 'POSITION_ASSISTANT' },
    { label: '职位负责人及协助人', value: 'POSITION_OWNER_ASSISTANT' },
    { label: '用人经理', value: 'MANAGER' },
    { label: 'HRBP', value: 'HRBP' },
  ],
  CUSTOM: [
    { label: '默认处理人 (指定)', value: 'CUSTOM_HANDLER' },
  ],
}

const strategyOptions = [
  { label: '无特定规则', value: 'NONE' },
  { label: '邀约阶段轮流邀约制', value: 'ROUND_ROBIN' },
  { label: '按页面展示顺序执行', value: 'IN_ORDER' },
]

const timeLimitConditionOptions = [
  { label: '判断阶段条件', value: 'STAGE_CONDITION' },
  { label: '判断年龄', value: 'AGE' },
  { label: '判断工作经验', value: 'WORK_YEARS' },
  { label: '判断岗位年限', value: 'POSITION_YEARS' },
  { label: '判断最高学历', value: 'HIGHEST_EDU' },
]

const timeLimitActionOptions = [
  { label: '自动转交下一处理人', value: 'TRANSFER' },
  { label: '自动归档', value: 'ARCHIVE' },
  { label: '通知 HR', value: 'NOTIFY' },
]

// 2026-07-03: BE 没实现 /api/v1/dictionary/ (Plan 注释标记 "待实现"). 之前 fetch → 404 → fallback.
//   404 在 main.ts 全局拦截器里 console.warn, 噪声. 既然 fallback 跟远端数据只是名称不同 (code 一致),
//   干脆不请求, 直接用 hardcoded 列表, 避免 404 噪声.
const interviewRoundOptions = ref<{ label: string; value: string }[]>([
  { label: '联合面试', value: 'JOINT' },
  { label: '综合面试', value: 'COMPREHENSIVE' },
  { label: '初试', value: 'INITIAL' },
  { label: '复试', value: 'SECOND' },
  { label: '终试', value: 'FINAL' },
])
const interviewFormOptions = ref<{ label: string; value: string }[]>([
  { label: '现场面试', value: 'ONSITE' },
  { label: '电话面试', value: 'PHONE' },
  { label: '视频面试', value: 'VIDEO' },
  { label: 'AI 面试', value: 'AI' },
])

// 保留函数签名以便后续如果 BE 接入 /api/v1/dictionary/ 也能快速切回 (把下面 ref 改回空 [] 即可).
async function loadDictionaryOptions() {
  // 2026-07-03: 故意 no-op, 真实字典拉取在 BE 端没实现. 真正接入时恢复:
  //   const token = localStorage.getItem('accessToken') || localStorage.getItem('token')
  //   const [roundRes, formRes] = await Promise.all([
  //     axios.get(`${config.api.baseUrl}/dictionary/interview_round`, { headers: { Authorization: `Bearer ${token}` } }),
  //     axios.get(`${config.api.baseUrl}/dictionary/interview_format`, { headers: { Authorization: `Bearer ${token}` } }),
  //   ])
  //   interviewRoundOptions.value = (roundRes.data?.data?.items || []).map(...)
}

// ==================== 表格列 ====================
const handlerColumns = [
  {
    title: '数据来源', key: 'dataSource', width: 130,
    render: (row: any) => h(NSelect, {
      value: row.dataSource,
      options: dataSourceOptions,
      size: 'small',
      'onUpdate:value': (v: any) => { row.dataSource = v; row.field = '' },
    }),
  },
  {
    title: '取值字段', key: 'field', width: 180,
    render: (row: any) => h(NSelect, {
      value: row.field,
      options: fieldOptionsBySource[row.dataSource] || [],
      size: 'small',
      placeholder: '选择字段',
    }),
  },
  {
    title: '处理规则', key: 'strategy', width: 180,
    render: (row: any) => h(NSelect, {
      value: row.strategy,
      options: strategyOptions,
      size: 'small',
    }),
  },
  {
    title: '启用', key: 'enabled', width: 70,
    render: (row: any) => h(NSwitch, {
      value: row.enabled,
      size: 'small',
      'onUpdate:value': (v: boolean) => { row.enabled = v },
    }),
  },
  {
    title: '操作', key: 'op', width: 70,
    render: (row: any) => h(NButton, {
      size: 'small', text: true, type: 'error',
      onClick: () => removeHandlerRule(row),
    }, { default: () => '删除' }),
  },
]

const timeLimitColumns = [
  {
    title: '规则名', key: 'name', width: 160,
    render: (row: any) => h(NInput, {
      value: row.name,
      size: 'small',
      placeholder: '如: 超时 72h 自动转交',
      'onUpdate:value': (v: string) => { row.name = v },
    }),
  },
  {
    title: '执行条件', key: 'condition', width: 160,
    render: (row: any) => h(NSelect, {
      value: row.condition,
      options: timeLimitConditionOptions,
      size: 'small',
    }),
  },
  {
    title: '执行动作', key: 'action', width: 160,
    render: (row: any) => h(NSelect, {
      value: row.action,
      options: timeLimitActionOptions,
      size: 'small',
    }),
  },
  {
    title: '启停', key: 'enabled', width: 70,
    render: (row: any) => h(NSwitch, {
      value: row.enabled,
      size: 'small',
      'onUpdate:value': (v: boolean) => { row.enabled = v },
    }),
  },
  {
    title: '操作', key: 'op', width: 70,
    render: (row: any) => h(NButton, {
      size: 'small', text: true, type: 'error',
      onClick: () => removeTimeLimitRule(row),
    }, { default: () => '删除' }),
  },
]

// ==================== 增删 ====================
function addHandlerRule() {
  form.handlerRules.push({
    _key: `h_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    dataSource: 'FROM_DEMAND',
    field: '',
    strategy: 'NONE',
    enabled: true,
  })
}

function removeHandlerRule(row: any) {
  form.handlerRules = form.handlerRules.filter(r => r._key !== row._key)
}

function addTimeLimitRule() {
  form.timeLimitRules.push({
    _key: `t_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name: '',
    condition: 'STAGE_CONDITION',
    action: 'TRANSFER',
    enabled: true,
  })
}

function removeTimeLimitRule(idx: number) {
  form.timeLimitRules.splice(idx, 1)
}

/**
 * 2026-09-03 自动跳过 block 操作 (原型新增模块)
 * - 开关状态保留在 form.skipEnabled (UI-only)
 * - 规则列表 form.skipRules 同理
 * - 后端暂未实现 skip 字段 → 不写入后端；本块作为 UI 演示存在
 */
function addSkipRule() {
  form.skipRules.push({
    _key: `s_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    condition: '',
    action: '跳过本阶段',
    enabled: true,
  })
}

function removeSkipRule(idx: number) {
  form.skipRules.splice(idx, 1)
}

/**
 * 面试轮次 / 面试形式 多选切换 (原型 option-grid 交互)
 */
function onInterviewToggle(kind: 'rounds' | 'forms', value: string, checked: boolean) {
  const key = kind === 'rounds' ? 'interviewRounds' : 'interviewForms'
  const arr = form[key] as string[]
  const idx = arr.indexOf(value)
  if (checked && idx < 0) arr.push(value)
  if (!checked && idx >= 0) arr.splice(idx, 1)
}

// Plan L #5: 插入时间限制预置规则
function insertPreset(level: 'PRESIDENT' | 'DIRECTOR' | 'OTHER') {
  const presets: Record<string, { days: number; label: string }> = {
    PRESIDENT: { days: 90, label: '总裁级' },
    DIRECTOR: { days: 60, label: '总监级' },
    OTHER: { days: 30, label: '其他级别' },
  }
  const p = presets[level]
  if (!p) return
  // 2026-07-03: 删掉现有 timeLimit 规则 (通常是从 DB load 出来的 t_existing_0,
  //   _key 不匹配 t_preset_* 模式, 会让 handleSubmit 的 timeLimit 推导取不到 hours).
  //   用户点预置按钮 = 「我要换成 X 天的限制」, 用预设行覆盖而不是追加.
  form.timeLimitRules = form.timeLimitRules.filter(r => !r._key?.startsWith('t_existing_'))
  form.timeLimitRules.push({
    _key: `t_preset_${level}_${Date.now()}`,
    name: `${p.label} ${p.days} 天超时自动处理`,
    condition: 'STAGE_CONDITION',
    action: 'TRANSFER',
    enabled: true,
  })
  // timeLimit 字段在提交时按 level 转换
  form.timeLimitHoursByLevel = form.timeLimitHoursByLevel || {}
  form.timeLimitHoursByLevel[level] = p.days * 24
  message.success(`已添加 ${p.label} 预置规则`)
}

// ==================== 监听 open 加载已有规则 ====================
watch(() => props.show, async (v) => {
  if (!v || !props.linkId) return
  loading.value = true
  // Plan L #6: 字典动态加载
  loadDictionaryOptions()
  try {
    // 加载 stage rule
    const rules = await listStageRules({ linkId: props.linkId })
    if (rules?.[0]) {
      const r = rules[0]
      form.autoAdvanceType = r.autoAdvanceType
      form.autoAdvanceTiming = r.autoAdvanceTiming
      form.autoAdvanceDays = r.autoAdvanceDays
      // 处理人多行
      const userIds = r.defaultHandlerUserIds || []
      if (userIds.length > 0) {
        form.handlerRules = userIds.map((uid: string, i: number) => ({
          _key: `h_existing_${i}`,
          dataSource: 'CUSTOM',
          field: 'CUSTOM_HANDLER',
          strategy: r.defaultHandlerType === 'FROM_DEMAND' ? 'IN_ORDER' : r.defaultHandlerType === 'FROM_POSITION' ? 'IN_ORDER' : 'NONE',
          enabled: true,
        }))
      } else if (r.defaultHandlerFields && r.defaultHandlerFields.length > 0) {
        form.handlerRules = r.defaultHandlerFields.map((f: string, i: number) => ({
          _key: `h_existing_${i}`,
          dataSource: r.defaultHandlerType || 'FROM_DEMAND',
          field: f,
          strategy: 'IN_ORDER',
          enabled: true,
        }))
      } else {
        form.handlerRules = []
      }
      // 限时 (timeLimit 字段 + scope)
      if (r.timeLimit) {
        form.timeLimitRules = [{
          _key: 't_existing_0',
          name: `${r.timeLimit}h 自动处理`,
          condition: 'STAGE_CONDITION',
          action: 'TRANSFER',
          enabled: true,
        }]
        // 2026-07-03: 同步把 hours 存进 _EXISTING 桶, 让 handleSubmit 找到并保留原值
        //   (axios 不传 undefined 字段, 不存就意味着 DB 列不变; 但用户改天再改时 form 已经
        //   没 hours 参考了, 容易丢). 这里保留现有 hours, 等用户点预置按钮再覆盖.
        form.timeLimitHoursByLevel = { ...(form.timeLimitHoursByLevel || {}), _EXISTING: r.timeLimit }
      } else {
        form.timeLimitRules = []
      }
      // 面试
      form.interviewRounds = r.interviewRoundIds || []
      // 2026-07-07: 把后端持久化的 interviewFormat (逗号分隔字符串) 拆回数组
      //   写回 form.interviewForms, 否则重新打开已配置的阶段看不到已选形式.
      form.interviewForms = r.interviewFormat
        ? r.interviewFormat.split(',').map((s: string) => s.trim()).filter(Boolean)
        : []
      // 2026-07-07: 回填 inheritPriorConsensus / grabModeEnabled, 否则重打开已配置阶段看不到勾选
      form.inheritPriorConsensus = r.inheritPriorConsensus ?? false
      form.grabModeEnabled = r.isGrabMode ?? false
    } else {
      // reset
      form.autoAdvanceType = 'NONE'
      form.autoAdvanceTiming = 'NONE'
      form.autoAdvanceDays = undefined
      form.handlerRules = []
      form.timeLimitRules = []
      form.interviewRounds = []
      form.interviewForms = []
    }

    // 加载 entry condition
    const conds = await listEntryConditions({ linkId: props.linkId })
    if (conds?.[0]) {
      condForm.matchType = conds[0].matchType
      condForm.conditionType = conds[0].conditionType
      condForm.prompt = conds[0].prompt || ''
      condForm.items = conds[0].items || []
    } else {
      condForm.matchType = 'ALL'
      condForm.conditionType = 'MIXED'
      condForm.prompt = ''
      condForm.items = []
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

// ==================== 提交 ====================
async function handleSubmit() {
  if (!props.linkId) {
    message.error('缺少 linkId')
    return
  }
  // 表达式非法 → 阻断提交（此前只在 blur 提示，提交路径无校验，错误配置会被写库）
  if (hasExprError.value) {
    message.error(`条件表达式校验失败: ${exprValidation.value?.error}`)
    return
  }
  saving.value = true
  try {
      // 同步默认处理人 · 主配置（参照原型交互）→ form.handlerRules[0]
      // 当且仅当用户没有手动添加「高级规则」时，主配置就是唯一规则；
      // 已添加多条时，主配置作为隐藏的第一条继续生效（向后兼容既有 StageRule）。
      const primaryAsRule = {
        _key: form.handlerRules[0]?._key || 'primary',
        dataSource: primaryHandler.dataSource === 'NONE' ? 'CUSTOM' : primaryHandler.dataSource,
        field: primaryHandler.field || '',
        strategy: primaryHandler.strategy,
        enabled: primaryHandler.dataSource !== 'NONE',
      }
      if (form.handlerRules.length === 0) {
        form.handlerRules = [primaryAsRule]
      } else {
        form.handlerRules[0] = primaryAsRule
      }
      // 聚合: 默认处理人多行 → flat fields
      const handlerFields: string[] = []
      const handlerUserIds: string[] = []
      let handlerType: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM' = 'CUSTOM'
      for (const r of form.handlerRules.filter(r => r.enabled)) {
        if (r.dataSource === 'CUSTOM') {
          handlerUserIds.push(r.field) // 简化: 这里实际应是 user id
        } else {
          handlerFields.push(r.field)
          handlerType = r.dataSource
        }
      }
      // 2026-07-03: timeLimit 之前写死 72 (忽略用户在「插入预置」按钮选的 90/60/30 天).
      //   insertPreset() 把 days * 24 存进 form.timeLimitHoursByLevel[level],
      //   submit 时按「首个有 enabled 规则的级别」取出 hours, 没规则时返 undefined.
      const enabledTimeLimitRule = form.timeLimitRules.find(r => r.enabled)
      let timeLimitHours: number | undefined = undefined
      if (enabledTimeLimitRule && form.timeLimitHoursByLevel) {
        // 找该 rule 对应的 level key (rule._key 形如 t_preset_PRESIDENT_<ts>)
        const match = enabledTimeLimitRule._key.match(/^t_preset_(\w+)_\d+$/)
        if (match && form.timeLimitHoursByLevel[match[1]] != null) {
          timeLimitHours = form.timeLimitHoursByLevel[match[1]]
        } else {
          // 兜底: 取任意 level 的 hours
          const firstKey = Object.keys(form.timeLimitHoursByLevel)[0]
          if (firstKey) timeLimitHours = form.timeLimitHoursByLevel[firstKey]
        }
      }
      await upsertStageRule(props.linkId, {
        autoAdvanceType: form.autoAdvanceType,
        autoAdvanceTiming: form.autoAdvanceTiming,
        autoAdvanceDays: form.autoAdvanceDays,
        defaultHandlerType: handlerType,
        defaultHandlerFields: handlerFields,
        defaultHandlerUserIds: handlerUserIds,
        timeLimit: timeLimitHours,
        timeLimitScope: 'NEW_ONLY',
        interviewRoundIds: form.interviewRounds,
        // 2026-07-03: 之前这两个开关只读不写, BE 上对应字段:
        //   inheritPriorConsensus → inherit_prior_consensus (BooleanField)
        //   grabModeEnabled       → is_grab_mode (BooleanField)
        inheritPriorConsensus: form.inheritPriorConsensus,
        isGrabMode: form.grabModeEnabled,
        // 2026-07-03: BE StageRuleSerializer.validate() 在 is_grab_mode=true 时校验
        //   grab_threshold ≥ 5 (apps/process/serializers.py:186-191). DRF ModelSerializer
        //   PUT 走 full validation, 不传 grab_threshold → null → 触发校验失败.
        //   这里固定传 30 (model default), 跟 BE 默认一致, 用户没改就不用关心.
        grabThreshold: 30,
        // 2026-07-03: form.interviewForms (复选) 是数组, BE StageRule.interview_format 是 CharField,
        //   把所选形式 join 成 "VIDEO,ONSITE" 形式入字符串字段. BE 没有 JSON 字段对应.
        interviewFormat: form.interviewForms.join(','),
      })
    // 2026-08-31 修复：原逻辑用 activeTab === 'condition' 分支判定，但本弹窗是扁平表单、没有
    //   tab 切换 UI → activeTab 恒为 'auto' → 进入条件**从未被保存**，用户配置的进入条件全丢。
    //   改为「只要用户实际填写了任一字段就提交」，全空则不创建空记录（避免脏数据）。
    const hasConditionInput =
      condForm.prompt.trim() !== '' ||
      condForm.expression.trim() !== '' ||
      (condForm.items?.length || 0) > 0
    if (hasConditionInput) {
      await upsertEntryCondition(props.linkId, {
        matchType: condForm.matchType,
        conditionType: condForm.conditionType,
        prompt: condForm.prompt,
        items: condForm.items,
      })
    }
    message.success('已保存')
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
/* ==================== Modal 容器 ==================== */
/* 内容外层：n-spin 的加载态会临时清空表单，给最小高度避免面板塌成一条缝 */
.rule-config-body {
  min-height: 280px;
}
/* 统一间距：用 gap 替代各 section 的 margin-bottom，行距更一致；padding 交给 scroll 容器 */
.rule-config-flat {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: 0;
}

/* ==================== HERO HEADER ==================== */
.hero {
  background: linear-gradient(135deg, var(--glass-bg-input) 0%, var(--c-info-soft) 100%); /* v2.8 T2.8.3: 浅色硬编码渐变 → tokens */
  margin: -20px -20px 20px -20px;
  padding: 20px var(--space-6);
  border-bottom: 1px solid var(--g1);
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}
.hero__icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--g1);
  flex-shrink: 0;
  box-shadow: 0 2px 6px var(--c-info-soft);
}
.hero__main {
  flex: 1;
  min-width: 0;
}
.hero__title {
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--n-850);
  line-height: 1.4;
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.hero__stage-chip {
  font-size: var(--fs-13);
  font-weight: 500;
  color: var(--n-580);
  letter-spacing: 0;
}
.hero__subtitle {
  font-size: var(--fs-13);
  color: var(--n-440);
  margin-top: var(--space-1);
  line-height: 1.5;
}
/* 即时生效小标识（参照原型）；颜色走 --brand token，无硬编码 */
.hero__tip {
  align-self: center;
  font-size: var(--fs-12);
  color: var(--brand);
  background: var(--brand-a12);
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  flex-shrink: 0;
  margin-right: 36px; /* 让出 close 按钮位置 */
}
.hero__close {
  position: absolute;
  top: 16px;
  right: 20px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--n-440);
  font-size: var(--fs-18);
  padding: var(--space-1);
  line-height: 1;
  border-radius: 4px;
  transition: background 0.15s, color 0.15s;
}
.hero__close:hover {
  background: var(--overlay-scrim-weak);
  color: var(--n-850);
}

/* ==================== Section Card ==================== */
/* 2026-09-03 视觉整改 v3：完全按原型 HTML 的 .config-card 视觉实现
   - config-card：浅灰底（--bg-subtle → --g1），圆角 12px，1px border，padding 14-16px
   - card-title：14px 600 + 蓝色 icon 前缀（--brand），无下划线
   - 内部 flow-block：白底，圆角 10px，1px border（白底 block 在浅灰 card 内浮起） */
.config-card {
  background: var(--g1);
  border: 1px solid var(--g2);
  border-radius: var(--radius-md); /* 16px → 与原型 12px 接近但保留项目 token */
  padding: 14px var(--space-4) var(--space-4);
  margin-bottom: 0;
}
.card-title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  letter-spacing: -0.01em;
}
.card-title :deep(.n-icon) {
  color: var(--brand);
  font-size: 14px;
  flex-shrink: 0;
}
.title-desc {
  font-weight: 400;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin-left: 2px;
}

/* ==================== Flow Block (白底块，在 config-card 内浮起) ==================== */
.flow-block {
  background: var(--surface); /* 原型 white */
  border-radius: var(--radius-sm); /* 8px 接近原型 10px */
  padding: 10px 14px;
  margin-bottom: 10px;
  border: 1px solid var(--g2);
  transition: box-shadow var(--duration-fast) var(--ease-out);
}
.flow-block:last-child {
  margin-bottom: 0;
}
.flow-block:hover {
  box-shadow: var(--shadow-xs);
}
.block-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.block-header :deep(.n-icon) {
  color: var(--brand);
  font-size: 12px;
  flex-shrink: 0;
}
.block-desc {
  font-weight: 400;
  font-size: 11.5px;
  color: var(--ink-soft);
  margin-left: 2px;
  line-height: 1.4;
}
.block-header--secondary {
  font-size: 13.5px;
  font-weight: 650;
}
.block-header--split {
  justify-content: space-between;
  align-items: center;
}
.block-header__main {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

/* ==================== Option Grid (复选/单选内联) ==================== */
.option-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  padding: 2px 0;
}
.opt-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-13);
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  padding: 2px 0;
  transition: color var(--duration-fast) var(--ease-out);
}
.opt-item:hover {
  color: var(--brand);
}
.opt-item :deep(.n-checkbox),
.opt-item :deep(.n-radio) {
  margin-right: 2px;
}
.opt-item :deep(.n-checkbox .n-checkbox__label),
.opt-item :deep(.n-radio .n-radio__label) {
  font-size: var(--fs-13);
  padding-left: 0;
}

/* ==================== Flow Condition Row (自动流转 / 默认处理人 字段并排) ==================== */
.flow-condition-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.flow-condition-row + .flow-condition-row {
  margin-top: 10px;
}
.flow-condition-row--3 {
  /* 3 列默认处理人内联 */
}
.flow-field {
  flex: 1;
  min-width: 0;
}
.flow-field .field-label {
  display: block;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  margin-bottom: 4px;
  font-weight: 500;
  line-height: 1.3;
}
.required-mark {
  color: var(--c-error);
  margin-left: 2px;
}

/* ==================== Switch Pill (开关，参照原型) ==================== */
.switch-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  transition: color var(--duration-fast) var(--ease-out);
  flex-shrink: 0;
}
.switch-pill--on {
  color: var(--brand);
}
.switch-pill__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.switch-pill__track {
  position: relative;
  width: 40px;
  height: 22px;
  background: var(--g6);
  border-radius: var(--radius-pill);
  transition: background var(--duration-base) var(--ease-out);
  display: inline-block;
  flex-shrink: 0;
}
.switch-pill__dot {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  background: var(--surface);
  border-radius: 50%;
  box-shadow: var(--shadow-xs);
  transition: transform var(--duration-base) var(--ease-out);
}
.switch-pill--on .switch-pill__track {
  background: var(--brand);
}
.switch-pill--on .switch-pill__dot {
  transform: translateX(18px);
}
.switch-pill__label {
  font-weight: 500;
  min-width: 28px;
}

/* ==================== Rule Content Reveal ==================== */
.rule-content {
  transition: opacity var(--duration-base) var(--ease-out),
              max-height var(--duration-base) var(--ease-out);
  overflow: hidden;
  max-height: 2000px;
  opacity: 1;
}
.rule-content--hidden {
  max-height: 0;
  opacity: 0;
  pointer-events: none;
  margin: 0 !important;
}

/* ==================== Rule Table (原 HTML 原生 table) ==================== */
.rule-table-wrap {
  overflow-x: auto;
  margin-top: 6px;
  border-radius: var(--radius-sm);
  scrollbar-width: thin;
}
.rule-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--fs-12);
  background: var(--surface);
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--g2);
}
.rule-table :deep(.n-data-table-th) {
  background: var(--g1);
  font-weight: 500;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  border-bottom: 1px solid var(--g2);
}
.rule-table :deep(.n-data-table-td) {
  font-size: var(--fs-12) !important;
  color: var(--ink);
  border-bottom: 1px solid var(--g2);
}
.rule-table__empty {
  text-align: center;
  color: var(--ink-faint);
  padding: 14px !important;
  font-style: italic;
}
.action-btns {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.action-btns a {
  color: var(--brand);
  text-decoration: none;
  cursor: pointer;
  font-size: var(--fs-12);
  transition: color var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.action-btns a:hover {
  color: var(--brand-hover);
  text-decoration: underline;
}
.action-btns a.danger {
  color: var(--c-error);
}
.action-btns a.danger:hover {
  color: var(--c-error-deep);
}

/* ==================== Actions Row (添加规则 + 预置 按钮组) ==================== */
.actions-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 8px;
}

/* ==================== Outline Primary Button ==================== */
.btn-outline-primary {
  background: transparent;
  border: 1px dashed var(--brand);
  color: var(--brand);
  padding: 0 14px;
  height: 30px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-weight: 500;
}
.btn-outline-primary:hover {
  background: var(--brand-a12);
  border-style: solid;
}

/* ==================== Field Hint (进入条件 block 下方的提示) ==================== */
.field-hint {
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.5;
}
.field-error-hint {
  font-size: var(--fs-12);
  color: var(--c-error);
  line-height: 1.5;
}

/* ==================== 分区锚点导航（sticky 吸顶） ==================== */
/* 配置项较多时（6 个分区）提供快速定位；用负边距吃掉内容区左右 padding 让底纹铺满，
   sticky 钉在内容滚动容器顶部，随内容滚动始终可见。 */
.section-nav {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0 -20px var(--space-4) -20px;
  padding: var(--space-2) 20px;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--glass-blur-card));
  -webkit-backdrop-filter: blur(var(--glass-blur-card));
  border-bottom: 1px solid var(--g2);
}
.section-nav__item {
  appearance: none;
  border: 1px solid var(--g2);
  background: var(--glass-bg-input);
  color: var(--n-580);
  font-size: var(--fs-12);
  line-height: 1;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: background 0.15s var(--ease-out), color 0.15s var(--ease-out), border-color 0.15s var(--ease-out);
}
.section-nav__item:hover {
  border-color: var(--glass-border-strong);
  color: var(--ink);
}
.section-nav__item--active {
  background: var(--brand);
  border-color: var(--brand);
  color: var(--n-100);
}

/* ==================== Footer ==================== */
/* footer 在 #footer 插槽 → 渲染为 .n-card__footer，是 .n-card 的 flex 兄弟节点，
   永远在滚动容器之外、天然钉在底部，无需 sticky。 */
.modal-footer {
  background: var(--glass-bg-input); /* v2.8 T2.8.3: 浅灰 → var(--glass-bg-input) */
  border-top: 1px solid var(--g1);
  padding: var(--space-3) 20px;
  margin: var(--space-4) -20px -20px -20px;
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  z-index: 10;
}

/* ==================== Form 内嵌控件：禁用默认的 label 灰底 ==================== */
.field-value :deep(.n-checkbox) {
  font-size: var(--fs-13);
}
.field-value :deep(.n-radio) {
  font-size: var(--fs-13);
}
.field-value :deep(.n-base-selection),
.field-value :deep(.n-input) {
  width: 100%;
}

/* ==================== 响应式 ==================== */
@media (max-width: 900px) {
  /* 中屏：3 字段内联降为 2 列 */
}
@media (max-width: 767px) {
  .section-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .section-nav::-webkit-scrollbar { display: none; }
  .section-nav__item {
    flex: 0 0 auto;
  }
  .flow-condition-row {
    flex-direction: column;
    gap: 10px;
  }
  .flow-condition-row + .flow-condition-row {
    margin-top: 10px;
  }
}
@media (max-width: 600px) {
  .hero {
    padding: var(--space-4);
    margin: -16px -16px var(--space-3) -16px;
  }
  .hero__icon {
    width: 36px;
    height: 36px;
  }
  .hero__title {
    font-size: var(--fs-16);
  }
  .hero__tip {
    margin-right: 32px;
    font-size: var(--fs-12);
  }
  .config-card {
    padding: 10px 10px 12px;
  }
  .actions-row {
    flex-direction: column;
    align-items: stretch;
  }
  .block-header--split {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
}
</style>

<style>
/* Unscoped global style: hide n-card-header rendered by preset="card"
   to avoid duplicate close button + wasted vertical space.
   Cannot use :deep() in scoped style because n-card teleports
   the header outside the parent's data-v boundary. */
.stage-rule-config-modal .n-card-header {
  display: none; /* v2.9: 移除 !important；.stage-rule-config-modal .n-card-header 特异性(0,2,0) 已压 Naive 默认 header */
}
/* 2026-08-30 滚动修复：preset=card 的 .n-card 经 teleport 挂到 body，scoped :deep 命中不到。
   与 ProcessDetailModal 同款方案：card 走 flex 列 + 90vh 上限，content 用 flex:1 + min-height:0
   拿到剩余高度并滚动；hero 在 content 内随内容一起滚动，footer 由 Naive 默认 flex-shrink:0 钉底。
   ⚠️ 类名铁律：Card 内容区是 .n-card-content（单横线 block 类，见 glass.css「弹窗统一」段注释），
   不是 .n-card__content —— 旧写法选择器永不匹配导致整段修复无效。 */
.stage-rule-config-modal {
  display: flex;
  flex-direction: column;
  /* 全局 .n-modal .n-card 已统一兜底，这里仅补齐类级强化（不重复定义可删，保留以显式表达意图） */
}
.stage-rule-config-modal .n-card-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>

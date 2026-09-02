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
            <div class="hero__title">阶段规则配置</div>
            <div class="hero__subtitle">
              为阶段「{{ stage?.name || '未命名' }}」配置规则
            </div>
          </div>
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
          <!-- Section 1: 自动处理规则 (总开关) -->
          <div class="section-card" data-section="auto">
            <div class="section-card__title">自动处理规则</div>
            <div class="section-card__hint">
              流程自动化的总开关 (启用 = 满足下阶段进入条件时自动流转到下个阶段)
            </div>
            <div class="field-row">
              <span class="field-label">启用自动处理</span>
              <span class="field-value">
                <n-checkbox v-model:checked="form.autoAdvanceEnabled">满足下阶段进入条件时, 自动流转到下阶段</n-checkbox>
              </span>
            </div>
            <div class="field-row">
              <span class="field-label">兜选机制 (N+2 推荐)</span>
              <span class="field-value">
                <n-checkbox v-model:checked="form.grabModeEnabled">N+2 推荐兜选</n-checkbox>
              </span>
            </div>
            <div class="field-row field-row--last">
              <span class="field-label">引用前序双 A 的一致意见</span>
              <span class="field-value">
                <n-checkbox v-model:checked="form.inheritPriorConsensus">继承前序流程双 A 的一致意见</n-checkbox>
              </span>
            </div>
          </div>

          <!-- Section 2: 自动化流转条件 -->
          <div class="section-card" data-section="flow">
            <div class="section-card__title">自动化流转条件</div>
            <div class="section-card__hint">当前阶段的自动化填充规则</div>
            <div class="field-row">
              <span class="field-label">自动化流转条件</span>
              <span class="field-value">
                <n-select v-model:value="form.autoAdvanceType" :options="autoAdvanceOptions" size="small" />
              </span>
            </div>
            <div v-if="form.autoAdvanceType !== 'NONE'" class="field-row">
              <span class="field-label">执行时机</span>
              <span class="field-value">
                <n-radio-group v-model:value="form.autoAdvanceTiming">
                  <n-space>
                    <n-radio value="NONE">不执行</n-radio>
                    <n-radio value="IMMEDIATE">立即执行</n-radio>
                    <n-radio value="DELAYED">延迟</n-radio>
                  </n-space>
                </n-radio-group>
              </span>
            </div>
            <div v-if="form.autoAdvanceTiming === 'DELAYED'" class="field-row field-row--last">
              <span class="field-label">延迟天数 (1-15 工作日)</span>
              <span class="field-value">
                <n-input-number v-model:value="form.autoAdvanceDays" :min="1" :max="15" size="small" />
              </span>
            </div>
          </div>

          <!-- Section 3: 默认处理人 -->
          <div class="section-card" data-section="handler">
            <div class="section-card__title">默认处理人</div>
            <div class="section-card__hint">进入本阶段时自动为默认处理人添加待办任务</div>
            <n-data-table
              :columns="handlerColumns"
              :data="form.handlerRules"
              :row-key="(r: any) => r._key"
              size="small"
              :pagination="false"
              class="rule-table"
            />
            <div class="section-card__actions">
              <n-button size="small" type="primary" dashed @click="addHandlerRule">
                + 添加处理人规则
              </n-button>
            </div>
          </div>

          <!-- Section 4: 阶段限时 -->
          <div class="section-card" data-section="timelimit">
            <div class="section-card__title">阶段限时</div>
            <div class="section-card__hint">
              限制阶段总时长, 超时自动归档候选人到公共人库, 选择对全部候选人生效时, 会在原有剩余时间上增加锁定时间
            </div>
            <div class="field-row">
              <span class="field-label">是否开启</span>
              <span class="field-value">
                <n-switch v-model:value="form.timeLimitEnabled" />
              </span>
            </div>
            <template v-if="form.timeLimitEnabled">
              <n-data-table
                :columns="timeLimitColumns"
                :data="form.timeLimitRules"
                :row-key="(r: any) => r._key"
                size="small"
                :pagination="false"
                class="rule-table"
              />
              <div class="section-card__actions">
                <n-button size="small" type="primary" dashed @click="addTimeLimitRule">
                  + 添加规则
                </n-button>
                <n-divider vertical />
                <n-text depth="3" style="font-size: 12px">插入预置:</n-text>
                <n-button size="small" @click="insertPreset('PRESIDENT')">总裁级 (90 天)</n-button>
                <n-button size="small" @click="insertPreset('DIRECTOR')">总监级 (60 天)</n-button>
                <n-button size="small" @click="insertPreset('OTHER')">其他级别 (30 天)</n-button>
              </div>
            </template>
          </div>

          <!-- Section 5: 面试轮次 + 形式 (仅 INTERVIEW/INVITATION 阶段) -->
          <div v-if="isInterviewType" class="section-card" data-section="interview">
            <div class="section-card__title">面试轮次 + 形式</div>
            <div class="field-row">
              <span class="field-label">面试轮次 (可多选)</span>
              <span class="field-value">
                <n-checkbox-group v-model:value="form.interviewRounds">
                  <n-space>
                    <n-checkbox
                      v-for="opt in interviewRoundOptions"
                      :key="opt.value"
                      :value="opt.value"
                    >{{ opt.label }}</n-checkbox>
                  </n-space>
                </n-checkbox-group>
              </span>
            </div>
            <div class="field-row field-row--last">
              <span class="field-label">面试形式 (可多选)</span>
              <span class="field-value">
                <n-checkbox-group v-model:value="form.interviewForms">
                  <n-space>
                    <n-checkbox
                      v-for="opt in interviewFormOptions"
                      :key="opt.value"
                      :value="opt.value"
                    >{{ opt.label }}</n-checkbox>
                  </n-space>
                </n-checkbox-group>
              </span>
            </div>
          </div>

          <!-- Section 6: 进入条件 -->
          <div class="section-card" data-section="condition">
            <div class="section-card__title">进入条件</div>
            <div class="section-card__hint">
              候选人进入此阶段需满足的判定条件 (Stage Rule 的 EntryCondition) — 对配置后进入阶段的简历立即生效
            </div>
            <div class="field-row">
              <span class="field-label">判定方式</span>
              <span class="field-value">
                <n-radio-group v-model:value="condForm.matchType">
                  <n-space>
                    <n-radio value="ALL">全部满足 (AND)</n-radio>
                    <n-radio value="ANY">任意满足 (OR)</n-radio>
                  </n-space>
                </n-radio-group>
              </span>
            </div>
            <div
              class="field-row"
              :class="exprValidation && !exprValidation.valid ? 'field-row--error' : ''"
            >
              <span class="field-label">条件表达式 (可选)</span>
              <span class="field-value">
                <n-input
                  v-model:value="condForm.expression"
                  placeholder="如: (1 AND 2) OR (3 AND 4)"
                  :status="exprValidation && !exprValidation.valid ? 'error' : undefined"
                  size="small"
                  @blur="onExprBlur"
                />
                <div v-if="exprValidation && !exprValidation.valid" class="field-error-hint">
                  {{ exprValidation.error }}
                </div>
                <div v-else class="field-hint">留空则用上面条件树自动生成</div>
              </span>
            </div>
            <div class="field-row field-row--last">
              <span class="field-label">未满足条件时提示内容</span>
              <span class="field-value">
                <n-input
                  v-model:value="condForm.prompt"
                  type="textarea"
                  :rows="3"
                  placeholder="如: 请先完成 HRBP 评估"
                  size="small"
                />
                <div class="field-hint">选填。填写后会在候选人未满足进入条件时展示该提示。</div>
              </span>
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
import { SettingsOutline, CloseOutline } from '@vicons/ionicons5'

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
  grabModeEnabled: false,            // N+2 推荐兜选
  inheritPriorConsensus: false,      // 引用前序双 A 的一致意见
  timeLimitEnabled: false,
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
  // 阶段限时 (多行)
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
  { label: '满足下阶段进入条件时', value: 'MEET_NEXT' },
  { label: '无视下阶段进入条件', value: 'IGNORE_NEXT' },
  { label: '满足下阶段条件或 N+2 推荐', value: 'MEET_NEXT_OR_N2' },
  { label: 'N+1 全部通过', value: 'N1_ALL_PASS' },
]

const dataSourceOptions = [
  { label: '需求中', value: 'FROM_DEMAND' },
  { label: '职位中', value: 'FROM_POSITION' },
  { label: '默认处理人', value: 'CUSTOM' },
]

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

function removeTimeLimitRule(row: any) {
  form.timeLimitRules = form.timeLimitRules.filter(r => r._key !== row._key)
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
}
.hero__subtitle {
  font-size: var(--fs-13);
  color: var(--n-440);
  margin-top: var(--space-1);
  line-height: 1.5;
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
.section-card {
  background: var(--glass-bg-input); /* v2.8 T2.8.3: 浅灰 → var(--glass-bg-input) */
  border: 1px solid var(--g1);
  border-radius: 8px;
  padding: var(--space-4) 20px;
  margin-bottom: 0;            /* 间距统一交给 .rule-config-flat 的 gap */
  scroll-margin-top: 52px;     /* 锚点导航 sticky 吸顶时不遮挡分区标题 */
  position: relative;
}
.section-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 4px;
  background: var(--brand);
  border-radius: 0 2px 2px 0;
}
.section-card__title {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--n-850);
  margin: 0 0 var(--space-3) 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--g2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.section-card__title::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: var(--brand);
  border-radius: 2px;
}
.section-card__hint {
  font-size: var(--fs-12);
  color: var(--n-440);
  line-height: 1.6;
  margin: -4px 0 var(--space-3) 0;
  padding: var(--space-2) var(--space-3);
  background: var(--g1);
  border-radius: 4px;
  border-left: 2px solid var(--g6);
}
.section-card__actions {
  margin-top: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* ==================== Field Row ==================== */
.field-row {
  display: flex;
  align-items: center;
  min-height: 36px;
  padding: var(--space-1) 0;
  border-bottom: 1px dashed var(--g2);
}
.field-row:last-child {
  border-bottom: none;
}
.field-row--error {
  background: var(--g1);
  margin: 0 -8px;
  padding: var(--space-1) var(--space-2);
  border-radius: 4px;
}
.field-label {
  flex: 0 0 110px;
  text-align: right;
  padding-right: var(--space-4);
  font-size: var(--fs-13);
  color: var(--n-580);
  font-weight: 500;
  line-height: 1.5;
}
.field-label--required::after {
  content: ' *';
  color: var(--c-error);
}
.field-value {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.field-hint {
  font-size: var(--fs-12);
  color: var(--n-440);
  line-height: 1.5;
}
.field-error-hint {
  font-size: var(--fs-12);
  color: var(--c-error);
  line-height: 1.5;
}

/* ==================== Data Table ==================== */
.rule-table {
  margin: var(--space-1) 0 0 0;
}
.rule-table :deep(.n-data-table-th) {
  background: var(--glass-bg-input);
  font-weight: 600;
  font-size: var(--fs-12);
  color: var(--ink);
}
.rule-table :deep(.n-data-table-td) {
  font-weight: 600;
  font-size: var(--fs-12);
  color: var(--ink);
}
.rule-table :deep(.n-data-table-th__title) {
  font-weight: 600;
}
.rule-table :deep(.n-data-table-td) {
  font-size: var(--fs-12) !important;
}
.rule-table :deep(.n-data-table-td--ellipsis) {
  padding: 6px 10px !important;
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
/* 中屏：标签列收窄，避免大屏 110px 在 768px 左右显得空旷 */
@media (max-width: 900px) {
  .field-label {
    flex-basis: 96px;
  }
}
@media (max-width: 767px) {
  /* 窄屏：锚点导航横向滚动，避免换行挤占内容高度 */
  .section-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .section-nav::-webkit-scrollbar { display: none; }
  .section-nav__item {
    flex: 0 0 auto;
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
  .field-row {
    flex-direction: column;
    align-items: flex-start;
    padding: var(--space-2) 0;
  }
  .field-label {
    flex: none;
    text-align: left;
    padding: 0 0 var(--space-1) 0;
    width: 100%;
  }
  .field-value {
    width: 100%;
  }
  .section-card {
    padding: var(--space-3) 14px;
  }
  .section-card__actions {
    flex-direction: column;
    align-items: stretch;
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

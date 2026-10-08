<script lang="ts">
// 设计稿：2026-09-03 stitch design（Production 四要素 + 五能 + 面试结论）
// 数据契约对齐后端 InterviewEvaluation：
//   scores(JSON) / overall_score / recommendation / comment
// 新增字段（落库在 comment 或自定义 meta_json，需后端扩展）：
//   - 四维符合性评价：每维 compliance 字段（PASS/PARTIAL/FAIL）+ reason 文字依据
//   - 五能价值观评分：5 维 1-5 评分（与历史 demo 评分语义一致）
//   - 面试结论：suggestedLevel (职级 select) / suggestedSalary (薪资 input) / finalResult (3 档)
//   - 推荐结果最终以 finalResult 为主，写入 recommendation

export type ComplianceLevel = 'PASS' | 'PARTIAL' | 'FAIL'
export type FinalResult = 'PASS' | 'FAIL' | 'PENDING'

/** 四维符合性维度（来自设计稿，固定顺序） */
export const FOUR_DIMS: ReadonlyArray<{ key: string; name: string }> = [
  { key: 'laodongzhe',    name: '劳动者' },
  { key: 'laodonggongju', name: '劳动工具' },
  { key: 'laodongziliao', name: '劳动资料' },
  { key: 'laodongduixiang', name: '劳动对象' },
]

/** 五能价值观维度（来自设计稿，固定顺序） */
export const FIVE_VALUES: ReadonlyArray<{ key: string; name: string }> = [
  { key: 'zunzhongshishi', name: '尊重事实' },
  { key: 'ziwopipan',      name: '自我批判' },
  { key: 'jijizhudong',    name: '积极主动' },
  { key: 'renzhenfuke',    name: '认真负责' },
  { key: 'jiankufendou',   name: '艰苦奋斗' },
]

export interface ComplianceItem {
  compliance: ComplianceLevel | null
  reason: string
}

export interface Candidate {
  name: string
  position: string
  level: string
  interviewDate: string
}

export interface Evaluation {
  candidate: Candidate
  /** 四维符合性评价（劳动者/工具/资料/对象），key = FOUR_DIMS.key */
  compliances: Record<string, ComplianceItem>
  /** 五能价值观评分（5 维），key = FIVE_VALUES.key，value = 1-5 */
  values: Record<string, number>
  /** 建议职级 */
  suggestedLevel: string
  /** 建议薪资（月薪，文本由用户自由填写） */
  suggestedSalary: string
  /** 最终结果 */
  finalResult: FinalResult
  /** 综合评语 */
  comment: string
}

export interface SubmitPayload {
  compliances: Record<string, ComplianceItem>
  values: Record<string, number>
  suggestedLevel: string
  suggestedSalary: string
  finalResult: FinalResult
  comment: string
}
</script>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
/**
 * 面试评价表单（设计稿 · 卡片式 · v2 重构）
 * -------------------------------------------------------------
 * 三态：
 *   - mode="edit"  填写评价（默认，可提交）
 *   - mode="view"  只读查看（所有 input disabled，提交按钮替换为"关闭"）
 *
 * 数据流：
 *   props.evaluation 传入回显（用于 view 态/草稿恢复）
 *   不传时使用内置 DEMO 演示（生产环境应强制 props.evaluation）
 *
 * 提交校验：
 *   - 五能 5 维 必填 1-5 分（任一缺失拦截）
 *   - 四维任一选"不符合"时，文字依据必填
 *   - 最终结果（通过/不通过/待定）必填
 *   - 综合评语 必填
 *   - 不强制要求"建议职级 / 建议薪资"（设计稿未标红）
 */
import { ref, computed, watch } from 'vue'
import { NModal, NButton, NInput, NSelect, NRadioGroup, NRadio, NSpace, useMessage } from 'naive-ui'
const { t } = useI18n()

const props = withDefaults(defineProps<{
  show?: boolean
  mode?: 'view' | 'edit'
  evaluation?: Evaluation
}>(), {
  show: false,
  mode: 'edit',
  evaluation: undefined,
})

const emit = defineEmits<{
  'update:show': [boolean]
  submit: [payload: SubmitPayload]
}>()

const message = useMessage()

/* ---------- 内置 demo（生产应传 props.evaluation） ---------- */
const DEMO: Evaluation = {
  candidate: {
    name: '杨前',
    position: '客服产品专家 · 联合面试',
    level: '经理 / 四级',
    interviewDate: '2026-08-31',
  },
  compliances: {
    laodongzhe:      { compliance: null, reason: '' },
    laodonggongju:   { compliance: 'FAIL', reason: '' }, // demo：故意触发"不符合"必填
    laodongziliao:   { compliance: null, reason: '' },
    laodongduixiang: { compliance: null, reason: '' },
  },
  values: {
    zunzhongshishi: 0,
    ziwopipan:      0,
    jijizhudong:    0,
    renzhenfuke:    0,
    jiankufendou:   0,
  },
  suggestedLevel: '经理',
  suggestedSalary: '30K-35K',
  finalResult: 'PASS',
  comment: '',
}

/* ---------- 选项常量 ---------- */
const COMPLIANCE_OPTIONS: ReadonlyArray<{ value: ComplianceLevel; label: string }> = [
  { value: 'PASS',    label: '符合' },
  { value: 'PARTIAL', label: '部分符合' },
  { value: 'FAIL',    label: '不符合' },
]

const LEVEL_OPTIONS = [
  { value: '专员',     label: '专员' },
  { value: '主管',     label: '主管' },
  { value: '经理',     label: '经理' },
  { value: '总监',     label: '总监' },
  { value: '高级总监', label: '高级总监' },
  { value: '副总裁',   label: '副总裁' },
]

/* ---------- 状态 ---------- */
const source = computed(() => props.evaluation ?? DEMO)
const editing = ref(props.mode === 'edit')

const compliances = ref<Record<string, ComplianceItem>>({})
const values = ref<Record<string, number>>({})
const suggestedLevel = ref<string>('经理')
const suggestedSalary = ref<string>('')
const finalResult = ref<FinalResult>('PASS')
const comment = ref<string>('')

function loadDraft() {
  compliances.value = JSON.parse(JSON.stringify(source.value.compliances))
  values.value = { ...source.value.values }
  suggestedLevel.value = source.value.suggestedLevel
  suggestedSalary.value = source.value.suggestedSalary
  finalResult.value = source.value.finalResult
  comment.value = source.value.comment
}
watch(() => [props.show, props.mode], () => {
  if (props.show) {
    editing.value = props.mode === 'edit'
    if (editing.value) loadDraft()
  }
}, { immediate: true })

/* ---------- 校验 ---------- */
const allValuesFilled = computed(() => {
  for (const v of FIVE_VALUES) {
    const score = values.value[v.key] ?? 0
    if (score < 1) return false
  }
  return true
})
const allCompliancesFilled = computed(() => {
  for (const d of FOUR_DIMS) {
    if (!compliances.value[d.key]?.compliance) return false
  }
  return true
})
const failedComplianceReasonsFilled = computed(() => {
  for (const d of FOUR_DIMS) {
    const item = compliances.value[d.key]
    if (item?.compliance === 'FAIL' && !item.reason?.trim()) return false
  }
  return true
})
const commentFilled = computed(() => !!comment.value?.trim())
const canSubmit = computed(() =>
  allValuesFilled.value
  && allCompliancesFilled.value
  && failedComplianceReasonsFilled.value
  && commentFilled.value,
)

const submitHint = computed(() => {
  if (!allCompliancesFilled.value) return '请完成生产力四要素符合性评价'
  if (!failedComplianceReasonsFilled.value) return '选择"不符合"时评价依据必填'
  if (!allValuesFilled.value) return '请完成五能价值观 1-5 分评分'
  if (!commentFilled.value) return '请填写综合评语'
  return ''
})

/* ---------- 交互 ---------- */
function setCompliance(dimKey: string, level: ComplianceLevel) {
  if (!editing.value) return
  const cur = compliances.value[dimKey]?.compliance
  compliances.value[dimKey] = {
    compliance: cur === level ? null : level,
    reason: compliances.value[dimKey]?.reason ?? '',
  }
}
function setValue(dimKey: string, score: number) {
  if (!editing.value) return
  values.value[dimKey] = score
}

function handleSubmit() {
  if (!canSubmit.value) {
    message.warning(submitHint.value || '请完整填写表单')
    return
  }
  emit('submit', {
    compliances: JSON.parse(JSON.stringify(compliances.value)),
    values: { ...values.value },
    suggestedLevel: suggestedLevel.value,
    suggestedSalary: suggestedSalary.value,
    finalResult: finalResult.value,
    comment: comment.value,
  })
  message.success('评价已提交（设计态·未落库）')
  emit('update:show', false)
}
function close() { emit('update:show', false) }

/* ---------- 计算合计（仅展示用） ---------- */
const avgValueScore = computed(() => {
  const scores = Object.values(values.value).filter(v => v > 0)
  if (!scores.length) return 0
  return Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 10) / 10
})
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :bordered="false"
    :mask-closable="false"
    style="width: 880px; max-width: 96vw;"
    :title="editing ? t('pages.interview.InterviewEvaluationModal.s22') : t('pages.interview.InterviewEvaluationModal.s23')"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="ats-eval">
      <!-- ===== Header（岗位 / 层级 / 面试日期） ===== -->
      <header class="ats-header">
        <h1 class="ats-header__title">{{ editing ? t('pages.interview.InterviewEvaluationModal.s24') : t('pages.interview.InterviewEvaluationModal.s25') }}</h1>
        <div class="ats-header__meta">
          <span><b>{{ t('pages.interview.InterviewEvaluationModal.s1') }}</b> {{ source.candidate.position }}</span>
          <span><b>{{ t('pages.interview.InterviewEvaluationModal.s2') }}</b> {{ source.candidate.level }}</span>
          <span><b>{{ t('pages.interview.InterviewEvaluationModal.s3') }}</b> {{ source.candidate.interviewDate }}</span>
        </div>
      </header>

      <div class="ats-body">
        <!-- ===== 黄色提示 banner ===== -->
        <div class="ats-banner">
          <svg class="ats-banner__icon" viewBox="0 0 20 20" fill="currentColor">
            <path clip-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" fill-rule="evenodd" />
          </svg>
          <div class="ats-banner__text">
            <p>{{ t('pages.interview.InterviewEvaluationModal.s4') }}</p>
            <p>{{ t('pages.interview.InterviewEvaluationModal.s17') }}</p>
          </div>
        </div>

        <!-- ===== 区块 1：生产力四要素符合性评价 ===== -->
        <section class="ats-section">
          <div class="ats-section__head">
            <span class="ats-section__bar" />
            <h2 class="ats-section__title">{{ t('pages.interview.InterviewEvaluationModal.s5') }}</h2>
          </div>
          <div class="ats-section__list">
            <div
              v-for="dim in FOUR_DIMS"
              :key="dim.key"
              class="ats-comp"
              :class="{ 'ats-comp--invalid': editing && compliances[dim.key]?.compliance === 'FAIL' && !compliances[dim.key]?.reason?.trim() }"
            >
              <div class="ats-comp__head">
                <div class="ats-comp__name">
                  <span class="ats-comp__required">*</span>{{ dim.name }}
                </div>
                <div class="ats-comp__choices">
                  <button
                    v-for="opt in COMPLIANCE_OPTIONS"
                    :key="opt.value"
                    type="button"
                    class="ats-chip"
                    :class="[
                      'ats-chip--' + opt.value.toLowerCase(),
                      { 'is-active': compliances[dim.key]?.compliance === opt.value },
                    ]"
                    :disabled="!editing"
                    @click="setCompliance(dim.key, opt.value)"
                  >
{{ opt.label }}
</button>
                </div>
              </div>
              <n-input
                v-model:value="compliances[dim.key].reason"
                type="textarea"
                :rows="2"
                :placeholder="compliances[dim.key]?.compliance === 'FAIL' ? t('pages.interview.InterviewEvaluationModal.s26') : t('pages.interview.InterviewEvaluationModal.s27')"
                :disabled="!editing"
                :status="editing && compliances[dim.key]?.compliance === 'FAIL' && !compliances[dim.key]?.reason?.trim() ? 'error' : undefined"
              />
              <p v-if="editing && compliances[dim.key]?.compliance === 'FAIL' && !compliances[dim.key]?.reason?.trim()" class="ats-comp__hint">
                {{ t('pages.interview.InterviewEvaluationModal.s18') }}
              </p>
            </div>
          </div>
        </section>

        <!-- ===== 区块 2：五能价值观评价 ===== -->
        <section class="ats-section">
          <div class="ats-section__head">
            <span class="ats-section__bar" />
            <h2 class="ats-section__title">{{ t('pages.interview.InterviewEvaluationModal.s6') }}</h2>
            <span v-if="editing" class="ats-section__avg">{{ t('pages.interview.InterviewEvaluationModal.s19') }} {{ avgValueScore }}</span>
          </div>
          <div class="ats-section__list">
            <div
              v-for="val in FIVE_VALUES"
              :key="val.key"
              class="ats-val"
            >
              <div class="ats-val__name">
                <span class="ats-comp__required">*</span>{{ val.name }}
              </div>
              <div class="ats-val__rating">
                <button
                  v-for="n in 5"
                  :key="n"
                  type="button"
                  class="ats-dot"
                  :class="{ 'is-active': (values[val.key] ?? 0) >= n }"
                  :disabled="!editing"
                  @click="setValue(val.key, (values[val.key] ?? 0) === n ? 0 : n)"
                >
{{ n }}
</button>
              </div>
            </div>
          </div>
        </section>

        <!-- ===== 区块 3：面试结论 ===== -->
        <section class="ats-section">
          <div class="ats-section__head">
            <span class="ats-section__bar" />
            <h2 class="ats-section__title">{{ t('pages.interview.InterviewEvaluationModal.s7') }}</h2>
          </div>
          <div class="ats-section__list">
            <div class="ats-concl">
              <div class="ats-concl__row">
                <label class="ats-concl__label">{{ t('pages.interview.InterviewEvaluationModal.s8') }}</label>
                <n-select
                  v-model:value="suggestedLevel"
                  :options="LEVEL_OPTIONS"
                  :disabled="!editing"
                  style="max-width: 12rem;"
                />
                <label class="ats-concl__label ats-concl__label--salary">{{ t('pages.interview.InterviewEvaluationModal.s20') }}</label>
                <n-input
                  v-model:value="suggestedSalary"
                  :disabled="!editing"
                  :placeholder="t('pages.interview.InterviewEvaluationModal.s15')"
                  style="max-width: 12rem;"
                />
              </div>
              <div class="ats-concl__row">
                <label class="ats-concl__label"><span class="ats-comp__required">*</span>{{ t('pages.interview.InterviewEvaluationModal.s9') }}</label>
                <n-radio-group v-model:value="finalResult" :disabled="!editing">
                  <n-space>
                    <n-radio value="PASS">{{ t('pages.interview.InterviewEvaluationModal.s10') }}</n-radio>
                    <n-radio value="FAIL">{{ t('pages.interview.InterviewEvaluationModal.s11') }}</n-radio>
                    <n-radio value="PENDING">{{ t('pages.interview.InterviewEvaluationModal.s12') }}</n-radio>
                  </n-space>
                </n-radio-group>
              </div>
              <div class="ats-concl__row ats-concl__row--comment">
                <label class="ats-concl__label"><span class="ats-comp__required">*</span>{{ t('pages.interview.InterviewEvaluationModal.s13') }}</label>
                <n-input
                  v-model:value="comment"
                  type="textarea"
                  :rows="3"
                  :placeholder="t('pages.interview.InterviewEvaluationModal.s16')"
                  :disabled="!editing"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- ===== 底部提交 ===== -->
        <div class="ats-footer">
          <n-button
            v-if="editing"
            type="primary"
            size="large"
            :disabled="!canSubmit"
            class="ats-submit"
            @click="handleSubmit"
          >
{{ t('pages.interview.InterviewEvaluationModal.s21') }}
</n-button>
          <n-button v-else type="default" size="large" class="ats-submit" @click="close">{{ t('pages.interview.InterviewEvaluationModal.s14') }}</n-button>
        </div>
      </div>
    </div>
  </n-modal>
</template>

<style scoped>
/* ===== 根容器 ===== */
.ats-eval {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-radius: 16px;
  overflow: hidden;
}

/* ===== Header ===== */
.ats-header {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-hairline);
}
.ats-header__title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 12px;
  color: var(--ink);
}
.ats-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 32px;
  font-size: 13px;
  color: var(--ink-soft);
}
.ats-header__meta b {
  color: var(--ink);
  font-weight: 500;
  margin-right: 4px;
}

/* ===== Body ===== */
.ats-body {
  padding: 20px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ===== 黄色提示 banner ===== */
.ats-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid var(--brand-warm-soft);
  background: var(--brand-warm-soft);
  border-radius: 12px;
  color: var(--ink);
}
.ats-banner__icon {
  width: 20px; height: 20px;
  color: var(--brand-warm-deep);
  flex-shrink: 0;
}
.ats-banner__text {
  display: flex; flex-direction: column; gap: 4px;
  font-size: 13px;
  font-weight: 500;
}
.ats-banner__text p { margin: 0; line-height: 1.5; }

/* ===== Section 通用 ===== */
.ats-section__head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px;
}
.ats-section__bar {
  width: 4px; height: 20px;
  border-radius: 9999px;
  background: var(--brand-warm);
}
.ats-section__title {
  font-size: 16px; font-weight: 600;
  color: var(--ink);
  margin: 0;
}
.ats-section__avg {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-faint);
}
.ats-section__list {
  display: flex; flex-direction: column; gap: 10px;
}

/* ===== 4 维符合性项 ===== */
.ats-comp {
  background: var(--g1);
  border-radius: 12px;
  padding: 12px 16px;
  border: 1px solid var(--border-hairline);
}
.ats-comp__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.ats-comp__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
}
.ats-comp__required {
  color: var(--c-error);
  margin-right: 4px;
}
.ats-comp__choices {
  display: flex; gap: 6px;
}
.ats-comp__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--c-error);
}

/* ===== 三档 chip ===== */
.ats-chip {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-hairline);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.ats-chip:hover:not(:disabled) {
  border-color: var(--brand-warm);
}
.ats-chip.is-active.ats-chip--pass {
  background: var(--brand-warm);
  border-color: var(--brand-warm);
  color: var(--brand-warm-deep);
  font-weight: 500;
}
.ats-chip.is-active.ats-chip--partial {
  background: var(--c-info);
  border-color: var(--c-info);
  color: #FFFFFF;
  font-weight: 500;
}
.ats-chip.is-active.ats-chip--fail {
  background: var(--brand-warm);
  border-color: var(--brand-warm);
  color: var(--brand-warm-deep);
  font-weight: 500;
}
.ats-chip:disabled { cursor: not-allowed; opacity: .85; }

/* ===== 5 能价值观项 ===== */
.ats-val {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px;
  background: var(--g1);
  border-radius: 12px;
  border: 1px solid var(--border-hairline);
}
.ats-val__name {
  font-size: 14px; font-weight: 500; color: var(--ink);
}
.ats-val__rating { display: flex; gap: 8px; }
.ats-dot {
  width: 32px; height: 32px;
  border-radius: 9999px;
  border: 1px solid var(--border-hairline);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 13px; font-weight: 500;
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.ats-dot:hover:not(:disabled) { border-color: var(--brand-warm); }
.ats-dot.is-active {
  background: var(--brand-warm);
  border-color: var(--brand-warm);
  color: var(--brand-warm-deep);
  font-weight: 600;
}
.ats-dot:disabled { cursor: not-allowed; opacity: .85; }

/* ===== 面试结论 ===== */
.ats-concl {
  background: var(--g1);
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid var(--border-hairline);
  display: flex; flex-direction: column; gap: 14px;
}
.ats-concl__row {
  display: flex; align-items: center; gap: 12px;
  flex-wrap: wrap;
}
.ats-concl__row--comment { flex-direction: column; align-items: stretch; gap: 6px; }
.ats-concl__label {
  font-size: 13px; font-weight: 500;
  color: var(--ink-soft);
  min-width: 130px;
  white-space: nowrap;
}
.ats-concl__label--salary { min-width: auto; margin-left: 12px; }

/* ===== 底部 ===== */
.ats-footer {
  display: flex; justify-content: center;
  padding: 8px 0 4px;
}
.ats-submit {
  min-width: 160px;
  border-radius: 9999px;
  font-weight: 600;
}

/* ===== view 态统一降低对比 ===== */
.ats-eval :deep(.n-input--disabled),
.ats-eval :deep(.n-select--disabled) {
  opacity: .9;
}

/* ===== 响应式 ===== */
@media (max-width: 720px) {
  .ats-header { padding: 16px; }
  .ats-header__title { font-size: 20px; }
  .ats-body { padding: 16px; }
  .ats-concl__row { flex-direction: column; align-items: stretch; }
  .ats-concl__label { min-width: 0; }
  .ats-concl__label--salary { margin-left: 0; }
  .ats-val__rating { gap: 6px; }
  .ats-dot { width: 28px; height: 28px; font-size: 12px; }
}
</style>
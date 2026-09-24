<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, watch, h } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NSwitch,
  NButton, NTag, NSpace, NGrid, NGi, NAlert, NText, NIcon, NTooltip, useMessage,
} from 'naive-ui'
import { InformationCircleOutline as Info } from '@vicons/ionicons5'
import {
  STRENGTH, DEPTS, POSITIONS, LEVELS, ALL_MONTHS,
  listDimensions, listIndicators, createRule, updateRule,
  type ControlRule, type ControlDimension, type ControlIndicator, type Strength,
} from '../api/campusControl'
import { extractApiError } from '../api/dynamic-field'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  rule: ControlRule | null
  /** 'view' 只读详情；'create' 新建（空白表单）；'edit' 编辑已有规则 */
  mode?: 'view' | 'create' | 'edit'
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved', rule: ControlRule): void
}>()

const message = useMessage()

const dimensions = ref<ControlDimension[]>([])
const indicators = ref<ControlIndicator[]>([])
const loadingOptions = ref(false)
const saving = ref(false)
const editing = ref(false)

const blank = () => ({
  code: '',
  bu: '',
  position: '',
  level: '',
  dimension: '',
  indicator: '',
  year: new Date().getFullYear(),
  strength: '硬约束' as Strength,
  annualTarget: 0,
  monthlyTargets: Array(12).fill(0) as number[],
  // v2.10：月度浮动目标（roll-over）；与 DB 字段 rollover_enabled 对应
  rolloverEnabled: false,
})

const form = reactive(blank())

const dimensionOptions = computed(() => dimensions.value.map((d) => ({ label: d.name, value: d.id })))
const indicatorOptions = computed(() =>
  indicators.value
    .filter((i) => i.dimension === form.dimension)
    .map((i) => ({ label: i.name, value: i.id })),
)
const deptOptions = [{ label: '全局', value: '' }, ...DEPTS.map((v) => ({ label: v, value: v }))]
const positionOptions = [{ label: '不限', value: '' }, ...POSITIONS.map((v) => ({ label: v, value: v }))]
const levelOptions = [{ label: '不限', value: '' }, ...LEVELS.map((v) => ({ label: v, value: v }))]
const strengthOptions = STRENGTH.map((v) => ({ label: v, value: v }))

/** 强度等级 → 标签样式类。
 *  P0-1 修复：原 mapping 把"硬约束"误标为 error 红，违反 AGENTS.md R-211（语义色仅做状态）。
 *  改用三档中性灰语义：硬约束=已锁定 / 软约束=参考性 / 指导=建议性，对比度均 ≥ 7:1（vs 白底）。*/
const strengthClass = (s: string) => {
  if (s === '硬约束') return 'rc-tag rc-tag--hard'
  if (s === '软约束') return 'rc-tag rc-tag--soft'
  return 'rc-tag rc-tag--advisory'
}
/** 强度等级 → 文字解释（用于 hover/aria-label）*/
const strengthDesc = (s: string) => {
  if (s === '硬约束') return '硬约束：违反将直接驳回，不可豁免'
  if (s === '软约束') return '软约束：违反会告警但允许豁免审批'
  return '指导：仅作建议，不做强制'
}
const scopeText = (bu: string, position: string, level: string) => {
  if (!bu && !position && !level) return '全局（不限定部门/职务/职级）'
  return [bu, position || '职务不限', level || '职级不限'].filter(Boolean).join(' · ')
}

/** 实时计算：12 月目标之和（用于加和异常 alert）。*/
const monthlySum = computed(() =>
  form.monthlyTargets.reduce((acc, v) => acc + (Number(v) || 0), 0),
)
/** 编辑模式下且年度目标 > 0 时，月度加和 ≠ 年度目标 视为异常。*/
const monthlySumMismatch = computed(() => {
  if (!editing.value) return false
  if (form.annualTarget <= 0) return false
  return monthlySum.value !== form.annualTarget
})

function syncFormFromRule(r: ControlRule | null) {
  const b = blank()
  if (r) {
    Object.assign(b, {
      code: r.code,
      bu: r.bu || '',
      position: r.position || '',
      level: r.level || '',
      dimension: r.dimension,
      indicator: r.indicator,
      year: r.year,
      strength: r.strength,
      annualTarget: Math.round(r.annualTarget || 0),
      monthlyTargets: Array.isArray(r.monthlyTargets) && r.monthlyTargets.length === 12
        ? r.monthlyTargets.map((v) => Math.round(v || 0))
        : Array(12).fill(0),
      // v2.10：浮动目标开关；缺省视为关闭（v2.4 行为零回归）
      rolloverEnabled: Boolean(r.rolloverEnabled),
    })
  }
  Object.assign(form, b)
}

async function loadOptions() {
  if (loadingOptions.value) return
  loadingOptions.value = true
  try {
    const [d, i] = await Promise.all([listDimensions(), listIndicators()])
    dimensions.value = d
    indicators.value = i
  } catch (e) {
    message.error(extractApiError(e, '加载维度/指标失败'))
  } finally {
    loadingOptions.value = false
  }
}

watch(
  () => props.show,
  async (v) => {
    if (v) {
      editing.value = props.mode === 'create' || props.mode === 'edit'
      syncFormFromRule(props.rule)
      await loadOptions()
    }
  },
)

function close() {
  emit('update:show', false)
}

function onDimensionChange() {
  // 维度切换后，若当前指标不属于新维度则清空
  if (form.indicator && !indicatorOptions.value.some((o) => o.value === form.indicator)) {
    form.indicator = ''
  }
}

function evenFillMonthly() {
  const total = Math.max(0, Math.round(form.annualTarget))
  const base = Math.floor(total / 12)
  const rem = total - base * 12
  form.monthlyTargets = Array.from({ length: 12 }, (_, i) => base + (i < rem ? 1 : 0))
}

/** 友好中文校验：清晰指出校验失败原因、触发条件、适用规则范围。
 *  返回 null 表示通过；返回 string 即为给用户看的提示文本。*/
function validate(): string | null {
  if (!form.dimension) return '请先选择「维度」（院校标签/专业标签/性别）后再保存'
  if (!form.indicator) return '请先选择「指标」（所选维度下的具体分类，如 985、男、工学）后再保存'
  if (!form.year) return '请填写「生效年度」（如 2026），用于按年度统计管控目标'
  if (form.annualTarget < 0) return '「年度目标人数」不能为负数，请调整为 ≥ 0 的整数'
  if (monthlySumMismatch.value) {
    return (
      `12 个月目标之和（${monthlySum.value}）与「年度目标人数」（${form.annualTarget}）不一致；` +
      `请调整下方 1月..12月 列使加和 = 年度目标，或点击「按年度均分」自动分配。` +
      `（该规则适用于所有 12 个月度校验，所有指标月度目标均须等于年度目标人数）`
    )
  }
  return null
}

async function save() {
  const err = validate()
  if (err) {
    message.warning(err)
    return
  }
  saving.value = true
  // 扁平规则模型下每条 = 独占 (适用范围, 维度, 年度, 指标) 组合，不存在多指标按占比分配；
  // 占比仅作"看板·月度任务拆解完成度"参考（产品设计 §4.4），无 UI 填写价值，故 payload 恒为 1.0。
  const payload = {
    bu: form.bu,
    position: form.position,
    level: form.level,
    dimension: form.dimension,
    indicator: form.indicator,
    year: form.year,
    target: 1.0,
    strength: form.strength,
    annualTarget: Math.round(form.annualTarget),
    monthlyTargets: form.monthlyTargets.map((v) => Math.round(v || 0)),
    // v2.10：浮动目标开关透传（后端 BooleanField 默认 False；缺省时按 v2.4 行为零回归）
    rolloverEnabled: Boolean(form.rolloverEnabled),
  }
  try {
    const saved = props.rule
      ? await updateRule(props.rule.id, payload)
      : await createRule(payload)
    message.success(props.rule ? '规则已更新' : '规则已创建')
    emit('saved', saved)
    close()
  } catch (e) {
    message.error(extractApiError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="rule ? `规则 ${rule.code || ''}` : '新增规则'"
    :style="{ width: '760px', maxWidth: '94vw' }"
    :bordered="false"
    :segmented="{ content: true, footer: true }"
    class="rule-config-modal"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
      <div class="rule-config-modal__scroll">
      <n-space vertical :size="18">
        <!-- 模块一：规则信息 -->
        <section>
          <div class="rc-section-title">{{ t('components.RuleConfigDrawer.s1') }}</div>
          <n-form :disabled="!editing" label-placement="top">
            <!-- T130：第 1 行 3 列 — 维度 / 指标 / 生效年度 -->
            <n-grid :cols="3" :x-gap="12">
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s11')" required>
                  <n-select
                    v-model:value="form.dimension"
                    :options="dimensionOptions"
                    :placeholder="t('components.RuleConfigDrawer.s5')"
                    :disabled="!editing"
                    @update:value="onDimensionChange"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s12')" required>
                  <n-select
                    v-model:value="form.indicator"
                    :options="indicatorOptions"
                    :placeholder="t('components.RuleConfigDrawer.s6')"
                    :disabled="!editing || !form.dimension"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s13')" required>
                  <n-input-number v-model:value="form.year" :min="2020" :max="2100" style="width: 100%" />
                </n-form-item>
              </n-gi>
            </n-grid>

            <!-- T130：第 2 行 3 列 — 部门 / 职务 / 职级 -->
            <n-grid :cols="3" :x-gap="12">
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s14')">
                  <n-select v-model:value="form.bu" :options="deptOptions" :placeholder="t('components.RuleConfigDrawer.s7')" clearable />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s15')">
                  <n-select v-model:value="form.position" :options="positionOptions" :placeholder="t('components.RuleConfigDrawer.s8')" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item :label="t('components.RuleConfigDrawer.s16')">
                  <n-select v-model:value="form.level" :options="levelOptions" :placeholder="t('components.RuleConfigDrawer.s9')" />
                </n-form-item>
              </n-gi>
            </n-grid>
</n-form>
        </section>

        <!-- 模块二：管控目标 -->
        <section>
          <div class="rc-section-title">{{ t('components.RuleConfigDrawer.s2') }}</div>
          <n-form :disabled="!editing" label-placement="top">
            <!-- 年度目标行：两列布局（年度输入 | 月度浮动目标开关 + 提示 icon）。
                 提示文本从行内字面量收为 n-tooltip + Lucide Info，hover 触发，避免挤压第二列。 -->
            <n-form-item :label="t('components.RuleConfigDrawer.s17')">
              <n-grid :cols="2" :x-gap="16" responsive="screen" class="rc-annual-row">
                <n-gi>
                  <n-space align="center" :wrap="false">
                    <n-input-number v-model:value="form.annualTarget" :min="0" :step="1" />
                    <n-button type="primary" size="small" :disabled="!editing" @click="evenFillMonthly">{{ t('components.RuleConfigDrawer.s3') }}</n-button>
                  </n-space>
                </n-gi>
                <n-gi>
                  <n-space
                    align="center"
                    :wrap="false"
                    :size="8"
                    :class="['rc-rollover-cell', { 'rc-rollover-cell--on': form.rolloverEnabled }]"
                  >
                    <span class="rc-rollover-label">{{ t('components.RuleConfigDrawer.s4') }}</span>
                    <n-switch v-model:value="form.rolloverEnabled" :disabled="!editing" />
                    <n-tooltip placement="left-start" :show-arrow="true">
                      <template #trigger>
                        <!-- P0-2：包 <button> 让键盘可达 + aria-label，
                             用 .rc-info-btn 命中 :focus-visible 环，避免 R-109 失守 -->
                        <button type="button" class="rc-info-btn" :aria-label="t('components.RuleConfigDrawer.s10')">
                          <n-icon :component="Info" />
                        </button>
                      </template>
                      <!-- 保留完整 60 字公式定义（"本月目标 = 本月额定目标 + 浮动目标（= 已过去月份目标合计 − 已过去月份入职且在职，负数裁 0）"）。
                           placement="left-start" + CSS max-width:360 + white-space:normal + word-break 让它自然换行，
                           不再靠删减文案解决布局问题（兵哥 2026-09-06 拍红框：删减后用户看不懂核心公式）。-->
                      开启后，本月目标 = 本月额定目标 + 浮动目标（= 已过去月份目标合计 − 已过去月份入职且在职，负数裁 0）
                    </n-tooltip>
                    <!-- P1-2：启用时给右列底部加极简状态文字（绿色 token），
                         让"开关打开后的行为变化"对用户即时可见 -->
                    <span v-if="form.rolloverEnabled" class="rc-rollover-state">已开启 · 滚动目标</span>
                  </n-space>
                </n-gi>
              </n-grid>
            </n-form-item>
            <n-form-item label="月度目标（人）">
              <!-- P0-3：当!editing 时整体降透明度 + 贴 readonly 角标，
                   让"只读"与"空值"视觉可区分（违反 R-101 状态视觉完整）-->
              <div :class="['rc-monthly', { 'rc-monthly--readonly': !editing }]">
                <div v-for="(m, i) in form.monthlyTargets" :key="i" class="rc-monthly-item">
                  <span class="rc-monthly-label">{{ ALL_MONTHS[i] }}</span>
                  <n-input-number v-model:value="form.monthlyTargets[i]" :min="0" :step="1" size="small" />
                </div>
                <span v-if="!editing" class="rc-readonly-badge">查看中 · 不可编辑</span>
              </div>
            </n-form-item>

            <!-- T131：月度加和异常时显示红框错误 alert（强提示，阻止保存） -->
            <n-alert
              v-if="monthlySumMismatch"
              type="error"
              :show-icon="true"
              title="12 个月目标之和 ≠ 年度目标"
              style="margin-top: 4px"
            >
              当前月度加和 <strong>{{ monthlySum }}</strong> 人，与「年度目标人数」{{ form.annualTarget }} 人不一致；
              请调整 1月..12月 列使加和 = 年度目标，或点击「按年度均分」自动分配。
            </n-alert>
</n-form>
        </section>

        <!-- 模块三：管控强度 -->
        <section>
          <div class="rc-section-title">管控强度</div>
          <n-form :disabled="!editing" label-placement="top">
            <n-form-item>
              <n-select v-model:value="form.strength" :options="strengthOptions" />
              <!-- P0-1：n-tag :type 三态改用 .rc-tag + 三档中性灰语义类，避免红色"硬约束"误读为 error -->
              <span
                v-if="!editing"
                :class="strengthClass(form.strength)"
                role="status"
                :aria-label="strengthDesc(form.strength)"
                class="rc-tag-inline"
              >{{ form.strength }}</span>
            </n-form-item>
                      </n-form>
        </section>
      </n-space>
      </div>

      <template #footer>
        <!-- 底部操作栏：align="center" 让按钮在 footer 高度内纵向居中；
             真正起效的是 un-scoped .n-card.rule-config-modal .n-card__footer { display:flex; align-items:center } -->
        <n-space align="center" justify="end" :size="12" :wrap="false">
          <!-- P1-3：min-width:88px 让"编辑"/"关闭"两个按钮等宽，对齐感提升 -->
          <n-button v-if="!editing" class="rc-footer-btn" @click="editing = true">编辑</n-button>
          <n-button v-else class="rc-footer-btn" tertiary @click="close">取消</n-button>
          <n-button v-if="editing" class="rc-footer-btn" type="primary" :loading="saving" @click="save">保存</n-button>
          <n-button v-if="!editing" class="rc-footer-btn" @click="close">关闭</n-button>
        </n-space>
      </template>
  </n-modal>
</template>

<style scoped>
.rc-section-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  margin-bottom: var(--space-3);
  padding-left: 10px;
  border-left: 3px solid var(--brand);
  color: var(--ink);
}
.rc-monthly {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-2);  /* P2-1: 行间距统一 8px token，避免 6px 魔数 */
  align-items: flex-end;
  position: relative;
  transition: opacity .15s ease;
}
.rc-monthly-item {
  display: flex;
  flex-direction: column;
  gap: 4px;                              /* P2-1: 2px → 4px，月标与输入框呼吸更舒展 */
  padding: 4px 6px;                       /* P2-1: 输入容器内 padding，避免数字贴边框 */
  border-radius: var(--radius-sm);
  transition: background .15s ease;
  /* 一行 4 个：12 月目标分 3 行展示，配合 modal 宽度 760px */
  flex: 1 1 calc((100% - 24px) / 4);
  min-width: 96px;
}
/* P0-3: readonly 态 — 月度矩阵降透明度 + 灰色滤色，区分"不可编辑"与"空值" */
.rc-monthly--readonly {
  opacity: 0.55;
  filter: saturate(0.6);
}
.rc-monthly-label {
  font-size: var(--fs-12);               /* P2-1: 11px → 12px，对齐 tokens.css 字号刻度 */
  color: var(--ink-soft);
  font-weight: 500;
}
/* P0-3: 角标 — 浮动在月度矩阵左上，明确"查看中"语义 */
.rc-readonly-badge {
  position: absolute;
  top: -2px;
  left: 0;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  background: var(--g2);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

/* ==================== 年度目标行：两列布局（年度输入 | 月度浮动目标开关 + 提示 icon） ==================== */
/* n-grid:2 + 16px 横向间距，两端对齐 form-item 宽度 */
.rc-annual-row {
  width: 100%;
}
.rc-rollover-label {
  font-size: var(--fs-13);
  color: var(--ink);
  font-weight: 500;
  white-space: nowrap;
}
/* 右侧 rollover 容器 + 启用态视觉反馈（P1-2）：
   启用时底色变 brand-soft + 左 2px brand 边，状态即时可见 */
.rc-rollover-cell {
  transition: background .15s ease, box-shadow .15s ease;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border-left: 2px solid transparent;
}
.rc-rollover-cell--on {
  background: var(--c-success-soft);
  border-left-color: var(--c-success);
}
.rc-rollover-state {
  font-size: var(--fs-12);
  color: var(--c-success-deep);
  font-weight: 500;
  margin-left: 4px;
}
/* P0-2: 信息按钮 — 让 n-tooltip 触发器键盘可达 + :focus-visible 环 */
.rc-info-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  cursor: help;
  border-radius: 50%;
  padding: 0;
  transition: color .15s ease, background .15s ease;
}
.rc-info-btn:hover,
.rc-info-btn:focus-visible {
  color: var(--brand);
  background: var(--g1);
  outline: none;
}
.rc-info-btn:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}
/* 注：tooltip 宽度兜底写在 un-scoped <style> 块（避免 :deep 穿透到 n-card 内部
   v-binder-follower 时被 scoped data-v 拦截）。 */
/* P0-1: 强度等级标签 — 三档中性灰（替代原 error/warning/default 三态红黄） */
.rc-tag,
.rc-tag-inline {
  display: inline-flex;
  align-items: center;
  margin-left: 10px;
  padding: 3px 12px;
  border-radius: 999px;                       /* P2-2: 圆角胶囊，强化"补充说明 badge"语义 */
  font-size: var(--fs-13);                    /* P1-4: 从 12px small tag → 13px 中字阶，对比度+层级 */
  font-weight: 500;
  line-height: 1.4;
  user-select: none;
  white-space: nowrap;
}
.rc-tag--hard {
  color: var(--ink);                          /* 硬约束：深色文字 + 浅灰底 = 已锁定 */
  background: var(--g2);
  border: 1px solid var(--g4);
}
.rc-tag--soft {
  color: var(--ink-soft);                     /* 软约束：次要文字 + 更浅底 = 参考性 */
  background: var(--g1);
  border: 1px solid var(--g3);
}
.rc-tag--advisory {
  color: var(--ink-faint);                    /* 指导：辅助文字 + 最浅底 = 建议性 */
  background: transparent;
  border: 1px dashed var(--g4);
}

/* P1-3: 底栏按钮等宽 + min-width:88px */
.rc-footer-btn {
  min-width: 88px;
}

/* P2-3: modal 标题区文字 max-width 防挤压 close 按钮 */
:deep(.n-card-header__main) {
  max-width: calc(100% - 48px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<!-- NModal preset=card 由 teleport 渲染到 body，scoped data-v 不可达。
     Naive 把 class 合并到 .n-card 根（class="n-card ... rule-config-modal"）。
     滚动方案：不使用 content-scrollable（会经 Naive 内部 NScrollbar 触发
     "Non-function value encountered for default slot" Vue 警告，且无法从模板侧消除），
     改为在默认插槽内放一个原生滚动容器 .rule-config-modal__scroll 接管内部滚动。
     原生 div 走 element 渲染路径、不经 normalizeVNodeSlots，因此无该告警；
     同时也避免 n-card flex 链失效的老坑（e80b392）。
     第二个 <style> 不带 scoped，对全局生效，专门命中 teleport 出来的 modal 根。 -->
<style>
.n-card.rule-config-modal {
  max-height: min(90vh, 1000px);
}
.rule-config-modal__scroll {
  max-height: calc(min(90vh, 1000px) - 156px);
  overflow-y: auto;
  /* 滚动条 gutter：用浏览器原生 scrollbar-gutter: stable 而非 padding-right 魔数。
     旧写法 padding-right: var(--space-1) = 4px 是凭感觉加的滚动条占位，但
     实测当前 modal scrollWidth(688) === clientWidth(688) → 无滚动条 → 这 4px 是无意义魔数；
     即使有滚动条，macOS overlay (0px) / Windows (15-17px) 宽度不一，固定 padding 也覆盖不全。
     scrollbar-gutter: stable 让浏览器始终预留滚动条槽位，跨平台一致 + 治本。*/
  scrollbar-gutter: stable;
}
/* Tooltip 宽度兜底（un-scoped 兜底版本）：实测 v-binder-follower 被 Naive 挂到 n-card 内（而非 body），
   :deep 在 scoped 里能命中。但万一 Naive 升级改了挂载点，这个 un-scoped 选择器兜底确保宽度受控。
   真实场景：n-modal-container > n-card > v-binder-follower-container > v-binder-follower-content > n-popover */
body > div.n-modal-container .n-popover {
  max-width: 360px !important;
  word-break: break-word;
  white-space: normal;
  line-height: 1.5;
}
body > div.n-modal-container .n-popover .n-popover__content {
  max-width: 360px;
}

/* 底部操作栏：用兵哥给的精确深选择器（命中 .n-modal-container 链路下的
   .rule-config-modal .n-card__footer）确保覆盖 Naive 默认 footer padding。
   display:flex + align-items:center 保持按钮纵向居中；
   padding:24px var(--space-6) (上下 24px、左右 24px) 给按钮充分呼吸——
   ⚠️ 千万别再用 var(--space-5)！tokens.css §8 只定义了 --space-1/2/3/4/6/8/12/16，
   --space-5 未定义 → CSS shorthand 解析失败 → 整条规则 drop → Naive 默认 0 padding 接管。
   实测根因（2026-09-06 getComputedStyle 硬证据：footer padding 全 0px）——
   兵哥"上下右全贴边"截图即来自此坑。改用 --space-6（24px）+ 上下 24px 真正解套。
   顶部 1px hairline 视觉断带，让 footer 与上方 form 段分开；justify-content: flex-end 让按钮靠右。 */
body > div.n-modal-container > div > div > div.n-scrollbar-container > div > div.n-card.n-card--content-segmented.n-card--footer-segmented.n-modal.rule-config-modal > div.n-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  padding: 24px var(--space-6);
  border-top: 1px solid var(--border-hairline);
  background: linear-gradient(180deg, transparent 0%, var(--g1) 100%);
}
</style>

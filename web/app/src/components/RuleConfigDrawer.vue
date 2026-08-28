<script setup lang="ts">
import { ref, reactive, computed, watch, h } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NInputNumber, NSelect,
  NButton, NTag, NSpace, NGrid, NGi, NDivider, NAlert, useMessage,
} from 'naive-ui'
import {
  STRENGTH, DEPTS, POSITIONS, LEVELS, ALL_MONTHS,
  listDimensions, listIndicators, createRule, updateRule,
  type ControlRule, type ControlDimension, type ControlIndicator, type Strength,
} from '../api/campusControl'
import { extractApiError } from '../api/dynamic-field'

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

const strengthType = (s: string) => (s === '硬约束' ? 'error' : s === '软约束' ? 'warning' : 'default')
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
    :content-scrollable="true"
    class="rule-config-modal"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
      <n-space vertical :size="14">
        <!-- 模块一：规则信息 -->
        <section>
          <div class="rc-section-title"><span class="dot" />规则信息</div>
          <n-form :disabled="!editing" label-placement="top">
            <!-- T130：第 1 行 3 列 — 维度 / 指标 / 生效年度 -->
            <n-grid :cols="3" :x-gap="12">
              <n-gi>
                <n-form-item label="维度" required>
                  <n-select
                    v-model:value="form.dimension"
                    :options="dimensionOptions"
                    placeholder="选择维度"
                    :disabled="!editing"
                    @update:value="onDimensionChange"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="指标" required>
                  <n-select
                    v-model:value="form.indicator"
                    :options="indicatorOptions"
                    placeholder="选择指标"
                    :disabled="!editing || !form.dimension"
                  />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="生效年度" required>
                  <n-input-number v-model:value="form.year" :min="2020" :max="2100" style="width: 100%" />
                </n-form-item>
              </n-gi>
            </n-grid>

            <!-- T130：第 2 行 3 列 — 部门 / 职务 / 职级 -->
            <n-grid :cols="3" :x-gap="12">
              <n-gi>
                <n-form-item label="部门">
                  <n-select v-model:value="form.bu" :options="deptOptions" placeholder="全局" clearable />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="职务">
                  <n-select v-model:value="form.position" :options="positionOptions" placeholder="不限" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="职级">
                  <n-select v-model:value="form.level" :options="levelOptions" placeholder="不限" />
                </n-form-item>
              </n-gi>
            </n-grid>

          </n-form>
        </section>

        <n-divider />

        <!-- 模块二：管控目标 -->
        <section>
          <div class="rc-section-title"><span class="dot" />管控目标</div>
          <n-form :disabled="!editing" label-placement="top">
            <n-form-item label="年度目标(人)">
              <n-space align="center" :wrap="false">
                <n-input-number v-model:value="form.annualTarget" :min="0" :step="1" />
                <n-button type="primary" size="small" :disabled="!editing" @click="evenFillMonthly">按年度均分</n-button>
              </n-space>
            </n-form-item>
            <n-form-item label="月度目标(人)">
              <div class="rc-monthly">
                <div v-for="(m, i) in form.monthlyTargets" :key="i" class="rc-monthly-item">
                  <span class="rc-monthly-label">{{ ALL_MONTHS[i] }}</span>
                  <n-input-number v-model:value="form.monthlyTargets[i]" :min="0" :step="1" size="small" />
                </div>
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

        <n-divider />

        <!-- 模块三：管控强度 -->
        <section>
          <div class="rc-section-title"><span class="dot" />管控强度</div>
          <n-form :disabled="!editing" label-placement="top">
            <n-form-item>
              <n-select v-model:value="form.strength" :options="strengthOptions" />
              <n-tag
                v-if="!editing"
                :type="strengthType(form.strength)"
                :bordered="false"
                size="small"
                style="margin-left: 10px"
              >{{ form.strength }}</n-tag>
            </n-form-item>
          </n-form>
        </section>
      </n-space>

      <template #footer>
        <n-space justify="end">
          <n-button v-if="!editing" @click="editing = true">编辑</n-button>
          <n-button v-else tertiary @click="close">取消</n-button>
          <n-button v-if="editing" type="primary" :loading="saving" @click="save">保存</n-button>
          <n-button v-if="!editing" @click="close">关闭</n-button>
        </n-space>
      </template>
  </n-modal>
</template>

<style scoped>
.rc-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--ink, #1f2937);
}
.rc-section-title .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary, #6366f1);
}
.rc-monthly {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 6px;
  align-items: flex-end;
}
.rc-monthly-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  /* 一行 4 个：12 月目标分 3 行展示，配合 modal 宽度 760px */
  flex: 1 1 calc((100% - 18px) / 4);
  min-width: 96px;
}
.rc-monthly-label {
  font-size: 11px;
  color: var(--ink-soft, #6b7280);
}
</style>

<!-- NModal preset=card 由 teleport 渲染到 body，scoped data-v 不可达。
     Naive 把 class 合并到 .n-card 根（class="n-card ... rule-config-modal"）。
     max-height 限制 modal 总高度 + contentScrollable 让 Naive 内置 NScrollbar
     接管 content 内部滚动，避免 12 月目标表单撑爆视口。
     （Playwright 复验证：12 月 + 规则信息 + 管控强度 ≈ 1595px > 典型 900vh）
     第二个 <style> 不带 scoped，对全局生效，专门命中 teleport 出来的 modal 根。 -->
<style>
.n-card.rule-config-modal {
  max-height: min(90vh, 1000px);
}
</style>

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
  targetPct: 0,
  strength: '软约束' as Strength,
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
const deptOptions = DEPTS.map((v) => ({ label: v, value: v }))
const positionOptions = [{ label: '不限', value: '' }, ...POSITIONS.map((v) => ({ label: v, value: v }))]
const levelOptions = [{ label: '不限', value: '' }, ...LEVELS.map((v) => ({ label: v, value: v }))]
const strengthOptions = STRENGTH.map((v) => ({ label: v, value: v }))

const strengthType = (s: string) => (s === '硬约束' ? 'error' : s === '软约束' ? 'warning' : 'default')
const scopeText = (bu: string, position: string, level: string) => {
  if (!bu && !position && !level) return '全局'
  return [bu, position || '职务不限', level || '职级不限'].filter(Boolean).join(' · ')
}

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
      targetPct: Math.round((r.target || 0) * 1000) / 10,
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
  const base = Math.floor(form.annualTarget / 12)
  const rem = form.annualTarget - base * 12
  form.monthlyTargets = Array.from({ length: 12 }, (_, i) => base + (i < rem ? 1 : 0))
}

function validate(): string | null {
  if (!form.dimension) return '请选择维度'
  if (!form.indicator) return '请选择指标'
  if (!form.year) return '请填写生效年度'
  if (form.targetPct < 0 || form.targetPct > 100) return '占比目标须在 0~100% 之间'
  if (form.annualTarget < 0) return '年度目标不能为负'
  return null
}

async function save() {
  const err = validate()
  if (err) {
    message.warning(err)
    return
  }
  saving.value = true
  const payload = {
    bu: form.bu,
    position: form.position,
    level: form.level,
    dimension: form.dimension,
    indicator: form.indicator,
    year: form.year,
    target: form.targetPct / 100,
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
    :style="{ width: '560px', maxWidth: '94vw' }"
    :bordered="false"
    :segmented="{ content: true, footer: true }"
    class="rule-config-modal"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
      <n-space vertical :size="18">
        <!-- 模块一：规则信息 -->
        <section>
          <div class="rc-section-title"><span class="dot" />规则信息</div>
          <n-form :disabled="!editing" label-placement="top">
            <n-form-item label="规则编号">
              <n-input :value="form.code" readonly placeholder="保存后自动生成（G + 4 位）" />
            </n-form-item>
            <n-form-item label="维度" required>
              <n-select
                v-model:value="form.dimension"
                :options="dimensionOptions"
                placeholder="选择维度"
                :disabled="!editing"
                @update:value="onDimensionChange"
              />
            </n-form-item>
            <n-form-item label="指标" required>
              <n-select
                v-model:value="form.indicator"
                :options="indicatorOptions"
                placeholder="选择指标"
                :disabled="!editing || !form.dimension"
              />
            </n-form-item>
            <n-grid :cols="2" :x-gap="12">
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
            </n-grid>
            <n-grid :cols="2" :x-gap="12">
              <n-gi>
                <n-form-item label="职级">
                  <n-select v-model:value="form.level" :options="levelOptions" placeholder="不限" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="生效年度" required>
                  <n-input-number v-model:value="form.year" :min="2020" :max="2100" />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-alert v-if="!editing" type="info" :show-icon="true">
              适用范围：<strong>{{ scopeText(form.bu, form.position, form.level) }}</strong>
            </n-alert>
          </n-form>
        </section>

        <n-divider />

        <!-- 模块二：管控目标 -->
        <section>
          <div class="rc-section-title"><span class="dot" />管控目标</div>
          <n-form :disabled="!editing" label-placement="top">
            <n-grid :cols="2" :x-gap="12">
              <n-gi>
                <n-form-item label="占比目标(%)">
                  <n-input-number v-model:value="form.targetPct" :min="0" :max="100" :step="0.5" />
                </n-form-item>
              </n-gi>
              <n-gi>
                <n-form-item label="年度目标(人)">
                  <n-input-number v-model:value="form.annualTarget" :min="0" :step="1" />
                </n-form-item>
              </n-gi>
            </n-grid>
            <n-form-item label="月度目标(人)">
              <div class="rc-monthly">
                <div v-for="(m, i) in form.monthlyTargets" :key="i" class="rc-monthly-item">
                  <span class="rc-monthly-label">{{ ALL_MONTHS[i] }}</span>
                  <n-input-number v-model:value="form.monthlyTargets[i]" :min="0" :step="1" size="small" />
                </div>
                <n-button v-if="editing" size="tiny" tertiary @click="evenFillMonthly">按年度均分</n-button>
              </div>
            </n-form-item>
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
            <n-alert type="default" :show-icon="false" style="margin-top: 4px">
              硬约束：命中即阻断 Offer 录入；软约束 / 仅提示：放行并提示。
            </n-alert>
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
  gap: 8px;
  align-items: center;
}
.rc-monthly-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rc-monthly-label {
  font-size: 11px;
  color: var(--ink-soft, #6b7280);
}
</style>

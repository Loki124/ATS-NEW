<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NModal, NButton, NSpace, NRadioGroup, NRadio, NSteps, NStep, useMessage,
} from 'naive-ui'
import {
  listBackgroundCheckSuppliers, uploadBackgroundCheckReport, getBackgroundCheckSuggestions,
  createBackgroundCheckOrder,
  type BackgroundCheckSupplier, type BgSuggestion, type BgCandidate,
} from '../../api/integration'
import BgUploadForm from './BgUploadForm.vue'
import BgOrderForm from './BgOrderForm.vue'

const props = defineProps<{
  show: boolean
  candidate: BgCandidate
  /** 补充背调时传入父订单 id；为空表示新增背调 */
  parentOrderId?: string
}>()
const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'created'): void
}>()

const { t } = useI18n()
const message = useMessage()

const isSupplement = computed(() => !!props.parentOrderId)

// ---------- 步骤状态 ----------
// step: 1 选择是否已有报告；2 分支（上传 / 下单），提交即终态（无 step3）
const step = ref(1)
const hasReport = ref<boolean | null>(null)

// ---------- 下单分支：供应商 ----------
const suppliers = ref<BackgroundCheckSupplier[]>([])
const loadingSuppliers = ref(false)

// ---------- 上传分支：背调建议 ----------
const suggestions = ref<BgSuggestion[]>([])
const loadingSuggestions = ref(false)

// ---------- 提交态 ----------
const submitting = ref(false)

// 子表单引用（用于 footer 提交按钮桥接；submit 由子表单 defineExpose 暴露）
const uploadFormRef = ref<{ submit: () => void } | null>(null)
const orderFormRef = ref<{ submit: () => void } | null>(null)

function resetAll() {
  step.value = 1
  hasReport.value = null
  suppliers.value = []
  loadingSuppliers.value = false
  suggestions.value = []
  loadingSuggestions.value = false
}

async function loadSuppliers() {
  loadingSuppliers.value = true
  try {
    // 下单分支仅系统已对接供应商
    suppliers.value = await listBackgroundCheckSuppliers('system_order')
  } catch (e: any) {
    message.error(t('pages.candidate.InitiateBgCheck.loadSuppliersFail'))
  } finally {
    loadingSuppliers.value = false
  }
}

async function loadSuggestions() {
  loadingSuggestions.value = true
  try {
    suggestions.value = await getBackgroundCheckSuggestions(props.candidate.id)
  } catch (e: any) {
    suggestions.value = []
  } finally {
    loadingSuggestions.value = false
  }
}

watch(() => props.show, (v) => {
  if (v) {
    resetAll()
  }
})

function goNext() {
  if (step.value === 1) {
    if (hasReport.value === null) {
      message.error(t('pages.candidate.InitiateBgCheck.requiredHasReport'))
      return
    }
    step.value = 2
    if (hasReport.value) {
      loadSuggestions()
    } else {
      loadSuppliers()
    }
  }
}

function goBack() {
  if (step.value === 2) {
    step.value = 1
  }
}

function handleCancel() {
  emit('update:show', false)
}

// footer 提交按钮 → 触发对应子表单的 submit（子表单内部先校验）
function onUploadSubmit() {
  uploadFormRef.value?.submit()
}
function onOrderSubmit() {
  orderFormRef.value?.submit()
}

// ---------- 上传分支提交 ----------
async function handleUpload(payload: any) {
  submitting.value = true
  try {
    const res = await uploadBackgroundCheckReport({
      candidate_id: props.candidate.id,
      candidate_name: props.candidate.name,
      phone: props.candidate.phone,
      report_url: payload.reportUrl || '',
      remark: payload.remark || '',
      package_name: payload.packageName || '',
      bg_provider: payload.bgProvider || '',
      bg_time: payload.bgTime || '',
      bg_result: payload.bgResult || '',
      subject_snapshot: payload.subjectSnapshot || {},
      answers: payload.answers || [],
      bg_suggestions: payload.bgSuggestions || [],
      parent_order_id: props.parentOrderId,
    })
    if (res.success) {
      message.success(t('pages.candidate.InitiateBgCheck.uploaded'))
      emit('created')
      emit('update:show', false)
    } else {
      message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${res.message || ''}`)
    }
  } catch (e: any) {
    message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${e?.response?.data?.message || e?.message || ''}`)
  } finally {
    submitting.value = false
  }
}

// ---------- 下单分支提交 ----------
async function handleOrder(payload: any) {
  submitting.value = true
  try {
    const res = await createBackgroundCheckOrder({
      candidate_id: props.candidate.id,
      candidate_name: props.candidate.name,
      phone: props.candidate.phone,
      config_id: payload.configId,
      items: payload.items,
      channel: 'SYSTEM_ORDER',
      remark: payload.remark || '',
      package_name: payload.packageName || '',
      bg_result: payload.bgResult || '',
      contactable: payload.contactable ?? null,
      subject_snapshot: payload.subjectSnapshot || {},
      expected_onboarding_date: payload.expectedOnboardingDate || '',
      parent_order_id: props.parentOrderId,
      bg_suggestions: payload.bgSuggestions || [],
    })
    if (res.success) {
      message.success(t('pages.candidate.InitiateBgCheck.success'))
      emit('created')
      emit('update:show', false)
    } else {
      message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${res.message || ''}`)
    }
  } catch (e: any) {
    message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${e?.response?.data?.message || e?.message || ''}`)
  } finally {
    submitting.value = false
  }
}

const stepStatus = computed<'process' | 'error'>(() => (submitting.value ? 'process' : 'process'))
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="isSupplement ? t('pages.candidate.InitiateBgCheck.titleSupplement') : t('pages.candidate.InitiateBgCheck.title')"
    :style="{ width: '640px', maxWidth: '94vw' }"
    :mask-closable="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <n-space vertical :size="16">
      <n-steps :current="step" :status="stepStatus" size="small">
        <n-step :title="t('pages.candidate.InitiateBgCheck.step1')" />
        <n-step :title="hasReport ? t('pages.candidate.InitiateBgCheck.stepUpload') : t('pages.candidate.InitiateBgCheck.stepChannel')" />
      </n-steps>

      <!-- 步骤 1：是否已有背调报告 -->
      <div v-if="step === 1">
        <div class="bg-field-label required">{{ t('pages.candidate.InitiateBgCheck.hasReportLabel') }}</div>
        <n-radio-group v-model:value="hasReport">
          <n-space>
            <n-radio :value="true">{{ t('pages.candidate.InitiateBgCheck.hasReportYes') }}</n-radio>
            <n-radio :value="false">{{ t('pages.candidate.InitiateBgCheck.hasReportNo') }}</n-radio>
          </n-space>
        </n-radio-group>
        <n-alert type="info" :show-icon="false" style="margin-top: 12px">
          {{ t('pages.candidate.InitiateBgCheck.hasReportHint') }}
        </n-alert>
      </div>

      <!-- 步骤 2：上传分支（图2 添加背调信息） -->
      <BgUploadForm
        v-else-if="step === 2 && hasReport"
        ref="uploadFormRef"
        :candidate="candidate"
        :suggestions="suggestions"
        :loading-suggestions="loadingSuggestions"
        :submitting="submitting"
        @submit="handleUpload"
        @cancel="handleCancel"
      />

      <!-- 步骤 2：下单分支（图3 供应商优选） -->
      <BgOrderForm
        v-else-if="step === 2 && !hasReport"
        ref="orderFormRef"
        :candidate="candidate"
        :suppliers="suppliers"
        :loading-suppliers="loadingSuppliers"
        :submitting="submitting"
        @submit="handleOrder"
        @cancel="handleCancel"
      />
    </n-space>

    <!-- 双「下一步」Bug 修复：step1 仅一个「下一步」；step2 按 hasReport 显示上传/下单提交 -->
    <template #footer>
      <n-space justify="end">
        <n-button :disabled="submitting" @click="handleCancel">
          {{ t('pages.candidate.InitiateBgCheck.cancel') }}
        </n-button>
        <n-button v-if="step > 1" :disabled="submitting" @click="goBack">
          {{ t('pages.candidate.InitiateBgCheck.back') }}
        </n-button>
        <n-button v-if="step === 1" type="primary" :disabled="submitting" @click="goNext">
          {{ t('pages.candidate.InitiateBgCheck.next') }}
        </n-button>
        <n-button v-if="step === 2 && hasReport" type="primary" :loading="submitting" @click="onUploadSubmit">
          {{ t('pages.candidate.InitiateBgCheck.submitUpload') }}
        </n-button>
        <n-button v-if="step === 2 && !hasReport" type="primary" :loading="submitting" @click="onOrderSubmit">
          {{ t('pages.candidate.InitiateBgCheck.confirmOrder') }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped>
.bg-field-label { font-size: var(--fs-13); font-weight: 600; margin-bottom: 6px; color: var(--ink-soft); }
.bg-field-label.required::before { content: '*'; color: var(--c-error); margin-right: 4px; }
</style>

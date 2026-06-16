<script setup lang="ts">
/**
 * 面试反馈表单 - PRD G3.6
 * G19 - 历史评价预览面板
 */
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard, NForm, NFormItem, NInput, NButton, NSpace, NSelect, NAlert,
  NCheckbox, NSpin, useMessage, NTag, NDivider,
} from 'naive-ui'
import {
  submitFeedback, getInterviewHistory, type InterviewHistory,
} from '../../api/interview'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const interviewId = computed(() => String(route.params.id || route.query.interviewId || ''))
const candidateId = computed(() => String(route.query.candidateId || ''))

const form = ref<{ result: 'PASS' | 'FAIL' | null; reason: string; values: string; comprehensive: string; recommendation: string; participantFeedback: string }>({
  result: null,
  reason: '',
  values: '',
  comprehensive: '',
  recommendation: '',
  participantFeedback: '',
})

const history = ref<InterviewHistory | null>(null)
const historyLoading = ref(false)
const viewedPrevious = ref(false)
const submitting = ref(false)

const resultOptions = [
  { label: '通过 (PASS)', value: 'PASS' },
  { label: '不通过 (FAIL)', value: 'FAIL' },
]

const hasHistory = computed(() => (history.value?.total || 0) > 0)

async function loadHistory() {
  if (!candidateId.value) return
  historyLoading.value = true
  try {
    history.value = await getInterviewHistory(candidateId.value)
  } catch (e: any) {
    message.warning(`历史评价加载失败: ${e?.message || '未知错误'}`)
  } finally {
    historyLoading.value = false
  }
}

async function handleSubmit() {
  if (!form.value.result) {
    message.error('请选择结果 (PASS/FAIL)')
    return
  }
  if (hasHistory.value && !viewedPrevious.value) {
    message.warning('请勾选"我已阅读历史评价"')
    return
  }
  submitting.value = true
  try {
    const payload: any = { ...form.value, viewedPrevious: viewedPrevious.value }
    if (hasHistory.value) {
      payload.previousFeedback = history.value!.previousFeedback
    }
    const res = await submitFeedback(interviewId.value, payload)
    message.success(res.data?.prefilled ? '反馈提交成功 (已自动预填历史)' : '反馈提交成功')
    router.back()
  } catch (e: any) {
    message.error(`提交失败: ${e?.response?.data?.message || e?.message || '未知错误'}`)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<template>
  <div class="interview-feedback-form" style="max-width: 900px; margin: 0 auto; padding: 16px;">
    <n-card title="面试反馈" :bordered="false">
      <!-- G19: 历史评价预览面板 -->
      <n-spin :show="historyLoading">
        <n-alert
          v-if="hasHistory"
          type="info"
          :show-icon="false"
          title="历史评价预览 (G19 自动预填)"
          style="margin-bottom: 16px;"
        >
          <div style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">
            {{ history?.previousFeedback }}
          </div>
          <n-divider style="margin: 12px 0;" />
          <n-space>
            <n-tag :type="history!.passCount > 0 ? 'success' : 'default'">
              通过 {{ history!.passCount }} 次
            </n-tag>
            <n-tag :type="history!.failCount > 0 ? 'error' : 'default'">
              未通过 {{ history!.failCount }} 次
            </n-tag>
            <n-tag>共 {{ history!.total }} 次</n-tag>
          </n-space>
          <div style="margin-top: 12px;">
            <n-checkbox v-model:checked="viewedPrevious">
              我已阅读历史评价
            </n-checkbox>
          </div>
        </n-alert>
      </n-spin>

      <n-form label-placement="top">
        <n-form-item label="结果" required>
          <n-select
            v-model:value="form.result"
            :options="resultOptions"
            placeholder="请选择"
            style="max-width: 300px;"
          />
        </n-form-item>
        <n-form-item label="原因 / 评价">
          <n-input
            v-model:value="form.reason"
            type="textarea"
            :rows="3"
            placeholder="技术能力、沟通、综合素质等"
          />
        </n-form-item>
        <n-form-item label="价值观匹配">
          <n-input v-model:value="form.values" placeholder="可选项" />
        </n-form-item>
        <n-form-item label="综合能力">
          <n-input v-model:value="form.comprehensive" placeholder="可选项" />
        </n-form-item>
        <n-form-item label="推荐意见">
          <n-input v-model:value="form.recommendation" placeholder="可选项" />
        </n-form-item>
        <n-form-item label="面试者反馈 (候选人)">
          <n-input
            v-model:value="form.participantFeedback"
            type="textarea"
            :rows="2"
            placeholder="候选人对面试的反馈"
          />
        </n-form-item>
        <n-form-item>
          <n-space>
            <n-button type="primary" :loading="submitting" @click="handleSubmit">
              提交反馈
            </n-button>
            <n-button @click="router.back()">取消</n-button>
          </n-space>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

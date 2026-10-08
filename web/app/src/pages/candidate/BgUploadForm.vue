<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  NInput, NSelect, NDatePicker, NUpload, NText, NEmpty, NList, NListItem, useMessage,
} from 'naive-ui'
import { uploadMedia, type BgCandidate, type BgSuggestion } from '../../api/integration'

const props = defineProps<{
  candidate: BgCandidate
  suggestions: BgSuggestion[]
  loadingSuggestions?: boolean
  submitting?: boolean
}>()
const emit = defineEmits<{
  (e: 'submit', payload: any): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()
const message = useMessage()

// ---------- 表单字段 ----------
const packageName = ref('')
const bgProvider = ref('')
const bgTime = ref<number | null>(null)
const bgResult = ref<string | null>(null)
const reportUrl = ref('')
const remark = ref('')
const uploading = ref(false)
const answers = reactive<Record<string, string>>({})

const bgResultOptions = computed(() => [
  { value: 'PASS', label: t('pages.candidate.InitiateBgCheck.bgResultPass') },
  { value: 'DOUBT', label: t('pages.candidate.InitiateBgCheck.bgResultDoubt') },
  { value: 'FAIL', label: t('pages.candidate.InitiateBgCheck.bgResultFail') },
  { value: 'PENDING', label: t('pages.candidate.InitiateBgCheck.bgResultPending') },
])

const allSuggestionsAnswered = computed(() => {
  if (props.suggestions.length === 0) return true
  return props.suggestions.every((s) => (answers[s.interviewer] || '').trim())
})

// 背调人信息快照（上传分支不修编辑，直接取候选详情值）
function buildSnapshot() {
  return {
    name: props.candidate.name,
    phone: props.candidate.phone,
    id_card_no: props.candidate.idCardNo || '',
    email: props.candidate.email || '',
    position: props.candidate.position || '',
    expected_onboarding_date: props.candidate.expectedOnboardingDate || null,
  }
}

// ---------- 文件上传：先调 /media/upload/ 拿 url ----------
async function customRequest({ file, onFinish, onError }: any) {
  uploading.value = true
  try {
    const res = await uploadMedia(file.file)
    if (res && res.url) {
      reportUrl.value = res.url
      message.success(t('pages.candidate.InitiateBgCheck.uploadSuccess'))
      onFinish()
    } else {
      onError()
      message.error(t('pages.candidate.InitiateBgCheck.uploadFail'))
    }
  } catch (e: any) {
    onError()
    message.error(`${t('pages.candidate.InitiateBgCheck.failPrefix')} ${e?.response?.data?.message || e?.message || ''}`)
  } finally {
    uploading.value = false
  }
}

// ---------- 校验 + 提交（由父级 footer 按钮触发） ----------
function submit() {
  if (!packageName.value.trim()) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredPackageName'))
    return
  }
  if (!bgProvider.value.trim()) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredBgProvider'))
    return
  }
  if (bgTime.value == null) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredBgTime'))
    return
  }
  if (!bgResult.value) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredBgResult'))
    return
  }
  if (!reportUrl.value.trim()) {
    message.error(t('pages.candidate.InitiateBgCheck.requiredReport'))
    return
  }
  if (!allSuggestionsAnswered.value) {
    message.error(t('pages.candidate.InitiateBgCheck.suggestionRequired'))
    return
  }
  emit('submit', {
    packageName: packageName.value.trim(),
    bgProvider: bgProvider.value.trim(),
    bgTime: bgTime.value ? new Date(bgTime.value).toISOString() : '',
    bgResult: bgResult.value,
    reportUrl: reportUrl.value.trim(),
    remark: remark.value.trim(),
    answers: props.suggestions.map((s) => ({
      interviewer: s.interviewer,
      answer: (answers[s.interviewer] || '').trim(),
    })),
    bgSuggestions: props.suggestions.map((s) => ({
      interviewer: s.interviewer,
      interviewer_name: s.interviewerName,
      suggestion: s.suggestion,
      answer: (answers[s.interviewer] || '').trim(),
    })),
    subjectSnapshot: buildSnapshot(),
  })
}

defineExpose({ submit })
</script>

<template>
  <div>
    <n-spin :show="loadingSuggestions">
      <div class="bg-form">
        <!-- 背调人信息：姓名/手机号/应聘职位/邮箱集中一处（与下单分支一致，无重复头部） -->
        <section class="bgu-block">
          <header class="bgu-sec">
            <span class="bgu-sec__idx">1</span>
            <span class="bgu-sec__title">{{ t('pages.candidate.InitiateBgCheck.subjectInfo') }}</span>
            <span class="bgu-sec__hint">{{ t('pages.candidate.InitiateBgCheck.bgSubject') }}</span>
          </header>
          <div class="bgu-grid">
            <div class="bgu-field">
              <span class="bgu-field__label">{{ t('pages.candidate.CandidateDetail.s154') }}</span>
              <span class="bgu-field__static">{{ candidate.name || '—' }}</span>
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label">{{ t('pages.candidate.CandidateDetail.s103') }}</span>
              <span class="bgu-field__static">{{ candidate.phone || '—' }}</span>
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label">{{ t('pages.candidate.InitiateBgCheck.position') }}</span>
              <span class="bgu-field__static">{{ candidate.position || '—' }}</span>
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label">{{ t('pages.candidate.CandidateDetail.s107') }}</span>
              <span class="bgu-field__static">{{ candidate.email || '—' }}</span>
            </div>
          </div>
        </section>

        <!-- 背调报告信息：前四个字段一行两列 -->
        <section class="bgu-block">
          <header class="bgu-sec">
            <span class="bgu-sec__idx">2</span>
            <span class="bgu-sec__title">{{ t('pages.candidate.InitiateBgCheck.reportInfo') }}</span>
          </header>
          <div class="bgu-grid">
            <div class="bgu-field">
              <span class="bgu-field__label bgu-req">{{ t('pages.candidate.InitiateBgCheck.packageName') }}</span>
              <n-input
                v-model:value="packageName"
                :placeholder="t('pages.candidate.InitiateBgCheck.packageNamePlaceholder')"
                :disabled="submitting"
              />
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label bgu-req">{{ t('pages.candidate.InitiateBgCheck.bgProvider') }}</span>
              <n-input
                v-model:value="bgProvider"
                :placeholder="t('pages.candidate.InitiateBgCheck.bgProviderPlaceholder')"
                :disabled="submitting"
              />
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label bgu-req">{{ t('pages.candidate.InitiateBgCheck.bgTime') }}</span>
              <n-date-picker
                v-model:value="bgTime"
                type="date"
                :placeholder="t('pages.candidate.InitiateBgCheck.bgTimePlaceholder')"
                :disabled="submitting"
                style="width: 100%"
              />
            </div>
            <div class="bgu-field">
              <span class="bgu-field__label bgu-req">{{ t('pages.candidate.InitiateBgCheck.bgResult') }}</span>
              <n-select
                v-model:value="bgResult"
                :options="bgResultOptions"
                :placeholder="t('pages.candidate.InitiateBgCheck.bgResultPlaceholder')"
                :disabled="submitting"
              />
            </div>
          </div>
        </section>

        <!-- 报告上传 + 备注：整行 -->
        <section class="bgu-block">
          <header class="bgu-sec">
            <span class="bgu-sec__idx">3</span>
            <span class="bgu-sec__title bgu-req">{{ t('pages.candidate.InitiateBgCheck.reportUpload') }}</span>
          </header>
          <n-upload
            :max="1"
            :custom-request="customRequest"
            :disabled="submitting || uploading"
          >
            <n-button :disabled="submitting || uploading">
              {{ t('pages.candidate.InitiateBgCheck.uploadFile') }}
            </n-button>
          </n-upload>
          <n-text depth="3" style="font-size: 12px">{{ t('pages.candidate.InitiateBgCheck.reportUploadHint') }}</n-text>
          <n-input
            v-model:value="reportUrl"
            :placeholder="t('pages.candidate.InitiateBgCheck.reportUrlPlaceholder')"
            :disabled="submitting"
            style="margin-top: 8px"
          />
        </section>

        <!-- 订单备注 / 背调建议：整行 -->
        <section class="bgu-block">
          <header class="bgu-sec">
            <span class="bgu-sec__idx">4</span>
            <span class="bgu-sec__title">{{ t('pages.candidate.InitiateBgCheck.remark') }}</span>
          </header>
          <n-input
            v-model:value="remark"
            type="textarea"
            :rows="2"
            :maxlength="200"
            show-count
            :placeholder="t('pages.candidate.InitiateBgCheck.remarkPlaceholder')"
            :disabled="submitting"
          />
        </section>
      </div>

      <!-- 背调建议问答题（按面试官） -->
      <div class="bg-field-label" style="margin-top: 16px">
        {{ t('pages.candidate.InitiateBgCheck.suggestionsTitle') }}
        <span v-if="loadingSuggestions" class="bg-muted">{{ t('pages.candidate.InitiateBgCheck.loading') }}</span>
      </div>
      <n-empty v-if="!loadingSuggestions && suggestions.length === 0" :description="t('pages.candidate.InitiateBgCheck.noSuggestions')" />
      <n-list v-else bordered style="margin-top: 4px">
        <n-list-item v-for="s in suggestions" :key="s.interviewer">
          <div class="bg-q">
            <div class="bg-q__ask">
              <b>{{ s.interviewerName }}</b>：{{ s.suggestion }}
            </div>
            <n-input
              v-model:value="answers[s.interviewer]"
              type="textarea"
              :rows="2"
              :placeholder="t('pages.candidate.InitiateBgCheck.answerPlaceholder')"
              :disabled="submitting"
            />
          </div>
        </n-list-item>
      </n-list>
    </n-spin>
  </div>
</template>

<style scoped>
.bg-field-label { font-size: var(--fs-13); font-weight: 600; margin-bottom: 6px; color: var(--ink-soft); }
.bg-field-label.required::before { content: '*'; color: var(--c-error); margin-right: 4px; }
.bg-muted { font-size: var(--fs-13); color: var(--ink-faint); font-weight: 400; margin-left: 8px; }
.bg-q__ask { font-size: var(--fs-13); margin-bottom: 6px; line-height: 1.5; }

/* ===== 分区结构（与下单分支 BgOrderForm 视觉一致） ===== */
.bg-form { display: flex; flex-direction: column; gap: var(--space-5); }
.bgu-block { display: flex; flex-direction: column; gap: var(--space-3); }
.bgu-sec { display: flex; align-items: center; gap: var(--space-2); }
.bgu-sec__idx {
  flex: none;
  width: 18px; height: 18px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: var(--radius-pill);
  background: var(--brand);
  color: var(--on-brand);
  font-size: var(--fs-12); font-weight: 700; line-height: 1;
  font-variant-numeric: tabular-nums;
}
.bgu-sec__title { font-size: var(--fs-14); font-weight: 700; color: var(--ink); letter-spacing: .01em; }
.bgu-sec__hint { font-size: var(--fs-12); color: var(--ink-faint); font-weight: 400; }
.bgu-req::before { content: '*'; color: var(--c-error); margin-right: 3px; }

.bgu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3) var(--space-4); }
.bgu-field { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
.bgu-field__label { font-size: var(--fs-12); font-weight: 600; color: var(--ink-soft); }
.bgu-field__static {
  font-size: var(--fs-14); font-weight: 600; color: var(--ink);
  padding: 5px 0; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

@media (max-width: 560px) {
  .bgu-grid { grid-template-columns: 1fr; }
}
</style>

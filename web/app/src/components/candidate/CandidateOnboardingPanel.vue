<template>
  <div class="candidate-onboarding-panel">
    <div class="onboarding-toolbar">
      <n-button size="small" :loading="loading" @click="loadOnboardings">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        {{ t('pages.candidate.CandidateDetail.s259') }}
      </n-button>
      <n-tag v-if="loadError" type="error" :bordered="false" size="small">{{ loadError }}</n-tag>
    </div>

    <n-spin :show="loading">
      <div v-if="onboardings.length > 0" class="onboarding-list">
        <n-card v-for="o in onboardings" :key="o.id" size="small" :bordered="true" class="onboarding-card">
          <div class="onboarding-head">
            <div class="onboarding-head-left">
              <span class="onboarding-name">{{ o.candidateName || o.positionTitle || o.id }}</span>
              <n-tag :type="onboardingStateColor(o.state)" :bordered="false" size="small">
                {{ onboardingStateLabel(o) }}
              </n-tag>
            </div>
            <div class="onboarding-head-right">
              <template v-if="availableActions(o).length > 0">
                <n-button
                  size="tiny"
                  type="primary"
                  :loading="actingId === o.id"
                  @click="runAction(o, availableActions(o)[0])"
                >
                  {{ actionLabel(availableActions(o)[0]) }}
                </n-button>
                <n-dropdown
                  v-if="availableActions(o).length > 1"
                  :options="dropdownOptions(o)"
                  trigger="click"
                  @select="(k: string) => runAction(o, k)"
                >
                  <n-button size="tiny" quaternary :loading="actingId === o.id">
                    {{ t('pages.candidate.CandidateDetail.s266') }}
                  </n-button>
                </n-dropdown>
              </template>
              <n-text v-else depth="3" style="font-size: var(--fs-12)">
                {{ t('pages.candidate.CandidateDetail.s267') }}
              </n-text>
            </div>
          </div>

          <n-grid :cols="2" :x-gap="12" :y-gap="8" responsive="screen" class="onboarding-fields">
            <n-gi>
              <div class="onboarding-field">
                <span class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s262') }}</span>
                <span class="onboarding-field-value">{{ o.positionTitle || '—' }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="onboarding-field">
                <span class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s322') }}</span>
                <span class="onboarding-field-value">{{ formatDate(o.startDate) }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="onboarding-field">
                <span class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s323') }}</span>
                <span class="onboarding-field-value">{{ formatDate(o.actualStartDate) }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="onboarding-field">
                <span class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s324') }}</span>
                <span class="onboarding-field-value">{{ formatDate(o.probationEndDate) }}</span>
              </div>
            </n-gi>
          </n-grid>

          <!-- 转正结果 / 时间 -->
          <div v-if="o.regularizationResult || o.regularizationAt" class="onboarding-regularize">
            <span class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s326') }}</span>
            <span class="onboarding-field-value">
              {{ o.regularizationResult || '—' }}<template v-if="o.regularizationAt"> · {{ formatDateTime(o.regularizationAt) }}</template>
            </span>
          </div>

          <!-- 入职待办清单 -->
          <div v-if="normalizeTodo(o.todoList).length > 0" class="onboarding-todo">
            <div class="onboarding-field-label">{{ t('pages.candidate.CandidateDetail.s327') }}</div>
            <ul class="todo-list">
              <li v-for="(item, i) in normalizeTodo(o.todoList)" :key="i" :class="{ done: item.done }">
                <n-icon v-if="item.done" :component="CheckmarkDoneOutline" size="14" class="todo-check" />
                <n-icon v-else :component="EllipseOutline" size="14" class="todo-check todo-pending" />
                <span>{{ item.text }}</span>
              </li>
            </ul>
          </div>
        </n-card>
      </div>

      <n-empty v-else-if="!loading" :description="t('pages.candidate.CandidateDetail.s321')" style="margin: 24px 0" />
    </n-spin>

    <!-- 延期：选择新的入职日期 -->
    <n-modal
      v-model:show="delay.show"
      preset="dialog"
      :title="t('pages.candidate.CandidateDetail.s338')"
      style="width: 480px; max-width: 90vw"
      :mask-closable="false"
      :close-on-esc="false"
    >
      <n-form :model="delay" label-placement="left" :label-width="100">
        <n-form-item :label="t('pages.candidate.CandidateDetail.s337')">
          <n-date-picker
            v-model:value="delay.dateTs"
            type="date"
            clearable
            style="width: 100%"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="delay.show = false">{{ t('reasonLibrary.common.cancel') }}</n-button>
          <n-button type="primary" :loading="delay.loading" :disabled="!delay.dateTs" @click="confirmDelay">
            {{ t('pages.candidate.CandidateDetail.s270') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 转正：选择结果 -->
    <n-modal
      v-model:show="regularize.show"
      preset="dialog"
      :title="t('pages.candidate.CandidateDetail.s339')"
      style="width: 420px; max-width: 90vw"
      :mask-closable="false"
      :close-on-esc="false"
    >
      <n-form :model="regularize" label-placement="left" :label-width="100">
        <n-form-item :label="t('pages.candidate.CandidateDetail.s325')">
          <n-select
            v-model:value="regularize.result"
            :options="[
              { label: t('pages.candidate.CandidateDetail.s340'), value: 'PASS' },
              { label: t('pages.candidate.CandidateDetail.s341'), value: 'FAIL' },
            ]"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="regularize.show = false">{{ t('reasonLibrary.common.cancel') }}</n-button>
          <n-button type="primary" :loading="regularize.loading" @click="confirmRegularize">
            {{ t('pages.candidate.CandidateDetail.s270') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * 候选人详情页 · 待入职（Onboarding）页签
 *
 * 背景（2026-10-21）：原独立的「待入职」全局列表页被移除，待入职功能并入候选人管理，
 * 作为详情页 offer 之后的独立页签呈现（按 candidate 过滤）。
 *
 * 契约要点（详见 api/onboarding.ts 头部说明）：
 *  - 状态字段为后端 `state`（+ stateDisplay），共 7 态；
 *  - 流转入参为 `{action, new_date?, result?}`；delay 需日期、regularize 可带结果；
 *  - 可执行动作严格按后端 FSM 边收紧，终态不臆造动作。
 */
import { ref, computed, watch, onMounted } from 'vue'
import {
  NButton, NSpace, NTag, NIcon, NCard, NGrid, NGi, NSpin, NEmpty, NText, NDropdown,
  NModal, NForm, NFormItem, NDatePicker, NSelect, useMessage, useDialog,
} from 'naive-ui'
import { RefreshOutline, CheckmarkDoneOutline, EllipseOutline } from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import {
  listOnboardingsByCandidate, transitionOnboarding,
  onboardingStateLabel, onboardingStateColor, onboardingActionsFor,
  isParamAction, ONBOARDING_ACTION_LABEL, ONBOARDING_ACTION,
  type Onboarding,
} from '../../api/onboarding'

const props = defineProps<{
  candidateId: string
}>()

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

const onboardings = ref<Onboarding[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
const actingId = ref<string>('')

const delay = ref({ show: false, loading: false, dateTs: null as number | null, onboardingId: '' })
const regularize = ref({ show: false, loading: false, result: 'PASS', onboardingId: '' })

async function loadOnboardings() {
  const cid = props.candidateId
  if (!cid) {
    onboardings.value = []
    return
  }
  loading.value = true
  loadError.value = null
  try {
    const res: any = await listOnboardingsByCandidate(cid, { page: 1, pageSize: 50 })
    // 兼容 {data:[...]} 与 {items:[...]} 两种信封（后端为分页结构）
    onboardings.value = (res?.items ?? res?.data ?? []) as Onboarding[]
  } catch (e: any) {
    loadError.value = e?.message || t('pages.candidate.CandidateDetail.s275')
    onboardings.value = []
  } finally {
    loading.value = false
  }
}

function availableActions(o: Onboarding): string[] {
  return onboardingActionsFor(o.state)
}

function actionLabel(action: string): string {
  return ONBOARDING_ACTION_LABEL[action] || action
}

function dropdownOptions(o: Onboarding): Array<{ label: string; key: string }> {
  // 首个动作已作为主按钮，下拉展示其余
  return availableActions(o).slice(1).map((a) => ({ label: actionLabel(a), key: a }))
}

interface TodoItem { text: string; done: boolean }
function normalizeTodo(list?: Array<string | { text: string; done?: boolean }>): TodoItem[] {
  if (!Array.isArray(list)) return []
  return list.map((it) => {
    if (typeof it === 'string') return { text: it, done: false }
    return { text: it.text, done: !!it.done }
  })
}

async function runAction(o: Onboarding, action: string) {
  if (action === ONBOARDING_ACTION.DELAY) {
    delay.value = { show: true, loading: false, dateTs: null, onboardingId: o.id }
    return
  }
  if (action === ONBOARDING_ACTION.REGULARIZE) {
    regularize.value = { show: true, loading: false, result: 'PASS', onboardingId: o.id }
    return
  }
  // 简单动作：二次确认后执行
  try {
    await dialog.warning({
      title: t('pages.candidate.CandidateDetail.s272'),
      content: t('pages.candidate.CandidateDetail.s336'),
      positiveText: t('pages.candidate.CandidateDetail.s270'),
      negativeText: t('reasonLibrary.common.cancel'),
    })
  } catch {
    return
  }
  await doTransition(o.id, action)
}

async function confirmDelay() {
  if (!delay.value.dateTs) {
    message.warning(t('pages.candidate.CandidateDetail.s337'))
    return
  }
  const newDate = new Date(delay.value.dateTs).toISOString().slice(0, 10)
  const id = delay.value.onboardingId
  delay.value.loading = true
  try {
    await doTransition(id, ONBOARDING_ACTION.DELAY, { newDate })
    delay.value.show = false
  } finally {
    delay.value.loading = false
  }
}

async function confirmRegularize() {
  const id = regularize.value.onboardingId
  regularize.value.loading = true
  try {
    await doTransition(id, ONBOARDING_ACTION.REGULARIZE, { result: regularize.value.result })
    regularize.value.show = false
  } finally {
    regularize.value.loading = false
  }
}

async function doTransition(onboardingId: string, action: string, payload?: { newDate?: string; result?: string }) {
  actingId.value = onboardingId
  try {
    await transitionOnboarding(onboardingId, action, payload)
    message.success(t('pages.candidate.CandidateDetail.s274'))
    await loadOnboardings()
  } catch (e: any) {
    message.error(e?.message || t('pages.candidate.CandidateDetail.s275'))
  } finally {
    actingId.value = ''
  }
}

function formatDate(v?: string | null): string {
  if (!v) return '—'
  return v.slice(0, 10)
}

function formatDateTime(v?: string | null): string {
  if (!v) return '—'
  return v.slice(0, 16).replace('T', ' ')
}

watch(() => props.candidateId, () => loadOnboardings())
onMounted(() => loadOnboardings())

defineExpose({ reload: loadOnboardings })
</script>

<style scoped>
.candidate-onboarding-panel { padding: 4px 0; }
.onboarding-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.onboarding-list { display: flex; flex-direction: column; gap: 12px; }
.onboarding-card { border-radius: 12px; }
.onboarding-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.onboarding-head-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.onboarding-head-right { display: flex; align-items: center; gap: 8px; }
.onboarding-name { font-weight: 600; font-size: var(--fs-14); color: var(--ink); }
.onboarding-fields { margin-top: 12px; }
.onboarding-field { display: flex; flex-direction: column; gap: 2px; }
.onboarding-field-label { font-size: var(--fs-12); color: var(--ink-faint); }
.onboarding-field-value { font-size: var(--fs-14); color: var(--ink); }
.onboarding-regularize { margin-top: 10px; display: flex; gap: 8px; align-items: baseline; }
.onboarding-todo { margin-top: 12px; }
.todo-list { list-style: none; padding: 0; margin: 6px 0 0; display: flex; flex-direction: column; gap: 4px; }
.todo-list li { display: flex; align-items: center; gap: 6px; font-size: var(--fs-13); color: var(--ink-soft); }
.todo-list li.done { color: var(--ink-faint); text-decoration: line-through; }
.todo-check { color: var(--c-success); }
.todo-check.todo-pending { color: var(--ink-faint); }
</style>

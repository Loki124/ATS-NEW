<template>
  <div class="candidate-offer-panel">
    <div class="offer-toolbar">
      <n-button size="small" :loading="loading" @click="loadOffers">
        <template #icon><n-icon :component="RefreshOutline" /></template>
        {{ t('pages.candidate.CandidateDetail.s259') }}
      </n-button>
      <n-tag v-if="loadError" type="error" :bordered="false" size="small">{{ loadError }}</n-tag>
    </div>

    <n-spin :show="loading">
      <div v-if="offers.length > 0" class="offer-list">
        <n-card v-for="o in offers" :key="o.id" size="small" :bordered="true" class="offer-card">
          <div class="offer-head">
            <div class="offer-head-left">
              <span class="offer-code">{{ o.code || o.id }}</span>
              <n-tag :type="offerStateColor(o.state)" :bordered="false" size="small">
                {{ offerStateLabel(o) }}
              </n-tag>
              <span v-if="o.level" class="offer-level">{{ t('pages.candidate.CandidateDetail.s261') }} {{ o.level }}</span>
            </div>
            <div class="offer-head-right">
              <template v-if="availableActions(o).length > 0">
                <n-button
                  size="tiny"
                  type="primary"
                  v-if="availableActions(o)[0] && !isDangerousAction(availableActions(o)[0])"
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
                <n-button
                  v-else-if="availableActions(o).length === 1 && isDangerousAction(availableActions(o)[0])"
                  size="tiny"
                  type="error"
                  :loading="actingId === o.id"
                  @click="runAction(o, availableActions(o)[0])"
                >
                  {{ actionLabel(availableActions(o)[0]) }}
                </n-button>
              </template>
              <n-text v-else depth="3" style="font-size: var(--fs-12)">
                {{ t('pages.candidate.CandidateDetail.s267') }}
              </n-text>
            </div>
          </div>

          <n-grid :cols="2" :x-gap="12" :y-gap="8" responsive="screen" class="offer-fields">
            <n-gi>
              <div class="offer-field">
                <span class="offer-field-label">{{ t('pages.candidate.CandidateDetail.s262') }}</span>
                <span class="offer-field-value">{{ o.positionTitle || '—' }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="offer-field">
                <span class="offer-field-label">{{ t('pages.candidate.CandidateDetail.s263') }}</span>
                <span class="offer-field-value">{{ formatSalary(o) }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="offer-field">
                <span class="offer-field-label">{{ t('pages.candidate.CandidateDetail.s264') }}</span>
                <span class="offer-field-value">{{ formatDate(o.startDate) }}</span>
              </div>
            </n-gi>
            <n-gi>
              <div class="offer-field">
                <span class="offer-field-label">{{ t('pages.candidate.CandidateDetail.s265') }}</span>
                <span class="offer-field-value">{{ formatDate(o.expireDate) }}</span>
              </div>
            </n-gi>
          </n-grid>
        </n-card>
      </div>

      <n-empty v-else-if="!loading" :description="t('pages.candidate.CandidateDetail.s260')" style="margin: 24px 0" />
    </n-spin>

    <!-- 危险动作：填写原因 + 二次确认 -->
    <n-modal
      v-model:show="danger.show"
      preset="dialog"
      :title="danger.title"
      style="width: 480px; max-width: 90vw"
      :mask-closable="false"
      :close-on-esc="false"
    >
      <n-form :model="danger" label-placement="left" :label-width="80">
        <n-form-item :label="t('pages.candidate.CandidateDetail.s268')">
          <n-input
            v-model:value="danger.reason"
            type="textarea"
            :rows="3"
            :placeholder="t('pages.candidate.CandidateDetail.s269')"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="danger.show = false">{{ t('reasonLibrary.common.cancel') }}</n-button>
          <n-button type="error" :loading="danger.loading" @click="confirmDangerAction">
            {{ t('pages.candidate.CandidateDetail.s270') }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
/**
 * 候选人详情页 · Offer 页签
 *
 * 背景（2026-10-14）：原「Offer管理」一级菜单被移除，Offer 功能并入候选人管理。
 * 数据源：GET /offers/?candidate=<id>（后端 filterset_fields 含 candidate，无需改后端）。
 *
 * 契约要点（详见 api/offer.ts 头部说明）：
 *  - 状态字段为后端 `state`（+ stateDisplay），不是 offerStatus；
 *  - 流转入参为 `{action}`，取值 submit_approval/approve/reject/send/accept/
 *    negotiate/candidate_reject/onboarded；
 *  - 可执行动作严格按后端 FSM 边收紧，终态不臆造动作。
 */
import { ref, watch, onMounted } from 'vue'
import { NButton, NSpace, NTag, NIcon, NCard, NGrid, NGi, NSpin, NEmpty, NText, NDropdown, NModal, NForm, NFormItem, NInput, useMessage, useDialog } from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { useI18n } from 'vue-i18n'
import {
  listOffersByCandidate, transitionOffer,
  offerStateLabel, offerStateColor, offerActionsFor,
  isDangerousAction, OFFER_ACTION_LABEL,
  type Offer,
} from '../../api/offer'

const props = defineProps<{
  candidateId: string
}>()

const { t } = useI18n()
const message = useMessage()
const dialog = useDialog()

const offers = ref<Offer[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
const actingId = ref<string>('')

const danger = ref({
  show: false, loading: false, title: '', reason: '',
  offerId: '', action: '',
})

async function loadOffers() {
  const cid = props.candidateId
  if (!cid) {
    offers.value = []
    return
  }
  loading.value = true
  loadError.value = null
  try {
    const res: any = await listOffersByCandidate(cid, { page: 1, pageSize: 50 })
    // 兼容 {data:[...]} 与 {items:[...]} 两种信封（后端为分页结构）
    offers.value = (res?.items ?? res?.data ?? []) as Offer[]
  } catch (e: any) {
    loadError.value = e?.message || t('pages.candidate.CandidateDetail.s271')
    offers.value = []
  } finally {
    loading.value = false
  }
}

function availableActions(o: Offer): string[] {
  return offerActionsFor(o.state)
}

function actionLabel(action: string): string {
  return OFFER_ACTION_LABEL[action] || action
}

function dropdownOptions(o: Offer): Array<{ label: string; key: string }> {
  return availableActions(o).map((a) => ({ label: actionLabel(a), key: a }))
}

async function runAction(o: Offer, action: string) {
  if (isDangerousAction(action)) {
    danger.value = {
      show: true, loading: false, reason: '',
      offerId: o.id, action,
      title: `${t('pages.candidate.CandidateDetail.s268')} · ${actionLabel(action)}`,
    }
    return
  }
  await doTransition(o.id, action)
}

async function confirmDangerAction() {
  if (!danger.value.reason.trim()) {
    message.warning(t('pages.candidate.CandidateDetail.s269'))
    return
  }
  const { offerId, action } = danger.value
  try {
    await dialog.warning({
      title: t('pages.candidate.CandidateDetail.s272'),
      content: t('pages.candidate.CandidateDetail.s273'),
      positiveText: t('pages.candidate.CandidateDetail.s270'),
      negativeText: t('reasonLibrary.common.cancel'),
    })
  } catch {
    return
  }
  danger.value.loading = true
  try {
    await doTransition(offerId, action, danger.value.reason)
    danger.value.show = false
    danger.value.reason = ''
  } finally {
    danger.value.loading = false
  }
}

async function doTransition(offerId: string, action: string, reason?: string) {
  actingId.value = offerId
  try {
    await transitionOffer(offerId, action, reason)
    message.success(t('pages.candidate.CandidateDetail.s274'))
    await loadOffers()
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

function formatSalary(o: Offer): string {
  if (o.salary === null || o.salary === undefined || o.salary === '') return '—'
  const cur = o.salaryCurrency || 'CNY'
  return `${cur === 'CNY' ? '¥' : cur} ${o.salary}`
}

watch(() => props.candidateId, () => loadOffers())
onMounted(() => loadOffers())

defineExpose({ reload: loadOffers })
</script>

<style scoped>
.candidate-offer-panel { padding: 4px 0; }
.offer-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.offer-list { display: flex; flex-direction: column; gap: 12px; }
.offer-card { border-radius: 12px; }
.offer-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.offer-head-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.offer-head-right { display: flex; align-items: center; gap: 8px; }
.offer-code { font-family: var(--font-mono, monospace); font-size: var(--fs-12); color: var(--ink-soft); }
.offer-level { font-size: var(--fs-12); color: var(--ink-faint); }
.offer-fields { margin-top: 12px; }
.offer-field { display: flex; flex-direction: column; gap: 2px; }
.offer-field-label { font-size: var(--fs-12); color: var(--ink-faint); }
.offer-field-value { font-size: var(--fs-14); color: var(--ink); }
</style>
<template>
  <div class="page-container process-stage-rules">
<div class="page-body">
    <div class="page-header">
      <div>
        <n-space align="center">
          <n-button text @click="$router.back()">
            <template #icon><n-icon :component="ArrowBackOutline" /></template>
            {{ t('pages.settings.ProcessStageRules.s1') }}
          </n-button>
          <h2 class="page-title">{{ processName }} - {{ stageName }} - {{ t('pages.settings.ProcessStageRules.s68') }}</h2>
        </n-space>
        <p class="page-subtitle">{{ t('pages.settings.ProcessStageRules.s2') }}</p>
      </div>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 3: 自动归档（仅 process 级别） -->
      <n-tab-pane v-if="!linkId" name="archive" :tab="t('pages.settings.ProcessStageRules.s3')">
        <n-spin :show="archiveLoading">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
            {{ t('pages.settings.ProcessStageRules.s4') }}
          </n-alert>
          <n-form label-placement="top" class="psr-form-max">
            <!-- 邀约不成功 -->
            <n-form-item :label="t('pages.settings.ProcessStageRules.s5')">
              <n-space>
                <n-switch v-model:value="archiveForms.invite.enabled" @update:value="(_v: boolean) => saveArchive('INVITE_FAIL', archiveForms.invite)" />
                <n-input v-model:value="archiveForms.invite.failTags" :placeholder="t('pages.settings.ProcessStageRules.s6')" :disabled="!archiveForms.invite.enabled" style="width: 240px" />
                <n-input-number v-model:value="archiveForms.invite.maxAttempts" :min="1" :max="10" :placeholder="t('pages.settings.ProcessStageRules.s7')" :disabled="!archiveForms.invite.enabled" class="psr-input-days" />
              </n-space>
            </n-form-item>

            <!-- Offer 不通过 -->
            <n-form-item :label="t('pages.settings.ProcessStageRules.s8')">
              <n-space>
                <n-switch v-model:value="archiveForms.offer.enabled" @update:value="(_v: boolean) => saveArchive('OFFER_FAIL', archiveForms.offer)" />
                <n-text v-if="archiveForms.offer.enabled" type="success" size="small">{{ t('pages.settings.ProcessStageRules.s9') }}</n-text>
                <n-text v-else depth="3" size="small">{{ t('pages.settings.ProcessStageRules.s10') }}</n-text>
              </n-space>
            </n-form-item>

            <!-- 评估/筛选/面试不通过 -->
            <n-form-item :label="t('pages.settings.ProcessStageRules.s11')">
              <n-space>
                <n-switch v-model:value="archiveForms.eval.enabled" @update:value="(_v: boolean) => saveArchive('EVAL_FAIL', archiveForms.eval)" />
                <n-input v-model:value="archiveForms.eval.failTags" :placeholder="t('pages.settings.ProcessStageRules.s12')" :disabled="!archiveForms.eval.enabled" style="width: 320px" />
                <n-select
                  v-model:value="archiveForms.eval.executeTiming"
                  :options="[{label: t('pages.settings.ProcessStageRules.s19'), value:'IMMEDIATE'},{label: t('pages.settings.ProcessStageRules.s70'), value:'DELAYED'}]"
                  :disabled="!archiveForms.eval.enabled"
                  style="width: 140px"
                />
                <n-input-number v-model:value="archiveForms.eval.delayDays" :min="1" :max="15" :disabled="!archiveForms.eval.enabled || archiveForms.eval.executeTiming !== 'DELAYED'" class="psr-input-days-sm" />
              </n-space>
            </n-form-item>

            <!-- 超时未分配 -->
            <n-form-item :label="t('pages.settings.ProcessStageRules.s13')">
              <n-space>
                <n-switch v-model:value="archiveForms.timeout.enabled" @update:value="(_v: boolean) => saveArchive('TIMEOUT_UNASSIGNED', archiveForms.timeout)" />
                <n-input-number v-model:value="archiveForms.timeout.timeoutDays" :min="1" :max="30" :disabled="!archiveForms.timeout.enabled" class="psr-input-days" />
                <n-text depth="3" size="small">{{ t('pages.settings.ProcessStageRules.s14') }}</n-text>
              </n-space>
            </n-form-item>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- Tab 1: 阶段规则 -->
      <n-tab-pane name="rule" :tab="t('pages.settings.ProcessStageRules.s15')">
        <n-spin :show="ruleLoading">
          <n-form :model="ruleForm" label-placement="top" class="psr-form-max">
            <n-form-item :label="t('pages.settings.ProcessStageRules.s16')">
              <n-select v-model:value="ruleForm.autoAdvanceType" :options="autoAdvanceOptions" />
            </n-form-item>

            <n-form-item v-if="ruleForm.autoAdvanceType !== 'NONE'" :label="t('pages.settings.ProcessStageRules.s17')">
              <n-radio-group v-model:value="ruleForm.autoAdvanceTiming">
                <n-space>
                  <n-radio value="NONE">{{ t('pages.settings.ProcessStageRules.s18') }}</n-radio>
                  <n-radio value="IMMEDIATE">{{ t('pages.settings.ProcessStageRules.s19') }}</n-radio>
                  <n-radio value="DELAYED">{{ t('pages.settings.ProcessStageRules.s20') }}</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item v-if="ruleForm.autoAdvanceTiming === 'DELAYED'" :label="t('pages.settings.ProcessStageRules.s21')">
              <n-input-number v-model:value="ruleForm.autoAdvanceDays" :min="1" :max="15" />
            </n-form-item>

            <n-divider title-placement="left">{{ t('pages.settings.ProcessStageRules.s22') }}</n-divider>

            <n-form-item :label="t('pages.settings.ProcessStageRules.s23')">
              <n-radio-group v-model:value="ruleForm.defaultHandlerType">
                <n-space>
                  <n-radio value="FROM_DEMAND">{{ t('pages.settings.ProcessStageRules.s24') }}</n-radio>
                  <n-radio value="FROM_POSITION">{{ t('pages.settings.ProcessStageRules.s25') }}</n-radio>
                  <n-radio value="CUSTOM">{{ t('pages.settings.ProcessStageRules.s26') }}</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item v-if="ruleForm.defaultHandlerType === 'CUSTOM'" :label="t('pages.settings.ProcessStageRules.s27')">
              <n-select
                v-model:value="ruleForm.defaultHandlerUserIds"
                multiple
                filterable
                :options="userOptions"
                :placeholder="t('pages.settings.ProcessStageRules.s28')"
                :loading="userLoading"
              />
            </n-form-item>

            <n-form-item v-if="ruleForm.defaultHandlerType !== 'CUSTOM'" :label="t('pages.settings.ProcessStageRules.s29')">
              <n-select
                v-model:value="ruleForm.defaultHandlerFields"
                multiple
                :options="handlerFieldOptions[ruleForm.defaultHandlerType] || []"
                :placeholder="t('pages.settings.ProcessStageRules.s30')"
              />
            </n-form-item>

            <n-divider title-placement="left">{{ t('pages.settings.ProcessStageRules.s31') }}</n-divider>

            <n-form-item :label="t('pages.settings.ProcessStageRules.s32')">
              <n-input-number v-model:value="ruleForm.timeLimit" :min="0" :placeholder="t('pages.settings.ProcessStageRules.s33')" style="width: 200px" />
            </n-form-item>

            <n-form-item v-if="ruleForm.timeLimit" :label="t('pages.settings.ProcessStageRules.s34')">
              <n-radio-group v-model:value="ruleForm.timeLimitScope">
                <n-space>
                  <n-radio value="NEW_ONLY">{{ t('pages.settings.ProcessStageRules.s35') }}</n-radio>
                  <n-radio value="ALL">{{ t('pages.settings.ProcessStageRules.s36') }}</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-divider v-if="isInterviewType" title-placement="left">{{ t('pages.settings.ProcessStageRules.s37') }}</n-divider>

            <n-form-item v-if="isInterviewType" :label="t('pages.settings.ProcessStageRules.s38')">
              <n-select
                v-model:value="ruleForm.interviewRoundIds"
                multiple
                :options="roundOptions"
                :loading="roundLoading"
                :placeholder="t('pages.settings.ProcessStageRules.s39')"
              />
            </n-form-item>

            <n-space justify="end" class="psr-actions-top">
              <n-button type="primary" :loading="ruleSaving" @click="saveRule">{{ t('pages.settings.ProcessStageRules.s40') }}</n-button>
            </n-space>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- Tab 2: 进入条件 -->
      <n-tab-pane name="condition" :tab="t('pages.settings.ProcessStageRules.s41')">
        <n-spin :show="condLoading">
          <n-form :model="condForm" label-placement="top" class="psr-form-max">
            <n-form-item :label="t('pages.settings.ProcessStageRules.s42')">
              <n-radio-group v-model:value="condForm.matchType">
                <n-space>
                  <n-radio value="ALL">{{ t('pages.settings.ProcessStageRules.s43') }}</n-radio>
                  <n-radio value="ANY">{{ t('pages.settings.ProcessStageRules.s44') }}</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item :label="t('pages.settings.ProcessStageRules.s45')">
              <n-select v-model:value="condForm.conditionType" :options="conditionTypeOptions" />
            </n-form-item>

            <n-form-item :label="t('pages.settings.ProcessStageRules.s46')">
              <n-input v-model:value="condForm.prompt" type="textarea" :rows="3" :placeholder="t('pages.settings.ProcessStageRules.s47')" />
            </n-form-item>

            <n-divider title-placement="left">{{ t('pages.settings.ProcessStageRules.s48') }}</n-divider>

            <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
              {{ t('pages.settings.ProcessStageRules.s71') }}<strong>{{ rootItems.length }}</strong>{{ t('pages.settings.ProcessStageRules.s72') }}3{{ t('pages.settings.ProcessStageRules.s73') }}
            </n-alert>

            <ConditionTreeEditor
              v-model="condForm.items"
              :all-stages="allStages"
              :all-link-ids="allLinkIds"
            />

            <n-space justify="end" class="psr-actions-top">
              <n-button type="primary" :loading="condSaving" @click="saveCondition">{{ t('pages.settings.ProcessStageRules.s49') }}</n-button>
            </n-space>
          </n-form>
        </n-spin>
      </n-tab-pane>
    </n-tabs>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue'
import { useMessage, NSpace, NButton, NSelect, NInputNumber, NRadio, NRadioGroup, NInput, NForm, NFormItem, NTabs, NTabPane, NSpin, NDivider, NAlert, NTag, NIcon } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { listProcessLinks, upsertStageRule, upsertEntryCondition, listRounds, listProcesses, listStageRules, listEntryConditions, type ConditionItem } from '../../api/recruitment-process'
import { listAutoArchiveRules, upsertAutoArchiveRule } from '../../api/recruitment-process'
import { listUsers } from '../../api/users'
import ConditionTreeEditor from '../../components/ConditionTreeEditor.vue'

// 嵌套条件项（3 级树） - 扩展 ConditionItem 增加 children 字段
interface ConditionItemTree extends ConditionItem {
  children?: ConditionItemTree[]
}

import { extractApiError } from '../../api/dynamic-field'
const message = useMessage()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const linkId = computed(() => route.query.linkId as string)
const processId = computed(() => route.query.processId as string)
const activeTab = ref(route.query.tab === 'condition' ? 'condition' : 'rule')

const processName = ref('')
const stageName = ref('')
const isInterviewType = ref(false)
const allStages = ref<any[]>([])
const allLinkIds = ref<string[]>([])

// ==================== Tab 1: 阶段规则 ====================
const ruleLoading = ref(false)
const ruleSaving = ref(false)
const ruleForm = reactive({
  autoAdvanceType: 'NONE' as 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS',
  autoAdvanceTiming: 'NONE' as 'NONE' | 'IMMEDIATE' | 'DELAYED',
  autoAdvanceDays: undefined as number | undefined,
  defaultHandlerType: 'CUSTOM' as 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM',
  defaultHandlerFields: [] as string[],
  defaultHandlerUserIds: [] as string[],
  timeLimit: undefined as number | undefined,
  timeLimitScope: 'NEW_ONLY' as 'NEW_ONLY' | 'ALL',
  interviewRoundIds: [] as string[],
})

const autoAdvanceOptions = [
  { label: t('pages.settings.ProcessStageRules.s50'), value: 'NONE' },
  { label: t('pages.settings.ProcessStageRules.s51'), value: 'MEET_NEXT' },
  { label: t('pages.settings.ProcessStageRules.s52'), value: 'IGNORE_NEXT' },
  { label: t('pages.settings.ProcessStageRules.s53'), value: 'MEET_NEXT_OR_N2' },
  { label: t('pages.settings.ProcessStageRules.s54'), value: 'N1_ALL_PASS' },
]

const handlerFieldOptions: Record<string, any[]> = {
  FROM_DEMAND: [
    { label: t('pages.settings.ProcessStageRules.s55'), value: 'MANAGER' },
    { label: t('pages.settings.ProcessStageRules.s56'), value: 'MANAGER_SUPER' },
    { label: 'HRBP', value: 'HRBP' },
  ],
  FROM_POSITION: [
    { label: t('pages.settings.ProcessStageRules.s57'), value: 'POSITION_OWNER' },
    { label: t('pages.settings.ProcessStageRules.s58'), value: 'POSITION_ASSISTANT' },
    { label: t('pages.settings.ProcessStageRules.s59'), value: 'POSITION_OWNER_AND_ASSISTANT' },
    { label: t('pages.settings.ProcessStageRules.s60'), value: 'MANAGER' },
    { label: t('pages.settings.ProcessStageRules.s61'), value: 'MANAGER_SUPER' },
  ],
  CUSTOM: [],
}

const userOptions = ref<any[]>([])
const userLoading = ref(false)
async function loadUsers() {
  userLoading.value = true
  try {
    const users = await listUsers()
    userOptions.value = users.map((u) => ({
      label: u.realName || u.username || u.id,
      value: u.id,
    }))
  } finally {
    userLoading.value = false
  }
}

const roundOptions = ref<any[]>([])
const roundLoading = ref(false)
async function loadRounds() {
  roundLoading.value = true
  try {
    const rounds = await listRounds()
    roundOptions.value = rounds.map((r) => ({ label: r.name, value: r.id }))
  } finally {
    roundLoading.value = false
  }
}

async function loadRule() {
  ruleLoading.value = true
  try {
    const rules = await listStageRules({ linkId: linkId.value })
    if (rules?.[0]) {
      const r = rules[0]
      Object.assign(ruleForm, {
        autoAdvanceType: r.autoAdvanceType,
        autoAdvanceTiming: r.autoAdvanceTiming,
        autoAdvanceDays: r.autoAdvanceDays,
        defaultHandlerType: r.defaultHandlerType,
        defaultHandlerFields: r.defaultHandlerFields || [],
        defaultHandlerUserIds: r.defaultHandlerUserIds || [],
        timeLimit: r.timeLimit,
        timeLimitScope: r.timeLimitScope,
        interviewRoundIds: r.interviewRoundIds || [],
      })
    }
  } finally {
    ruleLoading.value = false
  }
}

async function saveRule() {
  ruleSaving.value = true
  try {
    await upsertStageRule(linkId.value, {
      ...ruleForm,
      processId: processId.value,
    })
    message.success(t('pages.settings.ProcessStageRules.s62'))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageRules.s74'))
  } finally {
    ruleSaving.value = false
  }
}

// ==================== Tab 2: 进入条件 ====================
const condLoading = ref(false)
const condSaving = ref(false)
const condForm = reactive({
  matchType: 'ALL' as 'ALL' | 'ANY',
  conditionType: 'MIXED' as 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED',
  prompt: '',
  items: [] as ConditionItemTree[],
})

const conditionTypeOptions = [
  { label: t('pages.settings.ProcessStageRules.s63'), value: 'MIXED' },
  { label: t('pages.settings.ProcessStageRules.s64'), value: 'STAGE_STATUS' },
  { label: t('pages.settings.ProcessStageRules.s65'), value: 'CANDIDATE' },
]

async function loadCondition() {
  condLoading.value = true
  try {
    const conds = await listEntryConditions({ linkId: linkId.value })
    if (conds?.[0]) {
      const c = conds[0]
      Object.assign(condForm, {
        matchType: c.matchType,
        conditionType: c.conditionType,
        prompt: c.prompt || '',
        items: c.items || [],
      })
    }
  } finally {
    condLoading.value = false
  }
}

async function saveCondition() {
  condSaving.value = true
  try {
    // 收集全部 linkIds 用于 ConditionTreeEditor 的 refStageId 选项
    const all = allLinkIds.value
    await upsertEntryCondition(linkId.value, {
      matchType: condForm.matchType,
      conditionType: condForm.conditionType,
      prompt: condForm.prompt,
      items: condForm.items,
    })
    message.success(t('pages.settings.ProcessStageRules.s66'))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageRules.s74'))
  } finally {
    condSaving.value = false
  }
}


const rootItems = computed(() => condForm.items.filter((it) => !it.parentId))

// ==================== Tab 3: 自动归档 ====================
const archiveLoading = ref(false)
const archiveForms = reactive({
  invite: { enabled: false, failTags: '', maxAttempts: 3 },
  offer: { enabled: false },
  eval: { enabled: false, failTags: t('pages.settings.ProcessStageRules.s75'), executeTiming: 'IMMEDIATE', delayDays: undefined as number | undefined },
  timeout: { enabled: false, timeoutDays: 3 },
})

async function loadArchiveRules() {
  archiveLoading.value = true
  try {
    const rules = await listAutoArchiveRules({ processId: processId.value })
    for (const r of rules) {
      if (r.ruleType === 'INVITE_FAIL') {
        archiveForms.invite.enabled = r.enabled
        archiveForms.invite.failTags = (r.config?.failTags || []).join(',')
        archiveForms.invite.maxAttempts = r.config?.maxAttempts || 3
      } else if (r.ruleType === 'OFFER_FAIL') {
        archiveForms.offer.enabled = r.enabled
      } else if (r.ruleType === 'EVAL_FAIL') {
        archiveForms.eval.enabled = r.enabled
        archiveForms.eval.failTags = (r.config?.failTags || []).join(',')
        archiveForms.eval.executeTiming = r.config?.executeTiming || 'IMMEDIATE'
        archiveForms.eval.delayDays = r.config?.delayDays
      } else if (r.ruleType === 'TIMEOUT_UNASSIGNED') {
        archiveForms.timeout.enabled = r.enabled
        archiveForms.timeout.timeoutDays = r.config?.timeoutDays || 3
      }
    }
  } finally {
    archiveLoading.value = false
  }
}

async function saveArchive(ruleType: string, form: any) {
  try {
    let config: any = {}
    if (ruleType === 'INVITE_FAIL') {
      config = {
        failTags: (form.failTags || '').split(',').map((s: string) => s.trim()).filter(Boolean),
        maxAttempts: form.maxAttempts || 3,
      }
    } else if (ruleType === 'OFFER_FAIL') {
      config = { rejectTypes: ['REJECTED_BY_APPROVER', 'REJECTED_BY_CANDIDATE'] }
    } else if (ruleType === 'EVAL_FAIL') {
      config = {
        failTags: (form.failTags || '').split(',').map((s: string) => s.trim()).filter(Boolean),
        executeTiming: form.executeTiming,
        delayDays: form.executeTiming === 'DELAYED' ? form.delayDays : undefined,
      }
    } else if (ruleType === 'TIMEOUT_UNASSIGNED') {
      config = { timeoutDays: form.timeoutDays || 3 }
    }
    await upsertAutoArchiveRule({
      processId: processId.value,
      ruleType: ruleType as 'INVITE_FAIL' | 'OFFER_FAIL' | 'EVAL_FAIL' | 'TIMEOUT_UNASSIGNED',
      enabled: form.enabled,
      config,
    })
    message.success(t('pages.settings.ProcessStageRules.s76', { ruleType }))
  } catch (e: any) {
    message.error(e?.response?.data?.message || t('pages.settings.ProcessStageRules.s74'))
  }
}

// ==================== 初始化 ====================
onMounted(async () => {
  if (!linkId.value || !processId.value) {
    message.error(t('pages.settings.ProcessStageRules.s67'))
    router.back()
    return
  }
  // 加载 process 名称
  try {
    const procs = await listProcesses()
    const p = procs.find((x) => x.id === processId.value)
    if (p) processName.value = p.name
  } catch (e) { message.error(extractApiError(e, t('pages.settings.ProcessStageRules.s77'))) }
  // 加载 link 列表（找 stage 名称 + 全部 linkIds）
  try {
    const links = await listProcessLinks(processId.value)
    const link = links.find((l) => l.id === linkId.value)
    if (link) {
      stageName.value = link.customName || link.stage?.name
      isInterviewType.value = link.stage?.stageType === 'INTERVIEW'
    }
    allLinkIds.value = links.map((l) => l.id)
  } catch (e) { message.error(extractApiError(e, t('pages.settings.ProcessStageRules.s78'))) }
  await Promise.all([loadRule(), loadCondition(), loadRounds(), loadUsers(), loadArchiveRules()])
})
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}


.process-stage-rules {
  padding: 20px var(--space-6);
}
/* 删除 scoped .page-header margin-bottom 覆盖（规范：复用全局 glass.css 通栏分隔线规则） */
.page-header h2 {
  margin: 0;
  font-size: var(--fs-18);
  font-weight: 600;
}
/* 字段宽度与表单宽度收敛（替代散落的 max-width:800px / width:NNNpx 行内样式） */
.psr-form-max      { max-width: 800px; }
.psr-actions-top   { margin-top: 16px; }
.psr-input-days    { width: 120px; }
.psr-input-days-sm { width: 80px;  }
</style>

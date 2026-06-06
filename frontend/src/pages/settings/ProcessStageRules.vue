<template>
  <div class="process-stage-rules">
    <div class="page-header">
      <n-space align="center">
        <n-button text @click="$router.back()">
          <template #icon><n-icon :component="ArrowBackOutline" /></template>
          返回
        </n-button>
        <h2>{{ processName }} - {{ stageName }} - 规则配置</h2>
      </n-space>
    </div>

    <n-tabs v-model:value="activeTab" type="line" animated>
      <!-- Tab 3: 自动归档（仅 process 级别） -->
      <n-tab-pane v-if="!linkId" name="archive" tab="自动归档">
        <n-spin :show="archiveLoading">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
            基于规则自动淘汰候选人。最多可配置 4 种规则：邀约不成功 / Offer 不通过 / 评估不通过 / 超时未分配。
          </n-alert>
          <n-form label-placement="top" style="max-width: 800px">
            <!-- 邀约不成功 -->
            <n-form-item label="邀约不成功（失败标签次数触发）">
              <n-space>
                <n-switch v-model:value="archiveForms.invite.enabled" @update:value="(v) => saveArchive('INVITE_FAIL', archiveForms.invite)" />
                <n-input v-model:value="archiveForms.invite.failTags" placeholder="失败标签（逗号分隔）" :disabled="!archiveForms.invite.enabled" style="width: 240px" />
                <n-input-number v-model:value="archiveForms.invite.maxAttempts" :min="1" :max="10" placeholder="最大次数" :disabled="!archiveForms.invite.enabled" style="width: 120px" />
              </n-space>
            </n-form-item>

            <!-- Offer 不通过 -->
            <n-form-item label="Offer 不通过（审批人拒绝/候选人拒绝）">
              <n-space>
                <n-switch v-model:value="archiveForms.offer.enabled" @update:value="(v) => saveArchive('OFFER_FAIL', archiveForms.offer)" />
                <n-text v-if="archiveForms.offer.enabled" type="success" size="small">已启用（覆盖默认两条规则）</n-text>
                <n-text v-else depth="3" size="small">默认 2 条：审批人拒绝 + 候选人拒绝</n-text>
              </n-space>
            </n-form-item>

            <!-- 评估/筛选/面试不通过 -->
            <n-form-item label="评估/筛选/面试不通过（指定标签）">
              <n-space>
                <n-switch v-model:value="archiveForms.eval.enabled" @update:value="(v) => saveArchive('EVAL_FAIL', archiveForms.eval)" />
                <n-input v-model:value="archiveForms.eval.failTags" placeholder="不通过标签（逗号分隔，如 跳槽频繁）" :disabled="!archiveForms.eval.enabled" style="width: 320px" />
                <n-select
                  v-model:value="archiveForms.eval.executeTiming"
                  :options="[{label:'立即执行',value:'IMMEDIATE'},{label:'延迟执行',value:'DELAYED'}]"
                  :disabled="!archiveForms.eval.enabled"
                  style="width: 140px"
                />
                <n-input-number v-model:value="archiveForms.eval.delayDays" :min="1" :max="15" :disabled="!archiveForms.eval.enabled || archiveForms.eval.executeTiming !== 'DELAYED'" style="width: 80px" />
              </n-space>
            </n-form-item>

            <!-- 超时未分配 -->
            <n-form-item label="超时未分配（3 天未分配则自动合并/转移）">
              <n-space>
                <n-switch v-model:value="archiveForms.timeout.enabled" @update:value="(v) => saveArchive('TIMEOUT_UNASSIGNED', archiveForms.timeout)" />
                <n-input-number v-model:value="archiveForms.timeout.timeoutDays" :min="1" :max="30" :disabled="!archiveForms.timeout.enabled" style="width: 120px" />
                <n-text depth="3" size="small">天</n-text>
              </n-space>
            </n-form-item>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- Tab 1: 阶段规则 -->
      <n-tab-pane name="rule" tab="阶段规则">
        <n-spin :show="ruleLoading">
          <n-form :model="ruleForm" label-placement="top" style="max-width: 800px">
            <n-form-item label="自动化流转条件">
              <n-select v-model:value="ruleForm.autoAdvanceType" :options="autoAdvanceOptions" />
            </n-form-item>

            <n-form-item v-if="ruleForm.autoAdvanceType !== 'NONE'" label="执行时机">
              <n-radio-group v-model:value="ruleForm.autoAdvanceTiming">
                <n-space>
                  <n-radio value="NONE">不执行</n-radio>
                  <n-radio value="IMMEDIATE">立即执行</n-radio>
                  <n-radio value="DELAYED">延迟</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item v-if="ruleForm.autoAdvanceTiming === 'DELAYED'" label="延迟天数（1-15 工作日）">
              <n-input-number v-model:value="ruleForm.autoAdvanceDays" :min="1" :max="15" />
            </n-form-item>

            <n-divider title-placement="left">默认处理人</n-divider>

            <n-form-item label="数据来源">
              <n-radio-group v-model:value="ruleForm.defaultHandlerType">
                <n-space>
                  <n-radio value="FROM_DEMAND">需求中</n-radio>
                  <n-radio value="FROM_POSITION">职位中</n-radio>
                  <n-radio value="CUSTOM">自定义</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item v-if="ruleForm.defaultHandlerType === 'CUSTOM'" label="指定人员（多选）">
              <n-select
                v-model:value="ruleForm.defaultHandlerUserIds"
                multiple
                filterable
                :options="userOptions"
                placeholder="选择具体人员"
                :loading="userLoading"
              />
            </n-form-item>

            <n-form-item v-if="ruleForm.defaultHandlerType !== 'CUSTOM'" label="取值字段（多选）">
              <n-select
                v-model:value="ruleForm.defaultHandlerFields"
                multiple
                :options="handlerFieldOptions[ruleForm.defaultHandlerType] || []"
                placeholder="选择取值字段"
              />
            </n-form-item>

            <n-divider title-placement="left">阶段限时</n-divider>

            <n-form-item label="限制时长（小时）">
              <n-input-number v-model:value="ruleForm.timeLimit" :min="0" placeholder="留空表示不限制" style="width: 200px" />
            </n-form-item>

            <n-form-item v-if="ruleForm.timeLimit" label="生效范围">
              <n-radio-group v-model:value="ruleForm.timeLimitScope">
                <n-space>
                  <n-radio value="NEW_ONLY">仅对新进入有效</n-radio>
                  <n-radio value="ALL">对全部生效</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-divider v-if="isInterviewType" title-placement="left">面试轮次（仅面试型阶段）</n-divider>

            <n-form-item v-if="isInterviewType" label="关联面试轮次（多选）">
              <n-select
                v-model:value="ruleForm.interviewRoundIds"
                multiple
                :options="roundOptions"
                :loading="roundLoading"
                placeholder="选择面试轮次"
              />
            </n-form-item>

            <n-space justify="end" style="margin-top: 16px">
              <n-button type="primary" :loading="ruleSaving" @click="saveRule">保存规则</n-button>
            </n-space>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- Tab 2: 进入条件 -->
      <n-tab-pane name="condition" tab="进入条件">
        <n-spin :show="condLoading">
          <n-form :model="condForm" label-placement="top" style="max-width: 800px">
            <n-form-item label="判定方式">
              <n-radio-group v-model:value="condForm.matchType">
                <n-space>
                  <n-radio value="ALL">全部满足（AND）</n-radio>
                  <n-radio value="ANY">任意满足（OR）</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item label="条件类型">
              <n-select v-model:value="condForm.conditionType" :options="conditionTypeOptions" />
            </n-form-item>

            <n-form-item label="提示内容（候选人转移阶段不满足条件时展示）">
              <n-input v-model:value="condForm.prompt" type="textarea" :rows="3" placeholder="留空使用默认模板" />
            </n-form-item>

            <n-divider title-placement="left">条件项（3 级嵌套 AND/OR 树）</n-divider>

            <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
              从 <strong>{{ rootItems.length }}</strong> 个根条件项开始。每个条件可挂子条件，最多 3 级嵌套。
            </n-alert>

            <ConditionTreeEditor
              v-model="condForm.items"
              :all-stages="allStages"
              :all-link-ids="allLinkIds"
            />

            <n-space justify="space-between" style="margin-top: 16px">
              <n-button @click="testCondition" :loading="testing">测试条件</n-button>
              <n-button type="primary" :loading="condSaving" @click="saveCondition">保存条件</n-button>
            </n-space>

            <n-alert v-if="testResult" :type="testResult.passed ? 'success' : 'error'" :show-icon="false" style="margin-top: 12px">
              <strong>结果：{{ testResult.passed ? '✅ 通过' : '❌ 不通过' }}</strong>
              <div v-if="testResult.prompt" style="margin-top: 6px; white-space: pre-wrap">{{ testResult.prompt }}</div>
            </n-alert>
          </n-form>
        </n-spin>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, h } from 'vue'
import { useMessage, NSpace, NButton, NSelect, NInputNumber, NRadio, NRadioGroup, NInput, NForm, NFormItem, NTabs, NTabPane, NSpin, NDivider, NAlert, NTag, NIcon } from 'naive-ui'
import { ArrowBackOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import { listProcessLinks, upsertStageRule, upsertEntryCondition, evaluateEntryCondition, listRounds, listProcesses } from '../../api/recruitment-process'
import { listAutoArchiveRules, upsertAutoArchiveRule } from '../../api/recruitment-process'
import ConditionTreeEditor from '../../components/ConditionTreeEditor.vue'

const message = useMessage()
const route = useRoute()
const router = useRouter()

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
  { label: '不自动流转', value: 'NONE' },
  { label: '满足下阶段进入条件时', value: 'MEET_NEXT' },
  { label: '无视下阶段进入条件', value: 'IGNORE_NEXT' },
  { label: '满足下阶段条件或 N+2 推荐', value: 'MEET_NEXT_OR_N2' },
  { label: 'N+1 全部通过', value: 'N1_ALL_PASS' },
]

const handlerFieldOptions: Record<string, any[]> = {
  FROM_DEMAND: [
    { label: '用人经理', value: 'MANAGER' },
    { label: '用人经理上级', value: 'MANAGER_SUPER' },
    { label: 'HRBP', value: 'HRBP' },
  ],
  FROM_POSITION: [
    { label: '职位负责人', value: 'POSITION_OWNER' },
    { label: '职位协助人', value: 'POSITION_ASSISTANT' },
    { label: '职位负责人及协助人', value: 'POSITION_OWNER_AND_ASSISTANT' },
    { label: '用人经理', value: 'MANAGER' },
    { label: '用人经理上级', value: 'MANAGER_SUPER' },
  ],
  CUSTOM: [],
}

const userOptions = ref<any[]>([])
const userLoading = ref(false)
async function loadUsers() {
  userLoading.value = true
  try {
    // TODO: 接入 /api/users 列表
    userOptions.value = [
      { label: '系统管理员', value: '584e0711-fab7-4cb8-aca2-2716d9229bf8' },
    ]
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
    const res = await fetch(`/api/recruitment-rules/stage-rules?linkId=${linkId.value}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    })
    if (res.ok) {
      const json = await res.json()
      if (json.success && json.data?.[0]) {
        const r = json.data[0]
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
    message.success('阶段规则已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
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
  items: [] as any[],
})

const conditionTypeOptions = [
  { label: '混合条件 (候选人+阶段状态)', value: 'MIXED' },
  { label: '仅阶段状态', value: 'STAGE_STATUS' },
  { label: '仅候选人', value: 'CANDIDATE' },
]

const testing = ref(false)
const testResult = ref<any>(null)

async function loadCondition() {
  condLoading.value = true
  try {
    const res = await fetch(`/api/recruitment-rules/entry-conditions?linkId=${linkId.value}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    })
    if (res.ok) {
      const json = await res.json()
      if (json.success && json.data?.[0]) {
        const c = json.data[0]
        Object.assign(condForm, {
          matchType: c.matchType,
          conditionType: c.conditionType,
          prompt: c.prompt || '',
          items: c.items || [],
        })
      }
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
    message.success('进入条件已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    condSaving.value = false
  }
}

async function testCondition() {
  testing.value = true
  testResult.value = null
  try {
    const res = await fetch(`/api/recruitment-rules/entry-conditions/${linkId.value}/evaluate`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        candidate: { age: 30, highestEducation: '博士', gender: '男' },
        stageStatuses: {},
      }),
    })
    const json = await res.json()
    if (json.success) {
      testResult.value = json.data
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '测试失败')
  } finally {
    testing.value = false
  }
}

const rootItems = computed(() => condForm.items.filter((it) => !it.parentId))

// ==================== Tab 3: 自动归档 ====================
const archiveLoading = ref(false)
const archiveForms = reactive({
  invite: { enabled: false, failTags: '', maxAttempts: 3 },
  offer: { enabled: false },
  eval: { enabled: false, failTags: '跳槽频繁', executeTiming: 'IMMEDIATE', delayDays: undefined as number | undefined },
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
      ruleType,
      enabled: form.enabled,
      config,
    })
    message.success(`${ruleType} 已保存`)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  }
}

// ==================== 初始化 ====================
onMounted(async () => {
  if (!linkId.value || !processId.value) {
    message.error('缺少 linkId 或 processId 参数')
    router.back()
    return
  }
  // 加载 process 名称
  try {
    const procs = await listProcesses()
    const p = procs.find((x) => x.id === processId.value)
    if (p) processName.value = p.name
  } catch {}
  // 加载 link 列表（找 stage 名称 + 全部 linkIds）
  try {
    const links = await listProcessLinks(processId.value)
    const link = links.find((l) => l.id === linkId.value)
    if (link) {
      stageName.value = link.customName || link.stage?.name
      isInterviewType.value = link.stage?.stageType === 'INTERVIEW'
    }
    allLinkIds.value = links.map((l) => l.id)
  } catch {}
  await Promise.all([loadRule(), loadCondition(), loadRounds(), loadUsers(), loadArchiveRules()])
})
</script>

<style scoped>
.process-stage-rules {
  padding: 20px 24px;
}
.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style>

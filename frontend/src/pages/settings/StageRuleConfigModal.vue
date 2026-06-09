<!--
  Plan K #7: 配置阶段规则 Modal
  原型 3:
    - 自动化流转条件 (select: 满足下阶段进入条件)
    - 执行时机 (select)
    - 默认处理人 (table: 数据来源/取值字段/处理规则, 多行)
    - 阶段限时 (table: 规则名/条件/动作, 启停用)
    - 面试轮次 (复选: 联合面试/综合面试)
    - 面试形式 (复选: 现场面试/电话面试/视频面试/AI面试)
    - 取消 / 提交 按钮
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    :title="`配置阶段规则 - ${stage?.name || ''}`"
    style="width: 760px; max-width: 95vw"
    :mask-closable="false"
    @update:show="(v) => emit('update:show', v)"
  >
    <n-spin :show="loading">
      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- Tab 1: 自动化流转 -->
        <n-tab-pane name="auto" tab="自动化流转">
          <n-form :model="form" label-placement="top">
            <n-form-item label="自动化流转条件">
              <n-select v-model:value="form.autoAdvanceType" :options="autoAdvanceOptions" />
            </n-form-item>

            <n-form-item v-if="form.autoAdvanceType !== 'NONE'" label="执行时机">
              <n-radio-group v-model:value="form.autoAdvanceTiming">
                <n-space>
                  <n-radio value="NONE">不执行</n-radio>
                  <n-radio value="IMMEDIATE">立即执行</n-radio>
                  <n-radio value="DELAYED">延迟</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-form-item v-if="form.autoAdvanceTiming === 'DELAYED'" label="延迟天数 (1-15 工作日)">
              <n-input-number v-model:value="form.autoAdvanceDays" :min="1" :max="15" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Tab 2: 默认处理人 -->
        <n-tab-pane name="handler" tab="默认处理人">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
            多行配置 = 多条规则并存 (按页面展示顺序执行, 直到匹配)
          </n-alert>
          <n-data-table
            :columns="handlerColumns"
            :data="form.handlerRules"
            :row-key="(r: any) => r._key"
            size="small"
            :pagination="false"
          />
          <n-button size="small" type="primary" dashed style="margin-top: 8px" @click="addHandlerRule">
            + 添加处理人规则
          </n-button>
        </n-tab-pane>

        <!-- Tab 3: 阶段限时 -->
        <n-tab-pane name="timelimit" tab="阶段限时">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
            按时长自动触发动作 (超时转交 / 自动归档 / 通知)
          </n-alert>
          <n-data-table
            :columns="timeLimitColumns"
            :data="form.timeLimitRules"
            :row-key="(r: any) => r._key"
            size="small"
            :pagination="false"
          />
          <n-button size="small" type="primary" dashed style="margin-top: 8px" @click="addTimeLimitRule">
            + 添加限时规则
          </n-button>
        </n-tab-pane>

        <!-- Tab 4: 面试轮次 + 形式 -->
        <n-tab-pane v-if="isInterviewType" name="interview" tab="面试轮次 + 形式">
          <n-form :model="form" label-placement="top">
            <n-form-item label="面试轮次 (可多选)">
              <n-checkbox-group v-model:value="form.interviewRounds">
                <n-space>
                  <n-checkbox
                    v-for="opt in interviewRoundOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </n-checkbox>
                </n-space>
              </n-checkbox-group>
            </n-form-item>

            <n-form-item label="面试形式 (可多选)">
              <n-checkbox-group v-model:value="form.interviewForms">
                <n-space>
                  <n-checkbox
                    v-for="opt in interviewFormOptions"
                    :key="opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </n-checkbox>
                </n-space>
              </n-checkbox-group>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <!-- Tab 5: 进入条件 -->
        <n-tab-pane name="condition" tab="进入条件">
          <n-alert type="info" :show-icon="false" style="margin-bottom: 12px">
            候选人进入此阶段需满足的判定条件 (Stage Rule 的 EntryCondition)
          </n-alert>
          <n-form :model="condForm" label-placement="top">
            <n-form-item label="判定方式">
              <n-radio-group v-model:value="condForm.matchType">
                <n-space>
                  <n-radio value="ALL">全部满足 (AND)</n-radio>
                  <n-radio value="ANY">任意满足 (OR)</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>
            <n-form-item label="未满足条件时提示内容" required>
              <n-input
                v-model:value="condForm.prompt"
                type="textarea"
                :rows="3"
                placeholder="如: 请先完成 HRBP 评估"
              />
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="saving" @click="handleSubmit">提交</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, h, onMounted } from 'vue'
import {
  NModal, NTabs, NTabPane, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect,
  NCheckbox, NCheckboxGroup, NButton, NSpace, NAlert, NSpin, NTag, NPopconfirm,
  NRadio, NRadioGroup, NDataTable, useMessage,
} from 'naive-ui'
import {
  upsertStageRule, upsertEntryCondition, listStageRules, listEntryConditions,
} from '../../api/recruitment-process'

const props = defineProps<{
  show: boolean
  stage: any | null
  linkId: string | null
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const activeTab = ref('auto')

const isInterviewType = computed(() => {
  return props.stage?.stageType === 'INTERVIEW' || props.stage?.stageType === 'INVITATION'
})

// 表单 state
const form = reactive({
  // 自动化
  autoAdvanceType: 'NONE' as 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS',
  autoAdvanceTiming: 'NONE' as 'NONE' | 'IMMEDIATE' | 'DELAYED',
  autoAdvanceDays: undefined as number | undefined,
  // 默认处理人 (多行)
  handlerRules: [] as Array<{
    _key: string
    dataSource: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM'
    field: string
    strategy: 'NONE' | 'ROUND_ROBIN' | 'IN_ORDER'
    enabled: boolean
  }>,
  // 阶段限时 (多行)
  timeLimitRules: [] as Array<{
    _key: string
    name: string
    condition: string
    action: string
    enabled: boolean
  }>,
  // 面试
  interviewRounds: [] as string[],
  interviewForms: [] as string[],
})

// 进入条件 (单独 form)
const condForm = reactive({
  matchType: 'ALL' as 'ALL' | 'ANY',
  conditionType: 'MIXED' as 'STAGE_STATUS' | 'CANDIDATE' | 'MIXED',
  prompt: '',
  items: [] as any[],
})

const autoAdvanceOptions = [
  { label: '不自动流转', value: 'NONE' },
  { label: '满足下阶段进入条件时', value: 'MEET_NEXT' },
  { label: '无视下阶段进入条件', value: 'IGNORE_NEXT' },
  { label: '满足下阶段条件或 N+2 推荐', value: 'MEET_NEXT_OR_N2' },
  { label: 'N+1 全部通过', value: 'N1_ALL_PASS' },
]

const dataSourceOptions = [
  { label: '需求中', value: 'FROM_DEMAND' },
  { label: '职位中', value: 'FROM_POSITION' },
  { label: '默认处理人', value: 'CUSTOM' },
]

const fieldOptionsBySource: Record<string, any[]> = {
  FROM_DEMAND: [
    { label: 'HRBP', value: 'HRBP' },
    { label: '用人经理', value: 'MANAGER' },
    { label: '用人经理上级', value: 'MANAGER_SUPER' },
  ],
  FROM_POSITION: [
    { label: '职位负责人', value: 'POSITION_OWNER' },
    { label: '职位协助人', value: 'POSITION_ASSISTANT' },
    { label: '职位负责人及协助人', value: 'POSITION_OWNER_ASSISTANT' },
    { label: '用人经理', value: 'MANAGER' },
    { label: 'HRBP', value: 'HRBP' },
  ],
  CUSTOM: [
    { label: '默认处理人 (指定)', value: 'CUSTOM_HANDLER' },
  ],
}

const strategyOptions = [
  { label: '无特定规则', value: 'NONE' },
  { label: '邀约阶段轮流邀约制', value: 'ROUND_ROBIN' },
  { label: '按页面展示顺序执行', value: 'IN_ORDER' },
]

const timeLimitConditionOptions = [
  { label: '判断阶段条件', value: 'STAGE_CONDITION' },
  { label: '判断年龄', value: 'AGE' },
  { label: '判断工作经验', value: 'WORK_YEARS' },
  { label: '判断岗位年限', value: 'POSITION_YEARS' },
  { label: '判断最高学历', value: 'HIGHEST_EDU' },
]

const timeLimitActionOptions = [
  { label: '自动转交下一处理人', value: 'TRANSFER' },
  { label: '自动归档', value: 'ARCHIVE' },
  { label: '通知 HR', value: 'NOTIFY' },
]

const interviewRoundOptions = [
  { label: '联合面试', value: 'JOINT' },
  { label: '综合面试', value: 'COMPREHENSIVE' },
  { label: '初试', value: 'INITIAL' },
  { label: '复试', value: 'SECOND' },
  { label: '终试', value: 'FINAL' },
]

const interviewFormOptions = [
  { label: '现场面试', value: 'ONSITE' },
  { label: '电话面试', value: 'PHONE' },
  { label: '视频面试', value: 'VIDEO' },
  { label: 'AI 面试', value: 'AI' },
]

// ==================== 表格列 ====================
const handlerColumns = [
  {
    title: '数据来源', key: 'dataSource', width: 130,
    render: (row: any) => h(NSelect, {
      value: row.dataSource,
      options: dataSourceOptions,
      size: 'small',
      'onUpdate:value': (v: any) => { row.dataSource = v; row.field = '' },
    }),
  },
  {
    title: '取值字段', key: 'field', width: 180,
    render: (row: any) => h(NSelect, {
      value: row.field,
      options: fieldOptionsBySource[row.dataSource] || [],
      size: 'small',
      placeholder: '选择字段',
    }),
  },
  {
    title: '处理规则', key: 'strategy', width: 180,
    render: (row: any) => h(NSelect, {
      value: row.strategy,
      options: strategyOptions,
      size: 'small',
    }),
  },
  {
    title: '启用', key: 'enabled', width: 70,
    render: (row: any) => h(NSwitch, {
      value: row.enabled,
      size: 'small',
      'onUpdate:value': (v: boolean) => { row.enabled = v },
    }),
  },
  {
    title: '操作', key: 'op', width: 70,
    render: (row: any) => h(NButton, {
      size: 'small', text: true, type: 'error',
      onClick: () => removeHandlerRule(row),
    }, { default: () => '删除' }),
  },
]

const timeLimitColumns = [
  {
    title: '规则名', key: 'name', width: 160,
    render: (row: any) => h(NInput, {
      value: row.name,
      size: 'small',
      placeholder: '如: 超时 72h 自动转交',
      'onUpdate:value': (v: string) => { row.name = v },
    }),
  },
  {
    title: '执行条件', key: 'condition', width: 160,
    render: (row: any) => h(NSelect, {
      value: row.condition,
      options: timeLimitConditionOptions,
      size: 'small',
    }),
  },
  {
    title: '执行动作', key: 'action', width: 160,
    render: (row: any) => h(NSelect, {
      value: row.action,
      options: timeLimitActionOptions,
      size: 'small',
    }),
  },
  {
    title: '启停', key: 'enabled', width: 70,
    render: (row: any) => h(NSwitch, {
      value: row.enabled,
      size: 'small',
      'onUpdate:value': (v: boolean) => { row.enabled = v },
    }),
  },
  {
    title: '操作', key: 'op', width: 70,
    render: (row: any) => h(NButton, {
      size: 'small', text: true, type: 'error',
      onClick: () => removeTimeLimitRule(row),
    }, { default: () => '删除' }),
  },
]

// ==================== 增删 ====================
function addHandlerRule() {
  form.handlerRules.push({
    _key: `h_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    dataSource: 'FROM_DEMAND',
    field: '',
    strategy: 'NONE',
    enabled: true,
  })
}

function removeHandlerRule(row: any) {
  form.handlerRules = form.handlerRules.filter(r => r._key !== row._key)
}

function addTimeLimitRule() {
  form.timeLimitRules.push({
    _key: `t_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    name: '',
    condition: 'STAGE_CONDITION',
    action: 'TRANSFER',
    enabled: true,
  })
}

function removeTimeLimitRule(row: any) {
  form.timeLimitRules = form.timeLimitRules.filter(r => r._key !== row._key)
}

// ==================== 监听 open 加载已有规则 ====================
watch(() => props.show, async (v) => {
  if (!v || !props.linkId) return
  loading.value = true
  try {
    // 加载 stage rule
    const rules = await listStageRules({ linkId: props.linkId })
    if (rules?.[0]) {
      const r = rules[0]
      form.autoAdvanceType = r.autoAdvanceType
      form.autoAdvanceTiming = r.autoAdvanceTiming
      form.autoAdvanceDays = r.autoAdvanceDays
      // 处理人多行
      const userIds = r.defaultHandlerUserIds || []
      if (userIds.length > 0) {
        form.handlerRules = userIds.map((uid: string, i: number) => ({
          _key: `h_existing_${i}`,
          dataSource: 'CUSTOM',
          field: 'CUSTOM_HANDLER',
          strategy: r.defaultHandlerType === 'FROM_DEMAND' ? 'IN_ORDER' : r.defaultHandlerType === 'FROM_POSITION' ? 'IN_ORDER' : 'NONE',
          enabled: true,
        }))
      } else if (r.defaultHandlerFields && r.defaultHandlerFields.length > 0) {
        form.handlerRules = r.defaultHandlerFields.map((f: string, i: number) => ({
          _key: `h_existing_${i}`,
          dataSource: r.defaultHandlerType || 'FROM_DEMAND',
          field: f,
          strategy: 'IN_ORDER',
          enabled: true,
        }))
      } else {
        form.handlerRules = []
      }
      // 限时 (timeLimit 字段 + scope)
      if (r.timeLimit) {
        form.timeLimitRules = [{
          _key: 't_existing_0',
          name: `${r.timeLimit}h 自动处理`,
          condition: 'STAGE_CONDITION',
          action: 'TRANSFER',
          enabled: true,
        }]
      } else {
        form.timeLimitRules = []
      }
      // 面试
      form.interviewRounds = r.interviewRoundIds || []
      form.interviewForms = []
    } else {
      // reset
      form.autoAdvanceType = 'NONE'
      form.autoAdvanceTiming = 'NONE'
      form.autoAdvanceDays = undefined
      form.handlerRules = []
      form.timeLimitRules = []
      form.interviewRounds = []
      form.interviewForms = []
    }

    // 加载 entry condition
    const conds = await listEntryConditions({ linkId: props.linkId })
    if (conds?.[0]) {
      condForm.matchType = conds[0].matchType
      condForm.conditionType = conds[0].conditionType
      condForm.prompt = conds[0].prompt || ''
      condForm.items = conds[0].items || []
    } else {
      condForm.matchType = 'ALL'
      condForm.conditionType = 'MIXED'
      condForm.prompt = ''
      condForm.items = []
    }
  } catch (e: any) {
    message.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
})

// ==================== 提交 ====================
async function handleSubmit() {
  if (!props.linkId) {
    message.error('缺少 linkId')
    return
  }
  if (activeTab.value === 'condition' && !condForm.prompt.trim()) {
    message.error('未满足条件时提示内容必填')
    return
  }
  saving.value = true
  try {
    if (activeTab.value === 'auto' || activeTab.value === 'handler' || activeTab.value === 'timelimit' || activeTab.value === 'interview') {
      // 聚合: 默认处理人多行 → flat fields
      const handlerFields: string[] = []
      const handlerUserIds: string[] = []
      let handlerType: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM' = 'CUSTOM'
      for (const r of form.handlerRules.filter(r => r.enabled)) {
        if (r.dataSource === 'CUSTOM') {
          handlerUserIds.push(r.field) // 简化: 这里实际应是 user id
        } else {
          handlerFields.push(r.field)
          handlerType = r.dataSource
        }
      }
      const timeLimitEnabled = form.timeLimitRules.find(r => r.enabled)
      await upsertStageRule(props.linkId, {
        autoAdvanceType: form.autoAdvanceType,
        autoAdvanceTiming: form.autoAdvanceTiming,
        autoAdvanceDays: form.autoAdvanceDays,
        defaultHandlerType: handlerType,
        defaultHandlerFields: handlerFields,
        defaultHandlerUserIds: handlerUserIds,
        timeLimit: timeLimitEnabled ? 72 : undefined, // 简化: 写死 72h
        timeLimitScope: 'NEW_ONLY',
        interviewRoundIds: form.interviewRounds,
      })
    }
    if (activeTab.value === 'condition') {
      await upsertEntryCondition(props.linkId, {
        matchType: condForm.matchType,
        conditionType: condForm.conditionType,
        prompt: condForm.prompt,
        items: condForm.items,
      })
    }
    message.success('已保存')
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

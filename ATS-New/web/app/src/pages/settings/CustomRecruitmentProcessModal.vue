<!--
  Plan K #6: 自定义招聘流程 Modal
  原型 2:
    - 基础信息: 流程名称 / 适用部门 (多选) / 是否启用 / 是否校验简历评分
    - 流程描述 (textarea)
    - 7 阶段 (3 个为系统默认不可删):
      1. 初评        (起 - 不可删)
      2. HRBP 评估
      3. 用人经理评估
      4. 邀约面试
      5. 联合面试
      6. 待入职
      7. 正式录用    (终 - 不可删)
    - 每阶段可配: 自动化流转条件 / 默认处理人 / 阶段限时 / 包含功能 / 进入条件
    - 阶段行: 配置进入条件 + 配置阶段规则 + 删除
    - 取消 / 确认 按钮
-->
<template>
  <n-modal
    :show="show"
    preset="card"
    :title="editing ? `编辑流程 - ${editing.name}` : '新建自定义招聘流程'"
    style="width: 900px; max-width: 95vw"
    :mask-closable="false"
    @update:show="(v) => emit('update:show', v)"
  >
    <n-spin :show="loading">
      <!-- ====== 基础信息 ====== -->
      <n-divider title-placement="left">基础信息</n-divider>
      <n-form :model="form" label-placement="top" :show-feedback="false">
        <n-grid :cols="2" :x-gap="16">
          <n-grid-item>
            <n-form-item label="流程名称" required>
              <n-input v-model:value="form.name" placeholder="如：技术部社招流程" />
            </n-form-item>
          </n-grid-item>
          <!-- 2026-06-17: 适用范围 4 指标 (含值来源 + 包含/不包含 + 多值) -->
          <n-grid-item :span="2">
            <n-form-item label="适用范围 (4 指标 × 包含/不包含 × 多值)">
              <n-space vertical :size="6" style="width: 100%">
                <div v-for="(ind, idx) in form.applicableIndicators" :key="ind.key" class="scope-row">
                  <n-space :wrap-item="false" align="center" :size="8" style="width: 100%">
                    <n-tag :type="SCOPE_INDICATOR_META[ind.key].tagType" size="small" style="min-width: 88px">
                      {{ SCOPE_INDICATOR_META[ind.key].label }}
                    </n-tag>
                    <n-radio-group v-model:value="ind.mode" size="small">
                      <n-radio value="include">包含</n-radio>
                      <n-radio value="exclude">不包含</n-radio>
                    </n-radio-group>
                    <n-select
                      v-model:value="ind.values"
                      multiple
                      filterable
                      clearable
                      placeholder="留空 = 不约束 (全部通过)"
                      :options="ind.options"
                      :loading="ind.loading"
                      style="min-width: 280px; flex: 1"
                    />
                  </n-space>
                </div>
              </n-space>
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="适用范围组合 (多指标时)">
              <n-radio-group v-model:value="form.applicableMode" size="small">
                <n-radio value="ALL">全部满足 (AND)</n-radio>
                <n-radio value="ANY">任一满足 (OR)</n-radio>
              </n-radio-group>
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="是否启用">
              <n-switch v-model:value="form.statusActive">
                <template #checked>启用</template>
                <template #unchecked>停用</template>
              </n-switch>
            </n-form-item>
          </n-grid-item>
          <n-grid-item>
            <n-form-item label="是否校验简历评分">
              <n-switch v-model:value="form.validateResumeScore" />
            </n-form-item>
          </n-grid-item>
        </n-grid>
        <n-form-item label="流程描述">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="可选" />
        </n-form-item>
      </n-form>

      <!-- ====== 流程阶段 ====== -->
      <n-divider title-placement="left">流程阶段 (7 阶段: 起 2 + 中间 5 + 终 1)</n-divider>
      <n-alert type="info" :show-icon="false" style="margin-bottom: 12px; font-size: 12px">
        起止阶段 (初评/正式录用) 不可删除。中间 5 个业务阶段可单独配置或删除。系统提供 7 阶段标准模板, 可编辑后保存。
      </n-alert>

      <n-spin :show="stageLoading">
        <div class="stage-list">
          <div
            v-for="(stage, idx) in stages"
            :key="String(stage.id || stage.code || idx)"
            class="stage-row"
            :class="{ 'stage-row-selected': selectedStageIdx === idx }"
            @click.self="selectedStageIdx = idx"
          >
            <div class="stage-num">{{ Number(idx) + 1 }}</div>
            <div class="stage-info">
              <div class="stage-name">
                <n-tag v-if="stage.isStart" type="success" size="small">起始</n-tag>
                <n-tag v-if="stage.isEnd" type="warning" size="small">结束</n-tag>
                <n-tag :type="getStageTypeColor(stage.stageType)" size="small">
                  {{ stage.stageType || 'FILTER' }}
                </n-tag>
                <span class="name-text">{{ stage.name }}</span>
                <n-text v-if="stage.code" depth="3" style="font-size: 11px">{{ stage.code }}</n-text>
                <n-tag v-if="selectedStageIdx === idx" type="primary" size="small" style="margin-left: 6px">已选</n-tag>
              </div>
              <div class="stage-limit">
                <n-input-number
                  v-model:value="stage.stageLimit"
                  :min="0"
                  size="small"
                  placeholder="阶段限时 (h)"
                  style="width: 130px"
                />
              </div>
            </div>
            <div class="stage-actions">
              <n-button size="small" text type="primary" @click.stop="openStageRuleConfig(stage)">配置阶段规则</n-button>
              <n-button size="small" text type="primary" @click.stop="openEntryCondition(stage)">配置进入条件</n-button>
              <n-popconfirm
                v-if="!stage.isStart && !stage.isEnd"
                @positive-click="removeStage(idx)"
              >
                <template #trigger>
                  <n-button size="small" text type="error">删除</n-button>
                </template>
                确定删除阶段「{{ stage.name }}」？
              </n-popconfirm>
              <n-tag v-else type="default" size="small">起止不可删</n-tag>
            </div>
          </div>
        </div>
      </n-spin>

      <n-space style="margin-top: 12px">
        <n-button size="small" type="primary" dashed @click="addStage('preceding')" :disabled="selectedStageIdx === null">
          <template #icon>+</template>
          在选中前插入
        </n-button>
        <n-button size="small" type="primary" dashed @click="addStage('following')" :disabled="selectedStageIdx === null">
          <template #icon>+</template>
          在选中后插入
        </n-button>
        <n-button size="small" type="default" dashed @click="addStage('end')">
          <template #icon>+</template>
          追加到末尾
        </n-button>
        <n-popconfirm @positive-click="removeSelectedStage">
          <template #trigger>
            <n-button size="small" type="error" dashed :disabled="selectedStageIdx === null">
              <template #icon>×</template>
              删除选中
            </n-button>
          </template>
          确定删除选中的阶段？
        </n-popconfirm>
        <n-text depth="3" style="font-size: 12px">
          {{
            selectedStageIdx === null
              ? '未选中任何阶段 (点阶段行的空白处选中)'
              : `已选中第 ${selectedStageIdx + 1} 行`
          }}
          · 可选阶段库: {{ availableToAdd.length }} 个
        </n-text>
      </n-space>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="saving" @click="handleSubmit">确认</n-button>
      </n-space>
    </template>

    <!-- 配置阶段规则 modal (嵌套) -->
    <StageRuleConfigModal
      v-model:show="showRuleConfig"
      :stage="ruleEditingStage"
      :link-id="ruleEditingLinkId"
      :initial-tab="showRuleConfigTab"
      @saved="onRuleSaved"
    />
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, h, computed } from 'vue'
import {
  NModal, NForm, NFormItem, NInput, NInputNumber, NSwitch, NSelect, NButton, NSpace,
  NDivider, NAlert, NSpin, NTag, NPopconfirm, NGrid, NGridItem, NText, useMessage,
} from 'naive-ui'
import {
  listProcesses, getProcess, createProcess, updateProcess,
  listStages, listProcessLinks, addProcessLink, deleteProcessLink, updateProcessLink,
  upsertStageRule, upsertEntryCondition,
} from '../../api/recruitment-process'
import StageRuleConfigModal from './StageRuleConfigModal.vue'
import type { TagType } from '../../api/offer'

// 阶段类型颜色映射
const STAGE_TYPE_COLOR: Record<string, string> = {
  FILTER: 'info',
  INTERVIEW: 'success',
  OFFER: 'warning',
  ONBOARDING: 'error',
  INVITATION: 'default',
}

const props = defineProps<{
  show: boolean
  editing: any | null
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'saved'): void
}>()

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const stageLoading = ref(false)
const deptLoading = ref(false)
const deptOptions = ref<{ label: string; value: string }[]>([])

// 7 阶段标准模板 (按顺序: 1=起, 7=终)
const STANDARD_STAGES = [
  { code: 'P001', name: '初评',         stageType: 'FILTER',     isStart: true,  isEnd: false, stageLimit: 24 },
  { code: 'P010', name: 'HRBP 评估',    stageType: 'FILTER',     isStart: false, isEnd: false, stageLimit: 48 },
  { code: 'P011', name: '用人经理评估',  stageType: 'FILTER',     isStart: false, isEnd: false, stageLimit: 48 },
  { code: 'P012', name: '邀约面试',      stageType: 'INVITATION', isStart: false, isEnd: false, stageLimit: 72 },
  { code: 'P013', name: '联合面试',      stageType: 'INTERVIEW',  isStart: false, isEnd: false, stageLimit: 72 },
  { code: 'P014', name: '待入职',        stageType: 'ONBOARDING', isStart: false, isEnd: false, stageLimit: 168 },
  { code: 'P002', name: '正式录用',      stageType: 'ONBOARDING', isStart: false, isEnd: true,  stageLimit: 720 },
]

// 2026-06-17: 适用范围 4 指标 — 每行 key 固定, 配 mode (含/不含) + values (多选)
type ScopeKey = 'department' | 'level' | 'position' | 'user'
interface ScopeIndicator {
  key: ScopeKey
  mode: 'include' | 'exclude'
  values: string[]
  options: { label: string; value: string }[]
  loading: boolean
}
const SCOPE_INDICATOR_META: Record<ScopeKey, { label: string; tagType: 'info' | 'success' | 'warning' | 'error' }> = {
  department: { label: '需求部门', tagType: 'info' },
  level:     { label: '需求职级', tagType: 'success' },
  position:  { label: '需求职务', tagType: 'warning' },
  user:      { label: '登录人',   tagType: 'error' },
}
// 静态职级选项 (User.level 字段是 CharField, 不受 choices 约束, seed 也没填)
// 覆盖行业通用 P1-P7 (专业级) + M1-M4 (管理级)
const LEVEL_OPTIONS = [
  { label: 'P1 (助理)', value: 'P1' },
  { label: 'P2 (专员)', value: 'P2' },
  { label: 'P3 (高级专员)', value: 'P3' },
  { label: 'P4 (资深)', value: 'P4' },
  { label: 'P5 (专家)', value: 'P5' },
  { label: 'P6 (高级专家)', value: 'P6' },
  { label: 'P7 (资深专家)', value: 'P7' },
  { label: 'M1 (主管)', value: 'M1' },
  { label: 'M2 (经理)', value: 'M2' },
  { label: 'M3 (高级经理)', value: 'M3' },
  { label: 'M4 (总监)', value: 'M4' },
]

const form = reactive({
  name: '',
  description: '',
  statusActive: true,
  validateResumeScore: true,
  applicableMode: 'ALL' as 'ALL' | 'ANY',  // 多指标组合: ALL=全部满足, ANY=任一满足
  applicableIndicators: [
    { key: 'department', mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
    { key: 'level',     mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
    { key: 'position',  mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
    { key: 'user',      mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
  ] as ScopeIndicator[],
})

// 当前流程下的所有 link (含 serverId - 已有链接,  vs localOnly - 仅本地)
const stages = ref<any[]>([])
const availableToAdd = ref<any[]>([])

// 2026-06-17: 选中的阶段 idx, 用于「添加前序/后序」+ 「删除」操作
//   点击 stage-row (空白处) 选中, 再点底部「在选中前/后插入」+「删除选中」按钮
const selectedStageIdx = ref<number | null>(null)

// 嵌套 rule config modal 状态
const showRuleConfig = ref(false)
const showRuleConfigTab = ref<'auto' | 'handler' | 'timelimit' | 'interview' | 'condition'>('auto')
const ruleEditingStage = ref<any>(null)
const ruleEditingLinkId = ref<string | null>(null)

function getStageTypeColor(t: string): TagType {
  return (STAGE_TYPE_COLOR as Record<string, TagType>)[t] || 'default'
}

// ==================== 监听 open 加载 ====================
watch(() => props.show, async (v) => {
  if (!v) return
  await loadDepartments()
  if (props.editing) {
    // 编辑模式
    Object.assign(form, {
      name: props.editing.name || '',
      description: props.editing.description || '',
      statusActive: props.editing.status === 'ACTIVE',
      validateResumeScore: props.editing.validateResumeScore ?? true,
      applicableMode: props.editing.applicableMode || 'ALL',
    })
    // 从 BE 的 applicable_scope JSONField 反序列化 4 指标
    // 兼容老格式: {items, expression} 直接进 mode
    const scope = props.editing.applicableScope || {}
    const incoming = Array.isArray(scope.indicators) ? scope.indicators : []
    for (const ind of form.applicableIndicators) {
      const found = incoming.find((x: any) => x.key === ind.key)
      if (found) {
        ind.mode = found.mode || 'include'
        ind.values = Array.isArray(found.values) ? [...found.values] : []
      } else {
        ind.mode = 'include'
        ind.values = []
      }
    }
    // 兼容老字段 (旧数据还可能在 applicableDepartments)
    const depInd = form.applicableIndicators.find(i => i.key === 'department')
    if (depInd && depInd.values.length === 0 && Array.isArray(props.editing.applicableDepartments)) {
      depInd.values = [...props.editing.applicableDepartments]
    }
    await loadExistingStages(props.editing.id)
  } else {
    // 新建模式 - 用 7 阶段标准模板
    Object.assign(form, {
      name: '', description: '', statusActive: true, validateResumeScore: true,
      applicableMode: 'ALL',
      applicableIndicators: [
        { key: 'department', mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
        { key: 'level',     mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
        { key: 'position',  mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
        { key: 'user',      mode: 'include', values: [], options: [], loading: false } as ScopeIndicator,
      ],
    })
    stages.value = STANDARD_STAGES.map(s => ({ ...s, _local: true }))
    await loadAvailableStages()
  }
})

async function loadDepartments() {
  deptLoading.value = true
  try {
    // 同时拉部门/职务/登录人 3 个值源 (一次性塞进 form.applicableIndicators 的 options)
    const { default: axios } = await import('axios')
    const cfg = (await import('../../config')).default
    const token = localStorage.getItem('token')
    const auth = { headers: { Authorization: `Bearer ${token}` } }
    const base = cfg.api.baseUrl

    // 并行 3 个请求
    const [deptRes, posRes, userRes] = await Promise.all([
      axios.get(`${base}/departments/`, auth).catch(() => ({ data: { data: [] } })),
      axios.get(`${base}/positions/`,   auth).catch(() => ({ data: { data: [] } })),
      axios.get(`${base}/users/`,       auth).catch(() => ({ data: { data: [] } })),
    ])

    const deptList = deptRes.data?.data || []
    const posList  = posRes.data?.data  || []
    const userList = userRes.data?.data || []

    deptOptions.value = deptList.map((d: any) => ({ label: d.name, value: d.id }))

    // 写入 indicators 的 options
    const find = (key: ScopeKey) => form.applicableIndicators.find(i => i.key === key)
    const depInd = find('department'); if (depInd) depInd.options = deptList.map((d: any) => ({ label: d.name, value: d.id }))
    const lvlInd = find('level');     if (lvlInd) lvlInd.options = LEVEL_OPTIONS
    const posInd = find('position');  if (posInd) posInd.options = posList.map((p: any) => ({ label: p.title || p.name || p.code, value: p.id }))
    const usrInd = find('user');      if (usrInd) usrInd.options = userList.map((u: any) => ({ label: u.realName || u.username, value: u.id }))

    // 兼容旧字段 (可能还有代码读 applicableDepartments)
    // 加载后从 indicators 反向同步过去
    const depIndSync = find('department')
    if (depIndSync) {
      form.applicableDepartments = [...depIndSync.values]
    }
  } catch {
    deptOptions.value = []
  } finally {
    deptLoading.value = false
  }
}

async function loadExistingStages(processId: string) {
  stageLoading.value = true
  try {
    const links = await listProcessLinks(processId)
    stages.value = links
      .sort((a: any, b: any) => a.orderIndex - b.orderIndex)
      .map((l: any) => ({
        id: l.id, // processStageLink.id
        code: l.stage?.code,
        name: l.customName || l.stage?.name,
        stageType: l.stage?.stageType,
        isStart: l.isStart,
        isEnd: l.isEnd,
        stageLimit: l.stageLimit,
        _linkId: l.id,
        _stageId: l.stageId,
      }))
    await loadAvailableStages(processId)
  } finally {
    stageLoading.value = false
  }
}

async function loadAvailableStages(excludeProcessId?: string) {
  try {
    // 2026-06-17: 修 — BE RecruitmentStage.status 枚举是 ENABLED/DISABLED (StageStatus TextChoices),
    //             FE 之前发 ACTIVE/INACTIVE → 400 validation_error. 改 ENABLED 即可.
    const all = await listStages({ status: 'ENABLED' })
    const usedCodes = new Set(stages.value.map(s => s.code).filter(Boolean))
    availableToAdd.value = all.filter(s => !usedCodes.has(s.code))
  } catch (e: any) {
    message.error(e?.response?.data?.message || '阶段库加载失败')
  }
}

function addStage(position: 'preceding' | 'following' | 'end' = 'end') {
  // 2026-06-17: 基于选中阶段 (selectedStageIdx) 插入 — 前序/后序
  if (availableToAdd.value.length === 0) {
    message.warning('暂无可添加阶段')
    return
  }
  const s = availableToAdd.value[0]
  let insertIdx: number
  if (position === 'preceding' && selectedStageIdx.value !== null) {
    insertIdx = selectedStageIdx.value  // 插到选中之前
  } else if (position === 'following' && selectedStageIdx.value !== null) {
    insertIdx = selectedStageIdx.value + 1  // 插到选中之后
  } else {
    // 默认 / 无选中 → 插到倒数第二 (「正式录用」之前)
    insertIdx = Math.max(0, stages.value.length - 1)
  }
  stages.value.splice(insertIdx, 0, {
    code: s.code,
    name: s.name,
    stageType: s.stageType,
    isStart: false,
    isEnd: false,
    stageLimit: 72,
    _local: true,
  })
  // 新插入的 stage 自动选中 (方便用户继续加前序/后序)
  selectedStageIdx.value = insertIdx
  // 更新 available
  availableToAdd.value = availableToAdd.value.filter(x => x.code !== s.code)
}

function removeSelectedStage() {
  if (selectedStageIdx.value === null) {
    message.warning('请先选中一个阶段 (点阶段行的空白处)')
    return
  }
  removeStage(selectedStageIdx.value)
  selectedStageIdx.value = null
}

function removeStage(idx: number) {
  const s = stages.value[idx]
  if (s._linkId) {
    // 已存在的 link, 标记为待删除
    s._toDelete = true
  }
  stages.value.splice(idx, 1)
  // 重新放回 available
  if (s.code) {
    availableToAdd.value.push({ code: s.code, name: s.name, stageType: s.stageType })
  }
}

function openStageRuleConfig(stage: any) {
  if (!stage._linkId) {
    message.warning('请先保存流程, 再配置阶段规则')
    return
  }
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId
  showRuleConfigTab.value = 'auto'  // 2026-06-17: 默认打开「自动化流转」tab
  showRuleConfig.value = true
}

function openEntryCondition(stage: any) {
  if (!stage._linkId) {
    message.warning('请先保存流程, 再配置进入条件')
    return
  }
  // 2026-06-17: 之前是 message.info 告诉用户去「配置阶段规则」tab — 太绕了.
  //   现在直接打开同一个 modal 但默认 tab 是「进入条件」.
  ruleEditingStage.value = stage
  ruleEditingLinkId.value = stage._linkId
  showRuleConfigTab.value = 'condition'  // 直接打开「进入条件」tab
  showRuleConfig.value = true
}

function onRuleSaved() {
  message.success('规则已保存')
}

async function handleSubmit() {
  if (!form.name.trim()) {
    message.error('流程名称必填')
    return
  }
  saving.value = true
  try {
    let processId: string
    if (props.editing) {
      // 更新基础信息
      await updateProcess(props.editing.id, {
        name: form.name,
        description: form.description,
        status: form.statusActive ? 'ACTIVE' : 'INACTIVE',
        validateResumeScore: form.validateResumeScore,
        // 2026-06-17: 4 指标 → 序列化到 applicable_scope JSONField (BE 原字段无 schema 变化)
        applicableScope: {
          mode: form.applicableMode,
          indicators: form.applicableIndicators
            .filter((ind: ScopeIndicator) => ind.values.length > 0)
            .map((ind: ScopeIndicator) => ({ key: ind.key, mode: ind.mode, values: [...ind.values] })),
        },
      })
      processId = props.editing.id
    } else {
      // 创建
      const created = await createProcess({
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        applicableScope: {
          mode: form.applicableMode,
          indicators: form.applicableIndicators
            .filter((ind: ScopeIndicator) => ind.values.length > 0)
            .map((ind: ScopeIndicator) => ({ key: ind.key, mode: ind.mode, values: [...ind.values] })),
        },
      })
      processId = created.id
    }

    // 处理阶段 link 变化
    if (!props.editing) {
      // 新建 - 删除默认起止, 按 stages 顺序重建
      const existingLinks = await listProcessLinks(processId)
      for (const l of existingLinks) {
        await deleteProcessLink(l.id).catch(() => {})
      }
      for (let i = 0; i < stages.value.length; i++) {
        const s = stages.value[i]
        // 找 stageId (系统阶段 P001/P002 直接 lookup, 业务阶段也查)
        // 简化: 用 listStages 找 code → id
        if (!s._stageId && s.code) {
          const allStages = await listStages()
          const st = allStages.find(x => x.code === s.code)
          if (st) s._stageId = st.id
        }
        if (!s._stageId) {
          message.error(`阶段 ${s.name} 找不到全局模板`)
          continue
        }
        await addProcessLink({
          processId,
          stageId: s._stageId,
          orderIndex: i,
          customName: s.name !== s.code ? s.name : undefined,
        })
      }
    } else {
      // 编辑 - 更新每个 link 的 stageLimit
      for (const s of stages.value) {
        if (s._linkId) {
          await updateProcessLink(s._linkId, {
            stageLimit: s.stageLimit || undefined,
          }).catch(() => {})
        }
      }
    }

    message.success(props.editing ? '已更新' : '已创建')
    emit('saved')
    emit('update:show', false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.stage-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
  padding: 4px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background: #fafafa;
}
.stage-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  padding: 10px 12px;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.stage-row:hover {
  border-color: #b0d4ff;
  background: #f5faff;
}
/* 2026-06-17: 选中高亮 (操作"添加前序/后序/删除选中" 按钮依赖 selectedStageIdx) */
.stage-row-selected {
  border-color: #FBCE5B;
  background: #fffbe6;
  box-shadow: 0 0 0 2px rgba(251, 206, 91, 0.2);
}
.stage-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2080f0;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
}
.stage-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.stage-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
.name-text {
  font-weight: 500;
  font-size: 14px;
}
.stage-actions {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}
</style>

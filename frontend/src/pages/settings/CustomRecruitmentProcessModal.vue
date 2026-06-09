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
          <n-grid-item>
            <n-form-item label="适用部门 (多选)">
              <n-select
                v-model:value="form.applicableDepartments"
                multiple
                filterable
                :options="deptOptions"
                placeholder="留空 = 全部"
                :loading="deptLoading"
              />
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
              <n-button size="small" text type="primary" @click="openStageRuleConfig(stage)">配置阶段规则</n-button>
              <n-button size="small" text type="primary" @click="openEntryCondition(stage)">配置进入条件</n-button>
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
        <n-button size="small" type="primary" dashed @click="addStage">
          <template #icon>+</template>
          添加前序阶段
        </n-button>
        <n-text depth="3" style="font-size: 12px">
          可选阶段库: {{ availableToAdd.length }} 个
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
      @saved="onRuleSaved"
    />
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, h } from 'vue'
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

const form = reactive({
  name: '',
  description: '',
  statusActive: true,
  validateResumeScore: true,
  applicableDepartments: [] as string[],
  applicableMode: 'ALL' as 'ALL' | 'ANY',
})

// 当前流程下的所有 link (含 serverId - 已有链接,  vs localOnly - 仅本地)
const stages = ref<any[]>([])
const availableToAdd = ref<any[]>([])

// 嵌套 rule config modal 状态
const showRuleConfig = ref(false)
const ruleEditingStage = ref<any>(null)
const ruleEditingLinkId = ref<string | null>(null)

function getStageTypeColor(t: string) {
  return ({ FILTER: 'info', INTERVIEW: 'success', OFFER: 'warning', ONBOARDING: 'error', INVITATION: 'default' } as any)[t] || 'default'
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
      applicableDepartments: props.editing.applicableDepartments || [],
      applicableMode: props.editing.applicableMode || 'ALL',
    })
    await loadExistingStages(props.editing.id)
  } else {
    // 新建模式 - 用 7 阶段标准模板
    Object.assign(form, {
      name: '', description: '', statusActive: true, validateResumeScore: true,
      applicableDepartments: [], applicableMode: 'ALL',
    })
    stages.value = STANDARD_STAGES.map(s => ({ ...s, _local: true }))
    await loadAvailableStages()
  }
})

async function loadDepartments() {
  deptLoading.value = true
  try {
    // 简单从后端拉, 走 /api/departments
    const { default: axios } = await import('axios')
    const cfg = (await import('../../config')).default
    const token = localStorage.getItem('token')
    const res = await axios.get(`${cfg.api.baseUrl}/departments`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const list = res.data?.data || []
    deptOptions.value = list.map((d: any) => ({ label: d.name, value: d.id }))
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
    const all = await listStages({ status: 'ACTIVE' })
    const usedCodes = new Set(stages.value.map(s => s.code).filter(Boolean))
    availableToAdd.value = all.filter(s => !usedCodes.has(s.code))
  } catch (e: any) {
    message.error(e?.response?.data?.message || '阶段库加载失败')
  }
}

function addStage() {
  // 简化: 取第一个可添加的阶段
  if (availableToAdd.value.length === 0) {
    message.warning('暂无可添加阶段')
    return
  }
  const s = availableToAdd.value[0]
  // 插入到倒数第二 (正式录用之前)
  const insertIdx = stages.value.length - 1
  stages.value.splice(insertIdx, 0, {
    code: s.code,
    name: s.name,
    stageType: s.stageType,
    isStart: false,
    isEnd: false,
    stageLimit: 72,
    _local: true,
  })
  // 更新 available
  availableToAdd.value = availableToAdd.value.filter(x => x.code !== s.code)
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
  showRuleConfig.value = true
}

function openEntryCondition(stage: any) {
  if (!stage._linkId) {
    message.warning('请先保存流程, 再配置进入条件')
    return
  }
  // 复用 stage rule modal 的 tab 设计 - 此处直接路由
  message.info(`进入条件: 阶段 ${stage.name} (请使用「配置阶段规则」中的进入条件 tab)`)
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
        applicableDepartments: form.applicableDepartments,
        applicableMode: form.applicableMode,
      })
      processId = props.editing.id
    } else {
      // 创建
      const created = await createProcess({
        name: form.name,
        description: form.description,
        validateResumeScore: form.validateResumeScore,
        applicableDepartments: form.applicableDepartments,
        applicableMode: form.applicableMode,
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

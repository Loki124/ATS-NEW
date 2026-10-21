<template>
  <div class="candidate-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-title">
        <h1>{{ t('pages.candidate.CandidateList.s1') }}</h1>
        <n-text :depth="3">{{ t('pages.candidate.CandidateList.s2') }}</n-text>
      </div>
      <n-space>
        <n-button type="primary" :disabled="selectedCandidates.length === 0" class="batch-notify-btn" @click="openBatchNotificationModal">
          <template #icon><n-icon :component="PaperPlaneOutline" /></template>
          {{ t('pages.candidate.CandidateList.s52', { n: selectedCandidates.length }) }}
        </n-button>
        <n-button type="primary" size="large" class="add-button" data-testid="add-candidate-btn" @click="showAddModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          {{ t('pages.candidate.CandidateList.s3') }}
        </n-button>
      </n-space>
    </div>

    <!-- 招聘流程管道：流程选择 + 阶段可点击统计卡片 -->
    <div class="pipeline-board mb-4">
      <div class="pipeline-board-head">
        <div class="pipeline-board-title">
          <n-icon :component="GitNetworkOutline" class="pb-icon" />
          <span>招聘流程管道</span>
        </div>
        <n-select
          v-model:value="selectedProcessId"
          :options="processOptions"
          placeholder="选择招聘流程"
          :loading="processLoading"
          size="medium"
          style="width: 260px"
          @update:value="onProcessChange"
        />
      </div>

      <n-empty
        v-if="!selectedProcessId && !processLoading"
        description="选择上方招聘流程，查看各阶段候选人统计"
        class="pipeline-empty"
      />
      <div v-else-if="stagesLoading" class="pipeline-loading">阶段统计加载中…</div>
      <div v-else-if="pipelineStages.length" class="pipeline-track">
        <button
          type="button"
          class="stage-card stage-card--edge stage-card--all"
          :class="{ active: selectedStageLinkId === ALL_KEY }"
          @click="toggleAllInProcess()"
        >
          <span class="stage-name">全部</span>
          <span class="stage-type">汇总</span>
          <span class="stage-count-row">
            <span class="stage-count">{{ processTotalCount }}</span>
            <span class="stage-unit">人</span>
          </span>
        </button>
        <button
          v-for="(stage, idx) in pipelineStages"
          :key="stage.linkId"
          type="button"
          class="stage-card"
          :class="{ active: selectedStageLinkId === stage.linkId }"
          @click="toggleStage(stage)"
        >
          <span class="stage-index">{{ idx + 1 }}</span>
          <span class="stage-name">{{ stage.name }}</span>
          <span class="stage-type">{{ stageTypeLabel(stage.stageType) }}</span>
          <span class="stage-count-row">
            <span class="stage-count">{{ stage.count }}</span>
            <span class="stage-unit">人</span>
          </span>
        </button>
        <button
          type="button"
          class="stage-card stage-card--edge stage-card--archived"
          :class="{ active: selectedStageLinkId === ARCHIVED_KEY }"
          @click="toggleArchived()"
        >
          <span class="stage-name">已归档</span>
          <span class="stage-type stage-type--muted">终态</span>
          <span class="stage-count-row">
            <span class="stage-count">{{ archivedCount }}</span>
            <span class="stage-unit">人</span>
          </span>
        </button>
      </div>
      <n-empty v-else description="该流程暂无阶段配置" class="pipeline-empty" />

      <div v-if="selectedStageLinkId" class="pipeline-active-hint">
        <n-tag type="primary" round size="small" :bordered="false">
          {{ activeStageName }} · {{ activeStageCount }} 人
        </n-tag>
        <n-button
          text
          size="small"
          type="primary"
          :disabled="stageFilterLoading"
          @click="clearStageFilter"
        >
          清除筛选
        </n-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <n-card class="filter-card mb-4">
      <n-space :size="12" :wrap="true" align="center">
        <n-input
          v-model:value="searchText"
          :placeholder="t('pages.candidate.CandidateList.s4')"
          clearable
          style="width: 260px"
          @keyup.enter="handleSearch"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select v-model:value="positionTypeFilter" :placeholder="t('pages.candidate.CandidateList.s5')" style="width: 140px" clearable :options="positionTypeOptions" />
        <n-select v-model:value="positionFilter" :placeholder="t('pages.candidate.CandidateList.s6')" style="width: 160px" clearable :options="positionOptions" />
        <n-select v-model:value="demandFilter" :placeholder="t('pages.candidate.CandidateList.s7')" style="width: 150px" clearable :options="demandOptions" />
        <n-select v-model:value="departmentFilter" :placeholder="t('pages.candidate.CandidateList.s8')" style="width: 140px" clearable :options="departmentOptions" />
        <n-select v-model:value="channelFilter" :placeholder="t('pages.candidate.CandidateList.s9')" style="width: 130px" clearable :options="channelOptions" />
        <n-select
          v-model:value="ruleSceneFilter"
          :placeholder="t('pages.candidate.CandidateList.s10')"
          style="width: 150px"
          clearable
          :options="ruleSceneOptions"
          @update:value="loadCandidates"
        />
        <n-button @click="showMoreFilter">
          <template #icon><n-icon :component="FunnelOutline" /></template>
          {{ t('pages.candidate.CandidateList.s11') }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 快捷筛选 + 批量操作 -->
    <n-card :bordered="false" class="action-filter-card mb-4">
      <div class="action-filter-bar">
        <n-space :size="8" :wrap="true">
          <n-button
            size="small"
            round
            :type="statusFilter === null ? 'primary' : 'default'"
            @click="setStatusFilter(null)"
          >
            {{ t('pages.candidate.CandidateList.s12') }}
          </n-button>
          <n-button
            v-for="s in quickFilters"
            :key="s.key"
            size="small"
            round
            :type="statusFilter === s.key ? 'primary' : 'default'"
            @click="setStatusFilter(s.key)"
          >
            {{ s.label }}
          </n-button>
        </n-space>
        <n-space :size="8">
          <n-button size="small" @click="message.info('批量导入人才库功能开发中')">
            <template #icon><n-icon :component="CloudUploadOutline" /></template>
            {{ t('pages.candidate.CandidateList.s13') }}
          </n-button>
          <n-button size="small" @click="message.info('批量分配职位功能开发中')">
            <template #icon><n-icon :component="GitPullRequestOutline" /></template>
            {{ t('pages.candidate.CandidateList.s14') }}
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 候选人卡片列表 -->
    <n-card class="list-card">
      <n-checkbox-group v-model:value="selectedKeys">
        <div class="candidate-list">
          <!-- 2026-10-21：整卡可点进入详情；checkbox 与右侧操作区 stop 防误触 -->
          <div v-for="row in rows" :key="row.key" class="candidate-row" @click="handleViewDetail(row)">
            <div class="row-checkbox" @click.stop>
              <n-checkbox :value="row.key" />
            </div>
            <div class="row-main">
              <div class="row-top">
                <!-- 左列：标题行（姓名+编号+次数+标签）/ 资料行 / 投递行 -->
                <div class="row-left">
                  <div class="card-head">
                    <span class="candidate-name">{{ row.name }}</span>
                    <span class="candidate-code">（{{ row.code || row.id }}）</span>
                    <span v-if="row.applicationCount" class="apply-count">{{ row.applicationCount }}次</span>
                    <span
                      v-for="tag in row.tags"
                      :key="tag.label"
                      class="mini-tag"
                      :class="`mini-tag--${tag.type}`"
                    >{{ tag.label }}</span>
                  </div>
                  <div v-if="row.infoPieces.length" class="info-line">
                    <template v-for="(piece, i) in row.infoPieces" :key="i">
                      <span v-if="i > 0" class="info-divider">|</span>
                      <span class="info-piece">{{ piece }}</span>
                    </template>
                  </div>
                  <div v-if="row.applyLine" class="apply-line" :title="row.applyLine">{{ row.applyLine }}</div>
                </div>
                <!-- 中列：工作经历（接口未返回时整列隐藏，数据驱动） -->
                <div v-if="row.workExperiences.length" class="row-mid">
                  <div
                    v-for="(exp, idx) in row.workExperiences.slice(0, 3)"
                    :key="idx"
                    class="work-item"
                  >
                    <span class="work-date">{{ exp.start }} ~ {{ exp.end }}</span>
                    <span class="work-company">{{ exp.company }}</span>
                    <template v-if="exp.position">
                      <span class="work-divider">|</span>
                      <span class="work-position">{{ exp.position }}</span>
                    </template>
                  </div>
                </div>
                <!-- 右列：阶段流转（label：value 行） -->
                <div class="row-right">
                  <div v-for="st in row.stageLines" :key="st.label" class="stage-line">
                    <span class="stage-label">{{ st.label }}：</span>
                    <span class="stage-value" :class="st.cls">{{ st.value }}</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 右上操作：更多 ⋯ 下拉（查看详情/转发简历/安排面试） + 备注（stop：不触发整卡跳转） -->
            <div class="row-actions" @click.stop>
              <n-dropdown
                trigger="click"
                :options="[
                  { label: t('pages.candidate.CandidateList.s19'), key: 'detail' },
                  { label: '转发简历', key: 'forward' },
                  { label: '安排面试', key: 'interview' },
                ]"
                @select="(k: string) => onRowAction(k, row)"
              >
                <button class="more-btn" type="button" aria-label="更多操作">
                  <n-icon :component="EllipsisHorizontal" />
                </button>
              </n-dropdown>
              <button class="note-btn" type="button" @click="onCandidateRowAction('note', row)">备 注</button>
            </div>
          </div>
        </div>
      </n-checkbox-group>

      <n-empty
        v-if="!listLoading && rows.length === 0"
        description="暂无候选人数据"
        class="candidate-empty"
      />

      <!-- 分页 -->
      <div class="list-pagination">
        <n-pagination
          v-model:page="paginationReactive.page"
          v-model:page-size="paginationReactive.pageSize"
          :item-count="paginationReactive.itemCount"
          :page-sizes="[10, 20, 50]"
          show-size-picker
          show-quick-jumper
        />
        <span class="pagination-total">{{ t('pages.candidate.CandidateList.s21') }}{{ paginationReactive.itemCount }}{{ t('pages.candidate.CandidateList.s22') }}</span>
      </div>
    </n-card>

    <!-- 新增候选人弹窗 V2 -->
    <AddCandidateModal
      v-model:show="addModalVisible"
      @created="handleAddSuccess"
    />

    <!-- 批量发送通知弹窗 -->
    <n-modal
      v-model:show="batchNotificationModalVisible"
      :width="1000"
      :mask-closable="false"
      preset="card"
      class="notification-modal"
    >
      <template #header>
        <div class="modal-header">
          <span class="modal-title">{{ t('pages.candidate.CandidateList.s23') }}</span>
          <button class="close-btn" @click="batchNotificationModalVisible = false">
            <n-icon :component="CloseOutline" />
          </button>
        </div>
        <div class="candidate-summary">
          <n-avatar :size="48" class="candidate-avatar-sm">
            {{ selectedCandidates.length }}
          </n-avatar>
          <div class="candidate-info">
            <div class="candidate-name-row">
              <span class="candidate-name">{{ t('pages.candidate.CandidateList.s24') }}{{ selectedCandidates.length }}{{ t('pages.candidate.CandidateList.s25') }}</span>
            </div>
            <div class="candidate-contact-row">
              <span>{{ t('pages.candidate.CandidateList.s26') }}</span>
            </div>
          </div>
        </div>
      </template>

      <div class="modal-content">
        <!-- 左侧选择区域 -->
        <div class="left-sidebar">
          <!-- Step 1: 选择发送内容 -->
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">1</span>
              {{ t('pages.candidate.CandidateList.s27') }}
            </h3>
            <div class="step-content">
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateList.s28') }}</div>
                <label class="content-item selected">
                  <n-checkbox v-model:checked="notificationForm.interviewForm" />
                  <span>{{ t('pages.candidate.CandidateList.s29') }}</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateList.s30') }}</div>
                <n-radio-group v-model:value="notificationForm.personalityTest">
                  <n-space vertical>
                    <n-radio value="pdp_mbti_20">{{ t('pages.candidate.CandidateList.s31') }}</n-radio>
                    <n-radio value="pdp_mbti_93">{{ t('pages.candidate.CandidateList.s32') }}</n-radio>
                  </n-space>
                </n-radio-group>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateList.s33') }}</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.applicationForm" />
                  <span>{{ t('pages.candidate.CandidateList.s34') }}</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">{{ t('pages.candidate.CandidateList.s35') }}</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.onboardingDocs" />
                  <span>{{ t('pages.candidate.CandidateList.s36') }}</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Step 2: 选择通知方式 -->
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">2</span>
              {{ t('pages.candidate.CandidateList.s37') }}
            </h3>
            <div class="step-content">
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendEmail" />
                <n-icon :component="MailOutline" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateList.s38') }}</span>
              </label>
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendSms" />
                <n-icon :component="ChatbubblesOutline" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateList.s39') }}</span>
              </label>
              <label class="method-item">
                <n-checkbox v-model:checked="notificationForm.sendWechat" />
                <n-icon :component="LogoWechat" class="method-icon" />
                <span class="method-name">{{ t('pages.candidate.CandidateList.s40') }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 右侧内容区域 -->
        <div class="right-content">
          <div class="info-callout">
            <span>{{ t('pages.candidate.CandidateList.s41') }}</span>
          </div>

          <div v-if="notificationForm.sendEmail" class="editor-section">
            <div class="editor-header">
              <n-icon :component="MailOutline" class="editor-icon" />
              <h4 class="editor-title">{{ t('pages.candidate.CandidateList.s42') }}</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">{{ t('pages.candidate.CandidateList.s43') }}</label>
              <n-input v-model:value="notificationForm.emailSubject" class="email-subject-input" />
            </div>
            <div class="editor-field">
              <label class="field-label">{{ t('pages.candidate.CandidateList.s44') }}</label>
              <n-input v-model:value="notificationForm.emailContent" type="textarea" :rows="8" class="email-content-input" />
            </div>
          </div>

          <div v-if="notificationForm.sendSms" class="editor-section">
            <div class="editor-header">
              <n-icon :component="ChatbubblesOutline" class="editor-icon" />
              <h4 class="editor-title">{{ t('pages.candidate.CandidateList.s45') }}</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">{{ t('pages.candidate.CandidateList.s46') }}</label>
                <span class="counter-text">{{ t('pages.candidate.CandidateList.s54', { n: notificationForm.smsContent.length }) }}<strong>{{ notificationForm.smsContent.length }}</strong>{{ t('pages.candidate.CandidateList.s47') }}</span>
              </div>
              <n-input v-model:value="notificationForm.smsContent" type="textarea" :rows="4" class="sms-content-input" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="recipient-info">{{ t('pages.candidate.CandidateList.s48') }}{{ selectedCandidates.length }}{{ t('pages.candidate.CandidateList.s49') }}</div>
          <div class="footer-buttons">
            <n-button @click="batchNotificationModalVisible = false">{{ t('pages.candidate.CandidateList.s50') }}</n-button>
            <n-button type="primary" class="send-btn-primary" @click="handleBatchSendNotification">
              <template #icon><n-icon :component="PaperPlaneOutline" /></template>
              {{ t('pages.candidate.CandidateList.s51') }}
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, h, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag, NIcon, NButton, NSpace, NAvatar, NCheckbox, NCheckboxGroup, NPagination, NDropdown } from 'naive-ui'
import {
  AddOutline,
  SearchOutline,
  FunnelOutline,
  GitNetworkOutline,
  EllipsisHorizontal,
  PaperPlaneOutline,
  CloseOutline,
  MailOutline,
  ChatbubblesOutline,
  LogoWechat,
  CloudUploadOutline,
  GitPullRequestOutline,
} from '@vicons/ionicons5'
import AddCandidateModal from './AddCandidateModal.vue'
import { fetchStatusSchema, listCandidates, type StatusSchema } from '@/api/candidate'
// 流程-阶段管道（真实数据：流程 → 阶段 → 各阶段候选人数量）
import { listProcesses, getProcess } from '@/api/recruitment-process'
import { listApplications, extractCandidateId } from '@/api/application'
// 2026-09-25: 按规则筛选（指标库 FILTER 场景）
import { filterByScene, filterBySceneAsync, getFilterTaskStatus } from '@/api/metrics'
import type { TagType } from '@/api/offer'
const { t } = useI18n()

const router = useRouter()
const message = useMessage()

type CandidateTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error'
interface CandidateItem {
  key: string
  name: string
  id: string
  /** 候选人编号 (C+8位流水号, 后端 save() 自动补号) */
  code: string
  /** 投递次数 (申请数) */
  applicationCount: number
  gender: string
  age: number
  education: string
  experience: string
  phone: string
  email: string
  location: string
  /** 资料行片段：性别 | 年龄 | 学历（年限）| 手机 | 邮箱 | 城市（空值已剔除） */
  infoPieces: string[]
  /** 投递行：yyyy.mm.dd 投递 | 渠道 | 当前职位 */
  applyLine: string
  tags: Array<{ label: string; type: CandidateTagType }>
  position: string
  channel: string
  stage: string
  createdAt: string
  workExperiences: Array<{ company: string; position: string; start: string; end: string }>
  /** 阶段流转行（现阶段/上一阶段/下一阶段 的 label：value 展示态） */
  stageLines: Array<{ label: string; value: string; cls: string }>
  stageFlow: {
    current: { name: string; status: string; date: string; handler: string; result: string }
    previous: { name: string; status: string; date: string; handler: string; result: string }
    next: { name: string; status: string; date: string; handler: string; result: string }
  }
}

const addModalVisible = ref(false)
const searchText = ref('')
const positionFilter = ref<string | undefined>()
const positionTypeFilter = ref<string | undefined>()
const demandFilter = ref<string | undefined>()
const departmentFilter = ref<string | undefined>()
const channelFilter = ref<string | undefined>()

// G44 11 状态字段筛选
const STATUS_SCHEMA = ref<Array<{ key: string; label: string; order: number }>>([])
const statusFilter = ref<string | null>(null)

onMounted(async () => {
  try {
    const schema: StatusSchema = await fetchStatusSchema()
    if (schema && typeof schema === 'object') {
      STATUS_SCHEMA.value = Object.entries(schema)
        .map(([key, v]) => ({ key, label: v.label, order: v.order }))
        .sort((a, b) => a.order - b.order)
    }
  } catch (e) {
    // 静默失败: 11 状态筛选可选
    console.warn('fetchStatusSchema 失败', e)
  }
  // 加载招聘流程管道（流程选择 → 阶段统计卡片 → 点击筛选候选人）
  await loadProcesses()
  // 拉取真实候选人列表（替换原 mockData）
  await loadCandidates()
})

function setStatusFilter(key: string | null) {
  statusFilter.value = key
  handleSearch()
}

const stageFilter = ref<string | undefined>()
const selectedKeys = ref<string[]>([])

// ===== 真实数据（2026-09-25 替换原 mockData，接 GET /api/v1/candidates/）=====
const rows = ref<CandidateItem[]>([])
const listLoading = ref(false)
/** 按规则筛选：选中后仅展示符合「筛选」场景启用规则的候选人 */
const ruleSceneFilter = ref<string | undefined>()
/** 异步筛选进度（仅候选人数超过同步上限时出现） */
const filterProgress = ref<{ current: number; total: number } | null>(null)

// ===== 招聘流程管道（流程 → 阶段 → 各阶段候选人数量 → 点击卡片筛选）=====
// 2026-10-13: 替换原硬编码 mock 统计条（pipelineStats），改为接真实流程/阶段/申请数据，
// 避免"能点但数据假"的假实现（见本文件下方 loadCandidates 历史注释）。
const STAGE_TYPE_LABELS: Record<string, string> = {
  START_END: '起止',
  SCREEN: '筛选',
  INVITATION: '邀约',
  INTERVIEW: '面试',
  ASSESSMENT: '测评',
  OFFER: 'Offer',
  OTHER: '其他',
}
function stageTypeLabel(t: string): string {
  return STAGE_TYPE_LABELS[t] || '阶段'
}

interface PipelineStage {
  linkId: string
  stageId: string
  name: string
  stageType: string
  order: number
  count: number
}

// 管道首/尾两张特殊卡片：「全部」= 该流程全部申请人；「已归档」= 终态（未通过/撤回/超时归档）
const ALL_KEY = '__all__'
const ARCHIVED_KEY = '__archived__'
const ARCHIVED_STATES = ['REJECTED', 'WITHDRAWN', 'TIMEOUT']

const processOptions = ref<{ label: string; value: string | null }[]>([])
const processLoading = ref(false)
const selectedProcessId = ref<string | null>(null)
const stagesLoading = ref(false)
const stageFilterLoading = ref(false)
const pipelineStages = ref<PipelineStage[]>([])
const selectedStageLinkId = ref<string | null>(null)
/** 当前选中（阶段/全部/已归档）对应的候选人 id 白名单（来自该流程的申请记录） */
const stageCandidateIds = ref<string[] | null>(null)
/** 「已归档」卡片计数（终态申请数） */
const archivedCount = ref(0)

/** 「全部」卡片计数 = 该流程各阶段人数之和（终态仍停留在各自阶段，故含在内） */
const processTotalCount = computed(() =>
  pipelineStages.value.reduce((sum, s) => sum + (s.count || 0), 0),
)

const activeStageName = computed(() => {
  if (selectedStageLinkId.value === ALL_KEY) return '全部'
  if (selectedStageLinkId.value === ARCHIVED_KEY) return '已归档'
  return pipelineStages.value.find((s) => s.linkId === selectedStageLinkId.value)?.name || ''
})
const activeStageCount = computed(() => {
  if (selectedStageLinkId.value === ALL_KEY) return processTotalCount.value
  if (selectedStageLinkId.value === ARCHIVED_KEY) return archivedCount.value
  return pipelineStages.value.find((s) => s.linkId === selectedStageLinkId.value)?.count ?? 0
})

/** 加载流程列表；默认选择「全部流程」（不绑定具体流程），用户可手动切换 */
async function loadProcesses() {
  processLoading.value = true
  try {
    const list = await listProcesses()
    processOptions.value = [
      { label: '全部流程', value: null },
      ...(list || []).map((p: any) => ({ label: p.name, value: p.id })),
    ]
    // 默认不选中具体流程，保持「全部流程」视角；用户选择流程后再加载阶段卡片
    selectedProcessId.value = null
  } catch (e) {
    console.warn('加载招聘流程失败', e)
  } finally {
    processLoading.value = false
  }
}

/** 加载选中流程的阶段：先并行拉取各阶段候选人数量，再一次性渲染卡片，避免卡片里显示「…」 */
async function loadProcessStages() {
  const pid = selectedProcessId.value
  pipelineStages.value = []
  selectedStageLinkId.value = null
  stageCandidateIds.value = null
  archivedCount.value = 0
  if (!pid) {
    stagesLoading.value = false
    return
  }
  stagesLoading.value = true
  try {
    const proc: any = await getProcess(pid)
    const links: any[] = proc?.stageLinks ?? proc?.stages ?? []
    const stages: PipelineStage[] = (links || [])
      .map((l: any) => {
        const stage = l.stage || l
        return {
          linkId: l.id,
          stageId: stage?.id,
          name: l.displayName || l.customName || stage?.name || '阶段',
          stageType: stage?.stageType || 'OTHER',
          order: l.order ?? 0,
          count: 0,
        }
      })
      .sort((a: PipelineStage, b: PipelineStage) => (a.order ?? 0) - (b.order ?? 0))
    // 并行统计各阶段候选人数量（pageSize=1 仅取总数，降低 payload）
    await Promise.all(
      stages.map(async (s) => {
        try {
          const res = await listApplications({ processId: pid, stageId: s.stageId, pageSize: 1 })
          s.count = res.pagination.total
        } catch {
          s.count = 0
        }
      }),
    )
    pipelineStages.value = stages
    // 「已归档」计数：终态（未通过/撤回/超时归档）申请数，并行拉取
    try {
      const counts = await Promise.all(
        ARCHIVED_STATES.map((st) =>
          listApplications({ processId: pid, state: st, pageSize: 1 }).then((r) => r.pagination.total),
        ),
      )
      archivedCount.value = counts.reduce((a, b) => a + b, 0)
    } catch {
      archivedCount.value = 0
    }
  } catch (e) {
    console.warn('加载流程阶段失败', e)
  } finally {
    stagesLoading.value = false
  }
}

async function onProcessChange(val: string | null) {
  selectedProcessId.value = val
  await loadProcessStages()
  handleSearch()
}

/**
 * 分页收集某组过滤条件（流程[+阶段 | +状态]）下的全部候选人 id（去重）。
 * 应对后端单页上限；25 页安全帽防止极端数据下无限请求。
 */
async function collectCandidateIds(base: {
  processId: string
  stageId?: string
  state?: string
}): Promise<string[]> {
  const ids = new Set<string>()
  let page = 1
  const pageSize = 200
  while (page <= 25) {
    const res = await listApplications({ ...base, page, pageSize })
    let added = 0
    for (const a of res.data || []) {
      const cid = extractCandidateId(a.candidate)
      if (cid && !ids.has(cid)) {
        ids.add(cid)
        added += 1
      }
    }
    const total = res.pagination.total
    if (ids.size >= total || added === 0) break
    page += 1
  }
  return Array.from(ids)
}

/** 应用某张卡片（阶段/全部/已归档）的候选人白名单并刷新列表 */
async function applyStageFilter(key: string, ids: string[]) {
  selectedStageLinkId.value = key
  stageCandidateIds.value = ids
  handleSearch()
}

/** 点击阶段卡片：选中即按该阶段筛选候选人；再次点击取消 */
async function toggleStage(stage: PipelineStage) {
  if (selectedStageLinkId.value === stage.linkId) {
    clearStageFilter()
    return
  }
  stageFilterLoading.value = true
  try {
    const ids = await collectCandidateIds({ processId: selectedProcessId.value as string, stageId: stage.stageId })
    await applyStageFilter(stage.linkId, ids)
  } catch {
    stageCandidateIds.value = []
  } finally {
    stageFilterLoading.value = false
  }
}

/** 点击「全部」卡片：显示该流程下所有阶段的候选人 */
async function toggleAllInProcess() {
  if (selectedStageLinkId.value === ALL_KEY) {
    clearStageFilter()
    return
  }
  stageFilterLoading.value = true
  try {
    const ids = await collectCandidateIds({ processId: selectedProcessId.value as string })
    await applyStageFilter(ALL_KEY, ids)
  } catch {
    stageCandidateIds.value = []
  } finally {
    stageFilterLoading.value = false
  }
}

/** 点击「已归档」卡片：显示该流程下终态（未通过/撤回/超时归档）的候选人 */
async function toggleArchived() {
  if (selectedStageLinkId.value === ARCHIVED_KEY) {
    clearStageFilter()
    return
  }
  stageFilterLoading.value = true
  try {
    const all = new Set<string>()
    for (const st of ARCHIVED_STATES) {
      const ids = await collectCandidateIds({ processId: selectedProcessId.value as string, state: st })
      ids.forEach((x) => all.add(x))
    }
    await applyStageFilter(ARCHIVED_KEY, Array.from(all))
  } catch {
    stageCandidateIds.value = []
  } finally {
    stageFilterLoading.value = false
  }
}

/** 清除阶段筛选，恢复全部候选人列表 */
function clearStageFilter() {
  selectedStageLinkId.value = null
  stageCandidateIds.value = null
  handleSearch()
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * 解析「符合规则的候选人 ID」。
 * 同步扫描有上限：未截断直接用；被截断则转后台异步任务并轮询，避免结果静默不全。
 */
async function resolvePassedIds(): Promise<string[] | null> {
  const sync = await filterByScene('FILTER')
  if (!sync.truncated) {
    return sync.passedIds || []
  }
  try {
    const { taskId } = await filterBySceneAsync('FILTER')
    for (let i = 0; i < 60; i++) {
      await sleep(1000)
      const st = await getFilterTaskStatus(taskId)
      if (st.status === 'done') {
        filterProgress.value = null
        return st.passedIds || []
      }
      if (st.status === 'not_found') return null
      filterProgress.value = { current: st.progress || 0, total: st.total || 0 }
    }
    message.warning('规则筛选超时，请重试')
    return null
  } catch (error: any) {
    const detail = error?.response?.data?.error
    message.error(detail ? String(detail) : '规则筛选失败')
    return null
  } finally {
    filterProgress.value = null
  }
}

/** 后端 CandidateListSerializer(camelCase) → 卡片行结构（2026-10-12 对齐参考样式） */
function mapCandidate(r: any): CandidateItem {
  const workYearsNum = r.workYears != null && r.workYears !== '' ? Number(r.workYears) : null
  // 资料行片段：性别 | 年龄 | 学历（工作年限）| 手机 | 邮箱 | 城市（空值自动剔除）
  const infoPieces = [
    r.gender || '',
    r.age != null && r.age !== '' ? `${r.age}${t('pages.candidate.CandidateList.s15')}` : '',
    r.highestEducation
      ? `${r.highestEducation}${workYearsNum != null ? `（${workYearsNum}年）` : ''}`
      : '',
    r.phone || '',
    r.email || '',
    r.currentCity || '',
  ].filter(Boolean)
  // 投递行：yyyy.mm.dd 投递 | 渠道 | 当前职位
  const applyDate = r.createdAt
    ? `${String(r.createdAt).slice(0, 10).replace(/-/g, '.')} 投递`
    : ''
  const applyLine = [applyDate, r.sourceChannelName || '', r.currentPosition || '']
    .filter(Boolean)
    .join(' | ')
  // 后端列表接口不含 stageFlow（阶段流转展示态），此处用真实状态填充当前阶段，
  // 其余留空 —— 避免模板读 row.stageFlow.current 抛错导致整列表不渲染。
  const flow = {
    current: { name: r.stateDisplay || r.currentState || '—', status: '', date: '', handler: '', result: '' },
    previous: { name: '', status: '', date: '', handler: '', result: '' },
    next: { name: '', status: '', date: '', handler: '', result: '' },
  }
  const stageValue = (f: { name: string; status: string }) =>
    [f.name, f.status].filter(Boolean).join('，') || '—'
  return {
    key: r.id,
    id: r.id,
    code: r.code || '',
    applicationCount: r.applicationCount ?? 0,
    name: r.name || '',
    gender: r.gender || '',
    age: r.age ?? undefined,
    education: r.highestEducation || '-',
    experience: r.currentPosition || '-',
    phone: r.phone || '',
    email: r.email || '',
    location: r.currentCity || '-',
    infoPieces,
    applyLine,
    tags: (r.tags || []).map((t: any) => ({
      label: typeof t === 'string' ? t : String(t?.label ?? t),
      type: 'default' as const,
    })),
    position: r.currentPosition || r.currentCompany || '-',
    channel: r.sourceChannelName || '-',
    stage: r.currentState || '',
    createdAt: String(r.createdAt || '').slice(0, 10),
    workExperiences: [],
    stageFlow: flow,
    stageLines: [
      { label: t('pages.candidate.CandidateList.s16'), value: stageValue(flow.current), cls: 'current' },
      { label: t('pages.candidate.CandidateList.s17'), value: stageValue(flow.previous), cls: 'pass' },
      { label: t('pages.candidate.CandidateList.s18'), value: stageValue(flow.next), cls: 'next' },
    ],
  } as unknown as CandidateItem
}

async function loadCandidates() {
  listLoading.value = true
  try {
    // 规则场景筛选：含派生指标，先算 passedIds 作为白名单
    let ruleIds: string[] | null = null
    if (ruleSceneFilter.value === 'FILTER') {
      const res = await filterByScene('FILTER')
      ruleIds = res?.passedIds || []
      if (!ruleIds.length) {
        rows.value = []
        paginationReactive.itemCount = 0
        return
      }
    }
    // 流程-阶段筛选：点击阶段卡片后，取该流程该阶段下的候选人 id 白名单
    const stageIds = stageCandidateIds.value
    const ruleActive = ruleIds !== null
    const stageActive = stageIds !== null
    // 合并两类白名单：两者皆有时取交集，否则取其一；任一激活过滤器无匹配 → 直接空结果
    // （避免 ids='' 被后端忽略而回退为全量列表）
    let ids: string | undefined
    if (ruleActive || stageActive) {
      const r = ruleIds ?? []
      const s = stageIds ?? []
      if (ruleActive && stageActive) {
        const set = new Set(s)
        const inter = r.filter((x) => set.has(x))
        if (inter.length === 0) {
          rows.value = []
          paginationReactive.itemCount = 0
          return
        }
        ids = inter.join(',')
      } else if (stageActive) {
        if (s.length === 0) {
          rows.value = []
          paginationReactive.itemCount = 0
          return
        }
        ids = s.join(',')
      } else {
        // 仅规则筛选：ruleIds 已在上方保证非空
        ids = r.join(',')
      }
    }
    const resp = await listCandidates({
      page: paginationReactive.page,
      pageSize: paginationReactive.pageSize,
      keyword: searchText.value || undefined,
      ids,
    })
    const list = resp?.data ?? []
    rows.value = list.map(mapCandidate)
    paginationReactive.itemCount = resp?.pagination?.total ?? list.length
  } catch (error) {
    message.error('加载候选人失败')
    rows.value = []
  } finally {
    listLoading.value = false
  }
}

const selectedCandidates = computed(() => rows.value.filter((d) => selectedKeys.value.includes(d.key)))
const batchNotificationModalVisible = ref(false)

const paginationReactive = reactive({
  page: 1,
  pageSize: 10,
  itemCount: 0, // 2026-09-25: 真实总数由接口 pagination.total 回填（原硬编码 156）
})

const notificationForm = ref({
  interviewForm: true,
  personalityTest: 'pdp_mbti_20',
  applicationForm: false,
  onboardingDocs: false,
  sendEmail: true,
  sendSms: true,
  sendWechat: false,
  emailSubject: '面试邀请通知',
  emailContent: '尊敬的候选人，您好！\n\n我们诚挚邀请您参加面试，期待与您进一步交流。\n\n祝好',
  smsContent: '',
})

// 招聘流程阶段统计条已由上方"流程管道"(loadProcessStages) 以真实数据驱动，
// 原硬编码 mock 数组 pipelineStats 已移除，避免"能点但数据假"的假实现。

// 快捷筛选标签
const quickFilters = [
  { label: '沟通Offer', key: 'offer' },
  { label: '待安排面试', key: 'pending_interview' },
  { label: '面试中', key: 'interview' },
  { label: '筛选中', key: 'screening' },
  { label: '已入职', key: 'hired' },
]

// 选项
const positionTypeOptions = [
  { label: '技术类', value: 'tech' },
  { label: '产品类', value: 'product' },
  { label: '设计类', value: 'design' },
  { label: '销售类', value: 'sales' },
]
const positionOptions = [
  { label: '前端开发工程师', value: '1' },
  { label: '后端开发工程师', value: '2' },
  { label: '产品经理', value: '3' },
  { label: 'UI设计师', value: '4' },
]
const demandOptions = [
  { label: '2026-Q3-Java后端', value: 'd1' },
  { label: '2026-Q3-前端', value: 'd2' },
  { label: '2026-Q3-产品', value: 'd3' },
]
const departmentOptions = [
  { label: '研发中心', value: 'rd' },
  { label: '产品中心', value: 'pm' },
  { label: '设计部', value: 'design' },
]
const channelOptions = [
  { label: 'Boss直聘', value: 'boss' },
  { label: '拉勾网', value: 'lagou' },
  { label: '猎聘网', value: 'liepin' },
  { label: '内部推荐', value: 'internal' },
]
const stageOptions = [
  { label: '筛选中', value: 'screening' },
  { label: '面试中', value: 'interview' },
  { label: 'Offer沟通', value: 'offer' },
  { label: '已入职', value: 'hired' },
]

// 按规则筛选（指标库「筛选」场景的启用规则；规则在 设置 → 规则管理 维护）
const ruleSceneOptions = [
  { label: '符合筛选规则', value: 'FILTER' },
]

// 2026-09-25: 原 mockData 演示数据已移除 —— 候选人列表改为接真实 API
// (GET /api/v1/candidates/，见下方 loadCandidates)。列表由真实数据驱动，
// 不再保留假数据，避免出现"能点但数据假"的假实现。

const channelMap: Record<string, { text: string; tagType: TagType }> = {
  boss: { text: 'Boss直聘', tagType: 'info' },
  lagou: { text: '拉勾网', tagType: 'info' },
  liepin: { text: '猎聘网', tagType: 'warning' },
  internal: { text: '内部推荐', tagType: 'success' },
}

const stageMap: Record<string, { text: string; tagType: TagType }> = {
  screening: { text: '筛选中', tagType: 'info' },
  interview: { text: '面试中', tagType: 'warning' },
  offer: { text: 'Offer沟通', tagType: 'warning' },
  hired: { text: '已入职', tagType: 'success' },
}

function channelToTagType(c: string) { return channelMap[c]?.tagType || 'default' }
function stageToTagType(s: string) { return stageMap[s]?.tagType || 'default' }
function getChannelText(c: string) { return channelMap[c]?.text || c }
function getStageText(s: string) { return stageMap[s]?.text || s }

const showAddModal = () => { addModalVisible.value = true }
const handleAddSuccess = () => { message.success('候选人添加成功'); addModalVisible.value = false }
const openBatchNotificationModal = () => {
  if (selectedCandidates.value.length === 0) {
    message.warning('请先选择要发送通知的候选人')
    return
  }
  batchNotificationModalVisible.value = true
}
const handleBatchSendNotification = () => {
  const { sendEmail, sendSms, sendWechat } = notificationForm.value
  if (!sendEmail && !sendSms && !sendWechat) {
    message.warning('请至少选择一种通知方式')
    return
  }
  if (sendEmail && !notificationForm.value.emailSubject.trim()) {
    message.warning('请填写邮件主题')
    return
  }
  if (sendSms && !notificationForm.value.smsContent.trim()) {
    message.warning('请填写短信内容')
    return
  }
  const selectedCount = selectedCandidates.value.length
  message.success(`已成功向 ${selectedCount} 位候选人发送通知`)
  batchNotificationModalVisible.value = false
  selectedKeys.value = []
}
const handleViewDetail = (record: any) => { router.push(`/candidates/${record.key}`) }
const onCandidateRowAction = (key: string, _row: any) => {
  // v2: row-bottom 下拉（占位 handler · 后续接入）
  message.info({ forward: '转发简历功能开发中', note: '备注功能开发中', interview: '安排面试功能开发中' }[key] || '未知操作')
}
/** 右上「更多 ⋯」下拉分发：详情直达，其余走占位 handler */
const onRowAction = (key: string, row: CandidateItem) => {
  if (key === 'detail') { handleViewDetail(row); return }
  onCandidateRowAction(key, row)
}
const handleSearch = () => { paginationReactive.page = 1; loadCandidates() }
const exportData = () => { message.info('导出功能开发中') }
const showMoreFilter = () => { message.info('更多筛选功能开发中') }

// 切换分页/筛选时清空选择（可选）
watch(statusFilter, () => { selectedKeys.value = [] })
// 2026-09-25: 分页变化 → 重新拉取真实列表
watch(
  () => [paginationReactive.page, paginationReactive.pageSize],
  () => { loadCandidates() },
)
</script>

<style scoped>
.candidate-list-page { padding: var(--space-6); animation: wb-fade-up var(--duration-slow) var(--ease-out) both; }
.page-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title h1 {
  margin: 0 0 var(--space-1);
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}

/* 招聘流程管道 */
.pipeline-board {
  background: var(--glass-bg-card);
  border: 1px solid var(--border-hairline);
  border-radius: 12px;
  padding: var(--space-3);
  box-shadow: 0 1px 4px var(--overlay-scrim-weak);
}
.pipeline-board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.pipeline-board-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.pipeline-board-title .pb-icon {
  color: var(--brand);
  font-size: 18px;
}
.pipeline-track {
  display: flex;
  align-items: stretch;
  gap: var(--space-2);
  overflow-x: auto;
  padding-bottom: var(--space-1);
}
.pipeline-track::-webkit-scrollbar { height: 6px; }
.pipeline-track::-webkit-scrollbar-thumb {
  background: var(--scrollbar-color-default);
  border-radius: 3px;
}
.pipeline-track::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-color-hover);
}
.stage-card {
  position: relative;
  flex: 0 0 auto;
  min-width: 104px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 8px 11px;
  text-align: left;
  cursor: pointer;
  background: var(--glass-bg-card);
  border: 1px solid var(--border-hairline);
  border-radius: 10px;
  transition: transform var(--duration-base) var(--ease-out),
    box-shadow var(--duration-base) var(--ease-out),
    border-color var(--duration-base) var(--ease-out);
  font: inherit;
  color: inherit;
}
.stage-card::before {
  content: '';
  position: absolute;
  left: 11px;
  right: 11px;
  top: 0;
  height: 2px;
  border-radius: 0 0 2px 2px;
  background: var(--brand);
  opacity: 0;
  transition: opacity var(--duration-base) var(--ease-out);
}
.stage-card:hover {
  border-color: var(--brand);
  box-shadow: 0 4px 14px var(--overlay-scrim-weak);
  transform: translateY(-1px);
}
.stage-card:hover::before { opacity: 0.5; }
.stage-card.active {
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 100%);
  border-color: var(--brand);
}
.stage-card.active::before { opacity: 1; background: var(--g1); }
.stage-card.active .stage-name,
.stage-card.active .stage-count,
.stage-card.active .stage-unit { color: var(--g1); }
.stage-index {
  position: absolute;
  top: 7px;
  right: 10px;
  font-size: 10px;
  font-weight: 700;
  color: var(--ink-faint);
  opacity: 0.55;
}
.stage-card.active .stage-index { color: var(--g1); opacity: 0.85; }
.stage-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.2;
  padding-right: 16px;
}
.stage-type {
  display: inline-block;
  margin-top: 1px;
  width: fit-content;
  font-size: 10px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--brand);
  color: var(--g1);
}
.stage-type--muted {
  background: var(--glass-bg-card);
  color: var(--ink-faint);
  border: 1px solid var(--border-hairline);
}
.stage-card.active .stage-type {
  background: var(--g1);
  color: var(--brand);
}
.stage-card.active .stage-type--muted {
  background: var(--g1);
  color: var(--brand);
  border-color: transparent;
}
.stage-count-row {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
  margin-top: 3px;
}
.stage-count {
  font-size: 18px;
  font-weight: 800;
  color: var(--brand);
  line-height: 1.1;
}
.stage-unit {
  font-size: 10px;
  color: var(--ink-faint);
}
.pipeline-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4) 0;
  font-size: 13px;
  color: var(--ink-faint);
}
.pipeline-empty { padding: var(--space-3) 0; }
.candidate-empty { padding: var(--space-6) 0; }
.pipeline-active-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

/* 筛选卡片 */
.filter-card,
.action-filter-card,
.list-card {
  box-shadow: 0 1px 4px var(--overlay-scrim-weak);
}
.action-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
}

/* 按钮品牌色 · v2: 移除 !important · 字色由 App.vue themeOverrides 统一 */
.add-button, .batch-notify-btn, .send-btn-primary {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  border: 1px solid var(--overlay-glass-mid);
  /* 不再覆盖 color — 走全局主按钮字色 var(--g1) */
}

/* 候选人列表 */
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.candidate-row {
  position: relative;
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--glass-bg-card);
  border: 1px solid var(--border-hairline);
  border-bottom: 1px dashed var(--border-hairline);
  border-radius: 12px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.candidate-row {
  cursor: pointer;
}
.candidate-row:hover {
  box-shadow: 0 4px 16px var(--overlay-scrim-weak);
  border-color: var(--brand);
}
.row-checkbox {
  padding-top: 2px;
  flex-shrink: 0;
}
.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.row-top {
  display: flex;
  gap: 20px;
}
.row-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.row-right {
  flex: 0 0 280px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-left: 1px solid var(--border-hairline);
  padding-left: var(--space-4);
  align-items: flex-start;
}

/* 卡片头部：姓名 + 编号 + 次数 + 小标签 */
.card-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 8px;
}
.candidate-name {
  font-size: var(--fs-15);
  font-weight: 600;
  color: var(--ink);
  cursor: pointer;
  transition: color 0.15s var(--ease-out);
}
.candidate-name:hover { color: var(--brand-fg); }
.candidate-code {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}
.apply-count {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}

/* 小标签（迷你 chip） */
.mini-tag {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  line-height: 1;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
}
.mini-tag--default { background: var(--glass-bg-input); color: var(--ink-soft); }
.mini-tag--primary { background: var(--brand-soft); color: var(--brand-fg); }
.mini-tag--info { background: var(--c-info-bg); color: var(--c-info-deep); }
.mini-tag--success { background: var(--c-success-bg); color: var(--c-success-deep); }
.mini-tag--warning { background: var(--c-warning-bg); color: var(--c-warning-deep); }
.mini-tag--error { background: var(--c-error-bg); color: var(--c-error-deep); }

/* 资料行：管道符分隔（性别 | 年龄 | 学历 | 手机 | 邮箱 | 城市） */
.info-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  font-size: var(--fs-13);
  color: var(--ink-soft);
}
.info-piece { color: var(--ink-soft); }
.info-divider {
  color: var(--ink-faint);
  margin: 0 8px;
}

/* 投递行：yyyy.mm.dd 投递 | 渠道 | 当前职位 */
.apply-line {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 中列：工作经历（接口返回时渲染，否则整列隐藏 — 数据驱动） */
.row-mid {
  flex: 0 0 240px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-left: 1px solid var(--border-hairline);
  padding-left: var(--space-4);
}
.work-item {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px;
  font-size: var(--fs-12);
}
.work-date { color: var(--ink-faint); white-space: nowrap; }
.work-company { color: var(--ink); font-weight: 500; }
.work-divider { color: var(--ink-faint); }
.work-position { color: var(--ink-soft); }

/* 右列：阶段流转（label：value 行，蓝=当前/绿=通过/橙=下一阶段/灰=占位） */
.stage-line {
  display: flex;
  align-items: baseline;
  font-size: var(--fs-12);
  line-height: 1.5;
}
.stage-label {
  color: var(--ink-faint);
  flex-shrink: 0;
  margin-right: 2px;
}
.stage-value {
  color: var(--ink);
  font-weight: 500;
}
.stage-value.placeholder { color: var(--ink-faint); font-weight: 400; }
.stage-value.current { color: var(--brand-fg); }
.stage-value.pass { color: var(--c-success-deep); }
.stage-value.next { color: var(--c-warning-deep); }

/* 右上操作：更多 ⋯ 下拉 + 备注 */
.row-actions {
  position: absolute;
  top: var(--space-3);
  right: var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.more-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ink-faint);
  font-size: 18px;
  transition: background 0.15s var(--ease-out), color 0.15s var(--ease-out);
}
.more-btn:hover { background: var(--brand-tint); color: var(--brand-fg); }
.note-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: var(--fs-13);
  color: var(--ink-soft);
  padding: 4px 6px;
  border-radius: 6px;
  letter-spacing: 1px;
  transition: background 0.15s var(--ease-out), color 0.15s var(--ease-out);
}
.note-btn:hover { background: var(--brand-tint); color: var(--brand-fg); }

/* 分页 */
.list-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: 20px;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-hairline);
}
.pagination-total { font-size: var(--fs-13); color: var(--ink-faint); }

/* 响应式 */
@media (max-width: 1024px) {
  .row-top { flex-direction: column; }
  .row-mid, .row-right {
    border-left: none;
    padding-left: 0;
    flex: 1 1 auto;
  }
}
@media (max-width: 768px) {
  .action-filter-bar { flex-direction: column; align-items: flex-start; }
  .pipeline-stat-item { min-width: 72px; padding: var(--space-2) 10px; }
  .candidate-list-page { padding: var(--space-4); }
}

/* 批量通知弹窗样式（保留） */
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: var(--fs-18); font-weight: 600; }
.close-btn {
  background: none; border: none; font-size: var(--fs-18); cursor: pointer; color: var(--n-400);
}
.close-btn:hover { color: var(--n-650); }
.candidate-summary {
  display: flex; align-items: center; gap: var(--space-3); margin-top: var(--space-4); padding: var(--space-3);
  background: var(--glass-bg-input); border-radius: 8px;
}
.candidate-avatar-sm {
  background: linear-gradient(135deg, var(--brand), var(--brand-grad-a));
  /* 不再覆盖 color — 走全局主按钮字色 var(--g1) */
  font-weight: 600;
}
.modal-content { display: flex; gap: var(--space-6); margin-top: var(--space-6); }
.left-sidebar { width: 280px; flex-shrink: 0; }
.step-section { margin-bottom: var(--space-6); }
.step-title { display: flex; align-items: center; gap: var(--space-2); font-size: var(--fs-14); font-weight: 600; margin: 0 0 var(--space-3); }
.step-number {
  width: 24px; height: 24px;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 100%);
  color: var(--ink); border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: var(--fs-12);
}
.step-content { padding-left: var(--space-8); }
.content-group { margin-bottom: var(--space-4); }
.content-group-title { font-size: var(--fs-12); color: var(--n-400); margin-bottom: var(--space-2); }
.content-item {
  display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2);
  border-radius: 6px; cursor: pointer; transition: background 0.15s var(--ease-out);
}
.content-item:hover { background: var(--brand-tint); }
.content-item.selected { background: var(--brand-soft); }
.method-item {
  display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3);
  border-radius: 8px; cursor: pointer; transition: background 0.15s var(--ease-out); margin-bottom: var(--space-2);
}
.method-item:hover { background: var(--glass-bg-input); }
.method-item.selected { background: var(--brand-tint); border: 1px solid var(--brand); }
.method-icon { font-size: var(--fs-18); color: var(--brand-fg); }
.method-name { font-weight: 500; }
.right-content { flex: 1; min-width: 0; }
.info-callout {
  background: var(--g1); border: 1px solid var(--c-info-bg); border-radius: 6px;
  padding: var(--space-3); font-size: var(--text-body); color: var(--c-info-deep); margin-bottom: var(--space-4);
}
.editor-section { background: var(--glass-bg-input); border-radius: 8px; padding: var(--space-4); margin-bottom: var(--space-4); }
.editor-header { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4); }
.editor-icon { font-size: var(--fs-18); color: var(--brand-fg); }
.editor-title { font-weight: 600; margin: 0; }
.editor-field { margin-bottom: var(--space-3); }
.field-label { display: block; font-size: var(--fs-13); color: var(--n-500); margin-bottom: 6px; }
.sms-counter { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.counter-text { font-size: var(--fs-12); color: var(--n-400); }
.modal-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: var(--space-6); padding-top: var(--space-4); border-top: 1px solid var(--border-hairline);
}
.recipient-info { font-size: var(--fs-14); color: var(--n-500); }
.footer-buttons { display: flex; gap: var(--space-2); }

/* === v2 响应式补丁 === */
@media (max-width: 1280px) {
  .page-title { font-size: var(--text-h2); }
  :deep(.n-data-table-wrapper) {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
@media (max-width: 768px) {
  .page-header { flex-direction: column; align-items: stretch; gap: var(--space-3); }
  .stats-row { grid-template-columns: repeat(2, 1fr) !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 2 列） */
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: 1fr !important; } /* v2.9: 保留 !important（覆盖 Naive n-grid 内联 grid-template-columns，移除则移动端不退化为 1 列） */
}

</style>

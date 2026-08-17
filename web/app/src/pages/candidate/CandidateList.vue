<template>
  <div class="candidate-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-title">
        <h1>候选人管理</h1>
        <n-text :depth="3">管理所有候选人信息，推进招聘流程</n-text>
      </div>
      <n-space>
        <n-button type="primary" :disabled="selectedCandidates.length === 0" class="batch-notify-btn" @click="openBatchNotificationModal">
          <template #icon><n-icon :component="PaperPlaneOutline" /></template>
          批量发送通知 ({{ selectedCandidates.length }})
        </n-button>
        <n-button type="primary" size="large" class="add-button" data-testid="add-candidate-btn" @click="showAddModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增候选人
        </n-button>
      </n-space>
    </div>

    <!-- 招聘流程阶段统计条 -->
    <div class="pipeline-stats mb-4">
      <div
        v-for="s in pipelineStats"
        :key="s.key ?? 'all'"
        class="pipeline-stat-item"
        :class="{ active: statusFilter === s.key }"
        @click="setStatusFilter(s.key)"
      >
        <div class="pipeline-stat-value">{{ s.value }}</div>
        <div class="pipeline-stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 筛选区域 -->
    <n-card class="filter-card mb-4">
      <n-space :size="12" :wrap="true" align="center">
        <n-input
          v-model:value="searchText"
          placeholder="在当前页面搜索关键词"
          clearable
          style="width: 260px"
          @keyup.enter="handleSearch"
        >
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <n-select v-model:value="positionTypeFilter" placeholder="职位类型" style="width: 140px" clearable :options="positionTypeOptions" />
        <n-select v-model:value="positionFilter" placeholder="应聘职位" style="width: 160px" clearable :options="positionOptions" />
        <n-select v-model:value="demandFilter" placeholder="招聘需求" style="width: 150px" clearable :options="demandOptions" />
        <n-select v-model:value="departmentFilter" placeholder="用人部门" style="width: 140px" clearable :options="departmentOptions" />
        <n-select v-model:value="channelFilter" placeholder="简历来源" style="width: 130px" clearable :options="channelOptions" />
        <n-button @click="showMoreFilter">
          <template #icon><n-icon :component="FunnelOutline" /></template>
          更多筛选
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
            全部
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
            批量导入人才库
          </n-button>
          <n-button size="small" @click="message.info('批量分配职位功能开发中')">
            <template #icon><n-icon :component="GitPullRequestOutline" /></template>
            批量分配职位
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 候选人卡片列表 -->
    <n-card class="list-card">
      <n-checkbox-group v-model:value="selectedKeys">
        <div class="candidate-list">
          <div v-for="row in mockData" :key="row.key" class="candidate-row">
            <div class="row-checkbox">
              <n-checkbox :value="row.key" />
            </div>
            <div class="row-main">
              <div class="row-top">
                <!-- 左侧：候选人基本信息 + 履历时间线 -->
                <div class="row-left">
                  <div class="candidate-title">
                    <span class="candidate-name" @click="handleViewDetail(row)">{{ row.name }}</span>
                    <span class="candidate-id">（{{ row.id }}）</span>
                    <n-space :size="8" class="candidate-meta" align="center">
                      <span>{{ row.gender }}</span>
                      <span>{{ row.age }}岁</span>
                      <span><n-icon :component="SchoolOutline" size="12" /> {{ row.education }}</span>
                      <span><n-icon :component="BriefcaseOutline" size="12" /> {{ row.experience }}</span>
                      <span><n-icon :component="CallOutline" size="12" /> {{ row.phone }}</span>
                      <span><n-icon :component="MailOutline" size="12" /> {{ row.email }}</span>
                      <span><n-icon :component="LocationOutline" size="12" /> {{ row.location }}</span>
                    </n-space>
                  </div>
                  <n-space :size="6" class="tag-list">
                    <n-tag
                      v-for="tag in row.tags"
                      :key="tag.label"
                      :type="tag.type"
                      size="small"
                      :bordered="false"
                      round
                    >
                      {{ tag.label }}
                    </n-tag>
                  </n-space>
                  <div class="work-timeline">
                    <div
                      v-for="(exp, idx) in row.workExperiences.slice(0, 2)"
                      :key="idx"
                      class="timeline-item"
                    >
                      <n-icon :component="TimeOutline" size="13" class="timeline-icon" />
                      <span class="timeline-date">{{ exp.start }} - {{ exp.end }}</span>
                      <span class="timeline-company">{{ exp.company }}</span>
                      <span class="timeline-divider">|</span>
                      <span class="timeline-position">{{ exp.position }}</span>
                    </div>
                    <div v-if="row.workExperiences.length > 2" class="timeline-more">
                      +{{ row.workExperiences.length - 2 }} 段经历
                    </div>
                  </div>
                </div>

                <!-- 右侧：阶段流转 -->
                <div class="row-right">
                  <div class="stage-item current">
                    <div class="stage-label">现阶段</div>
                    <div class="stage-content">
                      <div class="stage-name">{{ row.stageFlow.current.name }}</div>
                      <div class="stage-status">{{ row.stageFlow.current.status }}</div>
                      <div class="stage-foot">
                        <span>{{ row.stageFlow.current.date }}</span>
                        <span class="stage-handler">{{ row.stageFlow.current.handler }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="stage-item previous">
                    <div class="stage-label">上阶段</div>
                    <div class="stage-content">
                      <div class="stage-name">{{ row.stageFlow.previous.name }}</div>
                      <div class="stage-status" :class="row.stageFlow.previous.result">{{ row.stageFlow.previous.status }}</div>
                      <div class="stage-foot">
                        <span>{{ row.stageFlow.previous.date }}</span>
                        <span class="stage-handler">{{ row.stageFlow.previous.handler }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="stage-item next">
                    <div class="stage-label">下阶段</div>
                    <div class="stage-content">
                      <div class="stage-name">{{ row.stageFlow.next.name }}</div>
                      <div class="stage-status placeholder">{{ row.stageFlow.next.status || '—' }}</div>
                      <div class="stage-foot">
                        <span>{{ row.stageFlow.next.date || '' }}</span>
                        <span class="stage-handler">{{ row.stageFlow.next.handler || '' }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 底部操作栏 -->
              <div class="row-bottom">
                <n-space :size="16">
                  <n-button text type="primary" size="small" @click="handleViewDetail(row)">查看详情</n-button>
                  <n-button text size="small">转发简历</n-button>
                  <n-button text size="small">备注</n-button>
                  <n-button text size="small">安排面试</n-button>
                </n-space>
                <n-button text size="small">
                  <n-icon :component="EllipsisHorizontalCircleOutline" size="18" />
                </n-button>
              </div>
            </div>
          </div>
        </div>
      </n-checkbox-group>

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
        <span class="pagination-total">共 {{ paginationReactive.itemCount }} 条</span>
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
          <span class="modal-title">批量发送通知</span>
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
              <span class="candidate-name">已选择 {{ selectedCandidates.length }} 位候选人</span>
            </div>
            <div class="candidate-contact-row">
              <span>选定的候选人将收到相同的通知内容</span>
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
              选择发送内容
            </h3>
            <div class="step-content">
              <div class="content-group">
                <div class="content-group-title">面试登记表</div>
                <label class="content-item selected">
                  <n-checkbox v-model:checked="notificationForm.interviewForm" />
                  <span>收集候选人基本信息</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">性格测试</div>
                <n-radio-group v-model:value="notificationForm.personalityTest">
                  <n-space vertical>
                    <n-radio value="pdp_mbti_20">PDP+20题版MBTI</n-radio>
                    <n-radio value="pdp_mbti_93">PDP+93题版MBTI</n-radio>
                  </n-space>
                </n-radio-group>
              </div>
              <div class="content-group">
                <div class="content-group-title">应聘登记表</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.applicationForm" />
                  <span>完善工作履历及教育背景</span>
                </label>
              </div>
              <div class="content-group">
                <div class="content-group-title">入职材料</div>
                <label class="content-item">
                  <n-checkbox v-model:checked="notificationForm.onboardingDocs" />
                  <span>收集入职资料及相关证明</span>
                </label>
              </div>
            </div>
          </div>

          <!-- Step 2: 选择通知方式 -->
          <div class="step-section">
            <h3 class="step-title">
              <span class="step-number">2</span>
              选择通知方式
            </h3>
            <div class="step-content">
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendEmail" />
                <n-icon :component="MailOutline" class="method-icon" />
                <span class="method-name">邮件通知</span>
              </label>
              <label class="method-item selected">
                <n-checkbox v-model:checked="notificationForm.sendSms" />
                <n-icon :component="ChatbubblesOutline" class="method-icon" />
                <span class="method-name">短信通知</span>
              </label>
              <label class="method-item">
                <n-checkbox v-model:checked="notificationForm.sendWechat" />
                <n-icon :component="LogoWechat" class="method-icon" />
                <span class="method-name">微信企业号推送</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 右侧内容区域 -->
        <div class="right-content">
          <div class="info-callout">
            <span>系统将基于选择的「发送内容」自动为候选人生成对应待办，选择多个内容时会同时发送</span>
          </div>

          <div v-if="notificationForm.sendEmail" class="editor-section">
            <div class="editor-header">
              <n-icon :component="MailOutline" class="editor-icon" />
              <h4 class="editor-title">邮件通知</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">邮件主题</label>
              <n-input v-model:value="notificationForm.emailSubject" class="email-subject-input" />
            </div>
            <div class="editor-field">
              <label class="field-label">邮件正文</label>
              <n-input v-model:value="notificationForm.emailContent" type="textarea" :rows="8" class="email-content-input" />
            </div>
          </div>

          <div v-if="notificationForm.sendSms" class="editor-section">
            <div class="editor-header">
              <n-icon :component="ChatbubblesOutline" class="editor-icon" />
              <h4 class="editor-title">短信通知</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">短信正文</label>
                <span class="counter-text">已输入 <strong>{{ notificationForm.smsContent.length }}</strong> / 70 字</span>
              </div>
              <n-input v-model:value="notificationForm.smsContent" type="textarea" :rows="4" class="sms-content-input" />
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <div class="recipient-info">通知将发送至: {{ selectedCandidates.length }} 个候选人</div>
          <div class="footer-buttons">
            <n-button @click="batchNotificationModalVisible = false">取消</n-button>
            <n-button type="primary" class="send-btn-primary" @click="handleBatchSendNotification">
              <template #icon><n-icon :component="PaperPlaneOutline" /></template>
              确认发送
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag, NIcon, NButton, NSpace, NAvatar, NCheckbox, NCheckboxGroup, NPagination } from 'naive-ui'
import {
  AddOutline,
  SearchOutline,
  FunnelOutline,
  DownloadOutline,
  EllipsisHorizontalCircleOutline,
  CallOutline,
  PaperPlaneOutline,
  CloseOutline,
  MailOutline,
  ChatbubblesOutline,
  LogoWechat,
  PeopleOutline,
  PersonAddOutline,
  TimeOutline,
  LocationOutline,
  SchoolOutline,
  BriefcaseOutline,
  CloudUploadOutline,
  GitPullRequestOutline,
} from '@vicons/ionicons5'
import AddCandidateModal from './AddCandidateModal.vue'
import { fetchStatusSchema, type StatusSchema } from '@/api/candidate'
import type { TagType } from '@/api/offer'

const router = useRouter()
const message = useMessage()

type CandidateTagType = 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error'
interface CandidateItem {
  key: string
  name: string
  id: string
  gender: string
  age: number
  education: string
  experience: string
  phone: string
  email: string
  location: string
  tags: Array<{ label: string; type: CandidateTagType }>
  position: string
  channel: string
  stage: string
  createdAt: string
  workExperiences: Array<{ company: string; position: string; start: string; end: string }>
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
})

function setStatusFilter(key: string | null) {
  statusFilter.value = key
  handleSearch()
}

const stageFilter = ref<string | undefined>()
const selectedKeys = ref<string[]>([])
const selectedCandidates = computed(() => mockData.filter((d) => selectedKeys.value.includes(d.key)))
const batchNotificationModalVisible = ref(false)

const paginationReactive = reactive({
  page: 1,
  pageSize: 10,
  itemCount: 156,
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

// 招聘流程阶段统计（横向条）
const pipelineStats = [
  { label: '全部流程', value: '2.5W', key: null },
  { label: '初筛', value: 2, key: 'initial' },
  { label: 'HR初筛评估', value: 231, key: 'hr_screening' },
  { label: '用人经理筛选', value: 437, key: 'manager_screening' },
  { label: '招聘经理筛选', value: 18, key: 'recruiter_screening' },
  { label: '待安排面试', value: 113, key: 'pending_interview' },
  { label: '沟通Offer', value: 238, key: 'offer' },
  { label: '薪酬确认', value: 87, key: 'salary' },
  { label: '背景调查', value: 6, key: 'background' },
  { label: '待入职', value: 9, key: 'pending_hire' },
  { label: '正式录用', value: 773, key: 'hired' },
  { label: '已归档', value: '2.5W', key: 'archived' },
]

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

// 演示数据 — 参照截图结构扩展
const mockData: CandidateItem[] = [
  {
    key: '1',
    name: '李六',
    id: 'CDD005201',
    gender: '男',
    age: 26,
    education: '本科',
    experience: '4年',
    phone: '111****0032',
    email: 'liuliu@example.com',
    location: '北京-已毕业',
    tags: [
      { label: '工学', type: 'default' },
      { label: '进一步沟通', type: 'warning' },
      { label: '不匹配', type: 'error' },
    ],
    position: 'Java开发-测试职位',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-27',
    workExperiences: [
      { company: '微软亚洲研究院', position: '程序员', start: '2022.07', end: '2024.07' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-未创建', date: '08月05日', handler: '高晨阳', result: 'pending' },
      previous: { name: '综合面试', status: '全部通过', date: '07月30日', handler: '卢玉林', result: 'pass' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
  {
    key: '2',
    name: '王鹏飞',
    id: 'CDD003812',
    gender: '男',
    age: 37,
    education: '大专',
    experience: '18年',
    phone: '181****0557',
    email: 'wangpf@example.com',
    location: '重庆',
    tags: [
      { label: '五险一金', type: 'default' },
      { label: '随时到岗', type: 'success' },
      { label: '一本院校', type: 'info' },
    ],
    position: '渠道销售',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-26',
    workExperiences: [
      { company: '重庆kG电器销售有限公司', position: '渠道销售', start: '2021.01', end: '2024.11' },
      { company: '佛山市北外电器科技有限公司', position: '区域总监', start: '2018.06', end: '2019.11' },
      { company: '阿克苏诺贝尔(中国)有限公司', position: '城市经理', start: '2011.12', end: '2017.04' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-未创建', date: '08月05日', handler: '徐月', result: 'pending' },
      previous: { name: '综合面试', status: '全部通过', date: '07月27日', handler: '杨尹升', result: 'pass' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
  {
    key: '3',
    name: '潘明1',
    id: 'CDD001961',
    gender: '男',
    age: 25,
    education: '本科',
    experience: '应届生',
    phone: '181****1931',
    email: 'panming@example.com',
    location: '上海',
    tags: [
      { label: '本科', type: 'info' },
      { label: '应届生', type: 'default' },
    ],
    position: 'Java开发-测试职位',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-25',
    workExperiences: [
      { company: '暂无工作经历', position: '', start: '', end: '' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-审批中', date: '08月05日', handler: '杨尹升', result: 'pending' },
      previous: { name: '综合面试', status: '全部不通过', date: '07月30日', handler: '', result: 'reject' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
  {
    key: '4',
    name: '张三',
    id: 'CDD005878',
    gender: '男',
    age: 8,
    education: '本科',
    experience: '1年',
    phone: '186****8825',
    email: 'zhangsan@example.com',
    location: '深圳',
    tags: [
      { label: '1年', type: 'default' },
      { label: '不接受加班', type: 'warning' },
      { label: '品牌学校毕业', type: 'success' },
    ],
    position: 'Java开发-测试职位',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-24',
    workExperiences: [
      { company: '个人', position: '', start: '2025.01', end: '2025.03' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-审批中', date: '08月05日', handler: '高晨阳', result: 'pending' },
      previous: { name: '综合面试', status: '全部通过', date: '07月30日', handler: '卢玉林', result: 'pass' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
  {
    key: '5',
    name: '陈汪军',
    id: 'CDD008882',
    gender: '男',
    age: 26,
    education: '本科',
    experience: '4年',
    phone: '181****0988',
    email: 'chenwj@example.com',
    location: '深圳',
    tags: [
      { label: '不接受加班', type: 'warning' },
      { label: '品牌学校毕业', type: 'success' },
    ],
    position: '报关/报检员',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-23',
    workExperiences: [
      { company: '深圳市有信达供应链服务有限公司', position: '报关/报检员', start: '2022.07', end: '2024.07' },
      { company: '广州地铁集团有限公司', position: '安全员', start: '2019.07', end: '2021.12' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-审批中', date: '08月05日', handler: '杨尹升', result: 'pending' },
      previous: { name: '综合面试', status: '全部通过', date: '07月30日', handler: '韩爽', result: 'pass' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
  {
    key: '6',
    name: '李二',
    id: 'CDD008911',
    gender: '男',
    age: 26,
    education: '本科',
    experience: '1年',
    phone: '186****7777',
    email: 'lier@example.com',
    location: '北京',
    tags: [
      { label: '本科', type: 'info' },
      { label: '985', type: 'success' },
      { label: '工学', type: 'default' },
    ],
    position: 'Java开发-测试职位',
    channel: 'boss',
    stage: 'offer',
    createdAt: '2026-04-22',
    workExperiences: [
      { company: '微软亚洲研究院', position: '程序员', start: '2024.01', end: '2024.06' },
      { company: '微软亚洲研究院', position: '程序员', start: '2022.07', end: '2023.07' },
    ],
    stageFlow: {
      current: { name: '沟通Offer', status: '审批-审批中', date: '08月05日', handler: '杨尹升', result: 'pending' },
      previous: { name: '综合面试', status: '全部通过', date: '07月30日', handler: '杨尹升', result: 'pass' },
      next: { name: '待入职', status: '', date: '', handler: '', result: '' },
    },
  },
]

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
const handleSearch = () => { /* search */ }
const exportData = () => { message.info('导出功能开发中') }
const showMoreFilter = () => { message.info('更多筛选功能开发中') }

// 切换分页/筛选时清空选择（可选）
watch(statusFilter, () => { selectedKeys.value = [] })
</script>

<style scoped>
.candidate-list-page { padding: 24px; }
.page-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title h1 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
}

/* 顶部流程统计条 */
.pipeline-stats {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.pipeline-stats::-webkit-scrollbar { height: 4px; }
.pipeline-stats::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 2px; }
.pipeline-stat-item {
  flex: 0 0 auto;
  min-width: 84px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.pipeline-stat-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.pipeline-stat-item.active {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  border-color: #FBCE5B;
}
.pipeline-stat-item.active .pipeline-stat-value,
.pipeline-stat-item.active .pipeline-stat-label { color: #1f2937; }
.pipeline-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
}
.pipeline-stat-label {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
  white-space: nowrap;
}

/* 筛选卡片 */
.filter-card,
.action-filter-card,
.list-card {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.action-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

/* 按钮品牌色 */
.add-button, .batch-notify-btn, .send-btn-primary {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%) !important;
  border: none !important;
  color: #1f2937 !important;
}

/* 候选人列表 */
.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.candidate-row {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  transition: box-shadow 0.2s, border-color 0.2s;
}
.candidate-row:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  border-color: #e5e7eb;
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
  gap: 8px;
}
.row-right {
  flex: 0 0 300px;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 6px;
  border-left: 1px solid #f0f0f0;
  padding-left: 16px;
  align-items: flex-start;
}

/* 候选人标题 */
.candidate-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  row-gap: 4px;
}
.candidate-name {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  cursor: pointer;
}
.candidate-name:hover { color: #E5B82A; }
.candidate-id {
  font-size: 12px;
  color: #8c8c8c;
}
.candidate-meta {
  font-size: 12px;
  color: #595959;
}
.candidate-meta span {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

/* 标签 */
.tag-list { flex-wrap: wrap; gap: 4px; }

/* 工作经历时间线 */
.work-timeline {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.timeline-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #595959;
}
.timeline-icon { color: #8c8c8c; flex-shrink: 0; }
.timeline-date { color: #8c8c8c; white-space: nowrap; }
.timeline-company { color: #262626; font-weight: 500; }
.timeline-divider { color: #d9d9d9; }
.timeline-position { color: #595959; }
.timeline-more {
  font-size: 12px;
  color: #1890ff;
  cursor: default;
}

/* 阶段流转 */
.stage-item {
  flex: 1;
  min-width: 84px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
.stage-label {
  color: #8c8c8c;
  font-size: 12px;
  line-height: 1.4;
  margin-bottom: 1px;
}
.stage-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.stage-name { color: #262626; font-weight: 500; font-size: 12px; }
.stage-status { color: #595959; font-size: 12px; }
.stage-status.pass { color: #52c41a; }
.stage-status.reject { color: #ff4d4f; }
.stage-status.placeholder { color: #bfbfbf; }
.stage-foot {
  display: flex;
  gap: 4px;
  color: #8c8c8c;
  font-size: 11px;
  flex-wrap: wrap;
}
.stage-handler { color: #595959; }

/* 底部操作 */
.row-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px dashed #f0f0f0;
}

/* 分页 */
.list-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
.pagination-total { font-size: 13px; color: #8c8c8c; }

/* 响应式 */
@media (max-width: 1024px) {
  .row-top { flex-direction: column; }
  .row-right {
    border-left: none;
    padding-left: 0;
    flex: 1 1 auto;
  }
}
@media (max-width: 768px) {
  .action-filter-bar { flex-direction: column; align-items: flex-start; }
  .pipeline-stat-item { min-width: 72px; padding: 8px 10px; }
  .candidate-list-page { padding: 16px; }
}

/* 批量通知弹窗样式（保留） */
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-title { font-size: 18px; font-weight: 600; }
.close-btn {
  background: none; border: none; font-size: 18px; cursor: pointer; color: #999;
}
.close-btn:hover { color: #333; }
.candidate-summary {
  display: flex; align-items: center; gap: 12px; margin-top: 16px; padding: 12px;
  background: #f5f5f5; border-radius: 8px;
}
.candidate-avatar-sm {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%) !important;
  color: #1f2937 !important; font-weight: 600;
}
.modal-content { display: flex; gap: 24px; margin-top: 24px; }
.left-sidebar { width: 280px; flex-shrink: 0; }
.step-section { margin-bottom: 24px; }
.step-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; margin: 0 0 12px; }
.step-number {
  width: 24px; height: 24px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #1f2937; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.step-content { padding-left: 32px; }
.content-group { margin-bottom: 16px; }
.content-group-title { font-size: 12px; color: #999; margin-bottom: 8px; }
.content-item {
  display: flex; align-items: center; gap: 8px; padding: 8px;
  border-radius: 6px; cursor: pointer; transition: background 0.3s;
}
.content-item:hover { background: #f5f5f5; }
.content-item.selected { background: #f0f0ff; }
.method-item {
  display: flex; align-items: center; gap: 8px; padding: 12px;
  border-radius: 8px; cursor: pointer; transition: background 0.3s; margin-bottom: 8px;
}
.method-item:hover { background: #f5f5f5; }
.method-item.selected { background: #f0f0ff; border: 1px solid #FBCE5B; }
.method-icon { font-size: 18px; color: #FBCE5B; }
.method-name { font-weight: 500; }
.right-content { flex: 1; min-width: 0; }
.info-callout {
  background: #e6f7ff; border: 1px solid #91d5ff; border-radius: 6px;
  padding: 12px; font-size: 13px; color: #1890ff; margin-bottom: 16px;
}
.editor-section { background: #fafafa; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.editor-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.editor-icon { font-size: 18px; color: #FBCE5B; }
.editor-title { font-weight: 600; margin: 0; }
.editor-field { margin-bottom: 12px; }
.field-label { display: block; font-size: 13px; color: #666; margin-bottom: 6px; }
.sms-counter { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.counter-text { font-size: 12px; color: #999; }
.modal-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 24px; padding-top: 16px; border-top: 1px solid #f0f0f0;
}
.recipient-info { font-size: 14px; color: #666; }
.footer-buttons { display: flex; gap: 8px; }
</style>

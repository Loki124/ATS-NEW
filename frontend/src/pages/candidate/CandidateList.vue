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
        <n-button type="primary" size="large" class="add-button" @click="showAddModal">
          <template #icon><n-icon :component="AddOutline" /></template>
          新增候选人
        </n-button>
      </n-space>
    </div>

    <!-- 筛选区域 -->
    <n-card class="filter-card mb-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-3 flex-wrap">
          <n-input
            v-model:value="searchText"
            placeholder="搜索候选人姓名、手机号、邮箱..."
            clearable
            style="width: 280px"
            @keyup.enter="handleSearch"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-select v-model:value="positionFilter" placeholder="应聘职位" style="width: 160px" clearable :options="positionOptions" />
          <n-select v-model:value="channelFilter" placeholder="简历来源" style="width: 140px" clearable :options="channelOptions" />
          <n-select v-model:value="stageFilter" placeholder="当前阶段" style="width: 120px" clearable :options="stageOptions" />
        </div>
        <n-space>
          <n-button @click="exportData">
            <template #icon><n-icon :component="DownloadOutline" /></template>
            导出数据
          </n-button>
          <n-button @click="showMoreFilter">
            <template #icon><n-icon :component="FunnelOutline" /></template>
            更多筛选
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 统计数据 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" :item-responsive="true" class="mb-4">
      <n-grid-item span="4 m:2 l:1">
        <n-card size="small" class="stat-card text-center">
          <div class="stat-value" style="color: #FBCE5B">156</div>
          <div class="stat-label">候选人总数</div>
        </n-card>
      </n-grid-item>
      <n-grid-item span="4 m:2 l:1">
        <n-card size="small" class="stat-card text-center">
          <div class="stat-value" style="color: #13c2c2">45</div>
          <div class="stat-label">筛选中</div>
        </n-card>
      </n-grid-item>
      <n-grid-item span="4 m:2 l:1">
        <n-card size="small" class="stat-card text-center">
          <div class="stat-value" style="color: #faad14">28</div>
          <div class="stat-label">面试中</div>
        </n-card>
      </n-grid-item>
      <n-grid-item span="4 m:2 l:1">
        <n-card size="small" class="stat-card text-center">
          <div class="stat-value" style="color: #52c41a">8</div>
          <div class="stat-label">待入职</div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 表格 -->
    <n-card class="table-card">
      <n-data-table
        :columns="columns"
        :data="mockData"
        :row-key="(row: any) => row.key"
        :pagination="paginationReactive"
        :row-selection="rowSelection"
        @update:checked-row-keys="handleSelectionChange"
      />
    </n-card>

    <!-- 新增候选人弹窗 -->
    <AddCandidateModal
      v-model:visible="addModalVisible"
      @close="closeAddModal"
      @success="handleAddSuccess"
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

          <div class="editor-section" v-if="notificationForm.sendEmail">
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

          <div class="editor-section" v-if="notificationForm.sendSms">
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
import { ref, reactive, h, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, NTag, NIcon, NButton, NSpace } from 'naive-ui'
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
} from '@vicons/ionicons5'
import AddCandidateModal from './AddCandidateModal.vue'

const router = useRouter()
const message = useMessage()

const addModalVisible = ref(false)
const searchText = ref('')
const positionFilter = ref<string | undefined>()
const channelFilter = ref<string | undefined>()
const stageFilter = ref<string | undefined>()
const selectedCandidates = ref<any[]>([])
const batchNotificationModalVisible = ref(false)

const rowSelection = computed(() => ({
  selectedRowKeys: selectedCandidates.value.map((c: any) => c.key),
}))

const paginationReactive = reactive({
  page: 1,
  pageSize: 10,
  itemCount: 156,
  showTotal: (total: number) => `共 ${total} 条`,
  showSizePicker: true,
  showQuickJumper: true,
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

// 表格列（Naive render 函数）
const columns = [
  {
    title: '候选人',
    key: 'name',
    render: (row: any) =>
      h('div', { class: 'candidate-cell', onClick: () => handleViewDetail(row) }, [
        h(NIcon, { size: 32, color: '#FBCE5B', round: true }, { default: () => row.name?.[0] || 'A' }),
        h('div', { class: 'candidate-info' }, [
          h('div', { class: 'candidate-name' }, row.name),
          h('div', { class: 'candidate-email' }, row.email),
        ]),
      ]),
  },
  {
    title: '手机号',
    key: 'phone',
    render: (row: any) =>
      h('span', null, [
        h(NIcon, { component: CallOutline, size: 14, style: 'margin-right: 4px' }),
        row.phone,
      ]),
  },
  {
    title: '应聘职位',
    key: 'position',
    render: (row: any) => h(NTag, { type: 'info' }, { default: () => row.position }),
  },
  {
    title: '简历来源',
    key: 'channel',
    render: (row: any) =>
      h(NTag, { type: channelToTagType(row.channel) as any }, { default: () => getChannelText(row.channel) }),
  },
  {
    title: '当前阶段',
    key: 'stage',
    render: (row: any) =>
      h(NTag, { type: stageToTagType(row.stage) as any }, { default: () => getStageText(row.stage) }),
  },
  { title: '添加时间', key: 'createdAt' },
  {
    title: '操作',
    key: 'action',
    width: 120,
    render: (row: any) =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => handleViewDetail(row) }, { default: () => '查看' }),
          h(
            NButton,
            { text: true, size: 'small' },
            {
              default: () => h(NIcon, { component: EllipsisHorizontalCircleOutline, size: 16 }),
            }
          ),
        ],
      }),
  },
]

// 选项
const positionOptions = [
  { label: '前端开发工程师', value: '1' },
  { label: '后端开发工程师', value: '2' },
  { label: '产品经理', value: '3' },
  { label: 'UI设计师', value: '4' },
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

const mockData = [
  { key: '1', name: '张三', email: 'zhangsan@example.com', phone: '138****8888', position: '前端开发工程师', channel: 'boss', stage: 'screening', createdAt: '2026-04-27' },
  { key: '2', name: '李四', email: 'lisi@example.com', phone: '139****6666', position: '产品经理', channel: 'lagou', stage: 'interview', createdAt: '2026-04-26' },
  { key: '3', name: '王五', email: 'wangwu@example.com', phone: '137****5555', position: 'UI设计师', channel: 'liepin', stage: 'offer', createdAt: '2026-04-25' },
  { key: '4', name: '赵六', email: 'zhaoliu@example.com', phone: '136****4444', position: '后端开发工程师', channel: 'internal', stage: 'hired', createdAt: '2026-04-24' },
]

const channelMap: Record<string, { text: string; tagType: string }> = {
  boss: { text: 'Boss直聘', tagType: 'info' },
  lagou: { text: '拉勾网', tagType: 'info' },
  liepin: { text: '猎聘网', tagType: 'warning' },
  internal: { text: '内部推荐', tagType: 'success' },
}

const stageMap: Record<string, { text: string; tagType: string }> = {
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
const closeAddModal = () => { addModalVisible.value = false }
const handleAddSuccess = () => { message.success('候选人添加成功') }
const handleSelectionChange = (keys: any[]) => {
  selectedCandidates.value = mockData.filter((d) => keys.includes(d.key))
}
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
  selectedCandidates.value = []
}
const handleViewDetail = (record: any) => { router.push(`/candidates/${record.key}`) }
const handleSearch = () => { /* search */ }
const exportData = () => { message.info('导出功能开发中') }
const showMoreFilter = () => { message.info('更多筛选功能开发中') }
</script>

<style scoped>
.candidate-list-page { padding: 24px; }
.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title h1 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 600;
}
.add-button, .batch-notify-btn, .send-btn-primary {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%) !important;
  border: none !important;
  color: #000 !important;
}
.stat-card { border-radius: 8px; }
.stat-value { font-size: 24px; font-weight: 600; }
.stat-label { font-size: 12px; color: #999; margin-top: 4px; }
.candidate-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.candidate-info { display: flex; flex-direction: column; }
.candidate-name { font-weight: 500; color: #FBCE5B; }
.candidate-email { font-size: 12px; color: #999; }

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
  color: #000 !important; font-weight: 600;
}
.modal-content { display: flex; gap: 24px; margin-top: 24px; }
.left-sidebar { width: 280px; flex-shrink: 0; }
.step-section { margin-bottom: 24px; }
.step-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; margin: 0 0 12px; }
.step-number {
  width: 24px; height: 24px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #000; border-radius: 50%;
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

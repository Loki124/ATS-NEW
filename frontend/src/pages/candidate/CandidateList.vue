<template>
  <div class="candidate-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-title">
        <h1>候选人管理</h1>
        <a-typography-text type="secondary">管理所有候选人信息，推进招聘流程</a-typography-text>
      </div>
      <a-space>
        <a-button
          type="primary"
          @click="openBatchNotificationModal"
          :disabled="selectedCandidates.length === 0"
          class="batch-notify-btn"
        >
          <template #icon><SendOutlined /></template>
          批量发送通知 ({{ selectedCandidates.length }})
        </a-button>
        <a-button
          type="primary"
          size="large"
          @click="showAddModal"
          class="add-button"
        >
          <template #icon><PlusOutlined /></template>
          新增候选人
        </a-button>
      </a-space>
    </div>

    <!-- 筛选区域 -->
    <a-card class="filter-card">
      <a-row :gutter="[16, 16]" align="middle">
        <a-col flex="auto">
          <a-space wrap>
            <a-input
              v-model:value="searchText"
              placeholder="搜索候选人姓名、手机号、邮箱..."
              allow-clear
              style="width: 280px; border-radius: 8px"
              @pressEnter="handleSearch"
            >
              <template #prefix><SearchOutlined /></template>
            </a-input>
            <a-select v-model:value="positionFilter" placeholder="应聘职位" style="width: 160px" allow-clear>
              <a-select-option value="1">前端开发工程师</a-select-option>
              <a-select-option value="2">后端开发工程师</a-select-option>
              <a-select-option value="3">产品经理</a-select-option>
              <a-select-option value="4">UI设计师</a-select-option>
            </a-select>
            <a-select v-model:value="channelFilter" placeholder="简历来源" style="width: 140px" allow-clear>
              <a-select-option value="boss">Boss直聘</a-select-option>
              <a-select-option value="lagou">拉勾网</a-select-option>
              <a-select-option value="liepin">猎聘网</a-select-option>
              <a-select-option value="internal">内部推荐</a-select-option>
            </a-select>
            <a-select v-model:value="stageFilter" placeholder="当前阶段" style="width: 120px" allow-clear>
              <a-select-option value="screening">筛选中</a-select-option>
              <a-select-option value="interview">面试中</a-select-option>
              <a-select-option value="offer">Offer沟通</a-select-option>
              <a-select-option value="hired">已入职</a-select-option>
            </a-select>
          </a-space>
        </a-col>
        <a-col>
          <a-space>
            <a-button @click="exportData"><DownloadOutlined /> 导出数据</a-button>
            <a-button @click="showMoreFilter"><FilterOutlined /> 更多筛选</a-button>
          </a-space>
        </a-col>
      </a-row>
    </a-card>

    <!-- 统计数据 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card size="small" class="stat-card">
          <div class="stat-value" style="color: #FBCE5B">156</div>
          <div class="stat-label">候选人总数</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" class="stat-card">
          <div class="stat-value" style="color: #13c2c2">45</div>
          <div class="stat-label">筛选中</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" class="stat-card">
          <div class="stat-value" style="color: #faad14">28</div>
          <div class="stat-label">面试中</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" class="stat-card">
          <div class="stat-value" style="color: #52c41a">8</div>
          <div class="stat-label">待入职</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 表格 -->
    <a-card class="table-card">
      <a-table
        :columns="columns"
        :data-source="mockData"
        :row-key="(record: any) => record.key"
        :pagination="{
          total: 156,
          pageSize: 10,
          showTotal: (total: number) => `共 ${total} 条`,
          showSizeChanger: true,
          showQuickJumper: true,
        }"
        :row-selection="rowSelection"
        style="border-radius: 8px"
        @selection-change="handleSelectionChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="candidate-cell" @click="handleViewDetail(record)">
              <a-avatar :style="{ background: 'linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%)', color: '#000' }">
                {{ record.name?.[0] || 'A' }}
              </a-avatar>
              <div class="candidate-info">
                <div class="candidate-name">{{ record.name }}</div>
                <div class="candidate-email">{{ record.email }}</div>
              </div>
            </div>
          </template>
          <template v-else-if="column.key === 'phone'">
            <span><PhoneOutlined style="margin-right: 4px" />{{ record.phone }}</span>
          </template>
          <template v-else-if="column.key === 'position'">
            <a-tag color="blue">{{ record.position }}</a-tag>
          </template>
          <template v-else-if="column.key === 'channel'">
            <a-tag :color="getChannelColor(record.channel)">{{ getChannelText(record.channel) }}</a-tag>
          </template>
          <template v-else-if="column.key === 'stage'">
            <a-tag :color="getStageColor(record.stage)">{{ getStageText(record.stage) }}</a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="handleViewDetail(record)">查看</a-button>
              <a-dropdown :trigger="['click']">
                <a-button type="text" size="small">
                  <MoreOutlined />
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item key="view" @click="handleViewDetail(record)">查看详情</a-menu-item>
                    <a-menu-item key="edit">编辑</a-menu-item>
                    <a-menu-item key="transfer">转移到其他职位</a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="archive" danger>归档</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增候选人弹窗 -->
    <AddCandidateModal
      v-model:visible="addModalVisible"
      @close="closeAddModal"
      @success="handleAddSuccess"
    />

    <!-- 批量发送通知弹窗 -->
    <a-modal
      v-model:open="batchNotificationModalVisible"
      :width="1000"
      :footer="null"
      :maskClosable="false"
      class="notification-modal"
    >
      <template #title>
        <div class="modal-header">
          <span class="modal-title">批量发送通知</span>
          <button class="close-btn" @click="batchNotificationModalVisible = false">
            <CloseOutlined />
          </button>
        </div>
        <div class="candidate-summary">
          <a-avatar :size="48" class="candidate-avatar-sm">
            {{ selectedCandidates.length }}
          </a-avatar>
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
              <!-- 面试登记表 -->
              <div class="content-group">
                <div class="content-group-title">面试登记表</div>
                <label class="content-item selected">
                  <a-checkbox v-model:checked="notificationForm.interviewForm"></a-checkbox>
                  <span>收集候选人基本信息</span>
                </label>
              </div>
              <!-- 性格测试 -->
              <div class="content-group">
                <div class="content-group-title">性格测试</div>
                <div class="radio-group">
                  <label class="radio-item">
                    <a-radio-group v-model:value="notificationForm.personalityTest">
                      <a-radio value="pdp_mbti_20">PDP+20题版MBTI</a-radio>
                    </a-radio-group>
                  </label>
                  <label class="radio-item">
                    <a-radio-group v-model:value="notificationForm.personalityTest">
                      <a-radio value="pdp_mbti_93">PDP+93题版MBTI</a-radio>
                    </a-radio-group>
                  </label>
                </div>
              </div>
              <!-- 应聘登记表 -->
              <div class="content-group">
                <div class="content-group-title">应聘登记表</div>
                <label class="content-item">
                  <a-checkbox v-model:checked="notificationForm.applicationForm"></a-checkbox>
                  <span>完善工作履历及教育背景</span>
                </label>
              </div>
              <!-- 入职材料 -->
              <div class="content-group">
                <div class="content-group-title">入职材料</div>
                <label class="content-item">
                  <a-checkbox v-model:checked="notificationForm.onboardingDocs"></a-checkbox>
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
                <a-checkbox v-model:checked="notificationForm.sendEmail"></a-checkbox>
                <MailOutlined class="method-icon" />
                <span class="method-name">邮件通知</span>
              </label>
              <label class="method-item selected">
                <a-checkbox v-model:checked="notificationForm.sendSms"></a-checkbox>
                <MessageOutlined class="method-icon" />
                <span class="method-name">短信通知</span>
              </label>
              <label class="method-item">
                <a-checkbox v-model:checked="notificationForm.sendWechat"></a-checkbox>
                <WechatOutlined class="method-icon" />
                <span class="method-name">微信企业号推送</span>
              </label>
            </div>
          </div>
        </div>

        <!-- 右侧内容区域 -->
        <div class="right-content">
          <!-- 提示信息 -->
          <div class="info-callout">
            <span>系统将基于选择的「发送内容」自动为候选人生成对应待办，选择多个内容时会同时发送</span>
          </div>

          <!-- 邮件通知编辑 -->
          <div class="editor-section" v-if="notificationForm.sendEmail">
            <div class="editor-header">
              <MailOutlined class="editor-icon" />
              <h4 class="editor-title">邮件通知</h4>
            </div>
            <div class="editor-field">
              <label class="field-label">邮件主题</label>
              <a-input
                v-model:value="notificationForm.emailSubject"
                class="email-subject-input"
              />
            </div>
            <div class="editor-field">
              <label class="field-label">邮件正文</label>
              <a-textarea
                v-model:value="notificationForm.emailContent"
                :rows="8"
                class="email-content-input"
              />
            </div>
          </div>

          <!-- 短信通知编辑 -->
          <div class="editor-section" v-if="notificationForm.sendSms">
            <div class="editor-header">
              <MessageOutlined class="editor-icon" />
              <h4 class="editor-title">短信通知</h4>
            </div>
            <div class="editor-field">
              <div class="sms-counter">
                <label class="field-label">短信正文</label>
                <span class="counter-text">已输入 <strong>{{ notificationForm.smsContent.length }}</strong> / 70 字</span>
              </div>
              <a-textarea
                v-model:value="notificationForm.smsContent"
                :rows="4"
                class="sms-content-input"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部 -->
      <div class="modal-footer">
        <div class="recipient-info">
          通知将发送至: {{ selectedCandidates.length }} 个候选人
        </div>
        <div class="footer-buttons">
          <a-button @click="batchNotificationModalVisible = false">取消</a-button>
          <a-button type="primary" class="send-btn-primary" @click="handleBatchSendNotification">
            <template #icon><SendOutlined /></template>
            确认发送
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  MoreOutlined,
  PhoneOutlined,
  SendOutlined,
  CloseOutlined,
  MailOutlined,
  MessageOutlined,
  WechatOutlined,
} from '@ant-design/icons-vue'
import AddCandidateModal from './AddCandidateModal.vue'

const router = useRouter()

const addModalVisible = ref(false)
const searchText = ref('')
const positionFilter = ref<string | undefined>()
const channelFilter = ref<string | undefined>()
const stageFilter = ref<string | undefined>()
const selectedCandidates = ref<any[]>([])
const batchNotificationModalVisible = ref(false)

const rowSelection = computed(() => ({
  selectedRowKeys: selectedCandidates.value.map((c: any) => c.key),
  onChange: (selectedRowKeys: any[], selectedRows: any[]) => {
    selectedCandidates.value = selectedRows
  },
}))

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

const columns = [
  {
    title: '候选人',
    key: 'name',
    dataIndex: 'name',
  },
  {
    title: '手机号',
    key: 'phone',
    dataIndex: 'phone',
  },
  {
    title: '应聘职位',
    key: 'position',
    dataIndex: 'position',
  },
  {
    title: '简历来源',
    key: 'channel',
    dataIndex: 'channel',
  },
  {
    title: '当前阶段',
    key: 'stage',
    dataIndex: 'stage',
  },
  {
    title: '添加时间',
    key: 'createdAt',
    dataIndex: 'createdAt',
  },
  {
    title: '操作',
    key: 'action',
    width: 100,
  },
]

const mockData = [
  {
    key: '1',
    name: '张三',
    email: 'zhangsan@example.com',
    phone: '138****8888',
    position: '前端开发工程师',
    channel: 'boss',
    stage: 'screening',
    createdAt: '2026-04-27',
  },
  {
    key: '2',
    name: '李四',
    email: 'lisi@example.com',
    phone: '139****6666',
    position: '产品经理',
    channel: 'lagou',
    stage: 'interview',
    createdAt: '2026-04-26',
  },
  {
    key: '3',
    name: '王五',
    email: 'wangwu@example.com',
    phone: '137****5555',
    position: 'UI设计师',
    channel: 'liepin',
    stage: 'offer',
    createdAt: '2026-04-25',
  },
  {
    key: '4',
    name: '赵六',
    email: 'zhaoliu@example.com',
    phone: '136****4444',
    position: '后端开发工程师',
    channel: 'internal',
    stage: 'hired',
    createdAt: '2026-04-24',
  },
]

const channelMap: Record<string, { text: string; color: string }> = {
  boss: { text: 'Boss直聘', color: 'purple' },
  lagou: { text: '拉勾网', color: 'cyan' },
  liepin: { text: '猎聘网', color: 'orange' },
  internal: { text: '内部推荐', color: 'green' },
}

const stageMap: Record<string, { text: string; color: string }> = {
  screening: { text: '筛选中', color: 'processing' },
  interview: { text: '面试中', color: 'warning' },
  offer: { text: 'Offer沟通', color: 'orange' },
  hired: { text: '已入职', color: 'success' },
}

const getChannelColor = (channel: string) => {
  return channelMap[channel]?.color || 'default'
}

const getChannelText = (channel: string) => {
  return channelMap[channel]?.text || channel
}

const getStageColor = (stage: string) => {
  return stageMap[stage]?.color || 'default'
}

const getStageText = (stage: string) => {
  return stageMap[stage]?.text || stage
}

const showAddModal = () => {
  addModalVisible.value = true
}

const closeAddModal = () => {
  addModalVisible.value = false
}

const handleAddSuccess = () => {
  message.success('候选人添加成功')
}

const handleSelectionChange = (selectedRowKeys: any[], selectedRows: any[]) => {
  selectedCandidates.value = selectedRows
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
  // 发送逻辑
  const selectedCount = selectedCandidates.value.length
  message.success(`已成功向 ${selectedCount} 位候选人发送通知`)
  batchNotificationModalVisible.value = false
  // Reset selection
  selectedCandidates.value = []
}

const handleViewDetail = (record: any) => {
  router.push(`/candidates/${record.key}`)
}

const handleSearch = () => {
  // 搜索逻辑
}

const exportData = () => {
  message.info('导出功能开发中')
}

const showMoreFilter = () => {
  message.info('更多筛选功能开发中')
}
</script>

<style scoped>
.candidate-list-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.add-button {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  border: none;
  color: #000 !important;
}

.filter-card {
  margin-bottom: 16px;
  border-radius: 12px;
}

.stat-card {
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.table-card {
  border-radius: 12px;
}

.candidate-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.candidate-info {
  display: flex;
  flex-direction: column;
}

.candidate-name {
  font-weight: 500;
  color: #FBCE5B;
}

.candidate-email {
  font-size: 12px;
  color: #999;
}

/* Batch notification modal styles */
.batch-notify-btn {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  border: none;
  color: #000 !important;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #999;
}

.close-btn:hover {
  color: #333;
}

.candidate-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.candidate-avatar-sm {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #000;
  font-weight: 600;
}

.modal-content {
  display: flex;
  gap: 24px;
  margin-top: 24px;
}

.left-sidebar {
  width: 280px;
  flex-shrink: 0;
}

.step-section {
  margin-bottom: 24px;
}

.step-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.step-number {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  color: #000;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.step-content {
  padding-left: 32px;
}

.content-group {
  margin-bottom: 16px;
}

.content-group-title {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.content-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s;
}

.content-item:hover {
  background: #f5f5f5;
}

.content-item.selected {
  background: #f0f0ff;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.radio-item {
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
}

.radio-item:hover {
  background: #f5f5f5;
}

.method-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.3s;
  margin-bottom: 8px;
}

.method-item:hover {
  background: #f5f5f5;
}

.method-item.selected {
  background: #f0f0ff;
  border: 1px solid #FBCE5B;
}

.method-icon {
  font-size: 18px;
  color: #FBCE5B;
}

.method-name {
  font-weight: 500;
}

.right-content {
  flex: 1;
  min-width: 0;
}

.info-callout {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  color: #1890ff;
  margin-bottom: 16px;
}

.editor-section {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.editor-icon {
  font-size: 18px;
  color: #FBCE5B;
}

.editor-title {
  font-weight: 600;
  margin: 0;
}

.editor-field {
  margin-bottom: 12px;
}

.field-label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
}

.email-subject-input,
.email-content-input,
.sms-content-input {
  border-radius: 6px;
}

.sms-counter {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.counter-text {
  font-size: 12px;
  color: #999;
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.recipient-info {
  font-size: 14px;
  color: #666;
}

.footer-buttons {
  display: flex;
  gap: 8px;
}

.send-btn-primary {
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  border: none;
  color: #000 !important;
}
</style>
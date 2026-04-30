<template>
  <div class="candidate-list-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-title">
        <h1>候选人管理</h1>
        <a-typography-text type="secondary">管理所有候选人信息，推进招聘流程</a-typography-text>
      </div>
      <a-button 
        type="primary" 
        size="large"
        @click="showAddModal"
        class="add-button"
      >
        <template #icon><PlusOutlined /></template>
        新增候选人
      </a-button>
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
          <div class="stat-value" style="color: #667eea">156</div>
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
        style="border-radius: 8px"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="candidate-cell" @click="handleViewDetail(record)">
              <a-avatar :style="{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }">
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  DownloadOutlined,
  MoreOutlined,
  PhoneOutlined,
} from '@ant-design/icons-vue'
import AddCandidateModal from './AddCandidateModal.vue'

const router = useRouter()

const addModalVisible = ref(false)
const searchText = ref('')
const positionFilter = ref<string | undefined>()
const channelFilter = ref<string | undefined>()
const stageFilter = ref<string | undefined>()

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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  height: 40px;
  padding-left: 20px;
  padding-right: 20px;
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
  color: #667eea;
}

.candidate-email {
  font-size: 12px;
  color: #999;
}
</style>
<template>
  <div class="resume-list-container">
    <!-- 顶部导航和筛选 -->
    <div class="page-header">
      <n-tabs v-model:value="activeTab" type="line" @update:value="handleTabChange">
        <n-tab-pane name="PENDING_ASSIGN" tab="待分配" />
        <n-tab-pane name="ASSIGNED" tab="已分配" />
        <n-tab-pane name="ARCHIVED" tab="已归档" />
        <n-tab-pane name="DUPLICATE" tab="重复简历" />
      </n-tabs>
      <n-space>
        <n-button @click="handleRefresh">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          刷新
        </n-button>
      </n-space>
    </div>

    <!-- 子筛选 -->
    <div class="sub-filters" v-if="activeTab === 'PENDING_ASSIGN'">
      <n-space>
        <n-radio-group v-model:value="subStatus" @update:value="handleSubStatusChange">
          <n-radio-button value="">全部</n-radio-button>
          <n-radio-button value="SCORING">评分中</n-radio-button>
          <n-radio-button value="APPROVAL">审批中</n-radio-button>
          <n-radio-button value="SUSPECTED">疑似</n-radio-button>
        </n-radio-group>
      </n-space>
    </div>

    <!-- 简历列表 -->
    <n-spin :show="loading">
      <div class="resume-grid">
        <n-card
          v-for="resume in resumeList"
          :key="resume.id"
          class="resume-card"
          hoverable
          @click="handleViewResume(resume)"
        >
          <div class="resume-card-header">
            <div class="resume-name">{{ resume.candidate?.name || '未知' }}</div>
            <n-tag :type="getStatusType(resume.resumeStatus)">
              {{ getStatusText(resume.resumeStatus) }}
            </n-tag>
          </div>

          <div class="resume-card-body">
            <div class="info-row">
              <n-icon :component="CallOutline" /> {{ resume.candidate?.phone || '-' }}
            </div>
            <div class="info-row">
              <n-icon :component="MailOutline" /> {{ resume.candidate?.email || '-' }}
            </div>
            <div class="info-row">
              <n-icon :component="DocumentTextOutline" /> {{ resume.source || '-' }}
            </div>
            <div class="info-row" v-if="resume.matchScore">
              <n-icon :component="StarOutline" /> 匹配度: {{ resume.matchScore }}
            </div>
          </div>

          <!-- 锁定人信息 -->
          <div class="locker-info" v-if="resume.formalLockerId || resume.tempLockerId">
            <n-tooltip :placement="'top'">
              <template #trigger>
                <div class="locker-badge">
                  <n-icon :component="LockClosedOutline" />
                  <span v-if="resume.formalLockerId">正式: {{ getLockerName(resume) }}</span>
                  <span v-else-if="resume.tempLockerId">临时: {{ getTempLockerTime(resume) }}</span>
                </div>
              </template>
              {{ getLockerTooltip(resume) }}
            </n-tooltip>
          </div>

          <!-- 子状态标记 -->
          <div class="sub-status-tags" v-if="resume.resumeSubStatus">
            <n-tag v-if="resume.resumeSubStatus === 'SCORING'" type="info">
              <template #icon><n-icon :component="SyncOutline" /></template>
              评分中
            </n-tag>
            <n-tag v-if="resume.resumeSubStatus === 'APPROVAL'" type="warning">
              <template #icon><n-icon :component="TimeOutline" /></template>
              审批中
            </n-tag>
          </div>

          <div class="resume-card-footer">
            <span class="create-time">{{ formatDate(resume.createdAt) }}</span>
            <n-space size="small">
              <n-button
                text
                type="primary"
                size="small"
                v-if="canAssign(resume)"
                :disabled="resume.resumeSubStatus === 'SCORING'"
                @click.stop="handleAssign(resume)"
              >
                分配
              </n-button>
              <n-button
                text
                type="primary"
                size="small"
                v-if="canArchive(resume)"
                @click.stop="handleArchive(resume)"
              >
                归档
              </n-button>
              <n-button
                text
                type="primary"
                size="small"
                v-if="canActivate(resume)"
                @click.stop="handleActivate(resume)"
              >
                激活
              </n-button>
            </n-space>
          </div>
        </n-card>
      </div>

      <!-- 空状态 -->
      <n-empty v-if="!loading && resumeList.length === 0" description="暂无简历" />
    </n-spin>

    <!-- 分页 -->
    <div class="pagination" v-if="total > 0">
      <n-pagination
        v-model:page="currentPage"
        :page-size="pageSize"
        :item-count="total"
        show-quick-jumper
        @update:page="handlePageChange"
      />
    </div>

    <!-- 简历详情抽屉 -->
    <n-drawer v-model:show="detailVisible" :width="600" placement="right">
      <n-drawer-content :title="currentResume?.candidate?.name" closable>
        <template v-if="currentResume">
          <n-descriptions title="基本信息" :column="2">
            <n-descriptions-item label="姓名">{{ currentResume.candidate?.name }}</n-descriptions-item>
            <n-descriptions-item label="手机">{{ currentResume.candidate?.phone }}</n-descriptions-item>
            <n-descriptions-item label="邮箱">{{ currentResume.candidate?.email }}</n-descriptions-item>
            <n-descriptions-item label="来源">{{ currentResume.source }}</n-descriptions-item>
          </n-descriptions>

          <n-divider />

          <!-- 锁定人信息 -->
          <div class="locker-section">
            <h4><n-icon :component="LockClosedOutline" /> 锁定人信息</h4>
            <n-space vertical style="width: 100%">
              <n-alert
                v-if="currentResume.formalLockerId"
                type="success"
                :title="`正式锁定人: ${getFormalLockerName(currentResume)}`"
                show-icon
              />
              <n-alert
                v-if="currentResume.tempLockerId && isTempLockerValid(currentResume)"
                type="info"
                :title="`临时锁定人: ${getTempLockerName(currentResume)} (剩余: ${getTempLockerRemaining(currentResume)})`"
                show-icon
              />
            </n-space>
          </div>

          <n-divider />

          <!-- 操作按钮 -->
          <n-space vertical style="width: 100%">
            <n-button
              v-if="canAssign(currentResume)"
              type="primary"
              block
              :disabled="currentResume.resumeSubStatus === 'SCORING'"
              @click="handleAssign(currentResume)"
            >
              分配到职位
            </n-button>
            <n-button
              v-if="canArchive(currentResume)"
              block
              @click="handleArchive(currentResume)"
            >
              放入人才库
            </n-button>
            <n-button
              v-if="canActivate(currentResume)"
              type="primary"
              block
              @click="handleActivate(currentResume)"
            >
              重新激活
            </n-button>
          </n-space>

          <n-divider />

          <!-- 流转日志 -->
          <h4><n-icon :component="TimeOutline" /> 流转日志</h4>
          <n-timeline>
            <n-timeline-item v-for="log in flowLogs" :key="log.id">
              <p><strong>{{ getActionText(log.action) }}</strong></p>
              <p v-if="log.operatorName">{{ log.operatorName }}</p>
              <p class="log-time">{{ formatDate(log.createdAt) }}</p>
            </n-timeline-item>
          </n-timeline>
        </template>
      </n-drawer-content>
    </n-drawer>

    <!-- 分配弹窗 -->
    <n-modal
      v-model:show="assignVisible"
      preset="dialog"
      title="分配简历"
      positive-text="确定"
      negative-text="取消"
      :loading="assignLoading"
      @positive-click="handleAssignConfirm"
    >
      <n-form :model="assignForm" label-placement="top" class="mt-4">
        <n-form-item label="选择职位" required>
          <n-select
            v-model:value="assignForm.positionId"
            placeholder="请选择目标职位"
            filterable
            :options="positionOptions"
          />
        </n-form-item>
        <n-form-item label="跳过评分">
          <n-checkbox v-model:checked="assignForm.skipScoring">直接分配，不进行匹配度评分</n-checkbox>
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import {
  RefreshOutline,
  CallOutline,
  MailOutline,
  DocumentTextOutline,
  StarOutline,
  LockClosedOutline,
  TimeOutline,
  SyncOutline,
} from '@vicons/ionicons5'
import { get, post } from '../../api/auth'

const message = useMessage()

// 状态
const activeTab = ref('PENDING_ASSIGN')
const subStatus = ref('')
const loading = ref(false)
const resumeList = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 详情抽屉
const detailVisible = ref(false)
const currentResume = ref<any>(null)
const flowLogs = ref<any[]>([])

// 分配弹窗
const assignVisible = ref(false)
const assignLoading = ref(false)
const assignForm = reactive({
  resumeId: '',
  positionId: '',
  skipScoring: false
})

// 职位选项
const positionOptions = ref<any[]>([])

// 加载简历列表
const loadResumes = async () => {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, pageSize: pageSize.value }
    if (activeTab.value !== 'DUPLICATE') {
      params.status = activeTab.value
    } else {
      params.status = 'DELETED'
      params.duplicateOfId = 'not_null'
    }
    if (subStatus.value) {
      params.subStatus = subStatus.value
    }

    const res = await get('/resumes', { params })
    if (res.data.success) {
      resumeList.value = res.data.data.list
      total.value = res.data.data.total
    }
  } catch (error) {
    console.error('加载简历失败', error)
  } finally {
    loading.value = false
  }
}

// 加载职位列表
const loadPositions = async () => {
  try {
    const res = await get('/positions', { params: { status: 'ACTIVE' } })
    if (res.data.success) {
      positionOptions.value = res.data.data.map((p: any) => ({
        value: p.id,
        label: `${p.name} (${p.department?.name || '未知部门'})`
      }))
    }
  } catch (error) {
    console.error('加载职位失败', error)
  }
}

// 加载流转日志
const loadFlowLogs = async (resumeId: string) => {
  try {
    const res = await get(`/resume/${resumeId}/flow-logs`)
    if (res.data.success) {
      flowLogs.value = res.data.data
    }
  } catch (error) {
    console.error('加载流转日志失败', error)
  }
}

// Tab切换
const handleTabChange = () => {
  currentPage.value = 1
  subStatus.value = ''
  loadResumes()
}

// 子状态筛选
const handleSubStatusChange = () => {
  currentPage.value = 1
  loadResumes()
}

// 刷新
const handleRefresh = () => {
  loadResumes()
}

// 分页
const handlePageChange = (page: number) => {
  currentPage.value = page
  loadResumes()
}

// 查看简历
const handleViewResume = async (resume: any) => {
  currentResume.value = resume
  detailVisible.value = true
  await loadFlowLogs(resume.id)
}

// 分配简历
const handleAssign = (resume: any) => {
  assignForm.resumeId = resume.id
  assignForm.positionId = ''
  assignForm.skipScoring = false
  assignVisible.value = true
}

// 确认分配
const handleAssignConfirm = async () => {
  if (!assignForm.positionId) {
    message.warning('请选择职位')
    return false
  }

  assignLoading.value = true
  try {
    const res = await post(`/resume/${assignForm.resumeId}/assign`, {
      positionId: assignForm.positionId,
      operatorId: localStorage.getItem('userId'),
      skipScoring: assignForm.skipScoring
    })

    if (res.data.success) {
      message.success(res.data.data?.needScoring ? '简历正在评分中' : '分配成功')
      assignVisible.value = false
      loadResumes()
    } else {
      message.error(res.data.message || '分配失败')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.message || '分配失败')
  } finally {
    assignLoading.value = false
  }
}

// 归档简历
const handleArchive = async (resume: any) => {
  try {
    await post(`/resume/${resume.id}/archive`, {
      operatorId: localStorage.getItem('userId'),
      archiveType: 'MANUAL',
      archiveToPool: 'GENERAL'
    })
    message.success('已放入人才库')
    loadResumes()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '归档失败')
  }
}

// 激活简历
const handleActivate = async (resume: any) => {
  try {
    await post(`/resume/${resume.id}/activate`, {
      operatorId: localStorage.getItem('userId')
    })
    message.success('激活成功')
    loadResumes()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '激活失败')
  }
}

// 权限判断
const canAssign = (resume: any) => {
  return resume.resumeStatus === 'PENDING_ASSIGN' &&
    (resume.formalLockerId === localStorage.getItem('userId') ||
      resume.tempLockerId === localStorage.getItem('userId'))
}

const canArchive = (resume: any) => {
  return resume.resumeStatus === 'PENDING_ASSIGN'
}

const canActivate = (resume: any) => {
  return resume.resumeStatus === 'ARCHIVED'
}

// 状态颜色和文本
const getStatusType = (status: string): 'info' | 'success' | 'warning' | 'error' | 'default' => {
  const map: Record<string, 'info' | 'success' | 'warning' | 'error' | 'default'> = {
    'PENDING_ASSIGN': 'info',
    'ASSIGNED': 'success',
    'ARCHIVED': 'warning',
    'DELETED': 'error'
  }
  return map[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'PENDING_ASSIGN': '待分配',
    'ASSIGNED': '已分配',
    'ARCHIVED': '已归档',
    'DELETED': '已删除'
  }
  return texts[status] || status
}

// 锁定人信息
const getLockerTooltip = (resume: any) => {
  if (resume.formalLockerId) return '正式锁定人'
  if (resume.tempLockerId) return '临时锁定人 (72h)'
  return ''
}

const getLockerName = (resume: any) => {
  return resume.formalLockerName || '未知'
}

const getTempLockerTime = (resume: any) => {
  if (!resume.tempLockerExpireTime) return ''
  const remaining = new Date(resume.tempLockerExpireTime).getTime() - Date.now()
  if (remaining <= 0) return '已过期'
  const hours = Math.floor(remaining / (1000 * 60 * 60))
  const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60))
  return `${hours}:${minutes.toString().padStart(2, '0')}`
}

const isTempLockerValid = (resume: any) => {
  return resume.tempLockerExpireTime && new Date(resume.tempLockerExpireTime) > new Date()
}

const getTempLockerRemaining = (resume: any) => {
  if (!resume.tempLockerExpireTime) return ''
  const remaining = new Date(resume.tempLockerExpireTime).getTime() - Date.now()
  if (remaining <= 0) return '已过期'
  const hours = Math.floor(remaining / (1000 * 60 * 60))
  const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60))
  return `${hours}小时${minutes}分钟`
}

// 流转日志操作文本
const getActionText = (action: string) => {
  const texts: Record<string, string> = {
    'UPLOAD': '上传简历',
    'ASSIGN': '分配到职位',
    'ARCHIVE': '放入人才库',
    'ACTIVATE': '重新激活',
    'MERGE': '合并简历',
    'SCORE': '匹配度评分',
    'APPROVE': '审批通过',
    'REJECT': '审批驳回'
  }
  return texts[action] || action
}

// 日期格式化
const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

// 获取正式锁定人姓名
const getFormalLockerName = (resume: any) => {
  if (!resume.formalLockerId) return '未知'
  return resume.formalLockerName || '未知'
}

// 获取临时锁定人姓名
const getTempLockerName = (resume: any) => {
  return resume.tempLockerName || '未知'
}

onMounted(() => {
  loadResumes()
  loadPositions()
})
</script>

<style scoped>
.resume-list-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.sub-filters {
  margin-bottom: 16px;
}

.resume-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.resume-card {
  cursor: pointer;
}

.resume-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.resume-name {
  font-size: 16px;
  font-weight: 600;
}

.resume-card-body {
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #666;
  font-size: 13px;
}

.locker-info {
  margin-bottom: 8px;
}

.locker-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.sub-status-tags {
  margin-bottom: 8px;
}

.resume-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.create-time {
  font-size: 12px;
  color: #999;
}

.pagination {
  margin-top: 24px;
  text-align: right;
}

.locker-section {
  margin-bottom: 16px;
}

.locker-section h4 {
  margin-bottom: 12px;
}

.log-time {
  font-size: 12px;
  color: #999;
}
</style>

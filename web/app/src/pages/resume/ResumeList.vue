<template>
  <div class="resume-list-container">
    <!-- 顶部导航和筛选 -->
    <div class="page-header">
      <n-tabs v-model:value="activeTab" type="line" @update:value="handleTabChange">
        <n-tab-pane name="PENDING_ASSIGN" :tab="t('pages.resume.ResumeList.s1')" />
        <n-tab-pane name="ASSIGNED" :tab="t('pages.resume.ResumeList.s2')" />
        <n-tab-pane name="ARCHIVED" :tab="t('pages.resume.ResumeList.s3')" />
        <n-tab-pane name="DUPLICATE" :tab="t('pages.resume.ResumeList.s4')" />
      </n-tabs>
      <n-space>
        <n-button @click="handleRefresh">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          {{ t('pages.resume.ResumeList.s5') }}
        </n-button>
      </n-space>
    </div>

    <!-- 子筛选 -->
    <div v-if="activeTab === 'PENDING_ASSIGN'" class="sub-filters">
      <n-space>
        <n-radio-group v-model:value="subStatus" @update:value="handleSubStatusChange">
          <n-radio-button value="">{{ t('pages.resume.ResumeList.s6') }}</n-radio-button>
          <n-radio-button value="SCORING">{{ t('pages.resume.ResumeList.s7') }}</n-radio-button>
          <n-radio-button value="APPROVAL">{{ t('pages.resume.ResumeList.s8') }}</n-radio-button>
          <n-radio-button value="SUSPECTED">{{ t('pages.resume.ResumeList.s9') }}</n-radio-button>
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
            <div v-if="resume.matchScore" class="info-row">
              <n-icon :component="StarOutline" /> {{ t('pages.resume.ResumeList.s35', { n: resume.matchScore }) }}
            </div>
          </div>

          <!-- 锁定人信息 -->
          <div v-if="resume.formalLockerId || resume.tempLockerId" class="locker-info">
            <n-tooltip :placement="'top'">
              <template #trigger>
                <div class="locker-badge">
                  <n-icon :component="LockClosedOutline" />
                  <span v-if="resume.formalLockerId">{{ t('pages.resume.ResumeList.s10') }}{{ getLockerName(resume) }}</span>
                  <span v-else-if="resume.tempLockerId">{{ t('pages.resume.ResumeList.s11') }}{{ getTempLockerTime(resume) }}</span>
                </div>
              </template>
              {{ getLockerTooltip(resume) }}
            </n-tooltip>
          </div>

          <!-- 子状态标记 -->
          <div v-if="resume.resumeSubStatus" class="sub-status-tags">
            <n-tag v-if="resume.resumeSubStatus === 'SCORING'" type="info">
              <template #icon><n-icon :component="SyncOutline" /></template>
              {{ t('pages.resume.ResumeList.s12') }}
            </n-tag>
            <n-tag v-if="resume.resumeSubStatus === 'APPROVAL'" type="warning">
              <template #icon><n-icon :component="TimeOutline" /></template>
              {{ t('pages.resume.ResumeList.s13') }}
            </n-tag>
          </div>

          <div class="resume-card-footer">
            <span class="create-time">{{ formatDate(resume.createdAt) }}</span>
            <n-space size="small">
              <n-button
                v-if="canAssign(resume)"
                text
                type="primary"
                size="small"
                :disabled="resume.resumeSubStatus === 'SCORING'"
                @click.stop="handleAssign(resume)"
              >
                {{ t('pages.resume.ResumeList.s14') }}
              </n-button>
              <n-button
                v-if="canArchive(resume)"
                text
                type="primary"
                size="small"
                @click.stop="handleArchive(resume)"
              >
                {{ t('pages.resume.ResumeList.s15') }}
              </n-button>
              <n-button
                v-if="canActivate(resume)"
                text
                type="primary"
                size="small"
                @click.stop="handleActivate(resume)"
              >
                {{ t('pages.resume.ResumeList.s16') }}
              </n-button>
            </n-space>
          </div>
        </n-card>
      </div>

      <!-- 空状态 -->
      <n-empty v-if="!loading && resumeList.length === 0" :description="t('pages.resume.ResumeList.s17')" />
    </n-spin>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination">
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
          <n-descriptions :title="t('pages.resume.ResumeList.s18')" :column="2">
            <n-descriptions-item :label="t('pages.resume.ResumeList.s19')">{{ currentResume.candidate?.name }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.resume.ResumeList.s20')">{{ currentResume.candidate?.phone }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.resume.ResumeList.s21')">{{ currentResume.candidate?.email }}</n-descriptions-item>
            <n-descriptions-item :label="t('pages.resume.ResumeList.s22')">{{ currentResume.source }}</n-descriptions-item>
          </n-descriptions>

          <n-divider />

          <!-- 锁定人信息 -->
          <div class="locker-section">
            <h4><n-icon :component="LockClosedOutline" />{{ t('pages.resume.ResumeList.s23') }}</h4>
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
              {{ t('pages.resume.ResumeList.s24') }}
            </n-button>
            <n-button
              v-if="canArchive(currentResume)"
              block
              @click="handleArchive(currentResume)"
            >
              {{ t('pages.resume.ResumeList.s25') }}
            </n-button>
            <n-button
              v-if="canActivate(currentResume)"
              type="primary"
              block
              @click="handleActivate(currentResume)"
            >
              {{ t('pages.resume.ResumeList.s26') }}
            </n-button>
          </n-space>

          <n-divider />

          <!-- 流转日志 -->
          <h4><n-icon :component="TimeOutline" />{{ t('pages.resume.ResumeList.s27') }}</h4>
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
      :title="t('pages.resume.ResumeList.s28')"
      :positive-text="t('pages.resume.ResumeList.s29')"
      :negative-text="t('pages.resume.ResumeList.s30')"
      :loading="assignLoading"
      :mask-closable="false"
      :on-mask-click="requestClose"
      :close-on-esc="false"
      @negative-click="requestClose"
      @positive-click="handleAssignConfirm"
    >
      <n-form :model="assignForm" label-placement="top" class="mt-4">
        <n-form-item :label="t('pages.resume.ResumeList.s31')" required>
          <n-select
            v-model:value="assignForm.positionId"
            :placeholder="t('pages.resume.ResumeList.s32')"
            filterable
            :options="positionOptions"
          />
        </n-form-item>
        <n-form-item :label="t('pages.resume.ResumeList.s33')">
          <n-checkbox v-model:checked="assignForm.skipScoring">{{ t('pages.resume.ResumeList.s34') }}</n-checkbox>
        </n-form-item>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useCloseGuard } from '@/composables/useCloseGuard'
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
import { useI18n } from 'vue-i18n'

import { extractApiError } from '../../api/dynamic-field'
const message = useMessage()
const { t } = useI18n()

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

// 弹窗关闭守卫：保存中拦截；有未保存修改时二次确认（防点遮罩/ESC 静默丢草稿）
const { requestClose } = useCloseGuard({
  isSaving: () => assignLoading.value,
  isDirty: () => true,
  onClose: () => { assignVisible.value = false },
})
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

    // 2026-07-01 花无缺: 之前是 '/resumes' (404), 实际后端在 '/scraped-resumes/'
    const res = await get('/scraped-resumes', { params })
    if (res.data.success) {
      resumeList.value = res.data.data
      total.value = res.data.pagination?.total ?? 0
    }
  } catch (error) {
    message.error(extractApiError(error, '加载简历失败'))
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
    message.error(extractApiError(error, '加载职位失败'))
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
    message.error(extractApiError(error, '加载流转日志失败'))
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
  padding: var(--space-6);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.sub-filters {
  margin-bottom: var(--space-4);
}

.resume-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.resume-card {
  cursor: pointer;
}

.resume-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.resume-name {
  font-size: var(--fs-16);
  font-weight: 600;
}

.resume-card-body {
  margin-bottom: var(--space-3);
}

.info-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  color: var(--n-500);
  font-size: var(--fs-13);
}

.locker-info {
  margin-bottom: var(--space-2);
}

.locker-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px var(--space-2);
  background: var(--glass-bg-input);
  border-radius: 4px;
  font-size: var(--fs-12);
  color: var(--n-500);
}

.sub-status-tags {
  margin-bottom: var(--space-2);
}

.resume-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-hairline);
}

.create-time {
  font-size: var(--fs-12);
  color: var(--n-400);
}

.pagination {
  margin-top: var(--space-6);
  text-align: right;
}

.locker-section {
  margin-bottom: var(--space-4);
}

.locker-section h4 {
  margin-bottom: var(--space-3);
}

.log-time {
  font-size: var(--fs-12);
  color: var(--n-400);
}
</style>

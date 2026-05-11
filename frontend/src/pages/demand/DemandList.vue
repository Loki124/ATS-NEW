<template>
  <div class="demand-container">
    <div class="page-header">
      <h1 class="page-title">需求管理</h1>
      <a-space>
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索需求名称或编号"
          style="width: 240px"
          @search="handleSearch"
        />
        <a-select
          v-model:value="filterStatus"
          placeholder="需求状态"
          style="width: 120px"
          allowClear
          @change="handleFilter"
        >
          <a-select-option value="DRAFT">草稿</a-select-option>
          <a-select-option value="IN_PROGRESS">进行中</a-select-option>
          <a-select-option value="COMPLETED">已完成</a-select-option>
          <a-select-option value="PAUSED">已暂停</a-select-option>
        </a-select>
        <a-button type="primary" @click="handleCreate">
          <template #icon><PlusOutlined /></template>
          创建需求
        </a-button>
      </a-space>
    </div>

    <!-- 卡片列表 -->
    <div class="demand-list">
      <div
        v-for="item in demands"
        :key="item.id"
        class="demand-card"
        :class="{ 'selected': selectedDemand?.id === item.id }"
      >
        <div class="card-left" @click="handleCardClick(item)">
          <div class="card-main">
            <div class="card-title">
              <span class="demand-code">{{ item.code }}</span>
              <a-tag :color="getStatusColor(item.demandStatus)" class="status-tag">
                {{ getStatusText(item.demandStatus) }}
              </a-tag>
              <a-tag :color="getApprovalColor(item.approvalStatus)" class="status-tag">
                {{ getApprovalText(item.approvalStatus) }}
              </a-tag>
            </div>
            <div class="demand-name">{{ item.name }}</div>
            <div class="demand-meta">
              <span class="meta-item">
                <span class="label">部门：</span>
                <span class="value">{{ item.department?.name || '-' }}</span>
              </span>
              <span class="meta-item">
                <span class="label">类型：</span>
                <a-tag :color="item.demandType === 'SOCIAL' ? 'blue' : 'green'" size="small">
                  {{ item.demandType === 'SOCIAL' ? '社招' : '校招' }}
                </a-tag>
              </span>
              <span class="meta-item">
                <span class="label">薪资：</span>
                <span class="value">
                  {{ item.salaryMin && item.salaryMax ? `${item.salaryMin}K - ${item.salaryMax}K` : '-' }}
                </span>
              </span>
            </div>
          </div>
          <div class="card-stats">
            <div class="stat-item">
              <span class="stat-value">{{ item._count?.positions || 0 }}</span>
              <span class="stat-label">职位</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-value">{{ item.hiredCount || 0 }}</span>
              <span class="stat-label">入职</span>
            </div>
          </div>
        </div>
        <div class="card-right">
          <a-button type="text" @click.stop="handleEdit(item)">编辑</a-button>
          <a-button type="text" @click.stop="handleCardClick(item)">详情</a-button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">
      <a-spin />
    </div>

    <div v-if="demands.length === 0 && !loading" class="empty-wrapper">
      <a-empty description="暂无需求数据">
        <a-button type="primary" @click="handleCreate">创建需求</a-button>
      </a-empty>
    </div>

    <!-- 加载状态 -->
    <a-spin v-if="loading" class="loading-spinner" />

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:open="detailVisible"
      :title="selectedDemand?.code + ' ' + selectedDemand?.name"
      :width="680"
      placement="right"
      @close="detailVisible = false"
    >
      <template v-if="selectedDemand">
        <!-- 基本信息 -->
        <a-tabs v-model:activeKey="activeTab" class="detail-tabs">
          <a-tab-pane key="detail" tab="详情">
            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">基本信息</span>
              </div>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">需求编号</span>
                  <span class="info-value code">{{ selectedDemand.code }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">需求名称</span>
                  <span class="info-value">{{ selectedDemand.name }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">所属部门</span>
                  <span class="info-value">{{ selectedDemand.department?.name || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">需求人数</span>
                  <span class="info-value">{{ selectedDemand.positionCount }}人</span>
                </div>
                <div class="info-item">
                  <span class="info-label">需求类型</span>
                  <span class="info-value">
                    <a-tag :color="selectedDemand.demandType === 'SOCIAL' ? 'blue' : 'green'" size="small">
                      {{ selectedDemand.demandType === 'SOCIAL' ? '社会招聘' : '校园招聘' }}
                    </a-tag>
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">需求状态</span>
                  <span class="info-value">
                    <a-tag :color="getStatusColor(selectedDemand.demandStatus)">
                      {{ getStatusText(selectedDemand.demandStatus) }}
                    </a-tag>
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">审批状态</span>
                  <span class="info-value">
                    <a-tag :color="getApprovalColor(selectedDemand.approvalStatus)">
                      {{ getApprovalText(selectedDemand.approvalStatus) }}
                    </a-tag>
                  </span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">职位信息</span>
              </div>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">职位系列</span>
                  <span class="info-value">{{ selectedDemand.positionSeries || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">职级</span>
                  <span class="info-value">{{ selectedDemand.jobLevel || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">薪资范围</span>
                  <span class="info-value">
                    {{ selectedDemand.salaryMin && selectedDemand.salaryMax ? `${selectedDemand.salaryMin}K - ${selectedDemand.salaryMax}K` : '-' }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">开始日期</span>
                  <span class="info-value">{{ formatDate(selectedDemand.startDate) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">结束日期</span>
                  <span class="info-value">{{ formatDate(selectedDemand.endDate) }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">描述信息</span>
              </div>
              <div class="desc-content">
                <div class="desc-item">
                  <span class="desc-label">需求描述</span>
                  <div class="desc-value">{{ selectedDemand.description || '-' }}</div>
                </div>
                <div class="desc-item">
                  <span class="desc-label">候选人要求</span>
                  <div class="desc-value">{{ selectedDemand.requirements || '-' }}</div>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <div class="section-header">
                <span class="section-title">招聘进度</span>
              </div>
              <div class="progress-stats">
                <div class="progress-stat">
                  <span class="stat-num">{{ selectedDemand._count?.positions || 0 }}</span>
                  <span class="stat-label">关联职位</span>
                </div>
                <div class="progress-stat">
                  <span class="stat-num">{{ selectedDemand.positionCount || 0 }}</span>
                  <span class="stat-label">需求人数</span>
                </div>
                <div class="progress-stat">
                  <span class="stat-num">{{ selectedDemand.hiredCount || 0 }}</span>
                  <span class="stat-label">已入职</span>
                </div>
                <div class="progress-stat">
                  <span class="stat-num">{{ selectedDemand.onBoardCount || 0 }}</span>
                  <span class="stat-label">待入职</span>
                </div>
              </div>
            </div>
          </a-tab-pane>

          <a-tab-pane key="candidates" tab="候选人">
            <a-empty description="暂无候选人数据" />
          </a-tab-pane>

          <a-tab-pane key="profile" tab="职位画像">
            <div class="profile-section">
              <div class="profile-header">
                <span class="profile-title">职位画像</span>
                <span class="profile-subtitle">基于需求信息生成</span>
              </div>

              <div class="profile-content">
                <!-- 硬性要求 -->
                <div class="profile-block">
                  <div class="block-header">
                    <span class="block-title">硬性要求</span>
                  </div>
                  <div class="block-items">
                    <div class="profile-item">
                      <span class="item-icon">🎓</span>
                      <span class="item-label">学历要求</span>
                      <span class="item-value">{{ getEducationText(selectedDemand) }}</span>
                    </div>
                    <div class="profile-item">
                      <span class="item-icon">💼</span>
                      <span class="item-label">工作经验</span>
                      <span class="item-value">{{ getExperienceText(selectedDemand) }}</span>
                    </div>
                    <div class="profile-item">
                      <span class="item-icon">🏢</span>
                      <span class="item-label">职级要求</span>
                      <span class="item-value">{{ selectedDemand.jobLevel || '-' }}</span>
                    </div>
                    <div class="profile-item">
                      <span class="item-icon">👥</span>
                      <span class="item-label">招聘人数</span>
                      <span class="item-value">{{ selectedDemand.positionCount }}人</span>
                    </div>
                  </div>
                </div>

                <!-- 技能要求 -->
                <div class="profile-block">
                  <div class="block-header">
                    <span class="block-title">技能要求</span>
                  </div>
                  <div class="skills-list">
                    <a-tag v-for="skill in getSkillsList(selectedDemand)" :key="skill" color="blue">{{ skill }}</a-tag>
                    <span v-if="getSkillsList(selectedDemand).length === 0" class="no-data">暂无技能要求</span>
                  </div>
                </div>

                <!-- 薪资待遇 -->
                <div class="profile-block">
                  <div class="block-header">
                    <span class="block-title">薪资待遇</span>
                  </div>
                  <div class="salary-info">
                    <div class="salary-range">
                      <span class="salary-num">{{ selectedDemand.salaryMin || '-' }}K</span>
                      <span class="salary-separator">-</span>
                      <span class="salary-num">{{ selectedDemand.salaryMax || '-' }}K</span>
                    </div>
                    <span class="salary-unit">月薪</span>
                  </div>
                </div>

                <!-- 加分项 -->
                <div class="profile-block">
                  <div class="block-header">
                    <span class="block-title">加分项</span>
                  </div>
                  <div class="bonus-list">
                    <div class="bonus-item">
                      <span class="bonus-icon">🌟</span>
                      <span>知名企业工作经历</span>
                    </div>
                    <div class="bonus-item">
                      <span class="bonus-icon">🌟</span>
                      <span>海外留学背景</span>
                    </div>
                    <div class="bonus-item">
                      <span class="bonus-icon">🌟</span>
                      <span>相关行业经验</span>
                    </div>
                  </div>
                </div>

                <!-- 工作地点 -->
                <div class="profile-block">
                  <div class="block-header">
                    <span class="block-title">工作地点</span>
                  </div>
                  <div class="location-info">
                    <span class="location-icon">📍</span>
                    <span class="location-text">总部 / 远程可选</span>
                  </div>
                </div>
              </div>
            </div>
          </a-tab-pane>

          <a-tab-pane key="records" tab="流程记录">
            <a-empty description="暂无流程记录" />
          </a-tab-pane>
        </a-tabs>

        <div class="drawer-footer">
          <a-space>
            <a-button
              v-if="selectedDemand.demandStatus === 'DRAFT'"
              type="primary"
              @click="handleSubmitApproval"
            >
              提交审批
            </a-button>
            <a-button @click="handleEdit(selectedDemand)">编辑</a-button>
          </a-space>
        </div>
      </template>
    </a-drawer>

    <!-- 创建/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="formData.id ? '编辑需求' : '创建需求'"
      @ok="handleSave"
      @cancel="modalVisible = false"
      :width="600"
      :confirmLoading="submitting"
    >
      <a-form :model="formData" :label-col="{ span: 6 }">
        <a-form-item label="需求名称" required>
          <a-input v-model:value="formData.name" placeholder="请输入需求名称" />
        </a-form-item>
        <a-form-item label="所属部门" required>
          <a-select v-model:value="formData.departmentId" placeholder="请选择部门">
            <a-select-option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="需求类型" required>
          <a-select v-model:value="formData.demandType" placeholder="请选择">
            <a-select-option value="SOCIAL">社会招聘</a-select-option>
            <a-select-option value="CAMPUS">校园招聘</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="需求人数">
          <a-input-number v-model:value="formData.positionCount" :min="1" :max="100" style="width: 100%" />
        </a-form-item>
        <a-form-item label="职位系列">
          <a-input v-model:value="formData.positionSeries" placeholder="如：技术、产品、运营" />
        </a-form-item>
        <a-form-item label="职级">
          <a-input v-model:value="formData.jobLevel" placeholder="如：P6、M1" />
        </a-form-item>
        <a-form-item label="薪资范围">
          <a-row :gutter="8">
            <a-col :span="12">
              <a-input-number v-model:value="formData.salaryMin" placeholder="最低薪资(K)" style="width: 100%" />
            </a-col>
            <a-col :span="12">
              <a-input-number v-model:value="formData.salaryMax" placeholder="最高薪资(K)" style="width: 100%" />
            </a-col>
          </a-row>
        </a-form-item>
        <a-form-item label="开始日期">
          <a-date-picker v-model:value="formData.startDate" style="width: 100%" />
        </a-form-item>
        <a-form-item label="结束日期">
          <a-date-picker v-model:value="formData.endDate" style="width: 100%" />
        </a-form-item>
        <a-form-item label="需求描述">
          <a-textarea v-model:value="formData.description" :rows="3" placeholder="请输入需求描述" />
        </a-form-item>
        <a-form-item label="候选人要求">
          <a-textarea v-model:value="formData.requirements" :rows="3" placeholder="请输入候选人要求" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { get, post, put } from '../../api/auth'
import dayjs from 'dayjs'

const loading = ref(false)
const demands = ref<any[]>([])
const departments = ref<any[]>([])
const selectedDemand = ref<any>(null)
const detailVisible = ref(false)
const modalVisible = ref(false)
const submitting = ref(false)
const keyword = ref('')
const filterStatus = ref('')
const activeTab = ref('detail')

const formData = ref<any>({
  id: '',
  name: '',
  departmentId: '',
  demandType: 'SOCIAL',
  positionCount: 1,
  positionSeries: '',
  jobLevel: '',
  salaryMin: null,
  salaryMax: null,
  startDate: null,
  endDate: null,
  description: '',
  requirements: ''
})

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    'DRAFT': 'default',
    'NOT_STARTED': 'default',
    'IN_PROGRESS': 'processing',
    'COMPLETED': 'success',
    'PAUSED': 'warning',
    'STOPPED': 'error'
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'DRAFT': '草稿',
    'NOT_STARTED': '未开始',
    'IN_PROGRESS': '进行中',
    'COMPLETED': '已完成',
    'PAUSED': '已暂停',
    'STOPPED': '已停招'
  }
  return texts[status] || status
}

const getApprovalColor = (status: string) => {
  const colors: Record<string, string> = {
    'NOT_STARTED': 'default',
    'PENDING': 'processing',
    'APPROVED': 'success',
    'REJECTED': 'error'
  }
  return colors[status] || 'default'
}

const getApprovalText = (status: string) => {
  const texts: Record<string, string> = {
    'NOT_STARTED': '未发起',
    'PENDING': '审批中',
    'APPROVED': '已通过',
    'REJECTED': '已拒绝'
  }
  return texts[status] || status
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD')
}

const getEducationText = (demand: any) => {
  if (!demand) return '-'
  if (demand.demandType === 'CAMPUS') return '本科及以上'
  return '大专及以上'
}

const getExperienceText = (demand: any) => {
  if (!demand) return '-'
  if (demand.jobLevel) {
    if (demand.jobLevel.includes('P4') || demand.jobLevel.includes('P5')) return '1-3年'
    if (demand.jobLevel.includes('P6')) return '3-5年'
    if (demand.jobLevel.includes('P7') || demand.jobLevel.includes('P8')) return '5年以上'
  }
  return '不限'
}

const getSkillsList = (demand: any) => {
  if (!demand) return []
  const skills: string[] = []
  if (demand.positionSeries) {
    if (demand.positionSeries.includes('技术') || demand.positionSeries.includes('研发')) {
      skills.push('JavaScript/TypeScript', 'Vue/React', 'Node.js', '数据库', 'API设计')
    }
    if (demand.positionSeries.includes('产品')) {
      skills.push('需求分析', '产品设计', '原型工具', '数据分析', '项目管理')
    }
    if (demand.positionSeries.includes('运营')) {
      skills.push('内容运营', '用户运营', '活动策划', '数据分析', '文案撰写')
    }
  }
  return skills.length > 0 ? skills : []
}

const fetchDemands = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value) params.status = filterStatus.value

    const res = await get('/demands', params)
    if (res.data.success) {
      demands.value = res.data.data.list
    }
  } catch (error) {
    message.error('获取需求列表失败')
  } finally {
    loading.value = false
  }
}

const fetchDepartments = async () => {
  try {
    const res = await get('/users/departments')
    if (res.data.success) {
      departments.value = res.data.data
    }
  } catch (error) {
    console.error('获取部门失败', error)
  }
}

const handleCardClick = (item: any) => {
  selectedDemand.value = item
  detailVisible.value = true
}

const handleCreate = () => {
  formData.value = {
    id: '',
    name: '',
    departmentId: '',
    demandType: 'SOCIAL',
    positionCount: 1,
    positionSeries: '',
    jobLevel: '',
    salaryMin: null,
    salaryMax: null,
    startDate: null,
    endDate: null,
    description: '',
    requirements: ''
  }
  modalVisible.value = true
}

const handleEdit = (item: any) => {
  formData.value = { ...item }
  modalVisible.value = true
}

const handleSave = async () => {
  if (!formData.value.name || !formData.value.departmentId) {
    message.warning('请填写必填项')
    return
  }

  submitting.value = true
  try {
    const data = {
      ...formData.value,
      startDate: formData.value.startDate ? dayjs(formData.value.startDate).format('YYYY-MM-DD') : null,
      endDate: formData.value.endDate ? dayjs(formData.value.endDate).format('YYYY-MM-DD') : null
    }

    if (formData.value.id) {
      await put(`/demands/${formData.value.id}`, data)
      message.success('更新成功')
    } else {
      await post('/demands', data)
      message.success('创建成功')
    }
    modalVisible.value = false
    fetchDemands()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleSubmitApproval = async () => {
  if (!selectedDemand.value) return
  try {
    await post(`/demands/${selectedDemand.value.id}/submit`)
    message.success('提交审批成功')
    detailVisible.value = false
    fetchDemands()
  } catch (error: any) {
    message.error(error?.response?.data?.message || '提交失败')
  }
}

const handleSearch = () => fetchDemands()
const handleFilter = () => fetchDemands()

onMounted(() => {
  fetchDemands()
  fetchDepartments()
})
</script>

<style scoped>
.demand-container {
  padding: 24px;
  min-height: 100%;
  background: #f0f2f5;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.demand-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.demand-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: white;
  border-radius: 8px;
  padding: 16px 20px;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.demand-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.demand-card.selected {
  border-color: #1890ff;
}

.card-left {
  display: flex;
  align-items: center;
  flex: 1;
  cursor: pointer;
}

.card-main {
  flex: 1;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.demand-code {
  color: #1890ff;
  font-weight: 600;
  font-size: 14px;
}

.status-tag {
  margin-right: 0;
}

.demand-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
}

.demand-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.meta-item .label {
  color: #999;
}

.meta-item .value {
  color: #666;
}

.card-stats {
  display: flex;
  align-items: center;
  margin-left: 40px;
  padding-left: 40px;
  border-left: 1px solid #f0f0f0;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 48px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #999;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: #f0f0f0;
  margin: 0 16px;
}

.card-right {
  display: flex;
  gap: 8px;
  margin-left: 24px;
}

.loading-spinner {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.empty-wrapper {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.drawer-code {
  color: #1890ff;
  font-weight: 600;
}

.detail-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 16px;
}

.detail-section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #999;
}

.info-value {
  font-size: 14px;
  color: #333;
}

.info-value.code {
  color: #1890ff;
  font-weight: 500;
}

.desc-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.desc-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.desc-label {
  font-size: 12px;
  color: #999;
}

.desc-value {
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  background: #fafafa;
  padding: 12px;
  border-radius: 4px;
}

.progress-stats {
  display: flex;
  gap: 16px;
}

.progress-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.stat-num {
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.stat-label {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.drawer-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-start;
}

/* 职位画像样式 */
.profile-section {
  padding-bottom: 24px;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.profile-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.profile-subtitle {
  font-size: 12px;
  color: #999;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-block {
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.block-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.block-items {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.profile-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-icon {
  font-size: 14px;
}

.item-label {
  font-size: 13px;
  color: #999;
  min-width: 70px;
}

.item-value {
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.no-data {
  font-size: 13px;
  color: #999;
}

.salary-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.salary-range {
  display: flex;
  align-items: center;
}

.salary-num {
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.salary-separator {
  font-size: 16px;
  color: #999;
  margin: 0 4px;
}

.salary-unit {
  font-size: 13px;
  color: #999;
}

.bonus-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bonus-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
}

.bonus-icon {
  font-size: 12px;
}

.location-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.location-icon {
  font-size: 14px;
}

.location-text {
  font-size: 13px;
  color: #333;
}
</style>
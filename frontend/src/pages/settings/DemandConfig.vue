<template>
  <div class="config-container">
    <div class="page-header">
      <h1 class="page-title">招聘需求设置</h1>
      <a-space>
        <a-button @click="handleReset">重置</a-button>
        <a-button type="primary" @click="handleSave" :loading="saving">保存配置</a-button>
      </a-space>
    </div>

    <div class="config-content">
      <a-form :model="formData" :label-col="{ span: 6 }" :wrapper-col="{ span: 18 }">
        <!-- 招聘类型配置 -->
        <a-card title="招聘类型配置" class="config-card">
          <a-form-item label="启用社会招聘">
            <a-switch v-model:checked="formData.enableSocial" />
          </a-form-item>
          <a-form-item label="启用校园招聘">
            <a-switch v-model:checked="formData.enableCampus" />
          </a-form-item>
          <a-form-item label="启用实习生招聘">
            <a-switch v-model:checked="formData.enableIntern" />
          </a-form-item>
          <a-form-item label="启用内推">
            <a-switch v-model:checked="formData.enableReferral" />
          </a-form-item>
        </a-card>

        <!-- 部门配置 -->
        <a-card title="部门配置" class="config-card">
          <a-form-item label="允许跨部门招聘">
            <a-switch v-model:checked="formData.allowCrossDepartment" />
          </a-form-item>
          <a-form-item label="默认需求部门">
            <a-select v-model:value="formData.defaultDepartmentId" placeholder="请选择默认部门" style="width: 200px">
              <a-select-option v-for="dept in departments" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="部门层级限制">
            <a-input-number v-model:value="formData.departmentLevelLimit" :min="1" :max="5" />
            <span class="input-tip">级</span>
          </a-form-item>
        </a-card>

        <!-- 薪资配置 -->
        <a-card title="薪资配置" class="config-card">
          <a-form-item label="薪资单位">
            <a-select v-model:value="formData.salaryUnit" style="width: 120px">
              <a-select-option value="K">K (千元)</a-select-option>
              <a-select-option value="W">W (万元)</a-select-option>
              <a-select-option value="Y">元</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="最低薪资">
            <a-input-number v-model:value="formData.minSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </a-form-item>
          <a-form-item label="最高薪资">
            <a-input-number v-model:value="formData.maxSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </a-form-item>
          <a-form-item label="薪资保密">
            <a-switch v-model:checked="formData.salaryConfidential" />
            <span class="switch-tip">开启后候选人无法查看具体薪资</span>
          </a-form-item>
        </a-card>

        <!-- 职位配置 -->
        <a-card title="职位配置" class="config-card">
          <a-form-item label="默认招聘人数">
            <a-input-number v-model:value="formData.defaultPositionCount" :min="1" :max="100" />
            <span class="input-tip">人</span>
          </a-form-item>
          <a-form-item label="最大招聘人数">
            <a-input-number v-model:value="formData.maxPositionCount" :min="1" :max="500" />
            <span class="input-tip">人</span>
          </a-form-item>
          <a-form-item label="启用职位系列">
            <a-switch v-model:checked="formData.enablePositionSeries" />
          </a-form-item>
          <a-form-item label="启用职级">
            <a-switch v-model:checked="formData.enableJobLevel" />
          </a-form-item>
          <a-form-item label="职级体系">
            <a-checkbox-group v-model:value="formData.jobLevelSystem">
              <a-checkbox value="P">P系列（专业）</a-checkbox>
              <a-checkbox value="M">M系列（管理）</a-checkbox>
              <a-checkbox value="T">T系列（技术）</a-checkbox>
            </a-checkbox-group>
          </a-form-item>
        </a-card>

        <!-- 需求流程配置 -->
        <a-card title="需求流程配置" class="config-card">
          <a-form-item label="需要审批">
            <a-switch v-model:checked="formData.requireApproval" />
          </a-form-item>
          <a-form-item label="审批流程" v-if="formData.requireApproval">
            <a-select v-model:value="formData.approvalProcessId" placeholder="请选择审批流程" style="width: 200px">
              <a-select-option v-for="process in processes" :key="process.id" :value="process.id">
                {{ process.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="自动分配HRBP">
            <a-switch v-model:checked="formData.autoAssignHRBP" />
          </a-form-item>
          <a-form-item label="自动分配用人经理">
            <a-switch v-model:checked="formData.autoAssignManager" />
          </a-form-item>
          <a-form-item label="需求有效期">
            <a-input-number v-model:value="formData.demandValidDays" :min="1" :max="365" />
            <span class="input-tip">天</span>
            <span class="input-tip-tip">超过天数自动关闭需求</span>
          </a-form-item>
        </a-card>

        <!-- 候选人配置 -->
        <a-card title="候选人配置" class="config-card">
          <a-form-item label="自动查重">
            <a-switch v-model:checked="formData.autoDuplicateCheck" />
          </a-form-item>
          <a-form-item label="简历保护期">
            <a-input-number v-model:value="formData.resumeProtectionDays" :min="0" :max="365" />
            <span class="input-tip">天</span>
          </a-form-item>
          <a-form-item label="保护期候选人可见">
            <a-switch v-model:checked="formData.protectedCandidateVisible" />
          </a-form-item>
          <a-form-item label="候选人来源必填">
            <a-switch v-model:checked="formData.requireCandidateSource" />
          </a-form-item>
        </a-card>

        <!-- 消息通知配置 -->
        <a-card title="消息通知配置" class="config-card">
          <a-form-item label="需求创建通知">
            <a-switch v-model:checked="formData.notifyOnCreate" />
          </a-form-item>
          <a-form-item label="需求审批通知">
            <a-switch v-model:checked="formData.notifyOnApproval" />
          </a-form-item>
          <a-form-item label="需求变更通知">
            <a-switch v-model:checked="formData.notifyOnChange" />
          </a-form-item>
          <a-form-item label="需求关闭通知">
            <a-switch v-model:checked="formData.notifyOnClose" />
          </a-form-item>
          <a-form-item label="通知方式">
            <a-checkbox-group v-model:value="formData.notifyMethods">
              <a-checkbox value="wechat">企业微信</a-checkbox>
              <a-checkbox value="email">邮件</a-checkbox>
              <a-checkbox value="sms">短信</a-checkbox>
            </a-checkbox-group>
          </a-form-item>
        </a-card>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { get, post } from '../../api/auth'

const saving = ref(false)
const departments = ref<any[]>([])
const processes = ref<any[]>([])

const formData = ref<any>({
  // 招聘类型
  enableSocial: true,
  enableCampus: true,
  enableIntern: true,
  enableReferral: true,

  // 部门配置
  allowCrossDepartment: false,
  defaultDepartmentId: '',
  departmentLevelLimit: 3,

  // 薪资配置
  salaryUnit: 'K',
  minSalary: 5,
  maxSalary: 100,
  salaryConfidential: true,

  // 职位配置
  defaultPositionCount: 1,
  maxPositionCount: 50,
  enablePositionSeries: true,
  enableJobLevel: true,
  jobLevelSystem: ['P', 'M'],

  // 需求流程配置
  requireApproval: true,
  approvalProcessId: '',
  autoAssignHRBP: false,
  autoAssignManager: false,
  demandValidDays: 90,

  // 候选人配置
  autoDuplicateCheck: true,
  resumeProtectionDays: 30,
  protectedCandidateVisible: true,
  requireCandidateSource: true,

  // 消息通知配置
  notifyOnCreate: true,
  notifyOnApproval: true,
  notifyOnChange: true,
  notifyOnClose: true,
  notifyMethods: ['wechat', 'email']
})

const defaultFormData = { ...formData.value }

const fetchConfig = async () => {
  try {
    const res = await get('/system/config/demand')
    if (res.data.success && res.data.data) {
      formData.value = { ...formData.value, ...res.data.data }
    }
  } catch (error) {
    console.error('获取配置失败', error)
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

const fetchProcesses = async () => {
  try {
    const res = await get('/processes')
    if (res.data.success) {
      processes.value = res.data.data
    }
  } catch (error) {
    console.error('获取流程失败', error)
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await post('/system/config/demand', formData.value)
    message.success('配置保存成功')
  } catch (error: any) {
    message.error(error?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  formData.value = { ...defaultFormData }
  message.info('已重置为默认配置')
}

onMounted(() => {
  fetchConfig()
  fetchDepartments()
  fetchProcesses()
})
</script>

<style scoped>
.config-container {
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

.config-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-card {
  border-radius: 8px;
}

.config-card :deep(.ant-card-head) {
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.config-card :deep(.ant-card-head-title) {
  font-weight: 600;
}

.config-card :deep(.ant-form-item) {
  margin-bottom: 16px;
}

.config-card :deep(.ant-form-item:last-child) {
  margin-bottom: 0;
}

.input-tip {
  margin-left: 8px;
  color: #999;
}

.input-tip-tip {
  margin-left: 8px;
  color: #999;
  font-size: 12px;
}

.switch-tip {
  margin-left: 12px;
  color: #999;
  font-size: 12px;
}
</style>
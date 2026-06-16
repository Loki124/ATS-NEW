<template>
  <div class="config-container">
    <div class="page-header">
      <h1 class="page-title">招聘需求设置</h1>
      <n-space>
        <n-button @click="handleReset">重置</n-button>
        <n-button type="primary" :loading="saving" @click="handleSave">保存配置</n-button>
      </n-space>
    </div>

    <div class="config-content">
      <n-form :model="formData" label-placement="left" :label-width="180">
        <!-- 功能设置 -->
        <n-card title="功能设置" class="config-card">
          <n-form-item label="需求使用模式">
            <div class="form-field-wrap">
              <n-radio-group v-model:value="formData.demandMode">
                <n-radio value="task">任务模式</n-radio>
                <n-radio value="quick_leave">闪离模式</n-radio>
                <n-radio value="non_task">非任务模式</n-radio>
              </n-radio-group>
              <div class="field-note">
                <span>任务模式：按招聘流程任务推进</span>
                <span>闪离模式：快速入职流程</span>
                <span>非任务模式：自由招聘流程</span>
              </div>
            </div>
          </n-form-item>
          <n-form-item label="需求终止态">
            <n-checkbox-group v-model:value="formData.terminationStatus">
              <n-space>
                <n-checkbox value="completed">已完成</n-checkbox>
                <n-checkbox value="stopped">已停招</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">选择可用作需求终止的状态</span>
          </n-form-item>
          <n-form-item label="Offer人数管控">
            <n-switch v-model:value="formData.offerHeadcountControl" />
            <span class="switch-tip">开启后Offer创建数量受需求人数限制</span>
          </n-form-item>
        </n-card>

        <!-- 抢单设置 -->
        <n-card title="抢单设置" class="config-card">
          <n-form-item label="全局开启抢单模式">
            <n-switch v-model:value="formData.grabModeEnabled" />
            <span class="switch-tip">开启后抢单功能生效，需求中的交易信息模块内容可配置</span>
          </n-form-item>
          <n-form-item label="抢单模式开关权限">
            <n-checkbox-group v-model:value="formData.grabModeSwitchRoles">
              <n-space>
                <n-checkbox value="super_admin_product">超管-产线</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">仅选中的角色可以操作抢单模式开关</span>
          </n-form-item>
          <n-form-item label="抢单人配置权限">
            <n-checkbox-group v-model:value="formData.grabModeOperatorRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">可添加/删除抢单人（系统自动填充的抢单人不可删除）</span>
          </n-form-item>
          <n-form-item label="抢单金额配置权限">
            <n-checkbox-group v-model:value="formData.grabModeAmountRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">可配置抢单相关金额</span>
          </n-form-item>
          <n-form-item label="交易信息管理权限">
            <n-checkbox-group v-model:value="formData.transactionManageRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
                <n-checkbox value="demand_manager">需求负责人</n-checkbox>
                <n-checkbox value="super_admin_business">超管-业务</n-checkbox>
                <n-checkbox value="super_admin_product">超管-产线</n-checkbox>
                <n-checkbox value="personal">个人</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">可查看和操作需求中的交易信息</span>
          </n-form-item>
          <n-form-item label="超时自动入池">
            <n-input-number v-model:value="formData.grabPoolTimeoutHours" :min="0" :max="168" />
            <span class="input-tip">小时</span>
            <span class="switch-tip">超过指定时间未邀约成功自动进入抢单池（0表示关闭）</span>
          </n-form-item>
          <n-form-item label="职位创建权限">
            <n-radio-group v-model:value="formData.positionCreateRole">
              <n-radio value="hrbp">HRBP</n-radio>
              <n-radio value="demand_assistant">需求协助人</n-radio>
            </n-radio-group>
            <span class="switch-tip">控制谁可以创建职位</span>
          </n-form-item>
        </n-card>

        <!-- 画像设置 -->
        <n-card title="画像设置" class="config-card">
          <n-form-item label="画像字段约束规则">
            <div class="profile-rules-editor">
              <n-input
                v-model:value="formData.profileFieldRules"
                type="textarea"
                placeholder="请输入画像字段约束规则，每行一条规则，格式：字段名:规则描述"
                :rows="6"
                class="rules-textarea"
              />
              <div class="rules-tip">
                <p>规则格式示例：</p>
                <p>experience: 工作年限需在1-10年之间</p>
                <p>education: 学历需为本科及以上</p>
                <p>skills: 技能标签至少选择2个</p>
              </div>
            </div>
          </n-form-item>
        </n-card>

        <!-- 招聘类型配置 -->
        <n-card title="招聘类型配置" class="config-card">
          <n-form-item label="启用社会招聘">
            <n-switch v-model:value="formData.enableSocial" />
          </n-form-item>
          <n-form-item label="启用校园招聘">
            <n-switch v-model:value="formData.enableCampus" />
          </n-form-item>
          <n-form-item label="启用实习生招聘">
            <n-switch v-model:value="formData.enableIntern" />
          </n-form-item>
          <n-form-item label="启用内推">
            <n-switch v-model:value="formData.enableReferral" />
          </n-form-item>
        </n-card>

        <!-- 部门配置 -->
        <n-card title="部门配置" class="config-card">
          <n-form-item label="允许跨部门招聘">
            <n-switch v-model:value="formData.allowCrossDepartment" />
          </n-form-item>
          <n-form-item label="默认需求部门">
            <n-select
              v-model:value="formData.defaultDepartmentId"
              placeholder="请选择默认部门"
              style="width: 200px"
              :options="departmentOptions"
            />
          </n-form-item>
          <n-form-item label="部门层级限制">
            <n-input-number v-model:value="formData.departmentLevelLimit" :min="1" :max="5" />
            <span class="input-tip">级</span>
          </n-form-item>
        </n-card>

        <!-- 薪资配置 -->
        <n-card title="薪资配置" class="config-card">
          <n-form-item label="薪资单位">
            <n-select
              v-model:value="formData.salaryUnit"
              style="width: 120px"
              :options="salaryUnitOptions"
            />
          </n-form-item>
          <n-form-item label="最低薪资">
            <n-input-number v-model:value="formData.minSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </n-form-item>
          <n-form-item label="最高薪资">
            <n-input-number v-model:value="formData.maxSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </n-form-item>
          <n-form-item label="薪资保密">
            <n-switch v-model:value="formData.salaryConfidential" />
            <span class="switch-tip">开启后候选人无法查看具体薪资</span>
          </n-form-item>
        </n-card>

        <!-- 职位配置 -->
        <n-card title="职位配置" class="config-card">
          <n-form-item label="默认招聘人数">
            <n-input-number v-model:value="formData.defaultPositionCount" :min="1" :max="100" />
            <span class="input-tip">人</span>
          </n-form-item>
          <n-form-item label="最大招聘人数">
            <n-input-number v-model:value="formData.maxPositionCount" :min="1" :max="500" />
            <span class="input-tip">人</span>
          </n-form-item>
          <n-form-item label="启用职位系列">
            <n-switch v-model:value="formData.enablePositionSeries" />
          </n-form-item>
          <n-form-item label="启用职级">
            <n-switch v-model:value="formData.enableJobLevel" />
          </n-form-item>
          <n-form-item label="职级体系">
            <n-checkbox-group v-model:value="formData.jobLevelSystem">
              <n-space>
                <n-checkbox value="P">P系列（专业）</n-checkbox>
                <n-checkbox value="M">M系列（管理）</n-checkbox>
                <n-checkbox value="T">T系列（技术）</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
        </n-card>

        <!-- 需求流程配置 -->
        <n-card title="需求流程配置" class="config-card">
          <n-form-item label="需要审批">
            <n-switch v-model:value="formData.requireApproval" />
          </n-form-item>
          <n-form-item v-if="formData.requireApproval" label="审批流程">
            <n-select
              v-model:value="formData.approvalProcessId"
              placeholder="请选择审批流程"
              style="width: 200px"
              :options="processOptions"
            />
          </n-form-item>
          <n-form-item label="自动分配HRBP">
            <n-switch v-model:value="formData.autoAssignHRBP" />
          </n-form-item>
          <n-form-item label="自动分配用人经理">
            <n-switch v-model:value="formData.autoAssignManager" />
          </n-form-item>
          <n-form-item label="需求有效期">
            <n-input-number v-model:value="formData.demandValidDays" :min="1" :max="365" />
            <span class="input-tip">天</span>
            <span class="input-tip-tip">超过天数自动关闭需求</span>
          </n-form-item>
        </n-card>

        <!-- 候选人配置 -->
        <n-card title="候选人配置" class="config-card">
          <n-form-item label="自动查重">
            <n-switch v-model:value="formData.autoDuplicateCheck" />
          </n-form-item>
          <n-form-item label="简历保护期">
            <n-input-number v-model:value="formData.resumeProtectionDays" :min="0" :max="365" />
            <span class="input-tip">天</span>
          </n-form-item>
          <n-form-item label="保护期候选人可见">
            <n-switch v-model:value="formData.protectedCandidateVisible" />
          </n-form-item>
          <n-form-item label="候选人来源必填">
            <n-switch v-model:value="formData.requireCandidateSource" />
          </n-form-item>
        </n-card>

        <!-- 消息通知配置 -->
        <n-card title="消息通知配置" class="config-card">
          <n-form-item label="需求创建通知">
            <n-switch v-model:value="formData.notifyOnCreate" />
          </n-form-item>
          <n-form-item label="需求审批通知">
            <n-switch v-model:value="formData.notifyOnApproval" />
          </n-form-item>
          <n-form-item label="需求变更通知">
            <n-switch v-model:value="formData.notifyOnChange" />
          </n-form-item>
          <n-form-item label="需求关闭通知">
            <n-switch v-model:value="formData.notifyOnClose" />
          </n-form-item>
          <n-form-item label="通知方式">
            <n-checkbox-group v-model:value="formData.notifyMethods">
              <n-space>
                <n-checkbox value="wechat">企业微信</n-checkbox>
                <n-checkbox value="email">邮件</n-checkbox>
                <n-checkbox value="sms">短信</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
        </n-card>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { get, post } from '../../api/auth'

const message = useMessage()

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

  // 功能设置
  demandMode: 'task',
  terminationStatus: ['completed', 'stopped'],
  offerHeadcountControl: true,

  // 抢单设置
  grabModeEnabled: false,
  grabModeSwitchRoles: ['super_admin_product'],
  grabModeOperatorRoles: ['hrbp'],
  grabModeAmountRoles: ['hrbp'],
  transactionManageRoles: ['hrbp', 'demand_manager', 'super_admin_business', 'super_admin_product', 'personal'],
  grabPoolTimeoutHours: 48,
  positionCreateRole: 'hrbp',

  // 画像设置
  profileFieldRules: '',

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

const departmentOptions = computed(() =>
  departments.value.map(d => ({ label: d.name, value: d.id }))
)

const processOptions = computed(() =>
  processes.value.map(p => ({ label: p.name, value: p.id }))
)

const salaryUnitOptions = [
  { label: 'K (千元)', value: 'K' },
  { label: 'W (万元)', value: 'W' },
  { label: '元', value: 'Y' },
]

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

.config-card :deep(.n-card-header) {
  background: #fafafa;
  border-radius: 8px 8px 0 0;
}

.config-card :deep(.n-card-header__main) {
  font-weight: 600;
}

.config-card :deep(.n-form-item) {
  margin-bottom: 16px;
}

.config-card :deep(.n-form-item:last-child) {
  margin-bottom: 0;
}

.form-field-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
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

.field-note {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.profile-rules-editor {
  width: 100%;
}

.rules-textarea {
  border-radius: 6px;
}

.rules-tip {
  margin-top: 8px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
}

.rules-tip p {
  margin: 0 0 4px 0;
  line-height: 1.6;
}
</style>

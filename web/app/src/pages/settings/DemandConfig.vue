<template>
  <div class="page-container config-container">
    <div class="page-header">
<div>
        <h1 class="dc-title gradient-title">{ t('pages.settings.DemandConfig.s1') }</h1>
        <p class="dc-subtitle">{ t('pages.settings.DemandConfig.s2') }</p>
      </div>
      <n-space>
        <n-button @click="handleReset">{ t('pages.settings.DemandConfig.s3') }</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">{ t('pages.settings.DemandConfig.s4') }</n-button>
      </n-space>
    </div>

    <div class="config-content page-body">
<n-form :model="formData" label-placement="left" :label-width="180">
        <!-- 功能设置 -->
        <n-card :title="t('pages.settings.DemandConfig.s49')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s59')">
            <div class="form-field-wrap">
              <n-radio-group v-model:value="formData.demandMode">
                <n-radio value="task">{ t('pages.settings.DemandConfig.s5') }</n-radio>
                <n-radio value="quick_leave">{ t('pages.settings.DemandConfig.s6') }</n-radio>
                <n-radio value="non_task">{ t('pages.settings.DemandConfig.s7') }</n-radio>
              </n-radio-group>
              <div class="field-note">
                <span>{ t('pages.settings.DemandConfig.s8') }</span>
                <span>{ t('pages.settings.DemandConfig.s9') }</span>
                <span>{ t('pages.settings.DemandConfig.s10') }</span>
              </div>
            </div>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s60')">
            <n-checkbox-group v-model:value="formData.terminationStatus">
              <n-space>
                <n-checkbox value="completed">{ t('pages.settings.DemandConfig.s11') }</n-checkbox>
                <n-checkbox value="stopped">{ t('pages.settings.DemandConfig.s12') }</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s13') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s61')">
            <n-switch v-model:value="formData.offerHeadcountControl" />
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s14') }</span>
          </n-form-item>
        </n-card>

        <!-- 抢单设置 -->
        <n-card :title="t('pages.settings.DemandConfig.s50')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s62')">
            <n-switch v-model:value="formData.grabModeEnabled" />
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s15') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s63')">
            <n-checkbox-group v-model:value="formData.grabModeSwitchRoles">
              <n-space>
                <n-checkbox value="super_admin_product">{ t('pages.settings.DemandConfig.s16') }</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s17') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s64')">
            <n-checkbox-group v-model:value="formData.grabModeOperatorRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s18') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s65')">
            <n-checkbox-group v-model:value="formData.grabModeAmountRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s19') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s66')">
            <n-checkbox-group v-model:value="formData.transactionManageRoles">
              <n-space>
                <n-checkbox value="hrbp">HRBP</n-checkbox>
                <n-checkbox value="demand_manager">{ t('pages.settings.DemandConfig.s20') }</n-checkbox>
                <n-checkbox value="super_admin_business">{ t('pages.settings.DemandConfig.s21') }</n-checkbox>
                <n-checkbox value="super_admin_product">{ t('pages.settings.DemandConfig.s22') }</n-checkbox>
                <n-checkbox value="personal">{ t('pages.settings.DemandConfig.s23') }</n-checkbox>
              </n-space>
            </n-checkbox-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s24') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s67')">
            <n-input-number v-model:value="formData.grabPoolTimeoutHours" :min="0" :max="168" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s25') }</span>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s26') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s68')">
            <n-radio-group v-model:value="formData.positionCreateRole">
              <n-radio value="hrbp">HRBP</n-radio>
              <n-radio value="demand_assistant">{ t('pages.settings.DemandConfig.s27') }</n-radio>
            </n-radio-group>
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s28') }</span>
          </n-form-item>
        </n-card>

        <!-- 画像设置 -->
        <n-card :title="t('pages.settings.DemandConfig.s51')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s69')">
            <div class="profile-rules-editor">
              <n-input
                v-model:value="formData.profileFieldRules"
                type="textarea"
                :placeholder="t('pages.settings.DemandConfig.s46')"
                :rows="6"
                class="rules-textarea"
              />
              <div class="rules-tip">
                <p>{ t('pages.settings.DemandConfig.s29') }</p>
                <p>{ t('pages.settings.DemandConfig.s30') }</p>
                <p>{ t('pages.settings.DemandConfig.s31') }</p>
                <p>{ t('pages.settings.DemandConfig.s32') }</p>
              </div>
            </div>
          </n-form-item>
        </n-card>

        <!-- 招聘类型配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s52')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s70')">
            <n-switch v-model:value="formData.enableSocial" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s71')">
            <n-switch v-model:value="formData.enableCampus" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s72')">
            <n-switch v-model:value="formData.enableIntern" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s73')">
            <n-switch v-model:value="formData.enableReferral" />
          </n-form-item>
        </n-card>

        <!-- 部门配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s53')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s74')">
            <n-switch v-model:value="formData.allowCrossDepartment" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s75')">
            <n-select
              v-model:value="formData.defaultDepartmentId"
              :placeholder="t('pages.settings.DemandConfig.s47')"
              style="width: 200px"
              :options="departmentOptions"
            />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s76')">
            <n-input-number v-model:value="formData.departmentLevelLimit" :min="1" :max="5" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s33') }</span>
          </n-form-item>
        </n-card>

        <!-- 薪资配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s54')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s77')">
            <n-select
              v-model:value="formData.salaryUnit"
              style="width: 120px"
              :options="salaryUnitOptions"
            />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s78')">
            <n-input-number v-model:value="formData.minSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s79')">
            <n-input-number v-model:value="formData.maxSalary" :min="0" style="width: 120px" />
            <span class="input-tip">{{ formData.salaryUnit }}</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s80')">
            <n-switch v-model:value="formData.salaryConfidential" />
            <span class="switch-tip">{ t('pages.settings.DemandConfig.s34') }</span>
          </n-form-item>
        </n-card>

        <!-- 职位配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s55')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s81')">
            <n-input-number v-model:value="formData.defaultPositionCount" :min="1" :max="100" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s35') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s82')">
            <n-input-number v-model:value="formData.maxPositionCount" :min="1" :max="500" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s36') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s83')">
            <n-switch v-model:value="formData.enablePositionSeries" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s84')">
            <n-switch v-model:value="formData.enableJobLevel" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s85')">
            <n-checkbox-group v-model:value="formData.jobLevelSystem">
              <n-space>
                <n-checkbox value="P">{ t('pages.settings.DemandConfig.s37') }</n-checkbox>
                <n-checkbox value="M">{ t('pages.settings.DemandConfig.s38') }</n-checkbox>
                <n-checkbox value="T">{ t('pages.settings.DemandConfig.s39') }</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
        </n-card>

        <!-- 需求流程配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s56')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s86')">
            <n-switch v-model:value="formData.requireApproval" />
          </n-form-item>
          <n-form-item v-if="formData.requireApproval" :label="t('pages.settings.DemandConfig.s87')">
            <n-select
              v-model:value="formData.approvalProcessId"
              :placeholder="t('pages.settings.DemandConfig.s48')"
              style="width: 200px"
              :options="processOptions"
            />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s88')">
            <n-switch v-model:value="formData.autoAssignHRBP" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s89')">
            <n-switch v-model:value="formData.autoAssignManager" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s90')">
            <n-input-number v-model:value="formData.demandValidDays" :min="1" :max="365" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s40') }</span>
            <span class="input-tip-tip">{ t('pages.settings.DemandConfig.s41') }</span>
          </n-form-item>
        </n-card>

        <!-- 候选人配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s57')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s91')">
            <n-switch v-model:value="formData.autoDuplicateCheck" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s92')">
            <n-input-number v-model:value="formData.resumeProtectionDays" :min="0" :max="365" />
            <span class="input-tip">{ t('pages.settings.DemandConfig.s42') }</span>
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s93')">
            <n-switch v-model:value="formData.protectedCandidateVisible" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s94')">
            <n-switch v-model:value="formData.requireCandidateSource" />
          </n-form-item>
        </n-card>

        <!-- 消息通知配置 -->
        <n-card :title="t('pages.settings.DemandConfig.s58')" class="config-card">
          <n-form-item :label="t('pages.settings.DemandConfig.s95')">
            <n-switch v-model:value="formData.notifyOnCreate" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s96')">
            <n-switch v-model:value="formData.notifyOnApproval" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s97')">
            <n-switch v-model:value="formData.notifyOnChange" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s98')">
            <n-switch v-model:value="formData.notifyOnClose" />
          </n-form-item>
          <n-form-item :label="t('pages.settings.DemandConfig.s99')">
            <n-checkbox-group v-model:value="formData.notifyMethods">
              <n-space>
                <n-checkbox value="wechat">{ t('pages.settings.DemandConfig.s43') }</n-checkbox>
                <n-checkbox value="email">{ t('pages.settings.DemandConfig.s44') }</n-checkbox>
                <n-checkbox value="sms">{ t('pages.settings.DemandConfig.s45') }</n-checkbox>
              </n-space>
            </n-checkbox-group>
          </n-form-item>
        </n-card>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, onMounted, computed } from 'vue'
import { useMessage } from 'naive-ui'
import { get, post } from '../../api/auth'

import { extractApiError } from '../../api/dynamic-field'
const { t } = useI18n()
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
    message.error(extractApiError(error, '获取配置失败'))
  }
}

const fetchDepartments = async () => {
  try {
    const res = await get('/users/departments')
    if (res.data.success) {
      departments.value = res.data.data
    }
  } catch (error) {
    message.error(extractApiError(error, '获取部门失败'))
  }
}

const fetchProcesses = async () => {
  try {
    const res = await get('/processes')
    if (res.data.success) {
      processes.value = res.data.data
    }
  } catch (error) {
    message.error(extractApiError(error, '获取流程失败'))
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
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}

/* 2026-08-24 兵哥反馈：拆成「标题区 + 内容区」，滚动职责下放到 .page-body
   - 标题区固定不动（flex-shrink: 0）→ 配置类页面保存/重置按钮始终可触达
   - 内容区自己滚（flex: 1, min-height: 0, overflow-y: auto）→ 与 AccountSettings/ThemeSettings 同范式
   - 避免原 .config-container min-height:100% 触发整页内嵌滚动条 + sticky header 被卡片内容穿透 */
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* [T11] 同步限制 X 方向: 子元素 n-checkbox/n-radio 白空间 nowrap 会撑宽父容器 */
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 兼容旧类名（如果模板残留 .config-content 不带 .page-body 时仍生效） */
.config-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
  overflow: auto;
  /* 玻璃化由全局 .glass-panel 提供（v2 阶段 3 收口） */
}

.config-card {
  border-radius: 8px;
}

.config-card :deep(.n-card-header) {
  background: var(--g1);
  border-radius: 8px 8px 0 0;}

.config-card :deep(.n-card-header__main) {
  font-weight: 600;
}

.config-card :deep(.n-form-item) {
  margin-bottom: var(--space-4);
}

.config-card :deep(.n-form-item:last-child) {
  margin-bottom: 0;
}

.form-field-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.input-tip {
  margin-left: var(--space-2);
  color: var(--n-400);
}

.input-tip-tip {
  margin-left: var(--space-2);
  color: var(--n-400);
  font-size: var(--fs-12);
}

.switch-tip {
  margin-left: var(--space-3);
  color: var(--n-400);
  font-size: var(--fs-12);
}

.field-note {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: var(--space-1);
  font-size: var(--fs-12);
  color: var(--n-400);
}

.profile-rules-editor {
  width: 100%;
}

.rules-textarea {
  border-radius: 6px;
}

.rules-tip {
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: var(--g1);
  border-radius: 6px;
  font-size: var(--fs-12);
  color: var(--n-500);
}

.rules-tip p {
  margin: 0 0 var(--space-1) 0;
  line-height: 1.6;
}
</style>

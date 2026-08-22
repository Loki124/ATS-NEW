<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">个人设置</h1>
    </div>

    <!-- 个人设置 -->
    <n-card class="settings-section" :bordered="false">
      <template #header>
        <div class="section-title">
          <span>个人设置</span>
          <n-tag type="info" size="small" class="section-tag">全局</n-tag>
        </div>
      </template>

      <n-alert type="info" :show-icon="true" class="section-alert">
        企业已购买 Moka People 系统，需从 People 花名册修改员工姓名、邮箱、手机号。
      </n-alert>

      <n-form label-placement="left" :label-width="96" :model="formState" class="profile-form">
        <n-grid :cols="1" :x-gap="24">
          <n-gi>
            <n-form-item label="姓名">
              <n-input v-model:value="formState.realName" placeholder="请输入姓名" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="电话">
              <n-input v-model:value="formState.phone" placeholder="请输入电话" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="邮箱" :feedback="emailFeedback" :validation-status="emailStatus">
              <n-input v-model:value="formState.email" placeholder="请输入邮箱" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="密码">
              <n-button type="primary" ghost size="small" @click="showPasswordModal = true">
                <template #icon>
                  <n-icon :component="LockClosedOutline" />
                </template>
                更改密码
              </n-button>
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="帮助与反馈">
              <n-button size="small" @click="handleUploadEnv">
                <template #icon>
                  <n-icon :component="CloudUploadOutline" />
                </template>
                上传当前浏览器环境
              </n-button>
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>

      <n-space justify="end" class="section-actions">
        <n-button type="primary" @click="handleSaveProfile">保存</n-button>
      </n-space>
    </n-card>

    <!-- 浏览器通知 -->
    <n-card class="settings-section" :bordered="false">
      <template #header>
        <div class="section-title">
          <span>浏览器通知</span>
          <n-tag type="info" size="small" class="section-tag">全局</n-tag>
        </div>
      </template>

      <p class="section-desc">此功能需要浏览器授权</p>

      <n-form label-placement="left" :label-width="96">
        <n-form-item label="使用通知">
          <n-switch v-model:value="useNotification" />
        </n-form-item>
      </n-form>

      <n-collapse-transition :show="useNotification">
        <n-checkbox-group v-model:value="notificationOptions" class="notification-grid">
          <n-grid :cols="4" :x-gap="16" :y-gap="12" responsive="screen">
            <n-gi v-for="opt in notificationList" :key="opt.value">
              <n-checkbox :value="opt.value" :label="opt.label" />
            </n-gi>
          </n-grid>
        </n-checkbox-group>
      </n-collapse-transition>

      <n-space justify="end" class="section-actions">
        <n-button type="primary" @click="handleSaveNotifications">保存</n-button>
      </n-space>
    </n-card>

    <!-- 自定义默认选项设置 -->
    <n-card class="settings-section" :bordered="false">
      <template #header>
        <div class="section-title">
          <span>自定义默认选项设置</span>
          <n-tag type="info" size="small" class="section-tag">全局</n-tag>
        </div>
      </template>

      <p class="section-desc">
        设置后，系统中相关选项默认使用您的设置项；若未设置，系统中默认使用系统默认选项。
      </p>

      <n-form label-placement="left" :label-width="120">
        <n-form-item label="默认简历接收邮箱">
          <n-select
            v-model:value="defaultResumeMailbox"
            placeholder="请选择简历接收邮箱"
            :options="resumeMailboxOptions"
            style="width: 320px"
          />
        </n-form-item>
      </n-form>

      <n-space justify="end" class="section-actions">
        <n-button type="primary" @click="handleSaveDefaults">保存</n-button>
      </n-space>
    </n-card>

    <!-- 更改密码弹窗 -->
    <n-modal
      v-model:show="showPasswordModal"
      preset="card"
      title="更改密码"
      style="width: 480px"
      :mask-closable="false"
    >
      <n-form label-placement="left" :label-width="100" :model="passwordForm">
        <n-form-item label="原密码">
          <n-input v-model:value="passwordForm.oldPassword" type="password" show-password-on="click" placeholder="请输入原密码" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="passwordForm.newPassword" type="password" show-password-on="click" placeholder="请输入新密码" />
        </n-form-item>
        <n-form-item label="确认密码" :validation-status="passwordConfirmStatus" :feedback="passwordConfirmFeedback">
          <n-input v-model:value="passwordForm.confirmPassword" type="password" show-password-on="click" placeholder="请再次输入新密码" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showPasswordModal = false">取消</n-button>
          <n-button type="primary" @click="handleChangePassword">确定</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  NCard,
  NForm,
  NFormItem,
  NInput,
  NButton,
  NSpace,
  NTag,
  NAlert,
  NSwitch,
  NCheckbox,
  NCheckboxGroup,
  NGrid,
  NGi,
  NSelect,
  NModal,
  NIcon,
  NCollapseTransition,
  useMessage,
} from 'naive-ui'
import {
  LockClosedOutline,
  CloudUploadOutline,
} from '@vicons/ionicons5'
import { useUserStore } from '../../stores/user'
import api from '../../api/auth'

const message = useMessage()
const userStore = useUserStore()
const user = computed(() => userStore.user)

// ===== 个人设置表单 =====
const formState = reactive({
  username: user.value?.username || '',
  realName: user.value?.realName || '',
  email: user.value?.email || '',
  phone: user.value?.phone || '',
})

const emailReg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const emailStatus = computed(() => {
  if (!formState.email) return undefined
  return emailReg.test(formState.email) ? undefined : 'error'
})
const emailFeedback = computed(() => {
  return emailStatus.value === 'error' ? '请输入正确的邮箱地址' : undefined
})

// ===== 浏览器通知 =====
const useNotification = ref(true)
const notificationList = [
  { value: 'follow', label: '跟进提醒' },
  { value: 'at', label: '@通知' },
  { value: 'checkin', label: '签到通知' },
  { value: 'interview_resume', label: '面试官简历筛选通知' },
  { value: 'candidate_interview', label: '候选人接受拒绝面试通知' },
  { value: 'interview_feedback', label: '面试官面试反馈' },
  { value: 'candidate_offer', label: '候选人接受拒绝Offer通知' },
  { value: 'offer_approval', label: 'Offer审批状态通知' },
  { value: 'headhunter', label: '猎头及内推提醒' },
]
const notificationOptions = ref<string[]>([
  'follow',
  'at',
  'checkin',
  'interview_resume',
  'candidate_interview',
  'interview_feedback',
  'candidate_offer',
  'offer_approval',
  'headhunter',
])

// ===== 自定义默认选项 =====
const defaultResumeMailbox = ref<string | null>(null)
const resumeMailboxOptions = [
  { label: '招聘公共邮箱', value: 'recruit@company.com' },
  { label: '技术招聘邮箱', value: 'tech-hire@company.com' },
  { label: '校招邮箱', value: 'campus@company.com' },
]

// ===== 更改密码 =====
const showPasswordModal = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const passwordConfirmStatus = computed(() => {
  if (!passwordForm.confirmPassword) return undefined
  return passwordForm.confirmPassword === passwordForm.newPassword ? undefined : 'error'
})
const passwordConfirmFeedback = computed(() => {
  return passwordConfirmStatus.value === 'error' ? '两次输入的密码不一致' : undefined
})

// ===== 初始化 =====
onMounted(() => {
  formState.username = user.value?.username || ''
  formState.realName = user.value?.realName || ''
  formState.email = user.value?.email || ''
  formState.phone = user.value?.phone || ''
})

// ===== 事件处理 =====
async function handleSaveProfile() {
  if (emailStatus.value === 'error') {
    message.error('请检查邮箱格式')
    return
  }
  if (!user.value?.id) {
    message.error('用户未登录')
    return
  }
  try {
    const { data } = await api.put(`/users/${user.value.id}/`, {
      realName: formState.realName,
      email: formState.email,
      phone: formState.phone,
    })
    if (data.success) {
      message.success('个人信息保存成功')
    } else {
      message.error(data.error || '保存失败')
    }
  } catch (error) {
    message.error('保存失败')
  }
}

function handleSaveNotifications() {
  message.success('浏览器通知设置已保存')
}

function handleSaveDefaults() {
  message.success('默认选项设置已保存')
}

function handleUploadEnv() {
  const env = navigator.userAgent
  console.log('上传当前浏览器环境:', env)
  message.success('浏览器环境已上传')
}

function handleChangePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
    message.error('请填写完整密码信息')
    return
  }
  if (passwordConfirmStatus.value === 'error') {
    message.error('两次输入的密码不一致')
    return
  }
  message.success('密码修改成功')
  showPasswordModal.value = false
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
  overflow-y: auto;
}
.page-header {
  flex-shrink: 0;
  margin-bottom: 16px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.settings-section {
  margin-bottom: 16px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.section-tag {
  font-weight: 500;
}
.section-alert {
  margin-bottom: 16px;
}
.section-desc {
  margin: 0 0 16px;
  color: var(--ink-soft);
  font-size: 13px;
}
.profile-form {
  max-width: 720px;
}
.notification-grid {
  padding: 12px 0 4px;
}
.section-actions {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-hairline);
}
</style>

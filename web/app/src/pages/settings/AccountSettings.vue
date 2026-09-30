<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.AccountSettings.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.AccountSettings.s2') }}</p>
    </div>

    <!-- 个人设置 / 浏览器通知 / 通知选项 三块内容统一进 .page-body 滚动区 -->
    <div class="page-body">
      <!-- 个人设置 -->
      <div class="glass-panel glass-panel--card">
        <div class="glass-panel__title">
          <span>{{ t('pages.settings.AccountSettings.s3') }}</span>
          <n-tag type="info" size="small" class="section-tag">{{ t('pages.settings.AccountSettings.s4') }}</n-tag>
        </div>
        <div class="glass-panel__body">
      <n-form label-placement="left" :label-width="96" :model="formState" class="profile-form">
        <n-grid :cols="1" :x-gap="24">
          <n-gi>
            <n-form-item :label="t('pages.settings.AccountSettings.s5')">
              <n-input v-model:value="formState.realName" :placeholder="t('pages.settings.AccountSettings.s6')" disabled />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item :label="t('pages.settings.AccountSettings.s7')">
              <n-input v-model:value="formState.phone" :placeholder="t('pages.settings.AccountSettings.s8')" disabled />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item :label="t('pages.settings.AccountSettings.s9')" :feedback="emailFeedback" :validation-status="emailStatus">
              <n-input v-model:value="formState.email" :placeholder="t('pages.settings.AccountSettings.s10')" disabled />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item :label="t('pages.settings.AccountSettings.s11')">
              <n-button type="primary" ghost size="small" @click="showPasswordModal = true">
                <template #icon>
                  <n-icon :component="LockClosedOutline" />
                </template>
                {{ t('pages.settings.AccountSettings.s12') }}
              </n-button>
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item :label="t('pages.settings.AccountSettings.s13')">
              <n-button size="small" @click="handleUploadEnv">
                <template #icon>
                  <n-icon :component="CloudUploadOutline" />
                </template>
                {{ t('pages.settings.AccountSettings.s14') }}
              </n-button>
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
        </div>
      </div>

    <!-- 浏览器通知 -->
    <div class="glass-panel glass-panel--card">
      <div class="glass-panel__title">
        <span>{{ t('pages.settings.AccountSettings.s15') }}</span>
        <n-tag type="info" size="small" class="section-tag">{{ t('pages.settings.AccountSettings.s16') }}</n-tag>
      </div>
      <div class="glass-panel__body">
<p class="section-desc">{{ t('pages.settings.AccountSettings.s17') }}</p>

      <n-form label-placement="left" :label-width="96">
        <n-form-item :label="t('pages.settings.AccountSettings.s18')">
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
      </div>
    </div>

    <!-- 自定义默认选项设置 -->
    <div class="glass-panel glass-panel--card">
      <div class="glass-panel__title">
        <span>{{ t('pages.settings.AccountSettings.s19') }}</span>
        <n-tag type="info" size="small" class="section-tag">{{ t('pages.settings.AccountSettings.s20') }}</n-tag>
      </div>
      <div class="glass-panel__body">
<p class="section-desc">
        {{ t('pages.settings.AccountSettings.s21') }}
      </p>

      <n-form label-placement="left" :label-width="120">
        <n-form-item :label="t('pages.settings.AccountSettings.s22')">
          <n-select
            v-model:value="defaultResumeMailbox"
            :placeholder="t('pages.settings.AccountSettings.s23')"
            :options="resumeMailboxOptions"
            style="width: 320px"
          />
        </n-form-item>
      </n-form>
      </div>
    </div>
    </div><!-- /.page-body -->

    <!-- 更改密码弹窗 -->
    <n-modal
      v-model:show="showPasswordModal"
      preset="card"
      :title="t('pages.settings.AccountSettings.s24')"
      style="width: 480px; max-width: 90vw"
      :mask-closable="false"
    >
      <n-form label-placement="left" :label-width="100" :model="passwordForm">
        <n-form-item :label="t('pages.settings.AccountSettings.s25')">
          <n-input v-model:value="passwordForm.oldPassword" type="password" show-password-on="click" :placeholder="t('pages.settings.AccountSettings.s26')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.AccountSettings.s27')">
          <n-input v-model:value="passwordForm.newPassword" type="password" show-password-on="click" :placeholder="t('pages.settings.AccountSettings.s28')" />
        </n-form-item>
        <n-form-item :label="t('pages.settings.AccountSettings.s29')" :validation-status="passwordConfirmStatus" :feedback="passwordConfirmFeedback">
          <n-input v-model:value="passwordForm.confirmPassword" type="password" show-password-on="click" :placeholder="t('pages.settings.AccountSettings.s30')" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showPasswordModal = false">{{ t('pages.settings.AccountSettings.s31') }}</n-button>
          <n-button type="primary" class="gradient-btn" @click="handleChangePassword">{{ t('pages.settings.AccountSettings.s32') }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, computed, onMounted } from 'vue'
import {
  NForm,
  NFormItem,
  NInput,
  NButton,
  NSpace,
  NTag,
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
import { changePassword } from '../../api/auth'
const { t } = useI18n()

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
  return emailStatus.value === 'error' ? t('pages.settings.AccountSettings.s39') : undefined
})

// ===== 浏览器通知 =====
const useNotification = ref(true)
const notificationList = [
  { value: 'follow', label: t('pages.settings.AccountSettings.s40') },
  { value: 'at', label: t('pages.settings.AccountSettings.s41') },
  { value: 'checkin', label: t('pages.settings.AccountSettings.s42') },
  { value: 'interview_resume', label: t('pages.settings.AccountSettings.s43') },
  { value: 'candidate_interview', label: t('pages.settings.AccountSettings.s44') },
  { value: 'interview_feedback', label: t('pages.settings.AccountSettings.s45') },
  { value: 'candidate_offer', label: t('pages.settings.AccountSettings.s46') },
  { value: 'offer_approval', label: t('pages.settings.AccountSettings.s47') },
  { value: 'headhunter', label: t('pages.settings.AccountSettings.s48') },
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
  { label: t('pages.settings.AccountSettings.s33'), value: 'recruit@company.com' },
  { label: t('pages.settings.AccountSettings.s34'), value: 'tech-hire@company.com' },
  { label: t('pages.settings.AccountSettings.s35'), value: 'campus@company.com' },
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
  return passwordConfirmStatus.value === 'error' ? t('pages.settings.AccountSettings.s38') : undefined
})

// ===== 初始化 =====
onMounted(() => {
  formState.username = user.value?.username || ''
  formState.realName = user.value?.realName || ''
  formState.email = user.value?.email || ''
  formState.phone = user.value?.phone || ''
})

// ===== 事件处理 =====
function handleUploadEnv() {
  const env = navigator.userAgent
  console.log(t('pages.settings.AccountSettings.s51'), env)
  message.success(t('pages.settings.AccountSettings.s36'))
}

async function handleChangePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
    message.error(t('pages.settings.AccountSettings.s37'))
    return
  }
  if (passwordConfirmStatus.value === 'error') {
    message.error(t('pages.settings.AccountSettings.s38'))
    return
  }
  try {
    const { data } = await changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    if (data.success) {
      message.success(data.message || t('pages.settings.AccountSettings.s49'))
      showPasswordModal.value = false
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    } else {
      message.error(data.message || t('pages.settings.AccountSettings.s50'))
    }
  } catch (error: any) {
    const errMsg = error.response?.data?.message || error.message || t('pages.settings.AccountSettings.s50')
    message.error(errMsg)
  }
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}

/* 2026-08-24 兵哥 19:59 反馈：拆成「标题区 + 内容区」，滚动职责下放到 .page-body
   - 标题区固定不动（flex-shrink: 0）
   - 内容区自己滚（flex: 1, min-height: 0, overflow-y: auto）
   - 避免原 .page-container overflow-y: auto 触发整页内嵌滚动条 + 与外层 .settings-scroll 双滚冲突 */
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* [T11] 同步限制 X 方向: 子元素 n-checkbox 白空间 nowrap 会撑宽父容器 */
  overflow-x: hidden;
  /* 内容卡片间留点呼吸间距 */
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 删除 scoped .page-header/.page-title 覆盖（规范：复用全局 glass.css 渐变规格） */

/* .settings-section 已废弃（卡片改为 .glass-panel--card，间距由 .page-body gap 提供） */
/* .section-title 已统一由全局 .glass-panel__title 提供 flex + gap + 字重 */
.section-tag {
  font-weight: 500;
}
.section-desc {
  margin: 0 0 var(--space-4);
  color: var(--ink-soft);
  font-size: var(--fs-13);
}
.profile-form {
  max-width: 720px;
}
.notification-grid {
  padding: var(--space-3) 0 var(--space-1);
  /* [T11] 浏览器通知 4 列网格: 长 label "候选人接受拒绝Offer通知" 默认 nowrap 会撑宽 n-gi,
     进而让 .n-grid 在 >= viewport 时隐式撑出横向滚动条; 允许换行让列宽自适应 */
}
.notification-grid :deep(.n-checkbox .n-checkbox__label) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}
/* 防御: 兜底阻断 X 溢出, 即使 grid 列宽计算异常也不出现横向滚动条 */
.notification-grid :deep(.n-grid) {
  overflow-x: hidden;
  min-width: 0;
}
.notification-grid :deep(.n-grid .n-grid-item) {
  min-width: 0;
}
</style>

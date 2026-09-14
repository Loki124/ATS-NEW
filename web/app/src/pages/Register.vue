<template>
  <div class="login-page">
    <div class="app-aurora">
      <div class="aurora-spot"></div>
    </div>

    <div class="login-container">
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="currentColor" class="logo-icon">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <h1 class="brand-title gradient-title">ATS 招聘管理系统</h1>
        <p class="brand-subtitle">申请注册账号</p>
      </div>

      <div class="glass-panel login-card">
        <!-- 步骤 1：填写信息并提交注册 -->
        <n-form
          v-if="step === 'form'"
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          @submit.prevent="onSubmit"
        >
          <n-form-item path="email">
            <n-input
              v-model:value="form.email"
              placeholder="企业邮箱"
              size="large"
              class="glass-input login-input"
              :disabled="submitting"
            >
              <template #prefix><n-icon :component="MailOutline" /></template>
            </n-input>
          </n-form-item>

          <n-form-item path="fullName">
            <n-input
              v-model:value="form.fullName"
              placeholder="姓名"
              size="large"
              class="glass-input login-input"
              :disabled="submitting"
            >
              <template #prefix><n-icon :component="PersonOutline" /></template>
            </n-input>
          </n-form-item>

          <n-form-item path="password">
            <n-input
              v-model:value="form.password"
              type="password"
              show-password-on="click"
              placeholder="密码（至少 8 位，含字母和数字）"
              size="large"
              class="glass-input login-input"
              :disabled="submitting"
              @keyup.enter="onSubmit"
            >
              <template #prefix><n-icon :component="LockClosedOutline" /></template>
            </n-input>
          </n-form-item>

          <n-form-item>
            <n-button
              type="primary"
              block
              size="large"
              :loading="submitting"
              attr-type="submit"
            >
              提交注册并获取验证码
            </n-button>
          </n-form-item>
        </n-form>

        <!-- 步骤 2：输入邮箱验证码 -->
        <div v-else class="verify-block">
          <n-alert type="info" :show-icon="true" class="verify-tip">
            验证码已发送至 <strong>{{ form.email }}</strong>，请查收邮件并填写 6 位验证码。
          </n-alert>

          <div class="code-input-wrapper">
            <n-input
              v-model:value="form.code"
              placeholder="6 位验证码"
              size="large"
              class="code-input glass-input login-input"
              :maxlength="6"
              :disabled="verifying"
            >
              <template #prefix><n-icon :component="LockClosedOutline" /></template>
            </n-input>
            <n-button
              class="code-button"
              size="large"
              :disabled="codeSent && countdown > 0"
              @click="onResend"
            >
              {{ codeSent && countdown > 0 ? `${countdown}s` : '重新获取' }}
            </n-button>
          </div>

          <n-button
            type="primary"
            block
            size="large"
            :loading="verifying"
            :disabled="form.code.length !== 6"
            @click="onVerify"
          >
            验证邮箱并提交审核
          </n-button>
        </div>

        <div class="login-footer">
          <p>已有账号？<a href="#" class="forgot-link" @click.prevent="goLogin">直接登录</a></p>
        </div>
      </div>

      <div class="login-features">
        <div class="feature-item"><span class="feature-icon">📧</span><span>邮箱验证</span></div>
        <div class="feature-item"><span class="feature-icon">👥</span><span>人工审核</span></div>
        <div class="feature-item"><span class="feature-icon">🔒</span><span>安全注册</span></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick, onBeforeUnmount, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { PersonOutline, LockClosedOutline, MailOutline } from '@vicons/ionicons5'
import { register, verifyRegisterCode, resendRegisterCode } from '../api/auth'

const router = useRouter()
const message = useMessage()

const step = ref<'form' | 'verify'>('form')
const submitting = ref(false)
const verifying = ref(false)
const codeSent = ref(false)
const countdown = ref(60)

const formRef = ref<FormInst | null>(null)
const form = reactive({ email: '', fullName: '', password: '', code: '' })

const rules: FormRules = {
  email: {
    required: true,
    message: '请输入企业邮箱',
    trigger: ['blur', 'input'],
    type: 'email',
  },
  fullName: { required: true, message: '请输入姓名', trigger: 'blur' },
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  code: { required: true, message: '请输入 6 位验证码', trigger: 'blur' },
}

const onSubmit = (e?: Event) => {
  e?.preventDefault()
  formRef.value?.validate(async (errors) => {
    if (errors) return
    submitting.value = true
    try {
      const { data } = await register({
        email: form.email.trim().toLowerCase(),
        password: form.password,
        fullName: form.fullName.trim(),
      })
      if (data.success) {
        step.value = 'verify'
        startCountdown()
        message.success('注册申请已提交，验证码已发送至您的邮箱')
      } else {
        message.error(data.message || '注册失败')
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.code === 'EMAIL_EXISTS' ? '该邮箱已被注册' :
        err?.message || '网络错误，请稍后重试'
      message.error(msg)
    } finally {
      submitting.value = false
    }
  })
}

const onVerify = async () => {
  verifying.value = true
  try {
    const { data } = await verifyRegisterCode(form.email.trim().toLowerCase(), form.code.trim())
    if (data.success) {
      message.success('邮箱验证成功，已提交管理员审核', {
        render: () => h('div', {
          style: 'background: color-mix(in srgb, var(--c-success) 18%, transparent); border: 1px solid color-mix(in srgb, var(--c-success) 35%, transparent); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: var(--c-success); padding: 8px 14px; border-radius: 6px;',
        }, '邮箱验证成功，已提交管理员审核'),
      })
      await nextTick()
      router.replace('/login')
    } else {
      message.error(data.message || '验证失败')
    }
  } catch (err: any) {
    message.error(err?.response?.data?.message || err?.message || '验证失败，请重试')
  } finally {
    verifying.value = false
  }
}

const onResend = async () => {
  if (codeSent.value && countdown.value > 0) return
  try {
    await resendRegisterCode(form.email.trim().toLowerCase())
    codeSent.value = true
    startCountdown()
    message.success('验证码已重新发送')
  } catch (err: any) {
    message.error(err?.response?.data?.message || err?.message || '重发失败')
  }
}

const startCountdown = () => {
  codeSent.value = true
  countdown.value = 60
  if (codeTimer !== null) clearInterval(codeTimer)
  codeTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (codeTimer !== null) {
        clearInterval(codeTimer)
        codeTimer = null
      }
    }
  }, 1000)
}

const goLogin = () => router.replace('/login')

let codeTimer: ReturnType<typeof setInterval> | null = null
onBeforeUnmount(() => {
  if (codeTimer !== null) clearInterval(codeTimer)
})
</script>

<style scoped>
.login-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
}
.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
}
.login-brand {
  text-align: center;
  margin-bottom: var(--space-8);
}
.brand-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--brand) 0%, var(--brand-grad-a) 100%);
  box-shadow: 0 12px 32px var(--glow-brand), inset 0 1px 0 rgba(255, 255, 255, .4);
  color: #fff;
}
.logo-icon { width: 50px; height: 50px; }
.brand-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 10px;
  line-height: 1.25;
}
.brand-subtitle {
  font-size: var(--text-body);
  color: var(--ink-soft);
  margin: 0;
}
.login-card {
  padding: var(--space-6) var(--space-8);
}
.verify-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.verify-tip {
  margin-bottom: var(--space-2);
}
.code-input-wrapper {
  display: flex;
  gap: var(--space-2);
  width: 100%;
}
.code-input { flex: 1; }
:deep(.code-button) {
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  color: var(--ink);
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
  transition: all var(--duration-fast) var(--ease-out);
}
:deep(.code-button:not([disabled]):hover) {
  border-color: var(--brand);
  color: var(--brand);
}
:deep(.code-button[disabled]) {
  color: var(--ink-faint);
  cursor: not-allowed;
  opacity: .65;
}
:deep(.login-input .n-input) {
  background: var(--glass-bg-input);
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}
:deep(.login-input .n-input-wrapper) { background: transparent; }
:deep(.login-input .n-input__border),
:deep(.login-input .n-input__state-border) {
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  background: transparent;
}
:deep(.login-input.n-input--focus .n-input__border),
:deep(.login-input.n-input--focus .n-input__state-border) {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-tint);
}
:deep(.login-input .n-input__placeholder),
:deep(.login-input .n-input__input-el),
:deep(.login-input .n-input__textarea-el) { color: var(--ink); }
:deep(.login-input .n-input__placeholder) { color: var(--ink-faint); }
:deep(.login-input .n-input__prefix),
:deep(.login-input .n-input__suffix) { color: var(--ink-soft); }
.login-footer {
  text-align: center;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-hairline);
}
.login-footer p { color: var(--ink-faint); font-size: var(--text-meta); margin: 0; }
.forgot-link {
  color: var(--brand);
  font-size: var(--text-small);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-out);
}
.forgot-link:hover { color: var(--brand-hover); }
.login-features {
  display: flex;
  justify-content: center;
  gap: var(--space-8);
  margin-top: var(--space-8);
  flex-wrap: wrap;
}
.feature-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  color: var(--ink-soft);
  font-size: var(--text-meta);
  font-weight: 500;
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
}
.feature-icon { font-size: var(--text-body); line-height: 1; }
@media (max-width: 600px) {
  .login-page { padding: var(--space-6) var(--space-4); }
  .login-container { max-width: none; width: 100%; }
  .login-card { padding: var(--space-4) var(--space-4); }
}
</style>

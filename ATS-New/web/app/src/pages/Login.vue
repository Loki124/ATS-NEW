<template>
  <div class="login-page">
    <div class="login-background">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <div class="login-container">
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="currentColor" class="logo-icon text-primary">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.48 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>
        <h1 class="brand-title">ATS招聘管理系统</h1>
        <p class="brand-subtitle">智能招聘 · 高效管理 · 数据驱动</p>
      </div>

      <n-card class="login-card" :bordered="false">
        <n-tabs v-model:value="activeTab" type="line" animated centered>
          <!-- 账号密码登录 -->
          <n-tab-pane name="account" tab="账号密码">
            <n-form
              ref="formAccountRef"
              :model="formAccount"
              :rules="accountRules"
              size="large"
              @submit.prevent="onAccountFinish"
            >
              <n-form-item path="username">
                <n-input
                  v-model:value="formAccount.username"
                  placeholder="用户名"
                  size="large"
                >
                  <template #prefix>
                    <n-icon :component="PersonOutline" />
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item path="password">
                <n-input
                  v-model:value="formAccount.password"
                  type="password"
                  show-password-on="click"
                  placeholder="密码"
                  size="large"
                  @keyup.enter="onAccountFinish"
                >
                  <template #prefix>
                    <n-icon :component="LockClosedOutline" />
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item>
                <div class="form-options">
                  <n-checkbox v-model:checked="rememberMe">记住我</n-checkbox>
                  <a href="#" class="forgot-link">忘记密码?</a>
                </div>
              </n-form-item>

              <n-form-item>
                <n-button
                  type="primary"
                  block
                  size="large"
                  :loading="loading"
                  attr-type="submit"
                  @click="onAccountFinish"
                >
                  登 录
                </n-button>
              </n-form-item>
            </n-form>
          </n-tab-pane>

          <!-- 短信验证码登录 -->
          <n-tab-pane name="sms" tab="手机验证码">
            <n-form :model="formSms" size="large" @submit.prevent="onSmsFinish">
              <n-form-item>
                <n-input v-model:value="formSms.phone" placeholder="请输入手机号" size="large">
                  <template #prefix>
                    <span class="input-icon">📱</span>
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item>
                <div class="code-input-wrapper">
                  <n-input v-model:value="formSms.code" placeholder="验证码" class="code-input" size="large">
                    <template #prefix>
                      <n-icon :component="LockClosedOutline" />
                    </template>
                  </n-input>
                  <n-button
                    class="code-button"
                    size="large"
                    :disabled="codeSent"
                    @click="sendCode"
                  >
                    {{ codeSent ? `${countdown}s` : '获取验证码' }}
                  </n-button>
                </div>
              </n-form-item>

              <n-form-item>
                <n-button
                  type="primary"
                  block
                  size="large"
                  :loading="loading"
                  attr-type="submit"
                  @click="onSmsFinish"
                >
                  登 录
                </n-button>
              </n-form-item>
            </n-form>
          </n-tab-pane>
        </n-tabs>

        <div class="login-footer">
          <p>默认账号: admin / admin123</p>
        </div>
      </n-card>

      <div class="login-features">
        <div class="feature-item">
          <span class="feature-icon">📊</span>
          <span>数据看板</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">👥</span>
          <span>人才库</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">📋</span>
          <span>流程管理</span>
        </div>
        <div class="feature-item">
          <span class="feature-icon">🔔</span>
          <span>智能提醒</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useUserStore } from '../stores/user'
import { login } from '../api/auth'

const router = useRouter()
const userStore = useUserStore()
const message = useMessage()

const loading = ref(false)
const activeTab = ref('account')
const rememberMe = ref(false)
const codeSent = ref(false)
const countdown = ref(60)

const formAccountRef = ref<FormInst | null>(null)
const formAccount = reactive({ username: '', password: '' })
const formSms = reactive({ phone: '', code: '' })

const accountRules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

const handleLogin = async (values: { username: string; password: string }) => {
  loading.value = true
  try {
    const response = await login(values.username, values.password)
    const data = response.data
    if (data.success) {
      localStorage.setItem('token', data.data.token)
      userStore.setUser({
        id: data.data.user.id,
        username: data.data.user.username,
        realName: data.data.user.realName,
        email: data.data.user.email,
        phone: data.data.user.phone,
        roleType: data.data.user.roleType,
      })
      if (rememberMe.value) {
        localStorage.setItem('rememberMe', 'true')
      }
      message.success('登录成功！')
      router.push('/dashboard')
    } else {
      message.error(data.message || '登录失败')
    }
  } catch (error: any) {
    message.error(error?.response?.data?.message || '登录失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

const onAccountFinish = (e?: Event) => {
  e?.preventDefault()
  formAccountRef.value?.validate((errors) => {
    if (!errors) {
      handleLogin(formAccount)
    }
  })
}

const onSmsFinish = () => {
  message.info('短信登录功能开发中')
}

const sendCode = () => {
  if (!formSms.phone) {
    message.warning('请输入手机号')
    return
  }
  codeSent.value = true
  countdown.value = 60
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      codeSent.value = false
    }
  }, 1000)
  message.success('验证码已发送')
}
</script>

<style scoped>
.login-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FBCE5B 0%, #E5B82A 100%);
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
}
.login-background {
  position: absolute;
  inset: 0;
  z-index: 0;
}
.shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
.shape-1 { width: 400px; height: 400px; top: -100px; right: -100px; animation: float 6s ease-in-out infinite; }
.shape-2 { width: 300px; height: 300px; bottom: -50px; left: -50px; animation: float 8s ease-in-out infinite; }
.shape-3 { width: 200px; height: 200px; top: 50%; left: 50%; animation: float 10s ease-in-out infinite; }
@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
}
.login-brand {
  text-align: center;
  margin-bottom: 40px;
}
.brand-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: white;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}
.logo-icon { width: 50px; height: 50px; }
.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin: 0 0 10px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}
.brand-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
}
.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}
.login-form { padding: 0; }
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.forgot-link {
  color: #FBCE5B;
  font-size: 14px;
  text-decoration: none;
}
.forgot-link:hover { color: #E5B82A; }
.code-input-wrapper {
  display: flex;
  gap: 10px;
  width: 100%;
}
.code-input { flex: 1; }
.login-footer {
  text-align: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
.login-footer p {
  color: #8c8c8c;
  font-size: 14px;
  margin: 0;
}
.login-features {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-top: 40px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}
.feature-icon { font-size: 20px; }
@media (max-width: 768px) {
  .login-features { gap: 20px; }
  .feature-item { font-size: 12px; }
}
</style>

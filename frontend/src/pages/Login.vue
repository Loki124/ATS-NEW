<template>
  <div class="login-page">
    <div class="login-background">
      <div class="login-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
    </div>
    
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="currentColor" class="logo-icon">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
          </svg>
        </div>
        <h1 class="brand-title">ATS招聘管理系统</h1>
        <p class="brand-subtitle">智能招聘 · 高效管理 · 数据驱动</p>
      </div>

      <a-card class="login-card" :bordered="false">
        <a-tabs 
          v-model:activeKey="activeTab" 
          centered
          class="login-tabs"
        >
          <a-tab-pane tab="账号密码" key="account">
            <a-form
              name="login"
              :model="formState"
              @finish="onFinish"
              size="large"
              class="login-form"
            >
              <a-form-item
                name="username"
                :rules="[{ required: true, message: '请输入用户名!' }]"
              >
                <a-input 
                  v-model:value="formState.username"
                  placeholder="用户名"
                  size="large"
                >
                  <template #prefix>
                    <UserOutlined class="input-icon" />
                  </template>
                </a-input>
              </a-form-item>

              <a-form-item
                name="password"
                :rules="[{ required: true, message: '请输入密码!' }]"
              >
                <a-input-password
                  v-model:value="formState.password"
                  placeholder="密码"
                  size="large"
                >
                  <template #prefix>
                    <LockOutlined class="input-icon" />
                  </template>
                </a-input-password>
              </a-form-item>

              <a-form-item>
                <div class="form-options">
                  <label class="remember-me">
                    <input type="checkbox" v-model="rememberMe" />
                    <span>记住我</span>
                  </label>
                  <a href="#" class="forgot-link">忘记密码?</a>
                </div>
              </a-form-item>

              <a-form-item>
                <a-button 
                  type="primary" 
                  html-type="submit" 
                  block
                  :loading="loading"
                  class="login-button"
                  size="large"
                >
                  登 录
                </a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>

          <a-tab-pane tab="手机验证码" key="sms">
            <a-form
              name="smsLogin"
              :model="smsFormState"
              @finish="onSmsFinish"
              size="large"
              class="login-form"
            >
              <a-form-item
                name="phone"
                :rules="[{ required: true, message: '请输入手机号!' }]"
              >
                <a-input 
                  v-model:value="smsFormState.phone"
                  placeholder="请输入手机号"
                  size="large"
                >
                  <template #prefix>
                    <span class="input-icon">📱</span>
                  </template>
                </a-input>
              </a-form-item>

              <a-form-item
                name="code"
                :rules="[{ required: true, message: '请输入验证码!' }]"
              >
                <div class="code-input-wrapper">
                  <a-input 
                    v-model:value="smsFormState.code"
                    placeholder="验证码"
                    class="code-input"
                    size="large"
                  >
                    <template #prefix>
                      <LockOutlined class="input-icon" />
                    </template>
                  </a-input>
                  <a-button class="code-button" size="large" @click="sendCode" :disabled="codeSent">
                    {{ codeSent ? `${countdown}s` : '获取验证码' }}
                  </a-button>
                </div>
              </a-form-item>

              <a-form-item>
                <a-button 
                  type="primary" 
                  html-type="submit" 
                  block
                  :loading="loading"
                  class="login-button"
                  size="large"
                >
                  登 录
                </a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
        </a-tabs>

        <div class="login-footer">
          <p>默认账号: admin / admin123</p>
        </div>
      </a-card>

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
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { useUserStore } from '../stores/user'
import { login } from '../api/auth'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const activeTab = ref('account')
const rememberMe = ref(false)
const codeSent = ref(false)
const countdown = ref(60)

const formState = reactive({
  username: '',
  password: ''
})

const smsFormState = reactive({
  phone: '',
  code: ''
})

const handleLogin = async (values: any) => {
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

const onFinish = (values: any) => {
  handleLogin(values)
}

const onSmsFinish = (values: any) => {
  // 短信登录逻辑
  message.info('短信登录功能开发中')
}

const sendCode = () => {
  if (!smsFormState.phone) {
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
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.login-shapes {
  position: absolute;
  width: 100%;
  height: 100%;
}

.shape {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.shape-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  animation: float 6s ease-in-out infinite;
}

.shape-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
  animation: float 8s ease-in-out infinite;
}

.shape-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 50%;
  animation: float 10s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-20px) rotate(5deg); }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 480px;
  padding: 20px;
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

.logo-icon {
  width: 50px;
  height: 50px;
  color: #667eea;
}

.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin: 0 0 10px 0;
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
  padding: 20px 0;
}

.login-tabs :deep(.ant-tabs-tab) {
  font-size: 16px;
  padding: 12px 20px;
}

.login-tabs :deep(.ant-tabs-tab-active) {
  font-weight: 600;
}

.login-form {
  padding: 20px 30px;
}

.login-form :deep(.ant-input-affix-wrapper) {
  border-radius: 8px;
  padding: 12px 16px;
}

.login-form :deep(.ant-input) {
  font-size: 15px;
}

.input-icon {
  color: #8c8c8c;
  font-size: 16px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remember-me {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #595959;
}

.remember-me input {
  margin-right: 6px;
}

.forgot-link {
  color: #667eea;
  font-size: 14px;
}

.forgot-link:hover {
  color: #764ba2;
}

.login-button {
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  font-weight: 600;
  transition: all 0.3s;
}

.login-button:hover {
  opacity: 0.9;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.code-input-wrapper {
  display: flex;
  gap: 10px;
}

.code-input {
  flex: 1;
}

.code-button {
  width: 120px;
  border-radius: 8px;
  background: #f0f0f0;
  border: none;
  color: #666;
  font-weight: 500;
}

.code-button:hover {
  background: #e0e0e0;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  padding-top: 20px;
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

.feature-icon {
  font-size: 20px;
}

@media (max-width: 768px) {
  .login-features {
    gap: 20px;
  }
  
  .feature-item {
    font-size: 12px;
  }
}
</style>
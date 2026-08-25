<template>
  <div class="login-page">
    <!-- T2.1: 全局极光底（DESIGN.md §2）—— 全站 fixed，z-index 0，pointer-events none -->
    <div class="app-aurora">
      <div class="aurora-spot"></div>
    </div>

    <div class="login-container">
      <!-- 顶部品牌区 -->
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="currentColor" class="logo-icon">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <h1 class="brand-title gradient-title">ATS 招聘管理系统</h1>
        <p class="brand-subtitle">智能招聘 · 高效管理 · 数据驱动</p>
      </div>

      <!-- T2.2: 玻璃面板登录卡（DESIGN.md §4 玻璃面板 · .glass-panel） -->
      <div class="glass-panel login-card">
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
                  class="glass-input login-input"
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
                  class="glass-input login-input"
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
                <n-input
                  v-model:value="formSms.phone"
                  placeholder="请输入手机号"
                  size="large"
                  class="glass-input login-input"
                >
                  <template #prefix>
                    <span class="input-icon">📱</span>
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item>
                <div class="code-input-wrapper">
                  <n-input
                    v-model:value="formSms.code"
                    placeholder="验证码"
                    class="code-input glass-input login-input"
                    size="large"
                  >
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
      </div>

      <!-- 底部功能特性（玻璃小卡） -->
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
import { ref, reactive, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useUserStore } from '../stores/user'
import { login } from '../api/auth'
import { deriveRoleType } from '../utils/role'

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
      // 修复: 兼容 Django SimpleJWT 双 token 模式
      //   旧 login API 返回 { token: 'xxx' } (单 token)
      //   新 Django login API 返回 { access, refresh, user } (双 token)
      // 仅写 'accessToken' (新规范). 老 API 文件用
      //   localStorage.getItem('accessToken') || localStorage.getItem('token')
      // 已经兼容 (见 web/app/src/api/*.ts).
      const _token = data.data.token || data.data.access
      const _refresh = data.data.refresh
      if (_token) {
        userStore.setAccessToken(_token)
        // 清掉旧 key (如果历史登录残留): 双写会导致 401 后 router guard 误判
        localStorage.removeItem('token')
      }
      if (_refresh) {
        userStore.setRefreshToken(_refresh)
      }
      // 后端 (apps/core/views_auth.py:49-56) emit:
      //   { id, username, fullName, employeeId, department, roles: string[] }
      // 2026-06-17: BE 启用 drf-camel-case 后, snake_case 字段自动转 camelCase, FE 直接消费.
      // 单词字段 (id, username, roles, department) 不受影响.
      const roles: string[] = data.data.user.roles ?? []
      const roleType = deriveRoleType(roles)

      userStore.setUser({
        id: data.data.user.id,
        username: data.data.user.username,
        realName: data.data.user.fullName,
        employeeId: data.data.user.employeeId,
        departmentId: data.data.user.department,
        // roles 是真值 (后端 RBAC); roleType 是 guard / UI 用的派生便利字段
        roles,
        roleType,
      })
      if (rememberMe.value) {
        localStorage.setItem('rememberMe', 'true')
      }
      // 2026-08-25：登录成功 toast 加半透明绿色底色（Naive 默认 toast 在暗色页面上没背景，看不清）
      message.success('登录成功！', {
        containerStyle: 'background: rgba(22, 163, 74, 0.18); border: 1px solid rgba(22, 163, 74, 0.35); backdrop-filter: blur(8px); color: #16a34a;',
      })
      // 用 nextTick 避免 message toast 在路由切换时被销毁
      await nextTick()
      // 用 replace 而非 push：登录后用替换语义，避免返回按钮回到 /login
      await router.replace('/dashboard').catch((e: any) => {
        // Vue Router 在重复 push 或 abort 时 reject NavigationFailure —
        // replace 通常不会重复，但防御性 catch 防止导航卡住
        if (e?.name === 'NavigationFailure') return
        console.error('[login] navigation failed:', e?.message)
      })
    } else {
      message.error(data.message || '登录失败')
    }
  } catch (error: any) {
    // 2026-07-02: 网络错误 / 5xx 时给用户反馈, 之前只 console.error 用户无感
    console.error('[login] error:', error?.response?.status, error?.message)
    const msg = error?.response?.data?.message
      || error?.message
      || '网络错误, 请稍后重试'
    message.error(msg)
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
  // 2026-07-02: setInterval 提到外面, onBeforeUnmount 清掉, 防路由切换后计时器泄漏
  if (codeTimer !== null) clearInterval(codeTimer)
  codeTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (codeTimer !== null) {
        clearInterval(codeTimer)
        codeTimer = null
      }
      codeSent.value = false
    }
  }, 1000)
  message.success('验证码已发送')
}

let codeTimer: ReturnType<typeof setInterval> | null = null
onBeforeUnmount(() => {
  if (codeTimer !== null) clearInterval(codeTimer)
})
</script>

<style scoped>
/* ============================================================
 * Login.vue — 阶段 2 玻璃化（T2.2）
 *   - 极光底（DESIGN.md §2）
 *   - 玻璃面板登录卡（DESIGN.md §4 玻璃面板 · .glass-panel）
 *   - 输入框穿透 Naive UI：使用 .glass-input 等价样式（tokens.css 变量驱动）
 *   - 渐变标题（DESIGN.md §3 · .gradient-title）
 *   - 暗色模式：组件 CSS 不变，自动跟随 body.dark
 *   - 响应式：< 600px 卡片占满宽度
 * ============================================================ */

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

/* === 顶部品牌区 === */
.login-brand {
  text-align: center;
  margin-bottom: 32px;
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
  color: #fff; /* 品牌色块上的图标 = 白色（DESIGN.md §4 btn-primary） */
}
.logo-icon { width: 50px; height: 50px; }
.brand-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 10px;
  line-height: 1.25;
  /* 渐变文字（DESIGN.md §3）：brand → brand-grad-a → brand-grad-b */
}
.brand-subtitle {
  font-size: var(--text-body);
  color: var(--ink-soft);
  margin: 0;
}

/* === 玻璃面板登录卡 === */
.login-card {
  padding: var(--space-6) var(--space-8);
  /* .glass-panel 已提供背景/blur/边框/高光/圆角/阴影 */
}

/* === 输入框：穿透 Naive UI 内部，套用 .glass-input 等价样式 === */
:deep(.login-input .n-input) {
  background: var(--glass-bg-input);
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}
/* Naive UI 内层 .n-input-wrapper 用作视觉层（border 在这里），让其透明显示外层 */
:deep(.login-input .n-input-wrapper) {
  background: transparent;
}
/* Naive UI 的边框层（绝对定位在 wrapper 里） */
:deep(.login-input .n-input__border),
:deep(.login-input .n-input__state-border) {
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  background: transparent;
}
/* focus 态（n-input--focus） */
:deep(.login-input.n-input--focus .n-input__border),
:deep(.login-input.n-input--focus .n-input__state-border) {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-tint);
}
/* placeholder / prefix 图标颜色 */
:deep(.login-input .n-input__placeholder),
:deep(.login-input .n-input__input-el),
:deep(.login-input .n-input__textarea-el) {
  color: var(--ink);
}
:deep(.login-input .n-input__placeholder) {
  color: var(--ink-faint);
}
:deep(.login-input .n-input__prefix),
:deep(.login-input .n-input__suffix) {
  color: var(--ink-soft);
}

/* === 表单选项（记住我 / 忘记密码）=== */
.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.forgot-link {
  color: var(--brand);
  font-size: var(--text-small);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-out);
}
.forgot-link:hover {
  color: var(--brand-hover);
}

/* === 短信验证码输入框组 === */
.code-input-wrapper {
  display: flex;
  gap: var(--space-2);
  width: 100%;
}
.code-input { flex: 1; }
/* code-button 用玻璃次按钮（hover 描边变品牌色） */
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

/* === 底部 footer（默认账号提示）=== */
.login-footer {
  text-align: center;
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-hairline);
}
.login-footer p {
  color: var(--ink-faint);
  font-size: var(--text-meta);
  margin: 0;
}

/* === 底部特性（玻璃小卡风格）=== */
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

/* === 响应式（DESIGN.md §8）===
 *  < 600px：卡片占满宽度，去掉 max-width 限制，缩小 padding
 */
@media (max-width: 600px) {
  .login-page {
    padding: 24px 16px;
  }
  .login-container {
    max-width: none; /* 关键：去掉 480px 上限，让卡片占满宽度 */
    width: 100%;
  }
  .login-card {
    padding: var(--space-4) var(--space-4);
  }
  .login-features {
    gap: var(--space-3);
  }
}
@media (max-width: 380px) {
  .login-features {
    gap: var(--space-2);
  }
  .feature-item {
    padding: 4px 10px;
    font-size: 11px;
  }
}
</style>
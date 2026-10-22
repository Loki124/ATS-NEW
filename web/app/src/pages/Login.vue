<template>
    <div class="login-page">
    <!-- T2.1: 全局极光底（DESIGN.md §2）—— 全站 fixed，z-index 0，pointer-events none -->
    <div class="app-aurora">
      <div class="aurora-spot"></div>
    </div>

    <!-- P1-3: 登录页语言切换（独立页无 Layout，用全局 currentLocale 驱动） -->
    <div class="login-lang-switch">
      <button
        v-for="loc in supportedLocales"
        :key="loc.code"
        type="button"
        class="lang-btn"
        :class="{ active: currentLocale === loc.code }"
        @click="setLocale(loc.code)"
      >
        {{ loc.native }}
      </button>
    </div>

    <div class="login-container">
      <!-- 顶部品牌区 -->
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="currentColor" class="logo-icon">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
          </svg>
        </div>
        <h1 class="brand-title gradient-title">{{ t('pages.Login.s1') }}</h1>
        <p class="brand-subtitle">{{ t('pages.Login.s2') }}</p>
      </div>

      <!-- T2.2: 玻璃面板登录卡（DESIGN.md §4 玻璃面板 · .glass-panel） -->
      <div class="glass-panel login-card">
        <n-tabs v-model:value="activeTab" type="line" animated centered>
          <!-- 账号密码登录 -->
          <n-tab-pane name="account" :tab="t('pages.Login.s4')">
            <n-form
              ref="formAccountRef"
              :model="formAccount"
              :rules="accountRules"
              size="large"
              label-placement="top"
              @submit.prevent="onAccountFinish"
            >
              <n-form-item path="username" :label="t('pages.Login.s3')">
                <n-input
                  v-model:value="formAccount.username"
                  :placeholder="t('pages.Login.s3')"
                  size="large"
                  class="glass-input login-input"
                >
                  <template #prefix>
                    <n-icon :component="PersonOutline" />
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item path="password" :label="t('pages.Login.s6')">
                <n-input
                  v-model:value="formAccount.password"
                  type="password"
                  show-password-on="click"
                  :placeholder="t('pages.Login.s6')"
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
                  <n-checkbox v-model:checked="rememberMe">{{ t('pages.Login.s7') }}</n-checkbox>
                  <a href="#" class="forgot-link">{{ t('pages.Login.s8') }}</a>
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
                  {{ t('pages.Login.s9') }}
                </n-button>
              </n-form-item>
            </n-form>
          </n-tab-pane>

          <!-- 邮箱验证码登录（免密） -->
          <n-tab-pane name="email" :tab="t('pages.Login.s5')">
            <n-form :model="formEmail" size="large" label-placement="top" @submit.prevent="onEmailFinish">
              <n-form-item :label="t('pages.Login.s13')">
                <n-input
                  v-model:value="formEmail.email"
                  :placeholder="t('pages.Login.s10')"
                  size="large"
                  class="glass-input login-input"
                >
                  <template #prefix>
                    <n-icon :component="MailOutline" />
                  </template>
                </n-input>
              </n-form-item>

              <n-form-item :label="t('pages.Login.s11')">
                <div class="code-input-wrapper">
                  <n-input
                    v-model:value="formEmail.code"
                    :placeholder="t('pages.Login.s11')"
                    class="code-input glass-input login-input"
                    size="large"
                    @keyup.enter="onEmailFinish"
                  >
                    <template #prefix>
                      <n-icon :component="LockClosedOutline" />
                    </template>
                  </n-input>
                  <n-button
                    class="code-button"
                    size="large"
                    :loading="sendingCode"
                    :disabled="codeSent"
                    @click="sendEmailCode"
                  >
                    {{ codeSent ? `${countdown}s` : t('pages.Login.s12') }}
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
                  @click="onEmailFinish"
                >
                  {{ t('pages.Login.s9') }}
                </n-button>
              </n-form-item>
            </n-form>
          </n-tab-pane>
        </n-tabs>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, reactive, nextTick, onBeforeUnmount, h } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, type FormInst, type FormRules } from 'naive-ui'
import { PersonOutline, LockClosedOutline, MailOutline } from '@vicons/ionicons5'
import { useUserStore } from '../stores/user'
import { login, sendEmailLoginCode, emailLogin } from '../api/auth'
import { deriveRoleType } from '../utils/role'
import { currentLocale, SUPPORTED_LOCALES, type AppLocale } from '../locales'
const { t } = useI18n()

// P1-3: 登录页语言切换（currentLocale 是全局唯一真相源，赋值即切换 + 持久化）
const supportedLocales = SUPPORTED_LOCALES
function setLocale(code: AppLocale) {
  currentLocale.value = code
}

const router = useRouter()
const userStore = useUserStore()
const message = useMessage()

const loading = ref(false)
const activeTab = ref('account')
const rememberMe = ref(false)
const codeSent = ref(false)
const sendingCode = ref(false)
const countdown = ref(60)

const formAccountRef = ref<FormInst | null>(null)
const formAccount = reactive({ username: '', password: '' })
// 2026-10-18 兵哥：原「短信验证码登录」改为「邮箱验证码登录（免密）」。
//   自助注册已下线，账号由管理员开通；待激活用户首次完成邮箱验证即自动激活。
const formEmail = reactive({ email: '', code: '' })

const accountRules: FormRules = {
  username: { required: true, message: '请输入用户名', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' },
}

/**
 * 登录成功后的统一收尾：写 token / 写用户态 / toast / 跳转。
 * 账号密码登录与邮箱验证码登录共用（后端两者返回体同构）。
 */
const completeLogin = async (data: any) => {
  // 兼容 Django SimpleJWT 双 token 模式:
  //   旧 login API 返回 { token: 'xxx' } (单 token)
  //   新 Django login API 返回 { access, refresh, user } (双 token)
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
  // 后端 (apps/core/views_auth.py) emit:
  //   { id, username, fullName, employeeId, department, roles: string[] }
  // 2026-06-17: BE 启用 drf-camel-case 后, snake_case 字段自动转 camelCase, FE 直接消费.
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
  // 注：message API 的 MessageOptions 不含 containerStyle（仅 MessageProvider 才有），故改用 render 自渲染保留下暗色可读性
  message.success(t('pages.Login.s20'), {
    render: () => h('div', {
      style: 'background: color-mix(in srgb, var(--c-success) 18%, transparent); border: 1px solid color-mix(in srgb, var(--c-success) 35%, transparent); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: var(--c-success-deep); padding: 8px 14px; border-radius: 6px;',
    }, t('pages.Login.s20')),
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
}

/** 登录失败统一提示：账号状态类错误给出明确指引，其余走通用提示。 */
const reportLoginError = (error: any) => {
  console.error('[login] error:', error?.response?.status, error?.message)
  const status = error?.response?.status
  const data = error?.response?.data || {}
  // 待激活 / 已停用账号：后端返回 403 + code=account_pending|account_disabled
  // （apps/core/views_auth.py login_view）。不再误报"密码错误"，给出明确指引。
  if (status === 403 && data.code === 'account_pending') {
    message.warning(data.message || t('pages.Login.s24'))
  } else if (status === 403 && data.code === 'account_disabled') {
    message.error(data.message || t('pages.Login.s25'))
  } else {
    const msg = data.message || error?.message || t('pages.Login.s26')
    message.error(msg)
  }
}

const handleLogin = async (values: { username: string; password: string }) => {
  loading.value = true
  try {
    const response = await login(values.username, values.password)
    const data = response.data
    if (data.success) {
      await completeLogin(data)
    } else {
      message.error(data.message || '登录失败')
    }
  } catch (error: any) {
    // 2026-07-02: 网络错误 / 5xx 时给用户反馈, 之前只 console.error 用户无感
    reportLoginError(error)
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

// ===== 邮箱验证码登录（免密）=====
const onEmailFinish = (e?: Event) => {
  e?.preventDefault()
  if (!formEmail.email) {
    message.warning(t('pages.Login.s10'))
    return
  }
  if (!formEmail.code) {
    message.warning(t('pages.Login.s11'))
    return
  }
  loading.value = true
  emailLogin(formEmail.email, formEmail.code)
    .then(async (response: any) => {
      await completeLogin(response.data)
    })
    .catch(reportLoginError)
    .finally(() => {
      loading.value = false
    })
}

/** 发送邮箱验证码：后端会先校验账号有效性（不存在/已停用直接拒绝，不发邮件）。 */
const sendEmailCode = async () => {
  if (!formEmail.email) {
    message.warning(t('pages.Login.s10'))
    return
  }
  sendingCode.value = true
  try {
    const response: any = await sendEmailLoginCode(formEmail.email)
    if (response.data?.success) {
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
      message.success(response.data.message || t('pages.Login.s23'))
    } else {
      message.error(response.data?.message || t('pages.Login.s26'))
    }
  } catch (error: any) {
    const data = error?.response?.data || {}
    message.error(data.message || error?.message || t('pages.Login.s26'))
  } finally {
    sendingCode.value = false
  }
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

/* === P1-3: 语言切换（右上角玻璃分段开关）=== */
.login-lang-switch {
  position: absolute;
  top: var(--space-5);
  right: var(--space-5);
  z-index: 2;
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  border-radius: var(--radius-pill);
  background: var(--glass-bg-card);
  border: 1px solid var(--glass-border);
  backdrop-filter: blur(var(--glass-blur-input));
  -webkit-backdrop-filter: blur(var(--glass-blur-input));
}
.lang-btn {
  appearance: none;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: var(--text-small);
  font-weight: 500;
  line-height: 1;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  color: var(--ink-soft);
  transition: all var(--duration-fast) var(--ease-out);
}
.lang-btn:hover {
  color: var(--ink);
}
.lang-btn.active {
  color: #fff;
  background: var(--brand-button);
  box-shadow: 0 2px 8px var(--glow-brand);
}
.lang-btn.active:hover {
  color: #fff;
}

/* === 顶部品牌区 === */
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
  color: var(--brand-fg);
  font-size: var(--text-small);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-out);
}
.forgot-link:hover {
  color: var(--brand-fg-hover);
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
  color: var(--brand-fg);
}
:deep(.code-button[disabled]) {
  color: var(--ink-faint);
  cursor: not-allowed;
  opacity: .65;
}

/* === 响应式（DESIGN.md §8）===
 *  < 600px：卡片占满宽度，去掉 max-width 限制，缩小 padding
 */
@media (max-width: 600px) {
  .login-page {
    padding: var(--space-6) var(--space-4);
  }
  .login-container {
    max-width: none; /* 关键：去掉 480px 上限，让卡片占满宽度 */
    width: 100%;
  }
  .login-card {
    padding: var(--space-4) var(--space-4);
  }
}
</style>
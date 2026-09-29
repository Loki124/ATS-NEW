<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.CompanyBrand.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.CompanyBrand.s2') }}</p>
      </div>
    </div>

    <div class="page-body">
      <n-form ref="formRef" :model="formData" label-placement="left" :label-width="110">
        <div class="brand-grid">
          <!-- 左列：基础信息 -->
          <div class="brand-col">
            <n-card :title="t('pages.settings.CompanyBrand.s6')" class="config-card">
              <n-form-item :label="t('pages.settings.CompanyBrand.s7')">
                <n-input
                  v-model:value="formData.companyName"
                  :placeholder="t('pages.settings.CompanyBrand.s3')"
                  maxlength="255"
                  show-count
                />
              </n-form-item>
              <n-form-item :label="t('pages.settings.CompanyBrand.s8')">
                <n-input
                  v-model:value="formData.brandSlogan"
                  :placeholder="t('pages.settings.CompanyBrand.s4')"
                  maxlength="255"
                  show-count
                />
              </n-form-item>
              <n-form-item :label="t('pages.settings.CompanyBrand.s9')">
                <n-input
                  v-model:value="formData.brandIntro"
                  type="textarea"
                  :placeholder="t('pages.settings.CompanyBrand.s5')"
                  :rows="4"
                />
              </n-form-item>
            </n-card>

            <n-card title="Logo" class="config-card">
              <div class="logo-block">
                <div class="logo-preview" :class="{ 'is-empty': !formData.logoUrl }">
                  <img v-if="formData.logoUrl" :src="formData.logoUrl" :alt="t('pages.settings.CompanyBrand.s10')" class="logo-img" />
                  <n-empty v-else :description="t('pages.settings.CompanyBrand.s11')" size="small" />
                </div>
                <div class="logo-actions">
                  <n-upload
                    :show-file-list="false"
                    accept="image/*"
                    :disabled="uploading"
                    @before-upload="onBeforeLogoUpload"
                  >
                    <n-button size="small" type="primary" :loading="uploading" secondary>
                      <template #icon>
                        <n-icon><CloudUploadOutline /></n-icon>
                      </template>
                      {{ formData.logoUrl ? t('pages.settings.CompanyBrand.s46') : t('pages.settings.CompanyBrand.s47') }}
                    </n-button>
                  </n-upload>
                  <n-button size="small" tertiary :disabled="!formData.logoUrl" @click="formData.logoUrl = ''">
                    {{ t('pages.settings.CompanyBrand.s12') }}
                  </n-button>
                </div>
                <n-input
                  v-model:value="formData.logoUrl"
                  :placeholder="t('pages.settings.CompanyBrand.s13')"
                  class="logo-url-input"
                />
                <p class="field-hint">{{ t('pages.settings.CompanyBrand.s14') }}</p>
              </div>
            </n-card>

            <n-card :title="t('pages.settings.CompanyBrand.s15')" class="config-card">
              <n-form-item :label="t('pages.settings.CompanyBrand.s16')">
                <n-input v-model:value="formData.contactEmail" placeholder="hr@example.com" maxlength="255" />
              </n-form-item>
              <n-form-item :label="t('pages.settings.CompanyBrand.s17')">
                <n-input v-model:value="formData.contactPhone" :placeholder="t('pages.settings.CompanyBrand.s18')" maxlength="64" />
              </n-form-item>
            </n-card>
          </div>

          <!-- 右列：展示与预览 -->
          <div class="brand-col">
            <n-card :title="t('pages.settings.CompanyBrand.s19')" class="config-card preview-card">
              <div class="portal-preview" :style="portalStyle">
                <div class="portal-banner" :style="bannerStyle">
                  <img v-if="formData.logoUrl" :src="formData.logoUrl" class="portal-logo" alt="Logo" />
                  <div v-else class="portal-logo portal-logo--ph">LOGO</div>
                  <div class="portal-meta">
                    <div class="portal-name">{{ formData.companyName || t('pages.settings.CompanyBrand.s48') }}</div>
                    <div class="portal-slogan">{{ formData.brandSlogan || t('pages.settings.CompanyBrand.s49') }}</div>
                  </div>
                </div>
                <div class="portal-body">
                  <h4 class="portal-title">{{ formData.portalTitle || t('pages.settings.CompanyBrand.s50') }}</h4>
                  <p class="portal-sub">{{ formData.portalSubtitle || t('pages.settings.CompanyBrand.s51') }}</p>
                  <n-button size="small" :color="primaryColorSafe" class="portal-cta">{{ t('pages.settings.CompanyBrand.s20') }}</n-button>
                  <div v-if="formData.socialLinks.length" class="portal-links">
                    <span
                      v-for="link in formData.socialLinks"
                      :key="link.url"
                      class="portal-link"
                      :style="{ color: primaryColorSafe, borderColor: primaryColorSafe }"
                    >{{ link.label || link.platform || t('pages.settings.CompanyBrand.s52') }}</span>
                  </div>
                </div>
              </div>
            </n-card>

            <n-card :title="t('pages.settings.CompanyBrand.s21')" class="config-card">
              <n-form-item :label="t('pages.settings.CompanyBrand.s22')">
                <n-input v-model:value="formData.portalTitle" :placeholder="t('pages.settings.CompanyBrand.s23')" maxlength="255" />
              </n-form-item>
              <n-form-item :label="t('pages.settings.CompanyBrand.s24')">
                <n-input v-model:value="formData.portalSubtitle" :placeholder="t('pages.settings.CompanyBrand.s25')" maxlength="255" />
              </n-form-item>
              <n-form-item :label="t('pages.settings.CompanyBrand.s26')">
                <n-input
                  v-model:value="formData.portalBannerUrl"
                  :placeholder="t('pages.settings.CompanyBrand.s27')"
                />
              </n-form-item>
              <div v-if="formData.portalBannerUrl" class="banner-preview">
                <img :src="formData.portalBannerUrl" :alt="t('pages.settings.CompanyBrand.s28')" class="banner-img" />
              </div>
              <n-form-item :label="t('pages.settings.CompanyBrand.s29')">
                <div class="color-row">
                  <!-- 空值回落默认品牌色, 避免显示透明棋盘格像「故障」 -->
                  <n-color-picker
                    :value="formData.primaryColor || DEFAULT_BRAND"
                    :show-alpha="false"
                    :modes="['hex']"
                    class="color-picker"
                    @update:value="formData.primaryColor = $event"
                  />
                  <span class="field-hint">{{ t('pages.settings.CompanyBrand.s30') }}</span>
                </div>
              </n-form-item>
            </n-card>

            <n-card :title="t('pages.settings.CompanyBrand.s31')" class="config-card">
              <n-space vertical :size="12">
                <div
                  v-for="(link, idx) in formData.socialLinks"
                  :key="idx"
                  class="social-row"
                >
                  <n-select
                    v-model:value="link.platform"
                    :options="platformOptions"
                    class="social-platform"
                    :placeholder="t('pages.settings.CompanyBrand.s32')"
                  />
                  <n-input v-model:value="link.label" class="social-label" :placeholder="t('pages.settings.CompanyBrand.s33')" />
                  <n-input v-model:value="link.url" class="social-url" :placeholder="t('pages.settings.CompanyBrand.s34')" />
                  <n-button text type="error" @click="removeSocial(idx)">{{ t('pages.settings.CompanyBrand.s35') }}</n-button>
                </div>
                <n-button dashed block @click="addSocial">{{ t('pages.settings.CompanyBrand.s36') }}</n-button>
              </n-space>
            </n-card>
          </div>
        </div>
      </n-form>

      <!-- 底部 sticky 操作条：长表单滚动时操作始终可见（UX 修复：原按钮悬在页头，动线断裂） -->
      <div class="form-actions">
        <span class="save-state" :class="{ 'is-dirty': isDirty }">
          {{ isDirty ? t('pages.settings.CompanyBrand.s53') : t('pages.settings.CompanyBrand.s54') }}
        </span>
        <n-space>
          <n-button :disabled="!isDirty || saving" @click="handleReset">{{ t('pages.settings.CompanyBrand.s37') }}</n-button>
          <n-button type="primary" :loading="saving" :disabled="!isDirty && !saving" @click="handleSave">{{ t('pages.settings.CompanyBrand.s38') }}</n-button>
        </n-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed, onMounted } from 'vue'
import {
  NButton, NSpace, NCard, NForm, NFormItem, NInput, NColorPicker, NSelect, NEmpty,
  NUpload, NIcon, useMessage,
} from 'naive-ui'
import { CloudUploadOutline } from '@vicons/ionicons5'
import { fetchBrandInfo, updateBrandInfo, uploadBrandLogo, type BrandInfo, type SocialLink } from '../../api/brand'
import { useBrandStore } from '../../stores/brand'
const { t } = useI18n()

const message = useMessage()
const brandStore = useBrandStore()
const saving = ref(false)
const uploading = ref(false)
const formRef = ref()

const platformOptions = [
  { label: t('pages.settings.CompanyBrand.s39'), value: 'official_site' },
  { label: t('pages.settings.CompanyBrand.s40'), value: 'wechat' },
  { label: t('pages.settings.CompanyBrand.s41'), value: 'weibo' },
  { label: t('pages.settings.CompanyBrand.s55'), value: 'linkedin' },
  { label: t('pages.settings.CompanyBrand.s42'), value: 'other' },
]

const DEFAULT_BRAND = '#6366F1'

const emptyForm = (): BrandInfo => ({
  id: '',
  companyName: '',
  brandSlogan: '',
  brandIntro: '',
  logoUrl: '',
  portalTitle: '',
  portalSubtitle: '',
  portalBannerUrl: '',
  primaryColor: '',
  contactEmail: '',
  contactPhone: '',
  socialLinks: [],
  createdAt: '',
  updatedAt: '',
})

const formData = ref<BrandInfo>(emptyForm())
const serverSnapshot = ref<BrandInfo>(emptyForm())

/** 未保存更改检测：与上次服务端快照比较（保存/重置后自动归零） */
const isDirty = computed(
  () => JSON.stringify(formData.value) !== JSON.stringify(serverSnapshot.value),
)

/** 合法 hex 校验，避免非法色值注入预览 / 主题 */
function isValidHex(hex: string): boolean {
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(hex)
}
const primaryColorSafe = computed(() =>
  isValidHex(formData.value.primaryColor) ? formData.value.primaryColor : DEFAULT_BRAND,
)

/** 门户预览样式：主题色驱动标题/CTA/链接，banner 优先用图、否则用主题色渐变 */
const bannerStyle = computed(() => {
  if (formData.value.portalBannerUrl) {
    return { backgroundImage: `url(${formData.value.portalBannerUrl})` }
  }
  return {
    backgroundImage: `linear-gradient(135deg, ${primaryColorSafe.value}, color-mix(in srgb, ${primaryColorSafe.value} 55%, #000))`,
  }
})
const portalStyle = computed(() => ({ '--pc': primaryColorSafe.value } as Record<string, string>))

const fetchInfo = async () => {
  try {
    // 若管理后台启动时已在 main.ts 拉取过，直接复用 brand store，避免重复请求
    let info: BrandInfo
    if (brandStore.loaded && brandStore.info) {
      info = brandStore.info
    } else {
      info = await fetchBrandInfo()
      brandStore.setInfo(info)
    }
    formData.value = { ...emptyForm(), ...info }
    serverSnapshot.value = { ...info }
  } catch (e: any) {
    message.error(t('pages.settings.CompanyBrand.s56') + (e?.message || e))
  }
}

const addSocial = () => {
  formData.value.socialLinks.push({ platform: 'official_site', label: '', url: '' } as SocialLink)
}

const removeSocial = (idx: number) => {
  formData.value.socialLinks.splice(idx, 1)
}

/** n-upload 拦截默认上传，改为走自有 API；返回 false 阻止组件内置请求 */
const onBeforeLogoUpload = (data: { file: { file: File | null } }): boolean => {
  const f = data?.file?.file
  if (!f) return false
  void doUploadLogo(f)
  return false
}

const doUploadLogo = async (file: File) => {
  uploading.value = true
  try {
    const url = await uploadBrandLogo(file)
    formData.value.logoUrl = url
    // 上传仅更新表单, 需点「保存配置」才落库; 提示必须说清下一步, 避免误以为已生效
    message.success(t('pages.settings.CompanyBrand.s43'))
  } catch (e: any) {
    message.error(t('pages.settings.CompanyBrand.s57') + (e?.response?.data?.detail || e?.message || e))
  } finally {
    uploading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const payload = {
      companyName: formData.value.companyName,
      brandSlogan: formData.value.brandSlogan,
      brandIntro: formData.value.brandIntro,
      logoUrl: formData.value.logoUrl,
      portalTitle: formData.value.portalTitle,
      portalSubtitle: formData.value.portalSubtitle,
      portalBannerUrl: formData.value.portalBannerUrl,
      primaryColor: formData.value.primaryColor,
      contactEmail: formData.value.contactEmail,
      contactPhone: formData.value.contactPhone,
      socialLinks: formData.value.socialLinks.filter((l) => l.url),
    }
    const info = await updateBrandInfo(payload)
    // ★ 关键修复：「配置的内容没有被应用」——保存后同步到 brand store，
    // 主题色 / 系统名称 / Logo / 浏览器 title + favicon 全站即时生效
    brandStore.setInfo(info)
    formData.value = { ...emptyForm(), ...info }
    serverSnapshot.value = { ...info }
    message.success(t('pages.settings.CompanyBrand.s44'))
  } catch (e: any) {
    message.error(t('pages.settings.CompanyBrand.s58') + (e?.response?.data?.message || e?.message || e))
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  formData.value = { ...emptyForm(), ...serverSnapshot.value }
  message.info(t('pages.settings.CompanyBrand.s45'))
}

onMounted(() => {
  fetchInfo()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: var(--space-6);
  box-sizing: border-box;
}

.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* === 响应式双列网格（替代原单窄列，提升空间利用率）=== */
.brand-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
  align-items: start;
}
.brand-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}
@media (max-width: 960px) {
  .brand-grid { grid-template-columns: 1fr; }
}

/* === 入场动效（受控、系统合规、尊重 reduced-motion）=== */
@keyframes card-in {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.config-card {
  animation: card-in .42s cubic-bezier(.22, .61, .36, 1) both;
}
.brand-col > .config-card:nth-child(1) { animation-delay: 0s; }
.brand-col > .config-card:nth-child(2) { animation-delay: .06s; }
.brand-col > .config-card:nth-child(3) { animation-delay: .12s; }
@media (prefers-reduced-motion: reduce) {
  .config-card { animation: none; }
}

.config-card :deep(.n-card-header) {
  padding-bottom: var(--space-3);
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-hairline);
}
.config-card :deep(.n-card-header__main) {
  font-weight: 600;
  color: var(--ink);
}
.config-card :deep(.n-form-item) {
  margin-bottom: var(--space-4);
}
.config-card :deep(.n-form-item:last-child) {
  margin-bottom: 0;
}

/* === Logo 卡片 === */
.logo-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.logo-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 96px;
  padding: var(--space-3);
  border: 1px dashed var(--n-300);
  border-radius: var(--radius-md);
  background: var(--glass-bg-input);
}
.logo-preview.is-empty {
  background: transparent;
}
.logo-img {
  max-height: 80px;
  max-width: 100%;
  object-fit: contain;
}
.logo-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
/* n-upload 默认块级会把「更换 Logo / 清除」挤成两行, 强制行内排布 */
.logo-actions :deep(.n-upload) {
  display: inline-flex;
}
.logo-url-input {
  width: 100%;
}

/* === 门户预览卡 === */
.preview-card :deep(.n-card__content) { padding: var(--space-3); }
.portal-preview {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--glass-border);
  background: var(--glass-bg-card);
}
.portal-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background-size: cover;
  background-position: center;
  color: #fff;
  min-height: 88px;
}
.portal-logo {
  width: 48px;
  height: 48px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  background: var(--n-100);
  padding: 4px;
  flex-shrink: 0;
}
.portal-logo--ph {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fs-12);
  font-weight: 700;
  letter-spacing: .04em;
  background: var(--n-100);
  color: var(--ink-soft);
}
.portal-meta { min-width: 0; }
.portal-name {
  font-size: var(--fs-16);
  font-weight: 700;
  line-height: 1.3;
  text-shadow: 0 1px 4px rgba(0, 0, 0, .35);
}
.portal-slogan {
  font-size: var(--fs-12);
  opacity: .92;
  text-shadow: 0 1px 4px rgba(0, 0, 0, .35);
}
.portal-body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.portal-title {
  margin: 0;
  font-size: var(--fs-18);
  font-weight: 600;
  color: var(--pc);
  transition: color .3s ease;
}
.portal-sub {
  margin: 0;
  font-size: var(--fs-13);
  color: var(--ink-soft);
}
.portal-cta { align-self: flex-start; }
.portal-links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-1);
}
.portal-link {
  font-size: var(--fs-12);
  padding: 2px 10px;
  border: 1px solid;
  border-radius: var(--radius-pill);
}

/* === Banner 预览 === */
.banner-preview {
  margin-top: var(--space-3);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--n-300);
}
.banner-img {
  display: block;
  width: 100%;
  max-height: 200px;
  object-fit: cover;
}

/* === 主题色行 === */
.color-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.color-picker {
  width: 100%;
  max-width: 220px;
}

/* === 社交链接行（窄屏堆叠防溢出，R-103）=== */
.social-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.social-platform { width: 160px; flex-shrink: 0; }
.social-label { width: 180px; flex-shrink: 0; }
.social-url { flex: 1; min-width: 0; }
@media (max-width: 560px) {
  .social-row {
    flex-direction: column;
    align-items: stretch;
  }
  .social-platform, .social-label, .social-url { width: 100%; }
}

.field-hint {
  margin: 0;
  font-size: var(--fs-12);
  color: var(--n-400);
  line-height: 1.5;
}

/* === 底部 sticky 操作条（滚动时始终可见; 玻璃面板与全站设置页一致）=== */
.form-actions {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background: var(--glass-bg-elevated);
  backdrop-filter: blur(var(--glass-blur-panel));
  -webkit-backdrop-filter: blur(var(--glass-blur-panel));
}
.save-state {
  font-size: var(--fs-12);
  color: var(--ink-faint);
}
.save-state.is-dirty {
  color: var(--c-warning, #f59e0b);
}
</style>

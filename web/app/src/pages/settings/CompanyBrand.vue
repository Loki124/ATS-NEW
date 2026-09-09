<template>
  <div class="page-container config-container">
    <div class="page-header">
      <div>
        <h1 class="dc-title gradient-title">品牌信息管理</h1>
        <p class="dc-subtitle">维护雇主品牌文案、Logo 及招聘门户展示信息</p>
      </div>
      <n-space>
        <n-button :loading="resetting" @click="handleReset">重置</n-button>
        <n-button type="primary" class="gradient-btn" :loading="saving" @click="handleSave">保存配置</n-button>
      </n-space>
    </div>

    <div class="config-content page-body">
      <n-form ref="formRef" :model="formData" label-placement="left" :label-width="140">
        <!-- 品牌基础 -->
        <n-card title="品牌基础" class="config-card">
          <n-form-item label="公司 / 雇主名称">
            <n-input
              v-model:value="formData.companyName"
              placeholder="如：腾讯招聘 / 某某科技"
              maxlength="255"
              show-count
            />
          </n-form-item>
          <n-form-item label="品牌标语">
            <n-input
              v-model:value="formData.brandSlogan"
              placeholder="如：用户为本，科技向善"
              maxlength="255"
              show-count
            />
          </n-form-item>
          <n-form-item label="品牌文案">
            <n-input
              v-model:value="formData.brandIntro"
              type="textarea"
              placeholder="雇主品牌介绍文案，可展示在招聘门户「关于我们」等区域"
              :rows="4"
            />
          </n-form-item>
        </n-card>

        <!-- Logo -->
        <n-card title="Logo" class="config-card">
          <n-form-item label="Logo 地址">
            <n-input
              v-model:value="formData.logoUrl"
              placeholder="可访问的 Logo 图片 URL（https://...）"
            />
            <span class="switch-tip">当前仅支持填写图片 URL；上传通道后续版本开放</span>
          </n-form-item>
          <div v-if="formData.logoUrl" class="logo-preview">
            <img :src="formData.logoUrl" alt="Logo 预览" class="logo-img" />
          </div>
          <n-empty v-else description="填写 Logo 地址后可在此预览" size="small" />
        </n-card>

        <!-- 招聘门户展示 -->
        <n-card title="招聘门户展示" class="config-card">
          <n-form-item label="门户标题">
            <n-input v-model:value="formData.portalTitle" placeholder="招聘门户标题，如：加入我们" maxlength="255" />
          </n-form-item>
          <n-form-item label="门户副标题">
            <n-input v-model:value="formData.portalSubtitle" placeholder="门户副标题 / 一句话定位" maxlength="255" />
          </n-form-item>
          <n-form-item label="门户 Banner">
            <n-input v-model:value="formData.portalBannerUrl" placeholder="可访问的 Banner 图片 URL（https://...）" />
          </n-form-item>
          <div v-if="formData.portalBannerUrl" class="banner-preview">
            <img :src="formData.portalBannerUrl" alt="Banner 预览" class="banner-img" />
          </div>
          <n-form-item label="门户主题色">
            <n-color-picker
              v-model:value="formData.primaryColor"
              :show-alpha="false"
              :modes="['hex']"
              style="width: 220px"
            />
            <span class="switch-tip">用于门户品牌化着色（hex，如 #6366F1）</span>
          </n-form-item>
        </n-card>

        <!-- 联系信息 -->
        <n-card title="联系信息" class="config-card">
          <n-form-item label="招聘邮箱">
            <n-input v-model:value="formData.contactEmail" placeholder="hr@example.com" maxlength="255" />
          </n-form-item>
          <n-form-item label="招聘电话">
            <n-input v-model:value="formData.contactPhone" placeholder="如：0755-12345678" maxlength="64" />
          </n-form-item>
        </n-card>

        <!-- 社交 / 官网链接 -->
        <n-card title="社交 / 官网链接" class="config-card">
          <n-space vertical :size="12">
            <div
              v-for="(link, idx) in formData.socialLinks"
              :key="idx"
              class="social-row"
            >
              <n-select
                v-model:value="link.platform"
                :options="platformOptions"
                style="width: 160px"
                placeholder="平台"
              />
              <n-input v-model:value="link.label" placeholder="展示名称（如：官网）" style="width: 180px" />
              <n-input v-model:value="link.url" placeholder="链接地址 https://..." style="flex: 1" />
              <n-button text type="error" @click="removeSocial(idx)">移除</n-button>
            </div>
            <n-button dashed block @click="addSocial">+ 添加一条链接</n-button>
          </n-space>
        </n-card>
      </n-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NSpace, NCard, NForm, NFormItem, NInput, NColorPicker, NSelect, NEmpty, useMessage } from 'naive-ui'
import { fetchBrandInfo, updateBrandInfo, type BrandInfo, type SocialLink } from '../../api/brand'

const message = useMessage()
const saving = ref(false)
const resetting = ref(false)
const formRef = ref()

const platformOptions = [
  { label: '官网', value: 'official_site' },
  { label: '微信公众号', value: 'wechat' },
  { label: '微博', value: 'weibo' },
  { label: 'LinkedIn', value: 'linkedin' },
  { label: '其他', value: 'other' },
]

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

const fetchInfo = async () => {
  try {
    const info = await fetchBrandInfo()
    formData.value = { ...emptyForm(), ...info }
    serverSnapshot.value = { ...info }
  } catch (e: any) {
    message.error('加载品牌信息失败: ' + (e?.message || e))
  }
}

const addSocial = () => {
  formData.value.socialLinks.push({ platform: 'official_site', label: '', url: '' } as SocialLink)
}

const removeSocial = (idx: number) => {
  formData.value.socialLinks.splice(idx, 1)
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
    formData.value = { ...emptyForm(), ...info }
    serverSnapshot.value = { ...info }
    message.success('品牌信息保存成功')
  } catch (e: any) {
    message.error('保存失败: ' + (e?.response?.data?.message || e?.message || e))
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  formData.value = { ...emptyForm(), ...serverSnapshot.value }
  message.info('已还原为上次保存的内容')
}

onMounted(() => {
  fetchInfo()
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

/* 标题区固定 + 内容区自滚（与 DemandConfig/AccountSettings 同范式） */
.page-header {
  flex-shrink: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.config-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.config-card {
  border-radius: 8px;
}

.config-card :deep(.n-card-header) {
  background: var(--g1);
  border-radius: 8px 8px 0 0;
}

.config-card :deep(.n-card-header__main) {
  font-weight: 600;
}

.config-card :deep(.n-form-item) {
  margin-bottom: var(--space-4);
}

.config-card :deep(.n-form-item:last-child) {
  margin-bottom: 0;
}

.switch-tip {
  margin-left: var(--space-3);
  color: var(--n-400);
  font-size: var(--fs-12);
}

.logo-preview {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px dashed var(--n-300);
  border-radius: 8px;
  display: flex;
  justify-content: center;
  background: var(--g1);
}
.logo-img {
  max-height: 80px;
  max-width: 100%;
  object-fit: contain;
}

.banner-preview {
  margin-top: var(--space-3);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--n-300);
}
.banner-img {
  display: block;
  width: 100%;
  max-height: 200px;
  object-fit: cover;
}

.social-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
</style>

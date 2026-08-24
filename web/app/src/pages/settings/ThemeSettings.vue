<template>
  <div class="theme-settings">
    <!-- 页面标题（DESIGN.md §3 渐变标题） -->
    <div class="page-header">
      <h1 class="gradient-title page-title">主题外观</h1>
      <p class="page-subtitle">个性化品牌色与显示模式 · 改一处即全站联动</p>
    </div>

    <!-- 玻璃面板：主容器（DESIGN.md §4） -->
    <div class="glass-panel theme-panel">
      <!-- === 品牌色取色器 === -->
      <section class="theme-section">
        <div class="section-header">
          <h2 class="section-title">品牌色</h2>
          <p class="section-desc">单一输入 · 自动派生 hover/pressed/暗色变体 · 联动所有按钮/激活态/玻璃辉光</p>
        </div>

        <div class="brand-row">
          <!-- 大色块预览（用当前 brand + 渐变 + 玻璃辉光） -->
          <div class="brand-preview" :style="{ background: previewGradient }">
            <div class="brand-preview-inner">
              <span class="brand-hex">{{ brandHex.toUpperCase() }}</span>
              <span class="brand-hint">点击右侧色块修改</span>
            </div>
          </div>

          <!-- 色块输入（n-color-picker） -->
          <div class="brand-input">
            <label class="input-label">颜色值</label>
            <n-color-picker
              v-model:value="brandHex"
              :show-alpha="false"
              :swatches="swatchColors"
              :actions="['confirm']"
              size="medium"
              @confirm="onBrandConfirm"
              @complete="onBrandComplete"
            />
            <p class="input-hint">支持 HEX（如 #6366F1）/ RGB / HSL</p>
          </div>

          <!-- 推荐色快捷按钮（6 个） -->
          <div class="brand-presets">
            <label class="input-label">推荐色</label>
            <div class="preset-grid">
              <button
                v-for="preset in presets"
                :key="preset.hex"
                class="preset-swatch"
                :class="{ active: brandHex.toLowerCase() === preset.hex.toLowerCase() }"
                :style="{ background: preset.hex }"
                :title="preset.name"
                @click="applyPreset(preset.hex)"
              >
                <span class="preset-name">{{ preset.name }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 派生色预览（hover/pressed/soft/tint） -->
        <div class="derivations">
          <div class="derivation-item">
            <div class="swatch" :style="{ background: 'var(--brand)' }"></div>
            <span class="label">品牌色</span>
            <code class="value">{{ brandHex }}</code>
          </div>
          <div class="derivation-item">
            <div class="swatch" :style="{ background: 'var(--brand-hover)' }"></div>
            <span class="label">hover</span>
            <code class="value">{{ brandHoverHex }}</code>
          </div>
          <div class="derivation-item">
            <div class="swatch" :style="{ background: 'var(--brand-pressed)' }"></div>
            <span class="label">pressed</span>
            <code class="value">{{ brandPressedHex }}</code>
          </div>
          <div class="derivation-item">
            <div class="swatch" :style="{ background: 'var(--brand-soft)' }"></div>
            <span class="label">soft（12%）</span>
            <code class="value">rgba</code>
          </div>
        </div>
      </section>

      <!-- === 暗色模式 === -->
      <section class="theme-section">
        <div class="section-header">
          <h2 class="section-title">显示模式</h2>
          <p class="section-desc">浅色 / 暗色 / 跟随系统 · 偏好持久化到 localStorage</p>
        </div>

        <n-radio-group v-model:value="modeDraft" name="theme-mode" size="medium">
          <n-radio-button value="light">
            <template #default>
              <div class="mode-option">
                <n-icon :component="SunnyOutline" />
                <span>浅色</span>
              </div>
            </template>
          </n-radio-button>
          <n-radio-button value="dark">
            <template #default>
              <div class="mode-option">
                <n-icon :component="MoonOutline" />
                <span>暗色</span>
              </div>
            </template>
          </n-radio-button>
          <n-radio-button value="auto">
            <template #default>
              <div class="mode-option">
                <n-icon :component="DesktopOutline" />
                <span>跟随系统</span>
              </div>
            </template>
          </n-radio-button>
        </n-radio-group>

        <p v-if="modeDraft === 'auto'" class="mode-hint">
          当前系统主题：<strong>{{ systemPrefersDark ? '暗色' : '浅色' }}</strong>
          （<code>prefers-color-scheme: dark</code>）
        </p>
      </section>

      <!-- === 操作栏 === -->
      <section class="theme-section actions-section">
        <n-button class="btn-secondary" @click="onReset">
          <template #icon><n-icon :component="RefreshOutline" /></template>
          恢复默认
        </n-button>
        <n-button class="btn-primary" @click="onSave" :disabled="!isDirty">
          <template #icon><n-icon :component="CheckmarkOutline" /></template>
          保存
        </n-button>
      </section>

      <!-- === 预览 === -->
      <section class="theme-section">
        <div class="section-header">
          <h2 class="section-title">实时预览</h2>
          <p class="section-desc">玻璃原子组件演示（DESIGN.md §4）</p>
        </div>
        <div class="preview-grid">
          <div class="glass-card preview-card">
            <h3 class="preview-card-title">玻璃卡片</h3>
            <p class="preview-card-text">半透明白底 + 顶部高光</p>
          </div>
          <div class="preview-card-actions">
            <button class="btn-primary">主按钮</button>
            <button class="btn-secondary">次按钮</button>
            <button class="btn-ghost">幽灵按钮</button>
            <button class="btn-danger">危险按钮</button>
          </div>
          <div class="preview-tags">
            <span class="glass-tag glass-tag--brand">品牌 tag</span>
            <span class="glass-tag glass-tag--success">成功</span>
            <span class="glass-tag glass-tag--warning">警告</span>
            <span class="glass-tag glass-tag--error">错误</span>
            <span class="glass-tag glass-tag--info">信息</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useMessage } from 'naive-ui'
import {
  SunnyOutline,
  MoonOutline,
  DesktopOutline,
  RefreshOutline,
  CheckmarkOutline,
} from '@vicons/ionicons5'
import { useThemeStore, type ThemeMode } from '../../stores/theme'

const message = useMessage()
const themeStore = useThemeStore()
const { brandHex, brandHoverHex, brandPressedHex, mode: storeMode } = storeToRefs(themeStore)

// === 状态 ===
const brandHexDraft = ref(brandHex.value)
const modeDraft = ref<ThemeMode>(storeMode.value)

// 系统偏好（mode='auto' 时显示）
const systemPrefersDark = ref(false)
let mq: MediaQueryList | null = null

function updateSystemPrefersDark() {
  if (mq) systemPrefersDark.value = mq.matches
}

// === 派生 ===
const isDirty = computed(() =>
  brandHexDraft.value.toLowerCase() !== brandHex.value.toLowerCase() ||
  modeDraft.value !== storeMode.value
)

const previewGradient = computed(() => {
  // 大色块预览：用 brand + grad-a 渐变 + 玻璃辉光
  return `linear-gradient(135deg, ${brandHexDraft.value} 0%, var(--brand-grad-a) 100%)`
})

const swatchColors = [
  '#6366F1', '#0052D9', '#8B5CF6', '#EC4899',
  '#10B981', '#F59E0B', '#EF4444', '#0EA5E9',
  '#14B8A6', '#F97316', '#84CC16', '#6366F1',
]

const presets = [
  { name: '默认·靛紫', hex: '#6366F1' },
  { name: '腾讯蓝', hex: '#0052D9' },
  { name: '紫罗兰', hex: '#8B5CF6' },
  { name: '品红', hex: '#EC4899' },
  { name: '翠绿', hex: '#10B981' },
  { name: '琥珀', hex: '#F59E0B' },
]

// === 操作 ===
function onBrandConfirm(value: string) {
  brandHexDraft.value = value
}

function onBrandComplete(value: string) {
  brandHexDraft.value = value
}

function applyPreset(hex: string) {
  brandHexDraft.value = hex
}

function onSave() {
  if (!isDirty.value) return
  themeStore.setBrand(brandHexDraft.value)
  themeStore.setMode(modeDraft.value)
  message.success('主题已保存 · 全站立即生效')
}

function onReset() {
  themeStore.reset()
  brandHexDraft.value = themeStore.brandHex
  modeDraft.value = themeStore.mode
  message.info('已恢复默认主题（#6366F1 / 浅色）')
}

// === 生命周期 ===
onMounted(() => {
  if (window.matchMedia) {
    mq = window.matchMedia('(prefers-color-scheme: dark)')
    updateSystemPrefersDark()
    mq.addEventListener('change', updateSystemPrefersDark)
  }
})

onUnmounted(() => {
  if (mq) mq.removeEventListener('change', updateSystemPrefersDark)
})
</script>

<style scoped>
.theme-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}

.page-header {
  flex-shrink: 0;
}
/* P5 整改：删除 scoped .page-title 字号覆盖（review 2.6），复用全局 .page-title 26px 渐变规格 */
.page-subtitle {
  font-size: var(--text-body);
  color: var(--ink-soft);
  margin: var(--space-2) 0 0;
}

/* === 玻璃主容器 === */
.theme-panel {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  overflow: auto;
}

.theme-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.section-header { display: flex; flex-direction: column; gap: var(--space-1); }
.section-title {
  font-size: var(--text-h3);
  font-weight: 600;
  margin: 0;
  color: var(--ink);
}
.section-desc {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin: 0;
}

/* === 品牌色取色器 === */
.brand-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-4);
  align-items: start;
}
@media (max-width: 900px) {
  .brand-row { grid-template-columns: 1fr; }
}

.brand-preview {
  height: 140px;
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px var(--glow-brand), inset 0 1px 0 rgba(255, 255, 255, .4);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.brand-preview-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, .3);
}
.brand-hex {
  font-family: var(--font-mono);
  font-size: var(--text-h3);
  font-weight: 700;
  letter-spacing: 0.02em;
}
.brand-hint {
  font-size: var(--text-meta);
  opacity: 0.85;
}

.input-label {
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--ink-soft);
  margin-bottom: var(--space-2);
  display: block;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.input-hint {
  font-size: var(--text-meta);
  color: var(--ink-faint);
  margin: var(--space-2) 0 0;
}

/* === 推荐色 === */
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}
.preset-swatch {
  position: relative;
  height: 56px;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  overflow: hidden;
  padding: var(--space-1);
}
.preset-swatch:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, .15);
}
.preset-swatch.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-soft);
}
.preset-name {
  font-size: var(--text-meta);
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, .3);
  line-height: 1.2;
}

/* === 派生色预览 === */
.derivations {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--glass-bg-input);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
}
@media (max-width: 700px) {
  .derivations { grid-template-columns: repeat(2, 1fr); }
}
.derivation-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  text-align: center;
}
.swatch {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-xs);
}
.label {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  font-weight: 500;
}
.value {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
}

/* === 模式选项 === */
.mode-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.mode-hint {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  margin: var(--space-2) 0 0;
}
.mode-hint code {
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--glass-bg-input);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

/* === 操作栏 === */
.actions-section {
  flex-direction: row;
  justify-content: flex-end;
  gap: var(--space-3);
  border-top: 1px solid var(--border-hairline);
  padding-top: var(--space-4);
}

/* === 预览网格 === */
.preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}
@media (max-width: 700px) {
  .preview-grid { grid-template-columns: 1fr; }
}
.preview-card-title {
  font-size: var(--text-h4);
  font-weight: 600;
  color: var(--ink);
  margin: 0 0 var(--space-1);
}
.preview-card-text {
  font-size: var(--text-small);
  color: var(--ink-soft);
  margin: 0;
}
.preview-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.preview-tags {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>

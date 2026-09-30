<template>
  <div class="page-container">
<div class="page-body">
    <div class="page-header">
      <h1 class="page-title">{{ t('pages.settings.ScoringRules.s1') }}</h1>
      <p class="page-subtitle">{{ t('pages.settings.ScoringRules.s2') }}</p>
    </div>
    <div class="glass-panel">
      <n-empty :description="t('pages.settings.ScoringRules.s3')">
        <template #icon>
          <n-icon :component="StarOutline" :size="64" color="var(--brand)" />
        </template>
      </n-empty>
    </div>
    </div><!-- /.page-body -->
</div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { StarOutline } from '@vicons/ionicons5'
const { t } = useI18n()
</script>

<style scoped>
/* === 2026-08-24 page-header + page-body 三件套（与 AccountSettings/DemandConfig 同款）
   - 标题区固定（flex-shrink: 0）→ 配置/操作按钮始终可触达
   - 内容区自己滚（flex: 1; min-height: 0; overflow-y: auto）→ 与外层 .settings-scroll 滚职责分离
   - 结构上让 sticky header 天然占据物理空间 → 解决下方内容穿透 header 的视觉 bug === */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0;
}
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

/* === glass-panel 局部覆盖 === */
/* .glass-panel 全局无内边距（glass.css:63），本页只有一个空状态居中显示，
   显式补 16px 让 <n-empty> 离玻璃面板边缘有呼吸空间，与 .glass-card 默认 padding 一致。 */
.glass-panel {
  padding: var(--space-4);
}
</style>

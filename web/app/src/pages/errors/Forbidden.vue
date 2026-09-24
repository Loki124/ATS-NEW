<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <h1 class="err-code">403</h1>
        <span class="err-tag">{ t('pages.errors.Forbidden.s1') }</span>
      </div>
      <div class="err-right">
        <h2 class="err-title">{ t('pages.errors.Forbidden.s2') }</h2>
        <p class="err-desc">{ t('pages.errors.Forbidden.s3') }</p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">{ t('pages.errors.Forbidden.s4') }</button>
          <button class="btn btn-secondary" @click="$router.back()">{ t('pages.errors.Forbidden.s5') }</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<!-- v2 bugfix P1-B: .err-* CSS 已统一抽到 styles/glass.css（DRY 修复），组件无 scoped 样式 -->
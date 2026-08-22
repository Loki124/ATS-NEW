<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <h1 class="err-code">404</h1>
        <span class="err-tag">PAGE NOT FOUND</span>
      </div>
      <div class="err-right">
        <h2 class="err-title">您访问的页面不存在</h2>
        <p class="err-desc">页面可能已被移除、链接拼写错误，或临时无法访问。请检查 URL 或使用下方按钮回到主流程。</p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
          <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
/* v2.7 错误页双列布局 */
.err-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 60vh; padding: var(--space-6); text-align: left;
}
.err-card {
  padding: var(--space-8);
  display: grid; grid-template-columns: auto 1fr;
  gap: var(--space-8); align-items: center;
  max-width: 620px;
  border: 1.5px solid var(--glass-border-strong);
}
.err-left  { display: flex; flex-direction: column; gap: 6px; min-width: 140px; }
.err-right { display: flex; flex-direction: column; gap: var(--space-3); align-items: flex-start; }
.err-code {
  font-size: 72px; font-weight: 800; line-height: 1; margin: 0;
  letter-spacing: -.04em;
  background: linear-gradient(135deg, var(--brand) 0%,
    color-mix(in srgb, var(--brand) 40%, transparent) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  font-feature-settings: "tnum";
}
.err-tag { font-size: var(--text-meta); color: var(--ink-faint); font-weight: 600; letter-spacing: .08em; text-transform: uppercase; }
.err-title { font-size: var(--text-h2); font-weight: 700; color: var(--ink); margin: 0; line-height: 1.3; }
.err-desc  { color: var(--ink-soft); font-size: var(--text-body); margin: 0; line-height: 1.7; max-width: 36ch; }
.err-actions { display: flex; gap: var(--space-3); margin-top: var(--space-3); flex-wrap: wrap; }
@media (max-width: 560px) {
  .err-card { grid-template-columns: 1fr; gap: var(--space-5); padding: var(--space-6); }
  .err-left, .err-right { align-items: center; text-align: center; }
  .err-code { font-size: 56px; }
}
</style>
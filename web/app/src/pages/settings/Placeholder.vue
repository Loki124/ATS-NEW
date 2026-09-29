<template>
  <div class="err-page">
    <div class="glass-panel err-card">
      <div class="err-left">
        <n-icon :component="meta.iconComp" :size="56" class="placeholder-icon" />
        <span class="err-tag">PLACEHOLDER</span>
      </div>
      <div class="err-right">
        <h2 class="err-title">{{ meta.title }}</h2>
        <p class="err-desc">{{ meta.description }}</p>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
          <span class="placeholder-tag">{{ t('pages.settings.Placeholder.s1') }}</span>
          <span class="placeholder-eta">ETA: {{ meta.eta }}</span>
        </div>
        <p style="font-size:var(--text-meta);color:var(--ink-faint);margin:0;font-family:monospace">
          Issue: {{ meta.issue }} · Owner: {{ meta.owner }} · PR: {{ meta.pr }}
        </p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">{{ t('pages.settings.Placeholder.s2') }}</button>
          <button class="btn btn-secondary" @click="$router.back()">{{ t('pages.settings.Placeholder.s3') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { HandLeftOutline, DocumentTextOutline, LinkOutline, GlobeOutline, BarChartOutline, ConstructOutline } from '@vicons/ionicons5'
const { t } = useI18n()

const route = useRoute()
const META_MAP: Record<string, any> = {
  '/settings/onboarding': { iconComp: HandLeftOutline, title: t('pages.settings.Placeholder.s4'), description: t('pages.settings.Placeholder.s5'), eta: '2026-Q4', issue: 'ATS-142', owner: t('pages.settings.Placeholder.s18'), pr: '#438' },
  '/settings/approval':   { iconComp: DocumentTextOutline, title: t('pages.settings.Placeholder.s7'), description: t('pages.settings.Placeholder.s8'), eta: '2026-Q4', issue: 'ATS-143', owner: t('pages.settings.Placeholder.s18'), pr: '#439' },
  '/settings/external':   { iconComp: LinkOutline, title: t('pages.settings.Placeholder.s9'), description: t('pages.settings.Placeholder.s10'), eta: t('pages.settings.Placeholder.s11'), issue: '—', owner: '—', pr: '—' },
  '/settings/public':     { iconComp: GlobeOutline, title: t('pages.settings.Placeholder.s12'), description: t('pages.settings.Placeholder.s13'), eta: t('pages.settings.Placeholder.s11'), issue: '—', owner: '—', pr: '—' },
  '/report':              { iconComp: BarChartOutline, title: t('pages.settings.Placeholder.s14'), description: t('pages.settings.Placeholder.s15'), eta: t('pages.settings.Placeholder.s16'), issue: 'ATS-201', owner: '—', pr: '—' },
}
const meta = computed(() => {
  if (route.meta?.title) {
    return {
      iconComp: ConstructOutline,
      title: route.meta.title,
      description: (route.meta.description || '') as string,
      eta: t('pages.settings.Placeholder.s11'),
      issue: '—',
      owner: '—',
      pr: '—',
    }
  }
  return META_MAP[route.path] || { iconComp: ConstructOutline, title: t('pages.settings.Placeholder.s17'), description: '', eta: t('pages.settings.Placeholder.s11'), issue: '—', owner: '—', pr: '—' }
})
</script>

<style scoped>
/* v2 bugfix P1-B: .err-* CSS 已统一抽到 styles/glass.css（DRY 修复）
   此处仅保留占位页专属样式（.placeholder-icon / .placeholder-tag / .placeholder-eta）。 */
.placeholder-icon { font-size: 48px; background: none; -webkit-background-clip: initial; background-clip: initial; -webkit-text-fill-color: initial; color: var(--ink); font-feature-settings: normal; letter-spacing: 0; }
.placeholder-tag { display: inline-flex; align-items: center; gap: 6px; padding: var(--space-1) var(--space-3); border-radius: var(--radius-pill); background: var(--c-info-soft); color: var(--c-info); font-size: var(--text-meta); font-weight: 500; }
.placeholder-eta { font-size: var(--text-small); color: var(--ink-soft); font-family: monospace; }
</style>
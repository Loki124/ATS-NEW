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
          <span class="placeholder-tag">开发中</span>
          <span class="placeholder-eta">ETA: {{ meta.eta }}</span>
        </div>
        <p style="font-size:var(--text-meta);color:var(--ink-faint);margin:0;font-family:monospace">
          Issue: {{ meta.issue }} · Owner: {{ meta.owner }} · PR: {{ meta.pr }}
        </p>
        <div class="err-actions">
          <button class="btn btn-primary" @click="$router.replace('/dashboard')">返回工作台</button>
          <button class="btn btn-secondary" @click="$router.back()">返回上一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { HandLeftOutline, DocumentTextOutline, LinkOutline, GlobeOutline, BarChartOutline, ConstructOutline } from '@vicons/ionicons5'

const route = useRoute()
const META_MAP: Record<string, any> = {
  '/settings/onboarding': { iconComp: HandLeftOutline, title: '入职设置', description: '员工入职流程配置（部门 / 资料模板 / 流程节点 / 自动通知规则）', eta: '2026-Q4', issue: 'ATS-142', owner: '花无缺', pr: '#438' },
  '/settings/approval':   { iconComp: DocumentTextOutline, title: '审批设置', description: '审批流配置（审批人 / 节点 / 通知规则）', eta: '2026-Q4', issue: 'ATS-143', owner: '花无缺', pr: '#439' },
  '/settings/external':   { iconComp: LinkOutline, title: '生态对接', description: '生态对接配置（背调 / HRIS / OA）', eta: '待规划', issue: '—', owner: '—', pr: '—' },
  '/settings/public':     { iconComp: GlobeOutline, title: '公共设置', description: '公开页面配置（招聘门户 / 自定义字段）', eta: '待规划', issue: '—', owner: '—', pr: '—' },
  '/report':              { iconComp: BarChartOutline, title: '数据中心', description: '招聘数据报表与分析（漏斗 / 转化 / 周期 / 来源）', eta: '规划中', issue: 'ATS-201', owner: '—', pr: '—' },
}
const meta = computed(() => {
  if (route.meta?.title) {
    return {
      iconComp: ConstructOutline,
      title: route.meta.title,
      description: (route.meta.description || '') as string,
      eta: '待规划',
      issue: '—',
      owner: '—',
      pr: '—',
    }
  }
  return META_MAP[route.path] || { iconComp: ConstructOutline, title: '页面建设中', description: '', eta: '待规划', issue: '—', owner: '—', pr: '—' }
})
</script>

<style scoped>
/* v2 bugfix P1-B: .err-* CSS 已统一抽到 styles/glass.css（DRY 修复）
   此处仅保留占位页专属样式（.placeholder-icon / .placeholder-tag / .placeholder-eta）。 */
.placeholder-icon { font-size: 48px; background: none; -webkit-background-clip: initial; background-clip: initial; -webkit-text-fill-color: initial; color: var(--ink); font-feature-settings: normal; letter-spacing: 0; }
.placeholder-tag { display: inline-flex; align-items: center; gap: 6px; padding: var(--space-1) var(--space-3); border-radius: var(--radius-pill); background: var(--c-info-soft); color: var(--c-info); font-size: var(--text-meta); font-weight: 500; }
.placeholder-eta { font-size: var(--text-small); color: var(--ink-soft); font-family: monospace; }
</style>
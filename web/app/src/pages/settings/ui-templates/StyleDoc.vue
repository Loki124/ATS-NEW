<template>
  <div class="doc-stage">
    <header class="doc-head">
      <h2 class="doc-title">前端组件规范样式文档</h2>
      <p class="doc-subtitle">
        系统级前端 UI 规范的结构化全文：页面骨架 / 间距 / 颜色 / 表格 / 弹窗 / 表单 / 状态机 /
        无障碍 / 命名约束 / 新增页面检查清单。与 docs/04-ui/UI_STANDARD.md（规范全文）、
        AGENTS.md 机器约束同源；每条的渲染效果可在「规则」分类中实时演示。
      </p>
      <div class="doc-meta">
        <n-tag size="small" :bordered="false" type="success">MUST 必须遵守</n-tag>
        <n-tag size="small" :bordered="false" type="error">NEVER 禁止</n-tag>
        <n-tag size="small" :bordered="false" type="default">NOTE 说明</n-tag>
      </div>
    </header>

    <section v-for="sec in doc" :key="sec.key" class="doc-section">
      <h3 class="doc-section-title">{{ sec.title }}</h3>
      <p v-if="sec.intro" class="doc-section-intro">{{ sec.intro }}</p>
      <ul class="doc-list">
        <li v-for="(item, i) in sec.items" :key="i" class="doc-item">
          <span class="doc-badge" :class="'doc-badge--' + item.level">{{ levelLabel(item.level) }}</span>
          <span class="doc-item-text">{{ item.text }}</span>
          <code v-if="item.code" class="doc-code">{{ item.code }}</code>
        </li>
      </ul>
    </section>

    <footer class="doc-foot">
      <n-icon :component="InformationCircleOutline" class="doc-foot-icon" />
      <span>{{ DOC_SOURCE_NOTE }}</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
/**
 * StyleDoc.vue — 「样式文档」页签（2026-10-18 兵哥要求「加个页签输出前端组件规范样式文档说明」）
 *
 * 数据来自 styleGuideDoc.ts（唯一数据源）；本组件只负责渲染。
 * 与 docs/04-ui/UI_STANDARD.md、AGENTS.md、styles/glass.css 同源同步。
 */
import { InformationCircleOutline } from '@vicons/ionicons5'
import { STYLE_GUIDE_DOC as doc, DOC_SOURCE_NOTE, type DocLevel } from './styleGuideDoc'

function levelLabel(level: DocLevel): string {
  if (level === 'must') return '必须'
  if (level === 'never') return '禁止'
  return '说明'
}
</script>

<style scoped>
.doc-stage {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
}
.doc-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-hairline);
}
.doc-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
}
.doc-subtitle {
  margin: 0;
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.7;
}
.doc-meta {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.doc-section {
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-hairline);
}
.doc-section:last-of-type { border-bottom: none; }
.doc-section-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-body);
  font-weight: 500;
}
.doc-section-intro {
  margin: 0 0 var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.7;
}
.doc-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.doc-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-meta);
  line-height: 1.8;
}
.doc-badge {
  flex: none;
  margin-top: 3px;
  padding: 0 var(--space-1);
  border-radius: var(--radius-sm);
  font-size: 11px;
  line-height: 18px;
}
.doc-badge--must {
  color: var(--c-success-deep);
  background: var(--c-success-soft);
}
.doc-badge--never {
  color: var(--c-error-deep);
  background: var(--c-error-soft);
}
.doc-badge--note {
  color: var(--ink-soft);
  background: var(--border-hairline);
}
.doc-item-text { min-width: 0; color: var(--ink); }
.doc-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--border-hairline);
  color: var(--ink);
  padding: 0 4px;
  border-radius: 4px;
  margin-left: var(--space-2);
}
.doc-foot {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-hairline);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.7;
}
.doc-foot-icon {
  flex: none;
  margin-top: 4px;
}
</style>

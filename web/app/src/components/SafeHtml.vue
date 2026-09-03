<template>
  <component :is="tag" :class="$style.root" v-html="sanitized" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeHtml } from '../utils/sanitizeHtml'

/**
 * SafeHtml —— R-107 用户输入转义 (P0 安全级)
 *
 * 用法：<SafeHtml :html="announcement.body" />
 *
 * 设计目的：
 *  1. 把 `v-html` 收敛到唯一 SFC 内 → 其他业务 .vue 文件禁止再写 v-html
 *     （vue/no-v-html lint 闸门自动 catch 任何新增 v-html）
 *  2. sanitizeHtml 已通过 src/utils/__tests__/sanitizeHtml.test.ts 验证 8+ 个 XSS 向量
 *     script 标签 / iframe 标签 / a href=javascript: / span style / on* 属性 / img onerror / data: URL / SVG / form / CSS expression
 *  3. 父组件不再需要 `eslint-disable-next-line vue/no-v-html`，lint 闸门恢复
 *
 * Props:
 *  - html: 原始 HTML 字符串（来自用户/管理员可控数据）
 *  - tag:  渲染根标签，默认 'div'（业务可按需指定 'article' / 'section'）
 */
const props = withDefaults(
  defineProps<{
    html?: string | null
    tag?: string
  }>(),
  { tag: 'div' },
)

const sanitized = computed(() => sanitizeHtml(props.html))
</script>

<style module>
.root {
  /* 富文本容器默认排版（沿用 AnnouncementDetail 原 ann-detail-body 样式契约） */
  font-size: var(--text-base, 14px);
  line-height: 1.7;
  color: var(--color-text-primary, #111827);
  word-break: break-word;
}
.root :deep(p) { margin: 0 0 12px; }
.root :deep(a) { color: var(--brand-button, #6366f1); text-decoration: none; }
.root :deep(a:hover) { text-decoration: underline; }
.root :deep(strong) { font-weight: 600; }
.root :deep(em) { font-style: italic; }
.root :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: var(--color-bg-subtle, #f9fafb);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.92em;
}
.root :deep(pre) {
  background: var(--color-bg-subtle, #f9fafb);
  padding: 12px 14px;
  border-radius: 8px;
  overflow-x: auto;
}
.root :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 14px;
  border-left: 3px solid var(--color-border, #e5e7eb);
  color: var(--color-text-secondary, #6b7280);
}
.root :deep(ul),
.root :deep(ol) { padding-left: 24px; margin: 0 0 12px; }
.root :deep(li) { margin: 4px 0; }
.root :deep(table) { border-collapse: collapse; width: 100%; }
.root :deep(th),
.root :deep(td) {
  border: 1px solid var(--color-border, #e5e7eb);
  padding: 6px 10px;
  text-align: left;
}
.root :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border, #e5e7eb);
  margin: 16px 0;
}
</style>

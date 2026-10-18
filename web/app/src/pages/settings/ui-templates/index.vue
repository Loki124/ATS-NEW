<template>
  <div class="page-container ui-templates">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t('pages.settings.UiTemplates.s1') }}</h1>
        <p class="page-subtitle">{{ t('pages.settings.UiTemplates.s2') }}</p>
      </div>
    </div>

    <div class="page-body">
      <div class="glass-panel panel-shell">
        <!-- 顶部：分类导航 -->
        <div class="toolbar">
          <n-radio-group v-model:value="activeCat" size="small" class="cat-switch">
            <n-radio-button
              v-for="c in categories"
              :key="c.key"
              :value="c.key"
            >
              {{ t(c.label) }}
            </n-radio-button>
          </n-radio-group>
          <div class="spacer"></div>
          <span class="stat-line">
            <template v-if="isDoc">
              {{ t('pages.settings.UiTemplates.s15') }} {{ STYLE_GUIDE_DOC.length }}
            </template>
            <template v-else>
              {{ t('pages.settings.UiTemplates.s3') }} {{ currentTemplates.length }} ·
              {{ t('pages.settings.UiTemplates.s4') }} {{ allTemplates.length }}
            </template>
          </span>
        </div>

        <div class="tpl-body">
          <!-- 左：模板清单（样式文档页签无模板列表，右栏全宽） -->
          <nav v-if="!isDoc" class="tpl-nav">
            <button
              v-for="tpl in currentTemplates"
              :key="tpl.key"
              class="tpl-nav-item"
              :class="{ active: tpl.key === activeKey }"
              type="button"
              @click="activeKey = tpl.key"
            >
              <span class="tpl-nav-name">{{ tpl.name }}</span>
              <span class="tpl-nav-summary">{{ tpl.summary }}</span>
            </button>
          </nav>

          <!-- 右：模板详情（渲染预览 + 代码结构 + 约束 + 参考页面） -->
          <section v-if="active" class="tpl-detail">
            <header class="tpl-detail-head">
              <h2 class="tpl-detail-title">{{ active.name }}</h2>
              <p class="tpl-detail-summary">{{ active.summary }}</p>
            </header>

            <!-- 渲染预览：活代码 Demo，可直接操作 -->
            <div class="tpl-block">
              <div class="tpl-block-head">
                <span class="tpl-block-title">{{ t('pages.settings.UiTemplates.s5') }}</span>
                <n-tag size="tiny" type="success" :bordered="false">
                  {{ t('pages.settings.UiTemplates.s6') }}
                </n-tag>
              </div>
              <component :is="demoComp" />
            </div>

            <!-- 关联速查：按分类展示 -->
            <div v-if="relatedTables.length" class="tpl-block">
              <div class="tpl-block-head">
                <span class="tpl-block-title">{{ t('pages.settings.UiTemplates.s7') }}</span>
              </div>
              <div v-for="tbl in relatedTables" :key="tbl.title" class="spec-table">
                <p class="spec-table-title">{{ tbl.title }}</p>
                <ul class="spec-list">
                  <li v-for="row in tbl.rows" :key="row.key">
                    <code v-if="row.mono">{{ row.key }}</code>
                    <span v-else>{{ row.key }}</span>
                    <span class="spec-desc">{{ row.desc }}</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- 代码结构 -->
            <div class="tpl-block">
              <div class="tpl-block-head">
                <span class="tpl-block-title">{{ t('pages.settings.UiTemplates.s8') }}</span>
                <n-button size="tiny" quaternary type="primary" @click="copyCode">
                  <template #icon><n-icon :component="CopyOutline" /></template>
                  {{ t('pages.settings.UiTemplates.s9') }}
                </n-button>
              </div>
              <pre class="code-block"><code>{{ active.code }}</code></pre>
            </div>

            <!-- 约束清单 -->
            <div class="tpl-block">
              <div class="tpl-block-head">
                <span class="tpl-block-title">{{ t('pages.settings.UiTemplates.s10') }}</span>
              </div>
              <ul class="rule-list">
                <li v-for="(r, i) in active.rules" :key="i">
                  <n-icon :component="CheckmarkCircleOutline" class="rule-icon" />
                  <span>{{ r }}</span>
                </li>
              </ul>
            </div>

            <!-- 参考页面 / 例外 -->
            <div class="tpl-block">
              <div class="tpl-block-head">
                <span class="tpl-block-title">{{ t('pages.settings.UiTemplates.s11') }}</span>
              </div>
              <ul class="ref-list">
                <li v-for="(r, i) in active.references" :key="i">
                  <n-icon :component="LinkOutline" class="ref-icon" />
                  <code>{{ r }}</code>
                </li>
              </ul>
              <template v-if="active.caveats?.length">
                <p class="caveat-title">{{ t('pages.settings.UiTemplates.s12') }}</p>
                <ul class="rule-list">
                  <li v-for="(c, i) in active.caveats" :key="i">
                    <n-icon :component="AlertCircleOutline" class="caveat-icon" />
                    <span>{{ c }}</span>
                  </li>
                </ul>
              </template>
            </div>
          </section>

          <!-- 样式文档页签：直接输出规范全文 -->
          <section v-else-if="isDoc" class="tpl-detail tpl-detail--full">
            <StyleDoc />
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * UiTemplates.vue — 前端 UI 模板中心（2026-10-18 兵哥立项）
 *
 * 职责：集中管理与预览系统级前端 UI 模板，按「数据列表 / 表单 / 弹窗 / 配置项 / 组件 /
 * 规则」六类组织，另有「样式文档」页签输出规范全文。支持查看每个模板的**代码结构**
 * 与**实际渲染效果**（活代码 Demo，非静态截图）。
 *
 * 数据来源：templateRegistry.ts（模板唯一真源）+ styleGuideDoc.ts（文档唯一数据源）。
 * 本文件只负责渲染与交互，新增/修改模板规格一律改数据文件，不改此处。
 *
 * ⚠️ 分类切换用的是 radio-button 而非 select：模板分类需要一眼看到全部，
 *    属于规范中「穷举可见」的场景（枚举筛选才统一用 n-select）。
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  CopyOutline,
  CheckmarkCircleOutline,
  LinkOutline,
  AlertCircleOutline,
} from '@vicons/ionicons5'
import {
  CATEGORIES,
  TEMPLATES,
  GLOBAL_CLASSES,
  COLUMN_TIERS,
  MODAL_WIDTHS,
  templatesByCategory,
  type TemplateCategory,
  type TemplateMeta,
  type SpecRow,
} from './templateRegistry'
import { STYLE_GUIDE_DOC } from './styleGuideDoc'

import ListDemo from './demos/ListDemo.vue'
import ModalDemo from './demos/ModalDemo.vue'
import FormDemo from './demos/FormDemo.vue'
import ConfigDemo from './demos/ConfigDemo.vue'
import ComponentDemo from './demos/ComponentDemo.vue'
import RulesDemo from './demos/RulesDemo.vue'
import StyleDoc from './StyleDoc.vue'

const { t } = useI18n()
const message = useMessage()

/** 分类 → Demo 组件映射（注册表 key 与 Demo 文件一一对应） */
const DEMO_MAP: Record<string, unknown> = {
  'list-standalone': ListDemo,
  'list-embedded': ListDemo,
  'list-columns': ListDemo,
  'modal-card': ModalDemo,
  'modal-confirm': ModalDemo,
  'form-standard': FormDemo,
  'config-page': ConfigDemo,
  'component-contracts': ComponentDemo,
  'rules-playground': RulesDemo,
}

const allTemplates = TEMPLATES
const categories = CATEGORIES

// 分类与模板都同步到 URL query（?cat=list&tpl=list-standalone）：
// 便于把「某个模板的用法」直接贴给同事，也避免每次分享都要重新点一遍。
const route = useRoute()
const router = useRouter()

/** query 值是否命中注册表（防手改 URL 落到空详情） */
function resolveCat(v: unknown): TemplateCategory {
  const s = typeof v === 'string' ? v : ''
  return CATEGORIES.some(c => c.key === s) ? (s as TemplateCategory) : 'list'
}

const activeCat = ref<TemplateCategory>(resolveCat(route.query.cat))
const currentTemplates = computed(() => templatesByCategory(activeCat.value))
const isDoc = computed(() => activeCat.value === 'doc')

/** 切换分类时自动选中该类第一个模板（除非 URL 显式指定了该类模板），避免右侧空白 */
function resolveTpl(v: unknown, cat: TemplateCategory): string {
  const s = typeof v === 'string' ? v : ''
  const hit = TEMPLATES.find(t => t.key === s && t.category === cat)
  return hit?.key ?? templatesByCategory(cat)[0]?.key ?? ''
}

const activeKey = ref(resolveTpl(route.query.tpl, activeCat.value))
const active = computed<TemplateMeta | undefined>(
  () => currentTemplates.value.find(t => t.key === activeKey.value)
    ?? currentTemplates.value[0]
)
const demoComp = computed(() => (active.value ? DEMO_MAP[active.value.key] : null))

// 反向同步：用户点分类 / 点模板时回写 query（replace 不污染历史栈）
watch(activeCat, (c) => {
  if (c === 'doc') {
    router.replace({ query: { ...route.query, cat: c } })
    return
  }
  activeKey.value = resolveTpl(route.query.tpl, c)
  router.replace({ query: { ...route.query, cat: c, tpl: activeKey.value } })
})
watch(activeKey, (k) => {
  router.replace({ query: { ...route.query, tpl: k } })
})

/** 分类相关速查表：仅在对应分类展示，避免信息过载 */
const relatedTables = computed<{ title: string; rows: SpecRow[] }[]>(() => {
  switch (activeCat.value) {
    case 'list':
      return [
        { title: '列对齐四档（useTableColumns 单一真源）', rows: COLUMN_TIERS },
      ]
    case 'modal':
      return [
        { title: '弹窗宽度档位（由站内存量 20+ 种收敛）', rows: MODAL_WIDTHS },
      ]
    case 'rules':
      return [
        { title: '列对齐四档（useTableColumns 单一真源）', rows: COLUMN_TIERS },
        { title: '弹窗宽度档位（由站内存量 20+ 种收敛）', rows: MODAL_WIDTHS },
        { title: '全局基础类（glass.css 提供，页面禁止重复定义）', rows: GLOBAL_CLASSES },
      ]
    case 'component':
      return [
        { title: '全局基础类（glass.css 提供，页面禁止重复定义）', rows: GLOBAL_CLASSES },
      ]
    default:
      return []
  }
})

async function copyCode() {
  if (!active.value) return
  try {
    await navigator.clipboard.writeText(active.value.code)
    message.success(t('pages.settings.UiTemplates.s13'))
  } catch {
    message.error(t('pages.settings.UiTemplates.s14'))
  }
}
</script>

<style scoped>
/* === 页面骨架：与其他设置页一致（模型 B：header 为 page-body 兄弟节点）=== */
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.stat-line {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}

/* === 主体：左导航 + 右详情（双栏）=== */
.tpl-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--space-4);
  overflow: hidden;
}
.tpl-nav {
  flex: none;
  width: 240px;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  overflow-y: auto;
  padding-right: var(--space-1);
}
.tpl-nav-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: flex-start;
  text-align: left;
  padding: var(--space-2);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  font: inherit;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}
.tpl-nav-item:hover {
  background: var(--glass-bg-panel);
}
.tpl-nav-item.active {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.tpl-nav-name {
  font-size: var(--text-body);
  font-weight: 500;
}
.tpl-nav-summary {
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.5;
}

.tpl-detail {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.tpl-detail-head {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.tpl-detail-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
}
.tpl-detail-summary {
  margin: 0;
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}

.tpl-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.tpl-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.tpl-block-title {
  font-size: var(--text-body);
  font-weight: 500;
}

/* === 代码块：原生 pre/code，零依赖 === */
.code-block {
  margin: 0;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--border-hairline);
  border: 1px solid var(--border-hairline);
  overflow-x: auto;
  max-height: 420px;
  overflow-y: auto;
}
.code-block code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: var(--text-meta);
  line-height: 1.6;
  white-space: pre;
}

/* === 约束 / 参考清单 === */
.rule-list,
.ref-list,
.spec-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.rule-list li,
.ref-list li,
.spec-list li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-meta);
  line-height: 1.7;
}
.rule-icon,
.ref-icon {
  flex: none;
  margin-top: 3px;
  color: var(--c-success);
}
.ref-icon { color: var(--ink-soft); }
.caveat-icon {
  flex: none;
  margin-top: 3px;
  color: var(--c-warning);
}
.caveat-title {
  margin: var(--space-3) 0 var(--space-1);
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--c-warning);
}
.rule-list code,
.ref-list code,
.spec-list code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--border-hairline);
  padding: 0 4px;
  border-radius: 4px;
}
.spec-table-title {
  margin: var(--space-2) 0 var(--space-1);
  font-size: var(--text-meta);
  font-weight: 500;
  color: var(--ink-soft);
}
.spec-desc {
  color: var(--ink-soft);
  margin-left: var(--space-2);
}
</style>

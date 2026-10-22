<template>
  <div class="page-container metrics-ws">
    <!-- ========== Header ========== -->
    <div class="page-header">
      <div>
        <h1 class="ws-title">{{ t('metrics.library.title') }}</h1>
        <p class="ws-subtitle">{{ t('metrics.library.subtitle') }}</p>
      </div>
    </div>

    <!-- ========== 顶层 Tab：指标定义 / 指标模板 ========== -->
    <div class="ws-body">
      <n-tabs v-model:value="activeTab" type="line">
        <!-- ---------- Tab 1：指标定义（只读，统一视图） ---------- -->
        <n-tab-pane name="definitions" :tab="t('metrics.tab.definitions')">
          <DefinitionsTab />
        </n-tab-pane>

        <!-- ---------- Tab 2：指标模板（CRUD） ---------- -->
        <n-tab-pane name="template" :tab="t('metrics.tab.template')">
          <TemplatesTab />
        </n-tab-pane>
      </n-tabs>
    </div>

    <!-- ========== 5 个弹窗 / 抽屉（共享 useMetricsWorkspace 状态） ========== -->
    <TemplateImportModal />
    <MetricDetailDrawer />
    <TemplateFormModal />
    <TemplateAffectedRulesModal />
    <TemplateVersionHistoryDrawer />
  </div>
</template>

<script setup lang="ts">
import { onMounted, provide } from 'vue'
import { METRICS_WORKSPACE_KEY, useMetricsWorkspace } from '@/composables/useMetricsWorkspace'
import DefinitionsTab from '@/components/metrics/workspace/DefinitionsTab.vue'
import TemplatesTab from '@/components/metrics/workspace/TemplatesTab.vue'
import MetricDetailDrawer from '@/components/metrics/workspace/MetricDetailDrawer.vue'
import TemplateImportModal from '@/components/metrics/workspace/TemplateImportModal.vue'
import TemplateFormModal from '@/components/metrics/workspace/TemplateFormModal.vue'
import TemplateAffectedRulesModal from '@/components/metrics/workspace/TemplateAffectedRulesModal.vue'
import TemplateVersionHistoryDrawer from '@/components/metrics/workspace/TemplateVersionHistoryDrawer.vue'

// 单一真相源：本组件（外壳）创建组合式一次并下发，7 个子组件 inject 同一实例。
const ws = useMetricsWorkspace()
provide(METRICS_WORKSPACE_KEY, ws)

const { t, activeTab, load } = ws

// 表格高度不再由 JS 测高决定（改用 naive-ui flex-height + CSS flex 链收敛），
// 故不再需要 resize 监听与 updateTableMaxHeight 调用。
onMounted(() => {
  load()
})
</script>

<!--
  注意：原 <style scoped> 已改为非 scoped（全局）。
  拆分后 7 个子组件内部的元素不再带有本组件的 scoped 数据属性，scoped 样式无法触达子组件内部，
  故改为全局样式；类名均带 ws-/tpl-/dm-/im-/affected-/verh-/pv-/ds- 前缀，不会污染其他组件。
  :deep() 与 :global() 在全局样式下无意义，已转为普通后代/全局选择器。
-->
<style>
.metrics-ws {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ws-title {
  margin: 0;
  font-size: var(--text-h3, 20px);
  font-weight: 600;
  color: var(--ink);
}
.ws-subtitle {
  margin: 4px 0 0;
  font-size: var(--text-small, 13px);
  color: var(--ink-faint);
}
/* ===== LIFE-2 受影响规则披露弹窗 ===== */
.affected-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.affected-alert-name {
  font-weight: 600;
}
.affected-alert-count {
  opacity: 0.8;
}
.affected-group-title {
  margin-top: 4px;
  font-size: var(--text-small, 13px);
  font-weight: 600;
  color: var(--ink);
}
.affected-table td,
.affected-table th {
  padding: 4px 8px;
  font-size: var(--text-small, 13px);
  vertical-align: middle;
}
.affected-suggest-title {
  margin-top: 4px;
  font-size: var(--text-small, 13px);
  font-weight: 600;
  color: var(--ink);
}
.affected-suggest-list {
  margin: 0;
  padding-left: var(--space-4);
  color: var(--ink-faint);
  font-size: var(--text-small, 13px);
  line-height: 1.7;
}
.ws-body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 让 n-tabs 占满 ws-body，tab pane 成为 flex 列，滚动职责下放到表格区
   铁律：全程用 flex:1;min-height:0，禁止 height:100%（依赖父级确定高度、在 flex 链里会塌缩） */
.metrics-ws {
  gap: 0 !important;
}
/* 两个 Tab 组件的根节点（.ws-tab-pane-body）：必须与 .ws-table-wrap 的 flex 链连通。
   🔴 2026-10-13 兵哥反馈"数据没显示全 + 分页条不显示"的根因：
     ① 此根节点原是无样式的裸 <div>（display:block）→ .ws-table-wrap 的 flex:1 完全失效，
        按内容自然高度撑开（实测 711px）；
     ② 旧 updateTableMaxHeight 用 window.innerHeight 硬算 max-height（`innerHeight - top - 24`），
        既没扣掉分页条(40px)也没扣表头，把 .ws-pager 顶到 y=917（视口仅 900）→ 分页条渲染在可视区外。
     修法：改用 naive-ui 原生 flex-height（高度交给 CSS flex 链收敛）+ 此处补齐根节点 flex 列，
        不再依赖任何 JS 测高。 */
.ws-tab-pane-body {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}
.metrics-ws .n-tabs {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
}
.metrics-ws .n-tab-pane {
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
}
.ws-tab-header {
  flex-shrink: 0;
}
/* 🔴 flex-height 的必要配套：n-data-table 自身必须参与 flex 链并可收缩。
   缺这条时 flex-height 找不到确定高度 → 退化为只渲表头（实测 table.h=41、body 空白），
   即「数据被吃」的典型症状。min-height:0 必写：flex 子项默认 min-height:auto 会撑爆。 */
.ws-spin > .n-data-table,
.ws-spin .n-data-table {
  flex: 1 1 auto;
  min-height: 0;
}
.ws-table-wrap {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  position: relative;
}
.ws-spin {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
}
.ws-spin .n-spin-content {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

/* ===== 工具栏：搜索 + 筛选 + 计数 ===== */
.ws-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}
.ws-toolbar-grow { flex: 1 1 auto; margin-bottom: 0; }
.ws-search { flex: 1 1 260px; max-width: 420px; }
.ws-filter { flex: 0 0 160px; }
.ws-pager-count {
  margin-right: var(--space-2);
  color: var(--ink-faint);
  font-size: var(--fs-12);
  white-space: nowrap;
}
.ws-tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}
.ws-io-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.ws-hidden-file { display: none; }

/* ===== 数据表（替代卡片网格） ===== */
.ws-table {
  width: 100%;
}
/* 指标管理表格滚动条常显（2026-10-13 兵哥反馈"滚动不到底"）
 * 根因同批量操作弹窗：Naive data-table 内部 scrollbar 默认 trigger='hover'，
 * 不悬停时滑块节点不在 DOM；叠加 glass.css 的 .n-scrollbar-rail 默认 opacity:0，
 * 用户看不到滚动条、无法滚动到底。
 * 修法：两个子 Tab 的表格都加 scrollbar-props={trigger:'none'} 让滑块常驻，
 * 此处强制 rail 常显以覆盖 glass.css 悬停规范。 */
.ws-table .n-scrollbar-rail--vertical,
.ws-table .n-scrollbar-rail--horizontal {
  opacity: 1 !important;
}
.ws-cell-name {
  font-weight: 600;
  color: var(--ink);
}
/* 编号：等宽 + 弱化配色，传达「系统生成、不可改」而非手填内容 */
.ws-cell-code {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  font-size: 13px;
  letter-spacing: 0.02em;
  color: var(--ink-faint);
}
/* 详情页编号：与表格保持一致的系统感 */
.dm-code {
  font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
  letter-spacing: 0.03em;
}
.ws-inout-cell {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  flex-wrap: wrap;
}
.ws-inout-part {
  white-space: nowrap;
}
.ws-inout-sep {
  color: var(--ink-faint);
  white-space: nowrap;
}
/* 来源标记：自动生成（弱化底色）vs 手工维护（描边），一眼分清可维护性 */
.ws-origin-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 18px;
  white-space: nowrap;
}
.ws-origin-tag.is-auto {
  background: var(--c-success-soft);
  color: var(--c-success-deep);
}
.ws-origin-tag.is-manual {
  background: transparent;
  border: 1px solid var(--g4);
  color: var(--ink-faint);
}
.ws-module-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  font-size: var(--fs-12);
  color: var(--ink);
  white-space: nowrap;
}
.ws-metric-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.ws-row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: nowrap;
}

/* 空态：在表格滚动区内撑满剩余高度 */
.ws-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 auto;
  min-height: 240px;
  padding: var(--space-8) 0;
}
/* 空态里的「清除筛选」按钮（DefinitionsTab / TemplatesTab） */
.ws-empty-action {
  flex-shrink: 0;
  margin-left: var(--space-3);
}

/* ===== 共享视觉元素（详情弹窗与卡片统一） ===== */
.ws-code {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: var(--fs-12);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
  color: var(--ink);
  word-break: break-all;
}
.ws-op-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--brand-a12);
  border: 1px solid var(--brand-a22);
  color: var(--brand-text);
  white-space: nowrap;
}
.ws-enum-tag {
  font-size: var(--fs-12);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  background: var(--c-success-soft);
  border: 1px solid color-mix(in srgb, var(--c-success) 24%, transparent);
  color: var(--c-success-deep);
  white-space: nowrap;
}
.ws-ops { display: flex; flex-wrap: wrap; gap: var(--space-1); }
.ws-muted { color: var(--ink-faint); font-size: var(--text-small, 13px); }

/* 详情弹窗（redesign 2026-10-03）：技术规格书式布局 */
.dm-hero {
  position: relative;
  padding: var(--space-5);
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--brand-a12), transparent 72%);
  border: 1px solid var(--brand-a22);
  overflow: hidden;
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}
.dm-eyebrow {
  display: block;
  font-size: var(--fs-12);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--brand-text);
  font-weight: 600;
  margin-bottom: var(--space-3);
}
.dm-hero-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.dm-kind-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 8px;
  border-radius: var(--radius-pill);
  font-size: var(--fs-15);
  font-weight: 600;
  background: var(--surface);
  border: 1px solid var(--border-hairline);
}
.dm-kind-badge.is-atomic { color: var(--brand-fg); border-color: color-mix(in srgb, var(--brand) 30%, transparent); }
.dm-kind-badge.is-derived { color: var(--brand-alt-ink); border-color: color-mix(in srgb, var(--brand-grad-a) 30%, transparent); }
.dm-meta-chip {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
  padding: 4px 8px;
  border-radius: var(--radius-pill);
  background: var(--g1);
  border: 1px solid var(--border-hairline);
}
.dm-meta-k { color: var(--ink-faint); font-size: var(--fs-12); }
.dm-meta-v { color: var(--ink); font-size: var(--fs-15); font-weight: 600; }

.dm-section {
  position: relative;
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out);
  animation: wb-fade-up var(--duration-slow) var(--ease-out) both;
}
.dm-section:hover {
  border-color: color-mix(in srgb, var(--brand) 30%, transparent);
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
}
.dm-section-label {
  color: var(--ink-faint);
  font-size: var(--fs-12);
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-2);
}
/* 必填参数区用「图标 + 文字」表达强调，不画左侧色条（X-20） */
.dm-section-label--warn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--c-warning-deep);
}
.dm-source {
  display: inline-block;
  max-width: 100%;
  font-size: var(--fs-13, 13px);
}
.dm-desc {
  margin: 0;
  color: var(--ink);
  font-size: var(--text-small, 13px);
  line-height: 1.6;
}

/* 详情弹窗：参数化 Handler 的参数编辑区 */
.detail-params-block { display: flex; flex-direction: column; gap: var(--space-3); }
.detail-params-form { display: flex; flex-direction: column; gap: var(--space-2); }
.detail-param-row { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.param-label { min-width: 96px; color: var(--ink); font-size: var(--fs-13, 13px); font-weight: 500; }
.param-input { width: 220px; max-width: 100%; }
.param-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.4; }

/* 详情弹窗：只读输入参数契约 */
.detail-params-readonly { display: flex; flex-direction: column; gap: var(--space-2); }
.param-meta { color: var(--ink-soft); font-size: var(--fs-12); }
.dm-hint { color: var(--ink-faint); font-size: var(--fs-12); margin-top: var(--space-2); }

.tpl-unit-field { margin-bottom: var(--space-4); }

/* ===== 指标模板弹窗（v3.1：滚动归位 / 关闭按钮归位 / 出参单位与样例） =====
 * ⚠️ 类名铁律（naive-ui 2.44.1 实测）：
 *    header  = .n-card-header   （单横线 block 类）
 *    content = .n-card-content  （单横线 block 类）
 *    footer  = .n-card__footer  （双下划线 element 类）
 *    弹窗 teleport 到 body，且 class 直接落在卡片元素自身（.n-card.n-modal）→
 *    内部元素用全局后代选择器，不能用 .n-card 自身写法。 */
.tpl-modal {
  --tpl-mono: ui-monospace, "SFMono-Regular", "JetBrains Mono", "Cascadia Code", Menlo, Consolas, monospace;
}
/* 卡片自身：flex 列 + 高度上限；只有内容区滚动 → footer/header 恒定在卡内（按钮不再溢出弹窗） */
.tpl-modal.n-card.n-modal {
  display: flex;
  flex-direction: column;
  height: min(88vh, 860px);
  border-radius: var(--radius-lg);
}
.n-modal.tpl-modal .n-card-header {
  flex-shrink: 0;
  padding: var(--space-3) var(--space-5);
  background: linear-gradient(120deg, var(--brand-soft), transparent 60%);
  border-bottom: 1px solid var(--border-hairline);
  /* header 带背景 + 卡片 overflow:visible → 需自行补圆角，否则方角盖住卡片顶部圆角 */
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
.n-modal.tpl-modal .n-card-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0; /* 内边距统一由 .tpl-form 给，避免与全局 --modal-pad-* 叠加 */
}
.n-modal.tpl-modal .n-card__footer {
  flex-shrink: 0;
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--border-hairline);
  background: var(--surface);
  /* footer 带不透明背景 + 卡片 overflow:visible → 补底部圆角，修掉「顶部圆角、底部直角」 */
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

/* 头部 */
.tpl-head { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
.tpl-monogram {
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: var(--brand-600); color: var(--on-brand);
  box-shadow: 0 4px 12px var(--brand-a32);
}
.tpl-head-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 auto; }
.tpl-head-title { display: flex; align-items: center; gap: var(--space-2); font-size: var(--fs-16); font-weight: 700; color: var(--ink); line-height: 1.3; }
/* 弹窗头部的编号标签：等宽，与主表格编号列同一视觉语言 */
.tpl-code-tag { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); letter-spacing: 0.03em; }
.tpl-head-meta { font-family: var(--tpl-mono); font-size: var(--fs-12); color: var(--ink-faint); letter-spacing: .01em; }
/* 关闭按钮：视觉 32×32，命中区扩至 44×44（R-102） */
.tpl-close {
  position: relative;
  margin-left: auto;
  display: inline-flex; align-items: center; justify-content: center;
  width: 32px; height: 32px; flex-shrink: 0; padding: 0;
  border: 1px solid transparent; border-radius: var(--radius-sm);
  background: transparent; color: var(--ink-soft); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.tpl-close::after { content: ''; position: absolute; inset: -6px; border-radius: inherit; }
.tpl-close:hover { background: var(--g1); color: var(--ink); }
.tpl-close:disabled { opacity: .5; cursor: not-allowed; }

/* 表单主体：单一滚动容器，分区面板之间 12px 节奏 */
.tpl-form { padding: var(--space-4) var(--space-5) var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); counter-reset: tplsec; }
.tpl-fields { display: grid; grid-template-columns: 1fr 1.2fr; gap: var(--space-3) var(--space-4); }
.tpl-alltext { width: 120px; min-width: 0; }

/* 全局收紧表单项底部间距与标签间距（标签降为次要级灰） */
.tpl-form .n-form-item { margin-bottom: 0 !important; }
.tpl-form .n-form-item-feedback-wrapper { min-height: 0 !important; }
.tpl-form .n-form-item-label { padding-bottom: 2px !important; font-size: var(--fs-12); color: var(--ink-soft); }

/* 分区面板：全弹窗唯一的容器层级（内部不再嵌套边框卡片） */
.tpl-sec {
  counter-increment: tplsec;
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.tpl-sec-head { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; margin-bottom: var(--space-3); }
.tpl-sec-head::before {
  content: counter(tplsec, decimal-leading-zero);
  font-family: var(--tpl-mono);
  font-size: 11px; font-weight: 700; letter-spacing: -.02em;
  color: var(--on-brand);
  background: var(--brand-600);
  width: 20px; height: 20px; border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px var(--brand-a32);
}
.tpl-sec-title { font-size: var(--fs-13); font-weight: 600; color: var(--ink); }
.tpl-sec-unit { font-family: var(--tpl-mono); }
.tpl-sec-count { margin-left: auto; font-family: var(--tpl-mono); font-size: var(--fs-12); color: var(--brand-text); background: var(--brand-soft); padding: 1px 8px; border-radius: var(--radius-pill); font-variant-numeric: tabular-nums; }
.tpl-sec-units { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; }
.tpl-sec-static { margin-left: auto; font-family: var(--tpl-mono); color: var(--brand-text); font-weight: 600; font-size: var(--fs-12); }
/* 纯说明型分区（自由文本出参「无值域」提示）：去掉卡片边框，避免与提示文案抢视觉层级 */
.tpl-sec-note {
  background: transparent;
  border-style: dashed;
}

/* 继承信息：出参 / 单位 / 取值方式 —— 品牌浅底信息条（左侧色条标识「继承自指标定义」） */
.tpl-inherit {
  display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap;
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--brand-tint);
  border-left: 3px solid var(--brand-600);
  border-radius: var(--radius-sm);
  font-size: var(--fs-12);
}
.tpl-inherit-k { color: var(--ink-soft); }
.tpl-inherit-v { color: var(--ink); font-weight: 600; }
.tpl-inherit-strong { color: var(--brand-text); }
.tpl-inherit-sep { color: var(--ink-faint); }

/* 单位 pill（品牌选中） */
.tpl-pill {
  display: inline-flex; align-items: center;
  padding: 2px 8px; border-radius: var(--radius-pill);
  border: 1px solid var(--border-hairline); background: var(--surface);
  color: var(--ink-soft); font-size: var(--fs-12); line-height: 1.5; cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.tpl-pill:hover { border-color: var(--brand-600); color: var(--brand-text); }
.tpl-pill.is-on { background: var(--brand-600); border-color: var(--brand-600); color: var(--on-brand); font-weight: 600; }

/* 参数配置：流式单行，字段按内容宽度贴左（不再 4 等分拉散） */
.tpl-param-block { display: flex; flex-direction: column; gap: var(--space-3); }
.tpl-param-grid { display: flex; flex-wrap: wrap; align-items: flex-start; gap: var(--space-3) var(--space-6); }
.tpl-param-field { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
.tpl-param-lbl { color: var(--ink-soft); font-size: var(--fs-12); font-weight: 500; line-height: 1.4; display: flex; align-items: center; min-height: 24px; }
.tpl-param-ctl { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
.tpl-param-ctl .n-input-number { flex-shrink: 0; }
.tpl-range-num { width: 76px; }
.tpl-range-static { color: var(--ink-faint); font-size: var(--fs-12); white-space: nowrap; }
.tpl-range-sep { color: var(--ink-faint); }
.tpl-mini { width: 56px; min-width: 0; }
.tpl-alltext { width: 120px; min-width: 0; }
/* 「启用全部」：复选框与标签同行（标题行），输入框另起一行；标签行统一高度保证各列对齐 */
.tpl-param-head { display: flex; align-items: center; gap: var(--space-2); min-height: 24px; cursor: pointer; }
.tpl-all-field { min-width: 120px; }

/* 运算符：chip 流式排布（面板即容器，不再另加边框块） */
.tpl-ops-block { min-width: 0; }
.tpl-ops { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.tpl-op {
  position: relative;
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: 4px 8px;
  border: 1px solid var(--border-hairline); border-radius: var(--radius-pill);
  background: var(--surface); color: var(--ink-soft);
  cursor: pointer; user-select: none;
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.tpl-op:hover { border-color: var(--brand-600); color: var(--brand-text); }
.tpl-op.is-on { background: var(--brand-600); border-color: var(--brand-600); color: var(--on-brand); font-weight: 600; }
/* 自由文本下不可选的运算符：置灰 + 禁止 hover 高亮，具体原因走 title 提示 */
.tpl-op.is-disabled { opacity: .45; cursor: not-allowed; }
.tpl-op.is-disabled:hover { border-color: var(--border-hairline); color: var(--ink-soft); }
.tpl-op-sym { font-family: var(--tpl-mono); font-size: var(--fs-12); font-weight: 700; line-height: 1; }
.tpl-op-lbl { font-size: var(--fs-12); line-height: 1.2; white-space: nowrap; }
.tpl-op input { position: absolute; opacity: 0; width: 0; height: 0; }
.tpl-info-text { color: var(--ink-faint); font-size: var(--fs-13); padding: var(--space-2) 0; }

/* 值域配置：重复行列表（浅灰条 + 细分隔，非嵌套卡片） */
.tpl-domain-block { min-width: 0; }
.tpl-segments { display: flex; flex-direction: column; gap: var(--space-2); }
.tpl-seg-row { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--g1); border-radius: var(--radius-sm); }
.tpl-seg-tag { font-family: var(--tpl-mono); font-size: 11px; font-weight: 700; color: var(--brand-text); background: var(--brand-soft); border-radius: var(--radius-sm); padding: 2px 8px; white-space: nowrap; }
.tpl-seg-num { width: 82px; }
.tpl-unit-text { color: var(--ink-soft); font-size: var(--fs-12); }
.tpl-seg-steplbl { color: var(--ink-faint); font-size: var(--fs-12); white-space: nowrap; }
.tpl-seg-step { width: 68px; }
.tpl-seg-del { margin-left: auto; }
.tpl-add-seg { color: var(--brand-text); align-self: flex-start; }
.domain-summary { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--c-success-soft); border-radius: var(--radius-sm); font-size: var(--fs-12); color: var(--c-success-deep); }
.ds-tag { font-weight: 600; white-space: nowrap; font-family: var(--tpl-mono); }
.ds-vals { color: var(--ink-soft); line-height: 1.6; }
.tpl-seg-row.is-invalid { box-shadow: inset 0 0 0 1px var(--c-error); }
.domain-error { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-2) var(--space-3); background: var(--c-error-soft); color: var(--c-error-deep); border-radius: var(--radius-sm); font-size: var(--fs-12); line-height: 1.6; }
/* 枚举型值域 = 候选值清单（纵向标签 + 多选），与数值分段的横向行不同构 */
.tpl-enum-block { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--g1); border-radius: var(--radius-sm); }
.tpl-enum-select { width: 100%; }
/* 🔴 实体引用型值域配置块（人员 / 部门）：视觉沿用枚举块，保持弹窗内一致性 */
.tpl-entity-block { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--g1); border-radius: var(--radius-sm); }
.tpl-entity-opt-row { display: flex; align-items: center; gap: var(--space-2); }
.tpl-entity-opt-type { flex: 0 0 auto; font-size: var(--fs-13); color: var(--ink-soft); white-space: nowrap; }
.tpl-entity-opt-auto { flex: 1 1 auto; font-size: var(--fs-13); color: var(--ink); }
.tpl-entity-add-row { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.tpl-entity-add-row .tpl-add-seg { margin-bottom: 0; flex: 0 0 auto; }
.tpl-entity-draft-type { flex: 0 0 180px; }
.tpl-entity-picker { flex: 1 1 240px; min-width: 0; }
.pv-entity { display: inline-flex; min-width: 0; width: 100%; }
.tpl-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.6; }
.tpl-hint-block { display: flex; align-items: flex-start; gap: var(--space-1); }
.tpl-field-error { display: flex; align-items: center; gap: var(--space-1); color: var(--c-error-deep); font-size: var(--fs-12); line-height: 1.6; }
/* 日期值域段：区间约束比数值段信息量大（类型 + 边界 + 步进粒度），用卡片两行排布 */
.tpl-seg-card { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-2) var(--space-3); background: var(--g1); border-radius: var(--radius-sm); }
.tpl-seg-card.is-invalid { box-shadow: inset 0 0 0 1px var(--c-error); }
.tpl-seg-card-head { display: flex; align-items: center; gap: var(--space-2); }
.tpl-seg-gran { font-size: var(--fs-12); color: var(--ink-faint); }
.tpl-seg-card-row { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-2); }
.tpl-seg-lbl { font-size: var(--fs-12); color: var(--ink-soft); white-space: nowrap; }
.tpl-bound-type { width: 104px; }
.tpl-bound-date { width: 148px; }
.tpl-bound-num { width: 78px; }
.tpl-bound-unit { width: 72px; }
.tpl-seg-boundtext { font-family: var(--tpl-mono); font-size: var(--fs-12); color: var(--ink-faint); }

/* 配置预览（结果读条）：左侧品牌色条标明「这是最终产出」 */
.tpl-readout {
  padding: var(--space-3) var(--space-4);
  background: var(--brand-tint);
  border: 1px solid var(--brand-a12);
  border-left: 3px solid var(--brand-600);
  border-radius: var(--radius-sm);
}
.tpl-readout-eyebrow { font-size: 11px; font-weight: 600; letter-spacing: .02em; color: var(--brand-text); margin-bottom: var(--space-2); }
.tpl-readout-row { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: var(--space-2); }
.tpl-readout-row.no-param { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr); }
/* 🔴 实体引用型：多出「取值方式」框（指标/运算符/取值方式/对象），列数随之 +1；
   不加这条第 4 个下拉会被挤进隐式第二行、再被弹窗高度裁掉（取证截图 v3-1 踩中） */
.tpl-readout-row.with-entity { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr); }
.tpl-readout-row.with-entity.no-param { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr) auto minmax(0, 1fr); }
.pv-select { min-width: 0; width: 100%; }
/* 实体取值方式下拉：与普通 pv-select 同宽，仅额外保证 7 列栅格内不被挤破 */
.pv-entity-sel { min-width: 0; width: 100%; flex-shrink: 1; }
/* 自由文本校验值走单行输入；空值判断不收输入，仅说明 */
.pv-text { display: inline-flex; min-width: 0; width: 100%; }
.pv-input { min-width: 0; width: 100%; }
.pv-novalue { color: var(--ink-faint); font-size: var(--fs-12); white-space: nowrap; }
.pv-error { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--c-error-deep); font-size: var(--fs-12); line-height: 1.6; }
.pv-arrow { color: var(--brand-600); flex-shrink: 0; justify-self: center; font-weight: 700; }
/* 区间双值：下限 / 上限两个框并排，包在同一栅格单元内，避免撑破 7 列布局 */
.pv-range { display: flex; align-items: center; gap: var(--space-2); min-width: 0; }
.pv-range .pv-select { flex: 1 1 0; width: auto; }

/* 状态：已移入基础信息栅格，开关比输入框矮 → 顶对齐，避免下沉一格 */
.tpl-status { align-self: start; margin-bottom: 0; }
.tpl-status .n-form-item-label { height: auto; }
.tpl-footer { width: 100%; }
.tpl-footer .n-button--primary { box-shadow: 0 4px 14px var(--brand-a32); }

@media (max-width: 640px) {
  .tpl-fields { grid-template-columns: 1fr; }
  .tpl-readout-row, .tpl-readout-row.no-param { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .pv-arrow { display: none; }
}

/* LIFE-1 版本历史抽屉 */
.verh-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.verh-name { font-weight: 600; color: var(--ink); }
.verh-count { color: var(--ink-faint); font-size: var(--fs-12); white-space: nowrap; }
.verh-empty { padding: var(--space-8) 0; display: flex; justify-content: center; }
.verh-list { display: flex; flex-direction: column; gap: var(--space-3); }
.verh-card {
  padding: var(--space-3) var(--space-4);
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
}
.verh-card-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2); }
.verh-version { font-weight: 600; color: var(--ink); }
.verh-note { color: var(--ink-soft); font-size: var(--fs-12); line-height: 1.5; margin-bottom: var(--space-2); }
.verh-foot { margin-bottom: var(--space-2); }
.verh-time { color: var(--ink-faint); font-size: var(--fs-12); }
.verh-actions { display: flex; justify-content: flex-end; }
.verh-sub-label {
  color: var(--ink-faint);
  font-size: var(--fs-12);
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: var(--space-2);
}
.verh-changed { margin-bottom: var(--space-3); }
.verh-changed-empty { color: var(--ink-faint); font-size: var(--fs-12); }
.verh-snap { margin-bottom: var(--space-3); }

/* 指标模板列表 / 指标定义列表分页控件 */
.ws-pager {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding: var(--space-3) 0 0;
}

/* ===== 导入弹窗（下载模板 + 选择文件 + 导入 + 异常反馈一体化） ===== */
.im-body { display: flex; flex-direction: column; gap: var(--space-3); }
.im-row { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.im-label { color: var(--ink-soft); font-size: var(--fs-13); flex-shrink: 0; }
.im-select { flex: 1 1 200px; max-width: 260px; }
.im-hint { color: var(--ink-faint); font-size: var(--fs-12); line-height: 1.5; flex: 1 1 auto; }
.im-divider { height: 1px; background: var(--border-hairline); }
.im-file {
  color: var(--ink);
  font-size: var(--fs-13);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}
.im-file-empty { color: var(--ink-faint); }
.im-feedback { margin-top: var(--space-1); }
.im-alert .n-alert-body { align-items: flex-start; }
.im-err-title { font-size: var(--fs-13); color: var(--ink); }
.im-err-list {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  line-height: 1.6;
}
.im-dl-btn { margin-top: var(--space-2); }
.im-footer { display: flex; justify-content: flex-end; gap: var(--space-2); }

@media (max-width: 768px) {
  .tpl-section-hint { margin-left: 0; width: 100%; }
  .tpl-output-hint { margin-left: 0; width: 100%; }
  /* 窄屏：参数配置放开换行、预览降级 2×2，避免过度拥挤 */
  .tpl-range-row { flex-wrap: wrap; }
  .tpl-preview-row,
  .tpl-preview-row.no-param { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .pv-arrow { display: none; }
  .pv-then { grid-column: 1 / -1; }
}
</style>

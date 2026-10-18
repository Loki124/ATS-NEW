<template>
  <!--
    ListTemplate.vue — 设置页列表模板（乙系 · 皮肤规范 v2，2026-10-18 兵哥专项调整）

    皮肤 7 条规范（仅限本模板，不影响其他页面；全局化时把 .stpl-* 样式搬入 glass.css）：
      1. 纯色背景：分区三级纯色（页底 < 内嵌 < 面板），禁渐变、禁 backdrop 模糊
      2. 按钮无阴影：box-shadow 全清
      3. 无边框：border 全清，分区只靠背景色差异
      4. 间距 8px 对齐：--space-1/2/4/6/8（4/8/16/24/32）
      5. 按钮四态：主(实色brand)/次(浅灰)/幽灵(透明)/危险(实色error)
      6. 容器边距成对：上下、左右各自对称
      7. 图标与文字间距固定 4px（--space-1）
  -->
  <div class="stpl-root">
    <!-- 页头：与内容区间距 24px（--space-6） -->
    <div class="stpl-header">
      <div>
        <h1 class="stpl-title">角色管理</h1>
        <p class="stpl-subtitle">维护系统角色与权限码分配，变更实时生效</p>
      </div>
    </div>

    <!-- 主体：面板内上下 16px、左右 16px（成对）；面板与页头间距 24px -->
    <div class="stpl-body">
      <div class="stpl-panel">
        <!-- 工具条：与表格区间距 8px（--space-2）；左搜索/筛选 + 右操作 -->
        <div class="stpl-toolbar">
          <n-input
            v-model:value="keyword"
            class="rule-filter-search"
            clearable
            placeholder="搜索角色名称或编码"
          >
            <template #prefix><n-icon :component="SearchOutline" /></template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            class="rule-filter-select"
            clearable
            :options="statusOptions"
            placeholder="状态"
          />
          <div class="spacer"></div>
          <n-button class="stpl-btn stpl-btn--ghost" quaternary @click="refresh">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary" @click="create">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建角色
          </n-button>
        </div>

        <!-- 表格：flex 撑满，仅表体滚动 -->
        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="rows"
            :row-key="(r: DemoRow) => r.id"
            :bordered="false"
            flex-height
          >
            <template #empty>
              <n-empty :description="rows.length === 0 ? '暂无角色数据' : '没有匹配当前搜索/筛选条件的角色'" />
            </template>
          </n-data-table>
        </div>
      </div>

      <!-- 按钮四态速览：主 / 次 / 幽灵 / 危险（间距 8px） -->
      <div class="stpl-panel stpl-btn-spec">
        <p class="stpl-spec-title">按钮四态（图标与文字间距固定 4px）</p>
        <div class="stpl-btn-row">
          <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary">
            <template #icon><n-icon :component="AddOutline" /></template>
            主按钮
          </n-button>
          <n-button class="stpl-btn stpl-btn--default" quaternary>
            <template #icon><n-icon :component="RefreshOutline" /></template>
            次按钮
          </n-button>
          <n-button class="stpl-btn stpl-btn--ghost" quaternary>幽灵按钮</n-button>
          <n-button class="stpl-btn stpl-btn--danger" quaternary type="error">
            <template #icon><n-icon :component="TrashOutline" /></template>
            危险按钮
          </n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ListTemplate.vue — 设置页列表模板（乙系）的皮肤规范 v2 落地载体
 *
 * 定位：模板中心「数据列表 → 独立设置页列表」的渲染预览。结构骨架与
 * templateRegistry.ts 的 list-standalone code 一致；皮肤（纯色/无边框/
 * 无阴影/四态按钮/4px 图标间距）全部收敛在本文件 scoped 内，
 * 不碰 glass.css 全局样式、不影响任何业务页面。
 *
 * 全局推行路径（兵哥确认方案后）：把 <style> 中的 .stpl-* 令牌与覆写
 * 原样搬入 glass.css 的对应区块即可，结构零改动。
 */
import { ref, h } from 'vue'
import { NDataTable, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import { AddOutline, RefreshOutline, CreateOutline, TrashOutline, SearchOutline } from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'

const message = useMessage()

interface DemoRow {
  id: number
  code: string
  count: number
  desc: string
}

const keyword = ref('')
const statusFilter = ref<string | null>(null)
const statusOptions = [
  { label: '启用', value: 'ACTIVE' },
  { label: '停用', value: 'INACTIVE' },
]

const rows = ref<DemoRow[]>([
  { id: 1, code: 'ROLE_ADMIN', count: 42, desc: '拥有全部数据权限，可管理身份与字典配置' },
  { id: 2, code: 'ROLE_HRBP', count: 18, desc: '负责所辖部门的人事业务' },
  { id: 3, code: 'ROLE_HR', count: 12, desc: '负责需求发布与候选人推进' },
  { id: 4, code: 'ROLE_TB', count: 6, desc: '仅查看所辖团队需求与简历' },
])

const columns = [
  column({ title: '编码', key: 'code', width: 160 }, 'short'),
  column({ title: '权限码数', key: 'count', width: 100 }, 'numeric'),
  column({ title: '说明', key: 'desc', width: 320 }, 'text'),
  column({
    title: '操作', key: 'actions', width: 176, fixed: 'right',
    render: (row: DemoRow) => h(NSpace, { size: 8, wrap: false }, () => [
      h(NButton, {
        class: 'stpl-btn stpl-btn--ghost',
        quaternary: true,
        size: OP_ACTION_BUTTON_SIZE,
        onClick: () => message.info(`编辑 ${row.code}（演示）`),
      }, {
        icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
        default: () => '编辑',
      }),
      h(NButton, {
        class: 'stpl-btn stpl-btn--danger-text',
        quaternary: true,
        size: OP_ACTION_BUTTON_SIZE,
        onClick: () => message.warning(`删除 ${row.code}（演示）`),
      }, {
        icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
        default: () => '删除',
      }),
    ]),
  }, 'control'),
]

function refresh() { message.success('已刷新（演示）') }
function create() { message.info('新建角色（演示）') }
</script>

<style scoped>
/* ═══════════ 皮肤令牌：全部引用现有语义令牌，零硬编码 hex ═══════════
 * 分区三级纯色 —— 页底 < 内嵌 < 面板，靠背景色差异区分，不使用边框。 */
.stpl-root {
  --stpl-page-bg: color-mix(in srgb, var(--ink) 3%, var(--surface));
  --stpl-inset-bg: color-mix(in srgb, var(--ink) 6%, var(--surface));
  --stpl-panel-bg: var(--surface);
  --stpl-gap-page: var(--space-6);   /* 24px：区块与区块 */
  --stpl-gap-inner: var(--space-4);  /* 16px：容器内 */
  --stpl-gap-tight: var(--space-2);  /* 8px：紧密元素 */
  --stpl-icon-gap: var(--space-1);   /* 4px：按钮图标与文字 */

  background: var(--stpl-page-bg);
  display: flex;
  flex-direction: column;
  gap: var(--stpl-gap-page);
  padding: var(--stpl-gap-page);            /* 上下左右对称 24px */
  border-radius: var(--radius-lg);
}

/* 页头：无边框，与面板只用背景差异 + 间距区分 */
.stpl-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--stpl-gap-inner);
}
.stpl-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
  color: var(--ink);
}
.stpl-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}

/* 主体：卡片之间间距 24px */
.stpl-body {
  display: flex;
  flex-direction: column;
  gap: var(--stpl-gap-page);
}

/* 面板：纯色底 + 无边框 + 无阴影 + 无模糊 */
.stpl-panel {
  background: var(--stpl-panel-bg);
  border: none;
  border-radius: var(--radius-lg);
  padding: var(--stpl-gap-inner);          /* 上下左右对称 16px */
}

/* 工具条：与表格间距 8px */
.stpl-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--stpl-gap-tight);
  margin-bottom: var(--stpl-gap-tight);
}
.stpl-toolbar .spacer { flex: 1; }

/* ═══════════ 按钮四态皮肤（模板级局部，全局推行时搬入 glass.css）═══════════
 * 全部基于 naive quaternary 基底（不渲染 __border，不会被设置页全局渐变
 * 注入规则命中，特异度冲突零风险）；阴影/渐变/边框一律清除。 */
.stpl-root :deep(.stpl-btn) {
  border: none;
  box-shadow: none;
  border-radius: var(--radius-sm);
  font-weight: 400;
  --n-icon-margin: var(--stpl-icon-gap);   /* 图标与文字固定 4px */
}
/* 兜底：若 naive 以 margin 方式实现 icon 间距，直接钉死 4px */
.stpl-root :deep(.stpl-btn .n-button__icon) {
  margin-right: var(--stpl-icon-gap);
  margin-left: 0;
}
.stpl-root :deep(.stpl-btn .n-button__content) {
  margin-left: 0;
}

/* 主按钮：品牌实色底 + 白字；hover/pressed 由 brand 派生（不引用不存在的令牌） */
.stpl-root :deep(.stpl-btn--primary) {
  background: var(--brand);
  color: var(--on-brand);
}
.stpl-root :deep(.stpl-btn--primary:hover) {
  background: color-mix(in srgb, var(--on-brand) 12%, var(--brand));
  color: var(--on-brand);
}
.stpl-root :deep(.stpl-btn--primary:active) {
  background: color-mix(in srgb, var(--ink) 14%, var(--brand));
}

/* 次按钮：浅灰实底 + 主文本色（无边框） */
.stpl-root :deep(.stpl-btn--default) {
  background: var(--stpl-inset-bg);
  color: var(--ink);
}
.stpl-root :deep(.stpl-btn--default:hover) {
  background: color-mix(in srgb, var(--ink) 10%, var(--surface));
  color: var(--ink);
}

/* 幽灵按钮：透明底 + 次要文本色，hover 才显底 */
.stpl-root :deep(.stpl-btn--ghost) {
  background: transparent;
  color: var(--ink-soft);
}
.stpl-root :deep(.stpl-btn--ghost:hover) {
  background: var(--stpl-inset-bg);
  color: var(--ink);
}

/* 危险按钮：实色 error 底 + 白字 */
.stpl-root :deep(.stpl-btn--danger) {
  background: var(--c-error);
  color: var(--on-brand);
}
.stpl-root :deep(.stpl-btn--danger:hover) {
  background: var(--c-error-deep);
  color: var(--on-brand);
}
/* 行内危险文字按钮（操作列删除）：无底、红色文字，保持表格行清爽 */
.stpl-root :deep(.stpl-btn--danger-text) {
  background: transparent;
  color: var(--c-error-deep);
}
.stpl-root :deep(.stpl-btn--danger-text:hover) {
  background: var(--c-error-soft);
  color: var(--c-error-deep);
}

/* loading / disabled 态：去阴影、降透明 */
.stpl-root :deep(.stpl-btn.n-button--loading),
.stpl-root :deep(.stpl-btn.n-button--disabled) {
  box-shadow: none;
  opacity: .6;
}

/* ═══════════ 按钮四态速览区 ═══════════ */
.stpl-btn-spec {
  background: var(--stpl-inset-bg);
}
.stpl-spec-title {
  margin: 0 0 var(--stpl-gap-tight);
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
.stpl-btn-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--stpl-gap-tight);
}
</style>

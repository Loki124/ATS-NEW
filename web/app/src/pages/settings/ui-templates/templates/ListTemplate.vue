<template>
  <!--
    ListTemplate.vue — 设置页列表模板（乙系 · 皮肤规范 v2，2026-10-18 兵哥专项调整）

    皮肤 7 条规范（见 templates/button-skin.css 与 <style>，仅模板级局部，
    不影响其他页面；全局化时原样搬入 glass.css）：
      1. 纯色背景：分区三级纯色（页底 < 内嵌 < 面板），禁渐变、禁 backdrop 模糊
      2. 按钮无阴影 3. 无边框：分区只靠背景色差异
      4. 间距 8px 对齐 5. 按钮四态（独立「按钮」页签展示）
      6. 容器边距成对 7. 图标与文字间距固定 4px
    渲染效果区带完整模拟数据（6 行角色 + 空态双态切换），可直接操作。
  -->
  <div class="stpl-root">
    <!-- 页头：与内容区间距 24px（--space-6） -->
    <div class="stpl-header">
      <div>
        <h1 class="stpl-title">角色管理</h1>
        <p class="stpl-subtitle">维护系统角色与权限码分配，变更实时生效</p>
      </div>
    </div>

    <!-- 主体：面板上下 16px（成对）；面板与页头间距 24px -->
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
          <!-- 幽灵按钮：刷新 -->
          <n-button class="stpl-btn stpl-btn--ghost" quaternary @click="refresh">
            <template #icon><n-icon :component="RefreshOutline" /></template>
            刷新
          </n-button>
          <!-- 幽灵按钮：切换空态演示 -->
          <n-button class="stpl-btn stpl-btn--ghost" quaternary @click="emptyDemo = !emptyDemo">
            <template #icon><n-icon :component="EyeOutline" /></template>
            {{ emptyDemo ? '恢复数据' : '模拟空态' }}
          </n-button>
          <!-- 主按钮：本视觉区唯一 -->
          <n-button class="stpl-btn stpl-btn--primary" quaternary type="primary" @click="create">
            <template #icon><n-icon :component="AddOutline" /></template>
            新建角色
          </n-button>
        </div>

        <!-- 表格：flex 撑满面板，仅表体内部滚动 -->
        <div class="table-wrap">
          <n-data-table
            :columns="columns"
            :data="displayRows"
            :row-key="(r: DemoRow) => r.id"
            :bordered="false"
            flex-height
          >
            <template #empty>
              <n-empty :description="emptyDemo ? '暂无角色数据' : '没有匹配当前搜索/筛选条件的角色'" />
            </template>
          </n-data-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ListTemplate.vue — 设置页列表模板（乙系）的皮肤规范 v2 落地载体
 *
 * 定位：模板中心「数据列表 → 独立设置页列表」的渲染预览。
 * 结构骨架与 templateRegistry.ts 的 list-standalone code 一致；皮肤收敛在
 * templates/button-skin.css（按钮）+ 本文件 scoped（布局），
 * 不碰 glass.css 全局样式、不影响任何业务页面。
 *
 * 全局推行路径（兵哥确认方案后）：把 button-skin.css 与 .stpl-* 布局
 * 原样搬入 glass.css 即可，结构零改动。
 */
import { ref, computed, h } from 'vue'
import { NDataTable, NSpace, NButton, NIcon, useMessage } from 'naive-ui'
import {
  AddOutline,
  RefreshOutline,
  CreateOutline,
  TrashOutline,
  SearchOutline,
  EyeOutline,
} from '@vicons/ionicons5'
import { column, OP_ACTION_BUTTON_SIZE } from '@/composables/useTableColumns'
import './button-skin.css'

const message = useMessage()

interface DemoRow {
  id: number
  code: string
  count: number
  desc: string
}

const keyword = ref('')
const statusFilter = ref<string | null>(null)
const emptyDemo = ref(false)
const statusOptions = [
  { label: '启用', value: 'ACTIVE' },
  { label: '停用', value: 'INACTIVE' },
]

const allRows = ref<DemoRow[]>([
  { id: 1, code: 'ROLE_ADMIN', count: 42, desc: '拥有全部数据权限，可管理身份与字典配置' },
  { id: 2, code: 'ROLE_HRBP', count: 18, desc: '负责所辖部门的人事业务' },
  { id: 3, code: 'ROLE_HR', count: 12, desc: '负责需求发布与候选人推进' },
  { id: 4, code: 'ROLE_TB', count: 6, desc: '仅查看所辖团队需求与简历' },
  { id: 5, code: 'ROLE_INTERVIEWER', count: 9, desc: '负责面试评价与日程确认' },
  { id: 6, code: 'ROLE_FINANCE', count: 4, desc: '负责 offer 薪资审批与合同归档' },
])

/** 空态演示开 → 「暂无数据」态；关 → 有数据；搜索命中空 → 「筛选无结果」态 */
const displayRows = computed<DemoRow[]>(() => {
  if (emptyDemo.value) return []
  const kw = keyword.value.trim()
  if (!kw) return allRows.value
  return allRows.value.filter(
    r => r.code.includes(kw.toUpperCase()) || r.desc.includes(kw)
  )
})

const columns = [
  column({ title: '编码', key: 'code', width: 200 }, 'short'),
  column({ title: '权限码数', key: 'count', width: 110 }, 'numeric'),
  column({ title: '说明', key: 'desc', width: 320 }, 'text'),
  column({
    title: '操作', key: 'actions', width: 150, fixed: 'right',
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
/* ═══════════ 布局皮肤（令牌与按钮皮肤在 templates/button-skin.css 全局定义）═══ */

/* 舞台：定高 + 完整 flex 链，让 .table-wrap + flex-height 拿到确定高度
 * （缺确定高度时 naive 会把数据行压成 0 高——只渲染表头，即「看不出效果」） */
.stpl-root {
  background: var(--stpl-page-bg);
  display: flex;
  flex-direction: column;
  height: 560px;
  min-height: 0;
  gap: var(--stpl-gap-page);
  padding: var(--stpl-gap-page);            /* 上下左右对称 24px */
  border-radius: var(--radius-lg);
}

/* 页头：无边框，与面板只用背景差异 + 间距区分 */
.stpl-header {
  flex: none;
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

/* 主体：撑满剩余高度 */
.stpl-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 面板：纯色底 + 无边框 + 无阴影 + 无模糊，撑满主体 */
.stpl-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--stpl-panel-bg);
  border: none;
  border-radius: var(--radius-lg);
  padding: var(--stpl-gap-inner);          /* 上下左右对称 16px */
}

/* 工具条：与表格间距 8px */
.stpl-toolbar {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--stpl-gap-tight);
  margin-bottom: var(--stpl-gap-tight);
}
.stpl-toolbar .spacer { flex: 1; }
</style>

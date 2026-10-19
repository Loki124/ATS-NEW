<template>
  <div class="demo-stage">
    <h3 class="demo-title">可复用组件速览</h3>
    <p class="demo-desc">
      以下为已定型或建议上升为系统级模板的组件与 composable。调用方一律通过引用接入，
      禁止在页面内重复实现同类逻辑。
    </p>

    <!-- 1. StateView：七态统一状态机 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">StateView.vue — 七态统一状态机</span>
        <n-tag type="success" size="small" :bordered="false">建议强制接入</n-tag>
      </div>
      <p class="demo-block-desc">
        覆盖 loading / empty / error / partial / no-permission / offline / limit 七态，
        对应 AGENTS.md R-104、R-111 的强制要求。点击切换状态查看渲染效果。
      </p>
      <n-space :size="8" class="demo-actions">
        <n-button
          v-for="s in stateKeys"
          :key="s"
          size="small"
          :type="state === s ? 'primary' : 'default'"
          @click="state = s"
        >
          {{ s }}
        </n-button>
        <n-button size="small" quaternary type="primary" @click="retry">模拟重试</n-button>
      </n-space>
      <div class="demo-preview">
        <StateView :state="state" :on-retry="retry" />
      </div>
    </section>

    <!-- 2. DraggableList：通用拖拽排序 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">DraggableList.vue — 通用拖拽排序</span>
        <n-tag type="info" size="small" :bordered="false">零业务依赖</n-tag>
      </div>
      <p class="demo-block-desc">
        纯受控组件（modelValue + itemKey + update:modelValue），HTML5 原生 DnD，
        可直接用于流程阶段、面试轮次等排序场景，无需自写拖拽逻辑。
      </p>
      <div class="demo-preview">
        <DraggableList v-model="draggable" item-key="label">
          <template #default="{ element }">
            <div class="drag-row">
              <n-icon :component="ReorderThreeOutline" class="drag-handle" />
              <span>{{ element.label }}</span>
            </div>
          </template>
        </DraggableList>
      </div>
    </section>

    <!-- 3. useTablePagination：分页统一模板（系统唯一入口） -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">useTablePagination — 分页统一模板</span>
        <n-tag type="success" size="small" :bordered="false">24 页在用 · 系统唯一入口</n-tag>
      </div>
      <p class="demo-block-desc">
        统一外观：<b>共 N 条 │ ‹ 1 2 3 › │ [20 / 页 ▾] │ 跳至 [__]</b>。
        禁在页面里手写 <code>{ pageSize: N }</code>、自造 prefix、或自己算 itemCount ——
        每页条数与可选项由 <code>TABLE_PAGE_SIZE</code> / <code>TABLE_PAGE_SIZE_OPTIONS</code> 单一真源决定。
      </p>

      <div class="demo-pager-row">
        <div class="demo-pager-item">
          <span class="demo-pager-label">本地分页 localPagination()</span>
          <n-pagination v-bind="localPg" />
        </div>
        <div class="demo-pager-item">
          <span class="demo-pager-label">远程分页 remotePagination()</span>
          <n-pagination v-bind="remotePg" @update:page="onRemotePage" />
        </div>
      </div>

      <ul class="demo-list">
        <li v-for="r in paginationRules" :key="r.name">
          <code>{{ r.name }}</code>
          <span class="demo-list-desc">{{ r.desc }}</span>
        </li>
      </ul>
    </section>

    <!-- 4. composable 契约 -->
    <section class="demo-block">
      <div class="demo-block-head">
        <span class="demo-block-title">composable 契约 — 逻辑单一真源</span>
      </div>
      <p class="demo-block-desc">
        已定型的三个 composable 覆盖列对齐、分页与弹窗脏守卫。调用方只引用、不重写。
      </p>
      <ul class="demo-list">
        <li v-for="c in composables" :key="c.name">
          <code>{{ c.name }}</code>
          <span class="demo-list-desc">{{ c.desc }}</span>
          <n-tag size="tiny" :bordered="false" type="default">{{ c.usage }}</n-tag>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * ComponentDemo.vue — 组件模板的活代码 Demo
 *
 * 演示点：
 *   1. StateView 七态状态机（loading/empty/error/partial/no-permission/offline/limit）
 *   2. DraggableList 通用拖拽排序（纯受控、零业务依赖）
 *   3. composable 契约说明（useTableColumns / useTablePagination / useCloseGuard）
 * ⚠️ StateView 内部文案为中文硬编码且不接受 t() 注入，接入业务页前需先做 i18n 改造。
 */
import { ref, computed } from 'vue'
import { NIcon, NPagination } from 'naive-ui'
import { ReorderThreeOutline } from '@vicons/ionicons5'
import StateView from '@/components/common/StateView.vue'
import DraggableList from '@/components/DraggableList.vue'
import { localPagination, remotePagination } from '@/composables/useTablePagination'

const stateKeys = ['loading', 'empty', 'error', 'partial', 'no-permission', 'offline', 'limit'] as const
type StateKey = (typeof stateKeys)[number]
const state = ref<StateKey>('loading')
const retry = () => { state.value = 'empty' }

const draggable = ref([
  { id: 1, label: '简历筛选' },
  { id: 2, label: '技术面试' },
  { id: 3, label: 'HR 面' },
  { id: 4, label: 'Offer 审批' },
])

/** 本地分页演示：一口气 11 条，n-pagination 自行切片 */
const localPg = localPagination()

/** 远程分页演示：服务端给 itemCount，切页触发重新拉取 */
const remotePage = ref(1)
const remoteItemCount = ref(11)
const remotePg = remotePagination({
  page: remotePage,
  itemCount: remoteItemCount,
  onPageChange: () => {
    // 真实页面在此 fetch
  },
})

function onRemotePage(p: number) {
  remotePage.value = p
}

const paginationRules = [
  { name: 'localPagination(pageSize?)', desc: '客户端分页：一口气取全量，n-data-table / n-pagination 自行切片。必须用非受控的 defaultPage / defaultPageSize' },
  { name: 'remotePagination({ page, itemCount, ... })', desc: '服务端分页：page 与 itemCount 由调用方以 Ref 维护；⚠️ naive 远程分页用 itemCount（非 total）表达总数' },
  { name: 'TABLE_PAGE_SIZE = 50', desc: '统一默认每页条数，全站唯一；禁页面自定义' },
  { name: 'TABLE_PAGE_SIZE_OPTIONS', desc: '统一每页条数可选项 [10, 20, 50, 100]；禁页面私加档位' },
  { name: '禁手写约定', desc: '页面内不得出现 { pageSize: N } 字面量、自造 prefix、或直接给 n-data-table 传 pagination 对象' },
]

const composables = [
  { name: 'useTableColumns', desc: '列对齐四档工厂 + 操作列规格常量', usage: '28 页在用' },
  { name: 'useTablePagination', desc: '分页统一入口（local / remote）', usage: '24 页在用 · 系统唯一' },
  { name: 'useCloseGuard', desc: '弹窗脏数据关闭守卫', usage: '15 页在用' },
]
</script>

<style scoped>
.demo-stage {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-hairline);
  background: var(--glass-bg-panel);
}
.demo-title {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 500;
}
.demo-desc {
  margin: var(--space-1) 0 var(--space-4);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.demo-block {
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--glass-bg-panel);
  border: 1px solid var(--border-hairline);
}
.demo-block:last-child { margin-bottom: 0; }
.demo-block-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.demo-block-title {
  font-size: var(--text-body);
  font-weight: 500;
}
.demo-block-desc {
  margin: 0 0 var(--space-2);
  font-size: var(--text-meta);
  color: var(--ink-soft);
  line-height: 1.6;
}
.demo-actions { margin-bottom: var(--space-3); }
.demo-preview {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-hairline);
  min-height: 72px;
}
.drag-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  margin-bottom: var(--space-1);
  border-radius: var(--radius-md);
  background: var(--glass-bg-panel);
  border: 1px solid var(--border-hairline);
  cursor: grab;
}
.drag-row:last-child { margin-bottom: 0; }
.drag-handle { color: var(--ink-soft); }
.demo-list {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-meta);
  line-height: 2;
}
.demo-list code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--brand-text, var(--ink));
}
.demo-list-desc {
  margin-left: var(--space-2);
  color: var(--ink-soft);
}

/* 分页统一模板演示 */
.demo-pager-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-6);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-hairline);
}
.demo-pager-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.demo-pager-label {
  font-size: var(--text-meta);
  color: var(--ink-soft);
}
</style>

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

    <!-- 3. composable 契约 -->
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
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { ReorderThreeOutline } from '@vicons/ionicons5'
import StateView from '@/components/common/StateView.vue'
import DraggableList from '@/components/DraggableList.vue'

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

const composables = [
  { name: 'useTableColumns', desc: '列对齐四档工厂 + 操作列规格常量', usage: '28 页在用' },
  { name: 'useTablePagination', desc: '分页统一入口（local / remote）', usage: '24 页在用' },
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
</style>

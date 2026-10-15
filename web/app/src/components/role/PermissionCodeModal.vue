<template>
  <n-modal
    :show="show"
    preset="card"
    :title="modalTitle"
    class="perm-code-modal"
    :bordered="false"
    style="width: 880px; max-width: 94vw"
    :mask-closable="true"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="pc-body">
      <!-- 模板基础信息（原「模板管理」列表页的字段，随入口收敛并入本弹窗） -->
      <section class="pc-meta">
        <div class="pc-meta-item">
          <span class="pc-meta-label">模板编码</span>
          <code class="pc-meta-code">{{ templateCode || '—' }}</code>
        </div>
        <div class="pc-meta-item">
          <span class="pc-meta-label">来源</span>
          <span class="pc-meta-tag" :class="{ 'pc-meta-tag--sys': isSystem === 1 }">
            {{ isSystem === 1 ? '系统预置' : '自定义' }}
          </span>
        </div>
        <div class="pc-meta-item">
          <span class="pc-meta-label">权限码数量</span>
          <span class="pc-meta-count">{{ total }} 项</span>
        </div>
        <p v-if="description" class="pc-meta-desc">{{ description }}</p>
      </section>

      <!-- 权限码：模块 → 子模块 两级分组，每个子模块独立成卡，避免整模块平铺堆砌 -->
      <template v-if="tree.length">
        <section v-for="m in tree" :key="m.module" class="pc-module">
          <header class="pc-module-head">
            <span class="pc-module-title">{{ m.moduleLabel }}</span>
            <span class="pc-module-count">{{ m.total }}</span>
          </header>
          <div class="pc-cards">
            <div v-for="s in m.subModules" :key="s.code" class="pc-card">
              <div v-if="s.label" class="pc-card-head">
                <span class="pc-card-title">{{ s.label }}</span>
                <span class="pc-card-count">{{ s.items.length }}</span>
              </div>
              <ul class="pc-list">
                <li v-for="it in s.items" :key="it.code" class="pc-item">
                  <span class="pc-name" :title="it.name">{{ it.name }}</span>
                  <code class="pc-code" :title="it.code">{{ it.code }}</code>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </template>
      <n-empty v-else description="该模板暂无权限码" />
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NModal, NEmpty } from 'naive-ui'
import {
  useResourceNames,
  groupPermissionCodesBySubModule,
  type ModuleCodeTree,
} from '@/composables/useResourceNames'

const props = defineProps<{
  show: boolean
  /** 展示标题用的模板名（可选）。 */
  title?: string
  /** 待展示的权限码（英文码数组）。 */
  codes: string[]
  /** 模板编码（基础信息区展示）。 */
  templateCode?: string
  /** 模板描述（基础信息区展示，空则不占位）。 */
  description?: string
  /** 是否系统预置模板：1 = 系统预置，其余 = 自定义。 */
  isSystem?: number | null
}>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

// 复用资源名映射单例：打开时确保中文名就绪（缓存未命中按英文码兜底），
// 就绪后强制重算分组，避免先渲染成裸英文码。
const { ensureLoaded } = useResourceNames()
const tree = ref<ModuleCodeTree[]>([])

const total = computed(() => props.codes?.length ?? 0)
const modalTitle = computed(() => (props.title ? `权限码明细 · ${props.title}` : '权限码明细'))

watch(
  [() => props.show, () => props.codes],
  async ([shown]) => {
    if (!shown) return
    await ensureLoaded().catch(() => {})
    tree.value = groupPermissionCodesBySubModule(props.codes ?? [])
  },
  { immediate: true },
)
</script>

<style scoped>
/* 居中模态内的权限码明细：模块 → 子模块 两级分组，中文名为主、英文码作副文本 */
.pc-body {
  max-height: 62vh;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ===== 模板基础信息条 ===== */
.pc-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-5);
  padding: var(--space-3) var(--space-4);
  background: var(--g1);
  border: 1px solid var(--g4);
  border-radius: var(--radius-md);
}
.pc-meta-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.pc-meta-label {
  flex: none;
  font-size: 12px;
  color: var(--ink-faint);
}
.pc-meta-code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-soft);
  overflow-wrap: anywhere;
}
/* 来源徽标：中性灰为默认（自定义），系统预置走品牌透底。
   刻意不用 NTag —— naive 会把 --n-* 写成元素 inline style，类选择器打不过，只能上 !important。 */
.pc-meta-tag {
  font-size: 12px;
  line-height: 1;
  padding: 3px 8px;
  border-radius: 999px;
  color: var(--ink-soft);
  background: var(--border-hairline);
}
.pc-meta-tag--sys {
  color: var(--brand-fg);
  background: var(--brand-soft);
}
.pc-meta-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.pc-meta-desc {
  flex: 1 1 100%;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink-soft);
}

/* ===== 一级：功能模块 ===== */
.pc-module {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.pc-module-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.pc-module-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  padding: 3px 10px;
  border-left: 3px solid var(--brand);
  background: var(--brand-tint);
  border-radius: 4px;
}
.pc-module-count {
  font-size: 12px;
  line-height: 1;
  color: var(--ink-faint);
  background: var(--g1);
  border-radius: 999px;
  padding: 3px 8px;
  font-variant-numeric: tabular-nums;
}

/* ===== 二级：子模块卡片网格（边界靠「面 + 线」双通道表达）===== */
.pc-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-2);
}
.pc-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--g4);
  border-radius: var(--radius-md);
  background: var(--surface);
  overflow: hidden;
}
.pc-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 6px var(--space-3);
  background: var(--g1);
  border-bottom: 1px solid var(--border-hairline);
}
.pc-card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.pc-card-count {
  flex: none;
  font-size: 11px;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}
.pc-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}
.pc-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 4px var(--space-3);
  transition: background var(--dur-fast, 120ms) ease;
}
.pc-item:hover {
  background: var(--g1);
}
.pc-name {
  font-size: 13px;
  color: var(--ink);
  overflow-wrap: anywhere;
}
/* 英文码为副文本：单行省略，完整值走 title（避免长码把卡片撑成多行） */
.pc-code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<template>
  <div class="step1">
    <div class="step-intro">
      <n-icon :component="InformationCircleOutline" color="var(--brand)" :size="16" />
      <span>
        {{ t('reasonLibrary.wizard.intro.step1') }}
        <br />
        {{ t('reasonLibrary.wizard.catCount', { count: categories.length }).replace('{count}', String(categories.length)) }} ·
        {{ t('reasonLibrary.wizard.leafCount', { leaf: leafCount }).replace('{leaf}', String(leafCount)) }} ·
        {{ t('reasonLibrary.wizard.maxLevelLabel', { level: maxLevel }).replace('{level}', String(maxLevel || '-')) }}
      </span>
    </div>

    <div class="cat-tree">
      <div class="cat-tree-head">
        <span class="rl-cat-title">
          <n-icon :component="GitNetworkOutline" :size="14" color="var(--ink-soft)" />
          {{ t('reasonLibrary.wizard.categoryTree') }}
        </span>
        <n-button size="small" type="primary" @click="addRoot">
          <template #icon><n-icon :component="AddOutline" /></template>
          {{ t('reasonLibrary.common.addRootCategory') }}
        </n-button>
      </div>

      <div v-if="!categories.length" class="rl-cat-empty">
        <n-empty :description="t('reasonLibrary.wizard.emptyCategory')" />
      </div>

      <div v-else class="cat-rows">
        <div v-for="row in flatRows" :key="row.cat.id" class="cat-row" :class="{ 'is-leaf': row.isLeaf }">
          <span class="indent" :style="{ width: row.depth * INDENT_STEP + ICON_SLOT + 'px' }">
            <!-- 修复: 折叠按钮此前是纯装饰图标, 点击无效果; 现为可点展开/折叠 -->
            <button
              v-if="row.childCount > 0"
              class="expand-btn"
              :title="t('reasonLibrary.wizard.cat.expand')"
              :aria-expanded="!collapsedIds.has(row.cat.id)"
              @click="toggleExpand(row.cat.id)"
            >
              <n-icon
                :component="ChevronForwardOutline"
                :size="16"
                :style="{ transform: collapsedIds.has(row.cat.id) ? 'none' : 'rotate(90deg)', transition: 'transform var(--dur-fast) var(--ease-out)' }"
              />
            </button>
          </span>
          <span class="level-badge" :class="`l${row.cat.level}`">
            {{ t('reasonLibrary.wizard.catLevel', { level: row.cat.level }).replace('{level}', String(row.cat.level)) }}
          </span>
          <input
            v-if="row.cat.level <= 4"
            class="cat-name-input"
            :value="row.cat.name"
            :disabled="isReadonly(row.cat)"
            :placeholder="t('reasonLibrary.wizard.addSubCategory')"
            @change="(e: any) => updateName(row.cat.id, e.target.value)"
            @keydown.enter="(e: any) => e.target.blur()"
          />
          <label v-if="row.isLeaf" class="custom-ck">
            <input
              type="checkbox"
              :checked="row.cat.allowCustom"
              :disabled="isReadonly(row.cat)"
              @change="(e: any) => updateAllowCustom(row.cat.id, e.target.checked)"
            />
            <span>{{ t('reasonLibrary.common.supportCustom') }}</span>
          </label>
          <span v-else class="cat-count">
            {{ t('reasonLibrary.wizard.childCount', { count: row.childCount }).replace('{count}', String(row.childCount)) }}
          </span>
          <span class="spacer" />
          <div class="cat-actions">
            <n-tooltip placement="top">
              <template #trigger>
                <button class="act-icon" :disabled="!canMoveUp(row.cat)" @click="moveCat(row.cat.id, -1)">
                  <n-icon :component="ArrowUpOutline" :size="12" />
                </button>
              </template>
              <span>{{ t('reasonLibrary.wizard.cat.moveUp') }}</span>
            </n-tooltip>
            <n-tooltip placement="top">
              <template #trigger>
                <button class="act-icon" :disabled="!canMoveDown(row.cat)" @click="moveCat(row.cat.id, 1)">
                  <n-icon :component="ArrowDownOutline" :size="12" />
                </button>
              </template>
              <span>{{ t('reasonLibrary.wizard.cat.moveDown') }}</span>
            </n-tooltip>
            <n-tooltip placement="top">
              <template #trigger>
                <button
                  class="act-icon"
                  :disabled="row.cat.level >= MAX_CATEGORY_LEVEL || isReadonly(row.cat)"
                  @click="addChild(row.cat.id)"
                >
                  <n-icon :component="AddOutline" :size="12" />
                </button>
              </template>
              <span>{{ row.cat.level >= MAX_CATEGORY_LEVEL ? t('reasonLibrary.wizard.maxLevelExceed') : t('reasonLibrary.wizard.cat.addChild') }}</span>
            </n-tooltip>
            <n-tooltip placement="top">
              <template #trigger>
                <button
                  class="act-icon danger"
                  :disabled="isReadonly(row.cat)"
                  @click="removeCat(row.cat.id)"
                >
                  <n-icon :component="TrashOutline" :size="12" />
                </button>
              </template>
              <span>{{ t('reasonLibrary.wizard.cat.remove') }}</span>
            </n-tooltip>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Step1Categories (T-18)
 * - 嵌套分类树 (最多 4 级)
 * - 行内编辑名称、↑↓、+子、删除、末级勾选"支持自定义"
 * - 系统预置分类 (isSystem=true) 仅超管可改; 其他人 disabled + tooltip
 * - categories 是 wizard payload 的核心, 通过 v-model 与父组件双向绑定
 */
import { ref, computed } from 'vue'
import {
  NButton, NIcon, NEmpty, NTooltip, useDialog, useMessage,
} from 'naive-ui'
import {
  AddOutline, TrashOutline, ArrowUpOutline, ArrowDownOutline,
  ChevronForwardOutline, GitNetworkOutline, InformationCircleOutline,
} from '@vicons/ionicons5'
import type { RuleCategory } from '../../../types/reason-library'
import { MAX_CATEGORY_LEVEL } from '../../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  categories: RuleCategory[]
}>()

const emit = defineEmits<{
  (e: 'update:categories', v: RuleCategory[]): void
}>()

const message = useMessage()
const dialog = useDialog()
let idSeq = 0
function uid(prefix = 'c') {
  idSeq += 1
  return `${prefix}-${Date.now().toString(36)}-${idSeq}`
}

// ============== 计算扁平行 ==============
interface FlatRow {
  cat: RuleCategory
  depth: number
  isLeaf: boolean
  childCount: number
}

// 分类树行首缩进布局常量 (需与 CSS .expand-btn 尺寸协同)
// 每行行首槽宽 = depth * INDENT_STEP + ICON_SLOT, 其中 ICON_SLOT 恒为展开按钮预留,
// 这样即使 depth=0 (缩进为 0) 或某行没有子分类(无按钮), 各行仍共用同一条
// 「展开按钮 / L 徽标」对齐列 —— 修复展开图标与 L 徽标重叠的问题。
const INDENT_STEP = 20
const ICON_SLOT = 22

// 折叠状态 (默认全展开): collapsedIds 记录被折叠的分类
const collapsedIds = ref<Set<string>>(new Set())
function toggleExpand(id: string) {
  const next = new Set(collapsedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsedIds.value = next
}

const flatRows = computed<FlatRow[]>(() => {
  const rows: FlatRow[] = []
  function walk(pid: string | undefined, depth: number) {
    // 折叠: 非根且被折叠的节点, 其整棵子树不渲染
    if (pid !== undefined && collapsedIds.value.has(pid)) return
    const list = props.categories
      .filter((c) => (c.parentId || '') === (pid || ''))
      .sort((a, b) => a.order - b.order)
    for (const c of list) {
      const children = props.categories.filter((x) => x.parentId === c.id)
      rows.push({
        cat: c,
        depth,
        isLeaf: children.length === 0,
        childCount: children.length,
      })
      walk(c.id, depth + 1)
    }
  }
  walk(undefined, 0)
  return rows
})

const leafCount = computed(() => flatRows.value.filter((r) => r.isLeaf).length)
const maxLevel = computed(() => {
  if (!props.categories.length) return 0
  return Math.max(...props.categories.map((c) => c.level))
})

// ============== 编辑权限 ==============
// Item3/Item6: 所有可访问页面的用户均支持编辑分类 (任意层级名称可改、末级"支持自定义"勾选可配);
// 取消原先"非超管整棵树只读"的限制 — 多级分类(2/3/4 级)添加入口全面放开。
function isReadonly(_cat: RuleCategory): boolean {
  return false
}

// ============== 操作 ==============
function emit2(next: RuleCategory[]) {
  emit('update:categories', next)
}

function addRoot() {
  const next = [...props.categories]
  const order = next.filter((c) => !c.parentId).length + 1
  next.push({
    id: uid(),
    name: t('reasonLibrary.wizard.addSubCategory'),
    parentId: undefined,
    level: 1,
    order,
    allowCustom: true,
    tags: [],
  })
  emit2(next)
}

function addChild(parentId: string) {
  const parent = props.categories.find((c) => c.id === parentId)
  if (!parent) return
  if (parent.level >= MAX_CATEGORY_LEVEL) {
    message.warning(t('reasonLibrary.wizard.maxLevelExceed'))
    return
  }
  const next = [...props.categories]
  const order = next.filter((c) => c.parentId === parentId).length + 1
  next.push({
    id: uid(),
    name: t('reasonLibrary.wizard.addSubCategory'),
    parentId,
    level: (parent.level + 1) as 1 | 2 | 3 | 4,
    order,
    allowCustom: true,
    tags: [],
  })
  // 加子分类后, 父分类不再支持自定义 (与原型 + 后端语义一致)
  parent.allowCustom = false
  emit2(next)
}

function removeCat(id: string) {
  const cat = props.categories.find((c) => c.id === id)
  if (!cat) return
  // 收集 id 与所有后代 id
  const ids = new Set<string>([id])
  let grew = true
  while (grew) {
    grew = false
    for (const c of props.categories) {
      if (c.parentId && ids.has(c.parentId) && !ids.has(c.id)) {
        ids.add(c.id)
        grew = true
      }
    }
  }
  const subCount = ids.size - 1
  dialog.warning({
    title: t('reasonLibrary.common.confirmDelete'),
    content: t('reasonLibrary.wizard.deleteCategory', { name: cat.name, count: subCount })
      .replace('{name}', cat.name)
      .replace('{count}', String(subCount)),
    positiveText: t('reasonLibrary.common.confirm'),
    negativeText: t('reasonLibrary.common.cancel'),
    onPositiveClick: () => {
      emit2(props.categories.filter((c) => !ids.has(c.id)))
    },
  })
}

function updateName(id: string, name: string) {
  const cat = props.categories.find((c) => c.id === id)
  if (!cat) return
  const trimmed = name.trim()
  if (!trimmed) return
  cat.name = trimmed
  // 触发响应式更新 (引用类型直接改不行, 复制浅拷贝)
  emit2([...props.categories])
}

function updateAllowCustom(id: string, checked: boolean) {
  const cat = props.categories.find((c) => c.id === id)
  if (!cat) return
  cat.allowCustom = checked
  emit2([...props.categories])
}

function moveCat(id: string, dir: -1 | 1) {
  const cat = props.categories.find((c) => c.id === id)
  if (!cat) return
  const sibs = props.categories
    .filter((c) => (c.parentId || '') === (cat.parentId || ''))
    .sort((a, b) => a.order - b.order)
  const idx = sibs.findIndex((c) => c.id === id)
  const tgt = idx + dir
  if (tgt < 0 || tgt >= sibs.length) return
  // 交换数组位置后重编 order 1..n — 修复 order 重复/空洞导致的『排序不生效』
  const arr = [...sibs]
  ;[arr[idx], arr[tgt]] = [arr[tgt], arr[idx]]
  arr.forEach((c, i) => { c.order = i + 1 })
  emit2([...props.categories])
}

function canMoveUp(cat: RuleCategory): boolean {
  const sibs = props.categories
    .filter((c) => (c.parentId || '') === (cat.parentId || ''))
    .sort((a, b) => a.order - b.order)
  return sibs[0]?.id !== cat.id
}
function canMoveDown(cat: RuleCategory): boolean {
  const sibs = props.categories
    .filter((c) => (c.parentId || '') === (cat.parentId || ''))
    .sort((a, b) => a.order - b.order)
  return sibs[sibs.length - 1]?.id !== cat.id
}
</script>

<style scoped>
.step1 { display: flex; flex-direction: column; gap: var(--space-3); height: 100%; }

.step-intro {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.6;
}
.step-intro b { color: var(--brand); font-weight: 600; }

.cat-tree {
  /* 去除全局 .glass-card 带来的半透明灰底 (rgba(255,255,255,.62)) → 正常白底 */
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.cat-tree-head {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border-bottom: 1px solid var(--border-hairline);
  flex-shrink: 0;
}
.rl-cat-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink-soft);
}
.rl-cat-empty {
  padding: var(--space-5);
}
.cat-rows {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.cat-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-hairline);
  transition: background var(--duration-fast) var(--ease-out);
}
.cat-row:last-child { border-bottom: none; }
.cat-row:hover { background: var(--brand-tint); }
.cat-row.is-leaf { background: transparent; }
.cat-row .indent {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  /* 行首槽 = depth*20 缩进 + 22px 图标位 (见 script INDENT_STEP/ICON_SLOT);
     flex-end 让展开按钮贴住图标位右缘, 从而各层级/有无子分类的行共用同一条
     对齐列 —— 避免按钮溢出窄槽压到右侧 L 徽标 */
  justify-content: flex-end;
  color: var(--ink-faint);
}
.level-badge {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  padding: 1px 6px;
  flex-shrink: 0;
  background: var(--g1);
  color: var(--ink-soft);
}
.level-badge.l1 { background: var(--brand-soft); color: var(--brand); }
.level-badge.l2 { background: var(--c-success-soft); color: var(--c-success-deep); }
.level-badge.l3 { background: rgba(139, 92, 246, .12); color: #6d28d9; }
.level-badge.l4 { background: var(--brand-warm-soft); color: var(--brand-warm-deep); }

.cat-name-input {
  border: 1px solid transparent;
  border-bottom: 1px dashed var(--border-hairline);
  background: transparent;
  font-size: var(--fs-13);
  color: var(--ink);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  flex: 0 1 240px;
  min-width: 0;
  transition: all var(--duration-fast) var(--ease-out);
}
.cat-name-input:hover { border-bottom-color: var(--brand); background: #fff; }
.cat-name-input:focus {
  outline: none;
  border: 1px solid var(--brand);
  border-bottom-style: solid;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, .12);
}
.cat-name-input:disabled { color: var(--ink-faint); cursor: not-allowed; }

.cat-count {
  font-size: var(--fs-11);
  color: var(--ink-faint);
  flex-shrink: 0;
}
.spacer { flex: 1; }
.custom-ck {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-12);
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}
.custom-ck input {
  appearance: none;
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--border-hairline, #c4c8d4);
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  position: relative;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out);
}
.custom-ck input:checked {
  background: var(--brand);
  border-color: var(--brand);
}
.custom-ck input:checked::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 1.5px;
  width: 4px;
  height: 9px;
  border: solid #fff;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}
.custom-ck input:disabled { cursor: not-allowed; opacity: .5; }

.expand-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border-hairline, rgba(15, 23, 42, .08));
  background: transparent;
  border-radius: 5px;
  cursor: pointer;
  color: var(--ink-soft);
  flex-shrink: 0;
}
.expand-btn:hover { background: var(--brand-tint, rgba(99,102,241,.1)); color: var(--brand); }
.cat-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-out);
  flex-shrink: 0;
}
.cat-row:hover .cat-actions { opacity: 1; }

.act-icon {
  border: none;
  background: none;
  color: var(--ink-soft);
  font-size: var(--fs-11);
  cursor: pointer;
  padding: 4px 7px;
  border-radius: 5px;
  transition: all var(--duration-fast) var(--ease-out);
}
.act-icon:hover:not(:disabled) { background: var(--brand-tint); color: var(--brand); }
.act-icon.danger:hover:not(:disabled) { background: var(--c-error-soft); color: var(--c-error); }
.act-icon:disabled { color: var(--ink-faint); opacity: .4; cursor: not-allowed; }
</style>

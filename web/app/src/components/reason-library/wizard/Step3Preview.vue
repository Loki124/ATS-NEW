<template>
  <div class="step3">
    <!-- ============ 模块一: 原因标签 (合并单元格式卡片网格, 零表格元素) ============ -->
    <div class="rl-preview-module">
      <div class="rl-mod-head">
        <h3>{{ t('reasonLibrary.wizard.preview.moduleTagsTitle') }}</h3>
        <span v-if="sceneName" class="rl-scene">{{ sceneName }}</span>
        <span
          v-if="maxSelectable > 0"
          class="rl-mod-limit"
          :class="{ full: limitReached }"
        >{{ t('reasonLibrary.wizard.preview.selectLimit', { count: selectedTagIds.size, max: maxSelectable }) }}</span>
      </div>

      <div v-if="!layout.cells.length" class="rl-empty">{{ t('reasonLibrary.wizard.preview.empty') }}</div>

      <!--
        视觉上还原电子表格的「合并单元格」排布:
        - 分类单元是纯卡片 <div>, 通过 grid-column / grid-row 的 span 跨列或跨行;
        - 末级分类单元向右延展到最深层级, 形成跨列合并; 有子级的分类向下跨越其子孙所占行, 形成跨行合并;
        - 尺寸错落 + 小间距 + 圆角, 使相邻单元连成一块, 产生「合并块」的连通感。
        底层为 CSS Grid + 卡片, 全组件未使用 <table> / <tr> / <td> 等任何表格元素。
      -->
      <div v-else class="rl-merge" :style="gridStyle">
        <!-- 分类单元 (按层级与子树范围跨行/跨列) -->
        <div
          v-for="cell in layout.cells"
          :key="cell.key"
          class="rl-cell"
          :class="{ 'is-leaf': cell.isLeaf, 'is-wide': cell.isWide }"
          :style="cellStyle(cell)"
        >
          {{ cell.name }}
        </div>

        <!-- 标签单元: 每个末级分类一行, 同类原因标签在此聚合排列 -->
        <div
          v-for="row in layout.rows"
          :key="row.catId"
          class="rl-tags"
          :style="rowStyle(row)"
        >
          <span v-if="!row.tags.length && !row.allowCustom" class="rl-tags-empty">—</span>
          <span
            v-for="tag in row.tags"
            :key="tag.id"
            class="rl-tag"
            :class="{
              selected: selectedTagIds.has(tag.id),
              disabled: !selectedTagIds.has(tag.id) && limitReached,
            }"
            @click="toggleTag(tag.id)"
          >
            <n-icon v-if="selectedTagIds.has(tag.id)" :component="CheckmarkOutline" :size="11" class="rl-tag-check" />
            {{ tag.name }}
          </span>
          <template v-if="row.allowCustom">
            <input
              v-if="editingOther[row.catId]"
              v-focus
              class="rl-other-input"
              :value="otherInputs[row.catId] || ''"
              :placeholder="t('reasonLibrary.wizard.preview.otherPlaceholder')"
              @input="(e: any) => onOtherInput(row.catId, (e.target as HTMLInputElement).value)"
              @keydown.enter="commitOther(row.catId)"
              @blur="commitOther(row.catId)"
            />
            <span
              v-else-if="otherInputs[row.catId]"
              class="rl-tag other-filled"
              @click="editOtherAgain(row.catId)"
            >{{ otherInputs[row.catId] }}</span>
            <span v-else class="rl-tag other" @click="onOtherClick(row.catId)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
          </template>
        </div>
      </div>
    </div>

    <!-- ============ 模块二: 详细原因 (多行文本框) ============ -->
    <div class="rl-preview-module">
      <div class="rl-mod-head">
        <h3>{{ t('reasonLibrary.wizard.preview.moduleDetailTitle') }}</h3>
      </div>
      <n-input
        v-model:value="detailReason"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 8 }"
        :placeholder="t('reasonLibrary.wizard.preview.detailPlaceholder')"
        class="rl-detail-input"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Step3Preview (业务方原因选择弹窗预览 / 模拟)
 *
 * 布局 (需求 2026-09-21 修订为「合并单元格式」卡片网格):
 * - 页面分为两个模块: ① 原因标签 (合并单元格式卡片网格) ② 详细原因 (多行文本框)
 * - 分类单元用 CSS Grid 的 grid-row / grid-column span 模拟电子表格的「合并单元格」:
 *     · 有子级的分类 → 向下跨越其子树占用的全部末级行 (跨行合并)
 *     · 末级分类     → 向右延展到最深层级所在列 (跨列合并)
 *   两者组合产生尺寸错落、彼此连通的合并块观感。
 * - 底层全部是卡片 div, 未使用任何 <table> / <tr> / <td> 元素 (需求硬约束)。
 * - 「其他」入口由末级分类的 allowCustom 控制 (终端用户态), 与本组件的管理员视角无关。
 * - 原因标签可勾选: 已选条数达到 maxSelectableTags (规则配置, 0=不限制) 时, 未选项禁用。
 *
 * 数据来源: wizard.categories + wizard.allTags + wizard.maxSelectableTags (仅读模拟)。
 */
import { computed, reactive, ref } from 'vue'
import { NInput, NIcon } from 'naive-ui'
import { CheckmarkOutline } from '@vicons/ionicons5'
import type { ReasonTag, RuleCategory, WizardPayload } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'

const props = defineProps<{
  wizard: WizardPayload
  allTags: ReasonTag[]
}>()

/** 一个分类单元在网格中的位置与跨度 (等价于合并单元格的锚点 + rowspan/colspan) */
interface MergeCell {
  key: string
  name: string
  col: number
  colSpan: number
  row: number
  rowSpan: number
  isLeaf: boolean
  isWide: boolean
}
/** 一个末级分类对应的「标签单元」行 */
interface TagRow {
  catId: string
  row: number
  tags: ReasonTag[]
  allowCustom: boolean
}

const selectedTagIds = ref<Set<string>>(new Set())
const detailReason = ref('')

const maxSelectable = computed<number>(() => {
  const m = props.wizard.maxSelectableTags
  return typeof m === 'number' && m > 0 ? m : 0
})
const limitReached = computed(() => maxSelectable.value > 0 && selectedTagIds.value.size >= maxSelectable.value)

const sceneName = computed(() => props.wizard.scenes?.[0] || '')

function toggleTag(id: string) {
  const next = new Set(selectedTagIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    if (limitReached.value) return // 已达上限, 不再增加 (静默, 视觉上已 disabled)
    next.add(id)
  }
  selectedTagIds.value = next
}

// ============= 末级「其他」自定义输入 =============
const editingOther = reactive<Record<string, boolean>>({})
const otherInputs = reactive<Record<string, string>>({})

function onOtherClick(id: string) {
  editingOther[id] = true
}
function onOtherInput(id: string, val: string) {
  otherInputs[id] = val
}
function commitOther(id: string) {
  const v = (otherInputs[id] ?? '').trim()
  if (!v) otherInputs[id] = ''
  editingOther[id] = false
}
function editOtherAgain(id: string) {
  editingOther[id] = true
}

// 进入编辑态时自动聚焦输入框
const vFocus = {
  mounted: (el: HTMLElement) => el.focus(),
}

// ============= 合并单元格式网格: 两遍扫描计算落位 =============
const layout = computed<{ cells: MergeCell[]; rows: TagRow[]; maxDepth: number }>(() => {
  const cats = props.wizard.categories || []
  const byParent = new Map<string, RuleCategory[]>()
  cats.forEach((c) => {
    const pid = c.parentId || ''
    if (!byParent.has(pid)) byParent.set(pid, [])
    byParent.get(pid)!.push(c)
  })
  const kids = (pid: string) => (byParent.get(pid) || []).slice().sort((a, b) => a.order - b.order)
  const tagById = new Map(props.allTags.map((tt) => [tt.id, tt]))
  const resolveTags = (c: RuleCategory): ReasonTag[] =>
    (c.tags || []).map((tt) => tagById.get(tt.id)).filter((tt): tt is ReasonTag => !!tt)

  // --- 第一遍: 计算每个节点的深度 与 其子树占用的末级行数 (rowSpan), 并得出最大深度 ---
  const depthOf = new Map<string, number>()
  const spanOf = new Map<string, number>()
  let maxDepth = 1
  const measure = (c: RuleCategory, depth: number): number => {
    depthOf.set(c.id, depth)
    if (depth > maxDepth) maxDepth = depth
    const ks = kids(c.id)
    if (!ks.length) {
      // 末级: 自身独占一行 (也是标签单元的载体)
      spanOf.set(c.id, 1)
      return 1
    }
    let n = 0
    ks.forEach((k) => { n += measure(k, depth + 1) })
    spanOf.set(c.id, n)
    return n
  }
  kids('').forEach((root) => measure(root, 1))

  // --- 第二遍: 深度优先落位, 生成分类单元 + 标签单元 ---
  const cells: MergeCell[] = []
  const rows: TagRow[] = []
  let cursor = 0 // 0-based: 下一个可用的末级行
  const place = (c: RuleCategory) => {
    const depth = depthOf.get(c.id) || 1
    const rowSpan = spanOf.get(c.id) || 1
    const rowStart = cursor
    const ks = kids(c.id)
    const isLeaf = ks.length === 0
    // 有子级: 只占自身所在列 (子级占右侧列) → 跨行
    // 末级  : 向右延展到最深层级所在列   → 跨列
    const colSpan = isLeaf ? maxDepth - depth + 1 : 1
    cells.push({
      key: c.id,
      name: c.name,
      col: depth,
      colSpan,
      row: rowStart + 1, // CSS Grid 行号从 1 开始
      rowSpan,
      isLeaf,
      isWide: isLeaf && colSpan > 1,
    })
    if (isLeaf) {
      rows.push({ catId: c.id, row: rowStart + 1, tags: resolveTags(c), allowCustom: c.allowCustom })
      cursor += 1
    } else {
      ks.forEach(place)
    }
  }
  kids('').forEach(place)

  return { cells, rows, maxDepth }
})

// 分类单元列数 = 最大层级; 末列 (1fr) 承接标签单元
const gridStyle = computed(() => {
  const n = Math.max(1, layout.value.maxDepth)
  return { gridTemplateColumns: `repeat(${n}, minmax(76px, 122px)) minmax(0, 1fr)` }
})

function cellStyle(cell: MergeCell) {
  return {
    gridColumn: `${cell.col} / span ${cell.colSpan}`,
    gridRow: `${cell.row} / span ${cell.rowSpan}`,
  }
}
function rowStyle(row: TagRow) {
  return {
    gridColumn: `${layout.value.maxDepth + 1}`,
    gridRow: `${row.row}`,
  }
}
</script>

<style scoped>
.step3 { display: flex; flex-direction: column; gap: var(--space-4); }

.rl-preview-module {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: var(--glass-bg-elevated);
  padding: var(--space-3);
}
.rl-mod-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: var(--space-3);
}
.rl-mod-head h3 {
  margin: 0;
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
}
.rl-scene {
  font-size: var(--fs-11);
  color: var(--ink-soft);
  background: var(--g1);
  border-radius: 999px;
  padding: 1px 9px;
}
.rl-mod-limit {
  margin-left: auto;
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
.rl-mod-limit.full { color: var(--c-error); font-weight: 600; }

/* === 合并单元格式卡片网格 (纯 CSS Grid, 零 <table>) ===
 * - 行高由标签单元内容决定; 跨行的分类单元随其跨越的行一起延展
 * - 小间距 + 圆角让相邻单元连成块, 强化「合并块」的连通观感
 */
.rl-merge {
  display: grid;
  gap: 5px;
  grid-auto-rows: minmax(40px, auto);
  align-items: stretch;
}

/* 分类单元: 靠 grid span 实现跨行/跨列, 视觉上等同合并单元格 */
.rl-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--brand-a12);
  border-radius: var(--radius-sm);
  background: var(--brand-tint);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-weight: 500;
  line-height: 1.45;
  text-align: center;
  overflow-wrap: anywhere;
  transition: border-color var(--duration-fast) var(--ease-out);
}
.rl-cell:hover { border-color: var(--brand); }
.rl-cell.is-leaf {
  background: var(--brand-soft);
  border-color: var(--brand-a22);
  color: var(--ink);
  font-weight: 600;
}
.rl-cell.is-wide { background: var(--brand-a22); }

/* 标签单元: 每个末级分类一行, 同类原因标签在此聚合排列 */
.rl-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  align-content: center;
  gap: 6px;
  min-width: 0;
  padding: 2px 0 2px var(--space-2);
}
.rl-tags-empty {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  user-select: none;
}

/* === 原因标签 capsule === */
.rl-tag {
  border: 1px solid var(--border-hairline);
  border-radius: 7px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-11);
  padding: 4px 11px;
  line-height: 1.4;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  user-select: none;
  transition: all var(--duration-fast) var(--ease-out);
}
.rl-tag:hover { border-color: var(--brand); color: var(--brand); }
.rl-tag.selected {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
  font-weight: 500;
}
.rl-tag.selected .rl-tag-check { color: #fff; }
.rl-tag.disabled {
  cursor: not-allowed;
  opacity: .45;
}
.rl-tag.disabled:hover { border-color: var(--border-hairline); color: var(--ink-soft); }
.rl-tag.other { border-style: dashed; color: var(--brand); border-color: var(--brand); }
.rl-tag.other:hover { background: var(--brand-tint); }
.rl-tag.other-filled { background: var(--brand-soft); border-color: var(--brand); color: var(--brand); }

.rl-other-input {
  border: 1px solid var(--brand);
  border-radius: 7px;
  font-size: var(--fs-11);
  padding: 4px 10px;
  line-height: 1.4;
  width: 130px;
  outline: none;
  color: var(--ink);
  background: var(--surface);
}
.rl-other-input:focus { box-shadow: 0 0 0 2px var(--brand-a22); }

.rl-empty {
  padding: 36px;
  text-align: center;
  color: var(--ink-faint);
  font-size: var(--fs-13);
}

.rl-detail-input { width: 100%; }
</style>

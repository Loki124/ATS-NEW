<script setup lang="ts">
/**
 * 业务侧原因标签选择器（2026-10-19；样式对齐管理端 Step3Preview 预览）
 *
 * 消费原因库「业务态」规则（GET /reason-library/active/?scene=xxx 返回的
 * SceneRule 完整树），在淘汰 / 放入人才库等业务弹窗内渲染可选原因标签。
 *
 * 视觉与交互还原管理端 Step3Preview 的「合并单元格式」预览：
 * - 弹窗标题：优先用规则配置的 modalTitle（配置人员可自定义），空则回退默认文案
 * - 合并单元格网格：分类单元按层级跨行/跨列（纯 CSS Grid，零 <table>），
 *   区块颜色以柔和底色（--cat-tint）表达，继承规则与预览一致
 * - 标签胶囊：已选=品牌底白字；达到 maxSelectableTags 上限后未选项呈禁用态，
 *   点击时 toast 明确提示（不静默吞掉操作）
 * - 末级分类 allowCustom=true 时提供「其他」自由输入（真实文本，非伪标签）；
 *   经 v-model:otherReasons 上报父组件，由后端随归因记录落库（custom_reasons）
 * - 标签来源：优先用分类自带的 tags；若后端仅下发 tagIds（序列化裁剪），
 *   自动回退拉取标签池（enabled, pageSize=500）按 id 重建
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { NAlert, NText, useMessage } from 'naive-ui'
import { listTags } from '../../api/reason-library'
import type { ReasonTag, RuleCategory, SceneRule } from '../../types/reason-library'

const props = defineProps<{
  /** 业务态命中的场景规则（非空才渲染本组件） */
  rule: SceneRule
  /** 覆盖规则的可选上限（一般不用，留扩展位） */
  max?: number
}>()

const selected = defineModel<string[]>('selected', { default: () => [] })
/** 自定义「其他」原因（末级分类 allowCustom 时终端用户输入），上报父组件落库 */
const otherReasons = defineModel<Array<{ catId: string; category: string; text: string }>>(
  'otherReasons',
  { default: () => [] },
)

const { t } = useI18n()
const message = useMessage()

// ============= 规则标题: 配置人员的 modalTitle 优先, 空则回退默认文案 =============
const displayTitle = computed(
  () => props.rule?.modalTitle?.trim() || t('reasonLibrary.picker.title'),
)

const maxSelected = computed(() => {
  if (props.max && props.max > 0) return props.max
  const n = Number(props.rule?.maxSelectableTags ?? 0)
  return n > 0 ? n : 5
})

// ============= 自定义「其他」状态（组件内部，上报 otherReasons） =============
const otherInputs = ref<Record<string, string>>({})
const editingOther = ref<Record<string, boolean>>({})
const customCount = computed(() => otherReasons.value.length)
const limitReached = computed(
  () => selected.value.length + customCount.value >= maxSelected.value,
)

/** 提交「其他」输入：非空→写入 otherReasons（替换同分类旧项）；空→清除 */
function commitOther(catId: string, catName: string, raw: string) {
  const v = (raw ?? '').trim()
  const next = otherReasons.value.filter((r) => r.catId !== catId)
  if (v) next.push({ catId, category: catName, text: v })
  otherReasons.value = next
  if (v) otherInputs.value[catId] = v
  else delete otherInputs.value[catId]
  editingOther.value[catId] = false
}
function clearOther(catId: string) {
  const entry = otherReasons.value.find((r) => r.catId === catId)
  commitOther(catId, entry?.category ?? '', '')
}
function editOtherAgain(catId: string) {
  editingOther.value[catId] = true
}
function onOtherClick(catId: string, catName: string) {
  // 已达上限且本分类「其他」尚未计入 → 阻止打开输入框并提示
  if (limitReached.value && !otherInputs.value[catId]) {
    message.warning(t('reasonLibrary.picker.maxReached', { n: maxSelected.value }))
    return
  }
  editingOther.value[catId] = true
}

// ============= 标签解析: 规则树 + tagIds 序列化裁剪兜底 =============
const cats = ref<RuleCategory[]>([])
const loadError = ref(false)

watch(
  () => props.rule,
  (rule) => {
    void resolve(rule)
  },
  { immediate: true },
)

/** 规则树 → 逐分类解析出可用标签（tags 缺失时从标签池按 tagIds 重建）。 */
async function resolve(rule: SceneRule) {
  loadError.value = false
  cats.value = []
  otherInputs.value = {} // 规则变化（重新打开弹窗）时清空内部「其他」草稿
  const list: RuleCategory[] = rule?.categories ?? []
  if (!list.length) return

  const needPool = list.some((c) => !(c.tags?.length) && (c.tagIds?.length ?? 0) > 0)
  let pool: Map<string, ReasonTag> | null = null
  if (needPool) {
    try {
      const page = await listTags({ enabled: true, pageSize: 500 })
      pool = new Map(page.items.map((tg) => [tg.id, tg]))
    } catch {
      loadError.value = true
      return
    }
  }

  cats.value = list.map((c) => {
    const tags = c.tags?.length
      ? c.tags
      : (c.tagIds ?? []).map((id) => pool?.get(id)).filter((x): x is ReasonTag => !!x)
    return { ...c, tags }
  })
}

// ============= 合并单元格式布局（算法与 Step3Preview 一致：两遍扫描） =============
interface MergeCell {
  key: string
  name: string
  col: number
  colSpan: number
  row: number
  rowSpan: number
  isLeaf: boolean
}
interface TagRow {
  catId: string
  name: string
  row: number
  tags: ReasonTag[]
  allowCustom: boolean
}

const layout = computed<{ cells: MergeCell[]; rows: TagRow[]; maxDepth: number }>(() => {
  const list = cats.value
  const byParent = new Map<string, RuleCategory[]>()
  list.forEach((c) => {
    const pid = c.parentId || ''
    if (!byParent.has(pid)) byParent.set(pid, [])
    byParent.get(pid)!.push(c)
  })
  const kids = (pid: string) => (byParent.get(pid) || []).slice().sort((a, b) => a.order - b.order)

  // 第一遍: 深度 + 子树占用的末级行数
  const depthOf = new Map<string, number>()
  const spanOf = new Map<string, number>()
  let maxDepth = 1
  const measure = (c: RuleCategory, depth: number): number => {
    depthOf.set(c.id, depth)
    if (depth > maxDepth) maxDepth = depth
    const ks = kids(c.id)
    if (!ks.length) {
      spanOf.set(c.id, 1)
      return 1
    }
    let n = 0
    ks.forEach((k) => {
      n += measure(k, depth + 1)
    })
    spanOf.set(c.id, n)
    return n
  }
  kids('').forEach((root) => measure(root, 1))

  // 第二遍: 深度优先落位 → 分类单元 + 末级标签行
  const cells: MergeCell[] = []
  const rows: TagRow[] = []
  let cursor = 0
  const place = (c: RuleCategory) => {
    const depth = depthOf.get(c.id) || 1
    const rowSpan = spanOf.get(c.id) || 1
    const rowStart = cursor
    const ks = kids(c.id)
    const isLeaf = ks.length === 0
    const colSpan = isLeaf ? maxDepth - depth + 1 : 1
    cells.push({
      key: c.id,
      name: c.name,
      col: depth,
      colSpan,
      row: rowStart + 1,
      rowSpan,
      isLeaf,
    })
    if (isLeaf) {
      rows.push({
        catId: c.id,
        name: c.name,
        row: rowStart + 1,
        tags: c.tags,
        allowCustom: c.allowCustom === true,
      })
      cursor += 1
    } else {
      ks.forEach(place)
    }
  }
  kids('').forEach(place)

  return { cells, rows, maxDepth }
})

const catMap = computed(() => new Map(cats.value.map((c) => [c.id, c])))

/**
 * 有效区块颜色（与 Step3Preview 同规则）:
 * 自身 color 非空 → 用之; 否则沿父链向上找第一个非空祖先; 全链皆空 → ''（默认品牌色）。
 */
function effectiveColor(cat: RuleCategory | undefined): string {
  let cur: RuleCategory | undefined = cat
  const visited = new Set<string>()
  while (cur && !visited.has(cur.id)) {
    visited.add(cur.id)
    if (cur.color) return cur.color
    if (!cur.parentId) break
    cur = catMap.value.get(cur.parentId)
  }
  return ''
}

/** 色值 → rgba（分类单元底色微染） */
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function cellStyle(cell: MergeCell): Record<string, string> {
  const style: Record<string, string> = {
    gridColumn: `${cell.col} / span ${cell.colSpan}`,
    gridRow: `${cell.row} / span ${cell.rowSpan}`,
  }
  const eff = effectiveColor(catMap.value.get(cell.key))
  if (eff) style['--cat-tint'] = hexToRgba(eff, 0.14)
  return style
}

function rowStyle(row: TagRow): Record<string, string> {
  return {
    gridColumn: `${layout.value.maxDepth + 1}`,
    gridRow: `${row.row}`,
  }
}

const gridStyle = computed(() => {
  const n = Math.max(1, layout.value.maxDepth)
  const w = catColWidth.value || CAT_FALLBACK_PX
  const catCols = Array(n)
    .fill(`${Math.round(w)}px`)
    .join(' ')
  return { gridTemplateColumns: `${catCols} 1fr` }
})

// ============= 选择 / 超限反馈 =============
function toggle(id: string) {
  const set = new Set(selected.value)
  if (set.has(id)) {
    set.delete(id)
  } else {
    if (limitReached.value) {
      message.warning(t('reasonLibrary.picker.maxReached', { n: maxSelected.value }))
      return
    }
    set.add(id)
  }
  selected.value = [...set]
}

// ============= 分类列宽: 同 Step3Preview, 由 font-size 推算「单行 5 个中文字」 =============
const CAT_LINE_CHARS = 5
const CAT_EXTRA_PX = 4
const CAT_FALLBACK_PX = CAT_LINE_CHARS * 12 + 3 * 2 + 1 * 2 + CAT_EXTRA_PX
const catColWidth = ref(0)
let _catMeasureTries = 0
function measureCatColWidth() {
  const el = document.querySelector('.rp-cell') as HTMLElement | null
  if (!el) {
    if (_catMeasureTries++ < 60) requestAnimationFrame(() => measureCatColWidth())
    return
  }
  _catMeasureTries = 0
  const s = getComputedStyle(el)
  const fs = parseFloat(s.fontSize) || 12
  const padX = parseFloat(s.paddingLeft) + parseFloat(s.paddingRight)
  const borderX = parseFloat(s.borderLeftWidth) + parseFloat(s.borderRightWidth)
  catColWidth.value = Math.ceil(CAT_LINE_CHARS * fs + padX + borderX + CAT_EXTRA_PX)
}
onMounted(measureCatColWidth)
watch(
  () => layout.value.cells.length,
  () => nextTick(measureCatColWidth),
)

// 进入编辑态时自动聚焦输入框
const vFocus = {
  mounted: (el: HTMLElement) => el.focus(),
}
</script>

<template>
  <div class="reason-picker">
    <div class="reason-picker-head">
      <span class="reason-picker-title">{{ displayTitle }}</span>
      <n-text :depth="3" style="font-size: var(--fs-12)">
        {{ t('reasonLibrary.picker.limit', { n: selected.length + customCount, m: maxSelected }) }}
      </n-text>
    </div>
    <n-alert v-if="rule?.tip" type="info" :bordered="false">
      {{ rule.tip }}
    </n-alert>
    <n-text v-if="loadError" type="error" style="font-size: var(--fs-12)">
      {{ t('reasonLibrary.picker.loadFailed') }}
    </n-text>
    <!-- 合并单元格式卡片网格 (纯 CSS Grid, 与 Step3Preview 预览同款) -->
    <div v-else-if="layout.cells.length" class="rp-merge" :style="gridStyle">
      <div
        v-for="cell in layout.cells"
        :key="cell.key"
        class="rp-cell"
        :class="{ 'is-leaf': cell.isLeaf }"
        :style="cellStyle(cell)"
      >
        <span class="rp-cell-name">{{ cell.name }}</span>
      </div>
      <div
        v-for="row in layout.rows"
        :key="row.catId"
        class="rp-tags"
        :style="rowStyle(row)"
      >
        <span v-if="!row.tags.length && !row.allowCustom" class="rp-tags-empty">—</span>
        <button
          v-for="tg in row.tags"
          :key="tg.id"
          type="button"
          class="rp-tag"
          :class="{
            selected: selected.includes(tg.id),
            disabled: !selected.includes(tg.id) && limitReached,
          }"
          :aria-disabled="!selected.includes(tg.id) && limitReached"
          @click="toggle(tg.id)"
        >
          {{ tg.name }}
        </button>
        <!-- 末级分类 allowCustom: 自定义「其他」自由输入（真实文本, 落库 custom_reasons） -->
        <template v-if="row.allowCustom">
          <input
            v-if="editingOther[row.catId]"
            v-focus
            class="rp-other-input"
            :value="otherInputs[row.catId] || ''"
            :placeholder="t('reasonLibrary.picker.otherPlaceholder')"
            @input="(e: any) => (otherInputs[row.catId] = (e.target as HTMLInputElement).value)"
            @keydown.enter="commitOther(row.catId, row.name, otherInputs[row.catId] || '')"
            @blur="commitOther(row.catId, row.name, otherInputs[row.catId] || '')"
          />
          <span
            v-else-if="otherInputs[row.catId]"
            class="rp-tag other-filled selected"
            @click="editOtherAgain(row.catId)"
          >
            <span class="rp-tag-text">{{ otherInputs[row.catId] }}</span>
            <span
              class="rp-tag-clear"
              role="button"
              :title="t('reasonLibrary.picker.otherClear')"
              @click.stop="clearOther(row.catId)"
            >×</span>
          </span>
          <button
            v-else
            type="button"
            class="rp-tag other"
            :class="{ disabled: limitReached }"
            :aria-disabled="limitReached"
            @click="onOtherClick(row.catId, row.name)"
          >
            {{ t('reasonLibrary.picker.other') }}
          </button>
        </template>
      </div>
    </div>
    <n-text v-else :depth="3" style="font-size: var(--fs-12)">
      {{ t('reasonLibrary.common.empty') }}
    </n-text>
  </div>
</template>

<style scoped>
.reason-picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.reason-picker-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.reason-picker-title {
  font-weight: 600;
  font-size: var(--fs-14);
  color: var(--ink);
}

/* === 合并单元格式卡片网格（与 Step3Preview 同款视觉）=== */
.rp-merge {
  display: grid;
  gap: 5px;
  grid-auto-rows: minmax(40px, auto);
  align-items: stretch;
}

.rp-cell {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) 3px;
  border: 1px solid var(--brand-a12);
  border-radius: var(--radius-sm);
  background: var(--cat-tint, var(--surface));
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-weight: 500;
  line-height: 1.45;
  text-align: center;
  overflow: hidden;
  overflow-wrap: anywhere;
  word-break: break-all;
}

.rp-cell.is-leaf {
  border-color: var(--brand-a22);
  color: var(--ink);
  font-weight: 600;
}

.rp-cell-name {
  position: relative;
  z-index: 1;
}

/* 标签单元: 每个末级分类一行, 同类原因标签在此聚合排列 */
.rp-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  align-content: center;
  gap: 6px;
  min-width: 0;
  padding: 2px 0 2px var(--space-2);
}

.rp-tags-empty {
  font-size: var(--fs-12);
  color: var(--ink-faint);
  user-select: none;
}

/* === 原因标签 capsule（语义化 button, 键盘可达）=== */
.rp-tag {
  appearance: none;
  border: 1px solid var(--border-hairline);
  border-radius: 7px;
  background: var(--surface);
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-family: inherit;
  padding: 4px 11px;
  line-height: 1.4;
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  cursor: pointer;
  user-select: none;
  transition: all var(--duration-fast) var(--ease-out);
}
.rp-tag:hover {
  border-color: var(--brand);
  color: var(--brand-fg);
}
.rp-tag:focus-visible {
  outline: 2px solid var(--brand-button);
  outline-offset: 2px;
}
.rp-tag.selected {
  background: var(--brand-button);
  border-color: var(--brand);
  color: #fff;
}
.rp-tag.disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.rp-tag.disabled:hover {
  border-color: var(--border-hairline);
  color: var(--ink-soft);
}

/* 未填写的「其他」入口: 虚线品牌色 */
.rp-tag.other {
  border-style: dashed;
  color: var(--brand-fg);
  border-color: var(--brand);
}
.rp-tag.other:hover {
  background: var(--brand-tint);
}
/* 已填内容的「其他」: 视觉完全复用 .rp-tag.selected (品牌底白字) */
.rp-tag.other-filled {
  cursor: text;
}
.rp-tag-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 1px;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  opacity: 0.7;
  transition: background-color var(--duration-fast) var(--ease-out), opacity var(--duration-fast) var(--ease-out);
}
.rp-tag-clear:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.22);
}
.rp-tag-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-other-input {
  border: 1px solid var(--brand);
  border-radius: 7px;
  font-size: var(--fs-12);
  padding: 4px 10px;
  line-height: 1.4;
  width: 130px;
  outline: none;
  color: var(--ink);
  background: var(--surface);
}
.rp-other-input:focus {
  box-shadow: 0 0 0 2px var(--brand-a22);
}
</style>

<template>
  <div class="step3">
    <!-- ============ 模拟真实业务弹窗: 还原终端用户看到的「标签选择」弹窗 ============ -->
    <div class="rl-sim-modal">
      <div class="rl-sim-modal__header">
        <!-- 模拟弹窗标题: 支持自定义输入, 默认占位「选择原因」; 改动经 update:modal-title 回传父组件写入规则 -->
        <n-input
          v-model:value="modalTitleModel"
          size="small"
          class="rl-sim-modal__title-input"
          :placeholder="t('reasonLibrary.wizard.preview.modalTitlePlaceholder')"
          :bordered="false"
        />
        <n-icon class="rl-sim-modal__close" :component="CloseOutline" :size="18" />
      </div>
      <div class="rl-sim-modal__body">
    <!-- ============ 模块一: 原因标签 (合并单元格式卡片网格, 零表格元素) ============ -->
    <div class="rl-preview-module">
      <div class="rl-mod-head">
        <h3>{{ t('reasonLibrary.wizard.preview.moduleTagsTitle') }}</h3>
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
        <!--
          分类单元 (按层级与子树范围跨行/跨列)。
          悬停时在当前卡片上叠加蒙层 + 「设置」按钮, 点击打开该分类的区块颜色弹窗。
        -->
        <div
          v-for="cell in layout.cells"
          :key="cell.key"
          class="rl-cell"
          :class="{ 'is-leaf': cell.isLeaf, 'is-wide': cell.isWide }"
          :style="cellStyle(cell)"
        >
          <span class="rl-cell-name">{{ cell.name }}</span>
          <div class="rl-cell-mask">
            <button
              type="button"
              class="rl-cell-set"
              @click.stop="openColorModal(cell.key)"
            >
              <n-icon :component="SettingsOutline" />
              <span>{{ t('reasonLibrary.wizard.preview.colorSet') }}</span>
            </button>
          </div>
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
              class="rl-tag other-filled selected"
              @click="editOtherAgain(row.catId)"
            >
              <span class="rl-tag-text">{{ otherInputs[row.catId] }}</span>
              <span
                class="rl-tag-clear"
                :title="t('reasonLibrary.wizard.preview.otherClear')"
                @click.stop="clearOther(row.catId)"
              >×</span>
            </span>
            <span v-else class="rl-tag other" :class="{ disabled: limitReached }" @click="onOtherClick(row.catId)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
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
      <div class="rl-sim-modal__footer">
        <n-button size="small" disabled>{{ t('reasonLibrary.common.cancel') }}</n-button>
        <n-button size="small" type="primary" disabled>{{ t('reasonLibrary.common.confirm') }}</n-button>
      </div>
    </div>

    <!-- ============ 区块颜色配置弹窗 (针对当前卡片) ============ -->
    <n-modal
      v-model:show="colorModalShow"
      preset="card"
      class="rl-color-modal"
      :title="colorModalTitle"
      style="max-width: 460px; width: 90vw;"
      :bordered="false"
      :mask-closable="true"
      @after-leave="onColorModalClosed"
    >
      <div v-if="editingCat" class="rl-color-body">
        <div class="rl-color-cur">
          <span class="rl-color-cur-name">{{ editingCat.name }}</span>
          <span class="rl-color-mode" :class="draftModeClass">{{ draftModeLabel }}</span>
        </div>
        <div class="rl-palette">
          <button
            v-for="c in BLOCK_COLORS"
            :key="c"
            type="button"
            class="rl-swatch"
            :class="{ active: draftColor === c }"
            :style="{ background: c }"
            :title="c"
            @click="draftColor = c"
          />
          <label class="rl-color-custom" :title="t('reasonLibrary.wizard.preview.colorCustom')">
            <input
              type="color"
              :value="draftColor || '#ffffff'"
              @input="(e: any) => (draftColor = (e.target as HTMLInputElement).value)"
            />
            <span>{{ t('reasonLibrary.wizard.preview.colorCustom') }}</span>
          </label>
        </div>
        <div class="rl-color-preview">
          <span class="rl-color-swatch" :style="{ background: swatchBg(draftEffectiveColor) }" />
          <span class="rl-color-preview-text">{{ draftPreviewText }}</span>
          <button
            v-if="draftColor"
            type="button"
            class="rl-color-reset"
            @click="draftColor = ''"
          >
            {{ t('reasonLibrary.wizard.preview.colorReset') }}
          </button>
        </div>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="colorModalShow = false">{{ t('reasonLibrary.common.cancel') }}</n-button>
          <n-button type="primary" @click="confirmColor">{{ t('reasonLibrary.common.confirm') }}</n-button>
        </n-space>
      </template>
    </n-modal>
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
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { NButton, NIcon, NInput, NModal, NSpace } from 'naive-ui'
import { SettingsOutline, CloseOutline } from '@vicons/ionicons5'
import type { ReasonTag, RuleCategory, WizardPayload } from '../../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  wizard: WizardPayload
  allTags: ReasonTag[]
}>()

/** 区块颜色变更回传父组件 (ReasonRuleWizard 写入 wizard.categories[i].color) */
const emit = defineEmits<{
  (e: 'update:color', p: { catId: string; color: string }): void
  (e: 'update:modal-title', v: string): void
}>()

/**
 * 模拟弹窗标题（默认「选择原因」）。
 * 以 computed 双向桥接：读取权威值 props.wizard.modalTitle；输入时 emit('update:modal-title')
 * 由父组件写入 wizard → 序列化时随规则保存进后端 modal_title。空值回退到默认占位文案。
 */
const modalTitleModel = computed<string>({
  get: () => props.wizard.modalTitle ?? '',
  set: (v: string) => emit('update:modal-title', v),
})

/** 预设调色板 — 满足「自定义其他颜色进行覆盖」的主要入口 */
const BLOCK_COLORS = [
  '#2080F0', '#18A058', '#F0A020', '#D03050', '#7C5CFC',
  '#2BB6C4', '#E35B8A', '#8F5E2E', '#5A6B7B', '#9C27B0',
]

const catMap = computed(() => {
  const m = new Map<string, RuleCategory>()
  ;(props.wizard.categories || []).forEach((c) => m.set(c.id, c))
  return m
})

/**
 * 有效区块颜色 (读取端实时推导, 不落库冗余值):
 * - 自身 color 非空 → 返回 (一级=专属色 / 非一级=自定义覆盖)
 * - 自身为空 → 沿父链向上找第一个非空的祖先 color
 * - 全链皆空 → 返回 '' (前端用默认品牌色)
 * 因此「改一级分类颜色 → 其下未自定义的子分类自动跟随」。
 */
function effectiveColor(cat: RuleCategory): string {
  let cur: RuleCategory | undefined = cat
  while (cur) {
    if (cur.color) return cur.color
    if (!cur.parentId) break
    cur = catMap.value.get(cur.parentId)
  }
  return ''
}

/** 找到所属一级分类 (沿父链上溯到 level===1) */
function level1Ancestor(cat: RuleCategory): RuleCategory | null {
  let cur: RuleCategory | undefined = cat
  while (cur && cur.level > 1 && cur.parentId) {
    const p = catMap.value.get(cur.parentId)
    if (!p) break
    cur = p
  }
  return cur && cur.level === 1 ? cur : null
}

function swatchBg(color: string): string {
  return color || 'var(--brand-tint)'
}

/** 色值 → rgba (用于分类单元底色微染) */
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  if (h.length !== 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// ============= 区块颜色弹窗 (悬停卡片 → 蒙层「设置」→ 弹窗) =============
const colorModalShow = ref(false)
const editingCatId = ref<string>('')
/** 草稿色: 弹窗内的临时选择, 确认前不写入 wizard (取消即丢弃) */
const draftColor = ref<string>('')

const editingCat = computed<RuleCategory | null>(
  () => catMap.value.get(editingCatId.value) ?? null,
)

const colorModalTitle = computed(
  () => t('reasonLibrary.wizard.preview.blockColorTitle'),
)

function openColorModal(catId: string) {
  const cat = catMap.value.get(catId)
  if (!cat) return
  editingCatId.value = catId
  draftColor.value = cat.color || ''  // 以当前已存色初始化草稿
  colorModalShow.value = true
}

/** 弹窗完全关闭后清空草稿, 避免下次打开残留 (取消/关闭均走此路径) */
function onColorModalClosed() {
  editingCatId.value = ''
  draftColor.value = ''
}

/** 确认: 将草稿色回传父组件写入 wizard.categories[i].color (空串=未自定义/继承) */
function confirmColor() {
  if (editingCatId.value) {
    emit('update:color', { catId: editingCatId.value, color: draftColor.value || '' })
  }
  colorModalShow.value = false
}

/** 草稿态下的有效色 (用于弹窗内预览色块): 草稿非空用草稿; 否则沿父链取继承色 */
const draftEffectiveColor = computed<string>(() => {
  const cat = editingCat.value
  if (!cat) return ''
  if (draftColor.value) return draftColor.value
  let cur: RuleCategory | undefined = cat
  while (cur) {
    if (cur.color) return cur.color
    if (!cur.parentId) break
    cur = catMap.value.get(cur.parentId)
  }
  return ''
})

const draftModeLabel = computed<string>(() => {
  const cat = editingCat.value
  if (!cat) return ''
  if (draftColor.value) {
    return cat.level === 1
      ? t('reasonLibrary.wizard.preview.colorModeExclusive')
      : t('reasonLibrary.wizard.preview.colorModeOverride')
  }
  if (cat.level === 1) return t('reasonLibrary.wizard.preview.colorModeDefault')
  const lv1 = level1Ancestor(cat)
  return t('reasonLibrary.wizard.preview.colorModeInherit', { name: lv1?.name || '' })
})

const draftModeClass = computed<string>(() => {
  const cat = editingCat.value
  if (!cat) return ''
  if (draftColor.value) return cat.level === 1 ? 'is-exclusive' : 'is-override'
  return cat.level === 1 ? 'is-default' : 'is-inherit'
})

const draftPreviewText = computed<string>(() => {
  if (draftColor.value) return draftColor.value.toUpperCase()
  if (editingCat.value?.level === 1) return t('reasonLibrary.wizard.preview.colorModeDefault')
  return t('reasonLibrary.wizard.preview.colorInheritHint')
})

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
  // 已达上限且本分类的「其他」尚未计入 → 阻止打开输入框
  if (limitReached.value && !selectedTagIds.value.has(`other:${id}`)) return
  editingOther[id] = true
}
function onOtherInput(id: string, val: string) {
  otherInputs[id] = val
}
function commitOther(id: string) {
  const v = (otherInputs[id] ?? '').trim()
  const s = new Set(selectedTagIds.value)
  if (v) {
    otherInputs[id] = v
    s.add(`other:${id}`)
  } else {
    otherInputs[id] = ''
    s.delete(`other:${id}`)
  }
  selectedTagIds.value = s
  editingOther[id] = false
}
function editOtherAgain(id: string) {
  editingOther[id] = true
}
function clearOther(id: string) {
  // 清除自定义内容, 恢复为原有「其他」占位标签, 并从已选计数移除
  otherInputs[id] = ''
  const s = new Set(selectedTagIds.value)
  s.delete(`other:${id}`)
  selectedTagIds.value = s
  editingOther[id] = false
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

// ============= 分类单元列宽: 统一「单行 5 个中文字」, 超长由 .rl-cell 的 word-break 在卡内折行 =============
// 列宽 = 5 个中文字的「真实渲染宽」(由 font-size 推算, 规避 canvas/探针文本测量受挂载时序干扰的偏差)
//       + 卡片水平内边距(3*2) + 边框(1*2) + 4px 呼吸余量。所有分类列等宽;
//       跨列融合卡天然 = N×5 字宽, 文本超长由 word-break 折行, 不再撑宽列(彻底消除「分类很宽」)。
const CAT_LINE_CHARS = 5
const CAT_EXTRA_PX = 4 // 5 字之外的呼吸余量(文字到边约 2px)
const CAT_FALLBACK_PX = CAT_LINE_CHARS * 12 + 3 * 2 + 1 * 2 + CAT_EXTRA_PX // 未测得前的兜底(真实字宽 12px/字)
const catColWidth = ref(0)
let _catMeasureTries = 0
function measureCatColWidth() {
  const ref = document.querySelector('.rl-cell') as HTMLElement | null
  // 网格单元可能尚未挂载(异步数据 / 步骤切换)→ 下一帧重试, 避免回到兜底值导致列宽偏大
  if (!ref) {
    if (_catMeasureTries++ < 60) requestAnimationFrame(() => measureCatColWidth())
    return
  }
  _catMeasureTries = 0
  const s = getComputedStyle(ref)
  const fs = parseFloat(s.fontSize) || 12
  const padX = parseFloat(s.paddingLeft) + parseFloat(s.paddingRight)
  const borderX = parseFloat(s.borderLeftWidth) + parseFloat(s.borderRightWidth)
  // 全宽 CJK 字 advance ≈ 1em = font-size(PingFang/微软雅黑等实测一致); 单行 4 字, 超长由 word-break 在卡内折行。
  // 直接由 font-size 推算, 规避 canvas/探针文本测量受挂载时序与 CSS 应用态干扰导致的字宽误判。
  catColWidth.value = Math.ceil(CAT_LINE_CHARS * fs + padX + borderX + CAT_EXTRA_PX)
}
onMounted(measureCatColWidth)
watch(() => layout.value.cells.length, () => nextTick(measureCatColWidth))

const gridStyle = computed(() => {
  const n = Math.max(1, layout.value.maxDepth)
  const w = catColWidth.value || CAT_FALLBACK_PX
  const catCols = Array(n).fill(`${Math.round(w)}px`).join(' ')
  // 末列(原因标签) 1fr 撑满剩余宽度, 吃掉原右侧空白; 胶囊在列内 flex-wrap 自然铺满整行。
  return {
    gridTemplateColumns: `${catCols} 1fr`,
  }
})

function cellStyle(cell: MergeCell) {
  const cat = catMap.value.get(cell.key)
  const eff = cat ? effectiveColor(cat) : ''
  const style: Record<string, string> = {
    gridColumn: `${cell.col} / span ${cell.colSpan}`,
    gridRow: `${cell.row} / span ${cell.rowSpan}`,
  }
  // 区块颜色统一表达为「四边等宽 1px 边框 + 整体柔和底色」。
  // 旧实现用「仅左侧 4px 加粗 + 左侧单独上色」做强调, 因左右边框宽度不对称, 在圆角处
  // 会渲染成左侧色块加重 / 突块 / 阴影般的异常视觉 (需求 2026-09-23 移除)。
  // 这里改为下发 CSS 变量: 未着色时不设置该变量 → CSS 回退到默认品牌边框与底色,
  // 着色时四边同色同宽 (边框宽度恒为 1px, 卡片盒尺寸不随是否着色而变)。
  if (eff) {
    // 仅下发底色变量: 边框不上色 (需求 2026-09-23 修订) —— 着色只以柔和底色表达,
    // 避免右侧/顶/底边框被上色造成与未着色卡不一致。未着色不设置变量 → 回退默认边框与底色。
    style['--cat-tint'] = hexToRgba(eff, 0.14)
  }
  return style
}
function rowStyle(row: TagRow) {
  return {
    gridColumn: `${layout.value.maxDepth + 1}`,
    gridRow: `${row.row}`,
  }
}
</script>

<style scoped>
.step3 { height: 100%; display: flex; flex-direction: column; }

/* === 模拟真实业务弹窗（还原终端用户看到的「标签选择」弹窗视觉效果）=== */
.rl-sim-modal {
  /* 完全铺满 step3(= wizard-body 可用区域), 自适应其宽高 */
  width: 100%;
  max-width: none;
  margin: 0;
  flex: 1 1 auto;
  min-height: 0;
  background: var(--surface);
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.rl-sim-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-hairline);
}
/* 模拟弹窗标题输入框: 外观还原为标题样式, 但可编辑; 默认占位「选择原因」 */
.rl-sim-modal__title-input {
  flex: 0 1 auto;
  max-width: 320px;
  min-width: 160px;
}
.rl-sim-modal__title-input :deep(.n-input__input-el) {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
}
.rl-sim-modal__title-input :deep(.n-input__placeholder) {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink-faint);
}
.rl-sim-modal__close { color: var(--ink-faint); cursor: default; flex-shrink: 0; }
.rl-sim-modal__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.rl-sim-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-hairline);
}
/* 模块在模拟弹窗内不再单独描边, 由弹窗本体提供外框 */
.rl-sim-modal .rl-preview-module {
  border: none;
  background: transparent;
  padding-left: 0;
  padding-right: 0;
}

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
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) 3px;
  border: 1px solid var(--brand-a12);
  border-radius: var(--radius-sm);
  /* 未着色分类单元格默认纯白底(去除品牌蓝紫调导致的「灰」观感); 仅显式着色(内联 --cat-tint)时上柔和底色, 边框不上色 */
  background: var(--cat-tint, var(--surface));
  color: var(--ink-soft);
  font-size: var(--fs-12);
  font-weight: 500;
  line-height: 1.45;
  text-align: center;
  overflow: hidden;
  overflow-wrap: anywhere;
  word-break: break-all;
  transition: border-color var(--duration-fast) var(--ease-out);
}
.rl-cell:hover { border-color: var(--brand); }
.rl-cell-name { position: relative; z-index: 1; }

/* 悬停蒙层 + 「设置」按钮: 仅 hover 时显示 (默认 opacity:0 + pointer-events:none, 不遮挡卡片) */
.rl-cell-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  background: rgba(0, 0, 0, .42);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--duration-fast) var(--ease-out);
}
.rl-cell:hover .rl-cell-mask { opacity: 1; pointer-events: auto; }
.rl-cell-set {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  border: none;
  border-radius: 6px;
  padding: 3px 9px;
  font-size: var(--fs-11);
  line-height: 1.3;
  color: #fff;
  background: var(--brand);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--duration-fast) var(--ease-out);
}
.rl-cell-set:hover { background: var(--brand-hover, var(--brand)); filter: brightness(1.08); }
.rl-cell.is-leaf {
  background: var(--cat-tint, var(--surface));
  border-color: var(--brand-a22);
  color: var(--ink);
  font-weight: 600;
}
.rl-cell.is-wide { background: var(--cat-tint, var(--surface)); }

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
  flex: 0 0 auto; /* 长度守恒: 列收窄时胶囊换行而非被压缩 */
  cursor: pointer;
  user-select: none;
  transition: all var(--duration-fast) var(--ease-out);
}
.rl-tag:hover { border-color: var(--brand); color: var(--brand); }
.rl-tag.selected {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
}
.rl-tag.disabled {
  cursor: not-allowed;
  opacity: .45;
}
.rl-tag.disabled:hover { border-color: var(--border-hairline); color: var(--ink-soft); }
.rl-tag.other { border-style: dashed; color: var(--brand); border-color: var(--brand); }
.rl-tag.other:hover { background: var(--brand-tint); }
/* 已填内容的「其他」: 视觉完全复用 .rl-tag.selected (品牌底白字), 仅颜色区分, 不引入抖动 */
.rl-tag-clear {
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
  opacity: .7;
  transition: background-color var(--duration-fast) var(--ease-out), opacity var(--duration-fast) var(--ease-out);
}
.rl-tag-clear:hover { opacity: 1; background: rgba(255, 255, 255, .22); }
.rl-tag-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

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

/* === 区块颜色配置弹窗 (针对当前卡片) === */
.rl-color-body { display: flex; flex-direction: column; gap: var(--space-4); }
.rl-color-cur {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.rl-color-cur-name {
  font-size: var(--fs-14);
  font-weight: 600;
  color: var(--ink);
  word-break: break-all;
}
.rl-color-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: var(--space-2) 0 0;
}
.rl-color-preview-text {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
.rl-color-swatch {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1px solid var(--border-hairline);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .35);
}
.rl-color-mode {
  flex: 0 0 auto;
  font-size: var(--fs-11);
  padding: 2px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-hairline);
  color: var(--ink-soft);
  background: var(--surface);
}
.rl-color-mode.is-exclusive { color: var(--brand); border-color: var(--brand-a22); background: var(--brand-tint); }
.rl-color-mode.is-override { color: #fff; border-color: transparent; background: var(--c-warn, #d97706); }
.rl-color-mode.is-inherit { color: var(--ink-soft); }
.rl-color-mode.is-default { color: var(--ink-faint); }
.rl-palette { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.rl-swatch {
  width: 20px;
  height: 20px;
  border-radius: 5px;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  outline: none;
  transition: transform var(--duration-fast) var(--ease-out);
}
.rl-swatch:hover { transform: scale(1.12); }
.rl-swatch.active {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--brand);
}
.rl-color-custom {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-11);
  color: var(--ink-soft);
  cursor: pointer;
}
.rl-color-custom input[type='color'] {
  width: 24px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border-hairline);
  border-radius: 5px;
  background: transparent;
  cursor: pointer;
}
.rl-color-reset {
  flex: 0 0 auto;
  font-size: var(--fs-11);
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-hairline);
  background: var(--surface);
  color: var(--ink-soft);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.rl-color-reset:hover { border-color: var(--brand); color: var(--brand); }
</style>

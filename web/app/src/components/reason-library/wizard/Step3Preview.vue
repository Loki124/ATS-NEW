<template>
  <div class="step3">
    <!-- ============ 模块一: 原因标签 (可勾选, 受规则「可选条数」限制) ============ -->
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

      <div v-if="!mergedRows.length" class="rl-empty">{{ t('reasonLibrary.wizard.preview.empty') }}</div>

      <div v-else class="rl-merged-table">
        <template v-for="(row, ri) in mergedRows" :key="ri">
          <!-- 第1列: L1 (纵向合并) -->
          <div
            v-if="row.l1IsFirst"
            class="rl-mcell l1"
            :style="{ gridRow: `span ${row.l1Rowspan}` }"
          >
{{ row.l1Name }}
</div>
          <!-- 第2列: L2 (纵向合并, 一个 L1 下多个 L2 则上下分割) -->
          <div
            v-if="row.l2IsFirst"
            class="rl-mcell l2"
            :style="{ gridRow: `span ${row.l2Rowspan}` }"
          >
{{ row.l2Name || '—' }}
</div>
          <!-- 第3列: L3 -->
          <div class="rl-mcell l3">{{ row.l3Name }}</div>
          <!-- 第4列: 原因标签 (可勾选) -->
          <div class="rl-mcell reason">
            <template v-for="leaf in row.leaves" :key="leaf.catId">
              <div v-if="leaf.label" class="rl-leaf-label">{{ leaf.label }}</div>
              <div class="rl-chips">
                <span
                  v-for="tag in leaf.tags"
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
                <template v-if="leaf.allowCustom">
                  <input
                    v-if="editingOther[leaf.catId]"
                    v-focus
                    class="rl-other-input"
                    :value="otherInputs[leaf.catId] || ''"
                    :placeholder="t('reasonLibrary.wizard.preview.otherPlaceholder')"
                    @input="(e: any) => onOtherInput(leaf.catId, (e.target as HTMLInputElement).value)"
                    @keydown.enter="commitOther(leaf.catId)"
                    @blur="commitOther(leaf.catId)"
                  />
                  <span
                    v-else-if="otherInputs[leaf.catId]"
                    class="rl-tag other-filled"
                    @click="editOtherAgain(leaf.catId)"
                  >{{ otherInputs[leaf.catId] }}</span>
                  <span v-else class="rl-tag other" @click="onOtherClick(leaf.catId)">{{ t('reasonLibrary.wizard.preview.other') }}</span>
                </template>
              </div>
            </template>
          </div>
        </template>
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
 * 布局 (需求 2026-09-21 修订):
 * - 页面分为上下两个模块:
 *     ① 原因标签: 展示 Step2 配置的标签, 用户可勾选 (受规则「可选条数」限制)
 *     ② 详细原因: 多行文本框
 * - 1-3 级分类用纵向合并单元格 (CSS Grid + grid-row: span): 左→右 分别是 L1 / L2 / L3;
 *   一个 L1 下有多个 L2 时, L2 列上下分割 (各自 rowspan 其下 L3 行数)。
 * - 第4级 (末级) 分类不单独成列, 其分类名作为小标签 + 原因标签一起落入第4列「原因」列。
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

interface LeafInfo {
  catId: string
  label: string // 第4级分类名 (L1-L3 末级留空)
  tags: ReasonTag[]
  allowCustom: boolean
}

interface PreviewRow {
  l1Name: string
  l2Name: string
  l3Name: string
  leaves: LeafInfo[]
  l1IsFirst: boolean
  l1Rowspan: number
  l2IsFirst: boolean
  l2Rowspan: number
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

// ============= 合并单元格数据模型 =============
const mergedRows = computed<PreviewRow[]>(() => {
  const cats = props.wizard.categories
  const byParent = new Map<string, RuleCategory[]>()
  cats.forEach((c) => {
    const pid = c.parentId || ''
    if (!byParent.has(pid)) byParent.set(pid, [])
    byParent.get(pid)!.push(c)
  })
  const tagById = new Map(props.allTags.map((tt) => [tt.id, tt]))
  const resolveTags = (c: RuleCategory): ReasonTag[] =>
    (c.tags || []).map((tt) => tagById.get(tt.id)).filter((tt): tt is ReasonTag => !!tt)
  const sortKids = (pid: string) => (byParent.get(pid) || []).sort((a, b) => a.order - b.order)

  // 递归收集某分类下的末级 (含其原因标签); 第4级带分类名标签
  const leavesUnder = (c: RuleCategory): LeafInfo[] => {
    const kids = sortKids(c.id)
    if (kids.length === 0) {
      return [{ catId: c.id, label: c.level >= 4 ? c.name : '', tags: resolveTags(c), allowCustom: c.allowCustom }]
    }
    return kids.flatMap(leavesUnder)
  }

  const rows: PreviewRow[] = []
  const l1s = sortKids('')
  for (const l1 of l1s) {
    const l2s = sortKids(l1.id)
    const l2Groups: { l2Name: string; rows: PreviewRow[] }[] = []
    if (!l2s.length) {
      // L1 本身即末级 (无 L2): 折叠为单行
      l2Groups.push({
        l2Name: '',
        rows: [{ l1Name: l1.name, l2Name: '', l3Name: l1.name, leaves: leavesUnder(l1), l1IsFirst: true, l1Rowspan: 1, l2IsFirst: true, l2Rowspan: 1 }],
      })
    } else {
      for (const l2 of l2s) {
        const l3s = sortKids(l2.id)
        const rowsInGroup: PreviewRow[] = []
        if (!l3s.length) {
          // L2 即末级 (无 L3)
          rowsInGroup.push({ l1Name: l1.name, l2Name: l2.name, l3Name: l2.name, leaves: leavesUnder(l2), l1IsFirst: true, l1Rowspan: 1, l2IsFirst: true, l2Rowspan: 1 })
        } else {
          for (const l3 of l3s) {
            rowsInGroup.push({ l1Name: l1.name, l2Name: l2.name, l3Name: l3.name, leaves: leavesUnder(l3), l1IsFirst: true, l1Rowspan: 1, l2IsFirst: true, l2Rowspan: 1 })
          }
        }
        l2Groups.push({ l2Name: l2.name, rows: rowsInGroup })
      }
    }
    const flat = l2Groups.flatMap((g) => g.rows)
    const l1Rowspan = flat.length
    flat.forEach((r, i) => {
      r.l1IsFirst = i === 0
      r.l1Rowspan = l1Rowspan
    })
    l2Groups.forEach((g) => {
      g.rows.forEach((r, ri) => {
        r.l2IsFirst = ri === 0
        r.l2Rowspan = g.rows.length
      })
    })
    rows.push(...flat)
  }
  return rows
})
</script>

<style scoped>
.step3 { display: flex; flex-direction: column; gap: var(--space-4); }

.rl-preview-module {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  background: #fff;
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

/* === 合并单元格表格 (CSS Grid) === */
.rl-merged-table {
  display: grid;
  grid-template-columns: 132px 132px 132px 1fr;
  grid-auto-flow: row;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.rl-mcell {
  border-right: 1px solid var(--border-hairline);
  border-bottom: 1px solid var(--border-hairline);
  padding: 10px 12px;
  font-size: var(--fs-12);
  min-height: 46px;
  display: flex;
  align-items: center;
}
.rl-mcell:nth-child(4n) { border-right: none; }
/* 每行最后一格 (reason) 去掉下边框由 grid 行决定, 这里统一保留 */

.rl-mcell.l1 {
  grid-column: 1;
  background: var(--brand-soft);
  font-weight: 600;
  color: var(--brand);
  justify-content: center;
  text-align: center;
  line-height: 1.4;
}
.rl-mcell.l2 {
  grid-column: 2;
  background: var(--g1);
  font-weight: 500;
  line-height: 1.4;
}
.rl-mcell.l3 {
  grid-column: 3;
  color: var(--ink-soft);
  line-height: 1.4;
}
.rl-mcell.reason {
  grid-column: 4;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px;
  align-content: flex-start;
  padding: 8px 12px;
}

.rl-leaf-label {
  width: 100%;
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.rl-leaf-label::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: .5;
}
.rl-chips { display: flex; flex-wrap: wrap; gap: 6px; width: 100%; align-content: flex-start; }

.rl-tag {
  border: 1px solid var(--border-hairline);
  border-radius: 7px;
  background: #fff;
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
.rl-tag.other:hover { background: rgba(54, 110, 235, .08); }
.rl-tag.other-filled { background: rgba(54, 110, 235, .1); border-color: var(--brand); color: var(--brand); }

.rl-other-input {
  border: 1px solid var(--brand);
  border-radius: 7px;
  font-size: var(--fs-11);
  padding: 4px 10px;
  line-height: 1.4;
  width: 130px;
  outline: none;
  color: var(--ink);
  background: #fff;
}
.rl-other-input:focus { box-shadow: 0 0 0 2px rgba(54, 110, 235, .18); }

.rl-empty {
  padding: 36px;
  text-align: center;
  color: var(--ink-faint);
  font-size: var(--fs-13);
}

.rl-detail-input { width: 100%; }
</style>

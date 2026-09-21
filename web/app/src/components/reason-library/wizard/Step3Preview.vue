<template>
  <div class="step3">
    <!-- ============ 模块一: 原因标签 (卡片式分类聚合, 无表格元素) ============ -->
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

      <div v-if="!tagCards.length" class="rl-empty">{{ t('reasonLibrary.wizard.preview.empty') }}</div>

      <div v-else class="tag-cards">
        <div v-for="card in tagCards" :key="card.name" class="tag-card">
          <div class="tag-card-head">
            <span class="tag-card-path">{{ card.name }}</span>
            <span class="tag-card-badge">{{ t('reasonLibrary.wizard.preview.tagTotal', { n: card.tagTotal }) }}</span>
          </div>

          <div class="tag-card-body">
            <div v-for="(grp, gi) in card.groups" :key="gi" class="tag-group">
              <div v-if="grp.name" class="tag-group-title"><span class="tg-bar"></span>{{ grp.name }}</div>
              <div class="tag-group-body">
                <div v-for="leaf in grp.leaves" :key="leaf.catId" class="tag-leaf">
                  <div v-if="leaf.label" class="tag-leaf-label">{{ leaf.label }}</div>
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
                </div>
              </div>
            </div>
          </div>
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
 * 布局 (需求 2026-09-21 修订为卡片式):
 * - 页面分为两个模块: ① 原因标签 (卡片式分类聚合) ② 详细原因 (多行文本框)
 * - 每个 L1 分类 = 一张 tag-card; L2 作为卡片内分组 (tag-group); L3/末级原因标签在分组内聚合排列。
 * - 卡片内「合并」含义: 同类 (同 L2 / 同末级) 的原因标签被聚合在同一 chip 容器内一并展示,
 *   不再使用任何 <table> 元素或 CSS Grid 伪装的合并单元格。
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

interface TagLeaf {
  catId: string
  label: string // 末级 (第4级) 分类名, 非末级留空
  tags: ReasonTag[]
  allowCustom: boolean
}
interface TagGroup {
  name: string // L2 分组名 (L1 直接末级时为 '')
  leaves: TagLeaf[]
  tagTotal: number
}
interface TagCard {
  name: string // L1 名
  groups: TagGroup[]
  tagTotal: number
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

// ============= 卡片式分类聚合数据模型 =============
const tagCards = computed<TagCard[]>(() => {
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
  const leavesUnder = (c: RuleCategory): TagLeaf[] => {
    const kids = sortKids(c.id)
    if (kids.length === 0) {
      return [{ catId: c.id, label: c.level >= 4 ? c.name : '', tags: resolveTags(c), allowCustom: c.allowCustom }]
    }
    return kids.flatMap(leavesUnder)
  }

  const cards: TagCard[] = []
  for (const l1 of sortKids('')) {
    const l2s = sortKids(l1.id)
    const groups: TagGroup[] = []
    if (!l2s.length) {
      // L1 本身即末级 (无 L2): 折叠为单分组
      const leaves = leavesUnder(l1)
      groups.push({ name: '', leaves, tagTotal: leaves.reduce((s, l) => s + l.tags.length, 0) })
    } else {
      for (const l2 of l2s) {
        const leaves = leavesUnder(l2)
        groups.push({ name: l2.name, leaves, tagTotal: leaves.reduce((s, l) => s + l.tags.length, 0) })
      }
    }
    const tagTotal = groups.reduce((s, g) => s + g.tagTotal, 0)
    cards.push({ name: l1.name, groups, tagTotal })
  }
  return cards
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

/* === 卡片式分类聚合 (替代原网格表格) === */
.tag-cards { display: flex; flex-direction: column; gap: var(--space-3); }
.tag-card {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--duration-fast) var(--ease-out);
}
.tag-card:hover { border-color: var(--brand); }
.tag-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-2) var(--space-3);
  background: var(--glass-bg-card);
  border-bottom: 1px solid var(--border-hairline);
}
.tag-card-path {
  font-size: var(--fs-13);
  font-weight: 600;
  color: var(--ink);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tag-card-badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  padding: 1px 7px;
  background: var(--g1);
  color: var(--ink-soft);
}
.tag-card-body {
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.tag-group { }
.tag-group-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: var(--space-2);
}
.tag-group-title .tg-bar {
  width: 3px;
  height: 13px;
  border-radius: 2px;
  background: var(--brand);
}
.tag-group-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-left: 10px;
  border-left: 2px solid var(--g1);
}
.tag-leaf { }
.tag-leaf-label {
  width: 100%;
  font-size: var(--fs-11);
  font-weight: 600;
  color: var(--ink-soft);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.tag-leaf-label::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: .5;
}

/* === 原因标签 capsule (沿用项目既有卡片式 chip 风格) === */
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

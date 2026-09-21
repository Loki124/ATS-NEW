<template>
  <div class="step2">
    <div class="step-intro">
      <n-icon :component="InformationCircleOutline" color="var(--brand)" :size="16" />
      <span>
        <b>{{ t('reasonLibrary.wizard.step2.title') }}</b>
        — {{ t('reasonLibrary.wizard.intro.step2') }}
      </span>
    </div>

    <div v-if="!leafCats.length" class="rl-empty">
      <n-empty :description="t('reasonLibrary.wizard.emptyCategory')" />
    </div>

    <div v-else class="assign-grid">
      <div
        v-for="cat in leafCats"
        :key="cat.id"
        class="assign-card glass-card"
        :class="{ locked: !cat.allowCustom }"
      >
        <div class="assign-head">
          <span class="path">{{ buildPath(cat.id) }}</span>
          <span class="assign-badge count">{{ cat.tags?.length || 0 }} 条</span>
          <span v-if="cat.allowCustom" class="assign-badge custom">
            {{ t('reasonLibrary.wizard.assign.customBadge') }}
          </span>
          <span v-else class="assign-badge system">
            <n-icon :component="LockClosedOutline" :size="10" />
            {{ t('reasonLibrary.wizard.assign.lockedBadge') }}
          </span>
          <n-button
            v-if="cat.allowCustom"
            size="tiny"
            @click="openPicker(cat)"
          >
            <template #icon><n-icon :component="AddOutline" :size="12" /></template>
            {{ t('reasonLibrary.wizard.assign.batchSelect') }}
          </n-button>
          <n-tooltip v-else placement="top">
            <template #trigger>
              <n-button size="tiny" disabled>
                <template #icon><n-icon :component="LockClosedOutline" :size="12" /></template>
                {{ t('reasonLibrary.common.locked') }}
              </n-button>
            </template>
            {{ t('reasonLibrary.wizard.assign.lockedTitle') }}
          </n-tooltip>
        </div>

        <div class="assign-body">
          <div class="assign-tags" :class="{ empty: !cat.tags?.length }">
            <span v-for="tag in cat.tags" :key="tag.id" class="tag-chip">
              {{ tag.name }}
              <button
                v-if="cat.allowCustom"
                class="rm"
                :title="t('reasonLibrary.common.delete')"
                @click="removeTag(cat.id, tag.id)"
              >
                <n-icon :component="CloseOutline" :size="10" />
              </button>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量选择标签弹窗 -->
    <!-- 配置阶段: 单个分类可超过 5 条, 不显示上限提示 (max-pick=0 表示不限制) -->
    <TagPickerModal
      v-model:show="pickerShow"
      :category-id="pickerCatId"
      :categories="categories"
      :available-tags="availableTags"
      :current-selected="pickerCurrentSelected"
      :exclude-tag-ids="Array.from(usedElsewhereIds)"
      :max-pick="0"
      @confirm="onPickerConfirm"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * Step2Assignments (T-18)
 * - 每张末级分类一张 assign-card
 * - 路径 + 条数 + system/custom badge + 批量选择按钮
 * - 已选 chip (tag-chip): 系统预置分类不可删, 自定义可删
 * - 批量选择按钮在 system 分类上 disabled + tooltip
 */
import { ref, computed } from 'vue'
import { NButton, NIcon, NEmpty, NTooltip } from 'naive-ui'
import { AddOutline, CloseOutline, LockClosedOutline, InformationCircleOutline } from '@vicons/ionicons5'
import type { ReasonTag, RuleCategory } from '../../../types/reason-library'
import { t } from '../../../locales/zh-CN'
import TagPickerModal from './TagPickerModal.vue'

const props = defineProps<{
  categories: RuleCategory[]
  availableTags: ReasonTag[]
}>()

const emit = defineEmits<{
  (e: 'update:categories', v: RuleCategory[]): void
}>()

const pickerShow = ref(false)
const pickerCatId = ref<string | null>(null)

const leafCats = computed<RuleCategory[]>(() => {
  const childMap = new Map<string, RuleCategory[]>()
  props.categories.forEach((c) => {
    const pid = c.parentId || ''
    if (!childMap.has(pid)) childMap.set(pid, [])
    childMap.get(pid)!.push(c)
  })
  return props.categories
    .filter((c) => !childMap.get(c.id)?.length)
    .sort((a, b) => a.order - b.order)
})

const pickerCurrentSelected = computed<ReasonTag[]>(() => {
  if (!pickerCatId.value) return []
  const cat = props.categories.find((c) => c.id === pickerCatId.value)
  return cat?.tags ?? []
})

// Item4: 已被其它分类占用的标签 id 集合 — 这些标签不可再选入当前分类 (单归属)
const usedElsewhereIds = computed<Set<string>>(() => {
  const curId = pickerCatId.value
  const set = new Set<string>()
  // 只统计【末级分类】的占用 — 标签仅允许挂在末级 (Item4 修订);
  // 非末级的历史脏绑定不参与判断, 修复『未被使用却提示已使用』的误报。
  const leafIds = new Set(
    props.categories
      .filter((c) => !props.categories.some((x) => x.parentId === c.id))
      .map((c) => c.id),
  )
  props.categories.forEach((c) => {
    if (c.id === curId || !leafIds.has(c.id)) return
    ;(c.tags || []).forEach((t) => set.add(t.id))
  })
  return set
})

function buildPath(id: string): string {
  const parts: string[] = []
  let cur = props.categories.find((c) => c.id === id)
  while (cur) {
    parts.unshift(cur.name)
    cur = cur.parentId ? props.categories.find((c) => c.id === cur!.parentId) : undefined
  }
  return parts.join(' / ')
}

function openPicker(cat: RuleCategory) {
  pickerCatId.value = cat.id
  pickerShow.value = true
}

function removeTag(catId: string, tagId: string) {
  const next = props.categories.map((c) => {
    if (c.id !== catId) return c
    return { ...c, tags: (c.tags || []).filter((t) => t.id !== tagId) }
  })
  emit('update:categories', next)
}

function onPickerConfirm(payload: { catId: string; selected: ReasonTag[] }) {
  const next = props.categories.map((c) =>
    c.id === payload.catId ? { ...c, tags: payload.selected } : c,
  )
  emit('update:categories', next)
  pickerShow.value = false
}
</script>

<style scoped>
.step2 { display: flex; flex-direction: column; gap: var(--space-3); }

.step-intro {
  display: flex;
  gap: var(--space-2);
  align-items: flex-start;
  padding: var(--space-2) var(--space-3);
  background: var(--brand-soft);
  border-radius: var(--radius-md);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  line-height: 1.6;
}
.step-intro b { color: var(--brand); font-weight: 600; }

.rl-empty { padding: var(--space-5); }

.assign-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.assign-card {
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color var(--duration-fast) var(--ease-out);
}
.assign-card:hover { border-color: var(--brand); }
.assign-card.locked { background: var(--g1); }

.assign-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: var(--space-2) var(--space-3);
  background: var(--glass-bg-card);
  border-bottom: 1px solid var(--border-hairline);
}
.assign-head .path {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.assign-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  font-weight: 600;
  border-radius: 4px;
  padding: 1px 7px;
  flex-shrink: 0;
}
.assign-badge.count { background: var(--g1); color: var(--ink-soft); }
.assign-badge.custom { background: rgba(139, 92, 246, .12); color: #6d28d9; }
.assign-badge.system { background: var(--brand-warm-soft); color: var(--brand-warm-deep); }

.assign-body { padding: var(--space-3); }
.assign-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 28px;
  align-items: flex-start;
}
.assign-tags.empty::before {
  content: '暂未选择标签';
  font-size: var(--fs-12);
  color: var(--ink-faint);
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--fs-12);
  background: #fff;
  border: 1px solid var(--border-hairline);
  border-radius: var(--radius-sm);
  padding: 4px 6px 4px 10px;
  color: var(--ink);
  transition: all var(--duration-fast) var(--ease-out);
}
.tag-chip:hover { border-color: var(--brand); }
.tag-chip .rm {
  border: none;
  background: none;
  color: var(--ink-faint);
  cursor: pointer;
  padding: 2px;
  font-size: var(--fs-10);
  border-radius: 4px;
  display: inline-flex;
}
.tag-chip .rm:hover { background: var(--c-error-soft); color: var(--c-error); }
</style>

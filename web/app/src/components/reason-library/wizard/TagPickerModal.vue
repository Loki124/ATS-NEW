<template>
  <n-modal
    :show="show"
    preset="card"
    :title="t('reasonLibrary.wizard.tagPicker.title')"
    style="max-width: 640px"
    :mask-closable="false"
    :bordered="false"
    :segmented="{ content: 'soft', footer: 'soft' }"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="picker-toolbar">
      <n-input
        v-model:value="search"
        :placeholder="t('reasonLibrary.wizard.tagPicker.searchPlaceholder')"
        clearable
        style="flex: 1"
      >
        <template #prefix><n-icon :component="SearchOutline" /></template>
      </n-input>
      <n-select
        v-model:value="typeFilter"
        :options="typeOptions"
        :placeholder="t('reasonLibrary.tags.filter.allType')"
        style="width: 130px"
        clearable
      />
      <n-checkbox v-model:checked="onlyAvailable" class="only-available">
        {{ t('reasonLibrary.wizard.tagPicker.onlyAvailable') }}
      </n-checkbox>
      <n-button size="small" @click="selectAll">
        {{ t('reasonLibrary.wizard.tagPicker.selectAll') }}
      </n-button>
      <n-button size="small" @click="clearAll">
        {{ t('reasonLibrary.wizard.tagPicker.clear') }}
      </n-button>
    </div>

    <div class="picker-list">
      <n-empty
        v-if="!filteredTags.length"
        :description="t('reasonLibrary.wizard.tagPicker.empty')"
      />
      <label
        v-for="tag in filteredTags"
        :key="tag.id"
        class="picker-row"
        :class="{ disabled: isExcluded(tag.id) }"
      >
        <input
          type="checkbox"
          :checked="selectedIds.has(tag.id)"
          :disabled="isExcluded(tag.id) || (!selectedIds.has(tag.id) && effectiveMax != null && selectedIds.size >= effectiveMax)"
          @change="(e: any) => toggle(tag.id, e.target.checked)"
        />
        <span class="name">
          {{ tag.name }}
          <span v-if="tag.enName" class="en">{{ tag.enName }}</span>
        </span>
        <span v-if="isExcluded(tag.id)" class="excluded-tip">
          {{ t('reasonLibrary.wizard.tagPicker.assignedElsewhereShort') }}
        </span>
        <span v-else :class="['type', tag.type]">
          {{ tag.type === 'system' ? t('reasonLibrary.common.system') : t('reasonLibrary.common.custom') }}
        </span>
      </label>
    </div>

    <template #footer>
      <div class="picker-foot">
        <span class="picker-count">
          {{ t('reasonLibrary.wizard.tagPicker.selectedCount', { count: selectedIds.size }).replace('{count}', String(selectedIds.size)) }}
          <n-tag v-if="effectiveMax && selectedIds.size >= effectiveMax" size="small" type="warning" bordered style="margin-left: 8px;">
            {{ t('reasonLibrary.wizard.tagPicker.maxPickWarn', { max: effectiveMax }) }}
          </n-tag>
        </span>
        <n-space>
          <n-button @click="emit('update:show', false)">{{ t('reasonLibrary.wizard.tagPicker.cancel') }}</n-button>
          <n-button type="primary" @click="confirm">{{ t('reasonLibrary.wizard.tagPicker.confirm') }}</n-button>
        </n-space>
      </div>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
/**
 * TagPickerModal (T-19)
 * - 批量选择标签
 * - 搜索 + 类型筛选 + 「仅看可用」筛选 + 全选 + 清空 + 确定
 * - 选择上限 (maxPick prop):
 *    缺省 = MAX_PICK(5) → 用户实际使用时硬上限, 明确 5 条;
 *    0 = 不限制 (配置阶段可超过 5 条); 正整数 = 该上限。
 * - 「仅看可用」: 隐藏已被同规则其它分类占用的标签 (Item4 单归属)
 */
import { ref, computed, watch } from 'vue'
import { NModal, NInput, NSelect, NButton, NSpace, NTag, NIcon, NEmpty, NCheckbox, useMessage } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import type { ReasonTag, RuleCategory } from '../../../types/reason-library'
import { MAX_PICK } from '../../../types/reason-library'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{
  show: boolean
  categoryId: string | null
  categories: RuleCategory[]
  availableTags: ReasonTag[]
  currentSelected: ReasonTag[]
  excludeTagIds?: string[]
  /**
   * 选择上限:
   * - 不传 / 缺省 → MAX_PICK (5): 「用户实际使用时」的硬上限 (明确 5 条)
   * - 0 → 不限制 (配置阶段可超过 5 条)
   * - 其它正整数 → 该上限
   */
  maxPick?: number | null
}>()

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'confirm', payload: { catId: string; selected: ReasonTag[] }): void
}>()

const message = useMessage()

// Item4: 已归属其它分类的标签不可跨分类重复选择
const excludeSet = computed<Set<string>>(() => new Set(props.excludeTagIds ?? []))
function isExcluded(id: string): boolean {
  return excludeSet.value.has(id)
}

const search = ref('')
const typeFilter = ref<'system' | 'custom' | null>(null)
const onlyAvailable = ref(true)
const selectedIds = ref<Set<string>>(new Set())

const typeOptions = [
  { label: t('reasonLibrary.tags.filter.system'), value: 'system' },
  { label: t('reasonLibrary.tags.filter.custom'), value: 'custom' },
]

// 有效上限: 缺省=MAX_PICK(5); 0/负数=不限制; 正整数=该值
const effectiveMax = computed<number | null>(() => {
  const m = props.maxPick ?? MAX_PICK
  return m <= 0 ? null : m
})

// 打开时同步当前已选
watch(
  () => [props.show, props.categoryId] as const,
  ([show, catId]) => {
    if (show && catId) {
      selectedIds.value = new Set(props.currentSelected.map((t) => t.id))
    }
    if (show) {
      search.value = ''
      typeFilter.value = null
      onlyAvailable.value = true
    }
  },
  { immediate: true },
)

/** 仅展示 enabled + 类型筛选 + 「仅看可用」后的标签 */
const filteredTags = computed<ReasonTag[]>(() => {
  const q = search.value.trim().toLowerCase()
  return props.availableTags.filter((t) => {
    if (!t.enabled) return false
    if (q && !t.name.toLowerCase().includes(q) && !(t.enName || '').toLowerCase().includes(q)) return false
    if (typeFilter.value && t.type !== typeFilter.value) return false
    // 仅看可用: 隐藏已被其它分类占用的标签
    if (onlyAvailable.value && isExcluded(t.id)) return false
    return true
  })
})

function toggle(id: string, checked: boolean) {
  if (checked) {
    // Item4: 已归属其它分类的标签不可跨分类重复选择
    if (isExcluded(id)) {
      message.warning(t('reasonLibrary.wizard.tagPicker.assignedElsewhere'))
      return
    }
    if (effectiveMax.value != null && selectedIds.value.size >= effectiveMax.value) return
    selectedIds.value.add(id)
  } else {
    selectedIds.value.delete(id)
  }
  // 触发响应式
  selectedIds.value = new Set(selectedIds.value)
}

function selectAll() {
  const next = new Set(selectedIds.value)
  for (const tag of filteredTags.value) {
    if (effectiveMax.value != null && next.size >= effectiveMax.value) break
    if (isExcluded(tag.id)) continue // Item4: 跳过已归属其它分类的标签
    next.add(tag.id)
  }
  selectedIds.value = next
}

function clearAll() {
  selectedIds.value = new Set()
}

function confirm() {
  if (!props.categoryId) {
    emit('update:show', false)
    return
  }
  const selected = props.availableTags.filter((t) => selectedIds.value.has(t.id))
  emit('confirm', { catId: props.categoryId, selected })
}
</script>

<style scoped>
.picker-toolbar {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-bottom: var(--space-2);
}
.only-available { white-space: nowrap; user-select: none; }
.picker-list {
  max-height: 380px;
  overflow-y: auto;
  padding: 4px 0;
}
.picker-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}
.picker-row:hover { background: var(--brand-tint); }
.picker-row input {
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
.picker-row input:checked {
  background: var(--brand);
  border-color: var(--brand);
}
.picker-row input:checked::after {
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
.picker-row input:disabled { cursor: not-allowed; opacity: .5; }
.picker-row .name {
  flex: 1;
  font-size: var(--fs-13);
  color: var(--ink);
}
.picker-row .en {
  font-size: var(--fs-11);
  color: var(--ink-faint);
  margin-left: 6px;
}
.picker-row .type {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 999px;
}
.picker-row .type.system { background: var(--brand-soft); color: var(--brand); }
.picker-row .type.custom { background: rgba(139, 92, 246, .12); color: #6d28d9; }
.picker-row.disabled { cursor: not-allowed; opacity: .6; }
.picker-row.disabled:hover { background: transparent; }
.excluded-tip {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--c-error-soft);
  color: var(--c-error);
  flex-shrink: 0;
}

.picker-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.picker-count {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}
</style>

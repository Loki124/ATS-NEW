<script setup lang="ts">
/**
 * 业务侧原因标签选择器（2026-10-19）
 *
 * 消费原因库「业务态」规则（GET /reason-library/active/?scene=xxx 返回的
 * SceneRule 完整树），在淘汰 / 放入人才库等业务弹窗内渲染可选原因标签。
 *
 * - 分组展示：按顶级分类聚合其子树内全部末级标签（允许中间层存在）
 * - 标签来源：优先用分类自带的 tags；若后端仅下发 tagIds（序列化裁剪），
 *   自动回退拉取标签池（enabled, pageSize=500）按 id 重建
 * - 可选上限：rule.maxSelectableTags（0 = 不限制，兜底 5 = 后端 MAX_PICK）
 * - 超限点击：拦截并 toast 提示，不静默吞掉用户操作
 */
import { computed, ref, watch } from 'vue'
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

const { t } = useI18n()
const message = useMessage()

interface Group {
  key: string
  name: string
  color: string
  tags: ReasonTag[]
}

const groups = ref<Group[]>([])
const loadError = ref(false)

const maxSelected = computed(() => {
  if (props.max && props.max > 0) return props.max
  const n = Number(props.rule?.maxSelectableTags ?? 0)
  return n > 0 ? n : 5
})

watch(
  () => props.rule,
  (rule) => {
    void resolve(rule)
  },
  { immediate: true },
)

/** 规则树 → 展示分组。独立函数便于 watch 复用。 */
async function resolve(rule: SceneRule) {
  loadError.value = false
  groups.value = []
  const cats: RuleCategory[] = rule?.categories ?? []
  if (!cats.length) return

  const byId = new Map(cats.map((c) => [c.id, c]))
  const topOf = (c: RuleCategory): RuleCategory => {
    let cur = c
    // 防御环引用：visited 集合兜底，避免脏数据死循环
    const visited = new Set<string>()
    while (cur.parentId && byId.has(cur.parentId) && !visited.has(cur.id)) {
      visited.add(cur.id)
      cur = byId.get(cur.parentId)!
    }
    return cur
  }

  // 序列化裁剪兜底：分类只有 tagIds 时从标签池重建
  const needPool = cats.some((c) => !(c.tags?.length) && (c.tagIds?.length ?? 0) > 0)
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

  const grouped = new Map<string, Group>()
  for (const cat of cats) {
    const tags = cat.tags?.length
      ? cat.tags
      : (cat.tagIds ?? []).map((id) => pool?.get(id)).filter((x): x is ReasonTag => !!x)
    if (!tags.length) continue
    const top = topOf(cat)
    let g = grouped.get(top.id)
    if (!g) {
      g = { key: top.id, name: top.name, color: top.color || '', tags: [] }
      grouped.set(top.id, g)
    }
    g.tags.push(...tags)
  }
  groups.value = [...grouped.values()]
}

function toggle(id: string) {
  const set = new Set(selected.value)
  if (set.has(id)) {
    set.delete(id)
  } else {
    if (set.size >= maxSelected.value) {
      message.warning(t('reasonLibrary.picker.maxReached', { n: maxSelected.value }))
      return
    }
    set.add(id)
  }
  selected.value = [...set]
}
</script>

<template>
  <div class="reason-picker">
    <div class="reason-picker-head">
      <span class="reason-picker-title">{{ t('reasonLibrary.picker.title') }}</span>
      <n-text :depth="3" style="font-size: var(--fs-12)">
        {{ t('reasonLibrary.picker.limit', { n: selected.length, m: maxSelected }) }}
      </n-text>
    </div>
    <n-alert v-if="rule?.tip" type="info" :bordered="false">
      {{ rule.tip }}
    </n-alert>
    <n-text v-if="loadError" type="error" style="font-size: var(--fs-12)">
      {{ t('reasonLibrary.picker.loadFailed') }}
    </n-text>
    <div v-for="g in groups" :key="g.key" class="reason-group">
      <div class="reason-group-name" :style="g.color ? { color: g.color } : undefined">
        {{ g.name }}
      </div>
      <div class="reason-tags">
        <n-check-tag
          v-for="tg in g.tags"
          :key="tg.id"
          size="small"
          :checked="selected.includes(tg.id)"
          @click="toggle(tg.id)"
        >
          {{ tg.name }}
        </n-check-tag>
      </div>
    </div>
    <n-text v-if="!groups.length && !loadError" :depth="3" style="font-size: var(--fs-12)">
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

.reason-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.reason-group-name {
  font-size: var(--fs-12);
  color: var(--ink-soft);
}

.reason-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
</style>

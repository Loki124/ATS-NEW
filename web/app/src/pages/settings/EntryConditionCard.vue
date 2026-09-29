<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { ChatbubbleEllipsesOutline, ClipboardOutline } from '@vicons/ionicons5'
const { t } = useI18n()

/**
 * 阶段「进入条件」信息卡片 —— 严格复现参考 HTML 的视觉与三种状态：
 *   1) 未配置进入条件（空态虚线框）
 *   2) 进入条件仅 1 组（headless 单组：无组名、无组间关系）
 *   3) 进入条件有多组（rule-top 组间表达式 + 每组独立头/条件/提示）
 * 视觉一律走 design token（tokens.css / brand-tokens.css），禁止硬编码色值/圆角。
 *
 * 数据契约：接受扁平 legacy 模型（link.entryCondition：matchType + items）
 * 或分组模型（含 groups 字段）。扁平模型 → 单组 headless；分组模型 → 多组。
 */

interface ConditionItemInput {
  field?: string
  operator?: string
  value?: any
  [k: string]: any
}
interface GroupInput {
  name?: string
  matchType?: 'ALL' | 'ANY'
  innerExpression?: string
  innerPrompt?: string
  conditions?: ConditionItemInput[]
  items?: ConditionItemInput[]
  [k: string]: any
}
interface EntryConditionInput {
  matchType?: 'ALL' | 'ANY'
  conditionType?: string
  prompt?: string
  items?: ConditionItemInput[]
  groups?: GroupInput[]
  groupLogic?: 'AND' | 'OR'
  [k: string]: any
}

const props = defineProps<{
  /** 扁平 legacy 模型（link.entryCondition）或分组模型（含 groups） */
  entryCondition?: EntryConditionInput | null
}>()

/** 运算符 → 中文标签（对齐 stage-rule/types.ts OperatorKey） */
const OP_LABEL: Record<string, string> = {
  EQ: t('pages.settings.EntryConditionCard.s3'), NEQ: t('pages.settings.EntryConditionCard.s4'), GT: t('pages.settings.EntryConditionCard.s5'), GTE: t('pages.settings.EntryConditionCard.s6'), LT: t('pages.settings.EntryConditionCard.s7'),
  LTE: t('pages.settings.EntryConditionCard.s8'), BETWEEN: t('pages.settings.EntryConditionCard.s9'), IN: t('pages.settings.EntryConditionCard.s10'), NOT_IN: t('pages.settings.EntryConditionCard.s11'),
  IS_EMPTY: t('pages.settings.EntryConditionCard.s12'), IS_NOT_EMPTY: t('pages.settings.EntryConditionCard.s13'),
}
/** 圆圈数字 ①..⑳（参考 HTML 用 ①/② 消除全局编号歧义） */
const CIRCLED = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩','⑪','⑫','⑬','⑭','⑮','⑯','⑰','⑱','⑲','⑳']

function opLabel(op?: string): string {
  if (!op) return ''
  return OP_LABEL[op] ?? op
}
function formatValue(v: any): string {
  if (v === null || v === undefined || v === '') return '—'
  if (Array.isArray(v)) return v.length ? v.join(t('pages.settings.EntryConditionCard.s14')) : t('pages.settings.EntryConditionCard.s15')
  return String(v)
}
function circled(i: number): string {
  return CIRCLED[i - 1] ?? String(i)
}

interface DisplayCond { no: string; field: string; op: string; value: string }
interface DisplayGroup {
  name?: string
  matchType: 'ALL' | 'ANY'
  conditions: DisplayCond[]
  innerPrompt?: string
}

const normalized = computed(() => {
  const raw = props.entryCondition
  if (!raw) return { isEmpty: true, groups: [] as DisplayGroup[], groupLogic: 'AND' as const, overallPrompt: '' }

  // 分组模型优先（未来后端返回 condition groups 时直接渲染多组）
  const rawGroups = Array.isArray(raw.groups) ? raw.groups : null
  let groups: DisplayGroup[] = []
  if (rawGroups && rawGroups.length) {
    groups = rawGroups.map((g) => ({
      name: g.name,
      matchType: (g.matchType ?? raw.matchType ?? 'ANY') as 'ALL' | 'ANY',
      conditions: (g.conditions ?? g.items ?? []).map((c: ConditionItemInput, i: number) => ({
        no: circled(i + 1),
        field: c.field ?? '',
        op: opLabel(c.operator),
        value: formatValue(c.value),
      })),
      innerPrompt: g.innerPrompt || g.innerExpression || '',
    }))
  } else if (Array.isArray(raw.items) && raw.items.length) {
    // 扁平 legacy 模型 → 单组 headless
    groups = [{
      name: undefined,
      matchType: (raw.matchType ?? 'ANY') as 'ALL' | 'ANY',
      conditions: raw.items.map((c, i) => ({
        no: circled(i + 1),
        field: c.field ?? '',
        op: opLabel(c.operator),
        value: formatValue(c.value),
      })),
      innerPrompt: raw.prompt || '',
    }]
  }

  if (!groups.length) {
    return { isEmpty: true, groups: [] as DisplayGroup[], groupLogic: 'AND' as const, overallPrompt: '' }
  }
  return {
    isEmpty: false,
    groups,
    groupLogic: (raw.groupLogic ?? 'AND') as 'AND' | 'OR',
    overallPrompt: raw.prompt || '',
  }
})

const isMulti = computed(() => normalized.value.groups.length > 1)
// 组间 chip：组1 and 组2 / 组1 or 组2
const groupExpr = computed(() => {
  const n = normalized.value.groups.length
  const word = normalized.value.groupLogic === 'OR' ? 'or' : 'and'
  return Array.from({ length: n }, (_, i) => t('pages.settings.EntryConditionCard.s16', { n: i + 1 })).join(` ${word} `)
})
const groupSem = computed(() =>
  normalized.value.groupLogic === 'OR' ? t('pages.settings.EntryConditionCard.s17') : t('pages.settings.EntryConditionCard.s18'),
)
// 单组 chip：① or ② / ① and ②（组内 matchType 用 ALL/ANY 语义）
function groupChip(g: DisplayGroup): string {
  const word = g.matchType === 'ANY' ? 'or' : 'and'
  return g.conditions.map((_c, i) => circled(i + 1)).join(` ${word} `)
}
function groupHeadLabel(g: DisplayGroup): string {
  return g.matchType === 'ALL' ? t('pages.settings.EntryConditionCard.s19') : t('pages.settings.EntryConditionCard.s20')
}
</script>

<template>
  <div class="entry-cond">
    <!-- 状态 1：空态 -->
    <div v-if="normalized.isEmpty" class="entry-cond__empty">
      <NIcon :component="ClipboardOutline" size="15" class="entry-cond__empty-icon" />
      <span>{{ t('pages.settings.EntryConditionCard.s1') }}</span>
    </div>

    <template v-else>
      <!-- 状态 3：多组 → 组间表达式 -->
      <div v-if="isMulti" class="entry-cond__top">
        <span class="entry-cond__top-label">{{ t('pages.settings.EntryConditionCard.s2') }}</span>
        <span class="entry-cond__chip">{{ groupExpr }}</span>
        <span class="entry-cond__top-sem">{{ groupSem }}</span>
      </div>

      <div class="entry-cond__groups">
        <div
          v-for="(g, gi) in normalized.groups"
          :key="gi"
          class="entry-cond__group"
        >
          <div
            class="entry-cond__group-head"
            :class="{ 'entry-cond__group-head--headless': !isMulti && !g.name }"
          >
            <span v-if="isMulti || g.name" class="entry-cond__group-name">
              {{ g.name || (t('pages.settings.EntryConditionCard.s21') + (gi + 1)) }}
            </span>
            <span class="entry-cond__group-sem">{{ groupHeadLabel(g) }}</span>
            <span class="entry-cond__chip entry-cond__chip--group">{{ groupChip(g) }}</span>
          </div>

          <div
            v-for="(c, ci) in g.conditions"
            :key="ci"
            class="entry-cond__cond"
          >
            <span class="entry-cond__no">{{ c.no }}</span>
            <span class="entry-cond__field">{{ c.field }}</span>
            <span class="entry-cond__op">{{ c.op }}</span>
            <span class="entry-cond__val">{{ c.value }}</span>
          </div>

          <div v-if="g.innerPrompt" class="entry-cond__tip">
            <NIcon :component="ChatbubbleEllipsesOutline" size="11" class="entry-cond__tip-icon" />
            <span>{{ g.innerPrompt }}</span>
          </div>
        </div>
      </div>

      <!-- 整体未满足提示 -->
      <div v-if="normalized.overallPrompt" class="entry-cond__tip entry-cond__tip--overall">
        <NIcon :component="ChatbubbleEllipsesOutline" size="11" class="entry-cond__tip-icon" />
        <span>{{ normalized.overallPrompt }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.entry-cond {
  width: 100%;
}

/* ===== 状态 1：空态（虚线框） ===== */
.entry-cond__empty {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border: 1px dashed var(--g4);
  background: var(--g1);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  font-size: var(--fs-12);
  color: var(--n-450);
}
.entry-cond__empty-icon {
  color: var(--n-450);
  flex: 0 0 auto;
}

/* ===== 组间表达式（多组） ===== */
.entry-cond__top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.entry-cond__top-label {
  font-size: var(--fs-12);
  color: var(--n-450);
}
.entry-cond__top-sem {
  font-size: var(--fs-12);
  color: var(--n-450);
}

/* ===== 关系 chip（组间 / 组内） ===== */
.entry-cond__chip {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--brand);
  background: var(--brand-soft);
  border-radius: var(--radius-sm);
  padding: 1px var(--space-2);
  line-height: 18px;
}
.entry-cond__chip--group {
  margin-left: auto;
  font-weight: 500;
  color: var(--ink-soft);
  background: var(--surface);
  border: 1px solid var(--g2);
}

/* ===== 组容器 ===== */
.entry-cond__groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-2);
}
.entry-cond__group {
  background: var(--g1);
  border: 1px solid var(--g2);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3) var(--space-3);
  transition: border-color var(--duration-fast) var(--ease-out);
}
.entry-cond__group:hover {
  border-color: var(--g4);
}

/* ===== 组头 ===== */
.entry-cond__group-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}
.entry-cond__group-head--headless {
  margin-bottom: var(--space-2);
}
.entry-cond__group-name {
  font-size: var(--fs-12);
  font-weight: 600;
  color: var(--ink-soft);
}
.entry-cond__group-sem {
  font-size: var(--fs-12);
  color: var(--n-450);
}

/* ===== 条件行 ===== */
.entry-cond__cond {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-12);
  color: var(--ink-soft);
  padding: 1.5px 0;
  min-width: 0;
  flex-wrap: wrap;
}
.entry-cond__no {
  color: var(--n-450);
  font-size: var(--fs-12);
  flex: 0 0 auto;
}
.entry-cond__field {
  font-weight: 500;
  color: var(--ink);
}
.entry-cond__op {
  color: var(--n-450);
  font-size: var(--fs-12);
}
.entry-cond__val {
  background: var(--surface);
  border: 1px solid var(--g2);
  border-radius: var(--radius-sm);
  padding: 0 var(--space-2);
  line-height: 18px;
  font-weight: 500;
  color: var(--ink);
}

/* ===== 未满足提示（橙） ===== */
.entry-cond__tip {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  font-size: var(--fs-12);
  line-height: 1.5;
  color: var(--brand-warm-deep);
  margin-top: var(--space-1);
}
.entry-cond__tip-icon {
  margin-top: 2px;
  flex: 0 0 auto;
}
.entry-cond__tip--overall {
  margin-top: var(--space-2);
}
</style>

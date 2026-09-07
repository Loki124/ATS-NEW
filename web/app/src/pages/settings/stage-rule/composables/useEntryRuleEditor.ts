/**
 * 进入条件二级弹窗 state（单条 EntryConditionRule 编辑）
 * UI 按 HTML 原型呈现嵌套条件组结构（groups[]），落库拍平为 flat items + 1 条 expression + 1 条 reject_message。
 * 主 modal 通过 open(rule?) 打开，commit() 返回深拷贝交由主表单落库。
 */
import { reactive, ref, computed } from 'vue'
import type { EntryConditionRule, ConditionItem, ConditionGroup } from '../types'
import { AR_MAX_CONDITIONS, AR_MAX_GROUPS, AR_RULE_NAME_MAX } from '../constants'
import { useExpressionValidator } from './useExpressionValidator'

function emptyItem(seq: number): ConditionItem {
  return {
    item_seq: seq,
    condition_type: 'DEMAND',
    field: 'DEMAND_LEVEL',
    operator: 'EQ',
    value: null,
  }
}

function emptyGroup(): ConditionGroup {
  return { conditions: [emptyItem(1)], innerExpression: '', innerPrompt: '' }
}

/** 加载：把后端 flat items 反向构造为 1 个 group（向后兼容旧数据） */
function inflateFromRule(rule: EntryConditionRule): { groups: ConditionGroup[]; groupExpression: string; overallPrompt: string } {
  return {
    groups: [{ conditions: rule.items.length ? rule.items.map((it) => ({ ...it })) : [emptyItem(1)], innerExpression: '', innerPrompt: '' }],
    groupExpression: rule.expression,
    overallPrompt: rule.reject_message,
  }
}

/** 落库：把嵌套 groups 拍平为 flat items + 1 条 expression + 1 条 reject_message */
function flattenToRule(args: {
  id?: string
  rule_name: string
  rule_seq: number
  status: 'ENABLED' | 'DISABLED'
  groups: ConditionGroup[]
  groupExpression: string
  overallPrompt: string
}): EntryConditionRule {
  let seq = 0
  const items: ConditionItem[] = []
  for (const g of args.groups) {
    for (const c of g.conditions) {
      seq += 1
      items.push({ ...c, item_seq: seq })
    }
  }
  return {
    id: args.id,
    rule_name: args.rule_name,
    rule_seq: args.rule_seq,
    status: args.status,
    expression: args.groupExpression,
    reject_message: args.overallPrompt,
    items,
  }
}

export function useEntryRuleEditor() {
  const visible = ref(false)
  const isNew = ref(false)
  const draft = reactive<{
    id?: string
    rule_name: string
    rule_seq: number
    status: 'ENABLED' | 'DISABLED'
    groups: ConditionGroup[]
    groupExpression: string
    overallPrompt: string
  }>({
    rule_name: '',
    rule_seq: 0,
    status: 'ENABLED',
    groups: [emptyGroup()],
    groupExpression: '',
    overallPrompt: '',
  })
  const { clientValidate } = useExpressionValidator()

  // ===== 派生状态 =====
  const flatItemCount = computed(() => draft.groups.reduce((n, g) => n + g.conditions.length, 0))
  const canAddGroup = computed(() => draft.groups.length < AR_MAX_GROUPS)

  function canAddItemInGroup(g: ConditionGroup): boolean {
    return g.conditions.length < AR_MAX_CONDITIONS
  }
  function canRemoveGroup(): boolean {
    return draft.groups.length > 1
  }
  function canRemoveItemInGroup(g: ConditionGroup): boolean {
    return g.conditions.length > 1
  }

  const groupError = computed(() => clientValidate(draft.groupExpression, draft.groups.length))
  const nameError = computed(() => {
    const n = draft.rule_name.trim()
    if (!n) return '规则名不能为空'
    if (n.length > AR_RULE_NAME_MAX) return `规则名不能超过 ${AR_RULE_NAME_MAX} 字`
    return ''
  })

  function itemError(it: ConditionItem): string {
    if (!it.field) return '字段不能为空'
    if (!it.operator) return '运算符不能为空'
    const noValue = it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY'
    if (!noValue && (it.value == null || (Array.isArray(it.value) && it.value.length === 0) || it.value === '')) {
      return '条件值不能为空'
    }
    return ''
  }

  function innerExprError(g: ConditionGroup): { empty: boolean; valid: boolean; error?: string } {
    if (!g.innerExpression || !g.innerExpression.trim()) return { empty: true, valid: true }
    return clientValidate(g.innerExpression, g.conditions.length)
  }

  function groupHasError(g: ConditionGroup): boolean {
    if (g.conditions.some((it) => itemError(it) !== '')) return true
    const ie = innerExprError(g)
    if (!ie.empty && !ie.valid) return true
    return false
  }

  const hasError = computed(
    () => !!nameError.value
      || (!groupError.value.empty && !groupError.value.valid)
      || draft.groups.some((g) => groupHasError(g))
      || !draft.overallPrompt.trim()
  )

  // ===== 操作 =====
  function open(rule?: EntryConditionRule) {
    isNew.value = !rule
    if (rule) {
      draft.id = rule.id
      draft.rule_name = rule.rule_name
      draft.rule_seq = rule.rule_seq
      draft.status = rule.status
      const inflated = inflateFromRule(rule)
      draft.groups = inflated.groups
      draft.groupExpression = inflated.groupExpression
      draft.overallPrompt = inflated.overallPrompt
    } else {
      draft.id = undefined
      draft.rule_name = ''
      draft.rule_seq = 0
      draft.status = 'ENABLED'
      draft.groups = [emptyGroup()]
      draft.groupExpression = ''
      draft.overallPrompt = ''
    }
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  function addGroup() {
    if (!canAddGroup.value) return
    draft.groups.push(emptyGroup())
  }

  function removeGroup(idx: number) {
    if (!canRemoveGroup()) return
    draft.groups.splice(idx, 1)
  }

  function addItem(g: ConditionGroup) {
    if (!canAddItemInGroup(g)) return
    g.conditions.push(emptyItem(g.conditions.length + 1))
  }

  function removeItem(g: ConditionGroup, idx: number) {
    if (!canRemoveItemInGroup(g)) return
    g.conditions.splice(idx, 1)
  }

  function commit(): EntryConditionRule {
    return flattenToRule({
      id: draft.id,
      rule_name: draft.rule_name,
      rule_seq: draft.rule_seq,
      status: draft.status,
      groups: draft.groups.map((g) => ({
        conditions: g.conditions.map((it) => ({ ...it })),
        innerExpression: g.innerExpression,
        innerPrompt: g.innerPrompt,
      })),
      groupExpression: draft.groupExpression,
      overallPrompt: draft.overallPrompt,
    })
  }

  return {
    visible,
    isNew,
    draft,
    flatItemCount,
    canAddGroup,
    canRemoveGroup,
    canAddItemInGroup,
    canRemoveItemInGroup,
    groupError,
    nameError,
    itemError,
    innerExprError,
    hasError,
    open,
    close,
    addGroup,
    removeGroup,
    addItem,
    removeItem,
    commit,
  }
}
/**
 * 进入条件二级弹窗 state（单条 EntryConditionRule 编辑）
 * 主 modal 通过 open(rule?) 打开，commit() 返回深拷贝交由主表单落库。
 */
import { reactive, ref, computed } from 'vue'
import type { EntryConditionRule, ConditionItem } from '../types'
import { AR_MAX_CONDITIONS, AR_RULE_NAME_MAX } from '../constants'
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

function cloneRule(rule: EntryConditionRule): EntryConditionRule {
  return {
    id: rule.id,
    rule_name: rule.rule_name,
    rule_seq: rule.rule_seq,
    status: rule.status,
    expression: rule.expression,
    reject_message: rule.reject_message,
    items: rule.items.map((it) => ({ ...it })),
  }
}

export function useEntryRuleEditor() {
  const visible = ref(false)
  const isNew = ref(false)
  const draft = reactive<EntryConditionRule>({
    rule_name: '',
    rule_seq: 0,
    status: 'ENABLED',
    expression: '',
    reject_message: '',
    items: [emptyItem(1)],
  })
  const { clientValidate } = useExpressionValidator()

  const canAddItem = computed(() => draft.items.length < AR_MAX_CONDITIONS)
  const exprError = computed(() => clientValidate(draft.expression, draft.items.length))
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

  const hasError = computed(
    () => !!nameError.value || !!exprError.value || draft.items.some((it) => itemError(it) !== ''),
  )

  function open(rule?: EntryConditionRule) {
    isNew.value = !rule
    const src = rule ? cloneRule(rule) : { rule_name: '', rule_seq: 0, status: 'ENABLED' as const, expression: '', reject_message: '', items: [emptyItem(1)] }
    draft.rule_name = src.rule_name
    draft.rule_seq = src.rule_seq
    draft.status = src.status
    draft.expression = src.expression
    draft.reject_message = src.reject_message
    draft.items = src.items.length ? src.items.map((it) => ({ ...it })) : [emptyItem(1)]
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  function addItem() {
    if (!canAddItem.value) return
    draft.items.push(emptyItem(draft.items.length + 1))
  }

  function removeItem(idx: number) {
    if (draft.items.length <= 1) return
    draft.items.splice(idx, 1)
    draft.items.forEach((it, i) => (it.item_seq = i + 1))
  }

  /** 重新编号（条件项顺序变化后调用） */
  function renumber() {
    draft.items.forEach((it, i) => (it.item_seq = i + 1))
  }

  /** 依据当前条件项数生成默认表达式（仅在用户未手填时建议） */
  function suggestExpression(): string {
    if (draft.items.length === 0) return ''
    return draft.items.map((_, i) => String(i + 1)).join(' and ')
  }

  function commit(): EntryConditionRule {
    renumber()
    return cloneRule(draft)
  }

  return {
    visible,
    isNew,
    draft,
    canAddItem,
    exprError,
    nameError,
    hasError,
    itemError,
    open,
    close,
    addItem,
    removeItem,
    renumber,
    suggestExpression,
    commit,
  }
}

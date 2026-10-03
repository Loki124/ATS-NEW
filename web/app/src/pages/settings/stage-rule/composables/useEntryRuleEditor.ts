/**
 * 进入条件二级弹窗 state（单条 EntryConditionRule 编辑）
 * UI 按 HTML 原型呈现嵌套条件组结构（groups[]），落库拍平为 flat items + 1 条 expression + 1 条 reject_message。
 * 主 modal 通过 open(rule?) 打开，commit() 返回深拷贝交由主表单落库。
 */
import { reactive, ref, computed } from 'vue'
import type { EntryConditionRule, ConditionItem, ConditionGroup } from '../types'
import { AR_MAX_CONDITIONS, AR_MAX_GROUPS } from '../constants'
import { useExpressionValidator, type ExprCheck } from './useExpressionValidator'

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

/**
 * 加载：把后端 flat items + expression 反序列化为嵌套条件组（前端归一化，无后端字段）。
 * - 解析顶层表达式的操作数为「条件组」，每个 (n) 或 (a op b) 还原为一组；
 * - 组号表达式（groupExpression）用扁平顶层运算符拼接，保证重新保存可无损还原；
 * - 若表达式含嵌套括号或编号无法完整覆盖 items，则降级为「每条 item 一组」并保留完整表达式到 groupExpression。
 */
function parseTopLevel(expr: string): { operands: string[]; ops: string[] } | null {
  const tokens: { type: 'group' | 'op'; text: string }[] = []
  let buf = ''
  let depth = 0
  for (let i = 0; i < expr.length; i++) {
    const ch = expr[i]
    if (ch === ' ') {
      if (buf) buf += ch
      continue
    }
    if (ch === '(') {
      if (depth === 0 && buf.trim() !== '') {
        tokens.push({ type: 'group', text: buf.trim() })
        buf = ''
      }
      depth++
      if (depth > 1) buf += ch
      continue
    }
    if (ch === ')') {
      depth--
      if (depth === 0) {
        tokens.push({ type: 'group', text: buf.trim() })
        buf = ''
      } else {
        buf += ch
      }
      continue
    }
    if (depth === 0) {
      const rest = expr.slice(i).toUpperCase()
      if (rest.startsWith('AND') || rest.startsWith('OR')) {
        if (buf.trim() !== '') {
          tokens.push({ type: 'group', text: buf.trim() })
          buf = ''
        }
        tokens.push({ type: 'op', text: rest.slice(0, 3) })
        i += 2
        continue
      }
    }
    buf += ch
  }
  if (buf.trim() !== '' && depth === 0) tokens.push({ type: 'group', text: buf.trim() })
  if (tokens.length === 0) return null
  const operands: string[] = []
  const ops: string[] = []
  for (let i = 0; i < tokens.length; i++) {
    if (i % 2 === 0) {
      if (tokens[i].type !== 'group') return null
      operands.push(tokens[i].text)
    } else {
      if (tokens[i].type !== 'op') return null
      ops.push(tokens[i].text)
    }
  }
  return { operands, ops }
}

/** 把全局编号集合 nums 内的编号重新编号为局部 1..N */
function localize(expr: string, nums: number[]): string {
  return expr.replace(/\d+/g, (m) => {
    const idx = nums.indexOf(Number(m))
    return idx >= 0 ? String(idx + 1) : m
  })
}

/** 把组内局部编号整体平移 offset，变成全局编号 */
function relabelItemNums(expr: string, offset: number): string {
  if (!expr || offset === 0) return expr
  return expr.replace(/\d+/g, (m) => String(Number(m) + offset))
}

/** 把 groupExpression 里的组号 1..G 替换为对应组的已编译子表达式 */
function relabelGroupNums(expr: string, compiled: string[]): string {
  let out = ''
  let buf = ''
  for (const ch of expr) {
    if (ch >= '0' && ch <= '9') {
      buf += ch
      continue
    }
    if (buf) {
      out += compiled[Number(buf) - 1] ?? buf
      buf = ''
    }
    out += ch
  }
  if (buf) out += compiled[Number(buf) - 1] ?? buf
  return out
}

/** 单组（全部 items 归一组，组内表达式留空） */
function singleGroup(items: ConditionItem[]): ConditionGroup {
  return { conditions: items.map((c) => ({ ...c })), innerExpression: '', innerPrompt: '' }
}

function inflateFromRule(rule: EntryConditionRule): { groups: ConditionGroup[]; groupExpression: string; overallPrompt: string } {
  const items = rule.items || []
  const expr = (rule.expression || '').trim()
  const overallPrompt = rule.reject_message || ''
  if (!expr || items.length === 0) {
    return { groups: [singleGroup(items)], groupExpression: '', overallPrompt }
  }
  const parsed = parseTopLevel(expr)
  if (parsed && parsed.operands.length > 0) {
    const bySeq = new Map<number, ConditionItem>()
    items.forEach((it) => bySeq.set(it.item_seq, it))
    const groups: ConditionGroup[] = []
    const used = new Set<number>()
    let ok = true
    for (const op of parsed.operands) {
      let groupItems: ConditionItem[] = []
      let innerExpr = ''
      if (op.startsWith('(') && op.endsWith(')')) {
        const inner = op.slice(1, -1).trim()
        if (inner.includes('(') || inner.includes(')')) {
          ok = false
          break
        }
        const nums = inner
          .split(/\s+/)
          .filter(Boolean)
          .filter((t) => /^\d+$/.test(t))
          .map(Number)
        groupItems = nums.map((n) => bySeq.get(n)).filter(Boolean) as ConditionItem[]
        nums.forEach((n) => used.add(n))
        if (/\b(AND|OR)\b/.test(inner)) innerExpr = localize(inner, nums)
      } else if (/^\d+$/.test(op)) {
        const n = Number(op)
        const it = bySeq.get(n)
        if (it) {
          groupItems = [it]
          used.add(n)
        }
      } else {
        ok = false
        break
      }
      if (groupItems.length === 0) {
        ok = false
        break
      }
      groups.push({ conditions: groupItems.map((c) => ({ ...c })), innerExpression: innerExpr, innerPrompt: '' })
    }
    if (ok && used.size === items.length && groups.length > 0) {
      // 组号表达式：用扁平顶层运算符拼接（符合「顶层单一运算符」约束）
      let ge = '1'
      for (let i = 0; i < parsed.ops.length; i++) ge += ` ${parsed.ops[i]} ${i + 2}`
      return { groups, groupExpression: ge, overallPrompt }
    }
  }
  // 降级：每条 item 一组，完整表达式保留到 groupExpression（常见深度 1 表达式仍可被前端校验通过）
  const fallback: ConditionGroup[] = items.map((it) => ({ conditions: [{ ...it }], innerExpression: '', innerPrompt: '' }))
  return { groups: fallback, groupExpression: expr, overallPrompt }
}

/** 落库：把嵌套 groups 编译为后端认识的 flat items + 单一 expression（全局 item 编号） */
function flattenToRule(args: {
  id?: string
  rule_seq: number
  status: 'ENABLED' | 'DISABLED'
  groups: ConditionGroup[]
  groupExpression: string
  overallPrompt: string
}): EntryConditionRule {
  let seq = 0
  const items: ConditionItem[] = []
  const compiled: string[] = []
  for (const g of args.groups) {
    const offset = seq
    const conds = g.conditions
    conds.forEach((c) => {
      seq += 1
      items.push({ ...c, item_seq: seq })
    })
    let sub: string
    if (conds.length === 1 && !g.innerExpression.trim()) {
      sub = String(offset + 1)
    } else if (g.innerExpression.trim()) {
      sub = `(${relabelItemNums(g.innerExpression, offset)})`
    } else {
      const nums = conds.map((_, i) => offset + 1 + i)
      sub = nums.length === 1 ? String(nums[0]) : `(${nums.join(' AND ')})`
    }
    compiled.push(sub)
  }
  const expression = args.groupExpression.trim()
    ? relabelGroupNums(args.groupExpression, compiled)
    : compiled.join(' AND ')
  return {
    id: args.id,
    rule_name: '进入条件规则',
    rule_seq: args.rule_seq,
    status: args.status,
    expression,
    reject_message: args.overallPrompt,
    items,
  }
}

export function useEntryRuleEditor() {
  const visible = ref(false)
  const isNew = ref(false)
  const draft = reactive<{
    id?: string
    rule_seq: number
    status: 'ENABLED' | 'DISABLED'
    groups: ConditionGroup[]
    groupExpression: string
    overallPrompt: string
  }>({
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

  function itemError(it: ConditionItem): string {
    if (!it.field) return '字段不能为空'
    if (!it.operator) return '运算符不能为空'
    if (it.operator === 'BETWEEN') {
      const v = it.value
      const ok =
        Array.isArray(v) &&
        v.length === 2 &&
        v[0] != null && v[0] !== '' &&
        v[1] != null && v[1] !== ''
      if (!ok) return '区间条件需填写最小值和最大值'
      return ''
    }
    const noValue = it.operator === 'IS_EMPTY' || it.operator === 'IS_NOT_EMPTY'
    if (!noValue && (it.value == null || (Array.isArray(it.value) && it.value.length === 0) || it.value === '')) {
      return '条件值不能为空'
    }
    return ''
  }

  function innerExprError(g: ConditionGroup): ExprCheck {
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
    () => (!groupError.value.empty && !groupError.value.valid)
      || draft.groups.some((g) => groupHasError(g))
      || !draft.overallPrompt.trim()
  )

  // ===== 操作 =====
  function open(rule?: EntryConditionRule) {
    isNew.value = !rule
    if (rule) {
      draft.id = rule.id
      draft.rule_seq = rule.rule_seq
      draft.status = rule.status
      const inflated = inflateFromRule(rule)
      draft.groups = inflated.groups
      draft.groupExpression = inflated.groupExpression
      draft.overallPrompt = inflated.overallPrompt
    } else {
      draft.id = undefined
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
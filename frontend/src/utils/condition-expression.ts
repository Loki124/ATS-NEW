/**
 * 条件表达式实时校验 - 前端版 (Plan L Task 3b)
 *
 * 与后端 backend/src/services/condition-expression-validator.service.js 保持一致逻辑
 * 用于 UI 实时反馈 - 无需调 API
 *
 * 返回: { valid: boolean, error?: string, normalized?: string, empty?: boolean }
 */

export interface ValidationResult {
  valid: boolean
  error?: string
  normalized?: string
  empty?: boolean
  itemCount?: number
}

export function validateExpression(expr: string | null | undefined, itemCount: number): ValidationResult {
  // 1. 空检查
  if (expr == null) return { valid: true, empty: true }
  const trimmed = String(expr).trim()
  if (trimmed === '') return { valid: true, empty: true }

  // 2. 规范化大小写
  const normalized = trimmed.replace(/\bAND\b/gi, 'AND').replace(/\bOR\b/gi, 'OR')

  // 3. 字符白名单
  if (!/^[\d\s()ANDOR]+$/.test(normalized)) {
    return { valid: false, error: '表达式包含非法字符 (仅允许数字、空格、括号、AND/OR)', normalized }
  }

  // 4. 括号成对
  const openCount = (normalized.match(/\(/g) || []).length
  const closeCount = (normalized.match(/\)/g) || []).length
  if (openCount !== closeCount) {
    return { valid: false, error: `括号不匹配: ${openCount} 个左括号 vs ${closeCount} 个右括号`, normalized }
  }

  // 5. 拆分顶层 group/op
  const groups = splitTopLevel(normalized)
  if (groups.length === 0) return { valid: false, error: '表达式解析失败', normalized }
  if (groups[0].type === 'op') return { valid: false, error: '表达式不能以 AND/OR 开头', normalized }
  if (groups[groups.length - 1].type === 'op') return { valid: false, error: '表达式不能以 AND/OR 结尾', normalized }

  // 6. 顶层交替
  for (let i = 1; i < groups.length; i += 2) {
    if (groups[i].type !== 'op') return { valid: false, error: '缺少 AND/OR 连接符', normalized }
  }
  for (let i = 2; i < groups.length; i += 2) {
    if (groups[i].type !== 'group') return { valid: false, error: '缺少条件组', normalized }
  }

  // 7. 校验 group
  const allNumbers: number[] = []
  for (const g of groups) {
    if (g.type !== 'group') continue
    const r = validateGroup(g.text)
    if (!r.valid) return { valid: false, error: `条件组 [${g.text}] 非法: ${r.error}`, normalized }
    allNumbers.push(...r.numbers)
  }

  // 8. 数字范围
  if (typeof itemCount === 'number' && itemCount >= 0) {
    for (const n of allNumbers) {
      if (n < 1 || n > itemCount) {
        return { valid: false, error: `数字 ${n} 超出范围 [1..${itemCount}]`, normalized }
      }
    }
  }

  return { valid: true, normalized, itemCount }
}

interface TokenGroup {
  type: 'group' | 'op'
  text: string
}

function splitTopLevel(expr: string): TokenGroup[] {
  const out: TokenGroup[] = []
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
        out.push({ type: 'group', text: buf.trim() })
        buf = ''
      }
      depth++
      if (depth > 1) buf += ch
      continue
    }
    if (ch === ')') {
      depth--
      if (depth === 0) {
        out.push({ type: 'group', text: buf.trim() })
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
          out.push({ type: 'group', text: buf.trim() })
          buf = ''
        }
        out.push({ type: 'op', text: rest.slice(0, 3) })
        i += 2
        continue
      }
      if (/[0-9]/.test(ch)) {
        buf += ch
        continue
      }
    } else {
      buf += ch
    }
  }
  if (buf.trim() !== '' && depth === 0) {
    out.push({ type: 'group', text: buf.trim() })
  }
  return out
}

function validateGroup(text: string): { valid: boolean; error?: string; numbers: number[] } {
  if (!text) return { valid: false, error: '空条件组', numbers: [] }
  if (text.includes('(') || text.includes(')')) {
    return { valid: false, error: '条件组内不允许嵌套括号', numbers: [] }
  }
  const tokens = text.split(/\s+/).filter((t) => t.length > 0)
  const numbers: number[] = []
  let seenAnd = false
  let seenOr = false
  for (const t of tokens) {
    if (t === 'AND') seenAnd = true
    else if (t === 'OR') seenOr = true
    else if (/^\d+$/.test(t)) numbers.push(Number(t))
    else return { valid: false, error: `非法 token: ${t}`, numbers: [] }
  }
  if (seenAnd && seenOr) return { valid: false, error: '同一组内不允许同时使用 AND 和 OR', numbers: [] }
  if (numbers.length === 0) return { valid: false, error: '条件组缺少数字', numbers: [] }
  return { valid: true, numbers }
}

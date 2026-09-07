/**
 * 表达式校验包装
 * - 客户端：复用 utils/condition-expression.validateExpression（括号配对 / AND·OR / 编号 1-N）
 * - 增强：补「大括号 {} 禁止」（原型 6 规则之一，原 util 未覆盖）
 * - 服务端：POST /expressions/validate 兜底（失败则 fail-open，不阻塞 UI）
 */
import { validateExpression } from '../../../../utils/condition-expression'
import { validateExpressionApi } from '../../../../api/recruitment-process'

export interface ExprCheck {
  valid: boolean
  error?: string
  empty?: boolean
}

export function useExpressionValidator() {
  /** 客户端实时校验（同步） */
  function clientValidate(expr: string | null | undefined, itemCount: number): ExprCheck {
    if (expr == null) return { valid: true, empty: true }
    const trimmed = String(expr).trim()
    if (trimmed === '') return { valid: true, empty: true }
    // 大括号嵌套禁止（原型规则）
    if (/[{}]/.test(trimmed)) {
      return { valid: false, error: '不允许使用大括号 {}' }
    }
    const r = validateExpression(trimmed, itemCount)
    return { valid: r.valid, error: r.error }
  }

  /** 服务端校验（异步，fail-open） */
  async function serverValidate(expr: string, maxId: number): Promise<ExprCheck> {
    try {
      const r = await validateExpressionApi(expr, maxId)
      return { valid: !!r?.valid, error: r?.error }
    } catch {
      return { valid: true }
    }
  }

  return { clientValidate, serverValidate }
}

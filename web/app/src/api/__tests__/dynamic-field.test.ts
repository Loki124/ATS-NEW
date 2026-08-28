import { describe, it, expect } from 'vitest'
import { extractApiError } from '../dynamic-field'

describe('extractApiError', () => {
  it('抽象 DRF UniqueTogetherValidator 文案（含字段错误数组）→ 命中业务友好兜底', () => {
    const e = {
      response: {
        data: {
          success: false,
          code: 'invalid',
          message: '请求处理失败',
          errors: {
            non_field_errors: ['字段 bu, position, level, dimension, indicator, year, is_active 必须能构成唯一集合。'],
          },
        },
      },
    }
    const out = extractApiError(e, '保存失败')
    expect(out).not.toMatch(/必须能构成唯一集合/)
    expect(out).toMatch(/已存在同名记录/)
  })

  it('抽象 DRF 文案（嵌套在 dict 里）→ 仍命中业务友好兜底', () => {
    const e = {
      response: {
        data: {
          success: false,
          errors: {
            detail: [{ message: 'The fields {a, b} must make a unique set.' }],
          },
        },
      },
    }
    const out = extractApiError(e, '保存失败')
    expect(out).toMatch(/已存在同名记录/)
  })

  it('普通字段级错误 → 展开 join', () => {
    const e = {
      response: {
        data: {
          success: false,
          errors: { dimension: ['请先选择「维度」后再保存'] },
        },
      },
    }
    expect(extractApiError(e, '保存失败')).toBe('请先选择「维度」后再保存')
  })

  it('errors 是普通字符串 → 直接返回', () => {
    const e = { response: { data: { errors: '某字段非法' } } }
    expect(extractApiError(e, 'fallback')).toBe('某字段非法')
  })

  it('无 errors / 无 message → 走 fallback', () => {
    const e = { response: { data: {} } }
    expect(extractApiError(e, 'fallback')).toBe('fallback')
  })

  it('回落到 data.message / data.detail', () => {
    expect(extractApiError({ response: { data: { message: 'm-msg' } } }, 'f')).toBe('m-msg')
    expect(extractApiError({ response: { data: { detail: 'd-msg' } } }, 'f')).toBe('d-msg')
  })

  it('完全没 e.response → 走 fallback', () => {
    expect(extractApiError({}, '保存失败')).toBe('保存失败')
  })
})

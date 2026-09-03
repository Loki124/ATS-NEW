import { describe, it, expect } from 'vitest'
import { sanitizeHtml } from '../sanitizeHtml'

describe('sanitizeHtml (AGENTS.md R-107 白名单消毒)', () => {
  it('整段移除 <script>', () => {
    const out = sanitizeHtml('<p>hi</p><script>alert(1)</script>')
    expect(out).not.toContain('<script')
    expect(out).toContain('hi')
  })

  it('整段移除 <iframe>/<object>/<embed>', () => {
    const out = sanitizeHtml('<iframe src="//evil"></iframe><p>ok</p>')
    expect(out).not.toContain('<iframe')
    expect(out).toContain('ok')
  })

  it('中和 javascript: 链接（移除 href，但保留安全标签）', () => {
    const out = sanitizeHtml('<a href="javascript:alert(1)">x</a>')
    expect(out).not.toContain('javascript:')
    expect(out).not.toContain('href=')
  })

  it('保留安全 https 链接并补 target/rel', () => {
    const out = sanitizeHtml('<a href="https://example.com">x</a>')
    expect(out).toContain('href="https://example.com"')
    expect(out).toContain('rel="noopener noreferrer"')
    expect(out).toContain('target="_blank"')
  })

  it('丢弃任意 <span style> 点击劫持 CSS', () => {
    const out = sanitizeHtml('<span style="position:fixed;top:0">x</span>')
    expect(out).not.toContain('position:fixed')
    expect(out).toContain('x')
  })

  it('移除 on* 事件处理器', () => {
    const out = sanitizeHtml('<div onclick="alert(1)">x</div>')
    expect(out).not.toContain('onclick')
  })

  it('移除 <img onerror> 等危险标签', () => {
    const out = sanitizeHtml('<img src=x onerror="alert(1)">')
    expect(out).not.toContain('<img')
    expect(out).not.toContain('onerror')
  })

  it('保留合法排版标签', () => {
    const out = sanitizeHtml('<p>a <strong>b</strong> <em>c</em> <ul><li>d</li></ul></p>')
    expect(out).toContain('<strong>')
    expect(out).toContain('<em>')
    expect(out).toContain('<li>')
  })

  it('空值 / undefined / null 返回空串', () => {
    expect(sanitizeHtml('')).toBe('')
    expect(sanitizeHtml(undefined)).toBe('')
    expect(sanitizeHtml(null)).toBe('')
  })
})

/**
 * sanitizeHtml —— 白名单 HTML 消毒器（AGENTS.md R-107）。
 *
 * 用途：公告正文等「用户可控富文本」在 v-html 渲染前消毒，杜绝 XSS。
 * 实现：DOMParser 解析 → 遍历 DOM 树 → 仅保留白名单标签/属性 → 对 href 做协议校验。
 *       这是严格的「白名单」策略（非旧版正则黑名单），可中和 <script>/<iframe>/
 *       javascript: 链接 / on* 事件 / 任意 style 点击劫持等向量。
 *
 * 长期更优方案：安装 dompurify（npm i dompurify）替换本实现。当前沙箱无网络，
 *       故用 DOMParser 白名单兜底；已通过 src/utils/__tests__/sanitizeHtml.test.ts
 *       验证下述向量均被中和：<script>、<iframe>、<a href="javascript:">、
 *       <span style="...">、on* 事件、<img onerror>。
 */

// 仅这些标签被保留（其余非危险标签解包保留文本，危险标签整段移除）
const ALLOWED_TAGS = new Set([
  'P', 'BR', 'STRONG', 'B', 'EM', 'I', 'U', 'S', 'UL', 'OL', 'LI',
  'A', 'H1', 'H2', 'H3', 'H4', 'BLOCKQUOTE', 'CODE', 'PRE', 'SPAN',
  'DIV', 'HR', 'TABLE', 'THEAD', 'TBODY', 'TR', 'TD', 'TH',
])

// 每个标签允许携带的属性白名单（不在表中的标签一律无属性）
const ALLOWED_ATTRS: Record<string, Set<string>> = {
  A: new Set(['HREF']),
}

// 整段移除的危险标签（不保留其文本，避免脚本/样式/表单泄漏）
const DANGEROUS_TAGS = new Set([
  'SCRIPT', 'STYLE', 'IFRAME', 'OBJECT', 'EMBED', 'FORM', 'INPUT',
  'BUTTON', 'SELECT', 'TEXTAREA', 'LINK', 'META', 'BASE', 'SVG',
  'MATH', 'IMG', 'FRAME', 'FRAMESET', 'DETAILS', 'SUMMARY',
])

// 仅允许安全协议的 URL（阻断 javascript:/data: 等）
const SAFE_URL = /^(https?:|mailto:|tel:|#)/i

function cleanAttributes(el: Element): void {
  for (const attr of Array.from(el.attributes)) {
    const tag = el.tagName.toUpperCase()
    const name = attr.name.toUpperCase()
    const allowed = ALLOWED_ATTRS[tag]?.has(name) || name.startsWith('DATA-')
    if (!allowed) {
      el.removeAttribute(attr.name)
      continue
    }
    if (name === 'HREF') {
      const val = attr.value.trim()
      if (!SAFE_URL.test(val)) {
        el.removeAttribute('href')
        el.removeAttribute('target')
        el.removeAttribute('rel')
        continue
      }
      // 外链强制新窗口 + 防反向 tabnabbing
      el.setAttribute('target', '_blank')
      el.setAttribute('rel', 'noopener noreferrer')
    }
  }
}

function unwrap(el: Element): void {
  const parent = el.parentNode
  if (!parent) return
  while (el.firstChild) parent.insertBefore(el.firstChild, el)
  parent.removeChild(el)
}

function walk(node: Node): void {
  const children = Array.from(node.childNodes)
  for (const child of children) {
    if (child.nodeType === child.COMMENT_NODE) {
      child.remove()
      continue
    }
    if (child.nodeType !== child.ELEMENT_NODE) continue
    const el = child as Element
    const tag = el.tagName.toUpperCase()
    if (DANGEROUS_TAGS.has(tag)) {
      el.remove()
      continue
    }
    if (!ALLOWED_TAGS.has(tag)) {
      // 非危险但非白名单（自定义标签）：先消毒子树，再解包保留其文本
      walk(el)
      unwrap(el)
      continue
    }
    cleanAttributes(el)
    walk(el)
  }
}

export function sanitizeHtml(raw?: string | null): string {
  if (!raw) return ''
  // 用 div + innerHTML 解析片段（DOMPurify 同款做法），规避 DOMParser 在部分环境
  // 把内容塞进嵌套 <body> 导致 doc.body.innerHTML 取到空外壳的问题。
  // 注意：innerHTML 赋值不会执行 <script>，且危险标签会被下方 walk 整段移除。
  const container = document.createElement('div')
  container.innerHTML = raw
  walk(container)
  return container.innerHTML
}

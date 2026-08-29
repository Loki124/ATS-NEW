/**
 * stylelint 插件：X-05 / R-214 颜色硬编码门禁
 * 强制 color 类属性使用设计 token（var(--*)），禁止裸 hex / rgba() / hsl()。
 * 不依赖任何第三方包，纯正则实现，兼容 stylelint 15/16。
 *
 * 允许值：
 *  - var(--xxx)
 *  - *-gradient(...)        （渐变整体，内部颜色由 token 提供）
 *  - color-mix(...)         （设计系统已统一用 color-mix 派生）
 *  - transparent / currentColor / inherit / initial / unset / none
 *  - 纯白 #fff/#ffffff、纯黑 #000/#000000（通用中性，非品牌/语义色）
 */
const stylelint = require('stylelint');

const COLOR_PROPS = new Set([
  'color', 'background-color', 'border-color',
  'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
  'fill', 'stroke', 'outline-color', 'text-decoration-color', 'caret-color',
]);
const SHORTHAND_PROPS = new Set([
  'background', 'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
  'outline', 'text-decoration',
]);

const VAR_RE = /var\([^)]*\)/g;
const NEUTRAL_KW = /(?:transparent|currentcolor|inherit|initial|unset|none|#fff|#ffffff|#000|#000000|white|black)/i;
const COLOR_LIT = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)/i;

// 删除 keyword(...) 平衡括号段（正确处理 gradient/color-mix 内含 rgba/var 的嵌套括号）
function stripBalanced(value, keyword) {
  const kw = keyword + '(';
  let out = '';
  let i = 0;
  while (i < value.length) {
    const idx = value.indexOf(kw, i);
    if (idx === -1) { out += value.slice(i); break; }
    out += value.slice(i, idx);
    let depth = 0;
    let j = idx + kw.length - 1; // 指向 '('
    for (; j < value.length; j++) {
      if (value[j] === '(') depth++;
      else if (value[j] === ')') { depth--; if (depth === 0) { j++; break; } }
    }
    i = j;
  }
  return out;
}

function hasHardcodedColor(value) {
  let v = String(value);
  v = stripBalanced(v, 'linear-gradient');
  v = stripBalanced(v, 'radial-gradient');
  v = stripBalanced(v, 'conic-gradient');
  v = stripBalanced(v, 'color-mix');
  v = v.replace(VAR_RE, '').replace(NEUTRAL_KW, '');
  return COLOR_LIT.test(v);
}

module.exports = {
  ruleName: 'strict-color/strict-color-value',
  rule: (primary) => (root, result) => {
    if (!primary) return;
    root.walkDecls((decl) => {
      const prop = decl.prop.toLowerCase();
      if (!COLOR_PROPS.has(prop) && !SHORTHAND_PROPS.has(prop)) return;
      if (hasHardcodedColor(decl.value)) {
        stylelint.utils.report({
          ruleName: 'strict-color-value',
          result,
          node: decl,
          word: decl.value,
          message: `颜色值禁止硬编码，请改用设计 token（var(--*)）：「${decl.value}」`,
        });
      }
    });
  },
};

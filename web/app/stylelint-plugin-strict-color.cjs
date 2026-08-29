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
const GRAD_RE = /(?:linear|radial|conic)-gradient\([^)]*\)/g;
const MIX_RE = /color-mix\([^)]*\)/g;
const NEUTRAL_KW = /(?:transparent|currentcolor|inherit|initial|unset|none|#fff|#ffffff|#000|#000000|white|black)/i;
const COLOR_LIT = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)/i;

function hasHardcodedColor(value) {
  let v = String(value)
    .replace(VAR_RE, '')
    .replace(GRAD_RE, '')
    .replace(MIX_RE, '')
    .replace(NEUTRAL_KW, '');
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

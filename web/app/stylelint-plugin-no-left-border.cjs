/**
 * stylelint 插件：X-20 卡片禁止左侧边框线
 *
 * 背景: 卡片左侧的彩色状态条（border-left: 3px solid var(--c-*)）把「颜色」
 *       变成了唯一的状态通道 —— 既与 R-109（错误不得仅靠颜色表达）相悖，
 *       又让同一视图出现两种卡片语言（带条 / 不带条）。
 *       2026-10-21 起全站卡片统一改为「1px 描边 + 标签/图标/文字」表达状态。
 *
 * 判定: 组件内任何 border-left / border-left-width / border-left-color /
 *       border-left-style 声明都视为违规，除非命中下方白名单。
 *       白名单是 fail-closed 的 —— 新增左侧线必须先在 PR 里登记原因，
 *       评审能看见「谁、为什么、在哪」。
 *
 * 豁免场景（非卡片左侧线，登记在案）:
 *   1. 树形层级引导线        —— 表达父子关系，不是卡片描边
 *   2. 行内分栏 hairline     —— 列与列之间的分隔线
 *   3. 引用块 / 提示块        —— 强调块本身不是卡片
 *   4. 表格单元状态条        —— 单元格内部指示
 *   5. 分组分隔线 / 标题强调条 —— 子项分组与标题层级
 *
 * 逃生舱: 确需新增时，用原生 stylelint 注释并写明原因：
 *   /* stylelint-disable-next-line no-left-border/no-left-border -- 原因 * /
 *
 * 不依赖任何第三方包，纯正则实现，兼容 stylelint 15/16。
 */
const stylelint = require('stylelint');

const LEFT_BORDER_PROPS = new Set([
  'border-left',
  'border-left-width',
  'border-left-color',
  'border-left-style',
]);

/**
 * 非卡片场景白名单。file 用后缀匹配（result.opts.from 是相对路径），
 * selector 用正则匹配整条选择器。reason 会随告警一起输出，便于评审追溯。
 */
const ALLOWLIST = [
  {
    file: 'src/components/ConditionTreeEditor.vue',
    selector: /^\.tree-item\b/,
    reason: '树形层级引导线（表达父子关系，非卡片描边）',
  },
  {
    file: 'src/components/SafeHtml.vue',
    selector: /blockquote/,
    reason: '引用块强调线（引用块不是卡片）',
  },
  {
    file: 'src/pages/candidate/CandidateList.vue',
    selector: /^\.(row-mid|row-right)\b/,
    reason: '行内分栏 hairline 分隔线（列间分隔，非卡片左侧边）',
  },
  {
    file: 'src/components/role/ModuleActionCard.vue',
    selector: /action-checks/,
    reason: '权限项分组分隔线（子项分组，非卡片描边）',
  },
  {
    file: 'src/components/RuleConfigDrawer.vue',
    selector: /^\.rc-section-title\b/,
    reason: '区块标题强调条（标题层级，非卡片描边）',
  },
  {
    file: 'src/components/RuleConfigDrawer.vue',
    selector: /^\.rc-rollover-cell/,
    reason: '表格单元状态条（单元格内指示，非卡片描边）',
  },
  {
    file: 'src/components/role/PermissionCodeModal.vue',
    selector: /^\.pc-module-title\b/,
    reason: '模块标题强调条（标题层级，非卡片描边）',
  },
  {
    file: 'src/pages/settings/MetricsWorkspace.vue',
    selector: /^\.tpl-(inherit|readout)\b/,
    reason: '模板提示块强调线（提示块不是卡片）',
  },
  {
    file: 'src/pages/settings/ExternalSettings.vue',
    selector: /^\.sub-title\b/,
    reason: '子标题强调条（标题层级，非卡片描边）',
  },
  {
    file: 'src/components/campus/PersonProfileModal.vue',
    selector: /^\.pp-section-title\b/,
    reason: '个人档案详情区块标题强调条（标题层级，非卡片描边）',
  },
  {
    file: 'src/pages/campus/RotationArrangement.vue',
    selector: /^\.form-section-title\b/,
    reason: '轮岗安排表单分组标题强调条（标题层级，非卡片描边）',
  },
];

/** 取出声明所属规则的选择器文本（兼容 @media 等嵌套结构）。 */
function selectorOf(decl) {
  let node = decl.parent;
  while (node) {
    if (node.type === 'rule' && node.selector) return node.selector;
    node = node.parent;
  }
  return '';
}

function isAllowlisted(file, selector) {
  return ALLOWLIST.some(
    (entry) =>
      file.endsWith(entry.file) && entry.selector.test(selector),
  );
}

module.exports = {
  ruleName: 'no-left-border/no-left-border',
  rule: (primary) => (root, result) => {
    if (!primary) return;
    const file = (result.opts && result.opts.from) || '';
    root.walkDecls((decl) => {
      const prop = decl.prop.toLowerCase();
      if (!LEFT_BORDER_PROPS.has(prop)) return;
      const selector = selectorOf(decl);
      if (isAllowlisted(file, selector)) return;
      stylelint.utils.report({
        ruleName: 'no-left-border/no-left-border',
        result,
        node: decl,
        word: decl.prop,
        message:
          'X-20：卡片禁止左侧边框线（border-left）。' +
          '状态请用「标签 / 徽标 / 图标 + 文字」表达（须满足 R-109 双通道）。' +
          '确属非卡片场景时，在 stylelint-plugin-no-left-border.cjs 的 ALLOWLIST 登记原因，' +
          '或使用 /* stylelint-disable-next-line no-left-border/no-left-border -- 原因 */。',
      });
    });
  },
};

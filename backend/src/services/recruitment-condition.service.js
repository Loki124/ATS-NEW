/**
 * 招聘条件求值服务 - PRD #5
 *
 * 复用 referral rule-evaluator 模式 (rule-evaluator.service.js)
 * 树形结构求值 - 最多 3 级嵌套
 *
 * 表达式示例：
 *   (1 or 2) and (3 or 4)
 *
 * 入参：
 *   items: ConditionItem[] (树形, 最多 3 级)
 *   matchType: 'ALL' | 'ANY'
 *   context: {
 *     candidate: { age, gender, marriage, highestEducation, firstEducation, job, level, ... },
 *     stageStatuses: { [stageId]: 'PASS' | 'FAIL' | 'PENDING' | ... }
 *   }
 *
 * 返回：
 *   { passed: boolean, failedItems: ConditionItem[] }
 */

const OPERATORS = {
  GT: (a, b) => Number(a) > Number(b),
  GTE: (a, b) => Number(a) >= Number(b),
  LT: (a, b) => Number(a) < Number(b),
  LTE: (a, b) => Number(a) <= Number(b),
  EQ: (a, b) => a == b,
  BETWEEN: (a, [lo, hi]) => Number(a) >= Number(lo) && Number(a) <= Number(hi),
  IN: (a, arr) => Array.isArray(arr) && arr.includes(a),
  NOT_IN: (a, arr) => Array.isArray(arr) && !arr.includes(a),
  CONTAINS: (a, b) => String(a ?? '').includes(String(b ?? '')),
  NOT_CONTAINS: (a, b) => !String(a ?? '').includes(String(b ?? '')),
  EMPTY: (a) => a === null || a === undefined || a === '' || (Array.isArray(a) && a.length === 0),
  NOT_EMPTY: (a) => !(a === null || a === undefined || a === '' || (Array.isArray(a) && a.length === 0)),
};

/**
 * 从 context 取出字段值
 * STAGE_STATUS 类型: 从 context.stageStatuses[refStageId] 取
 * 其它: 从 context.candidate[field] 取
 */
function getFieldValue(item, context) {
  if (item.field === 'STAGE_STATUS' && item.refStageId) {
    return context.stageStatuses?.[item.refStageId];
  }
  return context.candidate?.[item.field];
}

/**
 * 评估单条 ConditionItem
 */
function evaluateItem(item, context) {
  const value = getFieldValue(item, context);
  const opFn = OPERATORS[item.operator];
  if (!opFn) {
    // 未知 operator - 视为不通过
    return { passed: false, reason: `未知运算符: ${item.operator}` };
  }
  let passed;
  try {
    passed = opFn(value, item.value);
  } catch (e) {
    passed = false;
  }
  return { passed, value, item };
}

/**
 * 评估一个"分支" - 从根或子根开始
 * 1. 找出根的子项 (parentId = root.id)
 * 2. 评估每个子项
 * 3. 根的 relationToParent 是 null, 子项之间用 relationToParent 连接
 *    例如: (1 or 2) and (3 or 4)
 *    - 1 relationToParent=OR 2  -> (1 or 2)
 *    - 3 relationToParent=OR 4  -> (3 or 4)
 *    - (1 or 2) AND (3 or 4)  -> 整体
 *
 * 简化实现: 把子项扁平化为一个 list, 按 (root 关系: OR/AND) 评估
 *   if root.relation is OR: any-of
 *   if root.relation is AND: all-of
 */
function evaluateBranch(root, items, context, failedItems) {
  if (!root) return { passed: true };
  const children = items.filter((it) => it.parentId === root.id);
  if (children.length === 0) {
    // 叶子 (没有子项 = 它自己就是叶子)
    const r = evaluateItem(root, context);
    if (!r.passed) failedItems.push({ ...root, actualValue: r.value });
    return r;
  }
  // 有子项
  // children 之间的逻辑由第一个 child 的 relationToParent 决定 (从父来看)
  const logic = children[0].relationToParent || 'AND';
  const results = children.map((c) => evaluateBranch(c, items, context, failedItems));
  if (logic === 'OR') {
    return { passed: results.some((r) => r.passed) };
  }
  return { passed: results.every((r) => r.passed) };
}

/**
 * 主入口: 评估整棵条件树
 *   items: 全部 ConditionItem (含 parent 关系)
 *   matchType: 'ALL' | 'ANY'
 *   context: 见顶部说明
 */
export function evaluateConditionTree(items, matchType, context) {
  if (!items || items.length === 0) return { passed: true, failedItems: [] };
  const failedItems = [];
  // 找出所有根 (parentId 为 null) - 通常只有 1 个
  const roots = items.filter((it) => !it.parentId);
  const results = roots.map((r) => evaluateBranch(r, items, context, failedItems));
  const passed = matchType === 'ALL' ? results.every((r) => r.passed) : results.some((r) => r.passed);
  return { passed, failedItems };
}

/**
 * 构建失败提示 (#5.5 #1810)
 *   - 如果 condition 有自定义 prompt 字段, 优先用
 *   - 否则用默认模板: "未满足以下[全部/任一]条件: ..."
 */
export function buildFailedPrompt(items, failedItems, context, customPrompt) {
  if (customPrompt) return customPrompt;
  if (!failedItems || failedItems.length === 0) return null;
  const fieldLabels = {
    AGE: '年龄',
    GENDER: '性别',
    MARRIAGE: '婚育情况',
    HIGHEST_EDU: '最高学历',
    HIGHEST_EDU_DURATION: '最高学历教育时长',
    HIGHEST_EDU_SCHOOL_TAG: '最高学历院校标签',
    FIRST_EDU: '第一学历',
    FIRST_EDU_DURATION: '第一学历教育时长',
    FIRST_EDU_SCHOOL_TAG: '第一学历院校标签',
    JOB: '职务',
    LEVEL: '职级',
    COMPANY: '任职公司',
    RESUME_SOURCE: '简历来源',
    RESUME_CHANNEL: '简历渠道',
    STAGE_STATUS: '阶段状态',
  };
  const opLabels = {
    GT: '大于',
    GTE: '大于等于',
    LT: '小于',
    LTE: '小于等于',
    EQ: '等于',
    BETWEEN: '介于',
    IN: '包含',
    NOT_IN: '不包含',
    CONTAINS: '包含',
    NOT_CONTAINS: '不包含',
    EMPTY: '为空',
    NOT_EMPTY: '不为空',
  };
  const conditions = failedItems
    .map((it) => {
      const field = fieldLabels[it.field] || it.field;
      const op = opLabels[it.operator] || it.operator;
      const val = Array.isArray(it.value) ? it.value.join('/') : it.value;
      return `${field} ${op} ${val}`;
    })
    .join('; ');
  return `未满足以下条件: ${conditions}`;
}

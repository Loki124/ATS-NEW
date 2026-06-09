/**
 * 条件表达式校验服务 - PRD G38 (Plan L Task 3)
 *
 * 校验规则 (#5.4 表达式校验):
 *   1. 表达式可以为空 (空 = 全部满足) - { valid: true, empty: true }
 *   2. 数字范围: 仅允许 [1..N], N = itemCount
 *   3. AND / OR 必须大写
 *   4. 括号必须成对出现
 *   5. 同一括号内不允许同时出现 AND 和 OR
 *   6. 括号不允许嵌套 (顶层只能是一层)
 *   7. 数字之间必须用 AND/OR/括号分隔
 *   8. 表达式不能以 AND/OR 开头或结尾
 *
 * 返回: { valid: boolean, error?: string, normalized?: string, itemCount?: number }
 */

const VALID_OPS = ['AND', 'OR'];

/**
 * 主入口: 校验表达式
 * @param {string} expr - 表达式 (e.g. "(1 and 2) or (3 and 4)")
 * @param {number} itemCount - 条件项总数 (数字必须落在 [1..itemCount])
 * @returns {{ valid: boolean, error?: string, normalized?: string, empty?: boolean }}
 */
export function validateExpression(expr, itemCount) {
  // 1. 空检查
  if (expr == null) {
    return { valid: true, empty: true };
  }
  const trimmed = String(expr).trim();
  if (trimmed === '') {
    return { valid: true, empty: true };
  }

  // 2. 规范化: 替换 and/or 为 AND/OR (宽容大小写)
  const normalized = trimmed
    .replace(/\bAND\b/gi, 'AND')
    .replace(/\bOR\b/gi, 'OR');

  // 3. 字符白名单: 数字, 空格, 括号, AND, OR
  if (!/^[\d\s()ANDOR]+$/.test(normalized)) {
    return {
      valid: false,
      error: '表达式包含非法字符 (仅允许数字、空格、括号、AND/OR)',
      normalized,
    };
  }

  // 4. 括号成对检查
  const openCount = (normalized.match(/\(/g) || []).length;
  const closeCount = (normalized.match(/\)/g) || []).length;
  if (openCount !== closeCount) {
    return {
      valid: false,
      error: `括号不匹配: ${openCount} 个左括号 vs ${closeCount} 个右括号`,
      normalized,
    };
  }
  if (openCount > 0) {
    // 括号嵌套检查 - 用栈
    const stack = [];
    for (let i = 0; i < normalized.length; i++) {
      if (normalized[i] === '(') stack.push(i);
      if (normalized[i] === ')') {
        if (stack.length === 0) {
          return { valid: false, error: '多余的右括号', normalized };
        }
        stack.pop();
      }
    }
    if (stack.length > 0) {
      return { valid: false, error: '未闭合的左括号', normalized };
    }
  }

  // 5. 拆分顶层括号组 vs 顶层 AND/OR 连接
  //    规则: 表达式 = (group1) (op) (group2) (op) (group3) ...
  //          - group 必须是 (数字 + 内部 AND/OR 链) 或 单数字
  //          - op 必须在 group 之间
  const groups = splitTopLevel(normalized);
  if (groups.length === 0) {
    return { valid: false, error: '表达式解析失败', normalized };
  }

  // 6. 顶层不能是 AND/OR
  if (groups[0].type === 'op') {
    return { valid: false, error: '表达式不能以 AND/OR 开头', normalized };
  }
  if (groups[groups.length - 1].type === 'op') {
    return { valid: false, error: '表达式不能以 AND/OR 结尾', normalized };
  }

  // 7. 顶层 op/group 交替
  for (let i = 1; i < groups.length; i += 2) {
    if (groups[i].type !== 'op') {
      return { valid: false, error: '缺少 AND/OR 连接符', normalized };
    }
  }
  for (let i = 2; i < groups.length; i += 2) {
    if (groups[i].type !== 'group') {
      return { valid: false, error: '缺少条件组', normalized };
    }
  }

  // 8. 每个 group 内部校验: 不允许嵌套括号, 数字 + 内部 AND/OR
  const allNumbers = [];
  for (const g of groups) {
    if (g.type !== 'group') continue;
    const r = validateGroup(g.text);
    if (!r.valid) {
      return { valid: false, error: `条件组 [${g.text}] 非法: ${r.error}`, normalized };
    }
    allNumbers.push(...r.numbers);
  }

  // 9. 数字范围检查
  if (typeof itemCount === 'number' && itemCount >= 0) {
    for (const n of allNumbers) {
      if (n < 1 || n > itemCount) {
        return {
          valid: false,
          error: `数字 ${n} 超出范围 [1..${itemCount}]`,
          normalized,
        };
      }
    }
  }

  return { valid: true, normalized, itemCount };
}

/**
 * 拆分顶层表达式为 [group|op, group|op, group, ...]
 *   e.g. "(1 and 2) or (3 and 4)"
 *   → [ {type:'group', text:'1 and 2'}, {type:'op', text:'OR'}, {type:'group', text:'3 and 4'} ]
 */
function splitTopLevel(expr) {
  const out = [];
  let buf = '';
  let depth = 0;
  let lastWasOp = false;

  for (let i = 0; i < expr.length; i++) {
    const ch = expr[i];
    if (ch === ' ') {
      if (buf) { buf += ch; }
      continue;
    }
    if (ch === '(') {
      if (depth === 0) {
        // 顶层 '(' - 之前是 group, 现在是 group 起点
        if (buf.trim() !== '') {
          // buf 是数字 (无括号 group) - flush
          out.push({ type: 'group', text: buf.trim() });
          buf = '';
        }
      }
      depth++;
      if (depth > 1) {
        // 嵌套 - 后续会在 validateGroup 检测, 但这里仍要记录
        buf += ch;
      }
      continue;
    }
    if (ch === ')') {
      depth--;
      if (depth === 0) {
        // 顶层 ')' - 关闭 group
        out.push({ type: 'group', text: buf.trim() });
        buf = '';
        lastWasOp = false;
      } else {
        buf += ch;
      }
      continue;
    }
    if (depth === 0) {
      // 顶层 - 找 AND/OR token (大小写不敏感)
      const rest = expr.slice(i);
      const upper = rest.toUpperCase();
      if (upper.startsWith('AND') || upper.startsWith('OR')) {
        // flush 之前 buf
        if (buf.trim() !== '') {
          out.push({ type: 'group', text: buf.trim() });
          buf = '';
        }
        out.push({ type: 'op', text: upper.slice(0, 3) });
        i += 2; // skip 3 chars
        lastWasOp = true;
        continue;
      }
      if (/[0-9]/.test(ch)) {
        buf += ch;
        lastWasOp = false;
        continue;
      }
    } else {
      buf += ch;
    }
  }
  if (buf.trim() !== '' && depth === 0) {
    out.push({ type: 'group', text: buf.trim() });
  }
  return out;
}

/**
 * 校验单个 group 内部
 *   形如 "1 and 2 and 3" 或 "5"
 *   不允许嵌套括号, 不允许同组内 AND+OR 混用
 */
function validateGroup(text) {
  if (!text) return { valid: false, error: '空条件组' };
  if (text.includes('(') || text.includes(')')) {
    return { valid: false, error: '条件组内不允许嵌套括号' };
  }
  // 拆分数字和 op
  const tokens = text.split(/\s+/).filter((t) => t.length > 0);
  const numbers = [];
  let seenAnd = false;
  let seenOr = false;
  for (const t of tokens) {
    if (t === 'AND') {
      seenAnd = true;
    } else if (t === 'OR') {
      seenOr = true;
    } else if (/^\d+$/.test(t)) {
      numbers.push(Number(t));
    } else {
      return { valid: false, error: `非法 token: ${t}` };
    }
  }
  if (seenAnd && seenOr) {
    return { valid: false, error: '同一组内不允许同时使用 AND 和 OR' };
  }
  if (numbers.length === 0) {
    return { valid: false, error: '条件组缺少数字' };
  }
  return { valid: true, numbers };
}

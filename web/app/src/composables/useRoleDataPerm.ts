/**
 * useRoleDataPerm.ts — 角色数据权限抽屉的逻辑层（取数 / 草稿 / 脏检查 / 校验 / 提交 / 预览）。
 *
 * 同时导出纯函数:
 *   - validateExpr(expr, maxIndex) -> 错误原因 | null  （设计文档 §2.4 六条语法规则）
 *   - renderExpr / previewOf         —— 规则弹窗底部布尔表达式预览句
 *   - newGroup / newCondition        —— 新建骨架（至少 1 组 × 1 条件）
 */
import { computed, ref } from 'vue';
import type { Ref } from 'vue';
import {
  getRoleDataPerm,
  getRoleDataPermOptions,
  saveRoleDataPerm,
  type DataPermMode,
  type ModulePerm,
  type ModuleOption,
  type PermCondition,
  type PermConditionGroup,
  type RoleDataPermPayload,
  type PermValue,
  type AttributeField,
  type DynamicRelation,
  type DynamicSourceKey,
  type WriteMode,
  type WritePerm,
  type ActionDictItem,
  type ActionPreset,
} from '@/api/data-permission'

// 重新导出 API 层类型，供依赖本 composable 的组件统一从此处 import
export type {
  DataPermMode, ModulePerm, ModuleOption, PermCondition, PermConditionGroup,
  RoleDataPermPayload, Operator, DimensionMeta, PermValue, AttributeField,
  DynamicRelation, DynamicSourceKey, WriteMode, WritePerm,
  ActionDictItem, ActionPreset,
} from '@/api/data-permission';

export const MODULE_KEYS = ['demand', 'process', 'position', 'candidate', 'talent'] as const;

export const DIMENSION_LABELS: Record<string, string> = {
  dept: '部门',
  owner: '负责人',
  creator: '创建人',
  unit: '管理单元',
  process: '招聘流程',
  // 预览句兜底映射（renderCondition 只拿得到 dimension key，拿不到模块标签）。
  // 与后端 DIMENSION_META['lock_owner'].label 对齐；缺了它预览会裸渲染 key。
  lock_owner: '简历锁定人',
};

/** 属性条件运算符 -> 中文标签（与后端 attribute_fields.UNIFIED_OPERATOR_LABELS 对齐）。 */
export const ATTRIBUTE_OP_LABELS: Record<string, string> = {
  EQ: '等于', NEQ: '不等于', GT: '大于', GTE: '大于等于',
  LT: '小于', LTE: '小于等于', BETWEEN: '区间',
  IN: '属于', NOT_IN: '不属于', IS_EMPTY: '为空', IS_NOT_EMPTY: '不为空',
};

/** 无需业务值的运算符（空值类）。 */
export const ATTR_NOVALUE_OPS = new Set(['IS_EMPTY', 'IS_NOT_EMPTY']);
/**
 * 关系维度无需业务值的运算符（简历锁定人的「为空/不为空」）。
 *
 * 后端 `expr_compiler._compile_lock_owner_condition` 对这两个运算符忽略 values，
 * 保存校验（compile 的 lock_owner 空值分支）也整体放行 —— 前端校验必须同口径，
 * 否则「选为空 → 保存」会被「请为每条条件选择业务值」误拦（兵哥 2026-10-15：
 * 「锁定人为空/不为空为什么选不了」的后半段断链）。
 */
export const REL_NOVALUE_OPS = new Set(['is_empty', 'is_not_empty']);
/** 业务值为集合（多选）的运算符。 */
export const ATTR_LIST_OPS = new Set(['IN', 'NOT_IN']);

/**
 * 动态取值来源 -> 中文（与后端 context_resolvers.DYNAMIC_SOURCE_KEYS 对齐）。
 *
 * 🔴 A档文案修正（2026-10-15）：原文写「**我的**负责部门」，在权限配置语境下
 * "我的"指向不明 —— 管理员配置时看这三个选项，语义必须是**运行时登录的那个成员**，
 * 而不是配置人自己。证据：后端 responsible_department_ids(user) 的入参 user 是
 * 运行时登录用户（user.department ∪ Department.leader=user），每人取值不同。
 *
 * 🔴 同日二次修正（兵哥「该成员本人改为当前登录用户」）：
 *   currentUser.id 原为「该成员本人」，在「创建人/负责人」维度里读起来像在讲
 *   第三人，而它的实际语义就是**当前正在操作系统的登录者本人**（编译为 pk__in=[当前用户]），
 *   故改为「当前登录用户」。用词与系统其它位置（操作日志 / 登录态）保持一致，
 *   管理员不必在同一产品里记两套说法。
 */
export const DYNAMIC_SOURCE_LABELS: Record<string, string> = {
  'currentUser.departments': '当前登录用户负责的部门',
  'currentUser.deptSubtree': '当前登录用户负责的部门及其下级',
  'currentUser.id': '当前登录用户',
  'currentUser.managedUnits': '该成员的管理单元',
};

/**
 * 动态取值来源的补充说明（tooltip / 行内提示用）。
 * 🔴 「当前登录用户」不需要提示 —— 它字面已自解释，再加"非管理员所在部门"反而
 * 让人以为这里也有歧义；只有「该成员的负责部门」这类需要点明的才给说明。
 */
export const DYNAMIC_SOURCE_NOTES: Record<string, string> = {
  'currentUser.departments': '运行时取该角色成员的负责部门',
  'currentUser.deptSubtree': '运行时取该角色成员的负责部门及其下级',
  'currentUser.id': '',
  'currentUser.managedUnits': '运行时取该角色成员的管理单元',
};

/** 包含关系 -> 中文（与后端 context_resolvers.DYNAMIC_RELATIONS 对齐）。 */
export const DYNAMIC_RELATION_LABELS: Record<string, string> = {
  exact: '属于',
  in_subtree: '属于（含下级）',
  contains: '包含',
  overlap: '包含或属于',
};

/**
 * 按维度的可用动态来源（contextKeys）生成「取值来源」下拉选项（M03）。
 * dept 维度 -> 部门类来源；owner/creator -> currentUser.id；
 * unit -> currentUser.managedUnits。contextKeys 为空/缺省 = 该维度
 * 不支持动态取值（调用方不渲染切换器）。
 */
export function dynamicSourceOptions(contextKeys?: string[]) {
  return (contextKeys || []).map((k) => ({ label: DYNAMIC_SOURCE_LABELS[k] || k, value: k }))
}

/** 取值来源切换后的状态（纯函数，供弹窗写回草稿 + 单测断言）。 */
export interface ValueSourceState {
  valueSource: 'static' | 'dynamic';
  dynamicKey?: DynamicSourceKey;
  relation?: DynamicRelation;
}

/**
 * 由「取值来源下拉所选值」推导条件的新状态。
 *
 * @param selected 所选选项的 value —— 形态与 dynamicSourceOptions 产出的选项一致：
 *                'static' 或该维度的某个 contextKey（**不是** 'dynamic'）。
 * @param valueType 维度值类型；仅 'department' 具备 relation 包含关系语义。
 *
 * 纯函数，不改入参、不碰草稿 —— 调用方负责把结果写回 PermCondition。
 */
export function resolveValueSource(
  selected: string,
  valueType?: string,
): ValueSourceState {
  if (selected === 'static') {
    return { valueSource: 'static' };
  }
  return {
    valueSource: 'dynamic',
    // 关键：写用户实际选中的那个 key。取 contextKeys[0] 会把
    // 「我的负责部门及下级」静默降级成「我的负责部门」。
    dynamicKey: selected as DynamicSourceKey,
    relation: valueType === 'department' ? 'contains' : undefined,
  };
}

/** 可选包含关系（UI 下拉用）。 */
export const DYNAMIC_RELATION_OPTIONS = (
  Object.keys(DYNAMIC_RELATION_LABELS) as (keyof typeof DYNAMIC_RELATION_LABELS)[]
).map((k) => ({ label: DYNAMIC_RELATION_LABELS[k], value: k }));

// ===== 通用工具 =====

let _seq = 0;
export function uid(prefix = 'id'): string {
  return `${prefix}-${Date.now().toString(36)}-${(_seq++).toString(36)}`;
}

export function newCondition(
  kind: 'relationship' | 'attribute' = 'relationship',
  dimension = 'dept',
): PermCondition {
  // 属性条件分支**仅供存量数据反序列化**使用，不再有 UI 调用方新建它
  // （属性条件已下线，见 RuleConfigModal.vue 中的下线说明）。
  // 保留此分支是为了让从后端读回的 kind='attribute' 条件能被原样保留并回传，
  // 而不是被降级成 relationship 造成静默数据损坏。
  if (kind === 'attribute') {
    return {
      id: uid('c'),
      kind: 'attribute',
      operator: '',
      field: '',
      value: undefined,
      meta: { min: null, max: null },
      values: [],
    };
  }
  return { id: uid('c'), kind: 'relationship', dimension, operator: 'in', values: [] };
}

export function newGroup(): PermConditionGroup {
  return { id: uid('g'), expr: '1', conditions: [newCondition()] };
}

// ---------------------------------------------------------------------------
// 表达式校验（6 条语法规则，与后端 expr_compiler 等价）
// ---------------------------------------------------------------------------

type Tok = ['NUM', number] | ['OP', 'and' | 'or'] | ['PAREN', '(' | ')'];

function tokenize(expr: string): Tok[] | { error: string } {
  const tokens: Tok[] = [];
  let i = 0;
  const n = expr.length;
  while (i < n) {
    const c = expr[i];
    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') {
      i++;
      continue;
    }
    const code = c.codePointAt(0) ?? 0;
    if (code > 127) return { error: `非法字符 "${c}"（仅支持英文圆括号与 and/or）` };
    if (c === '(' || c === ')') {
      tokens.push(['PAREN', c]);
      i++;
      continue;
    }
    if (/[a-zA-Z]/.test(c)) {
      let j = i;
      while (j < n && /[a-zA-Z]/.test(expr[j])) j++;
      const word = expr.slice(i, j).toLowerCase();
      if (word !== 'and' && word !== 'or') return { error: `非法保留字 "${word}"（仅允许 and / or）` };
      tokens.push(['OP', word]);
      i = j;
      continue;
    }
    if (/[0-9]/.test(c)) {
      let j = i;
      while (j < n && /[0-9]/.test(expr[j])) j++;
      tokens.push(['NUM', parseInt(expr.slice(i, j), 10)]);
      i = j;
      continue;
    }
    return { error: `非法字符 "${c}"` };
  }
  return tokens;
}

/** 校验表达式（引用编号须 ∈ 1..maxIndex）。返回非法原因；合法返回 null。 */
export function validateExpr(expr: string, maxIndex: number): string | null {
  const trimmed = (expr || '').trim();
  if (!trimmed) return null; // 空表达式由调用方按默认处理
  const toks = tokenize(trimmed);
  if ('error' in toks) return toks.error;
  const res = parseFull(toks, 0, maxIndex);
  if (!res.valid) return res.error;
  if (res.pos !== toks.length) return '表达式存在多余内容';
  return null;
}

// 完整递归下降（校验 + 混用检测），返回 { valid, error, pos }
function parseFull(toks: Tok[], start: number, maxIndex: number) {
  let pos = start;
  let err: string | null = null;

  const atom = (depth: number): boolean => {
    if (pos >= toks.length) {
      err = '表达式不完整';
      return false;
    }
    const tok = toks[pos];
    if (tok[0] === 'PAREN' && tok[1] === '(') {
      if (depth >= 1) {
        err = '括号不可嵌套（最多一层）';
        return false;
      }
      pos++;
      if (!parseOr(depth + 1)) return false;
      if (pos >= toks.length || toks[pos][0] !== 'PAREN' || (toks[pos] as any)[1] !== ')') {
        err = '括号未闭合';
        return false;
      }
      pos++;
      return true;
    }
    if (tok[0] === 'NUM') {
      const num = tok[1];
      if (num < 1 || num > maxIndex) {
        err = `编号 ${num} 超出范围（应为 1..${maxIndex}）`;
        return false;
      }
      pos++;
      return true;
    }
    err = '表达式语法错误';
    return false;
  };

  const parseAnd = (depth: number): { andSeen: boolean } => {
    if (!atom(depth)) return { andSeen: false };
    let andSeen = false;
    while (pos < toks.length && toks[pos][0] === 'OP' && (toks[pos] as any)[1] === 'and') {
      andSeen = true;
      pos++;
      if (!atom(depth)) return { andSeen };
    }
    return { andSeen };
  };

  const parseOr = (depth: number): boolean => {
    const left = parseAnd(depth);
    if (!left.andSeen && err) return false;
    let orSeen = false;
    while (pos < toks.length && toks[pos][0] === 'OP' && (toks[pos] as any)[1] === 'or') {
      if (left.andSeen) {
        err = '同一括号层不能同时出现 and 与 or（需用括号分隔）';
        return false;
      }
      orSeen = true;
      pos++;
      const right = parseAnd(depth);
      if (!right.andSeen && err) return false;
      left.andSeen = left.andSeen || right.andSeen;
    }
    if (orSeen && left.andSeen) {
      err = '同一括号层不能同时出现 and 与 or（需用括号分隔）';
      return false;
    }
    return true;
  };

  const valid = parseOr(0);
  // 🔴 err 一旦被置位即为语法错误。关键漏判修复：`1 and` / `1 or 2 and` 这类
  // 「运算符结尾缺运算数」的表达式，parseAnd 会先记 andSeen=true 再因 atom 不完整报错，
  // 上面 `!left.andSeen && err` 守卫因 andSeen=true 不触发，但 err('表达式不完整') 已置位——
  // 旧逻辑靠 `if (!res.valid)` 判定，而此类表达式 res.valid 反被算成 true，于是被错误放行。
  // 后端 expr_compiler 对这类输入正确拒绝（已由序列化器守卫兜底），但前端也应在 typing 时
  // 立即标红，避免用户等到保存才撞 400。err 只在真实语法错误时被赋值，判非法无副作用。
  if (err) return { valid: false, error: err, pos };
  return { valid: true, error: null, pos };
}

// ---------------------------------------------------------------------------
// 预览句（布尔表达式 -> 可读中文）
// ---------------------------------------------------------------------------

function renderCondition(c: PermCondition): string {
  if (c.kind === 'attribute') {
    const fieldName = c.fieldName || c.field || '字段';
    const opLabel = ATTRIBUTE_OP_LABELS[c.operator] || c.operator;
    const v = c.value;
    if (c.operator === 'IS_EMPTY') return `${fieldName} 为空`;
    if (c.operator === 'IS_NOT_EMPTY') return `${fieldName} 不为空`;
    if (c.operator === 'BETWEEN') {
      const lo = c.meta?.min ?? '?';
      const hi = c.meta?.max ?? '?';
      return `${fieldName} 区间 [${lo}, ${hi}]`;
    }
    if (Array.isArray(v)) {
      const labels = v.map((x) =>
        x && typeof x === 'object' ? (x as PermValue).label : String(x),
      );
      return `${fieldName} ${opLabel} [${labels.join('、')}]`;
    }
    if (v && typeof v === 'object') {
      return `${fieldName} ${opLabel} [${(v as PermValue).label}]`;
    }
    return `${fieldName} ${opLabel} [${v ?? ''}]`;
  }
  // c.dimension 可空，直接用它做索引会命中 TS2538（undefined 不能作为索引类型）
  const dimKey = c.dimension ?? '';
  const dimLabel = DIMENSION_LABELS[dimKey] || dimKey;
  // 动态条件：值来自当前用户上下文，不是配置里选死的值
  if (c.valueSource === 'dynamic') {
    // 仅部门类维度有包含关系（relation）语义；user/unit 维度是「是」单义。
    // 缺省 relation 退化为 exact（与存量 operator='in' → 「属于」语义一致）。
    const rel = c.relation
      ? (DYNAMIC_RELATION_LABELS[c.relation] || '属于')
      : c.dimension === 'dept'
        ? '属于'
        : '是';
    const src = DYNAMIC_SOURCE_LABELS[c.dynamicKey || ''] || '当前用户';
    return `${dimLabel} ${rel} ${src}`;
  }
  // 无值运算符（简历锁定人的「为空/不为空」）没有业务值可罗列：直接渲染
  // 「维度 为空」。此前落进下方 opLabel 分支会渲染成「属于 []」（空列表），
  // 预览句既难读又与真实语义相反。
  if (REL_NOVALUE_OPS.has(c.operator || '')) {
    return `${dimLabel} ${c.operator === 'is_empty' ? '为空' : '不为空'}`;
  }
  const opLabel = c.operator === 'not_in' ? '不属于' : '属于';
  const vals = (c.values || []).map((v) => v.label).join('、');
  return `${dimLabel} ${opLabel} [${vals}]`;
}

function renderExpr(expr: string, renderNum: (n: number) => string): string {
  const toks = tokenize(expr);
  if ('error' in toks) return expr;
  return toks
    .map((tok) => {
      if (tok[0] === 'NUM') return renderNum(tok[1]);
      if (tok[0] === 'OP') return tok[1] === 'and' ? '且' : '或';
      return tok[1];
    })
    .join(' ');
}

/** 单个条件组的可读文本（**不含外层括号**）。
 *  口径与后端 expr_compiler 对齐：组内表达式留空 -> 组内条件按 **且(AND)** 组合。
 *  2026-10-18 从 previewOf 内联函数抽出：配置卡标签链（previewTags）要逐组渲染，
 *  而括号是整句预览才需要的包装，抽走后两处共用同一渲染源，不会各漂移。 */
export function previewGroupText(g: PermConditionGroup): string {
  return (g.expr || '').trim()
    ? renderExpr(g.expr, (cn) => renderCondition(g.conditions[cn - 1] ?? newCondition()))
    : g.conditions.map((c) => renderCondition(c)).join(' 且 ');
}

/** 给定模块（含 expr + groups），生成可读预览句 "可见数据 = ..."（不含前缀）。
 *  语义与后端 expr_compiler 对齐：
 *    - 组内表达式留空 -> 组内条件按 **且(AND)** 组合；
 *    - 组间组合留空     -> 各条件组按 **或(OR)** 组合。
 */
export function previewOf(m: ModulePerm): string {
  if (m.mode !== 'scope') return '';
  const groupText = (g: PermConditionGroup): string => `（${previewGroupText(g)}）`;
  const groups = m.groups.filter((g) => g.conditions.length > 0);
  if (groups.length === 0) return '';
  const inter = (m.expr || '').trim();
  return inter
    ? renderExpr(m.expr, (gn) => groupText(m.groups[gn - 1]))
    : groups.map((g) => groupText(g)).join(' 或 ');
}

/**
 * 配置卡「规则摘要标签链」（2026-10-18 兵哥原型 .tag-list）：
 * 每个**有条件**组一个标签文本，UI 层在标签之间插入「或」连接词
 * （组间组合留空时各组按 OR 组合，与 previewOf 同口径）。
 *
 * 🔴 组间是自定义组合表达式（如「1 且 2」）时**不拆成扁平标签链**，
 *    整句作为单一标签返回 —— 否则 UI 插的「或」连接词会把「且」渲染成「或」，
 *    属于放大权限的安全语义错误（管理员以为收窄、实际放宽）。
 */
export function previewTags(m: ModulePerm): string[] {
  if (m.mode !== 'scope') return [];
  const groups = m.groups.filter((g) => g.conditions.length > 0);
  if (groups.length === 0) return [];
  if ((m.expr || '').trim()) return [previewOf(m)];
  return groups.map((g) => previewGroupText(g));
}

// ---------------------------------------------------------------------------
// 草稿 / 脏检查 / 提交
// ---------------------------------------------------------------------------

function cloneModules(modules: ModulePerm[]): ModulePerm[] {
  return modules.map((m) => ({
    moduleKey: m.moduleKey,
    mode: m.mode,
    expr: m.expr,
    featureGranted: m.featureGranted,
    // 模板状态偏差由后端计算，随草稿一起带过去供 ModulePermCard 渲染标记。
    // 不参与 serialize() 脏检查 —— 它是服务端派生的展示信息，不是用户编辑内容。
    templateDrifts: (m.templateDrifts || []).map((d) => ({ ...d })),
    groups: m.groups.map(cloneGroup),
    // v2 写范围深拷贝（脏检查/保存链路必须带上，否则配置丢失）
    write: m.write
      ? {
          mode: m.write.mode,
          expr: m.write.expr,
          groups: (m.write.groups || []).map(cloneGroup),
          actions: [...(m.write.actions || [])],
        }
      : undefined,
  }));
}

function cloneGroup(g: PermConditionGroup): PermConditionGroup {
  return {
    id: g.id,
    expr: g.expr,
    conditions: g.conditions.map((c) => ({
      id: c.id,
      kind: c.kind,
      dimension: c.dimension,
      operator: c.operator,
      values: (c.values || []).map((v) => ({ id: v.id, label: v.label, stale: v.stale, emptyShell: v.emptyShell })),
      valueSource: c.valueSource,
      dynamicKey: c.dynamicKey,
      relation: c.relation,
      field: c.field,
      fieldName: c.fieldName,
      value: c.value,
      meta: c.meta ? { min: c.meta.min ?? null, max: c.meta.max ?? null } : undefined,
    })),
  };
}

function serializeGroup(g: PermConditionGroup) {
  return {
    expr: g.expr,
    conditions: g.conditions.map((c) => ({
      kind: c.kind,
      dimension: c.dimension,
      operator: c.operator,
      values: (c.values || []).map((v) => ({ id: v.id, label: v.label })),
      valueSource: c.valueSource,
      dynamicKey: c.dynamicKey,
      relation: c.relation,
      field: c.field,
      fieldName: c.fieldName,
      value: c.value,
      meta: c.meta,
    })),
  };
}

function serialize(modules: ModulePerm[]): string {
  return JSON.stringify(
    modules.map((m) => ({
      moduleKey: m.moduleKey,
      mode: m.mode,
      expr: m.expr,
      groups: m.groups.map(serializeGroup),
      // 2026-10-14 P0-1：write 的序列化口径必须与 submit() 的 payload **完全一致**
      // （groups 按 mode 收敛、缺 write 补四元组默认值）。原实现比 payload 宽松：
      // mode='all' 时仍序列化 groups，而 submit 会丢弃 groups → 保存后 saved 被
      // 后端返回值覆盖（groups 清空）→ 用户若此时做过其他改动，isDirty 会莫名翻true。
      // 口径统一消除这个抖动，也避免"序列化一致但语义不一致"的漂移复发。
      write: m.write
        ? {
            mode: m.write.mode,
            expr: m.write.mode === 'scope' ? m.write.expr : '',
            groups: m.write.mode === 'scope' ? (m.write.groups || []).map(serializeGroup) : [],
            actions: m.write.actions || [],
          }
        : { mode: 'none', expr: '', groups: [], actions: [] },
    })),
  );
}

/**
 * 读范围（数据权限）子集序列化 —— 与 serialize() 中 read 半边**逐字段同口径**，
 * 保证 `readDirty || writeDirty === isDirty`（两个页签的未保存圆点合起来不漏报）。
 */
function serializeRead(modules: ModulePerm[]): string {
  return JSON.stringify(
    modules.map((m) => ({
      moduleKey: m.moduleKey,
      mode: m.mode,
      expr: m.expr,
      groups: m.groups.map(serializeGroup),
    })),
  );
}

/**
 * 写范围（操作权限）子集序列化 —— 与 serialize() 中 write 半边同口径
 * （mode 收敛 + 缺 write 补四元组默认值）。
 */
function serializeWrite(modules: ModulePerm[]): string {
  return JSON.stringify(
    modules.map((m) => ({
      moduleKey: m.moduleKey,
      write: m.write
        ? {
            mode: m.write.mode,
            expr: m.write.mode === 'scope' ? m.write.expr : '',
            groups: m.write.mode === 'scope' ? (m.write.groups || []).map(serializeGroup) : [],
            actions: m.write.actions || [],
          }
        : { mode: 'none', expr: '', groups: [], actions: [] },
    })),
  );
}

// ---------------------------------------------------------------------------
// 写范围徽标语义（数据权限页签的只读摘要条与操作权限页签卡头共用同一判定，
// 避免两处各写一套导致「同一个状态两个颜色 / 两句话」）
// ---------------------------------------------------------------------------

export type WriteBadgeTone = 'default' | 'success' | 'error';

export interface WriteBadge {
  tone: WriteBadgeTone;
  /** i18n key（调用方用 t() 取文案，本函数保持纯逻辑可单测） */
  key: string;
  /** 已授权动作数（badge.active 需要） */
  n: number;
}

/**
 * 写范围徽标：未配置 / 全部可写 / 已授权 n 项 / 未授权任何操作。
 * 🔴 不能只看 actions.length：会把「配了范围却 0 项」显示成绿色 success，
 *    等于用颜色撒谎 —— 0 项实为 fail-closed 只读，是最该被看见的状态。
 */
export function writeBadge(w?: WritePerm): WriteBadge {
  const mode = w?.mode ?? 'none';
  if (mode === 'none') return { tone: 'default', key: 'dataperm.write.badge.none', n: 0 };
  if (mode === 'all') return { tone: 'success', key: 'dataperm.write.badge.all', n: 0 };
  const n = (w?.actions || []).length;
  return n === 0
    ? { tone: 'error', key: 'dataperm.write.badge.zero', n: 0 }
    : { tone: 'default', key: 'dataperm.write.badge.active', n };
}

export function useRoleDataPerm(roleId: Ref<string>) {
  const saved = ref<ModulePerm[]>([]);
  const draft = ref<ModulePerm[]>([]);
  const options = ref<ModuleOption[]>([]);
  /** 可配置动作字典（v2，options 下发；ModulePermCard 动作勾选/预设包下拉的数据源） */
  const actionRegistry = ref<ActionDictItem[]>([]);
  const presetPackages = ref<ActionPreset[]>([]);
  const loading = ref(false);
  const saving = ref(false);
  const errors = ref<Record<string, string>>({});
  /**
   * 每条校验错误归属的权限维度（2026-10-15 读/写拆分）。
   * 数据权限与操作权限拆成两个页签后，保存前预校验必须把用户**送到出错的那个页签**：
   * 读范围报错跳「数据权限」，写范围报错跳「操作权限」。只回 moduleKey 不够定位。
   */
  const errorKinds = ref<Record<string, 'read' | 'write'>>({});
  /**
   * 最近一次保存中「因payload 缺 write 键而沿用原值」的模块 key 列表（2026-10-14 P0-1）。
   * 正常前端恒为空 —— 它是"前端序列化回归"的后端哨兵回传，非空即须向管理员示警。
   * 消费方：ModulePermCard.vue 的 n-alert（失败/警告态必须可见，禁静默放过）。
   */
  const writeNormalized = ref<string[]>([]);

  const isDirty = computed(() => serialize(draft.value) !== serialize(saved.value));
  // 读/写分别标脏：两个页签各自的未保存圆点只反映自己那一半，
  // 避免「只改了操作权限」却在数据权限页签上亮圆点（反之亦然）。
  const readDirty = computed(() => serializeRead(draft.value) !== serializeRead(saved.value));
  const writeDirty = computed(() => serializeWrite(draft.value) !== serializeWrite(saved.value));

  function moduleOf(key: string): ModulePerm | undefined {
    return draft.value.find((m) => m.moduleKey === key);
  }

  async function load(): Promise<void> {
    loading.value = true;
    errors.value = {};
    errorKinds.value = {};
    try {
      const [data, opts] = await Promise.all([
        getRoleDataPerm(roleId.value),
        getRoleDataPermOptions(roleId.value).catch(() => ({
          modules: [] as ModuleOption[],
          actionRegistry: [] as ActionDictItem[],
          presetPackages: [] as ActionPreset[],
        })),
      ]);
      options.value = opts.modules;
      actionRegistry.value = opts.actionRegistry || [];
      presetPackages.value = opts.presetPackages || [];
      const EMPTY_WRITE = { mode: 'none' as const, expr: '', groups: [], actions: [] };
      // ⚠️ 兜底骨架的 mode 必须是 'unset'（未配置），**不是** 'all'。
      // 这两处只在 options 接口失败 / 后端少返回模块时命中，正常 GET 恒返回 5 模块，
      // 所以过去一直没人发现 —— 但它是有安全方向的错误：把"没配置过"显示并保存成
      // "全部可见"，等于给一个本该走默认范围（可能只能看自己）的角色**静默放大成全量**。
      // 后端 GET 对无规则行返回的正是 'unset'，此处必须与之一致。
      const skeleton = (k: string): ModulePerm => ({
        moduleKey: k,
        mode: 'unset' as DataPermMode,
        expr: '',
        groups: [],
        featureGranted: true,
        write: { ...EMPTY_WRITE },
      });
      const modules = data.modules && data.modules.length ? data.modules : MODULE_KEYS.map(skeleton);
      // 统一补齐 5 模块顺序（以 MODULE_KEYS 为准）
      const ordered = MODULE_KEYS.map(
        (k) => modules.find((m) => m.moduleKey === k) || skeleton(k),
      );
      saved.value = cloneModules(ordered);
      draft.value = cloneModules(ordered);
    } finally {
      loading.value = false;
    }
  }

  function setMode(key: string, mode: DataPermMode): void {
    const m = moduleOf(key);
    if (!m) return;
    const prev = m.mode;
    m.mode = mode;
    if (mode === 'scope' && m.groups.length === 0) {
      m.groups = [newGroup()];
    }
    // 切到「未配置」时清空规则（产品已拍板：切走即清）。
    // 理由：unset 的后端语义是"该模块没有任何规则行"，前端若把 groups/expr 留在内存里，
    // 管理员切到 unset 又切回 scope 时会看到一条"还在的旧规则"，误以为系统没清干净，
    // 而实际上后端已把行删了 —— 这正是数据权限里最容易被当成 bug 报上来的不一致。
    // 反过来（切 all 时不清）也有害：会把不可见的残留带进 isDirty 比对，制造假脏。
    if (mode === 'unset' && prev !== 'unset') {
      m.expr = '';
      m.groups = [];
    }
  }

  function setGroups(key: string, groups: PermConditionGroup[]): void {
    const m = moduleOf(key);
    if (!m) return;
    m.groups = groups;
  }

  // ===== v2 写范围（write 子结构）=====

  function writeOf(key: string): WritePerm | undefined {
    const m = moduleOf(key);
    if (!m) return undefined;
    if (!m.write) m.write = { mode: 'none', expr: '', groups: [], actions: [] };
    return m.write;
  }

  function setWriteMode(key: string, mode: WriteMode): void {
    const w = writeOf(key);
    if (!w) return;
    w.mode = mode;
    if (mode === 'scope' && w.groups.length === 0) {
      w.groups = [newGroup()];
    }
  }

  function setWriteGroups(key: string, groups: PermConditionGroup[]): void {
    const w = writeOf(key);
    if (!w) return;
    w.groups = groups;
  }

  function setWriteActions(key: string, actions: string[]): void {
    const w = writeOf(key);
    if (!w) return;
    w.actions = actions;
  }

  /**
   * 返回校验不合法的 moduleKey 列表（同时写入 errors 与 errorKinds）。
   *
   * 2026-10-15 读/写拆分后新增 errorKinds 归因：保存前预校验失败时，调用方要能把
   * 用户送到**出错的那个页签** —— 读范围报错跳「数据权限」，写范围报错跳「操作权限」。
   * 只回 moduleKey 不足以定位页签（同一个模块两边都能报错）。
   */
  function validate(): string[] {
    const bad: string[] = [];
    const errs: Record<string, string> = {};
    const kinds: Record<string, 'read' | 'write'> = {};
    /** 记录一条错误并归因到权限维度；同模块只保留第一条（与原行为一致）。 */
    const fail = (key: string, msg: string, kind: 'read' | 'write') => {
      if (errs[key]) return;
      errs[key] = msg;
      kinds[key] = kind;
      bad.push(key);
    };
    for (const m of draft.value) {
      // v2 写范围校验（独立于读范围 mode / featureGranted）：
      // fail-closed 语义下「配了范围不勾动作」= 拒绝一切写动作，必须显式拦截让管理员知情
      const w = m.write;
      if (w && w.mode !== 'none') {
        if ((w.actions || []).length === 0) {
          fail(m.moduleKey, '配置了写范围但未勾选任何动作（未勾选的动作将被一律拒绝）', 'write');
          continue;
        }
        if (w.mode === 'scope') {
          const totalW = (w.groups || []).reduce((acc, g) => acc + g.conditions.length, 0);
          if (totalW === 0) {
            fail(m.moduleKey, '写范围自定义条件请至少配置 1 条', 'write');
            continue;
          }
        }
      }
      if (m.mode !== 'scope' || !m.featureGranted) continue;
      const total = m.groups.reduce((acc, g) => acc + g.conditions.length, 0);
      if (total === 0) {
        fail(m.moduleKey, '请至少配置 1 个条件组及 1 条条件', 'read');
        continue;
      }
      // 组间组合表达式（引用条件组序号 1..N）
      if (m.expr.trim()) {
        const re = validateExpr(m.expr, m.groups.length);
        if (re) {
          fail(m.moduleKey, `组间组合表达式有误：${re}`, 'read');
          continue;
        }
      }
      // 每组内表达式（引用本组条件序号 1..N）
      for (let gi = 0; gi < m.groups.length; gi++) {
        const g = m.groups[gi];
        let groupBad = false;
        for (const c of g.conditions) {
          if (c.kind === 'attribute') {
            if (!c.field) {
              fail(m.moduleKey, '请选择属性字段', 'read');
              groupBad = true;
              break;
            }
            if (!c.operator) {
              fail(m.moduleKey, '请选择运算符', 'read');
              groupBad = true;
              break;
            }
            if (!ATTR_NOVALUE_OPS.has(c.operator)) {
              if (ATTR_LIST_OPS.has(c.operator)) {
                if (!Array.isArray(c.value) || c.value.length === 0) {
                  fail(m.moduleKey, '请选择业务值', 'read');
                  groupBad = true;
                  break;
                }
              } else if (c.operator === 'BETWEEN') {
                const mv = c.meta || {};
                if (mv.min == null || mv.max == null || mv.min === '' || mv.max === '') {
                  fail(m.moduleKey, '请填写区间最小值与最大值', 'read');
                  groupBad = true;
                  break;
                }
              } else if (c.value == null || c.value === '') {
                fail(m.moduleKey, '请填写条件值', 'read');
                groupBad = true;
                break;
              }
            }
          } else {
            // 无值运算符（简历锁定人的「为空/不为空」）：后端编译与保存校验
            // 均不要求业务值/动态源，前端同口径放行（详见 REL_NOVALUE_OPS 注释）。
            if (!REL_NOVALUE_OPS.has(c.operator || '')) {
              // 动态条件：不校验业务值（运行时注入），只校验来源已选且适应该维度
              if (c.valueSource === 'dynamic') {
                if (!c.dynamicKey) {
                  fail(m.moduleKey, '请为动态条件选择取值来源', 'read');
                  groupBad = true;
                  break;
                }
                // 维度适配（与后端 DYNAMIC_DIMENSION_RULES 对齐的前置校验）：
                // 来源必须出现在该维度的 contextKeys 里，否则后端保存期也会拒绝。
                const dims = options.value.find((o) => o.moduleKey === m.moduleKey)?.dimensions || [];
                const dim = dims.find((d) => d.key === c.dimension);
                if (dim && dim.contextKeys && !dim.contextKeys.includes(c.dynamicKey)) {
                  fail(m.moduleKey, `动态取值来源不适用于「${dim.label || c.dimension}」维度`, 'read');
                  groupBad = true;
                  break;
                }
              } else if ((c.values || []).length === 0) {
                fail(m.moduleKey, '请为每条条件选择业务值', 'read');
                groupBad = true;
                break;
              }
            }
          }
        }
        if (groupBad || errs[m.moduleKey]) break;
        if (g.expr.trim()) {
          const re = validateExpr(g.expr, g.conditions.length);
          if (re) {
            fail(m.moduleKey, `条件组 ${gi + 1} 组内表达式有误：${re}`, 'read');
            break;
          }
        }
      }
    }
    errors.value = errs;
    errorKinds.value = kinds;
    return bad;
  }

  async function submit(): Promise<boolean> {
    const bad = validate();
    if (bad.length) return false;
    saving.value = true;
    try {
      const payload: RoleDataPermPayload = {
        roleId: roleId.value,
        modules: draft.value.map((m) => ({
          moduleKey: m.moduleKey,
          // ⚠️ mode 必须**原样下发**（含 'unset'），不得"过滤掉 unset 模块"。
          // 后端 upsert_modules 对**未被 payload 提及**的模块是"不动（差分的核心）"，
          // 所以若 unset 模块不下发 → 不进写入循环 → 原有的 scope_type='CUSTOM'
          // 读行原封不动 → 管理员把模块改回未配置后点保存，**什么都没发生且返回 200**。
          // 「未配置」必须靠显式下发 unset + 后端真删行来实现，二者缺一即静默失效。
          mode: m.mode,
          expr: m.mode === 'scope' ? m.expr : '',
          groups: m.mode === 'scope' ? m.groups : [],
          featureGranted: m.featureGranted,
          // P0-1 修复：write 必须整段提交。此前漏传导致后端按 mode='none' 处理
          // 写范围，管理员配的操作权限静默消失（接口仍返回 200）——
          // 见 docs/ARCH_数据权限P0止血_系统设计.md §1.2.1 根因链。
          // 口径与 serialize() 保持一致：submit 提交什么，脏检查就必须比什么，
          // 否则两者各说各话，"看起来保存成功"却什么都没存。
          write: {
            mode: m.write?.mode ?? 'none',
            expr: m.write?.mode === 'scope' ? (m.write?.expr ?? '') : '',
            groups: m.write?.mode === 'scope' ? (m.write?.groups ?? []) : [],
            actions: m.write?.actions ?? [],
          },
        })),
      };
      const res = await saveRoleDataPerm(roleId.value, payload);
      saved.value = cloneModules(res.modules && res.modules.length ? res.modules : draft.value);
      draft.value = cloneModules(saved.value);
      errors.value = {};
      // P0-1 防复发哨兵：本次保存中有模块因 payload 缺 write 而沿用了原值。
      // 正常前端恒为空数组 —— 一旦非空，说明 submit 的序列化出现回归，
      // 必须让管理员知道「你看到的写范围可能不是最新提交的那份」，而不是静默放过。
      if (res.writeNormalized && res.writeNormalized.length > 0) {
        writeNormalized.value = res.writeNormalized;
      }
      return true;
    } catch (e: any) {
      const msg = e?.response?.data?.message || e?.message || '保存失败';
      throw new Error(msg);
    } finally {
      saving.value = false;
    }
  }

  function reset(): void {
    draft.value = cloneModules(saved.value);
    errors.value = {};
    errorKinds.value = {};
  }

  /**
   * 单模块「重置」（2026-10-18 兵哥原型：配置卡右上角「重置」按钮）：
   * 只把该模块**读范围**草稿还原为已保存版本 —— mode / expr / groups，
   * 以及随草稿展示的 templateDrifts（升级未保存时本地已摘掉漂移标记，还原时一并恢复，
   * 否则卡上会停在被撤销的升级所制造的"无漂移"假象上）。
   *
   * 与页级 reset() 的分工：页级是全量还原，为改一张卡而丢掉其它模块的在途配置得不偿失；
   * 单卡粒度让管理员只撤销这一张卡的未保存改动。
   * 🔴 刻意**不碰 write 半边**：写范围归「操作权限」页签的卡管，
   *    读卡的按钮静默撤销另一个页签的改动，会超出按钮所在卡片的语义。
   */
  function resetModule(key: string): void {
    const m = moduleOf(key);
    const src = saved.value.find((x) => x.moduleKey === key);
    if (!m || !src) return;
    const fresh = cloneModules([src])[0];
    m.mode = fresh.mode;
    m.expr = fresh.expr;
    m.groups = fresh.groups;
    m.templateDrifts = fresh.templateDrifts;
    // 该模块的校验错误针对的是已被丢弃的编辑，随草稿还原一并清除
    // （不清会出现「按钮已重置、红字仍在」的罗生门）。
    if (errors.value[key]) {
      const next = { ...errors.value };
      delete next[key];
      errors.value = next;
    }
    if (errorKinds.value[key]) {
      const next = { ...errorKinds.value };
      delete next[key];
      errorKinds.value = next;
    }
  }

  /**
   * 单模块读范围脏检查 —— 驱动卡内「重置」按钮的显隐。
   * 口径与 readDirty 完全同源（serializeRead 逐字段），只是粒度到模块：
   * 改了别的模块不算本卡脏（否则每张卡都亮「重置」，逼管理员做全量放弃）。
   */
  function moduleReadDirty(key: string): boolean {
    const d = moduleOf(key);
    const s = saved.value.find((x) => x.moduleKey === key);
    if (!d || !s) return false;
    return serializeRead([d]) !== serializeRead([s]);
  }

  return {
    saved,
    draft,
    options,
    actionRegistry,
    presetPackages,
    loading,
    saving,
    errors,
    errorKinds,
    writeNormalized,
    isDirty,
    readDirty,
    writeDirty,
    load,
    moduleOf,
    setMode,
    setGroups,
    setWriteMode,
    setWriteGroups,
    setWriteActions,
    validate,
    submit,
    reset,
    resetModule,
    moduleReadDirty,
    previewOf,
    previewGroupText,
    previewTags,
  };
}

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
} from '@/api/data-permission'

// 重新导出 API 层类型，供依赖本 composable 的组件统一从此处 import
export type {
  DataPermMode, ModulePerm, ModuleOption, PermCondition, PermConditionGroup,
  RoleDataPermPayload, Operator, DimensionMeta, PermValue,
} from '@/api/data-permission';

export const MODULE_KEYS = ['demand', 'process', 'position', 'candidate', 'talent'] as const;

export const DIMENSION_LABELS: Record<string, string> = {
  dept: '部门',
  owner: '负责人',
  creator: '创建人',
  process: '招聘流程',
};

/** 属性条件运算符 -> 中文标签（与后端 attribute_fields.UNIFIED_OPERATOR_LABELS 对齐）。 */
export const ATTRIBUTE_OP_LABELS: Record<string, string> = {
  EQ: '等于', NEQ: '不等于', GT: '大于', GTE: '大于等于',
  LT: '小于', LTE: '小于等于', BETWEEN: '区间',
  IN: '属于', NOT_IN: '不属于', IS_EMPTY: '为空', IS_NOT_EMPTY: '不为空',
};

/** 无需业务值的运算符（空值类）。 */
export const ATTR_NOVALUE_OPS = new Set(['IS_EMPTY', 'IS_NOT_EMPTY']);
/** 业务值为集合（多选）的运算符。 */
export const ATTR_LIST_OPS = new Set(['IN', 'NOT_IN']);

// ===== 通用工具 =====

let _seq = 0;
export function uid(prefix = 'id'): string {
  return `${prefix}-${Date.now().toString(36)}-${(_seq++).toString(36)}`;
}

export function newCondition(
  kind: 'relationship' | 'attribute' = 'relationship',
  dimension = 'dept',
): PermCondition {
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
  return { valid, error: err ?? (valid ? null : '表达式语法错误'), pos };
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
  const dimLabel = DIMENSION_LABELS[c.dimension] || c.dimension;
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

/** 给定模块（含 expr + groups），生成可读预览句 "可见数据 = ..."（不含前缀）。
 *  语义与后端 expr_compiler 对齐：
 *    - 组内表达式留空 -> 组内条件按 **且(AND)** 组合；
 *    - 组间组合留空     -> 各条件组按 **或(OR)** 组合。
 */
export function previewOf(m: ModulePerm): string {
  if (m.mode !== 'scope') return '';
  const groupText = (g: PermConditionGroup): string => {
    const inner = (g.expr || '').trim()
      ? renderExpr(g.expr, (cn) => renderCondition(g.conditions[cn - 1] ?? newCondition()))
      : g.conditions.map((c) => renderCondition(c)).join(' 且 ');
    return `（${inner}）`;
  };
  const groups = m.groups.filter((g) => g.conditions.length > 0);
  if (groups.length === 0) return '';
  const inter = (m.expr || '').trim();
  return inter
    ? renderExpr(m.expr, (gn) => groupText(m.groups[gn - 1]))
    : groups.map((g) => groupText(g)).join(' 或 ');
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
    groups: m.groups.map((g) => ({
      id: g.id,
      expr: g.expr,
      conditions: g.conditions.map((c) => ({
        id: c.id,
        kind: c.kind,
        dimension: c.dimension,
        operator: c.operator,
        values: (c.values || []).map((v) => ({ id: v.id, label: v.label, stale: v.stale })),
        field: c.field,
        fieldName: c.fieldName,
        value: c.value,
        meta: c.meta ? { min: c.meta.min ?? null, max: c.meta.max ?? null } : undefined,
      })),
    })),
  }));
}

function serialize(modules: ModulePerm[]): string {
  return JSON.stringify(
    modules.map((m) => ({
      moduleKey: m.moduleKey,
      mode: m.mode,
      expr: m.expr,
      groups: m.groups.map((g) => ({
        expr: g.expr,
        conditions: g.conditions.map((c) => ({
          kind: c.kind,
          dimension: c.dimension,
          operator: c.operator,
          values: (c.values || []).map((v) => ({ id: v.id, label: v.label })),
          field: c.field,
          fieldName: c.fieldName,
          value: c.value,
          meta: c.meta,
        })),
      })),
    })),
  );
}

export function useRoleDataPerm(roleId: Ref<string>) {
  const saved = ref<ModulePerm[]>([]);
  const draft = ref<ModulePerm[]>([]);
  const options = ref<ModuleOption[]>([]);
  const loading = ref(false);
  const saving = ref(false);
  const errors = ref<Record<string, string>>({});

  const isDirty = computed(() => serialize(draft.value) !== serialize(saved.value));

  function moduleOf(key: string): ModulePerm | undefined {
    return draft.value.find((m) => m.moduleKey === key);
  }

  async function load(): Promise<void> {
    loading.value = true;
    errors.value = {};
    try {
      const [data, opts] = await Promise.all([
        getRoleDataPerm(roleId.value),
        getRoleDataPermOptions(roleId.value).catch(() => [] as ModuleOption[]),
      ]);
      options.value = opts;
      const modules = data.modules && data.modules.length ? data.modules : MODULE_KEYS.map((k) => ({
        moduleKey: k,
        mode: 'all' as DataPermMode,
        expr: '',
        groups: [],
        featureGranted: true,
      }));
      // 统一补齐 5 模块顺序（以 MODULE_KEYS 为准）
      const ordered = MODULE_KEYS.map(
        (k) => modules.find((m) => m.moduleKey === k) || {
          moduleKey: k,
          mode: 'all' as DataPermMode,
          expr: '',
          groups: [],
          featureGranted: true,
        },
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
    m.mode = mode;
    if (mode === 'scope' && m.groups.length === 0) {
      m.groups = [newGroup()];
    }
  }

  function setGroups(key: string, groups: PermConditionGroup[]): void {
    const m = moduleOf(key);
    if (!m) return;
    m.groups = groups;
  }

  /** 返回校验不合法的 moduleKey 列表（同时写入 errors）。 */
  function validate(): string[] {
    const bad: string[] = [];
    const errs: Record<string, string> = {};
    for (const m of draft.value) {
      if (m.mode !== 'scope' || !m.featureGranted) continue;
      const total = m.groups.reduce((acc, g) => acc + g.conditions.length, 0);
      if (total === 0) {
        errs[m.moduleKey] = '请至少配置 1 个条件组及 1 条条件';
        bad.push(m.moduleKey);
        continue;
      }
      // 组间组合表达式（引用条件组序号 1..N）
      if (m.expr.trim()) {
        const re = validateExpr(m.expr, m.groups.length);
        if (re) {
          errs[m.moduleKey] = `组间组合表达式有误：${re}`;
          bad.push(m.moduleKey);
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
              errs[m.moduleKey] = '请选择属性字段';
              bad.push(m.moduleKey);
              groupBad = true;
              break;
            }
            if (!c.operator) {
              errs[m.moduleKey] = '请选择运算符';
              bad.push(m.moduleKey);
              groupBad = true;
              break;
            }
            if (!ATTR_NOVALUE_OPS.has(c.operator)) {
              if (ATTR_LIST_OPS.has(c.operator)) {
                if (!Array.isArray(c.value) || c.value.length === 0) {
                  errs[m.moduleKey] = '请选择业务值';
                  bad.push(m.moduleKey);
                  groupBad = true;
                  break;
                }
              } else if (c.operator === 'BETWEEN') {
                const mv = c.meta || {};
                if (mv.min == null || mv.max == null || mv.min === '' || mv.max === '') {
                  errs[m.moduleKey] = '请填写区间最小值与最大值';
                  bad.push(m.moduleKey);
                  groupBad = true;
                  break;
                }
              } else if (c.value == null || c.value === '') {
                errs[m.moduleKey] = '请填写条件值';
                bad.push(m.moduleKey);
                groupBad = true;
                break;
              }
            }
          } else {
            if ((c.values || []).length === 0) {
              errs[m.moduleKey] = '请为每条条件选择业务值';
              bad.push(m.moduleKey);
              groupBad = true;
              break;
            }
          }
        }
        if (groupBad || errs[m.moduleKey]) break;
        if (g.expr.trim()) {
          const re = validateExpr(g.expr, g.conditions.length);
          if (re) {
            errs[m.moduleKey] = `条件组 ${gi + 1} 组内表达式有误：${re}`;
            bad.push(m.moduleKey);
            break;
          }
        }
      }
    }
    errors.value = errs;
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
          mode: m.mode,
          expr: m.mode === 'scope' ? m.expr : '',
          groups: m.mode === 'scope' ? m.groups : [],
          featureGranted: m.featureGranted,
        })),
      };
      const res = await saveRoleDataPerm(roleId.value, payload);
      saved.value = cloneModules(res.modules && res.modules.length ? res.modules : draft.value);
      draft.value = cloneModules(saved.value);
      errors.value = {};
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
  }

  return {
    saved,
    draft,
    options,
    loading,
    saving,
    errors,
    isDirty,
    load,
    moduleOf,
    setMode,
    setGroups,
    validate,
    submit,
    reset,
    previewOf,
  };
}

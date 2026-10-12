/**
 * data-permission.ts — 角色数据权限（数据权限向导）API 客户端
 *
 * 后端端点:
 *   GET    /api/v1/roles/{id}/data-permissions/          读取某角色 5 模块配置
 *   POST   /api/v1/roles/{id}/data-permissions/          一次性保存 5 模块
 *   GET    /api/v1/roles/{id}/data-permissions/options/  模块×维度矩阵 + 维度值选项
 *
 * 响应格式: { success: boolean, data: ... }
 */
import { api } from '../utils/request'

// ===== 类型定义 =====

export type DataPermMode = 'none' | 'all' | 'scope';
export type Operator = 'in' | 'not_in';

/** 属性条件的运算符（UnifiedOperator 取值）。 */
export type AttrOperator =
  | 'EQ' | 'NEQ' | 'GT' | 'GTE' | 'LT' | 'LTE'
  | 'BETWEEN' | 'IN' | 'NOT_IN' | 'IS_EMPTY' | 'IS_NOT_EMPTY';

export interface PermValue {
  id: string | number;
  label: string;
  stale?: boolean;
}

/**
 * 动态取值来源（须与后端 context_resolvers.DYNAMIC_SOURCE_KEYS 保持一致）。
 * - currentUser.departments  当前用户负责的部门（所属部门 ∪ 其任 leader 的部门）
 * - currentUser.deptSubtree  上述部门 + 其所有子部门
 */
export type DynamicSourceKey =
  | 'currentUser.departments'
  | 'currentUser.deptSubtree';

/**
 * 业务字段与动态集合的包含关系（须与后端 context_resolvers.DYNAMIC_RELATIONS 一致）。
 * - exact       属于（精确）
 * - in_subtree  属于（含下级部门）
 * - contains    包含（业务部门是负责部门的父级）—— 本需求的核心语义
 * - overlap     包含或属于
 */
export type DynamicRelation = 'exact' | 'in_subtree' | 'contains' | 'overlap';

/** 属性条件：运算符选项（中文标签，来自后端 attributeFields）。 */
export interface AttrOperatorOption {
  value: string;
  label: string;
}

/** 属性条件：可配置字段（来自后端 attributeFields，全中文）。 */
export interface AttributeField {
  sourcePath: string;
  name: string;
  dataType: 'number' | 'enum' | 'boolean';
  enumValues: PermValue[];
  operators: AttrOperatorOption[];
}

export interface PermCondition {
  id: string;
  /** 条件类型：关系维度（默认）或 属性条件。 */
  kind?: 'relationship' | 'attribute';
  // 关系维度
  dimension?: string;
  operator: string;
  values?: PermValue[];
  // ===== 动态取值（2026-10-11 新增）=====
  /** 取值来源：static=配置时选定（缺省，存量数据），dynamic=运行时由当前用户上下文注入 */
  valueSource?: 'static' | 'dynamic';
  /** 动态值来源（valueSource='dynamic' 时必填，须与后端 DYNAMIC_SOURCE_KEYS 一致） */
  dynamicKey?: DynamicSourceKey;
  /** 业务字段与动态集合的包含关系（缺省 exact，与原 in 语义等价） */
  relation?: DynamicRelation;
  // 属性条件（复用指标目录标量字段，右值=字面量）
  field?: string;
  fieldName?: string; // 中文字段名（UI 选定后回填，便于预览句渲染）
  value?: unknown;
  /**
   * 区间（BETWEEN）上下限。
   * 运行时为 **string** —— 表单用 <n-input> 承载，值始终是文本；
   * 保存 / 执行前再按需 Number() 转换（见 rangeIssue 的 blank/Number 处理）。
   * 因此这里必须允许 string，否则 `v === ''` 的空值校验会被判为「永不成立」而失效。
   */
  meta?: { min?: string | number | null; max?: string | number | null };
}

export interface PermConditionGroup {
  id: string;
  expr: string;
  /**
   * 来源标记：该条件组由权限模板实例化而来。
   * 条件本身是**快照**（template 改版不影响已配规则），此标记仅用于
   * 展示来源与版本漂移提示，不参与运行时编译。
   */
  templateRef?: TemplateRef;
  conditions: PermCondition[];
}

export interface ModulePerm {
  moduleKey: string;
  mode: DataPermMode;
  expr: string;
  groups: PermConditionGroup[];
  featureGranted: boolean;
  /**
   * 权限模板状态偏差（后端读接口计算）。
   * 引用为快照语义，模板改版/删除都不会自动改动已配规则，
   * 靠这个字段提醒管理员「你引用的模板变了」。
   */
  templateDrifts?: TemplateDrift[];
}

export interface RoleDataPermPayload {
  roleId: string;
  modules: ModulePerm[];
}

export interface DimensionMeta {
  key: string;
  label: string;
  valueType: string;
  options: PermValue[];
}

export interface ModuleOption {
  moduleKey: string;
  label: string;
  dimensions: DimensionMeta[];
  attributeFields: AttributeField[];
}

// ===== API =====

export async function getRoleDataPerm(roleId: string): Promise<{ modules: ModulePerm[]; roleCode: string }> {
  const res = await api.get(`/roles/${roleId}/data-permissions/`);
  const data = res.data?.data || { roleId, roleCode: '', modules: [] };
  return { modules: data.modules || [], roleCode: data.roleCode || '' };
}

export async function saveRoleDataPerm(
  roleId: string,
  payload: RoleDataPermPayload,
): Promise<{ modules: ModulePerm[] }> {
  const res = await api.post(`/roles/${roleId}/data-permissions/`, payload);
  const data = res.data?.data || { modules: [] };
  return { modules: data.modules || [] };
}

export async function getRoleDataPermOptions(roleId: string): Promise<ModuleOption[]> {
  const res = await api.get(`/roles/${roleId}/data-permissions/options/`);
  const data = res.data?.data || { modules: [] };
  return data.modules || [];
}

// ===== 数据权限模板（可复用规则预设） =====

export interface ScopeTemplateParam {
  key: string;
  label: string;
  valueType?: 'dept' | 'user' | 'text' | 'number';
  required?: boolean;
  default?: unknown;
  /** 枚举型参数的候选值（文本 + 关系枚举等） */
  enum?: Array<string | { label: string; value: string }>;
}

export interface ScopeTemplate {
  id: string;
  code: string;
  name: string;
  moduleKey: string;
  description?: string;
  params: ScopeTemplateParam[];
  version: number;
  status: string;
}

export interface TemplateRef {
  templateCode: string;
  templateVersion: number;
  templateName: string;
  bindings: Record<string, unknown>;
}

/**
 * 模板状态偏差（后端 scope_templates.drift_of 产出）：
 *  - outdated  模板已升版本，快照落后 —— 需人工确认后升级
 *  - disabled  模板被停用，快照仍按原样执行
 *  - missing   模板不存在或已软删，引用仍按快照执行
 */
export type TemplateDriftState = 'outdated' | 'disabled' | 'missing';

export interface TemplateDrift {
  state: TemplateDriftState;
  templateCode: string;
  templateName?: string;
  snapshotVersion?: number;
  latestVersion?: number;
  /** 该漂移对应的条件组在 module.groups 里的下标（仅 outdated 有意义，用于定位替换） */
  groupIndex?: number;
}

/** 列出某模块可引用的权限模板 */
export async function listScopeTemplates(moduleKey: string): Promise<ScopeTemplate[]> {
  const res = await api.get('/data-permissions/templates/', {
    params: { module_key: moduleKey, status: 'ENABLED', page_size: 200 },
  });
  const data = res.data?.data;
  return Array.isArray(data) ? data : (data?.results || []);
}

/**
 * 试算绑定：返回模板在给定参数下展开后的条件组（不落库）。
 * 前端据此把模板「快照」进当前规则，运行时不再读模板 —— 避免改模板导致语义漂移。
 */
export async function previewBindTemplate(
  code: string,
  bindings: Record<string, unknown>,
): Promise<{ groups: Array<{ expr: string; conditions: PermCondition[] }>; templateCode: string; templateVersion: number }> {
  const res = await api.post(`/data-permissions/templates/${code}/preview-bind/`, { bindings });
  return res.data?.data;
}

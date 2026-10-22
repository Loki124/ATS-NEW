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

/**
 * 读范围模式。
 * - 'unset' 未配置：该模块**没有任何规则行**，运行时走角色默认数据范围（defaultDataScopeType）。
 *   🔴 与 'none' 语义完全相反：'none' 是「无权限」（显式落一行 scope_type=NONE），
 *      'unset' 是「没配过」（库里无行，落库动作= 删除读行）。前端把二者混为一谈会
 *      渲染出错误的安全语义（把"未配置"显示成"无权限"），且切模式时可能反向放大权限。
 *      后端见 apps/django/apps/data_permission/role_scope_api.py 的锁定注释。
 * - 'none' 无权限 / 'all' 全部 / 'scope' 指定范围。
 */
export type DataPermMode = 'unset' | 'none' | 'all' | 'scope';
export type Operator = 'in' | 'not_in';

/** 属性条件的运算符（UnifiedOperator 取值）。 */
export type AttrOperator =
  | 'EQ' | 'NEQ' | 'GT' | 'GTE' | 'LT' | 'LTE'
  | 'BETWEEN' | 'IN' | 'NOT_IN' | 'IS_EMPTY' | 'IS_NOT_EMPTY';

export interface PermValue {
  id: string | number;
  label: string;
  stale?: boolean;
  /** 管理单元空壳标记（M03 护栏一：无组织范围且无成员，选中也看不到数据；不阻断保存）。 */
  emptyShell?: boolean;
}

/**
 * 动态取值来源（须与后端 context_resolvers.DYNAMIC_SOURCE_KEYS 保持一致）。
 * - currentUser.departments  当前用户负责的部门（所属部门 ∪ 其任 leader 的部门）
 * - currentUser.deptSubtree  上述部门 + 其所有子部门
 * - currentUser.id           当前登录用户 id（owner/creator 维度, M03）
 * - currentUser.managedUnits 当前用户全角色并集的管理单元 id（unit 维度, M03）
 */
export type DynamicSourceKey =
  | 'currentUser.departments'
  | 'currentUser.deptSubtree'
  | 'currentUser.id'
  | 'currentUser.managedUnits';

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
  /**
   * 写范围（权限 v2）。undefined/缺省视为 { mode:'none' } = 未配置写范围 =
   * 沿用既有功能权限（opt-in fail-open 语义，与后端一致）。
   * actions 为空数组 = 拒绝一切写动作（合法但需前端二次确认）；
   * 后端动作级 fail-closed：配置写范围后未勾选的动作一律拒绝。
   */
  write?: WritePerm;
}

/** 写范围模式。none=不限制(现状)；all=全部可写；owner=仅负责人；scope=自定义条件组。 */
export type WriteMode = 'none' | 'all' | 'owner' | 'scope';

export interface WritePerm {
  mode: WriteMode;
  expr: string;
  groups: PermConditionGroup[];
  /** 允许的写动作 key 集合（来自 actionRegistry，DB 可配置）。mode!=none 时必填非空。 */
  actions: string[];
}

/** 动作字典条目（/data-permissions/actions/，DB 可配置，勿在前端硬编码清单）。 */
export interface ActionDictItem {
  key: string;
  label: string;
  category: 'read' | 'write' | 'destructive';
  destructive: boolean;
  enabled: boolean;
  is_system: boolean;
  sort_order: number;
}

/** 动作预设包（key 为存储契约，后端以数组形态下发避免 camelCase 转换破坏）。 */
export interface ActionPreset {
  key: string;
  label: string;
  actionKeys: string[];
  /** 动作归属的功能模块（如 candidate / position，复用权限资源模块 code；可空） */
  module?: string | null;
  /** 系统预设包不可删不可改 key（后端护栏，管理页用） */
  is_system?: boolean;
}

export interface RoleDataPermPayload {
  /**
   * 每模块配置。**write 必须整段提交**（2026-10-14 P0-1）。
   *
   * 历史上此处漏传 write，后端按 mode='none' 处理 → 管理员配的操作权限静默消失
   * 而接口仍返回 200。后端现已改为「缺键=保留原值+写哨兵」，但提交层仍必须
   * 显式带上 write，否则取消写范围将无法生效（缺键不再等价于 none）。
   */
  modules: ModulePerm[];
}

export interface OperatorOption {
  label: string;
  value: string;
  /**
   * 选中该运算符时是否不需要填业务值（如简历锁定人的「为空/不为空」）。
   * true 时前端隐藏校验值范围与校验值两个框。
   */
  noValue?: boolean;
}

export interface DimensionMeta {
  key: string;
  label: string;
  valueType: string;
  options: PermValue[];
  /**
   * 该维度可用的动态值来源（valueSource='dynamic' 时的快捷主体，后端
   * field_map.DIMENSION_META.contextKeys 透传）。空/缺省 = 不支持动态取值。
   */
  contextKeys?: string[];
  /**
   * 维度级运算符清单；后端按兵哥表格按维度精确下发。
   * 缺省时前端按 valueType（department/user/...）兜底推导。
   */
  operators?: OperatorOption[];
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
  const modules: ModulePerm[] = (data.modules || []).map((m: any) => ({
    ...m,
    // 写范围兜底：后端老版本/未配置时补默认 none，消费方无需判空
    write: m.write || { mode: 'none', expr: '', groups: [], actions: [] },
  }));
  return { modules, roleCode: data.roleCode || '' };
}

export async function saveRoleDataPerm(
  roleId: string,
  payload: RoleDataPermPayload,
): Promise<{ modules: ModulePerm[]; writeNormalized: string[] }> {
  const res = await api.post(`/roles/${roleId}/data-permissions/`, payload);
  const data = res.data?.data || { modules: [] };
  // writeNormalized：本次保存中「payload 缺 write 键且该模块原有 WRITE 规则」的模块 key。
  // 正常前端恒为 []（submit 必带 write）。非空 = 前端序列化回归的哨兵，
  // 后端已落审计，此处回传供调用方提示，见 docs/ARCH_数据权限P0止血_系统设计.md §1.2.2。
  return { modules: data.modules || [], writeNormalized: data.writeNormalized || [] };
}

/** options 接口完整响应（v2：含可配置动作字典与预设包，前端禁止硬编码动作清单） */
export interface DataPermOptionsResponse {
  modules: ModuleOption[];
  actionRegistry: ActionDictItem[];
  presetPackages: ActionPreset[];
}

export async function getRoleDataPermOptions(roleId: string): Promise<DataPermOptionsResponse> {
  const res = await api.get(`/roles/${roleId}/data-permissions/options/`);
  const data = res.data?.data || {};
  return {
    modules: data.modules || [],
    actionRegistry: data.actionRegistry || [],
    presetPackages: data.presetPackages || [],
  };
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

// ===== 动作字典 / 预设包（权限 v2：DB 可配置，管理接口仅超管） =====

/** 动作清单（含停用，管理页用；配置页应过滤 enabled 且 category∈write/destructive） */
export async function listActions(): Promise<ActionDictItem[]> {
  const res = await api.get('/data-permissions/actions/');
  return res.data?.data || [];
}

export async function createAction(body: {
  key: string; label: string; category: string; destructive?: boolean; sort_order?: number;
}): Promise<void> {
  await api.post('/data-permissions/actions/', body);
}

export async function updateAction(
  key: string,
  body: { label?: string; enabled?: boolean; sort_order?: number },
): Promise<void> {
  await api.patch(`/data-permissions/actions/${key}/`, body);
}

export async function deleteAction(key: string): Promise<void> {
  await api.delete(`/data-permissions/actions/${key}/`);
}

export async function listActionPresets(): Promise<ActionPreset[]> {
  const res = await api.get('/data-permissions/action-presets/');
  const data = res.data?.data;
  // 兼容两种形态：数组（标准）与映射（老后端）；映射键会被 camelCase 破坏，仅作兜底
  if (Array.isArray(data)) return data;
  return Object.entries(data || {}).map(([key, v]) => {
    // 富化后的值形如 {label, action_keys, module, is_system}；老形态为纯数组兜底
    if (Array.isArray(v)) return { key, label: key, actionKeys: v as string[] };
    const obj = v as Record<string, unknown>;
    return {
      key,
      label: (obj.label as string) || key,
      actionKeys: (obj.action_keys as string[]) ?? [],
      module: (obj.module as string) ?? null,
      is_system: obj.is_system as boolean | undefined,
    };
  });
}

export async function createActionPreset(body: {
  key: string; label: string; actionKeys: string[]; module?: string;
}): Promise<void> {
  await api.post('/data-permissions/action-presets/', body);
}

export async function updateActionPreset(
  key: string,
  body: { label?: string; actionKeys?: string[]; module?: string },
): Promise<void> {
  await api.patch(`/data-permissions/action-presets/${key}/`, body);
}

export async function deleteActionPreset(key: string): Promise<void> {
  await api.delete(`/data-permissions/action-presets/${key}/`);
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

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
  // 属性条件（复用指标目录标量字段，右值=字面量）
  field?: string;
  fieldName?: string; // 中文字段名（UI 选定后回填，便于预览句渲染）
  value?: unknown;
  meta?: { min?: number | null; max?: number | null };
}

export interface PermConditionGroup {
  id: string;
  expr: string;
  conditions: PermCondition[];
}

export interface ModulePerm {
  moduleKey: string;
  mode: DataPermMode;
  expr: string;
  groups: PermConditionGroup[];
  featureGranted: boolean;
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

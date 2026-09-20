// G42 - 动态字段定义 前端 API 客户端

import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export type FieldType =
  | 'TEXT' | 'NUMBER' | 'DATE' | 'DATE_RANGE' | 'SELECT' | 'MULTISELECT' | 'BOOLEAN'
  | 'ATTACHMENT' | 'ID_CARD' | 'BANK_CARD' | 'PHONE' | 'EMAIL'
  | 'LIST_SINGLE' | 'LIST_MULTI' | 'CONFIRM' | 'MULTILINE_TEXT'
  | 'ADDRESS'
  | 'REGION'
  | 'COMPOSITE';

/** 组合字段 (COMPOSITE) 的子字段定义 (与后端 DynamicField.sub_fields 对齐) */
export interface SubField {
  key: string;
  label: string;
  /** 子字段类型: 文本/数字/多行/附件/日期/手机号/邮箱 (后端仅允许此子集, 见 serializers.COMPOSITE allowed) */
  type: 'TEXT' | 'NUMBER' | 'MULTILINE_TEXT' | 'ATTACHMENT' | 'DATE' | 'PHONE' | 'EMAIL';
  required?: boolean;
}

/** 附件字段值结构: [{ id, name, url }] */
export interface AttachmentItem {
  id: string;
  name: string;
  url: string;
  size?: number;
  content_type?: string;
}

/** 组合字段值结构: { subKey: 子字段值 } (子字段为附件时值为 AttachmentItem[]) */
export type CompositeFieldValue = Record<string, unknown>;

/** 日期格式精度 (仅 DATE / DATE_RANGE 参考; 与后端 DynamicField.DateFormat 对齐) */
export type DateFormatValue = 'YEAR' | 'MONTH' | 'DAY';

/** 行政区划层级精度 (仅 REGION 参考; 与后端 DynamicField.RegionLevel 对齐) */
export type RegionLevelValue = 'PROVINCE' | 'CITY' | 'DISTRICT';

export type RegionFieldType = RegionLevelValue;

/** 行政区划级联型字段的值结构 (序列化入/出库为 JSON) */
export interface RegionFieldValue {
  country?: { code: string; name: string };
  province: { code: string; name: string };
  city?: { code: string; name: string };
  district?: { code: string; name: string };
}

export type LinkageConditionMode = 'ALL' | 'ANY';
export type LinkageConditionOp = 'EQ' | 'NE' | 'IN' | 'NOT_IN' | 'GT' | 'LT' | 'GTE' | 'LTE' | 'CONTAINS';
export type LinkageActionType = 'SHOW' | 'HIDE' | 'REQUIRE' | 'SET_VALUE' | 'READONLY' | 'CASCADE_OPTIONS';

export interface LinkageCondition {
  fieldKey: string;
  op: LinkageConditionOp;
  value: string | string[];
  valueLabel?: string | string[];
}

export interface LinkageAction {
  targetFieldKey: string;
  actionType: LinkageActionType;
  value?: string;
  readOnly?: boolean;
}

export interface FieldOption {
  id?: string;
  value: string;
  label: string;
  orderIndex?: number;
  isActive?: boolean;
}

export interface FieldModule {
  id: string;
  resource: string;
  code: string;
  name: string;
  description?: string;
  orderIndex: number;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface FieldGroup {
  id: string;
  moduleId: string;
  code: string;
  name: string;
  orderIndex: number;
  isActive: boolean;
  module?: FieldModule;
  createdAt?: string;
  updatedAt?: string;
}

export interface FieldLinkageRule {
  id: string;
  moduleId: string;
  name: string;
  conditionMode: LinkageConditionMode;
  conditions: LinkageCondition[];
  actions: LinkageAction[];
  orderIndex: number;
  isActive: boolean;
  module?: FieldModule;
  createdAt?: string;
  updatedAt?: string;
}

export type VisibilityPermission = 'ALL_VISIBLE' | 'MANAGER_HIDDEN';

export interface FieldDefinition {
  id: string;
  resource: string;
  fieldKey: string;
  label: string;
  /** 英文名称 — 2026-09-14 拆分增强 */
  labelEn?: string | null;
  fieldType: FieldType;
  isRequired: boolean;
  isVisible: boolean;
  placeholder?: string | null;
  helpText?: string | null;
  defaultValue?: string | null;
  validation?: string | null;
  orderIndex: number;
  groupName?: string | null;
  moduleId?: string | null;
  groupId?: string | null;
  module?: FieldModule | null;
  group?: FieldGroup | null;
  status?: string;
  options?: FieldOption[];
  /** 确认题专属字段 — 2026-09-14 拆分增强 */
  confirmationContent?: string | null;
  confirmationContentEn?: string | null;
  confirmationDeclaration?: string | null;
  confirmationDeclarationEn?: string | null;
  /** 可见权限 — 2026-09-14 拆分增强 */
  visibilityPermission?: VisibilityPermission;
  /** 选项来源 (2026-09-15): { type:'custom'|'dictionary'|'library'|'code_table', key }；非空时选项由后端按数据源动态解析 */
  optionsSource?: { type: string; key: string } | null;
  /** 2026-09-15 行政区划型字段开关: 开启后先选国家 */
  withCountry?: boolean;
  /** 2026-09-15 日期格式精度(年/年月/年月日, 仅 DATE/DATE_RANGE 参考; 默认 DAY) */
  dateFormat?: DateFormatValue | null;
  /** 2026-09-15 行政区划层级精度(省/省市/省市区, 仅 REGION 参考; 默认 DISTRICT) */
  regionLevel?: RegionLevelValue | null;
  /** 2026-09-16 (兵哥): 组合字段子结构定义(仅 COMPOSITE 使用); 普通字段为 null */
  subFields?: SubField[] | null;
  createdAt?: string;
  updatedAt?: string;
}

/** 后端 read 只返回嵌套 module/group, 但前端大量地方按平铺 moduleId/groupId 过滤/回填。
 * 在 API 层统一展开, 避免每个消费方重复处理嵌套对象。
 */
function normalizeField(f: FieldDefinition): FieldDefinition {
  if (!f) return f;
  return {
    ...f,
    moduleId: f.moduleId ?? f.module?.id ?? null,
    groupId: f.groupId ?? f.group?.id ?? null,
  };
}

function normalizeGroup(g: FieldGroup): FieldGroup {
  if (!g) return g;
  return { ...g, moduleId: g.moduleId ?? g.module?.id ?? '' };
}

function normalizeLinkageRule(r: FieldLinkageRule): FieldLinkageRule {
  if (!r) return r;
  return { ...r, moduleId: r.moduleId ?? r.module?.id ?? '' };
}

export const listFields = (resource: string, params: Record<string, unknown> = {}) =>
  api.get(`/dynamic-fields/${resource}/fields/`, { params })
    .then((r) => (r.data.data as FieldDefinition[]).map(normalizeField));

/** detail 端点统一按 id (nanoid) 寻址, 与后端 `get_object()` 契约一致 */
export const getField = (resource: string, id: string) =>
  api.get(`/dynamic-fields/${resource}/fields/${id}/`)
    .then((r) => normalizeField(r.data.data as FieldDefinition));

/**
 * 新建 / 编辑字段定义。
 *
 * 2026-08-04 修复: 原实现无论新建还是编辑都 POST 到 list 端点, 编辑时携带的
 * fieldKey 与已有记录相同 → 撞后端 unique_together → IntegrityError → HTTP 500。
 * 现按 `body.id` 是否存在区分:
 *   - 无 id → POST  /dynamic-fields/{resource}/fields/        (新建, 201)
 *   - 有 id → PUT   /dynamic-fields/{resource}/fields/{id}/   (编辑, 200)
 */
export const upsertField = (resource: string, body: Partial<FieldDefinition>) =>
  (body.id
    ? api.put(`/dynamic-fields/${resource}/fields/${body.id}/`, body)
    : api.post(`/dynamic-fields/${resource}/fields/`, body)
  ).then((r) => normalizeField(r.data.data as FieldDefinition));

export const deleteField = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/fields/${id}/`).then((r) => r.data);

/** 后端 reorder 端点只挂了 POST, 这里必须用 POST, 否则 405 */
export const reorderFields = (resource: string, orderedIds: string[]) =>
  api.post(`/dynamic-fields/${resource}/fields/reorder/`, { orderedIds }).then((r) => r.data);

/**
 * 单字段 order_index 写入。
 *
 * 2026-09-17 (寇豆码) 标准简历设置拖拽: 模块内字段拖拽后, 前端批量调用本函数
 * 把新顺序写回 DynamicField.order_index (步长 10 方便后续插入)。
 *
 * Args:
 *  resource: 资源类型 (Candidate / Position / ...)
 *  fieldId: 字段 id (nanoid, 与后端 detail 端点主键对齐)
 *  orderIndex: 新顺序值
 *
 * Returns:
 *  Promise<void> 成功 resolve, 失败 reject (前端做并发请求时捕获单条失败)
 */
export const updateFieldOrder = (
  resource: string,
  fieldId: string,
  orderIndex: number,
): Promise<void> =>
  api
    .patch(`/dynamic-fields/${resource}/fields/${fieldId}/`, { orderIndex })
    .then(() => undefined);

/**
 * 单值校验。
 *
 * 注意: 后端 `apps/dynamic_field/urls.py` 目前**未挂载** `<id>/validate/` 路由,
 * 调用会得到 404。当前无调用方, 待后端补齐该端点后方可使用。
 */
export const validateValue = (resource: string, id: string, value: any) =>
  api.post(`/dynamic-fields/${resource}/fields/${id}/validate/`, { value }).then((r) => r.data.data);

/**
 * 从后端错误响应里提取可读文案。
 *
 * 后端 `custom_exception_handler` 对 DRF 校验错误统一返回
 * `{ success, code, message: '请求处理失败', errors: { fieldKey: ['...'] } }`,
 * 只读 `message` 会永远显示泛化文案, 因此优先展开 `errors` 里的字段级提示。
 *
 * 2026-08-28 兜底: DRF ModelSerializer 自动注入的 UniqueTogetherValidator 默认文案
 * 是「字段 X, Y, Z 必须能构成唯一集合。」, 对用户不友好。即便后端已通过
 * ControlRuleSerializer.get_validators 替换为业务文案, 这里再做一道模式归一:
 * 万一后端再加新表 unique_together 漏改文案, 前端也能屏蔽抽象错误, 转友好提示。
 */
const UNIQUE_TOGETHER_ABSTRACT_PATTERN = /必须能构成唯一集合|make a unique set/i
const UNIQUE_TOGETHER_FRIENDLY = (
  '已存在同名记录（重复键）。请先停用或删除同名的旧记录后再新建，'
  + '或调整其中任意一个关键字段（适用范围 / 维度 / 指标 / 生效年度 / 启用状态）以避免冲突。'
)

function _walk(node: unknown, visit: (v: unknown) => void): void {
  if (node == null) return
  if (typeof node === 'string') { visit(node); return }
  if (Array.isArray(node)) { node.forEach((it) => _walk(it, visit)); return }
  if (typeof node === 'object') {
    Object.values(node as Record<string, unknown>).forEach((v) => _walk(v, visit))
  }
}

function _flattenStrings(node: unknown): string {
  const out: string[] = []
  _walk(node, (v) => out.push(String(v)))
  return out.join(' ')
}

export function extractApiError(e: any, fallback = '请求失败'): string {
  const data = e?.response?.data;
  const errors = data?.errors;

  if (errors) {
    // 优先吞掉「必须能构成唯一集合」这类抽象 DRF 模板, 转业务友好文案。
    // 深度遍历 errors 任何层级的字符串字段, 命中即整体替换, 避免误过嵌套报文。
    if (UNIQUE_TOGETHER_ABSTRACT_PATTERN.test(_flattenStrings(errors))) {
      return UNIQUE_TOGETHER_FRIENDLY
    }

    if (typeof errors === 'string') return errors;
    const flattened = Object.values(errors)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter((v): v is string => typeof v === 'string' && v.length > 0);
    if (flattened.length) return flattened.join('; ');
  }

  return data?.message || data?.detail || e?.message || fallback;
}

export const FIELD_TYPE_OPTIONS: { label: string; value: FieldType }[] = [
  { label: '文本', value: 'TEXT' },
  { label: '数字', value: 'NUMBER' },
  // 2026-09-15 (兵哥) 日期拆分: DATE 改名「单点日期」+ 新增 DATE_RANGE「日期范围」(格式精度见 DATE_FORMAT_OPTIONS)
  { label: '单点日期', value: 'DATE' },
  { label: '日期范围', value: 'DATE_RANGE' },
  { label: '下拉单选', value: 'SELECT' },
  { label: '下拉多选', value: 'MULTISELECT' },
  { label: '布尔', value: 'BOOLEAN' },
  { label: '附件', value: 'ATTACHMENT' },
  { label: '身份证', value: 'ID_CARD' },
  { label: '银行卡', value: 'BANK_CARD' },
  { label: '手机号', value: 'PHONE' },
  { label: '邮箱', value: 'EMAIL' },
  { label: '列表单选', value: 'LIST_SINGLE' },
  { label: '列表多选', value: 'LIST_MULTI' },
  { label: '确认题', value: 'CONFIRM' },
  { label: '多行文本', value: 'MULTILINE_TEXT' },
  // 2026-09-15 新增: 地址（单行文本，预览/申请表独占整行）
  { label: '地址', value: 'ADDRESS' },
  // 2026-09-15 新增: 行政区划型(数据源: G46 码表库 regions/countries; 层级精度由省/省市/省市区单选控制, 与 with_country 配套)
  { label: '行政区划', value: 'REGION' },
  // 2026-09-16 (兵哥): 组合字段型 — 一个字段聚合多个子字段(可含附件), 页面呈现为组合展示卡
  { label: '组合字段', value: 'COMPOSITE' },
];

export const FIELD_TYPE_LABEL: Record<FieldType, string> = {
  TEXT: '文本', NUMBER: '数字', DATE: '单点日期', DATE_RANGE: '日期范围',
  SELECT: '下拉单选', MULTISELECT: '下拉多选', BOOLEAN: '布尔',
  ATTACHMENT: '附件', ID_CARD: '身份证', BANK_CARD: '银行卡',
  PHONE: '手机号', EMAIL: '邮箱',
  LIST_SINGLE: '列表单选', LIST_MULTI: '列表多选',
  CONFIRM: '确认题',
  MULTILINE_TEXT: '多行文本',
  ADDRESS: '地址',
  REGION: '行政区划',
  COMPOSITE: '组合字段',
};

/** 日期格式精度选项 (兵哥 2026-09-15: 年 / 年月 / 年月日) */
export const DATE_FORMAT_OPTIONS: { label: string; value: DateFormatValue }[] = [
  { label: '年', value: 'YEAR' },
  { label: '年月', value: 'MONTH' },
  { label: '年月日', value: 'DAY' },
];

export const DATE_FORMAT_LABEL: Record<DateFormatValue, string> = {
  YEAR: '年', MONTH: '年月', DAY: '年月日',
};

/** 是否日期型字段(单点/范围), 渲染日期选择器并受 date_format 精度控制 */
export function isDateFieldType(t: string): boolean {
  return t === 'DATE' || t === 'DATE_RANGE';
}

/** 日期型字段 → n-date-picker type 映射(单点: year/month/date; 范围: yearrange/monthrange/daterange) */
export function datePickerType(fieldType: string, dateFormat: string | null | undefined): string {
  const f = (dateFormat || 'DAY') as DateFormatValue;
  const map: Record<DateFormatValue, string> = { YEAR: 'year', MONTH: 'month', DAY: 'date' };
  const rangeMap: Record<DateFormatValue, string> = { YEAR: 'yearrange', MONTH: 'monthrange', DAY: 'daterange' };
  return fieldType === 'DATE_RANGE' ? rangeMap[f] : map[f];
}

/** 行政区划层级精度选项 (兵哥 2026-09-15: 省 / 省市 / 省市区) */
export const REGION_LEVEL_OPTIONS: { label: string; value: RegionLevelValue }[] = [
  { label: '省', value: 'PROVINCE' },
  { label: '省市', value: 'CITY' },
  { label: '省市区', value: 'DISTRICT' },
];

export const REGION_LEVEL_LABEL: Record<RegionLevelValue, string> = {
  PROVINCE: '省', CITY: '省市', DISTRICT: '省市区',
};

/** 是否行政区划型字段, 渲染级联选择器并受 region_level 精度控制 */
export function isRegionFieldType(t: string): boolean {
  return t === 'REGION';
}

/** 行政区划层级 → 是否显示市 / 区 (PROVINCE 仅省; CITY 省+市; DISTRICT 省+市+区) */
export function regionLevelShowCity(level: string | null | undefined): boolean {
  const l = (level || 'DISTRICT') as RegionLevelValue;
  return l === 'CITY' || l === 'DISTRICT';
}

export function regionLevelShowDistrict(level: string | null | undefined): boolean {
  return (level || 'DISTRICT') === 'DISTRICT';
}

/** 可见权限枚举选项（字段权限管理弹窗） */
export const VISIBILITY_PERMISSION_OPTIONS: { label: string; value: VisibilityPermission }[] = [
  { label: '全员可见', value: 'ALL_VISIBLE' },
  { label: '用人经理端不可见', value: 'MANAGER_HIDDEN' },
];

export const VISIBILITY_PERMISSION_LABEL: Record<VisibilityPermission, string> = {
  ALL_VISIBLE: '全员可见',
  MANAGER_HIDDEN: '用人经理端不可见',
};

export const LINKAGE_CONDITION_MODE_OPTIONS: { label: string; value: LinkageConditionMode }[] = [
  { label: '满足以下所有条件', value: 'ALL' },
  { label: '满足以下任一条件', value: 'ANY' },
];

export const LINKAGE_OP_OPTIONS: { label: string; value: LinkageConditionOp }[] = [
  { label: '等于', value: 'EQ' },
  { label: '不等于', value: 'NE' },
  { label: '包含', value: 'IN' },
  { label: '不包含', value: 'NOT_IN' },
  { label: '大于', value: 'GT' },
  { label: '小于', value: 'LT' },
  { label: '大于等于', value: 'GTE' },
  { label: '小于等于', value: 'LTE' },
  { label: '包含文本', value: 'CONTAINS' },
];

export const LINKAGE_ACTION_OPTIONS: { label: string; value: LinkageActionType }[] = [
  { label: '显示', value: 'SHOW' },
  { label: '隐藏', value: 'HIDE' },
  { label: '设必填', value: 'REQUIRE' },
  { label: '赋值', value: 'SET_VALUE' },
  { label: '只读', value: 'READONLY' },
  { label: '级联选项', value: 'CASCADE_OPTIONS' },
];

// --- 模块配置 (FieldModule, 父级) ---
export const listModules = (resource: string) =>
  api.get(`/dynamic-fields/${resource}/modules/`).then((r) => r.data.data as FieldModule[]);

export const upsertModule = (resource: string, body: Partial<FieldModule>) =>
  (body.id
    ? api.put(`/dynamic-fields/${resource}/modules/${body.id}/`, body)
    : api.post(`/dynamic-fields/${resource}/modules/`, body)
  ).then((r) => r.data.data as FieldModule);

export const deleteModule = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/modules/${id}/`).then((r) => r.data);

/**
 * 确保 resource 下存在唯一默认模块 (code == resource); 不存在则后端自动创建。
 * 2026-09-14 动态字段拆分: embedded 视图进入时调用, 作为分组/联动规则的 FK 归属,
 * 使用户在业务模块内无需再配置「模块」。
 */
export const ensureDefaultModule = (resource: string, name?: string) =>
  api.post(`/dynamic-fields/${resource}/modules/ensure-default/`, name ? { name } : {})
    .then((r) => r.data.data as FieldModule);

// --- 分组配置 (FieldGroup, 子级) ---
export const listGroups = (resource: string, moduleId?: string) =>
  api.get(`/dynamic-fields/${resource}/groups/`, { params: moduleId ? { module_id: moduleId } : {} })
    .then((r) => (r.data.data as FieldGroup[]).map(normalizeGroup));

export const upsertGroup = (resource: string, body: Partial<FieldGroup>) =>
  (body.id
    ? api.put(`/dynamic-fields/${resource}/groups/${body.id}/`, body)
    : api.post(`/dynamic-fields/${resource}/groups/`, body)
  ).then((r) => normalizeGroup(r.data.data as FieldGroup));

export const deleteGroup = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/groups/${id}/`).then((r) => r.data);

// --- 联动规则 (FieldLinkageRule, 同模块) ---
export const listLinkageRules = (resource: string, moduleId?: string) =>
  api.get(`/dynamic-fields/${resource}/linkage-rules/`, { params: moduleId ? { module_id: moduleId } : {} })
    .then((r) => (r.data.data as FieldLinkageRule[]).map(normalizeLinkageRule));

export const upsertLinkageRule = (resource: string, body: Partial<FieldLinkageRule>) =>
  (body.id
    ? api.put(`/dynamic-fields/${resource}/linkage-rules/${body.id}/`, body)
    : api.post(`/dynamic-fields/${resource}/linkage-rules/`, body)
  ).then((r) => normalizeLinkageRule(r.data.data as FieldLinkageRule));

export const deleteLinkageRule = (resource: string, id: string) =>
  api.delete(`/dynamic-fields/${resource}/linkage-rules/${id}/`).then((r) => r.data);

// --- 字段导入 / 导出 ---
export const exportFieldsUrl = (resource: string, format: 'json' | 'csv', moduleId?: string, groupId?: string) => {
  const params = new URLSearchParams({ format });
  if (moduleId) params.set('module_id', moduleId);
  if (groupId) params.set('group_id', groupId);
  return `${config.api.baseUrl}/dynamic-fields/${resource}/fields/export/?${params.toString()}`;
};

/** 触发浏览器下载导出文件 (后端返回带 Content-Disposition 的文件流) */
export async function downloadExport(
  resource: string, format: 'json' | 'csv', moduleId?: string, groupId?: string,
): Promise<void> {
  const url = exportFieldsUrl(resource, format, moduleId, groupId);
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  const resp = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!resp.ok) throw new Error(`导出失败: HTTP ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `dynamic_fields.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

export const importFields = (
  resource: string, format: 'json' | 'csv', content: string,
) => api.post(`/dynamic-fields/${resource}/fields/import/`, { format, content })
  .then((r) => r.data as { success: boolean; created: number; updated: number; errors: number });

/** 导入模板下载地址 (后端 template 动作返回带 Content-Disposition 的文件流) */
export const templateUrl = (resource: string, format: 'json' | 'csv') => {
  const params = new URLSearchParams({ format });
  return `${config.api.baseUrl}/dynamic-fields/${resource}/fields/template/?${params.toString()}`;
};

/** 触发浏览器下载导入模板 */
export async function downloadTemplate(resource: string, format: 'json' | 'csv'): Promise<void> {
  const url = templateUrl(resource, format);
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  const resp = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!resp.ok) throw new Error(`模板下载失败: HTTP ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `dynamic_fields_template.${format}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
}

export default api;

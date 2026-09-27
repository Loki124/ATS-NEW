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
  | 'ATTACHMENT' | 'ID_CARD' | 'BANK_CARD' | 'PHONE' | 'EMAIL' | 'URL'
  | 'LIST_SINGLE' | 'LIST_MULTI' | 'CONFIRM' | 'MULTILINE_TEXT'
  | 'ADDRESS'
  | 'REGION'
  | 'COMPOSITE'
  | 'RICH_TEXT'
  | 'PERSON'
  | 'DEPARTMENT';

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

/** 限制条件配置 (2026-09-24 兵哥重构) — 按字段类型结构化的校验规则。
 *  - 数字类: min / max / step / decimals / unit (单位仅展示)
 *  - 文本类: maxLength (EMAIL/PHONE/ID_CARD/BANK_CARD/URL 的格式与长度由字段类型层固有约束, 无配置项)
 *  - 选项类 (LIST_SINGLE/LIST_MULTI): allowedValues (限定只能从这些值里选)
 *  - 日期类: minDate / maxDate (限制可选择的日期区间)
 *  - 通用: message (校验失败时的错误提示, 缺省由后端生成默认文案) */
export interface FieldValidation {
  min?: number | null;
  max?: number | null;
  step?: number | null;
  decimals?: number | null;
  /** 数字类专用: 单位 (仅展示, 不参与校验) */
  unit?: string | null;
  maxLength?: number | null;
  allowedValues?: string[] | null;
  /** 日期类专用: 可选范围起止 (YYYY-MM-DD) */
  minDate?: string | null;
  maxDate?: string | null;
  message?: string | null;
}

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
  /** 限制条件 (2026-09-24 兵哥): 按字段类型结构化的校验配置 */
  validation?: FieldValidation | null;
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
  /** 2026-09-27 (兵哥): 系统内置字段(种子预置) — 不可删除; 结构性属性后端守卫剥除 */
  isSystem?: boolean;
  /** 系统核心标识字段(需求编号/名称/状态)完全锁定 — 不可编辑/停用/删除 */
  isLocked?: boolean;
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
 * 单分组 order_index 写入。
 *
 * 2026-09-21 (寇豆码) 标准简历设置分组拖拽: 分组拖拽结束后, 前端批量调用本函数
 * 把新顺序写回 FieldGroup.order_index (步长 10 方便后续插入)。
 *
 * ⚠️ 必须同时携带 ``module_id``: 后端 ``FieldGroupSerializer.update()`` 会执行
 * ``validated_data['module_id'] = validated_data.pop('module_id', None) or None``,
 * 对**部分更新**(PATCH 仅带 order_index)会把 module_id 置空 → 触发
 * ``IntegrityError (Column 'module_id' cannot be null)`` → HTTP 500。
 * 故此处回传当前归属 module_id (等值重赋值, 语义无副作用), 以在不改后端的前提下
 * 让既有端点可用。
 *
 * Args:
 *  resource: 资源类型 (Candidate / Position / ...)
 *  groupId: 分组 id (nanoid, 与后端 detail 端点主键对齐)
 *  orderIndex: 新顺序值
 *  moduleId: 分组所属模块 id (可选; 传入则一并回写以规避上述 500)
 *
 * Returns:
 *  Promise<void> 成功 resolve, 失败 reject (前端做并发请求时捕获单条失败)
 */
export const updateGroupOrder = (
  resource: string,
  groupId: string,
  orderIndex: number,
  moduleId?: string | null,
): Promise<void> => {
  const body: Record<string, unknown> = { order_index: orderIndex };
  if (moduleId) body.module_id = moduleId;
  return api
    .patch(`/dynamic-fields/${resource}/groups/${groupId}/`, body)
    .then(() => undefined);
};

/**
 * 单值校验。
 *
 * 后端 `DynamicFieldViewSet.validate_field` (POST `<resource>/fields/<id>/validate/`)
 * 已挂载, 返回 `{ data: { valid, errors } }`。
 */
export const validateValue = (resource: string, id: string, value: any) =>
  api.post(`/dynamic-fields/${resource}/fields/${id}/validate/`, { value }).then((r) => r.data.data);

/**
 * 批量校验一组字段值 (2026-09-24 兵哥)。
 *
 * POST `<resource>/fields/validate-values/` { values: { fieldKey: value } }
 * → `{ data: { fieldKey: [errors] } }` (仅含不通过项, 键为 camelCase 与前端 fieldKey 对齐)。
 * 前端录入表单提交前可先调此端点做服务端权威校验。
 */
export const validateValues = (resource: string, values: Record<string, any>) =>
  api
    .post(`/dynamic-fields/${resource}/fields/validate-values/`, { values })
    .then((r) => (r.data?.data ?? {}) as Record<string, string[] | undefined>);

/**
 * 录入提交落库 (2026-09-24 兵哥)。
 *
 * POST `<resource>/fields/values/` { entityId, values }
 * 后端先按字段定义 + validation 做权威校验, 任一不通过 → 400 `{ errors }`; 全通过 → upsert。
 */
export const saveDynamicFieldValues = (
  resource: string,
  entityId: string,
  values: Record<string, any>,
) => api.post(`/dynamic-fields/${resource}/fields/values/`, { entityId, values }).then((r) => r.data);

/**
 * 按实体读取动态字段值 (2026-09-24 兵哥, 需求 4: 详情页渲染扩展字段)。
 *
 * GET `<resource>/fields/values/?entityId=X` → `{ data: [{ fieldKey, value }] }`
 * (数组 + 字符串 fieldKey, 保持原始 snake, 与 listFields 返回的 fieldKey 一致)。
 * 后端用数组而非 dict 是因为全局 CamelCaseJSONRenderer 会把 dict 的 snake 键 camel 化
 * (f_custom_text→fCustomText), 导致前端用 snake 的 f.fieldKey 索引永远 miss。
 * 这里把数组聚合成 `{ fieldKey: value }` 再返回, 调用方直接用 f.fieldKey 索引即可。
 * 仅返回有值的键; 未配置 / 未录入的字段不在返回中。
 */
export const getDynamicFieldValues = (resource: string, entityId: string) =>
  api
    .get(`/dynamic-fields/${resource}/fields/values/`, { params: { entityId } })
    .then((r) => {
      const list = ((r.data?.data ?? []) as { fieldKey: string; value: any }[]) || []
      const map: Record<string, any> = {}
      for (const it of list) map[it.fieldKey] = it.value
      return map
    });

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

/** 字段类型下拉选项 — 分组结构 (naive-ui n-select 原生支持 type:'group' 分组)。
 * 2026-09-24 (兵哥) 重构: 相似类型归类 (文本类/数值与时间/选择与确认/身份与联系/高级),
 * 「文本类」(最高频) 排在列表最前部。 */
export type FieldTypeOption =
  | { label: string; value: FieldType }
  | { type: 'group'; label: string; children: FieldTypeOption[] };

export const FIELD_TYPE_OPTIONS: FieldTypeOption[] = [
  { type: 'group', label: '文本类', children: [
    { label: '文本', value: 'TEXT' },
    { label: '多行文本', value: 'MULTILINE_TEXT' },
    // 2026-09-24 (兵哥): 富文本型 — 录入端渲染富文本编辑器, 值以规范化 HTML 字符串存储
    { label: '富文本', value: 'RICH_TEXT' },
    { label: '地址', value: 'ADDRESS' },
  ]},
  { type: 'group', label: '数值与时间', children: [
    { label: '数字', value: 'NUMBER' },
    // 2026-09-15 (兵哥) 日期拆分: DATE 改名「单点日期」+ 新增 DATE_RANGE「日期范围」
    { label: '单点日期', value: 'DATE' },
    { label: '日期范围', value: 'DATE_RANGE' },
  ]},
  { type: 'group', label: '选择与确认', children: [
    { label: '下拉单选', value: 'SELECT' },
    { label: '下拉多选', value: 'MULTISELECT' },
    { label: '列表单选', value: 'LIST_SINGLE' },
    { label: '列表多选', value: 'LIST_MULTI' },
    { label: '确认题', value: 'CONFIRM' },
  ]},
  { type: 'group', label: '身份与联系', children: [
    { label: '身份证', value: 'ID_CARD' },
    { label: '银行卡', value: 'BANK_CARD' },
    // 2026-09-24 (兵哥): 「手机号」更名为「电话」, 表单支持国际区号 (见 PHONE_DIAL_CODES)
    { label: '电话', value: 'PHONE' },
    { label: '邮箱', value: 'EMAIL' },
    { label: 'URL', value: 'URL' },
  ]},
  { type: 'group', label: '高级', children: [
    { label: '布尔', value: 'BOOLEAN' },
    { label: '附件', value: 'ATTACHMENT' },
    { label: '行政区划', value: 'REGION' },
    { label: '组合字段', value: 'COMPOSITE' },
  ]},
  { type: 'group', label: '人员与组织', children: [
    // 2026-09-24 (兵哥): 引用类字段 — 选项来源于系统用户 / 组织管理 (见 optionsSource)
    { label: '人员', value: 'PERSON' },
    { label: '部门', value: 'DEPARTMENT' },
  ]},
];

export const FIELD_TYPE_LABEL: Record<FieldType, string> = {
  TEXT: '文本', NUMBER: '数字', DATE: '单点日期', DATE_RANGE: '日期范围',
  SELECT: '下拉单选', MULTISELECT: '下拉多选', BOOLEAN: '布尔',
  ATTACHMENT: '附件', ID_CARD: '身份证', BANK_CARD: '银行卡',
  PHONE: '电话', EMAIL: '邮箱', URL: 'URL',
  LIST_SINGLE: '列表单选', LIST_MULTI: '列表多选',
  CONFIRM: '确认题',
  MULTILINE_TEXT: '多行文本',
  ADDRESS: '地址',
  REGION: '行政区划',
  COMPOSITE: '组合字段',
  RICH_TEXT: '富文本',
  PERSON: '人员',
  DEPARTMENT: '部门',
};

/** 国际电话区号清单 (2026-09-24 兵哥) — 录入「电话」字段时可选, 默认 +86。
 * 内置较全清单 + 可搜索 (按 区号/中文名/英文名 模糊匹配)。 */
export interface DialCode {
  /** 区号 (含 +, 如 '+86') */
  code: string;
  /** 中文国家/地区名 */
  country: string;
  /** 英文国家/地区名 */
  en: string;
}

export const PHONE_DIAL_CODES: DialCode[] = [
  { code: '+86', country: '中国', en: 'China' },
  { code: '+852', country: '中国香港', en: 'Hong Kong' },
  { code: '+853', country: '中国澳门', en: 'Macao' },
  { code: '+886', country: '中国台湾', en: 'Taiwan' },
  { code: '+1', country: '美国/加拿大', en: 'United States/Canada' },
  { code: '+44', country: '英国', en: 'United Kingdom' },
  { code: '+33', country: '法国', en: 'France' },
  { code: '+49', country: '德国', en: 'Germany' },
  { code: '+39', country: '意大利', en: 'Italy' },
  { code: '+34', country: '西班牙', en: 'Spain' },
  { code: '+31', country: '荷兰', en: 'Netherlands' },
  { code: '+41', country: '瑞士', en: 'Switzerland' },
  { code: '+43', country: '奥地利', en: 'Austria' },
  { code: '+45', country: '丹麦', en: 'Denmark' },
  { code: '+46', country: '瑞典', en: 'Sweden' },
  { code: '+47', country: '挪威', en: 'Norway' },
  { code: '+48', country: '波兰', en: 'Poland' },
  { code: '+351', country: '葡萄牙', en: 'Portugal' },
  { code: '+353', country: '爱尔兰', en: 'Ireland' },
  { code: '+358', country: '芬兰', en: 'Finland' },
  { code: '+420', country: '捷克', en: 'Czech Republic' },
  { code: '+36', country: '匈牙利', en: 'Hungary' },
  { code: '+7', country: '俄罗斯/哈萨克斯坦', en: 'Russia/Kazakhstan' },
  { code: '+81', country: '日本', en: 'Japan' },
  { code: '+82', country: '韩国', en: 'South Korea' },
  { code: '+65', country: '新加坡', en: 'Singapore' },
  { code: '+60', country: '马来西亚', en: 'Malaysia' },
  { code: '+66', country: '泰国', en: 'Thailand' },
  { code: '+84', country: '越南', en: 'Vietnam' },
  { code: '+63', country: '菲律宾', en: 'Philippines' },
  { code: '+62', country: '印度尼西亚', en: 'Indonesia' },
  { code: '+91', country: '印度', en: 'India' },
  { code: '+92', country: '巴基斯坦', en: 'Pakistan' },
  { code: '+880', country: '孟加拉国', en: 'Bangladesh' },
  { code: '+94', country: '斯里兰卡', en: 'Sri Lanka' },
  { code: '+95', country: '缅甸', en: 'Myanmar' },
  { code: '+855', country: '柬埔寨', en: 'Cambodia' },
  { code: '+856', country: '老挝', en: 'Laos' },
  { code: '+970', country: '巴勒斯坦', en: 'Palestine' },
  { code: '+971', country: '阿联酋', en: 'United Arab Emirates' },
  { code: '+972', country: '以色列', en: 'Israel' },
  { code: '+973', country: '巴林', en: 'Bahrain' },
  { code: '+974', country: '卡塔尔', en: 'Qatar' },
  { code: '+975', country: '不丹', en: 'Bhutan' },
  { code: '+976', country: '蒙古', en: 'Mongolia' },
  { code: '+977', country: '尼泊尔', en: 'Nepal' },
  { code: '+61', country: '澳大利亚', en: 'Australia' },
  { code: '+64', country: '新西兰', en: 'New Zealand' },
  { code: '+54', country: '阿根廷', en: 'Argentina' },
  { code: '+55', country: '巴西', en: 'Brazil' },
  { code: '+56', country: '智利', en: 'Chile' },
  { code: '+57', country: '哥伦比亚', en: 'Colombia' },
  { code: '+51', country: '秘鲁', en: 'Peru' },
  { code: '+52', country: '墨西哥', en: 'Mexico' },
  { code: '+58', country: '委内瑞拉', en: 'Venezuela' },
  { code: '+593', country: '厄瓜多尔', en: 'Ecuador' },
  { code: '+598', country: '乌拉圭', en: 'Uruguay' },
  { code: '+591', country: '玻利维亚', en: 'Bolivia' },
  { code: '+592', country: '圭亚那', en: 'Guyana' },
  { code: '+27', country: '南非', en: 'South Africa' },
  { code: '+20', country: '埃及', en: 'Egypt' },
  { code: '+234', country: '尼日利亚', en: 'Nigeria' },
  { code: '+254', country: '肯尼亚', en: 'Kenya' },
  { code: '+255', country: '坦桑尼亚', en: 'Tanzania' },
  { code: '+256', country: '乌干达', en: 'Uganda' },
  { code: '+233', country: '加纳', en: 'Ghana' },
  { code: '+212', country: '摩洛哥', en: 'Morocco' },
  { code: '+213', country: '阿尔及利亚', en: 'Algeria' },
  { code: '+216', country: '突尼斯', en: 'Tunisia' },
  { code: '+218', country: '利比亚', en: 'Libya' },
  { code: '+235', country: '乍得', en: 'Chad' },
  { code: '+237', country: '喀麦隆', en: 'Cameroon' },
  { code: '+238', country: '佛得角', en: 'Cape Verde' },
  { code: '+240', country: '赤道几内亚', en: 'Equatorial Guinea' },
  { code: '+241', country: '加蓬', en: 'Gabon' },
  { code: '+243', country: '刚果(金)', en: 'DR Congo' },
  { code: '+244', country: '安哥拉', en: 'Angola' },
  { code: '+245', country: '几内亚比绍', en: 'Guinea-Bissau' },
  { code: '+248', country: '塞舌尔', en: 'Seychelles' },
  { code: '+250', country: '卢旺达', en: 'Rwanda' },
  { code: '+251', country: '埃塞俄比亚', en: 'Ethiopia' },
  { code: '+257', country: '布隆迪', en: 'Burundi' },
  { code: '+260', country: '赞比亚', en: 'Zambia' },
  { code: '+261', country: '马达加斯加', en: 'Madagascar' },
  { code: '+263', country: '津巴布韦', en: 'Zimbabwe' },
  { code: '+264', country: '纳米比亚', en: 'Namibia' },
  { code: '+265', country: '马拉维', en: 'Malawi' },
  { code: '+266', country: '莱索托', en: 'Lesotho' },
  { code: '+267', country: '博茨瓦纳', en: 'Botswana' },
  { code: '+269', country: '科摩罗', en: 'Comoros' },
  { code: '+290', country: '圣赫勒拿', en: 'Saint Helena' },
  { code: '+299', country: '格陵兰', en: 'Greenland' },
  { code: '+30', country: '希腊', en: 'Greece' },
  { code: '+32', country: '比利时', en: 'Belgium' },
  { code: '+350', country: '直布罗陀', en: 'Gibraltar' },
  { code: '+352', country: '卢森堡', en: 'Luxembourg' },
  { code: '+354', country: '冰岛', en: 'Iceland' },
  { code: '+355', country: '阿尔巴尼亚', en: 'Albania' },
  { code: '+356', country: '马耳他', en: 'Malta' },
  { code: '+357', country: '塞浦路斯', en: 'Cyprus' },
  { code: '+359', country: '保加利亚', en: 'Bulgaria' },
  { code: '+370', country: '立陶宛', en: 'Lithuania' },
  { code: '+371', country: '拉脱维亚', en: 'Latvia' },
  { code: '+372', country: '爱沙尼亚', en: 'Estonia' },
  { code: '+373', country: '摩尔多瓦', en: 'Moldova' },
  { code: '+374', country: '亚美尼亚', en: 'Armenia' },
  { code: '+375', country: '白俄罗斯', en: 'Belarus' },
  { code: '+376', country: '安道尔', en: 'Andorra' },
  { code: '+377', country: '摩纳哥', en: 'Monaco' },
  { code: '+378', country: '圣马力诺', en: 'San Marino' },
  { code: '+380', country: '乌克兰', en: 'Ukraine' },
  { code: '+381', country: '塞尔维亚', en: 'Serbia' },
  { code: '+382', country: '黑山', en: 'Montenegro' },
  { code: '+383', country: '科索沃', en: 'Kosovo' },
  { code: '+385', country: '克罗地亚', en: 'Croatia' },
  { code: '+386', country: '斯洛文尼亚', en: 'Slovenia' },
  { code: '+387', country: '波斯尼亚和黑塞哥维那', en: 'Bosnia and Herzegovina' },
  { code: '+389', country: '北马其顿', en: 'North Macedonia' },
  { code: '+390', country: '梵蒂冈', en: 'Vatican City' },
  { code: '+501', country: '伯利兹', en: 'Belize' },
  { code: '+502', country: '危地马拉', en: 'Guatemala' },
  { code: '+503', country: '萨尔瓦多', en: 'El Salvador' },
  { code: '+504', country: '洪都拉斯', en: 'Honduras' },
  { code: '+505', country: '尼加拉瓜', en: 'Nicaragua' },
  { code: '+506', country: '哥斯达黎加', en: 'Costa Rica' },
  { code: '+507', country: '巴拿马', en: 'Panama' },
  { code: '+509', country: '海地', en: 'Haiti' },
  { code: '+590', country: '瓜德罗普', en: 'Guadeloupe' },
  { code: '+594', country: '法属圭亚那', en: 'French Guiana' },
  { code: '+595', country: '巴拉圭', en: 'Paraguay' },
  { code: '+596', country: '马提尼克', en: 'Martinique' },
  { code: '+597', country: '苏里南', en: 'Suriname' },
  { code: '+599', country: '库拉索', en: 'Curaçao' },
  { code: '+670', country: '东帝汶', en: 'Timor-Leste' },
  { code: '+672', country: '澳大利亚海外领地', en: 'Australian External Territories' },
  { code: '+673', country: '文莱', en: 'Brunei' },
  { code: '+674', country: '瑙鲁', en: 'Nauru' },
  { code: '+675', country: '巴布亚新几内亚', en: 'Papua New Guinea' },
  { code: '+676', country: '汤加', en: 'Tongatapu' },
  { code: '+677', country: '所罗门群岛', en: 'Solomon Islands' },
  { code: '+678', country: '瓦努阿图', en: 'Vanuatu' },
  { code: '+679', country: '斐济', en: 'Fiji' },
  { code: '+680', country: '帕劳', en: 'Palau' },
  { code: '+681', country: '瓦利斯和富图纳', en: 'Wallis and Futuna' },
  { code: '+682', country: '库克群岛', en: 'Cook Islands' },
  { code: '+683', country: '纽埃', en: 'Niue' },
  { code: '+685', country: '萨摩亚', en: 'Samoa' },
  { code: '+686', country: '基里巴斯', en: 'Kiribati' },
  { code: '+687', country: '新喀里多尼亚', en: 'New Caledonia' },
  { code: '+688', country: '图瓦卢', en: 'Tuvalu' },
  { code: '+689', country: '法属波利尼西亚', en: 'French Polynesia' },
  { code: '+690', country: '托克劳', en: 'Tokelau' },
  { code: '+691', country: '密克罗尼西亚', en: 'Micronesia' },
  { code: '+692', country: '马绍尔群岛', en: 'Marshall Islands' },
  { code: '+850', country: '朝鲜', en: 'North Korea' },
  { code: '+878', country: '国际卫星电话', en: 'Universal Personal Telecommunication' },
  { code: '+960', country: '马尔代夫', en: 'Maldives' },
  { code: '+961', country: '黎巴嫩', en: 'Lebanon' },
  { code: '+962', country: '约旦', en: 'Jordan' },
  { code: '+963', country: '叙利亚', en: 'Syria' },
  { code: '+964', country: '伊拉克', en: 'Iraq' },
  { code: '+965', country: '科威特', en: 'Kuwait' },
  { code: '+966', country: '沙特阿拉伯', en: 'Saudi Arabia' },
  { code: '+967', country: '也门', en: 'Yemen' },
  { code: '+968', country: '阿曼', en: 'Oman' },
  { code: '+992', country: '塔吉克斯坦', en: 'Tajikistan' },
  { code: '+993', country: '土库曼斯坦', en: 'Turkmenistan' },
  { code: '+994', country: '阿塞拜疆', en: 'Azerbaijan' },
  { code: '+995', country: '格鲁吉亚', en: 'Georgia' },
  { code: '+996', country: '吉尔吉斯斯坦', en: 'Kyrgyzstan' },
  { code: '+998', country: '乌兹别克斯坦', en: 'Uzbekistan' },
];

/** 按 区号 / 中文名 / 英文名 模糊搜索区号 (小写包含匹配) */
export function searchDialCodes(keyword: string): DialCode[] {
  const k = (keyword || '').trim().toLowerCase();
  if (!k) return PHONE_DIAL_CODES;
  return PHONE_DIAL_CODES.filter(
    (d) => d.code.toLowerCase().includes(k)
      || d.country.toLowerCase().includes(k)
      || d.en.toLowerCase().includes(k),
  );
}

/** 默认区号 */
export const DEFAULT_DIAL_CODE = '+86';

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
// 响应信封容错: 后端正常返回 { data: [...] }, 少数场景 (空/降级) 可能直返数组。
export const listGroups = (resource: string, moduleId?: string) =>
  api.get(`/dynamic-fields/${resource}/groups/`, { params: moduleId ? { module_id: moduleId } : {} })
    .then((r) => {
      const raw = (r.data?.data ?? r.data ?? []) as FieldGroup[];
      return (Array.isArray(raw) ? raw : []).map(normalizeGroup);
    });

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

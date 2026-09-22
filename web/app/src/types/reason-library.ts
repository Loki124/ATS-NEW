/**
 * Reason Library 类型定义 (T-13)
 *
 * 与后端 apps/django/apps/reason_library/ 对齐:
 * - 路由前缀: /api/v1/reason-library/
 * - 响应信封: { code: number, data: T | null, message: string }
 * - 字段命名: camelCase (DB snake_case 经 djangorestframework-camel-case 自动转换)
 * - 并发策略: 可选乐观锁。后端仅在请求带 If-Match 时校验; 前端由
 *           ENABLE_OPTIMISTIC_LOCK 开关控制, 单人场景默认关闭。
 *
 * Q&A 决策 (主理人拍板):
 * - Q1+Q2: 系统预置分类/规则仅超管可改, 其他人只读
 * - Q3: 业务态查询优先级 = 显式引用 > 系统预置; 多条显式引用取最新 updatedAt
 * - Q5: 标签 CSV 导入 / 规则 JSON 导入
 * - Q6: 同一场景仅可使用一个规则 + 有场景引用的规则不可停用
 * - Q7: 5 大类不作为标签字段
 * - Q-A1: MAX_PICK 全场景统一 5
 * - Q-A4: reason_tag.name UNIQUE 包含软删记录
 * - Q-A5: Active 查询缓存不按 user.role 区分
 */

// ==================== 枚举 / 字面量联合 ====================

/** 6 个业务场景 (PRD §3 + 后端 SceneKey choices) */
export type SceneKey =
  | '筛选不通过'
  | '取消面试'
  | '放入人才库'
  | '淘汰'
  | '标记失败'
  | '邀约标注'

/** 全部 SceneKey 数组 — TagPicker / SceneEditor / Step3 预览循环都用 */
export const SCENE_OPTIONS: ReadonlyArray<SceneKey> = [
  '筛选不通过',
  '取消面试',
  '放入人才库',
  '淘汰',
  '标记失败',
  '邀约标注',
]

/** 标签类型: system 仅超管可改, custom 自助维护 */
export type TagType = 'system' | 'custom'

/** 业务错误码 (与后端 exceptions.py BizCode 对齐, 见 API 文档 §4) */
export const BIZ_CODE = {
  // 成功（与后端 exceptions.py BizCode 对齐，成功码 = 0）
  SUCCESS: 0,
  // Tag
  TAG_NAME_DUPLICATED: 40001,
  SYSTEM_TAG_IMMUTABLE: 40002,
  TAG_HAS_REFS: 40003,
  CSV_FORMAT_INVALID: 40004,
  TAG_NOT_FOUND: 40401,
  TAG_ALREADY_ASSIGNED: 40902, // Item4: 标签已归属其它分类, 不可跨分类重复 (与后端 exceptions.BizCode 对齐)
  // Rule
  RULE_NAME_DUPLICATED: 40101,
  RULE_NOT_FOUND: 40102,
  OPTIMISTIC_LOCK_FAILED: 40103,
  RULE_HAS_SCENE_REFS: 40104,
  SYSTEM_RULE_IMMUTABLE: 40105,
  RULE_SCENE_CONFLICT: 40106,
  JSON_FORMAT_INVALID: 40107,
  CATEGORY_LEVEL_EXCEED: 40108,
} as const

export type BizCodeValue = typeof BIZ_CODE[keyof typeof BIZ_CODE]

// ==================== 业务实体 ====================

export interface ReasonTag {
  id: string
  code?: string
  name: string
  enName?: string
  tip?: string
  type: TagType
  enabled: boolean
  /** 引用计数 (规则→分类→标签) — 后端 retrieve 详情透出 */
  refCount?: number
  createdAt: string
  updatedAt: string
}

export interface ReasonTagPayload {
  name: string
  enName?: string
  tip?: string
  type?: TagType
  enabled?: boolean
}

/**
 * 原因分类 (嵌套树, 最多 4 级)
 * - tags 字段仅末级分类填充; 非末级 tags = [] (后端 serializer 约束)
 * - allowCustom: true → 业务方可在弹窗里追加"其他"输入
 */
export interface RuleCategory {
  id: string
  parentId?: string
  name: string
  level: 1 | 2 | 3 | 4
  order: number
  allowCustom: boolean
  tags: ReasonTag[]
  /**
   * 后端序列化仅下发 tagIds (camelCase), 不返回完整的 tags 对象。
   * 前端需从标签池 (allTags) 按 id 重建 tags, 否则编辑已有规则时
   * 所有已分配标签会被静默清空。见 ReasonRuleWizard.deepCloneCategories。
   */
  tagIds?: string[]
}

export interface SceneRule {
  id: string
  name: string
  isSystem: boolean
  enabled: boolean
  description?: string
  scenes: SceneKey[]
  /** 用户在实际使用弹窗中最多可选的原因标签条数 (0 表示不限制) */
  maxSelectableTags: number
  /** 完整嵌套分类树 (含末级 tags) */
  categories: RuleCategory[]
  /** 列表接口附加的统计字段 (后端 _count 或 @property) */
  sceneCount?: number
  categoryCount?: number
  tagCount?: number
  createdAt: string
  updatedAt: string
}

export interface SceneRuleListItem {
  id: string
  name: string
  isSystem: boolean
  enabled: boolean
  description?: string
  scenes: SceneKey[]
  /** 用户在实际使用弹窗中最多可选的原因标签条数 (0 表示不限制) */
  maxSelectableTags: number
  sceneCount: number
  categoryCount: number
  tagCount: number
  updatedAt: string
}

export interface SceneRuleUpdatePayload {
  name?: string
  description?: string
  enabled?: boolean
  scenes?: SceneKey[]
  /** 可选乐观锁: 仅 ENABLE_OPTIMISTIC_LOCK=true 时携带 (取自列表 updatedAt) */
  ifMatch?: string
}

// ==================== Wizard 专用 ====================

/**
 * Step3 预览与 Step1 编辑共用的 Wizard 草稿
 * - 三步通过 v-model 共享这一份, 任何一步修改都立即反映到预览
 * - assignments 不在此处: 直接读 categories[*].tags (后端以 tags 数组存储)
 */
export interface WizardPayload {
  /** 新建时为空字符串 ''; 编辑时为已有规则 id */
  id: string
  name: string
  description?: string
  enabled: boolean
  isSystem: boolean
  scenes: SceneKey[]
  /** 用户在实际使用弹窗中最多可选的原因标签条数 (0 表示不限制) */
  maxSelectableTags: number
  categories: RuleCategory[]
  updatedAt?: string
}

/**
 * Wizard 保存时真正发给后端的 payload (T-BF-02 BugFix):
 * - 字段命名与后端 WizardSaveSerializer 对齐 (snake_case)
 * - categories 项不含嵌套 tags 对象, 仅 tag_ids: string[]
 * - 父引用走 client_id 字符串, 而不是后端入库后的真实 id
 *
 * 由 api/reason-library.ts 的 toWizardSavePayload 从 WizardPayload 转换而来。
 */
export interface WizardSaveCategory {
  /** 已存在分类的真实 id (后端用于匹配已有记录) */
  id?: string
  /** 前端临时 ID — 新建分类必填, 已存在分类沿用 WizardPayload.id */
  client_id: string
  /** 父分类的 client_id (同一棵树内的临时引用) */
  parent_client_id?: string
  name: string
  order: number
  allow_custom: boolean
  tag_ids: string[]
}

export interface WizardSavePayload {
  name: string
  description?: string
  enabled: boolean
  scenes: SceneKey[]
  /** 用户可选原因标签上限 (0 表示不限制) */
  max_selectable_tags: number
  categories: WizardSaveCategory[]
  /** 可选乐观锁: 仅 ENABLE_OPTIMISTIC_LOCK=true 时携带 (对应 payload.updatedAt) */
  expected_updated_at?: string
}

// ==================== 响应信封 ====================

/** 标准响应 { code, data, message } */
export interface ApiResponse<T> {
  code: number
  data: T | null
  message: string
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

export interface TagListQuery {
  type?: TagType
  enabled?: boolean
  search?: string
  page?: number
  /** 后端 StandardResultsSetPagination 的参数名是 page_size */
  pageSize?: number
}

export interface RuleListQuery {
  isSystem?: boolean
  enabled?: boolean
  search?: string
  page?: number
  pageSize?: number
}

export interface TagImportResult {
  success: number
  failed: number
  errors: { row: number; message: string }[]
}

export interface SceneConfigItem {
  scene: SceneKey
  ruleId: string | null
  ruleName: string | null
}

export interface SceneConfigPayload {
  items: SceneConfigItem[]
}

// ==================== 常量 (与 §6 业务规则对齐) ====================

/** 单分类下最多可分配的标签数 — Q-A1 全场景统一 */
export const MAX_PICK = 5

/** 分类层级上限 */
export const MAX_CATEGORY_LEVEL = 4

/** CSV 模板列 (前端 import modal 提示用) */
export const CSV_COLUMNS_HINT = ['name(必填)', 'en_name', 'tip', 'type(custom)', 'enabled(true/false)']

/** 系统角色判定 — 调用 useUserStore().user?.roles?.includes('SUPER_ADMIN') */
export const ROLE_SUPER_ADMIN = 'SUPER_ADMIN'

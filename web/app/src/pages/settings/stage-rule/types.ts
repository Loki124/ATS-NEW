/**
 * 阶段配置规则 — 类型定义
 * 严格对齐后端 schema（EntryConditionRuleViewSet / StageRule skip_rules·archive_rules JSONField）。
 * 颜色 / 视觉一律走 design token，本文件不含任何样式。
 */

/** 数据源枚举（condition_type）。v1 仅渲染后端返回的 3 种，缺口（POSITION/RESUME）不出现。 */
export type SourceKey = 'STAGE_STATUS' | 'CANDIDATE' | 'DEMAND'

/** 运算符枚举（与后端 services.py 解析映射一致） */
export type OperatorKey =
  | 'EQ'
  | 'NEQ'
  | 'GT'
  | 'GTE'
  | 'LT'
  | 'LTE'
  | 'BETWEEN'
  | 'IN'
  | 'NOT_IN'
  | 'IS_EMPTY'
  | 'IS_NOT_EMPTY'

/** 自动跳过执行动作 */
export type SkipAction = 'SKIP' | 'APPROVE' | 'REJECT'

/** 单条条件项（1 个 EntryConditionRule = 1 expression + N ConditionItem，扁平无嵌套组） */
export interface ConditionItem {
  id?: string
  item_seq: number
  condition_type: SourceKey
  field: string
  stage_name?: string | null
  stage_statuses?: string[]
  operator: OperatorKey
  value?: any
  auto_filter_inactive_users?: boolean
}

/** 单个条件组（HTML 原型 UI 嵌套结构；后端无对应 schema，本地 state 模拟） */
export interface ConditionGroup {
  /** 组内条件项序列 1..N */
  conditions: ConditionItem[]
  /** 组内表达式（如 "1 and 2"），可空 */
  innerExpression: string
  /** 组内未满足提示，可空 */
  innerPrompt: string
}

/** 进入条件规则（= 原型 1 个条件组）。本地 draft 仍用 groups 嵌套结构，落库时拍平 */
export interface EntryConditionRule {
  id?: string
  rule_name: string
  rule_seq: number
  status: 'ENABLED' | 'DISABLED'
  /** 整条规则的"条件组表达式"（如 "(1) and (2)"），落库写入 expression */
  expression: string
  /** 整条规则的"整体未满足提示"（textarea，最多 500 字），落库写入 reject_message */
  reject_message: string
  /** 嵌套条件组（编辑态用）；加载/落库时与 items / expression / reject_message 双向转换 */
  groups?: ConditionGroup[]
  /** 拍平后的条件项（落库/加载用） */
  items: ConditionItem[]
}

/** 自动跳过规则（存于 StageRule.skip_rules JSON 数组） */
export interface SkipRule {
  id: string
  name: string
  enabled: boolean
  scope: 'NEW_ONLY' | 'ALL'
  expression: string
  items: ConditionItem[]
  action: SkipAction
}

/** 自动归档规则（存于 StageRule.archive_rules JSON 数组） */
export interface ArchiveRule {
  id: string
  name: string
  enabled: boolean
  scope: 'NEW_ONLY' | 'ALL'
  expression: string
  items: ConditionItem[]
  lock_days: number
  extend_days: number
  effective_scope: 'ALL' | 'NEW_ONLY'
}

/** 字段字典：单个字段定义 */
export interface FieldDef {
  field: string
  label: string
  operators: OperatorKey[]
  is_array?: boolean
  auto_filter_inactive_users?: boolean
  /** 值类型（后端按指标 data_type 推导）：number / string / date / boolean / enum。前端据此选择输入控件 */
  valueType?: 'number' | 'string' | 'date' | 'boolean' | 'enum'
  /** 枚举 / 布尔字段的下拉选项（后端就绪后由 /expressions/fields 返回，前端仅渲染） */
  options?: { label: string; value: string }[]
}

/** 字段字典：单个 source 定义 */
export interface SourceDef {
  source: SourceKey
  label: string
  fields: FieldDef[]
}

/** 字段字典整体结构（对齐 spec §1 约定契约） */
export interface FieldCatalog {
  sources: SourceDef[]
  operators: Record<OperatorKey, string>
}

/** 主表单聚合 state（StageRule 主链路 + entry/skip/archive 三类规则） */
export interface StageRuleFormState {
  // Card 2 默认处理人
  defaultHandlerType: 'FROM_DEMAND' | 'FROM_POSITION' | 'CUSTOM' | 'NONE'
  defaultHandlerFields: string[]
  defaultHandlerUserIds: string[]
  // Card 3 面试配置
  interviewRoundIds: string[]
  interviewFormat: string[]
  // Card 4 流程自动化
  autoEvalN2: boolean
  autoEvalPrevAa: boolean
  autoAdvanceType: 'NONE' | 'MEET_NEXT' | 'IGNORE_NEXT' | 'MEET_NEXT_OR_N2' | 'N1_ALL_PASS'
  autoAdvanceTiming: 'NONE' | 'IMMEDIATE' | 'DELAYED'
  autoAdvanceDays: number | null
  skipEnabled: boolean
  archiveEnabled: boolean
}

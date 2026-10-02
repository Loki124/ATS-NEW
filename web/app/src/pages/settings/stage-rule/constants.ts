/**
 * 阶段配置规则 — 静态 UI 配置（label / 选项 / 文案）
 *
 * 字段目录（source → field → operator → value）由真实后端端点
 *   GET /api/v1/expressions/fields（EntryConditionFieldCatalogView）提供，
 *   前端不再保留任何 mock 字段字典；本文件仅沉淀稳定的展示文案与下拉选项。
 *
 * 所有视觉一律走 design token，本文件不含任何样式。
 */
import type { OperatorKey, SourceKey } from './types'

/** source → UI 展示名（仅渲染后端支持的 3 种；POSITION/RESUME 缺口不出现） */
export const AR_SOURCE_LABELS: Record<SourceKey, string> = {
  DEMAND: '需求中',
  CANDIDATE: '候选人中',
  STAGE_STATUS: '阶段状态',
}

/** 运算符 → UI 展示名 */
export const AR_OPERATOR_LABELS: Record<OperatorKey, string> = {
  EQ: '等于',
  NEQ: '不等于',
  GT: '大于',
  GTE: '大于等于',
  LT: '小于',
  LTE: '小于等于',
  BETWEEN: '区间',
  IN: '属于',
  NOT_IN: '不属于',
  IS_EMPTY: '为空',
  IS_NOT_EMPTY: '不为空',
}

/** 自动跳过执行动作 → UI 展示名 */
export const AR_SKIP_ACTION_LABELS: Record<'SKIP' | 'APPROVE' | 'REJECT', string> = {
  SKIP: '跳过本阶段',
  APPROVE: '直接通过',
  REJECT: '直接拒绝',
}


/** Card 4 自动流转条件选项（静态，值复用后端 autoAdvanceType 枚举） */
export const AUTO_ADVANCE_OPTIONS = [
  { label: '不自动流转', value: 'NONE' },
  { label: '满足下阶段进入条件时 (推荐)', value: 'MEET_NEXT' },
  { label: '无视下阶段进入条件', value: 'IGNORE_NEXT' },
  { label: '满足下阶段条件或 N+2 推荐', value: 'MEET_NEXT_OR_N2' },
  { label: 'N+1 全部通过', value: 'N1_ALL_PASS' },
]

/** 执行时机选项（静态） */
export const AUTO_ADVANCE_TIMING_OPTIONS = [
  { label: '立即执行 (默认)', value: 'IMMEDIATE' },
  { label: '不执行', value: 'NONE' },
  { label: '延迟执行', value: 'DELAYED' },
]

/** Card 3 面试轮次：已改为真实数据源动态获取（listRounds → InterviewConfigCard），
 * 静态硬编码选项已删除（2026-10-02 兵哥：严禁 mock/硬编码）。 */

/** Card 3 面试形式静态选项（与后端枚举对齐；后续可由 dictionary-items?type_code=interview_mode 动态提供） */
export const INTERVIEW_FORMAT_OPTIONS = [
  { label: '现场', value: 'ONSITE' },
  { label: '电话', value: 'PHONE' },
  { label: '视频', value: 'VIDEO' },
  { label: 'AI', value: 'AI' },
]

/** Card 2 默认处理人数据来源（文档 §3.2.3 4 种：需求中/职位中/指定人/无默认处理人） */
export const HANDLER_SOURCE_OPTIONS = [
  { label: '需求中', value: 'FROM_DEMAND' },
  { label: '职位中', value: 'FROM_POSITION' },
  { label: '指定人', value: 'CUSTOM' },
  { label: '无默认处理人', value: 'NONE' },
]

/** Card 2 处理规则（静态） */
export const HANDLER_RULE_OPTIONS = [
  { label: '按顺序', value: 'IN_ORDER' },
  { label: '按角色', value: 'BY_ROLE' },
  { label: '指定人', value: 'ASSIGN' },
]

/** 条件组上限（原型约束） */
export const AR_MAX_CONDITIONS = 10

/** 条件组数上限（原型约束，最多 10 组） */
export const AR_MAX_GROUPS = 10

/** 规则名长度上限 */
export const AR_RULE_NAME_MAX = 30

/** 表达式 6 规则帮助文案（popover 用） */
export const EXPRESSION_HELP = [
  '仅允许数字、空格、括号与 AND / OR',
  '括号内不允许再嵌套括号',
  '同一组内不允许同时使用 AND 与 OR',
  '编号范围 1-N（N = 条件项数），引用未定义编号报错',
  '不允许使用大括号 {}',
  '表达式不能为空（留空 = 全部满足）',
]

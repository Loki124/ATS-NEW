/**
 * 阶段配置规则 — 临时常量 / mock 字段字典
 *
 * ⚠️ 过渡方案：后端 EntryConditionRuleViewSet 的字段字典接口
 *   (GET /api/v1/expressions/fields) 由后端 worker 实现中，前端先用本文件 mock 驱动 UI。
 *   字段名（DEMAND_LEVEL / HIRING_MANAGER / AGE / HIGHEST_EDU …）严格对齐后端
 *   services.py 真实解析映射，后端就绪后仅需把 listEntryConditionFields() 的 mock 分支切到真实接口，
 *   本文件即可整体退役（见 index.ts / useStageRuleForm 的 loadFields）。
 *
 * 所有视觉一律走 design token，本文件不含任何样式。
 */
import type { FieldCatalog, OperatorKey, SourceKey } from './types'

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

/**
 * 字段字典 mock（对齐 spec §1 契约结构）。
 * options 仅用于有固定枚举的字段（性别 / 学历 / 城市 / 部门 / 职级 / 阶段状态），
 * 其余（AGE / WORK_YEARS）走数值输入。
 */
export const AR_FIELD_CATALOG: FieldCatalog = {
  sources: [
    {
      source: 'DEMAND',
      label: '需求中',
      fields: [
        {
          field: 'DEMAND_LEVEL',
          label: '需求职级',
          operators: ['EQ', 'NEQ', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY'],
          options: [
            { label: 'P4', value: 'P4' },
            { label: 'P5', value: 'P5' },
            { label: 'P6', value: 'P6' },
            { label: 'P7', value: 'P7' },
            { label: 'P8', value: 'P8' },
          ],
        },
        { field: 'HIRING_MANAGER', label: '用人经理', operators: ['EQ', 'NEQ', 'IN'], auto_filter_inactive_users: true },
        {
          field: 'DEPARTMENT',
          label: '需求部门',
          operators: ['EQ', 'IN', 'NOT_IN'],
          options: [
            { label: '能效BG', value: '能效BG' },
            { label: '搜索BG', value: '搜索BG' },
            { label: '研发BG', value: '研发BG' },
          ],
        },
      ],
    },
    {
      source: 'CANDIDATE',
      label: '候选人中',
      fields: [
        { field: 'AGE', label: '年龄', operators: ['EQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'] },
        {
          field: 'GENDER',
          label: '性别',
          operators: ['EQ', 'NEQ', 'IN'],
          options: [
            { label: '男', value: 'MALE' },
            { label: '女', value: 'FEMALE' },
          ],
        },
        {
          field: 'HIGHEST_EDU',
          label: '最高学历',
          operators: ['EQ', 'NEQ', 'IN', 'NOT_IN'],
          options: [
            { label: '本科', value: 'BACHELOR' },
            { label: '硕士', value: 'MASTER' },
            { label: '博士', value: 'PHD' },
          ],
        },
        { field: 'WORK_YEARS', label: '工作年限', operators: ['EQ', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN'] },
        {
          field: 'CURRENT_CITY',
          label: '当前城市',
          operators: ['EQ', 'IN', 'NOT_IN'],
          options: [
            { label: '北京', value: '北京' },
            { label: '上海', value: '上海' },
            { label: '深圳', value: '深圳' },
            { label: '杭州', value: '杭州' },
          ],
        },
        {
          field: 'EXPECTED_CITY',
          label: '期望城市',
          operators: ['EQ', 'IN', 'NOT_IN'],
          options: [
            { label: '北京', value: '北京' },
            { label: '上海', value: '上海' },
            { label: '深圳', value: '深圳' },
            { label: '杭州', value: '杭州' },
          ],
        },
      ],
    },
    {
      source: 'STAGE_STATUS',
      label: '阶段状态',
      fields: [
        { field: 'stage_name', label: '阶段名称', operators: ['EQ', 'NEQ', 'IN'] },
        { field: 'stage_statuses', label: '阶段状态', operators: ['IN', 'NOT_IN'], is_array: true },
      ],
    },
  ],
  operators: AR_OPERATOR_LABELS,
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

/** Card 3 面试轮次 mock（后端就绪后由 dictionary-items?type_code=interview_round 替换） */
export const INTERVIEW_ROUND_OPTIONS = [
  { label: '联合面试', value: 'JOINT' },
  { label: '综合面试', value: 'COMPREHENSIVE' },
  { label: '初试', value: 'FIRST' },
  { label: '复试', value: 'SECOND' },
  { label: '终试', value: 'FINAL' },
]

/** Card 3 面试形式 mock（后端就绪后由 dictionary-items?type_code=interview_mode 替换） */
export const INTERVIEW_FORMAT_OPTIONS = [
  { label: '现场', value: 'ONSITE' },
  { label: '电话', value: 'PHONE' },
  { label: '视频', value: 'VIDEO' },
  { label: 'AI', value: 'AI' },
]

/** Card 2 默认处理人数据来源（静态，值复用后端 defaultHandlerType 枚举） */
export const HANDLER_SOURCE_OPTIONS = [
  { label: '需求中', value: 'FROM_DEMAND' },
  { label: '职位中', value: 'FROM_POSITION' },
  { label: '指定人', value: 'CUSTOM' },
]

/** Card 2 处理规则（静态） */
export const HANDLER_RULE_OPTIONS = [
  { label: '按顺序', value: 'IN_ORDER' },
  { label: '按角色', value: 'BY_ROLE' },
  { label: '指定人', value: 'ASSIGN' },
]

/** 条件组上限（原型约束） */
export const AR_MAX_CONDITIONS = 10

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

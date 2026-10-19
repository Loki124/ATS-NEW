/**
 * permissionMenu.ts — 菜单 / 路由可见性用的「前端路径 → 后端资源码」映射（G4）。
 *
 * 背景：
 *   身份管理里配置的功能权限（role_permission → /me.permissions）此前只落地在
 *   后端，前端菜单是静态数组、路由守卫只看 meta.roles，导致「配了功能权限但前端
 *   入口照常可见」。这里把菜单项与真实资源码对齐，让菜单/路由真正按配置显隐。
 *
 * 语义（fail-open，绝不把用户锁死）：
 *   - 未配置功能权限（/me.permissions 为空数组）→ 全部可见，交由后端 403 兜底；
 *   - 已配置 → 命中最长前缀对应的资源码才可见；
 *   - 未在表中登记的路径 → 视为公共入口，恒可见（逐步补齐，不阻塞上线）。
 *
 * 码表来源：apps/django/apps/core/management/commands/seed_v2_init.RESOURCES（MENU 类）。
 */
import type { MenuOption } from 'naive-ui'

interface MenuCodeRule {
  /** 路径前缀（按长度降序匹配，取最长命中） */
  prefix: string
  /** 对应 resource_code */
  code: string
}

/** 前端路径 → 资源码。按前缀长度降序匹配，保证 /settings/company/brand 不会被 /settings/company 抢走。 */
export const MENU_PERMISSION_RULES: MenuCodeRule[] = [
  // ===== 主导航 =====
  { prefix: '/candidates', code: 'recruit:candidate:menu:view' },
  { prefix: '/screenings', code: 'recruit:candidate:menu:view' },
  { prefix: '/demands', code: 'recruit:demand:menu:view' },
  { prefix: '/positions', code: 'recruit:position:menu:view' },
  { prefix: '/talent-pool', code: 'recruit:talent_pool:menu:view' },
  { prefix: '/interviews', code: 'recruit:interview:menu:view' },
  { prefix: '/invitations', code: 'recruit:invitation:menu:view' },
  { prefix: '/offers', code: 'recruit:offer:menu:view' },
  { prefix: '/onboardings', code: 'recruit:onboarding:menu:view' },
  { prefix: '/report', code: 'recruit:settings:data_dashboard:menu:view' },
  { prefix: '/my-resumes', code: 'recruit:settings:scraped_resumes:menu:view' },

  // ===== 公司信息 =====
  { prefix: '/settings/company/address', code: 'recruit:settings:company_address:menu:view' },
  { prefix: '/settings/company/meeting-rooms', code: 'recruit:settings:company_meeting_rooms:menu:view' },
  { prefix: '/settings/company/resume-mailbox', code: 'recruit:settings:company_resume_mailbox:menu:view' },
  { prefix: '/settings/company/brand', code: 'recruit:settings:company_brand:menu:view' },
  { prefix: '/settings/company', code: 'recruit:settings:company:menu:view' },

  // ===== 基本信息其余项 =====
  { prefix: '/settings/account', code: 'recruit:settings:account:menu:view' },
  { prefix: '/settings/department', code: 'recruit:settings:department:menu:view' },
  // ===== 组织管理：职务 / 职级（2026-10-14 org-mgmt）=====
  { prefix: '/settings/job-title', code: 'recruit:settings:job_title:menu:view' },
  { prefix: '/settings/job-level', code: 'recruit:settings:job_level:menu:view' },
  { prefix: '/settings/users/all', code: 'recruit:settings:users:all:menu:view' },
  { prefix: '/settings/registrations', code: 'recruit:settings:registrations:menu:view' },
  { prefix: '/settings/user-groups', code: 'recruit:settings:user_groups:menu:view' },

  // ===== 权限管理（本模块自身入口）=====
  { prefix: '/settings/permissions/resources', code: 'recruit:settings:permissions:resources:menu:view' },
  { prefix: '/settings/permissions', code: 'recruit:settings:permissions:menu:view' },
  // 动态策略（2026-10-19 补登记：此前未登记走 fail-open 恒可见，HRBP 等低权角色也能看到入口）
  { prefix: '/settings/dynamic-strategy', code: 'recruit:settings:dynamic_strategy:menu:view' },
  { prefix: '/settings/mou', code: 'recruit:mou:menu:view' },
  { prefix: '/settings/field-acl', code: 'recruit:settings:field_acl:menu:view' },

  // ===== 候选人信息 =====
  { prefix: '/settings/candidate-dynamic-fields', code: 'recruit:settings:candidate_dynamic_fields:menu:view' },
  { prefix: '/settings/standard-resume', code: 'recruit:settings:standard_resume:menu:view' },
  { prefix: '/settings/application-form', code: 'recruit:settings:application_form:menu:view' },
  { prefix: '/settings/candidate-info-table', code: 'recruit:settings:candidate_info_table:menu:view' },
  { prefix: '/settings/duplicate-candidate', code: 'recruit:settings:duplicate_candidate:menu:view' },
  { prefix: '/settings/resume-parser-engine', code: 'recruit:settings:resume_parser_engine:menu:view' },

  // ===== 需求管理 =====
  { prefix: '/settings/demand-dynamic-fields', code: 'recruit:settings:demand_dynamic_fields:menu:view' },
  { prefix: '/settings/demand-form-settings', code: 'recruit:settings:demand_form_settings:menu:view' },
  { prefix: '/settings/demand-config', code: 'recruit:settings:demand_config:menu:view' },
  { prefix: '/settings/scoring', code: 'recruit:settings:scoring:menu:view' },

  // ===== 职位 / 面试 / Offer / 校招管控 =====
  { prefix: '/settings/position-dynamic-fields', code: 'recruit:settings:position_dynamic_fields:menu:view' },
  { prefix: '/settings/position-form-settings', code: 'recruit:settings:position_form_settings:menu:view' },
  { prefix: '/settings/position-info', code: 'recruit:settings:position_info:menu:view' },
  { prefix: '/settings/interview-management', code: 'recruit:settings:interview_management:menu:view' },
  { prefix: '/settings/offer-management', code: 'recruit:settings:offer_management:menu:view' },
  { prefix: '/settings/campus-control', code: 'recruit:settings:campus_control:menu:view' },
  { prefix: '/settings/campus-ambassador', code: 'recruit:settings:campus_ambassador:menu:view' },
  { prefix: '/settings/campus-session', code: 'recruit:settings:campus_session:menu:view' },

  // ===== 校园招聘（campus 模块）：轮岗安排 / 轮岗资源 / 班级管理 / 人员管理 =====
  // 最长前缀匹配（permissionForPath 取最长命中）；fail-open：未登记路径恒可见。
  { prefix: '/campus/rotation-arrangement', code: 'recruit:campus:rotation:menu:view' },
  { prefix: '/campus/live-room', code: 'recruit:campus:resource:menu:view' },
  { prefix: '/campus/class-room', code: 'recruit:campus:class:menu:view' },
  { prefix: '/campus/person', code: 'recruit:campus:person:menu:view' },

  // ===== 招聘分类信息 =====
  { prefix: '/settings/dictionary', code: 'recruit:settings:dictionary:menu:view' },
  // 原因库（2026-10-19 补登记；子路径 tags/rules 由最长前缀命中本条）
  { prefix: '/settings/reason-library', code: 'recruit:settings:reason_library:menu:view' },

  // ===== 提速配置 =====
  { prefix: '/settings/recruitment-stage', code: 'recruit:settings:recruitment_stage:menu:view' },
  { prefix: '/settings/recruitment-process', code: 'recruit:settings:recruitment_process:menu:view' },
  { prefix: '/settings/recruitment-round', code: 'recruit:settings:recruitment_round:menu:view' },

  // ===== 内容管理 =====
  { prefix: '/settings/announcements', code: 'recruit:settings:announcements:menu:view' },

  // ===== 其他 =====
  { prefix: '/settings/code-tables', code: 'recruit:settings:code_tables:menu:view' },
  // 动态数据（院校库/专业库/公司库聚合页；2026-10-19 补登记）
  { prefix: '/settings/dynamic-data', code: 'recruit:settings:dynamic_data:menu:view' },
  // 前端组件规范（2026-10-19 补登记：纳入权限管控；「主题外观」/settings/theme 按兵哥拍板保持全员可见，不登记）
  { prefix: '/settings/ui-templates', code: 'recruit:settings:ui_templates:menu:view' },
  { prefix: '/settings/data-dashboard', code: 'recruit:settings:data_dashboard:menu:view' },
  { prefix: '/settings/external', code: 'recruit:settings:external:menu:view' },
  { prefix: '/settings/rule-engine', code: 'recruit:settings:rule_engine:menu:view' },
  { prefix: '/settings/metrics', code: 'recruit:settings:metrics:list' },
]

/** 取路径命中的资源码（最长前缀优先）；未登记返回 undefined。 */
export function permissionForPath(path: string): string | undefined {
  if (!path?.startsWith('/')) return undefined
  let hit: MenuCodeRule | undefined
  for (const rule of MENU_PERMISSION_RULES) {
    if (path === rule.prefix || path.startsWith(rule.prefix + '/')) {
      if (!hit || rule.prefix.length > hit.prefix.length) hit = rule
    }
  }
  return hit?.code
}

/** 该路径是否被门禁管辖（未登记的路径视为公共入口）。 */
export function isPathGuarded(path: string): boolean {
  return permissionForPath(path) !== undefined
}

/**
 * 递归按权限裁剪菜单树：
 * - 叶子项按自身 key 判定；**未登记路径一律保留**（fail-open 由本函数强制执行，
 *   不依赖调用方传入的 canAccess 对 undefined 的处理，避免误删公共入口）；
 * - 分组/父项在自身有 children 时，递归后 children 全空才移除（部分保留）；
 * - 未登记路径恒保留。
 */
export function filterMenuByPermission(
  options: MenuOption[],
  canAccess: (code?: string) => boolean,
): MenuOption[] {
  const out: MenuOption[] = []
  for (const opt of options) {
    const children = (opt.children ?? []) as MenuOption[]
    const key = String(opt.key ?? '')
    // 只有以 / 开头的 key 才是可点击路由；'g-xxx' 之类的分组/父项仅是容器，
    // 其自身没有权限码，子项被裁空时应整体消失，不留空壳标题。
    const selfCode = permissionForPath(key)
    if (children.length > 0) {
      const keptChildren = filterMenuByPermission(children, canAccess)
      const selfOk = key.startsWith('/') && (selfCode === undefined || canAccess(selfCode))
      if (keptChildren.length > 0 || selfOk) {
        out.push({ ...opt, children: keptChildren })
      }
      continue
    }
    if (selfCode === undefined || canAccess(selfCode)) out.push(opt)
  }
  return out
}

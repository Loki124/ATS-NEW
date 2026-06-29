/**
 * Role 派生工具 — 前端 RBAC 派生"主角色"用于 UI 简化
 *
 * 历史: 2026-06-15 refactor (commit `01c6b3d4 refactor: reorganize into ATS-New monorepo`)
 *       那个不完整 refactor 加了 `import { deriveRoleType } from '../utils/role'`
 *       在 user.ts:4 / Login.vue:158 但**漏了 file**,整个 main 分支 `npm run build`
 *       自那天起永远 fail (TS2307 cannot find module '../utils/role').
 *
 * 设计:
 *   - 后端 (apps/core/views_auth.py) emit roles: string[] (真值 RBAC role codes)
 *   - 路由级 RBAC 用 userRoles.some(r => requiredRoles.includes(r)) 多角色细粒度
 *   - UI 简化展示 / 顶栏 avatar 旁的角色标签 → 用 deriveRoleType 派生"主角色"
 *
 * 派生规则 (按 ROLE_PRIORITY 从高到低, 返回第一个匹配的):
 *   - 数组为空 → null
 *   - SUPER_ADMIN 永远排第一 (系统超管, 不受 RBAC 限制, router guard 里 isSuperAdmin 始终放行)
 *   - 未识别的 role 兜底返回 roles[0] (不返 null, 让 UI 至少显示点什么)
 *
 * 2026-06-28 花无缺 反推自:
 *   - src/stores/user.ts:21  (roleType?: string | null, 给路由 guard / 顶栏 UI 用)
 *   - src/stores/user.ts:126 (const roleType = deriveRoleType(roles))
 *   - src/pages/Login.vue:204 (const roleType = deriveRoleType(roles))
 *   - src/router/__tests__/router.test.ts:40,54,66,78,91
 *     (测试用 SUPER_ADMIN / HRBP / HR 三种 roleType 验证路由 guard)
 *
 * TODO (兵哥审):
 *   - ROLE_PRIORITY 排序对不对?后端 apps/core/permissions.py / RBAC 文档是不是还有别的 code?
 *   - 现排序按 router.test.ts 引用过的 role 倒推,实际生产可能漏了 ADMIN / RECRUITER / CANDIDATE 等
 *   - 后端实际 emit 的 role code 是什么格式?大写 snake_case 还是其他?
 */

/**
 * Role 优先级 (从高到低).
 * 排序依据: router guard 测试覆盖 + 业务常识 (超管 > HRBP > HR > 面试官 > 普通用户).
 *
 * ⚠️ 这是反推的最小集, 兵哥拿到真 RBAC 表后请补全 / 调整.
 */
export const ROLE_PRIORITY: readonly string[] = [
  'SUPER_ADMIN',   // 系统超管, 不受 RBAC 限制 (router guard `isSuperAdmin` 放行)
  'HRBP',          // HR Business Partner (业务 HR)
  'HR',            // HR 普通
  'RECRUITER',     // 招聘官 (UI 备选项, 不确定后端是否用这个 code)
  'INTERVIEWER',   // 面试官
  'USER',          // 普通登录用户
  // TODO: 兵哥补 ADMIN / CANDIDATE / 其他
] as const

/**
 * 从后端返回的 roles 数组派生"主角色" (用于 UI 简化展示).
 *
 * @param roles - 后端 emit 的 RBAC role codes (真值, 数组, 可空)
 * @returns 按 ROLE_PRIORITY 第一个匹配的 role code, 或:
 *   - `null` 当数组为空
 *   - `roles[0]` 当没有任何 ROLE_PRIORITY 里登记的 role (兜底, 至少显示第一个)
 *
 * @example
 *   deriveRoleType(['HR'])                          // 'HR'
 *   deriveRoleType(['HR', 'INTERVIEWER'])           // 'HR'  (按优先级)
 *   deriveRoleType(['SUPER_ADMIN', 'HR'])           // 'SUPER_ADMIN'
 *   deriveRoleType(['CUSTOM_UNKNOWN_ROLE'])          // 'CUSTOM_UNKNOWN_ROLE'  (兜底)
 *   deriveRoleType([])                              // null
 *   deriveRoleType(null)                            // null
 */
export function deriveRoleType(roles: string[] | null | undefined): string | null {
  if (!roles || roles.length === 0) return null
  for (const role of ROLE_PRIORITY) {
    if (roles.includes(role)) return role
  }
  // 没匹配到 ROLE_PRIORITY 里的任何 role (可能是新的 role code 还没登记)
  // 兜底: 返回第一个, 至少 UI 能显示, 后续可以补 ROLE_PRIORITY
  return roles[0]
}

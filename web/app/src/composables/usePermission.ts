/**
 * usePermission — 元素级最小权限 UI 的组合式.
 *
 * 后端 /me (apps/core/views_auth.py) 已返回 `permissions: string[]` (resource_code 扁平列表,
 * 如 'recruit:candidate:edit'), 按用户角色模板展开; 超管拿全部码.
 * 此前前端只用 meta.roles 白名单做路由级 RBAC, 元素级按钮从未消费 resource_code ——
 * 导致"页面能进但某个按钮该不该显示"只能硬编码角色判断. 本组合式 + v-permission 指令
 * 让任意按钮按真实权限自适应显示/禁用 (最小权限 UI).
 *
 * 用法:
 *   const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermission()
 *   hasPermission('recruit:candidate:edit')           // 单个
 *   hasAnyPermission(['a','b'])                        // 任一
 *   hasAllPermissions(['a','b'])                       // 全部
 *
 * 超管兜底: 即便 stale localStorage 里 permissions 为空, 只要 roles 含 SUPER_ADMIN 也放行,
 * 与后端 is_super_admin 语义一致.
 */
import { computed } from 'vue'
import { useUserStore } from '../stores/user'

const SUPER_ADMIN = 'SUPER_ADMIN'

export function usePermission() {
  const userStore = useUserStore()
  const permissions = computed<string[]>(() => userStore.user?.permissions ?? [])
  const roles = computed<string[]>(() => userStore.user?.roles ?? [])

  const isSuperAdmin = () => roles.value.includes(SUPER_ADMIN)

  /**
   * 后端是否已下发功能权限清单。
   * `permissions` 来自 /me 的 role_permission 展开（apps/core/views_auth.py:245-262），
   * 空数组意味着该用户的角色**从未配置过功能权限** —— 这是「未配置」而非「无权限」。
   */
  const isPermissionConfigured = computed<boolean>(() => permissions.value.length > 0)

  /**
   * 菜单 / 路由的可见性判定（fail-open，绝不把用户锁死）：
   * - 未配置功能权限（permissions 为空）→ 一律可见，交由后端 403 兜底；
   * - 已配置 → 必须命中对应资源码；
   * - 超管 → 恒可见。
   */
  const canAccess = (code?: string | null): boolean => {
    if (!code) return true
    if (isSuperAdmin()) return true
    if (!isPermissionConfigured.value) return true
    return permissions.value.includes(code)
  }

  /** 是否拥有某个资源码 */
  const hasPermission = (code: string): boolean => {
    if (isSuperAdmin()) return true
    return permissions.value.includes(code)
  }

  /** 是否拥有给定列表中的任意一个 */
  const hasAnyPermission = (codes: string | string[]): boolean => {
    const list = Array.isArray(codes) ? codes : [codes]
    if (isSuperAdmin()) return true
    return list.some((c) => permissions.value.includes(c))
  }

  /** 是否拥有给定列表中的全部 */
  const hasAllPermissions = (codes: string | string[]): boolean => {
    const list = Array.isArray(codes) ? codes : [codes]
    if (isSuperAdmin()) return true
    return list.every((c) => permissions.value.includes(c))
  }

  return {
    permissions,
    roles,
    isSuperAdmin,
    isPermissionConfigured,
    canAccess,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
  }
}

/**
 * v-permission — 元素级最小权限指令.
 *
 * 后端 /me (apps/core/views_auth.py) 已返回 `permissions: string[]` (resource_code 扁平列表,
 * 如 'recruit:candidate:edit'), 按用户角色模板展开; 超管拿全部码.
 * 此前前端只用 meta.roles 白名单做路由级 RBAC, 元素级按钮从没消费 resource_code ——
 * 导致"页面能进但某按钮该不该显示"只能硬编码角色判断. 本指令让任意元素按真实权限
 * 自适应隐藏/禁用 (最小权限 UI), 与 usePermission() 组合式同底层.
 *
 * 用法:
 *   <button v-permission="'recruit:candidate:edit'">编辑简历</button>      // 无权限: 隐藏
 *   <button v-permission.disable="'recruit:candidate:edit'">删除</button>  // 无权限: 置灰禁用
 *   <button v-permission="['a','b']">任一即可</button>                     // 数组: 任一命中即显示
 *
 * 超管兜底: roles 含 SUPER_ADMIN 时一律放行, 与后端 is_super_admin 语义一致.
 * 响应式: 通过 watch(permissions/roles) 跟随登录态变化; 切换账号后元素自动显隐.
 */
import type { App, Directive, DirectiveBinding } from 'vue'
import { watch } from 'vue'
import { usePermission } from '../composables/usePermission'

interface ElWithPerm extends HTMLElement {
  __perm?: ReturnType<typeof usePermission>
  __permissionStop__?: () => void
}

function apply(el: ElWithPerm, binding: DirectiveBinding) {
  const perm = el.__perm
  if (!perm) return
  const value = binding.value
  let allowed = false
  if (Array.isArray(value)) allowed = perm.hasAnyPermission(value as string[])
  else if (typeof value === 'string') allowed = perm.hasPermission(value)

  if (allowed) {
    el.style.display = ''
    el.style.pointerEvents = ''
    el.style.opacity = ''
    el.removeAttribute('disabled')
    return
  }
  if (binding.modifiers.disable) {
    el.style.pointerEvents = 'none'
    el.style.opacity = '0.5'
    el.setAttribute('disabled', '')
  } else {
    el.style.display = 'none'
  }
}

const permissionDirective: Directive = {
  mounted(el: ElWithPerm, binding: DirectiveBinding) {
    const perm = usePermission()
    el.__perm = perm
    // 跟随登录态变化: 切换账号 / 重新 fetchMe 后元素自动显隐
    el.__permissionStop__ = watch(
      [perm.permissions, perm.roles],
      () => apply(el, binding),
      { immediate: true },
    )
  },
  updated(el: ElWithPerm, binding: DirectiveBinding) {
    apply(el, binding)
  },
  unmounted(el: ElWithPerm) {
    el.__permissionStop__?.()
    delete el.__permissionStop__
    delete el.__perm
  },
}

export function setupPermissionDirective(app: App) {
  app.directive('permission', permissionDirective)
}

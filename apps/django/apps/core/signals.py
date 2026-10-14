"""Core Signals

轻量级 signal：监听 last_login 字段变化时同步 last_login_at
（不依赖 django-dirtyfields，使用 Django 内置 get_deferred_fields / pk 判定）
"""
import logging

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import User

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=User)
def sync_last_login_at(sender, instance, **kwargs):
    """Django 内置 last_login 字段被更新时，同步到自定义 last_login_at 字段

    通过对比 instance.pk 是否已存在 + 比较新旧值判断：
    - 新建用户（pk 为空）→ 跳过
    - last_login 变化 → 同步到 last_login_at
    """
    if not instance.pk:
        # 新建用户，跳过
        return
    try:
        old = User.objects.only('last_login').get(pk=instance.pk)
    except User.DoesNotExist:
        return
    if old.last_login != instance.last_login and instance.last_login is not None:
        instance.last_login_at = instance.last_login
        logger.debug('Synced last_login_at for user %s', instance.pk)


# ---------------------------------------------------------------------------
# P0-3 / R3 / C5：授权完整性钩子（替代 role_code FK 能达成但建不了的目标）。
#
# 为什么需要：RoleV2.role_code 是跨系统业务串、且 RoleV2 唯一键是
# (system_code, role_code) 复合键 → 无法建 FK（models_permission_v2.py:9,104）。
# 于是：
#   - UserRoleV2 侧：已由 user FK 覆盖（删用户清授权，见 0024）；
#   - RoleV2 侧：用 post_delete 信号清理 role_code 匹配的授权行，
#     保证「删角色 → 权限关联自动清除」（PRD P0-3 验收②的后半句，DR-01）。
#
# 用 post_delete 而非 pre_delete：此时 instance.pk 已不可用，但 instance.role_code
# / instance.system_code 仍可读。
#
# ⚠️ 删除是级联的、不可逆的：role_permission 侧的清理与角色删除同事务，角色删掉后
# 无法从本钩子恢复权限关联（role_permission 无快照）。这是预期行为（PRD P0-3 验收②
# 要求「自动清除」），但管理员必须知情 —— 前端删除角色的确认框文案须说明
# 「该角色的 N 条功能授权、M 条字段可见性规则将一并失效」（AGENTS.md R-106 破坏性告知）。
# T03 的数据库备份（见 ARCH §5.5.3）是这条唯一的兜底。
# ---------------------------------------------------------------------------
@receiver(post_delete, sender='core.RoleV2')
def purge_role_grants_on_delete(sender, instance, **kwargs):
    """删除角色时清掉 role_code 匹配的用户授权与权限关联。"""
    from apps.core.models_permission_v2 import RolePermissionV2, UserRoleV2

    UserRoleV2.objects.filter(
        role_code=instance.role_code, system_code=instance.system_code,
    ).delete()
    RolePermissionV2.objects.filter(
        role_code=instance.role_code, system_code=instance.system_code,
    ).delete()

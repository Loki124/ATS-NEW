"""校招生可见范围助手（2026-10-23 校招生全生命周期移植 · 契约 §1.3）。

**为什么要有这个模块**：校招域的「考核 / 学习 / 定岗」三个新 app 都要按
「当前用户能看哪些校招生」过滤列表，若各写各的，隔离口径必然漂移
（同一批人在三个页面可见范围不一致 = 静默越权）。故收敛为**唯一真源**。

**口径**（与逆向清单 §1.3 一致）：

| 角色 | 可见人员 |
|---|---|
| 超管 / 管理员 | 全部未删除人员 |
| 班主任（HEAD_TEACHER） | 自己带的班（`Person.head_teacher == user`） |
| 导师（MENTOR） | 自己带教的人（`Person.mentor == user`） |
| HRBP | 归属 HRBP（`Person.hrbp == user` 或班级 HRBP） |
| 校招生（STUDENT） | 仅本人（`Person.user_id == user.pk`） |
| 其他角色 | 本人（保守兜底：空集，不泄露） |

⚠️ **本助手是"基线隔离"，不是数据权限的替代品**：
数据权限（`apps/data_permission`）的 CUSTOM 规则在 ViewSet 层另行叠加。
两者取**交集**：本助手先按角色收窄，再由数据权限规则二次收窄。
若只看其一，会出现「角色隔离生效但数据权限形同虚设」或反之。

🔴 **不要在这里用 `Person.objects.all()`**：默认管理器可能过滤软删，
本模块统一显式 `deleted_at__isnull=True`（`objects` 是否已过滤软删取决于
`SoftDeleteModel` 的默认管理器实现 —— **显式写出来**最稳）。
"""
from django.db.models import Q, QuerySet

#: 校招域关心的角色码（`user_roles.role_code`，system_code='recruit'）
#: ⚠️ 角色码以 `roles` 表为真源（实测：SUPER_ADMIN / manage / HRBP / CAMPUS_MENTOR /
#:   HEAD_TEACHER / CLASS_MONITOR …）。导师的角色码是 **`CAMPUS_MENTOR`**（校园导师），
#:   不是 `MENTOR` —— 写错会让「导师只看自己徒弟」的隔离**静默失效**（退化成空集）。
ROLE_SUPER_ADMIN = 'SUPER_ADMIN'
ROLE_ADMIN = 'manage'
ROLE_HEAD_TEACHER = 'HEAD_TEACHER'
ROLE_MENTOR = 'CAMPUS_MENTOR'
ROLE_CLASS_MONITOR = 'CLASS_MONITOR'
ROLE_HRBP = 'HRBP'
ROLE_STUDENT = 'STUDENT'

#: 导师角色码的历史别名（若存量库存在旧码，一并识别）
ROLE_MENTOR_ALIASES = frozenset({ROLE_MENTOR, 'MENTOR'})

#: 视为"管理员"的角色码（不做范围收窄）
ADMIN_ROLE_CODES = frozenset({ROLE_SUPER_ADMIN, ROLE_ADMIN})


def user_role_codes(user) -> set[str]:
    """取用户的角色码集合（`user_roles` 表，system_code='recruit'）。

    ⚠️ 用 `values_list` 直取，**不做 ORM 关系名假设** —— `UserRoleV2` 的
    `related_name` 是 `user_roles_v2`，但历史上还有 V1 表遗留写法；
    直接查表最稳，也不会因为关系名变更而炸。
    """
    if user is None or not getattr(user, 'pk', None):
        return set()
    from apps.core.models_permission_v2 import UserRoleV2

    return set(
        UserRoleV2.objects.filter(user_id=user.pk, system_code='recruit')
        .values_list('role_code', flat=True)
    )


def is_admin(user) -> bool:
    """超管 / 管理员 —— 不做范围收窄。"""
    if user is None or not getattr(user, 'pk', None):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return bool(user_role_codes(user) & ADMIN_ROLE_CODES)


def visible_persons(user, queryset: QuerySet | None = None) -> QuerySet:
    """返回当前用户可见的校招生 queryset。

    Args:
        user: 当前登录用户（`request.user`）。
        queryset: 传入时在其基础上收窄（默认取全部未删除人员）。

    Returns:
        `campus_control.Person` 的 queryset（未做分页/序列化）。
    """
    from apps.campus_control.models import Person

    qs = queryset if queryset is not None else Person.objects.all()
    qs = qs.filter(deleted_at__isnull=True)

    if user is None or not getattr(user, 'pk', None):
        return qs.none()

    if getattr(user, 'is_superuser', False):
        return qs

    roles = user_role_codes(user)
    if roles & ADMIN_ROLE_CODES:
        return qs

    # 班主任：自己带的班
    if ROLE_HEAD_TEACHER in roles:
        return qs.filter(head_teacher_id=user.pk)

    # 导师：自己带教的人
    if roles & ROLE_MENTOR_ALIASES:
        return qs.filter(mentor_id=user.pk)

    # HRBP：本人归属 HRBP 或班级 HRBP
    if ROLE_HRBP in roles:
        return qs.filter(Q(hrbp_id=user.pk) | Q(class_room__hrbp_id=user.pk))

    # 校招生：仅本人（Person.user_id 存的是 core.User.id）
    if ROLE_STUDENT in roles:
        return qs.filter(user_id=user.pk)

    # 兜底：若该用户本身挂了校招生档案（Person.user_id），只给本人；
    # 否则给空集（**不泄露**）。
    own = qs.filter(user_id=user.pk)
    if own.exists():
        return own
    return qs.none()


def visible_person_ids(user) -> list[str]:
    """可见人员的 id 列表（供 in 过滤使用）。"""
    return list(visible_persons(user).values_list('id', flat=True))

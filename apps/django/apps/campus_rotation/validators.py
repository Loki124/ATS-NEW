"""campus_rotation 复用型校验工具。

集中放 BU 深度 / 身份角色 / 字典启用 / 上下级成环 等校验，供序列化器层调用。
所有函数对「字段未提供（None/空）」保持宽容（返回 True），由调用方决定是否必填。
"""
from django.db.models import Q
from rest_framework.exceptions import APIException

from apps.core.models import Department, User
from apps.core.models_permission_v2 import RoleV2, UserRoleV2
from apps.dictionary.models import DictionaryItem

# 导师名下 ONGOING 轮岗名额上限（方案 §3.2：上限来源 = 配置或约定常量）。
# 如后续需运营可调，可下沉到 CampusModuleConfig，但当前按约定常量落地。
MENTOR_ONGOING_CAPACITY = 20


class CapacityExceeded(APIException):
    """容量 / 名额饱和，返回 HTTP 409（方案 §3.2 契约）。

    在序列化器 validate() 中抛出：DRF 的 is_valid 仅捕获 ValidationError，
    本异常会冒泡到 DRF 异常处理器，返回标准 409（非 400 信封）。
    """

    status_code = 409
    default_detail = '容量或名额已饱和'
    default_code = 'capacity_exceeded'


def is_bu_depth(dept):
    """BU = 二级部门：parent IS NOT NULL AND parent__parent IS NULL（根=0、事业群=1、BU=2）。"""
    return bool(dept and dept.parent_id is not None and dept.parent.parent_id is None)


def user_has_campus_role(user_id, role_code):
    """校验某 User 是否具备指定 campus 身份角色（RoleV2 须存在且启用，且已授予该用户）。"""
    if not user_id:
        return True
    if not RoleV2.objects.filter(
        role_code=role_code, system_code='recruit', status=1, is_system=1,
    ).exists():
        # 角色未播种：写操作不应因种子缺失而放行，视为不具备该身份
        return False
    return UserRoleV2.objects.filter(
        user_id=user_id, role_code=role_code, system_code='recruit',
    ).exists()


def dict_key_active(type_code, key):
    """校验字典 type_code 下 key 存在且 is_active。空 key 视为无需校验。"""
    if not key:
        return True
    return DictionaryItem.objects.filter(
        type__code=type_code, key=key, is_active=True,
    ).exists()


def resolve_intent_bu(value):
    """按 code 或 name 解析 intent_bu 指向的 Department；不存在返回 None。"""
    if not value:
        return None
    return Department.objects.filter(
        Q(code=value) | Q(name=value),
    ).first()


def is_subordinate_of(manager_id, user_id):
    """判断 user_id 是否为 manager_id 的下属（递归遍历 direct_manager 链）。

    用于「直属上级防成环」：若把 user_id 设为 manager_id 的直属上级会形成环，则拒绝。
    """
    if not manager_id or not user_id or manager_id == user_id:
        return False
    visited = set()
    stack = [manager_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        for sub_id in User.objects.filter(direct_manager_id=current).values_list('id', flat=True):
            if sub_id == user_id:
                return True
            stack.append(sub_id)
    return False

"""Field ACL Services (PRD v4 §4.4 G43 字段级 ACL)

T30.175 (V2 cutover follow-up):
- user.user_roles 反向关联不存在, 改用 UserRoleV2 直查.

2026-08-03 R2 (寇豆码):
- 修正 DEFAULT_SENSITIVE_FIELDS['candidate'] 的键名:
    'id_card' -> 'id_card_no' (Candidate 上的真实字段名, 见 candidate/models.py:53;
                 原来的 'id_card' 永远匹配不到序列化输出, 规则形同虚设。
                 'id_card' 作为历史别名保留, 因为部分导入/外部对接 payload 用的是它)
    删除 'current_salary' (Candidate 上根本没有这个字段, 纯装饰)
- _mask_value 改为复用 apps/common/masking.py 的统一实现, 避免同一字段
  在不同入口脱敏格式不一致。
- apply_acl 本身此前**零业务调用** —— 服务写好了但没人用, 候选人列表/详情
  依然直吐明文 phone / email / id_card_no。现已通过
  apps/field_acl/mixins.py:FieldAclSerializerMixin 接到 Candidate 序列化器上。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from django.core.cache import cache

from apps.common.masking import (
    mask_amount,
    mask_email,
    mask_generic,
    mask_id_card,
    mask_phone,
)
from apps.core.models import User
from apps.core.role_v2_query import user_role_codes, is_super_admin

from apps.data_permission.enforcement import DataPermissionEnforcement

from .models import FieldACL, FieldPermission

logger = logging.getLogger(__name__)

#: FieldACL 规则缓存 TTL(秒). 规则是低频配置, 但列表接口每行都要用,
#: 不缓存会在 N 行列表上打 N 次 DB。
_RULES_CACHE_TTL = 60


class FieldAclService:
    """字段级 ACL 业务服务"""

    # 内置敏感字段清单（默认 MASK 规则）
    # R2: 键名必须和序列化器输出的字段名完全一致, 否则规则永远命中不到。
    DEFAULT_SENSITIVE_FIELDS = {
        # 'id_card' 是历史别名, 'id_card_no' 才是 Candidate 的真实字段名。
        # candidate_phone / candidate_email 是关联序列化器 (如 TalentPoolEntry)
        # 上的扁平化字段名, 同样要覆盖, 否则换个 API 就能拿到明文。
        'candidate': [
            'phone', 'email', 'id_card', 'id_card_no',
            'candidate_phone', 'candidate_email',
        ],
        'offer': ['salary', 'bonus'],
        'application': [],
    }

    @staticmethod
    def get_rules_map(entity: str) -> Dict:
        """取某实体的 (field, role_code) -> permission 映射, 带 60s 缓存."""
        cache_key = f'field_acl:rules:{entity}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        rules_map = {
            (r.field, r.role_code): r.permission
            for r in FieldACL.objects.filter(entity=entity)
        }
        cache.set(cache_key, rules_map, _RULES_CACHE_TTL)
        return rules_map

    @staticmethod
    def invalidate_rules_cache(entity: str = None) -> None:
        """规则变更后清缓存 (entity 为空时按已知实体全清)."""
        entities = [entity] if entity else list(FieldAclService.DEFAULT_SENSITIVE_FIELDS.keys())
        for ent in entities:
            cache.delete(f'field_acl:rules:{ent}')

    @staticmethod
    def apply_acl(entity: str, data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """根据用户角色对字段数据应用 ACL

        Args:
            entity: 实体名, 与 FieldACL.entity / DEFAULT_SENSITIVE_FIELDS 的 key 一致
            data:   序列化后的一行数据 (dict)
            user:   当前请求用户; 匿名用户按最严格处理

        Returns:
            脱敏后的新 dict (不修改入参)
        """
        if not isinstance(data, dict):
            return data

        # R2: 匿名用户原来是直接 `return data` —— 等于未登录反而能看全明文。
        # 现在按"无任何角色"处理, 走默认敏感字段 MASK。
        is_anonymous = user is None or not getattr(user, 'is_authenticated', False)
        if is_anonymous:
            user_roles: List[str] = []
        else:
            if is_super_admin(user):
                return data  # 超管或 SUPER_ADMIN 角色看所有
            user_roles = user_role_codes(user)

        rules_map = FieldAclService.get_rules_map(entity)

        masked = dict(data)
        for field, value in list(data.items()):
            perm = FieldAclService._get_field_permission(
                entity, field, user_roles, rules_map,
            )
            # 叠加 DataPermissionRule 列级规则 (按 ROLE/DEPARTMENT/USER 维度), 取最严格
            dp_perm = DataPermissionEnforcement.column_permission_for(user, entity, field)
            if dp_perm is not None:
                perm = DataPermissionEnforcement.most_restrictive(perm, dp_perm)
            if perm == FieldPermission.NONE:
                # 完全不可见 - 移除字段
                masked.pop(field, None)
            elif perm == FieldPermission.MASK:
                # 脱敏
                masked[field] = FieldAclService._mask_value(field, value)
            # READ - 保持原值

        return masked

    @staticmethod
    def _get_field_permission(
        entity: str,
        field: str,
        user_roles: List[str],
        rules_map: Dict,
    ) -> str:
        """获取字段权限（按角色最严格）"""
        perms = []
        for role in user_roles:
            key = (field, role)
            if key in rules_map:
                perms.append(rules_map[key])

        if not perms:
            # 无规则 - 检查默认敏感字段
            default_sensitive = FieldAclService.DEFAULT_SENSITIVE_FIELDS.get(entity, [])
            if field in default_sensitive:
                return FieldPermission.MASK
            return FieldPermission.READ

        # 取最严格：NONE > MASK > READ
        if FieldPermission.NONE in perms:
            return FieldPermission.NONE
        if FieldPermission.MASK in perms:
            return FieldPermission.MASK
        return FieldPermission.READ

    #: 字段名 -> 脱敏函数. R2: 统一走 apps/common/masking.py, 不再各写各的。
    _MASKERS = {
        'phone': mask_phone,
        'mobile': mask_phone,
        'contact_phone': mask_phone,
        'candidate_phone': mask_phone,
        'email': mask_email,
        'candidate_email': mask_email,
        'id_card': mask_id_card,
        'id_card_no': mask_id_card,
        'salary': mask_amount,
        'bonus': mask_amount,
        'current_salary': mask_amount,
        'expected_salary': mask_amount,
    }

    @staticmethod
    def _mask_value(field: str, value: Any) -> Any:
        """脱敏字段值 (按字段名选脱敏策略, 未知字段走通用规则)."""
        if value is None or value == '':
            return value
        masker = FieldAclService._MASKERS.get(field, mask_generic)
        return masker(value)

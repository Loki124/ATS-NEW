"""Field ACL Services (PRD v4 §4.4 G43 字段级 ACL)"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from apps.core.models import User

from .models import FieldACL, FieldPermission

logger = logging.getLogger(__name__)


class FieldAclService:
    """字段级 ACL 业务服务"""

    # 内置敏感字段清单（默认 MASK 规则）
    DEFAULT_SENSITIVE_FIELDS = {
        'candidate': ['phone', 'email', 'id_card', 'current_salary'],
        'offer': ['salary', 'bonus'],
        'application': [],
    }

    @staticmethod
    def apply_acl(entity: str, data: Dict[str, Any], user: User) -> Dict[str, Any]:
        """根据用户角色对字段数据应用 ACL"""
        if not isinstance(data, dict):
            return data
        if user is None or not user.is_authenticated:
            return data

        user_roles = list(user.user_roles.values_list('role__code', flat=True))
        if 'SUPER_ADMIN' in user_roles or user.is_superuser:
            return data  # 超管看所有

        # 获取该实体的所有 ACL 规则
        rules = FieldACL.objects.filter(entity=entity)
        rules_map = {(r.field, r.role_code): r.permission for r in rules}

        masked = dict(data)
        for field, value in list(data.items()):
            perm = FieldAclService._get_field_permission(
                entity, field, user_roles, rules_map,
            )
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

    @staticmethod
    def _mask_value(field: str, value: Any) -> str:
        """脱敏字段值"""
        if value is None or value == '':
            return value
        s = str(value)
        if field in ('phone', 'mobile'):
            # 138****8000
            if len(s) >= 7:
                return s[:3] + '****' + s[-4:]
        if field == 'email':
            # a***@example.com
            if '@' in s:
                local, domain = s.split('@', 1)
                if len(local) > 1:
                    return local[0] + '***@' + domain
                return '***@' + domain
        if field == 'id_card':
            # 110***********1234
            if len(s) >= 8:
                return s[:3] + '*' * (len(s) - 7) + s[-4:]
        if field in ('salary', 'current_salary', 'bonus'):
            # 数字字段 - 显示为 "***"
            return '***'
        # 通用 - 前 1 + 中间 * + 后 1
        if len(s) > 4:
            return s[0] + '*' * (len(s) - 2) + s[-1]
        return '*' * len(s)

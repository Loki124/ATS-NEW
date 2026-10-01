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
from django.db import DatabaseError

import logging
from typing import Any, Dict, List

from django.conf import settings
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
    def apply_acl(entity: str, data: Dict[str, Any], user: User,
                  request: Any = None) -> Dict[str, Any]:
        """根据用户角色对字段数据应用 ACL

        Args:
            entity: 实体名, 与 FieldACL.entity / DEFAULT_SENSITIVE_FIELDS 的 key 一致
            data:   序列化后的一行数据 (dict)
            user:   当前请求用户; 匿名用户按最严格处理
            request: 可选, 传入则按 (request, entity) 去重写访问审计埋点

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
                # 超管或 SUPER_ADMIN 角色看所有 (审计仍记一笔, 合规溯源)
                if request is not None:
                    FieldAclService._record_access(
                        request, entity, user, user_role_codes(user), [], [])
                return data
            user_roles = user_role_codes(user)

        # 全局强制开关: 即便某角色规则放行 READ, 默认敏感字段也强制 MASK
        # (NONE 维持更严)。默认 False, 不改现有行为; 运维可在环境变量开启作纵深防御。
        global_enforce = getattr(settings, 'FIELD_ACL_GLOBAL_ENFORCE', False)
        default_sensitive = FieldAclService.DEFAULT_SENSITIVE_FIELDS.get(entity, [])
        rules_map = FieldAclService.get_rules_map(entity)

        masked_fields: List[str] = []
        hidden_fields: List[str] = []
        masked = dict(data)
        for field, value in list(data.items()):
            perm = FieldAclService._get_field_permission(
                entity, field, user_roles, rules_map,
            )
            # 叠加 DataPermissionRule 列级规则 (按 ROLE/DEPARTMENT/USER 维度), 取最严格
            dp_perm = DataPermissionEnforcement.column_permission_for(user, entity, field)
            if dp_perm is not None:
                perm = DataPermissionEnforcement.most_restrictive(perm, dp_perm)
            # 全局强制: 敏感字段即便被角色放行也脱敏 (NONE 更严, 不动)
            if global_enforce and perm != FieldPermission.NONE and field in default_sensitive:
                perm = FieldPermission.MASK
            if perm == FieldPermission.NONE:
                # 完全不可见 - 移除字段
                masked.pop(field, None)
                hidden_fields.append(field)
            elif perm == FieldPermission.MASK:
                # 脱敏
                masked[field] = FieldAclService._mask_value(field, value)
                masked_fields.append(field)
            # READ - 保持原值

        if request is not None:
            FieldAclService._record_access(
                request, entity, user, user_roles, masked_fields, hidden_fields)
        return masked

    @staticmethod
    def _record_access(request, entity: str, user, user_roles: List[str],
                       masked_fields: List[str], hidden_fields: List[str]) -> None:
        """访问审计埋点: 每个 (request, entity) 只写一条 (列表 N 行 -> 1 条)。

        失败静默忽略, 绝不影响业务接口。
        """
        try:
            audited = getattr(request, '_field_acl_audited', None)
            if audited is None:
                audited = set()
                request._field_acl_audited = audited
            if entity in audited:
                return
            audited.add(entity)

            from .models import FieldAclAccessLog
            uid = ''
            uname = ''
            if user is not None and getattr(user, 'is_authenticated', False):
                uid = str(getattr(user, 'id', '') or '')
                uname = getattr(user, 'username', '') or ''
            FieldAclAccessLog.objects.create(
                entity=entity,
                user_id=uid,
                username=uname,
                role_codes=list(user_roles),
                masked_fields=list(masked_fields),
                hidden_fields=list(hidden_fields),
                request_path=getattr(request, 'path', '') or '',
                client_ip=(getattr(request, 'META', {}) or {}).get('REMOTE_ADDR', '') or '',
            )
        except (DatabaseError, ValueError, TypeError):  # 字段级 ACL 审计写入失败不应阻断主路径 (审计是 best-effort)
            logger.exception(
                'Field ACL 访问审计写入失败 (已忽略): entity=%s user=%s', entity, uid)

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

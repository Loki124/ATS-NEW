"""Field ACL 序列化器接入层 (2026-08-03 R2 寇豆码)

背景 (docs/ARCHITECTURE_REVIEW_2026-08-03.md):
  apps/field_acl/services.py:FieldAclService.apply_acl() 写得很完整 —— 角色规则、
  最严格取值、默认敏感字段、脱敏格式全都有 —— 但**全项目零业务调用**。
  也就是说字段级 ACL 这个功能只存在于代码库里, 线上候选人列表和详情
  依旧直接吐明文 phone / email / id_card_no 给任意登录用户。

  项目里唯一真实生效的脱敏是 apps/application/serializers.py:92 的
  get_candidate_phone(), 只覆盖了「投递列表里的候选人手机号」一个点。

本模块把 apply_acl 挂到序列化器的 to_representation 上, 让 ACL 真正生效。

使用方式:
    class CandidateListSerializer(FieldAclSerializerMixin, ModelSerializer):
        acl_entity = 'candidate'

行为约定:
  - 只影响**输出** (to_representation), 不影响 create/update 的入参校验
  - superuser / SUPER_ADMIN 角色不脱敏
  - serializer 没有 request context 时 (内部服务调用、管理命令、导出任务)
    不脱敏 —— 这些场景没有"当前用户"概念, 脱敏了反而会把脏数据写回业务流程。
    需要脱敏的内部场景应显式传 context={'request': request}。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .services import FieldAclService

logger = logging.getLogger(__name__)


class FieldAclSerializerMixin:
    """给 DRF Serializer 接上字段级 ACL 脱敏.

    子类必须设置 ``acl_entity``, 取值需与 FieldACL.entity /
    FieldAclService.DEFAULT_SENSITIVE_FIELDS 的 key 一致 (如 'candidate')。
    """

    #: 对应 FieldACL.entity, 空字符串表示不启用 ACL
    acl_entity: str = ''
    #: True 时, 拿不到 request context 也 fail-closed 脱敏 (防未来 view 忘传 context 又漏明文)。
    #: False (默认) 保持原语义: 无 context = 内部调用, 不做脱敏 (导出/同步等场景需要明文)。
    acl_strict: bool = False

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        data = super().to_representation(instance)
        entity = getattr(self, 'acl_entity', '')
        if not entity or not isinstance(data, dict):
            return data

        request = self.context.get('request') if hasattr(self, 'context') else None
        if request is None:
            # 无请求上下文: 若 acl_strict 则 fail-closed (宁可多脱敏也不泄漏),
            # 防止未来有 view 实例化序列化器忘传 context 又漏一次明文 (见 BUG-2 / QA 严过关)。
            # 内部导出/同步等确需明文输出的场景请显式设 acl_strict = False (或传 context)。
            if self.acl_strict:
                return self._apply_default_mask(entity, data)
            return data

        user = getattr(request, 'user', None)
        try:
            return FieldAclService.apply_acl(entity, data, user)
        except Exception:  # noqa: BLE001 — ACL 出错绝不能让业务接口 500
            logger.exception(
                'Field ACL 应用失败, 已降级为「全部脱敏」: entity=%s user=%s',
                entity,
                getattr(user, 'id', 'anon'),
            )
            # 降级策略: 宁可多脱敏也不泄漏 —— 把默认敏感字段全部打掉
            return self._apply_default_mask(entity, data)

    @staticmethod
    def _apply_default_mask(entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """fail-closed 兜底: 把默认敏感字段全部脱敏 (同错误降级策略)。"""
        fallback = dict(data)
        for field in FieldAclService.DEFAULT_SENSITIVE_FIELDS.get(entity, []):
            if field in fallback:
                fallback[field] = FieldAclService._mask_value(field, fallback[field])
        return fallback

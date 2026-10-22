"""统一审计埋点助手（需求 5-6「所有操作记录日志，便于追溯」）。

设计原则：
- 封装 AuditService.record，自动从 request 抽取 ip / user_agent / request_id；
- **降级不阻断主流程（fail-open）**：审计写入任何异常都只记 warning，绝不抛给业务，
  避免「审计挂了导致校招写操作全 500」。
- 写入口只需一行 `log_action(request, 'create', entity, instance.pk)` 即可。
"""
from __future__ import annotations

import logging

from apps.audit.services import AuditService

logger = logging.getLogger(__name__)


def _request_meta(request):
    """从 DRF request 抽取审计所需的网络上下文。"""
    if not request:
        return '', '', ''
    meta = getattr(request, 'META', {}) or {}
    ip = meta.get('REMOTE_ADDR', '') or ''
    ua = meta.get('HTTP_USER_AGENT', '') or ''
    rid = getattr(request, 'id', None) or ''
    return ip, ua, str(rid) if rid else ''


def log_action(
    request,
    action: str,
    entity: str,
    entity_id: str = '',
    field: str = '',
    old_value: str = '',
    new_value: str = '',
) -> None:
    """记录一条审计日志；失败降级为 warning，不阻断业务。

    Args:
        request: DRF request（用于取 user / ip / ua / request_id）；可传 None。
        action: 操作类型，建议取值 create / update / delete / restore /
                batch_assign / approve / confirm 等可读动词。
        entity: 业务实体标识（建议用模型 __name__ 或 ENTITY_SCOPE key）。
        entity_id: 主记录 id（批量操作可为汇总描述，如 "ids=1,2,3"）。
        field / old_value / new_value: 字段级变更明细（可选）。
    """
    try:
        user = getattr(request, 'user', None)
        ip, ua, rid = _request_meta(request)
        AuditService.record(
            user=user,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id != '' else '',
            field=field or '',
            old_value=str(old_value) if old_value else '',
            new_value=str(new_value) if new_value else '',
            ip=ip,
            user_agent=ua,
            request_id=rid,
        )
    except Exception as e:  # noqa: BLE001 — 审计失败不得阻断业务主路径
        logger.warning('审计埋点失败(已降级不阻断): entity=%s action=%s err=%s', entity, action, e)

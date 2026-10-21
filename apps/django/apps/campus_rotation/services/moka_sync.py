"""摩卡兼岗同步服务（需求 5-2 / S5-26）。

本期定位：**契约 + 桩实现**。真实摩卡 HTTP 调用待企业 API 授权后补齐，
届时只需替换 `_push_to_moka` 的实现体，调用方（视图 `sync` 动作 / 入职钩子 /
Celery 重试任务）无需改动。

契约（规格 §6.2 原文口径）::

    输入：person 工号/姓名、arrangement 轮岗部门/导师/直属上级、生效期
    输出：摩卡兼岗记录 ID → 写回 sync_request_id，status='SYNCED'
    失败：写 sync_error，status='FAILED'，不阻塞主流程（异步重试）

🔴 关键约束（**不阻塞主流程**）：
    `sync_concurrent_post` 内部捕获一切异常并落 `sync_status='FAILED'` +
    `sync_error`，**绝不向上抛异常**。兼岗记录是旁路数据，同步失败不应
    阻断轮岗安排本身的业务流。调用方只依据返回值（bool）决定是否排重试。

同步状态机::

    PENDING ──(推送成功)──→ SYNCED     写 sync_request_id + synced_at
       │
       └──(推送失败/未启用)──→ FAILED    写 sync_error（可重试）
                                │
                                └──(数据不完整无法同步)──→ SKIPPED

🔴 桩实现语义：本期不发起真实 HTTP 推送，统一走 SKIPPED（数据不具备同步条件）
或保持 PENDING 待真实通道就绪后重投。**严禁**在本期伪造 SYNCED 状态 ——
那会让台账上的「已同步」与摩卡侧实际状态永久性漂移，且无从校正。
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


class MokaSyncDisabled(Exception):
    """摩卡同步通道未启用（企业 API 未授权 / 配置缺失）。

    供 `_push_to_moka` 内部抛出，被 `sync_concurrent_post` 捕获后落 SKIPPED。
    """


def _build_payload(record) -> dict:
    """组装摩卡兼岗同步的请求载荷（契约输入部分）。

    从 record 及其关联的 person / arrangement 派生。字段名待企业 API 授权后
    与摩卡侧对齐，当前仅固化本域语义，不臆造对方字段名。
    """
    person = record.person
    arrangement = record.arrangement
    return {
        'person': {
            'id': str(person.id) if person else None,
            'employeeNo': getattr(person, 'employee_no', '') if person else '',
            'name': getattr(person, 'name', '') if person else '',
        },
        'arrangement': {
            'id': str(arrangement.id) if arrangement else None,
            'currentDept': getattr(arrangement, 'current_dept', None),
            'mentor': getattr(arrangement, 'mentor', None),
            'directManager': getattr(arrangement, 'direct_manager', None),
        },
        'post': {
            'postType': record.post_type,
            'effectiveFrom': (
                record.effective_from.isoformat() if record.effective_from else None
            ),
            'effectiveTo': (
                record.effective_to.isoformat() if record.effective_to else None
            ),
        },
    }


def _push_to_moka(payload: dict) -> str:
    """真实推送通道（待企业 API 授权后实现）。

    返回：摩卡兼岗记录 ID（写入 sync_request_id）。

    🔴 本期未接入真实通道 —— 主动抛 MokaSyncDisabled 而非静默返回假 ID，
    杜绝「假绿」：宁可状态是 SKIPPED/PENDING，也不伪造 SYNCED。
    """
    raise MokaSyncDisabled(
        '摩卡企业 API 未授权，真实推送通道待实现（本期为契约 + 桩）'
    )


def sync_concurrent_post(record) -> bool:
    """同步单条兼岗记录到摩卡。

    返回 True = 同步成功（status='SYNCED'）；False = 未成功
    （status='FAILED' 或 'SKIPPED'）。

    🔴 本函数**不抛异常**：所有失败路径都落库后返回 False，调用方据此排异步重试。
    """
    # 1) 数据完整性检查：缺人缺生效期无法同步 → SKIPPED
    if record.person_id is None or not record.effective_from:
        record.sync_status = 'SKIPPED'
        record.sync_error = '数据不完整：缺少人员或生效起，无法同步'
        record.save(update_fields=['sync_status', 'sync_error', 'updated_at'])
        logger.warning('兼岗同步跳过 id=%s：%s', record.id, record.sync_error)
        return False

    # 2) 组装载荷并推送
    try:
        payload = _build_payload(record)
        moka_record_id = _push_to_moka(payload)
    except MokaSyncDisabled as exc:
        # 通道未启用 → 保持 PENDING（待通道就绪后重投），不标 FAILED
        record.sync_status = 'PENDING'
        record.sync_error = str(exc)
        record.save(update_fields=['sync_status', 'sync_error', 'updated_at'])
        logger.info('兼岗同步未发送（通道未启用）id=%s', record.id)
        return False
    except Exception as exc:  # noqa: BLE001 —— 契约要求失败不阻塞主流程
        record.sync_status = 'FAILED'
        record.sync_error = f'{type(exc).__name__}: {exc}'[:2000]
        record.save(update_fields=['sync_status', 'sync_error', 'updated_at'])
        logger.exception('兼岗同步失败 id=%s', record.id)
        return False

    # 3) 成功：回写摩卡记录 ID + 同步时间
    record.sync_status = 'SYNCED'
    record.sync_request_id = str(moka_record_id)[:64]
    record.sync_error = ''
    record.synced_at = timezone.now()
    record.save(update_fields=[
        'sync_status', 'sync_request_id', 'sync_error', 'synced_at', 'updated_at',
    ])
    return True

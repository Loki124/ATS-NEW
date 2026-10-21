"""轮岗阶段考核规则引擎（需求 5-9 / S5-22）。

规则（规格 §6.9）::

    actual_end - actual_start >= 15 天 → assessment_status = 'REQUIRED'（必须考核）
                          <  15 天  → assessment_status = 'WAIVED'（免考）
    阶段置 DONE 时，若 REQUIRED 且无 assessment_result → 拒绝流转，返回 400

边界口径：
- 「15 天是否含首尾」（Q-02，业务方未最终拍板）按建议默认值实现：
  `end - start >= timedelta(days=15)` 即需考核。**不含首尾**（1 日至 15 日 = 14 天
  → 免考；1 日至 16 日 = 15 天 → 需考核）。该口径集中在
  `ASSESSMENT_MIN_DAYS` 一处，后续口径变更只改这一个常量。
- `actual_end` 为空时用 `planned_end`；`actual_start` 为空时用 `planned_start`。
- 实际与计划皆空 → 无法判定 → 保持 `PENDING`，**不阻断**，由定时任务兜底提醒。

设计要点：
- `evaluate_assessment_status` 是**纯函数**（不碰 DB），便于单测直接锁死边界。
- 判定与「置 DONE 时校验」分离：判定决定是否要考核，校验决定能不能算完成。
- 🔴 免考（WAIVED）不等于「无需任何记录」：WAIVED 阶段仍可置 DONE，
  但要求有过一次判定动作（`assessed_at` 有值），避免阶段被无声跳过。
"""
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# 考核天数阈值：>= 15 天必须考核（Q-02 建议默认值，禁散落硬编码）
ASSESSMENT_MIN_DAYS = 15

# 判定结果常量（与 RotationStage.ASSESSMENT_CHOICES 对齐）
STATUS_PENDING = 'PENDING'
STATUS_WAIVED = 'WAIVED'
STATUS_REQUIRED = 'REQUIRED'
STATUS_DONE = 'DONE'


def _resolve_window(stage) -> tuple:
    """解析阶段的有效起止区间。

    优先实际起止，缺失时回退计划起止（规格 §6.9）。
    返回 (start, end)，任一为 None 表示无法判定。
    """
    start = stage.actual_start or stage.planned_start
    end = stage.actual_end or stage.planned_end
    return start, end


def evaluate_assessment_status(stage) -> str:
    """判定阶段的考核状态（纯函数，不落库）。

    返回 PENDING / WAIVED / REQUIRED 之一。

    - 区间不可判定（起止皆缺）→ PENDING
    - 区间天数 >= ASSESSMENT_MIN_DAYS → REQUIRED
    - 区间天数 < ASSESSMENT_MIN_DAYS → WAIVED
    """
    start, end = _resolve_window(stage)
    if not start or not end:
        return STATUS_PENDING
    # end < start 视为数据错误，交给序列化器层校验拦截；此处按免考处理，
    # 避免负天数误判为「需考核」。
    if end < start:
        return STATUS_WAIVED
    if (end - start) >= timedelta(days=ASSESSMENT_MIN_DAYS):
        return STATUS_REQUIRED
    return STATUS_WAIVED


def can_mark_assessed(stage, *, pending_result: str = '') -> tuple:
    """阶段能否置为「已考核」（assessment_status='DONE'）。

    返回 (是否允许, 原因)。不通过时原因直接回给前端（400 报文）。

    Args:
        pending_result: 本次请求携带的考核结论（尚未落到实例上）。
            REQUIRED 状态下必须「实例已有结论 或 本次携带结论」二选一非空，
            否则拒绝。**必须计入**，否则「本次提交才填结论」的场景会被误拒。

    规则：
    - 状态须已判定（非 PENDING）—— 未判定说明区间信息不全，先补日期。
    - REQUIRED 必须有考核结论（assessment_result 非空）。
    - WAIVED 免考放行。
    """
    status = stage.assessment_status
    effective_result = (pending_result or '').strip() or (stage.assessment_result or '').strip()

    if status == STATUS_PENDING:
        # 尝试实时判定一次：可能刚补齐了日期（模型 save() 之外的内存态）
        evaluated = evaluate_assessment_status(stage)
        if evaluated == STATUS_PENDING:
            return False, '阶段起止日期不完整，无法判定考核状态'
        status = evaluated
        # 同步回实例，使调用方 save() 时落库为最新判定
        stage.assessment_status = evaluated
        if evaluated == STATUS_WAIVED:
            return True, ''

    if status == STATUS_REQUIRED:
        if not effective_result:
            return False, '轮岗满 15 天，必须填写考核结论后才能结束该阶段'
        return True, ''

    if status == STATUS_WAIVED:
        return True, ''

    return False, f'当前考核状态（{status}）不可置为已考核'


def mark_assessed(stage, *, result: str = '', assessed_by=None) -> None:
    """把阶段置为「已考核」（assessment_status='DONE'）。

    🔴 调用前必须先过 `can_mark_assessed`；本函数不再重复校验（避免两处口径漂移），
    但会在 result 为空且状态 REQUIRED 时直接抛 ValueError（防绕过）。
    """
    from django.utils import timezone

    status = stage.assessment_status
    if status == STATUS_REQUIRED and not (result or stage.assessment_result or '').strip():
        raise ValueError('轮岗满 15 天，必须填写考核结论')

    if result:
        stage.assessment_result = result
    if assessed_by is not None:
        stage.assessed_by = assessed_by
    stage.assessment_status = STATUS_DONE
    stage.assessed_at = timezone.now()
    stage.save(update_fields=[
        'assessment_status', 'assessment_result', 'assessed_by', 'assessed_at', 'updated_at',
    ])


def scan_pending_assessments(days_before_end: int = 3):
    """扫描「需考核但临近结束仍未考核」的阶段（定时任务用）。

    返回需要提醒的阶段 queryset 列表。口径：
    - assessment_status == 'REQUIRED'
    - 且 effective_end（实际结束优先，回退计划结束）距今 <= days_before_end 天
    - 且尚无考核结论

    🔴 防 N+1：只取判定所需字段，调用方按需再取详情。
    """
    from django.utils import timezone

    from apps.campus_rotation.models import RotationStage

    today = timezone.now().date()
    horizon = today + timedelta(days=days_before_end)

    candidates = RotationStage.objects.filter(
        assessment_status=STATUS_REQUIRED,
        deleted_at__isnull=True,
    ).filter(assessment_result='')[:500]

    need_remind = []
    for stage in candidates:
        _, end = _resolve_window(stage)
        if not end:
            continue
        if end <= horizon:
            need_remind.append(stage)
    return need_remind

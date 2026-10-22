"""GDPR 候选人 PII 清理 (整改卡 C3, 2026-10-21)

**口径 (兵哥 2026-10-21 拍板, 4 题全选推荐项)**:

1. **动态字段值** → 按 field_key / field_type 白名单只清个人敏感项 (身份证/手机/邮箱/住址),
   其余 (学历/期望薪资/意向城市/技能等) 保留为业务事实;
2. **简历正文** → `scraped_resumes.raw_content` 与 `candidates.resume_text` **整段清空**,
   `parsed_content` **保留结构化字段** (学历/技能/工作经历), 但其中的姓名/电话/邮箱等
   PII 键与值要清;
3. **面评/推荐理由/备注类文本** → **保留业务事实**, 但正则脱敏其中的手机号/邮箱/身份证;
4. **C4** (phone/email 落库加密) → 等 C3 落地后另开独立 PR。

**关键设计**:
- `PROTECT` 外键**不改** (改 CASCADE 会误删业务数据) —— 只清 PII 字段, 业务事实行保留;
- **软删行也要清** —— 软删行同样持有 PII, 用未过滤 manager 扫全表;
- 清理走 `apps.common.pii` 的白名单原语, 不做「字段名含 phone 就算 PII」的模糊猜测;
- 每次清理都返回**结构化报告**, 供审计与批量回填统计。
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.candidate.audit import compute_row_hash
from apps.candidate.models import (
    Candidate,
    CandidateFieldValue,
    CandidateForward,
    CandidateHistory,
    CandidatePositionRecommendation,
    CandidateScreening,
)
from apps.common.pii import (
    PII_FIELD_TYPES,
    is_sensitive_field_key,
    redact_field_value,
    scrub_json,
    scrub_text,
)
from apps.offer.models import Offer
from apps.process.models import CandidateRecommendation
from apps.reason_library.models import CandidateReasonRecord
from apps.referral.models import Referral
from apps.scraped_resume.models import ScrapedResume

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# 表级清理规格
# ══════════════════════════════════════════════════════════════════

#: 自由文本字段 → 只脱敏 (决策 3: 保留业务事实, 脱敏其中的联系方式)
TEXT_SCRUB_SPECS: tuple[tuple[Any, str], ...] = (
    (CandidateScreening, 'comment'),
    (CandidateForward, 'note'),
    (CandidatePositionRecommendation, 'reason'),
    (CandidateRecommendation, 'reason'),
    (CandidateReasonRecord, 'note'),
    (Referral, 'note'),
    (Offer, 'rejection_reason'),
)

#: JSON 字段 → 递归脱敏 (结构保留, 字符串值掩码)
JSON_SCRUB_SPECS: tuple[tuple[Any, str], ...] = (
    (Referral, 'detection_detail'),
    (CandidateReasonRecord, 'custom_reasons'),
)

#: `scraped_resumes.parsed_content` 里属 PII 的键 (解析结果结构: 姓名/电话/邮箱/工作经历…)
PARSED_CONTENT_PII_KEYS: frozenset[str] = frozenset({
    'name', 'fullname', 'full_name', 'realname', 'real_name',
    'phone', 'mobile', 'tel', 'telephone', 'contact', 'contact_phone',
    'email', 'mail', 'email_address',
    'idcard', 'id_card', 'idcardno', 'id_card_no', 'idnumber', 'id_number',
    'wechat', 'weixin', 'qq',
    'address', 'home_address', 'residence_address', 'location',
})


def _unfiltered(model):
    """取**未过滤 deleted_at** 的 manager —— 软删行同样持有 PII, 必须一并清理。

    优先用显式声明的 `all_objects`; 没有则用 `_base_manager` (Django 的无过滤兜底 manager,
    本仓未设置 `base_manager_name`, 故它就是普通 Manager)。
    """
    manager = getattr(model, 'all_objects', None)
    if manager is not None:
        return manager
    return model._base_manager


def _drop_pii_keys(value: Any, pii_keys: frozenset[str]) -> Any:
    """递归删除 JSON 结构里命中白名单的键 (值整体丢掉, 不留掩码残影)。"""
    if isinstance(value, dict):
        return {
            k: (_drop_pii_keys(v, pii_keys) if str(k).lower() not in pii_keys else None)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_drop_pii_keys(v, pii_keys) for v in value]
    return value


# ══════════════════════════════════════════════════════════════════
# 各表清理
# ══════════════════════════════════════════════════════════════════

def _purge_candidate_field_values(candidate: Candidate) -> dict:
    """`candidate_field_values`: 白名单 key → 清空 value; 其余 → 值内文本脱敏。

    这张表的 field_key 由客户端自由提交 (`PUT /candidates/{id}/field-values/`),
    **无字段定义可 join**, 故只能按 key 白名单判定 —— 与兵哥拍板的「field_key 白名单」一致。
    """
    cleared = scrubbed = 0
    for fv in _unfiltered(CandidateFieldValue).filter(candidate_id=candidate.id):
        original = fv.value
        if is_sensitive_field_key(fv.field_key):
            new_value = None
        else:
            new_value = scrub_json(original)
        if new_value == original:
            continue
        fv.value = new_value
        fv.save(update_fields=['value', 'updated_at'])
        if is_sensitive_field_key(fv.field_key):
            cleared += 1
        else:
            scrubbed += 1
    return {'cleared': cleared, 'scrubbed': scrubbed}


def _purge_dynamic_field_values(candidate: Candidate) -> dict:
    """`dynamic_field_values` (resource='Candidate'): 按 field_type 白名单清。

    **注意**: 这张表用泛型 `(resource, entity_id)` 引用业务实体, **不是真 FK**,
    所以「持 candidate 外键的 17 张表」盘点**漏掉了它** —— 它同样是候选人 PII 的存放处。
    它的 field_key 与 `DynamicField.field_key` 对齐 → 可 join 取权威 field_type,
    比按 key 猜更可靠 (决策 1 的「白名单」在这里落地为类型白名单)。
    """
    from apps.dynamic_field.models import DynamicField, DynamicFieldValue

    definitions = {
        d.field_key: d
        for d in DynamicField.objects.filter(resource='Candidate')
    }
    cleared = scrubbed = 0
    rows = DynamicFieldValue.objects.filter(resource='Candidate', entity_id=candidate.id)
    for row in rows:
        definition = definitions.get(row.field_key)
        original = row.value
        if definition is None:
            # 字段定义已删 (软删) → 保守按 key 白名单判定
            if is_sensitive_field_key(row.field_key):
                new_value = None
            else:
                new_value = scrub_json(original)
        elif definition.field_type in PII_FIELD_TYPES:
            new_value = None
        elif definition.field_type == 'COMPOSITE':
            new_value = _purge_composite_value(definition, original)
        else:
            new_value = scrub_json(original)
        if new_value == original:
            continue
        row.value = new_value
        row.save(update_fields=['value', 'updated_at'])
        if new_value is None:
            cleared += 1
        else:
            scrubbed += 1
    return {'cleared': cleared, 'scrubbed': scrubbed}


def _purge_composite_value(definition, value: Any) -> Any:
    """组合字段: 只清其中 PII 类型的**子字段**, 其余子字段保留。"""
    if not isinstance(value, dict):
        return scrub_json(value)
    sub_fields = definition.sub_fields or []
    if not isinstance(sub_fields, list):
        return scrub_json(value)
    pii_sub_keys = {
        str(sub.get('key'))
        for sub in sub_fields
        if isinstance(sub, dict) and str(sub.get('type') or '') in PII_FIELD_TYPES
    }
    out = {}
    for k, v in value.items():
        if str(k) in pii_sub_keys:
            continue
        out[k] = scrub_json(v)
    return out


def _purge_scraped_resumes(candidate: Candidate) -> dict:
    """`scraped_resumes`: raw_content 整段清空; parsed_content 保留结构但清 PII 键/值。"""
    raw_cleared = parsed_scrubbed = 0
    for resume in _unfiltered(ScrapedResume).filter(candidate=candidate):
        changed = False
        if resume.raw_content:
            resume.raw_content = ''
            changed = True
            raw_cleared += 1
        if resume.parsed_content:
            new_parsed = scrub_json(
                _drop_pii_keys(resume.parsed_content, PARSED_CONTENT_PII_KEYS)
            )
            if new_parsed != resume.parsed_content:
                resume.parsed_content = new_parsed
                changed = True
                parsed_scrubbed += 1
        if resume.source_url:
            new_url = scrub_text(resume.source_url)
            if new_url != resume.source_url:
                resume.source_url = new_url
                changed = True
        if changed:
            resume.save(update_fields=['raw_content', 'parsed_content', 'source_url', 'updated_at'])
    return {'raw_cleared': raw_cleared, 'parsed_scrubbed': parsed_scrubbed}


def _purge_text_fields(candidate: Candidate) -> dict:
    """面评/推荐理由/备注类文本 → 保留业务事实, 脱敏其中的联系方式。"""
    report: dict[str, int] = {}
    for model, field_name in TEXT_SCRUB_SPECS:
        rows = _unfiltered(model).filter(candidate=candidate)
        touched = 0
        for row in rows:
            raw = getattr(row, field_name, '') or ''
            if not isinstance(raw, str) or not raw:
                continue
            new_value = scrub_text(raw)
            if new_value == raw:
                continue
            setattr(row, field_name, new_value)
            row.save(update_fields=[field_name])
            touched += 1
        if touched:
            report[f'{model.__name__}.{field_name}'] = touched
    return report


def _purge_json_fields(candidate: Candidate) -> dict:
    """JSON 字段 → 递归脱敏 (结构保留)。"""
    report: dict[str, int] = {}
    for model, field_name in JSON_SCRUB_SPECS:
        rows = _unfiltered(model).filter(candidate=candidate)
        touched = 0
        for row in rows:
            raw = getattr(row, field_name, None)
            if not raw:
                continue
            new_value = scrub_json(raw)
            if new_value == raw:
                continue
            setattr(row, field_name, new_value)
            row.save(update_fields=[field_name])
            touched += 1
        if touched:
            report[f'{model.__name__}.{field_name}'] = touched
    return report


def _purge_gdpr_requests(candidate: Candidate) -> dict:
    """`gdpr_requests.submitted_email` —— 候选人邮箱的副本, 已处理的请求一并清空。

    只清 **COMPLETED / REJECTED** 的请求: 待验证 (PENDING / AWAITING_VERIFICATION)
    的请求还要靠邮箱发验证码, 清了会把流程打断。
    """
    from apps.gdpr.models import GDPRRequest, GDPRRequestStatus

    rows = GDPRRequest.objects.filter(
        candidate=candidate,
        status__in=[GDPRRequestStatus.COMPLETED, GDPRRequestStatus.REJECTED],
    ).exclude(submitted_email='')
    count = rows.count()
    if count:
        rows.update(submitted_email='')
    return {'submitted_email_cleared': count}


def _scrub_history_detail(detail: Any) -> Any:
    """审计 detail 脱敏: 变更明细里的 PII 值掩码/隐去, 其余字符串值递归脱敏。"""
    if not isinstance(detail, dict):
        return scrub_json(detail)
    out = dict(detail)
    changes = out.get('changes')
    if isinstance(changes, list):
        new_changes = []
        for item in changes:
            if not isinstance(item, dict):
                new_changes.append(item)
                continue
            item = dict(item)
            field = item.get('field')
            item['old'] = redact_field_value(field, item.get('old'))
            item['new'] = redact_field_value(field, item.get('new'))
            new_changes.append(item)
        out['changes'] = new_changes
    if 'note' in out:
        out['note'] = scrub_text(out.get('note'))
    return scrub_json(out)


def _purge_history_chain(candidate: Candidate, processor=None) -> dict:
    """清理候选人操作历史里的 PII 副本, 并**重算整条哈希链**。

    为什么必须重算: `row_hash = sha256(candidate_id|seq|action|detail|created_by|prev_hash)`,
    `detail` 在哈希输入里 → 改 detail 必然让 row_hash 失配, 触发
    `GET /candidates/{id}/histories/verify` 的篡改检测 (apps/candidate/views.py:427)。
    改第 N 行 → 第 N 行 hash 变 → 第 N+1 行的 prev_hash 也得跟着变 → 必须整链重算。

    重算后链仍然自洽 (校验端点依旧 ok=True), 并在链尾追加一条 `GDPR_PII_PURGED` 标记行,
    让"这次清理发生过"本身留在链上 —— 被遗忘权要的是**不可见**, 不是无痕。
    """
    rows = list(
        _unfiltered(CandidateHistory).filter(candidate_id=candidate.id).order_by('seq')
    )
    if not rows:
        # 没有历史行 → 无 PII 可清, 但**仍要留痕**: "这次清理发生过"本身是审计事实
        _append_purge_marker(candidate, processor, rows_scanned=0, rows_changed=0)
        return {'rows_scanned': 0, 'rows_changed': 0, 'chain_recomputed': False}

    changed = 0
    prev = ''
    for row in rows:
        new_detail = _scrub_history_detail(row.detail)
        if new_detail != row.detail:
            changed += 1
        new_hash = compute_row_hash(
            candidate.id, row.seq, row.action, new_detail, row.created_by_id, prev,
        )
        # 用 queryset.update 绕过模型的「不可篡改」守卫 —— 该守卫是给业务层用的,
        # 这里是受控的合规清理 (链会重算, 校验端点仍能验证通过)。
        _unfiltered(CandidateHistory).filter(pk=row.pk).update(
            detail=new_detail, prev_hash=prev, row_hash=new_hash,
        )
        prev = new_hash

    # 链尾追加清理标记行 (save() 会自动接 seq/prev_hash/row_hash)
    _append_purge_marker(candidate, processor, rows_scanned=len(rows), rows_changed=changed)
    return {
        'rows_scanned': len(rows),
        'rows_changed': changed,
        'chain_recomputed': True,
    }


def _append_purge_marker(candidate: Candidate, processor, *, rows_scanned: int, rows_changed: int) -> None:
    """在操作历史链尾追加 GDPR_PII_PURGED 标记行 (save() 自动接 seq/prev_hash/row_hash)。"""
    CandidateHistory.objects.create(
        candidate=candidate,
        action='GDPR_PII_PURGED',
        detail={
            'source': 'gdpr_forget',
            'purged_rows': rows_changed,
            'total_rows': rows_scanned,
            'at': timezone.now().isoformat(),
        },
        created_by=processor if (processor and processor.is_authenticated) else None,
    )


# ══════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════

@transaction.atomic
def purge_candidate_pii(candidate: Candidate, *, processor=None, include_audit_chain: bool = True) -> dict:
    """清理一名候选人的 PII 副本, 返回结构化报告。

    Args:
        candidate: 候选人实例 (主表的 name/phone/email/id_card_no 与 3 个 hash 列
            已由 C2 在本函数之前清空)。
        processor: 处理人 (超管), 写进审计标记行。
        include_audit_chain: 是否清理操作历史链并重算哈希。关掉则跳过
            (运维可先用 `purge_candidate_pii` 命令的 `--skip-audit-chain` 观察)。

    Returns:
        报告 dict (各表清理条数), 供审计与批量统计。
    """
    report: dict[str, Any] = {'candidate_id': candidate.id}

    # ── 主表: 简历正文整段清空 (决策 2, 与 raw_content 同口径) ──
    if candidate.resume_text:
        candidate.resume_text = ''
        candidate.save(update_fields=['resume_text', 'updated_at'])
        report['resume_text_cleared'] = True
    else:
        report['resume_text_cleared'] = False

    report['candidate_field_values'] = _purge_candidate_field_values(candidate)
    report['dynamic_field_values'] = _purge_dynamic_field_values(candidate)
    report['scraped_resumes'] = _purge_scraped_resumes(candidate)
    report['text_fields'] = _purge_text_fields(candidate)
    report['json_fields'] = _purge_json_fields(candidate)
    report['gdpr_requests'] = _purge_gdpr_requests(candidate)
    if include_audit_chain:
        report['history'] = _purge_history_chain(candidate, processor=processor)

    logger.info(
        'GDPR PII purge done: candidate=%s report=%s',
        candidate.id, report,
    )
    return report

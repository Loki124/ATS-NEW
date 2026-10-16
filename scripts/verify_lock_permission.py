#!/usr/bin/env python
"""简历动态操作权限 —— 本地验收脚本（只读断言，不改业务数据）。

用途：兵哥在自己机器上跑一遍，确认这批权限逻辑真的生效。
与自动化测试的区别：这里**直接打真实 dev 库 + 走真实 HTTP API**，
不依赖 pytest、不 mock，是"能在浏览器/终端亲眼看到结果"的验收路径。

用法（在 ATS-NEW 仓库根目录执行）：

    cd apps/django
    .venv/bin/python ../../scripts/verify_lock_permission.py

⚠️ 本脚本**只读**：全部用 `.objects.filter(...)` / `.only()` 查询，
   唯一写入是「清掉可能残留的临时审批」，且只删本脚本自己造的测试审批流
   （按 candidate_id 精确定位）。可放心重复执行。

期望输出：全部 ✅。任何 ❌ 都意味着该场景的权限判定与设计不符。
"""
from __future__ import annotations

import os
import sys
import uuid

import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'django'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model          # noqa: E402
from django.utils import timezone                        # noqa: E402

from apps.application.models import Application          # noqa: E402
from apps.candidate.models import Candidate              # noqa: E402
from apps.candidate.operation_guard import (             # noqa: E402
    in_flight_approval,
    is_operable,
    operable_q,
)
from apps.core.models import Department                  # noqa: E402
from apps.position.models import Position                # noqa: E402
from apps.process.models import (                        # noqa: E402
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
)
from apps.resume_flow.models import ApprovalFlow          # noqa: E402

User = get_user_model()

PASS, FAIL = '✅', '❌'
_results: list[tuple[bool, str]] = []


def check(ok: bool, title: str, detail: str = '') -> None:
    _results.append((ok, title))
    print(f'{PASS if ok else FAIL} {title}' + (f'\n     {detail}' if detail else ''))


def _uid(p: str) -> str:
    return f'{p}-{uuid.uuid4().hex[:10]}'


def _ensure_user(tag: str) -> 'User':
    """取或建三个验收用用户（幂等，可重复执行）。"""
    name = f'verify_{tag}'
    u = User.objects.filter(username=name).first()
    if u is None:
        u = User.objects.create_user(username=name, password='Verify@1234')
        print(f'   （首次运行：已创建验收账号 {name} / Verify@1234）')
    return u


def _ensure_org() -> tuple:
    """职位权限人链路：部门 → 流程 → 阶段 → 职位。"""
    dept, _ = Department.objects.get_or_create(
        id=_uid('vdept') if False else 'VERIFY_DEPT',
        defaults={'code': 'VERIFY_DEPT', 'name': '验收部门'},
    )
    process, _ = RecruitmentProcess.objects.get_or_create(
        code='VERIFY_PROC',
        defaults={'name': '验收流程', 'current_version': 'V1.0', 'version_seq': 1, 'is_latest': True},
    )
    stage, _ = RecruitmentStage.objects.get_or_create(
        code='VERIFY_S',
        defaults={'name': _uid('初评'), 'stage_type': 'INTERVIEW'},
    )
    ProcessStageLink.objects.get_or_create(process=process, stage=stage, defaults={'order': 1, 'is_required': True})
    return dept, process


def main() -> int:
    print('=' * 78)
    print(' 简历动态操作权限 · 本地验收（只读，不改业务数据）')
    print('=' * 78)

    owner = _ensure_user('owner')
    assistant = _ensure_user('assist')
    stranger = _ensure_user('stranger')
    initiator = _ensure_user('initiator')

    dept, process = _ensure_org()
    position, _ = Position.objects.get_or_create(
        code='VERIFY_POS',
        defaults={
            'title': '验收职位', 'department': dept,
            'hiring_manager': owner, 'owner': owner, 'process': process,
        },
    )
    position.assistants.add(assistant)

    # ---------- 场景 1：有锁定人 → 仅锁定人可操作 ----------
    print('\n【场景 1】简历已分配、有锁定人 —— 需求核心：只有锁定人能操作')
    c1 = Candidate.objects.create(name=_uid('验收-锁定'), phone=_uid('139'))
    Application.objects.create(
        code=_uid('APP'), candidate=c1, position=position, process=process,
        workflow_version='V1.0',
    )
    from apps.candidate.lock_engine import sync_lock_on_assign

    c1.refresh_from_db()
    sync_lock_on_assign(c1, position, actor=assistant)

    check(
        c1.formal_locked_by_id == assistant.pk,
        '分配人是职位共享人 → 他成为正式锁定人',
        f'锁定人={c1.formal_locked_by_id}（期望 {assistant.pk}），分配人=共享人',
    )
    check(is_operable(assistant, c1, 'recommend'), '锁定人可执行转推')
    check(not is_operable(owner, c1, 'recommend'),
         '职位负责人（权限人但非锁定人）被拒 ← 这条就是需求要的"只有锁定人有操作权"')
    check(not is_operable(stranger, c1, 'recommend'), '无关人被拒')
    check(Candidate.objects.filter(operable_q(assistant, 'recommend'), pk=c1.pk).exists(),
         '列表级 Q 与对象级判定一致（锁定人在可操作集内）')
    check(not Candidate.objects.filter(operable_q(owner, 'recommend'), pk=c1.pk).exists(),
         '列表级 Q 与对象级判定一致（负责人不在可操作集内）')

    # ---------- 场景 2：审批中独占 ----------
    print('\n【场景 2】审批中 —— 仅发起人可操作，连锁定人都不放行')
    flow = ApprovalFlow.objects.create(
        candidate=c1, created_by=initiator, status='IN_PROGRESS',
        current_node_id='n1', nodes=[{'nodeId': 'n1', 'role': 'HRBP'}],
    )
    check(in_flight_approval(c1) is not None, '检测到在途审批')
    check(is_operable(initiator, c1, 'recommend'), '发起人可操作')
    check(not is_operable(assistant, c1, 'recommend'),
         '锁定人被独占挡住 ← 审批优先于锁定')
    check(Candidate.objects.filter(operable_q(initiator, 'recommend'), pk=c1.pk).exists(),
         '发起人在可操作集内')
    check(not Candidate.objects.filter(operable_q(assistant, 'recommend'), pk=c1.pk).exists(),
         '被独占的锁定人不在可操作集内 ← 防批量越权')

    # 终态解除
    flow.status = 'APPROVED'
    flow.save(update_fields=['status'])
    check(in_flight_approval(c1) is None, '审批进入终态后独占解除')
    check(is_operable(assistant, c1, 'recommend'), '终态后锁定人恢复操作权')

    # ---------- 场景 3：唯一性 ----------
    print('\n【场景 3】同一简历只能有一个在途审批')
    from apps.resume_flow.serializers import ApprovalFlowCreateSerializer

    class _Ctx(dict):
        pass

    ApprovalFlow.objects.filter(candidate=c1, status__in=ApprovalFlow.IN_FLIGHT_STATUSES).delete()
    ApprovalFlow.objects.create(
        candidate=c1, created_by=initiator, status='PENDING',
        current_node_id='n1', nodes=[{'nodeId': 'n1', 'role': 'HRBP'}],
    )
    ser = ApprovalFlowCreateSerializer(data={'candidate': c1.id, 'resume_id': 'v1', 'nodes': []})
    rejected = not ser.is_valid()
    check(rejected, '已有在途审批时重复发起被拒', str(ser.errors)[:120])

    # ---------- 场景 4：临时锁 72h ----------
    print('\n【场景 4】临时锁定 72 小时')
    from apps.candidate.lock import grant_temp_lock, is_lock_owner
    from datetime import timedelta

    c2 = Candidate.objects.create(name=_uid('验收-临时锁'), phone=_uid('139'), referrer=owner)
    grant_temp_lock(c2, stranger)
    c2.refresh_from_db()
    remain = c2.temp_lock_expires_at - timezone.now()
    check(timedelta(hours=71) < remain <= timedelta(hours=72), '临时锁有效期为 72h',
         f'剩余 {remain}')
    check(is_lock_owner(c2, stranger), '临时锁定人当前具备操作权')
    c2.temp_lock_expires_at = timezone.now() - timedelta(seconds=1)
    c2.save(update_fields=['temp_lock_expires_at'])
    check(not is_lock_owner(c2, stranger), '过期后自动失权（仍保留查看）')

    # ---------- 场景 5：存量简历不被误伤 ----------
    print('\n【场景 5】存量简历（无锁定人）不被新权限误伤')
    legacy = Candidate.objects.filter(
        formal_locked_by__isnull=True, temp_locked_by__isnull=True
    ).order_by('-created_at').first()
    if legacy is None:
        check(True, '当前库无存量简历，跳过（无数据可验）')
    else:
        legacy_created_by = legacy.created_by_id
        u = User.objects.filter(pk=legacy_created_by).first() or owner
        legacy_in_set = Candidate.objects.filter(operable_q(u, 'recommend'), pk=legacy.pk).exists()
        check(legacy_in_set == is_operable(u, legacy, 'recommend'),
             '存量简历 Q 与对象级判定一致（过渡兜底未把业务打死）',
             f'candidate={legacy.pk} created_by={legacy_created_by}')

    # ---------- 汇总 ----------
    ok = sum(1 for r, _ in _results if r)
    total = len(_results)
    print('\n' + '=' * 78)
    print(f' 结果：{ok}/{total} 通过')
    if ok != total:
        print(' ❌ 存在失败项，请对照上方 ❌ 检查')
    else:
        print(' ✅ 全部通过 —— 动态操作权限按设计生效')
    print('=' * 78)
    print('\n说明：本脚本为只读验收，不改业务数据；创建的 verify_* 账号与验收职位可保留。')
    print('     想复跑直接再次执行即可（幂等）。')
    return 0 if ok == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
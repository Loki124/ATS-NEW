"""import_campus_data 管理命令冒烟测试（§7）。

覆盖：
- 默认空数据 dry-run 干净退出、不落库；
- 含未匹配部门/人员的 dry-run 报告 unmatched_* 且不落库；
- apply 幂等：重复执行同一业务唯一键只产生一行（update_or_create）。
"""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.campus_rotation.models import (
    ClassRoom,
    LiveRoom,
    RotationArrangement,
)


@pytest.mark.django_db
def test_dry_run_empty_exits_zero_and_writes_nothing():
    """空数据 dry-run：不抛错，三张表行数保持 0。"""
    out = StringIO()
    call_command('import_campus_data', dry_run=True, stdout=out)

    assert 'DRY-RUN 完成' in out.getvalue()
    assert LiveRoom.objects.count() == 0
    assert ClassRoom.objects.count() == 0
    assert RotationArrangement.objects.count() == 0


@pytest.mark.django_db
def test_dry_run_reports_unmatched_and_writes_nothing(tmp_path):
    """含未匹配引用的 dry-run：报告 unmatched_depts / unmatched_users，且不落库。"""
    payload = {
        'live_rooms': [
            {'room_no': 'LR000001', 'name': 'x', 'department': '不存在的部门XYZ',
             'bu': '不存在的BU', 'mentor': {'employee_id': 'ghost_1'}},
        ],
        'class_rooms': [
            {'code': 'CL000001', 'name': 'x',
             'head_teacher': {'username': 'ghost_2'}},
        ],
        'rotation_arrangements': [
            {'person_id': 100001, 'stage': 'PENDING',
             'direct_manager': {'username': 'ghost_3'}},
        ],
    }
    src = tmp_path / 'data.json'
    src.write_text(json.dumps(payload), encoding='utf-8')

    out = StringIO()
    call_command('import_campus_data', dry_run=True, source=str(src), stdout=out)
    report = out.getvalue()

    assert 'unmatched_depts' in report
    assert 'unmatched_users' in report
    assert '不存在的部门XYZ' in report
    assert 'ghost_1' in report
    # 不落库
    assert LiveRoom.objects.count() == 0
    assert ClassRoom.objects.count() == 0
    assert RotationArrangement.objects.count() == 0


@pytest.mark.django_db
def test_apply_is_idempotent_by_business_key(tmp_path):
    """apply 幂等：同一 room_no 重复执行只产生一行（update_or_create）。"""
    payload = {
        'live_rooms': [
            {'room_no': 'LR000010', 'name': '幂等测试间', 'platform': 'TENCENT_MEETING'},
        ],
        'class_rooms': [],
        'rotation_arrangements': [],
    }
    src = tmp_path / 'data.json'
    src.write_text(json.dumps(payload), encoding='utf-8')

    def apply_once():
        out = StringIO()
        call_command('import_campus_data', source=str(src), stdout=out)
        return out.getvalue()

    apply_once()
    assert LiveRoom.objects.filter(room_no='LR000010').count() == 1

    # 第二次执行：默认值不变，应走 update 而非 create（apply 模式报告 created=0）
    report2 = apply_once()
    assert 'created=0' in report2
    assert LiveRoom.objects.filter(room_no='LR000010').count() == 1
    # 再次确认更新链路未新增行
    assert LiveRoom.objects.count() == 1

"""backfill_process_start_end 管理命令测试

验证:
- 缺起止 link 的存量流程经命令回填后拥有 初评(P001, is_start) + 正式录用(P099, is_end)
- 顺序归一化 (初评 order=0 最前, 正式录用 order 最大收尾)
- 幂等: 重跑不产生重复 link
- 已软删的旧 link 被复活而非新建 (绕开 (process, stage) 唯一约束)
"""
import pytest
from django.core.management import call_command

from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
)


@pytest.fixture
def proc(db):
    return RecruitmentProcess.objects.create(
        code='WBT001', name='回填测试流程', status='ENABLED',
        is_enabled=True, current_version='V1.0',
    )


@pytest.fixture
def biz_stage(db):
    return RecruitmentStage.objects.create(
        code='PTESTBIZ', name='业务阶段', stage_type='SCREEN',
    )


def test_backfill_creates_missing_start_end(proc, biz_stage):
    # 故意只挂业务阶段, 不挂起止
    ProcessStageLink.objects.create(process=proc, stage=biz_stage, order=0)

    call_command('backfill_process_start_end')

    links = list(ProcessStageLink.objects.filter(
        process=proc, deleted_at__isnull=True,
    ).select_related('stage').order_by('order'))
    by_code = {l.stage.code: l for l in links}

    assert 'P001' in by_code and by_code['P001'].stage.is_start
    assert 'P099' in by_code and by_code['P099'].stage.is_end
    assert by_code['P001'].is_mandatory and by_code['P099'].is_mandatory
    # 顺序: 初评最前, 正式录用最后
    assert links[0].stage.code == 'P001'
    assert links[-1].stage.code == 'P099'


def test_backfill_idempotent(proc, biz_stage):
    ProcessStageLink.objects.create(process=proc, stage=biz_stage, order=0)

    call_command('backfill_process_start_end')
    n1 = ProcessStageLink.objects.filter(
        process=proc, deleted_at__isnull=True,
    ).count()

    call_command('backfill_process_start_end')  # 重跑
    n2 = ProcessStageLink.objects.filter(
        process=proc, deleted_at__isnull=True,
    ).count()

    assert n1 == n2  # 不重复创建
    # 起止仍各一条
    assert ProcessStageLink.objects.filter(
        process=proc, stage__code='P001', deleted_at__isnull=True,
    ).count() == 1
    assert ProcessStageLink.objects.filter(
        process=proc, stage__code='P099', deleted_at__isnull=True,
    ).count() == 1


def test_backfill_revives_soft_deleted_link(proc, biz_stage):
    # 预置一个被软删的起止 link (占 (process, stage) 唯一槽)
    soft = ProcessStageLink.objects.create(
        process=proc, stage=RecruitmentStage.objects.get(code='P001'),
        order=0, is_mandatory=True,
    )
    from apps.process.models import ProcessStageLink as _L
    _L.objects.filter(id=soft.id).update(deleted_at='2026-09-20 00:00:00')

    call_command('backfill_process_start_end')

    revived = ProcessStageLink.objects.get(id=soft.id)
    assert revived.deleted_at is None  # 复活而非新建
    assert ProcessStageLink.objects.filter(
        process=proc, stage__code='P001',
    ).count() == 1  # 唯一约束未被打破

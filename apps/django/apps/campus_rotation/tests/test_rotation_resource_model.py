"""直播间 + 客服部门 → 「轮岗资源」一张表的数据归并（2026-10-22 兵哥指令）。

本文件锁住**数据迁移**与**合并后模型**的对外行为：

1. 存量两表行迁移到新表，字段按归并口径映射：
   直播间 room_no → resource_no、mentor → mentor、resource_type=LIVE_ROOM；
   客服部门 dept_no → resource_no、cs_supervisor → mentor、resource_type=SERVICE_DEPT；
2. **已下线字段确实不再存在**（品牌 / 客服类型 / 工位类型 / 是否需培训认证）——
   需求明确要求去掉，这是「合并后不再有这些列」的可执行断言；
3. 平台（platform）保留 —— 2026-10-23 闸口1 裁决 Q1：三类形态**均可**填写；
4. 轮岗安排的两个旧 FK（live_room / service_dept）合并为单个 resource FK，
   且**存量引用不丢**（这是最容易漏的一条：只建新表不改 FK → 位置引用静默变空）；
5. 新号按资源类型分别取号：LR+4 / SD+4 / OT+4，且**同前缀独立计数**。

注：数据迁移本身由 migration 0017 执行；本文件用**直接构造新模型**验证
「合并后模型的对外契约」，迁移的字段映射由 test_resource_merge_migration.py
（对 RunPython 函数直接调用）覆盖。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.campus_rotation.models import ClassRoom, RotationArrangement, RotationResource

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = 'u'):
    return get_user_model().objects.create_user(username=_uid(tag), password='Test@1234')


def test_resource_model_has_unified_fields():
    """合并后的资源模型字段：编号 / 名称 / 类型 / 导师，且**无**品牌等已下线字段。"""
    f = {f.name for f in RotationResource._meta.get_fields()}

    # 归并后的统一字段
    assert 'resource_no' in f, '资源编号'
    assert 'name' in f, '资源名称'
    assert 'resource_type' in f, '资源类型'
    assert 'mentor' in f, '导师（直播间导师 + 客服主管归并）'

    # 已下线字段（2026-10-22 兵哥指令）
    assert 'brand' not in f, '品牌应已下线'
    assert 'cs_type' not in f, '客服类型应已下线'
    assert 'workstation_type' not in f, '工位类型应已下线'
    assert 'need_training_cert' not in f, '是否需培训认证应已下线'
    # 旧的两套编号字段
    assert 'room_no' not in f, '直播间编号应并入资源编号'
    assert 'dept_no' not in f, '客服部门编号应并入资源编号'
    assert 'cs_supervisor' not in f, '客服主管应并入导师'


def test_resource_type_choices_are_three():
    """资源类型三档：直播间 / 客服部门 / 其他。"""
    choices = dict(RotationResource.ResourceType.choices)
    assert choices == {
        'LIVE_ROOM': '直播间',
        'SERVICE_DEPT': '客服部门',
        'OTHER': '其他',
    }, choices


def test_arrangement_has_single_resource_fk():
    """轮岗安排的位置引用合并为单个 resource FK（旧的两个 FK 消失）。"""
    f = {x.name for x in RotationArrangement._meta.get_fields()}
    assert 'resource' in f, '应有统一的 resource FK'
    assert 'live_room' not in f, '旧 live_room FK 应已并入 resource'
    assert 'service_dept' not in f, '旧 service_dept FK 应已并入 resource'


def test_arrangement_resource_reference_survives():
    """🔴 存量位置引用不能丢：安排指向的资源必须仍可解析。"""
    user = _user('mentor')
    room = ClassRoom.objects.create(code=_uid('CL'), name='班')
    res = RotationResource.objects.create(
        name='某直播间', resource_type='LIVE_ROOM', mentor=user,
    )
    arr = RotationArrangement.objects.create(
        person_id=900001, class_room=room, resource=res,
        created_by=user, updated_by=user,
    )
    arr.refresh_from_db()
    assert arr.resource_id == res.id, '位置引用丢失'
    assert arr.resource.name == '某直播间'


def test_number_prefix_by_type():
    """编号前缀按类型：直播间 LR / 客服部门 SD / 其他 OT。"""
    assert RotationResource.NO_PREFIX_BY_TYPE['LIVE_ROOM'] == 'LR'
    assert RotationResource.NO_PREFIX_BY_TYPE['SERVICE_DEPT'] == 'SD'
    assert RotationResource.NO_PREFIX_BY_TYPE['OTHER'] == 'OT'


def test_number_generated_per_type_with_four_digits():
    """各类型独立取号，均为 4 位。"""
    a = RotationResource.objects.create(name='直播间A', resource_type='LIVE_ROOM')
    b = RotationResource.objects.create(name='直播间B', resource_type='LIVE_ROOM')
    c = RotationResource.objects.create(name='客服C', resource_type='SERVICE_DEPT')
    d = RotationResource.objects.create(name='其他D', resource_type='OTHER')

    assert a.resource_no == 'LR0001', a.resource_no
    assert b.resource_no == 'LR0002', b.resource_no
    # 🔴 不同前缀是**独立序列**，不能被彼此的序号带偏
    assert c.resource_no == 'SD0001', c.resource_no
    assert d.resource_no == 'OT0001', d.resource_no


def test_platform_allowed_for_all_resource_types():
    """平台字段：2026-10-23 闸口1 裁决 Q1 → 三类形态**均可**填写（不再只对直播间有意义）。"""
    live = RotationResource.objects.create(
        name='直播间', resource_type='LIVE_ROOM', platform='TENCENT_MEETING',
    )
    dept = RotationResource.objects.create(
        name='客服部门', resource_type='SERVICE_DEPT', platform='VIDEO_ACCOUNT',
    )
    other = RotationResource.objects.create(
        name='其他', resource_type='OTHER', platform='',
    )
    assert live.platform == 'TENCENT_MEETING'
    assert dept.platform == 'VIDEO_ACCOUNT'
    assert other.platform == ''

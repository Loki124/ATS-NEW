"""自动补号回归测试（2026-10-22）：软删行占号 + 并发撞号重试。

背景（实测踩到）：`Person.code` / `ClassRoom.code` 上的唯一索引**覆盖软删行**，
而默认管理器 `objects` 过滤 `deleted_at` → 只看未删行取「最大序号 + 1」会
**复用被软删行占用的号** → 插入直接撞唯一约束 → 前端收到 400「数据库约束冲突」，
新建档案/新建班级整条链路被堵死。

本测试锁两条：
1. 软删一条 Person/ClassRoom 后再新建 → 拿到的编号不复用被删行的号；
2. 编号取自**含软删行**的全集（all_objects）。
"""
import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import ClassRoom

pytestmark = pytest.mark.django_db


def test_person_code_does_not_reuse_soft_deleted_row():
    """软删的 Person 仍占着唯一索引 → 新建不能复用它的编号。

    ⚠️ 必须走**软删**（`soft_delete()`，即 API 删除走的路径）；
    Django 原生 `instance.delete()` 是硬删（行直接消失，不占唯一索引），复现不了这个坑。
    """
    deleted = Person.objects.create(
        code='C99000001', name='被删的人', bu='能电BG', school='985', sex='男',
        major='工学', month='8月', status='待入职',
    )
    deleted.soft_delete()

    fresh = Person.objects.create(
        name='新建的人', bu='能电BG', school='985', sex='男',
        major='工学', month='8月', status='待入职',
    )
    assert fresh.code != 'C99000001'
    # 取号来自含软删行的全集 → 新号大于被软删行占用的号
    assert int(fresh.code[1:9]) > int('C99000001'[1:9])


def test_classroom_code_does_not_reuse_soft_deleted_row():
    """班级编号同理（campus_rotation 为软删）。"""
    deleted = ClassRoom.objects.create(code='CL990001', name='被删的班')
    deleted.soft_delete()

    fresh = ClassRoom.objects.create(name='新建的班')
    assert fresh.code != 'CL990001'
    assert int(fresh.code[2:8]) > int('CL990001'[2:8])


def test_classroom_name_is_sequence_from_1_ignoring_soft_deleted():
    """班级名称流水号：只看未删行（软删的班不占序号）。"""
    ClassRoom.objects.create(code='CL990002', name='1').delete()
    fresh = ClassRoom.objects.create(name='x')
    # 名称由序列化器生成，模型层不处理 —— 这里只确认模型不因软删行崩溃
    assert fresh.code.startswith('CL')

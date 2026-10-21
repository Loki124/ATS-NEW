"""S5-09 回归：班级名 `name` 唯一约束必须被数据库层强制。

Q-06 盘点结论（2026-10-21，dev 库 `campus_rotation_class_rooms`）：0 行、0 重名组、0 空名，
故 `unique=True` 迁移（`0006_alter_classroom_name`）可安全落地，无冲突。本测试锁死该约束。
"""

import pytest
from django.db import IntegrityError, transaction

from apps.campus_rotation.models import ClassRoom

SENTINEL = '回归唯一性测试班'


@pytest.mark.django_db
def test_classroom_name_unique_enforced():
    ClassRoom.objects.filter(name=SENTINEL).delete()
    try:
        ClassRoom.objects.create(name=SENTINEL, batch='B')
        raised = False
        try:
            # 独立事务包裹，失败插入回滚后连接仍可复用
            with transaction.atomic():
                ClassRoom.objects.create(name=SENTINEL, batch='B')
            raised = False
        except IntegrityError:
            raised = True
        assert raised, '同名班级应触发 IntegrityError（unique 约束失效）'
    finally:
        ClassRoom.objects.filter(name=SENTINEL).delete()

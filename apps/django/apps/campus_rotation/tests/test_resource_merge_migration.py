"""直播间 + 客服部门 → 轮岗资源 的**数据迁移**端到端验证（2026-10-22 兵哥指令）。

用 Django 内置 `MigrationExecutor` 真跑一遍迁移：
  1. 迁到 0016（合并前）→ 造入两表存量数据 + 轮岗安排的位置引用；
  2. 迁到 0017（合并后）→ 断言数据已按归并口径落到新表。

为什么用真迁移而不是直接调 RunPython 函数：
直接调函数时，`apps.get_model()` 拿到的是**当前**模型状态（旧的 live_room /
service_dept FK 已被删），造不出带旧 FK 的历史行 → 测不到「引用是否跟着搬」。
真跑迁移才能拿到 0016 时刻的历史模型。

锁住的点：
  1. 直播间行 → resource_type=LIVE_ROOM，room_no → resource_no，mentor → mentor；
  2. 客服部门行 → resource_type=SERVICE_DEPT，dept_no → resource_no，
     cs_supervisor（客服主管）→ mentor（导师）；
  3. 平台（platform）只从直播间迁；
  4. 轮岗安排的 live_room / service_dept 归并到 resource FK，**引用不丢**；
  5. 软删行也一并迁移（唯一索引覆盖软删行，漏迁会让新号撞已占用的号）。
"""
import uuid

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# ⚠️ 事务标记必须挂在**方法级**（仓库守卫 tests/test_module_level_transaction_guard.py
#    硬性要求）：模块级 django_db(transaction=True) 会让本文件**每个**用例 teardown
#    都 flush 整库 → 抹掉已提交种子 → 后续用例批量 403。
#    本文件每个用例都要在**方法级**开事务：迁移要来回 unapply/apply（DDL 不可回滚，
#    在原子块里会隐式提交、破坏回滚）。

BEFORE = '0016_classroom_code_three_digits'
AFTER = '0017_rotation_resource_unified'
FINAL = '0018_drop_live_room_service_dept'


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@pytest.fixture(autouse=True)
def _restore_final_state():
    """每个用例结束后把库迁回**最终状态**（0018）。

    ⚠️ **MySQL 的 DDL 不可回滚** → 迁移状态**跨用例、跨会话**留存：
      · 本文件的用例会反复把库迁回 0016（旧表在、新表无）；
      · 若结束时不还原：① 后续用例（用当前模型的测试）撞「表不存在」；
        ② 更糟的是**下一次 pytest 会话**的 `django_db_setup` 会跑 `migrate`，
           而 `django_migrations` 里的记录与实际表结构已不一致 →
           报「Table 'campus_rotation_resources' already exists」→ **整场用例 error**。
    故每个用例结束都无条件迁回最终状态。
    """
    yield
    _migrate(FINAL)


def _migrate(target: str):
    """迁到目标迁移，并返回该时刻的**历史模型注册表**。

    🔴 关键：`MigrationExecutor.migrate()` 只改数据库 schema，**不改内存里的
    模型注册表** —— `django.apps.apps.get_model()` 拿到的仍是当前（合并后）模型，
    造不出带 live_room / service_dept 的历史行 → 测不到「引用是否跟着搬」。
    必须用 `project_state(...).apps` 取历史模型。
    """
    executor = MigrationExecutor(connection)
    executor.migrate([('campus_rotation', target)])
    executor.loader.build_graph()
    state = executor.loader.project_state([('campus_rotation', target)])
    return state.apps


def _seed_before_merge() -> dict:
    """在 0016 状态（合并前）造入两表存量数据 + 位置引用，返回关键 id。"""
    old_apps = _migrate(BEFORE)

    User = old_apps.get_model('core', 'User')
    LiveRoom = old_apps.get_model('campus_rotation', 'LiveRoom')
    ServiceDept = old_apps.get_model('campus_rotation', 'ServiceDept')
    Arr = old_apps.get_model('campus_rotation', 'RotationArrangement')

    # 🔴 清掉上一条用例的残留：MySQL 的 DDL 不可回滚 → 迁移状态与数据**跨用例留存**，
    #    而本文件每个用例都往同一批业务唯一键（room_no='ZB0001' 等）写数据
    #    → 不清会撞「Duplicate entry 'ZB0001'」。
    LiveRoom.objects.all().delete()
    ServiceDept.objects.all().delete()
    Arr.objects.all().delete()

    # ⚠️ 历史 User 模型没有 create_user（那是 manager 扩展）→ 用**当前**模型建用户，
    #    再用历史模型取同一行（两版 User 的字段兼容，只用到 pk 与 mentor 引用）。
    from django.contrib.auth import get_user_model
    current_user = get_user_model().objects.create_user(
        username=_uid('u'), password='Test@1234',
    )
    # 历史模型要求**同版本**的 User 实例（FK 赋值校验实例类型）
    user = User.objects.get(pk=current_user.pk)
    room = LiveRoom.objects.create(
        id=_uid('lr'), room_no='ZB0001', name='直播间一', mentor=user,
        platform='TENCENT_MEETING', location='深圳', capacity=10,
        social_count=3, is_active=True, remark='r1',
    )
    dept = ServiceDept.objects.create(
        id=_uid('sd'), dept_no='SD000001', name='客服部一', cs_supervisor=user, location='上海',
        capacity=20, social_count=4, is_active=True, remark='r2',
        brand='BRAND_X', cs_type='CS_T', workstation_type='WS_T',
        need_training_cert=True,
    )
    arr_room = Arr.objects.create(id=_uid('arr'), person_id=900101, live_room=room)
    arr_dept = Arr.objects.create(id=_uid('arr'), person_id=900102, service_dept=dept)
    # 软删行：唯一索引覆盖软删行，漏迁会让新号撞已占用的号
    # ⚠️ 历史模型没有 soft_delete()（那是 SoftDeleteModel 的方法）→ 直接置 deleted_at
    from django.utils import timezone
    soft = LiveRoom.objects.create(
        id=_uid('lr'), room_no='ZB0002', name='已删直播间',
        deleted_at=timezone.now(),
    )

    return {
        'room_id': room.id, 'dept_id': dept.id,
        'arr_room_id': arr_room.id, 'arr_dept_id': arr_dept.id,
        'user_id': user.id,
    }


@pytest.mark.django_db(transaction=True)
def test_migration_merges_both_tables_and_keeps_references():
    """真跑 0017 迁移，断言存量数据按口径归并且位置引用不丢。"""
    seeded = _seed_before_merge()
    new_apps = _migrate(AFTER)

    Res = new_apps.get_model('campus_rotation', 'RotationResource')
    Arr = new_apps.get_model('campus_rotation', 'RotationArrangement')

    # ① 两表行都迁到新表
    assert Res.objects.count() == 3, '两表存量行（含软删）都应迁到新表'

    # ② 直播间行
    migrated_room = Res.objects.get(resource_no='ZB0001')
    assert migrated_room.name == '直播间一'
    assert migrated_room.resource_type == 'LIVE_ROOM'
    assert migrated_room.mentor_id == seeded['user_id'], '直播间导师 → mentor'
    assert migrated_room.platform == 'TENCENT_MEETING', '平台应从直播间迁入'
    assert migrated_room.location == '深圳'
    assert migrated_room.capacity == 10
    assert migrated_room.remark == 'r1'

    # ③ 客服部门行
    migrated_dept = Res.objects.get(resource_no='SD000001')
    assert migrated_dept.name == '客服部一'
    assert migrated_dept.resource_type == 'SERVICE_DEPT'
    assert migrated_dept.mentor_id == seeded['user_id'], '客服主管 → mentor（导师）'
    assert migrated_dept.platform == '', '客服部门无平台'
    assert migrated_dept.location == '上海'
    assert migrated_dept.capacity == 20
    assert migrated_dept.remark == 'r2'

    # ④ 位置引用跟着搬（最易漏：只建新表不改 FK → 位置引用静默变空）
    arr_room = Arr.objects.get(id=seeded['arr_room_id'])
    arr_dept = Arr.objects.get(id=seeded['arr_dept_id'])
    assert arr_room.resource_id == seeded['room_id'], '直播间位置引用丢失'
    assert arr_dept.resource_id == seeded['dept_id'], '客服部门位置引用丢失'

    # ⑤ 软删行也迁移（否则新号会撞已占用的号）
    soft = Res.objects.filter(resource_no='ZB0002').first()
    assert soft is not None, '软删行必须一并迁移'
    assert soft.deleted_at is not None, '软删标记应保留'


@pytest.mark.django_db(transaction=True)
def test_migration_to_final_keeps_data_and_drops_old_tables():
    """🔴 真跑到 0018（删旧表）：新表数据仍在、旧表已消失、位置引用不丢。

    0018 是破坏性迁移（DROP TABLE / DROP COLUMN）—— 必须验证：
      · 数据在 0017 已搬完，0018 只是收尾 → 业务数据**不能**因删表而丢；
      · 旧表确实没了（否则「整合」只是加表不是合并）；
      · 轮岗安排的位置引用仍指向新表资源。
    """
    seeded = _seed_before_merge()
    final_apps = _migrate(FINAL)

    Res = final_apps.get_model('campus_rotation', 'RotationResource')
    Arr = final_apps.get_model('campus_rotation', 'RotationArrangement')

    # ① 数据仍在（3 行：直播间 + 客服部门 + 软删行）
    assert Res.objects.count() == 3, '删旧表不应影响新表数据'
    assert Res.objects.get(resource_no='ZB0001').name == '直播间一'
    assert Res.objects.get(resource_no='SD000001').name == '客服部一'

    # ② 位置引用仍指向新表
    assert Arr.objects.get(id=seeded['arr_room_id']).resource_id == seeded['room_id']
    assert Arr.objects.get(id=seeded['arr_dept_id']).resource_id == seeded['dept_id']

    # ③ 旧表确实被删掉了
    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name IN (%s, %s)",
            ['campus_rotation_live_rooms', 'campus_rotation_service_depts'],
        )
        assert not cur.fetchall(), '旧的两张表应已被删除'


@pytest.mark.django_db(transaction=True)
def test_migration_0018_is_reversible():
    """🔴 0018 可回滚：回滚后两张旧表被重建，且行数据按类型拆回。

    这是「生产切换可回退」的底线：删表迁移若不可逆，出问题就只能手工救火。

    ⚠️ 回滚分两步（与迁移本身的分步一致）：
      · 0018 → 0017：DeleteModel 的逆操作把两张旧表**重建出来**（此时为空表）；
      · 0017 → 0016：0017 的 backward（merge_resources_backward）把新表行**按类型拆回**旧表。
    只回滚到 0017 只能验证「表被重建」，验证「数据被拆回」必须再退一步。
    """
    seeded = _seed_before_merge()
    _migrate(FINAL)

    # ① 回滚到 0017 → 两张旧表被重建
    back_apps = _migrate(AFTER)
    LiveRoom = back_apps.get_model('campus_rotation', 'LiveRoom')
    ServiceDept = back_apps.get_model('campus_rotation', 'ServiceDept')
    assert LiveRoom is not None and ServiceDept is not None, '旧模型应被重新登记'

    # ② 继续回滚到 0016 → 行数据按类型拆回旧表
    old_apps = _migrate(BEFORE)
    LiveRoom = old_apps.get_model('campus_rotation', 'LiveRoom')
    ServiceDept = old_apps.get_model('campus_rotation', 'ServiceDept')

    assert LiveRoom.objects.filter(room_no='ZB0001').exists(), '直播间行应被拆回旧表'
    assert ServiceDept.objects.filter(dept_no='SD000001').exists(), '客服部门行应被拆回旧表'
    assert LiveRoom.objects.filter(room_no='ZB0001').first().name == '直播间一'
    # 软删行也要拆回（否则回滚后新号会撞已占用的号）
    assert LiveRoom.objects.filter(room_no='ZB0002').exists(), '软删行应被拆回旧表'

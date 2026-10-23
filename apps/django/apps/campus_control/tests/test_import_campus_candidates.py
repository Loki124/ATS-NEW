"""校招候选人同步导入 + 两表编号同源（2026-10-23）

覆盖 `import_campus_candidates` 与编号同源的关键判据：

1. **两表取号互撞**（真实缺陷）:
   `Candidate.save()` 与 `Person.save()` 各自只看**本表**最大号取号 →
   两张表同用 C+8 序列时会**互相抢占编号**
   （实测：档案占 C00000001~C00000058，候选人从 C00000008 起领
   → **51 个号被两边同时占用** → 档案永远无法与候选人同源）。
   修复：候选人取号一并看 Person 表已占用的号（与 Person.save 对称）。

2. **冲突判据要区分「同源」与「抢占」**:
   「候选人编号 == 它自己对应档案的编号」是回填后的**正常同源状态**，
   当成冲突处理会让每次重跑导入都把编号推走 → 与回填命令来回震荡。
   判据必须用 `Person.candidate` 外键关系，不能用 `extra['person_code']`
   （那是导入当时的旧编号，回填后已失效 → 全部误判为冲突）。

3. **导入映射与幂等**: 档案 → 候选人字段映射、重复执行不产生重复行。

4. **派生手机号双向一致**: 候选人侧派生 `199`+工号，档案侧也要写同一个值，
   否则「同名多人」的档案认不出人（存量有 4 组同名）。
"""
import pytest

from apps.campus_control.models import Person

pytestmark = pytest.mark.django_db


def _make_person(name='导入验证人', employee_id='25990001', phone='', code=None):
    kwargs = {
        'name': name,
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'status': '待入职',
        'employee_id': employee_id,
    }
    if phone:
        kwargs['phone'] = phone
    if code:
        kwargs['code'] = code
    return Person.objects.create(**kwargs)


def _run_import(*args):
    from django.core.management import call_command
    import io
    out = io.StringIO()
    call_command('import_campus_candidates', *args, stdout=out)
    return out.getvalue()


def test_candidate_auto_number_avoids_person_codes():
    """候选人自动取号必须避开校招档案已占用的 C 序列号（两表互撞修复）。"""
    from apps.candidate.models import Candidate

    # 档案先占住 C00000500
    Person.all_objects.filter(code='C00000500').delete()
    Person.all_objects.create(
        name='占号档案', code='C00000500', bu='能电BG', school='985',
        sex='男', major='工学', status='待入职',
    )
    try:
        cand = Candidate.objects.create(
            name='新候选人', phone='13800001234', recruit_type='campus',
        )
        assert cand.code != 'C00000500', '候选人不得领到档案已占用的号'
        assert cand.code > 'C00000500', f'应排在档案已用号之后: {cand.code}'
    finally:
        Person.all_objects.filter(code='C00000500').delete()


def test_import_creates_campus_candidate_with_mapped_fields():
    """导入把档案映射成校招分区候选人（字段映射正确）。"""
    from apps.candidate.models import Candidate

    _make_person(name='映射验证人', employee_id='25990002', phone='13800002222')
    try:
        _run_import()
        cand = Candidate.objects.filter(
            recruit_type='campus', name='映射验证人',
        ).first()
        assert cand is not None, '应创建校招分区候选人'
        assert cand.gender == '男'
        assert cand.school_tag == '985'
        assert cand.major_tag == '工学'
        assert (cand.extra or {}).get('employee_id') == '25990002'
        assert (cand.extra or {}).get('mock') is True, '须标记为模拟数据（便于将来替换）'
    finally:
        Candidate.objects.filter(name='映射验证人').delete()


def test_import_is_idempotent():
    """重复执行导入不产生重复候选人。"""
    from apps.candidate.models import Candidate

    _make_person(name='幂等验证人', employee_id='25990003', phone='13800003333')
    try:
        _run_import()
        first = Candidate.objects.filter(recruit_type='campus', name='幂等验证人').count()
        assert first == 1
        _run_import()
        second = Candidate.objects.filter(recruit_type='campus', name='幂等验证人').count()
        assert second == 1, f'重复执行不应新增: {first} → {second}'
    finally:
        Candidate.objects.filter(name='幂等验证人').delete()


def test_phone_backfill_makes_duplicate_names_distinguishable():
    """派生手机号回写档案侧 → 同名多人的档案能被认出人。"""
    from apps.campus_control.serializers import auto_match_candidate

    a = _make_person(name='同名甲', employee_id='25990004', phone='')
    b = _make_person(name='同名甲', employee_id='25990005', phone='')
    try:
        _run_import()
        a.refresh_from_db()
        b.refresh_from_db()
        assert a.phone and b.phone, '无手机号的档案应被补上派生测试号'
        assert a.phone != b.phone, '同名档案的派生号必须不同'
        # 认人：靠各自手机号精确区分
        # ⚠️ 候选人 phone 是**加密列**（Fernet 非确定性加密），不能直接等值查询
        #    —— 必须走 hash 盲索引（与 candidate/services.py 的主查重路径同款）。
        from apps.common.encryption import encrypted_field_eq_q
        from apps.candidate.models import Candidate

        matched = auto_match_candidate('同名甲', a.phone)
        assert matched is not None, '应能认出同名档案'
        expected = Candidate.objects.filter(
            encrypted_field_eq_q('phone_hash', a.phone), recruit_type='campus',
        ).first()
        assert expected is not None and matched.pk == expected.pk
        # 且认出的不是另一条同名档案
        other = Candidate.objects.filter(
            encrypted_field_eq_q('phone_hash', b.phone), recruit_type='campus',
        ).first()
        assert other is not None and other.pk != matched.pk, '同名档案不能认错人'
    finally:
        Candidate.objects.filter(name='同名甲').delete()


def test_no_phone_backfill_leaves_person_phone_untouched():
    """`--no-phone-backfill` 时不得改动档案手机号。"""
    from apps.candidate.models import Candidate

    person = _make_person(name='不写回验证人', employee_id='25990006', phone='')
    try:
        _run_import('--no-phone-backfill')
        person.refresh_from_db()
        assert person.phone == '', '加了 --no-phone-backfill 就不得写档案手机号'
    finally:
        Candidate.objects.filter(name='不写回验证人').delete()


def test_conflict_detection_ignores_same_source_pairs():
    """同源状态（候选人编号 == 自己档案的编号）不得被判为冲突。"""
    from apps.candidate.models import Candidate
    from apps.campus_control.management.commands.import_campus_candidates import Command

    person = _make_person(name='同源验证人', employee_id='25990007', phone='13800007777')
    try:
        _run_import()
        cand = Candidate.objects.get(recruit_type='campus', name='同源验证人')
        # 模拟回填：档案关联该候选人且编号一致
        Person.all_objects.filter(pk=person.pk).update(candidate=cand, code=cand.code)
        conflicts = Command()._find_conflicts()
        assert not any(c[0].pk == cand.pk for c in conflicts), '同源不得判为冲突'
    finally:
        Candidate.objects.filter(name='同源验证人').delete()

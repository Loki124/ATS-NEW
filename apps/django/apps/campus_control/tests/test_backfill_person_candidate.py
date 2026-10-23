"""存量校招生档案编号回填命令（2026-10-23）

覆盖 `backfill_person_candidate` 的四类分支:
1. 未关联 + 唯一同名候选人 → 关联候选人 + 编号换成候选人编号;
2. 已关联候选人但编号不一致 → **只纠正编号, 不换人**;
3. 认不出（无同名 / 手机号对不上）→ 不动, 进人工复核清单;
4. 目标编号已被别的档案占用 → 不动, 进人工复核清单（绝不撞 unique）;
5. dry-run → 零写库; --apply → 真写;
6. 幂等: 跑第二遍不再产生变更。
"""
import io
import csv

import pytest
from django.core.management import call_command

from apps.campus_control.models import Person

pytestmark = pytest.mark.django_db


def _make_candidate(name, phone='13800000000', recruit_type='campus', code=None):
    from apps.candidate.models import Candidate
    return Candidate.objects.create(
        name=name,
        phone=phone,
        recruit_type=recruit_type,
        **({'code': code} if code else {}),
    )


def _make_person(name, phone='', code=None, candidate=None):
    kwargs = {
        'name': name,
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'status': '待入职',
    }
    if phone:
        kwargs['phone'] = phone
    if code:
        kwargs['code'] = code
    if candidate is not None:
        kwargs['candidate'] = candidate
    return Person.objects.create(**kwargs)


def _run(*args, review_csv=None):
    """跑命令, 返回 stdout 文本。

    ⚠️ `--review-csv` 走 **kwargs 传（call_command 的关键字参数）,
    不能塞进位置参数 —— 位置参数会被当成命令的未知位置参数直接报错。
    """
    out = io.StringIO()
    kwargs = {'stdout': out}
    if review_csv is not None:
        kwargs['review_csv'] = str(review_csv)
    call_command('backfill_person_candidate', *args, **kwargs)
    return out.getvalue()


def _review_rows(path):
    with open(path, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def test_unlinked_person_gets_candidate_code(tmp_path):
    """未关联 + 唯一同名候选人 → 关联候选人, 编号换成候选人编号。"""
    cand = _make_candidate(name='李四')
    person = _make_person(name='李四', phone='13800000000')

    csv_path = tmp_path / 'review.csv'
    _run('--apply', review_csv=str(csv_path))

    person.refresh_from_db()
    assert person.candidate_id == cand.id
    assert person.code == cand.code


def test_already_linked_person_only_fixes_code_not_person(tmp_path):
    """已关联候选人但编号不一致 → 只纠正编号, **不换人**（不挂到别人头上）。"""
    cand = _make_candidate(name='王五')
    _make_candidate(name='王五', phone='13733334444')
    person = _make_person(name='王五', phone='13800000000', code='C00999999', candidate=cand)

    csv_path = tmp_path / 'review.csv'
    _run('--apply', review_csv=str(csv_path))

    person.refresh_from_db()
    assert person.candidate_id == cand.id, '已认定过的档案不得换人'
    assert person.code == cand.code, '编号应被纠正回该候选人的编号'


def test_unmatched_person_goes_to_review_list(tmp_path):
    """认不出候选人 → 不动档案, 进人工复核清单。"""
    person = _make_person(name='查无此人', phone='13555556666')
    before_code = person.code

    csv_path = tmp_path / 'review.csv'
    _run('--apply', review_csv=str(csv_path))

    person.refresh_from_db()
    assert person.candidate_id is None
    assert person.code == before_code, '认不出就不该改编号'

    rows = _review_rows(csv_path)
    assert len(rows) == 1
    assert rows[0]['姓名'] == '查无此人'
    assert rows[0]['未回填原因'] == '认不出候选人'


def test_occupied_candidate_code_goes_to_review_list(tmp_path):
    """候选人编号已被别的档案占用 → 不换源, 进清单, 不撞 unique。"""
    cand = _make_candidate(name='赵六')
    # 另一个档案先占用了该候选人编号
    _make_person(name='占位的人', phone='13700000000', code=cand.code)
    person = _make_person(name='赵六', phone='13800000000')

    csv_path = tmp_path / 'review.csv'
    _run('--apply', review_csv=str(csv_path))

    person.refresh_from_db()
    assert person.candidate_id is None, '编号被占用时不得换源'
    assert person.code != cand.code

    rows = _review_rows(csv_path)
    reasons = [r['未回填原因'] for r in rows]
    assert '候选人编号已被占用' in reasons


def test_dry_run_does_not_write(tmp_path):
    """dry-run（默认）→ 零写库。"""
    _make_candidate(name='孙七')
    person = _make_person(name='孙七', phone='13800000000')
    before = (person.candidate_id, person.code)

    out = _run(review_csv=str(tmp_path / 'review.csv'))
    assert 'DRY-RUN' in out

    person.refresh_from_db()
    assert (person.candidate_id, person.code) == before, 'dry-run 不得写库'


def test_apply_is_idempotent(tmp_path):
    """回填可重复跑: 第二遍无变更、无新增复核项。"""
    _make_candidate(name='周八')
    person = _make_person(name='周八', phone='13800000000')

    csv1 = tmp_path / 'r1.csv'
    _run('--apply', review_csv=str(csv1))
    person.refresh_from_db()
    code_after = person.code

    csv2 = tmp_path / 'r2.csv'
    _run('--apply', review_csv=str(csv2))
    person.refresh_from_db()
    assert person.code == code_after

    # 第二遍应认成「已同源」→ 不再进复核清单
    rows = _review_rows(csv2)
    assert all(r['姓名'] != '周八' for r in rows)


def test_social_candidate_not_matched(tmp_path):
    """社会招聘分区候选人不得被认成校招生（招聘类型硬分区）。"""
    _make_candidate(name='吴九', recruit_type='social')
    person = _make_person(name='吴九', phone='13800000000')
    before_code = person.code

    csv_path = tmp_path / 'review.csv'
    _run('--apply', review_csv=str(csv_path))

    person.refresh_from_db()
    assert person.candidate_id is None, '不得跨招聘分区认人'
    assert person.code == before_code

    rows = _review_rows(csv_path)
    assert len(rows) == 1
    assert rows[0]['未回填原因'] == '认不出候选人'


def test_review_csv_masks_phone(tmp_path):
    """复核清单里的手机号须脱敏（清单会流转给人工）。"""
    _make_person(name='郑十', phone='13512348000')
    csv_path = tmp_path / 'review.csv'
    _run(review_csv=str(csv_path))
    rows = _review_rows(csv_path)
    assert rows, '认不出的人应在清单里'
    assert '13512348000' not in rows[0]['联系电话']
    assert '*' in rows[0]['联系电话']

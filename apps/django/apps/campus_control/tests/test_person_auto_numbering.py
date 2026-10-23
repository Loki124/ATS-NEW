"""校招生档案自动编号取号口径（2026-10-23）

背景（真实缺陷,实测 ats_dev 复现）:
  `import_campus_lifecycle_data` 引入的 `CS` 前缀编号（CS00000878，实测 878 条）
  与候选人编号的 `C` + 8 位序列**并存**。
  `Person.save()` 的自动补号原先用 `code__startswith='C'` 取最大号 →
  会把 `CS...` 一并选中 → `int('S0000087')` 解析失败 → seq 归 0 →
  去抢 C00000001 → 若该号已被占用则 IntegrityError → 重试 3 次仍是同一号 →
  最终落到 `super().save()` 写入空 code → 撞 unique ⇒ **新建档案直接 500**。

修复: 取号精确匹配 `^C[0-9]{8}$`（Person 与 Candidate 两侧都是）。

⚠️ 判据设计要点（本文件第一版是**假绿**,已修正）:
  仅造一条 `CS` 存量编号 **不足以** 让缺陷显形 ——
  解析失败后 seq 归 0, 此时 `C00000001` 若**未被占用**,照样能领到它, 不报错。
  ⇒ 必须**同时占住 C00000001**, 才能逼出「撞号 → 重试 → 写空 code → 500」这条链。
  （本文件第 1 个用例已加此前置条件; 回退修复后该用例会红, 修复后绿。）

覆盖:
1. 存在 CS 前缀存量编号 **且 C00000001 已被占用** 时, 新建档案仍能自动补号;
2. 新建档案的编号避开 CS 前缀;
3. 候选人表侧同样按精确 C+8 取号（跨表不撞号）;
4. 候选人数已用掉的号不会被校招侧重复领取。
"""
import pytest

from apps.campus_control.models import Person

pytestmark = pytest.mark.django_db


def _occupy(code, name='占号人'):
    """占住一个编号（直接写 code，绕过自动补号）。"""
    Person.all_objects.filter(code=code).delete()
    return Person.all_objects.create(
        name=name,
        code=code,
        bu='能电BG',
        school='985',
        sex='男',
        major='工学',
        status='待入职',
    )


def _make_person(name='取号验证人'):
    """建一个档案（不传 code → 走 save() 的自动补号路径）。"""
    return Person.objects.create(
        name=name,
        bu='能电BG',
        school='985',
        sex='男',
        major='工学',
        status='待入职',
    )


def test_cs_prefix_legacy_rows_do_not_break_auto_numbering():
    """CS 前缀存量 + C00000001 已被占用 → 新建档案仍能自动补号（不得 500 / 不得空号）。"""
    # 前置 ①：CS 前缀存量编号（序号远大于 C 序列，模拟真实数据 878 条 CS 的场景）
    _occupy('CS00000878', 'CS 存量人')
    # 前置 ②：占住 C00000001 —— 没有这一步，缺陷不显形（见文件头「判据设计要点」）
    _occupy('C00000001', 'C 序列占号人')
    try:
        p = _make_person()
        assert p.code, '新建档案必须拿到编号（不得写入空 code）'
        assert p.code.startswith('C'), f'编号应走 C 序列, 实际 {p.code}'
        assert not p.code.startswith('CS'), f'不得领到 CS 前缀的号: {p.code}'
        assert len(p.code) == 9 and p.code[1:].isdigit(), f'编号应为 C + 8 位数字: {p.code}'
        assert p.code != 'C00000001', '不得领到已被占用的号'
    finally:
        Person.all_objects.filter(code__in=['CS00000878', 'C00000001']).delete()


def test_auto_numbering_avoids_occupied_c_number():
    """自动补号不得领到已被占用的号（空号场景不得写出空 code）。"""
    _occupy('C09999999', '高位占号人')
    try:
        p = _make_person(name='取号验证人二')
        assert p.code != 'C09999999'
        assert p.code
    finally:
        Person.all_objects.filter(code='C09999999').delete()


def test_auto_numbering_uses_candidate_max_to_avoid_cross_table_collision():
    """校招侧领号必须避开招聘系统候选人已用掉的 C 序列号（跨表不撞号）。"""
    from apps.candidate.models import Candidate

    Candidate.all_objects.filter(code='C09999998').delete()
    cand = Candidate.objects.create(
        name='跨表占号人',
        phone='13800009998',
        recruit_type='campus',
        code='C09999998',
    )
    try:
        p = _make_person(name='取号验证人三')
        assert p.code != cand.code, '校招侧不得领到候选人已用的号'
        assert p.code > cand.code, f'校招侧编号应排在候选人已用号之后: {p.code} vs {cand.code}'
    finally:
        Candidate.all_objects.filter(pk=cand.pk).delete()

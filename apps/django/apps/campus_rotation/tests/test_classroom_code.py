"""班级编号自动补号规则（2026-10-22 兵哥指令：CL+6 位 → **CL+3 位**）。

原实现两处都写死了 6 位，改 3 位后各自会静默出错，本文件逐条锁死：

1. **格式**：空表首个班级 = `CL001`（3 位），不是 `CL000001`。
2. **连续递增**：连续新建 = CL001 / CL002 / CL003。
3. **存量 6 位号混存**：库里已有 `CL000123`（旧 6 位格式）时，下一个必须是 `CL124`。
   ⚠️ 原实现 `int(code[2:8])` 是写死的 6 位切片，对 6 位存量号恰好能用，但若
   **混存**了不同位宽（3 位新号 + 6 位旧号）就会算错 —— 见用例 4/5。
4. **字符串序陷阱（关键）**：`order_by('-code')` 是**字典序**，`'CL99' > 'CL100000'`
   （'9' > '1'）→ 末行不是序号最大者 → 算出的号会**倒退并撞已占用的号**。
   本用例锁定：CL99 与 CL100000 混存时，下一个是 CL100001（按数值取 max），**不是** CL100。
5. **软删行占号**：唯一索引覆盖软删行 → 取号必须看含软删行的全集，
   否则会复用被删行占用的号 → 插入撞唯一约束。
6. **3 位容量边界**：序号 > 999 时不能被截断成 3 位（'CL1000' 仍是 4 位合法值）。
"""
import pytest

from apps.campus_rotation.models import ClassRoom

pytestmark = pytest.mark.django_db


def _reset() -> None:
    """清空班级（含软删行），让每个用例从空表起步。"""
    ClassRoom.all_objects.all().delete()


def test_first_classroom_code_is_three_digits():
    """空表首个班级 = CL001（3 位）。"""
    _reset()
    c = ClassRoom.objects.create(name='班级A')
    assert c.code == 'CL001', c.code
    assert len(c.code) == 5, f'应为 CL + 3 位，实际 {c.code}'


def test_codes_increment_sequentially():
    """连续新建：CL001 / CL002 / CL003。"""
    _reset()
    codes = [ClassRoom.objects.create(name=f'班级{i}').code for i in range(3)]
    assert codes == ['CL001', 'CL002', 'CL003'], codes


def test_legacy_six_digit_code_is_parsed_correctly():
    """存量 6 位号（CL000123）混存时，下一个是 CL124（不是 CL001 撞号）。"""
    _reset()
    ClassRoom.objects.create(code='CL000123', name='存量6位')
    c = ClassRoom.objects.create(name='班级B')
    assert c.code == 'CL124', c.code


def test_numeric_max_not_lexicographic_max():
    """🔴 字符串序陷阱：CL99 与 CL100000 混存时按**数值**取 max。

    字典序下 'CL99' > 'CL100000'（'9' > '1'）→ 若按 order_by('-code') 取末行，
    会算出 CL100 —— 而 CL100 若不存在则**静默跳号**、若存在则**撞唯一约束**。
    """
    _reset()
    ClassRoom.objects.create(code='CL99', name='三位')
    ClassRoom.objects.create(code='CL100000', name='六位')
    c = ClassRoom.objects.create(name='班级C')
    assert c.code == 'CL100001', c.code


def test_mixed_width_codes_take_numeric_max():
    """3 位新号与 6 位旧号混存：按数值取 max，不能因位数不同而算错。"""
    _reset()
    ClassRoom.objects.create(code='CL5', name='三位')
    ClassRoom.objects.create(code='CL000007', name='六位')
    c = ClassRoom.objects.create(name='班级D')
    assert c.code == 'CL008', c.code


def test_soft_deleted_row_still_occupies_number():
    """🔴 软删行占号：唯一索引覆盖软删行 → 取号须看全集，否则复用被删行的号必撞约束。

    ⚠️ 班级删除走 `soft_delete()`（views.py:95），不是 Django 的 `.delete()`
    （后者是硬删）。这里必须用 soft_delete 才能复现「行还在、但业务上已删」的真实状态。
    """
    _reset()
    c = ClassRoom.objects.create(name='将被软删')
    first_code = c.code
    c.soft_delete()
    assert ClassRoom.all_objects.filter(code=first_code).exists(), '软删行应仍在库里占号'
    nxt = ClassRoom.objects.create(name='软删后新建')
    assert nxt.code != first_code, '复用了软删行占用的号 → 必然撞唯一索引'
    assert nxt.code == f'CL{int(first_code[2:]) + 1:03d}', nxt.code


def test_code_beyond_three_digits_is_not_truncated():
    """序号超过 999 时不能被截断（CL1000 仍是 4 位合法值，不能变 CL000）。"""
    _reset()
    ClassRoom.objects.create(code='CL999', name='三位上限')
    c = ClassRoom.objects.create(name='超三位')
    assert c.code == 'CL1000', c.code

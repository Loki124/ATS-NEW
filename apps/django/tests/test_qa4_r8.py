"""QA-4: R8 DEPT / DEPT_AND_SUB 数据范围功能验证 (含 path 前缀误匹配边界)."""
import pytest
from apps.core.scope_resolver import _own_dept_ids, _dept_and_sub_ids


class _U:
    is_authenticated = True
    def __init__(self, dept_id): self.department_id = dept_id; self.pk = 1


@pytest.mark.django_db
def test_qa4_r8_dept_and_sub_tree():
    from apps.core.models import Department
    root = Department.objects.create(id='d1', code='QA4D1', name='技术中心', path='/d1/')
    child = Department.objects.create(id='d1a', code='QA4D1A', name='后端组', path='/d1/d1a/', parent=root)
    grand = Department.objects.create(id='d1a1', code='QA4D1A1', name='平台小组', path='/d1/d1a/d1a1/', parent=child)
    # 兄弟部门, 用于验证 path 前缀不会误匹配
    sib = Department.objects.create(id='d11', code='QA4D11', name='另一个中心', path='/d11/')

    own = _own_dept_ids(_U('d1'))
    sub = set(_dept_and_sub_ids(_U('d1')))
    print(f"\n[R8] DEPT(本部门)        = {own}")
    print(f"[R8] DEPT_AND_SUB(含子树) = {sorted(sub)}")
    assert own == ['d1'], 'DEPT 应只含本部门'
    assert sub == {'d1', 'd1a', 'd1a1'}, f'DEPT_AND_SUB 应含本部门+全部子孙, 实际 {sub}'
    assert 'd11' not in sub, '❌ path 前缀误匹配: 兄弟部门 d11 被算进子树'
    print("[R8] ✅ 子树正确, 兄弟部门未误入")

    # 中层部门只能看自己 + 下面
    sub_mid = set(_dept_and_sub_ids(_U('d1a')))
    print(f"[R8] 中层 d1a 的子树      = {sorted(sub_mid)}")
    assert sub_mid == {'d1a', 'd1a1'}, '中层部门不应看到父部门'
    print("[R8] ✅ 中层部门不向上越权")


@pytest.mark.django_db
def test_qa4_r8_no_department_falls_back():
    print(f"\n[R8] 无部门用户 DEPT      = {_own_dept_ids(_U(None))}")
    assert _own_dept_ids(_U(None)) == []
    assert _dept_and_sub_ids(_U(None)) == []
    print("[R8] ✅ 无部门用户返回空, 由上层落 SELF 兜底")

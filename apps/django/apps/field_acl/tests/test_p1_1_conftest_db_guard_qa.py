"""QA 独立验证：P1-1 闭环 —— conftest 的 db 依赖修复（函数式用例护栏）。

## 背景（QA 实测发现，工程师已修）

`apps/field_acl/tests/conftest.py` 的 autouse fixture
`_isolate_field_acl_rules_cache` 会调用
`FieldAclService.invalidate_rules_cache(None)`，而后者**会反查 FieldACL 表**
（`FieldACL.objects.values_list('entity', flat=True)`）。

原实现**没有声明 `db` 依赖**：
```python
@pytest.fixture(autouse=True)
def _isolate_field_acl_rules_cache():      # ← 缺 db
    FieldAclService.invalidate_rules_cache(None)
```

pytest-django 对**未标记 `django_db` 的函数式用例**默认禁止数据库访问，
于是该 fixture 在 setup 阶段直接抛：
```
RuntimeError: Database access not allowed, use the "django_db" mark,
or the "db" or "transactional_db" fixtures to enable it.
```
QA 实测：本目录下任何函数式用例 **8/8 全 ERROR**。

而工程师自己的用例用 `django.test.TestCase`（自带事务、DB 访问已预先授权），
完全不受影响 —— 所以这是个**"只对 TestCase 生效"的隐藏护栏缺口**：
conftest 看起来在工作，实则把函数式用例全堵死。

## 本文件的用途

这是一条**专门的闭环证据用例**，三个硬约束（缺一不可）：
  1. **函数式** pytest 用例（不是 TestCase 子类）；
  2. **无** `@pytest.mark.django_db` 标记；
  3. **不覆盖** conftest 的同名 fixture（让它原样执行）。

约束 3 尤其关键：QA 此前的 V2/V3 文件曾用同名 fixture 覆盖绕过此问题，
那样即使 conftest 回退也测不出来。现已去掉覆盖，本文件与那两个文件
共同构成回归护栏。

## 反证（QA 实测）

把 conftest 的 `def _isolate_field_acl_rules_cache(db):` 改回无 db 依赖：
```
ERROR apps/field_acl/tests/test_p1_1_conftest_db_guard_qa.py::test_function_style_case_can_access_db
E RuntimeError: Database access not allowed, use the "django_db" mark...
```
恢复后通过。证明本用例确有鉴别力。
"""

from apps.field_acl.models import FieldACL
from apps.field_acl.services import FieldAclService


def test_function_style_case_can_access_db():
    """函数式用例（无 django_db 标记、不覆盖 fixture）必须能访问数据库。

    只要 conftest 的 autouse fixture 还带着 `db` 依赖，它就会为每个用例
    打通数据库访问；本用例体里直接查表即为证据。

    注意：本函数签名里**故意不写 `db`** —— 授权完全来自 conftest fixture
    的依赖链。若 conftest 回退成无 db 依赖，setup 阶段就会 ERROR，
    根本走不到断言。
    """
    # 直接查表：这一步在 db 依赖缺失时会抛 RuntimeError
    count = FieldACL.objects.count()
    assert isinstance(count, int), 'FieldACL 表应可查询'


def test_conftest_fixture_invalidated_cache():
    """conftest 的 autouse fixture 必须真的清掉了规则缓存。

    `invalidate_rules_cache(None)` 会反查 FieldACL 表拿真实 entity 清单，
    再逐个删除 `field_acl:rules:<entity>` 缓存键。若该 fixture 因 db 缺失
    而在 setup 阶段炸掉，本用例同样会 ERROR（走不到这里）。
    """
    # 先塞一个脏值，模拟"上一个用例留下的缓存"
    from django.core.cache import cache
    cache.set('field_acl:rules:application', {('dirty', 'x'): 'NONE'}, 60)
    assert cache.get('field_acl:rules:application') is not None, '前置：脏缓存应存在'

    # 手动触发与 conftest 相同的失效动作，验证其可执行（即 DB 可访问）
    FieldAclService.invalidate_rules_cache(None)

    assert cache.get('field_acl:rules:application') is None, (
        'invalidate_rules_cache(None) 未清掉缓存 —— '
        '若它因 DatabaseError 被静默吞掉（services.py 的 except 分支），'
        '下一个用例会读到脏规则，表现为随机红'
    )


def test_rules_map_reflects_db_after_invalidate():
    """get_rules_map 读到的是库里的真实状态，不是陈旧缓存。"""
    # 库为空（事务隔离）→ 映射应为空
    assert FieldACL.objects.count() == 0, '前置条件：本用例库内应无规则行'
    rules = FieldAclService.get_rules_map('application')
    assert rules == {}, f'空库应得空映射，实际 {rules}'

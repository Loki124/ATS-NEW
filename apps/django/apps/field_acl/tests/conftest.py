"""字段 ACL 测试公共 fixture。

## 规则缓存隔离（必做，否则随机顺序下时红时绿）

`FieldAclService.get_rules_map` 对 `(entity, field, role_code) -> permission`
做了 **60s TTL 进程缓存**，而 `TestCase` / 事务回滚**不回滚进程级缓存**。
于是「先跑一个配了 NONE 的用例 → 再跑一个期望默认 MASK 的用例」时，
后者会命中前者留下的缓存值，断言随机翻红。

表现：在 `pytest-randomly`（本项目已启用）随机顺序下同一份代码时红时绿；
`-p no:randomly` 固定顺序则稳定 —— 是典型顺序依赖，不是功能回归。

与 data_permission/tests/conftest.py 里 `_isolate_action_dict_cache` 同源同解法：
每个用例前后强制清缓存。ACL 这条更关键 —— 它直接决定断言的脱敏结果，
缓存脏一次就等于"脱敏没生效"的假结论。
"""
import pytest

from apps.field_acl.services import FieldAclService


@pytest.fixture(autouse=True)
def _isolate_field_acl_rules_cache():
    """每个用例前后清空字段 ACL 规则缓存，杜绝跨用例污染。"""
    FieldAclService.invalidate_rules_cache(None)
    yield
    FieldAclService.invalidate_rules_cache(None)
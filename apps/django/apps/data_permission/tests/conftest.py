"""data_permission 测试公共 fixture。

## 动作字典缓存隔离（2026-10-14 补）

``action_registry`` 的动作/预设字典读走 **TTL 进程缓存**（默认 300s），而 ``TestCase``
的事务回滚**不会**回滚进程级缓存。于是：某用例停用/修改动作 → DB 回滚了，
缓存里却还是旧值 → 后续用例读到脏字典 → 断言随机翻红。

在 ``pytest-randomly``（本项目已启用）随机顺序下表现为**时红时绿**：同一份代码
连续跑几轮，失败数会在 0 / 6 / 29 之间跳。固定顺序（``-p no:randomly``）则稳定全绿
—— 这是典型的顺序依赖，而非功能回归，但 CI 跑的是随机顺序，必须根治。

故在此对每个用例前后强制失效缓存。这也正是 ``action_registry`` 模块 docstring
早已写明的约定：「用例间必须 invalidate_cache()」，此前只是没有统一落地。
"""
import pytest

from apps.data_permission.action_registry import invalidate_cache


@pytest.fixture(autouse=True)
def _isolate_action_dict_cache():
    """每个用例前后清空动作字典/预设缓存，杜绝跨用例污染。"""
    invalidate_cache()
    yield
    invalidate_cache()

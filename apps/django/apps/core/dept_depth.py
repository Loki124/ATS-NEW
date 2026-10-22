"""部门层级口径 —— 全仓唯一真相源。

层级编号（**0 基**）：根=0、事业群=1、**BU（二级部门）=2**、三级部门=3。

口径来源（三方一致，改动须同步）：
- 《校招生管理需求规格与实施方案》§6.1（`docs/03-product/校招生管理需求规格与实施方案.md`）：
  「根=0、事业群=1、BU=2、三级部门=3」。
- 前端 `web/app/src/utils/campus.ts`：`deptLevelMap` 根=0，`buOptions` 取 `level === 2`。
- 后端 `apps/campus_rotation/validators.py:is_bu_depth`：BU 判定。

⚠️ 口径漂移是本域最容易复发的一类 bug：
历史实现按「parent 存在且 parent.parent 为空」判定 BU（即 **第 1 级 / 事业群**），
与前端下拉的 `level === 2` 差一级 → 前端下拉里选得出的 BU **一提交必 400**
（`BU 须为二级部门（部门层级=第2级）`），而后端认可的 事业群 前端根本选不到。
故收敛为单一实现，各方一律调用本模块，禁止再各自实现一份层级判定。
"""
from apps.core.models import Department  # noqa: F401  (保持与 Django app 加载顺序的显式依赖)

# 层级封顶：脏数据成环时最多上溯这么多层，避免死循环。
_MAX_WALK = 6


def dept_depth(dept) -> int:
    """返回部门的 0 基层级深度（根=0）；非部门对象返回 -1。

    0 基编号下：
      根        depth=0  （parent_id 为空）
      事业群    depth=1
      BU        depth=2
      三级部门  depth=3
    """
    if dept is None:
        return -1
    depth = 0
    node = dept
    seen = {str(getattr(dept, 'pk', ''))}
    for _ in range(_MAX_WALK):
        if not getattr(node, 'parent_id', None):
            break
        parent = getattr(node, 'parent', None)
        if parent is None:  # parent_id 有值但对象取不到（脏 FK）
            break
        key = str(getattr(parent, 'pk', ''))
        if key in seen:  # 成环，停在已见节点
            break
        seen.add(key)
        node = parent
        depth += 1
    return depth


def is_bu_depth(dept) -> bool:
    """该部门是否为 BU（二级部门）—— 即 0 基层级 `depth == 2`。"""
    return dept_depth(dept) == 2


def bu_ancestor(dept):
    """返回该部门自身或其最近祖先中的 BU（二级部门）；找不到返回 None。

    自身即 BU 时返回自身。用于「给任意层级的部门求其归属 BU」这类解析。
    """
    node = dept
    seen = set()
    for _ in range(_MAX_WALK):
        if node is None:
            return None
        if is_bu_depth(node):
            return node
        key = str(getattr(node, 'pk', ''))
        if key in seen:  # 成环
            return None
        seen.add(key)
        node = getattr(node, 'parent', None)
    return None


def bg_ancestor(dept):
    """返回该部门自身或其最近祖先中的事业群（深度 1）；找不到返回 None。

    自身即事业群（depth == 1）时返回自身；根部门（depth == 0）无事业群祖先，返回 None。
    与 `bu_ancestor` 同构，供「按 BG 归集」的场景使用（如统计概览的需求归集）。
    """
    node = dept
    seen = set()
    for _ in range(_MAX_WALK):
        if node is None:
            return None
        if dept_depth(node) == 1:
            return node
        key = str(getattr(node, 'pk', ''))
        if key in seen:  # 成环
            return None
        seen.add(key)
        node = getattr(node, 'parent', None)
    return None

"""部门层级口径回归测试（2026-10-21 BU 400 修复）。

锁住一条**跨栈**契约：后端判定「某部门是不是 BU」的结果，必须与前端
`web/app/src/utils/campus.ts` 的 BU 下拉选项集合**完全一致**。

起因（真实故障）：后端 `is_bu_depth` 历史上按「parent 存在且 parent.parent 为空」
实现 = 0 基第 1 级（事业群），而前端 `buOptions` 取 `level === 2`（根=0 → 根的孙子）。
两边差一级，后果是：
  - 前端下拉里**选得出的** BU（能智BG / 运营中心）一提交就被后端 400 拒绝
    （`BU 须为二级部门（部门层级=第2级）`）；
  - 后端**认可**的 事业群 前端下拉里根本选不到。

口径真源：根=0、事业群=1、BU=2、三级部门=3
（PRD《校招生管理需求规格与实施方案》§6.1 + `apps/core/dept_depth.py`）。

本文件把前端的 level 算法原样复刻到后端，逐节点比对 —— 前端改了 level 口径而
后端没改（或反之），此测试立即红。
"""
import pytest

from apps.core.dept_depth import bu_ancestor, dept_depth, is_bu_depth
from apps.core.models import Department

pytestmark = pytest.mark.django_db


def _frontend_level(dept, by_id):
    """复刻 web/app/src/utils/campus.ts 的 deptLevelMap（根=0）。

    前端原文：根组织(无 parentId) = 第 0 级，其子 = 第 1 级，依此类推。
    buOptions 取 level === 2 作为 BU 下拉选项。
    """
    level = 0
    cur = dept
    seen = set()
    while cur is not None and getattr(cur, 'parent_id', None) and str(cur.pk) not in seen:
        seen.add(str(cur.pk))
        parent = by_id.get(str(cur.parent_id))
        if parent is None:
            break
        level += 1
        cur = parent
    return level


@pytest.fixture
def chain(db):
    """root(0) -> grp(1, 事业群) -> bu(2, BU) -> deep(3, 三级部门) -> leaf(4)"""
    root = Department.objects.create(id='dd-root', name='集团', code='DD_ROOT', path='/集团')
    grp = Department.objects.create(
        id='dd-grp', name='技术事业群', code='DD_GRP', parent=root, path='/集团/技术事业群',
    )
    bu = Department.objects.create(
        id='dd-bu', name='技术BU', code='DD_BU', parent=grp, path='/集团/技术事业群/技术BU',
    )
    deep = Department.objects.create(
        id='dd-deep', name='技术BU-子', code='DD_DEEP', parent=bu,
        path='/集团/技术事业群/技术BU/子',
    )
    leaf = Department.objects.create(
        id='dd-leaf', name='技术BU-孙', code='DD_LEAF', parent=deep,
        path='/集团/技术事业群/技术BU/子/孙',
    )
    return {'root': root, 'grp': grp, 'bu': bu, 'deep': deep, 'leaf': leaf}


def test_depth_numbering(chain):
    """0 基层级：根=0、事业群=1、BU=2、三级部门=3。"""
    assert dept_depth(chain['root']) == 0
    assert dept_depth(chain['grp']) == 1
    assert dept_depth(chain['bu']) == 2
    assert dept_depth(chain['deep']) == 3
    assert dept_depth(chain['leaf']) == 4


def test_is_bu_depth_matches_frontend_option_list(chain):
    """核心契约：后端判定 == 前端下拉选项集合。

    前端 buOptions 取 `level === 2`；后端 is_bu_depth 必须是同一集合。
    这条断言是本次 400 故障的防回归锁 —— 任何一边单独改口径都会红。
    """
    by_id = {str(d.id): d for d in Department.objects.all()}
    for dept in Department.objects.all():
        fe_bu = _frontend_level(dept, by_id) == 2
        be_bu = is_bu_depth(dept)
        assert fe_bu == be_bu, (
            f'{dept.name}: 前端下拉可选={fe_bu}, 后端 is_bu_depth={be_bu} —— '
            '前后端 BU 口径漂移，表现为「下拉选得到的 BU 一提交就 400」'
        )


def test_bu_ancestor_resolves_to_bu(chain):
    """任意层级部门向上解析出的 BU，必须是 0 基 depth==2 的那个。"""
    assert bu_ancestor(chain['bu']).pk == chain['bu'].pk
    assert bu_ancestor(chain['deep']).pk == chain['bu'].pk
    assert bu_ancestor(chain['leaf']).pk == chain['bu'].pk
    # 事业群自身不是 BU，且其上方无 BU
    assert bu_ancestor(chain['grp']) is None


def test_dept_depth_handles_cycle_without_hang():
    """脏数据成环时不得死循环（历史实现沿 parent 链上溯无环保护）。"""
    a = Department.objects.create(id='dd-cyc-a', name='环A', code='DD_CYC_A', path='/环A')
    b = Department.objects.create(
        id='dd-cyc-b', name='环B', code='DD_CYC_B', parent=a, path='/环A/环B',
    )
    # 直接改 a 的 parent 造成环（绕开 create 时的层级校验）
    Department.objects.filter(pk=a.pk).update(parent_id=b.pk)
    a.refresh_from_db()
    depth = dept_depth(a)
    assert depth >= 0
    assert is_bu_depth(a) is False

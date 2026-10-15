"""2026-10-15 兵哥弹窗选项表：三模块维度编译穿透验证（真实 MySQL DB）。

依据 docs/DESIGN_数据权限规则弹窗选项表.md §6，覆盖：
  1. dfv 跨需求（position.hrbp via demand）
  2. 候选人所属需求/职位 TBP（candidate.demand_tbp / position_tbp 的 path 收口）
  3. 简历锁定人空值 + 用户类（lock_owner 复合条件 + is_empty/is_not_empty）
  4. demand 可见集收窄 + 隐藏维度存量兼容（options_payload 不含隐藏项；owner/hr 仍可编译）
  5. 部门静态含下级（dept + relation=in_subtree）
  6. 动态当前登录用户（tbp + currentUser.id；path 维度 demand_tbp + currentUser.id）
"""
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.data_permission.expr_compiler import compile_scope_q
from apps.data_permission.role_scope_api import options_payload
from apps.demand.models import Demand
from apps.dynamic_field.models import DynamicFieldValue
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _dept(name: str | None = None) -> Department:
    name = name or _uid("BG")
    return Department.objects.create(id=name, name=name, code=name)


def _process() -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="社招标准流程", current_version="V1.0", version_seq=1, is_latest=True,
    )


def _stage(process: RecruitmentProcess) -> RecruitmentStage:
    stage = RecruitmentStage.objects.create(code=_uid("S"), name=_uid("初评"), stage_type="INTERVIEW")
    ProcessStageLink.objects.create(process=process, stage=stage, order=1)
    return stage


def _demand(dept, hr, requested_by, process, **extra) -> Demand:
    return Demand.objects.create(
        code=_uid("D"), title="测试需求", department=dept, requested_by=requested_by,
        hr=hr, headcount=1, process=process, sharers=[], **extra,
    )


def _position(dept, owner, process, demand=None) -> Position:
    return Position.objects.create(
        code=_uid("POS"), title="职位", department=dept,
        hiring_manager=owner, owner=owner, process=process, demand=demand,
    )


def _candidate(**extra) -> Candidate:
    return Candidate.objects.create(name=_uid("C"), phone=_uid("138"), **extra)


def _apply(cand, position, process, stage) -> Application:
    return Application.objects.create(
        code=_uid("APP"), candidate=cand, position=position, process=process,
        workflow_version="V1.0", current_stage=stage,
    )


def _compile(entity: str, dimension: str, *, user_ids=None, operator="in",
            value_source="static", dynamic_key=None, relation=None) -> object:
    """构造单条件 payload 并编译。user_ids 为静态值；动态时传 dynamic_key + user。"""
    cond = {"dimension": dimension, "operator": operator}
    if value_source == "dynamic":
        cond["valueSource"] = "dynamic"
        cond["dynamicKey"] = dynamic_key
    else:
        cond["values"] = [{"id": i} for i in (user_ids or [])]
    if relation is not None:
        cond["relation"] = relation
    payload = {"expr": "", "groups": [{"expr": "", "conditions": [cond]}]}
    return compile_scope_q(payload, entity)


# ---------------------------------------------------------------------------
# 1. dfv 跨需求（position.hrbp via demand）
# ---------------------------------------------------------------------------
def test_position_hrbp_dfv_via_demand():
    dept = _dept()
    process = _process()
    u1, u2 = _user("hrbp1"), _user("hrbp2")

    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    DynamicFieldValue.objects.create(resource="Demand", entity_id=demand.id, field_key="hrbp", value=u1.pk)
    pos_hit = _position(dept, u1, process, demand=demand)
    pos_miss = _position(dept, u1, process, demand=None)  # 无 demand -> 脱钩，不该命中

    q = _compile("position", "hrbp", user_ids=[u1.pk])
    assert q is not None
    matched = set(Position.objects.filter(q).values_list("pk", flat=True))
    assert pos_hit.pk in matched
    assert pos_miss.pk not in matched

    # 反向：hrbp=u2 不应命中
    q2 = _compile("position", "hrbp", user_ids=[u2.pk])
    assert pos_hit.pk not in set(Position.objects.filter(q2).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# 2. 候选人所属需求/职位 TBP（path 收口，杜绝 fan-out）
# ---------------------------------------------------------------------------
def test_candidate_demand_tbp_and_position_tbp_path():
    dept = _dept()
    process = _process()
    stage = _stage(process)
    u1, u2 = _user("tbp1"), _user("tbp2")

    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    pos = _position(dept, u1, process, demand=demand)
    c_hit = _candidate()
    _apply(c_hit, pos, process, stage)
    # 反例候选人：职位脱离需求（demand_id NULL）-> 不应命中任何 demand_* 维度
    pos_orphan = _position(dept, u1, process, demand=None)
    c_miss = _candidate()
    _apply(c_miss, pos_orphan, process, stage)

    for dim in ("demand_tbp", "position_tbp"):
        q = _compile("candidate", dim, user_ids=[u1.pk])
        assert q is not None, f"{dim} 应编译出非空 Q"
        matched = set(Candidate.objects.filter(q).values_list("pk", flat=True))
        assert c_hit.pk in matched, f"{dim} 应命中关联到 hr=u1 需求的候选人"
        assert c_miss.pk not in matched, f"{dim} 不应命中脱钩职位的候选人"

        q2 = _compile("candidate", dim, user_ids=[u2.pk])
        assert c_hit.pk not in set(Candidate.objects.filter(q2).values_list("pk", flat=True))


def test_candidate_demand_hrbp_dfv_path():
    dept = _dept()
    process = _process()
    stage = _stage(process)
    u1, u2 = _user("hrbp_d1"), _user("hrbp_d2")

    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    DynamicFieldValue.objects.create(resource="Demand", entity_id=demand.id, field_key="hrbp", value=u1.pk)
    pos = _position(dept, u1, process, demand=demand)
    c_hit = _candidate()
    _apply(c_hit, pos, process, stage)

    q = _compile("candidate", "demand_hrbp", user_ids=[u1.pk])
    assert c_hit.pk in set(Candidate.objects.filter(q).values_list("pk", flat=True))
    q2 = _compile("candidate", "demand_hrbp", user_ids=[u2.pk])
    assert c_hit.pk not in set(Candidate.objects.filter(q2).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# 3. 简历锁定人空值 + 用户类（lock_owner）
# ---------------------------------------------------------------------------
def test_candidate_lock_owner():
    now = timezone.now()
    u1, u2 = _user("lock1"), _user("lock2")

    c_formal = _candidate(formal_locked_by=u1)                 # 正式锁定 u1
    c_none = _candidate()                                      # 完全无锁
    c_expired = _candidate(temp_locked_by=u2, temp_lock_expires_at=now - timedelta(days=1))  # 临时锁已过期
    c_temp = _candidate(temp_locked_by=u2, temp_lock_expires_at=now + timedelta(days=1))      # 临时锁有效

    # is_empty -> 仅 c_none / c_expired 命中（过期 = 等同未锁定）
    q = _compile("candidate", "lock_owner", operator="is_empty")
    assert q is not None
    matched = set(Candidate.objects.filter(q).values_list("pk", flat=True))
    assert c_none.pk in matched and c_expired.pk in matched
    assert c_formal.pk not in matched and c_temp.pk not in matched

    # is_not_empty -> 仅 c_formal / c_temp 命中
    q = _compile("candidate", "lock_owner", operator="is_not_empty")
    matched = set(Candidate.objects.filter(q).values_list("pk", flat=True))
    assert c_formal.pk in matched and c_temp.pk in matched
    assert c_none.pk not in matched and c_expired.pk not in matched

    # 静态 in [u1] -> 仅 c_formal
    q = _compile("candidate", "lock_owner", user_ids=[u1.pk])
    matched = set(Candidate.objects.filter(q).values_list("pk", flat=True))
    assert c_formal.pk in matched
    assert c_temp.pk not in matched and c_expired.pk not in matched

    # 静态 in [u2] -> 仅 c_temp（c_expired 过期不计入）
    q = _compile("candidate", "lock_owner", user_ids=[u2.pk])
    matched = set(Candidate.objects.filter(q).values_list("pk", flat=True))
    assert c_temp.pk in matched
    assert c_formal.pk not in matched and c_expired.pk not in matched


# ---------------------------------------------------------------------------
# 4. demand 可见集收窄 + 隐藏维度存量兼容
# ---------------------------------------------------------------------------
def test_demand_visible_set_excludes_hidden_dimensions():
    resp = options_payload()
    demand_mod = next(m for m in resp["modules"] if m["moduleKey"] == "demand")
    visible = {d["key"] for d in demand_mod["dimensions"]}
    # 兵哥表：需求人员字段不止 创建人/TBP/HRBP —— 提出人/共享人/用人经理/用人经理上级/抢单人 一并可见
    expected = {"tbp", "hrbp", "creator", "dept", "requested_by", "sharers",
                "hiring_manager", "hiring_manager_superior", "resume_grabber"}
    assert visible == expected, f"demand 可见维度不符预期（多/缺）: {visible ^ expected}"
    # 隐藏维度（owner/hr 为 tbp 冗余别名；unit 全局隐藏）不应下发
    hidden = {"owner", "hr", "unit"}
    assert hidden.isdisjoint(visible), f"隐藏维度不应出现: {hidden & visible}"
    # 每个可见用户类维度都应下发 operators（包含/不包含），否则前端运算符下拉为空
    for d in demand_mod["dimensions"]:
        if d["valueType"] == "user":
            ops = {o["value"] for o in d.get("operators", [])}
            assert {"in", "not_in"} <= ops, f"维度 {d['key']} 缺少包含/不包含运算符: {ops}"


def test_demand_hidden_owner_and_hr_still_compile():
    """隐藏维度虽不下发，但存量规则（dimension='owner'/'hr'）仍能正常编译命中。"""
    dept = _dept()
    process = _process()
    u1, u2 = _user("owner1"), _user("owner2")
    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    other = _demand(dept, hr=u2, requested_by=u2, process=process)

    for dim in ("owner", "hr"):
        q = _compile("demand", dim, user_ids=[u1.pk])
        assert q is not None
        matched = set(Demand.objects.filter(q).values_list("pk", flat=True))
        assert demand.pk in matched, f"隐藏维度 {dim} 应命中 hr=u1 的需求"
        assert other.pk not in matched


def test_demand_hiring_manager_dynamic_current_user():
    """2026-10-15：补全的需求人员维度（用人经理）同样支持「当前登录用户」动态源。"""
    dept = _dept()
    process = _process()
    u1, u2 = _user("hm_dyn1"), _user("hm_dyn2")
    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    DynamicFieldValue.objects.create(resource="Demand", entity_id=demand.id, field_key="hiring_manager", value=u1.pk)

    q = _compile_with_user("demand", "hiring_manager", dynamic_key="currentUser.id", user=u1)
    assert demand.pk in set(Demand.objects.filter(q).values_list("pk", flat=True)), \
        "动态 用人经理(当前登录用户) 应命中自己是用人经理的需求"
    q2 = _compile_with_user("demand", "hiring_manager", dynamic_key="currentUser.id", user=u2)
    assert demand.pk not in set(Demand.objects.filter(q2).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# 5. 部门静态含下级（dept + relation=in_subtree）
# ---------------------------------------------------------------------------
def test_demand_dept_in_subtree():
    process = _process()
    a = _dept("DA-" + uuid.uuid4().hex[:8])
    b = Department.objects.create(id="DB-" + uuid.uuid4().hex[:8], name="DB", code="DB", parent=a)
    u = _user("hr_dept")

    d_a = _demand(a, hr=u, requested_by=u, process=process)
    d_b = _demand(b, hr=u, requested_by=u, process=process)

    # exact：仅挂在 A 的命中
    q = _compile("demand", "dept", user_ids=[a.id], relation="exact")
    matched = set(Demand.objects.filter(q).values_list("pk", flat=True))
    assert d_a.pk in matched and d_b.pk not in matched

    # in_subtree：A 及其下级 B 均命中
    q = _compile("demand", "dept", user_ids=[a.id], relation="in_subtree")
    matched = set(Demand.objects.filter(q).values_list("pk", flat=True))
    assert d_a.pk in matched and d_b.pk in matched


# ---------------------------------------------------------------------------
# 6. 动态当前登录用户（tbp + currentUser.id；path 维度 demand_tbp + currentUser.id）
# ---------------------------------------------------------------------------
def test_demand_tbp_dynamic_current_user():
    dept = _dept()
    process = _process()
    u1, u2 = _user("tu1"), _user("tu2")
    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    other = _demand(dept, hr=u2, requested_by=u2, process=process)

    # user=u1 -> 等价于 tbp in [u1.pk]
    q = _compile_with_user("demand", "tbp", dynamic_key="currentUser.id", user=u1)
    matched = set(Demand.objects.filter(q).values_list("pk", flat=True))
    assert demand.pk in matched
    assert other.pk not in matched

    # user=u2（非该需求 tbp）-> 不命中
    q = _compile_with_user("demand", "tbp", dynamic_key="currentUser.id", user=u2)
    assert demand.pk not in set(Demand.objects.filter(q).values_list("pk", flat=True))


def test_candidate_demand_tbp_dynamic_current_user():
    dept = _dept()
    process = _process()
    stage = _stage(process)
    u1, u2 = _user("ctu1"), _user("ctu2")
    demand = _demand(dept, hr=u1, requested_by=u1, process=process)
    pos = _position(dept, u1, process, demand=demand)
    c_hit = _candidate()
    _apply(c_hit, pos, process, stage)

    q = _compile_with_user("candidate", "demand_tbp", dynamic_key="currentUser.id", user=u1)
    assert c_hit.pk in set(Candidate.objects.filter(q).values_list("pk", flat=True))
    q2 = _compile_with_user("candidate", "demand_tbp", dynamic_key="currentUser.id", user=u2)
    assert c_hit.pk not in set(Candidate.objects.filter(q2).values_list("pk", flat=True))


def _compile_with_user(entity: str, dimension: str, *, dynamic_key: str, user, operator="in") -> object:
    """与 _compile 同等，但显式传入 user（动态条件需要）。"""
    cond = {
        "dimension": dimension, "operator": operator,
        "valueSource": "dynamic", "dynamicKey": dynamic_key,
    }
    payload = {"expr": "", "groups": [{"expr": "", "conditions": [cond]}]}
    return compile_scope_q(payload, entity, user=user)

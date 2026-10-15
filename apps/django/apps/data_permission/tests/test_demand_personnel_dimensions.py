"""task #15：招聘需求模块「人员类型字段」维度编译验证（穿透真实 DB）。

验证 field_map.py 把 demand 的 owner 维度扩展为全部人员类型字段后，
expr_compiler 能正确把每个维度编译成命中对应 Demand 的 Q：

  - hr            -> hr_id（FK 标量 __in）
  - requested_by  -> requested_by_id（FK 标量 __in）
  - sharers       -> JSON 多值 __contains
  - hrbp / hiring_manager / hiring_manager_superior -> DynamicFieldValue PERSON 子查询
  - resume_grabber-> Demand→Position→Application.grabbed_by 反向 FK 子查询收口
  - owner（隐藏别名）-> 仍映射到 hr_id，存量规则继续编译命中

每个维度都用「真实落库数据 + compile_scope_q 编译 + Demand 过滤」两步式断言，
杜绝假绿；另构造反例需求验证「不属于这些人的需求不被匹配」，并验证 neq 取反语义。
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.core.models import Department
from apps.data_permission.expr_compiler import compile_scope_q
from apps.demand.models import Demand
from apps.dynamic_field.models import DynamicFieldValue
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _user(tag: str = "u"):
    return get_user_model().objects.create_user(username=_uid(tag), password="Test@1234")


def _dept() -> Department:
    return Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BG"))


def _process() -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=_uid("PROC"), name="社招标准流程", current_version="V1.0", version_seq=1, is_latest=True,
    )


def _make_demand(dept, hr, requested_by, process, sharers=None) -> Demand:
    return Demand.objects.create(
        code=_uid("D"), title="测试需求", department=dept, requested_by=requested_by,
        hr=hr, headcount=1, process=process, sharers=sharers or [],
    )


def _compile(dimension: str, user_ids: list, operator: str = "in"):
    payload = {
        "expr": "",
        "groups": [{
            "expr": "",
            "conditions": [{
                "dimension": dimension, "operator": operator,
                "values": [{"id": i} for i in user_ids],
            }],
        }],
    }
    return compile_scope_q(payload, "demand")


def _matched_ids(dimension: str, user_ids: list, operator: str = "in") -> set:
    q = _compile(dimension, user_ids, operator)
    assert q is not None, f"维度 {dimension} 应编译出非空 Q"
    return set(Demand.objects.filter(q).values_list("pk", flat=True))


def test_demand_personnel_dimensions_all_match_and_negative_and_neq():
    dept = _dept()
    process = _process()

    u_hr = _user("hr")
    u_req = _user("req")
    u1 = _user("share1")
    u2 = _user("share2")
    u_hrbp = _user("hrbp")
    u_hm = _user("hm")
    u_hms = _user("hms")
    u_grab = _user("grab")

    # 主需求：挂满所有人员字段
    demand = _make_demand(dept, u_hr, u_req, process, sharers=[u1.pk, u2.pk])
    DynamicFieldValue.objects.create(resource="Demand", entity_id=demand.id, field_key="hrbp", value=u_hrbp.pk)
    DynamicFieldValue.objects.create(resource="Demand", entity_id=demand.id, field_key="hiring_manager", value=u_hm.pk)
    DynamicFieldValue.objects.create(
        resource="Demand", entity_id=demand.id, field_key="hiring_manager_superior", value=u_hms.pk,
    )

    # resume_grabber 链：demand -> position -> application(grabbed_by)
    position = Position.objects.create(
        code=_uid("POS"), title="职位", department=dept,
        hiring_manager=u_hr, owner=u_hr, process=process, demand=demand,
    )
    cand = Candidate.objects.create(name="抢单候选人", phone=_uid("138"))
    # 注意：'初评' 是迁移 0012 预置的内置阶段（recruitment_stages.name 唯一），
    # 测试库每次重建都会存在该 name，故此处必须用唯一名，否则触发唯一键冲突。
    stage = RecruitmentStage.objects.create(code=_uid("S"), name=_uid("初评"), stage_type="INTERVIEW")
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=1)
    Application.objects.create(
        code=_uid("APP"), candidate=cand, position=position, process=process,
        workflow_version="V1.0", current_stage=link.stage, is_grabbed=True, grabbed_by=u_grab,
    )

    # 反例需求：不属于任何这些人、无 dfv、无抢单
    demand_neg = _make_demand(dept, _user("nhr"), _user("nreq"), process, sharers=[])

    # (维度, 目标用户 id) —— 含 owner 向后兼容
    cases = [
        ("hr", [u_hr.pk]),
        ("requested_by", [u_req.pk]),
        ("sharers", [u1.pk]),
        ("sharers", [u2.pk]),
        ("hrbp", [u_hrbp.pk]),
        ("hiring_manager", [u_hm.pk]),
        ("hiring_manager_superior", [u_hms.pk]),
        ("resume_grabber", [u_grab.pk]),
        ("owner", [u_hr.pk]),
    ]
    for dim, ids in cases:
        matched = _matched_ids(dim, ids)
        assert demand.pk in matched, f"维度 {dim} 应命中主需求 {demand.code}"
        assert demand_neg.pk not in matched, f"维度 {dim} 不应命中反例需求（误放行）"

    # neq 取反：hr != u_hr 应排除主需求、命中反例
    matched = _matched_ids("hr", [u_hr.pk], operator="neq")
    assert demand.pk not in matched, "neq 应排除 hr 命中的主需求"
    assert demand_neg.pk in matched, "neq 应命中反例需求"

    # 探明 dfv PERSON value 实际存储类型（文档化，非硬约束；编译已用 OR 兼容 int/str）
    stored = DynamicFieldValue.objects.get(resource="Demand", entity_id=demand.id, field_key="hrbp")
    assert stored.value in (u_hrbp.pk, str(u_hrbp.pk)), \
        f"dfv value 应存为用户 id（实测类型 {type(stored.value).__name__}）"


def test_demand_personnel_dimension_dynamic_source_fail_closed():
    """phase-1：人员维度不支持动态取值，传动态源必须 fail-closed（编译出空命中集）。"""
    # 动态编译需要 user 上下文；这里直接验证编译结果是「不放行」的空集语义。
    payload = {
        "expr": "",
        "groups": [{
            "expr": "",
            "conditions": [{
                "dimension": "hrbp", "operator": "in",
                "valueSource": "dynamic", "dynamicKey": "currentUser.id",
                "values": [],
            }],
        }],
    }
    q = compile_scope_q(payload, "demand", user=_user("any"))
    # _deny_all() -> Q(pk__in=[])：任何 Demand 都不命中
    assert q is not None
    assert not Demand.objects.filter(q).exists(), "动态取值的人员维度必须 fail-closed（零命中）"

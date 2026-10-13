"""候选人详情序列化器新字段回归（2026-10-13 详情页字段补充）。

覆盖「锁定人 / 应聘渠道 / 简历来源 / 所属流程 / 当前阶段步骤条」所需出参：
- recruiter_name（锁定人，候选人级招聘官）
- resume_source（简历来源，按真实数据推导：摩卡同步/附件上传/手动录入）
- applications[].process_name（应聘职位对应的所属流程）
- applications[].grabbed_by_name（锁定人兜底：投递认领人）
- applications[].stage_list（流程阶段有序列表，驱动「当前阶段」步骤条）
- Prefetch 缓存路径：retrieve 走 _prefetched_objects_cache，不再逐行 N+1
"""
import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.candidate.serializers import CandidateDetailSerializer
from apps.core.models import Department
from apps.position.models import Position
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage

pytestmark = pytest.mark.django_db


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _make_process(name: str = "社招标准流程") -> RecruitmentProcess:
    return RecruitmentProcess.objects.create(
        code=_uid("PROC"), name=name, current_version="V1.0",
        version_seq=1, is_latest=True,
    )


def _make_stage(process: RecruitmentProcess, name: str, order: int, custom_name: str = "") -> ProcessStageLink:
    stage = RecruitmentStage.objects.create(
        code=_uid("P"), name=name, stage_type="INTERVIEW",
    )
    return ProcessStageLink.objects.create(
        process=process, stage=stage, order=order, custom_name=custom_name,
    )


def _make_candidate(**kwargs) -> Candidate:
    return Candidate.objects.create(name=kwargs.pop("name", "详情候选人"), phone=_uid("138"), **kwargs)


@pytest.mark.django_db
def test_header_fields_present_without_relations():
    """无任何关联时：锁定人/简历来源键仍在，resume_source 落「手动录入」。"""
    c = _make_candidate()
    data = CandidateDetailSerializer(c).data
    assert data["recruiter_name"] == ""
    assert data["resume_source"] == "手动录入"
    # 应聘渠道：无渠道时为空串而非缺失键
    assert data["source_channel_name"] == ""


def test_resume_source_derivation():
    """简历来源按真实入库形态推导，禁止虚构枚举。"""
    with_file = _make_candidate(resume_file_url="https://example.com/r.pdf")
    assert CandidateDetailSerializer(with_file).data["resume_source"] == "附件上传"
    with_moka = _make_candidate(moka_candidate_id="MK-1")
    assert CandidateDetailSerializer(with_moka).data["resume_source"] == "摩卡同步"
    # 两者都有时摩卡同步优先（先入库第三方同步）
    both = _make_candidate(resume_file_url="https://example.com/r.pdf", moka_candidate_id="MK-2")
    assert CandidateDetailSerializer(both).data["resume_source"] == "摩卡同步"


def test_recruiter_name_is_lock_person():
    """锁定人 = 候选人级招聘官 username。"""
    User = get_user_model()
    hr = User.objects.create_user(username=_uid("locker"), password="Test@1234")
    c = _make_candidate(recruiter=hr)
    data = CandidateDetailSerializer(c).data
    assert data["recruiter_name"] == hr.username


def _make_full_chain():
    """造 职位→流程→阶段链 + 投递，返回 (candidate, application, stage_names)。"""
    User = get_user_model()
    user = User.objects.create_user(username=_uid("hm"), password="Test@1234")
    locker = User.objects.create_user(username="锁定人小李", password="Test@1234")
    dept = Department.objects.create(id=_uid("dept"), name=_uid("BG"), code=_uid("BG"))
    process = _make_process()
    _make_stage(process, _uid("初评"), order=1)
    _make_stage(process, _uid("简历筛选"), order=2)
    current_stage = _make_stage(process, _uid("薪酬意向确认"), order=3, custom_name="沟通Offer")
    _make_stage(process, _uid("正式录用"), order=4)
    position = Position.objects.create(
        code=_uid("POS"), title="客服专员", department=dept,
        hiring_manager=user, owner=user, process=process,
    )
    candidate = _make_candidate(name="投递候选人")
    application = Application.objects.create(
        code=_uid("APP"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0",
        current_stage=current_stage.stage, is_grabbed=True, grabbed_by=locker,
    )
    return candidate, application


def test_applications_expose_process_stages_and_lock_fallback():
    """applications 出参含所属流程、当前阶段、阶段有序列表、认领人兜底。"""
    candidate, _ = _make_full_chain()
    apps = CandidateDetailSerializer(candidate).data["applications"]
    assert len(apps) == 1
    app = apps[0]
    assert app["position_title"] == "客服专员"
    assert app["process_name"] == "社招标准流程"
    assert app["current_stage"] is not None and app["current_stage"].endswith("薪酬意向确认")
    assert app["grabbed_by_name"] == "锁定人小李"
    # 阶段列表按 order 升序，且流程内显示名（custom_name）覆盖全局阶段名
    assert app["stage_list"][2] == "沟通Offer"
    assert len(app["stage_list"]) == 4


def test_get_applications_uses_prefetch_cache():
    """retrieve 路径：_prefetched_objects_cache 有 applications 时走缓存（软删记录不在其中）。"""
    candidate, _ = _make_full_chain()
    User = get_user_model()
    locker = User.objects.get(username="锁定人小李")
    # 再插一条软删投递：不应出现在出参
    process = RecruitmentProcess.objects.get(name="社招标准流程")
    position = Position.objects.get(title="客服专员")
    soft = Application.objects.create(
        code=_uid("APP"), candidate=candidate, position=position,
        process=process, workflow_version="V1.0", grabbed_by=locker,
    )
    soft.delete()  # SoftDeleteModel：置 deleted_at

    prefetched = list(
        Application.objects.filter(deleted_at__isnull=True)
        .select_related("position", "process", "current_stage", "grabbed_by")
        .prefetch_related("process__stage_links__stage")
        .order_by("-created_at")
    )
    candidate._prefetched_objects_cache = {"applications": prefetched}
    apps = CandidateDetailSerializer(candidate).data["applications"]
    assert len(apps) == 1, "软删投递不得泄漏；缓存路径必须生效"
    assert len(apps[0]["stage_list"]) == 4
    assert apps[0]["stage_list"][2] == "沟通Offer"

"""全局统一搜索端点测试 (apps/search/tests/test_search.py)

用 DRF APIClient + force_authenticate 验证 GET /api/v1/search/ 的契约:
- 6 个实体均可被搜索到
- candidate.phone 脱敏
- 软删 (deleted_at 有值) 的实体不出现
- 空 q 返回 totalGroups:0
- types 子集过滤
- limit 截断
- 驼峰键: totalGroups / scheduledAt / candidateName / realName / status
- 响应结构含 query/took/groups, 每组含 type/total/items
"""
import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Department, User
from apps.process.models import RecruitmentProcess, RecruitmentStage, ProcessStageLink
from apps.candidate.models import Candidate
from apps.demand.models import Demand
from apps.position.models import Position
from apps.application.models import Application, ApplicationStageRecord
from apps.interview.models import Interview
from apps.offer.models import Offer
from apps.referral.models import Referral


SEARCH_URL = '/api/v1/search/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='searcher', password='pw123456')


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def department(db):
    return Department.objects.create(name='研发部', code='rd', path='/研发部')


@pytest.fixture
def process(db):
    return RecruitmentProcess.objects.create(code='W001', name='标准流程')


@pytest.fixture
def stage(db, process):
    # 注意: P001(初评)/P099(正式录用) 已由进程迁移 0012 预置为 built-in 起止阶段,
    # 此处必须用非预置 code 避免与进程唯一约束冲突。
    rec = RecruitmentStage.objects.create(
        code='PTEST01', name='简历筛选', stage_type='SCREEN'
    )
    return ProcessStageLink.objects.create(process=process, stage=rec)


@pytest.fixture
def candidate(db):
    return Candidate.objects.create(
        name='王小明',
        phone='13812348000',
        email='wang@example.com',
        current_position='后端工程师',
    )


@pytest.fixture
def position(db, department, process, user):
    return Position.objects.create(
        code='POS001',
        title='高级后端工程师',
        department=department,
        hiring_manager=user,
        owner=user,
        process=process,
    )


@pytest.fixture
def application(db, candidate, position, process):
    return Application.objects.create(
        code='APP001',
        candidate=candidate,
        position=position,
        process=process,
        workflow_version='V1.0',
    )


@pytest.fixture
def demand(db, department, user, process):
    return Demand.objects.create(
        code='DEM001',
        title='后端招聘需求',
        department=department,
        requested_by=user,
        hr=user,
        headcount=2,
        process=process,
    )


@pytest.fixture
def interview(db, application, stage):
    return Interview.objects.create(
        code='INT001',
        application=application,
        stage_record=ApplicationStageRecord.objects.create(
            application=application,
            link=stage,
            stage=stage.stage,
        ),
        scheduled_at=datetime.datetime(2026, 8, 20, 10, 0, 0, tzinfo=datetime.timezone.utc),
    )


@pytest.fixture
def offer(db, application, candidate, position):
    return Offer.objects.create(
        code='OFF001',
        application=application,
        candidate=candidate,
        position=position,
    )


@pytest.fixture
def referral(db, candidate, user, position):
    return Referral.objects.create(
        referrer=user,
        candidate=candidate,
        position=position,
        referral_type='INTERNAL',
    )


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
def test_unauthenticated_returns_401(api_client):
    resp = api_client.get(SEARCH_URL, {'q': 'x'})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 各实体可搜到
# ---------------------------------------------------------------------------
def test_candidate_searchable(auth_client, candidate, application):
    resp = auth_client.get(SEARCH_URL, {'q': '王小明'})
    assert resp.status_code == 200
    data = resp.json()
    cand = _group(data, 'candidate')
    assert cand is not None
    assert cand['total'] >= 1
    item = cand['items'][0]
    assert item['id'] == str(candidate.id)
    assert item['name'] == '王小明'
    assert item['position']['name'] == '高级后端工程师'


def test_candidate_phone_masked(auth_client, candidate):
    resp = auth_client.get(SEARCH_URL, {'q': '王小明'})
    item = _group(resp.json(), 'candidate')['items'][0]
    assert '****' in item['phone']
    assert item['phone'] == '138****8000'


def test_demand_searchable(auth_client, demand):
    resp = auth_client.get(SEARCH_URL, {'q': '后端招聘需求'})
    grp = _group(resp.json(), 'demand')
    assert grp is not None and grp['total'] >= 1
    item = grp['items'][0]
    assert item['id'] == str(demand.id)
    assert item['title'] == '后端招聘需求'
    # state 映射为 status 输出
    assert item['status'] == demand.state


def test_position_searchable(auth_client, position):
    resp = auth_client.get(SEARCH_URL, {'q': '高级后端工程师'})
    grp = _group(resp.json(), 'position')
    assert grp is not None and grp['total'] >= 1
    item = grp['items'][0]
    assert item['id'] == str(position.id)
    assert item['name'] == position.title  # title → name
    assert item['status'] == position.state  # state → status


def test_interview_searchable(auth_client, interview):
    resp = auth_client.get(SEARCH_URL, {'q': 'INT001'})
    grp = _group(resp.json(), 'interview')
    assert grp is not None and grp['total'] >= 1
    item = grp['items'][0]
    assert item['id'] == str(interview.id)
    assert item['candidate']['name'] == '王小明'
    assert item['position']['name'] == '高级后端工程师'


def test_offer_searchable(auth_client, offer):
    # 用 candidate 名搜 offer
    resp = auth_client.get(SEARCH_URL, {'q': '王小明'})
    grp = _group(resp.json(), 'offer')
    assert grp is not None and grp['total'] >= 1
    item = grp['items'][0]
    assert item['id'] == str(offer.id)
    assert item['status'] == offer.state
    assert item['candidate']['name'] == '王小明'
    assert item['position']['name'] == '高级后端工程师'


def test_referral_searchable(auth_client, referral, user):
    resp = auth_client.get(SEARCH_URL, {'q': '王小明'})
    grp = _group(resp.json(), 'referral')
    assert grp is not None and grp['total'] >= 1
    item = grp['items'][0]
    assert item['id'] == str(referral.id)
    # candidateName 来自 obj.candidate.name (camelCase 渲染)
    assert item['candidateName'] == '王小明'
    # referrer.realName 来自 obj.referrer.full_name (camelCase 渲染)
    assert item['referrer']['realName'] == user.full_name


# ---------------------------------------------------------------------------
# 软删过滤
# ---------------------------------------------------------------------------
def test_soft_deleted_excluded(auth_client, candidate):
    candidate.deleted_at = timezone.now()
    candidate.save(update_fields=['deleted_at'])
    resp = auth_client.get(SEARCH_URL, {'q': '王小明'})
    grp = _group(resp.json(), 'candidate')
    assert grp is None or grp['total'] == 0


# ---------------------------------------------------------------------------
# 空 q
# ---------------------------------------------------------------------------
def test_empty_q(auth_client):
    resp = auth_client.get(SEARCH_URL, {'q': '   '})
    assert resp.status_code == 200
    data = resp.json()
    assert data['query'] == '   '
    assert data['took'] == 0
    assert data['totalGroups'] == 0
    assert data['groups'] == []


# ---------------------------------------------------------------------------
# types 子集过滤
# ---------------------------------------------------------------------------
def test_types_filter(auth_client, candidate, demand):
    # '王小明' 同时匹配 candidate (name) 与 offer/referral (candidate name),
    # 但 types=candidate 只应返回 candidate 组
    resp = auth_client.get(SEARCH_URL, {'q': '王小明', 'types': 'candidate'})
    data = resp.json()
    types = [g['type'] for g in data['groups']]
    assert types == ['candidate']


# ---------------------------------------------------------------------------
# limit 截断
# ---------------------------------------------------------------------------
def test_limit_truncation(auth_client, db):
    for i in range(7):
        Candidate.objects.create(
            name=f'批量候选人{i:02d}', phone=f'1390000000{i}'
        )
    resp = auth_client.get(SEARCH_URL, {'q': '批量候选人', 'limit': 3})
    grp = _group(resp.json(), 'candidate')
    assert grp['total'] == 7
    assert len(grp['items']) == 3


# ---------------------------------------------------------------------------
# 驼峰键校验
# ---------------------------------------------------------------------------
def test_camel_case_keys(auth_client, candidate, application, demand, position, interview, offer, referral):
    # q='王小明' 同时命中 candidate / offer / referral / interview (均关联 王小明)
    data = auth_client.get(SEARCH_URL, {'q': '王小明'}).json()
    # 顶层 totalGroups (snake total_groups → camel)
    assert 'totalGroups' in data
    assert isinstance(data['totalGroups'], int)
    assert 'took' in data and 'query' in data and 'groups' in data

    # referral: candidateName (candidate_name) + referrer.realName (real_name)
    rf = _group(data, 'referral')
    assert rf is not None and rf['total'] >= 1
    assert 'candidateName' in rf['items'][0]
    assert 'realName' in rf['items'][0]['referrer']

    # interview: scheduledAt (scheduled_at)
    iv = _group(data, 'interview')
    assert iv is not None and iv['total'] >= 1
    assert 'scheduledAt' in iv['items'][0]

    # offer: status (state → status)
    of = _group(data, 'offer')
    assert of is not None and of['total'] >= 1
    assert 'status' in of['items'][0]

    # demand: status (state → status) — 用其专属标题单独搜
    dd = auth_client.get(SEARCH_URL, {'q': '后端招聘需求'}).json()
    gd = _group(dd, 'demand')
    assert gd is not None and gd['total'] >= 1
    assert 'status' in gd['items'][0]

    # position: status (state → status) — 用其专属标题单独搜
    pp = auth_client.get(SEARCH_URL, {'q': '高级后端工程师'}).json()
    gp = _group(pp, 'position')
    assert gp is not None and gp['total'] >= 1
    assert 'status' in gp['items'][0]


# ---------------------------------------------------------------------------
# 响应结构
# ---------------------------------------------------------------------------
def test_response_structure(auth_client, candidate, application):
    data = auth_client.get(SEARCH_URL, {'q': '王小明'}).json()
    assert isinstance(data['query'], str)
    assert isinstance(data['took'], int)
    assert isinstance(data['totalGroups'], int)
    assert isinstance(data['groups'], list)
    for g in data['groups']:
        assert set(['type', 'total', 'items']).issubset(g.keys())
        assert isinstance(g['total'], int)
        assert isinstance(g['items'], list)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _group(data: dict, type_: str):
    for g in data.get('groups', []):
        if g['type'] == type_:
            return g
    return None

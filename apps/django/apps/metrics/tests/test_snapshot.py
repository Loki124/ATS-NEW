"""候选人快照测试 —— 验证真实 ORM 数据能被规则引擎按 source_path 取值。"""
import pytest

from apps.candidate.models import Candidate, CandidateFieldValue
from apps.metrics.services.candidate_snapshot import (
    build_candidate_snapshot,
    list_candidate_paths,
)
from apps.metrics.services.field_resolver import FieldResolverRegistry
from apps.metrics.services.metric_engine import MetricEngine

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _make_candidate(**kwargs):
    payload = {'name': '测试候选人', 'age': 30, 'phone': '13800138000'}
    payload.update(kwargs)
    return Candidate.objects.create(**payload)


def test_snapshot_exposes_basic_model_fields():
    c = _make_candidate(highest_education='本科', work_years=5)
    snap = build_candidate_snapshot(c.pk)
    assert snap['candidate']['age'] == 30
    assert snap['candidate']['name'] == '测试候选人'
    assert snap['candidate']['highest_education'] == '本科'


def test_snapshot_hides_sensitive_fields_by_default():
    """手机号/邮箱等敏感字段默认不进快照（对齐 field_acl 脱敏约定）。"""
    c = _make_candidate(email='a@b.com')
    snap = build_candidate_snapshot(c.pk)
    assert 'phone' not in snap['candidate']
    assert 'email' not in snap['candidate']


def test_snapshot_unknown_candidate_returns_empty():
    assert build_candidate_snapshot('not-exist') == {'candidate': {}}


def test_snapshot_expands_extra_json():
    """业务把结构化经历放进 extra 时，派生指标即可对真实数据生效。"""
    c = _make_candidate(extra={
        'workExperience': [
            {'company': 'A', 'start_date': '2020-01-01', 'end_date': '2021-01-01'},
            {'company': 'B', 'start_date': '2021-07-01', 'end_date': None},
        ]
    })
    snap = build_candidate_snapshot(c.pk)
    assert snap['candidate']['workExperience'][0]['company'] == 'A'
    # 解析器可直接取到嵌套数组
    assert FieldResolverRegistry.resolve(
        'candidate.workExperience.1.start_date', snap
    ) == '2021-07-01'


def test_snapshot_injects_candidate_field_values():
    c = _make_candidate()
    CandidateFieldValue.objects.create(candidate=c, field_key='custom_score', value=88)
    snap = build_candidate_snapshot(c.pk)
    assert snap['candidate']['custom_score'] == 88


def test_candidate_paths_contains_model_fields():
    paths = {p['path'] for p in list_candidate_paths()}
    assert 'candidate.age' in paths
    assert 'candidate.highest_education' in paths
    # 敏感字段不应出现在可引用清单
    assert not any(p.startswith('candidate.phone') for p in paths)


@pytest.mark.django_db
def test_end_to_end_rule_on_real_candidate():
    """真实闭环：候选人快照 → 原子指标 → 模板 → 执行（不再依赖示例数据）。"""
    from apps.metrics.models import AtomicMetric, MetricTemplate

    c = _make_candidate(age=35)
    metric = AtomicMetric.objects.create(
        name='年龄(快照测试)', source_path='candidate.age', data_type='number', unit='岁',
    )
    tpl = MetricTemplate.objects.create(
        name='年龄限制', atomic_metric=metric, operators=['GT', 'LT'],
    )
    snap = build_candidate_snapshot(c.pk)
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'GT', 'value': '30'}], snap,
    )
    assert result['pass'] is True
    assert result['steps'][0]['actual'] == 35


# ===== API =====

def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def test_api_snapshot_ok(auth_client):
    c = _make_candidate(age=28)
    resp = auth_client.get(f'{BASE}candidates/{c.pk}/snapshot/')
    assert resp.status_code == 200
    assert _unwrap(resp)['candidate']['age'] == 28


def test_api_snapshot_404_for_unknown(auth_client):
    resp = auth_client.get(f'{BASE}candidates/ghost/snapshot/')
    assert resp.status_code == 404


def test_api_candidate_fields(auth_client):
    resp = auth_client.get(BASE + 'candidate-fields/')
    assert resp.status_code == 200
    rows = _unwrap(resp)
    assert any(r['path'] == 'candidate.age' for r in rows)

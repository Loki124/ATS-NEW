"""业务触发点测试 —— 入池 / 筛选 / 评分 场景下规则的生效与阻断语义。"""
import pytest

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, MetricRule, MetricTemplate
from apps.metrics.services.rule_trigger import evaluate_scene, filter_candidates_by_scene

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _make_candidate(age: int = 35, name: str = '触发点候选人'):
    return Candidate.objects.create(name=name, age=age, phone='13900000009')


def _age_template(operators=None):
    metric = AtomicMetric.objects.create(
        name='触发点年龄', source_path='candidate.age', data_type='number', unit='岁',
    )
    return MetricTemplate.objects.create(
        name='触发点年龄模板', atomic_metric=metric, operators=operators or ['GT', 'LT'],
    )


def _rule(scene: str, value: str, *, action_type: str = 'DEDUCT', enabled: bool = True, template=None):
    return MetricRule.objects.create(
        name=f'规则-{scene}-{value}',
        scene=scene,
        conditions=[{
            'templateId': (template or _age_template()).pk,
            'operator': 'GT',
            'value': value,
        }],
        action_type=action_type,
        enabled=enabled,
    )


def test_no_rules_in_scene_passes():
    cand = _make_candidate()
    result = evaluate_scene('TALENT_POOL', cand.pk)
    assert result['pass'] is True
    assert result['blocked'] is False
    assert '无启用规则' in result['message']


def test_blocking_rule_failure_blocks():
    cand = _make_candidate(age=20)
    _rule('TALENT_POOL', '30', action_type='VETO')
    result = evaluate_scene('TALENT_POOL', cand.pk)
    assert result['pass'] is False
    assert result['blocked'] is True
    assert '不满足规则' in result['message']


def test_non_blocking_rule_failure_does_not_block():
    """安全默认：未开启阻断的规则不满足时仅记录，不阻断业务。"""
    cand = _make_candidate(age=20)
    _rule('TALENT_POOL', '30', action_type='DEDUCT')
    result = evaluate_scene('TALENT_POOL', cand.pk)
    assert result['pass'] is False
    assert result['blocked'] is False
    assert '已放行' in result['message']


def test_passing_rule_allows():
    cand = _make_candidate(age=35)
    _rule('TALENT_POOL', '30', action_type='VETO')
    result = evaluate_scene('TALENT_POOL', cand.pk)
    assert result['pass'] is True
    assert result['blocked'] is False


def test_disabled_rule_is_skipped():
    cand = _make_candidate(age=20)
    _rule('TALENT_POOL', '30', action_type='VETO', enabled=False)
    result = evaluate_scene('TALENT_POOL', cand.pk)
    assert result['evaluated'] == 0
    assert result['blocked'] is False


def test_rules_of_other_scene_not_applied():
    """场景隔离：入池规则不影响评分场景。"""
    cand = _make_candidate(age=20)
    _rule('TALENT_POOL', '30', action_type='VETO')
    result = evaluate_scene('SCORING', cand.pk)
    assert result['evaluated'] == 0


def test_unknown_candidate_not_blocked_but_flagged():
    _rule('FILTER', '30', action_type='VETO')
    result = evaluate_scene('FILTER', 'ghost-id')
    assert result['pass'] is False
    assert '不存在' in result['message']


def test_filter_candidates_by_scene():
    young = _make_candidate(age=20, name='年轻')
    senior = _make_candidate(age=40, name='资深')
    _rule('FILTER', '30', action_type='VETO')
    outcome = filter_candidates_by_scene('FILTER', [young.pk, senior.pk])
    assert str(senior.pk) in outcome['passedIds']
    assert str(young.pk) not in outcome['passedIds']
    assert outcome['rejected'][0]['candidateId'] == str(young.pk)


# ===== API =====

def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def test_api_evaluate_scene(auth_client):
    cand = _make_candidate(age=20)
    _rule('TALENT_POOL', '30', action_type='VETO')
    resp = auth_client.post(BASE + 'rules/evaluate-scene/', {
        'scene': 'TALENT_POOL', 'candidateId': str(cand.pk),
    }, format='json')
    assert resp.status_code == 200
    body = _unwrap(resp)
    assert body['blocked'] is True


def test_api_evaluate_scene_requires_params(auth_client):
    resp = auth_client.post(BASE + 'rules/evaluate-scene/', {}, format='json')
    assert resp.status_code == 400


def test_filter_task_returns_full_result():
    """异步任务（直接调用，不依赖 worker）：全量执行并返回 passedIds。"""
    from apps.metrics.tasks import filter_by_scene_task

    senior = _make_candidate(age=40, name='资深')
    young = _make_candidate(age=20, name='低龄')
    _rule('FILTER', '30', action_type='VETO')

    result = filter_by_scene_task('unit-test-task', 'FILTER')
    assert result['status'] == 'done'
    assert str(senior.pk) in result['passedIds']
    assert str(young.pk) not in result['passedIds']
    assert result['rejected'][0]['candidateId'] == str(young.pk)


def test_filter_endpoint_reports_scan_scope(auth_client):
    """同步端点必须暴露 scanned/total/truncated —— 避免静默截断。"""
    _make_candidate(age=40, name='范围内')
    _rule('FILTER', '30', action_type='VETO')
    resp = auth_client.post(BASE + 'rules/filter/', {'scene': 'FILTER'}, format='json')
    assert resp.status_code == 200
    body = _unwrap(resp)
    assert 'scanned' in body and 'total' in body and 'truncated' in body
    # 候选数远小于同步上限，不应被截断
    assert body['truncated'] is False
    assert body['scanned'] == body['total']


def test_talent_pool_entry_blocked_by_rule(auth_client):
    """集成：入池触发点真生效 —— 阻断型规则不满足时入池被拒（400）。"""
    cand = _make_candidate(age=20, name='低龄候选人')
    _rule('TALENT_POOL', '30', action_type='VETO')
    resp = auth_client.post('/api/v1/talent-pool/', {
        'candidate': str(cand.pk), 'source': 'DIRECT_IMPORT',
    }, format='json')
    assert resp.status_code == 400


def test_talent_pool_entry_allowed_when_rule_passes(auth_client):
    """集成：规则满足时入池正常放行。"""
    cand = _make_candidate(age=40, name='资深候选人')
    _rule('TALENT_POOL', '30', action_type='VETO')
    resp = auth_client.post('/api/v1/talent-pool/', {
        'candidate': str(cand.pk), 'source': 'DIRECT_IMPORT',
    }, format='json')
    assert resp.status_code in (200, 201)


def test_api_filter_without_ids_scans_candidates(auth_client):
    """不传 candidateIds 时自动扫描在库候选人（供列表页按规则筛选）。"""
    senior = _make_candidate(age=40, name='资深')
    young = _make_candidate(age=20, name='低龄')
    _rule('FILTER', '30', action_type='VETO')

    resp = auth_client.post(BASE + 'rules/filter/', {'scene': 'FILTER'}, format='json')
    assert resp.status_code == 200
    body = _unwrap(resp)
    assert str(senior.pk) in body['passedIds']
    assert str(young.pk) not in body['passedIds']


def test_candidate_list_supports_ids_filter(auth_client):
    """候选人列表支持 ids 白名单 —— 规则筛选结果集回传的落点。"""
    keep = _make_candidate(age=40, name='保留')
    drop = _make_candidate(age=20, name='排除')
    resp = auth_client.get('/api/v1/candidates/', {'ids': str(keep.pk)})
    assert resp.status_code == 200
    ids = [row['id'] for row in _unwrap(resp)]
    assert str(keep.pk) in ids
    assert str(drop.pk) not in ids


def test_api_filter_by_scene(auth_client):
    senior = _make_candidate(age=40, name='资深')
    _rule('FILTER', '30', action_type='VETO')
    resp = auth_client.post(BASE + 'rules/filter/', {
        'scene': 'FILTER', 'candidateIds': [str(senior.pk)],
    }, format='json')
    assert resp.status_code == 200
    assert str(senior.pk) in _unwrap(resp)['passedIds']

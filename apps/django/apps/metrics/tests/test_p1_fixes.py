"""P1 修复回归锁: Fix1(静默 except 补日志 + FAIL-not-500 语义保留) / Fix2(批量快照预取).

Fix1: metric_engine / candidate_snapshot 的静默 `except Exception: pass` 改为
      `except Exception as e: logger.warning(...)`, 但 FAIL / 跳过语义必须保留 —— 绝不 500。
Fix2: build_candidate_snapshot 内部委托新增的 build_candidate_snapshots 批量 IN 预取接口,
      rule_trigger.filter_candidates_by_scene / add_candidate.tasks.score_batch_task 复用预取,
      把逐候选 O(N) 快照查询降到 O(1)。
"""
import pytest
from unittest.mock import patch

from apps.candidate.models import Candidate
from apps.metrics.models import AtomicMetric, MetricTemplate
from apps.metrics.services.candidate_snapshot import (
    build_candidate_snapshot,
    build_candidate_snapshots,
)
from apps.metrics.services.metric_engine import MetricEngine


def _make_candidate(**kwargs):
    payload = {'name': '测试候选人', 'age': 30, 'phone': '13800138000'}
    payload.update(kwargs)
    return Candidate.objects.create(**payload)


@pytest.mark.django_db
def test_build_candidate_snapshots_equivalence_to_single():
    """Fix2 锁: 批量接口对单候选产出结构 == 原单候选接口 (行为零变化, 快照结构不变)."""
    c = _make_candidate(age=35, highest_education='本科')
    single = build_candidate_snapshot(c.pk)
    batch = build_candidate_snapshots([str(c.pk)])
    assert batch == {str(c.pk): single}
    assert batch[str(c.pk)]['candidate']['age'] == 35


@pytest.mark.django_db
def test_snapshot_build_failure_degrades_to_fail_not_500():
    """Fix1 锁: 候选快照组装异常必须在指标引擎内被捕获, 降级为 FAIL (绝不 500 / 不向外抛)."""
    metric = AtomicMetric.objects.create(
        name='年龄(P1容错)', source_path='candidate.age', data_type='number', unit='岁')
    tpl = MetricTemplate.objects.create(
        name='年龄限制', atomic_metric=metric, operators=['GT', 'LT'])

    def boom(cid, **kwargs):  # noqa: ANN001 - 模拟快照组装抛异常
        raise RuntimeError('injected snapshot failure')

    with patch(
        'apps.metrics.services.candidate_snapshot.build_candidate_snapshot',
        side_effect=boom,
    ):
        # 不应向外抛异常 (FAIL-not-500); 返回合法结果 dict 且整体 FAIL
        result = MetricEngine.evaluate_metric_condition(
            template_id=str(tpl.pk),
            context={'candidate_id': 'cand-xyz'},
            operator='GT',
            value='30',
        )
    assert isinstance(result, dict)
    assert result.get('pass') is False
    assert 'error' in result

"""简历解析结构化测试 —— 验证解析结果能落 extra 并驱动派生指标。"""
from datetime import date

import pytest

from apps.candidate.models import Candidate
from apps.metrics.models import DerivedMetric, MetricTemplate
from apps.metrics.services.candidate_snapshot import build_candidate_snapshot
from apps.metrics.services.metric_engine import MetricEngine
from apps.metrics.services.resume_struct import build_structured_extra, parse_period

pytestmark = pytest.mark.django_db


def test_parse_period_dot_format():
    start, end = parse_period('2018.07 - 2020.06')
    assert start == date(2018, 7, 1)
    assert end == date(2020, 6, 1)


def test_parse_period_full_iso():
    start, end = parse_period('2018-07-01 - 2020-06-30')
    assert start == date(2018, 7, 1)
    assert end == date(2020, 6, 30)


def test_parse_period_current_job_has_no_end():
    """在职（至今）→ end_date 为 None，MAX_GAP 会按今天计算。"""
    start, end = parse_period('2020.07 - 至今')
    assert start == date(2020, 7, 1)
    assert end is None


def test_parse_period_garbage_returns_none():
    assert parse_period('') == (None, None)
    assert parse_period(None) == (None, None)
    assert parse_period('不限') == (None, None)


def test_parse_period_swaps_reversed_range():
    start, end = parse_period('2020.06 - 2018.07')
    assert start == date(2018, 7, 1)
    assert end == date(2020, 6, 1)


def test_build_structured_extra():
    parsed = {
        'experiences': [
            {'period': '2018.01 - 2020.01', 'company': 'A公司', 'position': '工程师', 'summary': ''},
            {'period': '2020.07 - 至今', 'company': 'B公司', 'position': '高工', 'summary': ''},
        ],
        'educations': [
            {'period': '2014.09 - 2018.06', 'school': '某大学', 'major': '计算机', 'degree': '本科'},
        ],
    }
    extra = build_structured_extra(parsed)
    assert extra['workExperience'][0]['company'] == 'A公司'
    assert extra['workExperience'][0]['start_date'] == '2018-01-01'
    assert extra['workExperience'][1]['end_date'] is None  # 在职
    assert extra['education'][0]['degree'] == '本科'


def test_build_structured_extra_tolerates_empty():
    assert build_structured_extra({}) == {}
    assert build_structured_extra(None) == {}


def test_derived_metric_works_on_real_resume_data():
    """端到端：解析 → extra → 快照 → 派生指标（空窗期）→ 执行。

    这是本需求的核心价值：经历数据一旦落 extra，「空窗期 ≤ 6 个月」这类
    规则即可对**真实数据**生效，无需开发介入。
    """
    parsed = {
        'experiences': [
            {'period': '2018.01 - 2020.01', 'company': 'A公司', 'position': '工程师', 'summary': ''},
            {'period': '2020.07 - 至今', 'company': 'B公司', 'position': '高工', 'summary': ''},
        ],
        'educations': [
            {'period': '2014.09 - 2018.06', 'school': '某大学', 'major': '计算机', 'degree': '本科'},
        ],
    }
    cand = Candidate.objects.create(
        name='简历结构化候选人', phone='13900000002', age=30,
        extra=build_structured_extra(parsed),
    )
    snapshot = build_candidate_snapshot(cand.pk)
    assert snapshot['candidate']['workExperience'][0]['company'] == 'A公司'

    metric = DerivedMetric.objects.create(
        name='最大空窗期', calc_func='MAX_GAP',
        base_path='candidate.workExperience', data_type='number', unit='月',
    )
    tpl = MetricTemplate.objects.create(
        name='空窗期限制', derived_metric=metric, operators=['LTE', 'GT'],
    )

    # 两段间隔：2020-01-01 → 2020-07-01 = 6 个月 → ≤ 6 通过
    ok = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'LTE', 'value': '6'}], snapshot,
    )
    assert ok['pass'] is True, ok['steps'][0]
    assert ok['steps'][0]['actual'] == 6

    # 阈值收紧到 5 → 不通过（证明阈值可调、对真实数据生效）
    tight = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'LTE', 'value': '5'}], snapshot,
    )
    assert tight['pass'] is False


def test_highest_education_from_resume_data():
    """最高学历（按教育经历列表计算）对真实数据生效。"""
    parsed = {
        'educations': [
            {'period': '2014.09 - 2018.06', 'school': 'A大', 'major': '计算机', 'degree': '本科'},
            {'period': '2018.09 - 2021.06', 'school': 'B大', 'major': '软件', 'degree': '硕士'},
        ],
    }
    cand = Candidate.objects.create(
        name='学历候选人', phone='13900000003',
        extra=build_structured_extra(parsed),
    )
    snapshot = build_candidate_snapshot(cand.pk)

    metric = DerivedMetric.objects.create(
        name='最高学历', calc_func='HIGHEST_EDU',
        base_path='candidate.education', data_type='string',
    )
    tpl = MetricTemplate.objects.create(
        name='学历门槛', derived_metric=metric, operators=['EQ'],
    )
    result = MetricEngine.execute(
        [{'templateId': tpl.pk, 'operator': 'EQ', 'value': '硕士'}], snapshot,
    )
    assert result['pass'] is True
    assert result['steps'][0]['actual'] == '硕士'

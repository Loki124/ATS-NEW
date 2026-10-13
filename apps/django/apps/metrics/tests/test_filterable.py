"""filterable 红线元数据测试（ARCH §2.1/§2.2）。

覆盖：
  1. 迁移回填分类器 _classify_filterable：标量字段 True；JSON 路径 / 关系字段 /
     未知 entity 前缀 / 模型无该字段 -> False；
  2. attribute_fields_for 场景二分：row_filter 仅放行 filterable=True；
     evaluation 全部放行；未知场景显式抛错（不静默放行）；
  3. 保存期拦截：行级过滤场景引用 filterable=False 指标的属性条件，
     validate_scope_payload 拒绝保存（红线在保存期，而非运行期静默降级）。
"""
import importlib

import pytest

from apps.data_permission.attribute_fields import (
    SCENARIO_EVALUATION,
    SCENARIO_ROW_FILTER,
    attribute_fields_for,
)
from apps.data_permission.expr_compiler import validate_scope_payload
from apps.metrics.models import AtomicMetric


def _load_migration_module():
    return importlib.import_module(
        'apps.metrics.migrations.0031_atomicmetric_filterable'
    )


# ---------------------------------------------------------------------------
# 1. 回填分类器
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('source_path,expected', [
    ('candidate.age', True),                    # 标量数值
    ('candidate.name', True),                   # 标量文本
    ('demand.headcount', True),                 # 跨实体标量
    ('candidate.workExperience.0.company', False),  # 数组下标 JSON 路径
    ('candidate.resume.education', False),      # 嵌套 JSON 路径
    ('candidate.referrer', False),              # 关系字段 (FK)
    ('unknown_entity.field', False),            # 未知 entity 前缀
    ('candidate.no_such_field', False),         # 模型无该字段
    ('candidate', False),                       # 非两段形态
    ('', False),                                # 空路径
])
def test_classify_filterable(source_path, expected):
    mig = _load_migration_module()
    assert mig._classify_filterable(source_path) is expected


# ---------------------------------------------------------------------------
# 2. 场景二分
# ---------------------------------------------------------------------------

def _set_age_filterable(value: bool):
    """把种子数据里 candidate.age 指标的 filterable 置为指定值.

    种子回填会建 candidate.age 指标 (filterable=True), 与用例自建行同路径时
    目录映射后者胜出、断言失真; 直接删除又撞 MetricTemplate protected FK。
    故用 update() 翻转种子行标志 (age 是数值标量, 恒定出现在目录中)。
    """
    AtomicMetric.objects.filter(source_path='candidate.age').update(filterable=value)


@pytest.mark.django_db
def test_attribute_fields_row_filter_excludes_non_filterable():
    """row_filter 场景: filterable=False 的原子指标不下发."""
    _set_age_filterable(False)
    paths = [f['sourcePath'] for f in attribute_fields_for('candidate', scenario=SCENARIO_ROW_FILTER)]
    assert 'candidate.age' not in paths


@pytest.mark.django_db
def test_attribute_fields_evaluation_includes_all():
    """evaluation 场景: 不受 filterable 约束, 全部放行."""
    _set_age_filterable(False)
    paths = [f['sourcePath'] for f in attribute_fields_for('candidate', scenario=SCENARIO_EVALUATION)]
    assert 'candidate.age' in paths


@pytest.mark.django_db
def test_attribute_fields_default_scenario_is_row_filter():
    """缺省 scenario = row_filter (数据权限消费方向)."""
    _set_age_filterable(False)
    paths = [f['sourcePath'] for f in attribute_fields_for('candidate')]
    assert 'candidate.age' not in paths


def test_attribute_fields_unknown_scenario_raises():
    """未知场景显式抛错, 不静默按某一场景放行."""
    with pytest.raises(ValueError):
        attribute_fields_for('candidate', scenario='typo_scene')


@pytest.mark.django_db
def test_attribute_fields_carries_filterable_flag():
    """目录下发项携带 filterable 元数据, 前端可标注「仅点评估」."""
    _set_age_filterable(True)
    fields = attribute_fields_for('candidate', scenario=SCENARIO_EVALUATION)
    age = next(f for f in fields if f['sourcePath'] == 'candidate.age')
    assert age['filterable'] is True


# ---------------------------------------------------------------------------
# 3. 保存期拦截 (红线: 配置越界在保存期拒绝, 非运行期降级)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_validate_rejects_non_filterable_attribute_condition():
    """行级过滤场景引用 filterable=False 指标的属性条件 -> 保存期拒绝."""
    _set_age_filterable(False)
    payload = {'expr': '', 'groups': [{'expr': '', 'conditions': [
        {'kind': 'attribute', 'field': 'candidate.age', 'operator': 'GT', 'value': 25},
    ]}]}
    reason = validate_scope_payload(payload, 'candidate')
    assert reason is not None
    assert 'candidate.age' in reason


@pytest.mark.django_db
def test_validate_accepts_filterable_attribute_condition():
    """filterable=True 的属性条件正常通过保存期校验."""
    _set_age_filterable(True)
    payload = {'expr': '', 'groups': [{'expr': '', 'conditions': [
        {'kind': 'attribute', 'field': 'candidate.age', 'operator': 'GT', 'value': 25},
    ]}]}
    assert validate_scope_payload(payload, 'candidate') is None

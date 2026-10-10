"""指标编号测试 —— 编号由系统自动生成、唯一、且不可被写入端点篡改。

前缀约定：AM=原子指标 / DM=派生指标 / MT=指标模板。
范式沿用 campus_control 的规则编号补号测试（事务内取最大序号 +1）。
"""
import pytest

from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate

pytestmark = pytest.mark.django_db


def _mk_atomic(name: str) -> AtomicMetric:
    return AtomicMetric.objects.create(
        name=name, source_path=f'candidate.{name}', data_type='string',
    )


def test_code_prefix_by_entity():
    """三类实体各用自己的前缀，互不串号。"""
    a = _mk_atomic('编号测试原子')
    d = DerivedMetric.objects.create(
        name='编号测试派生', calc_func='MAX_GAP', base_path='candidate.workExperience',
    )
    t = MetricTemplate.objects.create(
        name='编号测试模板', atomic_metric=a, operators=['EQ'],
    )
    assert a.code.startswith('AM')
    assert d.code.startswith('DM')
    assert t.code.startswith('MT')


def test_code_auto_increments_and_unique():
    """连续新建时序号递增且不重复。"""
    a1 = _mk_atomic('编号自增一')
    a2 = _mk_atomic('编号自增二')
    assert int(a1.code[2:]) + 1 == int(a2.code[2:])
    assert len({a1.code, a2.code}) == 2


def test_code_read_only_on_update():
    """编号不可更改：即便显式赋值 code 也以库中原值为准（模型层 editable=False）。"""
    a = _mk_atomic('编号只读验证')
    original = a.code
    a.code = 'AM9999'
    a.save()
    a.refresh_from_db()
    assert a.code == original


def test_next_code_is_scoped_by_prefix():
    """回归：取号必须按前缀隔离。

    若对全表 order_by('-code')，末行通常是别的前缀（'D' > 'A'，DM 压过 AM），
    前缀不匹配会退回 seq=0 → 返回 AM0001 → 撞上已存在的 AM0001 唯一约束。
    """
    from apps.metrics.models import AtomicMetric, DerivedMetric, MetricTemplate

    AtomicMetric.objects.create(
        name='编号回归-原子', source_path='reg.atomic.a', data_type='string', status='enabled',
    )
    # 制造「别的前缀序号更大」的场景：DM 与 MT 的序号都远超 AM
    for i in range(3):
        DerivedMetric.objects.create(
            name=f'编号回归-派生{i}', calc_func='count', base_path=f'reg.derived{i}',
            data_type='number', status='enabled', code=f'DM009{i}',
        )
    MetricTemplate.objects.create(
        name='编号回归-模板', atomic_metric=AtomicMetric.objects.first(),
        status='enabled', code='MT0088',
    )

    new_atomic = AtomicMetric.objects.create(
        name='编号回归-原子2', source_path='reg.atomic.b', data_type='string', status='enabled',
    )
    assert new_atomic.code.startswith('AM') and new_atomic.code != 'AM0001', \
        f'应接着 AM 序列递增，实际 {new_atomic.code}'

    codes = list(AtomicMetric.objects.values_list('code', flat=True))
    assert len(codes) == len(set(codes))

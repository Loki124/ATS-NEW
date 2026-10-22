"""需求字段结构对齐《需求字段规范》穿透测试 (2026-10-12)。

锁定 dynamic_field/migrations/0024_align_demand_fields_to_spec 落地后的 DB 形态:
  - 系统字段标签对齐(岗位职责/任职资格/需求主责人/需求职级/需求紧急程度 + 5 个新增);
  - 12 个自定义字段就位;
  - 规范 5 分类分组归类;
  - 0025 软删历史遗留行后, 活跃字段集合与规范 key 全集严格一致(双向);
  - DemandCreateSerializer 收新列; DemandDetailSerializer 按 state 派生审批状态。
"""
import pytest

from apps.demand.serializers import (
    DemandCreateSerializer,
    DemandDetailSerializer,
)
from apps.dynamic_field.models import DynamicField
from apps.dynamic_field.system_fields import DEMAND_SPEC_FIELD_KEYS


def _demand_field_map():
    """resource=Demand 的 field_key → (label, is_system, group_name)。"""
    return {
        f.field_key: (f.label, f.is_system, f.group_name)
        for f in DynamicField.objects.filter(resource='Demand', deleted_at__isnull=True)
    }


@pytest.mark.django_db
def test_system_field_labels_aligned_to_spec():
    m = _demand_field_map()
    # 复用列仅改标签(field_key 不变)
    assert m['jd'][0] == '岗位职责'
    assert m['requirements'][0] == '任职资格'
    assert m['hr'][0] == '需求主责人'
    assert m['level'][0] == '需求职级'
    assert m['priority'][0] == '需求紧急程度'
    # 均为系统字段
    for k in ('jd', 'requirements', 'hr', 'level', 'priority'):
        assert m[k][1] is True


@pytest.mark.django_db
def test_new_system_fields_present():
    m = _demand_field_map()
    for key, label in [
        ('talent_level', '人才层级'), ('talent_nature', '职位性质'),
        ('date_range', '需求起止日期'), ('sharers', '需求共享人'),
        ('approval_status', '审批状态'),
    ]:
        assert key in m, f'缺少系统字段 {key}'
        assert m[key][0] == label
        assert m[key][1] is True


@pytest.mark.django_db
def test_custom_fields_present_and_not_system():
    m = _demand_field_map()
    custom = {
        'external_short_name': '对外简称', 'position_sequence': '岗位序列',
        'work_location': '工作地点', 'salary_range': '薪资范围',
        'experience_requirement': '经验要求', 'education_requirement': '学历要求',
        'expected_completion_date': '期望完成日期', 'hrbp': 'HRBP',
        'hiring_manager': '用人经理', 'hiring_manager_superior': '用人经理上级',
        'probation_assessment_goal': '试用期考核目标', 'demand_confirmation_form': '需求确认表',
    }
    for key, label in custom.items():
        assert key in m, f'缺少自定义字段 {key}'
        assert m[key][0] == label
        assert m[key][1] is False  # 自定义字段非系统


@pytest.mark.django_db
def test_fields_grouped_by_spec_category():
    m = _demand_field_map()
    assert m['jd'][2] == 'JD信息'
    assert m['title'][2] == 'JD信息'
    assert m['headcount'][2] == '基本信息'
    assert m['talent_nature'][2] == '基本信息'
    assert m['hr'][2] == '负责人信息'
    assert m['sharers'][2] == '负责人信息'
    assert m['hrbp'][2] == '负责人信息'
    assert m['probation_assessment_goal'][2] == '附件信息'
    assert m['demand_confirmation_form'][2] == '附件信息'
    assert m['code'][2] == '其他信息'
    assert m['state'][2] == '其他信息'
    assert m['approval_status'][2] == '其他信息'


@pytest.mark.django_db
def test_active_field_set_exactly_matches_spec():
    """活跃字段集合与规范 key 全集严格一致(双向断言)。

    测试库由全部迁移(含 0024 seed + 0025 软删残留)构建, 故本断言同时锁定:
    0024 漏 seed / 0025 漏删 / system_fields.DEMAND_SPEC_FIELD_KEYS 与迁移内联清单漂移。
    """
    m = _demand_field_map()
    active = set(m.keys())
    expected = set(DEMAND_SPEC_FIELD_KEYS)
    assert active == expected, (
        f'多余字段: {sorted(active - expected)}; 缺失字段: {sorted(expected - active)}'
    )


@pytest.mark.django_db
def test_create_serializer_accepts_new_columns(department):
    s = DemandCreateSerializer(data={
        'title': 'X', 'department': department.id, 'headcount': 1,
        'talent_level': '高级', 'talent_nature': 'FULLTIME',
        'date_range': ['2026-01-01T00:00:00Z', '2026-06-30T00:00:00Z'],
        'sharers': ['u1', 'u2'],
    })
    assert s.is_valid(), s.errors
    assert s.validated_data['talent_nature'] == 'FULLTIME'
    assert s.validated_data['sharers'] == ['u1', 'u2']


@pytest.mark.django_db
def test_detail_serializer_derives_approval_status():
    from apps.demand.models import Demand
    # headcount/filled_count 必填: 详情序列化器的 headcount_remaining 会做减法,
    # 内存对象不设值会 None - int 崩溃 (与生产 DB 行不同, 那里列有默认值).
    d = Demand(state='PENDING', approval_status='', headcount=1, filled_count=0)
    assert DemandDetailSerializer(d).data['approval_status'] == 'PENDING'
    d2 = Demand(state='DRAFT', approval_status='APPROVED', headcount=1, filled_count=0)
    assert DemandDetailSerializer(d2).data['approval_status'] == 'APPROVED'
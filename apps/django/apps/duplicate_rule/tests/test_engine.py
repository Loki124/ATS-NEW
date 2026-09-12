"""查重规则判定参考实现（services.compare）测试

守住三类语义：
1. 标量查重项：忽略空格 / 连字符 / 大小写
2. 经历类查重项：任一条目关键字段完全一致即命中
3. 规则条件：ALL=全部一致；ANY=任意 N 项一致；停用规则不参与判定
4. 空值不得判为重复（防误合并）
"""
import pytest

from apps.duplicate_rule.models import DuplicateRule
from apps.duplicate_rule.services import compare, field_matches, rule_matches

pytestmark = pytest.mark.django_db


def make_rule(name='测试规则', logic='ALL', any_count=1, items=None, enabled=True):
    return DuplicateRule.objects.create(
        name=name,
        condition_logic=logic,
        any_count=any_count,
        items=items or [{'key': 'phone', 'strength': 'MEDIUM'}],
        is_enabled=enabled,
        is_system=False,
    )


# ============================================================
# field_matches：标量
# ============================================================
@pytest.mark.parametrize(
    'left,right',
    [
        ('138 0013 8000', '13800138000'),
        ('138-0013-8000', '13800138000'),
        ('A@Example.com', 'a@example.com'),
        ('张三', '张三'),
    ],
)
def test_scalar_fields_ignore_separators_and_case(left, right):
    assert field_matches('phone', left, right) is True


def test_scalar_fields_differ_when_values_differ():
    assert field_matches('phone', '13800138000', '13800138001') is False


@pytest.mark.parametrize('empty', [None, '', []])
def test_empty_values_never_match(empty):
    """任一侧为空都不得判为重复 —— 否则空值会把所有候选人判成重复。"""
    assert field_matches('phone', empty, '13800138000') is False
    assert field_matches('phone', '13800138000', empty) is False


# ============================================================
# field_matches：经历类
# ============================================================
def test_experience_matches_on_any_single_entry():
    left = {'work_experience': [
        {'company': '腾讯', 'start_date': '2020-01', 'end_date': '2022-01', 'title': 'PM'},
        {'company': '字节', 'start_date': '2018-01', 'end_date': '2020-01', 'title': 'RD'},
    ]}
    right = {'work_experience': [
        {'company': '字节', 'start_date': '2018-01', 'end_date': '2020-01', 'title': 'RD'},
    ]}
    assert field_matches('work_experience', left['work_experience'], right['work_experience']) is True


def test_experience_differs_when_title_differs():
    left = [{'company': '腾讯', 'start_date': '2020-01', 'end_date': '2022-01', 'title': 'PM'}]
    right = [{'company': '腾讯', 'start_date': '2020-01', 'end_date': '2022-01', 'title': 'RD'}]
    assert field_matches('work_experience', left, right) is False


def test_empty_experience_list_does_not_match():
    assert field_matches('work_experience', [], [{'company': '腾讯'}]) is False


# ============================================================
# rule_matches / compare
# ============================================================
def test_all_logic_requires_every_item():
    rule = make_rule(
        logic='ALL',
        items=[
            {'key': 'phone', 'strength': 'MEDIUM'},
            {'key': 'name', 'strength': 'WEAK'},
        ],
    )
    same = rule_matches(rule, {'phone': '13800138000', 'name': '张三'},
                        {'phone': '13800138000', 'name': '张三'})
    assert same['matched'] is True
    assert same['miss_keys'] == []

    partial = rule_matches(rule, {'phone': '13800138000', 'name': '张三'},
                           {'phone': '13800138000', 'name': '李四'})
    assert partial['matched'] is False
    assert partial['miss_keys'] == ['name']


def test_any_logic_hits_at_threshold():
    rule = make_rule(
        logic='ANY', any_count=2,
        items=[
            {'key': 'phone', 'strength': 'MEDIUM'},
            {'key': 'email', 'strength': 'MEDIUM'},
            {'key': 'name', 'strength': 'WEAK'},
        ],
    )
    one_hit = rule_matches(rule, {'phone': '13800138000', 'email': 'a@b.com', 'name': '张三'},
                           {'phone': '13800138000', 'email': 'x@y.com', 'name': '李四'})
    assert one_hit['matched'] is False
    assert one_hit['hit_keys'] == ['phone']

    two_hits = rule_matches(rule, {'phone': '13800138000', 'email': 'a@b.com', 'name': '张三'},
                            {'phone': '13800138000', 'email': 'a@b.com', 'name': '李四'})
    assert two_hits['matched'] is True
    assert two_hits['hit_labels'] == ['手机号', '邮箱']


def test_compare_reports_hit_rules_and_skips_disabled():
    make_rule(name='启用规则', items=[{'key': 'id_card', 'strength': 'STRONG'}], enabled=True)
    make_rule(name='停用规则', items=[{'key': 'id_card', 'strength': 'STRONG'}], enabled=False)

    result = compare({'id_card': '110101199001011234'}, {'id_card': '110101199001011234'})
    assert result['is_duplicate'] is True
    assert [r['rule_name'] for r in result['matched_rules']] == ['启用规则']
    assert result['evaluated_rules'] == 1, '停用规则不得参与判定'


def test_compare_returns_clean_when_no_rule_hits():
    make_rule(name='仅手机号', items=[{'key': 'phone', 'strength': 'MEDIUM'}])
    result = compare(
        {'phone': '13800138000', 'name': '张三'},
        {'phone': '13900139000', 'name': '李四'},
    )
    assert result['is_duplicate'] is False
    assert result['matched_rules'] == []
    assert result['evaluated_rules'] == 1


def test_compare_with_empty_payload_is_never_duplicate():
    """空简历（全无字段）不得命中任何规则。"""
    make_rule(name='全字段规则', items=[
        {'key': 'phone', 'strength': 'MEDIUM'},
        {'key': 'name', 'strength': 'WEAK'},
    ])
    result = compare({}, {})
    assert result['is_duplicate'] is False

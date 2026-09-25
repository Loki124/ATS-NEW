"""P1-A：指标规则校验链单元测试（规则级子集 V01–V10 / V16）。

注意：本测试刻意**不传 templateId**，使 DB 相关的模板存在性 / 运算符白名单校验
（V04/V07）被安全跳过，从而在无 DB 或 DB 不可用环境下也能稳定验证纯逻辑
（名称 / 逻辑枚举 / 运算符全局合法 / BETWEEN / IN / action_type）。
DB 相关门在 serializer 集成测试与 admin 路径中覆盖。
"""
from django.test import TestCase

from apps.metrics.services.rule_validators import validate_metric_rule


def _rule(name='年龄规则', scene='FILTER', logic='AND', conditions=None,
          blocking=False, action_type=None):
    return {
        'name': name,
        'scene': scene,
        'logic': logic,
        'conditions': conditions if conditions is not None else [],
        'blocking': blocking,
        'action_type': action_type,
    }


class ValidateMetricRuleTest(TestCase):
    def test_passes_valid_rule(self):
        rule = _rule(conditions=[{'operator': 'GT', 'value': 30}])
        self.assertEqual(validate_metric_rule(rule), [])

    def test_v01_empty_name(self):
        rule = _rule(name='', conditions=[{'operator': 'GT', 'value': 30}])
        self.assertTrue(any('名称' in e for e in validate_metric_rule(rule)))

    def test_v01_name_too_long(self):
        rule = _rule(name='x' * 129, conditions=[{'operator': 'GT', 'value': 30}])
        self.assertTrue(any('长度' in e for e in validate_metric_rule(rule)))

    def test_v02_no_conditions(self):
        rule = _rule(conditions=[])
        self.assertTrue(any('条件' in e for e in validate_metric_rule(rule)))

    def test_v03_condition_not_dict(self):
        rule = _rule(conditions=['not-a-dict'])
        self.assertTrue(any('格式不正确' in e for e in validate_metric_rule(rule)))

    def test_v05_bad_logic(self):
        rule = _rule(logic='XOR', conditions=[{'operator': 'GT', 'value': 30}])
        self.assertTrue(any('逻辑' in e for e in validate_metric_rule(rule)))

    def test_v06_bad_operator(self):
        rule = _rule(conditions=[{'operator': 'BADOP', 'value': 30}])
        self.assertTrue(any('运算符不合法' in e for e in validate_metric_rule(rule)))

    def test_v09_between_min_gt_max(self):
        rule = _rule(conditions=[{
            'operator': 'BETWEEN', 'meta': {'min': 60, 'max': 18},
        }])
        self.assertTrue(any('最小值不能大于' in e for e in validate_metric_rule(rule)))

    def test_v09_between_missing_min(self):
        rule = _rule(conditions=[{
            'operator': 'BETWEEN', 'meta': {'max': 18},
        }])
        self.assertTrue(any('必须包含 min' in e for e in validate_metric_rule(rule)))

    def test_v09_between_non_numeric(self):
        rule = _rule(conditions=[{
            'operator': 'BETWEEN', 'meta': {'min': 'abc', 'max': 18},
        }])
        self.assertTrue(any('合法数字' in e for e in validate_metric_rule(rule)))

    def test_v10_in_empty(self):
        rule = _rule(conditions=[{'operator': 'IN', 'value': []}])
        self.assertTrue(any('非空数组' in e for e in validate_metric_rule(rule)))

    def test_v10_in_has_empty_element(self):
        rule = _rule(conditions=[{'operator': 'IN', 'value': ['a', '']}])
        self.assertTrue(any('非空数组' in e for e in validate_metric_rule(rule)))

    def test_v08_bad_action_type(self):
        rule = _rule(action_type='WRONG',
                     conditions=[{'operator': 'GT', 'value': 30}])
        self.assertTrue(any('动作类型' in e for e in validate_metric_rule(rule)))

    def test_v16_mutex_blocking_skeleton_no_db(self):
        # 无 DB 环境下互斥硬查被跳过，blocking=True 不应崩溃且返回空（无其它错误）
        rule = _rule(blocking=True,
                     conditions=[{'operator': 'GT', 'value': 30}])
        self.assertEqual(validate_metric_rule(rule), [])

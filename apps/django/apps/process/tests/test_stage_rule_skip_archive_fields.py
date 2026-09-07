"""阶段配置规则组件 — StageRule.skip_rules / archive_rules 字段验证。

- serializer 暴露两个新字段（无需 DB）
- model 层 skip_rules / archive_rules 可写可读（roundtrip）
"""
from __future__ import annotations

from django.test import TestCase

from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
)
from apps.process.serializers import StageRuleSerializer


def _make_rule() -> StageRule:
    process = RecruitmentProcess.objects.create(
        code='W_SKIPARCH', name='跳过归档测试流程',
        current_version='V1.0', version_seq=1, is_latest=True,
    )
    stage = RecruitmentStage.objects.create(
        code='P_SKIPARCH', name='跳过归档测试阶段', stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(process=process, stage=stage, order=0)
    return StageRule.objects.create(link=link)


class StageRuleSkipArchiveSerializerTest(TestCase):
    """serializer.Meta.fields 必须暴露 skip_rules / archive_rules"""

    def test_serializer_exposes_skip_and_archive_rules(self):
        fields = StageRuleSerializer().fields
        self.assertIn('skip_rules', fields)
        self.assertIn('archive_rules', fields)
        # 应为可写 JSON 字段（非 read_only）
        self.assertNotIn('skip_rules', StageRuleSerializer.Meta.read_only_fields)
        self.assertNotIn('archive_rules', StageRuleSerializer.Meta.read_only_fields)


class StageRuleSkipArchiveRoundtripTest(TestCase):
    """model 层 skip_rules / archive_rules 可写可读"""

    def test_skip_rules_roundtrip(self):
        rule = _make_rule()
        skip_rules = [
            {
                'id': 'sk_1', 'name': '跳过1', 'enabled': True, 'scope': 'NEW_ONLY',
                'expression': '(1 or 2) and 3',
                'items': [
                    {
                        'id': 'ci_1', 'item_seq': 1, 'condition_type': 'CANDIDATE',
                        'field': 'HIGHEST_EDU', 'operator': 'IN',
                        'value': ['本科', '硕士'], 'stage_name': None,
                        'stage_statuses': [], 'auto_filter_inactive_users': False,
                    }
                ],
                'action': 'SKIP',
            }
        ]
        rule.skip_rules = skip_rules
        rule.save()
        rule.refresh_from_db()
        self.assertEqual(rule.skip_rules, skip_rules)

    def test_archive_rules_roundtrip(self):
        rule = _make_rule()
        archive_rules = [
            {
                'id': 'ar_1', 'name': '30天归档', 'enabled': True, 'scope': 'ALL',
                'expression': '1',
                'items': [
                    {
                        'id': 'ci_2', 'item_seq': 1, 'condition_type': 'DEMAND',
                        'field': 'DEMAND_LEVEL', 'operator': 'IN',
                        'value': ['P6', 'P7'], 'stage_name': None,
                        'stage_statuses': [], 'auto_filter_inactive_users': False,
                    }
                ],
                'lock_days': 30, 'extend_days': 0, 'effective_scope': 'ALL',
            }
        ]
        rule.archive_rules = archive_rules
        rule.save()
        rule.refresh_from_db()
        self.assertEqual(rule.archive_rules, archive_rules)

    def test_default_is_empty_list(self):
        rule = _make_rule()
        rule.refresh_from_db()
        self.assertEqual(rule.skip_rules, [])
        self.assertEqual(rule.archive_rules, [])

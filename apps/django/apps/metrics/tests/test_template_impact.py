"""LIFE-2：指标模板受影响规则枚举服务测试（事前披露）。

覆盖：
    - 进入条件（ORM）+ 跳过规则（JSON）均被正确枚举，total == 2
    - entry_conditions / stage_rules 字段正确（rule_id / stage_name / rule_type / process_name）
    - 不引用该模板的 ConditionItem / StageRule 不出现在结果中
    - 软删的 ConditionItem（deleted_at 已置）不计入（真实可靠，不假绿）
    - 模板不存在时抛出 MetricTemplate.DoesNotExist（视图层据此返回 404）
"""
from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from nanoid import generate as nanoid_generate

from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.metrics.models import (
    AtomicMetric,
    MetricDataType,
    MetricTemplate,
)
from apps.metrics.services.template_impact import get_template_affected_rules
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageRule,
)


def _new_id() -> str:
    return nanoid_generate(size=21)


OTHER_FIELD = 'other-template-id'


class TemplateImpactTest(TestCase):
    def setUp(self) -> None:
        # 1 个启用模板 T（引用 1 个原子指标）
        am = AtomicMetric.objects.create(
            name='tst_life2_atomic', source_path='candidate.age',
            data_type=MetricDataType.NUMBER, status='enabled',
        )
        self.template = MetricTemplate.objects.create(
            name='tst_life2_template', atomic_metric=am,
            operators=['GT', 'LT'], status='enabled', description='',
        )
        self.tid = str(self.template.id)

        # 流程 / 阶段 / 关联
        self.process = RecruitmentProcess.objects.create(
            code=_new_id()[:12], name='tst_life2_流程',
            current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
        )
        self.stage = RecruitmentStage.objects.create(
            code=_new_id()[:10], name='tst_life2_阶段', stage_type='SCREEN',
        )
        self.link = ProcessStageLink.objects.create(
            process=self.process, stage=self.stage, order=1,
        )

        # 进入条件规则（ORM）
        self.rule = EntryConditionRule.objects.create(
            link=self.link, process_id=str(self.process.id),
            workflow_version='V1.0', rule_name='tst_life2_进入规则',
        )
        # 引用 T 的 METRIC 条件项（item_seq 在规则内须唯一）
        ConditionItem.objects.create(
            rule=self.rule, item_seq=1, condition_type='METRIC',
            field=self.tid, operator='GT', value=18,
        )
        # 不引用 T 的条件项（field 为其他值）—— 应被排除
        ConditionItem.objects.create(
            rule=self.rule, item_seq=2, condition_type='METRIC',
            field=OTHER_FIELD, operator='EQ', value=1,
        )
        # 引用 T 但已软删的条件项 —— 应被排除
        deleted_item = ConditionItem.objects.create(
            rule=self.rule, item_seq=3, condition_type='METRIC',
            field=self.tid, operator='GT', value=99,
        )
        deleted_item.deleted_at = timezone.now()
        deleted_item.save(update_fields=['deleted_at'])

        # 跳过规则（JSON）：skip_rules 引用 T（METRIC 项）+ 一条无关 STAGE_STATUS 项
        StageRule.objects.create(
            link=self.link,
            skip_rules=[{
                'id': 'skip-1',
                'name': 'tst_life2_跳过规则',
                'enabled': True,
                'scope': 'ALL',
                'expression': '1',
                'action': 'SKIP',
                'items': [
                    {'condition_type': 'METRIC', 'field': self.tid,
                     'operator': 'EQ', 'value': 10},
                    {'condition_type': 'STAGE_STATUS', 'field': 'stage',
                     'operator': 'EQ', 'value': 'ENTERED'},
                ],
            }],
        )

        # 不引用 T 的另一条 StageRule（不同 link）—— 应被排除
        other_stage = RecruitmentStage.objects.create(
            code=_new_id()[:10], name='tst_life2_阶段2', stage_type='INTERVIEW',
        )
        other_link = ProcessStageLink.objects.create(
            process=self.process, stage=other_stage, order=2,
        )
        StageRule.objects.create(
            link=other_link,
            skip_rules=[{
                'id': 'skip-other',
                'name': 'tst_life2_无关跳过规则',
                'enabled': True,
                'scope': 'ALL',
                'expression': '1',
                'action': 'SKIP',
                'items': [
                    {'condition_type': 'METRIC', 'field': OTHER_FIELD,
                     'operator': 'EQ', 'value': 5},
                ],
            }],
        )

    def test_enumerates_referencing_rules(self) -> None:
        data = get_template_affected_rules(self.tid)
        self.assertEqual(data['template_id'], self.tid)
        self.assertEqual(data['template_name'], self.template.name)
        self.assertEqual(data['template_status'], 'enabled')
        # 进入条件 1 条 + 跳过规则 1 条
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['entry_conditions']), 1)
        self.assertEqual(len(data['stage_rules']), 1)

        entry = data['entry_conditions'][0]
        self.assertEqual(entry['rule_id'], str(self.rule.id))
        self.assertEqual(entry['rule_name'], self.rule.rule_name)
        self.assertEqual(entry['rule_status'], self.rule.status)
        self.assertEqual(entry['expression'], self.rule.expression)
        self.assertEqual(entry['operator'], 'GT')
        self.assertEqual(entry['value'], 18)
        self.assertEqual(entry['process_id'], str(self.process.id))
        self.assertEqual(entry['process_name'], self.process.name)
        self.assertEqual(entry['stage_id'], str(self.stage.id))
        # stage_name 优先取 custom_name（此处为空）→ 回退 stage.name
        self.assertEqual(entry['stage_name'], self.stage.name)

        stage = data['stage_rules'][0]
        self.assertEqual(stage['rule_type'], 'skip')
        self.assertEqual(stage['rule_name'], 'tst_life2_跳过规则')
        self.assertTrue(stage['rule_enabled'])
        self.assertEqual(stage['item_id'], 0)
        self.assertEqual(stage['operator'], 'EQ')
        self.assertEqual(stage['value'], 10)
        self.assertEqual(stage['process_name'], self.process.name)
        self.assertEqual(stage['stage_name'], self.stage.name)

    def test_excludes_non_referencing_and_soft_deleted(self) -> None:
        data = get_template_affected_rules(self.tid)
        # 进入条件仅含引用 T 的项；OTHER_FIELD 项与软删项均不出现
        entry_rule_ids = {e['item_id'] for e in data['entry_conditions']}
        self.assertEqual(len(entry_rule_ids), 1)
        # 跳过规则仅含引用 T 的 skip-1；skip-other 不出现
        stage_rule_ids = {s['rule_id'] for s in data['stage_rules']}
        self.assertEqual(stage_rule_ids, {'skip-1'})
        # total 严格为 2，证明无关项/软删项均被排除
        self.assertEqual(data['total'], 2)

    def test_template_not_found_raises(self) -> None:
        from apps.metrics.models import MetricTemplate
        with self.assertRaises(MetricTemplate.DoesNotExist):
            get_template_affected_rules('00000000-0000-0000-0000-000000000000')


# ============================================================================
# LIFE-2 HTTP 层集成测试（新增，不改任何业务代码）
# ----------------------------------------------------------------------------
# 鉴权沿用项目既有全局 auth_client fixture（tests/fixtures_common: super_user
# + Bearer JWT），与同目录 test_api.py / test_envelope.py 完全一致；fixture 的
# 必填字段照搬本文件 TemplateImpactTest.setUp 已验证可跑通的组合。
# 覆盖：路由注册、success_response 信封（code==0 / success==True）、
# drf-camel-case 字段转换（snake→camelCase）、404 返回。
# ============================================================================
import pytest

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _build_template_with_reference():
    """构造一个被引用的指标模板 T，并挂 1 条引用它的进入条件 + 1 条引用它的跳过规则。

    必填字段照搬本文件 setUp 中已验证可跑通的组合，确保能真实落库。
    """
    am = AtomicMetric.objects.create(
        name='tst_http_atomic', source_path='candidate.age',
        data_type=MetricDataType.NUMBER, status='enabled',
    )
    template = MetricTemplate.objects.create(
        name='tst_http_template', atomic_metric=am,
        operators=['GT', 'LT'], status='enabled', description='',
    )
    tid = str(template.id)

    process = RecruitmentProcess.objects.create(
        code=_new_id()[:12], name='tst_http_流程',
        current_version='V1.0', version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_new_id()[:10], name='tst_http_阶段', stage_type='SCREEN',
    )
    link = ProcessStageLink.objects.create(
        process=process, stage=stage, order=1,
    )
    rule = EntryConditionRule.objects.create(
        link=link, process_id=str(process.id),
        workflow_version='V1.0', rule_name='tst_http_进入规则',
    )
    ConditionItem.objects.create(
        rule=rule, item_seq=1, condition_type='METRIC',
        field=tid, operator='GT', value=18,
    )
    StageRule.objects.create(
        link=link,
        skip_rules=[{
            'id': 'skip-http-1',
            'name': 'tst_http_跳过规则',
            'enabled': True,
            'scope': 'ALL',
            'expression': '1',
            'action': 'SKIP',
            'items': [
                {'condition_type': 'METRIC', 'field': tid,
                 'operator': 'EQ', 'value': 10},
            ],
        }],
    )
    return template, rule, process


def test_affected_rules_endpoint_envelope_and_camelcase(auth_client):
    """(a) 命中被引用模板 → 200 + 信封(code==0) + camelCase 字段 + 引用规则出现。"""
    template, rule, process = _build_template_with_reference()

    resp = auth_client.get(f'{BASE}templates/{template.id}/affected-rules/')

    assert resp.status_code == 200
    body = resp.json()
    # 信封契约：success_response 包裹 → {success: True, code: 0, data, message}
    assert body['success'] is True
    assert body['code'] == 0
    data = body['data']
    # camelCase 键由 CamelCaseJSONRenderer 在最终渲染时由 snake_case 转换
    assert 'entryConditions' in data
    assert 'stageRules' in data
    assert 'total' in data
    # 进入条件 1 条 + 跳过规则 1 条
    assert data['total'] == 2
    assert len(data['entryConditions']) == 1
    assert len(data['stageRules']) == 1
    # 引用的进入条件规则确实出现（按 camelCase 键断言）
    entry = data['entryConditions'][0]
    assert entry['ruleName'] == rule.rule_name
    assert entry['processName'] == process.name
    # 引用的跳过规则也出现
    assert data['stageRules'][0]['ruleName'] == 'tst_http_跳过规则'


def test_affected_rules_endpoint_404_for_missing_template(auth_client):
    """(b) 不存在的 UUID 作 pk → 404（视图捕获 MetricTemplate.DoesNotExist）。"""
    missing_pk = '00000000-0000-0000-0000-000000000000'
    resp = auth_client.get(f'{BASE}templates/{missing_pk}/affected-rules/')

    assert resp.status_code == 404

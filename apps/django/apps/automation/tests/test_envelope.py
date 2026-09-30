"""信封契约 — AutomationRuleViewSet / AutomationLogViewSet (信封收口 Batch 10, 后端-only).

- AutomationRuleViewSet 加 EnvelopeWriteMixin(首位基类) 覆盖 create / retrieve / update;
  @action toggle/logs/stats 已手动信封, 保留.
- AutomationLogViewSet 加 EnvelopeReadOnlyMixin 覆盖 retrieve (list 已由分页信封).

FE 影响面核查: 全仓 web/app/src 无 automation-rules 端点 API 调用 → 零 FE 改动.

权限: HasProcessPermission / V2Permission, auth_client=super_user 经 is_super_admin 短路.
"""
import uuid

import pytest
from rest_framework.test import APIClient

from apps.automation.models import AutomationLog, AutomationRule
from apps.candidate.models import Candidate
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db

RULE_LIST = '/api/v1/automation-rules/'
LOG_LIST = '/api/v1/automation-rules/logs/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_process():
    process = RecruitmentProcess.objects.create(
        code=_uid('PROC'), name='信封流程', current_version='V1.0',
        version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_uid('STG'), name='信封阶段', stage_type=StageType.SCREEN,
    )
    ProcessStageLink.objects.create(
        process=process, stage=stage, order=1, is_required=True,
    )
    return process, stage


def _make_rule(process, stage) -> AutomationRule:
    return AutomationRule.objects.create(
        name='信封规则', process=process, stage=stage,
        trigger_type='STAGE_ENTERED', trigger_timing='IMMEDIATE',
        action_type='REMIND',
    )


# ---------- AutomationRuleViewSet ----------

def test_rule_list_envelope(auth_client):
    resp = auth_client.get(RULE_LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_rule_retrieve_envelope(auth_client):
    process, stage = _make_process()
    rule = _make_rule(process, stage)
    resp = auth_client.get(f'{RULE_LIST}{rule.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(rule.id)
    assert resp.data['data']['name'] == '信封规则'


def test_rule_update_envelope(auth_client):
    process, stage = _make_process()
    rule = _make_rule(process, stage)
    resp = auth_client.patch(
        f'{RULE_LIST}{rule.id}/', {'name': '信封规则改'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['data']['name'] == '信封规则改'


def test_rule_create_envelope(auth_client):
    process, stage = _make_process()
    resp = auth_client.post(RULE_LIST, {
        'name': '信封新建规则',
        'process': str(process.id),
        'stage': str(stage.id),
        'trigger_type': 'STAGE_ENTERED',
        'trigger_timing': 'IMMEDIATE',
        'action_type': 'REMIND',
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['success'] is True
    assert resp.data['data']['id']
    assert resp.data['data']['name'] == '信封新建规则'


# ---------- AutomationLogViewSet (ReadOnly) ----------

def test_log_list_envelope(auth_client):
    process, stage = _make_process()
    rule = _make_rule(process, stage)
    AutomationLog.objects.create(
        rule=rule, candidate_id='cand-log-001',
        evaluate_result='PASS', action_taken='REMIND',
    )
    resp = auth_client.get(LOG_LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_log_retrieve_envelope(auth_client):
    process, stage = _make_process()
    rule = _make_rule(process, stage)
    log = AutomationLog.objects.create(
        rule=rule, candidate_id='cand-log-002',
        evaluate_result='PASS', action_taken='REMIND',
    )
    resp = auth_client.get(f'{LOG_LIST}{log.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(log.id)

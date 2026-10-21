"""候选人审计体系行为测试（Task 2/3/4 挂钩 —— 穿透真实链路）。

覆盖：
- 基本信息更新 → INFO_UPDATED 字段级 before/after diff（穿透 PATCH 端点）
- 简历文件替换   → RESUME_UPLOADED（穿透 PATCH 端点）
- 阶段变更       → 跨 app 写 STAGE_CHANGED（穿透 ApplicationService.advance）
- histories 查询 → 时间倒序 + action 过滤
- verify 接口    → 篡改行哈希链可检测
"""
import pytest
from django.utils import timezone

from apps.candidate.models import Candidate, CandidateHistory
from apps.application.models import Application, ApplicationState, ApplicationStageRecord
from apps.application.services import ApplicationService
from apps.position.models import Position, PositionState
from apps.process.models import ProcessStageLink, RecruitmentProcess, RecruitmentStage, StageType


def _unpack(resp, key='data'):
    """兼容 {code,message,data:{results}} 信封 与 裸 {data:{...}} 两种形态。"""
    body = resp.json()
    inner = body.get(key, body) if isinstance(body, dict) else body
    if isinstance(inner, dict) and 'results' in inner:
        return inner['results']
    return inner


@pytest.mark.django_db
class TestCandidateAuditBehavior:
    def test_update_records_info_updated_with_field_diff(self, auth_client):
        c = Candidate.objects.create(name='审计A', phone='13800007001', email='old@x.com', recruit_type='social')
        resp = auth_client.patch(f'/api/v1/candidates/{c.id}/', {'email': 'new@x.com'}, format='json')
        assert resp.status_code == 200, resp.content
        h = CandidateHistory.objects.filter(candidate=c, action='INFO_UPDATED').first()
        assert h is not None, '基本信息更新应写入 INFO_UPDATED'
        changes = {ch['field']: ch for ch in h.detail.get('changes', [])}
        assert 'email' in changes, 'email 变更应被字段级记录'
        assert changes['email']['old'] == 'old@x.com'
        assert changes['email']['new'] == 'new@x.com'

    def test_update_records_resume_uploaded(self, auth_client):
        c = Candidate.objects.create(name='审计B', phone='13800007002', recruit_type='social')
        resp = auth_client.patch(
            f'/api/v1/candidates/{c.id}/', {'resume_file_url': 'https://x.com/r.pdf'}, format='json',
        )
        assert resp.status_code == 200, resp.content
        h = CandidateHistory.objects.filter(candidate=c, action='RESUME_UPLOADED').first()
        assert h is not None, '简历文件替换应写入 RESUME_UPLOADED'
        changes = {ch['field']: ch for ch in h.detail.get('changes', [])}
        assert changes.get('resume_file_url', {}).get('new') == 'https://x.com/r.pdf'

    def test_update_accepts_relative_resume_url(self, auth_client):
        """2026-10-21 回归：本地/SECURE_MEDIA_DOWNLOAD 回传的是站内相对路径
        (/media/uploads/... 或 /api/v1/media/secure/...)，PATCH 必须接受，不得按 URLField 拒绝 400。
        """
        c = Candidate.objects.create(name='审计相对路径', phone='13800007012', recruit_type='social')
        for url in ('/media/uploads/20261021/abc.pdf', '/api/v1/media/secure/uploads/20261021/abc.pdf'):
            resp = auth_client.patch(
                f'/api/v1/candidates/{c.id}/', {'resume_file_url': url}, format='json',
            )
            assert resp.status_code == 200, f'相对路径 {url} 应被接受: {resp.content}'
            c.refresh_from_db()
            assert c.resume_file_url == url

    def test_histories_endpoint_time_desc_and_filter(self, auth_client):
        c = Candidate.objects.create(name='审计C', phone='13800007003', recruit_type='social')
        CandidateHistory.objects.create(candidate=c, action='INFO_UPDATED', detail={'changes': []})
        CandidateHistory.objects.create(candidate=c, action='RESUME_PARSED', detail={'parse': {}})
        resp = auth_client.get(f'/api/v1/candidates/{c.id}/histories/')
        assert resp.status_code == 200, resp.content
        items = _unpack(resp)
        actions = [r['action'] for r in items]
        assert 'RESUME_PARSED' in actions and 'INFO_UPDATED' in actions
        # action 过滤
        resp2 = auth_client.get(f'/api/v1/candidates/{c.id}/histories/?action=RESUME_PARSED')
        items2 = _unpack(resp2)
        assert all(r['action'] == 'RESUME_PARSED' for r in items2), 'action 过滤应只返回 RESUME_PARSED'

    def test_verify_detects_tampered_row(self, auth_client):
        c = Candidate.objects.create(name='审计D', phone='13800007004', recruit_type='social')
        h1 = CandidateHistory.objects.create(candidate=c, action='CREATED', detail={'source': 'api'})
        h2 = CandidateHistory.objects.create(candidate=c, action='INFO_UPDATED', detail={'changes': []})
        h1.refresh_from_db()
        h2.refresh_from_db()
        # 篡改第二行 row_hash（绕过模型 save 守卫，直接 SQL 更新，模拟外部篡改）
        CandidateHistory.objects.filter(pk=h2.pk).update(row_hash='deadbeef' * 8)
        resp = auth_client.get(f'/api/v1/candidates/{c.id}/histories/verify/')
        assert resp.status_code == 200, resp.content
        body = resp.json()
        data = body.get('data', body)
        assert data.get('ok') is False, '篡改哈希后应检测失败'
        assert data.get('brokenAt') == h2.seq, 'brokenAt 应指向被篡改行'

    def test_stage_change_writes_candidate_history(self, super_user, department):
        process = RecruitmentProcess.objects.create(
            code='AUDITP', name='审计流程', current_version='V1.0', version_seq=1, is_latest=True,
        )
        s1 = RecruitmentStage.objects.create(code='AS1', name='初筛', stage_type=StageType.SCREEN)
        s2 = RecruitmentStage.objects.create(code='AS2', name='面试', stage_type=StageType.INTERVIEW)
        link1 = ProcessStageLink.objects.create(process=process, stage=s1, order=1)
        ProcessStageLink.objects.create(process=process, stage=s2, order=2)
        position = Position.objects.create(
            code='AUDITPOS', title='审计职位', department=department,
            hiring_manager=super_user, owner=super_user, headcount=1,
            state=PositionState.DRAFT, process=process,
        )
        position.submit_publish()
        position.save()
        position.publish()
        position.save()
        cand = Candidate.objects.create(name='审计E', phone='13800007005', recruit_type='social')
        app = Application.objects.create(
            code='AUDITAPP', candidate=cand, position=position, process=process,
            workflow_version=process.current_version, state=ApplicationState.ACTIVE,
            current_link=link1, current_stage=s1, last_advanced_at=timezone.now(),
        )
        ApplicationStageRecord.objects.create(
            application=app, link=link1, stage=s1,
            state=ApplicationStageRecord.StageState.PENDING, entered_at=timezone.now(),
        )
        before = CandidateHistory.objects.filter(candidate=cand, action='STAGE_CHANGED').count()
        ApplicationService.advance_application_to_next_stage(app)
        after = CandidateHistory.objects.filter(candidate=cand, action='STAGE_CHANGED').count()
        assert after == before + 1, '阶段推进应写一条 STAGE_CHANGED'
        h = CandidateHistory.objects.filter(candidate=cand, action='STAGE_CHANGED').order_by('-seq').first()
        assert h.detail['from_stage'] == '初筛' and h.detail['to_stage'] == '面试', h.detail
